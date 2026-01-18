"""
Enhanced Learning API - Maximum Capability Proactive Learning

Endpoints for:
- Enhanced Oracle Memory (calibration, correlation, reasoning chains)
- Enhanced Proactive Learning (LLM orchestration, evidence-based)
- Failure tracking and analysis
- Pattern evolution monitoring
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

router = APIRouter(prefix="/enhanced-learning", tags=["enhanced-learning"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class RecordOutcomeRequest(BaseModel):
    """Record prediction outcome for calibration."""
    memory_id: str
    was_correct: bool
    actual_outcome: Optional[str] = None


class RecordFailureRequest(BaseModel):
    """Record a failed prediction."""
    memory_id: str
    title: str
    predicted_confidence: float
    actual_outcome: str
    impact: float = 0.5


class RecordPatternRequest(BaseModel):
    """Record pattern outcome."""
    pattern_id: str
    description: str
    success: bool


class RetrieveRequest(BaseModel):
    """Retrieve memory items."""
    query: str
    item_types: Optional[List[str]] = None
    limit: int = 10
    min_confidence: float = 0.0


class EvidenceChainRequest(BaseModel):
    """Build evidence chain."""
    query: str
    max_hops: int = 3


# =============================================================================
# MEMORY ENDPOINTS
# =============================================================================

@router.get("/memory/stats")
async def get_memory_stats() -> Dict[str, Any]:
    """
    **Get Enhanced Memory Statistics**
    
    Returns:
    - Calibration report (ECE, accuracy by type)
    - Correlation statistics
    - Priority queue status
    - Memory breakdown by type
    """
    try:
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        memory = get_enhanced_oracle_memory()
        return memory.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/calibration")
async def get_calibration_report() -> Dict[str, Any]:
    """
    **Get Confidence Calibration Report**
    
    Shows Expected Calibration Error (ECE) and accuracy by confidence bucket.
    """
    try:
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        memory = get_enhanced_oracle_memory()
        return memory.calibrator.get_calibration_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/correlations")
async def get_correlation_stats() -> Dict[str, Any]:
    """
    **Get Cross-Source Correlation Statistics**
    
    Shows clusters of correlated knowledge from multiple sources.
    """
    try:
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        memory = get_enhanced_oracle_memory()
        return memory.correlator.get_correlation_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/priority-items")
async def get_priority_items(limit: int = 10) -> Dict[str, Any]:
    """
    **Get Priority Items for Learning**
    
    Items with highest: impact × uncertainty × staleness
    """
    try:
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        memory = get_enhanced_oracle_memory()
        items = memory.get_priority_items(limit=limit)
        return {
            "count": len(items),
            "items": [item.to_dict() for item in items]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/expansion-targets")
async def get_expansion_targets() -> Dict[str, Any]:
    """
    **Get Expansion Targets**
    
    Items that need more evidence (high uncertainty or stale).
    """
    try:
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        memory = get_enhanced_oracle_memory()
        targets = memory.get_expansion_targets()
        return {"count": len(targets), "targets": targets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/retrieve")
async def retrieve_memory(request: RetrieveRequest) -> Dict[str, Any]:
    """
    **Retrieve Memory Items**
    
    Semantic search with type filtering.
    """
    try:
        from oracle_intelligence.enhanced_oracle_memory import (
            get_enhanced_oracle_memory, MemoryItemType
        )
        
        memory = get_enhanced_oracle_memory()
        
        item_types = None
        if request.item_types:
            item_types = [MemoryItemType(t) for t in request.item_types]
        
        items = await memory.retrieve(
            query=request.query,
            item_types=item_types,
            limit=request.limit,
            min_confidence=request.min_confidence
        )
        
        return {
            "query": request.query,
            "count": len(items),
            "items": [item.to_dict() for item in items]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/evidence-chain")
async def build_evidence_chain(request: EvidenceChainRequest) -> Dict[str, Any]:
    """
    **Build Multi-Hop Evidence Chain**
    
    Retrieves evidence through multiple hops to support a hypothesis.
    """
    try:
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        
        memory = get_enhanced_oracle_memory()
        chain = await memory.retrieve_evidence_chain(
            query=request.query,
            max_hops=request.max_hops
        )
        
        return chain.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/record-outcome")
async def record_outcome(request: RecordOutcomeRequest) -> Dict[str, Any]:
    """
    **Record Prediction Outcome**
    
    Updates calibration and item confidence based on outcome.
    """
    try:
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        
        memory = get_enhanced_oracle_memory()
        await memory.record_outcome(
            memory_id=request.memory_id,
            was_correct=request.was_correct,
            actual_outcome=request.actual_outcome
        )
        
        return {"status": "recorded", "memory_id": request.memory_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/memory/save")
async def save_memory_state() -> Dict[str, Any]:
    """
    **Save Memory State**
    
    Persists calibration and correlation state.
    """
    try:
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        memory = get_enhanced_oracle_memory()
        memory.save_state()
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# LEARNING ENDPOINTS
# =============================================================================

@router.get("/learning/stats")
async def get_learning_stats() -> Dict[str, Any]:
    """
    **Get Enhanced Learning Statistics**
    
    Returns learning cycle stats, LLM orchestration counts, etc.
    """
    try:
        from oracle_intelligence.enhanced_proactive_learning import get_enhanced_proactive_learning
        learning = get_enhanced_proactive_learning()
        return learning.get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/generate-targets")
async def generate_learning_targets() -> Dict[str, Any]:
    """
    **Generate Learning Targets**
    
    Identifies what knowledge to acquire based on:
    - Evidence gaps
    - Stale knowledge
    - Pattern drift
    - Failed predictions
    - Cross-pollination opportunities
    - Frontier exploration
    """
    try:
        from oracle_intelligence.enhanced_proactive_learning import get_enhanced_proactive_learning
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        
        hub = get_oracle_hub()
        memory = get_enhanced_oracle_memory()
        
        learning = get_enhanced_proactive_learning(
            oracle_hub=hub,
            enhanced_memory=memory
        )
        
        targets = await learning.generate_learning_targets()
        
        return {
            "count": len(targets),
            "by_mode": {
                mode: len([t for t in targets if t.mode.value == mode])
                for mode in ["evidence_gap", "uncertainty", "staleness", "pattern_drift", "failure", "cross", "frontier"]
            },
            "targets": [t.to_dict() for t in targets[:20]]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/run-cycle")
async def run_learning_cycle() -> Dict[str, Any]:
    """
    **Run Learning Cycle**
    
    Executes one complete learning cycle:
    1. Generate targets
    2. LLM planning
    3. Fetch from sources
    4. LLM analysis
    5. LLM critique
    6. Store approved knowledge
    """
    try:
        from oracle_intelligence.enhanced_proactive_learning import get_enhanced_proactive_learning
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        
        hub = get_oracle_hub()
        memory = get_enhanced_oracle_memory()
        
        learning = get_enhanced_proactive_learning(
            oracle_hub=hub,
            enhanced_memory=memory
        )
        
        result = await learning.run_learning_cycle()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/start")
async def start_continuous_learning(interval_seconds: int = 300) -> Dict[str, Any]:
    """
    **Start Continuous Learning**
    
    Runs learning cycle in background at specified interval.
    """
    try:
        from oracle_intelligence.enhanced_proactive_learning import get_enhanced_proactive_learning
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        
        hub = get_oracle_hub()
        memory = get_enhanced_oracle_memory()
        
        learning = get_enhanced_proactive_learning(
            oracle_hub=hub,
            enhanced_memory=memory
        )
        learning.learning_interval = interval_seconds
        
        return learning.start_continuous_learning()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/stop")
async def stop_continuous_learning() -> Dict[str, Any]:
    """
    **Stop Continuous Learning**
    """
    try:
        from oracle_intelligence.enhanced_proactive_learning import get_enhanced_proactive_learning
        learning = get_enhanced_proactive_learning()
        return learning.stop_continuous_learning()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/record-failure")
async def record_failure(request: RecordFailureRequest) -> Dict[str, Any]:
    """
    **Record Failed Prediction**
    
    Records for counterfactual analysis and targeted learning.
    """
    try:
        from oracle_intelligence.enhanced_proactive_learning import get_enhanced_proactive_learning
        learning = get_enhanced_proactive_learning()
        
        learning.record_prediction_failure(
            memory_id=request.memory_id,
            title=request.title,
            predicted_confidence=request.predicted_confidence,
            actual_outcome=request.actual_outcome,
            impact=request.impact
        )
        
        return {"status": "recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/learning/record-pattern")
async def record_pattern(request: RecordPatternRequest) -> Dict[str, Any]:
    """
    **Record Pattern Outcome**
    
    Tracks pattern success/failure for drift detection.
    """
    try:
        from oracle_intelligence.enhanced_proactive_learning import get_enhanced_proactive_learning
        learning = get_enhanced_proactive_learning()
        
        learning.record_pattern_outcome(
            pattern_id=request.pattern_id,
            description=request.description,
            success=request.success
        )
        
        return {"status": "recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# COMBINED STATUS
# =============================================================================

@router.get("/status")
async def get_enhanced_system_status() -> Dict[str, Any]:
    """
    **Get Complete Enhanced System Status**
    
    Returns status of all enhanced components.
    """
    try:
        from oracle_intelligence.enhanced_oracle_memory import get_enhanced_oracle_memory
        from oracle_intelligence.enhanced_proactive_learning import get_enhanced_proactive_learning
        from oracle_intelligence.reverse_knn_learning import get_reverse_knn_learning
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        
        return {
            "oracle_hub": get_oracle_hub().get_status(),
            "enhanced_memory": get_enhanced_oracle_memory().get_stats(),
            "proactive_learning": get_enhanced_proactive_learning().get_stats(),
            "reverse_knn": get_reverse_knn_learning().get_stats()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/initialize-all")
async def initialize_all_systems() -> Dict[str, Any]:
    """
    **Initialize All Enhanced Systems**
    
    Starts Oracle Hub, Enhanced Memory, Proactive Learning, and Reverse KNN.
    """
    try:
        from oracle_intelligence.enhanced_proactive_learning import initialize_enhanced_learning
        from oracle_intelligence.reverse_knn_learning import initialize_reverse_knn_with_oracle
        
        learning = await initialize_enhanced_learning()
        rknn = await initialize_reverse_knn_with_oracle()
        
        return {
            "status": "initialized",
            "learning_running": learning is not None,
            "rknn_running": rknn is not None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
