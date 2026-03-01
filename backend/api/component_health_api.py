"""
Component Health API — behavioral profiling, health map, timeline,
problems list, and auto-remediation via Genesis key time-series.

Every Grace component emits Genesis keys. This API aggregates them into:
  - Behavioral profiles (expected activity windows, anomaly detection)
  - Health map (green/yellow/orange/red per component)
  - Timeline view (drill-down into a component's history)
  - Problems list (all current issues, color-coded)
  - Remediation rules (auto-fix or suggest for approval)
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
import json
import logging
import threading
import time as _time

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/component-health", tags=["Component Health"])

# ── Component Registry ───────────────────────────────────────────────
# Maps logical component names to Genesis key patterns that identify them.

COMPONENT_REGISTRY = {
    "chat_engine": {
        "label": "Chat Engine",
        "key_types": ["ai_response", "user_input"],
        "tags": ["chat", "prompt"],
        "who_patterns": ["app.send_prompt", "app.chat"],
        "expected_interval_min": 60,
        "always_on": False,
        "dependencies": ["llm_orchestrator", "database", "retrieval"],
    },
    "llm_orchestrator": {
        "label": "LLM Orchestrator",
        "key_types": ["ai_response", "external_api_call"],
        "tags": ["llm", "ollama", "kimi", "opus"],
        "who_patterns": ["llm_orchestrator"],
        "expected_interval_min": 30,
        "always_on": True,
        "dependencies": ["ollama_service", "kimi_service", "opus_service"],
    },
    "consensus_engine": {
        "label": "Consensus Engine",
        "key_types": ["ai_response"],
        "tags": ["consensus", "roundtable"],
        "who_patterns": ["consensus_engine"],
        "expected_interval_min": None,
        "always_on": False,
        "dependencies": ["llm_orchestrator", "kimi_service", "opus_service"],
    },
    "retrieval": {
        "label": "RAG Retrieval",
        "key_types": ["ai_response"],
        "tags": ["rag", "retrieval", "search"],
        "who_patterns": ["retriever", "retrieve"],
        "expected_interval_min": 30,
        "always_on": False,
        "dependencies": ["qdrant_service", "embedding"],
    },
    "ingestion": {
        "label": "Document Ingestion",
        "key_types": ["file_ingestion", "file_op"],
        "tags": ["ingestion", "ingest"],
        "who_patterns": ["ingestion", "file_manager"],
        "expected_interval_min": None,
        "always_on": False,
        "dependencies": ["database", "qdrant_service", "embedding"],
    },
    "database": {
        "label": "Database",
        "key_types": ["database_change", "system_event"],
        "tags": ["database", "db", "sqlite"],
        "who_patterns": ["database", "session"],
        "expected_interval_min": 15,
        "always_on": True,
        "dependencies": [],
    },
    "genesis_tracker": {
        "label": "Genesis Tracking",
        "key_types": [],
        "tags": ["genesis"],
        "who_patterns": ["genesis", "tracker"],
        "expected_interval_min": 5,
        "always_on": True,
        "dependencies": ["database"],
    },
    "diagnostic_engine": {
        "label": "Diagnostic Engine",
        "key_types": ["system_event"],
        "tags": ["diagnostic", "heartbeat", "healing"],
        "who_patterns": ["diagnostic"],
        "expected_interval_min": 2,
        "always_on": True,
        "dependencies": [],
    },
    "self_healing": {
        "label": "Self-Healing",
        "key_types": ["system_event", "fix"],
        "tags": ["healing", "self-heal", "auto-fix"],
        "who_patterns": ["healing", "heal"],
        "expected_interval_min": None,
        "always_on": False,
        "dependencies": ["diagnostic_engine", "genesis_tracker"],
    },
    "continuous_learning": {
        "label": "Continuous Learning",
        "key_types": ["learning_complete", "practice_outcome"],
        "tags": ["learning", "continuous-learning", "training"],
        "who_patterns": ["learning", "training"],
        "expected_interval_min": None,
        "always_on": False,
        "dependencies": ["database", "qdrant_service"],
    },
    "file_watcher": {
        "label": "File Watcher",
        "key_types": ["file_op", "code_change"],
        "tags": ["file-watcher", "watcher"],
        "who_patterns": ["file_watcher", "watcher"],
        "expected_interval_min": None,
        "always_on": True,
        "dependencies": ["genesis_tracker"],
    },
    "ollama_service": {
        "label": "Ollama (Local LLM)",
        "key_types": [],
        "tags": ["ollama"],
        "who_patterns": ["ollama"],
        "expected_interval_min": None,
        "always_on": True,
        "dependencies": [],
        "health_check_url": "http://localhost:11434/api/tags",
    },
    "qdrant_service": {
        "label": "Qdrant (Vector DB)",
        "key_types": [],
        "tags": ["qdrant"],
        "who_patterns": ["qdrant"],
        "expected_interval_min": None,
        "always_on": True,
        "dependencies": [],
        "health_check_url": "http://localhost:6333/collections",
    },
    "kimi_service": {
        "label": "Kimi K2.5",
        "key_types": ["external_api_call"],
        "tags": ["kimi"],
        "who_patterns": ["kimi"],
        "expected_interval_min": None,
        "always_on": False,
        "dependencies": [],
    },
    "opus_service": {
        "label": "Opus 4.6",
        "key_types": ["external_api_call"],
        "tags": ["opus"],
        "who_patterns": ["opus"],
        "expected_interval_min": None,
        "always_on": False,
        "dependencies": [],
    },
    "embedding": {
        "label": "Embedding Model",
        "key_types": [],
        "tags": ["embedding"],
        "who_patterns": ["embedding"],
        "expected_interval_min": None,
        "always_on": True,
        "dependencies": [],
    },
}

# ── Remediation rules ────────────────────────────────────────────────

REMEDIATION_RULES = [
    {
        "id": "restart_on_silence",
        "description": "If always-on service has no activity for 1 hour, suggest restart",
        "condition": "always_on AND no_activity_minutes > 60",
        "action": "suggest_restart",
        "auto_execute": False,
        "severity": "warning",
    },
    {
        "id": "heal_on_errors",
        "description": "If error rate > 30% in last 15 min, trigger healing",
        "condition": "error_rate > 0.3 AND window_minutes = 15",
        "action": "trigger_healing",
        "auto_execute": True,
        "severity": "critical",
    },
    {
        "id": "alert_degradation",
        "description": "If response latency 2x baseline, alert degradation",
        "condition": "avg_latency > 2 * baseline_latency",
        "action": "alert",
        "auto_execute": False,
        "severity": "warning",
    },
    {
        "id": "gc_on_high_memory",
        "description": "If memory > 85%, run GC",
        "condition": "memory_percent > 85",
        "action": "gc_collect",
        "auto_execute": True,
        "severity": "warning",
    },
]

# ── Approval queue ───────────────────────────────────────────────────

_approval_queue: List[dict] = []
_approval_lock = threading.Lock()


# ── Core logic ───────────────────────────────────────────────────────

def _get_genesis_keys(minutes: int = 60, component_id: str = None,
                      limit: int = 500) -> List[dict]:
    """Query Genesis keys from the database."""
    try:
        from database.session import session_scope
        from models.genesis_key_models import GenesisKey
        since = datetime.utcnow() - timedelta(minutes=minutes)

        with session_scope() as session:
            q = session.query(GenesisKey).filter(
                GenesisKey.when_timestamp >= since
            ).order_by(GenesisKey.when_timestamp.desc())

            if component_id and component_id in COMPONENT_REGISTRY:
                comp = COMPONENT_REGISTRY[component_id]
                from sqlalchemy import or_
                filters = []
                for tag in comp.get("tags", []):
                    filters.append(GenesisKey.tags.like(f'%"{tag}"%'))
                for who in comp.get("who_patterns", []):
                    filters.append(GenesisKey.who_actor.like(f'%{who}%'))
                if filters:
                    q = q.filter(or_(*filters))

            keys = q.limit(limit).all()
            return [
                {
                    "key_id": k.key_id,
                    "key_type": k.key_type.value if hasattr(k.key_type, 'value') else str(k.key_type),
                    "what": k.what_description,
                    "who": k.who_actor,
                    "when": k.when_timestamp.isoformat() if k.when_timestamp else None,
                    "where": k.where_location,
                    "why": k.why_reason,
                    "how": k.how_method,
                    "is_error": k.is_error,
                    "error_type": k.error_type,
                    "error_message": k.error_message,
                    "tags": json.loads(k.tags) if isinstance(k.tags, str) else (k.tags or []),
                    "file_path": k.file_path,
                    "has_fix": k.has_fix_suggestion,
                    "fix_applied": k.fix_applied,
                }
                for k in keys
            ]
    except Exception as e:
        logger.warning("Could not query genesis keys: %s", e)
        return []


def _get_time_context() -> dict:
    """Get temporal context for health classification."""
    try:
        from cognitive.time_sense import TimeSense
        return TimeSense.get_context()
    except Exception:
        return {}


def _publish_health_change(component_id: str, old_status: str, new_status: str, reason: str):
    """Publish health changes to the event bus for system-wide awareness."""
    try:
        from cognitive.event_bus import publish_async
        publish_async("system.health_changed", {
            "component": component_id,
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason,
        }, source="component_health")
    except Exception:
        pass


_last_known_status: Dict[str, str] = {}


def _classify_component(comp_id: str, comp: dict, keys: List[dict],
                        service_health: dict) -> dict:
    """Classify a component's health status."""
    now = datetime.utcnow()
    comp_keys = []
    for k in keys:
        tags = k.get("tags", [])
        who = (k.get("who") or "").lower()
        matched = False
        for tag in comp.get("tags", []):
            if tag in tags:
                matched = True
                break
        if not matched:
            for pat in comp.get("who_patterns", []):
                if pat in who:
                    matched = True
                    break
        if matched:
            comp_keys.append(k)

    total = len(comp_keys)
    errors = sum(1 for k in comp_keys if k.get("is_error"))
    error_rate = errors / total if total > 0 else 0

    last_seen = None
    if comp_keys:
        last_seen = comp_keys[0].get("when")

    minutes_since = None
    if last_seen:
        try:
            dt = datetime.fromisoformat(last_seen)
            minutes_since = (now - dt).total_seconds() / 60
        except Exception:
            pass

    # Check service health URL
    url_healthy = None
    if "health_check_url" in comp:
        url_healthy = service_health.get(comp_id, None)

    # Classify
    status = "green"
    reason = "Healthy"

    if url_healthy is False:
        status = "red"
        reason = "Service unreachable"
    elif error_rate > 0.5 and total >= 3:
        status = "red"
        reason = f"High error rate: {error_rate:.0%} ({errors}/{total})"
    elif error_rate > 0.2 and total >= 3:
        status = "orange"
        reason = f"Elevated errors: {error_rate:.0%}"
    elif comp.get("always_on") and minutes_since is not None and minutes_since > 60:
        status = "orange"
        reason = f"No activity for {minutes_since:.0f} min (always-on)"
    elif comp.get("always_on") and total == 0:
        status = "orange"
        reason = "No activity in window (always-on)"
    elif comp.get("expected_interval_min") and minutes_since:
        expected = comp["expected_interval_min"]
        if minutes_since > expected * 3:
            status = "orange"
            reason = f"Silent for {minutes_since:.0f} min (expected every {expected} min)"
        elif minutes_since > expected * 1.5:
            status = "yellow"
            reason = f"Idle {minutes_since:.0f} min"
    elif total == 0 and not comp.get("always_on"):
        status = "yellow"
        reason = "Idle (expected)"

    # Publish health change to event bus if status changed
    prev = _last_known_status.get(comp_id)
    if prev and prev != status:
        _publish_health_change(comp_id, prev, status, reason)
    _last_known_status[comp_id] = status

    return {
        "id": comp_id,
        "label": comp.get("label", comp_id),
        "status": status,
        "reason": reason,
        "total_events": total,
        "errors": errors,
        "error_rate": round(error_rate, 3),
        "last_seen": last_seen,
        "minutes_since": round(minutes_since, 1) if minutes_since else None,
        "always_on": comp.get("always_on", False),
        "dependencies": comp.get("dependencies", []),
    }


