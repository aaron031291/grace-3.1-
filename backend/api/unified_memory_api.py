"""
Unified Memory API - Grace's Complete Memory System

One API for all memory operations.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

router = APIRouter(prefix="/api/memory", tags=["Unified Memory"])


class RememberRequest(BaseModel):
    content: str = Field(..., description="What to remember")
    memory_type: str = Field("semantic", description="episodic/procedural/semantic/working/learning/causal")
    source: str = Field("api", description="Source of this memory")
    trust_score: float = Field(0.5, description="Trust score 0-1")
    tags: List[str] = Field(default_factory=list, description="Tags")


class RecallRequest(BaseModel):
    query: str = Field(..., description="What to search for")
    memory_types: Optional[List[str]] = Field(None, description="Filter by type")
    min_trust: float = Field(0.0, description="Minimum trust score")
    limit: int = Field(10, description="Max results")


class EpisodeRequest(BaseModel):
    what_happened: str
    outcome: str
    source: str = "api"
    tags: List[str] = Field(default_factory=list)


class ProcedureRequest(BaseModel):
    name: str
    steps: List[str]
    source: str = "api"


class CausalRequest(BaseModel):
    cause: str
    effect: str
    source: str = "api"


@router.get("/dashboard")
async def memory_dashboard() -> Dict[str, Any]:
    from cognitive.unified_memory import get_unified_memory
    return get_unified_memory().get_dashboard()


@router.get("/stats")
async def memory_stats() -> Dict[str, Any]:
    from cognitive.unified_memory import get_unified_memory
    return get_unified_memory().get_stats()


@router.post("/remember")
async def remember(request: RememberRequest) -> Dict[str, Any]:
    from cognitive.unified_memory import get_unified_memory, MemoryType
    mem = get_unified_memory()
    try:
        mt = MemoryType(request.memory_type)
    except ValueError:
        mt = MemoryType.SEMANTIC
    memory = mem.remember(
        content=request.content,
        memory_type=mt,
        source=request.source,
        trust_score=request.trust_score,
        tags=request.tags,
    )
    return {"status": "remembered", "memory": memory.to_dict()}


@router.post("/recall")
async def recall(request: RecallRequest) -> Dict[str, Any]:
    from cognitive.unified_memory import get_unified_memory, MemoryType
    mem = get_unified_memory()
    types = None
    if request.memory_types:
        types = [MemoryType(t) for t in request.memory_types if t in [e.value for e in MemoryType]]
    results = mem.recall(
        query=request.query,
        memory_types=types,
        min_trust=request.min_trust,
        limit=request.limit,
    )
    return {
        "query": request.query,
        "results": [m.to_dict() for m in results],
        "count": len(results),
    }


@router.post("/episode")
async def remember_episode(request: EpisodeRequest) -> Dict[str, Any]:
    from cognitive.unified_memory import get_unified_memory
    memory = get_unified_memory().remember_episode(
        what_happened=request.what_happened,
        outcome=request.outcome,
        source=request.source,
        tags=request.tags,
    )
    return {"status": "remembered", "memory": memory.to_dict()}


@router.post("/procedure")
async def remember_procedure(request: ProcedureRequest) -> Dict[str, Any]:
    from cognitive.unified_memory import get_unified_memory
    memory = get_unified_memory().remember_procedure(
        name=request.name,
        steps=request.steps,
        source=request.source,
    )
    return {"status": "remembered", "memory": memory.to_dict()}


@router.post("/cause")
async def remember_cause(request: CausalRequest) -> Dict[str, Any]:
    from cognitive.unified_memory import get_unified_memory
    memory = get_unified_memory().remember_cause(
        cause=request.cause,
        effect=request.effect,
        source=request.source,
    )
    return {"status": "remembered", "memory": memory.to_dict()}


@router.post("/consolidate")
async def consolidate() -> Dict[str, Any]:
    from cognitive.unified_memory import get_unified_memory
    return get_unified_memory().run_consolidation()


@router.get("/working")
async def working_memory() -> Dict[str, Any]:
    from cognitive.unified_memory import get_unified_memory
    mem = get_unified_memory()
    return {
        "working_memory": [m.to_dict() for m in mem.get_working_memory()],
        "size": len(mem._working_memory),
    }


@router.delete("/{memory_id}")
async def forget(memory_id: str) -> Dict[str, Any]:
    from cognitive.unified_memory import get_unified_memory
    success = get_unified_memory().forget(memory_id)
    return {"forgotten": success, "memory_id": memory_id}


@router.post("/reinforce/{memory_id}")
async def reinforce(memory_id: str) -> Dict[str, Any]:
    from cognitive.unified_memory import get_unified_memory
    success = get_unified_memory().reinforce(memory_id)
    return {"reinforced": success, "memory_id": memory_id}
