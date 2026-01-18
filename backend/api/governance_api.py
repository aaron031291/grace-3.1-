"""
Governance API - Layer 3 Quorum Verification Endpoints

Provides REST API for:
- Trust assessment of data/actions
- Quorum decision requests
- Component KPI tracking
- Governance status monitoring
- Whitelist management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/governance", tags=["Governance"])


class TrustAssessmentRequest(BaseModel):
    """Request to assess trustworthiness of data."""
    data: Any
    origin: str
    genesis_key_id: Optional[str] = None
    correlation_check: bool = True
    timesense_validate: bool = True


class QuorumDecisionRequest(BaseModel):
    """Request for quorum decision."""
    proposal: Dict[str, Any]
    required_votes: int = 3
    escalation_threshold: float = 0.7


class KPIRecordRequest(BaseModel):
    """Request to record component outcome."""
    component_id: str
    success: bool
    meets_grace_standard: bool = True
    meets_user_standard: bool = True
    weight: float = 1.0


class WhitelistRequest(BaseModel):
    """Request to modify whitelist."""
    source: str


@router.post("/trust/assess")
async def assess_trust(request: TrustAssessmentRequest):
    """
    Assess trustworthiness of data or action.
    
    Trust Sources:
    - WHITELIST, INTERNAL_DATA, PROACTIVE_LEARNING, ORACLE, HUMAN_TRIGGERED: 100% trusted
    - WEB, LLM_QUERY, CHAT_MESSAGE, EXTERNAL_FILE: Requires verification
    
    Verification passes when data correlates across multiple sources.
    Genesis Keys help detect contradictions.
    TimeSense validates temporal consistency.
    """
    try:
        from governance.layer3_quorum_verification import get_quorum_engine
        
        engine = get_quorum_engine()
        assessment = await engine.assess_trust(
            data=request.data,
            origin=request.origin,
            genesis_key_id=request.genesis_key_id,
            correlation_check=request.correlation_check,
            timesense_validate=request.timesense_validate
        )
        
        return {
            "success": True,
            "assessment": assessment.to_dict()
        }
    except Exception as e:
        logger.error(f"Trust assessment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quorum/request")
async def request_quorum_decision(request: QuorumDecisionRequest):
    """
    Request quorum decision for a proposal.
    
    The Parliament system votes on the proposal.
    Requires multiple votes for consensus.
    Low confidence results in escalation.
    """
    try:
        from governance.layer3_quorum_verification import get_quorum_engine
        
        engine = get_quorum_engine()
        session = await engine.request_quorum(
            proposal=request.proposal,
            required_votes=request.required_votes,
            escalation_threshold=request.escalation_threshold
        )
        
        return {
            "success": True,
            "session_id": session.session_id,
            "decision": session.decision.value if session.decision else None,
            "confidence": session.confidence,
            "votes": len(session.votes),
            "genesis_key_id": session.genesis_key_id
        }
    except Exception as e:
        logger.error(f"Quorum request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kpi/record")
async def record_kpi_outcome(request: KPIRecordRequest):
    """
    Record component outcome for KPI tracking.
    
    KPIs adjust based on:
    - Success/failure
    - Meeting Grace's standards
    - Meeting user's standards
    
    Score goes UP with success + meeting standards.
    Score goes DOWN with failure or not meeting standards.
    """
    try:
        from governance.layer3_quorum_verification import get_quorum_engine
        
        engine = get_quorum_engine()
        engine.record_component_outcome(
            component_id=request.component_id,
            success=request.success,
            meets_grace_standard=request.meets_grace_standard,
            meets_user_standard=request.meets_user_standard,
            weight=request.weight
        )
        
        kpi = engine.get_component_kpi(request.component_id)
        
        return {
            "success": True,
            "component_id": request.component_id,
            "current_score": kpi.current_score if kpi else 0.5,
            "trend": kpi.trend if kpi else "stable"
        }
    except Exception as e:
        logger.error(f"KPI recording failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kpi/all")
async def get_all_kpis():
    """Get KPIs for all Grace components."""
    try:
        from governance.layer3_quorum_verification import get_quorum_engine
        
        engine = get_quorum_engine()
        return {
            "success": True,
            "kpis": engine.get_all_kpis()
        }
    except Exception as e:
        logger.error(f"Failed to get KPIs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kpi/{component_id}")
async def get_component_kpi(component_id: str):
    """Get KPI for a specific component."""
    try:
        from governance.layer3_quorum_verification import get_quorum_engine
        
        engine = get_quorum_engine()
        kpi = engine.get_component_kpi(component_id)
        
        if not kpi:
            raise HTTPException(status_code=404, detail=f"Component {component_id} not found")
        
        return {
            "success": True,
            "kpi": kpi.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get KPI: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_governance_status():
    """
    Get overall governance status.
    
    Returns:
    - Governance health score
    - All component KPIs
    - Trust verification statistics
    - Quorum session statistics
    - Constitutional framework info
    """
    try:
        from governance.layer3_quorum_verification import get_quorum_engine
        
        engine = get_quorum_engine()
        return {
            "success": True,
            "governance": engine.get_governance_status()
        }
    except Exception as e:
        logger.error(f"Failed to get governance status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/whitelist/add")
async def add_to_whitelist(request: WhitelistRequest):
    """Add a source to the trusted whitelist (100% trust)."""
    try:
        from governance.layer3_quorum_verification import get_quorum_engine
        
        engine = get_quorum_engine()
        engine.add_to_whitelist(request.source)
        
        return {
            "success": True,
            "message": f"Added {request.source} to whitelist",
            "whitelist_size": len(engine.whitelist)
        }
    except Exception as e:
        logger.error(f"Failed to add to whitelist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/whitelist/remove")
async def remove_from_whitelist(request: WhitelistRequest):
    """Remove a source from the whitelist."""
    try:
        from governance.layer3_quorum_verification import get_quorum_engine
        
        engine = get_quorum_engine()
        engine.remove_from_whitelist(request.source)
        
        return {
            "success": True,
            "message": f"Removed {request.source} from whitelist",
            "whitelist_size": len(engine.whitelist)
        }
    except Exception as e:
        logger.error(f"Failed to remove from whitelist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/constitutional/principles")
async def get_constitutional_principles():
    """Get Grace's constitutional principles (ethical guidelines)."""
    from governance.layer3_quorum_verification import ConstitutionalFramework
    
    return {
        "success": True,
        "principles": ConstitutionalFramework.CORE_PRINCIPLES,
        "autonomy_tiers": ConstitutionalFramework.AUTONOMY_TIERS
    }


@router.post("/constitutional/check")
async def check_constitutional_compliance(action: Dict[str, Any]):
    """Check if an action complies with constitutional principles."""
    from governance.layer3_quorum_verification import ConstitutionalFramework
    
    compliant, violations = ConstitutionalFramework.check_compliance(action)
    
    return {
        "success": True,
        "compliant": compliant,
        "violations": violations
    }