def _check_service_health() -> dict:
    """Check health URLs for services that expose them."""
    import urllib.request
    results = {}
    for comp_id, comp in COMPONENT_REGISTRY.items():
        url = comp.get("health_check_url")
        if not url:
            continue
        try:
            req = urllib.request.Request(url, method="GET")
            urllib.request.urlopen(req, timeout=2)
            results[comp_id] = True
        except Exception:
            results[comp_id] = False
    return results


def _evaluate_remediation(components: List[dict]) -> List[dict]:
    """Check remediation rules against component states."""
    actions = []
    for comp in components:
        if comp["status"] == "red":
            actions.append({
                "component": comp["id"],
                "label": comp["label"],
                "rule": "heal_on_errors" if comp["errors"] > 0 else "restart_on_silence",
                "severity": "critical",
                "reason": comp["reason"],
                "action": "trigger_healing",
                "auto_execute": comp["errors"] > 0,
                "status": "pending",
            })
        elif comp["status"] == "orange" and comp.get("always_on"):
            actions.append({
                "component": comp["id"],
                "label": comp["label"],
                "rule": "restart_on_silence",
                "severity": "warning",
                "reason": comp["reason"],
                "action": "suggest_restart",
                "auto_execute": False,
                "status": "pending_approval",
            })
    return actions


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/map")
async def health_map(window_minutes: int = Query(60, ge=5, le=1440)):
    """
    Component health map — color-coded status for every component.
    Green = healthy, Yellow = idle, Orange = degrading, Red = broken.
    """
    keys = _get_genesis_keys(minutes=window_minutes, limit=2000)
    service_health = _check_service_health()

    components = []
    for comp_id, comp in COMPONENT_REGISTRY.items():
        classified = _classify_component(comp_id, comp, keys, service_health)
        components.append(classified)

    status_counts = defaultdict(int)
    for c in components:
        status_counts[c["status"]] += 1

    problems = [c for c in components if c["status"] in ("red", "orange")]
    remediation = _evaluate_remediation(components)

    # Auto-execute safe remediations
    for action in remediation:
        if action.get("auto_execute"):
            try:
                _auto_execute_remediation(action)
                action["status"] = "auto_executed"
            except Exception as e:
                action["status"] = f"failed: {e}"
        elif action.get("status") == "pending_approval":
            with _approval_lock:
                _approval_queue.append({
                    **action,
                    "queued_at": datetime.utcnow().isoformat(),
                })

    time_ctx = _get_time_context()

    return {
        "components": components,
        "summary": dict(status_counts),
        "total": len(components),
        "problems": problems,
        "remediation": remediation,
        "window_minutes": window_minutes,
        "generated_at": datetime.utcnow().isoformat(),
        "time_context": {
            "period": time_ctx.get("period", "unknown"),
            "is_business_hours": time_ctx.get("is_business_hours", False),
            "day_of_week": time_ctx.get("day_of_week", "unknown"),
        },
    }


