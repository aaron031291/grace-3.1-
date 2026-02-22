"""
Autonomous CI/CD API
====================
REST API for GRACE's fully autonomous, Genesis Key-native CI/CD system.

NO GitHub Actions - Fully GRACE-controlled using Genesis Keys.

Provides:
- Autonomous pipeline triggering and management
- Intelligent test selection
- Closed-loop feedback from production
- Self-healing integration
- Genesis Key tracking for all operations

Classes:
- `PipelineTriggerRequest`
- `AutonomousEventRequest`
- `IntelligentDecisionRequest`
- `TestResultRequest`
- `FeedbackMetricRequest`
- `ApprovalRequest`
- `PipelineDefinition`
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import asdict

from genesis.cicd import get_cicd, Pipeline, PipelineStage, StageType, PipelineStatus
from genesis.autonomous_cicd_engine import (
    get_autonomous_cicd_engine,
    start_autonomous_cicd,
    stop_autonomous_cicd,
    AutonomyLevel,
    AutonomousTriggerType
)
from genesis.intelligent_cicd_orchestrator import (
    get_intelligent_cicd_orchestrator,
    IntelligenceMode,
    TriggerSource,
    TestSelectionStrategy
)

router = APIRouter(prefix="/api/cicd", tags=["Genesis CI/CD"])


# =============================================================================
# Request/Response Models
# =============================================================================

class PipelineTriggerRequest(BaseModel):
    """Request to trigger a pipeline."""
    pipeline_id: str = Field("grace-ci", description="Pipeline ID to trigger")
    branch: str = Field("main", description="Git branch")
    trigger: str = Field("manual", description="Trigger type")
    triggered_by: str = Field("api", description="Who/what triggered")
    variables: Optional[Dict[str, str]] = Field(None, description="Environment variables")


class AutonomousEventRequest(BaseModel):
    """Request to process an autonomous event."""
    event_type: str = Field(..., description="Event type (file_change, health_check, etc.)")
    payload: Dict[str, Any] = Field(..., description="Event payload")
    source: str = Field("api", description="Event source")


class IntelligentDecisionRequest(BaseModel):
    """Request for intelligent CI/CD decision."""
    trigger_source: str = Field(..., description="What triggered this decision")
    context: Dict[str, Any] = Field(default_factory=dict, description="Decision context")
    changed_files: Optional[List[str]] = Field(None, description="List of changed files")
    max_tests: Optional[int] = Field(None, description="Maximum tests to select")
    time_budget: Optional[float] = Field(None, description="Time budget in seconds")


class TestResultRequest(BaseModel):
    """Request to record test results."""
    test_id: str
    passed: bool
    duration: float
    coverage: Optional[float] = None


class FeedbackMetricRequest(BaseModel):
    """Request to record feedback metric."""
    metric_name: str
    value: float
    source: str = "production"


class ApprovalRequest(BaseModel):
    """Request to approve/reject a decision."""
    decision_id: str
    approved: bool
    approver: str = "user"
    reason: Optional[str] = None


class PipelineDefinition(BaseModel):
    """Pipeline definition for registration."""
    id: str
    name: str
    description: str = ""
    triggers: List[str] = Field(default_factory=lambda: ["manual"])
    branches: List[str] = Field(default_factory=lambda: ["main"])
    stages: List[Dict[str, Any]] = Field(default_factory=list)


# =============================================================================
# CORE PIPELINE ENDPOINTS
# =============================================================================

@router.get("/pipelines")
async def list_pipelines():
    """
    List all registered pipelines.

    Returns pipeline definitions with Genesis Key tracking.
    """
    cicd = get_cicd()
    pipelines = cicd.list_pipelines()

    return {
        "count": len(pipelines),
        "pipelines": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "triggers": p.triggers,
                "branches": p.branches,
                "stages": [s.name for s in p.stages],
                "timeout_minutes": p.timeout_minutes
            }
            for p in pipelines
        ]
    }


@router.get("/pipelines/{pipeline_id}")
async def get_pipeline(pipeline_id: str):
    """Get details of a specific pipeline."""
    cicd = get_cicd()
    pipeline = cicd.get_pipeline(pipeline_id)

    if not pipeline:
        raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_id}' not found")

    return {
        "id": pipeline.id,
        "name": pipeline.name,
        "description": pipeline.description,
        "triggers": pipeline.triggers,
        "branches": pipeline.branches,
        "stages": [
            {
                "name": s.name,
                "type": s.stage_type.value,
                "commands": s.commands,
                "timeout": s.timeout_seconds,
                "depends_on": s.depends_on,
                "continue_on_error": s.continue_on_error
            }
            for s in pipeline.stages
        ],
        "timeout_minutes": pipeline.timeout_minutes,
        "created_at": pipeline.created_at
    }


@router.post("/pipelines")
async def register_pipeline(definition: PipelineDefinition):
    """
    Register a new pipeline.

    Creates a Genesis Key-tracked pipeline definition.
    """
    cicd = get_cicd()

    # Convert stage definitions
    stages = []
    for stage_def in definition.stages:
        stages.append(PipelineStage(
            name=stage_def.get("name", "unnamed"),
            stage_type=StageType(stage_def.get("type", "custom")),
            commands=stage_def.get("commands", []),
            working_dir=stage_def.get("working_dir"),
            timeout_seconds=stage_def.get("timeout", 600),
            continue_on_error=stage_def.get("continue_on_error", False),
            depends_on=stage_def.get("depends_on", []),
            artifacts=stage_def.get("artifacts", [])
        ))

    pipeline = Pipeline(
        id=definition.id,
        name=definition.name,
        description=definition.description,
        triggers=definition.triggers,
        branches=definition.branches,
        stages=stages
    )

    cicd.register_pipeline(pipeline)

    return {
        "status": "registered",
        "pipeline_id": pipeline.id,
        "name": pipeline.name,
        "stages_count": len(stages)
    }


@router.post("/trigger")
async def trigger_pipeline(request: PipelineTriggerRequest):
    """
    Trigger a pipeline run.

    Creates Genesis Keys for full traceability.
    """
    cicd = get_cicd()

    try:
        run = await cicd.trigger_pipeline(
            pipeline_id=request.pipeline_id,
            trigger=request.trigger,
            branch=request.branch,
            triggered_by=request.triggered_by,
            variables=request.variables
        )

        return {
            "status": "triggered",
            "run_id": run.id,
            "pipeline_id": run.pipeline_id,
            "pipeline_name": run.pipeline_name,
            "genesis_key": run.genesis_key,
            "trigger": run.trigger,
            "branch": run.branch
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runs")
async def list_runs(
    pipeline_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """List pipeline runs with optional filters."""
    cicd = get_cicd()

    status_filter = None
    if status:
        try:
            status_filter = PipelineStatus(status)
        except ValueError:
            pass

    runs = cicd.list_runs(
        pipeline_id=pipeline_id,
        status=status_filter,
        limit=limit
    )

    return {
        "count": len(runs),
        "runs": [
            {
                "id": r.id,
                "pipeline_id": r.pipeline_id,
                "pipeline_name": r.pipeline_name,
                "genesis_key": r.genesis_key,
                "status": r.status.value,
                "trigger": r.trigger,
                "branch": r.branch,
                "triggered_by": r.triggered_by,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "duration_seconds": r.duration_seconds,
                "stages_completed": len([s for s in r.stage_results if s.status == PipelineStatus.SUCCESS])
            }
            for r in runs
        ]
    }


@router.get("/runs/{run_id}")
async def get_run(run_id: str):
    """Get details of a specific pipeline run."""
    cicd = get_cicd()
    run = cicd.get_run(run_id)

    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    return {
        "id": run.id,
        "pipeline_id": run.pipeline_id,
        "pipeline_name": run.pipeline_name,
        "genesis_key": run.genesis_key,
        "status": run.status.value,
        "trigger": run.trigger,
        "branch": run.branch,
        "commit_sha": run.commit_sha,
        "commit_message": run.commit_message,
        "triggered_by": run.triggered_by,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "duration_seconds": run.duration_seconds,
        "stages": [
            {
                "name": s.stage_name,
                "status": s.status.value,
                "duration": s.duration_seconds,
                "exit_code": s.exit_code,
                "stdout": s.stdout[-2000:] if s.stdout else "",  # Last 2KB
                "stderr": s.stderr[-2000:] if s.stderr else ""
            }
            for s in run.stage_results
        ],
        "artifacts": run.artifacts,
        "metadata": run.metadata
    }


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    """Cancel a running pipeline."""
    cicd = get_cicd()

    success = await cicd.cancel_run(run_id)

    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel run (not found or already completed)")

    return {"status": "cancelled", "run_id": run_id}


@router.get("/genesis-keys")
async def list_genesis_keys(run_id: Optional[str] = None, limit: int = 100):
    """
    List Genesis Keys from CI/CD operations.

    Full audit trail of all CI/CD actions.
    """
    cicd = get_cicd()
    keys = cicd.get_genesis_keys(run_id)

    # Sort by timestamp and limit
    sorted_keys = sorted(
        keys.items(),
        key=lambda x: x[1].get("timestamp", ""),
        reverse=True
    )[:limit]

    return {
        "count": len(sorted_keys),
        "genesis_keys": [
            {
                "key": k,
                "action": v.get("action"),
                "timestamp": v.get("timestamp"),
                "metadata": v.get("metadata")
            }
            for k, v in sorted_keys
        ]
    }


# =============================================================================
# AUTONOMOUS ENGINE ENDPOINTS
# =============================================================================

@router.post("/autonomous/start")
async def start_engine():
    """Start the autonomous CI/CD engine."""
    await start_autonomous_cicd()
    return {"status": "started", "message": "Autonomous CI/CD engine is now running"}


@router.post("/autonomous/stop")
async def stop_engine():
    """Stop the autonomous CI/CD engine."""
    await stop_autonomous_cicd()
    return {"status": "stopped", "message": "Autonomous CI/CD engine stopped"}


@router.get("/autonomous/status")
async def get_engine_status():
    """Get autonomous engine status."""
    engine = get_autonomous_cicd_engine()
    return engine.get_status()


@router.post("/autonomous/event")
async def process_event(request: AutonomousEventRequest):
    """
    Process an autonomous event.

    The engine will analyze and decide on appropriate CI/CD actions.
    """
    engine = get_autonomous_cicd_engine()

    try:
        event_type = AutonomousTriggerType(request.event_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type. Valid: {[t.value for t in AutonomousTriggerType]}"
        )

    # Route to appropriate handler
    if event_type == AutonomousTriggerType.FILE_CHANGE:
        decision = await engine.on_file_change(
            file_path=request.payload.get("file_path", ""),
            change_type=request.payload.get("change_type", "modified")
        )
    elif event_type == AutonomousTriggerType.ANOMALY_RESPONSE:
        decision = await engine.on_anomaly_detected(
            anomaly_type=request.payload.get("anomaly_type", "unknown"),
            severity=request.payload.get("severity", "medium"),
            details=request.payload.get("details", {})
        )
    elif event_type == AutonomousTriggerType.HEALING_ACTION:
        decision = await engine.on_healing_request(
            healing_action=request.payload.get("healing_action", ""),
            context=request.payload.get("context", {})
        )
    elif event_type == AutonomousTriggerType.LEARNING_OPPORTUNITY:
        decision = await engine.on_learning_opportunity(
            topic=request.payload.get("topic", ""),
            learning_type=request.payload.get("learning_type", "code_change")
        )
    else:
        decision = None

    if decision:
        return {
            "processed": True,
            "decision": {
                "decision_id": decision.decision_id,
                "action": decision.action,
                "risk_level": decision.risk_level.value,
                "confidence": decision.confidence,
                "execution_mode": decision.execution_mode,
                "approved": decision.approved,
                "reasoning": decision.reasoning,
                "genesis_key": decision.genesis_key
            }
        }

    return {"processed": True, "decision": None, "message": "No action required"}


@router.get("/autonomous/decisions")
async def list_decisions(pending_only: bool = False, limit: int = 50):
    """List autonomous decisions."""
    engine = get_autonomous_cicd_engine()

    if pending_only:
        decisions = engine.get_pending_decisions()
    else:
        decisions = list(engine.decisions.values())[-limit:]

    return {
        "count": len(decisions),
        "decisions": [
            {
                "decision_id": d.decision_id,
                "event_id": d.event_id,
                "action": d.action,
                "risk_level": d.risk_level.value,
                "confidence": d.confidence,
                "approved": d.approved,
                "execution_mode": d.execution_mode,
                "reasoning": d.reasoning,
                "genesis_key": d.genesis_key,
                "timestamp": d.timestamp
            }
            for d in decisions
        ]
    }


@router.post("/autonomous/approve")
async def approve_decision(request: ApprovalRequest):
    """Approve or reject a pending autonomous decision."""
    engine = get_autonomous_cicd_engine()

    if request.approved:
        decision = await engine.approve_decision(
            decision_id=request.decision_id,
            approver=request.approver
        )
    else:
        decision = await engine.reject_decision(
            decision_id=request.decision_id,
            reason=request.reason or "User rejected"
        )

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    return {
        "status": "approved" if request.approved else "rejected",
        "decision_id": decision.decision_id,
        "action": decision.action,
        "execution_mode": decision.execution_mode
    }


@router.post("/autonomous/outcome")
async def record_outcome(
    decision_id: str,
    success: bool,
    details: Optional[Dict[str, Any]] = None
):
    """Record outcome for learning."""
    engine = get_autonomous_cicd_engine()
    engine.record_outcome(decision_id, success, details)

    return {"status": "recorded", "decision_id": decision_id, "success": success}


# =============================================================================
# INTELLIGENT ORCHESTRATOR ENDPOINTS
# =============================================================================

@router.get("/intelligent/status")
async def get_orchestrator_status():
    """Get intelligent orchestrator status."""
    orchestrator = get_intelligent_cicd_orchestrator()
    return orchestrator.get_status()


@router.post("/intelligent/decide")
async def make_intelligent_decision(request: IntelligentDecisionRequest):
    """
    Make an intelligent CI/CD decision.

    Uses ML-based test selection and closed-loop feedback.
    """
    orchestrator = get_intelligent_cicd_orchestrator()

    try:
        trigger = TriggerSource(request.trigger_source)
    except ValueError:
        trigger = TriggerSource.USER_REQUEST

    context = request.context
    if request.changed_files:
        context["changed_files"] = request.changed_files
    if request.max_tests:
        context["max_tests"] = request.max_tests
    if request.time_budget:
        context["time_budget"] = request.time_budget

    decision = await orchestrator.make_pipeline_decision(
        trigger_source=trigger,
        context=context
    )

    return {
        "decision_id": decision.decision_id,
        "decision": decision.decision.value,
        "confidence": decision.confidence,
        "reasoning": decision.reasoning,
        "test_strategy": decision.test_strategy.value,
        "tests_selected": len(decision.tests_selected),
        "pipeline_modifications": decision.pipeline_modifications,
        "genesis_key": decision.genesis_key
    }


@router.post("/intelligent/execute/{decision_id}")
async def execute_intelligent_decision(decision_id: str):
    """Execute a previous intelligent decision."""
    orchestrator = get_intelligent_cicd_orchestrator()

    decision = orchestrator.decisions.get(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    result = await orchestrator.execute_decision(decision)

    return result


@router.post("/intelligent/test-result")
async def record_test_result(request: TestResultRequest):
    """Record test result for intelligent test selection."""
    orchestrator = get_intelligent_cicd_orchestrator()

    orchestrator.test_selector.record_test_result(
        test_id=request.test_id,
        passed=request.passed,
        duration=request.duration,
        coverage=request.coverage or 0.0
    )

    return {"status": "recorded", "test_id": request.test_id}


@router.post("/intelligent/feedback")
async def record_feedback_metric(request: FeedbackMetricRequest):
    """Record production feedback metric."""
    orchestrator = get_intelligent_cicd_orchestrator()

    metric = orchestrator.feedback_loop.record_metric(
        name=request.metric_name,
        value=request.value,
        source=request.source
    )

    return {
        "status": "recorded",
        "metric": request.metric_name,
        "value": request.value,
        "trend": metric.trend
    }


@router.get("/intelligent/feedback")
async def get_feedback_summary():
    """Get feedback loop summary."""
    orchestrator = get_intelligent_cicd_orchestrator()

    return {
        "metrics": {
            name: {
                "latest": metrics[-1].value if metrics else None,
                "trend": metrics[-1].trend if metrics else "unknown",
                "data_points": len(metrics)
            }
            for name, metrics in orchestrator.feedback_loop.metrics.items()
        },
        "recent_actions": orchestrator.feedback_loop.feedback_actions[-10:]
    }


@router.get("/intelligent/test-metrics")
async def get_test_metrics(limit: int = 50):
    """Get test metrics for intelligent selection."""
    orchestrator = get_intelligent_cicd_orchestrator()

    metrics = list(orchestrator.test_selector.test_metrics.values())
    metrics.sort(key=lambda m: m.priority_score, reverse=True)

    return {
        "count": len(metrics),
        "metrics": [
            {
                "test_id": m.test_id,
                "pass_rate": m.pass_rate,
                "avg_duration": m.avg_duration,
                "failure_recency": m.failure_recency,
                "coverage_value": m.coverage_value,
                "priority_score": m.priority_score,
                "total_runs": m.total_runs
            }
            for m in metrics[:limit]
        ]
    }


@router.post("/intelligent/select-tests")
async def select_tests(
    strategy: str = "impact_analysis",
    changed_files: Optional[List[str]] = None,
    max_tests: Optional[int] = None,
    time_budget: Optional[float] = None
):
    """Select tests using intelligent strategy."""
    orchestrator = get_intelligent_cicd_orchestrator()

    try:
        strat = TestSelectionStrategy(strategy)
    except ValueError:
        strat = TestSelectionStrategy.ALL_TESTS

    selected = orchestrator.test_selector.select_tests(
        strategy=strat,
        changed_files=changed_files,
        max_tests=max_tests,
        time_budget=time_budget
    )

    return {
        "strategy": strategy,
        "tests_selected": len(selected),
        "tests": selected
    }


@router.get("/intelligent/dashboard")
async def get_intelligent_dashboard():
    """Get comprehensive dashboard for intelligent CI/CD."""
    orchestrator = get_intelligent_cicd_orchestrator()
    return orchestrator.get_dashboard_data()


# =============================================================================
# INTEGRATION ENDPOINTS
# =============================================================================

@router.post("/integrate/healing")
async def integrate_with_healing(failure_context: Dict[str, Any]):
    """
    Integrate with autonomous healing system.

    Triggers healing when CI/CD failures occur.
    """
    orchestrator = get_intelligent_cicd_orchestrator()
    result = await orchestrator.integrate_with_healing(failure_context)
    return result


@router.post("/integrate/genesis-triggers")
async def integrate_with_genesis_triggers(genesis_key_id: str):
    """
    Integrate with Genesis Key trigger pipeline.

    Connects CI/CD with the autonomous trigger system.
    """
    orchestrator = get_intelligent_cicd_orchestrator()
    result = await orchestrator.integrate_with_genesis_triggers(genesis_key_id)
    return result


# =============================================================================
# SYSTEM ENDPOINTS
# =============================================================================

@router.get("/health")
async def health_check():
    """CI/CD system health check."""
    cicd = get_cicd()
    engine = get_autonomous_cicd_engine()

    return {
        "status": "healthy",
        "cicd": {
            "pipelines": len(cicd.pipelines),
            "active_runs": len(cicd.active_runs),
            "genesis_keys": len(cicd.genesis_keys)
        },
        "autonomous_engine": {
            "running": engine._running,
            "autonomy_level": engine.autonomy_level.name,
            "decisions": len(engine.decisions)
        },
        "timestamp": datetime.now().isoformat()
    }
