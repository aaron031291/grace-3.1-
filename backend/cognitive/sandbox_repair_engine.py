"""
cognitive/sandbox_repair_engine.py
───────────────────────────────────────────────────────────────────────
Sandbox Repair Engine  (Phase 3.3)

Isolated test environment for auto-generated patches.

Problem:
  HealingCoordinator generates code fixes → FixApplier writes directly
  to disk → if the fix breaks something, rollback is reactive.

Solution:
  Before FixApplier touches the live codebase, SandboxRepairEngine:
  1. Copies the target file (+ its test file) into a temp sandbox
  2. Applies the patch to the SANDBOX copy
  3. Runs syntax check → static analysis → test execution in isolation
  4. Only if ALL checks pass → promotes the patch for live application
  5. Records sandbox verdict as a learning example for future decisions

Flow:
  HealingCoordinator._step_code_fix() → SandboxRepairEngine.evaluate()
    → sandbox_copy → apply_patch → syntax_check → run_tests
    → SandboxVerdict (pass/fail + detail)
  If verdict.passed → FixApplier.apply() (live)
  If verdict.failed → reject patch, store failure as learning

Connected to:
  - code_sandbox.py (subprocess execution, static analysis)
  - fix_applier.py (live application after sandbox approval)
  - healing_coordinator.py (upstream — generates the patch)
  - unified_memory (stores sandbox outcomes as learning examples)
  - event_bus (publishes sandbox.repair.* events)
"""

import ast
import hashlib
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent  # backend/
_PROJECT_ROOT = _BACKEND_ROOT.parent
MAX_TEST_TIMEOUT = 60  # seconds for test execution in sandbox


@dataclass
class SandboxVerdict:
    """Result of evaluating a patch in the sandbox."""
    passed: bool = False
    patch_hash: str = ""
    target_file: str = ""
    # Stage results
    syntax_valid: bool = False
    static_warnings: List[str] = field(default_factory=list)
    static_clean: bool = False
    tests_run: bool = False
    tests_passed: bool = False
    test_output: str = ""
    test_failures: int = 0
    # Timing
    total_ms: float = 0.0
    # Rejection reason (if failed)
    rejection_reason: str = ""
    # Metadata
    sandbox_dir: str = ""
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "patch_hash": self.patch_hash,
            "target_file": self.target_file,
            "syntax_valid": self.syntax_valid,
            "static_warnings": self.static_warnings,
            "static_clean": self.static_clean,
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "test_failures": self.test_failures,
            "test_output": self.test_output[:2000],
            "total_ms": round(self.total_ms, 1),
            "rejection_reason": self.rejection_reason,
            "timestamp": self.timestamp,
        }


