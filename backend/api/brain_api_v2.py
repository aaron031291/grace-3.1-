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


def _call(brain: str, action: str, payload: dict, handlers: dict,
          client_ip: str = "unknown") -> BrainResponse:
    """Route action to handler with tracing, rate limiting, validation, Genesis tracking."""

    # Start trace
    try:
        from core.tracing import new_trace, add_span, light_track
        trace_id = new_trace()
        add_span(f"brain/{brain}/{action}", {"client_ip": client_ip})
        light_track("api_request", f"brain/{brain}/{action}", f"brain.{brain}", ["brain", brain, action])
    except Exception:
        trace_id = None

    # Rate limit check
    try:
        from core.security import check_rate_limit
        if not check_rate_limit(brain, client_ip):
            return BrainResponse(brain=brain, action=action, ok=False,
                                 error="Rate limit exceeded — try again in 60s")
    except Exception:
        pass

    # Input sanitization
    try:
        from core.security import check_sql_injection, sanitize_string
        for key, val in (payload or {}).items():
            if isinstance(val, str):
                if check_sql_injection(val):
                    return BrainResponse(brain=brain, action=action, ok=False,
                                         error=f"Invalid input in field '{key}'")
                payload[key] = sanitize_string(val)
    except Exception:
        pass

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


_calling_brain = "external"


def call_brain(brain_name: str, action: str, payload: dict = None) -> dict:
    """Cross-brain call with Hebbian learning — synapses strengthen on success."""
    global _calling_brain
    source = _calling_brain
    brains = {"chat": _chat, "files": _files, "govern": _govern, "ai": _ai,
              "system": _system, "data": _data, "tasks": _tasks, "code": _code}
    factory = brains.get(brain_name)
    if not factory:
        return {"ok": False, "error": f"Unknown brain: {brain_name}"}
    handler = factory().get(action)
    if not handler:
        return {"ok": False, "error": f"Unknown action '{action}' in brain '{brain_name}'"}
    try:
        old_caller = _calling_brain
        _calling_brain = brain_name
        data = handler(payload or {})
        _calling_brain = old_caller

        try:
            from core.hebbian import get_hebbian_mesh
            get_hebbian_mesh().record(source, brain_name, success=True)
        except Exception:
            pass

        return {"ok": True, "data": data}
    except Exception as e:
        try:
            from core.hebbian import get_hebbian_mesh
            get_hebbian_mesh().record(source, brain_name, success=False)
        except Exception:
            pass
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
    from core.services.files_service import tree, browse, read, write, create, delete, search, stats, docs_all
    return {
        "tree":     lambda p: tree(p.get("path"), p.get("max_depth", 3)),
        "browse":   lambda p: browse(p.get("path", "")),
        "read":     lambda p: read(p["path"]),
        "write":    lambda p: write(p["path"], p["content"]),
        "create":   lambda p: create(p.get("path", ""), p.get("content", ""), p.get("directory")),
        "delete":   lambda p: delete(p["path"]),
        "search":   lambda p: search(p["query"], p.get("limit", 10)),
        "docs_all": lambda p: docs_all(),
        "stats":    lambda p: stats(),
    }


