"""
Librarian API endpoints.
Provides REST API for tag management, relationships, rules, approval workflow, and document processing.
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends, Body
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging
import json

from database.session import get_session
from models.librarian_models import (
    LibrarianTag, DocumentTag, DocumentRelationship,
    LibrarianRule, LibrarianAction, LibrarianAudit
)
from models.database_models import Document
from librarian.tag_manager import TagManager
from librarian.rule_categorizer import RuleBasedCategorizer
from librarian.relationship_manager import RelationshipManager
from librarian.approval_workflow import ApprovalWorkflow
from librarian.engine import LibrarianEngine
from embedding import get_embedding_model
from ollama_client.client import get_ollama_client
from vector_db.client import get_qdrant_client
from settings import settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/librarian", tags=["Librarian"])

# Global singleton instances
_librarian_engine: Optional[LibrarianEngine] = None


def get_librarian_engine(session: Session) -> LibrarianEngine:
    """Get or create librarian engine singleton."""
    global _librarian_engine

    if _librarian_engine is None:
        logger.info("[LIBRARIAN-API] Initializing LibrarianEngine singleton")
        try:
            _librarian_engine = LibrarianEngine(
                db_session=session,
                embedding_model=get_embedding_model(),
                ollama_client=get_ollama_client(),
                vector_db_client=get_qdrant_client(),
                ai_model_name=settings.LIBRARIAN_AI_MODEL,
                use_ai=settings.LIBRARIAN_USE_AI,
                detect_relationships=settings.LIBRARIAN_DETECT_RELATIONSHIPS,
                ai_confidence_threshold=settings.LIBRARIAN_AI_CONFIDENCE_THRESHOLD,
                similarity_threshold=settings.LIBRARIAN_SIMILARITY_THRESHOLD
            )
            logger.info("[LIBRARIAN-API] LibrarianEngine initialized successfully")
        except Exception as e:
            logger.error(f"[LIBRARIAN-API] Failed to initialize LibrarianEngine: {e}")
            raise HTTPException(status_code=503, detail="Librarian engine unavailable")

    return _librarian_engine


# ==================== Pydantic Response Models ====================

class TagResponse(BaseModel):
    """Tag information response."""
    id: int = Field(..., description="Tag ID")
    name: str = Field(..., description="Tag name")
    description: Optional[str] = Field(None, description="Tag description")
    color: str = Field(..., description="Tag color (hex)")
    category: Optional[str] = Field(None, description="Tag category")
    usage_count: int = Field(..., description="Number of times tag is used")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class TagListResponse(BaseModel):
    """List of tags response."""
    tags: List[TagResponse] = Field(..., description="List of tags")
    total: int = Field(..., description="Total number of tags")


class TagCreateRequest(BaseModel):
    """Request to create a tag."""
    name: str = Field(..., description="Tag name")
    description: Optional[str] = Field(None, description="Tag description")
    color: Optional[str] = Field("#3B82F6", description="Tag color (hex)")
    category: Optional[str] = Field(None, description="Tag category")


class TagUpdateRequest(BaseModel):
    """Request to update a tag."""
    description: Optional[str] = Field(None, description="Tag description")
    color: Optional[str] = Field(None, description="Tag color (hex)")
    category: Optional[str] = Field(None, description="Tag category")


class TagAssignRequest(BaseModel):
    """Request to assign tags to a document."""
    tag_names: List[str] = Field(..., description="List of tag names to assign")
    assigned_by: str = Field("user", description="Who assigned the tags")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence in assignment")


class DocumentTagsResponse(BaseModel):
    """Document tags response."""
    document_id: int = Field(..., description="Document ID")
    tags: List[Dict[str, Any]] = Field(..., description="List of tag assignments")
    total: int = Field(..., description="Total number of tags")


class TagSearchRequest(BaseModel):
    """Request to search documents by tags."""
    tag_names: List[str] = Field(..., description="Tags to search for")
    match_all: bool = Field(False, description="Require all tags (AND) or any tag (OR)")
    limit: int = Field(100, ge=1, le=1000, description="Maximum results")


class TagSearchResponse(BaseModel):
    """Tag search results response."""
    documents: List[Dict[str, Any]] = Field(..., description="List of matching documents")
    total: int = Field(..., description="Total matches")
    matched_tags: List[str] = Field(..., description="Tags that were matched")


class TagStatisticsResponse(BaseModel):
    """Tag usage statistics response."""
    total_tags: int = Field(..., description="Total number of tags")
    by_category: Dict[str, int] = Field(..., description="Tags grouped by category")
    most_used: List[Dict[str, Any]] = Field(..., description="Most frequently used tags")
    recent_tags: List[Dict[str, Any]] = Field(..., description="Recently created tags")


class RelationshipResponse(BaseModel):
    """Relationship information response."""
    id: int = Field(..., description="Relationship ID")
    source_document_id: int = Field(..., description="Source document ID")
    target_document_id: int = Field(..., description="Target document ID")
    relationship_type: str = Field(..., description="Type of relationship")
    confidence: float = Field(..., description="Confidence score")
    strength: float = Field(..., description="Relationship strength")
    detected_by: str = Field(..., description="Detection method")
    created_at: str = Field(..., description="Creation timestamp")


class DocumentRelationshipsResponse(BaseModel):
    """Document relationships response."""
    document_id: int = Field(..., description="Document ID")
    outgoing: List[RelationshipResponse] = Field(..., description="Outgoing relationships")
    incoming: List[RelationshipResponse] = Field(..., description="Incoming relationships")
    total: int = Field(..., description="Total relationships")


class RelationshipCreateRequest(BaseModel):
    """Request to create a relationship."""
    source_document_id: int = Field(..., description="Source document ID")
    target_document_id: int = Field(..., description="Target document ID")
    relationship_type: str = Field(..., description="Type of relationship")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score")
    strength: Optional[float] = Field(None, ge=0.0, le=1.0, description="Relationship strength")


class DependencyGraphResponse(BaseModel):
    """Dependency graph response."""
    root_document_id: int = Field(..., description="Root document ID")
    nodes: List[Dict[str, Any]] = Field(..., description="Graph nodes (documents)")
    edges: List[Dict[str, Any]] = Field(..., description="Graph edges (relationships)")
    depth: int = Field(..., description="Graph depth")


class RuleResponse(BaseModel):
    """Rule information response."""
    id: int = Field(..., description="Rule ID")
    name: str = Field(..., description="Rule name")
    pattern_type: str = Field(..., description="Pattern type")
    pattern_value: str = Field(..., description="Pattern value/regex")
    action_type: str = Field(..., description="Action type")
    action_params: Dict[str, Any] = Field(..., description="Action parameters")
    priority: int = Field(..., description="Rule priority")
    enabled: bool = Field(..., description="Whether rule is enabled")
    matches_count: int = Field(..., description="Number of matches")
    last_matched_at: Optional[str] = Field(None, description="Last match timestamp")


class RuleListResponse(BaseModel):
    """List of rules response."""
    rules: List[RuleResponse] = Field(..., description="List of rules")
    total: int = Field(..., description="Total number of rules")


class RuleCreateRequest(BaseModel):
    """Request to create a rule."""
    name: str = Field(..., description="Rule name")
    pattern_type: str = Field(..., description="Pattern type (extension, filename, path, content)")
    pattern_value: str = Field(..., description="Pattern value/regex")
    action_type: str = Field(..., description="Action type (assign_tag, etc.)")
    action_params: Dict[str, Any] = Field(..., description="Action parameters")
    priority: int = Field(0, description="Rule priority (higher = first)")
    enabled: bool = Field(True, description="Whether rule is enabled")


class RuleUpdateRequest(BaseModel):
    """Request to update a rule."""
    name: Optional[str] = Field(None, description="Rule name")
    pattern_value: Optional[str] = Field(None, description="Pattern value/regex")
    action_params: Optional[Dict[str, Any]] = Field(None, description="Action parameters")
    priority: Optional[int] = Field(None, description="Rule priority")
    enabled: Optional[bool] = Field(None, description="Whether rule is enabled")


class RuleTestResponse(BaseModel):
    """Rule test results response."""
    rule_id: int = Field(..., description="Rule ID")
    rule_name: str = Field(..., description="Rule name")
    matched_documents: List[Dict[str, Any]] = Field(..., description="Documents that matched")
    total_matches: int = Field(..., description="Total number of matches")


class ActionResponse(BaseModel):
    """Action information response."""
    id: int = Field(..., description="Action ID")
    document_id: Optional[int] = Field(None, description="Related document ID")
    action_type: str = Field(..., description="Action type")
    action_params: Dict[str, Any] = Field(..., description="Action parameters")
    permission_tier: str = Field(..., description="Permission tier")
    status: str = Field(..., description="Action status")
    confidence: float = Field(..., description="Confidence score")
    reason: Optional[str] = Field(None, description="Reason for action")
    reviewed_by: Optional[str] = Field(None, description="Reviewer")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class ActionListResponse(BaseModel):
    """List of actions response."""
    actions: List[ActionResponse] = Field(..., description="List of actions")
    total: int = Field(..., description="Total number of actions")
    pending_count: int = Field(..., description="Number of pending actions")
    approved_count: int = Field(..., description="Number of approved actions")
    rejected_count: int = Field(..., description="Number of rejected actions")


class ActionApproveRequest(BaseModel):
    """Request to approve an action."""
    reviewed_by: str = Field(..., description="Reviewer identifier")
    notes: Optional[str] = Field(None, description="Approval notes")


class ActionRejectRequest(BaseModel):
    """Request to reject an action."""
    reviewed_by: str = Field(..., description="Reviewer identifier")
    reason: str = Field(..., description="Rejection reason")


class BatchApproveRequest(BaseModel):
    """Request to batch approve actions."""
    action_ids: List[int] = Field(..., description="List of action IDs to approve")
    reviewed_by: str = Field(..., description="Reviewer identifier")


class ProcessingResponse(BaseModel):
    """Document processing response."""
    status: str = Field(..., description="Processing status")
    document_id: int = Field(..., description="Document ID")
    tags_assigned: int = Field(..., description="Number of tags assigned")
    relationships_detected: int = Field(..., description="Number of relationships detected")
    rules_matched: List[str] = Field(..., description="List of matched rule names")
    ai_analysis: Optional[Dict[str, Any]] = Field(None, description="AI analysis results")
    processing_time: float = Field(..., description="Processing time in seconds")


class BatchProcessingRequest(BaseModel):
    """Request to batch process documents."""
    document_ids: List[int] = Field(..., description="List of document IDs")
    use_ai: Optional[bool] = Field(None, description="Use AI analysis")
    detect_relationships: Optional[bool] = Field(None, description="Detect relationships")


class BatchProcessingResponse(BaseModel):
    """Batch processing response."""
    total: int = Field(..., description="Total documents processed")
    successful: int = Field(..., description="Successfully processed")
    failed: int = Field(..., description="Failed to process")
    results: List[ProcessingResponse] = Field(..., description="Individual results")


class ReprocessAllRequest(BaseModel):
    """Request to reprocess all documents."""
    use_ai: bool = Field(False, description="Use AI analysis")
    detect_relationships: bool = Field(True, description="Detect relationships")
    batch_size: int = Field(10, ge=1, le=100, description="Batch size")
    limit: Optional[int] = Field(None, description="Limit number of documents")


class StatisticsResponse(BaseModel):
    """System statistics response."""
    tags: Dict[str, Any] = Field(..., description="Tag statistics")
    rules: Dict[str, Any] = Field(..., description="Rule statistics")
    relationships: Dict[str, Any] = Field(..., description="Relationship statistics")
    documents_processed: int = Field(..., description="Number of documents processed")
    ai_available: bool = Field(..., description="Whether AI is available")
    relationships_enabled: bool = Field(..., description="Whether relationships are enabled")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    overall_status: str = Field(..., description="Overall system status")
    components: Dict[str, str] = Field(..., description="Component statuses")
    version: str = Field(..., description="Librarian version")


# ==================== Tag Management Endpoints ====================

@router.get("/tags", response_model=TagListResponse, summary="List all tags")
async def list_tags(
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    session: Session = Depends(get_session)
):
    """List all tags with optional category filter."""
    try:
        tag_manager = TagManager(session)

        # Query tags
        query = session.query(LibrarianTag)
        if category:
            query = query.filter(LibrarianTag.category == category)

        tags = query.order_by(LibrarianTag.usage_count.desc()).limit(limit).all()

        tag_responses = []
        for tag in tags:
            tag_responses.append(TagResponse(
                id=tag.id,
                name=tag.name,
                description=tag.description,
                color=tag.color,
                category=tag.category,
                usage_count=tag.usage_count,
                created_at=tag.created_at.isoformat(),
                updated_at=tag.updated_at.isoformat()
            ))

        return TagListResponse(
            tags=tag_responses,
            total=len(tag_responses)
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error listing tags: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tags", response_model=TagResponse, summary="Create new tag")
async def create_tag(
    request: TagCreateRequest = Body(...),
    session: Session = Depends(get_session)
):
    """Create a new tag."""
    try:
        tag_manager = TagManager(session)

        tag = tag_manager.get_or_create_tag(
            name=request.name,
            description=request.description,
            category=request.category,
            color=request.color
        )

        return TagResponse(
            id=tag.id,
            name=tag.name,
            description=tag.description,
            color=tag.color,
            category=tag.category,
            usage_count=tag.usage_count,
            created_at=tag.created_at.isoformat(),
            updated_at=tag.updated_at.isoformat()
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error creating tag: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/statistics", response_model=TagStatisticsResponse, summary="Get tag statistics")
async def get_tag_statistics(
    session: Session = Depends(get_session)
):
    """Get comprehensive tag usage statistics."""
    try:
        tag_manager = TagManager(session)
        stats = tag_manager.get_tag_statistics()

        return TagStatisticsResponse(
            total_tags=stats.get("total_tags", 0),
            by_category=stats.get("by_category", {}),
            most_used=stats.get("most_used", []),
            recent_tags=stats.get("recent_tags", [])
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error getting tag statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/popular", response_model=TagListResponse, summary="Get popular tags")
async def get_popular_tags(
    limit: int = Query(20, ge=1, le=100, description="Number of tags to return"),
    session: Session = Depends(get_session)
):
    """Get most frequently used tags."""
    try:
        tags = session.query(LibrarianTag).order_by(
            LibrarianTag.usage_count.desc()
        ).limit(limit).all()

        tag_responses = []
        for tag in tags:
            tag_responses.append(TagResponse(
                id=tag.id,
                name=tag.name,
                description=tag.description,
                color=tag.color,
                category=tag.category,
                usage_count=tag.usage_count,
                created_at=tag.created_at.isoformat(),
                updated_at=tag.updated_at.isoformat()
            ))

        return TagListResponse(
            tags=tag_responses,
            total=len(tag_responses)
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error getting popular tags: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tags/{tag_id}", response_model=TagResponse, summary="Get tag by ID")
async def get_tag(
    tag_id: int = Path(..., description="Tag ID"),
    session: Session = Depends(get_session)
):
    """Get detailed information about a specific tag."""
    try:
        tag = session.query(LibrarianTag).filter(LibrarianTag.id == tag_id).first()

        if not tag:
            raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found")

        return TagResponse(
            id=tag.id,
            name=tag.name,
            description=tag.description,
            color=tag.color,
            category=tag.category,
            usage_count=tag.usage_count,
            created_at=tag.created_at.isoformat(),
            updated_at=tag.updated_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error getting tag {tag_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/tags/{tag_id}", response_model=TagResponse, summary="Update tag")
async def update_tag(
    tag_id: int = Path(..., description="Tag ID"),
    request: TagUpdateRequest = Body(...),
    session: Session = Depends(get_session)
):
    """Update an existing tag."""
    try:
        tag = session.query(LibrarianTag).filter(LibrarianTag.id == tag_id).first()

        if not tag:
            raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found")

        # Update fields
        if request.description is not None:
            tag.description = request.description
        if request.color is not None:
            tag.color = request.color
        if request.category is not None:
            tag.category = request.category

        tag.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(tag)

        return TagResponse(
            id=tag.id,
            name=tag.name,
            description=tag.description,
            color=tag.color,
            category=tag.category,
            usage_count=tag.usage_count,
            created_at=tag.created_at.isoformat(),
            updated_at=tag.updated_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error updating tag {tag_id}: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tags/{tag_id}", summary="Delete tag")
async def delete_tag(
    tag_id: int = Path(..., description="Tag ID"),
    session: Session = Depends(get_session)
):
    """Delete a tag and all its assignments."""
    try:
        tag = session.query(LibrarianTag).filter(LibrarianTag.id == tag_id).first()

        if not tag:
            raise HTTPException(status_code=404, detail=f"Tag {tag_id} not found")

        # Delete all assignments first
        session.query(DocumentTag).filter(DocumentTag.tag_id == tag_id).delete()

        # Delete the tag
        session.delete(tag)
        session.commit()

        return {"success": True, "message": f"Tag '{tag.name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error deleting tag {tag_id}: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/tags", response_model=DocumentTagsResponse, summary="Get document tags")
async def get_document_tags(
    document_id: int = Path(..., description="Document ID"),
    session: Session = Depends(get_session)
):
    """Get all tags assigned to a document."""
    try:
        tag_manager = TagManager(session)
        tags = tag_manager.get_document_tags(document_id)

        return DocumentTagsResponse(
            document_id=document_id,
            tags=tags,
            total=len(tags)
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error getting document {document_id} tags: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{document_id}/tags", summary="Assign tags to document")
async def assign_document_tags(
    document_id: int = Path(..., description="Document ID"),
    request: TagAssignRequest = Body(...),
    session: Session = Depends(get_session)
):
    """Assign tags to a document."""
    try:
        tag_manager = TagManager(session)

        assignments = tag_manager.assign_tags(
            document_id=document_id,
            tag_names=request.tag_names,
            assigned_by=request.assigned_by,
            confidence=request.confidence
        )

        return {
            "success": True,
            "message": f"Assigned {len(assignments)} tags to document {document_id}",
            "assignments": len(assignments)
        }

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error assigning tags to document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}/tags/{tag_name}", summary="Remove tag from document")
async def remove_document_tag(
    document_id: int = Path(..., description="Document ID"),
    tag_name: str = Path(..., description="Tag name to remove"),
    session: Session = Depends(get_session)
):
    """Remove a tag from a document."""
    try:
        tag_manager = TagManager(session)
        success = tag_manager.remove_tag(document_id, tag_name)

        if not success:
            raise HTTPException(status_code=404, detail=f"Tag '{tag_name}' not found on document {document_id}")

        return {"success": True, "message": f"Removed tag '{tag_name}' from document {document_id}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error removing tag from document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/tags", response_model=TagSearchResponse, summary="Search documents by tags")
async def search_by_tags(
    request: TagSearchRequest = Body(...),
    session: Session = Depends(get_session)
):
    """Search for documents that match specified tags."""
    try:
        tag_manager = TagManager(session)

        document_ids = tag_manager.search_documents_by_tags(
            tag_names=request.tag_names,
            match_all=request.match_all,
            limit=request.limit
        )

        # Get document info
        documents = []
        for doc_id in document_ids:
            doc = session.query(Document).filter(Document.id == doc_id).first()
            if doc:
                doc_tags = tag_manager.get_document_tags(doc_id)
                documents.append({
                    "id": doc.id,
                    "filename": doc.filename,
                    "file_path": doc.file_path,
                    "source": doc.source,
                    "tags": doc_tags,
                    "created_at": doc.created_at.isoformat()
                })

        return TagSearchResponse(
            documents=documents,
            total=len(documents),
            matched_tags=request.tag_names
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error searching by tags: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Relationship Endpoints ====================

@router.get("/documents/{document_id}/relationships", response_model=DocumentRelationshipsResponse, summary="Get document relationships")
async def get_document_relationships(
    document_id: int = Path(..., description="Document ID"),
    session: Session = Depends(get_session)
):
    """Get all relationships for a document."""
    try:
        rel_manager = RelationshipManager(
            session,
            get_embedding_model(),
            get_qdrant_client()
        )

        rels = rel_manager.get_document_relationships(document_id)

        def to_response(rel_dict):
            return RelationshipResponse(
                id=rel_dict["id"],
                source_document_id=rel_dict["source_document_id"],
                target_document_id=rel_dict["target_document_id"],
                relationship_type=rel_dict["relationship_type"],
                confidence=rel_dict["confidence"],
                strength=rel_dict["strength"],
                detected_by=rel_dict["detected_by"],
                created_at=rel_dict["created_at"]
            )

        return DocumentRelationshipsResponse(
            document_id=document_id,
            outgoing=[to_response(r) for r in rels["outgoing"]],
            incoming=[to_response(r) for r in rels["incoming"]],
            total=len(rels["outgoing"]) + len(rels["incoming"])
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error getting relationships for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relationships", response_model=RelationshipResponse, summary="Create relationship")
async def create_relationship(
    request: RelationshipCreateRequest = Body(...),
    session: Session = Depends(get_session)
):
    """Create a new relationship between documents."""
    try:
        rel_manager = RelationshipManager(
            session,
            get_embedding_model(),
            get_qdrant_client()
        )

        rel = rel_manager.create_relationship(
            source_id=request.source_document_id,
            target_id=request.target_document_id,
            type=request.relationship_type,
            confidence=request.confidence,
            strength=request.strength or 0.5,
            detected_by="manual"
        )

        return RelationshipResponse(
            id=rel.id,
            source_document_id=rel.source_document_id,
            target_document_id=rel.target_document_id,
            relationship_type=rel.relationship_type,
            confidence=rel.confidence,
            strength=rel.strength,
            detected_by=rel.detected_by,
            created_at=rel.created_at.isoformat()
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error creating relationship: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/relationships/{relationship_id}", summary="Delete relationship")
async def delete_relationship(
    relationship_id: int = Path(..., description="Relationship ID"),
    session: Session = Depends(get_session)
):
    """Delete a relationship."""
    try:
        rel = session.query(DocumentRelationship).filter(
            DocumentRelationship.id == relationship_id
        ).first()

        if not rel:
            raise HTTPException(status_code=404, detail=f"Relationship {relationship_id} not found")

        session.delete(rel)
        session.commit()

        return {"success": True, "message": f"Relationship {relationship_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error deleting relationship {relationship_id}: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}/graph", response_model=DependencyGraphResponse, summary="Get dependency graph")
async def get_dependency_graph(
    document_id: int = Path(..., description="Document ID"),
    max_depth: int = Query(3, ge=1, le=10, description="Maximum graph depth"),
    session: Session = Depends(get_session)
):
    """Get dependency graph for a document."""
    try:
        rel_manager = RelationshipManager(
            session,
            get_embedding_model(),
            get_qdrant_client()
        )

        graph = rel_manager.get_dependency_graph(document_id, max_depth=max_depth)

        return DependencyGraphResponse(
            root_document_id=document_id,
            nodes=graph["nodes"],
            edges=graph["edges"],
            depth=max_depth
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error getting dependency graph for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{document_id}/detect-relationships", summary="Detect relationships")
async def detect_relationships(
    document_id: int = Path(..., description="Document ID"),
    max_candidates: int = Query(20, ge=1, le=100, description="Maximum candidates"),
    similarity_threshold: float = Query(0.7, ge=0.0, le=1.0, description="Similarity threshold"),
    session: Session = Depends(get_session)
):
    """Trigger relationship detection for a document."""
    try:
        rel_manager = RelationshipManager(
            session,
            get_embedding_model(),
            get_qdrant_client()
        )

        relationships = rel_manager.detect_relationships(
            document_id=document_id,
            max_candidates=max_candidates,
            similarity_threshold=similarity_threshold
        )

        return {
            "success": True,
            "message": f"Detected {len(relationships)} relationships",
            "relationships": len(relationships)
        }

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error detecting relationships for document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Rule Management Endpoints ====================

@router.get("/rules", response_model=RuleListResponse, summary="List all rules")
async def list_rules(
    enabled_only: bool = Query(True, description="Only show enabled rules"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    session: Session = Depends(get_session)
):
    """List all categorization rules."""
    try:
        query = session.query(LibrarianRule)

        if enabled_only:
            query = query.filter(LibrarianRule.enabled == True)

        rules = query.order_by(LibrarianRule.priority.desc()).limit(limit).all()

        rule_responses = []
        for rule in rules:
            rule_responses.append(RuleResponse(
                id=rule.id,
                name=rule.name,
                pattern_type=rule.pattern_type,
                pattern_value=rule.pattern_value,
                action_type=rule.action_type,
                action_params=json.loads(rule.action_params) if isinstance(rule.action_params, str) else rule.action_params,
                priority=rule.priority,
                enabled=rule.enabled,
                matches_count=rule.matches_count,
                last_matched_at=rule.last_matched_at.isoformat() if rule.last_matched_at else None
            ))

        return RuleListResponse(
            rules=rule_responses,
            total=len(rule_responses)
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error listing rules: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules", response_model=RuleResponse, summary="Create rule")
async def create_rule(
    request: RuleCreateRequest = Body(...),
    session: Session = Depends(get_session)
):
    """Create a new categorization rule."""
    try:
        categorizer = RuleBasedCategorizer(session)

        rule = categorizer.create_rule(
            name=request.name,
            pattern_type=request.pattern_type,
            pattern_value=request.pattern_value,
            action_type=request.action_type,
            action_params=request.action_params,
            priority=request.priority,
            enabled=request.enabled
        )

        return RuleResponse(
            id=rule.id,
            name=rule.name,
            pattern_type=rule.pattern_type,
            pattern_value=rule.pattern_value,
            action_type=rule.action_type,
            action_params=json.loads(rule.action_params) if isinstance(rule.action_params, str) else rule.action_params,
            priority=rule.priority,
            enabled=rule.enabled,
            matches_count=rule.matches_count,
            last_matched_at=rule.last_matched_at.isoformat() if rule.last_matched_at else None
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error creating rule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/statistics", summary="Get rule statistics")
async def get_rule_statistics(
    session: Session = Depends(get_session)
):
    """Get rule effectiveness statistics."""
    try:
        categorizer = RuleBasedCategorizer(session)
        stats = categorizer.get_rule_statistics()

        return stats

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error getting rule statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/rules/{rule_id}", response_model=RuleResponse, summary="Get rule by ID")
async def get_rule(
    rule_id: int = Path(..., description="Rule ID"),
    session: Session = Depends(get_session)
):
    """Get detailed information about a specific rule."""
    try:
        rule = session.query(LibrarianRule).filter(LibrarianRule.id == rule_id).first()

        if not rule:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        return RuleResponse(
            id=rule.id,
            name=rule.name,
            pattern_type=rule.pattern_type,
            pattern_value=rule.pattern_value,
            action_type=rule.action_type,
            action_params=json.loads(rule.action_params) if isinstance(rule.action_params, str) else rule.action_params,
            priority=rule.priority,
            enabled=rule.enabled,
            matches_count=rule.matches_count,
            last_matched_at=rule.last_matched_at.isoformat() if rule.last_matched_at else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error getting rule {rule_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}", response_model=RuleResponse, summary="Update rule")
async def update_rule(
    rule_id: int = Path(..., description="Rule ID"),
    request: RuleUpdateRequest = Body(...),
    session: Session = Depends(get_session)
):
    """Update an existing rule."""
    try:
        rule = session.query(LibrarianRule).filter(LibrarianRule.id == rule_id).first()

        if not rule:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        # Update fields
        if request.name is not None:
            rule.name = request.name
        if request.pattern_value is not None:
            rule.pattern_value = request.pattern_value
        if request.action_params is not None:
            rule.action_params = json.dumps(request.action_params)
        if request.priority is not None:
            rule.priority = request.priority
        if request.enabled is not None:
            rule.enabled = request.enabled

        rule.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(rule)

        return RuleResponse(
            id=rule.id,
            name=rule.name,
            pattern_type=rule.pattern_type,
            pattern_value=rule.pattern_value,
            action_type=rule.action_type,
            action_params=json.loads(rule.action_params) if isinstance(rule.action_params, str) else rule.action_params,
            priority=rule.priority,
            enabled=rule.enabled,
            matches_count=rule.matches_count,
            last_matched_at=rule.last_matched_at.isoformat() if rule.last_matched_at else None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error updating rule {rule_id}: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}", summary="Delete rule")
async def delete_rule(
    rule_id: int = Path(..., description="Rule ID"),
    session: Session = Depends(get_session)
):
    """Delete a rule."""
    try:
        rule = session.query(LibrarianRule).filter(LibrarianRule.id == rule_id).first()

        if not rule:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        session.delete(rule)
        session.commit()

        return {"success": True, "message": f"Rule '{rule.name}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error deleting rule {rule_id}: {e}", exc_info=True)
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules/{rule_id}/test", response_model=RuleTestResponse, summary="Test rule")
async def test_rule(
    rule_id: int = Path(..., description="Rule ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum documents to test"),
    session: Session = Depends(get_session)
):
    """Test a rule against existing documents."""
    try:
        categorizer = RuleBasedCategorizer(session)

        matches = categorizer.test_rule_against_documents(rule_id, limit=limit)

        rule = session.query(LibrarianRule).filter(LibrarianRule.id == rule_id).first()
        rule_name = rule.name if rule else f"Rule {rule_id}"

        return RuleTestResponse(
            rule_id=rule_id,
            rule_name=rule_name,
            matched_documents=matches,
            total_matches=len(matches)
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error testing rule {rule_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Approval Workflow Endpoints ====================

@router.get("/actions/pending", response_model=ActionListResponse, summary="Get pending actions")
async def get_pending_actions(
    permission_tier: Optional[str] = Query(None, description="Filter by permission tier"),
    session: Session = Depends(get_session)
):
    """Get all pending actions requiring approval."""
    try:
        workflow = ApprovalWorkflow(session)
        pending = workflow.get_pending_actions(permission_tier=permission_tier)

        # Get counts
        all_actions = session.query(LibrarianAction).all()
        pending_count = sum(1 for a in all_actions if a.status == "pending")
        approved_count = sum(1 for a in all_actions if a.status == "approved")
        rejected_count = sum(1 for a in all_actions if a.status == "rejected")

        action_responses = []
        for action in pending:
            action_responses.append(ActionResponse(
                id=action.id,
                document_id=action.document_id,
                action_type=action.action_type,
                action_params=json.loads(action.action_params) if isinstance(action.action_params, str) else action.action_params,
                permission_tier=action.permission_tier,
                status=action.status,
                confidence=action.confidence,
                reason=action.reason,
                reviewed_by=action.reviewed_by,
                created_at=action.created_at.isoformat(),
                updated_at=action.updated_at.isoformat()
            ))

        return ActionListResponse(
            actions=action_responses,
            total=len(action_responses),
            pending_count=pending_count,
            approved_count=approved_count,
            rejected_count=rejected_count
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error getting pending actions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/{action_id}/approve", summary="Approve action")
async def approve_action(
    action_id: int = Path(..., description="Action ID"),
    request: ActionApproveRequest = Body(...),
    session: Session = Depends(get_session)
):
    """Approve a pending action."""
    try:
        workflow = ApprovalWorkflow(session)

        success = workflow.approve_action(
            action_id=action_id,
            reviewed_by=request.reviewed_by,
            notes=request.notes
        )

        if not success:
            raise HTTPException(status_code=404, detail=f"Action {action_id} not found or not pending")

        return {"success": True, "message": f"Action {action_id} approved successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error approving action {action_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/{action_id}/reject", summary="Reject action")
async def reject_action(
    action_id: int = Path(..., description="Action ID"),
    request: ActionRejectRequest = Body(...),
    session: Session = Depends(get_session)
):
    """Reject a pending action."""
    try:
        workflow = ApprovalWorkflow(session)

        success = workflow.reject_action(
            action_id=action_id,
            reviewed_by=request.reviewed_by,
            reason=request.reason
        )

        if not success:
            raise HTTPException(status_code=404, detail=f"Action {action_id} not found or not pending")

        return {"success": True, "message": f"Action {action_id} rejected successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error rejecting action {action_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/actions/batch-approve", summary="Batch approve actions")
async def batch_approve_actions(
    request: BatchApproveRequest = Body(...),
    session: Session = Depends(get_session)
):
    """Approve multiple actions at once."""
    try:
        workflow = ApprovalWorkflow(session)

        count = workflow.batch_approve(
            action_ids=request.action_ids,
            reviewed_by=request.reviewed_by
        )

        return {
            "success": True,
            "message": f"Approved {count} actions successfully",
            "approved": count
        }

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error batch approving actions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions/audit", summary="Get audit log")
async def get_audit_log(
    document_id: Optional[int] = Query(None, description="Filter by document ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum results"),
    session: Session = Depends(get_session)
):
    """Get audit log of all actions."""
    try:
        query = session.query(LibrarianAudit)

        if document_id:
            query = query.filter(LibrarianAudit.document_id == document_id)

        audit_entries = query.order_by(LibrarianAudit.created_at.desc()).limit(limit).all()

        entries = []
        for entry in audit_entries:
            entries.append({
                "id": entry.id,
                "action_id": entry.action_id,
                "document_id": entry.document_id,
                "action_type": entry.action_type,
                "action_details": json.loads(entry.action_details) if isinstance(entry.action_details, str) else entry.action_details,
                "status": entry.status,
                "error_message": entry.error_message,
                "created_at": entry.created_at.isoformat()
            })

        return {"audit_entries": entries, "total": len(entries)}

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error getting audit log: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions/statistics", summary="Get action statistics")
async def get_action_statistics(
    session: Session = Depends(get_session)
):
    """Get action workflow statistics."""
    try:
        workflow = ApprovalWorkflow(session)
        stats = workflow.get_action_statistics()

        return stats

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error getting action statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Processing & Statistics Endpoints ====================

@router.post("/process/{document_id}", response_model=ProcessingResponse, summary="Process document")
async def process_document(
    document_id: int = Path(..., description="Document ID"),
    use_ai: Optional[bool] = Query(None, description="Use AI analysis"),
    detect_relationships: Optional[bool] = Query(None, description="Detect relationships"),
    session: Session = Depends(get_session)
):
    """Process a document through the librarian system."""
    try:
        import time
        start_time = time.time()

        librarian = get_librarian_engine(session)

        result = librarian.process_document(
            document_id=document_id,
            use_ai=use_ai,
            detect_relationships=detect_relationships,
            auto_execute=True
        )

        processing_time = time.time() - start_time

        return ProcessingResponse(
            status=result["status"],
            document_id=document_id,
            tags_assigned=result["tags_assigned"],
            relationships_detected=result["relationships_detected"],
            rules_matched=result["rules_matched"],
            ai_analysis=result.get("ai_analysis"),
            processing_time=processing_time
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error processing document {document_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/batch", response_model=BatchProcessingResponse, summary="Batch process documents")
async def batch_process_documents(
    request: BatchProcessingRequest = Body(...),
    session: Session = Depends(get_session)
):
    """Process multiple documents in batch."""
    try:
        librarian = get_librarian_engine(session)

        results = librarian.process_batch(
            document_ids=request.document_ids,
            use_ai=request.use_ai,
            detect_relationships=request.detect_relationships,
            skip_errors=True
        )

        processing_responses = []
        successful = 0
        failed = 0

        for result in results:
            if result["status"] == "success":
                successful += 1
            else:
                failed += 1

            processing_responses.append(ProcessingResponse(
                status=result["status"],
                document_id=result["document_id"],
                tags_assigned=result.get("tags_assigned", 0),
                relationships_detected=result.get("relationships_detected", 0),
                rules_matched=result.get("rules_matched", []),
                ai_analysis=result.get("ai_analysis"),
                processing_time=result.get("processing_time", 0.0)
            ))

        return BatchProcessingResponse(
            total=len(request.document_ids),
            successful=successful,
            failed=failed,
            results=processing_responses
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error batch processing documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/all", summary="Reprocess all documents")
async def reprocess_all_documents(
    request: ReprocessAllRequest = Body(...),
    session: Session = Depends(get_session)
):
    """Reprocess all documents in the knowledge base."""
    try:
        librarian = get_librarian_engine(session)

        summary = librarian.reprocess_all_documents(
            use_ai=request.use_ai,
            detect_relationships=request.detect_relationships,
            batch_size=request.batch_size,
            limit=request.limit
        )

        return summary

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error reprocessing all documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=StatisticsResponse, summary="Get system statistics")
async def get_statistics(
    session: Session = Depends(get_session)
):
    """Get comprehensive librarian system statistics."""
    try:
        librarian = get_librarian_engine(session)
        stats = librarian.get_system_statistics()

        return StatisticsResponse(
            tags=stats["tags"],
            rules=stats["rules"],
            relationships=stats["relationships"],
            documents_processed=stats.get("documents_processed", 0),
            ai_available=stats["ai_available"],
            relationships_enabled=stats["relationships_enabled"]
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error getting statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthCheckResponse, summary="Health check")
async def health_check(
    session: Session = Depends(get_session)
):
    """Check librarian system health."""
    try:
        librarian = get_librarian_engine(session)
        health = librarian.health_check()

        return HealthCheckResponse(
            overall_status=health["overall_status"],
            components=health["components"],
            version="1.0.0"
        )

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error checking health: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Genesis Key Curation Endpoints ====================

@router.post("/genesis-keys/curate-today", summary="Curate today's Genesis Keys")
async def curate_genesis_keys_today(
    session: Session = Depends(get_session)
):
    """
    Curate Genesis Keys for today.

    Exports all Genesis Keys to Layer 1 organized by type with metadata.
    """
    try:
        from librarian.genesis_key_curator import get_genesis_key_curator

        curator = get_genesis_key_curator()
        result = curator.curate_today(session=session)

        return result

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error curating Genesis Keys: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/genesis-keys/curate-yesterday", summary="Curate yesterday's Genesis Keys")
async def curate_genesis_keys_yesterday(
    session: Session = Depends(get_session)
):
    """Curate Genesis Keys for yesterday (useful for missed days)."""
    try:
        from librarian.genesis_key_curator import get_genesis_key_curator

        curator = get_genesis_key_curator()
        result = curator.curate_yesterday(session=session)

        return result

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error curating yesterday's keys: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/genesis-keys/backfill", summary="Backfill missing days")
async def backfill_genesis_keys(
    days_back: int = Query(7, ge=1, le=30, description="Number of days to backfill"),
    session: Session = Depends(get_session)
):
    """Backfill Genesis Key curation for missing days."""
    try:
        from librarian.genesis_key_curator import get_genesis_key_curator

        curator = get_genesis_key_curator()
        result = curator.backfill_missing_days(days_back=days_back, session=session)

        return result

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error backfilling keys: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/genesis-keys/status", summary="Get curation status")
async def get_curation_status():
    """Get current Genesis Key curation status."""
    try:
        from librarian.genesis_key_curator import get_genesis_key_curator

        curator = get_genesis_key_curator()
        status = curator.get_curation_status()

        return status

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error getting curation status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/genesis-keys/start-scheduler", summary="Start daily curation scheduler")
async def start_curation_scheduler():
    """Start the 24-hour Genesis Key curation scheduler."""
    try:
        from librarian.genesis_key_curator import get_genesis_key_curator

        curator = get_genesis_key_curator()
        curator.schedule_daily_curation()

        return {
            "success": True,
            "message": "Genesis Key daily curation scheduler started",
            "next_run": "00:00 UTC daily"
        }

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error starting scheduler: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/genesis-keys/stop-scheduler", summary="Stop daily curation scheduler")
async def stop_curation_scheduler():
    """Stop the 24-hour Genesis Key curation scheduler."""
    try:
        from librarian.genesis_key_curator import get_genesis_key_curator

        curator = get_genesis_key_curator()
        curator.stop_scheduler()

        return {
            "success": True,
            "message": "Genesis Key daily curation scheduler stopped"
        }

    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error stopping scheduler: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/genesis-keys/summary/{date}", summary="Get daily summary")
async def get_daily_summary(
    date: str = Path(..., description="Date in YYYY-MM-DD format")
):
    """Get metadata summary for a specific day."""
    try:
        from genesis.daily_organizer import get_daily_organizer

        organizer = get_daily_organizer()
        summary = organizer.get_daily_summary(date)

        if not summary:
            raise HTTPException(status_code=404, detail=f"No summary found for {date}")

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LIBRARIAN-API] Error getting daily summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
