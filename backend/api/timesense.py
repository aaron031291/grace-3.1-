"""
TimeSense API Endpoints

Provides REST API access to Grace's time calibration and prediction system.

Endpoints:
- GET /timesense/status - Get engine status and health
- GET /timesense/profiles - List all time profiles
- GET /timesense/profile/{primitive} - Get specific profile
- POST /timesense/estimate - Get time estimate for operation
- POST /timesense/calibrate - Trigger calibration
- GET /timesense/predictions - Get prediction accuracy stats
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from timesense.engine import get_timesense_engine, TimeSenseEngine, EngineStatus
from timesense.primitives import PrimitiveType, PrimitiveCategory, get_primitive_registry
from timesense.predictor import PredictionResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/timesense", tags=["TimeSense"])


# ================================================================
# REQUEST/RESPONSE MODELS
# ================================================================

class EstimateRequest(BaseModel):
    """Request for time estimate."""
    primitive_type: str = Field(..., description="Type of primitive operation")
    size: float = Field(..., description="Size in the primitive's native unit")
    model_name: Optional[str] = Field(None, description="Model name for LLM/embedding")


class FileProcessingEstimateRequest(BaseModel):
    """Request for file processing estimate."""
    file_size_bytes: int = Field(..., description="File size in bytes")
    include_embedding: bool = Field(True, description="Include embedding step")
    model_name: Optional[str] = Field(None, description="Embedding model name")


class RetrievalEstimateRequest(BaseModel):
    """Request for retrieval estimate."""
    query_tokens: int = Field(50, description="Number of tokens in query")
    top_k: int = Field(10, description="Number of results to retrieve")
    num_vectors: int = Field(10000, description="Size of vector collection")


class LLMEstimateRequest(BaseModel):
    """Request for LLM estimate."""
    prompt_tokens: int = Field(..., description="Number of tokens in prompt")
    max_output_tokens: int = Field(..., description="Maximum tokens to generate")
    model_name: Optional[str] = Field(None, description="LLM model name")


class TaskEstimateRequest(BaseModel):
    """Request for composed task estimate."""
    task_id: str = Field(..., description="Unique task identifier")
    description: str = Field(..., description="Task description")
    steps: List[Dict[str, Any]] = Field(..., description="List of steps with primitive_type, size, unit")


class EstimateResponse(BaseModel):
    """Response with time estimate."""
    p50_ms: float = Field(..., description="Median estimate (milliseconds)")
    p90_ms: float = Field(..., description="90th percentile estimate")
    p95_ms: float = Field(..., description="95th percentile estimate")
    p99_ms: float = Field(..., description="99th percentile estimate")
    confidence: float = Field(..., description="Confidence in estimate (0-1)")
    confidence_level: str = Field(..., description="Confidence level (low/medium/high/very_high)")
    human_readable: str = Field(..., description="Human-readable estimate")
    warnings: List[str] = Field(default_factory=list, description="Any warnings")
    is_extrapolation: bool = Field(False, description="Prediction beyond calibrated range")
    is_stale: bool = Field(False, description="Based on old calibration data")


class ProfileResponse(BaseModel):
    """Response with profile information."""
    primitive_type: str
    status: str
    unit: str
    throughput: Optional[float] = None
    overhead_ms: float
    confidence: float
    freshness: float
    last_calibrated: Optional[str] = None
    calibration_count: int
    model: Dict[str, Any]


class CalibrationRequest(BaseModel):
    """Request to trigger calibration."""
    quick: bool = Field(True, description="Run quick calibration")
    primitive_type: Optional[str] = Field(None, description="Specific primitive to recalibrate")


class CalibrationResponse(BaseModel):
    """Response from calibration."""
    duration_seconds: float
    primitives_calibrated: int
    measurements_collected: int
    errors: List[str]


# ================================================================
# ENDPOINTS
# ================================================================

@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """
    Get TimeSense engine status and health.

    Returns current status, profile statistics, and prediction accuracy.
    """
    engine = get_timesense_engine()
    return engine.get_status()


@router.get("/health")
async def get_health() -> Dict[str, Any]:
    """
    Get health check for monitoring.

    Returns simple health status for load balancers.
    """
    engine = get_timesense_engine()
    return engine.get_health()


@router.get("/primitives")
async def list_primitives() -> Dict[str, Any]:
    """
    List all available primitive operations.

    Returns the catalog of primitives that can be benchmarked.
    """
    registry = get_primitive_registry()
    primitives = registry.get_all()

    by_category = {}
    for p in primitives:
        cat = p.category.value
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append({
            'type': p.primitive_type.value,
            'name': p.name,
            'description': p.description,
            'unit': p.unit,
            'available': p.available,
            'tags': p.tags
        })

    return {
        'total': len(primitives),
        'categories': list(by_category.keys()),
        'by_category': by_category
    }


@router.get("/profiles")
async def list_profiles() -> Dict[str, Any]:
    """
    List all calibrated time profiles.

    Returns summary of all profiles with their status.
    """
    engine = get_timesense_engine()
    return engine.get_profile_summary()


@router.get("/profile/{primitive_type}")
async def get_profile(
    primitive_type: str,
    model_name: Optional[str] = None
) -> ProfileResponse:
    """
    Get specific time profile.

    Returns detailed profile information for a primitive.
    """
    try:
        ptype = PrimitiveType(primitive_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown primitive type: {primitive_type}")

    engine = get_timesense_engine()
    profile = engine.get_profile(ptype, model_name)

    if not profile:
        raise HTTPException(status_code=404, detail=f"Profile not found: {primitive_type}")

    data = profile.to_dict()
    return ProfileResponse(
        primitive_type=data['primitive_type'],
        status=data['status'],
        unit=data['unit'],
        throughput=data.get('throughput'),
        overhead_ms=data.get('overhead_ms', 0),
        confidence=data['confidence'],
        freshness=data['freshness'],
        last_calibrated=data.get('last_calibrated'),
        calibration_count=data['calibration_count'],
        model=data.get('scaling_model', {})
    )


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_primitive(request: EstimateRequest) -> EstimateResponse:
    """
    Get time estimate for a primitive operation.

    Provide the primitive type and size to get predicted duration.
    """
    try:
        ptype = PrimitiveType(request.primitive_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown primitive type: {request.primitive_type}")

    engine = get_timesense_engine()

    if not engine.is_ready():
        raise HTTPException(status_code=503, detail="TimeSense engine not ready")

    prediction = engine.predict(ptype, request.size, request.model_name)

    return EstimateResponse(
        p50_ms=prediction.p50_ms,
        p90_ms=prediction.p90_ms,
        p95_ms=prediction.p95_ms,
        p99_ms=prediction.p99_ms,
        confidence=prediction.confidence,
        confidence_level=prediction.confidence_level.value,
        human_readable=prediction.human_readable(),
        warnings=prediction.warnings,
        is_extrapolation=prediction.is_extrapolation,
        is_stale=prediction.is_stale
    )


@router.post("/estimate/file", response_model=EstimateResponse)
async def estimate_file_processing(request: FileProcessingEstimateRequest) -> EstimateResponse:
    """
    Get time estimate for file processing pipeline.

    Estimates: read -> chunk -> embed -> store
    """
    engine = get_timesense_engine()

    if not engine.is_ready():
        raise HTTPException(status_code=503, detail="TimeSense engine not ready")

    prediction = engine.estimate_file_processing(
        request.file_size_bytes,
        request.include_embedding,
        request.model_name
    )

    return EstimateResponse(
        p50_ms=prediction.p50_ms,
        p90_ms=prediction.p90_ms,
        p95_ms=prediction.p95_ms,
        p99_ms=prediction.p99_ms,
        confidence=prediction.confidence,
        confidence_level=prediction.confidence_level.value,
        human_readable=prediction.human_readable(),
        warnings=prediction.warnings,
        is_extrapolation=prediction.is_extrapolation,
        is_stale=prediction.is_stale
    )


@router.post("/estimate/retrieval", response_model=EstimateResponse)
async def estimate_retrieval(request: RetrievalEstimateRequest) -> EstimateResponse:
    """
    Get time estimate for RAG retrieval.

    Estimates: embed query -> vector search -> fetch documents
    """
    engine = get_timesense_engine()

    if not engine.is_ready():
        raise HTTPException(status_code=503, detail="TimeSense engine not ready")

    prediction = engine.estimate_retrieval(
        request.query_tokens,
        request.top_k,
        request.num_vectors
    )

    return EstimateResponse(
        p50_ms=prediction.p50_ms,
        p90_ms=prediction.p90_ms,
        p95_ms=prediction.p95_ms,
        p99_ms=prediction.p99_ms,
        confidence=prediction.confidence,
        confidence_level=prediction.confidence_level.value,
        human_readable=prediction.human_readable(),
        warnings=prediction.warnings,
        is_extrapolation=prediction.is_extrapolation,
        is_stale=prediction.is_stale
    )


@router.post("/estimate/llm", response_model=EstimateResponse)
async def estimate_llm_response(request: LLMEstimateRequest) -> EstimateResponse:
    """
    Get time estimate for LLM response generation.

    Estimates: process prompt -> generate tokens
    """
    engine = get_timesense_engine()

    if not engine.is_ready():
        raise HTTPException(status_code=503, detail="TimeSense engine not ready")

    prediction = engine.estimate_llm_response(
        request.prompt_tokens,
        request.max_output_tokens,
        request.model_name
    )

    return EstimateResponse(
        p50_ms=prediction.p50_ms,
        p90_ms=prediction.p90_ms,
        p95_ms=prediction.p95_ms,
        p99_ms=prediction.p99_ms,
        confidence=prediction.confidence,
        confidence_level=prediction.confidence_level.value,
        human_readable=prediction.human_readable(),
        warnings=prediction.warnings,
        is_extrapolation=prediction.is_extrapolation,
        is_stale=prediction.is_stale
    )


@router.post("/calibrate", response_model=CalibrationResponse)
async def trigger_calibration(
    request: CalibrationRequest,
    background_tasks: BackgroundTasks
) -> CalibrationResponse:
    """
    Trigger calibration of time profiles.

    Can run quick or full calibration, optionally for specific primitive.
    """
    engine = get_timesense_engine()

    if request.primitive_type:
        # Recalibrate specific primitive
        try:
            ptype = PrimitiveType(request.primitive_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown primitive type: {request.primitive_type}")

        count = engine.force_recalibrate(ptype)
        return CalibrationResponse(
            duration_seconds=0,
            primitives_calibrated=count,
            measurements_collected=0,
            errors=[]
        )
    else:
        # Run full calibration
        report = engine.calibration_service.run_startup_calibration(quick=request.quick)
        return CalibrationResponse(
            duration_seconds=report.duration_seconds,
            primitives_calibrated=report.primitives_calibrated,
            measurements_collected=report.measurements_collected,
            errors=report.errors
        )


@router.get("/predictions/accuracy")
async def get_prediction_accuracy(
    primitive_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get prediction accuracy statistics.

    Returns how accurate recent predictions have been.
    """
    engine = get_timesense_engine()
    accuracy = engine.predictor.get_prediction_accuracy()

    return {
        'overall': accuracy,
        'engine_stats': {
            'predictions_within_p95': engine.stats.predictions_within_p95,
            'mean_absolute_error': engine.stats.mean_absolute_error,
            'total_predictions': engine.stats.total_predictions
        }
    }