def _govern() -> dict:
    from core.services.govern_service import (
        dashboard, get_approvals, approve_action, get_scores,
        list_rules, get_persona, update_persona, genesis_stats,
        trigger_healing, trigger_learning, genesis_keys, approvals_history,
    )
    return {
        "dashboard":  lambda p: dashboard(),
        "approvals":  lambda p: get_approvals(),
        "approve":    lambda p: approve_action(p["id"], p.get("action", "approved"), p.get("reason", "")),
        "scores":     lambda p: get_scores(),
        "rules":      lambda p: list_rules(),
        "persona":    lambda p: get_persona(),
        "update_persona": lambda p: update_persona(p.get("personal"), p.get("professional")),
        "genesis_stats": lambda p: genesis_stats(),
        "heal":       lambda p: trigger_healing(),
        "learn":      lambda p: trigger_learning(),
        "genesis_keys": lambda p: genesis_keys(p.get("limit", 20)),
        "approvals_history": lambda p: approvals_history(p.get("limit", 30)),
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
        "dl_predict": lambda p: _dl_predict(p),
        "dl_train": lambda p: _dl_train(p),
        "pipeline": lambda p: _run_pipeline(p),
        "pipeline_progress": lambda p: _run_pipeline({"progress": True, "run_id": p.get("run_id")}),
        "pipeline_bg": lambda p: _run_pipeline({"background": True, "task": p.get("task", p.get("prompt", ""))}),
        "ooda": lambda p: _ooda(p),
        "ambiguity": lambda p: _ambiguity(p),
        "invariants": lambda p: _invariants(),
        "cognitive_report": lambda p: _cognitive_report(p),
        "bandit_select": lambda p: _bandit_select(p),
        "knowledge_gaps_deep": lambda p: _knowledge_gaps_deep(),
        "deterministic_scan": lambda p: _deterministic_scan(),
        "deterministic_fix": lambda p: _deterministic_fix(p),
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
        "synapses":    lambda p: _synapses(),
        "synapse_map": lambda p: _synapse_brain(p),
        "traces":      lambda p: _recent_traces(),
        "trace_stats": lambda p: _trace_stats(),
        "hot_reload_service": lambda p: _hot_reload_svc(p),
        "hot_reload_all": lambda p: _hot_reload_all(),
        "save_and_reload": lambda p: _save_reload(p),
        "reload_history": lambda p: _reload_history(),
        "genesis_storage": lambda p: _genesis_storage_stats(),
        "genesis_cleanup": lambda p: _genesis_cleanup(),
        "genesis_hot": lambda p: _genesis_hot(p),
        "file_events": lambda p: _file_events(p),
        "scan_upload": lambda p: _scan_upload(p),
        "process_documents": lambda p: _process_docs(p),
        "processing_status": lambda p: _processing_status(),
        "workspace_context": lambda p: _workspace_ctx(p),
        "undo": lambda p: _undo(p),
        "redo": lambda p: _redo(p),
        "profile": lambda p: _profile(p),
        "update_profile": lambda p: _update_profile(p),
        "notifications": lambda p: _notifications(p),
        "notify": lambda p: _notify(p),
        "permissions": lambda p: _permissions(p),
        "set_permission": lambda p: _set_perm(p),
        "shortcuts": lambda p: _shortcuts(),
        "fuzzy_search": lambda p: _fuzzy(p),
        "generate_report": lambda p: _generate_report(p),
        "list_reports": lambda p: _list_reports(),
        "get_report": lambda p: _get_report(p),
        "intelligence": lambda p: _intelligence_report(p),
        "trust":        lambda p: _trust_state(),
        "mine_keys":    lambda p: _mine_genesis_keys(p),
        "mine_episodes": lambda p: _mine_episodes(),
    }


def _data() -> dict:
    from core.services.data_service import api_sources, web_sources, add_api, add_web, delete_source, stats as data_stats, flash_cache_stats
    return {
        "api_sources": lambda p: api_sources(),
        "web_sources": lambda p: web_sources(),
        "add_api":     lambda p: add_api(p),
        "add_web":     lambda p: add_web(p),
        "delete":      lambda p: delete_source(p["source_id"]),
        "stats":       lambda p: data_stats(),
        "flash_cache": lambda p: flash_cache_stats(),
    }


def _tasks() -> dict:
    from core.services.tasks_service import (
        live_activity, task_history, submit_task, get_scheduled,
        schedule_task, delete_scheduled, time_sense, planner_sessions,
    )
    return {
        "live":       lambda p: live_activity(),
        "history":    lambda p: task_history(p.get("limit", 40)),
        "submit":     lambda p: submit_task(p),
        "scheduled":  lambda p: get_scheduled(),
        "schedule":   lambda p: schedule_task(p),
        "delete":     lambda p: delete_scheduled(p["task_id"]),
        "time_sense": lambda p: time_sense(),
        "planner":    lambda p: planner_sessions(),
    }


