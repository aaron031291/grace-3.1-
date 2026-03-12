#!/usr/bin/env python3
"""
Deterministic verification that everything built for GRACE has been built.

Defines a single manifest of "built" criteria and runs each check in a fixed order.
Writes a verification manifest (JSON) with timestamp and pass/fail per check so you
can re-run anytime to confirm state. Exit code 0 only if all required checks pass.

Usage (from repo root):
  python scripts/verify_built.py
  python scripts/verify_built.py --manifest-only   # only write manifest, no backend Python checks
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Repo root = parent of scripts/
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"
FRONTEND = REPO_ROOT / "frontend"

# ─── BUILD MANIFEST: single source of truth for "everything built" ───
# Each entry: (id, description, required, check_fn)
# check_fn(manifest_dict) -> (passed: bool, detail: str)


def _file_exists(rel_path: Path, is_dir: bool = False) -> bool:
    p = REPO_ROOT / rel_path if not rel_path.is_absolute() else rel_path
    return p.exists() and (p.is_dir() if is_dir else p.is_file())


def check_backend_requirements(_) -> tuple[bool, str]:
    p = BACKEND / "requirements.txt"
    if not p.is_file():
        return False, "backend/requirements.txt not found"
    return True, f"exists ({p.stat().st_size} bytes)"


def check_backend_venv(_) -> tuple[bool, str]:
    venv = BACKEND / "venv"
    if not venv.is_dir():
        return False, "backend/venv not found (run setup_backend.bat)"
    py = venv / "Scripts" / "python.exe" if os.name == "nt" else venv / "bin" / "python"
    if not py.exists():
        return False, "venv Python executable not found"
    return True, "venv present"


def check_backend_db(_) -> tuple[bool, str]:
    db = BACKEND / "data" / "grace.db"
    if not db.is_file():
        return False, "backend/data/grace.db not found (run migrations)"
    return True, f"exists ({db.stat().st_size} bytes)"


def check_backend_app(_) -> tuple[bool, str]:
    app = BACKEND / "app.py"
    if not app.is_file():
        return False, "backend/app.py not found"
    return True, "exists"


def check_backend_dirs(_) -> tuple[bool, str]:
    for name in ("api", "core", "database"):
        d = BACKEND / name
        if not d.is_dir():
            return False, f"backend/{name}/ missing"
    return True, "api, core, database present"


def check_backend_verify_script(_) -> tuple[bool, str]:
    """Run backend's verify_system.py with backend venv (imports + brain + services)."""
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


def check_frontend_package(_) -> tuple[bool, str]:
    p = FRONTEND / "package.json"
    if not p.is_file():
        return False, "frontend/package.json not found"
    return True, "exists"


def check_frontend_node_modules(_) -> tuple[bool, str]:
    nm = FRONTEND / "node_modules"
    if not nm.is_dir():
        return False, "frontend/node_modules not found (run setup_frontend.bat)"
    return True, "present"


def check_frontend_build(_) -> tuple[bool, str]:
    """Optional: frontend production build (vite outputs to dist/)."""
    dist = FRONTEND / "dist"
    if not dist.is_dir():
        return False, "frontend/dist not found (run: npm run build in frontend)"
    index = dist / "index.html"
    if not index.is_file():
        return False, "frontend/dist/index.html missing"
    return True, "dist/ present"


# Required = must pass for "everything built". Optional = inform only.
BUILD_MANIFEST = [
    ("backend_requirements", "Backend requirements.txt", True, check_backend_requirements),
    ("backend_venv", "Backend venv", True, check_backend_venv),
    ("backend_db", "Backend database (migrations run)", True, check_backend_db),
    ("backend_app", "Backend app.py", True, check_backend_app),
    ("backend_dirs", "Backend api/core/database dirs", True, check_backend_dirs),
    ("backend_verify_script", "Backend verify_system.py (imports + brain)", True, check_backend_verify_script),
    ("frontend_package", "Frontend package.json", True, check_frontend_package),
    ("frontend_node_modules", "Frontend node_modules", True, check_frontend_node_modules),
    ("frontend_build", "Frontend production build (dist/)", False, check_frontend_build),
]


def run_checks(manifest_only: bool = False) -> dict:
    """Run all manifest checks; return dict suitable for verification_manifest.json."""
    results = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(REPO_ROOT),
        "checks": [],
        "summary": {"passed": 0, "failed": 0, "required_failed": 0},
    }
    for check_id, name, required, check_fn in BUILD_MANIFEST:
        if manifest_only and check_id == "backend_verify_script":
            results["checks"].append({
                "id": check_id,
                "name": name,
                "required": required,
                "passed": None,
                "detail": "skipped (--manifest-only)",
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


def main() -> int:
    manifest_only = "--manifest-only" in sys.argv
    print("=" * 64)
    print("  GRACE — Deterministic build verification")
    print("=" * 64)
    print(f"  Repo root: {REPO_ROOT}")
    print()

    results = run_checks(manifest_only=manifest_only)

    for c in results["checks"]:
        status = "[OK]" if c["passed"] is True else ("[FAIL]" if c["passed"] is False else "[SKIP]")
        req = " (required)" if c.get("required") else " (optional)"
        print(f"  {status} {c['name']}{req}")
        if c.get("detail"):
            print(f"      {c['detail']}")

    manifest_path = REPO_ROOT / "verification_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(results, f, indent=2)
    print()
    print(f"  Manifest written: {manifest_path}")

    print()
    print("=" * 64)
    s = results["summary"]
    required_ok = s["required_failed"] == 0
    if required_ok:
        print("  STATUS: All required checks passed — everything built is verified.")
    else:
        print(f"  STATUS: {s['required_failed']} required check(s) failed.")
    print("=" * 64)
    return 0 if required_ok else 1


if __name__ == "__main__":
    sys.exit(main())
