"""
Diagnostic Machine API Endpoints

Provides REST API for:
- Running diagnostic cycles
- Getting health status
- Viewing diagnostic history
- Managing the diagnostic engine
- CI/CD integration webhooks
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

from .diagnostic_engine import (
    DiagnosticEngine,
    get_diagnostic_engine,
    start_diagnostic_engine,
    stop_diagnostic_engine,
    TriggerSource,
    EngineState,
)
from .sensors import SensorLayer
from .interpreters import InterpreterLayer
from .judgement import JudgementLayer
from .action_router import ActionRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagnostic", tags=["Diagnostic Machine"])


# Request/Response models
class DiagnosticTriggerRequest(BaseModel):
    """Request to trigger a diagnostic cycle."""
    source: str = Field(default="api", description="Trigger source (api, webhook, cicd)")
    reason: Optional[str] = Field(default=None, description="Reason for trigger")
    pipeline_id: Optional[str] = Field(default=None, description="CI/CD pipeline ID if applicable")


class DiagnosticTriggerResponse(BaseModel):
    """Response from diagnostic trigger."""
    cycle_id: str
    success: bool
    health_status: str
    health_score: float
    recommended_action: str
    action_taken: str
    duration_ms: float
    message: str


class HealthSummaryResponse(BaseModel):
    """Health summary response."""
    status: str
    health_score: float
    confidence: float
    last_check: Optional[str]
    degraded_components: List[str]
    critical_components: List[str]
    avm_level: str
    recommended_action: str


class EngineStatusResponse(BaseModel):
    """Engine status response."""
    state: str
    heartbeat_interval: int
    total_cycles: int
    successful_cycles: int
    failed_cycles: int
    total_alerts: int
    total_healing_actions: int
    total_freeze_events: int
    uptime_seconds: float


class CICDWebhookRequest(BaseModel):
    """CI/CD webhook request."""
    pipeline_id: str
    event: str = Field(default="completed", description="Pipeline event type")
    status: str = Field(default="success", description="Pipeline status")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SensorFlagRequest(BaseModel):
    """Request to flag an issue from a sensor."""
    sensor_type: str
    severity: str = Field(default="medium", description="low, medium, high, critical")
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


# Singleton engine instance
_engine: Optional[DiagnosticEngine] = None


def get_engine() -> DiagnosticEngine:
    """Get or create the diagnostic engine."""
    global _engine
    if _engine is None:
        _engine = get_diagnostic_engine(
            heartbeat_interval=60,
            enable_heartbeat=True,
            enable_cicd=True,
            enable_healing=True,
            enable_forensics=True,
        )
    return _engine


# API Endpoints
@router.get("/health", response_model=HealthSummaryResponse)
async def get_health_summary():
    """Get current system health summary from diagnostic machine."""
    try:
        engine = get_engine()
        summary = engine.get_health_summary()

        return HealthSummaryResponse(
            status=summary.get('status', 'unknown'),
            health_score=summary.get('health_score', 0.0),
            confidence=summary.get('confidence', 0.0),
            last_check=summary.get('last_check'),
            degraded_components=summary.get('degraded_components', []),
            critical_components=summary.get('critical_components', []),
            avm_level=summary.get('avm_level', 'unknown'),
            recommended_action=summary.get('recommended_action', 'none'),
        )
    except Exception as e:
        logger.error(f"Error getting health summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=EngineStatusResponse)
async def get_engine_status():
    """Get diagnostic engine status and statistics."""
    try:
        engine = get_engine()
        stats = engine.stats

        return EngineStatusResponse(
            state=engine.state.value,
            heartbeat_interval=engine.heartbeat_interval,
            total_cycles=stats.total_cycles,
            successful_cycles=stats.successful_cycles,
            failed_cycles=stats.failed_cycles,
            total_alerts=stats.total_alerts,
            total_healing_actions=stats.total_healing_actions,
            total_freeze_events=stats.total_freeze_events,
            uptime_seconds=stats.uptime_seconds,
        )
    except Exception as e:
        logger.error(f"Error getting engine status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger", response_model=DiagnosticTriggerResponse)
async def trigger_diagnostic(request: DiagnosticTriggerRequest):
    """Manually trigger a diagnostic cycle."""
    try:
        engine = get_engine()

        # Determine trigger source
        source_map = {
            'api': TriggerSource.API,
            'manual': TriggerSource.MANUAL,
            'webhook': TriggerSource.WEBHOOK,
            'cicd': TriggerSource.CICD_PIPELINE,
        }
        trigger_source = source_map.get(request.source, TriggerSource.API)

        # Run diagnostic cycle
        cycle = engine.run_cycle(trigger_source)

        # Build response
        health_status = "unknown"
        health_score = 0.0
        recommended_action = "none"
        action_taken = "none"

        if cycle.judgement:
            health_status = cycle.judgement.health.status.value
            health_score = cycle.judgement.health.overall_score
            recommended_action = cycle.judgement.recommended_action

        if cycle.action_decision:
            action_taken = cycle.action_decision.action_type.value

        return DiagnosticTriggerResponse(
            cycle_id=cycle.cycle_id,
            success=cycle.success,
            health_status=health_status,
            health_score=health_score,
            recommended_action=recommended_action,
            action_taken=action_taken,
            duration_ms=cycle.total_duration_ms,
            message=cycle.error_message or "Diagnostic cycle completed successfully",
        )
    except Exception as e:
        logger.error(f"Error triggering diagnostic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/cicd")
async def cicd_webhook(request: CICDWebhookRequest, background_tasks: BackgroundTasks):
    """Webhook endpoint for CI/CD pipeline integration."""
    try:
        engine = get_engine()

        # Trigger diagnostic in background
        background_tasks.add_task(
            engine.trigger_from_cicd,
            request.pipeline_id
        )

        return {
            "status": "accepted",
            "message": f"Diagnostic triggered for pipeline {request.pipeline_id}",
            "pipeline_event": request.event,
        }
    except Exception as e:
        logger.error(f"CI/CD webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sensor/flag")
async def flag_sensor_issue(request: SensorFlagRequest, background_tasks: BackgroundTasks):
    """Flag an issue from a sensor to trigger diagnostic."""
    try:
        engine = get_engine()

        # Trigger diagnostic in background
        background_tasks.add_task(
            engine.trigger_from_sensor,
            request.sensor_type,
            request.message
        )

        return {
            "status": "accepted",
            "message": f"Sensor flag received: {request.sensor_type}",
            "severity": request.severity,
        }
    except Exception as e:
        logger.error(f"Sensor flag error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_engine():
    """Start the diagnostic engine with heartbeat."""
    try:
        engine = get_engine()
        success = engine.start()

        return {
            "status": "started" if success else "failed",
            "state": engine.state.value,
            "heartbeat_interval": engine.heartbeat_interval,
        }
    except Exception as e:
        logger.error(f"Error starting engine: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_engine():
    """Stop the diagnostic engine."""
    try:
        engine = get_engine()
        success = engine.stop()

        return {
            "status": "stopped" if success else "failed",
            "state": engine.state.value,
        }
    except Exception as e:
        logger.error(f"Error stopping engine: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause")
async def pause_engine():
    """Pause the diagnostic engine heartbeat."""
    try:
        engine = get_engine()
        engine.pause()

        return {
            "status": "paused",
            "state": engine.state.value,
        }
    except Exception as e:
        logger.error(f"Error pausing engine: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume")
async def resume_engine():
    """Resume the diagnostic engine heartbeat."""
    try:
        engine = get_engine()
        engine.resume()

        return {
            "status": "resumed",
            "state": engine.state.value,
        }
    except Exception as e:
        logger.error(f"Error resuming engine: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_diagnostic_history(limit: int = 10):
    """Get recent diagnostic cycle history."""
    try:
        engine = get_engine()
        cycles = engine.get_recent_cycles(limit)

        return {
            "cycles": [
                {
                    "cycle_id": c.cycle_id,
                    "trigger_source": c.trigger_source.value,
                    "success": c.success,
                    "health_status": c.judgement.health.status.value if c.judgement else "unknown",
                    "health_score": c.judgement.health.overall_score if c.judgement else 0.0,
                    "action_taken": c.action_decision.action_type.value if c.action_decision else "none",
                    "duration_ms": c.total_duration_ms,
                    "timestamp": c.cycle_end.isoformat() if c.cycle_end else None,
                }
                for c in cycles
            ],
            "total": len(cycles),
        }
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/full-report")
async def get_full_diagnostic_report():
    """Get a comprehensive diagnostic report."""
    try:
        engine = get_engine()

        # Run a fresh diagnostic cycle
        cycle = engine.run_cycle(TriggerSource.API)

        # Build comprehensive report
        report = {
            "report_id": f"REPORT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "generated_at": datetime.utcnow().isoformat(),
            "cycle_id": cycle.cycle_id,
            "success": cycle.success,
        }

        if cycle.sensor_data:
            sensor_layer = SensorLayer()
            report["sensors"] = sensor_layer.to_dict(cycle.sensor_data)

        if cycle.interpreted_data:
            interpreter_layer = InterpreterLayer()
            report["interpretation"] = interpreter_layer.to_dict(cycle.interpreted_data)

        if cycle.judgement:
            judgement_layer = JudgementLayer()
            report["judgement"] = judgement_layer.to_dict(cycle.judgement)

        if cycle.action_decision:
            action_router = ActionRouter()
            report["action"] = action_router.to_dict(cycle.action_decision)

        # Add engine stats
        stats = engine.stats
        report["engine_stats"] = {
            "state": engine.state.value,
            "total_cycles": stats.total_cycles,
            "uptime_seconds": stats.uptime_seconds,
            "average_cycle_duration_ms": stats.average_cycle_duration_ms,
        }

        return report

    except Exception as e:
        logger.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/avn/alerts")
async def get_avn_alerts():
    """Get Anomaly Violation Notification alerts."""
    try:
        engine = get_engine()
        cycles = engine.get_recent_cycles(50)

        alerts = []
        for cycle in cycles:
            if cycle.judgement and cycle.judgement.avn_alerts:
                for alert in cycle.judgement.avn_alerts:
                    alerts.append({
                        "alert_id": alert.alert_id,
                        "cycle_id": cycle.cycle_id,
                        "severity": alert.severity,
                        "anomaly_type": alert.anomaly_type,
                        "violation_type": alert.violation_type,
                        "message": alert.message,
                        "timestamp": alert.timestamp.isoformat(),
                    })

        return {
            "alerts": alerts[-20:],  # Last 20 alerts
            "total": len(alerts),
        }
    except Exception as e:
        logger.error(f"Error getting AVN alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/avm/status")
async def get_avm_status():
    """Get Anomaly Violation Monitor status."""
    try:
        engine = get_engine()
        cycles = engine.get_recent_cycles(1)

        if not cycles or not cycles[0].judgement:
            return {
                "status": "unknown",
                "message": "No diagnostic data available",
            }

        avm = cycles[0].judgement.avm_status
        return {
            "monitor_id": avm.monitor_id,
            "is_active": avm.is_active,
            "anomalies_detected": avm.anomalies_detected,
            "violations_detected": avm.violations_detected,
            "last_check": avm.last_check.isoformat(),
            "alert_level": avm.current_alert_level,
        }
    except Exception as e:
        logger.error(f"Error getting AVM status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forensics")
async def get_forensic_findings():
    """Get forensic analysis findings."""
    try:
        engine = get_engine()
        cycles = engine.get_recent_cycles(10)

        findings = []
        for cycle in cycles:
            if cycle.judgement and cycle.judgement.forensic_findings:
                for finding in cycle.judgement.forensic_findings:
                    findings.append({
                        "finding_id": finding.finding_id,
                        "cycle_id": cycle.cycle_id,
                        "category": finding.category,
                        "description": finding.description,
                        "confidence": finding.confidence,
                        "related_components": finding.related_components,
                    })

        return {
            "findings": findings,
            "total": len(findings),
        }
    except Exception as e:
        logger.error(f"Error getting forensic findings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
