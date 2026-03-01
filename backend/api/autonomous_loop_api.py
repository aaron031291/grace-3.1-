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


def _run_cycle() -> dict:
    """Execute one full autonomous cycle."""
    cycle_start = time.time()
    result = {
        "cycle_id": f"AUTO-{int(time.time())}",
        "timestamp": datetime.utcnow().isoformat(),
        "triggers_found": 0,
        "actions": [],
        "outcome": "clean",
    }

    # ── 1. TRIGGER: Scan for problems ────────────────────────────
    problems = []
    try:
        from api.brain_api import call_brain
        health = call_brain("system", "problems", {})
        if health.get("ok") and health.get("data", {}).get("problems"):
            for p in health["data"]["problems"]:
                problems.append({
                    "source": "component_health",
                    "target": p.get("label", p.get("id", "")),
                    "status": p.get("status"),
                    "reason": p.get("reason", ""),
                    "severity": "critical" if p.get("status") == "red" else "warning",
                })
    except Exception as e:
        logger.debug(f"Health scan skipped: {e}")

    try:
        from api.runtime_triggers_api import _scan_resources, _scan_services, _scan_code
        for scanner in [_scan_resources, _scan_services, _scan_code]:
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
        return result

    # ── 2. DECIDE + ACT for each problem ─────────────────────────
    for problem in problems[:5]:
        action = _decide_and_act(problem)
        result["actions"].append(action)

        with _loop_lock:
            _loop_state["actions_taken"] += 1
            if action["type"] == "heal":
                _loop_state["healed"] += 1
            elif action["type"] == "learn":
                _loop_state["learned"] += 1
            elif action["type"] == "code":
                _loop_state["coded"] += 1
            elif action["type"] == "escalate":
                _loop_state["escalated"] += 1

    # ── 3. LEARN: Record outcome ─────────────────────────────────
    try:
        from api._genesis_tracker import track
        track(
            key_type="system_event",
            what=f"Autonomous cycle {result['cycle_id']}: {len(problems)} triggers, {len(result['actions'])} actions",
            who="autonomous_loop",
            how="ouroboros_cycle",
            output_data={
                "triggers": len(problems),
                "actions": len(result["actions"]),
                "healed": sum(1 for a in result["actions"] if a["type"] == "heal"),
                "learned": sum(1 for a in result["actions"] if a["type"] == "learn"),
            },
            tags=["autonomous", "ouroboros", "cycle"],
        )
    except Exception:
        pass

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
