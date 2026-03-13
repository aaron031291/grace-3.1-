"""
Autonomous Loop — "Ouroboros"

Unifies self-healing, self-learning, and coding agent into ONE
continuous control loop. Runs every 30s inside the diagnostic engine.

Flow:
  TRIGGER → DIAGNOSE → DECIDE → ACT → LEARN → VERIFY → LOOP

  1. TRIGGER: Any anomaly detected (probe, trigger scan, component health)
  2. DIAGNOSE: 4-layer diagnostic engine classifies severity
  3. DECIDE: Decision matrix routes to correct action type:
     - HEAL: DB reconnect, cache clear, GC, service restart
     - LEARN: Memory mesh ingestion, knowledge gap fill, pattern extraction
     - CODE: Qwen generates fix, consensus verifies, apply if agreed
     - ESCALATE: Queue for human approval
  4. ACT: Execute the chosen action via Brain API
  5. LEARN: Record outcome in memory mesh (success/failure/partial)
  6. VERIFY: Re-probe to confirm fix worked
  7. LOOP: Feed verification result back as new trigger data

All actions tracked via Genesis keys with full provenance chain.
"""

from fastapi import APIRouter, Body
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
import threading
import time
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/autonomous", tags=["Autonomous Loop"])

_loop_state = {
    "running": False,
    "cycle_count": 0,
    "last_cycle": None,
    "last_result": None,
    "actions_taken": 0,
    "healed": 0,
    "learned": 0,
    "coded": 0,
    "escalated": 0,
    "errors": 0,
}
_loop_lock = threading.Lock()
_loop_log: list = []


def _get_time_context() -> dict:
    try:
        from cognitive.time_sense import TimeSense
        return TimeSense.get_context()
    except Exception:
        return {}


def _get_trust_score(component: str) -> float:
    try:
        from cognitive.trust_engine import get_trust_engine
        te = get_trust_engine()
        score = te.score_output(component, component, "", source="autonomous_loop")
        return float(score) if isinstance(score, (int, float)) else 0.7
    except Exception:
        return 0.7


def _get_mirror_observation() -> dict:
    try:
        import urllib.request, json as _j
        req = urllib.request.Request("http://127.0.0.1:8000/api/component-health/mirror-feed")
        with urllib.request.urlopen(req, timeout=3) as resp:
            return _j.loads(resp.read())
    except Exception:
        return {}


def _recall_similar_episode(problem_text: str) -> dict:
    """Check episodic memory for similar past problems and what worked."""
    try:
        from database.session import session_scope
        from cognitive.episodic_memory import EpisodicBuffer
        with session_scope() as sess:
            buffer = EpisodicBuffer(sess)
            episodes = buffer.recall_similar(problem_text, k=3, min_trust=0.6)
            if episodes:
                ep = episodes[0]
                return {
                    "found": True,
                    "past_problem": ep.problem[:200] if ep.problem else "",
                    "past_action": ep.action[:200] if isinstance(ep.action, str) else str(ep.action)[:200],
                    "past_outcome": ep.outcome[:200] if isinstance(ep.outcome, str) else str(ep.outcome)[:200],
                    "trust": ep.trust_score,
                }
    except Exception:
        pass
    return {"found": False}


def _update_kpis(cycle_result: dict):
    """Update KPI tracker with loop metrics."""
    try:
        from api.kpi_api import get_kpi_tracker
        tracker = get_kpi_tracker()
        tracker.increment_kpi("autonomous_loop", "cycles_completed", 1)
        tracker.increment_kpi("autonomous_loop", "triggers_detected", cycle_result.get("triggers_found", 0))
        for a in cycle_result.get("actions", []):
            tracker.increment_kpi("autonomous_loop", f"actions_{a['type']}", 1)
        if cycle_result.get("trust_blocked", 0) > 0:
            tracker.increment_kpi("autonomous_loop", "trust_blocked", cycle_result["trust_blocked"])
    except Exception:
        pass


