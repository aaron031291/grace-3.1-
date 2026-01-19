"""
Whitelist Learning Pipeline API
===============================
REST API for the Whitelist Learning Pipeline.
Human-approved data flows through GRACE's complete learning system.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
import json
import logging

from genesis.whitelist_learning_pipeline import (
    get_whitelist_pipeline,
    DataCategory,
    TrustLevel,
    PipelineStage,
    WhitelistEntry,
    PipelineResult
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whitelist", tags=["Whitelist Learning"])


# =============================================================================
# Request/Response Models
# =============================================================================

class WhitelistProcessRequest(BaseModel):
    """Request to process data through the whitelist pipeline."""
    content: str = Field(..., description="Content to process")
    source: str = Field(..., description="Source of the data (who provided it)")
    category: str = Field(..., description="Category of data")
    trust_level: str = Field(default="medium", description="Trust level of source")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    user_id: Optional[str] = Field(default=None, description="User ID if from a user")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    parent_entry_id: Optional[str] = Field(default=None, description="Parent entry ID")


class TrainingExampleRequest(BaseModel):
    """Request to add a training example."""
    input_text: str = Field(..., description="Input for the training example")
    output_text: str = Field(..., description="Expected output")
    source: str = Field(default="human", description="Source of the example")
    trust_level: str = Field(default="verified", description="Trust level")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class FeedbackRequest(BaseModel):
    """Request to submit feedback for learning."""
    content: str = Field(..., description="Feedback content")
    feedback_type: str = Field(..., description="Type: positive, negative, correction")
    related_genesis_key: Optional[str] = Field(default=None, description="Related Genesis Key")
    source: str = Field(default="human", description="Source of feedback")


class KnowledgeFactRequest(BaseModel):
    """Request to add a knowledge fact."""
    fact: str = Field(..., description="The knowledge fact")
    domain: str = Field(default="general", description="Knowledge domain")
    source: str = Field(..., description="Source of the fact")
    trust_level: str = Field(default="medium", description="Trust level")
    verification_status: str = Field(default="unverified", description="Verification status")


class PipelineResponse(BaseModel):
    """Response for pipeline processing."""
    success: bool
    entry_id: str
    genesis_key: str
    stage: str
    stages_completed: List[str]
    file_path: Optional[str]
    memory_id: Optional[str]
    embedding_id: Optional[str]
    knowledge_id: Optional[str]
    patterns_found: int
    contradictions_found: int
    trust_score: float
    confidence: float
    duration_ms: int
    message: str


# =============================================================================
# Processing Endpoints
# =============================================================================

@router.post("/process", response_model=PipelineResponse)
async def process_whitelist_entry(request: WhitelistProcessRequest):
    """
    Process data through the complete whitelist learning pipeline.

    Pipeline stages:
    1. Trust Verification
    2. Genesis Key Assignment
    3. Data Extraction
    4. Librarian Filing
    5. Embedding Generation
    6. Memory Storage
    7. Memory Mesh Linking
    8. Cognitive Processing
    9. Clarity Analysis
    10. Contradiction Check
    11. Pattern Extraction
    12. ML Training
    13. Knowledge Base Update
    14. Proactive Learning
    15. Mirror Observation
    """
    pipeline = get_whitelist_pipeline()

    try:
        category = DataCategory(request.category)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid category: {request.category}. Valid: {[c.value for c in DataCategory]}"
        )

    try:
        trust_level = TrustLevel(request.trust_level)
    except ValueError:
        trust_level = TrustLevel.MEDIUM

    result = await pipeline.process(
        content=request.content,
        source=request.source,
        category=category,
        trust_level=trust_level,
        metadata=request.metadata,
        user_id=request.user_id,
        session_id=request.session_id,
        parent_entry_id=request.parent_entry_id
    )

    return PipelineResponse(
        success=result.success,
        entry_id=result.entry_id,
        genesis_key=result.genesis_key,
        stage=result.stage.value,
        stages_completed=result.stages_completed,
        file_path=result.file_path,
        memory_id=result.memory_id,
        embedding_id=result.embedding_id,
        knowledge_id=result.knowledge_id,
        patterns_found=len(result.patterns_found),
        contradictions_found=len(result.contradictions),
        trust_score=result.trust_score,
        confidence=result.confidence,
        duration_ms=result.duration_ms,
        message=result.message
    )


@router.post("/training-example")
async def add_training_example(request: TrainingExampleRequest):
    """
    Add a training example for ML learning.

    Training examples are processed with high priority and
    directly contribute to GRACE's learning.
    """
    pipeline = get_whitelist_pipeline()

    # Format as training example
    content = f"""## Training Example

### Input:
{request.input_text}

