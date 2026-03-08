"""
Deterministic build verification — in-brain version.

Same manifest and checks as scripts/verify_built.py, runnable from backend.
Used by system.verify_built and by the unified trigger loop (determinism trigger).
"""

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

# Backend dir = parent of core/
BACKEND = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND.parent
FRONTEND = REPO_ROOT / "frontend"


def _check_backend_requirements(_: dict) -> Tuple[bool, str]:
    p = BACKEND / "requirements.txt"
    if not p.is_file():
        return False, "backend/requirements.txt not found"
    return True, f"exists ({p.stat().st_size} bytes)"


def _check_backend_venv(_: dict) -> Tuple[bool, str]:
    venv = BACKEND / "venv"
    if not venv.is_dir():
        return False, "backend/venv not found (run setup_backend.bat)"
    py = venv / "Scripts" / "python.exe" if os.name == "nt" else venv / "bin" / "python"
    if not py.exists():
        return False, "venv Python executable not found"
    return True, "venv present"


def _check_backend_db(_: dict) -> Tuple[bool, str]:
    db = BACKEND / "data" / "grace.db"
    if not db.is_file():
        return False, "backend/data/grace.db not found (run migrations)"
    return True, f"exists ({db.stat().st_size} bytes)"


def _check_backend_app(_: dict) -> Tuple[bool, str]:
    if not (BACKEND / "app.py").is_file():
        return False, "backend/app.py not found"
    return True, "exists"


def _check_backend_dirs(_: dict) -> Tuple[bool, str]:
    for name in ("api", "core", "database"):
        if not (BACKEND / name).is_dir():
            return False, f"backend/{name}/ missing"
    return True, "api, core, database present"


def _check_backend_verify_script(_: dict) -> Tuple[bool, str]:
    venv_py = BACKEND / ("venv/Scripts/python.exe" if os.name == "nt" else "venv/bin/python")
    script = BACKEND / "scripts" / "verify_system.py"
    if not venv_py.exists() or not script.exists():
        return False, "venv or scripts/verify_system.py missing"
    env = os.environ.copy()
    env["SKIP_EMBEDDING_LOAD"] = "true"
    env["SKIP_QDRANT_CHECK"] = "true"
    env["SKIP_OLLAMA_CHECK"] = "true"
    env["SKIP_AUTO_INGESTION"] = "true"
    env["DISABLE_CONTINUOUS_LEARNING"] = "true"
    env["SKIP_LLM_CHECK"] = "true"
    env["PYTHONIOENCODING"] = "utf-8"
    try:
        r = subprocess.run(
            [str(venv_py), str(script)],
            cwd=str(BACKEND),
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=60,
        )
        if r.returncode != 0:
            return False, (r.stderr or r.stdout or "non-zero exit")[:200]
        if "ALL CHECKS PASSED" not in r.stdout and "ALL CHECKS PASSED" not in (r.stdout + r.stderr):
            return False, "verify_system.py did not report ALL CHECKS PASSED"
        return True, "verify_system.py passed"
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:200]


def _check_frontend_package(_: dict) -> Tuple[bool, str]:
    if not (FRONTEND / "package.json").is_file():
        return False, "frontend/package.json not found"
    return True, "exists"


def _check_frontend_node_modules(_: dict) -> Tuple[bool, str]:
    if not (FRONTEND / "node_modules").is_dir():
        return False, "frontend/node_modules not found (run setup_frontend.bat)"
    return True, "present"


def _check_frontend_build(_: dict) -> Tuple[bool, str]:
    dist = FRONTEND / "dist"
    if not dist.is_dir():
        return False, "frontend/dist not found (run: npm run build in frontend)"
    if not (dist / "index.html").is_file():
        return False, "frontend/dist/index.html missing"
    return True, "dist/ present"


# (id, name, required, check_fn)
BUILD_MANIFEST: List[Tuple[str, str, bool, Callable[[dict], Tuple[bool, str]]]] = [
    ("backend_requirements", "Backend requirements.txt", True, _check_backend_requirements),
    ("backend_venv", "Backend venv", True, _check_backend_venv),
    ("backend_db", "Backend database (migrations run)", True, _check_backend_db),
    ("backend_app", "Backend app.py", True, _check_backend_app),
    ("backend_dirs", "Backend api/core/database dirs", True, _check_backend_dirs),
    ("backend_verify_script", "Backend verify_system.py (imports + brain)", True, _check_backend_verify_script),
    ("frontend_package", "Frontend package.json", True, _check_frontend_package),
    ("frontend_node_modules", "Frontend node_modules", True, _check_frontend_node_modules),
    ("frontend_build", "Frontend production build (dist/)", False, _check_frontend_build),
]


def run_verify_built_checks(skip_verify_script: bool = False) -> Dict[str, Any]:
    """
    Run all build verification checks. Returns manifest dict (timestamp_utc, checks, summary).
    Used by system.verify_built brain action and by determinism trigger.
    """
    results: Dict[str, Any] = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "checks": [],
        "summary": {"passed": 0, "failed": 0, "required_failed": 0},
    }
    for check_id, name, required, check_fn in BUILD_MANIFEST:
        if skip_verify_script and check_id == "backend_verify_script":
            results["checks"].append({
                "id": check_id,
                "name": name,
                "required": required,
                "passed": None,
                "detail": "skipped",
            })
            continue
        try:
            passed, detail = check_fn(results)
        except Exception as e:
            passed, detail = False, str(e)[:200]
        results["checks"].append({
            "id": check_id,
            "name": name,
            "required": required,
            "passed": passed,
            "detail": detail,
        })
        if passed:
            results["summary"]["passed"] += 1
        else:
            results["summary"]["failed"] += 1
            if required:
                results["summary"]["required_failed"] += 1
    return results


def all_required_passed(manifest: Dict[str, Any]) -> bool:
    """True if every required check in the manifest passed."""
    return manifest.get("summary", {}).get("required_failed", 1) == 0
