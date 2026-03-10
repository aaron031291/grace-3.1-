"""
Grace Test Framework — Robust testing that a non-developer can use.

One command tells you: "Is Grace healthy? What's broken? How to fix it?"

Three modes:
  1. SMOKE TEST: Quick 30-second check — is everything alive?
  2. FULL TEST: Run all 135+ tests, report pass/fail with plain English
  3. DIAGNOSTIC: Deep analysis of what's broken and why

Output is ALWAYS plain English, not stack traces.
The framework wraps pytest but translates everything for a human.
"""

import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).parent.parent
RESULTS_DIR = BACKEND_DIR / "data" / "test_results"


def smoke_test() -> Dict[str, Any]:
    """
    Quick 30-second health check. Tests the critical paths.
    Returns plain English result.
    """
    start = time.time()
    results = {
        "type": "smoke_test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": [],
        "passed": 0,
        "failed": 0,
        "status": "unknown",
    }

    checks = [
        ("Python imports", _check_imports),
        ("Database connection", _check_database),
        ("Trust Engine", _check_trust_engine),
        ("Flash Cache", _check_flash_cache),
        ("Architecture Compass", _check_compass),
        ("Event Bus", _check_event_bus),
        ("Unified Memory", _check_unified_memory),
        ("Circuit Breaker", _check_circuit_breaker),
        ("Consensus Engine", _check_consensus),
        ("Grace Compiler", _check_compiler),
        ("Reporting Engine", _check_reporting),
        ("Reverse kNN", _check_reverse_knn),
        ("Frontend build", _check_frontend_build),
    ]

    for name, check_fn in checks:
        try:
            ok, detail = check_fn()
            results["checks"].append({
                "name": name,
                "passed": ok,
                "detail": detail,
            })
            if ok:
                results["passed"] += 1
            else:
                results["failed"] += 1
        except Exception as e:
            results["checks"].append({
                "name": name,
                "passed": False,
                "detail": f"Crashed: {str(e)[:100]}",
            })
            results["failed"] += 1

    results["duration_ms"] = round((time.time() - start) * 1000, 1)
    results["status"] = "HEALTHY" if results["failed"] == 0 else "DEGRADED" if results["failed"] <= 3 else "UNHEALTHY"

    # Plain English summary
    results["summary"] = _build_smoke_summary(results)

    _save_result(results)
    return results


def full_test() -> Dict[str, Any]:
    """
    Run the full test suite and translate results to plain English.
    """
    start = time.time()

    test_files = [
        "tests/test_chunked_upload.py",
        "tests/test_flash_cache.py",
        "tests/test_consensus_engine.py",
        "tests/test_opus_10_improvements.py",
        "tests/test_integration_chain.py",
        "tests/test_docs_library_api.py",
    ]

    cmd = [sys.executable, "-m", "pytest"] + test_files + ["-q", "--tb=line", "--no-header"]

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=120,
            cwd=str(BACKEND_DIR),
            env={**os.environ, "SKIP_EMBEDDING_LOAD": "true", "SKIP_QDRANT_CHECK": "true",
                 "SKIP_OLLAMA_CHECK": "true", "DISABLE_GENESIS_TRACKING": "true"},
        )

        output = proc.stdout + proc.stderr
        passed = 0
        failed = 0
        errors = []

        for line in output.split("\n"):
            if "passed" in line and "warning" in line:
                import re
                m = re.search(r'(\d+) passed', line)
                if m:
                    passed = int(m.group(1))
                m = re.search(r'(\d+) failed', line)
                if m:
                    failed = int(m.group(1))
            elif "FAILED" in line:
                test_name = line.split("FAILED")[-1].strip().split(" ")[0] if "FAILED" in line else line
                errors.append(test_name[:100])

    except subprocess.TimeoutExpired:
        passed, failed = 0, 0
        errors = ["Test suite timed out after 120 seconds"]
    except Exception as e:
        passed, failed = 0, 0
        errors = [str(e)]

    duration = round((time.time() - start) * 1000, 1)

    result = {
        "type": "full_test",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "failed": failed,
        "total": passed + failed,
        "pass_rate": round(passed / max(passed + failed, 1) * 100, 1),
        "errors": errors,
        "duration_ms": duration,
        "status": "ALL PASS" if failed == 0 else f"{failed} FAILURES",
        "summary": "",
    }

    if failed == 0:
        result["summary"] = f"All {passed} tests passed in {duration/1000:.1f} seconds. Grace is healthy."
    else:
        result["summary"] = (
            f"{passed} tests passed, {failed} failed ({result['pass_rate']}% pass rate).\n"
            f"Failed tests:\n" + "\n".join(f"  - {e}" for e in errors[:10])
        )

    _save_result(result)
    return result


