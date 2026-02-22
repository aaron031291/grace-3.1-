"""
Learning Memory API Endpoints

Provides access to learning memory system with trust scoring
and integration with memory mesh.

Classes:
- `LearningExperienceRequest`
- `FeedbackRequest`
- `TrainingDataRequest`
- `PatternResponse`
- `PatternsListResponse`
- `PatternExtractRequest`
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from sqlalchemy.orm import Session
from pathlib import Path

from database.session import get_session
from cognitive.memory_mesh_integration import MemoryMeshIntegration
from cognitive.memory_mesh_snapshot import MemoryMeshSnapshot, create_memory_mesh_snapshot
from settings import KNOWLEDGE_BASE_PATH


router = APIRouter(prefix="/learning-memory", tags=["Learning Memory"])


# ==================== Pydantic Models ====================

class LearningExperienceRequest(BaseModel):
    """Request to record a learning experience."""
    experience_type: str = Field(..., description="Type: success, failure, feedback, correction, pattern")
    context: Dict[str, Any] = Field(..., description="Contextual information")
    action_taken: Dict[str, Any] = Field(..., description="What was done")
    outcome: Dict[str, Any] = Field(..., description="What happened")
    expected_outcome: Optional[Dict[str, Any]] = Field(None, description="What was expected")
    source: str = Field("system_observation", description="Source of learning")
    user_id: Optional[str] = Field(None, description="Genesis ID if user-provided")
    genesis_key_id: Optional[str] = Field(None, description="Link to Genesis Key")


class FeedbackRequest(BaseModel):
    """User feedback on Grace's performance."""
    interaction_id: str = Field(..., description="ID of interaction being rated")
    feedback_type: str = Field(..., description="positive, negative, correction")
    feedback_text: Optional[str] = Field(None, description="Optional text feedback")
    rating: Optional[float] = Field(None, description="Rating 0-1")
    correction: Optional[Dict[str, Any]] = Field(None, description="Corrected output")
    user_id: str = Field(..., description="Genesis ID of user providing feedback")


class TrainingDataRequest(BaseModel):
    """Request to get training data."""
    experience_type: Optional[str] = Field(None, description="Filter by type")
    min_trust_score: float = Field(0.7, description="Minimum trust threshold")
    max_examples: int = Field(1000, description="Maximum examples")
    export_format: str = Field("json", description="json or jsonl")


# ==================== Endpoints ====================

