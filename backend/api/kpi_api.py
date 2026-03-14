import datetime
from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kpi", tags=["KPI Dashboard"])

_FALLBACK_COMPONENTS = [
    {"name": "coding_agent", "status": "no_data", "trust_score": 0.0, "total_actions": 0, "kpi_count": 0},
    {"name": "diagnostic_engine", "status": "no_data", "trust_score": 0.0, "total_actions": 0, "kpi_count": 0},
    {"name": "self_healing", "status": "no_data", "trust_score": 0.0, "total_actions": 0, "kpi_count": 0},
    {"name": "knowledge_retrieval", "status": "no_data", "trust_score": 0.0, "total_actions": 0, "kpi_count": 0},
    {"name": "genesis_tracker", "status": "no_data", "trust_score": 0.0, "total_actions": 0, "kpi_count": 0},
]


def _get_live_components():
    """Try to get live component data from the KPI tracker singleton."""
    try:
        from ml_intelligence.kpi_tracker import get_kpi_tracker
        tracker = get_kpi_tracker()
        if not tracker.components:
            return None
        health = tracker.get_system_health()
        components = []
        for name, signal in health.get("components", {}).items():
            components.append({
                "name": signal.get("component_name", name),
                "status": signal.get("status", "unknown"),
                "trust_score": signal.get("trust_score", 0.5),
                "total_actions": signal.get("total_actions", 0),
                "kpi_count": signal.get("kpi_count", 0),
            })
        return components if components else None
    except Exception:
        logger.warning("[KPI-API] Could not fetch live component data, using fallback")
        return None


@router.get("/health")
async def get_kpi_health():
    """Return top-level system health for the KPI dashboard."""
    trust = 0.0
    status = "awaiting_data"
    component_count = len(_FALLBACK_COMPONENTS)
    try:
        from ml_intelligence.kpi_tracker import get_kpi_tracker
        tracker = get_kpi_tracker()
        if tracker.components:
            health = tracker.get_system_health()
            trust = health.get("system_trust_score", trust)
            status = health.get("status", status)
            component_count = health.get("component_count", component_count)
    except Exception:
        logger.warning("[KPI-API] Could not fetch live health, using fallback")

    return {
        "system_trust_score": trust,
        "status": status,
        "component_count": component_count,
    }


@router.get("/dashboard")
async def get_kpi_dashboard():
    """Return dashboard aggregates for components."""
    components = _get_live_components() or _FALLBACK_COMPONENTS

    sorted_comps = sorted(components, key=lambda x: x["trust_score"], reverse=True)

    top_performers = [c["name"] for c in sorted_comps[:3] if c["trust_score"] >= 0.8]
    needs_attention = [c["name"] for c in sorted_comps if c["trust_score"] < 0.8]

    return {
        "top_performers": top_performers,
        "needs_attention": needs_attention,
        "components": components,
    }


