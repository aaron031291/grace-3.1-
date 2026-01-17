"""
Layer 2 Intelligence API Endpoints - Cognitive Processing Engine

Provides endpoints for Layer 2 Intelligence (Cognitive Processing Engine):
- Deep intent analysis
- Context-aware reasoning
- OODA loop processing
- Multi-system intelligence integration

Layer 2 processes inputs through:
OBSERVE → ORIENT → DECIDE → ACT

All operations are tracked with Genesis Keys and integrated with Layer 1 message bus.
"""
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import datetime

from database.session import get_session
from genesis_ide.layer_intelligence import Layer2Intelligence

router = APIRouter(prefix="/layer2", tags=["Layer 2 Intelligence"])


# ==================== Pydantic Models ====================

class CognitiveProcessRequest(BaseModel):
    """Request for cognitive processing."""
    intent: str = Field(..., description="User intent or query")
    entities: Optional[Dict[str, Any]] = Field(None, description="Extracted entities (files, goals, problems, etc.)")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    user_id: Optional[str] = Field(None, description="User ID for tracking")


class CognitiveProcessResponse(BaseModel):
    """Response from cognitive processing."""
    intent: str
    observations: Dict[str, Any]
    orientation: Dict[str, Any]
    decision: Dict[str, Any]
    confidence: float
    clarity: Optional[Dict[str, Any]] = None
    genesis_keys: Optional[Dict[str, str]] = None


class Layer2StatusResponse(BaseModel):
    """Layer 2 system status."""
    initialized: bool
    connected_systems: Dict[str, bool]
    metrics: Dict[str, Any]
    message_bus_connected: bool


# ==================== Layer 2 Instance Management ====================

_layer2_instance: Optional[Layer2Intelligence] = None


def get_layer2_intelligence(session: Session) -> Layer2Intelligence:
    """Get or create Layer 2 Intelligence instance."""
    global _layer2_instance
    
    if _layer2_instance is None:
        repo_path = Path.cwd()
        _layer2_instance = Layer2Intelligence(
            session=session,
            repo_path=repo_path
        )
        # Note: initialize() should be called separately or on first use
    
    return _layer2_instance


# ==================== API Endpoints ====================

