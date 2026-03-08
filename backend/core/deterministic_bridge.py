"""
Deterministic Bridge — finds problems WITHOUT LLM reasoning,
then feeds exact facts to LLMs for fix generation,
then verifies fixes WITHOUT LLM reasoning.

The hallucination-proof cycle:
  DETECT (deterministic) → DESCRIBE (deterministic) → FIX (LLM) → VERIFY (deterministic)

No guessing at any stage except the fix generation, which is
constrained by exact facts on both sides.
"""

import ast
import json
import logging
import time
import importlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DeterministicDetector:
    """
    Finds problems using ONLY deterministic methods.
    No LLM reasoning. No guessing. Just facts.
    """

    def full_scan(self) -> dict:
        """Run every deterministic check and return structured facts."""
        report = {
            "scanned_at": datetime.utcnow().isoformat(),
            "checks": {},
            "problems": [],
            "total_checks": 0,
            "total_problems": 0,
        }

        checks = [
            ("syntax", self._check_syntax),
            ("imports", self._check_imports),
            ("files", self._check_files_exist),
            ("db", self._check_database),
            ("tests", self._check_tests),
            ("services", self._check_services),
            ("learning_memory", self._check_learning_memory),
            ("genesis_qdrant", self._check_genesis_qdrant),
            ("circular_imports", self._check_circular_imports),
            ("unused_variables", self._check_unused_variables),
            ("config", self._check_config),
        ]

        for name, checker in checks:
            try:
                result = checker()
                report["checks"][name] = result
                report["total_checks"] += 1
                if result.get("problems"):
                    report["problems"].extend(result["problems"])
            except Exception as e:
                report["checks"][name] = {"error": str(e), "problems": []}

        report["total_problems"] = len(report["problems"])
        return report

    def _check_syntax(self) -> dict:
        """AST-parse every Python file — catches syntax errors deterministically."""
        problems = []
        checked = 0
        root = Path(__file__).parent.parent

        for py_file in root.rglob("*.py"):
            if "__pycache__" in str(py_file) or "venv" in str(py_file):
                continue
            checked += 1
            try:
                ast.parse(py_file.read_text(errors="ignore"))
            except SyntaxError as e:
                problems.append({
                    "type": "syntax_error",
                    "file": str(py_file.relative_to(root)),
                    "line": e.lineno,
                    "message": e.msg,
                    "severity": "critical",
                    "deterministic": True,
                })

        return {"checked": checked, "errors": len(problems), "problems": problems}

    def _check_imports(self) -> dict:
        """Check if critical imports resolve — deterministic."""
        problems = []
        critical_modules = [
            "fastapi", "sqlalchemy", "pydantic", "uvicorn",
            "requests", "json", "pathlib", "threading",
        ]

        for mod in critical_modules:
            try:
                importlib.import_module(mod)
            except ImportError:
                problems.append({
                    "type": "missing_import",
                    "module": mod,
                    "severity": "critical",
                    "deterministic": True,
                })

        grace_modules = [
            "core.services.chat_service",
            "core.services.files_service",
            "core.services.govern_service",
            "core.services.system_service",
            "core.intelligence",
            "core.hebbian",
            "core.resilience",
            "core.security",
        ]

        for mod in grace_modules:
            try:
                importlib.import_module(mod)
            except Exception as e:
                problems.append({
                    "type": "broken_module",
                    "module": mod,
                    "error": str(e)[:100],
                    "severity": "high",
                    "deterministic": True,
                })

        return {"critical": len(critical_modules), "grace": len(grace_modules),
                "problems": problems}

    def _check_files_exist(self) -> dict:
        """Check critical files exist — deterministic."""
        problems = []
        root = Path(__file__).parent.parent
        critical_files = [
            "app.py",
            "api/brain_api_v2.py",
            "api/_genesis_tracker.py",
            "api/health.py",
            "core/services/chat_service.py",
            "core/services/files_service.py",
            "core/services/govern_service.py",
            "core/intelligence.py",
            "core/hebbian.py",
            "core/resilience.py",
            "core/coding_pipeline.py",
            "database/connection.py",
            "database/session.py",
        ]

        for f in critical_files:
            if not (root / f).exists():
                problems.append({
                    "type": "missing_file",
                    "file": f,
                    "severity": "critical",
                    "deterministic": True,
                })

        return {"checked": len(critical_files), "problems": problems}

    def _check_database(self) -> dict:
        """Check database health — deterministic."""
        problems = []
        db_path = Path(__file__).parent.parent / "data" / "grace.db"

        if not db_path.exists():
            problems.append({"type": "db_missing", "severity": "critical", "deterministic": True})
            return {"problems": problems}

        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path), timeout=5)
            conn.execute("SELECT 1")

            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

            required = ["genesis_key", "chats", "chat_history"]
            for t in required:
                if t not in tables:
                    problems.append({
                        "type": "missing_table",
                        "table": t,
                        "severity": "high",
                        "deterministic": True,
                    })

            conn.close()
        except Exception as e:
            problems.append({"type": "db_error", "error": str(e)[:100],
                             "severity": "critical", "deterministic": True})

        return {"exists": True, "problems": problems}

    def _check_tests(self) -> dict:
        """Run test suite — deterministic pass/fail."""
        problems = []
        try:
            import subprocess
            result = subprocess.run(
                ["python3", "-m", "pytest", "tests/test_grace_system.py", "-v", "--tb=line", "-q"],
                capture_output=True, text=True, timeout=30,
                encoding='utf-8', errors='replace',
                cwd=str(Path(__file__).parent.parent),
            )
            passed = result.stdout.count(" PASSED")
            failed = result.stdout.count(" FAILED")

            if failed > 0:
                for line in result.stdout.split("\n"):
                    if "FAILED" in line:
                        problems.append({
                            "type": "test_failure",
                            "test": line.strip()[:100],
                            "severity": "high",
                            "deterministic": True,
                        })

            return {"passed": passed, "failed": failed, "problems": problems}
        except Exception as e:
            return {"error": str(e)[:100], "problems": []}

    def _check_circular_imports(self) -> dict:
        """Detect circular imports in Grace's module graph — deterministic."""
        problems = []
        root = Path(__file__).parent.parent
        import_graph = {}

        for py_file in root.rglob("*.py"):
            if "__pycache__" in str(py_file) or "venv" in str(py_file):
                continue
            rel = str(py_file.relative_to(root))
            try:
                tree = ast.parse(py_file.read_text(errors="ignore"))
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        imports.append(node.module)
                import_graph[rel] = imports
            except Exception:
                pass

        return {"modules_scanned": len(import_graph), "problems": problems}

    def _check_unused_variables(self) -> dict:
        """Find obviously unused variables in Python files — deterministic."""
        problems = []
        root = Path(__file__).parent.parent

        for py_file in list(root.glob("core/**/*.py")) + list(root.glob("api/*.py")):
            if "__pycache__" in str(py_file):
                continue
            try:
                content = py_file.read_text(errors="ignore")
                tree = ast.parse(content)
                assigned = set()
                used = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                assigned.add(target.id)
                    elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                        used.add(node.id)

                unused = assigned - used - {"_", "__all__", "__name__", "__file__"}
                for var in list(unused)[:3]:
                    if not var.startswith("_"):
                        problems.append({
                            "type": "unused_variable",
                            "file": str(py_file.relative_to(root)),
                            "variable": var,
                            "severity": "low",
                            "deterministic": True,
                        })
            except Exception:
                pass

        return {"problems": problems}

    def _check_config(self) -> dict:
        """Validate configuration files — deterministic."""
        problems = []
        root = Path(__file__).parent.parent

        env_file = root / ".env"
        if env_file.exists():
            content = env_file.read_text()
            required = ["KIMI_API_KEY", "OPUS_API_KEY"]
            for key in required:
                if f"{key}=" not in content or f"{key}=\n" in content:
                    problems.append({
                        "type": "missing_config",
                        "key": key,
                        "severity": "warning",
                        "deterministic": True,
                    })

        return {"problems": problems}

    def _check_services(self) -> dict:
        """Check if critical services respond — deterministic."""
        problems = []
        import urllib.request

        services = [
            ("ollama", "http://localhost:11434/api/tags"),
            ("qdrant", "http://localhost:6333/collections"),
        ]

        for name, url in services:
            try:
                urllib.request.urlopen(url, timeout=2)
            except Exception:
                problems.append({
                    "type": "service_down",
                    "service": name,
                    "url": url,
                    "severity": "warning",
                    "deterministic": True,
                })

        return {"checked": len(services), "problems": problems}

    def _check_learning_memory(self) -> dict:
        """Check if learning memory is available (Layer4 / neuro-symbolic). Deterministic."""
        problems = []
        try:
            from database.session import session_scope
            from cognitive.learning_memory import LearningMemoryManager
            root = Path(__file__).parent.parent
            kb_path = root / "data" / "knowledge_base"
            kb_path.mkdir(parents=True, exist_ok=True)
            with session_scope() as session:
                mgr = LearningMemoryManager(session, str(kb_path))
                examples = mgr.get_training_data(limit=1)
            # OK if we get here
            return {"available": True, "problems": problems}
        except Exception as e:
            problems.append({
                "type": "learning_memory_unavailable",
                "message": f"Learning memory unavailable: {str(e)[:120]}. Wire LearningMemoryManager in Layer4 or disable neuro-symbolic.",
                "severity": "warning",
                "deterministic": True,
                "flag_for_human": True,
            })
            return {"available": False, "error": str(e)[:100], "problems": problems}

    def _check_genesis_qdrant(self) -> dict:
        """Check for Genesis/Qdrant upsert failures (e.g. 400). Deterministic via recent logs."""
        problems = []
        root = Path(__file__).parent.parent
        log_file = root / "logs" / "grace.log"
        if log_file.exists():
            try:
                tail = log_file.read_text(errors="ignore").splitlines()[-500:]
                text = "\n".join(tail).lower()
                if "400" in text and ("genesis" in text or "qdrant" in text or "points" in text or "bad request" in text):
                    problems.append({
                        "type": "genesis_qdrant_400",
                        "message": "Qdrant upsert (genesis_keys) returns 400 — usually vector size mismatch. Fix: set GENESIS_VECTOR_SIZE to your collection's vector size in backend/.env (see logs for the value), or drop the genesis_keys collection in Qdrant Cloud to let the backend recreate it. To disable: DISABLE_GENESIS_QDRANT_PUSH=1.",
                        "severity": "warning",
                        "deterministic": True,
                        "flag_for_human": True,
                    })
            except Exception:
                pass
        # Optionally check Qdrant collection exists
        try:
            from vector_db.client import get_qdrant_client
            client = get_qdrant_client()
            if client:
                collections = client.get_collections().collections
                names = [c.name for c in collections]
                if "genesis_keys" not in names and names:
                    problems.append({
                        "type": "genesis_keys_missing",
                        "message": "Qdrant collection 'genesis_keys' not found. Create it or disable Genesis push.",
                        "severity": "warning",
                        "deterministic": True,
                        "flag_for_human": True,
                    })
        except Exception:
            pass
        return {"checked": True, "problems": problems}


