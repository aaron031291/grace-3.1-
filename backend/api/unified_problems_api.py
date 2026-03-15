"""
Unified Problems API — Single Source of Truth for All System Problems.

Aggregates alerts from:
  1. Blackbox Scanner (57 detectors)
  2. Component Health (Genesis-key-based component status)
  3. Diagnostic Machine (4-layer diagnostic engine)
  4. Validation & Trust (KPI failures, trust drops)
  5. Cognitive Decorator Events (invariant violations, confidence drops)
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import asyncio
import logging
import json

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/problems", tags=["Unified Problems"])


# ── Pydantic Models (Single Source of Truth) ─────────────────────

class UnifiedAlert(BaseModel):
    """One problem from any source, normalized to a common shape."""
    source: str = Field(..., description="Origin: blackbox, component_health, diagnostic, validation, cognitive")
    severity: str = Field("info", description="critical, warning, info")
    category: str = Field("general", description="Problem category")
    title: str = Field(..., description="Short problem title")
    description: str = Field("", description="Detailed description")
    component: Optional[str] = Field(None, description="Affected component ID")
    file: Optional[str] = Field(None, description="Affected file path")
    line: Optional[int] = Field(None, description="Line number in file")
    fix_suggestion: Optional[str] = Field(None, description="Suggested fix")
    occurrences: int = Field(1, description="Times seen")
    first_seen: Optional[str] = Field(None, description="ISO timestamp of first detection")
    last_seen: Optional[str] = Field(None, description="ISO timestamp of latest detection")
    auto_healable: bool = Field(False, description="Whether auto-remediation is available")
    remediation_action: Optional[str] = Field(None, description="Remediation action type")


class UnifiedProblemsReport(BaseModel):
    """Complete aggregated problems report."""
    total_issues: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    sources_queried: List[str] = []
    sources_failed: List[str] = []
    alerts: List[UnifiedAlert] = []
    component_summary: Dict[str, str] = Field(default_factory=dict, description="component_id -> status color")
    scan_duration_ms: float = 0.0
    generated_at: str = ""


class UnifiedProblemsResponse(BaseModel):
    ok: bool = True
    report: Optional[UnifiedProblemsReport] = None
    recent_actions: List[Dict[str, Any]] = []
    error: Optional[str] = None


# ── Collectors ───────────────────────────────────────────────────

def _collect_blackbox_alerts() -> List[UnifiedAlert]:
    """Collect alerts from the 57-detector blackbox scanner."""
    alerts = []
    try:
        from cognitive.spindle_blackbox_scanner import get_blackbox_scanner
        scanner = get_blackbox_scanner()
        report = scanner.get_latest_report()
        if report is None:
            return []
        for a in report.alerts:
            alerts.append(UnifiedAlert(
                source="blackbox",
                severity=a.severity,
                category=a.category,
                title=a.title,
                description=a.description,
                file=a.file,
                line=a.line,
                fix_suggestion=a.fix_suggestion,
                occurrences=a.occurrences,
                first_seen=a.first_seen.isoformat() if a.first_seen else None,
                last_seen=a.last_seen.isoformat() if a.last_seen else None,
            ))
    except Exception as e:
        logger.warning("Blackbox collector failed: %s", e)
    return alerts


def _collect_component_health_alerts() -> tuple:
    """Collect degraded/broken component alerts and summary map."""
    alerts = []
    summary = {}
    try:
        from api.component_health_api import (
            COMPONENT_REGISTRY, _get_genesis_keys, _classify_component,
            _check_service_health, _evaluate_remediation,
        )
        keys = _get_genesis_keys(minutes=60, limit=2000)
        service_health = _check_service_health()

        for comp_id, comp in COMPONENT_REGISTRY.items():
            classified = _classify_component(comp_id, comp, keys, service_health)
            summary[comp_id] = classified["status"]

            if classified["status"] in ("red", "orange"):
                sev = "critical" if classified["status"] == "red" else "warning"
                alerts.append(UnifiedAlert(
                    source="component_health",
                    severity=sev,
                    category="component_degradation",
                    title=f"{classified['label']} — {classified['reason']}",
                    description=f"Error rate: {classified['error_rate']:.1%}, events: {classified['total_events']}, errors: {classified['errors']}",
                    component=comp_id,
                    last_seen=classified.get("last_seen"),
                    auto_healable=classified["status"] == "red" and classified["errors"] > 0,
                    remediation_action="trigger_healing" if classified["status"] == "red" else "suggest_restart",
                ))

        # Also pull remediation queue
        remediation = _evaluate_remediation([c for c in [
            _classify_component(cid, comp, keys, service_health)
            for cid, comp in COMPONENT_REGISTRY.items()
        ] if c["status"] in ("red", "orange")])

        for r in remediation:
            if r.get("auto_execute") and r.get("status") != "auto_executed":
                for a in alerts:
                    if a.component == r["component"]:
                        a.auto_healable = True
                        a.remediation_action = r["action"]

    except Exception as e:
        logger.warning("Component health collector failed: %s", e)
    return alerts, summary


def _collect_diagnostic_alerts() -> List[UnifiedAlert]:
    """Collect alerts from the 4-layer Diagnostic Machine."""
    alerts = []
    try:
        from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
        engine = get_diagnostic_engine(enable_heartbeat=False, enable_healing=False)
        summary = engine.get_health_summary()

        for comp in summary.get("degraded_components", []):
            alerts.append(UnifiedAlert(
                source="diagnostic",
                severity="warning",
                category="diagnostic_degraded",
                title=f"Degraded: {comp}",
                description=f"Diagnostic Machine flagged {comp} as degraded",
                component=comp,
            ))

        for comp in summary.get("critical_components", []):
            alerts.append(UnifiedAlert(
                source="diagnostic",
                severity="critical",
                category="diagnostic_critical",
                title=f"Critical: {comp}",
                description=f"Diagnostic Machine flagged {comp} as critical",
                component=comp,
            ))

        score = summary.get("health_score", 1.0)
        if score < 0.5:
            alerts.append(UnifiedAlert(
                source="diagnostic",
                severity="critical",
                category="system_health",
                title=f"System health score critically low: {score:.2f}",
                description=f"Overall health: {summary.get('status', 'unknown')}, AVM level: {summary.get('avm_level', 'unknown')}",
            ))
        elif score < 0.75:
            alerts.append(UnifiedAlert(
                source="diagnostic",
                severity="warning",
                category="system_health",
                title=f"System health score degraded: {score:.2f}",
                description=f"Overall health: {summary.get('status', 'unknown')}, recommended: {summary.get('recommended_action', 'none')}",
            ))
    except Exception as e:
        logger.warning("Diagnostic collector failed: %s", e)
    return alerts


def _collect_validation_alerts() -> List[UnifiedAlert]:
    """Collect trust/KPI failures from the Validation API."""
    alerts = []
    try:
        from ml_intelligence.kpi_tracker import get_kpi_tracker
        tracker = get_kpi_tracker()
        if not tracker:
            return []

        components = [
            "coding_agent.verification", "verification_pass",
            "brain_code", "brain_ai", "brain_system",
            "brain_learn", "brain_memory", "error_pipeline",
        ]

        for comp in components:
            try:
                trust = tracker.get_component_trust_score(comp)
                kpis = tracker.get_component_kpis(comp)
                if trust is not None and trust < 0.5:
                    failures = kpis.get_kpi("failures").count if kpis else 0
                    alerts.append(UnifiedAlert(
                        source="validation",
                        severity="critical" if trust < 0.3 else "warning",
                        category="trust_degradation",
                        title=f"Low trust: {comp} ({trust:.2f})",
                        description=f"Trust score dropped below threshold. Failures: {failures}",
                        component=comp,
                    ))
            except Exception:
                pass
    except Exception as e:
        logger.warning("Validation collector failed: %s", e)
    return alerts


def _collect_cognitive_alerts() -> List[UnifiedAlert]:
    """Collect invariant violations and confidence drops from cognitive decorators."""
    alerts = []
    try:
        from cognitive.event_bus import get_recent_events
        events = get_recent_events(limit=200)
        for evt in events:
            topic = getattr(evt, "topic", "") if hasattr(evt, "topic") else evt.get("topic", "")
            data = getattr(evt, "data", {}) if hasattr(evt, "data") else evt.get("data", {})

            if "invariant" in topic and "violation" in topic:
                alerts.append(UnifiedAlert(
                    source="cognitive",
                    severity="critical",
                    category="invariant_violation",
                    title=data.get("title", f"Invariant violation: {topic}"),
                    description=data.get("description", str(data)),
                    component=data.get("component"),
                ))
            elif "confidence" in topic and "drop" in topic:
                alerts.append(UnifiedAlert(
                    source="cognitive",
                    severity="warning",
                    category="confidence_drop",
                    title=data.get("title", f"Confidence drop: {topic}"),
                    description=data.get("description", str(data)),
                    component=data.get("component"),
                ))
            elif "health_changed" in topic:
                new_status = data.get("new_status", "")
                if new_status in ("red", "orange", "critical", "degraded"):
                    alerts.append(UnifiedAlert(
                        source="cognitive",
                        severity="critical" if new_status in ("red", "critical") else "warning",
                        category="health_change",
                        title=f"{data.get('component', 'Unknown')} status → {new_status}",
                        description=data.get("reason", ""),
                        component=data.get("component"),
                    ))
    except Exception as e:
        logger.warning("Cognitive collector failed: %s", e)
    return alerts


def _collect_recent_actions() -> List[Dict[str, Any]]:
    """Collect recent autonomous actions from spindle projection."""
    try:
        from cognitive.spindle_problems_projection import get_problems_projection
        projection = get_problems_projection()
        summary = projection.get_problems_summary()
        return summary.get("recent_actions", [])
    except Exception:
        return []


# ── Main Endpoint ────────────────────────────────────────────────

@router.get("/unified", response_model=UnifiedProblemsResponse)
async def get_unified_problems():
    """
    Single source of truth for ALL system problems.
    Aggregates: blackbox scanner, component health, diagnostic machine,
    validation/trust, and cognitive decorator events.
    """
    import time
    t0 = time.time()

    all_alerts: List[UnifiedAlert] = []
    sources_queried = []
    sources_failed = []
    component_summary = {}

    # Run all collectors
    collectors = {
        "blackbox": lambda: (_collect_blackbox_alerts(), None),
        "component_health": lambda: _collect_component_health_alerts(),
        "diagnostic": lambda: (_collect_diagnostic_alerts(), None),
        "validation": lambda: (_collect_validation_alerts(), None),
        "cognitive": lambda: (_collect_cognitive_alerts(), None),
    }

    for source_name, collector in collectors.items():
        try:
            result = collector()
            if source_name == "component_health":
                alerts, summary = result
                component_summary = summary or {}
            else:
                alerts, _ = result
            all_alerts.extend(alerts)
            sources_queried.append(source_name)
        except Exception as e:
            logger.error("Unified collector %s failed: %s", source_name, e)
            sources_failed.append(source_name)

    # Sort: critical first, then warning, then info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    all_alerts.sort(key=lambda a: severity_order.get(a.severity, 3))

    elapsed_ms = (time.time() - t0) * 1000

    report = UnifiedProblemsReport(
        total_issues=len(all_alerts),
        critical_count=sum(1 for a in all_alerts if a.severity == "critical"),
        warning_count=sum(1 for a in all_alerts if a.severity == "warning"),
        info_count=sum(1 for a in all_alerts if a.severity == "info"),
        sources_queried=sources_queried,
        sources_failed=sources_failed,
        alerts=all_alerts,
        component_summary=component_summary,
        scan_duration_ms=round(elapsed_ms, 2),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    recent_actions = _collect_recent_actions()

    return UnifiedProblemsResponse(ok=True, report=report, recent_actions=recent_actions)


@router.post("/scan")
async def trigger_unified_scan():
    """Trigger a fresh blackbox scan then return unified problems."""
    try:
        from cognitive.spindle_blackbox_scanner import get_blackbox_scanner
        import asyncio
        scanner = get_blackbox_scanner()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, scanner.run_scan)
    except Exception as e:
        logger.warning("Blackbox scan trigger failed: %s", e)

    return await get_unified_problems()


# ── WebSocket: Real-time unified events ──────────────────────────

@router.websocket("/ws")
async def unified_problems_websocket(websocket: WebSocket):
    """
    WebSocket for real-time problem updates.
    Forwards events from spindle, component health changes, diagnostic
    alerts, and cognitive events — all on one socket.
    """
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=500)
    loop = asyncio.get_running_loop()

    FORWARD_TOPICS = (
        "spindle.blackbox",
        "audit.spindle",
        "system.health_changed",
        "diagnostic.",
        "healing.",
        "invariant.",
        "confidence.",
        "deterministic.",
    )

    def _handler(event):
        topic = getattr(event, "topic", "") if hasattr(event, "topic") else ""
        if any(topic.startswith(p) for p in FORWARD_TOPICS):
            try:
                out = {
                    "topic": topic,
                    "data": getattr(event, "data", {}),
                    "source": getattr(event, "source", "system"),
                    "timestamp": getattr(event, "timestamp", None),
                }
                loop.call_soon_threadsafe(queue.put_nowait, out)
            except asyncio.QueueFull:
                pass

    try:
        from cognitive.event_bus import subscribe, unsubscribe
        subscribe("*", _handler)
    except Exception:
        pass

    logger.info("[UNIFIED-PROBLEMS-WS] Client connected")

    try:
        while True:
            data = await queue.get()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        logger.info("[UNIFIED-PROBLEMS-WS] Client disconnected")
    except Exception as e:
        logger.error("[UNIFIED-PROBLEMS-WS] Error: %s", e)
    finally:
        try:
            from cognitive.event_bus import unsubscribe
            unsubscribe("*", _handler)
        except Exception:
            pass
