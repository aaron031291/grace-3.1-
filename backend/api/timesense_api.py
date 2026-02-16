"""
TimeSense API - Grace's Understanding of Time, Scale, and Capacity

Endpoints:
- /api/timesense/dashboard - Full dashboard (timing + capacity + rates)
- /api/timesense/understand/{size_bytes} - What does this data size mean?
- /api/timesense/estimate/{operation}/{size_bytes} - How long will this take?
- /api/timesense/capacity - Grace's memory and storage self-awareness
- /api/timesense/can-handle/{size_bytes} - Can Grace handle this data?
- /api/timesense/rates - Processing rates per operation (MB/s)
- /api/timesense/context - Current temporal context
- /api/timesense/predict/{operation} - Predict operation duration
- /api/timesense/cost/{operation} - Estimate operation cost
- /api/timesense/anomalies - Temporal anomalies
- /api/timesense/ooda - OODA cycle timing
"""

from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/api/timesense", tags=["TimeSense"])


@router.get("/dashboard")
async def timesense_dashboard() -> Dict[str, Any]:
    """Full TimeSense dashboard: timing, capacity, rates, scale understanding."""
    from cognitive.timesense import get_timesense
    return get_timesense().get_dashboard()


@router.get("/understand/{size_bytes}")
async def understand_data_size(size_bytes: float) -> Dict[str, Any]:
    """Grace explains what a data size means and how she'd handle it.

    Example: /api/timesense/understand/1073741824 (1GB)
    Returns: analogy, processing time estimates, feasibility assessment.
    """
    from cognitive.timesense import get_timesense
    return get_timesense().understand_data_size(size_bytes)


@router.get("/estimate/{operation}/{size_bytes}")
async def estimate_task_time(operation: str, size_bytes: float) -> Dict[str, Any]:
    """Estimate how long an operation will take for a given data size.

    Example: /api/timesense/estimate/ingestion.embed/104857600 (100MB)
    Returns: estimated time based on Grace's measured processing rate.
    """
    from cognitive.timesense import get_timesense
    return get_timesense().estimate_task_time(operation, size_bytes)


@router.get("/capacity")
async def capacity() -> Dict[str, Any]:
    """Grace's memory and storage self-awareness.

    Returns: RAM (total/available), disk (total/available),
    knowledge base size, and self-assessment.
    """
    from cognitive.timesense import get_timesense
    return get_timesense().get_capacity().to_dict()


@router.get("/can-handle/{size_bytes}")
async def can_handle(size_bytes: float) -> Dict[str, Any]:
    """Can Grace handle this amount of data right now?

    Grace's honest self-assessment of her current capacity.
    """
    from cognitive.timesense import get_timesense
    return get_timesense().can_handle(size_bytes)


@router.get("/rates")
async def processing_rates() -> Dict[str, Any]:
    """Grace's measured processing rates (MB/s) per operation type."""
    from cognitive.timesense import get_timesense
    return get_timesense().get_processing_rates()


@router.get("/context")
async def temporal_context() -> Dict[str, Any]:
    """Grace's current temporal awareness."""
    from cognitive.timesense import get_timesense
    return get_timesense().get_temporal_context().to_dict()


@router.get("/predict/{operation}")
async def predict_duration(operation: str) -> Dict[str, Any]:
    """Predict how long an operation will take based on history."""
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
    """Temporal anomalies - operations outside expected range."""
    from cognitive.timesense import get_timesense
    ts = get_timesense()
    return {
        "anomalies": ts.get_anomalies(limit),
        "total_detected": ts._stats["total_anomalies_detected"],
    }


@router.get("/ooda")
async def ooda_timing() -> Dict[str, Any]:
    """OODA cycle timing breakdown per phase."""
    from cognitive.timesense import get_timesense
    return get_timesense()._ooda_timer.get_stats()


@router.get("/stats")
async def timesense_stats() -> Dict[str, Any]:
    """TimeSense engine statistics."""
    from cognitive.timesense import get_timesense
    return get_timesense().get_stats()


# =============================================================================
# ENHANCED CAPABILITIES
# =============================================================================

@router.get("/plan/{task_type}/{size_bytes}")
async def plan_task(task_type: str, size_bytes: float) -> Dict[str, Any]:
    """Plan a complex task with step-by-step time estimates.

    Grace breaks down a task and estimates each step.
    task_type: ingest_repository, ingest_document, chat_query,
               knowledge_base_rebuild, web_scrape
    """
    from cognitive.timesense import get_timesense
    ts = get_timesense()
    plan = ts.task_planner.plan(task_type, size_bytes)
    return plan.to_dict()