### Expected Output:
{request.output_text}
"""

    try:
        trust_level = TrustLevel(request.trust_level)
    except ValueError:
        trust_level = TrustLevel.VERIFIED

    result = await pipeline.process(
        content=content,
        source=request.source,
        category=DataCategory.TRAINING_EXAMPLE,
        trust_level=trust_level,
        metadata={
            "input_text": request.input_text,
            "output_text": request.output_text,
            **(request.metadata or {})
        }
    )

    return {
        "success": result.success,
        "entry_id": result.entry_id,
        "genesis_key": result.genesis_key,
        "patterns_found": len(result.patterns_found),
        "message": "Training example added for learning"
    }


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """
    Submit feedback for GRACE to learn from.

    Feedback types:
    - positive: Reinforces good behavior
    - negative: Indicates issues to avoid
    - correction: Provides correct answer/approach
    """
    pipeline = get_whitelist_pipeline()

    # Determine category based on feedback type
    if request.feedback_type == "correction":
        category = DataCategory.CORRECTION
    else:
        category = DataCategory.FEEDBACK

    content = f"""## Feedback ({request.feedback_type})

{request.content}

Related Genesis Key: {request.related_genesis_key or 'N/A'}
"""

    result = await pipeline.process(
        content=content,
        source=request.source,
        category=category,
        trust_level=TrustLevel.HIGH,
        metadata={
            "feedback_type": request.feedback_type,
            "related_genesis_key": request.related_genesis_key
        }
    )

    return {
        "success": result.success,
        "entry_id": result.entry_id,
        "genesis_key": result.genesis_key,
        "message": f"Feedback ({request.feedback_type}) processed"
    }


@router.post("/knowledge-fact")
async def add_knowledge_fact(request: KnowledgeFactRequest):
    """
    Add a knowledge fact to GRACE's knowledge base.

    Facts can be verified or unverified based on trust level.
    """
    pipeline = get_whitelist_pipeline()

    content = f"""## Knowledge Fact

**Domain:** {request.domain}
**Verification:** {request.verification_status}