@router.get("/timeline/{component_id}")
async def component_timeline(
    component_id: str,
    window_minutes: int = Query(60, ge=5, le=10080),
    limit: int = Query(200, ge=10, le=1000),
):
    """
    Timeline view for a single component — Genesis key activity,
    gaps, errors, latency spikes, metadata.
    """
    if component_id not in COMPONENT_REGISTRY:
        raise HTTPException(404, f"Unknown component: {component_id}")

    comp = COMPONENT_REGISTRY[component_id]
    keys = _get_genesis_keys(minutes=window_minutes, component_id=component_id, limit=limit)

    gaps = []
    prev_time = None
    for k in reversed(keys):
        if k.get("when") and prev_time:
            try:
                dt = datetime.fromisoformat(k["when"])
                gap_min = (dt - prev_time).total_seconds() / 60
                expected = comp.get("expected_interval_min")
                if expected and gap_min > expected * 2:
                    gaps.append({
                        "start": prev_time.isoformat(),
                        "end": k["when"],
                        "gap_minutes": round(gap_min, 1),
                        "expected_minutes": expected,
                    })
                prev_time = dt
            except Exception:
                pass
        elif k.get("when"):
            try:
                prev_time = datetime.fromisoformat(k["when"])
            except Exception:
                pass

    errors = [k for k in keys if k.get("is_error")]
    deps = comp.get("dependencies", [])

    return {
        "component_id": component_id,
        "label": comp.get("label"),
        "always_on": comp.get("always_on", False),
        "expected_interval_min": comp.get("expected_interval_min"),
        "dependencies": deps,
        "events": keys,
        "total_events": len(keys),
        "errors": errors,
        "error_count": len(errors),
        "gaps": gaps,
        "window_minutes": window_minutes,
    }