def _code() -> dict:
    from core.services.code_service import (
        list_projects, project_tree, read_file, write_file,
        create_file, delete_file, generate_code, apply_code,
    )
    from core.services.project_service import (
        list_projects as list_visual_projects,
        create_project, get_project, get_project_context,
        write_project_file, read_project_file,
    )
    return {
        "projects":  lambda p: list_projects(),
        "tree":      lambda p: project_tree(p.get("folder", "."), p.get("max_depth", 3)),
        "read":      lambda p: read_file(p["path"]),
        "write":     lambda p: write_file(p["path"], p["content"]),
        "create":    lambda p: create_file(p["path"], p.get("content", "")),
        "delete":    lambda p: delete_file(p["path"]),
        "generate":  lambda p: generate_code(p.get("prompt", ""), p.get("project_folder", "")),
        "apply":     lambda p: apply_code(p["path"], p["content"]),
        "visual_projects": lambda p: list_visual_projects(),
        "create_project": lambda p: create_project(p.get("name", ""), p.get("description", ""), p.get("type", "fullstack")),
        "get_project": lambda p: get_project(p.get("id", p.get("project_id", ""))),
        "project_context": lambda p: {"context": get_project_context(p.get("id", ""))},
        "project_write": lambda p: write_project_file(p["project_id"], p["path"], p["content"]),
        "project_read": lambda p: read_project_file(p["project_id"], p["path"]),
        "project_chat": lambda p: _project_scoped_chat(p),
    }


def _project_scoped_chat(p):
    """Chat scoped to a specific project — LLM sees project files as context."""
    from core.services.project_service import get_project_context
    project_id = p.get("project_id", p.get("id", ""))
    message = p.get("message", p.get("prompt", ""))
    context = get_project_context(project_id)

    from api.brain_api_v2 import call_brain
    return call_brain("ai", "fast", {
        "prompt": f"Project context:\n{context[:8000]}\n\nUser question: {message}",
        "models": p.get("models", ["kimi"]),
    }).get("data", {})


# ═══════════════════════════════════════════════════════════════════
#  INTERNAL HELPERS — direct calls replacing HTTP
# ═══════════════════════════════════════════════════════════════════


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


def _hot_reload_svc(p):
    from core.hot_reload import hot_reload_service
    return hot_reload_service(p.get("service", p.get("name", "")))

def _hot_reload_all():
    from core.hot_reload import hot_reload_all_services
    return hot_reload_all_services()

def _save_reload(p):
    from core.hot_reload import save_and_reload
    return save_and_reload(p.get("path", ""), p.get("content", ""))

def _reload_history():
    from core.hot_reload import get_reload_history
    return {"history": get_reload_history()}

def _genesis_storage_stats():
    from core.genesis_storage import get_genesis_storage
    return get_genesis_storage().get_stats()

def _genesis_cleanup():
    from core.genesis_storage import get_genesis_storage
    return get_genesis_storage().cleanup_expired()

def _file_events(p):
    from core.workspace_bridge import get_recent_events
    return {"events": get_recent_events(p.get("limit", 50))}

def _process_docs(p):
    from core.document_processor import process_documents
    return process_documents(p.get("files", []), p.get("category", "general"), p.get("workspace", ""))

def _processing_status():
    from core.document_processor import get_processing_status
    return get_processing_status()

def _scan_upload(p):
    from core.workspace_bridge import scan_upload
    return scan_upload(p.get("path", ""), p.get("content", ""))

def _undo(p):
    from core.user_features import undo
    r = undo(p.get("path", ""))
    return {"undone": r is not None}

def _redo(p):
    from core.user_features import redo
    r = redo(p.get("path", ""))
    return {"redone": r is not None}

def _profile(p):
    from core.user_features import get_profile
    return get_profile(p.get("user_id", "default"))

def _update_profile(p):
    from core.user_features import update_profile
    uid = p.pop("user_id", "default")
    return update_profile(uid, p)

def _notifications(p):
    from core.user_features import get_notifications
    return {"notifications": get_notifications(p.get("unread_only", False))}

def _notify(p):
    from core.user_features import notify
    return notify(p.get("title", ""), p.get("message", ""), p.get("type", "info"))

def _permissions(p):
    from core.user_features import get_workspace_permissions
    return get_workspace_permissions(p.get("workspace", ""))

def _set_perm(p):
    from core.user_features import set_permission
    return set_permission(p.get("workspace", ""), p.get("user_id", ""), p.get("level", "read"))

def _shortcuts():
    from core.user_features import get_shortcuts
    return get_shortcuts()

def _fuzzy(p):
    from core.user_features import fuzzy_search
    return {"results": fuzzy_search(p.get("query", ""), p.get("limit", 20))}

def _workspace_ctx(p):
    from core.workspace_bridge import get_workspace_context
    return {"context": get_workspace_context(p.get("workspace", ""))}

def _generate_report(p):
    from core.reports import generate_daily_report
    return generate_daily_report(hours=p.get("hours", 24))

def _list_reports():
    from core.reports import list_reports
    return {"reports": list_reports()}