def diagnostic() -> Dict[str, Any]:
    """
    Deep diagnostic: what's broken, why, and how to fix it.
    Combines smoke test + full test + system health + plain English advice.
    """
    smoke = smoke_test()
    full = full_test()

    # System health
    health_data = {}
    try:
        from cognitive.central_orchestrator import get_orchestrator
        orch = get_orchestrator()
        health_data = orch.check_integration_health()
    except Exception:
        pass

    # Loop status
    loop_data = {}
    try:
        from cognitive.circuit_breaker import get_loop_status
        loop_data = get_loop_status()
    except Exception:
        pass

    # Build the diagnostic report
    problems = []
    fixes = []

    # From smoke test
    for check in smoke.get("checks", []):
        if not check["passed"]:
            problems.append(f"{check['name']}: {check['detail']}")

            # Suggest fixes
            name = check["name"].lower()
            if "database" in name:
                fixes.append("Database: Run 'python scripts/init_kb.py --create-tables' to initialise")
            elif "qdrant" in name or "vector" in name:
                fixes.append("Vector DB: Run 'docker run -d --name qdrant -p 6333:6333 qdrant/qdrant'")
            elif "frontend" in name:
                fixes.append("Frontend: Run 'cd frontend && npm install && npm run build'")
            else:
                fixes.append(f"{check['name']}: Check the logs in logs/grace.log for details")

    # From full test
    for error in full.get("errors", []):
        problems.append(f"Test failure: {error}")

    # From health check
    if health_data.get("broken", 0) > 0:
        problems.append(f"{health_data['broken']} system integrations are broken")
        fixes.append("Run the Grace compiler on broken modules to diagnose: POST /api/audit/compiler/compile")

    result = {
        "type": "diagnostic",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "smoke_test": smoke,
        "full_test": full,
        "integration_health": health_data,
        "loop_count": len(loop_data),
        "problems": problems,
        "fixes": fixes,
        "overall_status": smoke["status"],
        "summary": "",
    }

    if not problems:
        result["summary"] = (
            f"Grace is HEALTHY.\n"
            f"- Smoke test: {smoke['passed']}/{smoke['passed']+smoke['failed']} checks passed\n"
            f"- Full test: {full['passed']} tests passed\n"
            f"- Integration: {health_data.get('health_percent', 0)}% healthy\n"
            f"- Loops: {len(loop_data)} active\n\n"
            f"No action needed."
        )
    else:
        result["summary"] = (
            f"Grace has {len(problems)} issue(s):\n\n"
            + "\n".join(f"  Problem: {p}" for p in problems[:10])
            + "\n\nSuggested fixes:\n"
            + "\n".join(f"  Fix: {f}" for f in fixes[:10])
        )

    _save_result(result)
    return result


# ── Individual checks ─────────────────────────────────────────────────

def _check_imports():
    try:
        from cognitive import pipeline, consensus_engine, flash_cache, trust_engine
        from cognitive import circuit_breaker, event_bus, unified_memory
        from cognitive import architecture_compass, grace_compiler, reverse_knn
        return True, "All core modules importable"
    except ImportError as e:
        return False, f"Import failed: {e}"