@router.get("/problems")
async def problems_list():
    """
    All current problems — color-coded, with diagnosis and remediation.
    """
    keys = _get_genesis_keys(minutes=60, limit=2000)
    service_health = _check_service_health()

    problems = []
    for comp_id, comp in COMPONENT_REGISTRY.items():
        classified = _classify_component(comp_id, comp, keys, service_health)
        if classified["status"] in ("red", "orange"):
            problems.append(classified)

    problems.sort(key=lambda p: {"red": 0, "orange": 1}.get(p["status"], 2))

    remediation = _evaluate_remediation(problems)

    return {
        "problems": problems,
        "total": len(problems),
        "critical": sum(1 for p in problems if p["status"] == "red"),
        "degrading": sum(1 for p in problems if p["status"] == "orange"),
        "remediation": remediation,
        "checked_at": datetime.utcnow().isoformat(),
    }


@router.get("/dependencies/{component_id}")
async def dependency_graph(component_id: str):
    """Upstream and downstream dependencies for a component."""
    if component_id not in COMPONENT_REGISTRY:
        raise HTTPException(404, f"Unknown component: {component_id}")

    comp = COMPONENT_REGISTRY[component_id]
    upstream = comp.get("dependencies", [])

    downstream = []
    for cid, c in COMPONENT_REGISTRY.items():
        if component_id in c.get("dependencies", []):
            downstream.append(cid)

    return {
        "component_id": component_id,
        "label": comp.get("label"),
        "upstream": [
            {"id": u, "label": COMPONENT_REGISTRY.get(u, {}).get("label", u)}
            for u in upstream
        ],
        "downstream": [
            {"id": d, "label": COMPONENT_REGISTRY.get(d, {}).get("label", d)}
            for d in downstream
        ],
    }


