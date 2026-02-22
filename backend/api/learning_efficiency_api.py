"""
Learning Efficiency API - Data-to-Insight Ratio Tracking

Tracks and reports how much data is required to gain new insights,
domains, and intelligence.

Classes:
- `DataConsumptionRequest`
- `InsightRecordRequest`
- `EfficiencyMetricsResponse`
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

from database.session import get_session
from cognitive.learning_efficiency_tracker import LearningEfficiencyTracker
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/learning-efficiency", tags=["learning-efficiency"])


# ==================== Request/Response Models ====================

class DataConsumptionRequest(BaseModel):
    """Record data consumption."""
    bytes_consumed: float = Field(..., description="Bytes of data consumed")
    documents_consumed: int = Field(1, description="Number of documents")
    chunks_consumed: int = Field(0, description="Number of chunks")
    domain: Optional[str] = Field(None, description="Domain/category")
    genesis_key_id: Optional[str] = Field(None, description="Genesis Key ID")


class InsightRecordRequest(BaseModel):
    """Record a new insight."""
    insight_type: str = Field(..., description="Type: concept, pattern, skill, domain, procedure")
    description: str = Field(..., description="Description of insight")
    trust_score: float = Field(..., ge=0.0, le=1.0, description="Trust score (0-1)")
    domain: Optional[str] = Field(None, description="Domain/category")
    learning_example_id: Optional[str] = Field(None, description="Learning example ID")
    genesis_key_id: Optional[str] = Field(None, description="Genesis Key ID")
    time_to_insight_seconds: Optional[float] = Field(None, description="Time spent learning before this insight (seconds)")


class EfficiencyMetricsResponse(BaseModel):
    """Learning efficiency metrics."""
    summary: Dict[str, Any]
    efficiency: Dict[str, float]
    domains: Dict[str, Dict[str, Any]]
    domain_efficiency: Dict[str, Dict[str, float]]
    learning_curve: List[Dict[str, float]]
    optimal_paths: Dict[str, Any]


# ==================== Endpoints ====================

@router.post("/record-data-consumption")
async def record_data_consumption(
    request: DataConsumptionRequest,
    session: Session = Depends(get_session)
):
    """
    Record data consumption (called when documents are ingested).
    
    This should be called automatically during ingestion.
    """
    try:
        tracker = LearningEfficiencyTracker(session)
        tracker.record_data_consumption(
            bytes_consumed=request.bytes_consumed,
            documents_consumed=request.documents_consumed,
            chunks_consumed=request.chunks_consumed,
            domain=request.domain,
            genesis_key_id=request.genesis_key_id
        )
        
        return {
            "status": "success",
            "message": "Data consumption recorded",
            "total_bytes": tracker.total_bytes_consumed,
            "total_documents": tracker.total_documents_consumed,
            "total_chunks": tracker.total_chunks_consumed
        }
    except Exception as e:
        logger.error(f"Error recording data consumption: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/record-insight")
async def record_insight(
    request: InsightRecordRequest,
    session: Session = Depends(get_session)
):
    """
    Record a new insight gained.
    
    Called when Grace gains new knowledge:
    - New concept learned
    - Pattern identified
    - Skill acquired
    - Domain mastered
    - Procedure created
    """
    try:
        tracker = LearningEfficiencyTracker(session)
        time_to_insight = None
        if request.time_to_insight_seconds is not None:
            from datetime import timedelta
            time_to_insight = timedelta(seconds=request.time_to_insight_seconds)
        
        insight = tracker.record_insight(
            insight_type=request.insight_type,
            description=request.description,
            trust_score=request.trust_score,
            domain=request.domain,
            learning_example_id=request.learning_example_id,
            genesis_key_id=request.genesis_key_id,
            time_to_insight=time_to_insight
        )
        
        return {
            "status": "success",
            "insight_id": insight.insight_id,
            "data_consumed": insight.data_consumed,
            "total_insights": len(tracker.insights)
        }
    except Exception as e:
        logger.error(f"Error recording insight: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics", response_model=EfficiencyMetricsResponse)
async def get_efficiency_metrics(
    domain: Optional[str] = None,
    time_window_hours: Optional[int] = None,
    session: Session = Depends(get_session)
):
    """
    Get learning efficiency metrics.
    
    Returns:
    - Data-to-insight ratios (bytes/documents/chunks per insight)
    - Domain acquisition efficiency
    - Learning curves
    - Optimal learning paths
    """
    try:
        tracker = LearningEfficiencyTracker(session)
        
        time_window = None
        if time_window_hours:
            time_window = timedelta(hours=time_window_hours)
        
        metrics = tracker.get_efficiency_metrics(domain=domain, time_window=time_window)
        export = tracker.export_metrics()
        
        return EfficiencyMetricsResponse(**export)
    except Exception as e:
        logger.error(f"Error getting efficiency metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimal-paths")
async def get_optimal_learning_paths(
    session: Session = Depends(get_session)
):
    """
    Get recommended optimal learning paths based on efficiency data.
    
    Returns domains ordered by learning efficiency (most efficient first).
    """
    try:
        tracker = LearningEfficiencyTracker(session)
        paths = tracker.get_optimal_learning_paths()
        
        return {
            "status": "success",
            "recommendations": paths
        }
    except Exception as e:
        logger.error(f"Error getting optimal paths: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domain/{domain}/efficiency")
async def get_domain_efficiency(
    domain: str,
    session: Session = Depends(get_session)
):
    """
    Get efficiency metrics for a specific domain.
    
    Returns:
    - Bytes per insight
    - Documents per insight
    - Total insights
    - Skill level progression
    """
    try:
        tracker = LearningEfficiencyTracker(session)
        metrics = tracker.get_efficiency_metrics(domain=domain)
        
        domain_data = tracker.domain_data_consumption.get(domain, {})
        domain_acq = tracker.domain_acquisitions.get(domain)
        
        return {
            "domain": domain,
            "efficiency": {
                "bytes_per_insight": metrics.bytes_per_insight,
                "documents_per_insight": metrics.documents_per_insight,
                "chunks_per_insight": metrics.chunks_per_insight,
                "seconds_per_insight": metrics.seconds_per_insight,
                "hours_per_insight": metrics.hours_per_insight,
                "insights_per_hour": metrics.insights_per_hour,
                "insights_per_day": metrics.insights_per_day
            },
            "data_consumption": domain_data,
            "acquisition": {
                "skill_level": domain_acq.skill_level if domain_acq else None,
                "total_insights": domain_acq.total_insights if domain_acq else 0,
                "trust_score": domain_acq.current_trust_score if domain_acq else 0.0,
                "data_at_acquisition": domain_acq.data_consumed_at_acquisition if domain_acq else {},
                "time_to_acquisition_hours": domain_acq.time_to_acquisition.total_seconds() / 3600 if domain_acq else 0.0,
                "insights_per_hour": domain_acq.insights_per_hour if domain_acq else 0.0
            }
        }
    except Exception as e:
        logger.error(f"Error getting domain efficiency: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_efficiency_summary(
    session: Session = Depends(get_session)
):
    """
    Get a quick summary of learning efficiency.
    
    Returns key metrics in a human-readable format.
    """
    try:
        tracker = LearningEfficiencyTracker(session)
        metrics = tracker.get_efficiency_metrics()
        
        return {
            "total_data_consumed": {
                "bytes": tracker.total_bytes_consumed,
                "mb": tracker.total_bytes_consumed / 1024 / 1024,
                "gb": tracker.total_bytes_consumed / 1024 / 1024 / 1024,
                "documents": tracker.total_documents_consumed,
                "chunks": tracker.total_chunks_consumed
            },
            "insights_gained": {
                "total": len(tracker.insights),
                "by_type": {
                    insight_type: sum(1 for i in tracker.insights if i.insight_type == insight_type)
                    for insight_type in set(i.insight_type for i in tracker.insights)
                }
            },
            "efficiency": {
                "bytes_per_insight": metrics.bytes_per_insight,
                "mb_per_insight": metrics.bytes_per_insight / 1024 / 1024,
                "documents_per_insight": metrics.documents_per_insight,
                "chunks_per_insight": metrics.chunks_per_insight
            },
            "domains": {
                "total": len(tracker.domain_acquisitions),
                "list": list(tracker.domain_acquisitions.keys()),
                "bytes_per_domain": metrics.bytes_per_domain,
                "mb_per_domain": metrics.bytes_per_domain / 1024 / 1024
            },
            "learning_curve": {
                "trend": "improving" if len(metrics.learning_curve) > 1 and 
                        metrics.learning_curve[-1][1] < metrics.learning_curve[0][1] 
                        else "stable",
                "first_insight_efficiency": metrics.learning_curve[0][1] if metrics.learning_curve else 0,
                "latest_efficiency": metrics.learning_curve[-1][1] if metrics.learning_curve else 0,
                "first_insight_time_seconds": metrics.time_per_insight_trend[0][1] if metrics.time_per_insight_trend else 0,
                "latest_time_seconds": metrics.time_per_insight_trend[-1][1] if metrics.time_per_insight_trend else 0,
                "velocity_improving": len(metrics.velocity_trend) > 1 and 
                                     metrics.velocity_trend[-1][1] > metrics.velocity_trend[0][1],
                "first_velocity": metrics.velocity_trend[0][1] if metrics.velocity_trend else 0,
                "latest_velocity": metrics.velocity_trend[-1][1] if metrics.velocity_trend else 0
            }
        }
    except Exception as e:
        logger.error(f"Error getting efficiency summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
