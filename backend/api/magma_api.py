"""
Magma Memory API - Graph-based Memory System

Endpoints for Grace's Magma memory system:
- /api/magma/query - Query memory with intent-aware routing
- /api/magma/ingest - Ingest content into relation graphs
- /api/magma/stats - Memory statistics
- /api/magma/why - Causal inference (why did X happen?)
- /api/magma/context - Get LLM context for a query
- /api/magma/graphs - Relation graph statistics
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List

router = APIRouter(prefix="/api/magma", tags=["Magma Memory"])


class IngestRequest(BaseModel):
    content: str = Field(..., description="Content to ingest")
    genesis_key_id: Optional[str] = Field(None, description="Genesis Key for tracking")
    source: Optional[str] = Field(None, description="Source identifier")


class QueryRequest(BaseModel):
    query: str = Field(..., description="Query string")
    limit: int = Field(10, description="Max results")


class CausalRequest(BaseModel):
    question: str = Field(..., description="Why question for causal inference")


@router.post("/ingest")
async def magma_ingest(request: IngestRequest) -> Dict[str, Any]:
    """Ingest content into Magma relation graphs."""
    from cognitive.magma import get_grace_magma
    magma = get_grace_magma()
    result = magma.ingest(
        content=request.content,
        genesis_key_id=request.genesis_key_id,
        source=request.source or "api",
    )
    return {
        "status": "ingested",
        "segments": getattr(result, "segments_created", 0) if result else 0,
        "links": getattr(result, "links_created", 0) if result else 0,
    }


@router.post("/query")
async def magma_query(request: QueryRequest) -> Dict[str, Any]:
    """Query Magma memory with intent-aware routing."""
    from cognitive.magma import get_grace_magma
    magma = get_grace_magma()
    results = magma.query(query=request.query, limit=request.limit)
    return {
        "query": request.query,
        "results": [
            {
                "content": getattr(r, "content", str(r))[:500],
                "score": getattr(r, "score", 0.0),
                "graph": getattr(r, "graph", "unknown"),
            }
            for r in (results or [])
        ],
        "count": len(results) if results else 0,
    }


@router.post("/context")
async def magma_context(request: QueryRequest) -> Dict[str, Any]:
    """Get LLM-ready context for a query from Magma memory."""
    from cognitive.magma import get_grace_magma
    magma = get_grace_magma()
    results = magma.query(query=request.query, limit=request.limit)
    context = magma.get_context(results, query=request.query)
    return {
        "query": request.query,
        "context": context,
        "sources": len(results) if results else 0,
    }


@router.post("/why")
async def magma_why(request: CausalRequest) -> Dict[str, Any]:
    """Causal inference - why did something happen?"""
    from cognitive.magma import get_grace_magma
    magma = get_grace_magma()
    try:
        explanation = magma.why(request.question)
        return {
            "question": request.question,
            "explanation": str(explanation) if explanation else "No causal chain found",
        }
    except Exception as e:
        return {
            "question": request.question,
            "explanation": f"Causal inference unavailable: {str(e)}",
        }


@router.get("/stats")
async def magma_stats() -> Dict[str, Any]:
    """Magma memory statistics."""
    from cognitive.magma import get_grace_magma
    magma = get_grace_magma()
    return magma.get_stats()


@router.get("/graphs")
async def magma_graphs() -> Dict[str, Any]:
    """Relation graph statistics."""
    from cognitive.magma import get_grace_magma
    magma = get_grace_magma()
    stats = magma.get_stats()
    return {"graphs": stats.get("graphs", {})}
