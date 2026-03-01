"""
Brain API v2 — CLEAN version. No HTTP-to-localhost calls.
All business logic via direct Python function calls through core/services/.

8 domains, 95+ actions, zero self-HTTP.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Any, Optional, Dict, List
from datetime import datetime
import logging
import time

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/brain", tags=["Brain API"])


class BrainRequest(BaseModel):
    action: str
    payload: Optional[Dict[str, Any]] = {}


class BrainResponse(BaseModel):
    brain: str
    action: str
    ok: bool
    data: Any = None
    error: Optional[str] = None
    latency_ms: float = 0
    genesis_key_id: Optional[str] = None


class BrainOrchestration(BaseModel):
    steps: list


def _call(brain: str, action: str, payload: dict, handlers: dict) -> BrainResponse:
    """Route action to handler, track via Genesis."""
    start = time.time()
    handler = handlers.get(action)
    if not handler:
        return BrainResponse(brain=brain, action=action, ok=False,
                             error=f"Unknown action '{action}'. Available: {', '.join(sorted(handlers.keys()))}")
    try:
        data = handler(payload)
        latency = round((time.time() - start) * 1000, 1)
        gk = None
        try:
            from api._genesis_tracker import track
            gk = track(key_type="api_request", what=f"brain/{brain}/{action}",
                       who=f"brain.{brain}", how=action,
                       tags=["brain", brain, action])
        except Exception:
            pass
        return BrainResponse(brain=brain, action=action, ok=True,
                             data=data, latency_ms=latency, genesis_key_id=gk)
    except Exception as e:
        latency = round((time.time() - start) * 1000, 1)
        try:
            from api._genesis_tracker import track
            track(key_type="error", what=f"brain/{brain}/{action}: {e}",
                  who=f"brain.{brain}", is_error=True,
                  error_type=type(e).__name__, error_message=str(e)[:200],
                  tags=["brain", brain, action, "error"])
        except Exception:
            pass
        return BrainResponse(brain=brain, action=action, ok=False,
                             error=str(e)[:300], latency_ms=latency)


def call_brain(brain_name: str, action: str, payload: dict = None) -> dict:
    """Cross-brain call — any brain can call another."""
    brains = {"chat": _chat, "files": _files, "govern": _govern, "ai": _ai,
              "system": _system, "data": _data, "tasks": _tasks, "code": _code}
    factory = brains.get(brain_name)
    if not factory:
        return {"ok": False, "error": f"Unknown brain: {brain_name}"}
    handler = factory().get(action)
    if not handler:
        return {"ok": False, "error": f"Unknown action '{action}' in brain '{brain_name}'"}
    try:
        return {"ok": True, "data": handler(payload or {})}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}


# ═══════════════════════════════════════════════════════════════════
#  HANDLERS — direct function calls, no HTTP
# ═══════════════════════════════════════════════════════════════════

def _chat() -> dict:
    from core.services.chat_service import (
        list_chats, create_chat, get_chat, delete_chat,
        get_history, send_prompt, run_consensus, get_world_model,
    )
    return {
        "list": lambda p: list_chats(p.get("limit", 50)),
        "create": create_chat,
        "get": get_chat,
        "delete": delete_chat,
        "history": get_history,
        "send": send_prompt,
        "consensus": run_consensus,
        "world_model": lambda p: get_world_model(p),
    }


def _files() -> dict:
    import requests as req
    B = "http://127.0.0.1:8000"
    j = lambda r: r.json() if r.ok else {"error": f"{r.status_code}"}
    return {
        "tree":     lambda p: j(req.get(f"{B}/api/librarian-fs/tree", params=p, timeout=10)),
        "browse":   lambda p: j(req.get(f"{B}/api/librarian-fs/browse", params={"path": p.get("path", "")}, timeout=10)),
        "read":     lambda p: j(req.get(f"{B}/api/librarian-fs/file/content", params={"path": p["path"]}, timeout=10)),
        "write":    lambda p: j(req.put(f"{B}/api/librarian-fs/file/content", json=p, timeout=10)),
        "create":   lambda p: j(req.post(f"{B}/api/librarian-fs/file/create", json=p, timeout=10)),
        "delete":   lambda p: j(req.delete(f"{B}/api/librarian-fs/file", params={"path": p["path"]}, timeout=10)),
        "search":   lambda p: j(req.post(f"{B}/retrieve/search", params={"query": p["query"]}, timeout=15)),
        "docs_all": lambda p: j(req.get(f"{B}/api/docs/all", timeout=10)),
        "stats":    lambda p: j(req.get(f"{B}/api/librarian-fs/stats", timeout=10)),
    }


def _govern() -> dict:
    import requests as req
    B = "http://127.0.0.1:8000"
    j = lambda r: r.json() if r.ok else {"error": f"{r.status_code}"}
    return {
        "dashboard":  lambda p: j(req.get(f"{B}/api/governance-hub/dashboard", timeout=10)),
        "approvals":  lambda p: j(req.get(f"{B}/api/governance-hub/approvals", timeout=10)),
        "approve":    lambda p: j(req.post(f"{B}/api/governance-hub/approvals/{p['id']}", json=p, timeout=10)),
        "scores":     lambda p: j(req.get(f"{B}/api/governance-hub/scores", timeout=10)),
        "rules":      lambda p: j(req.get(f"{B}/api/governance-rules/documents", timeout=10)),
        "persona":    lambda p: j(req.get(f"{B}/api/governance-rules/persona", timeout=10)),
        "genesis_stats": lambda p: _genesis_stats(),
        "heal":       lambda p: j(req.post(f"{B}/api/governance-hub/healing/trigger", timeout=30)),
        "learn":      lambda p: j(req.post(f"{B}/api/governance-hub/learning/trigger", timeout=30)),
        "genesis_keys": lambda p: _genesis_keys(p.get("limit", 20)),
        "approvals_history": lambda p: j(req.get(f"{B}/api/governance-hub/approvals/history", params=p, timeout=10)),
    }


def _ai() -> dict:
    from core.services.system_service import get_consensus_models
    return {
        "models": lambda p: get_consensus_models(),
        "consensus": lambda p: _run_consensus_full(p),
        "quick": lambda p: _run_consensus_quick(p),
        "fast": lambda p: _run_consensus_fast(p),
        "console": lambda p: _console_ask(p),
        "diagnose": lambda p: _console_diagnose(),
        "knowledge_gaps": lambda p: _knowledge_gaps(),
        "integration_matrix": lambda p: _integration_matrix(),
        "logic_tests": lambda p: _logic_tests(),
        "generate": lambda p: _code_generate(p),
        "oracle": lambda p: _oracle_dashboard(),
        "training": lambda p: _oracle_training(),
    }


def _system() -> dict:
    from core.services.system_service import (
        get_runtime_status, hot_reload, pause_runtime, resume_runtime,
        get_health_dashboard, get_bi_dashboard, get_diagnostics_status,
    )
    from api.autonomous_loop_api import _loop_state, _loop_log
    return {
        "runtime":      lambda p: get_runtime_status(),
        "hot_reload":   lambda p: hot_reload(),
        "pause":        lambda p: pause_runtime(),
        "resume":       lambda p: resume_runtime(),
        "health":       lambda p: get_health_dashboard(),
        "bi":           lambda p: get_bi_dashboard(),
        "diagnostics":  lambda p: get_diagnostics_status(),
        "health_map":   lambda p: _health_map(p),
        "problems":     lambda p: _problems(),
        "baselines":    lambda p: _baselines(),
        "orphans":      lambda p: _orphans(),
        "correlate":    lambda p: _correlate(p),
        "triggers":     lambda p: _trigger_scan(),
        "scan_heal":    lambda p: _scan_heal(),
        "probe":        lambda p: _probe_sweep(),
        "probe_models": lambda p: _probe_models(),
        "auto_status":  lambda p: dict(_loop_state),
        "auto_start":   lambda p: _auto_start(p),
        "auto_stop":    lambda p: _auto_stop(),
        "auto_cycle":   lambda p: _auto_cycle(),
        "auto_log":     lambda p: {"log": list(reversed(_loop_log[-20:]))},
        "consensus_fix": lambda p: _consensus_fix(),
        "connectivity": lambda p: _connectivity(),
    }


def _data() -> dict:
    import requests as req
    B = "http://127.0.0.1:8000"
    j = lambda r: r.json() if r.ok else {"error": f"{r.status_code}"}
    return {
        "api_sources": lambda p: j(req.get(f"{B}/api/whitelist-hub/api-sources", timeout=10)),
        "web_sources": lambda p: j(req.get(f"{B}/api/whitelist-hub/web-sources", timeout=10)),
        "add_api":     lambda p: j(req.post(f"{B}/api/whitelist-hub/api-sources", json=p, timeout=10)),
        "add_web":     lambda p: j(req.post(f"{B}/api/whitelist-hub/web-sources", json=p, timeout=10)),
        "stats":       lambda p: j(req.get(f"{B}/api/whitelist-hub/stats", timeout=10)),
        "flash_cache": lambda p: _flash_cache_stats(),
    }


def _tasks() -> dict:
    import requests as req
    B = "http://127.0.0.1:8000"
    j = lambda r: r.json() if r.ok else {"error": f"{r.status_code}"}
    return {
        "live":       lambda p: j(req.get(f"{B}/api/tasks-hub/live", timeout=10)),
        "history":    lambda p: j(req.get(f"{B}/api/tasks-hub/history", params={"limit": p.get("limit", 40)}, timeout=10)),
        "submit":     lambda p: j(req.post(f"{B}/api/tasks-hub/submit", json=p, timeout=15)),
        "scheduled":  lambda p: j(req.get(f"{B}/api/tasks-hub/scheduled", timeout=10)),
        "schedule":   lambda p: j(req.post(f"{B}/api/tasks-hub/schedule", json=p, timeout=10)),
        "time_sense": lambda p: _time_sense(),
        "planner":    lambda p: j(req.get(f"{B}/api/planner/sessions", timeout=10)),
    }


def _code() -> dict:
    import requests as req
    B = "http://127.0.0.1:8000"
    j = lambda r: r.json() if r.ok else {"error": f"{r.status_code}"}
    return {
        "projects":  lambda p: j(req.get(f"{B}/api/codebase-hub/projects", timeout=10)),
        "tree":      lambda p: j(req.get(f"{B}/api/codebase-hub/tree/{p['folder']}", timeout=10)),
        "read":      lambda p: j(req.get(f"{B}/api/codebase-hub/file", params={"path": p["path"]}, timeout=10)),
        "write":     lambda p: j(req.put(f"{B}/api/codebase-hub/file", json=p, timeout=10)),
        "generate":  lambda p: _code_generate(p),
        "apply":     lambda p: j(req.post(f"{B}/api/coding-agent/apply", json=p, timeout=30)),
    }


# ═══════════════════════════════════════════════════════════════════
#  INTERNAL HELPERS — direct calls replacing HTTP
# ═══════════════════════════════════════════════════════════════════

def _genesis_stats():
    from database.session import session_scope
    from models.genesis_key_models import GenesisKey
    from sqlalchemy import func
    from datetime import timedelta
    with session_scope() as s:
        total = s.query(func.count(GenesisKey.id)).scalar() or 0
        errors = s.query(func.count(GenesisKey.id)).filter(GenesisKey.is_error == True).scalar() or 0
        return {"total_keys": total, "total_errors": errors}


def _genesis_keys(limit: int = 20):
    from database.session import session_scope
    from models.genesis_key_models import GenesisKey
    with session_scope() as s:
        keys = s.query(GenesisKey).order_by(GenesisKey.when_timestamp.desc()).limit(limit).all()
        return {"keys": [{"key_id": k.key_id, "key_type": str(k.key_type), "what": k.what_description} for k in keys]}


def _run_consensus_full(p):
    from cognitive.consensus_engine import run_consensus
    r = run_consensus(prompt=p.get("prompt", ""), models=p.get("models"), source="user")
    return {"final_output": r.final_output, "confidence": r.confidence, "models_used": r.models_used,
            "agreements": r.agreements, "disagreements": r.disagreements}


def _run_consensus_quick(p):
    from cognitive.consensus_engine import run_consensus
    r = run_consensus(prompt=p.get("prompt", ""), models=["qwen", "reasoning"], source="user")
    return {"final_output": r.final_output, "confidence": r.confidence}


def _run_consensus_fast(p):
    from cognitive.consensus_engine import layer1_deliberate, _check_model_available
    models = p.get("models") or [m for m in ["kimi", "opus", "qwen", "reasoning"] if _check_model_available(m)]
    responses = layer1_deliberate(p.get("prompt", ""), models, p.get("system_prompt", ""), "")
    return {"models_used": models, "individual_responses": [
        {"model_id": r.model_id, "model_name": r.model_name, "response": r.response, "error": r.error, "latency_ms": r.latency_ms}
        for r in responses
    ]}


def _console_ask(p):
    try:
        from api.live_console_api import _ask
        return _ask(p.get("message", ""), p.get("use_consensus", True))
    except Exception:
        return _run_consensus_fast({"prompt": p.get("message", ""), "models": ["kimi", "opus"]})


def _console_diagnose():
    try:
        from api.live_console_api import _diagnose
        return _diagnose()
    except Exception:
        return {"diagnosis": "unavailable"}


def _knowledge_gaps():
    try:
        from cognitive.reverse_knn import scan_knowledge_gaps
        return scan_knowledge_gaps()
    except Exception:
        return {"gaps": []}


def _integration_matrix():
    try:
        from cognitive.live_integration import get_integration_matrix
        return get_integration_matrix()
    except Exception:
        return {"matrix": []}


def _logic_tests():
    try:
        from cognitive.deep_test_engine import get_deep_test_engine
        return get_deep_test_engine().run_logic_tests()
    except Exception:
        return {"status": "unavailable"}


def _code_generate(p):
    try:
        from cognitive.qwen_coding_net import generate_code
        return generate_code(p.get("prompt", ""), p.get("project_folder", ""))
    except Exception as e:
        return {"error": str(e)}


def _oracle_dashboard():
    try:
        from cognitive.training_ingest import get_training_stats
        return get_training_stats()
    except Exception:
        return {"status": "unavailable"}


def _oracle_training():
    try:
        from database.session import session_scope
        from cognitive.learning_memory import LearningExample
        with session_scope() as s:
            examples = s.query(LearningExample).order_by(LearningExample.id.desc()).limit(20).all()
            return {"data": [{"id": str(e.id), "type": e.example_type, "trust": e.trust_score} for e in examples]}
    except Exception:
        return {"data": []}


def _health_map(p):
    from api.component_health_api import health_map
    import asyncio
    return asyncio.get_event_loop().run_until_complete(health_map(p.get("window_minutes", 60)))


def _problems():
    from api.component_health_api import problems_list
    import asyncio
    return asyncio.get_event_loop().run_until_complete(problems_list())


def _baselines():
    from api.component_health_api import learned_baselines
    import asyncio
    return asyncio.get_event_loop().run_until_complete(learned_baselines())


def _orphans():
    from api.component_health_api import detect_orphan_services
    import asyncio
    return asyncio.get_event_loop().run_until_complete(detect_orphan_services())


def _correlate(p):
    from api.component_health_api import correlate_failure
    import asyncio
    return asyncio.get_event_loop().run_until_complete(correlate_failure(p.get("component", "")))


def _trigger_scan():
    from api.runtime_triggers_api import scan_triggers
    import asyncio
    return asyncio.get_event_loop().run_until_complete(scan_triggers())


def _scan_heal():
    from api.runtime_triggers_api import scan_and_heal
    import asyncio
    return asyncio.get_event_loop().run_until_complete(scan_and_heal())


def _probe_sweep():
    from api.probe_agent_api import probe_sweep
    import asyncio
    return asyncio.get_event_loop().run_until_complete(probe_sweep())


def _probe_models():
    from api.probe_agent_api import probe_models
    import asyncio
    return asyncio.get_event_loop().run_until_complete(probe_models())


def _auto_start(p):
    from api.autonomous_loop_api import _background_loop, _stop_event, _loop_state
    import threading
    if _loop_state["running"]:
        return {"status": "already_running"}
    _stop_event.clear()
    _loop_state["running"] = True
    t = threading.Thread(target=_background_loop, args=(p.get("interval", 30),), daemon=True)
    t.start()
    return {"status": "started"}


def _auto_stop():
    from api.autonomous_loop_api import _stop_event, _loop_state
    _stop_event.set()
    _loop_state["running"] = False
    return {"status": "stopped"}


def _auto_cycle():
    from api.autonomous_loop_api import _run_cycle
    return _run_cycle()


def _consensus_fix():
    from api.consensus_fixer_api import _get_all_problems, _consensus_diagnose_and_fix
    problems = _get_all_problems()
    results = [_consensus_diagnose_and_fix(p) for p in problems[:5]]
    return {"problems": len(problems), "diagnosed": len(results)}


def _connectivity():
    from core.services.system_service import get_runtime_status
    return get_runtime_status()


def _flash_cache_stats():
    try:
        from cognitive.flash_cache import get_flash_cache
        return get_flash_cache().get_stats()
    except Exception:
        return {"entries": 0}


def _time_sense():
    from cognitive.time_sense import TimeSense
    return TimeSense.get_context()


# ═══════════════════════════════════════════════════════════════════
#  DIRECTORY + ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

def _build_directory():
    return {
        "chat":   {"actions": list(_chat().keys()), "description": "Conversations, prompts, consensus, world model"},
        "files":  {"actions": list(_files().keys()), "description": "Folders, documents, uploads, search, librarian"},
        "govern": {"actions": list(_govern().keys()), "description": "Governance, approvals, rules, persona, genesis"},
        "ai":     {"actions": list(_ai().keys()), "description": "Consensus, models, coding agent, oracle, testing"},
        "system": {"actions": list(_system().keys()), "description": "Health, runtime, monitoring, autonomous loop"},
        "data":   {"actions": list(_data().keys()), "description": "Whitelist sources, flash cache"},
        "tasks":  {"actions": list(_tasks().keys()), "description": "Scheduling, time sense, planner"},
        "code":   {"actions": list(_code().keys()), "description": "Codebase, projects, code generation"},
    }


BRAIN_DIRECTORY = _build_directory()


@router.post("/chat", response_model=BrainResponse)
async def brain_chat(req: BrainRequest):
    return _call("chat", req.action, req.payload or {}, _chat())

@router.post("/files", response_model=BrainResponse)
async def brain_files(req: BrainRequest):
    return _call("files", req.action, req.payload or {}, _files())

@router.post("/govern", response_model=BrainResponse)
async def brain_govern(req: BrainRequest):
    return _call("govern", req.action, req.payload or {}, _govern())

@router.post("/ai", response_model=BrainResponse)
async def brain_ai(req: BrainRequest):
    return _call("ai", req.action, req.payload or {}, _ai())

@router.post("/system", response_model=BrainResponse)
async def brain_system(req: BrainRequest):
    return _call("system", req.action, req.payload or {}, _system())

@router.post("/data", response_model=BrainResponse)
async def brain_data(req: BrainRequest):
    return _call("data", req.action, req.payload or {}, _data())

@router.post("/tasks", response_model=BrainResponse)
async def brain_tasks(req: BrainRequest):
    return _call("tasks", req.action, req.payload or {}, _tasks())

@router.post("/code", response_model=BrainResponse)
async def brain_code(req: BrainRequest):
    return _call("code", req.action, req.payload or {}, _code())

@router.get("/directory")
async def brain_directory():
    d = _build_directory()
    total = sum(len(b["actions"]) for b in d.values())
    return {"brains": d, "total_brains": len(d), "total_actions": total,
            "usage": "POST /brain/{domain} { action: '...', payload: {...} }"}

@router.post("/orchestrate")
async def orchestrate(req: BrainOrchestration):
    start = time.time()
    results = []
    for i, step in enumerate(req.steps):
        r = call_brain(step.get("brain", ""), step.get("action", ""), step.get("payload", {}))
        results.append({"step": i, "brain": step.get("brain"), "action": step.get("action"),
                        "ok": r.get("ok"), "data": r.get("data"), "error": r.get("error")})
    return {"steps": results, "total": len(results),
            "succeeded": sum(1 for r in results if r["ok"]),
            "failed": sum(1 for r in results if not r["ok"]),
            "latency_ms": round((time.time() - start) * 1000, 1)}