@router.post("/task/start")
async def start_task_tracking(
    task_id: str,
    primitive_type: Optional[str] = None,
    size: float = 0
) -> Dict[str, Any]:
    """
    Start tracking a task for time measurement.

    Returns prediction if primitive_type is provided.
    """
    engine = get_timesense_engine()

    ptype = None
    if primitive_type:
        try:
            ptype = PrimitiveType(primitive_type)
        except ValueError:
            pass

    prediction = engine.start_task(task_id, ptype, size)

    return {
        'task_id': task_id,
        'tracking': True,
        'prediction': prediction.to_dict() if prediction else None
    }


@router.post("/task/end")
async def end_task_tracking(
    task_id: str,
    actual_size: Optional[float] = None
) -> Dict[str, Any]:
    """
    End tracking a task and record actual duration.

    Returns actual duration and error vs prediction.
    """
    engine = get_timesense_engine()

    task = engine.get_task(task_id)
    prediction = task.prediction if task else None

    actual_ms = engine.end_task(task_id, actual_size)

    if actual_ms is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    error_ratio = None
    if prediction and prediction.p50_ms > 0:
        error_ratio = (actual_ms - prediction.p50_ms) / prediction.p50_ms

    return {
        'task_id': task_id,
        'actual_ms': actual_ms,
        'predicted_ms': prediction.p50_ms if prediction else None,
        'error_ratio': error_ratio,
        'within_p95': actual_ms <= prediction.p95_ms if prediction else None
    }


# ================================================================
# INCLUDE ROUTER IN APP
# ================================================================

def include_timesense_router(app):
    """Include TimeSense router in FastAPI app."""
    app.include_router(router)
    logger.info("[TIMESENSE] API routes registered")