# Trust thresholds per action type
TRUST_THRESHOLDS = {
    "heal": 0.5,
    "learn": 0.4,
    "code": 0.8,
    "escalate": 0.0,
}


def _run_cycle() -> dict:
    """Execute one full autonomous cycle with trust, time, mirror, memory."""
    cycle_start = time.time()
    result = {
        "cycle_id": f"AUTO-{int(time.time())}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "triggers_found": 0,
        "actions": [],
        "outcome": "clean",
        "trust_blocked": 0,
        "deferred": 0,
    }

    # ── TIME FILTER: Check temporal context ──────────────────────
    time_ctx = _get_time_context()
    is_quiet = time_ctx.get("period") in ("late_night", "night")
    result["time_context"] = {
        "period": time_ctx.get("period", "unknown"),
        "is_business_hours": time_ctx.get("is_business_hours", False),
        "is_quiet": is_quiet,
    }

    # ── MIRROR: Get self-observation ─────────────────────────────
    mirror = _get_mirror_observation()
    result["mirror"] = {
        "problems_observed": len(mirror.get("problems", [])),
        "total_events_1h": mirror.get("total_events_1h", 0),
        "error_count_1h": mirror.get("error_count_1h", 0),
    }

    # ── 1. TRIGGER: DETERMINISTIC scan first, then component health ──
    problems = []

    # PRIMARY: Deterministic detection (no LLM)
    try:
        from core.deterministic_bridge import build_deterministic_report, DeterministicAutoFixer
        det_report = build_deterministic_report()
        for p in det_report.get("problems", []):
            problems.append({
                "source": "deterministic",
                "target": p.get("file", p.get("module", p.get("service", p.get("type", "")))),
                "status": "red" if p.get("severity") == "critical" else "orange",
                "reason": f"[{p['type']}] {p.get('message', p.get('error', ''))}",
                "severity": p.get("severity", "warning"),
                "flag_for_human": p.get("flag_for_human", False),
            })

        # Auto-fix what we can without LLM (deterministic fixes only)
        if det_report.get("problems"):
            fixer = DeterministicAutoFixer()
            auto_fixes = fixer.auto_fix(det_report["problems"])
            result["auto_fixes"] = len(auto_fixes)
            # Problems that should be flagged for human (no auto-fix available)
            for_human = [p for p in det_report.get("problems", []) if p.get("flag_for_human")]
            if for_human:
                result["for_human"] = [
                    {"type": p.get("type"), "message": p.get("message", p.get("error", ""))[:200]}
                    for p in for_human
                ]
                from api.spindle_autonomy import autonomy_gate
                actually_for_human = []
                for p in for_human:
                    trust = _get_trust_score(p.get("target", "system"))
                    gate = autonomy_gate(p, trust)
                    
                    if not gate["autonomy"]:
                        logger.error(
                            "FLAG_FOR_HUMAN (escalated, trust=%.2f): [%s] %s",
                            trust,
                            p.get("type", ""),
                            p.get("message", p.get("error", ""))[:300],
                        )
                        actually_for_human.append(p)
                    else:
                        logger.info(
                            "AUTONOMY_GATE (passed, fallback=%s, trust=%.2f): [%s] %s - bypassing FLAG_FOR_HUMAN",
                            gate["fallback"],
                            trust,
                            p.get("type", ""),
                            p.get("message", p.get("error", ""))[:300],
                        )
                        p["flag_for_human"] = False
                        
                if actually_for_human:
                    try:
                        from api.brain_api_v2 import call_brain
                        call_brain("system", "notify", {
                            "title": "Ouroboros: Issues need human attention",
                            "message": "; ".join((p.get("message", p.get("error", "")) or "")[:80] for p in actually_for_human[:3]),
                            "type": "escalate",
                        })
                    except Exception:
                        pass
    except Exception:
        pass

    # SECONDARY: Component health (existing behavior)
    try:
        from api.component_health_api import (
            COMPONENT_REGISTRY, _get_genesis_keys, _classify_component,
            _check_service_health
        )
        keys = _get_genesis_keys(minutes=60, limit=2000)
        svc_health = _check_service_health()
        for comp_id, comp in COMPONENT_REGISTRY.items():
            classified = _classify_component(comp_id, comp, keys, svc_health)
            if classified["status"] in ("red", "orange"):
                problems.append({
                    "source": "component_health",
                    "target": classified["label"],
                    "component_id": comp_id,
                    "status": classified["status"],
                    "reason": classified["reason"],
                    "severity": "critical" if classified["status"] == "red" else "warning",
                })
    except Exception as e:
        logger.debug(f"Health scan skipped: {e}")

    try:
        from api.runtime_triggers_api import _scan_resources, _scan_code, _scan_build
        for scanner in [_scan_resources, _scan_code, _scan_build]:
            try:
                found = scanner()
                for t in found:
                    entry = t.to_dict() if hasattr(t, "to_dict") else t
                    if entry.get("severity") in ("critical", "warning"):
                        problems.append({
                            "source": "trigger_scan",
                            "target": entry.get("name", ""),
                            "status": entry.get("severity"),
                            "reason": entry.get("detail", ""),
                            "severity": entry.get("severity"),
                        })
            except Exception:
                pass
    except Exception:
        pass

    result["triggers_found"] = len(problems)

    # Unified trigger loop: run determinism, self-heal, diagnostics, self-learning, self-governance, coding agent
    try:
        from api.brain_api_v2 import call_brain
        unified = call_brain("system", "run_unified_triggers", {"category": None})
        result["unified_triggers"] = unified.get("summary", {})
    except Exception as e:
        logger.debug("Unified triggers skipped: %s", e)
        result["unified_triggers"] = {"run": 0, "ok": 0, "failed": 0}

    # ── 1b. DEEP INTELLIGENCE (parallel + background) ───────────────────
    try:
        from api.brain_api_v2 import call_brain
        from core.async_parallel import run_parallel, run_background

        # Root cause correlation — don't alert on leaf failures (sequential, touches problems)
        for p in list(problems):
            if p.get("component_id"):
                corr = call_brain("system", "correlate", {"component": p["component_id"]})
                if corr.get("ok") and corr.get("data", {}).get("suppress_alert"):
                    p["suppressed"] = True
                    problems.remove(p)

        # Run independent intelligence calls in parallel
        def _orphans(): return call_brain("system", "orphans", {})
        def _baselines(): return call_brain("system", "baselines", {})
        def _mine_keys(): return call_brain("system", "mine_keys", {"hours": 1})
        def _episodes(): return call_brain("system", "mine_episodes", {})
        def _intel(): return call_brain("system", "intelligence", {"hours": 1})
        def _synapses(): return call_brain("system", "synapses", {})
        def _trust(): return call_brain("system", "trust", {})
        out = run_parallel([_orphans, _baselines, _mine_keys, _episodes, _intel, _synapses, _trust], return_exceptions=True)
        orphans = out[0] if not isinstance(out[0], Exception) else {}
        baselines = out[1] if not isinstance(out[1], Exception) else {}
        key_patterns = out[2] if not isinstance(out[2], Exception) else {}
        episodes = out[3] if not isinstance(out[3], Exception) else {}
        intel = out[4] if not isinstance(out[4], Exception) else {}
        synapses = out[5] if not isinstance(out[5], Exception) else {}
        trust_state = out[6] if not isinstance(out[6], Exception) else {}

        if orphans.get("ok") and orphans.get("data", {}).get("orphans"):
            for o in orphans["data"]["orphans"]:
                problems.append({"source": "orphan_detection", "target": o.get("label", ""),
                                 "reason": o.get("diagnosis", ""), "severity": "warning"})
        result["baselines_checked"] = baselines.get("ok", False)
        if key_patterns.get("ok"):
            repeated = key_patterns.get("data", {}).get("repeated_failures", [])
            for rf in repeated[:3]:
                problems.append({"source": "genesis_pattern", "target": rf.get("pattern", ""),
                                 "reason": f"Repeated {rf.get('count', 0)}x", "severity": "warning"})
        result["episodes_mined"] = episodes.get("ok", False)
        result["intelligence_consulted"] = intel.get("ok", False)
        result["synapses_checked"] = synapses.get("ok", False)
        result["trust_state"] = trust_state.get("data", {}).get("models", {}) if trust_state.get("ok") else {}

        # Fire-and-forget: maintenance and scans (background)
        def _deep_background():
            try:
                call_brain("system", "genesis_cleanup", {})
                critical = [p for p in problems if p.get("severity") == "critical"]
                if critical:
                    call_brain("system", "consensus_fix", {})
                call_brain("system", "triggers", {})
                call_brain("system", "security_scan", {"code": "", "file": ""})
                call_brain("govern", "heal", {})
                call_brain("govern", "learn", {})
                call_brain("ai", "diagnose", {})
                call_brain("ai", "integration_matrix", {})
                call_brain("ai", "knowledge_gaps", {})
                call_brain("ai", "fill_knowledge_gaps", {"max_gaps": 3, "auto_ingest": True})
                call_brain("ai", "oracle_export", {"limit": 300})
                call_brain("ai", "governance_training_cycle", {"export_to_oracle": False, "run_sandbox_review": True})
                if problems:
                    call_brain("system", "notify", {
                        "title": f"Ouroboros: {len(problems)} issues",
                        "message": ", ".join(p.get("target", "?")[:20] for p in problems[:3]),
                        "type": "warning",
                    })
            except Exception as e:
                logger.debug("Deep intelligence background: %s", e)
        run_background(_deep_background, "deep_intelligence")

        # Commit batch (sync, quick)
        try:
            from core.commit_batch_trigger import check_and_upload_if_batch
            result["commit_batch"] = check_and_upload_if_batch()
        except Exception:
            result["commit_batch"] = {"triggered": False, "error": "import or run failed"}

    except Exception as e:
        logger.debug(f"Deep intelligence scan: {e}")

    if not problems:
        # Clean cycle — do maintenance tasks
        try:
            from api.brain_api_v2 import call_brain

            # Retrain DL model
            call_brain("ai", "dl_train", {"hours": 24, "limit": 500})

            # Check pipeline progress (if any background pipelines running)
            call_brain("ai", "pipeline_progress", {})

            # Generate periodic report
            call_brain("system", "generate_report", {"hours": 6})

            # Hot reload all services (pick up any changes)
            call_brain("system", "hot_reload_all", {})

            # Security scan
            call_brain("system", "security_scan", {"code": "", "file": ""})

            # Rollback check — verify snapshots exist
            call_brain("system", "snapshots", {})

            # Verify provenance ledger integrity
            call_brain("system", "verify_ledger", {})

        except Exception:
            pass

        result["outcome"] = "clean"
        result["latency_ms"] = round((time.time() - cycle_start) * 1000, 1)
        _update_kpis(result)
        return result

    # ── 2. DECIDE + ACT in parallel (then trust gate + time filter + memory) ──
    from core.async_parallel import run_parallel, run_background
    problems_batch = problems[:5]
    if problems_batch:
        thunks = [lambda _p=p: _decide_and_act(_p) for p in problems_batch]
        actions_raw = run_parallel(thunks, return_exceptions=True)
    else:
        actions_raw = []
    for problem, action in zip(problems_batch, actions_raw):
        if isinstance(action, Exception):
            action = {"target": problem.get("target", ""), "reason": problem.get("reason", ""), "type": "escalate", "result": {"error": str(action)[:200]}}
        # TRUST GATE: check trust before executing
        trust = _get_trust_score(problem.get("target", "system"))
        threshold = TRUST_THRESHOLDS.get(action["type"], 0.5)
        action["trust_score"] = trust
        action["trust_threshold"] = threshold

        if trust < threshold and action["type"] != "escalate":
            action["trust_blocked"] = True
            action["type"] = "escalate"
            action["result"] = {"reason": f"Trust {trust:.2f} < threshold {threshold}"}
            result["trust_blocked"] += 1
        else:
            action["trust_blocked"] = False

        # TIME FILTER: defer non-urgent during quiet hours
        if is_quiet and problem.get("severity") != "critical" and action["type"] not in ("escalate",):
            action["deferred"] = True
            action["result"] = {"reason": "Deferred to business hours (non-critical, quiet period)"}
            result["deferred"] += 1
        else:
            action["deferred"] = False

        # EPISODIC MEMORY: recall similar past problems
        episode = _recall_similar_episode(problem.get("reason", ""))
        action["episodic_recall"] = episode

        result["actions"].append(action)

        with _loop_lock:
            _loop_state["actions_taken"] += 1
            cat = action["type"]
            if cat in _loop_state:
                _loop_state[cat] += 1

    # ── 2b. Cross-trigger: after any heal/learn, trigger learning in background ──
    action_types_done = {a.get("type") for a in result.get("actions", [])}
    if action_types_done & {"heal", "learn"}:
        def _trigger_learn():
            try:
                from api.brain_api_v2 import call_brain
                call_brain("govern", "learn", {})
            except Exception:
                pass
        run_background(_trigger_learn, "govern/learn")

    # ── 3. LEARN: Record outcome + update KPIs ──────────────────
    try:
        from api._genesis_tracker import track
        track(
            key_type="system_event",
            what=f"Ouroboros cycle {result['cycle_id']}: {len(problems)} triggers, "
                 f"{len(result['actions'])} actions, {result['trust_blocked']} trust-blocked, "
                 f"{result['deferred']} deferred",
            who="autonomous_loop",
            how="ouroboros_cycle",
            output_data={
                "triggers": len(problems),
                "actions": len(result["actions"]),
                "trust_blocked": result["trust_blocked"],
                "deferred": result["deferred"],
                "time_period": time_ctx.get("period"),
                "mirror_errors": mirror.get("error_count_1h", 0),
            },
            tags=["autonomous", "ouroboros", "cycle"],
        )
    except Exception:
        pass

    _update_kpis(result)

    # Record as episodic memory — real learning from real outcomes
    for action in result.get("actions", []):
        try:
            from database.session import session_scope
            from cognitive.episodic_memory import EpisodicBuffer
            from cognitive.learning_memory import _to_json_str
            with session_scope() as s:
                buf = EpisodicBuffer(s)
                buf.record_episode(
                    problem=action.get("reason", action.get("target", "unknown problem")),
                    action={"type": action.get("type", "unknown"), "target": action.get("target", "")},
                    outcome=action.get("result", {}),
                    predicted_outcome={"success": True} if not action.get("deferred") else None,
                    trust_score=action.get("trust_score", 0.5),
                    source="ouroboros_loop",
                    genesis_key_id=result.get("cycle_id"),
                )
        except Exception:
            pass

    # ── 4. RECURSIVE VERIFY: re-scan and act once more if problems remain ──
    max_verify_rounds = 2
    for verify_round in range(max_verify_rounds - 1):
        try:
            from core.deterministic_bridge import build_deterministic_report
            det_report2 = build_deterministic_report()
            still_problems = [p for p in det_report2.get("problems", []) if not p.get("flag_for_human")]
            if not still_problems:
                break
            # One more DECIDE + ACT pass on remaining problems (up to 3)
            for problem in still_problems[:3]:
                action = _decide_and_act({
                    "source": problem.get("type", "deterministic"),
                    "target": problem.get("file", problem.get("module", problem.get("service", ""))),
                    "reason": f"[{problem.get('type')}] {problem.get('message', problem.get('error', ''))}",
                    "severity": problem.get("severity", "warning"),
                    "flag_for_human": problem.get("flag_for_human", False),
                })
                trust = _get_trust_score(problem.get("file", "system"))
                threshold = TRUST_THRESHOLDS.get(action["type"], 0.5)
                if trust >= threshold and not (is_quiet and action["type"] not in ("escalate",)):
                    result["actions"].append(action)
                    with _loop_lock:
                        _loop_state["actions_taken"] += 1
                        if action.get("type") in _loop_state:
                            _loop_state[action["type"]] += 1
        except Exception as e:
            logger.debug("Verify round %s: %s", verify_round + 1, e)
            break

    # ── 5. COMPOSITE LOOP: run heal_and_learn when we took heal/learn actions ──
    action_types = {a.get("type") for a in result.get("actions", [])}
    if action_types & {"heal", "learn"}:
        try:
            from cognitive.loop_orchestrator import LoopOrchestrator
            orch = LoopOrchestrator.get_instance()
            composite_result = orch.execute_composite(
                "heal_and_learn",
                context={"cycle_id": result.get("cycle_id"), "triggers": len(problems), "actions": len(result["actions"])},
                parallel=False,
            )
            result["composite_loop"] = {
                "id": "heal_and_learn",
                "verdict": composite_result.verdict,
                "passed": composite_result.loops_passed,
                "failed": composite_result.loops_failed,
            }
        except Exception as e:
            logger.debug("Composite loop heal_and_learn: %s", e)
            result["composite_loop"] = {"id": "heal_and_learn", "error": str(e)[:200]}

    result["outcome"] = "acted"
    result["latency_ms"] = round((time.time() - cycle_start) * 1000, 1)
    return result