class SandboxRepairEngine:
    """
    Evaluates auto-generated patches in an isolated sandbox before
    they touch the live codebase.

    Usage:
        engine = get_sandbox_repair_engine()
        verdict = engine.evaluate(
            target_file="cognitive/healing_coordinator.py",
            patch_code="<new file contents>",
        )
        if verdict.passed:
            fix_applier.apply(target_file, patch_code)
    """

    def __init__(self):
        self._total_evaluations = 0
        self._total_passed = 0
        self._total_failed = 0
        self._history: List[SandboxVerdict] = []
        self._max_history = 100

    def evaluate(
        self,
        target_file: str,
        patch_code: str,
        run_tests: bool = True,
        test_file: Optional[str] = None,
    ) -> SandboxVerdict:
        """
        Evaluate a patch in the sandbox.

        Args:
            target_file: Relative path (to backend/) of the file to patch
            patch_code: The new file contents (complete replacement)
            run_tests: Whether to run the test file in sandbox
            test_file: Explicit test file path. If None, auto-discovers.

        Returns:
            SandboxVerdict with pass/fail and detailed results
        """
        self._total_evaluations += 1
        t0 = time.perf_counter()
        patch_hash = hashlib.sha256(patch_code.encode()).hexdigest()[:16]

        verdict = SandboxVerdict(
            patch_hash=patch_hash,
            target_file=target_file,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # ── Stage 1: Syntax check ─────────────────────────────────
        try:
            ast.parse(patch_code)
            verdict.syntax_valid = True
        except SyntaxError as e:
            verdict.rejection_reason = f"Syntax error: line {e.lineno}: {e.msg}"
            verdict.total_ms = (time.perf_counter() - t0) * 1000
            self._record_verdict(verdict)
            return verdict

        # ── Stage 2: Static analysis ──────────────────────────────
        from cognitive.code_sandbox import static_analyse
        warnings = static_analyse(patch_code)
        verdict.static_warnings = warnings
        verdict.static_clean = len(warnings) == 0

        # Critical static warnings block promotion
        critical_warnings = [w for w in warnings if "dangerous" in w.lower()]
        if critical_warnings:
            verdict.rejection_reason = f"Critical static analysis: {critical_warnings[0]}"
            verdict.total_ms = (time.perf_counter() - t0) * 1000
            self._record_verdict(verdict)
            return verdict

        # ── Stage 3: Sandbox test execution ───────────────────────
        if run_tests:
            sandbox_dir = None
            try:
                sandbox_dir = self._create_sandbox(target_file, patch_code, test_file)
                verdict.sandbox_dir = str(sandbox_dir)

                actual_test = test_file or self._discover_test_file(target_file)
                if actual_test:
                    test_result = self._run_tests_in_sandbox(
                        sandbox_dir, target_file, actual_test,
                    )
                    verdict.tests_run = True
                    verdict.tests_passed = test_result["passed"]
                    verdict.test_output = test_result["output"]
                    verdict.test_failures = test_result["failures"]

                    if not verdict.tests_passed:
                        verdict.rejection_reason = (
                            f"Tests failed ({verdict.test_failures} failure(s)): "
                            f"{test_result['error_summary']}"
                        )
                        verdict.total_ms = (time.perf_counter() - t0) * 1000
                        self._record_verdict(verdict)
                        return verdict
                else:
                    # No test file found — still pass syntax + static
                    verdict.tests_run = False
            finally:
                if sandbox_dir:
                    self._cleanup_sandbox(sandbox_dir)

        # ── All stages passed ─────────────────────────────────────
        verdict.passed = True
        verdict.total_ms = (time.perf_counter() - t0) * 1000
        self._total_passed += 1
        self._record_verdict(verdict)

        logger.info(
            "[SANDBOX-REPAIR] ✅ Patch %s approved for %s (%.1fms, tests=%s)",
            patch_hash, target_file, verdict.total_ms,
            "passed" if verdict.tests_passed else "skipped",
        )
        return verdict

    # ── Sandbox Environment ───────────────────────────────────────────

    def _create_sandbox(
        self,
        target_file: str,
        patch_code: str,
        test_file: Optional[str],
    ) -> Path:
        """
        Create an isolated sandbox directory with:
        - The patched target file
        - The test file (if found)
        - Minimal necessary context (conftest, __init__.py files)
        """
        sandbox = Path(tempfile.mkdtemp(prefix="grace_sandbox_"))

        # Resolve target path
        target_path = _BACKEND_ROOT / target_file
        if not target_path.suffix:
            target_path = target_path.with_suffix(".py")

        # Create directory structure in sandbox
        sandbox_target = sandbox / target_file
        sandbox_target.parent.mkdir(parents=True, exist_ok=True)

        # Write patched code
        sandbox_target.write_text(patch_code, encoding="utf-8")

        # Copy __init__.py files along the path for proper imports
        rel_parts = Path(target_file).parts[:-1]
        for i in range(len(rel_parts)):
            init_src = _BACKEND_ROOT / Path(*rel_parts[:i+1]) / "__init__.py"
            init_dst = sandbox / Path(*rel_parts[:i+1]) / "__init__.py"
            if init_src.exists():
                init_dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(init_src, init_dst)
            else:
                init_dst.parent.mkdir(parents=True, exist_ok=True)
                init_dst.touch()

        # Copy test file
        actual_test = test_file or self._discover_test_file(target_file)
        if actual_test:
            test_path = _BACKEND_ROOT / actual_test
            if test_path.exists():
                sandbox_test = sandbox / actual_test
                sandbox_test.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(test_path, sandbox_test)

                # Copy test __init__.py files
                test_parts = Path(actual_test).parts[:-1]
                for i in range(len(test_parts)):
                    init_src = _BACKEND_ROOT / Path(*test_parts[:i+1]) / "__init__.py"
                    init_dst = sandbox / Path(*test_parts[:i+1]) / "__init__.py"
                    if init_src.exists() and not init_dst.exists():
                        init_dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(init_src, init_dst)
                    elif not init_dst.exists():
                        init_dst.parent.mkdir(parents=True, exist_ok=True)
                        init_dst.touch()

        # Copy conftest.py if it exists
        conftest = _BACKEND_ROOT / "conftest.py"
        if conftest.exists():
            shutil.copy2(conftest, sandbox / "conftest.py")

        # Copy pytest.ini if it exists
        pytest_ini = _BACKEND_ROOT / "pytest.ini"
        if pytest_ini.exists():
            shutil.copy2(pytest_ini, sandbox / "pytest.ini")

        return sandbox

    def _discover_test_file(self, target_file: str) -> Optional[str]:
        """
        Auto-discover the test file for a given source file.

        Convention mapping:
          cognitive/foo.py → tests/cognitive/test_foo.py
          core/bar.py → tests/core/test_bar.py
          self_healing/baz.py → tests/self_healing/test_baz.py
        """
        target = Path(target_file)
        stem = target.stem
        parent = target.parent

        # Primary: tests/<parent>/test_<stem>.py
        candidates = [
            Path("tests") / parent / f"test_{stem}.py",
            Path("tests") / f"test_{stem}.py",
            parent / f"test_{stem}.py",
        ]

        for candidate in candidates:
            full = _BACKEND_ROOT / candidate
            if full.exists():
                return str(candidate)

        return None

    def _run_tests_in_sandbox(
        self,
        sandbox_dir: Path,
        target_file: str,
        test_file: str,
    ) -> Dict[str, Any]:
        """Run tests in the sandbox subprocess."""
        test_path = sandbox_dir / test_file
        if not test_path.exists():
            return {
                "passed": False,
                "output": "",
                "failures": 0,
                "error_summary": f"Test file not found in sandbox: {test_file}",
            }

        env = os.environ.copy()
        # Add both sandbox and original backend to PYTHONPATH so imports resolve
        env["PYTHONPATH"] = f"{sandbox_dir}{os.pathsep}{_BACKEND_ROOT}{os.pathsep}{_PROJECT_ROOT}"

        try:
            proc = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_path), "-v", "--tb=short", "-x"],
                capture_output=True,
                text=True,
                timeout=MAX_TEST_TIMEOUT,
                cwd=str(sandbox_dir),
                env=env,
            )

            output = proc.stdout + proc.stderr
            passed = proc.returncode == 0

            # Count failures from pytest output
            failures = 0
            for line in output.splitlines():
                if " failed" in line and "passed" in line:
                    import re
                    m = re.search(r"(\d+) failed", line)
                    if m:
                        failures = int(m.group(1))
                elif line.strip().startswith("FAILED"):
                    failures += 1

            # Extract error summary
            error_summary = ""
            if not passed:
                lines = output.strip().splitlines()
                for line in reversed(lines):
                    line = line.strip()
                    if line and not line.startswith("="):
                        error_summary = line[:200]
                        break

            return {
                "passed": passed,
                "output": output[:5000],
                "failures": failures,
                "error_summary": error_summary,
            }

        except subprocess.TimeoutExpired:
            return {
                "passed": False,
                "output": "",
                "failures": 1,
                "error_summary": f"Tests timed out after {MAX_TEST_TIMEOUT}s",
            }
        except Exception as e:
            return {
                "passed": False,
                "output": "",
                "failures": 1,
                "error_summary": str(e)[:200],
            }

    @staticmethod
    def _cleanup_sandbox(sandbox_dir: Path):
        """Remove sandbox temp directory."""
        try:
            shutil.rmtree(sandbox_dir, ignore_errors=True)
        except Exception:
            pass

    # ── Recording & Learning ──────────────────────────────────────────

    def _record_verdict(self, verdict: SandboxVerdict):
        """Record verdict in history, telemetry, and store as learning example."""
        if not verdict.passed:
            self._total_failed += 1

        # Telemetry: record sandbox operation for baseline/drift tracking
        try:
            from telemetry.telemetry_service import get_telemetry_service
            from models.telemetry_models import OperationType
            telemetry = get_telemetry_service()
            with telemetry.track_operation(
                OperationType.SANDBOX_REPAIR,
                f"sandbox_{verdict.target_file}",
                metadata={
                    "passed": verdict.passed,
                    "patch_hash": verdict.patch_hash,
                    "rejection_reason": verdict.rejection_reason[:200] if verdict.rejection_reason else "",
                },
            ):
                pass
        except Exception:
            pass

        self._history.append(verdict)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Store as learning example
        try:
            from cognitive.unified_memory import get_unified_memory
            mem = get_unified_memory()
            mem.store_learning(
                input_ctx=f"Sandbox repair evaluation: {verdict.target_file}",
                expected="patch passes all sandbox checks",
                actual=f"{'PASSED' if verdict.passed else 'FAILED'}: {verdict.rejection_reason or 'all checks passed'}",
                trust=0.85 if verdict.passed else 0.3,
                source="sandbox_repair_engine",
                example_type="sandbox_repair",
            )
        except Exception:
            pass

        # Publish event
        try:
            from cognitive.event_bus import publish_async
            publish_async(
                f"sandbox.repair.{'approved' if verdict.passed else 'rejected'}",
                verdict.to_dict(),
                source="sandbox_repair_engine",
            )
        except Exception:
            pass

        # Genesis tracking
        try:
            from api._genesis_tracker import track
            track(
                key_type="system_event",
                what=f"Sandbox repair {'APPROVED' if verdict.passed else 'REJECTED'}: {verdict.target_file}",
                how="SandboxRepairEngine.evaluate",
                output_data=verdict.to_dict(),
                tags=["sandbox", "repair", "phase_3.3",
                      "approved" if verdict.passed else "rejected"],
            )
        except Exception:
            pass

    # ── Status API ────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_evaluations": self._total_evaluations,
            "total_passed": self._total_passed,
            "total_failed": self._total_failed,
            "pass_rate": round(
                self._total_passed / max(self._total_evaluations, 1), 3
            ),
        }

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [v.to_dict() for v in reversed(self._history[-limit:])]


# ── Singleton ─────────────────────────────────────────────────────────
_engine: Optional[SandboxRepairEngine] = None


def get_sandbox_repair_engine() -> SandboxRepairEngine:
    global _engine
    if _engine is None:
        _engine = SandboxRepairEngine()
    return _engine
