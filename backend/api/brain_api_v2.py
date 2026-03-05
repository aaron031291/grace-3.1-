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
              "system": _system, "data": _data, "tasks": _tasks, "code": _code,
              "deterministic": _deterministic, "workspace": _workspace}
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
        "genesis_deterministic_scan": lambda p: _genesis_deterministic_scan(),
        "rag_deterministic_scan": lambda p: _rag_deterministic_scan(),
        "triad": lambda p: _run_triad(p),
        "triad_status": lambda p: _triad_status(),

        # Sub-Agent System
        "agent_submit": lambda p: _agent_submit(p),
        "agent_status": lambda p: _agent_task_status(p),
        "agent_parallel": lambda p: _agent_parallel(p),
        "agent_collaborative": lambda p: _agent_collaborative(p),
        "agent_pipeline": lambda p: _agent_pipeline(p),
        "agent_pool_status": lambda p: _agent_pool_status(),
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
        "worker_pool":  lambda p: _worker_pool_status(),
        "llm_cache":    lambda p: _llm_cache_stats(),
        "clear_llm_cache": lambda p: _clear_llm_cache(),
        "api_costs":    lambda p: _api_cost_summary(),
        "memory_pressure": lambda p: _memory_pressure(),
        "snapshot_stats": lambda p: _snapshot_stats(),
        "db_info":      lambda p: _db_info(),
        "user_rate_limit": lambda p: _user_rate_check(p),
        "lifecycle_scan": lambda p: _lifecycle_scan(),
        "lifecycle_probe_heal": lambda p: _lifecycle_probe_heal(p),
        "lifecycle_events": lambda p: _lifecycle_events(p),
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
        "generate":  lambda p: _contract_enforced_generate(p),
        "generate_raw": lambda p: generate_code(p.get("prompt", ""), p.get("project_folder", "")),
        "apply":     lambda p: apply_code(p["path"], p["content"]),
        "visual_projects": lambda p: list_visual_projects(),
        "create_project": lambda p: create_project(p.get("name", ""), p.get("description", ""), p.get("type", "fullstack")),
        "get_project": lambda p: get_project(p.get("id", p.get("project_id", ""))),
        "project_context": lambda p: {"context": get_project_context(p.get("id", ""))},
        "project_write": lambda p: write_project_file(p["project_id"], p["path"], p["content"]),
        "project_read": lambda p: read_project_file(p["project_id"], p["path"]),
        "project_chat": lambda p: _project_scoped_chat(p),
    }


def _contract_enforced_generate(p):
    """
    Code generation through GRACE protocol — contract-enforced.

    AI-to-AI: structured protocol (GraceMessage/GraceResponse).
    NLP: generated only for human-facing output.
    Contract: deterministic checks (syntax, imports, security, trust).
    """
    from core.grace_protocol import GraceMessage, OperationType, OutputMode, route_message

    prompt = p.get("prompt", "")
    if not prompt:
        return {"error": "Missing 'prompt'"}

    execution_allowed = p.get("execution_allowed", p.get("execute", True))

    msg = GraceMessage(
        operation=OperationType.CODE_GENERATE,
        source="brain.code",
        target="coding_agent",
        payload={
            "prompt": prompt,
            "project_folder": p.get("project_folder", ""),
            "file_path": p.get("file_path", ""),
            "component": p.get("component", "user_request"),
        },
        output_mode=OutputMode.HUMAN if p.get("human_facing", True) else OutputMode.AI,
        contract_type="code_generation",
        execution_allowed=execution_allowed,
    )

    response = route_message(msg)
    result = response.to_dict()

    if response.human_text:
        result["explanation"] = response.human_text
    return result


def _project_scoped_chat(p):
    """Chat scoped to a specific project — LLM sees project files as context."""
    from core.services.project_service import get_project_context
    project_id = p.get("project_id", p.get("id", ""))
    message = p.get("message", p.get("prompt", ""))
    context = get_project_context(project_id)

    from api.brain_api_v2 import call_brain as _cb_inner
    return _cb_inner("ai", "fast", {
        "prompt": f"Project context:\n{context[:8000]}\n\nUser question: {message}",
        "models": p.get("models", ["kimi"]),
    }).get("data", {})