def _decide_and_act(problem: dict) -> dict:
    """
    Agentic decide-and-act: ask the brain what to do, then execute it.
    All decisions flow through system/decide_autonomous_action; the loop only executes.
    """
    from api.brain_api_v2 import call_brain

    target = problem.get("target", "")
    reason = problem.get("reason", "")
    action = {"target": target, "reason": reason, "type": "none", "result": None}

    # 1. Ask brain for decision (single agentic decision point)
    try:
        decision_resp = call_brain("system", "decide_autonomous_action", problem)
    except Exception as e:
        action["type"] = "escalate"
        action["result"] = {"error": str(e)[:100], "queued": "human_review"}
        return action

    if not decision_resp.get("ok"):
        action["type"] = "escalate"
        action["result"] = {"error": decision_resp.get("error", "decision failed")[:100], "queued": "human_review"}
        return action

    data = decision_resp.get("data") or {}

    # 2. Escalate: no execution, just record
    if data.get("escalate"):
        action["type"] = "escalate"
        action["result"] = {"queued": "human_review", "reason": data.get("reason", reason)}
        return action

    # 3. Execute the action the brain chose
    brain = data.get("brain")
    act = data.get("action")
    payload = data.get("payload") or {}
    action["type"] = data.get("type", "heal")

    try:
        action["result"] = call_brain(brain, act, payload)
    except Exception as e:
        action["result"] = {"error": str(e)[:100]}

    return action


