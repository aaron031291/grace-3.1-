"""
DevOps Healing API - API endpoint for Grace's DevOps healing agent
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from database.session import get_db
from cognitive.devops_healing_agent import (
    get_devops_healing_agent,
    DevOpsLayer,
    IssueCategory
)

router = APIRouter(prefix="/api/grace/devops", tags=["Grace DevOps Healing"])


class HealingRequestModel(BaseModel):
    """Model for healing request."""
    issue_description: str = Field(..., description="Description of the issue")
    error_type: Optional[str] = Field(None, description="Type of error")
    error_message: Optional[str] = Field(None, description="Error message")
    affected_layer: Optional[str] = Field(None, description="Affected DevOps layer")
    issue_category: Optional[str] = Field(None, description="Category of issue")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    affected_files: Optional[List[str]] = Field(default=None, description="Affected files")


@router.post("/heal")
async def request_healing(request: HealingRequestModel, db: Session = Depends(get_db)):
    """
    Grace can use this endpoint to request healing for issues.
    
    The DevOps agent will:
    1. Analyze the issue
    2. Check if Grace has knowledge to fix it
    3. Request knowledge if needed
    4. Attempt to fix the issue
    5. Request help if fix fails
    """
    try:
        devops_agent = get_devops_healing_agent(session=db)
        
        # Convert string to enum if provided
        affected_layer = None
        if request.affected_layer:
            try:
                affected_layer = DevOpsLayer(request.affected_layer)
            except ValueError:
                pass
        
        issue_category = None
        if request.issue_category:
            try:
                issue_category = IssueCategory(request.issue_category)
            except ValueError:
                pass
        
        # Create error object if provided
        error = None
        if request.error_type or request.error_message:
            class ErrorWrapper(Exception):
                def __init__(self, msg):
                    self.msg = msg
                    super().__init__(msg)
            
            error = ErrorWrapper(request.error_message or request.error_type)
        
        # Add affected files to context
        context = request.context or {}
        if request.affected_files:
            context["affected_files"] = request.affected_files
        
        # Request healing
        result = devops_agent.detect_and_heal(
            issue_description=request.issue_description,
            error=error,
            affected_layer=affected_layer,
            issue_category=issue_category,
            context=context
        )
        
        return {
            "success": True,
            "healing_result": result,
            "message": "Healing request processed"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process healing request: {str(e)}")


@router.get("/statistics")
async def get_healing_statistics(db: Session = Depends(get_db)):
    """Get DevOps healing agent statistics."""
    try:
        devops_agent = get_devops_healing_agent(session=db)
        stats = devops_agent.get_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.get("/layers")
async def list_devops_layers():
    """List available DevOps layers."""
    return {
        "layers": [
            {"value": layer.value, "name": layer.name}
            for layer in DevOpsLayer
        ]
    }


@router.get("/categories")
async def list_issue_categories():
    """List available issue categories."""
    return {
        "categories": [
            {"value": cat.value, "name": cat.name}
            for cat in IssueCategory
        ]
    }