# ═══════════════════════════════════════════════════════════════════
#  DETERMINISTIC BRAIN — 9th brain domain
# ═══════════════════════════════════════════════════════════════════

def _deterministic() -> dict:
    """
    The Deterministic Brain — all deterministic capabilities as a first-class brain.

    Consolidates: scanning, fixing, lifecycle, event bus, coding contracts,
    genesis validation, RAG validation, component probing, and logging.
    """
    return {
        # Scanning
        "scan": lambda p: _deterministic_scan(),
        "fix": lambda p: _deterministic_fix(p),
        "genesis_scan": lambda p: _genesis_deterministic_scan(),
        "rag_scan": lambda p: _rag_deterministic_scan(),

        # Lifecycle
        "lifecycle_scan": lambda p: _lifecycle_scan(),
        "probe_heal": lambda p: _lifecycle_probe_heal(p),
        "probe_all": lambda p: _det_probe_all(),
        "lifecycle_events": lambda p: _lifecycle_events(p),
        "registry": lambda p: _det_registry(),

        # Event Bus (multi-entry-point)
        "publish": lambda p: _det_publish(p),
        "bus_stats": lambda p: _det_bus_stats(),
        "bus_log": lambda p: _det_bus_log(p),
        "init_bridges": lambda p: _det_init_bridges(),

        # Coding Contracts
        "validate_code": lambda p: _det_validate_code(p),
        "validate_fix": lambda p: _det_validate_fix(p),
        "validate_component": lambda p: _det_validate_component(p),
        "validate_healing": lambda p: _det_validate_healing(p),
        "contracts": lambda p: _det_contracts(),

        # Logging
        "log": lambda p: _lifecycle_events(p),
        "log_summary": lambda p: _det_log_summary(),

        # GRACE Protocol (structured AI-to-AI, NLP only human-facing)
        "protocol_route": lambda p: _protocol_route(p),
        "protocol_review": lambda p: _protocol_review(p),

        # E2E Validation (Genesis → Output, fully deterministic)
        "e2e_validate": lambda p: _e2e_validate(),
        "e2e_stage": lambda p: _e2e_stage(p),
    }


def _det_probe_all():
    from core.deterministic_lifecycle import probe_all_components, _registry, auto_discover_components
    if not _registry:
        auto_discover_components()
    return probe_all_components()

def _det_registry():
    from core.deterministic_lifecycle import get_registry, _registry, auto_discover_components
    if not _registry:
        auto_discover_components()
    return {"registry": get_registry(), "total": len(get_registry())}

def _det_publish(p):
    from core.deterministic_event_bus import publish, TOPICS
    topic = p.get("topic", "deterministic.problem_detected")
    comp = p.get("component", "unknown")
    payload = p.get("payload", {})
    priority = p.get("priority", 5)
    task_id = publish(topic, comp, payload, priority, source="brain_api")
    return {"task_id": task_id, "topic": topic, "component": comp, "available_topics": TOPICS}

def _det_bus_stats():
    from core.deterministic_event_bus import get_bus_stats
    return get_bus_stats()

def _det_bus_log(p):
    from core.deterministic_event_bus import get_task_log
    return {"tasks": get_task_log(p.get("limit", 50))}

def _det_init_bridges():
    from core.deterministic_event_bus import initialize_bridges
    initialize_bridges()
    return {"status": "bridges_initialized"}

def _det_validate_code(p):
    from core.deterministic_coding_contracts import execute_code_generation_contract
    return execute_code_generation_contract(
        component=p.get("component", "unknown"),
        generated_code=p.get("code", ""),
        file_path=p.get("file_path"),
        min_trust=p.get("min_trust", 0.5),
    ).to_dict()