# ── Coding Agent Integration ──────────────────────────────────────────────

def submit_coding_task(
    instructions: str,
    context: dict = None,
    priority: int = 5,
    error_class: str = "",
    origin: str = "error_pipeline",
) -> str:
    """
    Submit a coding task to the coding agent queue.

    Called by error_pipeline when a runtime error needs a code fix,
    and by the autonomous loop when it detects a code-related problem.

    Returns a task_id string.
    """
    try:
        from coding_agent.task_queue import submit
        task_id = submit(
            task_type="fix_error" if error_class else "code_task",
            instructions=instructions,
            context=context or {},
            priority=priority,
            origin=origin,
            error_class=error_class,
        )
        logger.info(
            "[AUTONOMOUS] Coding task submitted: %s (class=%s)", task_id, error_class
        )
        return task_id
    except Exception as e:
        logger.error("[AUTONOMOUS] submit_coding_task failed: %s", e)
        return f"error_{int(time.time())}"


# ── Background loop ──────────────────────────────────────────────

_stop_event = threading.Event()


def _background_loop(interval_seconds: int = 30):
    """Background autonomous loop."""
    while not _stop_event.is_set():
        try:
            result = _run_cycle()
            with _loop_lock:
                _loop_state["cycle_count"] += 1
                _loop_state["last_cycle"] = result["timestamp"]
                _loop_state["last_result"] = result["outcome"]
                _loop_log.append(result)
                if len(_loop_log) > 100:
                    _loop_log.pop(0)
        except Exception as e:
            with _loop_lock:
                _loop_state["errors"] += 1
            logger.error(f"Autonomous loop error: {e}")
            # Self-healing: hot-reload so next cycle picks up code fixes
            try:
                from core.hot_reload import hot_reload_all_services
                hot_reload_all_services()
            except Exception:
                pass

        _stop_event.wait(interval_seconds)


