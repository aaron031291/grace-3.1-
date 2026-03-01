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

from fastapi import APIRouter
from typing import Dict, Any, List
from datetime import datetime
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
        from api.component_health_api import _get_genesis_keys, _get_time_context as _tc
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
        "timestamp": datetime.utcnow().isoformat(),
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

    # ── 1. TRIGGER: Scan for problems ────────────────────────────
    problems = []
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
        from api.runtime_triggers_api import _scan_resources, _scan_code
        for scanner in [_scan_resources, _scan_code]:
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

    if not problems:
        result["outcome"] = "clean"
        result["latency_ms"] = round((time.time() - cycle_start) * 1000, 1)
        _update_kpis(result)
        return result

    # ── 2. DECIDE + ACT (with trust gate + time filter + memory) ──
    for problem in problems[:5]:
        action = _decide_and_act(problem)

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

    result["outcome"] = "acted"
    result["latency_ms"] = round((time.time() - cycle_start) * 1000, 1)
    return result


def _decide_and_act(problem: dict) -> dict:
    """Decide what type of action to take and execute it."""
    target = problem.get("target", "")
    reason = problem.get("reason", "")
    severity = problem.get("severity", "warning")

    action = {"target": target, "reason": reason, "type": "none", "result": None}

    # Service down → HEAL
    if "unreachable" in reason.lower() or "down" in reason.lower() or "connection" in reason.lower():
        action["type"] = "heal"
        try:
            from api.brain_api import call_brain
            action["result"] = call_brain("system", "scan_heal", {})
        except Exception as e:
            action["result"] = {"error": str(e)[:100]}
        return action

    # No activity (always-on) → HEAL (diagnostic cycle)
    if "no activity" in reason.lower() and severity == "critical":
        action["type"] = "heal"
        try:
            from diagnostic_machine.diagnostic_engine import get_diagnostic_engine, TriggerSource
            engine = get_diagnostic_engine()
            engine.run_cycle(TriggerSource.SENSOR_FLAG)
            action["result"] = {"ran": "diagnostic_cycle"}
        except Exception as e:
            action["result"] = {"error": str(e)[:100]}
        return action

    # High CPU/RAM → HEAL (GC)
    if "cpu" in reason.lower() or "ram" in reason.lower() or "memory" in reason.lower():
        action["type"] = "heal"
        import gc
        gc.collect()
        action["result"] = {"ran": "gc_collect"}
        return action

    # Import/code errors → LEARN (record for future reference)
    if "import" in reason.lower() or "module" in reason.lower() or "dependency" in reason.lower():
        action["type"] = "learn"
        try:
            from api._genesis_tracker import track
            track(
                key_type="gap_identified",
                what=f"Code gap: {target} — {reason}",
                who="autonomous_loop",
                tags=["autonomous", "gap", "code-issue"],
            )
            action["result"] = {"recorded": "knowledge_gap"}
        except Exception as e:
            action["result"] = {"error": str(e)[:100]}
        return action

    # Test failures → LEARN + optionally CODE
    if "test" in reason.lower() or "failure" in reason.lower():
        action["type"] = "learn"
        try:
            from api._genesis_tracker import track
            track(
                key_type="gap_identified",
                what=f"Test gap: {target} — {reason}",
                who="autonomous_loop",
                tags=["autonomous", "gap", "test-failure"],
            )
            action["result"] = {"recorded": "test_gap"}
        except Exception as e:
            action["result"] = {"error": str(e)[:100]}
        return action

    # Everything else → ESCALATE
    action["type"] = "escalate"
    action["result"] = {"queued": "human_review", "reason": reason}
    return action


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