def _det_validate_fix(p):
    from core.deterministic_coding_contracts import execute_code_fix_contract
    return execute_code_fix_contract(
        component=p.get("component", "unknown"),
        file_path=p.get("file_path", ""),
        fix_code=p.get("code", ""),
        original_problems=p.get("problems", []),
        min_trust=p.get("min_trust", 0.5),
    ).to_dict()

def _det_validate_component(p):
    from core.deterministic_coding_contracts import execute_component_creation_contract
    return execute_component_creation_contract(
        component=p.get("component", "unknown"),
        component_code=p.get("code", ""),
        file_path=p.get("file_path", ""),
        min_trust=p.get("min_trust", 0.6),
    ).to_dict()

def _det_validate_healing(p):
    from core.deterministic_coding_contracts import execute_healing_contract
    return execute_healing_contract(
        component=p.get("component", "unknown"),
        healing_code=p.get("code", ""),
        healing_method=p.get("method", "unknown"),
        min_trust=p.get("min_trust", 0.5),
    ).to_dict()

def _det_contracts():
    from core.deterministic_coding_contracts import get_available_contracts
    return get_available_contracts()

def _det_log_summary():
    from core.deterministic_logger import get_event_summary
    return get_event_summary()


def _e2e_validate():
    """Run full deterministic e2e LLM pipeline validation: Genesis → Output."""
    from core.deterministic_e2e_validator import run_e2e_validation
    return run_e2e_validation().to_dict()


def _e2e_stage(p):
    """Run a single e2e validation stage by number (1-10)."""
    stage_num = p.get("stage", 0)
    from core.deterministic_e2e_validator import (
        _stage_genesis, _stage_governance, _stage_memory,
        _stage_retrieval, _stage_llm_providers, _stage_cognitive_pipeline,
        _stage_coding_contracts, _stage_brain_api, _stage_agent_pool,
        _stage_output_integrity,
    )
    stage_map = {
        1: _stage_genesis, 2: _stage_governance, 3: _stage_memory,
        4: _stage_retrieval, 5: _stage_llm_providers, 6: _stage_cognitive_pipeline,
        7: _stage_coding_contracts, 8: _stage_brain_api, 9: _stage_agent_pool,
        10: _stage_output_integrity,
    }
    fn = stage_map.get(stage_num)
    if not fn:
        return {"error": f"Invalid stage {stage_num}. Valid: 1-10",
                "stages": {k: fn.__name__.replace("_stage_", "") for k, fn in stage_map.items()}}
    from dataclasses import asdict
    return asdict(fn())


def _protocol_route(p):
    """Route a structured message through the GRACE protocol.
    AI-to-AI: structured only. NLP generated only when output_mode == 'human'."""
    from core.grace_protocol import GraceMessage, OperationType, OutputMode, route_message

    op_str = p.get("operation", "analyze")
    try:
        operation = OperationType(op_str)
    except ValueError:
        return {"error": f"Unknown operation: {op_str}. Valid: {[o.value for o in OperationType]}"}

    output_mode = OutputMode.HUMAN if p.get("human_facing", False) else OutputMode.AI

    msg = GraceMessage(
        operation=operation,
        source=p.get("source", "brain.deterministic"),
        target=p.get("target", "auto"),
        payload=p.get("payload", {}),
        output_mode=output_mode,
        contract_type=p.get("contract_type"),
        execution_allowed=p.get("execution_allowed", False),
    )
    return route_message(msg).to_dict()


def _protocol_review(p):
    """Review code through the GRACE protocol — deterministic checks, structured output."""
    from core.grace_protocol import GraceMessage, OperationType, OutputMode, route_message

    code = p.get("code", "")
    if not code:
        return {"error": "Missing 'code' in payload"}

    msg = GraceMessage(
        operation=OperationType.CODE_REVIEW,
        source="brain.deterministic",
        target="code_reviewer",
        payload={
            "code": code,
            "component": p.get("component", "unknown"),
        },
        output_mode=OutputMode.HUMAN if p.get("human_facing", False) else OutputMode.AI,
    )
    return route_message(msg).to_dict()


