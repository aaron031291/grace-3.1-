"""
Healing ↔ Coding Agent Bidirectional Communication API

API endpoints for bidirectional communication between:
1. Self-Healing System → Coding Agent
2. Coding Agent → Self-Healing System
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session

from database.session import get_session
from cognitive.coding_agent_healing_bridge import (
    get_coding_agent_healing_bridge,
    CodingAgentHealingBridge,
    AssistanceType
)

router = APIRouter(prefix="/healing-coding-bridge", tags=["healing-coding-bridge"])

# Global bridge instance
_bridge: Optional[CodingAgentHealingBridge] = None


def get_bridge(session: Session = Depends(get_session)) -> CodingAgentHealingBridge:
    """Get or create bridge instance."""
    global _bridge
    
    if _bridge is None:
        # Get coding agent and healing system
        try:
            from cognitive.enterprise_coding_agent import get_enterprise_coding_agent
            from cognitive.autonomous_healing_system import get_autonomous_healing
            from pathlib import Path
            
            coding_agent = get_enterprise_coding_agent(
                session=session,
                repo_path=Path.cwd(),
                enable_learning=True,
                enable_sandbox=True
            )
            
            healing_system = get_autonomous_healing(
                session=session,
                repo_path=Path.cwd(),
                coding_agent=coding_agent
            )
            
            _bridge = get_coding_agent_healing_bridge(
                coding_agent=coding_agent,
                healing_system=healing_system
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize bridge: {str(e)}")
    
    return _bridge


# ==================== Request Models ====================

class HealingToCodingRequest(BaseModel):
    """Request from Self-Healing to Coding Agent."""
    assistance_type: str = Field(..., description="Type of assistance (code_generation, code_fix, etc.)")
    description: str = Field(..., description="Description of what's needed")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    priority: str = Field("high", description="Priority (low, medium, high, critical)")


class CodingToHealingRequest(BaseModel):
    """Request from Coding Agent to Self-Healing."""
    issue_description: str = Field(..., description="Description of the issue")
    affected_files: List[str] = Field(default_factory=list, description="Files affected")
    issue_type: str = Field("code_issue", description="Type of issue")
    priority: str = Field("medium", description="Priority (low, medium, high, critical)")


class DiagnosticRequest(BaseModel):
    """Request for diagnostic analysis."""
    description: str = Field(..., description="What to diagnose")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


# ==================== API Endpoints ====================

@router.post("/healing-to-coding")
async def healing_to_coding(
    request: HealingToCodingRequest,
    bridge: CodingAgentHealingBridge = Depends(get_bridge)
):
    """
    Self-Healing System requests assistance from Coding Agent.
    
    Use cases:
    - Need code generation for fixes
    - Need code refactoring
    - Need code optimization
    - Need code review
    """
    try:
        # Map string to enum
        type_map = {
            "code_generation": AssistanceType.CODE_GENERATION,
            "code_fix": AssistanceType.CODE_FIX,
            "code_refactor": AssistanceType.CODE_REFACTOR,
            "code_optimize": AssistanceType.CODE_OPTIMIZE,
            "code_review": AssistanceType.CODE_REVIEW,
            "bug_fix": AssistanceType.BUG_FIX
        }
        
        assistance_type = type_map.get(request.assistance_type, AssistanceType.CODE_GENERATION)
        
        result = bridge.healing_request_coding_assistance(
            assistance_type=assistance_type,
            description=request.description,
            context=request.context,
            priority=request.priority
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to request coding assistance: {str(e)}")


@router.post("/coding-to-healing")
async def coding_to_healing(
    request: CodingToHealingRequest,
    bridge: CodingAgentHealingBridge = Depends(get_bridge)
):
    """
    Coding Agent requests assistance from Self-Healing System.
    
    Use cases:
    - Code generation failed
    - Code has issues that need healing
    - Need diagnostic analysis
    """
    try:
        result = bridge.coding_agent_request_healing_assistance(
            issue_description=request.issue_description,
            affected_files=request.affected_files,
            issue_type=request.issue_type,
            priority=request.priority
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to request healing: {str(e)}")


@router.post("/diagnostic")
async def request_diagnostic(
    request: DiagnosticRequest,
    bridge: CodingAgentHealingBridge = Depends(get_bridge)
):
    """Request diagnostic analysis."""
    try:
        result = bridge.coding_agent_request_diagnostic(
            description=request.description,
            context=request.context
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to request diagnostic: {str(e)}")


@router.get("/requests/pending")
async def get_pending_requests(
    bridge: CodingAgentHealingBridge = Depends(get_bridge)
):
    """Get all pending assistance requests."""
    try:
        requests = bridge.get_pending_requests()
        return {"pending_requests": requests, "count": len(requests)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pending requests: {str(e)}")


@router.get("/requests/completed")
async def get_completed_requests(
    limit: int = 50,
    bridge: CodingAgentHealingBridge = Depends(get_bridge)
):
    """Get completed assistance requests."""
    try:
        requests = bridge.get_completed_requests(limit=limit)
        return {"completed_requests": requests, "count": len(requests)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get completed requests: {str(e)}")