@router.get("/approvals")
async def get_approvals():
    """Get pending remediation approvals."""
    with _approval_lock:
        return {"approvals": list(_approval_queue), "total": len(_approval_queue)}


@router.post("/approvals/{index}/approve")
async def approve_remediation(index: int):
    """Approve a pending remediation action."""
    with _approval_lock:
        if index < 0 or index >= len(_approval_queue):
            raise HTTPException(404, "Approval not found")
        action = _approval_queue.pop(index)

    try:
        _auto_execute_remediation(action)
        action["status"] = "approved_and_executed"
    except Exception as e:
        action["status"] = f"approved_but_failed: {e}"

    return action


@router.post("/approvals/{index}/reject")
async def reject_remediation(index: int):
    """Reject a pending remediation action."""
    with _approval_lock:
        if index < 0 or index >= len(_approval_queue):
            raise HTTPException(404, "Approval not found")
        action = _approval_queue.pop(index)
        action["status"] = "rejected"
    return action


@router.get("/rules")
async def get_remediation_rules():
    """Get all remediation rules."""
    return {"rules": REMEDIATION_RULES}


@router.get("/registry")
async def get_component_registry():
    """Get the full component registry with expected behaviors."""
    return {
        "components": {
            cid: {
                "label": c.get("label"),
                "always_on": c.get("always_on", False),
                "expected_interval_min": c.get("expected_interval_min"),
                "dependencies": c.get("dependencies", []),
                "tags": c.get("tags", []),
            }
            for cid, c in COMPONENT_REGISTRY.items()
        },
        "total": len(COMPONENT_REGISTRY),
    }


@router.get("/mirror-feed")
async def mirror_feed():
    """
    Data feed for the Mirror Self-Model — component health patterns
    suitable for self-reflection and anomaly observation.
    """
    keys = _get_genesis_keys(minutes=60, limit=2000)
    service_health = _check_service_health()

    components = []
    for comp_id, comp in COMPONENT_REGISTRY.items():
        classified = _classify_component(comp_id, comp, keys, service_health)
        components.append(classified)

    time_ctx = _get_time_context()
    problems = [c for c in components if c["status"] in ("red", "orange")]

    # Activity patterns for the mirror
    try:
        from cognitive.time_sense import TimeSense
        timestamps = [k["when"] for k in keys if k.get("when")]
        activity = TimeSense.activity_patterns(timestamps) if timestamps else {}
    except Exception:
        activity = {}

    return {
        "component_statuses": {c["id"]: c["status"] for c in components},
        "problems": [{"id": p["id"], "status": p["status"], "reason": p["reason"]} for p in problems],
        "total_events_1h": len(keys),
        "error_count_1h": sum(1 for k in keys if k.get("is_error")),
        "activity_patterns": activity,
        "time_context": time_ctx,
        "observation": (
            f"{len(problems)} components degraded/broken out of {len(components)} total. "
            f"Period: {time_ctx.get('period', '?')}. "
            f"Events in last hour: {len(keys)}."
        ),
    }


def _auto_execute_remediation(action: dict):
    """Execute a remediation action."""
    act = action.get("action", "")
    comp = action.get("component", "")

    if act == "trigger_healing":
        try:
            from diagnostic_machine.diagnostic_engine import get_diagnostic_engine, TriggerSource
            engine = get_diagnostic_engine()
            engine.run_cycle(TriggerSource.SENSOR_FLAG)
        except Exception:
            import gc
            gc.collect()
    elif act == "gc_collect":
        import gc
        gc.collect()
    elif act == "suggest_restart":
        logger.warning("Restart suggested for %s — requires manual action", comp)
    else:
        logger.info("No auto-execution for action: %s", act)

    try:
        from api._genesis_tracker import track
        track(
            key_type="system_event",
            what=f"Auto-remediation: {act} for {comp}",
            who="component_health_api",
            why=action.get("reason", ""),
            tags=["remediation", "auto-heal", comp],
        )
    except Exception:
        pass