def _workspace() -> dict:
    """Workspace brain — internal VCS, CI/CD, multi-tenant management.
    Bridges dev tab, codebase, docs, and projects through Grace's platform."""
    from core.services.workspace_service import (
        ws_list, ws_create, ws_snapshot, ws_history, ws_diff,
        ws_rollback, ws_branches, ws_create_branch, ws_files,
        ws_content, ws_snapshot_dir, ws_pipeline_run, ws_pipeline_history,
    )
    return {
        "list":             lambda p: ws_list(),
        "create":           ws_create,
        "snapshot":         ws_snapshot,
        "snapshot_dir":     ws_snapshot_dir,
        "history":          ws_history,
        "diff":             ws_diff,
        "rollback":         ws_rollback,
        "content":          ws_content,
        "files":            ws_files,
        "branches":         ws_branches,
        "create_branch":    ws_create_branch,
        "pipeline_run":     ws_pipeline_run,
        "pipeline_history": ws_pipeline_history,
    }


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


def _worker_pool_status():
    from core.worker_pool import pool_status
    return pool_status()


def _llm_cache_stats():
    from core.security import get_llm_cache
    return get_llm_cache().stats()


def _clear_llm_cache():
    from core.security import get_llm_cache
    get_llm_cache().clear()
    return {"cleared": True}


def _api_cost_summary():
    from core.security import get_cost_tracker
    return get_cost_tracker().get_summary()


def _memory_pressure():
    from core.memory_injector import get_memory_pressure
    return get_memory_pressure()


def _snapshot_stats():
    from core.memory_injector import get_snapshot_stats
    return get_snapshot_stats()


def _db_info():
    try:
        from database.connection import DatabaseConnection
        from core.db_compat import get_table_stats, get_db_size_mb
        engine = DatabaseConnection.get_engine()
        return {
            "dialect": engine.dialect.name,
            "size_mb": get_db_size_mb(engine),
            "tables": get_table_stats(engine),
            "healthy": DatabaseConnection.health_check(),
        }
    except Exception as e:
        return {"error": str(e)}


def _user_rate_check(p):
    from core.security import check_user_rate_limit
    user_id = p.get("user_id", "anonymous")
    tier = p.get("tier", "default")
    return check_user_rate_limit(user_id, tier)


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

def _genesis_deterministic_scan():
    from genesis.deterministic_genesis_validator import run_genesis_validation
    return run_genesis_validation().to_dict()

def _rag_deterministic_scan():
    from retrieval.deterministic_rag_validator import run_rag_validation
    return run_rag_validation().to_dict()

def _lifecycle_scan():
    from core.deterministic_lifecycle import lifecycle_scan
    return lifecycle_scan()

def _lifecycle_probe_heal(p):
    comp = p.get("component_id", p.get("component", ""))
    if comp:
        from core.deterministic_lifecycle import run_lifecycle, _registry, register_component
        if comp not in _registry:
            register_component(comp, comp)
        return run_lifecycle(comp).to_dict()
    else:
        from core.deterministic_lifecycle import run_lifecycle_all
        return run_lifecycle_all()

def _lifecycle_events(p):
    from core.deterministic_logger import get_event_log, get_event_summary
    comp = p.get("component", "")
    limit = p.get("limit", 50)
    return {"events": get_event_log(comp or None, limit), "summary": get_event_summary()}

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
        "code":          {"actions": list(_code().keys()), "description": "Codebase, projects, code generation"},
        "deterministic": {"actions": list(_deterministic().keys()), "description": "Deterministic scanning, lifecycle, event bus, coding contracts, probing"},
        "workspace":     {"actions": list(_workspace().keys()), "description": "Internal VCS, CI/CD, multi-tenant workspaces (replaces GitHub)"},
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