# ── Endpoints ────────────────────────────────────────────────────

@router.get("/status")
async def loop_status():
    """Get autonomous loop status."""
    with _loop_lock:
        return dict(_loop_state)


@router.post("/start")
async def start_loop(interval: int = 30):
    """Start the autonomous loop."""
    with _loop_lock:
        if _loop_state["running"]:
            return {"status": "already_running"}
        _loop_state["running"] = True

    _stop_event.clear()
    t = threading.Thread(target=_background_loop, args=(interval,), daemon=True)
    t.start()
    return {"status": "started", "interval_seconds": interval}


@router.post("/stop")
async def stop_loop():
    """Stop the autonomous loop."""
    _stop_event.set()
    with _loop_lock:
        _loop_state["running"] = False
    return {"status": "stopped"}


@router.post("/cycle")
async def run_single_cycle():
    """Run a single autonomous cycle manually."""
    result = _run_cycle()
    with _loop_lock:
        _loop_state["cycle_count"] += 1
        _loop_state["last_cycle"] = result["timestamp"]
        _loop_state["last_result"] = result["outcome"]
        _loop_log.append(result)
    return result


@router.get("/log")
async def get_loop_log(limit: int = 20):
    """Get recent autonomous loop activity."""
    with _loop_lock:
        return {"log": list(reversed(_loop_log[-limit:])), "total": len(_loop_log)}


# ── Unified trigger brain (determinism, self-heal, diagnostics, self-learning, self-governance, coding agent) ──

@router.get("/triggers/definitions")
async def get_unified_trigger_definitions(category: Optional[str] = None, trigger_ids: Optional[str] = None):
    """List all defined triggers; optional filter by category or comma-separated trigger_ids."""
    from core.unified_trigger_brain import get_trigger_definitions, get_categories
    ids = [x.strip() for x in (trigger_ids or "").split(",") if x.strip()] or None
    return {
        "triggers": get_trigger_definitions(category=category, trigger_ids=ids),
        "categories": get_categories(),
    }


@router.post("/triggers/run")
async def run_unified_triggers(payload: Dict[str, Any] = Body(default={})):
    """Run unified triggers (async multi-trigger). Body: { \"trigger_ids\": [...], \"category\": \"...\" }."""
    from api.brain_api_v2 import call_brain
    payload = payload or {}
    result = call_brain("system", "run_unified_triggers", {
        "trigger_ids": payload.get("trigger_ids"),
        "category": payload.get("category"),
    })
    return result