@router.post("/process", response_model=CognitiveProcessResponse)
async def process_cognitive_intent(
    request: CognitiveProcessRequest,
    session: Session = Depends(get_session)
):
    """
    Process intent through Layer 2 Intelligence (OODA Loop).
    
    This endpoint processes user intent through the complete cognitive cycle:
    1. OBSERVE: Gather intelligence from all systems
    2. ORIENT: Analyze situation with LLM intelligence
    3. DECIDE: Make intelligent decision
    4. ACT: Return decision for execution
    
    All operations are tracked with Genesis Keys and integrated with Layer 1.
    """
    try:
        layer2 = get_layer2_intelligence(session)
        
        # Ensure initialized
        if not layer2._llm_orchestrator:
            await layer2.initialize()
        
        # Process through OODA loop
        result = await layer2.process(
            intent=request.intent,
            entities=request.entities or {},
            context=request.context or {}
        )
        
        # Extract clarity and genesis keys if available
        clarity = result.get("clarity")
        genesis_keys = {}
        if "observe_key_id" in str(result):
            # Extract genesis key IDs from result
            pass  # Genesis keys are in the result context
        
        return CognitiveProcessResponse(
            intent=result.get("intent", request.intent),
            observations=result.get("observations", {}),
            orientation=result.get("orientation", {}),
            decision=result.get("decision", {}),
            confidence=result.get("confidence", 0.5),
            clarity=clarity,
            genesis_keys=genesis_keys
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Layer 2 processing failed: {str(e)}")


@router.get("/status", response_model=Layer2StatusResponse)
async def get_layer2_status(
    session: Session = Depends(get_session)
):
    """
    Get Layer 2 Intelligence system status.
    
    Returns:
    - Initialization status
    - Connected systems status
    - Current metrics
    - Layer 1 message bus connection status
    """
    try:
        layer2 = get_layer2_intelligence(session)
        
        # Check connected systems
        connected_systems = {
            "llm_orchestrator": layer2._llm_orchestrator is not None,
            "memory_mesh": layer2._memory_mesh is not None,
            "rag_retriever": layer2._rag_retriever is not None,
            "world_model": layer2._world_model is not None,
            "diagnostic_engine": layer2._diagnostic_engine is not None,
            "code_analyzer": layer2._code_analyzer is not None,
            "librarian": layer2._librarian is not None,
            "mirror_system": layer2._mirror_system is not None,
            "confidence_scorer": layer2._confidence_scorer is not None,
            "cognitive_engine": layer2._cognitive_engine is not None,
            "healing_system": layer2._healing_system is not None,
            "timesense": layer2._timesense is not None,
            "clarity_framework": layer2._clarity_framework is not None,
            "failure_learning": layer2._failure_learning is not None,
            "mutation_tracker": layer2._mutation_tracker is not None,
            "self_updater": layer2._self_updater is not None,
            "neuro_symbolic_reasoner": layer2._neuro_symbolic_reasoner is not None,
            "enterprise_neuro_symbolic": layer2._enterprise_neuro_symbolic is not None,
            "enterprise_rag": layer2._enterprise_rag is not None,
            "trust_aware_retriever": layer2._trust_aware_retriever is not None,
            "genesis_service": layer2._genesis_service is not None,
            "message_bus": layer2._message_bus is not None
        }
        
        return Layer2StatusResponse(
            initialized=layer2._llm_orchestrator is not None,
            connected_systems=connected_systems,
            metrics=layer2.metrics,
            message_bus_connected=layer2._message_bus is not None
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Layer 2 status: {str(e)}")


@router.post("/observe")
async def observe_phase(
    intent: str = Body(...),
    entities: Dict[str, Any] = Body(default={}),
    context: Dict[str, Any] = Body(default={}),
    session: Session = Depends(get_session)
):
    """
    Execute OBSERVE phase only.
    
    Gathers intelligence from all connected systems without full OODA cycle.
    Useful for getting context before processing.
    """
    try:
        layer2 = get_layer2_intelligence(session)
        
        if not layer2._llm_orchestrator:
            await layer2.initialize()
        
        observations = await layer2._observe(intent, entities, context)
        
        return {
            "intent": intent,
            "observations": observations,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OBSERVE phase failed: {str(e)}")


@router.post("/orient")
async def orient_phase(
    observations: Dict[str, Any] = Body(...),
    context: Dict[str, Any] = Body(default={}),
    session: Session = Depends(get_session)
):
    """
    Execute ORIENT phase only.
    
    Analyzes observations using LLM intelligence.
    Requires observations from OBSERVE phase.
    """
    try:
        layer2 = get_layer2_intelligence(session)
        
        if not layer2._llm_orchestrator:
            await layer2.initialize()
        
        orientation = await layer2._orient(observations, context)
        
        return {
            "orientation": orientation,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"ORIENT phase failed: {str(e)}")


@router.post("/decide")
async def decide_phase(
    orientation: Dict[str, Any] = Body(...),
    session: Session = Depends(get_session)
):
    """
    Execute DECIDE phase only.
    
    Makes decision based on orientation data.
    Requires orientation from ORIENT phase.
    """
    try:
        layer2 = get_layer2_intelligence(session)
        
        if not layer2._llm_orchestrator:
            await layer2.initialize()
        
        decision = await layer2._decide(orientation)
        
        return {
            "decision": decision,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DECIDE phase failed: {str(e)}")


@router.get("/metrics")
async def get_layer2_metrics(
    session: Session = Depends(get_session)
):
    """
    Get Layer 2 Intelligence metrics.
    
    Returns:
    - Cognitive cycles count
    - Decisions made
    - Insights generated
    - System performance metrics
    """
    try:
        layer2 = get_layer2_intelligence(session)
        
        return {
            "metrics": layer2.metrics,
            "context_memory_size": len(layer2._context_memory),
            "max_context": layer2._max_context
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")