{request.fact}
"""

    try:
        trust_level = TrustLevel(request.trust_level)
    except ValueError:
        trust_level = TrustLevel.MEDIUM

    result = await pipeline.process(
        content=content,
        source=request.source,
        category=DataCategory.KNOWLEDGE_FACT,
        trust_level=trust_level,
        metadata={
            "domain": request.domain,
            "verification_status": request.verification_status,
            "fact": request.fact
        }
    )

    return {
        "success": result.success,
        "entry_id": result.entry_id,
        "genesis_key": result.genesis_key,
        "knowledge_id": result.knowledge_id,
        "message": "Knowledge fact added"
    }


@router.post("/human-request")
async def process_human_request(
    request: str,
    source: str = "human",
    user_id: str = None,
    session_id: str = None
):
    """
    Process a human request through the learning pipeline.

    Human requests are analyzed and can trigger proactive learning.
    """
    pipeline = get_whitelist_pipeline()

    result = await pipeline.process(
        content=request,
        source=source,
        category=DataCategory.HUMAN_REQUEST,
        trust_level=TrustLevel.HIGH,
        user_id=user_id,
        session_id=session_id
    )

    return {
        "success": result.success,
        "entry_id": result.entry_id,
        "genesis_key": result.genesis_key,
        "stages_completed": result.stages_completed,
        "insights": result.insights,
        "message": "Human request processed"
    }


# =============================================================================
# Query Endpoints
# =============================================================================

@router.get("/entries")
async def list_entries(
    category: Optional[str] = None,
    trust_level: Optional[str] = None,
    limit: int = 100
):
    """
    List whitelist entries.

    Filter by category or trust level.
    """
    pipeline = get_whitelist_pipeline()

    cat_filter = DataCategory(category) if category else None
    trust_filter = TrustLevel(trust_level) if trust_level else None

    entries = pipeline.list_entries(
        category=cat_filter,
        trust_level=trust_filter,
        limit=limit
    )

    return {
        "count": len(entries),
        "entries": [
            {
                "entry_id": e.entry_id,
                "source": e.source,
                "category": e.category.value,
                "trust_level": e.trust_level.value,
                "genesis_key": e.genesis_key,
                "created_at": e.created_at,
                "content_preview": e.content[:200] + "..." if len(e.content) > 200 else e.content
            }
            for e in entries
        ]
    }


@router.get("/entries/{entry_id}")
async def get_entry(entry_id: str):
    """
    Get details of a specific whitelist entry.

    Includes full content and metadata.
    """
    pipeline = get_whitelist_pipeline()

    entry = pipeline.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry not found: {entry_id}")

    result = pipeline.get_result(entry_id)

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "source": entry.source,
            "category": entry.category.value,
            "content": entry.content,
            "trust_level": entry.trust_level.value,
            "genesis_key": entry.genesis_key,
            "user_id": entry.user_id,
            "session_id": entry.session_id,
            "parent_entry_id": entry.parent_entry_id,
            "metadata": entry.metadata,
            "created_at": entry.created_at
        },
        "result": {
            "success": result.success,
            "stage": result.stage.value,
            "stages_completed": result.stages_completed,
            "file_path": result.file_path,
            "memory_id": result.memory_id,
            "embedding_id": result.embedding_id,
            "knowledge_id": result.knowledge_id,
            "patterns_found": result.patterns_found,
            "contradictions": result.contradictions,
            "trust_score": result.trust_score,
            "confidence": result.confidence,
            "duration_ms": result.duration_ms
        } if result else None
    }


# =============================================================================
# Statistics Endpoints
# =============================================================================

@router.get("/statistics")
async def get_statistics():
    """
    Get whitelist pipeline statistics.

    Returns counts, success rates, and integration status.
    """
    pipeline = get_whitelist_pipeline()
    return pipeline.get_statistics()


@router.get("/integrations")
async def list_integrations():
    """
    List all pipeline integrations and their status.

    Shows which GRACE systems are connected.
    """
    pipeline = get_whitelist_pipeline()
    stats = pipeline.get_statistics()

    integrations = []
    for name, connected in stats.get("integrations", {}).items():
        integrations.append({
            "name": name.replace("_", " ").title(),
            "connected": connected,
            "status": "connected" if connected else "not available"
        })

    return {
        "total": len(integrations),
        "connected": sum(1 for i in integrations if i["connected"]),
        "integrations": integrations
    }


# =============================================================================
# Reference Data Endpoints
# =============================================================================

@router.get("/categories")
async def list_categories():
    """
    List available data categories.

    Each category has different processing rules.
    """
    descriptions = {
        "human_request": "Direct request from a human user",
        "research_data": "Research data for analysis",
        "code_snippet": "Code examples and snippets",
        "documentation": "Documentation and guides",
        "conversation": "Conversation logs for learning",
        "feedback": "Feedback on GRACE's responses",
        "correction": "Corrections to improve accuracy",
        "preference": "User preferences for personalization",
        "training_example": "Input/output pairs for training",
        "knowledge_fact": "Facts to add to knowledge base"
    }

    return {
        "categories": [
            {
                "value": c.value,
                "name": c.name,
                "description": descriptions.get(c.value, "")
            }
            for c in DataCategory
        ]
    }


@router.get("/trust-levels")
async def list_trust_levels():
    """
    List available trust levels.

    Higher trust levels receive priority processing.
    """
    descriptions = {
        "untrusted": "Unknown or untrusted source - minimal processing",
        "low": "Low trust - basic processing with verification",
        "medium": "Medium trust - standard processing",
        "high": "High trust - full processing with learning",
        "verified": "Verified source - trusted for training",
        "owner": "Owner/admin - full trust for all operations"
    }

    thresholds = {
        "untrusted": 0.0,
        "low": 0.25,
        "medium": 0.5,
        "high": 0.75,
        "verified": 0.9,
        "owner": 1.0
    }

    return {
        "trust_levels": [
            {
                "value": t.value,
                "name": t.name,
                "threshold": thresholds.get(t.value, 0.0),
                "description": descriptions.get(t.value, "")
            }
            for t in TrustLevel
        ]
    }


@router.get("/stages")
async def list_pipeline_stages():
    """
    List all pipeline stages.

    Shows the complete flow of data processing.
    """
    stage_order = [
        ("whitelist_entry", "Entry received"),
        ("trust_verification", "Verify source trust level"),
        ("genesis_key_assignment", "Assign Genesis Key for tracking"),
        ("data_extraction", "Extract content features"),
        ("content_analysis", "Analyze content"),
        ("librarian_filing", "File with Librarian"),
        ("file_naming", "Generate file name"),
        ("embedding_generation", "Generate vector embeddings"),
        ("memory_storage", "Store in learning memory"),
        ("memory_mesh_linking", "Link in memory mesh"),
        ("cognitive_processing", "Process through cognitive engine"),
        ("clarity_analysis", "Apply clarity framework"),
        ("contradiction_check", "Check for contradictions"),
        ("pattern_extraction", "Extract patterns for ML"),
        ("ml_training", "Queue for ML training"),
        ("knowledge_base_update", "Update knowledge base"),
        ("proactive_learning", "Trigger proactive learning"),
        ("mirror_observation", "Mirror observes learning"),
        ("complete", "Pipeline complete"),
        ("failed", "Pipeline failed")
    ]

    return {
        "stages": [
            {
                "value": stage,
                "order": idx + 1,
                "description": desc
            }
            for idx, (stage, desc) in enumerate(stage_order)
        ]
    }


# =============================================================================
# Health Endpoint
# =============================================================================

@router.get("/health")
async def whitelist_health():
    """
    Check whitelist pipeline health.

    Returns integration status and processing statistics.
    """
    pipeline = get_whitelist_pipeline()
    stats = pipeline.get_statistics()

    integrations = stats.get("integrations", {})
    connected_count = sum(1 for v in integrations.values() if v)
    total_integrations = len(integrations)

    return {
        "status": "healthy",
        "total_entries": stats.get("total_entries", 0),
        "total_processed": stats.get("total_processed", 0),
        "success_rate": stats.get("success_rate", 0.0),
        "integrations_connected": f"{connected_count}/{total_integrations}",
        "integration_health": "good" if connected_count >= total_integrations * 0.5 else "degraded"
    }
