"""
Consensus API — Multi-Model Roundtable

Endpoints for running the 4-layer consensus pipeline,
managing model selection, and the autonomous batch queue.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/consensus", tags=["Consensus Roundtable"])


class ConsensusRequest(BaseModel):
    prompt: str
    models: Optional[List[str]] = None  # ["opus", "kimi", "qwen", "reasoning"]
    system_prompt: str = ""
    context: str = ""
    source: str = "user"
    user_context: str = ""


class BatchQueryRequest(BaseModel):
    prompt: str
    context: str = ""
    priority: str = "normal"  # normal, high


class BatchRunRequest(BaseModel):
    max_queries: int = 5


# ── Model Discovery ──────────────────────────────────────────────────

@router.get("/models")
async def list_models():
    """
    List all available models for the roundtable.
    Returns availability status for each model based on current configuration.
    """
    from cognitive.consensus_engine import get_available_models
    models = get_available_models()
    return {"models": models}


# ── Run Consensus ─────────────────────────────────────────────────────

@router.post("/run")
async def run_consensus(req: ConsensusRequest):
    """
    Execute the full 4-layer consensus pipeline.

    Layer 1: Independent deliberation (all models run in parallel)
    Layer 2: Consensus formation (synthesise agreements/disagreements)
    Layer 3: Alignment (align to user/Grace/context needs)
    Layer 4: Verification (trust, hallucination, contradiction checks)
    """
    from cognitive.consensus_engine import run_consensus as _run

    try:
        result = _run(
            prompt=req.prompt,
            models=req.models,
            system_prompt=req.system_prompt,
            context=req.context,
            source=req.source,
            user_context=req.user_context,
        )

        return {
            "final_output": result.final_output,
            "confidence": result.confidence,
            "models_used": result.models_used,
            "individual_responses": result.individual_responses,
            "consensus": result.consensus_text[:3000],
            "alignment": result.alignment_text[:3000],
            "verification": result.verification,
            "agreements": result.agreements,
            "disagreements": result.disagreements,
            "total_latency_ms": result.total_latency_ms,
            "timestamp": result.timestamp,
        }
    except Exception as e:
        logger.error(f"Consensus run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick")
async def quick_consensus(req: ConsensusRequest):
    """
    Quick consensus with only local models (cost-free).
    Uses Qwen + Reasoning model only.
    """
    req.models = ["qwen", "reasoning"]
    return await run_consensus(req)


# ── Autonomous Batch Queue ────────────────────────────────────────────

@router.post("/batch/queue")
async def queue_query(req: BatchQueryRequest):
    """
    Queue a query for the next autonomous batch run.
    Grace uses this when she needs multi-model help but it's not urgent.
    """
    from cognitive.consensus_engine import queue_autonomous_query
    entry = queue_autonomous_query(
        prompt=req.prompt,
        context=req.context,
        priority=req.priority,
    )
    return {"queued": True, **entry}


@router.get("/batch/queue")
async def get_queue():
    """Get the current autonomous batch queue."""
    from cognitive.consensus_engine import get_batch_queue
    queue = get_batch_queue()
    return {
        "queue": queue,
        "total": len(queue),
        "pending": sum(1 for q in queue if q.get("status") == "queued"),
        "completed": sum(1 for q in queue if q.get("status") == "completed"),
    }


@router.post("/batch/run")
async def run_batch(req: BatchRunRequest):
    """
    Process queued autonomous queries.
    Limits to max_queries per batch to control token costs.
    """
    from cognitive.consensus_engine import run_batch as _run_batch
    results = _run_batch(max_queries=req.max_queries)

    try:
        from api._genesis_tracker import track
        track(
            key_type="system",
            what=f"Consensus batch run: {len(results)} queries processed",
            how="POST /api/consensus/batch/run",
            tags=["consensus", "batch", "autonomous"],
        )
    except Exception:
        pass

    return {"processed": len(results), "results": results}