@router.post("/deterministic", response_model=BrainResponse)
async def brain_deterministic(req: BrainRequest):
    return _call("deterministic", req.action, req.payload or {}, _deterministic())

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

@router.post("/workspace", response_model=BrainResponse)
async def brain_workspace(req: BrainRequest):
    return _call("workspace", req.action, req.payload or {}, _workspace())

def _agent_submit(p):
    """Submit a task to a specific Qwen agent for background processing."""
    from cognitive.qwen_agents import get_agent_pool, AgentRole, TaskPriority
    pool = get_agent_pool()
    role_map = {"code": AgentRole.CODE, "reason": AgentRole.REASON, "fast": AgentRole.FAST}
    role = role_map.get(p.get("role", "code"), AgentRole.CODE)
    priority_map = {"critical": TaskPriority.CRITICAL, "high": TaskPriority.HIGH,
                    "normal": TaskPriority.NORMAL, "low": TaskPriority.LOW, "background": TaskPriority.BACKGROUND}
    priority = priority_map.get(p.get("priority", "normal"), TaskPriority.NORMAL)
    task_id = pool.submit_background(
        prompt=p.get("prompt", ""),
        role=role,
        priority=priority,
        use_pipeline=p.get("use_pipeline", False),
        execution_allowed=p.get("execution_allowed", False),
        project_folder=p.get("project_folder", ""),
        context=p.get("context", {}),
    )
    return {"task_id": task_id, "role": role.value, "status": "queued"}


def _agent_task_status(p):
    """Get status of a background agent task."""
    from cognitive.qwen_agents import get_agent_pool
    task_id = p.get("task_id", "")
    if not task_id:
        return {"error": "Missing task_id"}
    result = get_agent_pool().get_task(task_id)
    return result or {"error": f"Task {task_id} not found"}


def _agent_parallel(p):
    """Run prompt across all 3 agents in parallel (multi-threaded)."""
    from cognitive.qwen_agents import get_agent_pool, AgentRole
    pool = get_agent_pool()
    roles = None
    if p.get("roles"):
        role_map = {"code": AgentRole.CODE, "reason": AgentRole.REASON, "fast": AgentRole.FAST}
        roles = [role_map[r] for r in p["roles"] if r in role_map]
    return pool.run_parallel(
        prompt=p.get("prompt", ""),
        roles=roles,
        context=p.get("context", {}),
        timeout=p.get("timeout", 120),
    )


def _agent_collaborative(p):
    """Full collaborative workflow: triage → parallel → synthesis → contract."""
    from cognitive.qwen_agents import get_agent_pool
    return get_agent_pool().run_collaborative(
        prompt=p.get("prompt", ""),
        context=p.get("context", {}),
        execution_allowed=p.get("execution_allowed", False),
    )


def _agent_pipeline(p):
    """Submit a task to the 9-layer coding pipeline via agent system. Returns task_id."""
    from cognitive.qwen_agents import get_agent_pool
    task_id = get_agent_pool().run_pipeline_with_agents(
        prompt=p.get("prompt", ""),
        execution_allowed=p.get("execution_allowed", False),
        project_folder=p.get("project_folder", ""),
    )
    return {"task_id": task_id, "status": "queued", "pipeline": "9_layer"}


def _agent_pool_status():
    """Get status of all Qwen agents."""
    from cognitive.qwen_agents import get_agent_pool
    return get_agent_pool().get_pool_status()


def _run_triad(p):
    """Run the Qwen Triad Orchestrator — async parallel processing across all 3 models."""
    import asyncio
    from cognitive.qwen_triad_orchestrator import get_triad_orchestrator

    orchestrator = get_triad_orchestrator()
    prompt = p.get("prompt", p.get("message", p.get("query", "")))
    if not prompt:
        return {"error": "Missing 'prompt' in payload"}

    loop = None
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        pass

    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(
                asyncio.run,
                orchestrator.process(
                    prompt=prompt,
                    system_prompt=p.get("system_prompt", ""),
                    execution_allowed=p.get("execution_allowed", False),
                    conversation_history=p.get("history", []),
                    project_folder=p.get("project_folder", ""),
                )
            )
            return future.result(timeout=300)
    else:
        return asyncio.run(
            orchestrator.process(
                prompt=prompt,
                system_prompt=p.get("system_prompt", ""),
                execution_allowed=p.get("execution_allowed", False),
                conversation_history=p.get("history", []),
                project_folder=p.get("project_folder", ""),
            )
        )


