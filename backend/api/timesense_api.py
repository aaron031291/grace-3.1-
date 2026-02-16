"""
TimeSense API - Temporal Reasoning Dashboard

Endpoints:
- /api/timesense/dashboard - Full timing dashboard
- /api/timesense/context - Current temporal context
- /api/timesense/predict/{operation} - Predict operation duration
- /api/timesense/cost/{operation} - Estimate operation cost
- /api/timesense/anomalies - Recent temporal anomalies
- /api/timesense/ooda - OODA cycle timing stats
"""

from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/api/timesense", tags=["TimeSense"])


@router.get("/dashboard")
async def timesense_dashboard() -> Dict[str, Any]:
    """Full TimeSense dashboard with all timing data."""
    from cognitive.timesense import get_timesense
    return get_timesense().get_dashboard()


@router.get("/context")
async def temporal_context() -> Dict[str, Any]:
    """Grace's current temporal awareness."""
    from cognitive.timesense import get_timesense
    return get_timesense().get_temporal_context().to_dict()


@router.get("/predict/{operation}")
async def predict_duration(operation: str) -> Dict[str, Any]:
    """Predict how long an operation will take."""
    from cognitive.timesense import get_timesense
    p = get_timesense().predict(operation)
    return {
        "operation": p.operation,
        "predicted_ms": round(p.predicted_ms, 2),
        "confidence": round(p.confidence, 3),
        "lower_bound_ms": round(p.lower_bound_ms, 2),
        "upper_bound_ms": round(p.upper_bound_ms, 2),
        "based_on_samples": p.based_on_samples,
    }


@router.get("/cost/{operation}")
async def estimate_cost(operation: str) -> Dict[str, Any]:
    """Estimate time and compute cost of an operation."""
    from cognitive.timesense import get_timesense
    c = get_timesense().estimate_cost(operation)
    return {
        "operation": c.operation,
        "estimated_time_ms": round(c.estimated_time_ms, 2),
        "estimated_cpu_cost": round(c.estimated_cpu_cost, 3),
        "estimated_memory_bytes": round(c.estimated_memory_bytes, 0),
        "confidence": round(c.confidence, 3),
        "is_expensive": c.is_expensive,
    }


@router.get("/anomalies")
async def temporal_anomalies(limit: int = 50) -> Dict[str, Any]:
    """Recent temporal anomalies."""
    from cognitive.timesense import get_timesense
    ts = get_timesense()
    return {
        "anomalies": ts.get_anomalies(limit),
        "total_detected": ts._stats["total_anomalies_detected"],
    }


@router.get("/ooda")
async def ooda_timing() -> Dict[str, Any]:
    """OODA cycle timing breakdown."""
    from cognitive.timesense import get_timesense
    return get_timesense()._ooda_timer.get_stats()


@router.get("/stats")
async def timesense_stats() -> Dict[str, Any]:
    """TimeSense engine statistics."""
    from cognitive.timesense import get_timesense
    return get_timesense().get_stats()
