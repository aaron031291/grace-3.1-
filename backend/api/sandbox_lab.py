"""
Autonomous Sandbox Lab API

Endpoints for Grace's self-improvement experimentation system

Classes:
- `ProposeExperimentRequest`
- `RecordImplementationRequest`
- `StartTrialRequest`
- `RecordTrialResultRequest`
- `ApprovalRequest`
- `ExperimentResponse`
- `ExperimentListResponse`
- `LabStatsResponse`
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

from cognitive.autonomous_sandbox_lab import (
    get_sandbox_lab,
    Experiment,
    ExperimentStatus,
    ExperimentType,
    TrustThreshold
)
from cognitive.continuous_learning_orchestrator import (
    get_continuous_orchestrator,
    start_continuous_learning,
    stop_continuous_learning
)

router = APIRouter(prefix="/sandbox-lab", tags=["sandbox-lab"])


# ==================== Request/Response Models ====================

class ProposeExperimentRequest(BaseModel):
    """Request to propose a new experiment"""
    name: str = Field(..., description="Experiment name")
    description: str = Field(..., description="What this experiment does")
    experiment_type: str = Field(..., description="Type: algorithm_improvement, new_capability, etc.")
    motivation: str = Field(..., description="Why Grace thinks this is valuable")
    proposed_by: str = Field("grace_mirror", description="Who proposed this")
    initial_trust_score: float = Field(0.5, ge=0.0, le=1.0, description="Initial trust (0.0-1.0)")


class RecordImplementationRequest(BaseModel):
    """Request to record sandbox implementation"""
    implementation_code: str = Field(..., description="Implementation code/algorithm")
    files_modified: List[str] = Field(..., description="List of files that would be modified")


class StartTrialRequest(BaseModel):
    """Request to start 90-day trial"""
    baseline_metrics: Dict[str, float] = Field(..., description="Baseline performance metrics")


class RecordTrialResultRequest(BaseModel):
    """Request to record trial result"""
    success: bool = Field(..., description="Was this trial data point successful?")
    metrics: Optional[Dict[str, float]] = Field(None, description="Updated performance metrics")


class ApprovalRequest(BaseModel):
    """Request to approve/reject experiment"""
    approved_by: str = Field("user", description="Who approved this")
    notes: Optional[str] = Field(None, description="Approval notes/reasoning")


class ExperimentResponse(BaseModel):
    """Response with experiment details"""
    experiment_id: str
    name: str
    description: str
    experiment_type: str
    status: str
    proposed_by: str
    motivation: str
    created_at: datetime
    trust_scores: Dict[str, Any]
    metrics: Dict[str, Any]
    trial: Dict[str, Any]
    approval: Dict[str, Any]
    gates: Dict[str, bool]


class ExperimentListResponse(BaseModel):
    """Response with list of experiments"""
    experiments: List[Dict[str, Any]]
    total: int
    by_status: Dict[str, int]


class LabStatsResponse(BaseModel):
    """Response with lab statistics"""
    total_experiments: int
    sandbox_experiments: int
    trial_experiments: int
    production_experiments: int
    rejected_experiments: int
    active_trials_count: int
    awaiting_approval_count: int
    average_trust_score: float
    average_improvement: float
    auto_approved: int
    user_approved: int


# ==================== Endpoints ====================

@router.get("/status", response_model=LabStatsResponse)
async def get_lab_status():
    """
    Get sandbox lab status and statistics

    Shows how many experiments Grace is running autonomously
    """
    lab = get_sandbox_lab()
    stats = lab.get_statistics()

    return LabStatsResponse(**stats)


@router.post("/experiments/propose", response_model=ExperimentResponse)
async def propose_experiment(request: ProposeExperimentRequest):
    """
    Propose a new experiment

    Grace (via Mirror) proposes self-improvement experiments
    """
    lab = get_sandbox_lab()

    try:
        exp_type = ExperimentType(request.experiment_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid experiment_type. Must be one of: {[e.value for e in ExperimentType]}"
        )

    exp = lab.propose_experiment(
        name=request.name,
        description=request.description,
        experiment_type=exp_type,
        motivation=request.motivation,
        proposed_by=request.proposed_by,
        initial_trust_score=request.initial_trust_score
    )

    return ExperimentResponse(**exp.to_dict())


@router.post("/experiments/{experiment_id}/sandbox", response_model=ExperimentResponse)
async def enter_sandbox(experiment_id: str):
    """
    Move experiment to sandbox for testing

    Experiment must have trust score >= 0.3
    """
    lab = get_sandbox_lab()

    if not lab.enter_sandbox(experiment_id):
        exp = lab.get_experiment(experiment_id)
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")

        raise HTTPException(
            status_code=400,
            detail=f"Cannot enter sandbox. Trust score {exp.current_trust_score:.2f} < {TrustThreshold.SANDBOX_ENTRY}"
        )

    exp = lab.get_experiment(experiment_id)
    return ExperimentResponse(**exp.to_dict())


@router.post("/experiments/{experiment_id}/implementation")
async def record_implementation(experiment_id: str, request: RecordImplementationRequest):
    """
    Record implementation code for sandbox experiment

    Grace writes the actual code for the improvement
    """
    lab = get_sandbox_lab()

    if not lab.record_sandbox_implementation(
        experiment_id,
        request.implementation_code,
        request.files_modified
    ):
        raise HTTPException(
            status_code=400,
            detail="Cannot record implementation. Experiment must be in sandbox status."
        )

    exp = lab.get_experiment(experiment_id)
    return ExperimentResponse(**exp.to_dict())


@router.post("/experiments/{experiment_id}/trial", response_model=ExperimentResponse)
async def start_trial(experiment_id: str, request: StartTrialRequest):
    """
    Start 90-day trial with live data

    Experiment must have:
    - Trust score >= 0.6
    - Implementation code recorded
    """
    lab = get_sandbox_lab()

    if not lab.start_trial(experiment_id, request.baseline_metrics):
        exp = lab.get_experiment(experiment_id)
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")

        if not exp.implementation_code:
            raise HTTPException(status_code=400, detail="Implementation code not recorded")

        raise HTTPException(
            status_code=400,
            detail=f"Cannot start trial. Trust score {exp.current_trust_score:.2f} < {TrustThreshold.TRIAL_ENTRY}"
        )

    exp = lab.get_experiment(experiment_id)
    return ExperimentResponse(**exp.to_dict())


@router.post("/experiments/{experiment_id}/trial/record")
async def record_trial_result(experiment_id: str, request: RecordTrialResultRequest):
    """
    Record a trial data point

    Called automatically as Grace uses the experimental algorithm on live data
    """
    lab = get_sandbox_lab()

    if not lab.record_trial_result(
        experiment_id,
        request.success,
        request.metrics
    ):
        raise HTTPException(
            status_code=400,
            detail="Cannot record trial result. Experiment must be in trial status."
        )

    exp = lab.get_experiment(experiment_id)
    return ExperimentResponse(**exp.to_dict())


@router.post("/experiments/{experiment_id}/approve")
async def approve_experiment(experiment_id: str, request: ApprovalRequest):
    """
    Approve experiment for production

    User approves Grace's self-improvement for production deployment
    """
    lab = get_sandbox_lab()

    if not lab.approve_for_production(
        experiment_id,
        request.approved_by,
        request.notes
    ):
        exp = lab.get_experiment(experiment_id)
        if not exp:
            raise HTTPException(status_code=404, detail="Experiment not found")

        raise HTTPException(
            status_code=400,
            detail="Cannot approve. Experiment must pass 90-day trial first."
        )

    # Immediately promote to production
    lab.promote_to_production(experiment_id)

    exp = lab.get_experiment(experiment_id)
    return ExperimentResponse(**exp.to_dict())


@router.post("/experiments/{experiment_id}/reject")
async def reject_experiment(experiment_id: str):
    """
    Reject experiment

    User decides not to deploy Grace's improvement
    """
    lab = get_sandbox_lab()
    exp = lab.get_experiment(experiment_id)

    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    exp.status = ExperimentStatus.REJECTED
    lab._save_experiment(exp)

    return {
        "status": "rejected",
        "experiment_id": experiment_id,
        "message": "Experiment rejected by user"
    }


@router.get("/experiments", response_model=ExperimentListResponse)
async def list_experiments(
    status: Optional[str] = None,
    experiment_type: Optional[str] = None
):
    """
    List all experiments

    Filter by status or type
    """
    lab = get_sandbox_lab()

    status_filter = None
    if status:
        try:
            status_filter = ExperimentStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in ExperimentStatus]}"
            )

    type_filter = None
    if experiment_type:
        try:
            type_filter = ExperimentType(experiment_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid experiment_type. Must be one of: {[t.value for t in ExperimentType]}"
            )

    experiments = lab.list_experiments(status_filter, type_filter)

    # Count by status
    by_status = {}
    for exp in experiments:
        status_value = exp.status.value
        by_status[status_value] = by_status.get(status_value, 0) + 1

    return ExperimentListResponse(
        experiments=[exp.to_dict() for exp in experiments],
        total=len(experiments),
        by_status=by_status
    )


@router.get("/experiments/{experiment_id}", response_model=ExperimentResponse)
async def get_experiment(experiment_id: str):
    """Get experiment details"""
    lab = get_sandbox_lab()
    exp = lab.get_experiment(experiment_id)

    if not exp:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return ExperimentResponse(**exp.to_dict())


@router.get("/experiments/active/trials")
async def get_active_trials():
    """
    Get all active trial experiments

    Shows experiments currently running 90-day trials
    """
    lab = get_sandbox_lab()
    trials = lab.get_active_trials()

    return {
        "active_trials": [exp.to_dict() for exp in trials],
        "count": len(trials)
    }


@router.get("/experiments/awaiting/approval")
async def get_awaiting_approval():
    """
    Get experiments awaiting user approval

    Shows which self-improvements Grace wants to deploy
    """
    lab = get_sandbox_lab()
    awaiting = lab.get_awaiting_approval()

    return {
        "awaiting_approval": [exp.to_dict() for exp in awaiting],
        "count": len(awaiting),
        "auto_approve_candidates": [
            exp.to_dict() for exp in awaiting if exp.can_auto_approve()
        ]
    }


@router.get("/thresholds")
async def get_trust_thresholds():
    """
    Get trust score thresholds for experiment gates

    Shows what trust scores are needed for each stage
    """
    return {
        "sandbox_entry": TrustThreshold.SANDBOX_ENTRY,
        "trial_entry": TrustThreshold.TRIAL_ENTRY,
        "production_ready": TrustThreshold.PRODUCTION_READY,
        "auto_approve": TrustThreshold.AUTO_APPROVE,
        "descriptions": {
            "sandbox_entry": "Minimum trust to enter sandbox testing",
            "trial_entry": "Minimum trust to start 90-day live trial",
            "production_ready": "Minimum trust for production promotion",
            "auto_approve": "Trust level for automatic approval (still notifies user)"
        }
    }


@router.get("/continuous/status")
async def get_continuous_learning_status():
    """
    Get continuous learning orchestrator status

    Shows Grace's continuous autonomous learning loop
    """
    orchestrator = get_continuous_orchestrator()
    return orchestrator.get_status()


@router.post("/continuous/start")
async def start_continuous():
    """
    Start continuous autonomous learning

    Grace will continuously:
    - Ingest new data
    - Learn from it
    - Propose experiments via Mirror
    - Run trials
    - Request approval for improvements
    """
    orchestrator = start_continuous_learning()
    return {
        "status": "started",
        "message": "Continuous autonomous learning activated",
        "orchestrator_status": orchestrator.get_status()
    }


@router.post("/continuous/stop")
async def stop_continuous():
    """
    Stop continuous autonomous learning

    Pauses the continuous learning loop
    """
    stop_continuous_learning()
    return {
        "status": "stopped",
        "message": "Continuous autonomous learning paused"
    }


@router.post("/continuous/config")
async def update_continuous_config(config: Dict[str, Any]):
    """
    Update continuous learning configuration

    Adjust intervals, thresholds, and auto-behaviors
    """
    orchestrator = get_continuous_orchestrator()

    for key, value in config.items():
        if key in orchestrator.config:
            orchestrator.config[key] = value

    return {
        "status": "updated",
        "config": orchestrator.config
    }