def _triad_status():
    """Get Qwen Triad Orchestrator status and configuration."""
    from settings import settings
    return {
        "models": {
            "code": settings.OLLAMA_MODEL_CODE or "qwen3:32b",
            "reason": settings.OLLAMA_MODEL_REASON or "qwen3:30b",
            "fast": settings.OLLAMA_MODEL_FAST or "qwen3:14b",
        },
        "features": {
            "async_parallel": True,
            "subsystem_context": [
                "memory", "genesis_keys", "diagnostics", "self_healing",
                "self_learning", "self_governance", "self_mirror", "timesense",
                "trust_scores", "hebbian_mesh",
            ],
            "governance": "read_only_unless_user_specifies_execution",
            "synthesis": "reasoning_model_merges_all_outputs",
        },
        "status": "active",
    }


@router.get("/directory")
async def brain_directory():
    d = _build_directory()
    total = sum(len(b["actions"]) for b in d.values())
    return {"brains": d, "total_brains": len(d), "total_actions": total,
            "usage": "POST /brain/{domain} { action: '...', payload: {...} }"}

@router.post("/agents/submit")
async def agent_submit_endpoint(req: BrainRequest):
    """Submit a task to a Qwen agent for background processing. Returns task_id."""
    return BrainResponse(brain="agents", action="submit", ok=True,
                         data=_agent_submit(req.payload or {}))


@router.post("/agents/status")
async def agent_status_endpoint(req: BrainRequest):
    """Check status of a background agent task."""
    return BrainResponse(brain="agents", action="status", ok=True,
                         data=_agent_task_status(req.payload or {}))


@router.post("/agents/parallel")
async def agent_parallel_endpoint(req: BrainRequest):
    """Run prompt across all 3 agents in parallel."""
    return BrainResponse(brain="agents", action="parallel", ok=True,
                         data=_agent_parallel(req.payload or {}))


@router.post("/agents/collaborative")
async def agent_collaborative_endpoint(req: BrainRequest):
    """Full collaborative workflow: triage → parallel → synthesis → contracts."""
    return BrainResponse(brain="agents", action="collaborative", ok=True,
                         data=_agent_collaborative(req.payload or {}))


@router.post("/agents/pipeline")
async def agent_pipeline_endpoint(req: BrainRequest):
    """Submit task to 9-layer coding pipeline via agent system."""
    return BrainResponse(brain="agents", action="pipeline", ok=True,
                         data=_agent_pipeline(req.payload or {}))


@router.get("/agents/pool")
async def agent_pool_status_endpoint():
    """Get status of all Qwen agents and their task queues."""
    return _agent_pool_status()


@router.post("/triad")
async def triad_endpoint(req: BrainRequest):
    """Qwen Triad — async parallel processing across all 3 Qwen models with full subsystem context."""
    from cognitive.qwen_triad_orchestrator import get_triad_orchestrator
    orchestrator = get_triad_orchestrator()
    payload = req.payload or {}
    prompt = payload.get("prompt", payload.get("message", payload.get("query", "")))
    if not prompt:
        raise HTTPException(status_code=400, detail="Missing 'prompt' in payload")
    result = await orchestrator.process(
        prompt=prompt,
        system_prompt=payload.get("system_prompt", ""),
        execution_allowed=payload.get("execution_allowed", False),
        conversation_history=payload.get("history", []),
        project_folder=payload.get("project_folder", ""),
    )
    return BrainResponse(brain="triad", action="process", ok=True, data=result)


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
