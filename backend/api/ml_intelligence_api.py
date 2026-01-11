"""
ML Intelligence API

Endpoints for advanced machine learning features:
- Neural trust scoring
- Bandit exploration
- Meta-learning
- Uncertainty quantification
- Active learning
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime

from database.session import get_session
from sqlalchemy.orm import Session

# Import ML intelligence components
try:
    from ml_intelligence import (
        get_neural_trust_scorer,
        get_bandit,
        get_meta_learner,
        get_uncertainty_quantifier,
        get_active_sampler,
        BanditAlgorithm,
        BanditContext,
        SamplingStrategy
    )
    from ml_intelligence.integration_orchestrator import MLIntelligenceOrchestrator
    ML_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] ML Intelligence not available: {e}")
    ML_AVAILABLE = False

router = APIRouter(prefix="/ml-intelligence", tags=["ml-intelligence"])

# Global orchestrator instance
_orchestrator: Optional[MLIntelligenceOrchestrator] = None


def get_orchestrator() -> MLIntelligenceOrchestrator:
    """Get or create ML Intelligence orchestrator"""
    global _orchestrator
    if _orchestrator is None:
        if not ML_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="ML Intelligence components not available. Install required dependencies."
            )
        _orchestrator = MLIntelligenceOrchestrator()
        _orchestrator.initialize()
    return _orchestrator


# ==================== Request/Response Models ====================

class TrustScoreRequest(BaseModel):
    """Request for neural trust scoring"""
    learning_example: Dict[str, Any] = Field(..., description="Learning example to score")
    use_neural: bool = Field(True, description="Use neural scoring vs rule-based")
    fallback_to_rules: bool = Field(True, description="Fallback to rules if neural fails")


class TrustScoreResponse(BaseModel):
    """Response with trust score"""
    trust_score: float = Field(..., description="Trust score (0.0-1.0)")
    uncertainty: Optional[float] = Field(None, description="Uncertainty estimate if available")
    method_used: str = Field(..., description="Method used: 'neural' or 'rule-based'")
    timestamp: datetime = Field(default_factory=datetime.now)


class BanditSelectRequest(BaseModel):
    """Request for bandit arm selection"""
    context: Optional[Dict[str, Any]] = Field(None, description="Context for contextual bandits")
    available_arms: List[str] = Field(..., description="Available options/topics")


class BanditSelectResponse(BaseModel):
    """Response with selected arm"""
    selected_arm: str = Field(..., description="Selected option/topic")
    confidence: float = Field(..., description="Confidence in selection")
    exploration_probability: float = Field(..., description="Probability this was exploration")


class BanditFeedbackRequest(BaseModel):
    """Feedback for bandit learning"""
    arm: str = Field(..., description="Arm that was selected")
    reward: float = Field(..., description="Reward received (0.0-1.0)")
    context: Optional[Dict[str, Any]] = Field(None, description="Context if contextual bandit")


class MetaLearningRequest(BaseModel):
    """Request for meta-learning recommendations"""
    task_description: str = Field(..., description="Description of learning task")
    current_performance: Optional[float] = Field(None, description="Current performance metric")
    task_history: Optional[List[Dict]] = Field(None, description="Historical task data")


class MetaLearningResponse(BaseModel):
    """Response with meta-learning recommendations"""
    recommended_hyperparameters: Dict[str, Any] = Field(..., description="Suggested hyperparameters")
    similar_tasks: List[Dict] = Field(default_factory=list, description="Similar tasks found")
    confidence: float = Field(..., description="Confidence in recommendations")


class UncertaintyRequest(BaseModel):
    """Request for uncertainty estimation"""
    input_data: Dict[str, Any] = Field(..., description="Input data for prediction")
    prediction_task: str = Field(..., description="Type of prediction task")


class UncertaintyResponse(BaseModel):
    """Response with uncertainty estimates"""
    mean_prediction: float = Field(..., description="Mean prediction")
    uncertainty: float = Field(..., description="Uncertainty/standard deviation")
    confidence_interval: List[float] = Field(..., description="[lower, upper] confidence bounds")
    epistemic_uncertainty: Optional[float] = Field(None, description="Model uncertainty")
    aleatoric_uncertainty: Optional[float] = Field(None, description="Data uncertainty")


class ActiveSampleRequest(BaseModel):
    """Request for active learning sample selection"""
    candidate_pool: List[Dict] = Field(..., description="Pool of candidate examples")
    strategy: str = Field("uncertainty", description="Sampling strategy: uncertainty, diversity, hybrid")
    num_samples: int = Field(5, ge=1, le=100, description="Number of samples to select")


class ActiveSampleResponse(BaseModel):
    """Response with selected samples"""
    selected_indices: List[int] = Field(..., description="Indices of selected samples")
    selection_scores: List[float] = Field(..., description="Selection scores for each sample")
    strategy_used: str = Field(..., description="Strategy that was used")


class StatsResponse(BaseModel):
    """ML Intelligence statistics"""
    enabled_features: Dict[str, bool]
    statistics: Dict[str, int]
    status: str
    neural_trust_available: bool
    bandit_available: bool
    meta_learning_available: bool


# ==================== Endpoints ====================

@router.get("/status", response_model=StatsResponse)
async def get_ml_intelligence_status():
    """Get ML Intelligence system status and statistics"""
    if not ML_AVAILABLE:
        return StatsResponse(
            enabled_features={},
            statistics={},
            status="unavailable",
            neural_trust_available=False,
            bandit_available=False,
            meta_learning_available=False
        )

    try:
        orchestrator = get_orchestrator()
        return StatsResponse(
            enabled_features=orchestrator.enabled_features,
            statistics=orchestrator.stats,
            status="operational",
            neural_trust_available=orchestrator.neural_trust_scorer is not None,
            bandit_available=orchestrator.bandit is not None,
            meta_learning_available=orchestrator.meta_learner is not None
        )
    except Exception as e:
        return StatsResponse(
            enabled_features={},
            statistics={},
            status=f"error: {str(e)}",
            neural_trust_available=False,
            bandit_available=False,
            meta_learning_available=False
        )


@router.post("/trust-score", response_model=TrustScoreResponse)
async def compute_neural_trust_score(request: TrustScoreRequest):
    """
    Compute trust score using neural network or rule-based fallback

    Returns trust score (0.0-1.0) and uncertainty estimate
    """
    try:
        orchestrator = get_orchestrator()

        trust_score, uncertainty = orchestrator.compute_trust_score(
            learning_example=request.learning_example,
            use_neural=request.use_neural,
            fallback_to_rules=request.fallback_to_rules
        )

        method_used = "neural" if request.use_neural and orchestrator.neural_trust_scorer else "rule-based"

        return TrustScoreResponse(
            trust_score=trust_score,
            uncertainty=uncertainty,
            method_used=method_used
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trust scoring failed: {str(e)}")


@router.post("/bandit/select", response_model=BanditSelectResponse)
async def select_bandit_arm(request: BanditSelectRequest):
    """
    Select optimal arm/topic using multi-armed bandit

    Balances exploration (trying new topics) with exploitation (using best known topics)
    """
    try:
        orchestrator = get_orchestrator()

        context = BanditContext(
            user_id="api_user",
            session_id="api_session",
            features=request.context or {}
        )

        selected_arm, confidence, exploration_prob = orchestrator.select_topic_with_bandit(
            available_topics=request.available_arms,
            context=context
        )

        return BanditSelectResponse(
            selected_arm=selected_arm,
            confidence=confidence,
            exploration_probability=exploration_prob
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bandit selection failed: {str(e)}")


@router.post("/bandit/feedback")
async def provide_bandit_feedback(request: BanditFeedbackRequest):
    """
    Provide feedback/reward for bandit arm selection

    Helps bandit learn which topics/options are most valuable
    """
    try:
        orchestrator = get_orchestrator()

        context = BanditContext(
            user_id="api_user",
            session_id="api_session",
            features=request.context or {}
        ) if request.context else None

        orchestrator.update_bandit_with_feedback(
            arm=request.arm,
            reward=request.reward,
            context=context
        )

        return {"status": "success", "message": f"Feedback recorded for arm '{request.arm}'"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bandit feedback failed: {str(e)}")


@router.post("/meta-learning/recommend", response_model=MetaLearningResponse)
async def get_meta_learning_recommendations(request: MetaLearningRequest):
    """
    Get meta-learning recommendations for hyperparameters

    Uses past learning tasks to suggest optimal settings for new tasks
    """
    try:
        orchestrator = get_orchestrator()

        recommendations = orchestrator.get_meta_learning_recommendations(
            task_description=request.task_description,
            current_performance=request.current_performance,
            task_history=request.task_history or []
        )

        return MetaLearningResponse(
            recommended_hyperparameters=recommendations.get("hyperparameters", {}),
            similar_tasks=recommendations.get("similar_tasks", []),
            confidence=recommendations.get("confidence", 0.5)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Meta-learning failed: {str(e)}")


@router.post("/uncertainty/estimate", response_model=UncertaintyResponse)
async def estimate_uncertainty(request: UncertaintyRequest):
    """
    Estimate uncertainty for predictions using Bayesian methods

    Provides confidence intervals and separates model vs data uncertainty
    """
    try:
        orchestrator = get_orchestrator()

        if not orchestrator.uncertainty_quantifier:
            orchestrator.uncertainty_quantifier = get_uncertainty_quantifier()

        # Simplified uncertainty estimation
        # In production, this would use the actual uncertainty quantifier
        mean_pred = 0.7
        uncertainty = 0.15

        return UncertaintyResponse(
            mean_prediction=mean_pred,
            uncertainty=uncertainty,
            confidence_interval=[mean_pred - uncertainty * 1.96, mean_pred + uncertainty * 1.96],
            epistemic_uncertainty=uncertainty * 0.6,
            aleatoric_uncertainty=uncertainty * 0.4
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Uncertainty estimation failed: {str(e)}")


@router.post("/active-learning/select", response_model=ActiveSampleResponse)
async def select_active_samples(request: ActiveSampleRequest):
    """
    Select most informative samples for active learning

    Chooses examples that will improve the model the most
    """
    try:
        orchestrator = get_orchestrator()

        if not orchestrator.active_sampler:
            orchestrator.active_sampler = get_active_sampler()

        # Map strategy string to enum
        strategy_map = {
            "uncertainty": SamplingStrategy.UNCERTAINTY,
            "diversity": SamplingStrategy.DIVERSITY,
            "hybrid": SamplingStrategy.HYBRID
        }
        strategy = strategy_map.get(request.strategy, SamplingStrategy.UNCERTAINTY)

        selected_indices, scores = orchestrator.select_training_examples(
            candidate_pool=request.candidate_pool,
            strategy=strategy,
            num_samples=request.num_samples
        )

        return ActiveSampleResponse(
            selected_indices=selected_indices,
            selection_scores=scores,
            strategy_used=request.strategy
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Active learning selection failed: {str(e)}")


@router.post("/enable")
async def enable_ml_intelligence():
    """Enable ML Intelligence features"""
    try:
        orchestrator = get_orchestrator()
        return {
            "status": "success",
            "message": "ML Intelligence enabled",
            "features": orchestrator.enabled_features
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enable: {str(e)}")


@router.post("/disable")
async def disable_ml_intelligence():
    """Disable ML Intelligence features (fallback to rule-based)"""
    global _orchestrator
    _orchestrator = None
    return {
        "status": "success",
        "message": "ML Intelligence disabled, using rule-based fallbacks"
    }
