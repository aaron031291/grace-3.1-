#!/usr/bin/env python3
"""
Grace AI System Verification — tests everything in one run.

Usage:
  python scripts/verify_system.py              # against running server
  python scripts/verify_system.py --offline     # import-only checks
"""

import sys, os, time, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("SKIP_EMBEDDING_LOAD", "true")
os.environ.setdefault("SKIP_QDRANT_CHECK", "true")
os.environ.setdefault("SKIP_OLLAMA_CHECK", "true")
os.environ.setdefault("SKIP_AUTO_INGESTION", "true")
os.environ.setdefault("DISABLE_CONTINUOUS_LEARNING", "true")
os.environ.setdefault("SKIP_LLM_CHECK", "true")

PASS = 0
FAIL = 0
SKIP = 0


def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name} — {detail}")


def skip(name, reason=""):
    global SKIP
    SKIP += 1
    print(f"  ⏭️  {name} — {reason}")


print("=" * 60)
print("  GRACE AI SYSTEM VERIFICATION")
print("=" * 60)

# ── 1. Import Checks ─────────────────────────────────────────
print("\n▶ IMPORTS")
try:
    from app import app
    check("app.py imports", True)
    check(f"Routes registered: {len(app.routes)}", len(app.routes) > 30)
except Exception as e:
    check("app.py imports", False, str(e))

try:
    from api.brain_api_v2 import call_brain, _build_directory
    d = _build_directory()
    check(f"Brain API: {len(d)} domains", len(d) == 8)
    total_actions = sum(len(b["actions"]) for b in d.values())
    check(f"Brain actions: {total_actions}", total_actions >= 80)
except Exception as e:
    check("Brain API import", False, str(e))

try:
    from core.services.chat_service import list_chats
    from core.services.files_service import tree, browse, stats
    from core.services.govern_service import get_persona, genesis_stats
    from core.services.data_service import api_sources, web_sources
    from core.services.tasks_service import time_sense, get_scheduled
    from core.services.code_service import list_projects
    from core.services.system_service import get_runtime_status, hot_reload
    check("All 7 service modules import", True)
except Exception as e:
    check("Service modules import", False, str(e))

try:
    from core.engines.consensus_engine import run_consensus, get_available_models
    check("Consensus engine import", True)
except Exception as e:
    check("Consensus engine import", False, str(e))

try:
    from core.memory.unified_memory import UnifiedMemory, LearningExample, Episode
    check("Unified memory import", True)
except Exception as e:
    check("Unified memory import", False, str(e))

try:
    from core.awareness.self_model import SelfModel, TimeSense
    ctx = TimeSense.get_context()
    check(f"TimeSense: period={ctx.get('period')}", "period" in ctx)
except Exception as e:
    check("TimeSense import", False, str(e))

try:
    from core.resilience import CircuitBreaker, ErrorBoundary, GracefulDegradation
    cb = CircuitBreaker("test", failure_threshold=3)
    check(f"Circuit breaker: state={cb.state}", cb.state == "closed")
    check(f"Degradation level: {GracefulDegradation.get_level()}", True)
except Exception as e:
    check("Resilience patterns import", False, str(e))

try:
    from api._genesis_tracker import track
    check("Genesis tracker import", True)
except Exception as e:
    check("Genesis tracker import", False, str(e))

# ── 2. Brain Domain Checks ───────────────────────────────────
print("\n▶ BRAIN DOMAINS")
try:
    from api.brain_api_v2 import _build_directory
    d = _build_directory()
    for domain, info in d.items():
        check(f"brain/{domain}: {len(info['actions'])} actions", len(info["actions"]) > 0)
except Exception as e:
    check("Brain domain check", False, str(e))

# ── 3. Service Function Checks ───────────────────────────────
print("\n▶ SERVICE FUNCTIONS")

try:
    from core.services.files_service import stats
    s = stats()
    check(f"files_service.stats(): {s.get('total_files', 0)} files", "total_files" in s)
except Exception as e:
    check("files_service.stats()", False, str(e))

try:
    from core.services.govern_service import get_persona
    p = get_persona()
    check(f"govern_service.get_persona()", isinstance(p, dict))
except Exception as e:
    check("govern_service.get_persona()", False, str(e))

try:
    from core.services.data_service import api_sources
    s = api_sources()
    check(f"data_service.api_sources(): {len(s.get('sources', []))} sources", "sources" in s)
except Exception as e:
    check("data_service.api_sources()", False, str(e))

try:
    from core.services.tasks_service import time_sense
    ts = time_sense()
    check(f"tasks_service.time_sense(): period={ts.get('period')}", "period" in ts)
except Exception as e:
    check("tasks_service.time_sense()", False, str(e))

try:
    from core.services.code_service import list_projects
    p = list_projects()
    check(f"code_service.list_projects(): {len(p.get('projects', []))} projects", "projects" in p)
except Exception as e:
    check("code_service.list_projects()", False, str(e))

# ── 4. Cross-Brain Call ──────────────────────────────────────
print("\n▶ CROSS-BRAIN ORCHESTRATION")
try:
    from api.brain_api_v2 import call_brain
    r = call_brain("tasks", "time_sense", {})
    check(f"call_brain('tasks', 'time_sense'): ok={r.get('ok')}", r.get("ok"))
except Exception as e:
    check("Cross-brain call", False, str(e))

try:
    r = call_brain("system", "runtime", {})
    check(f"call_brain('system', 'runtime'): ok={r.get('ok')}", r.get("ok"))
except Exception as e:
    check("Cross-brain system call", False, str(e))

# ── Summary ──────────────────────────────────────────────────
print("\n" + "=" * 60)
total = PASS + FAIL + SKIP
print(f"  RESULTS: {PASS} passed, {FAIL} failed, {SKIP} skipped (total {total})")
if FAIL == 0:
    print("  STATUS: ALL CHECKS PASSED ✅")
else:
    print(f"  STATUS: {FAIL} FAILURES ❌")
print("=" * 60)

sys.exit(0 if FAIL == 0 else 1)
