"""
Brain API v2 Ã¢â‚¬â€ CLEAN version. No HTTP-to-localhost calls.
All business logic via direct Python function calls through core/services/.

8 domains, 95+ actions, zero self-HTTP.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Any, Optional, Dict, List
from datetime import datetime
import asyncio
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


def _run_coro_sync(coro):
    """Run an async coroutine from sync code. Safe when called from a thread with or without a running event loop."""
    try:
        asyncio.get_running_loop()
        has_loop = True
    except RuntimeError:
        has_loop = False
    if not has_loop:
        return asyncio.run(coro)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()


def _genesis_safe_payload(obj, max_items=50, max_str=500):
    """Trim and sanitize payload for Genesis input_data/output_data (observability without huge blobs).
    Recursively replaces coroutines and other non-JSON-serializable values so DB insert never fails."""
    if obj is None:
        return None
    if asyncio.iscoroutine(obj):
        return "<coroutine not awaited>"
    if isinstance(obj, dict):
        out = {}
        for k, v in list(obj.items())[:max_items]:
            out[k] = _genesis_safe_payload(v, max_items=max_items, max_str=max_str)
        return out
    if isinstance(obj, (list, tuple)):
        return [_genesis_safe_payload(v, max_items=max_items, max_str=max_str) for v in list(obj)[:max_items]]
    if isinstance(obj, (str, bytes)):
        return (str(obj)[:max_str] if isinstance(obj, bytes) else obj[:max_str])
    try:
        import json
        json.dumps(obj, default=str)
        return obj
    except (TypeError, ValueError):
        return str(obj)[:max_str]


async def _call(brain: str, action: str, payload: dict, handlers: dict,
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
            try:
                from core.kpi_recorder import record_brain_kpi
                record_brain_kpi(brain, action, False)
            except Exception:
                pass
            return BrainResponse(brain=brain, action=action, ok=False,
                                 error="Rate limit exceeded Ã¢â‚¬â€ try again in 60s")
    except Exception:
        pass

    # Input sanitization
    try:
        from core.security import check_sql_injection, sanitize_string
        for key, val in (payload or {}).items():
            if isinstance(val, str):
                if check_sql_injection(val):
                    try:
                        from core.kpi_recorder import record_brain_kpi
                        record_brain_kpi(brain, action, False)
                    except Exception:
                        pass
                    return BrainResponse(brain=brain, action=action, ok=False,
                                        error=f"Invalid input in field '{key}'")
                payload[key] = sanitize_string(val)
    except Exception:
        pass

    start = time.time()
    handler = handlers.get(action)
    if not handler:
        try:
            from core.kpi_recorder import record_brain_kpi
            record_brain_kpi(brain, action, False)
        except Exception:
            pass
        return BrainResponse(brain=brain, action=action, ok=False,
                             error=f"Unknown action '{action}'. Available: {', '.join(sorted(handlers.keys()))}")
    try:
        data = handler(payload)
        if asyncio.iscoroutine(data):
            data = await data
        latency = round((time.time() - start) * 1000, 1)
        gk = None
        try:
            from api._genesis_tracker import track
            gk = track(
                key_type="api_request",
                what=f"brain/{brain}/{action}",
                where=f"/brain/{brain}",
                why="user or system action",
                who=f"brain.{brain}",
                how=action,
                input_data=_genesis_safe_payload(payload),
                output_data=_genesis_safe_payload(data) if data is not None else {"ok": True},
                tags=["brain", brain, action],
            )
        except Exception:
            pass
        try:
            from core.kpi_recorder import record_brain_kpi
            record_brain_kpi(brain, action, True)
        except Exception:
            pass
        return BrainResponse(brain=brain, action=action, ok=True,
                             data=data, latency_ms=latency, genesis_key_id=gk)
    except Exception as e:
        latency = round((time.time() - start) * 1000, 1)
        try:
            from api._genesis_tracker import track
            track(
                key_type="error",
                what=f"brain/{brain}/{action}: {e}",
                where=f"/brain/{brain}",
                why="user or system action",
                who=f"brain.{brain}",
                how=action,
                input_data=_genesis_safe_payload(payload),
                output_data={"error": str(e)[:500], "error_type": type(e).__name__},
                is_error=True,
                error_type=type(e).__name__,
                error_message=str(e)[:200],
                tags=["brain", brain, action, "error"],
            )
        except Exception:
            pass
        try:
            from core.kpi_recorder import record_brain_kpi
            record_brain_kpi(brain, action, False)
        except Exception:
            pass
        return BrainResponse(brain=brain, action=action, ok=False,
                             error=str(e)[:300], latency_ms=latency)


_calling_brain = "external"


def call_brain(brain_name: str, action: str, payload: dict = None) -> dict:
    """Cross-brain call with Hebbian learning Ã¢â‚¬â€ every action gets a Genesis key."""
    global _calling_brain
    source = _calling_brain
    brains = {"chat": _chat, "files": _files, "govern": _govern, "ai": _ai,
              "system": _system, "data": _data, "tasks": _tasks, "code": _code,
              "deterministic": _deterministic}
    factory = brains.get(brain_name)
    if not factory:
        try:
            from core.kpi_recorder import record_brain_kpi
            record_brain_kpi(brain_name, action or "unknown", False)
        except Exception:
            pass
        try:
            from api._genesis_tracker import track
            track(key_type="error", what=f"call_brain unknown brain: {brain_name}", who=source, is_error=True, tags=["brain", "error"])
        except Exception:
            pass
        return {"ok": False, "error": f"Unknown brain: {brain_name}"}
    handler = factory().get(action)
    if not handler:
        try:
            from core.kpi_recorder import record_brain_kpi
            record_brain_kpi(brain_name, action, False)
        except Exception:
            pass
        try:
            from api._genesis_tracker import track
            track(key_type="error", what=f"call_brain unknown action: {brain_name}/{action}", who=source, is_error=True, tags=["brain", "error"])
        except Exception:
            pass
        return {"ok": False, "error": f"Unknown action '{action}' in brain '{brain_name}'"}
    try:
        old_caller = _calling_brain
        _calling_brain = brain_name
        data = handler(payload or {})
        if asyncio.iscoroutine(data):
            data = _run_coro_sync(data)
        _calling_brain = old_caller

        try:
            from core.hebbian import get_hebbian_mesh
            get_hebbian_mesh().record(source, brain_name, success=True)
        except Exception:
            pass
        try:
            from api._genesis_tracker import track
            track(
                key_type="api_request",
                what=f"brain/{brain_name}/{action}",
                where=f"/brain/{brain_name}",
                why="internal brain call",
                who=f"brain.{source}",
                how=action,
                input_data=_genesis_safe_payload(payload or {}),
                output_data=_genesis_safe_payload(data) if data is not None else {"ok": True},
                tags=["brain", brain_name, action],
            )
        except Exception:
            pass
        try:
            from core.kpi_recorder import record_brain_kpi
            record_brain_kpi(brain_name, action, True)
        except Exception:
            pass
        return {"ok": True, "data": data}
    except Exception as e:
        try:
            from core.hebbian import get_hebbian_mesh
            get_hebbian_mesh().record(source, brain_name, success=False)
        except Exception:
            pass
        try:
            from api._genesis_tracker import track
            track(
                key_type="error",
                what=f"brain/{brain_name}/{action}: {e}",
                where=f"/brain/{brain_name}",
                why="internal brain call",
                who=f"brain.{source}",
                how=action,
                input_data=_genesis_safe_payload(payload or {}),
                output_data={"error": str(e)[:500], "error_type": type(e).__name__},
                is_error=True,
                error_type=type(e).__name__,
                error_message=str(e)[:200],
                tags=["brain", brain_name, action, "error"],
            )
        except Exception:
            pass
        try:
            from core.kpi_recorder import record_brain_kpi
            record_brain_kpi(brain_name, action, False)
        except Exception:
            pass
        return {"ok": False, "error": str(e)[:200]}


# Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢
#  AGENTIC SHARED ACTIONS Ã¢â‚¬â€ injected into every brain domain
# Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢

def _agentic_actions(brain_name: str) -> dict:
    """
    Shared agentic actions injected into every brain.
    Allows any brain action to be spawned as a background task.

    Usage: POST /brain/{domain} {"action": "spawn_task", "payload": {"action": "scan", "payload": {}}}
    """
    from core.agentic_runner import spawn_task, get_task, list_tasks, get_agent_runner
    return {
        "spawn_task": lambda p: spawn_task(
            brain=p.get("brain", brain_name),
            action=p.get("action", ""),
            payload=p.get("payload", {}),
        ),
        "task_status": lambda p: get_task(p.get("task_id", "")),
        "task_list":   lambda p: {"tasks": list_tasks(brain=p.get("brain"), limit=p.get("limit", 30))},
        "task_cancel": lambda p: {"cancelled": get_agent_runner().cancel_task(p.get("task_id", ""))},
        "task_cleanup": lambda p: (get_agent_runner().cleanup_old() or {"cleaned": True}),
    }


# Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢
#  HANDLERS Ã¢â‚¬â€ direct function calls, no HTTP
# Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢

def _chat() -> dict:
    from core.services.chat_service import (
        list_chats, create_chat, get_chat, delete_chat,
        get_history, send_prompt, send_prompt_with_rag, run_consensus, get_world_model,
    )
    return {
        "list": lambda p: list_chats(p.get("limit", 50)),
        "create": create_chat,
        "get": get_chat,
        "delete": delete_chat,
        "history": get_history,
        "send": send_prompt,
        "send_with_rag": send_prompt_with_rag,
        "consensus": run_consensus,
        "world_model": lambda p: get_world_model(p),
        **_agentic_actions("chat"),
    }


def _files() -> dict:
    from core.services.files_service import (
        tree, browse, read, write, create, delete, search, stats, docs_all,
        save_file_agentic, place_in_folder, create_doc, create_report, categorize, filing,
    )
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
        # Agentic filing and categorization (through brain + Qwen/librarian)
        "save_file":     lambda p: save_file_agentic(p),
        "place_in_folder": lambda p: place_in_folder(p),
        "create_doc":    lambda p: create_doc(p),
        "create_report": lambda p: create_report(p),
        "categorize":    lambda p: categorize(p),
        "filing":        lambda p: filing(p),
        **_agentic_actions("files"),
    }


def _govern() -> dict:
    from core.services.govern_service import (
        dashboard, get_approvals, approve_action, get_scores,
        list_rules, get_persona, update_persona, genesis_stats,
        trigger_healing, trigger_learning, record_gap, genesis_keys, approvals_history,
        adaptive_overrides, approve_override,
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
        "record_gap": lambda p: record_gap(p.get("what", ""), p.get("target", ""), p.get("tags")),
        "genesis_keys": lambda p: genesis_keys(p.get("limit", 20)),
        "approvals_history": lambda p: approvals_history(p.get("limit", 30)),
        "adaptive_overrides": lambda p: adaptive_overrides(p.get("limit", 20)),
        "approve_override": lambda p: approve_override(p.get("override_id"), p.get("action")),
        "coding_contract": lambda p: _governance_coding_contract(p),
        **_agentic_actions("govern"),
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
        "fill_knowledge_gaps": lambda p: _fill_knowledge_gaps(p or {}),
        "learning_memory_expand": lambda p: _learning_memory_expand(p or {}),
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
        "oracle_export": lambda p: _oracle_export(p or {}),
        "governance_training_cycle": lambda p: _governance_training_cycle(p or {}),
        "governance_report": lambda p: _governance_report(p or {}),
        "propose_architecture": lambda p: _propose_architecture(p),
        "build_architecture": lambda p: _build_architecture(p),
        **_agentic_actions("ai"),
    }

def _propose_architecture(p):
    from cognitive.architecture_proposer import get_architecture_proposer
    return get_architecture_proposer().propose(p.get("spec", {}))

def _build_architecture(p):
    from cognitive.architecture_proposer import get_architecture_proposer
    return get_architecture_proposer().build(p.get("proposal_id", ""))

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
        "decide_autonomous_action": lambda p: _decide_autonomous_action(p),
        "model_version_check": lambda p: _model_version_check(),
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
        "set_environment": lambda p: _set_env(p),
        "get_environment": lambda p: _get_env(),
        "list_environments": lambda p: _list_envs(),
        "env_write": lambda p: _env_write(p),
        "run_independent": lambda p: _run_independent(p),
        "run_failover": lambda p: _run_failover(p),
        "snapshot": lambda p: _snapshot(p),
        "rollback": lambda p: _rollback(p),
        "snapshots": lambda p: _list_snapshots(),
        "security_scan": lambda p: _security_scan(p),
        "budget_status": lambda p: _budget_status(),
        "set_budget": lambda p: _set_budget(p),
        "provenance": lambda p: _provenance_entries(p),
        "verify_ledger": lambda p: _verify_ledger(),
        "pool_stats": lambda p: _pool_stats(),
        "cache_stats": lambda p: _cache_stats(),
        "clear_cache": lambda p: _clear_cache(),
        "reset_db": lambda p: _reset_db(),
        "reset_vector_db": lambda p: _reset_vector_db(),
        "gc": lambda p: _gc(),
        "project_governance": lambda p: _project_gov(p),
        "set_project_rules": lambda p: _set_proj_rules(p),
        "create_approval": lambda p: _create_approval(p),
        "approval_list": lambda p: _approval_list(p),
        "respond_approval": lambda p: _respond_approval(p),
        "kpi_scores": lambda p: _kpi_scores(p),
        "kpi_dashboard": lambda p: _kpi_dashboard(),
        "compliance_presets": lambda p: _compliance_presets(),
        "apply_compliance": lambda p: _apply_compliance(p),
        "orchestrate": lambda p: _orchestrate(p),
        "containers": lambda p: _list_containers(),
        "container_stats": lambda p: _container_stats(p),
        "container_rules": lambda p: _container_rules(p),
        "container_knowledge": lambda p: _container_knowledge(p),
        "container_whitelist": lambda p: _container_whitelist(p),
        "container_context": lambda p: _container_context(p),
        "clone_grace": lambda p: _clone_grace(p),
        "global_rules": lambda p: {"rules": __import__("core.project_container", fromlist=["GLOBAL_RULES"]).GLOBAL_RULES},
        "create_user": lambda p: _create_user(p),
        "list_users": lambda p: _list_users(),
        "user_activity": lambda p: _user_activity(p),
        "project_activity": lambda p: _project_activity(p),
        "daily_summary": lambda p: _daily_summary(p),
        "switch_project": lambda p: _switch_project(p),
        "active_session": lambda p: _active_session(p),
        "librarian_ingest": lambda p: _librarian_ingest(p),
        "librarian_search": lambda p: _librarian_search(p),
        "librarian_versions": lambda p: _librarian_versions(p),
        "librarian_stats": lambda p: _librarian_stats(),
        "cross_search": lambda p: _cross_search(p),
        "export_project": lambda p: _export_project(p),
        "import_project": lambda p: _import_project(p),
        "copy_file_cross": lambda p: _copy_cross(p),
        "move_file_cross": lambda p: _move_cross(p),
        "project_rollback": lambda p: _project_rollback(p),
        "list_exports": lambda p: _list_exports(),
        "sync_events": lambda p: _sync_events(p),
        "sync_stats": lambda p: _sync_stats(),
        "dist_state": lambda p: _dist_stats(),
        "dist_set": lambda p: _dist_set(p),
        "dist_get": lambda p: _dist_get(p),
        "dist_instances": lambda p: _dist_instances(),
        "dist_session": lambda p: _dist_session(p),
        "semantic_search": lambda p: _semantic_search(p),
        "component_registry": lambda p: _component_registry(),
        "component_profile": lambda p: _component_profile(p),
        "validate_all": lambda p: _validate_all(),
        "validate_component": lambda p: _validate_one(p),
        "report_cards": lambda p: _report_cards(),
        "report_card": lambda p: _report_card(p),
        "generate_report": lambda p: _generate_report(p),
        "list_reports": lambda p: _list_reports(),
        "get_report": lambda p: _get_report(p),
        "intelligence": lambda p: _intelligence_report(p),
        "trust":        lambda p: _trust_state(),
        "mine_keys":    lambda p: _mine_genesis_keys(p),
        "mine_episodes": lambda p: _mine_episodes(),
        "architecture_explain":  lambda p: _architecture_explain(p),
        "architecture_find":    lambda p: _architecture_find(p),
        "architecture_connected": lambda p: _architecture_connected(p),
        "architecture_diagnose": lambda p: _architecture_diagnose(),
        "architecture_map":     lambda p: _architecture_map(),
        "embedding_config":     lambda p: _embedding_config(),
        "brain_directory":     lambda p: _brain_directory(),
        "models_summary":      lambda p: _models_summary(),
        "schema_info":         lambda p: _schema_info(),
        "graphs_info":         lambda p: _graphs_info(),
        "deterministic_first_loop": lambda p: _deterministic_first_loop(p),
        "verify_built": lambda p: _verify_built(p),
        "trigger_definitions": lambda p: _trigger_definitions(p),
        "run_unified_triggers": lambda p: _run_unified_triggers(p),
        "grace_state": lambda p: _grace_state(),
        "immune_scan": lambda p: _immune_scan(p),
        "immune_status": lambda p: _immune_status(),
        "immune_loop_start": lambda p: _immune_loop_start(),
        "immune_loop_stop": lambda p: _immune_loop_stop(),
        "immune_playbooks": lambda p: _immune_playbooks(),
        "proactive_engine_start": lambda p: _proactive_engine_start(),
        "proactive_engine_stop": lambda p: _proactive_engine_stop(),
        "proactive_engine_status": lambda p: _proactive_engine_status(),
        "trigger_healing_cycle": lambda p: _trigger_healing_cycle(p),
        "diagnostic_sensors": lambda p: _diagnostic_sensors(),
        "diagnostic_forensics": lambda p: _diagnostic_forensics(),
        "stress_test_start": lambda p: _stress_test_start(p),
        "stress_test_status": lambda p: _stress_test_status(),
        "stress_test_stop": lambda p: _stress_test_stop(),
        **_agentic_actions("system"),
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
        # Agentic librarian (Qwen-backed): process, place, suggest, categorize
        "librarian_process":      lambda p: _data_librarian_process(p),
        "librarian_organise_file": lambda p: _data_librarian_organise_file(p),
        "librarian_suggest_folder": lambda p: _data_librarian_suggest_folder(p),
        "librarian_categorize":   lambda p: _data_librarian_categorize(p),
        "librarian_on_new_folder": lambda p: _data_librarian_on_new_folder(p),
        "librarian_stats":        lambda p: _data_librarian_stats(),
        # Semantic entity classification Ã¢â‚¬â€ translate raw data to canonical domain model
        "classify_entity": lambda p: _classify_entity(p),
        "entity_schema_map": lambda p: _entity_schema_map(),
        **_agentic_actions("data"),
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
        **_agentic_actions("tasks"),
    }


def _classify_entity(p: dict) -> dict:
    """Classify raw data into a canonical semantic entity bucket."""
    from cognitive.semantic_entity_classifier import classify_entity
    return classify_entity(
        text=p.get("text", ""),
        filename=p.get("filename", ""),
        source_type=p.get("source_type", "user_generated"),
        metadata=p.get("metadata"),
    )


def _entity_schema_map() -> dict:
    """Return the full entity Ã¢â€ â€™ db_table/vector_collection mapping."""
    from cognitive.semantic_entity_classifier import ENTITY_SCHEMA_MAP
    return {
        "entity_buckets": list(ENTITY_SCHEMA_MAP.keys()),
        "schema_map": {k: {"db_table": v[0], "vector_collection": v[1]} for k, v in ENTITY_SCHEMA_MAP.items()},
    }


def _code() -> dict:
    from core.services.code_service import (
        list_projects, project_tree, read_file, write_file,
        create_file, delete_file, apply_code,
    )
    from core.services.code_service import generate_code as _code_service_generate
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
        "generate":  lambda p: _code_service_generate(p.get("prompt", ""), p.get("project_folder", ""), p.get("use_pipeline", False)),
        "generate_pipeline": lambda p: _code_service_generate(p.get("prompt", ""), p.get("project_folder", ""), True),
        "apply":     lambda p: apply_code(p["path"], p["content"]),
        "visual_projects": lambda p: list_visual_projects(),
        "create_project": lambda p: create_project(p.get("name", ""), p.get("description", ""), p.get("type", "fullstack")),
        "get_project": lambda p: get_project(p.get("id", p.get("project_id", ""))),
        "project_context": lambda p: {"context": get_project_context(p.get("id", ""))},
        "project_write": lambda p: write_project_file(p["project_id"], p["path"], p["content"]),
        "project_read": lambda p: read_project_file(p["project_id"], p["path"]),
        "project_chat": lambda p: _project_scoped_chat(p),
        "assimilate":   lambda p: _hunter_assimilate(p),
        **_agentic_actions("code"),
    }

def _deterministic() -> dict:
    return {
        "scan": lambda p: {"status": "mock"},
        "fix": lambda p: {"status": "mock"},
        **_agentic_actions("deterministic"),
    }


def _project_scoped_chat(p):
    """Chat scoped to a specific project Ã¢â‚¬â€ LLM sees project files as context."""
    from core.services.project_service import get_project_context
    project_id = p.get("project_id", p.get("id", ""))
    message = p.get("message", p.get("prompt", ""))
    context = get_project_context(project_id)

    from api.brain_api_v2 import call_brain
    return call_brain("ai", "fast", {
        "prompt": f"Project context:\n{context[:8000]}\n\nUser question: {message}",
        "models": p.get("models", ["kimi"]),
    }).get("data", {})


def _hunter_assimilate(p):
    """Run HUNTER assimilation (code Ã¢â€ â€™ analyse Ã¢â€ â€™ integrate). Handshake runs on success."""
    from cognitive.hunter_assimilator import get_hunter
    code = p.get("code", p.get("content", ""))
    description = p.get("description", "")
    user = p.get("user", "brain")
    if not code.strip():
        return {"error": "code or content required", "handshake_sent": False}
    result = get_hunter().assimilate(code, description=description, user=user)
    return {
        "handshake_sent": result.handshake_sent,
        "trust_score": result.trust_score,
        "files_created": result.files_created,
        "status": result.status,
        "success": result.status == "complete" and result.trust_score >= 60,
    }


# Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢
#  INTERNAL HELPERS Ã¢â‚¬â€ direct calls replacing HTTP
# Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢


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
    """Neighbor-by-neighbor gap analysis (reverse kNN)."""
    try:
        from cognitive.reverse_knn import scan_knowledge_gaps
        return scan_knowledge_gaps()
    except Exception:
        return {"gaps": []}


def _fill_knowledge_gaps(p: dict):
    """After neighbor search, pull from API, web search, and FlashCache to fill gaps."""
    try:
        from cognitive.reverse_knn import fill_gaps_from_sources
        max_gaps = p.get("max_gaps", 5)
        auto_ingest = p.get("auto_ingest", True)
        return fill_gaps_from_sources(max_gaps=max_gaps, auto_ingest=auto_ingest)
    except Exception as e:
        return {"error": str(e), "topics_processed": 0, "gaps_filled": 0}


def _learning_memory_expand(p: dict):
    """From learning memory: run neighbor search then pull from API, web, FlashCache."""
    try:
        from cognitive.reverse_knn import scan_knowledge_gaps, fill_gaps_from_sources
        gaps = scan_knowledge_gaps()
        total = (gaps.get("summary") or {}).get("total_gaps", 0)
        if total == 0:
            return {"scan": gaps, "filled": None, "message": "no_gaps_to_fill"}
        max_gaps = p.get("max_gaps", 5)
        filled = fill_gaps_from_sources(max_gaps=max_gaps, auto_ingest=True)
        return {"scan": gaps, "filled": filled}
    except Exception as e:
        return {"error": str(e), "scan": None, "filled": None}


def _oracle_export(p: dict):
    """Push learning memory to Oracle (human-readable files for librarian and file management)."""
    try:
        from cognitive.governance_training_loop import run_oracle_export
        import os
        kb_path = p.get("kb_path") or os.environ.get("GRACE_KNOWLEDGE_BASE_PATH")
        if kb_path:
            from pathlib import Path
            kb_path = Path(kb_path)
        return run_oracle_export(kb_path=kb_path, limit=p.get("limit", 500), min_trust=p.get("min_trust", 0.3))
    except Exception as e:
        return {"error": str(e), "exported": 0}


def _governance_training_cycle(p: dict):
    """Full cycle: KB Ã¢â€ â€™ Learning memory Ã¢â€ â€™ Oracle Ã¢â€ â€™ Sandbox review; 60d trial, governance, report, +30% approval."""
    try:
        from cognitive.governance_training_loop import run_full_cycle
        import os
        kb_path = p.get("kb_path") or os.environ.get("GRACE_KNOWLEDGE_BASE_PATH")
        if kb_path:
            from pathlib import Path
            kb_path = Path(kb_path)
        return run_full_cycle(
            kb_path=kb_path,
            export_to_oracle=p.get("export_to_oracle", True),
            run_sandbox_review=p.get("run_sandbox_review", True),
        )
    except Exception as e:
        return {"error": str(e), "cycle_at": None}


def _governance_report(p: dict):
    """60-day governance report for user-in-loop approval; +30% Ã¢â€ â€™ add to system."""
    try:
        from cognitive.governance_training_loop import get_governance_report
        return get_governance_report(experiment_id=p.get("experiment_id"))
    except Exception as e:
        return {"error": str(e)}


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
    """Agentic code generation: Qwen latest (reasoning + coding) via pipeline or fast path."""
    try:
        from cognitive.qwen_coding_net import generate_code
        return generate_code(
            p.get("prompt", ""),
            p.get("project_folder", ""),
            use_pipeline=p.get("use_pipeline", False),
        )
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
    return health_map(p.get("window_minutes", 60))


def _problems():
    from api.component_health_api import problems_list
    return problems_list()


def _baselines():
    from api.component_health_api import learned_baselines
    return learned_baselines()


def _orphans():
    from api.component_health_api import detect_orphan_services
    return detect_orphan_services()


def _correlate(p):
    from api.component_health_api import correlate_failure
    return _run_coro_sync(correlate_failure(p.get("component", "")))


def _trigger_scan():
    from api.runtime_triggers_api import scan_triggers
    return _run_coro_sync(scan_triggers())


def _scan_heal():
    from api.runtime_triggers_api import scan_and_heal
    return _run_coro_sync(scan_and_heal())


def _decide_autonomous_action(p: dict) -> dict:
    """
    Agentic decision: given a problem, return which brain action to run.
    Returns either {escalate: True, reason} or {escalate: False, brain, action, payload}.
    Centralizes routing so the autonomous loop only executes what the brain decides.
    """
    problem = p or {}
    target = problem.get("target", "")
    reason = problem.get("reason", "")
    severity = problem.get("severity", "warning")
    r = reason.lower()

    if problem.get("flag_for_human"):
        return {"escalate": True, "reason": reason, "type": "escalate"}

    # Service down Ã¢â€ â€™ HEAL (system/scan_heal)
    if "unreachable" in r or "down" in r or "connection" in r:
        return {"escalate": False, "brain": "system", "action": "scan_heal", "payload": {}, "type": "heal"}

    # No activity (always-on) Ã¢â€ â€™ HEAL (govern/heal)
    if "no activity" in r and severity == "critical":
        return {"escalate": False, "brain": "govern", "action": "heal", "payload": {}, "type": "heal"}

    # High CPU/RAM Ã¢â€ â€™ HEAL (govern/heal)
    if "cpu" in r or "ram" in r or "memory" in r:
        return {"escalate": False, "brain": "govern", "action": "heal", "payload": {}, "type": "heal"}

    # Import/code errors Ã¢â€ â€™ LEARN (govern/record_gap)
    if "import" in r or "module" in r or "dependency" in r:
        return {
            "escalate": False,
            "brain": "govern",
            "action": "record_gap",
            "payload": {
                "what": f"Code gap: {target} Ã¢â‚¬â€ {reason}",
                "target": target,
                "tags": ["autonomous", "gap", "code-issue"],
            },
            "type": "learn",
        }

    # Test failures Ã¢â€ â€™ LEARN (govern/record_gap)
    if "test" in r or "failure" in r:
        return {
            "escalate": False,
            "brain": "govern",
            "action": "record_gap",
            "payload": {
                "what": f"Test gap: {target} Ã¢â‚¬â€ {reason}",
                "target": target,
                "tags": ["autonomous", "gap", "test-failure"],
            },
            "type": "learn",
        }

    # Default: escalate
    return {"escalate": True, "reason": reason, "type": "escalate"}


def _model_version_check():
    """Run model auto-update check (Kimi/Opus/Ollama)."""
    from cognitive.model_updater import check_all_models
    return check_all_models()


def _probe_sweep():
    from api.probe_agent_api import probe_sweep
    return probe_sweep()


def _probe_models():
    from api.probe_agent_api import probe_models
    return probe_models()


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


def _architecture_explain(p):
    """What does this component do? (Living architectural map.)"""
    try:
        from cognitive.architecture_compass import get_compass
        component = p.get("component", p.get("name", ""))
        if not component:
            return {"error": "Provide 'component' or 'name' (e.g. pipeline, trust_engine)."}
        text = get_compass().explain(component)
        return {"component": component, "explanation": text}
    except Exception as e:
        return {"error": str(e)}


def _architecture_find(p):
    """What can handle this task? (Capability Ã¢â€ â€™ components.)"""
    try:
        from cognitive.architecture_compass import get_compass
        capability = p.get("capability", p.get("task", ""))
        if not capability:
            return {"error": "Provide 'capability' or 'task' (e.g. code review, health monitoring)."}
        components = get_compass().find_for(capability)
        return {"capability": capability, "components": components}
    except Exception as e:
        return {"error": str(e)}


def _architecture_connected(p):
    """Trace path from one component to another (dependency/connection graph)."""
    try:
        from cognitive.architecture_compass import get_compass
        comp_a = p.get("from", p.get("comp_a", p.get("source", "")))
        comp_b = p.get("to", p.get("comp_b", p.get("target", "")))
        if not comp_a or not comp_b:
            return {"error": "Provide 'from' and 'to' (or comp_a/comp_b, source/target)."}
        path = get_compass().how_connected(comp_a, comp_b)
        return {"from": comp_a, "to": comp_b, "path": path}
    except Exception as e:
        return {"error": str(e)}


def _architecture_diagnose():
    """Bottlenecks, isolated modules, most-depended-on, capabilities list."""
    try:
        from cognitive.architecture_compass import get_compass
        return get_compass().diagnose()
    except Exception as e:
        return {"error": str(e)}


def _architecture_map():
    """Full component map with an NLP-friendly narrative summary."""
    try:
        from cognitive.architecture_compass import get_compass
        data = get_compass().get_full_map()
        components = data.get("components") or {}
        total = data.get("total", len(components))
        connected = data.get("connected", 0)
        isolated_count = data.get("isolated", 0)

        # Build a short narrative summary (no LLM) for Ask tab / NLP
        top_hubs = sorted(
            components.items(),
            key=lambda x: x[1].get("connections_out", 0) + x[1].get("connections_in", 0),
            reverse=True,
        )[:5]
        isolated = [p for p, c in components.items() if c.get("isolated")]

        parts = [
            f"Grace has {total} components ({connected} connected, {isolated_count} isolated)."
        ]
        if top_hubs:
            hubs_str = ", ".join(
                f"{p.replace('/', '.')} ({c.get('connections_out', 0)} out, {c.get('connections_in', 0)} in)"
                for p, c in top_hubs
            )
            parts.append(f" Top hubs: {hubs_str}.")
        if isolated:
            names = [p.replace("/", ".") for p in isolated[:8]]
            parts.append(f" Isolated modules: {', '.join(names)}{'...' if len(isolated) > 8 else ''}.")
        data["summary"] = " ".join(parts)
        return data
    except Exception as e:
        return {"error": str(e)}


def _embedding_config():
    """What embedding model are we using? (Model name, path, dimension if loaded.)"""
    try:
        out = {}
        try:
            from settings import settings
            out["model_name"] = getattr(settings, "EMBEDDING_DEFAULT", None)
            out["model_path"] = getattr(settings, "EMBEDDING_MODEL_PATH", None)
            out["device"] = getattr(settings, "EMBEDDING_DEVICE", None)
        except Exception:
            out["model_name"] = None
            out["model_path"] = None
            out["device"] = None
        try:
            from embedding.embedder import get_embedding_model
            model = get_embedding_model()
            if model is not None:
                out["loaded"] = True
                out["dimension"] = model.get_embedding_dimension() if hasattr(model, "get_embedding_dimension") else None
            else:
                out["loaded"] = False
                out["dimension"] = None
        except Exception:
            out["loaded"] = False
            out["dimension"] = None
        return out
    except Exception as e:
        return {"error": str(e)}


def _brain_directory():
    """All brains (domains) and their actions Ã¢â‚¬â€ queryable API map."""
    try:
        d = _build_directory()
        total = sum(len(b["actions"]) for b in d.values())
        return {
            "brains": d,
            "total_brains": len(d),
            "total_actions": total,
            "usage": "POST /brain/{domain} with { action: '...', payload: {...} }",
        }
    except Exception as e:
        return {"error": str(e)}


def _models_summary():
    """LLM models + embedding model in one place."""
    try:
        out = {"embedding": _embedding_config()}
        try:
            from cognitive.consensus_engine import get_available_models
            out["llm_models"] = get_available_models()
        except Exception as e:
            out["llm_models"] = []
            out["llm_models_error"] = str(e)
        try:
            from settings import settings
            out["llm_provider"] = getattr(settings, "LLM_PROVIDER", "ollama")
        except Exception:
            out["llm_provider"] = None
        return out
    except Exception as e:
        return {"error": str(e)}


def _schema_info():
    """Database type, name, Qdrant status Ã¢â‚¬â€ schema/storage overview."""
    try:
        out = {}
        try:
            from settings import settings
            out["database"] = {
                "type": getattr(settings, "DATABASE_TYPE", "postgresql"),
                "name": getattr(settings, "DATABASE_NAME", "grace"),
                "path": getattr(settings, "DATABASE_PATH", None),
                "host": getattr(settings, "DATABASE_HOST", None),
                "port": getattr(settings, "DATABASE_PORT", None),
            }
        except Exception as e:
            out["database"] = {"error": str(e)}
        try:
            from database.connection import DatabaseConnection
            out["database"]["connected"] = DatabaseConnection.health_check()
        except Exception:
            out["database"]["connected"] = False
        try:
            from vector_db.client import get_qdrant_client
            from settings import settings
            q = get_qdrant_client()
            out["qdrant"] = {
                "connected": q.is_connected() if hasattr(q, "is_connected") else True,
                "url": getattr(settings, "QDRANT_URL", None) or (f"{getattr(settings, 'QDRANT_HOST', 'localhost')}:{getattr(settings, 'QDRANT_PORT', 6333)}"),
            }
            if hasattr(q, "list_collections"):
                out["qdrant"]["collections"] = len(q.list_collections())
            elif hasattr(q, "get_collections"):
                coll = q.get_collections()
                out["qdrant"]["collections"] = len(coll.collections) if coll and hasattr(coll, "collections") else 0
            else:
                out["qdrant"]["collections"] = None
        except Exception as e:
            out["qdrant"] = {"error": str(e)}
        return out
    except Exception as e:
        return {"error": str(e)}


def _graphs_info():
    """Graphs in Grace: component graph, vector store, magma."""
    try:
        out = {"graphs": []}
        try:
            from cognitive.architecture_compass import get_compass
            m = get_compass().get_full_map()
            out["component_graph"] = {"type": "architecture", "total_components": m.get("total", 0), "connected": m.get("connected", 0), "isolated": m.get("isolated", 0)}
            out["graphs"].append("component_graph (architecture compass)")
        except Exception as e:
            out["component_graph"] = {"error": str(e)}
        out["graphs"].append("qdrant (vector embeddings)")
        out["graphs"].append("magma (cognitive/memory graphs when enabled)")
        return out
    except Exception as e:
        return {"error": str(e)}


def _deterministic_first_loop(p):
    """Run deterministic-first loop: Genesis keys Ã¢â€ â€™ probe Ã¢â€ â€™ AST/deterministic fix Ã¢â€ â€™ handoff to LLM only when needed."""
    from core.deterministic_first_loop import run_deterministic_first_loop, get_handoff_context
    result = run_deterministic_first_loop(
        task=p.get("task"),
        run_probe=p.get("run_probe", True),
        run_genesis_search=p.get("run_genesis_search", True),
        run_deterministic_scan=p.get("run_deterministic_scan", True),
    )
    result["handoff_context"] = get_handoff_context(result)
    return result


def _deterministic() -> dict:
    """Deterministic brain: rule-only scan and fix. No LLM until handoff."""
    return {
        "scan": lambda p: _deterministic_scan(),
        "fix": lambda p: _deterministic_fix(p),
        "first_loop": lambda p: _deterministic_first_loop(p),
        "report": lambda p: _deterministic_scan(),  # alias for scan
        **_agentic_actions("deterministic"),
    }


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

def _set_env(p):
    from core.environment import set_environment
    return set_environment(p.get("name", p.get("environment", "")))

def _get_env():
    from core.environment import get_environment, get_environment_path
    env = get_environment()
    return {"environment": env, "path": str(get_environment_path())}

def _list_envs():
    from core.environment import list_environments
    return {"environments": list_environments()}

def _env_write(p):
    from core.environment import route_file_write
    return route_file_write(p.get("path", ""), p.get("content", ""), p.get("source", "dev_tab"))

def _snapshot(p):
    from core.safety import snapshot_state
    return {"snapshot_id": snapshot_state(p.get("label", ""))}

def _rollback(p):
    from core.safety import rollback_to
    return rollback_to(p.get("snapshot_id"))

def _list_snapshots():
    from core.safety import list_snapshots
    return {"snapshots": list_snapshots()}

def _security_scan(p):
    from core.safety import scan_code_security
    return scan_code_security(p.get("code", ""), p.get("file", ""))

def _budget_status():
    from core.safety import get_budget_status
    return get_budget_status()

def _set_budget(p):
    from core.safety import set_budget_limits
    return set_budget_limits(p.get("calls_per_hour"), p.get("tokens_per_hour"))

def _provenance_entries(p):
    from core.safety import get_ledger_entries
    return {"entries": get_ledger_entries(p.get("limit", 20))}

def _project_gov(p):
    from core.governance_engine import get_project_rules
    return get_project_rules(p.get("project_id", p.get("id", "")))


def _governance_coding_contract(p):
    """Return the governance coding contract (global + project rules) for the pipeline to enforce."""
    from core.governance_engine import get_governance_coding_contract
    return get_governance_coding_contract(p.get("project_id", p.get("id", "")))

def _set_proj_rules(p):
    from core.governance_engine import set_project_rules
    pid = p.pop("project_id", p.pop("id", ""))
    return set_project_rules(pid, p)

def _create_approval(p):
    from core.governance_engine import create_approval
    return create_approval(p.get("title",""), p.get("description",""),
                           p.get("category","general"), p.get("project_id",""),
                           p.get("severity","medium"), p.get("data"))

def _approval_list(p):
    from core.governance_engine import get_approvals
    return {"approvals": get_approvals(p.get("status"), p.get("project_id"))}

def _respond_approval(p):
    from core.governance_engine import respond_to_approval
    return respond_to_approval(p.get("id",0), p.get("action",""), p.get("reason",""))

def _kpi_scores(p):
    from core.governance_engine import get_kpi_scores
    return get_kpi_scores(p.get("component"))

def _kpi_dashboard():
    from core.governance_engine import get_kpi_dashboard
    return get_kpi_dashboard()

def _compliance_presets():
    from core.governance_engine import get_compliance_presets
    return get_compliance_presets()

def _apply_compliance(p):
    from core.governance_engine import apply_compliance_preset
    return apply_compliance_preset(p.get("project_id",""), p.get("preset",""))

def _semantic_search(p):
    from core.semantic_search import semantic_query
    return semantic_query(p.get("query", p.get("question", "")))

def _component_registry():
    from core.semantic_search import get_component_registry
    return get_component_registry()

def _component_profile(p):
    from core.semantic_search import get_component_profile
    return get_component_profile(p.get("component_id", p.get("id", "")))

def _validate_all():
    from core.component_validator import validate_all_components
    return validate_all_components()

def _validate_one(p):
    from core.component_validator import get_report_card
    return get_report_card(p.get("component_id", p.get("id", "")))

def _report_cards():
    from core.component_validator import get_all_report_cards
    return get_all_report_cards()

def _report_card(p):
    from core.component_validator import get_report_card
    return get_report_card(p.get("component_id", p.get("id", "")))

def _sync_events(p):
    from core.realtime_sync import get_recent_events
    return {"events": get_recent_events(p.get("since"), p.get("project_id"), p.get("limit", 50))}

def _sync_stats():
    from core.realtime_sync import get_sync_stats
    return get_sync_stats()

def _dist_stats():
    from core.distributed_state import get_distributed_stats
    return get_distributed_stats()

def _dist_set(p):
    from core.distributed_state import set_state
    return {"set": set_state(p.get("key", ""), p.get("value", ""))}

def _dist_get(p):
    from core.distributed_state import get_state
    return {"value": get_state(p.get("key", ""))}

def _dist_instances():
    from core.distributed_state import list_instances
    return {"instances": list_instances()}

def _dist_session(p):
    from core.distributed_state import get_user_session
    return get_user_session(p.get("user_id", "default"))

def _librarian_ingest(p):
    from core.librarian import ingest_document
    return ingest_document(p.get("path",""), p.get("content",""), p.get("project_id",""))


def _data_librarian_process(p):
    """Data brain: process document through librarian (ingest, categorize, tag). Uses Qwen for analysis."""
    from core.librarian import ingest_document
    return ingest_document(
        p.get("path", ""),
        p.get("content", ""),
        p.get("project_id", ""),
        p.get("source", "brain"),
    )


def _data_librarian_organise_file(p):
    """Data brain: move file to correct subfolder (agentic; Qwen suggests location)."""
    from pathlib import Path
    from cognitive.librarian_autonomous import get_autonomous_librarian
    path = p.get("path", "")
    target_folder = p.get("target_folder")
    if not path:
        return {"ok": False, "error": "path required"}
    lib = get_autonomous_librarian()
    if target_folder:
        try:
            from settings import settings
            kb = Path(getattr(settings, "KNOWLEDGE_BASE_PATH", "knowledge_base"))
            full = kb / path if not Path(path).is_absolute() else Path(path)
            target_dir = kb / target_folder.strip("/")
            target_dir.mkdir(parents=True, exist_ok=True)
            dest = target_dir / full.name
            if full.exists() and full != dest:
                import shutil
                shutil.move(str(full), str(dest))
                return {"action": "moved", "from": path, "to": str(dest.relative_to(kb))}
        except Exception as e:
            return {"action": "failed", "error": str(e)}
    return lib.organise_file(path)


def _data_librarian_suggest_folder(p):
    """Data brain: suggest subfolder for a path (Qwen-backed when needed)."""
    from pathlib import Path
    from cognitive.librarian_autonomous import get_autonomous_librarian
    path = p.get("path", "")
    if not path:
        return {"suggestion": None, "error": "path required"}
    try:
        from settings import settings
        kb = Path(getattr(settings, "KNOWLEDGE_BASE_PATH", "knowledge_base"))
        full = kb / path if not Path(path).is_absolute() else Path(path)
    except Exception:
        full = Path(path)
    suggestion = get_autonomous_librarian().suggest_location(full)
    return {"path": path, "suggestion": suggestion}


def _data_librarian_categorize(p):
    """Data brain: return category/tags for path (uses librarian engine + Qwen when available)."""
    from core.librarian import ingest_document
    path = p.get("path", "")
    if not path:
        return {"category": "unknown", "tags": []}
    try:
        from pathlib import Path
        from settings import settings
        kb = Path(getattr(settings, "KNOWLEDGE_BASE_PATH", "knowledge_base"))
        full = kb / path if not Path(path).is_absolute() else Path(path)
        content = full.read_text(errors="ignore")[:50000] if full.exists() else ""
    except Exception:
        content = ""
    meta = ingest_document(path, content, p.get("project_id", ""), source="categorize")
    return {"category": meta.get("category", "other"), "tags": meta.get("tags", []), "metadata": meta}


def _data_librarian_on_new_folder(p):
    """Data brain: notify librarian of new folder (triggers auto-research, taxonomy)."""
    from cognitive.librarian_autonomous import get_autonomous_librarian
    return get_autonomous_librarian().on_new_folder(p.get("folder_path", p.get("path", "")))


def _data_librarian_stats():
    """Data brain: librarian index stats."""
    from core.librarian import get_document_stats
    return get_document_stats()


def _librarian_search(p):
    from core.librarian import search_documents
    return {"results": search_documents(p.get("query",""), p.get("project_id",""), p.get("category",""))}

def _librarian_versions(p):
    from core.librarian import get_versions
    return {"versions": get_versions(p.get("path",""))}

def _librarian_stats():
    from core.librarian import get_document_stats
    return get_document_stats()

def _cross_search(p):
    from core.librarian import cross_project_search
    return {"results": cross_project_search(p.get("query",""), p.get("limit",30))}

def _export_project(p):
    from core.project_ops import export_project
    return export_project(p.get("project_id", p.get("id","")))

def _import_project(p):
    from core.project_ops import import_project
    return import_project(p.get("project_id",""), p.get("zip_path",""))

def _copy_cross(p):
    from core.project_ops import copy_file_between_projects
    return copy_file_between_projects(p.get("from_project",""), p.get("from_path",""),
                                       p.get("to_project",""), p.get("to_path"))

def _move_cross(p):
    from core.project_ops import move_file_between_projects
    return move_file_between_projects(p.get("from_project",""), p.get("from_path",""),
                                      p.get("to_project",""), p.get("to_path"))

def _project_rollback(p):
    from core.project_ops import project_rollback
    return project_rollback(p.get("project_id", p.get("id","")))

def _list_exports():
    from core.project_ops import list_exports
    return {"exports": list_exports()}

def _create_user(p):
    from core.multi_user import create_user
    return create_user(p.get("email", ""), p.get("name", ""))

def _list_users():
    from core.multi_user import list_users
    return {"users": list_users()}

def _user_activity(p):
    from core.multi_user import get_user_activity
    return {"activity": get_user_activity(p.get("user_id", ""), p.get("hours", 24))}

def _project_activity(p):
    from core.multi_user import get_project_activity
    return {"activity": get_project_activity(p.get("project_id", ""), p.get("hours", 24))}

def _daily_summary(p):
    from core.multi_user import generate_daily_summary
    return generate_daily_summary(p.get("project_id", ""), p.get("hours", 24))

def _switch_project(p):
    from core.multi_user import switch_project
    return switch_project(p.get("user_id", "default"), p.get("project_id", p.get("project", "")))

def _active_session(p):
    from core.multi_user import get_active_session
    return get_active_session(p.get("user_id", "default"))

def _list_containers():
    from core.project_container import list_containers
    return {"containers": list_containers()}

def _container_stats(p):
    from core.project_container import get_container
    return get_container(p.get("project_id", p.get("id", ""))).get_stats()

def _container_rules(p):
    from core.project_container import get_container
    return get_container(p.get("project_id", "")).get_rules()

def _container_knowledge(p):
    from core.project_container import get_container
    return get_container(p.get("project_id", "")).get_knowledge()

def _container_whitelist(p):
    from core.project_container import get_container
    return get_container(p.get("project_id", "")).get_whitelist()

def _container_context(p):
    from core.project_container import get_container
    return {"context": get_container(p.get("project_id", "")).get_context()}

def _clone_grace(p):
    from core.project_container import clone_grace_environment
    return clone_grace_environment(p.get("project_id", p.get("name", "")))

def _orchestrate(p):
    from core.brain_orchestrator import get_orchestrator
    return get_orchestrator().orchestrate(p.get("task_type","analyze"), p)

def _pool_stats():
    from core.worker_pool import get_pool_stats, get_cache_stats
    return {"pool": get_pool_stats(), "cache": get_cache_stats()}

def _cache_stats():
    from core.worker_pool import get_cache_stats
    return get_cache_stats()

def _clear_cache():
    from core.worker_pool import clear_cache
    clear_cache()
    return {"cleared": True}


def _reset_db():
    """Reset database connection (through brain)."""
    try:
        from database.connection import DatabaseConnection
        DatabaseConnection.close()
        return {"status": "closed"}
    except Exception as e:
        return {"status": "error", "detail": str(e)[:200]}


def _reset_vector_db():
    """Reset vector DB client (through brain) by forcing a new connection."""
    try:
        from vector_db.client import get_qdrant_client
        get_qdrant_client(force_new=True)
        return {"status": "reset"}
    except Exception as e:
        return {"status": "error", "detail": str(e)[:200]}


def _gc():
    """Force garbage collection (through brain)."""
    import gc
    gc.collect()
    return {"status": "ok"}


def _verify_ledger():
    from core.safety import verify_ledger
    return verify_ledger()

def _run_independent(p):
    from core.independent_models import run_independent
    return run_independent(p.get("prompt", ""), p.get("models"), p.get("system_prompt", ""))

def _run_failover(p):
    from core.independent_models import run_with_failover
    return run_with_failover(p.get("prompt", ""), p.get("models"), p.get("system_prompt", ""))

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


def _verify_built(p):
    """Deterministic verification that everything built has been built. Returns manifest."""
    from core.build_verification import run_verify_built_checks, all_required_passed
    skip_script = p.get("skip_verify_script", False)
    manifest = run_verify_built_checks(skip_verify_script=skip_script)
    manifest["ok"] = all_required_passed(manifest)
    return manifest


def _trigger_definitions(p):
    """Return unified trigger registry (determinism, self_heal, diagnostics, self_learning, self_governance, coding_agent)."""
    from core.unified_trigger_brain import get_trigger_definitions, get_categories
    category = p.get("category")
    trigger_ids = p.get("trigger_ids")
    return {
        "triggers": get_trigger_definitions(category=category, trigger_ids=trigger_ids),
        "categories": get_categories(),
    }


def _grace_state():
    """Single view of Grace state: Ouroboros, mirror, problems, health. For unified dashboard."""
    from api.autonomous_loop_api import _loop_state, _loop_log
    last_cycle = _loop_log[-1] if _loop_log else None
    try:
        from core.services.system_service import get_health_dashboard
        health = get_health_dashboard()
    except Exception:
        health = {}
    try:
        from api.component_health_api import _get_genesis_keys, _check_service_health, COMPONENT_REGISTRY, _classify_component
        keys = _get_genesis_keys(minutes=60, limit=500)
        svc = _check_service_health()
        problems = []
        for cid, comp in (COMPONENT_REGISTRY or {}).items():
            classified = _classify_component(cid, comp, keys, svc)
            if classified.get("status") in ("red", "orange"):
                problems.append({"component": classified.get("label", cid), "reason": classified.get("reason"), "status": classified["status"]})
        mirror = {"problems_observed": len(problems), "problems": problems[:10]}
    except Exception:
        mirror = {"problems_observed": 0, "problems": []}
    return {
        "ouroboros": {"running": _loop_state.get("running"), "cycle_count": _loop_state.get("cycle_count"), "last_cycle": _loop_state.get("last_cycle"), "last_result": _loop_state.get("last_result"), "actions_taken": _loop_state.get("actions_taken")},
        "last_cycle_detail": last_cycle,
        "mirror": mirror,
        "health": health,
    }


def _run_unified_triggers(p):
    """Run unified triggers (async loop); optionally filter by trigger_ids or category."""
    from core.unified_trigger_brain import run_triggers_sync
    return run_triggers_sync(
        trigger_ids=p.get("trigger_ids"),
        category=p.get("category"),
    )

def _knowledge_gaps_deep():
    from core.cognitive_mesh import CognitiveMesh
    return CognitiveMesh.analyze_knowledge_gaps()

def _immune_scan(p):
    try:
        from cognitive.proactive_healing_engine import get_proactive_engine
        engine = get_proactive_engine()
        immune = engine._get_immune()
        if immune:
            return immune.scan()
        return {"error": "Immune system not available"}
    except Exception as e:
        return {"error": str(e)}

def _immune_status():
    try:
        from cognitive.proactive_healing_engine import get_proactive_engine
        engine = get_proactive_engine()
        immune = engine._get_immune()
        if immune:
            return immune.get_status()
        return {"available": False}
    except Exception as e:
        return {"error": str(e)}

def _immune_loop_start():
    try:
        from cognitive.proactive_healing_engine import get_proactive_engine
        engine = get_proactive_engine()
        immune = engine._get_immune()
        if immune:
            immune.start_background_loop()
            return {"success": True, "status": "running"}
        return {"error": "Immune system not available"}
    except Exception as e:
        return {"error": str(e)}

def _immune_loop_stop():
    try:
        from cognitive.proactive_healing_engine import get_proactive_engine
        engine = get_proactive_engine()
        immune = engine._get_immune()
        if immune:
            immune.stop_background_loop()
            return {"success": True, "status": "stopped"}
        return {"error": "Immune system not available"}
    except Exception as e:
        return {"error": str(e)}

def _immune_playbooks():
    try:
        from cognitive.proactive_healing_engine import get_proactive_engine
        engine = get_proactive_engine()
        immune = engine._get_immune()
        if immune:
            return {"playbooks": immune.get_playbook()}
        return {"playbooks": []}
    except Exception as e:
        return {"error": str(e)}

def _proactive_engine_start():
    try:
        from cognitive.proactive_healing_engine import get_proactive_engine
        engine = get_proactive_engine()
        engine.start()
        return {"success": True, "status": "running"}
    except Exception as e:
        return {"error": str(e)}

def _proactive_engine_stop():
    try:
        from cognitive.proactive_healing_engine import get_proactive_engine
        engine = get_proactive_engine()
        engine.stop()
        return {"success": True, "status": "stopped"}
    except Exception as e:
        return {"error": str(e)}

def _proactive_engine_status():
    try:
        from cognitive.proactive_healing_engine import get_proactive_engine
        engine = get_proactive_engine()
        return {
            "status": "running" if engine.is_running else "stopped",
            "cycle_count": getattr(engine, "_cycle_count", 0),
            "anomalies_handled": engine.get_status().get("anomalies_handled", 0)
        }
    except Exception as e:
        return {"error": str(e)}

def _trigger_healing_cycle(p):
    try:
        anomaly_type = p.get("anomaly_type")
        component = p.get("component")
        context = p.get("context", {})
        
        if not anomaly_type or not component:
            return {"error": "Missing 'anomaly_type' or 'component' parameters."}
            
        from cognitive.proactive_healing_engine import get_proactive_engine
        engine = get_proactive_engine()
        result = engine.trigger_healing_cycle(
            anomaly_type=anomaly_type,
            component=component,
            context=context
        )
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)}

def _diagnostic_sensors():
    try:
        from diagnostic_machine.sensors import MetricSensors
        metrics = MetricSensors.collect_all()
        return {"sensors_status": "online", "metrics": metrics}
    except Exception as e:
        return {"error": str(e), "message": "Sensor collection failed."}

def _diagnostic_forensics():
    try:
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine
        engine = DiagnosticEngine()
        return engine.run_diagnostic_cycle()
    except Exception as e:
        return {"error": str(e)}

def _stress_test_start(p):
    try:
        # For unified brain, run synchronously to return results directly, or use an async agentic task
        from cognitive.deep_test_engine import DeepTestEngine
        engine = DeepTestEngine.get_instance()
        return engine.run_logic_tests()
    except Exception as e:
        return {"error": str(e)}

def _stress_test_status():
    from api.system_audit_api import _stress_test_status as status
    return status

def _stress_test_stop():
    return {"message": "Stop requested."}



# Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢
#  DIRECTORY + ENDPOINTS
# Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢

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
        "deterministic": {"actions": list(_deterministic().keys()), "description": "Rule-only scan and fix: AST, imports, DB, tests, services. No LLM until handoff. Verify-first cycle."},
    }


BRAIN_DIRECTORY = _build_directory()


@router.post("/chat", response_model=BrainResponse)
async def brain_chat(req: BrainRequest):
    return await _call("chat", req.action, req.payload or {}, _chat())

@router.post("/files", response_model=BrainResponse)
async def brain_files(req: BrainRequest):
    return await _call("files", req.action, req.payload or {}, _files())

@router.post("/govern", response_model=BrainResponse)
async def brain_govern(req: BrainRequest):
    return await _call("govern", req.action, req.payload or {}, _govern())

@router.post("/ai", response_model=BrainResponse)
async def brain_ai(req: BrainRequest):
    return await _call("ai", req.action, req.payload or {}, _ai())

@router.post("/system", response_model=BrainResponse)
async def brain_system(req: BrainRequest):
    return await _call("system", req.action, req.payload or {}, _system())

@router.post("/data", response_model=BrainResponse)
async def brain_data(req: BrainRequest):
    return await _call("data", req.action, req.payload or {}, _data())

@router.post("/tasks", response_model=BrainResponse)
async def brain_tasks(req: BrainRequest):
    return await _call("tasks", req.action, req.payload or {}, _tasks())

@router.post("/code", response_model=BrainResponse)
async def brain_code(req: BrainRequest):
    return await _call("code", req.action, req.payload or {}, _code())

@router.post("/deterministic", response_model=BrainResponse)
async def brain_deterministic(req: BrainRequest):
    return await _call("deterministic", req.action, req.payload or {}, _deterministic())

@router.post("/ask")
async def brain_ask(request: Request):
    """
    Smart routing Ã¢â‚¬â€ describe what you want in natural language.
    Grace auto-routes to the optimal brain + action.

    POST /brain/ask { "query": "what is the system health?" }
    """
    try:
        body = await request.json()
    except Exception:
        body = {}
    query = body.get("query", body.get("message", body.get("q", "")))
    payload = body.get("payload", {})

    # Direct route for clear "which/what/list LLM or models" questions so Ask tab never hits chat/send
    q = (query or "").strip().lower()
    if any(phrase in q for phrase in ("which llm", "which models", "what llm", "what models", "list llm", "list models", "llm in the system", "models in the system")):
        out = call_brain("system", "models_summary", {})
        out["routing"] = {"query": query, "brain": "system", "action": "models_summary", "confidence": 1.0, "auto_routed": True, "direct_route": True}
        return out

    from core.auto_router import smart_call
    return smart_call(query, payload)


@router.get("/directory")
async def brain_directory():
    try:
        from api._genesis_tracker import track
        track(key_type="api_request", what="brain/directory", who="api", how="GET", tags=["brain", "directory"])
    except Exception:
        pass
    d = _build_directory()
    total = sum(len(b["actions"]) for b in d.values())
    return {"brains": d, "total_brains": len(d), "total_actions": total,
            "usage": "POST /brain/{domain} { action: '...', payload: {...} }"}

@router.post("/orchestrate")
async def orchestrate(req: BrainOrchestration):
    try:
        from api._genesis_tracker import track
        track(key_type="api_request", what="brain/orchestrate", who="api", how="orchestrate",
              tags=["brain", "orchestrate"], output_data={"steps": len(req.steps or [])})
    except Exception:
        pass
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
