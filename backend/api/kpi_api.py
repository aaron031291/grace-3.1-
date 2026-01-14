"""
KPI Tracking API.

Endpoints for monitoring and managing Key Performance Indicators.
These endpoints are not exposed to the frontend yet - internal use only.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database.session import get_session

# Try to import KPI tracker, handle if not available
try:
    from ml_intelligence.kpi_tracker import get_kpi_tracker
    KPI_AVAILABLE = True
except ImportError:
    get_kpi_tracker = None
    KPI_AVAILABLE = False

router = APIRouter(prefix="/kpi", tags=["KPI Tracking"])


# ==================== Pydantic Models ====================

class KPIMetricResponse(BaseModel):
    """Response for a single KPI metric."""
    component_name: str = Field(..., description="Name of the component")
    metric_name: str = Field(..., description="Name of the metric")
    value: float = Field(..., description="Current metric value")
    count: int = Field(..., description="Number of times metric was recorded")
    timestamp: str = Field(..., description="Last update timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ComponentKPIsResponse(BaseModel):
    """Response for component KPIs."""
    component_name: str = Field(..., description="Name of the component")
    kpis: Dict[str, KPIMetricResponse] = Field(default_factory=dict, description="KPIs for component")
    trust_score: float = Field(..., description="Trust score derived from KPIs")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class SystemHealthResponse(BaseModel):
    """Response for system-wide health."""
    system_trust_score: float = Field(..., description="Overall system trust score")
    status: str = Field(..., description="System status: excellent, good, fair, poor")
    component_count: int = Field(..., description="Number of tracked components")
    components: Dict[str, Any] = Field(default_factory=dict, description="Per-component health")


class IncrementKPIRequest(BaseModel):
    """Request to increment a KPI."""
    component_name: str = Field(..., description="Name of the component")
    metric_name: str = Field(..., description="Name of the metric")
    value: float = Field(1.0, description="Value to increment by")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")


class RegisterComponentRequest(BaseModel):
    """Request to register a component for KPI tracking."""
    component_name: str = Field(..., description="Name of the component")
    metric_weights: Optional[Dict[str, float]] = Field(None, description="Weights for different metrics")


class TrustScoreResponse(BaseModel):
    """Response for trust score queries."""
    entity: str = Field(..., description="Component name or 'system'")
    trust_score: float = Field(..., description="Trust score (0-1)")
    status: str = Field(..., description="Status level")
    calculated_at: str = Field(..., description="Calculation timestamp")


class KPITrendResponse(BaseModel):
    """Response for KPI trend data."""
    component_name: str = Field(..., description="Name of the component")
    metric_name: str = Field(..., description="Name of the metric")
    current_value: float = Field(..., description="Current value")
    trend: str = Field(..., description="Trend direction: up, down, stable")
    change_percent: float = Field(..., description="Percent change")


# ==================== Endpoints ====================

@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health(session: Session = Depends(get_session)):
    """
    Get system-wide operational health.

    Returns aggregated health status from all tracked components.
    Includes trust scores and status levels for each component.
    """
    try:
        tracker = get_kpi_tracker()
        health = tracker.get_system_health()

        return SystemHealthResponse(
            system_trust_score=health["system_trust_score"],
            status=health["status"],
            component_count=health["component_count"],
            components=health["components"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trust/system", response_model=TrustScoreResponse)
async def get_system_trust_score(session: Session = Depends(get_session)):
    """
    Get system-wide trust score.

    Aggregates all component trust scores into a single system score.
    """
    try:
        tracker = get_kpi_tracker()
        trust_score = tracker.get_system_trust_score()

        # Determine status
        if trust_score >= 0.8:
            status = "excellent"
        elif trust_score >= 0.6:
            status = "good"
        elif trust_score >= 0.4:
            status = "fair"
        else:
            status = "poor"

        return TrustScoreResponse(
            entity="system",
            trust_score=trust_score,
            status=status,
            calculated_at=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trust/{component_name}", response_model=TrustScoreResponse)
async def get_component_trust_score(
    component_name: str,
    session: Session = Depends(get_session)
):
    """
    Get trust score for a specific component.

    Trust score is derived from the component's KPI performance.
    """
    try:
        tracker = get_kpi_tracker()
        trust_score = tracker.get_component_trust_score(component_name)

        # Determine status
        if trust_score >= 0.8:
            status = "excellent"
        elif trust_score >= 0.6:
            status = "good"
        elif trust_score >= 0.4:
            status = "fair"
        else:
            status = "poor"

        return TrustScoreResponse(
            entity=component_name,
            trust_score=trust_score,
            status=status,
            calculated_at=datetime.utcnow().isoformat()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/components", response_model=List[str])
async def list_tracked_components(session: Session = Depends(get_session)):
    """
    List all components being tracked for KPIs.
    """
    try:
        tracker = get_kpi_tracker()
        return list(tracker.components.keys())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/components/{component_name}", response_model=ComponentKPIsResponse)
async def get_component_kpis(
    component_name: str,
    session: Session = Depends(get_session)
):
    """
    Get all KPIs for a specific component.

    Returns detailed KPI metrics with values, counts, and metadata.
    """
    try:
        tracker = get_kpi_tracker()
        component = tracker.get_component_kpis(component_name)

        if not component:
            raise HTTPException(
                status_code=404,
                detail=f"Component '{component_name}' not found"
            )

        kpis = {}
        for metric_name, kpi in component.kpis.items():
            kpis[metric_name] = KPIMetricResponse(
                component_name=kpi.component_name,
                metric_name=kpi.metric_name,
                value=kpi.value,
                count=kpi.count,
                timestamp=kpi.timestamp.isoformat(),
                metadata=kpi.metadata
            )

        return ComponentKPIsResponse(
            component_name=component.component_name,
            kpis=kpis,
            trust_score=component.get_trust_score(),
            created_at=component.created_at.isoformat(),
            updated_at=component.updated_at.isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/components/{component_name}/signal")
async def get_component_health_signal(
    component_name: str,
    session: Session = Depends(get_session)
):
    """
    Get operational health signal for a component.

    Returns aggregated health information including status, trust score,
    and action counts.
    """
    try:
        tracker = get_kpi_tracker()
        signal = tracker.get_health_signal(component_name)
        return signal
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/increment")
async def increment_kpi(
    request: IncrementKPIRequest,
    session: Session = Depends(get_session)
):
    """
    Increment a KPI metric for a component.

    Used internally to track component actions and performance.
    """
    try:
        tracker = get_kpi_tracker()
        tracker.increment_kpi(
            component_name=request.component_name,
            metric_name=request.metric_name,
            value=request.value,
            metadata=request.metadata
        )

        return {
            "status": "success",
            "component": request.component_name,
            "metric": request.metric_name,
            "incremented_by": request.value
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register")
async def register_component(
    request: RegisterComponentRequest,
    session: Session = Depends(get_session)
):
    """
    Register a component for KPI tracking.

    Optionally specify metric weights for trust score calculation.
    """
    try:
        tracker = get_kpi_tracker()
        tracker.register_component(
            component_name=request.component_name,
            metric_weights=request.metric_weights
        )

        return {
            "status": "success",
            "component": request.component_name,
            "weights": request.metric_weights or "default"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_kpi_summary(session: Session = Depends(get_session)):
    """
    Get complete KPI summary for all components.

    Returns comprehensive view of all tracked metrics and trust scores.
    """
    try:
        tracker = get_kpi_tracker()
        return tracker.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/{component_name}/{metric_name}")
async def get_specific_metric(
    component_name: str,
    metric_name: str,
    session: Session = Depends(get_session)
):
    """
    Get a specific metric for a component.
    """
    try:
        tracker = get_kpi_tracker()
        component = tracker.get_component_kpis(component_name)

        if not component:
            raise HTTPException(
                status_code=404,
                detail=f"Component '{component_name}' not found"
            )

        if metric_name not in component.kpis:
            raise HTTPException(
                status_code=404,
                detail=f"Metric '{metric_name}' not found for component '{component_name}'"
            )

        kpi = component.kpis[metric_name]
        return {
            "component_name": kpi.component_name,
            "metric_name": kpi.metric_name,
            "value": kpi.value,
            "count": kpi.count,
            "timestamp": kpi.timestamp.isoformat(),
            "metadata": kpi.metadata
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-increment")
async def batch_increment_kpis(
    increments: List[IncrementKPIRequest],
    session: Session = Depends(get_session)
):
    """
    Batch increment multiple KPIs at once.

    Useful for tracking multiple metrics from a single operation.
    """
    try:
        tracker = get_kpi_tracker()
        results = []

        for req in increments:
            tracker.increment_kpi(
                component_name=req.component_name,
                metric_name=req.metric_name,
                value=req.value,
                metadata=req.metadata
            )
            results.append({
                "component": req.component_name,
                "metric": req.metric_name,
                "incremented_by": req.value
            })

        return {
            "status": "success",
            "count": len(results),
            "increments": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_kpi_dashboard(session: Session = Depends(get_session)):
    """
    Get dashboard-ready KPI data.

    Returns formatted data suitable for visualization in a dashboard.
    """
    try:
        tracker = get_kpi_tracker()
        health = tracker.get_system_health()

        # Build dashboard data
        dashboard = {
            "system": {
                "trust_score": health["system_trust_score"],
                "status": health["status"],
                "component_count": health["component_count"]
            },
            "components": [],
            "top_performers": [],
            "needs_attention": [],
            "timestamp": datetime.utcnow().isoformat()
        }

        # Process each component
        for name, comp_health in health["components"].items():
            comp_data = {
                "name": name,
                "trust_score": comp_health["trust_score"],
                "status": comp_health["status"],
                "total_actions": comp_health.get("total_actions", 0),
                "kpi_count": comp_health.get("kpi_count", 0)
            }
            dashboard["components"].append(comp_data)

            # Categorize
            if comp_health["trust_score"] >= 0.8:
                dashboard["top_performers"].append(name)
            elif comp_health["trust_score"] < 0.4:
                dashboard["needs_attention"].append(name)

        # Sort components by trust score
        dashboard["components"].sort(key=lambda x: x["trust_score"], reverse=True)

        return dashboard
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