@router.get("/components/{name}")
async def get_component_kpis(name: str):
    """Return specific detailed KPIs for a component."""
    # Try live tracker first
    try:
        from ml_intelligence.kpi_tracker import get_kpi_tracker
        tracker = get_kpi_tracker()
        comp = tracker.get_component_kpis(name)
        if comp is not None:
            data = comp.to_dict()
            return {
                "trust_score": data.get("trust_score", 0.5),
                "created_at": data.get("created_at", datetime.datetime.now(datetime.timezone.utc).isoformat()),
                "updated_at": data.get("updated_at", datetime.datetime.now(datetime.timezone.utc).isoformat()),
                "kpis": {
                    metric_name: {
                        "metric_name": metric_name,
                        "count": info.get("count", 0),
                        "value": info.get("value", 0.0),
                        "timestamp": info.get("timestamp", datetime.datetime.now(datetime.timezone.utc).isoformat()),
                    }
                    for metric_name, info in data.get("kpis", {}).items()
                },
            }
    except Exception:
        logger.debug(f"[KPI-API] Could not fetch live KPIs for {name}, using fallback")

    # Fallback to static data
    target_comp = next((c for c in _FALLBACK_COMPONENTS if c["name"] == name), None)

    if not target_comp:
        return {
            "trust_score": 0.0,
            "kpis": {},
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    return {
        "trust_score": 0.0,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kpis": {},
        "status": "no_data",
    }


@router.get("/trust-trends")
async def get_trust_trends():
    """Return trust score trends per component (from KPI tracker history)."""
    try:
        from ml_intelligence.kpi_tracker import get_kpi_tracker
        tracker = get_kpi_tracker()
        trends = {}
        for name, history in tracker.trust_history.items():
            trends[name] = history.to_dict()
        return {"trends": trends, "components": len(trends)}
    except Exception as e:
        logger.warning("[KPI-API] Could not fetch trust trends: %s", e)
        return {"trends": {}, "components": 0, "status": "unavailable"}


@router.get("/governance-summary")
async def get_governance_summary():
    """
    Governance dashboard: real-time KPI pass/fail, trust status, confidence.
    Aggregates data from KPI tracker and Trust Engine.
    """
    result = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "kpi": {"status": "awaiting_data", "system_trust": 0.0, "components": 0},
        "trust_engine": {"status": "awaiting_data", "system_trust": 0.0, "components": 0},
        "confidence": {"status": "awaiting_data"},
    }

    # KPI tracker data
    try:
        from ml_intelligence.kpi_tracker import get_kpi_tracker
        tracker = get_kpi_tracker()
        if tracker.components:
            health = tracker.get_system_health()
            result["kpi"] = {
                "status": health.get("status", "unknown"),
                "system_trust": round(health.get("system_trust_score", 0.0), 4),
                "components": health.get("component_count", 0),
                "component_health": {
                    name: {
                        "trust": sig.get("trust_score", 0.0),
                        "status": sig.get("status", "unknown"),
                        "actions": sig.get("total_actions", 0),
                    }
                    for name, sig in health.get("components", {}).items()
                },
            }
    except Exception as e:
        logger.warning("[KPI-API] Governance KPI fetch failed: %s", e)

    # Trust Engine data
    try:
        from cognitive.trust_engine import get_trust_engine
        te = get_trust_engine()
        system_trust = te.get_system_trust()
        result["trust_engine"] = {
            "status": "active" if system_trust.get("component_count", 0) > 0 else "awaiting_data",
            "system_trust": system_trust.get("system_trust", 0.0),
            "components": system_trust.get("component_count", 0),
            "needs_attention": system_trust.get("needs_attention", 0),
            "high_trust_count": system_trust.get("high_trust_count", 0),
            "low_trust_count": system_trust.get("low_trust_count", 0),
        }

        # Add confidence metrics
        try:
            confidence_data = {}
            for comp_id in system_trust.get("components", {}):
                conf = te.get_confidence(comp_id)
                confidence_data[comp_id] = conf
            result["confidence"] = {
                "status": "active" if confidence_data else "awaiting_data",
                "components": confidence_data,
            }
        except Exception as e:
            logger.debug("[KPI-API] Confidence metrics unavailable: %s", e)
    except Exception as e:
        logger.warning("[KPI-API] Governance trust engine fetch failed: %s", e)

    return result


@router.get("/pass-fail")
async def get_kpi_pass_fail():
    """Real-time KPI pass/fail status for all components."""
    try:
        from ml_intelligence.kpi_tracker import get_kpi_tracker
        tracker = get_kpi_tracker()
        results = {}
        for name, comp in tracker.components.items():
            trust = comp.get_trust_score()
            total = sum(kpi.count for kpi in comp.kpis.values())
            successes = comp.kpis.get("successes", None)
            failures = comp.kpis.get("failures", None)
            s_count = successes.count if successes else 0
            f_count = failures.count if failures else 0
            results[name] = {
                "trust_score": round(trust, 4),
                "total_actions": total,
                "successes": s_count,
                "failures": f_count,
                "pass_rate": round(s_count / max(s_count + f_count, 1), 4),
                "status": "passing" if trust >= 0.6 else "failing",
            }
        return {"components": results, "component_count": len(results)}
    except Exception as e:
        return {"components": {}, "component_count": 0, "error": str(e)}


@router.get("/confidence/{component_name}")
async def get_component_confidence(component_name: str):
    """Detailed confidence metrics for a specific component."""
    try:
        from cognitive.trust_engine import get_trust_engine
        te = get_trust_engine()
        conf = te.get_confidence(component_name)
        return {
            "component": component_name,
            **conf,
        }
    except Exception as e:
        return {"component": component_name, "confidence": 0.0, "error": str(e)}


@router.post("/snapshot")
async def take_trust_snapshot():
    """Trigger a trust snapshot for all components (normally called daily)."""
    try:
        from ml_intelligence.kpi_tracker import get_kpi_tracker
        tracker = get_kpi_tracker()
        results = tracker.take_daily_snapshot()
        return {"status": "snapshot_taken", "components": results}
    except Exception as e:
        return {"status": "error", "error": str(e)}
