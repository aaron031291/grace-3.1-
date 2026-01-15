"""
Grace Help API - API endpoint for Grace to request help autonomously
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from database.session import get_db
from cognitive.autonomous_help_requester import (
    get_help_requester,
    HelpPriority,
    HelpRequestType
)

router = APIRouter(prefix="/api/grace/help", tags=["Grace Help"])


class HelpRequestModel(BaseModel):
    """Model for help request."""
    request_type: str = Field(..., description="Type of help needed")
    priority: str = Field(..., description="Priority level")
    issue_description: str = Field(..., description="Description of the issue")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")
    affected_files: Optional[List[str]] = Field(default=None, description="Affected files")
    attempted_solutions: Optional[List[str]] = Field(default=None, description="Solutions already tried")
    genesis_key_id: Optional[str] = Field(default=None, description="Related Genesis Key ID")


@router.post("/request")
async def request_help(request: HelpRequestModel, db: Session = Depends(get_db)):
    """
    Grace can use this endpoint to request help autonomously.
    
    This is how Grace communicates with the AI assistant when she needs help.
    """
    try:
        help_requester = get_help_requester(session=db)
        
        # Convert string to enum
        try:
            request_type = HelpRequestType(request.request_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid request type: {request.request_type}"
            )
        
        try:
            priority = HelpPriority(request.priority)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid priority: {request.priority}"
            )
        
        result = help_requester.request_help(
            request_type=request_type,
            priority=priority,
            issue_description=request.issue_description,
            context=request.context,
            error_details=request.error_details,
            affected_files=request.affected_files,
            attempted_solutions=request.attempted_solutions,
            genesis_key_id=request.genesis_key_id
        )
        
        return {
            "success": True,
            "help_request": result["help_request"],
            "genesis_key_id": result["genesis_key_id"],
            "message": "Help request created successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create help request: {str(e)}")


@router.get("/statistics")
async def get_help_statistics(db: Session = Depends(get_db)):
    """Get statistics about Grace's help requests."""
    try:
        help_requester = get_help_requester(session=db)
        stats = help_requester.get_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.post("/debugging")
async def request_debugging_help(
    issue: str,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    affected_files: Optional[List[str]] = None,
    priority: str = "high",
    db: Session = Depends(get_db)
):
    """Convenience endpoint for debugging help requests."""
    try:
        help_requester = get_help_requester(session=db)
        
        error_details = {}
        if error_type or error_message:
            error_details = {
                "type": error_type,
                "message": error_message
            }
        
        try:
            priority_enum = HelpPriority(priority)
        except ValueError:
            priority_enum = HelpPriority.HIGH
        
        result = help_requester.request_debugging_help(
            issue=issue,
            error=None,  # Could parse error if needed
            affected_files=affected_files,
            context={"error_type": error_type, "error_message": error_message},
            priority=priority_enum
        )
        
        return {
            "success": True,
            "help_request": result["help_request"],
            "message": "Debugging help request created"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create debugging help request: {str(e)}")


@router.post("/stabilization")
async def request_stabilization_help(
    issue: str,
    system_status: Optional[Dict[str, Any]] = None,
    affected_components: Optional[List[str]] = None,
    priority: str = "critical",
    db: Session = Depends(get_db)
):
    """Convenience endpoint for system stabilization help requests."""
    try:
        help_requester = get_help_requester(session=db)
        
        try:
            priority_enum = HelpPriority(priority)
        except ValueError:
            priority_enum = HelpPriority.CRITICAL
        
        result = help_requester.request_stabilization_help(
            issue=issue,
            system_status=system_status,
            affected_components=affected_components,
            priority=priority_enum
        )
        
        return {
            "success": True,
            "help_request": result["help_request"],
            "message": "Stabilization help request created"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create stabilization help request: {str(e)}")


@router.post("/knowledge")
async def request_knowledge(
    topic: str,
    knowledge_type: str = "debugging",
    context: Optional[Dict[str, Any]] = None,
    priority: str = "medium",
    db: Session = Depends(get_db)
):
    """
    Grace can use this endpoint to request knowledge about specific topics.
    
    This allows Grace to learn about:
    - Debugging techniques
    - Problem-solving approaches
    - Best practices
    - Technology-specific knowledge
    - Solutions to common problems
    """
    try:
        help_requester = get_help_requester(session=db)
        
        try:
            priority_enum = HelpPriority(priority)
        except ValueError:
            priority_enum = HelpPriority.MEDIUM
        
        result = help_requester.request_knowledge(
            topic=topic,
            knowledge_type=knowledge_type,
            context=context,
            priority=priority_enum
        )
        
        return {
            "success": True,
            "help_request": result["help_request"],
            "ai_research_results": result.get("ai_research_results", []),
            "message": "Knowledge request created"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create knowledge request: {str(e)}")