@router.get("/plan/types")
async def available_task_types() -> Dict[str, Any]:
    """List available task types for planning."""
    from cognitive.timesense import get_timesense
    ts = get_timesense()
    return {"task_types": ts.task_planner.get_available_tasks()}


@router.get("/throughput")
async def throughput_budgets() -> Dict[str, Any]:
    """Get throughput budgets for all operations.

    Shows how many concurrent operations Grace can safely handle.
    """
    from cognitive.timesense import get_timesense
    ts = get_timesense()
    return ts.throughput.get_all_budgets()


@router.get("/throughput/{operation}")
async def throughput_budget(operation: str) -> Dict[str, Any]:
    """Get throughput budget for a specific operation."""
    from cognitive.timesense import get_timesense
    ts = get_timesense()
    return ts.throughput.get_budget(operation).to_dict()


@router.get("/memory-impact/{operation}/{size_bytes}")
async def predict_memory_impact(operation: str, size_bytes: float) -> Dict[str, Any]:
    """Predict memory impact before starting a heavy operation.

    Grace tells you: 'This will push RAM to 85%. Consider batching.'
    """
    from cognitive.timesense import get_timesense
    ts = get_timesense()
    return ts.memory_predictor.predict_memory_impact(operation, size_bytes)


@router.get("/trends")
async def performance_trends(days: int = 7) -> Dict[str, Any]:
    """Is Grace getting faster or slower? Performance trends over time."""
    from cognitive.timesense import get_timesense
    ts = get_timesense()
    return ts.trends.get_all_trends(days)


@router.get("/trends/{operation}")
async def operation_trend(operation: str, days: int = 7) -> Dict[str, Any]:
    """Performance trend for a specific operation."""
    from cognitive.timesense import get_timesense
    ts = get_timesense()
    return ts.trends.get_trend(operation, days)


# =============================================================================
# DEEP CAPABILITIES
# =============================================================================

@router.get("/learning-curves")
async def all_learning_curves() -> Dict[str, Any]:
    """Grace's learning curves - is she developing muscle memory?"""
    from cognitive.timesense import get_timesense
    return get_timesense().learning_curves.get_all_curves()


@router.get("/learning-curves/{operation}")
async def learning_curve(operation: str) -> Dict[str, Any]:
    """Learning curve for a specific operation."""
    from cognitive.timesense import get_timesense
    return get_timesense().learning_curves.get_curve(operation)


@router.get("/scaling")
async def predictive_scaling() -> Dict[str, Any]:
    """Predict when Grace will exhaust disk capacity."""
    from cognitive.timesense import get_timesense
    ts = get_timesense()
    cap = ts.get_capacity()
    return ts.scaler.predict_disk_exhaustion(cap.available_disk_bytes)


@router.get("/schedule")
async def optimal_schedule(duration_hours: int = 2) -> Dict[str, Any]:
    """Find the optimal time window for heavy operations."""
    from cognitive.timesense import get_timesense
    return get_timesense().scheduler.get_optimal_window(duration_hours)


@router.get("/schedule/now")
async def is_good_time_now() -> Dict[str, Any]:
    """Is right now a good time for heavy operations?"""
    from cognitive.timesense import get_timesense
    return get_timesense().scheduler.is_good_time_now()


@router.get("/dependencies/{task_type}")
async def operation_dependencies(task_type: str) -> Dict[str, Any]:
    """Get execution order with parallelization for a task type."""
    from cognitive.timesense import get_timesense
    ts = get_timesense()
    templates = ts.task_planner.TASK_TEMPLATES
    if task_type in templates:
        ops = [step[1] for step in templates[task_type]]
        return ts.dep_graph.get_execution_order(ops)
    return {"error": f"Unknown task type: {task_type}"}


@router.post("/save")
async def save_state() -> Dict[str, Any]:
    """Save TimeSense state to disk."""
    from cognitive.timesense import get_timesense
    success = get_timesense().save_state()
    return {"saved": success}


@router.post("/load")
async def load_state() -> Dict[str, Any]:
    """Load TimeSense state from disk."""
    from cognitive.timesense import get_timesense
    success = get_timesense().load_state()
    return {"loaded": success}