def _get_report(p):
    from core.reports import get_report
    return get_report(p.get("filename", ""))

def _genesis_hot(p):
    from core.genesis_storage import get_genesis_storage
    return {"keys": get_genesis_storage().get_hot(p.get("limit", 100))}

def _recent_traces():
    from core.tracing import get_recent_keys
    return {"keys": get_recent_keys(50)}


def _trace_stats():
    from core.tracing import get_buffer_stats
    return get_buffer_stats()


def _synapses():
    from core.hebbian import get_hebbian_mesh
    mesh = get_hebbian_mesh()
    return {"weights": mesh.get_weights(), "strongest": mesh.get_strongest(10)}


def _synapse_brain(p):
    from core.hebbian import get_hebbian_mesh
    return get_hebbian_mesh().get_brain_connectivity(p.get("brain", ""))


def _intelligence_report(p):
    from core.intelligence import get_intelligence_report
    return get_intelligence_report(hours=p.get("hours", 24))


def _trust_state():
    from core.intelligence import AdaptiveTrust
    return AdaptiveTrust.get_all_trust()


def _mine_genesis_keys(p):
    from core.intelligence import GenesisKeyMiner
    return GenesisKeyMiner().mine_patterns(hours=p.get("hours", 24), limit=p.get("limit", 5000))


def _mine_episodes():
    from core.intelligence import EpisodicMiner
    return EpisodicMiner().mine_episodes()


def _run_pipeline(p):
    from core.coding_pipeline import get_coding_pipeline, get_pipeline_progress
    pipeline = get_coding_pipeline()

    if p.get("background"):
        run_id = pipeline.run_background(p.get("task", p.get("prompt", "")), p)
        return {"run_id": run_id, "status": "queued", "message": "Pipeline running in background. Use ai/pipeline_progress to check status."}

    if p.get("progress"):
        progress = get_pipeline_progress()
        run_id = p.get("run_id")
        if run_id:
            return progress.get(run_id)
        return {"runs": progress.get_all()}

    result = pipeline.run(p.get("task", p.get("prompt", "")), p)
    return {
        "status": result.status,
        "trust_score": result.trust_score,
        "chunks": len(result.chunks),
        "duration_ms": result.total_duration_ms,
        "details": [
            {
                "chunk": c.chunk_id,
                "description": c.description[:100],
                "status": c.status,
                "layers": [{"layer": l.layer, "name": l.name, "status": l.status,
                            "trust": l.trust_score, "duration_ms": l.duration_ms}
                           for l in c.layers],
            }
            for c in result.chunks
        ],
    }


def _dl_predict(p):
    from core.deep_learning import get_model
    return get_model().predict(p)


def _dl_train(p):
    from core.deep_learning import get_model
    return get_model().train_from_db(hours=p.get("hours", 24), limit=p.get("limit", 1000))


def _ooda(p):
    from core.cognitive_mesh import CognitiveMesh
    return CognitiveMesh.ooda_cycle(p.get("observation", ""), p)


def _ambiguity(p):
    from core.cognitive_mesh import CognitiveMesh
    return CognitiveMesh.resolve_ambiguity(p.get("text", ""), p)


def _invariants():
    from core.cognitive_mesh import CognitiveMesh
    return CognitiveMesh.check_invariants()


def _cognitive_report(p):
    from core.cognitive_mesh import CognitiveMesh
    return CognitiveMesh.full_cognitive_report(p.get("query", ""))


def _bandit_select(p):
    from core.cognitive_mesh import CognitiveMesh
    return CognitiveMesh.bandit_select(p.get("options", []), p)


def _deterministic_scan():
    from core.deterministic_bridge import build_deterministic_report
    return build_deterministic_report()

def _deterministic_fix(p):
    from core.deterministic_bridge import deterministic_fix_cycle
    return deterministic_fix_cycle(p.get("task", ""))

def _knowledge_gaps_deep():
    from core.cognitive_mesh import CognitiveMesh
    return CognitiveMesh.analyze_knowledge_gaps()



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

@router.post("/ask")
async def brain_ask(request: Request):
    """
    Smart routing — describe what you want in natural language.
    Grace auto-routes to the optimal brain + action.

    POST /brain/ask { "query": "what is the system health?" }
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    query = body.get("query", body.get("message", body.get("q", "")))
    payload = body.get("payload", {})

    from core.auto_router import smart_call
    return smart_call(query, payload)


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