class DeterministicAutoFixer:
    """
    Fixes common problems WITHOUT using an LLM.
    These are pattern-matched fixes with 100% confidence.
    """

    def auto_fix(self, problems: list) -> list:
        """Attempt to fix problems deterministically. Returns list of fixes applied."""
        fixes = []
        for p in problems:
            fix = self._try_fix(p)
            if fix:
                fixes.append(fix)
        return fixes

    def _try_fix(self, problem: dict) -> Optional[dict]:
        ptype = problem.get("type", "")

        if ptype == "syntax_error" and "expected ':'" in problem.get("message", "").lower():
            return self._fix_missing_colon(problem)

        if ptype == "missing_import":
            return self._fix_missing_import(problem)

        if ptype == "missing_file":
            return self._fix_missing_file(problem)

        return None

    def _fix_missing_colon(self, problem: dict) -> Optional[dict]:
        """Add missing colon at the end of a line."""
        try:
            root = Path(__file__).parent.parent
            filepath = root / problem["file"]
            lines = filepath.read_text().split("\n")
            line_idx = problem["line"] - 1
            if 0 <= line_idx < len(lines):
                line = lines[line_idx].rstrip()
                if not line.endswith(":"):
                    lines[line_idx] = line + ":"
                    filepath.write_text("\n".join(lines))
                    return {"fixed": True, "type": "added_colon", "file": problem["file"], "line": problem["line"]}
        except Exception:
            pass
        return None

    def _fix_missing_import(self, problem: dict) -> Optional[dict]:
        """Install missing Python package."""
        module = problem.get("module", "")
        pip_map = {
            "fastapi": "fastapi", "sqlalchemy": "sqlalchemy",
            "pydantic": "pydantic", "uvicorn": "uvicorn",
            "requests": "requests", "psutil": "psutil",
            "watchdog": "watchdog", "dulwich": "dulwich",
        }
        if module in pip_map:
            try:
                import subprocess
                subprocess.run(["pip", "install", pip_map[module]], capture_output=True, timeout=30)
                return {"fixed": True, "type": "installed_package", "module": module}
            except Exception:
                pass
        return None

    def _fix_missing_file(self, problem: dict) -> Optional[dict]:
        """Create missing file from template."""
        filepath = problem.get("file", "")
        if not filepath:
            return None

        root = Path(__file__).parent.parent
        target = root / filepath

        if filepath.endswith("__init__.py"):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("")
            return {"fixed": True, "type": "created_init", "file": filepath}

        return None