@router.post("/record-experience")
async def record_learning_experience(
    request: LearningExperienceRequest,
    session: Session = Depends(get_session)
):
    """
    Record a learning experience in the memory mesh.

    This is the main entry point for learning data.
    Automatically:
    1. Calculates trust scores
    2. Stores in learning memory
    3. Feeds to episodic memory if high trust
    4. Creates/updates procedures if applicable
    """
    try:
        mesh = MemoryMeshIntegration(session, Path(KNOWLEDGE_BASE_PATH))

        example_id = mesh.ingest_learning_experience(
            experience_type=request.experience_type,
            context=request.context,
            action_taken=request.action_taken,
            outcome=request.outcome,
            expected_outcome=request.expected_outcome,
            source=request.source,
            user_id=request.user_id,
            genesis_key_id=request.genesis_key_id
        )

        return {
            "success": True,
            "learning_example_id": example_id,
            "message": "Learning experience recorded and integrated into memory mesh"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/user-feedback")
async def record_user_feedback(
    request: FeedbackRequest,
    session: Session = Depends(get_session)
):
    """
    Record user feedback.

    User feedback is high-value learning data with high trust scores.
    """
    try:
        mesh = MemoryMeshIntegration(session, Path(KNOWLEDGE_BASE_PATH))

        # Determine source based on feedback type
        if request.feedback_type == "positive":
            source = "user_feedback_positive"
        elif request.feedback_type == "negative":
            source = "user_feedback_negative"
        else:
            source = "user_feedback_correction"

        # Build learning data
        context = {
            "interaction_id": request.interaction_id,
            "feedback_type": request.feedback_type,
            "rating": request.rating
        }

        action_taken = {
            "type": "ai_response",
            "interaction_id": request.interaction_id
        }

        # Outcome depends on feedback type
        if request.correction:
            outcome = request.correction
            expected_outcome = None
        else:
            outcome = {
                "feedback": request.feedback_text,
                "rating": request.rating
            }
            expected_outcome = outcome

        example_id = mesh.ingest_learning_experience(
            experience_type="feedback",
            context=context,
            action_taken=action_taken,
            outcome=outcome,
            expected_outcome=expected_outcome,
            source=source,
            user_id=request.user_id
        )

        return {
            "success": True,
            "learning_example_id": example_id,
            "message": "User feedback recorded and integrated"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/training-data")
async def get_training_data(
    experience_type: Optional[str] = None,
    min_trust_score: float = 0.7,
    max_examples: int = 1000,
    session: Session = Depends(get_session)
):
    """
    Get high-trust training data.

    Returns learning examples suitable for:
    - Fine-tuning language models
    - Training classifiers
    - Improving inference patterns

    Only returns examples with trust score >= min_trust_score.
    """
    try:
        mesh = MemoryMeshIntegration(session, Path(KNOWLEDGE_BASE_PATH))

        training_data = mesh.get_training_dataset(
            experience_type=experience_type,
            min_trust_score=min_trust_score,
            max_examples=max_examples
        )

        return {
            "success": True,
            "count": len(training_data),
            "min_trust_score": min_trust_score,
            "data": training_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export-training-data")
async def export_training_data(
    request: TrainingDataRequest,
    session: Session = Depends(get_session)
):
    """
    Export training data to file.

    Useful for:
    - Fine-tuning external models
    - Sharing datasets
    - Backup/archival
    """
    try:
        mesh = MemoryMeshIntegration(session, Path(KNOWLEDGE_BASE_PATH))

        # Generate filename
        timestamp = int(datetime.now().timestamp())
        filename = f"training_data_{timestamp}.{request.export_format}"
        output_path = Path(KNOWLEDGE_BASE_PATH) / "exports" / filename

        # Ensure export directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        mesh.export_training_data_to_file(
            output_path=output_path,
            experience_type=request.experience_type,
            min_trust_score=request.min_trust_score,
            format=request.export_format
        )

        return {
            "success": True,
            "file_path": str(output_path),
            "format": request.export_format,
            "message": f"Training data exported to {filename}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_memory_mesh_stats(session: Session = Depends(get_session)):
    """
    Get statistics about the entire memory mesh.

    Shows:
    - Learning memory stats (examples, trust ratios)
    - Episodic memory stats (episodes, linkages)
    - Procedural memory stats (procedures, success rates)
    - Pattern extraction stats
    """
    try:
        mesh = MemoryMeshIntegration(session, Path(KNOWLEDGE_BASE_PATH))

        stats = mesh.get_memory_mesh_stats()

        return {
            "success": True,
            "stats": stats
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-folders")
async def sync_learning_folders(session: Session = Depends(get_session)):
    """
    Sync learning memory from file system folders.

    Reads all files from knowledge_base/layer_1/learning_memory/*
    and ingests them into the memory mesh.

    Useful for:
    - Initial import of existing data
    - Batch processing
    - Recovery after database reset
    """
    try:
        mesh = MemoryMeshIntegration(session, Path(KNOWLEDGE_BASE_PATH))

        mesh.sync_learning_folders()

        return {
            "success": True,
            "message": "Learning memory folders synced to memory mesh"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/feedback-loop/{learning_example_id}")
async def update_from_feedback_loop(
    learning_example_id: str,
    success: bool,
    actual_outcome: Dict[str, Any],
    session: Session = Depends(get_session)
):
    """
    Feedback loop: Update trust scores based on real-world outcomes.

    When a learning example is used and we observe the outcome,
    update its trust score and associated memories.

    Args:
        learning_example_id: ID of learning example that was used
        success: Whether using it led to success
        actual_outcome: The actual outcome observed
    """
    try:
        mesh = MemoryMeshIntegration(session, Path(KNOWLEDGE_BASE_PATH))

        mesh.feedback_loop_update(
            learning_example_id=learning_example_id,
            actual_outcome=actual_outcome,
            success=success
        )

        return {
            "success": True,
            "message": "Trust scores updated based on outcome"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/decay-trust-scores")
async def decay_trust_scores(session: Session = Depends(get_session)):
    """
    Apply time-based decay to all trust scores.

    Should be run periodically (e.g., daily cron job).
    Older examples gradually lose trust weight.
    """
    try:
        mesh = MemoryMeshIntegration(session, Path(KNOWLEDGE_BASE_PATH))

        mesh.learning_memory.decay_trust_scores()

        return {
            "success": True,
            "message": "Trust scores decayed based on age"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Import datetime
from datetime import datetime


# ==================== Immutable Memory Mesh Snapshot Endpoints ====================

@router.post("/snapshot/create")
async def create_immutable_snapshot(
    save_to_file: bool = True,
    session: Session = Depends(get_session)
):
    """
    Create immutable snapshot of entire memory mesh.

    This captures the complete state of:
    - All learning examples
    - All episodic memories
    - All procedural memories
    - All extracted patterns

    The snapshot is saved as .genesis_immutable_memory_mesh.json
    and serves as a recoverable, permanent record.
    """
    try:
        snapshot = create_memory_mesh_snapshot(
            session=session,
            knowledge_base_path=Path(KNOWLEDGE_BASE_PATH),
            save=save_to_file
        )

        return {
            "success": True,
            "snapshot": {
                "timestamp": snapshot["snapshot_metadata"]["timestamp"],
                "total_memories": snapshot["statistics"]["total_memories"],
                "statistics": snapshot["statistics"]
            },
            "saved_to_file": save_to_file,
            "file_path": str(Path(KNOWLEDGE_BASE_PATH) / ".genesis_immutable_memory_mesh.json") if save_to_file else None,
            "message": "Immutable memory mesh snapshot created"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot/versioned")
async def create_versioned_snapshot(session: Session = Depends(get_session)):
    """
    Create timestamped version of memory mesh snapshot.

    Creates a snapshot with timestamp in filename:
    .genesis_immutable_memory_mesh_YYYYMMDD_HHMMSS.json

    Useful for:
    - Backup before major changes
    - Historical tracking
    - Recovery points
    """
    try:
        snapshotter = MemoryMeshSnapshot(session, Path(KNOWLEDGE_BASE_PATH))
        file_path = snapshotter.create_versioned_snapshot()

        return {
            "success": True,
            "file_path": file_path,
            "message": "Versioned snapshot created"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshot/load")
async def load_immutable_snapshot(session: Session = Depends(get_session)):
    """
    Load the latest immutable memory mesh snapshot.

    Returns the snapshot data without restoring it to the database.
    Use this to inspect what's in the snapshot.
    """
    try:
        snapshotter = MemoryMeshSnapshot(session, Path(KNOWLEDGE_BASE_PATH))
        snapshot = snapshotter.load_snapshot()

        if not snapshot:
            raise HTTPException(status_code=404, detail="No snapshot file found")

        return {
            "success": True,
            "snapshot": snapshot,
            "message": "Snapshot loaded"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/snapshot/restore")
async def restore_from_snapshot(session: Session = Depends(get_session)):
    """
    Restore memory mesh from immutable snapshot.

    WARNING: This will merge snapshot data with current database.
    Existing data with same IDs will be updated.

    Use cases:
    - Recovery after data loss
    - Syncing across environments
    - Restoring to known good state
    """
    try:
        snapshotter = MemoryMeshSnapshot(session, Path(KNOWLEDGE_BASE_PATH))
        snapshot = snapshotter.load_snapshot()

        if not snapshot:
            raise HTTPException(status_code=404, detail="No snapshot file found")

        stats = snapshotter.restore_from_snapshot(snapshot)

        return {
            "success": True,
            "restoration_stats": stats,
            "message": "Memory mesh restored from snapshot"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/snapshot/compare")
async def compare_snapshots(
    snapshot1_path: str,
    snapshot2_path: str,
    session: Session = Depends(get_session)
):
    """
    Compare two snapshots to see what changed.

    Useful for:
    - Tracking learning progress
    - Auditing changes
    - Understanding growth over time
    """
    try:
        import json

        with open(snapshot1_path, 'r') as f:
            snapshot1 = json.load(f)

        with open(snapshot2_path, 'r') as f:
            snapshot2 = json.load(f)

        snapshotter = MemoryMeshSnapshot(session, Path(KNOWLEDGE_BASE_PATH))
        comparison = snapshotter.compare_snapshots(snapshot1, snapshot2)

        return {
            "success": True,
            "comparison": comparison,
            "message": "Snapshots compared"
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Snapshot file not found: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Pattern Learning Endpoints ====================

class PatternResponse(BaseModel):
    """Response for a learning pattern."""
    pattern_id: str = Field(..., description="Pattern unique identifier")
    pattern_name: str = Field(..., description="Pattern name")
    pattern_type: str = Field(..., description="Type: behavioral, optimization, error_recovery, etc.")
    preconditions: Dict[str, Any] = Field(..., description="When pattern applies")
    actions: Dict[str, Any] = Field(..., description="What to do")
    expected_outcomes: Dict[str, Any] = Field(..., description="Expected results")
    trust_score: float = Field(..., description="Pattern trust score 0-1")
    usage_count: int = Field(0, description="How many times pattern was used")
    success_rate: float = Field(0, description="Success rate when applied")
    created_at: str = Field(..., description="Creation timestamp")


class PatternsListResponse(BaseModel):
    """Response for listing patterns."""
    patterns: List[PatternResponse]
    total: int
    high_trust_count: int
    pattern_types: Dict[str, int]


class PatternExtractRequest(BaseModel):
    """Request to extract patterns."""
    min_examples: int = Field(3, description="Minimum examples needed for pattern")
    example_type: Optional[str] = Field(None, description="Filter by example type")
    force: bool = Field(False, description="Force re-extraction even if patterns exist")


@router.get("/patterns", response_model=PatternsListResponse)
async def get_all_patterns(
    pattern_type: Optional[str] = None,
    min_trust: float = 0.0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """
    Get all extracted learning patterns.

    Patterns are higher-level abstractions learned from multiple examples.
    They represent reusable knowledge that Grace can apply to new situations.
    """
    try:
        from cognitive.learning_memory import LearningPattern

        query = session.query(LearningPattern)

        if pattern_type:
            query = query.filter(LearningPattern.pattern_type == pattern_type)

        if min_trust > 0:
            query = query.filter(LearningPattern.trust_score >= min_trust)

        patterns_db = query.limit(limit).all()

        patterns = []
        type_counts = {}

        for p in patterns_db:
            pattern_resp = PatternResponse(
                pattern_id=str(p.id),
                pattern_name=p.pattern_name,
                pattern_type=p.pattern_type,
                preconditions=p.preconditions or {},
                actions=p.actions or {},
                expected_outcomes=p.expected_outcomes or {},
                trust_score=p.trust_score or 0.5,
                usage_count=p.usage_count or 0,
                success_rate=p.success_rate or 0.0,
                created_at=p.created_at.isoformat() if p.created_at else datetime.now().isoformat()
            )
            patterns.append(pattern_resp)

            # Count types
            if p.pattern_type not in type_counts:
                type_counts[p.pattern_type] = 0
            type_counts[p.pattern_type] += 1

        high_trust = sum(1 for p in patterns if p.trust_score >= 0.7)

        return PatternsListResponse(
            patterns=patterns,
            total=len(patterns),
            high_trust_count=high_trust,
            pattern_types=type_counts
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get patterns: {str(e)}")


@router.get("/patterns/{pattern_id}", response_model=PatternResponse)
async def get_pattern_by_id(
    pattern_id: str,
    session: Session = Depends(get_session)
):
    """
    Get a specific pattern by ID.

    Returns detailed information about the pattern including
    its preconditions, actions, and usage statistics.
    """
    try:
        from cognitive.learning_memory import LearningPattern

        pattern = session.query(LearningPattern).filter(
            LearningPattern.id == pattern_id
        ).first()

        if not pattern:
            raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

        return PatternResponse(
            pattern_id=str(pattern.id),
            pattern_name=pattern.pattern_name,
            pattern_type=pattern.pattern_type,
            preconditions=pattern.preconditions or {},
            actions=pattern.actions or {},
            expected_outcomes=pattern.expected_outcomes or {},
            trust_score=pattern.trust_score or 0.5,
            usage_count=pattern.usage_count or 0,
            success_rate=pattern.success_rate or 0.0,
            created_at=pattern.created_at.isoformat() if pattern.created_at else datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pattern: {str(e)}")


@router.post("/patterns/extract")
async def extract_patterns(
    request: PatternExtractRequest,
    session: Session = Depends(get_session)
):
    """
    Force pattern extraction from learning examples.

    Analyzes existing learning examples and extracts patterns
    where multiple similar examples exist.

    This is useful for:
    - Initial pattern extraction after bulk data import
    - Re-analysis after trust score updates
    - Manual triggering of learning consolidation
    """
    try:
        from cognitive.learning_memory import LearningMemoryManager, LearningExample, LearningPattern

        # Get learning examples
        query = session.query(LearningExample)

        if request.example_type:
            query = query.filter(LearningExample.example_type == request.example_type)

        examples = query.all()

        if len(examples) < request.min_examples:
            return {
                "success": False,
                "message": f"Not enough examples ({len(examples)}) for pattern extraction (min: {request.min_examples})",
                "examples_found": len(examples)
            }

        # Group examples by type
        type_groups = {}
        for ex in examples:
            if ex.example_type not in type_groups:
                type_groups[ex.example_type] = []
            type_groups[ex.example_type].append(ex)

        patterns_created = 0
        patterns_updated = 0

        # Extract patterns from each group
        for example_type, group in type_groups.items():
            if len(group) < request.min_examples:
                continue

            # Check if pattern already exists
            existing = session.query(LearningPattern).filter(
                LearningPattern.pattern_type == example_type
            ).first()

            if existing and not request.force:
                # Update existing pattern
                avg_trust = sum(e.trust_score for e in group) / len(group)
                existing.trust_score = avg_trust
                existing.usage_count = len(group)
                patterns_updated += 1
            else:
                # Create new pattern
                pattern_name = f"pattern_{example_type}_{datetime.now().timestamp()}"

                # Extract common elements (simplified)
                preconditions = {"example_count": len(group), "types": [example_type]}
                actions = {"derived_from": example_type}
                outcomes = {"expected": "success"}

                avg_trust = sum(e.trust_score for e in group) / len(group)

                new_pattern = LearningPattern(
                    pattern_name=pattern_name,
                    pattern_type=example_type,
                    preconditions=preconditions,
                    actions=actions,
                    expected_outcomes=outcomes,
                    trust_score=avg_trust,
                    usage_count=len(group),
                    success_rate=0.0
                )
                session.add(new_pattern)
                patterns_created += 1

        session.commit()

        return {
            "success": True,
            "patterns_created": patterns_created,
            "patterns_updated": patterns_updated,
            "example_groups": len(type_groups),
            "total_examples_analyzed": len(examples),
            "message": f"Pattern extraction complete. Created {patterns_created}, updated {patterns_updated}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern extraction failed: {str(e)}")


@router.delete("/patterns/{pattern_id}")
async def delete_pattern(
    pattern_id: str,
    session: Session = Depends(get_session)
):
    """
    Delete a learning pattern.

    Use with caution - deleting patterns removes learned knowledge.
    """
    try:
        from cognitive.learning_memory import LearningPattern

        pattern = session.query(LearningPattern).filter(
            LearningPattern.id == pattern_id
        ).first()

        if not pattern:
            raise HTTPException(status_code=404, detail=f"Pattern not found: {pattern_id}")

        session.delete(pattern)
        session.commit()

        return {
            "success": True,
            "message": f"Pattern {pattern_id} deleted"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete pattern: {str(e)}")
