"""
Healing Validation Pipeline - Plan → Patch → Validate → Rollback loop.

Implements a structured healing workflow with validation gates and rollback
capability based on oracle guidance for deterministic self-healing.
"""

import logging
import subprocess
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ValidationGate(str, Enum):
    """Validation gates that patches must pass."""
    SYNTAX_CHECK = "syntax_check"
    LINT_CHECK = "lint_check"
    TYPE_CHECK = "type_check"
    UNIT_TESTS = "unit_tests"
    INTEGRATION_TESTS = "integration_tests"


@dataclass
class Patch:
    """Represents a code patch to be applied."""
    file_path: str
    original_content: str
    patched_content: str
    description: str
    issue_type: str = ""
    line_range: Optional[Tuple[int, int]] = None
    confidence: float = 0.0
    applied_at: Optional[datetime] = None


@dataclass
class ValidationResult:
    """Result of a validation gate."""
    gate: ValidationGate
    passed: bool
    output: str = ""
    error: str = ""
    duration_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealingRun:
    """Tracks a complete healing run with all steps and outcomes."""
    run_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    
    detected_issues: List[Dict[str, Any]] = field(default_factory=list)
    proposed_patches: List[Patch] = field(default_factory=list)
    applied_patches: List[Patch] = field(default_factory=list)
    validation_steps: List[ValidationResult] = field(default_factory=list)
    
    overall_result: str = "pending"  # pending, success, failed, rolled_back
    trust_level: int = 0
    
    timing: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    rollback_performed: bool = False
    rollback_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence."""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "detected_issues_count": len(self.detected_issues),
            "proposed_patches_count": len(self.proposed_patches),
            "applied_patches_count": len(self.applied_patches),
            "validation_steps": [
                {
                    "gate": v.gate.value,
                    "passed": v.passed,
                    "duration_ms": v.duration_ms,
                }
                for v in self.validation_steps
            ],
            "overall_result": self.overall_result,
            "trust_level": self.trust_level,
            "timing": self.timing,
            "rollback_performed": self.rollback_performed,
            "rollback_reason": self.rollback_reason,
        }


class HealingValidationPipeline:
    """
    Implements Plan → Patch → Validate → Rollback healing loop.
    
    Features:
    - File snapshots before patching for safe rollback
    - Multi-gate validation (syntax, lint, type, tests)
    - Trust level enforcement for auto-apply decisions
    - Genesis Key trail for audit
    """

    def __init__(
        self,
        repo_path: Optional[Path] = None,
        test_subset: Optional[List[str]] = None,
        pytest_args: Optional[List[str]] = None,
    ):
        self.repo_path = repo_path or Path.cwd()
        self.test_subset = test_subset or []
        self.pytest_args = pytest_args or ["-q", "--tb=short", "-x"]
        
        self._snapshots: Dict[str, str] = {}
        self._current_run: Optional[HealingRun] = None
        
        self._tool_cache: Dict[str, bool] = {}
        
        logger.info(f"[HEALING-PIPELINE] Initialized with repo_path={self.repo_path}")

    def create_snapshot(self, files: List[str]) -> Dict[str, str]:
        """
        Backup file contents before patching.
        
        Args:
            files: List of file paths to snapshot
            
        Returns:
            Dict mapping file paths to their original contents
        """
        snapshots = {}
        for file_path in files:
            path = Path(file_path)
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8")
                    snapshots[str(path.absolute())] = content
                    logger.debug(f"[HEALING-PIPELINE] Snapshot created for {file_path}")
                except Exception as e:
                    logger.warning(f"[HEALING-PIPELINE] Could not snapshot {file_path}: {e}")
            else:
                logger.warning(f"[HEALING-PIPELINE] File not found for snapshot: {file_path}")
        
        self._snapshots.update(snapshots)
        return snapshots

    def apply_patch(self, patch: Patch) -> bool:
        """
        Apply a patch to a file.
        
        Args:
            patch: The Patch object to apply
            
        Returns:
            True if patch was applied successfully
        """
        try:
            path = Path(patch.file_path)
            
            if str(path.absolute()) not in self._snapshots:
                self.create_snapshot([str(path)])
            
            path.write_text(patch.patched_content, encoding="utf-8")
            patch.applied_at = datetime.utcnow()
            
            logger.info(f"[HEALING-PIPELINE] Applied patch to {patch.file_path}: {patch.description}")
            return True
            
        except Exception as e:
            logger.error(f"[HEALING-PIPELINE] Failed to apply patch to {patch.file_path}: {e}")
            return False

    def validate(
        self,
        gates: List[ValidationGate],
        files: Optional[List[str]] = None,
    ) -> Tuple[bool, List[ValidationResult]]:
        """
        Run validation gates.
        
        Args:
            gates: List of validation gates to run
            files: Optional list of files to validate (for targeted checks)
            
        Returns:
            (all_passed, list of ValidationResult)
        """
        results = []
        all_passed = True
        
        for gate in gates:
            start_time = time.time()
            
            if gate == ValidationGate.SYNTAX_CHECK:
                result = self._run_syntax_check(files)
            elif gate == ValidationGate.LINT_CHECK:
                result = self._run_lint_check(files)
            elif gate == ValidationGate.TYPE_CHECK:
                result = self._run_type_check(files)
            elif gate == ValidationGate.UNIT_TESTS:
                result = self._run_unit_tests()
            elif gate == ValidationGate.INTEGRATION_TESTS:
                result = self._run_integration_tests()
            else:
                result = ValidationResult(
                    gate=gate,
                    passed=False,
                    error=f"Unknown validation gate: {gate}",
                )
            
            result.duration_ms = (time.time() - start_time) * 1000
            results.append(result)
            
            if not result.passed:
                all_passed = False
                logger.warning(
                    f"[HEALING-PIPELINE] Validation gate {gate.value} FAILED: {result.error or result.output[:200]}"
                )
            else:
                logger.info(f"[HEALING-PIPELINE] Validation gate {gate.value} PASSED")
        
        return all_passed, results

    def rollback(self, reason: str = "") -> bool:
        """
        Restore files from snapshot if validation fails.
        
        Args:
            reason: Reason for rollback (for logging)
            
        Returns:
            True if all files were restored
        """
        if not self._snapshots:
            logger.warning("[HEALING-PIPELINE] No snapshots available for rollback")
            return False
        
        success = True
        restored_count = 0
        
        for file_path, content in self._snapshots.items():
            try:
                path = Path(file_path)
                path.write_text(content, encoding="utf-8")
                restored_count += 1
                logger.debug(f"[HEALING-PIPELINE] Restored {file_path}")
            except Exception as e:
                logger.error(f"[HEALING-PIPELINE] Failed to restore {file_path}: {e}")
                success = False
        
        logger.info(
            f"[HEALING-PIPELINE] Rollback completed: {restored_count}/{len(self._snapshots)} files restored. "
            f"Reason: {reason}"
        )
        
        if self._current_run:
            self._current_run.rollback_performed = True
            self._current_run.rollback_reason = reason
        
        self._snapshots.clear()
        return success

    def commit_healing_run(self, run: HealingRun) -> bool:
        """
        Persist healing run to Genesis Key trail.
        
        Args:
            run: The HealingRun to persist
            
        Returns:
            True if successfully committed
        """
        try:
            from genesis.genesis_key_service import get_genesis_service
            from models.genesis_key_models import GenesisKeyType
            
            genesis = get_genesis_service()
            
            genesis.create_key(
                key_type=GenesisKeyType.FIX if run.overall_result == "success" else GenesisKeyType.SYSTEM_EVENT,
                what_description=f"Healing run {run.run_id}: {run.overall_result}",
                who_actor="healing_validation_pipeline",
                where_location=str(self.repo_path),
                why_reason=f"Detected {len(run.detected_issues)} issues, applied {len(run.applied_patches)} patches",
                how_method="Plan-Patch-Validate-Rollback loop",
                context_data=run.to_dict(),
                tags=["healing", "validation_pipeline", run.overall_result],
            )
            
            logger.info(f"[HEALING-PIPELINE] Committed healing run {run.run_id} to Genesis trail")
            return True
            
        except Exception as e:
            logger.error(f"[HEALING-PIPELINE] Failed to commit healing run: {e}")
            return False

    def get_required_gates_for_trust_level(self, trust_level: int) -> List[ValidationGate]:
        """
        Get required validation gates based on trust level.
        
        Trust levels:
        - 0-1: No auto-apply (return empty - manual only)
        - 2-3: Require SYNTAX_CHECK + LINT_CHECK
        - 4+: Require full test suite
        
        Args:
            trust_level: Trust level (0-9)
            
        Returns:
            List of required validation gates
        """
        if trust_level <= 1:
            return []
        elif trust_level <= 3:
            return [ValidationGate.SYNTAX_CHECK, ValidationGate.LINT_CHECK]
        else:
            return [
                ValidationGate.SYNTAX_CHECK,
                ValidationGate.LINT_CHECK,
                ValidationGate.TYPE_CHECK,
                ValidationGate.UNIT_TESTS,
            ]

    def can_auto_apply(self, trust_level: int) -> bool:
        """Check if auto-apply is allowed at this trust level."""
        return trust_level >= 2

    def execute_healing_loop(
        self,
        issues: List[Dict[str, Any]],
        patches: List[Patch],
        trust_level: int,
    ) -> HealingRun:
        """
        Execute the complete Plan → Patch → Validate → Rollback loop.
        
        Args:
            issues: Detected issues to heal
            patches: Proposed patches
            trust_level: Current trust level
            
        Returns:
            HealingRun with complete results
        """
        import uuid
        
        run = HealingRun(
            run_id=f"HR-{uuid.uuid4().hex[:12]}",
            started_at=datetime.utcnow(),
            detected_issues=issues,
            proposed_patches=patches,
            trust_level=trust_level,
        )
        self._current_run = run
        
        start_time = time.time()
        
        if not self.can_auto_apply(trust_level):
            run.overall_result = "manual_required"
            run.completed_at = datetime.utcnow()
            run.timing["total_ms"] = (time.time() - start_time) * 1000
            logger.info(f"[HEALING-PIPELINE] Trust level {trust_level} requires manual approval")
            return run
        
        file_paths = [p.file_path for p in patches]
        self.create_snapshot(file_paths)
        run.timing["snapshot_ms"] = (time.time() - start_time) * 1000
        
        patch_start = time.time()
        for patch in patches:
            if self.apply_patch(patch):
                run.applied_patches.append(patch)
        run.timing["patch_ms"] = (time.time() - patch_start) * 1000
        
        if not run.applied_patches:
            run.overall_result = "no_patches_applied"
            run.completed_at = datetime.utcnow()
            run.timing["total_ms"] = (time.time() - start_time) * 1000
            return run
        
        required_gates = self.get_required_gates_for_trust_level(trust_level)
        
        validate_start = time.time()
        all_passed, results = self.validate(required_gates, file_paths)
        run.validation_steps = results
        run.timing["validation_ms"] = (time.time() - validate_start) * 1000
        
        if all_passed:
            run.overall_result = "success"
            self._snapshots.clear()
            logger.info(
                f"[HEALING-PIPELINE] Healing run {run.run_id} SUCCEEDED: "
                f"{len(run.applied_patches)} patches applied, all gates passed"
            )
        else:
            failed_gates = [r.gate.value for r in results if not r.passed]
            rollback_start = time.time()
            self.rollback(f"Validation failed: {', '.join(failed_gates)}")
            run.timing["rollback_ms"] = (time.time() - rollback_start) * 1000
            run.overall_result = "rolled_back"
            logger.warning(
                f"[HEALING-PIPELINE] Healing run {run.run_id} ROLLED BACK: "
                f"Failed gates: {failed_gates}"
            )
        
        run.completed_at = datetime.utcnow()
        run.timing["total_ms"] = (time.time() - start_time) * 1000
        
        self.commit_healing_run(run)
        self._current_run = None
        
        return run

    def _run_syntax_check(self, files: Optional[List[str]] = None) -> ValidationResult:
        """Run Python syntax check using py_compile."""
        if files:
            py_files = [f for f in files if f.endswith(".py")]
        else:
            py_files = list(self.repo_path.rglob("*.py"))[:50]
        
        errors = []
        for file_path in py_files:
            try:
                result = subprocess.run(
                    ["python", "-m", "py_compile", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=str(self.repo_path),
                )
                if result.returncode != 0:
                    errors.append(f"{file_path}: {result.stderr.strip()}")
            except subprocess.TimeoutExpired:
                errors.append(f"{file_path}: Timeout during syntax check")
            except Exception as e:
                errors.append(f"{file_path}: {str(e)}")
        
        return ValidationResult(
            gate=ValidationGate.SYNTAX_CHECK,
            passed=len(errors) == 0,
            output=f"Checked {len(py_files)} files",
            error="\n".join(errors) if errors else "",
            details={"files_checked": len(py_files), "errors": len(errors)},
        )

    def _run_lint_check(self, files: Optional[List[str]] = None) -> ValidationResult:
        """Run linter check (ruff or flake8)."""
        linter = self._detect_linter()
        if not linter:
            return ValidationResult(
                gate=ValidationGate.LINT_CHECK,
                passed=True,
                output="No linter available (ruff/flake8) - skipping",
                details={"skipped": True},
            )
        
        try:
            if files:
                target = [f for f in files if f.endswith(".py")]
                if not target:
                    return ValidationResult(
                        gate=ValidationGate.LINT_CHECK,
                        passed=True,
                        output="No Python files to lint",
                    )
            else:
                target = ["."]
            
            if linter == "ruff":
                cmd = ["ruff", "check", "--quiet"] + target
            else:
                cmd = ["flake8", "--quiet"] + target
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.repo_path),
            )
            
            passed = result.returncode == 0
            return ValidationResult(
                gate=ValidationGate.LINT_CHECK,
                passed=passed,
                output=result.stdout,
                error=result.stderr if not passed else "",
                details={"linter": linter, "return_code": result.returncode},
            )
            
        except subprocess.TimeoutExpired:
            return ValidationResult(
                gate=ValidationGate.LINT_CHECK,
                passed=False,
                error="Lint check timed out",
            )
        except Exception as e:
            return ValidationResult(
                gate=ValidationGate.LINT_CHECK,
                passed=False,
                error=str(e),
            )

    def _run_type_check(self, files: Optional[List[str]] = None) -> ValidationResult:
        """Run type check using mypy if available."""
        if not self._has_tool("mypy"):
            return ValidationResult(
                gate=ValidationGate.TYPE_CHECK,
                passed=True,
                output="mypy not available - skipping type check",
                details={"skipped": True},
            )
        
        try:
            if files:
                target = [f for f in files if f.endswith(".py")]
                if not target:
                    return ValidationResult(
                        gate=ValidationGate.TYPE_CHECK,
                        passed=True,
                        output="No Python files to type check",
                    )
            else:
                target = ["."]
            
            result = subprocess.run(
                ["python", "-m", "mypy", "--ignore-missing-imports", "--no-error-summary"] + target,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(self.repo_path),
            )
            
            passed = result.returncode == 0
            return ValidationResult(
                gate=ValidationGate.TYPE_CHECK,
                passed=passed,
                output=result.stdout,
                error=result.stderr if not passed else "",
                details={"return_code": result.returncode},
            )
            
        except subprocess.TimeoutExpired:
            return ValidationResult(
                gate=ValidationGate.TYPE_CHECK,
                passed=False,
                error="Type check timed out",
            )
        except Exception as e:
            return ValidationResult(
                gate=ValidationGate.TYPE_CHECK,
                passed=False,
                error=str(e),
            )

    def _run_unit_tests(self) -> ValidationResult:
        """Run unit tests using pytest."""
        try:
            cmd = ["python", "-m", "pytest"] + self.pytest_args
            
            if self.test_subset:
                cmd.extend(self.test_subset)
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.repo_path),
            )
            
            passed = result.returncode == 0
            return ValidationResult(
                gate=ValidationGate.UNIT_TESTS,
                passed=passed,
                output=result.stdout,
                error=result.stderr if not passed else "",
                details={"return_code": result.returncode},
            )
            
        except subprocess.TimeoutExpired:
            return ValidationResult(
                gate=ValidationGate.UNIT_TESTS,
                passed=False,
                error="Unit tests timed out",
            )
        except Exception as e:
            return ValidationResult(
                gate=ValidationGate.UNIT_TESTS,
                passed=False,
                error=str(e),
            )

    def _run_integration_tests(self) -> ValidationResult:
        """Run integration tests (placeholder for project-specific implementation)."""
        return ValidationResult(
            gate=ValidationGate.INTEGRATION_TESTS,
            passed=True,
            output="Integration tests not configured - skipping",
            details={"skipped": True},
        )

    def _detect_linter(self) -> Optional[str]:
        """Detect available linter (ruff preferred over flake8)."""
        if self._has_tool("ruff"):
            return "ruff"
        if self._has_tool("flake8"):
            return "flake8"
        return None

    def _has_tool(self, tool: str) -> bool:
        """Check if a tool is available."""
        if tool in self._tool_cache:
            return self._tool_cache[tool]
        
        result = shutil.which(tool) is not None
        self._tool_cache[tool] = result
        return result


_healing_pipeline: Optional[HealingValidationPipeline] = None


def get_healing_validation_pipeline(
    repo_path: Optional[Path] = None,
) -> HealingValidationPipeline:
    """Get or create global healing validation pipeline instance."""
    global _healing_pipeline
    if _healing_pipeline is None or repo_path is not None:
        _healing_pipeline = HealingValidationPipeline(repo_path=repo_path)
    return _healing_pipeline