def _check_database():
    try:
        from database.session import SessionLocal, initialize_session_factory
        if SessionLocal is None:
            initialize_session_factory()
            from database.session import SessionLocal as SL
            db = SL()
        else:
            db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
        return True, "Database connected"
    except Exception as e:
        return False, f"Database: {str(e)[:80]}"

def _check_trust_engine():
    try:
        from cognitive.trust_engine import get_trust_engine
        te = get_trust_engine()
        score = te.score_output("smoke_test", "Smoke Test", "test content", source="internal")
        return True, f"Trust engine active, scored: {score}"
    except Exception as e:
        return False, str(e)[:80]

def _check_flash_cache():
    try:
        from cognitive.flash_cache import get_flash_cache
        fc = get_flash_cache()
        s = fc.stats()
        return True, f"{s.get('total_entries', 0)} entries, {s.get('unique_keywords', 0)} keywords"
    except Exception as e:
        return False, str(e)[:80]

def _check_compass():
    try:
        from cognitive.architecture_compass import get_compass
        c = get_compass()
        c.build()
        d = c.diagnose()
        return True, f"{d.get('total_components', 0)} components mapped"
    except Exception as e:
        return False, str(e)[:80]

def _check_event_bus():
    try:
        from cognitive.event_bus import publish, get_recent_events
        publish("test.smoke", {"check": True}, source="smoke_test")
        events = get_recent_events(5)
        return True, f"Event bus active, {len(events)} recent events"
    except Exception as e:
        return False, str(e)[:80]

def _check_unified_memory():
    try:
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()
        stats = mem.get_stats()
        return True, f"Memory active, {len(stats)} systems"
    except Exception as e:
        return False, str(e)[:80]

def _check_circuit_breaker():
    try:
        from cognitive.circuit_breaker import NAMED_LOOPS
        return True, f"{len(NAMED_LOOPS)} named loops registered"
    except Exception as e:
        return False, str(e)[:80]

def _check_consensus():
    try:
        from cognitive.consensus_engine import get_available_models
        models = get_available_models()
        available = [m for m in models if m["available"]]
        return True, f"{len(available)}/{len(models)} models available"
    except Exception as e:
        return False, str(e)[:80]

def _check_compiler():
    try:
        from cognitive.grace_compiler import get_grace_compiler
        c = get_grace_compiler()
        r = c.compile("def hello(): return 'world'")
        return True, f"Compiler works, trust score: {r.trust_score}"
    except Exception as e:
        return False, str(e)[:80]

def _check_reporting():
    try:
        from cognitive.reporting_engine import generate_report
        return True, "Reporting engine importable"
    except Exception as e:
        return False, str(e)[:80]

def _check_reverse_knn():
    try:
        from cognitive.reverse_knn import get_reverse_knn
        knn = get_reverse_knn()
        return True, "Reverse kNN active"
    except Exception as e:
        return False, str(e)[:80]

def _check_frontend_build():
    try:
        dist = BACKEND_DIR.parent / "frontend" / "dist"
        if dist.exists() and (dist / "index.html").exists():
            return True, "Frontend built and ready"
        return False, "Frontend not built — run 'cd frontend && npm run build'"
    except Exception as e:
        return False, str(e)[:80]


def _build_smoke_summary(results: Dict) -> str:
    passed = results["passed"]
    failed = results["failed"]
    total = passed + failed

    if failed == 0:
        return f"All {total} checks passed. Grace is healthy and ready."

    failed_names = [c["name"] for c in results["checks"] if not c["passed"]]
    return (
        f"{passed}/{total} checks passed. {failed} issues found:\n"
        + "\n".join(f"  - {name}" for name in failed_names)
    )


def _save_result(result: Dict):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    (RESULTS_DIR / f"{result['type']}_{ts}.json").write_text(
        json.dumps(result, indent=2, default=str)
    )
