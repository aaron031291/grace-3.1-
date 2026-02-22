"""
Adaptive CI/CD API
==================
REST API for the adaptive CI/CD system.
Trust scores, KPIs, LLM orchestration, sandbox, governance.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

from genesis.adaptive_cicd import (
    get_adaptive_cicd,
    AdaptiveCICD,
    PipelineTrustLevel,
    AdaptiveTriggerReason,
    GovernanceAction
)

router = APIRouter(prefix="/api/cicd/adaptive", tags=["Adaptive CI/CD"])


# =============================================================================
# Request/Response Models
# =============================================================================

class TriggerRequest(BaseModel):
    """Request for adaptive pipeline trigger."""
    pipeline_id: str = Field(..., description="Pipeline to trigger")
    reason: str = Field("autonomous_decision", description="Trigger reason")
    branch: str = Field("main", description="Git branch")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class RecordRunRequest(BaseModel):
    """Request to record a pipeline run result."""
    pipeline_id: str
    status: str = Field(..., description="Run status (success/failed)")
    duration: float = Field(..., description="Duration in seconds")
    metadata: Optional[Dict[str, Any]] = None


class GovernanceApprovalRequest(BaseModel):
    """Request to approve/reject a governance request."""
    request_id: str
    approved: bool
    reviewer: str = Field("human", description="Reviewer identifier")


class TrustOverrideRequest(BaseModel):
    """Request to manually override trust score."""
    pipeline_id: str
    trust_level: str
    reason: str
    reviewer: str


# =============================================================================
# Trust Score Endpoints
# =============================================================================

@router.get("/trust")
async def list_trust_scores():
    """
    List trust scores for all pipelines.

    Returns trust levels, scores, and trends.
    """
    adaptive = get_adaptive_cicd()

    scores = []
    for pipeline_id, trust in adaptive.trust_scores.items():
        scores.append({
            "pipeline_id": trust.pipeline_id,
            "trust_level": trust.trust_level.value,
            "score": trust.score,
            "total_runs": trust.total_runs,
            "successful_runs": trust.successful_runs,
            "failed_runs": trust.failed_runs,
            "reliability_trend": trust.reliability_trend,
            "human_verified": trust.human_verified,
            "genesis_key": trust.genesis_key
        })

    return {
        "count": len(scores),
        "trust_scores": scores
    }


@router.get("/trust/{pipeline_id}")
async def get_trust_score(pipeline_id: str):
    """
    Get trust score for a specific pipeline.

    Returns detailed trust metrics and history.
    """
    adaptive = get_adaptive_cicd()
    trust = adaptive.calculate_trust_score(pipeline_id)

    return {
        "pipeline_id": trust.pipeline_id,
        "trust_level": trust.trust_level.value,
        "score": trust.score,
        "total_runs": trust.total_runs,
        "successful_runs": trust.successful_runs,
        "failed_runs": trust.failed_runs,
        "avg_duration": trust.avg_duration,
        "reliability_trend": trust.reliability_trend,
        "last_success": trust.last_success,
        "last_failure": trust.last_failure,
        "human_verified": trust.human_verified,
        "verification_date": trust.verification_date,
        "genesis_key": trust.genesis_key
    }


@router.post("/trust/override")
async def override_trust_score(request: TrustOverrideRequest):
    """
    Manually override a pipeline's trust level.

    For human verification or emergency adjustments.
    """
    adaptive = get_adaptive_cicd()

    try:
        trust_level = PipelineTrustLevel(request.trust_level)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trust level. Valid: {[t.value for t in PipelineTrustLevel]}"
        )

    # Get or create trust score
    if request.pipeline_id not in adaptive.trust_scores:
        adaptive.calculate_trust_score(request.pipeline_id)

    trust = adaptive.trust_scores[request.pipeline_id]
    trust.trust_level = trust_level
    trust.human_verified = True
    trust.verification_date = datetime.now().isoformat()

    return {
        "status": "updated",
        "pipeline_id": request.pipeline_id,
        "new_trust_level": trust_level.value,
        "verified_by": request.reviewer,
        "reason": request.reason
    }


# =============================================================================
# KPI Endpoints
# =============================================================================

@router.get("/kpis")
async def list_all_kpis():
    """
    List KPIs for all pipelines.

    Returns performance, quality, and efficiency metrics.
    """
    adaptive = get_adaptive_cicd()

    kpis = []
    for pipeline_id in adaptive.trust_scores.keys():
        kpi = adaptive.calculate_kpis(pipeline_id)
        kpis.append({
            "pipeline_id": kpi.pipeline_id,
            "success_rate": kpi.success_rate,
            "avg_duration": kpi.avg_duration_seconds,
            "throughput_per_hour": kpi.throughput_per_hour,
            "test_pass_rate": kpi.test_pass_rate,
            "retry_rate": kpi.retry_rate,
            "overall_health": kpi.overall_health,
            "performance_trend": kpi.performance_trend,
            "confidence": kpi.confidence
        })

    return {
        "count": len(kpis),
        "kpis": kpis
    }


@router.get("/kpis/{pipeline_id}")
async def get_pipeline_kpis(pipeline_id: str):
    """
    Get detailed KPIs for a specific pipeline.

    Includes full performance breakdown.
    """
    adaptive = get_adaptive_cicd()
    kpis = adaptive.calculate_kpis(pipeline_id)

    return {
        "pipeline_id": kpis.pipeline_id,
        "timestamp": kpis.timestamp,
        "performance": {
            "success_rate": kpis.success_rate,
            "avg_duration_seconds": kpis.avg_duration_seconds,
            "p95_duration_seconds": kpis.p95_duration_seconds,
            "throughput_per_hour": kpis.throughput_per_hour
        },
        "quality": {
            "test_pass_rate": kpis.test_pass_rate,
            "code_coverage": kpis.code_coverage,
            "security_score": kpis.security_score,
            "lint_score": kpis.lint_score
        },
        "efficiency": {
            "resource_utilization": kpis.resource_utilization,
            "queue_wait_time": kpis.queue_wait_time,
            "retry_rate": kpis.retry_rate
        },
        "trends": {
            "performance_trend": kpis.performance_trend,
            "quality_trend": kpis.quality_trend
        },
        "composite": {
            "overall_health": kpis.overall_health,
            "confidence": kpis.confidence
        }
    }


@router.get("/kpis/{pipeline_id}/history")
async def get_kpi_history(pipeline_id: str, limit: int = 50):
    """
    Get KPI history for a pipeline.

    Shows performance over time.
    """
    adaptive = get_adaptive_cicd()
    history = adaptive.kpi_history.get(pipeline_id, [])

    return {
        "pipeline_id": pipeline_id,
        "count": len(history),
        "history": [
            {
                "timestamp": k.timestamp,
                "success_rate": k.success_rate,
                "overall_health": k.overall_health,
                "performance_trend": k.performance_trend
            }
            for k in history[-limit:]
        ]
    }


# =============================================================================
# Adaptive Trigger Endpoints
# =============================================================================

@router.post("/trigger")
async def adaptive_trigger(request: TriggerRequest, background_tasks: BackgroundTasks):
    """
    Trigger a pipeline with full adaptive logic.

    1. Evaluates trust and KPIs
    2. Gets LLM recommendation
    3. Runs in sandbox if needed
    4. Requests governance approval if required
    5. Executes production run
    """
    adaptive = get_adaptive_cicd()

    try:
        reason = AdaptiveTriggerReason(request.reason)
    except ValueError:
        reason = AdaptiveTriggerReason.AUTONOMOUS_DECISION

    context = request.context or {}
    context["branch"] = request.branch

    result = await adaptive.trigger_autonomous_pipeline(
        pipeline_id=request.pipeline_id,
        reason=reason,
        context=context
    )

    return result


@router.post("/evaluate")
async def evaluate_trigger(request: TriggerRequest):
    """
    Evaluate if a pipeline should be triggered.

    Returns decision without executing.
    """
    adaptive = get_adaptive_cicd()

    try:
        reason = AdaptiveTriggerReason(request.reason)
    except ValueError:
        reason = AdaptiveTriggerReason.AUTONOMOUS_DECISION

    trigger = await adaptive.should_trigger_pipeline(
        pipeline_id=request.pipeline_id,
        reason=reason,
        context=request.context
    )

    return {
        "trigger_id": trigger.id,
        "pipeline_id": trigger.pipeline_id,
        "decision": {
            "should_proceed": not trigger.requires_approval or trigger.sandbox_required,
            "sandbox_required": trigger.sandbox_required,
            "requires_approval": trigger.requires_approval,
            "governance_action": trigger.governance_action.value if trigger.governance_action else None
        },
        "scores": {
            "trust": trigger.trust_score,
            "confidence": trigger.confidence
        },
        "llm_recommendation": trigger.llm_recommendation,
        "timestamp": trigger.timestamp
    }


@router.get("/triggers")
async def list_triggers(limit: int = 50):
    """
    List recent adaptive triggers.
    """
    adaptive = get_adaptive_cicd()

    triggers = list(adaptive.triggers.values())[-limit:]

    return {
        "count": len(triggers),
        "triggers": [
            {
                "id": t.id,
                "pipeline_id": t.pipeline_id,
                "reason": t.reason.value,
                "confidence": t.confidence,
                "trust_score": t.trust_score,
                "requires_approval": t.requires_approval,
                "sandbox_required": t.sandbox_required,
                "timestamp": t.timestamp
            }
            for t in triggers
        ]
    }


# =============================================================================
# Sandbox Endpoints
# =============================================================================

@router.post("/sandbox/{pipeline_id}")
async def run_sandbox(pipeline_id: str, branch: str = "main"):
    """
    Run a pipeline in sandbox mode.

    Isolated execution for testing.
    """
    adaptive = get_adaptive_cicd()

    result = await adaptive.run_in_sandbox(
        pipeline_id=pipeline_id,
        trigger_id=f"manual-{datetime.now().strftime('%H%M%S')}",
        context={"branch": branch}
    )

    return result


@router.get("/sandbox")
async def list_sandbox_runs(limit: int = 20):
    """
    List recent sandbox runs.
    """
    adaptive = get_adaptive_cicd()

    runs = list(adaptive.sandbox_runs.values())[-limit:]

    return {
        "count": len(runs),
        "sandbox_runs": runs
    }


# =============================================================================
# Governance Endpoints
# =============================================================================

@router.get("/governance")
async def list_governance_requests(status: Optional[str] = None):
    """
    List governance requests.

    Filter by status: pending, approved, rejected.
    """
    adaptive = get_adaptive_cicd()

    requests = list(adaptive.governance_requests.values())

    if status:
        requests = [r for r in requests if r.status == status]

    return {
        "count": len(requests),
        "requests": [
            {
                "id": r.id,
                "action": r.action.value,
                "pipeline_id": r.pipeline_id,
                "risk_level": r.risk_level,
                "reason": r.reason,
                "recommended_action": r.recommended_action,
                "status": r.status,
                "deadline": r.deadline,
                "reviewer": r.reviewer,
                "genesis_key": r.genesis_key
            }
            for r in requests
        ]
    }


@router.post("/governance/approve")
async def approve_governance(request: GovernanceApprovalRequest):
    """
    Approve or reject a governance request.

    Human oversight decision.
    """
    adaptive = get_adaptive_cicd()

    try:
        gov_request = adaptive.approve_governance_request(
            request_id=request.request_id,
            reviewer=request.reviewer,
            approved=request.approved
        )

        return {
            "status": "processed",
            "request_id": gov_request.id,
            "decision": gov_request.status,
            "reviewer": gov_request.reviewer,
            "response_time": gov_request.response_time
        }

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/governance/{request_id}")
async def get_governance_request(request_id: str):
    """
    Get details of a specific governance request.
    """
    adaptive = get_adaptive_cicd()

    gov_request = adaptive.governance_requests.get(request_id)

    if not gov_request:
        raise HTTPException(status_code=404, detail="Governance request not found")

    return {
        "id": gov_request.id,
        "action": gov_request.action.value,
        "pipeline_id": gov_request.pipeline_id,
        "trigger_id": gov_request.trigger_id,
        "reason": gov_request.reason,
        "risk_level": gov_request.risk_level,
        "llm_analysis": gov_request.llm_analysis,
        "recommended_action": gov_request.recommended_action,
        "status": gov_request.status,
        "deadline": gov_request.deadline,
        "reviewer": gov_request.reviewer,
        "response_time": gov_request.response_time,
        "genesis_key": gov_request.genesis_key
    }


# =============================================================================
# Recording & Analytics Endpoints
# =============================================================================

@router.post("/record")
async def record_run(request: RecordRunRequest):
    """
    Record a pipeline run result.

    Updates trust scores and KPIs.
    """
    adaptive = get_adaptive_cicd()

    adaptive.record_run_result(
        pipeline_id=request.pipeline_id,
        status=request.status,
        duration=request.duration,
        metadata=request.metadata
    )

    # Return updated scores
    trust = adaptive.trust_scores.get(request.pipeline_id)

    return {
        "status": "recorded",
        "pipeline_id": request.pipeline_id,
        "updated_trust": {
            "level": trust.trust_level.value if trust else "unknown",
            "score": trust.score if trust else 0
        }
    }


@router.get("/analyze")
async def analyze_improvements():
    """
    Analyze all pipelines and suggest improvements.

    GRACE's self-improvement recommendations.
    """
    adaptive = get_adaptive_cicd()
    analysis = await adaptive.analyze_and_improve()

    return analysis


@router.get("/dashboard")
async def get_dashboard():
    """
    Get comprehensive dashboard data.

    Overview of entire adaptive CI/CD system.
    """
    adaptive = get_adaptive_cicd()
    return adaptive.get_dashboard_data()


# =============================================================================
# LLM Integration Endpoints
# =============================================================================

@router.post("/llm/recommend")
async def get_llm_recommendation(pipeline_id: str, context: Optional[Dict[str, Any]] = None):
    """
    Get LLM recommendation for a pipeline.

    Intelligent analysis using LLM orchestration.
    """
    adaptive = get_adaptive_cicd()

    recommendation = await adaptive.get_llm_recommendation(
        pipeline_id=pipeline_id,
        context=context or {}
    )

    return {
        "pipeline_id": pipeline_id,
        "recommendation": recommendation,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/llm/cache")
async def get_llm_cache():
    """
    Get cached LLM recommendations.
    """
    adaptive = get_adaptive_cicd()

    return {
        "count": len(adaptive.llm_cache),
        "cache": [
            {
                "key": k,
                "recommendation": v.get("recommendation"),
                "timestamp": v.get("timestamp")
            }
            for k, v in adaptive.llm_cache.items()
        ]
    }
