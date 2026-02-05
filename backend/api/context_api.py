"""
Context API - User context submission and management for Tier 3 queries.

Provides endpoints for:
- Submitting user context to fill knowledge gaps
- Retrieving context request details
- Viewing context submission history
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from database.session import get_session
from models.query_intelligence_models import (
    QueryHandlingLog,
    KnowledgeGap,
    ContextSubmission
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/context", tags=["Context Management"])


# ==================== Request/Response Models ====================

class ContextGapSubmission(BaseModel):
    """Single context submission for a knowledge gap."""
    gap_id: str = Field(..., description="ID of the knowledge gap")
    value: str = Field(..., description="User-provided context value")


class SubmitContextRequest(BaseModel):
    """Request to submit context for a query."""
    query_id: str = Field(..., description="ID of the query needing context")
    contexts: List[ContextGapSubmission] = Field(..., description="List of context submissions")
    user_id: Optional[str] = Field(None, description="User identifier")
    genesis_key_id: Optional[str] = Field(None, description="Genesis Key for tracking")


class SubmitContextResponse(BaseModel):
    """Response after submitting context."""
    success: bool
    message: str
    contexts_accepted: int
    retry_query: bool = Field(True, description="Whether to retry the query with new context")


class ContextRequestDetails(BaseModel):
    """Details of a context request."""
    query_id: str
    query_text: str
    knowledge_gaps: List[Dict[str, Any]]
    created_at: datetime
    context_provided: bool


class ContextHistoryItem(BaseModel):
    """Single item in context submission history."""
    id: int
    query_id: str
    gap_id: Optional[str]
    submitted_context: str
    used_in_response: bool
    trust_score: float
    created_at: datetime


# ==================== Endpoints ====================

@router.post("/submit", response_model=SubmitContextResponse)
async def submit_context(
    request: SubmitContextRequest,
    session = Depends(get_session)
):
    """
    Submit user-provided context to fill knowledge gaps.
    
    After submission, the system will retry the query with the new context.
    
    Args:
        request: Context submission request
        session: Database session
        
    Returns:
        SubmitContextResponse with acceptance status
    """
    try:
        # Verify query exists
        query_log = session.query(QueryHandlingLog).filter(
            QueryHandlingLog.query_id == request.query_id
        ).first()
        
        if not query_log:
            raise HTTPException(
                status_code=404,
                detail=f"Query {request.query_id} not found"
            )
        
        # Verify gaps exist
        gap_ids = [ctx.gap_id for ctx in request.contexts]
        gaps = session.query(KnowledgeGap).filter(
            KnowledgeGap.gap_id.in_(gap_ids)
        ).all()
        
        if len(gaps) != len(gap_ids):
            raise HTTPException(
                status_code=400,
                detail="One or more gap IDs are invalid"
            )
        
        # Create context submissions
        contexts_accepted = 0
        for ctx in request.contexts:
            submission = ContextSubmission(
                query_id=request.query_id,
                gap_id=ctx.gap_id,
                submitted_context=ctx.value,
                user_id=request.user_id,
                genesis_key_id=request.genesis_key_id,
                trust_score=0.7  # Initial trust score for user-provided context
            )
            session.add(submission)
            contexts_accepted += 1
        
        # Update query log
        query_log.context_provided = True
        
        # Mark gaps as resolved
        for gap in gaps:
            gap.resolved = True
            gap.resolution_source = "user_submission"
            gap.resolved_at = datetime.utcnow()
        
        session.commit()
        
        logger.info(
            f"Accepted {contexts_accepted} context submissions for query {request.query_id}"
        )
        
        return SubmitContextResponse(
            success=True,
            message=f"Successfully accepted {contexts_accepted} context submission(s)",
            contexts_accepted=contexts_accepted,
            retry_query=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error submitting context: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error submitting context: {str(e)}"
        )


@router.get("/requests/{query_id}", response_model=ContextRequestDetails)
async def get_context_request(
    query_id: str,
    session = Depends(get_session)
):
    """
    Get details of a context request.
    
    Args:
        query_id: Query identifier
        session: Database session
        
    Returns:
        ContextRequestDetails with gap information
    """
    try:
        # Get query log
        query_log = session.query(QueryHandlingLog).filter(
            QueryHandlingLog.query_id == query_id
        ).first()
        
        if not query_log:
            raise HTTPException(
                status_code=404,
                detail=f"Query {query_id} not found"
            )
        
        # Get knowledge gaps
        gaps = session.query(KnowledgeGap).filter(
            KnowledgeGap.query_id == query_id
        ).all()
        
        knowledge_gaps = [
            {
                "gap_id": gap.gap_id,
                "topic": gap.gap_topic,
                "specific_question": gap.specific_question,
                "required": gap.required,
                "resolved": gap.resolved
            }
            for gap in gaps
        ]
        
        return ContextRequestDetails(
            query_id=query_log.query_id,
            query_text=query_log.query_text,
            knowledge_gaps=knowledge_gaps,
            created_at=query_log.created_at,
            context_provided=query_log.context_provided
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving context request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving context request: {str(e)}"
        )


@router.get("/history", response_model=List[ContextHistoryItem])
async def get_context_history(
    user_id: Optional[str] = None,
    limit: int = 50,
    session = Depends(get_session)
):
    """
    Get context submission history.
    
    Args:
        user_id: Optional filter by user
        limit: Maximum number of items to return
        session: Database session
        
    Returns:
        List of context submissions
    """
    try:
        query = session.query(ContextSubmission)
        
        if user_id:
            query = query.filter(ContextSubmission.user_id == user_id)
        
        submissions = query.order_by(
            ContextSubmission.created_at.desc()
        ).limit(limit).all()
        
        return [
            ContextHistoryItem(
                id=sub.id,
                query_id=sub.query_id,
                gap_id=sub.gap_id,
                submitted_context=sub.submitted_context,
                used_in_response=sub.used_in_response,
                trust_score=sub.trust_score,
                created_at=sub.created_at
            )
            for sub in submissions
        ]
        
    except Exception as e:
        logger.error(f"Error retrieving context history: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving context history: {str(e)}"
        )


@router.get("/stats")
async def get_context_stats(session = Depends(get_session)):
    """
    Get statistics about context submissions.
    
    Returns:
        Dictionary with context submission statistics
    """
    try:
        from sqlalchemy import func
        
        # Total submissions
        total_submissions = session.query(func.count(ContextSubmission.id)).scalar()
        
        # Submissions used in responses
        used_submissions = session.query(func.count(ContextSubmission.id)).filter(
            ContextSubmission.used_in_response == True
        ).scalar()
        
        # Total gaps
        total_gaps = session.query(func.count(KnowledgeGap.id)).scalar()
        
        # Resolved gaps
        resolved_gaps = session.query(func.count(KnowledgeGap.id)).filter(
            KnowledgeGap.resolved == True
        ).scalar()
        
        # Average trust score
        avg_trust = session.query(func.avg(ContextSubmission.trust_score)).scalar() or 0.0
        
        return {
            "total_submissions": total_submissions or 0,
            "used_submissions": used_submissions or 0,
            "usage_rate": (used_submissions / total_submissions * 100) if total_submissions else 0.0,
            "total_gaps": total_gaps or 0,
            "resolved_gaps": resolved_gaps or 0,
            "resolution_rate": (resolved_gaps / total_gaps * 100) if total_gaps else 0.0,
            "avg_trust_score": float(avg_trust)
        }
        
    except Exception as e:
        logger.error(f"Error retrieving context stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving context stats: {str(e)}"
        )
