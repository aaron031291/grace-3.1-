"""
Unified Learning Pipeline API

Exposes the 24/7 continuous learning pipeline and neighbor-by-neighbor
topic expansion engine for monitoring and control.

Classes:
- `PipelineSeedRequest`
- `PipelineConfigUpdate`

Database Tables:
None (no DB tables)

Connects To:
- `cognitive.unified_learning_pipeline`
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["Unified Learning Pipeline"])


class PipelineSeedRequest(BaseModel):
    """Request to add a seed topic for expansion."""
    topic: str = Field(..., description="Seed topic to expand")
    text: str = Field("", description="Optional text context for the seed")


class PipelineConfigUpdate(BaseModel):
    """Request to update pipeline configuration."""
    scan_interval_seconds: Optional[int] = None
    expansion_interval_seconds: Optional[int] = None
    min_trust_for_expansion: Optional[float] = None
    max_expansions_per_cycle: Optional[int] = None
    enable_predictive_prefetch: Optional[bool] = None


@router.get("/status")
async def get_pipeline_status():
    """Get the current status of the unified learning pipeline."""
    try:
        from cognitive.unified_learning_pipeline import get_unified_pipeline
        pipeline = get_unified_pipeline()
        return pipeline.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/start")
async def start_pipeline():
    """Start the 24/7 continuous learning pipeline."""
    try:
        from cognitive.unified_learning_pipeline import get_unified_pipeline
        pipeline = get_unified_pipeline()
        pipeline.start()
        return {
            "status": "started",
            "message": "24/7 continuous learning pipeline started",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_pipeline():
    """Stop the continuous learning pipeline."""
    try:
        from cognitive.unified_learning_pipeline import get_unified_pipeline
        pipeline = get_unified_pipeline()
        pipeline.stop()
        return {
            "status": "stopped",
            "message": "Pipeline stopped",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seed")
async def add_seed_topic(request: PipelineSeedRequest):
    """Add a seed topic for neighbor-by-neighbor expansion."""
    try:
        from cognitive.unified_learning_pipeline import get_unified_pipeline
        pipeline = get_unified_pipeline()
        pipeline.add_seed(request.topic, request.text)
        return {
            "status": "queued",
            "topic": request.topic,
            "pending_seeds": len(pipeline._pending_seeds),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/expand")
async def expand_topic_now(request: PipelineSeedRequest):
    """Immediately expand a topic using neighbor-by-neighbor search."""
    try:
        from cognitive.unified_learning_pipeline import get_unified_pipeline
        pipeline = get_unified_pipeline()
        result = pipeline._neighbor_engine.expand_from_seed(
            request.topic, request.text
        )
        return {
            "status": "expanded",
            "result": {
                "seed_topic": result.seed_topic,
                "neighbors_found": result.neighbors_found,
                "new_topics_discovered": result.new_topics_discovered,
                "knowledge_items_created": result.knowledge_items_created,
                "expansion_depth": result.expansion_depth,
                "duration_ms": result.duration_ms
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/graph")
async def get_knowledge_graph():
    """Get the current knowledge graph from neighbor-by-neighbor expansion."""
    try:
        from cognitive.unified_learning_pipeline import get_unified_pipeline
        pipeline = get_unified_pipeline()
        return pipeline._neighbor_engine.get_knowledge_graph()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config")
async def update_pipeline_config(config: PipelineConfigUpdate):
    """Update pipeline configuration."""
    try:
        from cognitive.unified_learning_pipeline import get_unified_pipeline
        pipeline = get_unified_pipeline()

        updates = config.model_dump(exclude_none=True)
        for key, value in updates.items():
            if key in pipeline.config:
                pipeline.config[key] = value

        return {
            "status": "updated",
            "config": pipeline.config,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
