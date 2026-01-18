"""
LLM Interaction Observatory API - Query and analyze LLM interactions.

Endpoints for:
- Recording LLM interactions
- Querying WHY an LLM responded a certain way
- Getting OODA analysis of interactions
- Extracting training datasets
- Viewing patterns and statistics
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from cognitive.llm_interaction_observatory import (
    LLMInteractionObservatory,
    InteractionType,
    ResponseQuality,
    create_observatory
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/llm-observatory", tags=["LLM Observatory"])

# Global instance
_observatory: Optional[LLMInteractionObservatory] = None


def get_observatory() -> LLMInteractionObservatory:
    """Get or create observatory instance."""
    global _observatory
    if _observatory is None:
        _observatory = create_observatory()
    return _observatory


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ObserveCallRequest(BaseModel):
    """Request to observe an LLM call."""
    prompt: str = Field(..., description="The prompt sent to LLM")
    response: str = Field(..., description="The response from LLM")
    model: str = Field("unknown", description="Model name")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    latency_ms: int = Field(0, description="Response latency in ms")
    input_tokens: int = Field(0, description="Input token count")
    output_tokens: int = Field(0, description="Output token count")
    temperature: float = Field(0.0, description="Temperature used")


class QueryWhyRequest(BaseModel):
    """Request to query why an LLM responded a certain way."""
    interaction_id: str = Field(..., description="Interaction ID to query")


class QueryByOutputRequest(BaseModel):
    """Request to query by output content."""
    output_fragment: str = Field(..., description="Fragment to search for in outputs")


class TrainingDataRequest(BaseModel):
    """Request for training data."""
    min_quality: str = Field("good", description="Minimum quality level")
    domains: Optional[List[str]] = Field(None, description="Filter by domains")
    limit: int = Field(1000, description="Maximum items to return")


# =============================================================================
# OBSERVATION ENDPOINTS
# =============================================================================

@router.post("/observe")
async def observe_llm_call(request: ObserveCallRequest):
    """
    Observe and record an LLM interaction.
    
    Call this after every LLM interaction to:
    - Log with Genesis Key
    - Analyze with OODA
    - Extract reasoning patterns
    - Assess quality
    """
    observatory = get_observatory()
    
    interaction = observatory.observe_call(
        prompt=request.prompt,
        response=request.response,
        model=request.model,
        system_prompt=request.system_prompt,
        context=request.context or {},
        latency_ms=request.latency_ms,
        input_tokens=request.input_tokens,
        output_tokens=request.output_tokens
    )
    
    return {
        "success": True,
        "interaction_id": interaction.interaction_id,
        "genesis_key_id": interaction.genesis_key_id,
        "type": interaction.interaction_type.value,
        "quality": interaction.quality.value,
        "quality_score": interaction.quality_score,
        "domain": interaction.domain,
        "ooda_summary": {
            "observed": interaction.ooda_observe.get("prompt_type"),
            "interpreted_as": interaction.ooda_orient.get("inferred_intent"),
            "strategy": interaction.ooda_decide.get("strategy_chosen"),
            "produced": interaction.ooda_act.get("response_type")
        }
    }


@router.post("/observe/batch")
async def observe_batch(interactions: List[ObserveCallRequest]):
    """Observe multiple LLM interactions."""
    observatory = get_observatory()
    results = []
    
    for req in interactions:
        interaction = observatory.observe_call(
            prompt=req.prompt,
            response=req.response,
            model=req.model,
            system_prompt=req.system_prompt,
            context=req.context or {},
            latency_ms=req.latency_ms
        )
        results.append({
            "interaction_id": interaction.interaction_id,
            "type": interaction.interaction_type.value,
            "quality": interaction.quality.value
        })
    
    return {
        "success": True,
        "observed": len(results),
        "interactions": results
    }


# =============================================================================
# QUERY ENDPOINTS
# =============================================================================

@router.get("/query/why/{interaction_id}")
async def query_why_response(interaction_id: str):
    """
    Query WHY an LLM generated a specific response.
    
    Returns OODA analysis explaining:
    - What the LLM observed in the prompt
    - How it interpreted the situation
    - What strategy it chose
    - What it produced and why
    """
    observatory = get_observatory()
    result = observatory.query_why(interaction_id)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return result


@router.post("/query/by-output")
async def query_by_output(request: QueryByOutputRequest):
    """
    Find interactions that contain specific output text.
    
    Useful for reverse engineering:
    - "Why did it generate this code pattern?"
    - "What prompts led to this type of response?"
    """
    observatory = get_observatory()
    results = observatory.query_by_output(request.output_fragment)
    
    return {
        "query": request.output_fragment,
        "matches": len(results),
        "interactions": results
    }


@router.get("/query/interactions")
async def query_interactions(
    type: Optional[str] = Query(None, description="Filter by interaction type"),
    quality: Optional[str] = Query(None, description="Filter by quality"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    min_score: float = Query(0.0, description="Minimum quality score"),
    limit: int = Query(100, description="Maximum results")
):
    """Query interactions with filters."""
    observatory = get_observatory()
    
    interaction_type = InteractionType(type) if type else None
    response_quality = ResponseQuality(quality) if quality else None
    
    results = observatory.repository.query(
        interaction_type=interaction_type,
        quality=response_quality,
        domain=domain,
        min_quality_score=min_score,
        limit=limit
    )
    
    return {
        "count": len(results),
        "interactions": [
            {
                "interaction_id": i.interaction_id,
                "type": i.interaction_type.value,
                "quality": i.quality.value,
                "quality_score": i.quality_score,
                "domain": i.domain,
                "model": i.model_name,
                "prompt_preview": i.prompt[:200],
                "response_preview": i.response[:200],
                "genesis_key_id": i.genesis_key_id
            }
            for i in results
        ]
    }


@router.get("/query/interaction/{interaction_id}")
async def get_interaction(interaction_id: str):
    """Get full details of a specific interaction."""
    observatory = get_observatory()
    interaction = observatory.repository.get(interaction_id)
    
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    return interaction.to_dict()


# =============================================================================
# OODA ANALYSIS ENDPOINTS
# =============================================================================

@router.get("/ooda/{interaction_id}")
async def get_ooda_analysis(interaction_id: str):
    """
    Get detailed OODA analysis for an interaction.
    
    OODA Loop:
    - OBSERVE: What was in the prompt
    - ORIENT: How it was interpreted
    - DECIDE: What approach was chosen
    - ACT: What was produced
    """
    observatory = get_observatory()
    interaction = observatory.repository.get(interaction_id)
    
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    return {
        "interaction_id": interaction_id,
        "observe": {
            "description": "What the LLM observed in the input",
            "analysis": interaction.ooda_observe
        },
        "orient": {
            "description": "How the LLM interpreted the situation",
            "analysis": interaction.ooda_orient
        },
        "decide": {
            "description": "What strategy the LLM chose",
            "analysis": interaction.ooda_decide
        },
        "act": {
            "description": "What the LLM produced",
            "analysis": interaction.ooda_act
        },
        "reasoning_chain": interaction.reasoning_chain,
        "key_decisions": interaction.key_decisions
    }


@router.get("/reasoning/{interaction_id}")
async def get_reasoning_chain(interaction_id: str):
    """Get the reasoning chain for an interaction."""
    observatory = get_observatory()
    interaction = observatory.repository.get(interaction_id)
    
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    
    return {
        "interaction_id": interaction_id,
        "reasoning_chain": interaction.reasoning_chain,
        "key_decisions": interaction.key_decisions,
        "strategy": interaction.ooda_decide.get("strategy_chosen"),
        "confidence": interaction.ooda_decide.get("confidence_level"),
        "alternatives_considered": interaction.ooda_decide.get("alternatives_considered")
    }


# =============================================================================
# TRAINING DATA ENDPOINTS
# =============================================================================

@router.post("/training-data")
async def get_training_data(request: TrainingDataRequest):
    """
    Get LLM interactions as training dataset.
    
    Returns high-quality interactions with:
    - Prompt/response pairs
    - OODA analysis
    - Reasoning chains
    - Quality scores
    """
    observatory = get_observatory()
    
    dataset = observatory.get_training_data(
        min_quality=request.min_quality,
        domains=request.domains
    )
    
    # Limit results
    dataset = dataset[:request.limit]
    
    return {
        "total_items": len(dataset),
        "min_quality": request.min_quality,
        "domains": request.domains,
        "dataset": dataset
    }


@router.get("/training-data/export")
async def export_training_data(
    min_quality: str = Query("good", description="Minimum quality"),
    format: str = Query("json", description="Export format (json, jsonl)")
):
    """Export training data in specified format."""
    observatory = get_observatory()
    
    dataset = observatory.get_training_data(min_quality=min_quality)
    
    if format == "jsonl":
        # Return as newline-delimited JSON
        import json
        lines = [json.dumps(item) for item in dataset]
        return {
            "format": "jsonl",
            "count": len(dataset),
            "data": "\n".join(lines)
        }
    else:
        return {
            "format": "json",
            "count": len(dataset),
            "data": dataset
        }


# =============================================================================
# PATTERNS AND STATISTICS
# =============================================================================

@router.get("/patterns")
async def get_patterns(
    type: Optional[str] = Query(None, description="Filter by interaction type")
):
    """
    Get patterns observed across LLM interactions.
    
    Shows:
    - Common strategies used
    - Domain distribution
    - Reasoning patterns
    - Common decisions
    """
    observatory = get_observatory()
    patterns = observatory.get_patterns(interaction_type=type)
    
    return {
        "interaction_type": type or "all",
        "patterns": patterns
    }


@router.get("/stats")
async def get_statistics():
    """Get observatory statistics."""
    observatory = get_observatory()
    return observatory.get_stats()


@router.get("/stats/quality")
async def get_quality_stats():
    """Get quality distribution statistics."""
    observatory = get_observatory()
    stats = observatory.get_stats()
    
    return {
        "total_observed": stats["total_observed"],
        "average_quality_score": stats["avg_quality_score"],
        "by_quality": stats["by_quality"],
        "quality_distribution": {
            k: v / stats["total_observed"] * 100 if stats["total_observed"] > 0 else 0
            for k, v in stats["by_quality"].items()
        }
    }


@router.get("/stats/types")
async def get_type_stats():
    """Get interaction type statistics."""
    observatory = get_observatory()
    stats = observatory.get_stats()
    
    return {
        "total_observed": stats["total_observed"],
        "by_type": stats["by_type"],
        "type_distribution": {
            k: v / stats["total_observed"] * 100 if stats["total_observed"] > 0 else 0
            for k, v in stats["by_type"].items()
        }
    }


# =============================================================================
# INFO ENDPOINTS
# =============================================================================

@router.get("/types")
async def get_interaction_types():
    """Get available interaction types."""
    return {
        "types": [
            {"value": t.value, "name": t.name}
            for t in InteractionType
        ]
    }


@router.get("/qualities")
async def get_quality_levels():
    """Get quality level definitions."""
    return {
        "levels": [
            {"value": "excellent", "description": "Exceptional response", "min_score": 0.85},
            {"value": "good", "description": "Good quality response", "min_score": 0.70},
            {"value": "acceptable", "description": "Acceptable response", "min_score": 0.50},
            {"value": "poor", "description": "Poor quality response", "min_score": 0.30},
            {"value": "failed", "description": "Failed response", "min_score": 0.0}
        ]
    }


@router.get("/ooda-framework")
async def get_ooda_framework():
    """Get explanation of OODA framework used for analysis."""
    return {
        "framework": "OODA Loop",
        "description": "Observe-Orient-Decide-Act framework for analyzing LLM reasoning",
        "phases": {
            "observe": {
                "description": "What the LLM observed in the input",
                "analyzes": [
                    "Prompt type and structure",
                    "Key entities mentioned",
                    "Constraints given",
                    "Examples provided",
                    "Task clarity"
                ]
            },
            "orient": {
                "description": "How the LLM interpreted the situation",
                "analyzes": [
                    "Inferred user intent",
                    "Domain identification",
                    "Complexity assessment",
                    "Knowledge areas accessed",
                    "Assumptions made"
                ]
            },
            "decide": {
                "description": "What strategy the LLM chose",
                "analyzes": [
                    "Strategy selection",
                    "Alternatives considered",
                    "Confidence level",
                    "Risk assessment",
                    "Trade-offs"
                ]
            },
            "act": {
                "description": "What the LLM produced",
                "analyzes": [
                    "Response type",
                    "Code generation",
                    "Explanation quality",
                    "Caveats mentioned",
                    "Follow-up suggestions"
                ]
            }
        },
        "usage": "Use /ooda/{interaction_id} to get OODA analysis for any observed interaction"
    }