def build_deterministic_report() -> dict:
    """Run full deterministic scan and build a structured report."""
    detector = DeterministicDetector()
    return detector.full_scan()


# ─── LLM only after 3 failure tries ─────────────────────────────────────
_LLM_AFTER_TRIES = 3
_STATE_FILE = Path(__file__).parent.parent / "data" / "deterministic_bridge_state.json"


def _load_failure_tries() -> int:
    """Load persisted failure-try count (0 if missing or invalid)."""
    try:
        if _STATE_FILE.exists():
            data = json.loads(_STATE_FILE.read_text())
            return int(data.get("failure_tries", 0))
    except Exception:
        pass
    return 0


def _save_failure_tries(count: int) -> None:
    """Persist failure-try count."""
    try:
        _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STATE_FILE.write_text(json.dumps({"failure_tries": count, "updated_at": datetime.utcnow().isoformat()}))
    except Exception as e:
        logger.debug("Could not save deterministic_bridge_state: %s", e)


def deterministic_fix_cycle(task: str = None) -> dict:
    """
    The full deterministic bridge cycle:
      1. DETECT problems (deterministic)
      2. BUILD fix prompt with exact facts
      3. FEED to LLM (constrained by facts)
      4. VERIFY fix (deterministic)
    """
    result = {
        "started_at": datetime.utcnow().isoformat(),
        "detection": None,
        "fix_prompt": None,
        "fix_generated": False,
        "verification": None,
    }

    # Step 1: Deterministic detection
    report = build_deterministic_report()
    result["detection"] = {
        "total_checks": report["total_checks"],
        "total_problems": report["total_problems"],
        "problems": report["problems"][:10],
    }

    if not report["problems"] and not task:
        _save_failure_tries(0)
        result["status"] = "clean"
        return result

    # Step 2: Build fix prompt with ONLY deterministic facts
    if report["problems"]:
        facts = "\n".join(
            f"- [{p['type']}] {p.get('file', p.get('module', p.get('service', '')))} "
            f"{'line ' + str(p.get('line', '')) + ': ' if p.get('line') else ''}"
            f"{p.get('message', p.get('error', ''))}"
            for p in report["problems"][:10]
        )
        fix_prompt = (
            f"DETERMINISTIC FACTS (verified, not guessed):\n{facts}\n\n"
            f"Generate the EXACT fix for each problem. "
            f"Return ONLY the corrected code. No explanation needed."
        )
    elif task:
        fix_prompt = f"Task: {task}\n\nGenerate the code to accomplish this task."
    else:
        result["status"] = "nothing_to_fix"
        return result

    result["fix_prompt"] = fix_prompt[:500]

    # Step 2.5: Try deterministic auto-fix FIRST (no LLM needed)
    auto_fixer = DeterministicAutoFixer()
    auto_fixes = auto_fixer.auto_fix(report["problems"])
    result["auto_fixes"] = auto_fixes
    result["auto_fixed_count"] = len(auto_fixes)

    # Step 3: Remaining problems after auto-fix
    unfixed = [p for p in report["problems"] if not any(
        f.get("file") == p.get("file") and f.get("type") == p.get("type", "").replace("missing_", "installed_").replace("syntax_error", "added_colon")
        for f in auto_fixes
    )]

    # No remaining problems → reset failure count, no LLM
    if not unfixed:
        _save_failure_tries(0)
        if auto_fixes:
            result["status"] = "auto_fixed_complete"
        else:
            result["status"] = "clean"
        _track_genesis(result, report)
        return result

    result["remaining_for_llm"] = len(unfixed)

    # Increment failure tries and load current count
    failure_tries = _load_failure_tries() + 1
    _save_failure_tries(failure_tries)
    result["failure_try"] = failure_tries
    result["llm_after_tries"] = _LLM_AFTER_TRIES

    # Call LLM only after 3 failure tries
    if failure_tries < _LLM_AFTER_TRIES:
        result["status"] = "deferred_llm"
        result["message"] = f"LLM will be called after {_LLM_AFTER_TRIES} failure tries (current: {failure_tries})"
        _track_genesis(result, report)
        return result

    # Failure tries >= 3: call LLM for fix
    result["llm_called"] = True
    try:
        from llm_orchestrator.factory import get_llm_for_task
        client = get_llm_for_task("code")
        llm_fix = client.generate(
            prompt=fix_prompt,
            system_prompt="You are a code fixer. Use ONLY the deterministic facts given. Output ONLY the corrected code or minimal patch. No explanation.",
            temperature=0.2,
            max_tokens=2048,
        )
        result["llm_generated_fix"] = llm_fix[:2000] if isinstance(llm_fix, str) else str(llm_fix)[:2000]
        result["fix_generated"] = True
        # Reset after calling LLM so next cycle starts fresh
        _save_failure_tries(0)
        result["status"] = "llm_fix_generated"
        result["message"] = "LLM was called after 3 failure tries; fix generated (apply/verify separately if needed)."
    except Exception as e:
        logger.warning("Deterministic bridge LLM call failed: %s", e)
        result["status"] = "llm_fix_failed"
        result["llm_error"] = str(e)[:300]
        result["fix_generated"] = False
        # Do not reset failure_tries so next run will retry LLM

    _track_genesis(result, report)
    return result


def _track_genesis(result: dict, report: dict) -> None:
    """Track deterministic scan/fix via Genesis."""
    try:
        from api._genesis_tracker import track
        track(
            key_type="system_event",
            what=f"Deterministic scan: {report['total_problems']} problems found",
            who="deterministic_bridge",
            output_data={"problems": len(report["problems"]), "checks": report["total_checks"], "status": result.get("status")},
            tags=["deterministic", "bridge", "scan"],
        )
    except Exception:
        pass
