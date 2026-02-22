"""
Genesis Key API endpoints.

Provides comprehensive tracking and version control capabilities.

Classes:
- `CreateGenesisKeyRequest`
- `GenesisKeyResponse`
- `FixSuggestionResponse`
- `AnalyzeCodeRequest`
- `CodeIssueResponse`
- `CreateUserRequest`
- `UserProfileResponse`
- `ArchiveResponse`
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session

from database.session import get_session
from models.genesis_key_models import (
    GenesisKey, FixSuggestion, GenesisKeyArchive, UserProfile,
    GenesisKeyType, GenesisKeyStatus, FixSuggestionStatus
)
from genesis.genesis_key_service import get_genesis_service
from genesis.code_analyzer import get_code_analyzer
from genesis.archival_service import get_archival_service

router = APIRouter(prefix="/genesis", tags=["Genesis Keys"])


# ==================== Pydantic Models ====================

class CreateGenesisKeyRequest(BaseModel):
    """Request to create a new Genesis Key."""
    key_type: str = Field(..., description="Type of Genesis Key")
    what_description: str = Field(..., description="What happened")
    who_actor: str = Field(..., description="Who performed the action")
    where_location: Optional[str] = Field(None, description="Where it happened")
    why_reason: Optional[str] = Field(None, description="Why it happened")
    how_method: Optional[str] = Field(None, description="How it was done")
    user_id: Optional[str] = Field(None, description="User ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    file_path: Optional[str] = Field(None, description="File path")
    line_number: Optional[int] = Field(None, description="Line number")
    function_name: Optional[str] = Field(None, description="Function name")
    code_before: Optional[str] = Field(None, description="Code before change")
    code_after: Optional[str] = Field(None, description="Code after change")
    input_data: Optional[Dict] = Field(None, description="Input data")
    output_data: Optional[Dict] = Field(None, description="Output data")
    context_data: Optional[Dict] = Field(None, description="Context data")
    tags: Optional[List[str]] = Field(None, description="Tags")


class GenesisKeyResponse(BaseModel):
    """Response model for Genesis Key."""
    key_id: str
    key_type: str
    status: str
    what_description: str
    who_actor: str
    when_timestamp: datetime
    where_location: Optional[str]
    why_reason: Optional[str]
    how_method: Optional[str]
    file_path: Optional[str]
    line_number: Optional[int]
    is_error: bool
    has_fix_suggestion: bool
    fix_applied: bool
    metadata_human: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class FixSuggestionResponse(BaseModel):
    """Response model for Fix Suggestion."""
    suggestion_id: str
    genesis_key_id: str
    suggestion_type: str
    title: str
    description: str
    severity: str
    fix_code: Optional[str]
    status: str
    confidence: Optional[float]

    model_config = ConfigDict(from_attributes=True)


class AnalyzeCodeRequest(BaseModel):
    """Request to analyze code."""
    code: str = Field(..., description="Code to analyze")
    language: str = Field(default="python", description="Programming language")
    file_path: Optional[str] = Field(None, description="File path for context")


class CodeIssueResponse(BaseModel):
    """Response model for code issue."""
    issue_type: str
    severity: str
    line_number: int
    column: Optional[int]
    message: str
    suggested_fix: Optional[str]
    fix_confidence: float
    context: Optional[str]


class CreateUserRequest(BaseModel):
    """Request to create/get user profile."""
    username: Optional[str] = None
    email: Optional[str] = None


class UserProfileResponse(BaseModel):
    """Response model for user profile."""
    user_id: str
    username: Optional[str]
    email: Optional[str]
    first_seen: datetime
    last_seen: datetime
    total_actions: int
    total_changes: int
    total_errors: int
    total_fixes: int

    model_config = ConfigDict(from_attributes=True)


class ArchiveResponse(BaseModel):
    """Response model for archive."""
    archive_id: str
    archive_date: datetime
    key_count: int
    error_count: int
    fix_count: int
    user_count: int
    most_active_user: Optional[str]
    most_changed_file: Optional[str]
    most_common_error: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ==================== Endpoints ====================

@router.post("/keys", response_model=GenesisKeyResponse)
async def create_genesis_key(
    request: CreateGenesisKeyRequest,
    session: Session = Depends(get_session)
):
    """Create a new Genesis Key for tracking."""
    try:
        genesis_service = get_genesis_service(session)

        # Convert string key_type to enum
        try:
            key_type = GenesisKeyType(request.key_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid key_type: {request.key_type}")

        key = genesis_service.create_key(
            key_type=key_type,
            what_description=request.what_description,
            who_actor=request.who_actor,
            where_location=request.where_location,
            why_reason=request.why_reason,
            how_method=request.how_method,
            user_id=request.user_id,
            session_id=request.session_id,
            file_path=request.file_path,
            line_number=request.line_number,
            function_name=request.function_name,
            code_before=request.code_before,
            code_after=request.code_after,
            input_data=request.input_data,
            output_data=request.output_data,
            context_data=request.context_data,
            tags=request.tags,
            session=session
        )

        return key
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keys", response_model=List[GenesisKeyResponse])
async def get_genesis_keys(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    key_type: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    is_error: Optional[bool] = None,
    has_fix: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    """Get Genesis Keys with filtering."""
    try:
        query = session.query(GenesisKey)

        if key_type:
            query = query.filter(GenesisKey.key_type == key_type)
        if status:
            query = query.filter(GenesisKey.status == status)
        if user_id:
            query = query.filter(GenesisKey.user_id == user_id)
        if is_error is not None:
            query = query.filter(GenesisKey.is_error == is_error)
        if has_fix is not None:
            query = query.filter(GenesisKey.has_fix_suggestion == has_fix)

        keys = query.order_by(GenesisKey.when_timestamp.desc()).offset(offset).limit(limit).all()
        return keys
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keys/{key_id}", response_model=GenesisKeyResponse)
async def get_genesis_key(
    key_id: str,
    session: Session = Depends(get_session)
):
    """Get a specific Genesis Key by ID."""
    key = session.query(GenesisKey).filter(GenesisKey.key_id == key_id).first()

    if not key:
        raise HTTPException(status_code=404, detail="Genesis Key not found")

    return key


@router.get("/keys/{key_id}/metadata")
async def get_key_metadata(
    key_id: str,
    format: str = Query("human", pattern="^(human|ai|both)$"),
    session: Session = Depends(get_session)
):
    """Get metadata for a Genesis Key (human and/or AI readable)."""
    key = session.query(GenesisKey).filter(GenesisKey.key_id == key_id).first()

    if not key:
        raise HTTPException(status_code=404, detail="Genesis Key not found")

    if format == "human":
        return {"metadata": key.metadata_human}
    elif format == "ai":
        return {"metadata": key.metadata_ai}
    else:  # both
        return {
            "human_readable": key.metadata_human,
            "ai_readable": key.metadata_ai
        }


@router.post("/keys/{key_id}/rollback")
async def rollback_to_key(
    key_id: str,
    rolled_back_by: str = Body(..., embed=True),
    session: Session = Depends(get_session)
):
    """Rollback to a specific Genesis Key state."""
    try:
        genesis_service = get_genesis_service(session)
        rollback_key = genesis_service.rollback_to_key(
            key_id=key_id,
            rolled_back_by=rolled_back_by,
            session=session
        )
        return {"success": True, "rollback_key_id": rollback_key.key_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-code", response_model=List[CodeIssueResponse])
async def analyze_code(request: AnalyzeCodeRequest):
    """Analyze code for errors and get fix suggestions."""
    try:
        analyzer = get_code_analyzer()

        if request.language == "python":
            issues = analyzer.analyze_python_code(request.code, request.file_path)
        elif request.language == "javascript":
            issues = analyzer.analyze_javascript_code(request.code, request.file_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported language: {request.language}")

        return [
            CodeIssueResponse(
                issue_type=issue.issue_type,
                severity=issue.severity,
                line_number=issue.line_number,
                column=issue.column,
                message=issue.message,
                suggested_fix=issue.suggested_fix,
                fix_confidence=issue.fix_confidence,
                context=issue.context
            )
            for issue in issues
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/keys/{key_id}/fixes", response_model=List[FixSuggestionResponse])
async def get_fix_suggestions(
    key_id: str,
    session: Session = Depends(get_session)
):
    """Get fix suggestions for a Genesis Key."""
    key = session.query(GenesisKey).filter(GenesisKey.key_id == key_id).first()

    if not key:
        raise HTTPException(status_code=404, detail="Genesis Key not found")

    return key.fix_suggestions


@router.post("/fixes/{suggestion_id}/apply")
async def apply_fix_suggestion(
    suggestion_id: str,
    applied_by: str = Body(..., embed=True),
    session: Session = Depends(get_session)
):
    """Apply a fix suggestion (one-click fix)."""
    try:
        genesis_service = get_genesis_service(session)
        fix_key = genesis_service.apply_fix(
            suggestion_id=suggestion_id,
            applied_by=applied_by,
            session=session
        )
        return {"success": True, "fix_key_id": fix_key.key_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/users", response_model=UserProfileResponse)
async def create_user_profile(
    request: CreateUserRequest,
    session: Session = Depends(get_session)
):
    """Create or get a user profile with Genesis-generated ID."""
    try:
        genesis_service = get_genesis_service(session)
        user = genesis_service.get_or_create_user(
            username=request.username,
            email=request.email,
            session=session
        )
        return user
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(
    user_id: str,
    session: Session = Depends(get_session)
):
    """Get user profile by ID."""
    user = session.query(UserProfile).filter(UserProfile.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User profile not found")

    return user


@router.get("/users/{user_id}/keys", response_model=List[GenesisKeyResponse])
async def get_user_keys(
    user_id: str,
    limit: int = Query(50, ge=1, le=500),
    session: Session = Depends(get_session)
):
    """Get all Genesis Keys for a specific user."""
    keys = session.query(GenesisKey).filter(
        GenesisKey.user_id == user_id
    ).order_by(GenesisKey.when_timestamp.desc()).limit(limit).all()

    return keys


@router.post("/archive/trigger")
async def trigger_archival(
    date: Optional[datetime] = None,
    session: Session = Depends(get_session)
):
    """Manually trigger archival for a specific date."""
    try:
        archival_service = get_archival_service(session)
        archive = archival_service.archive_daily_keys(target_date=date, session=session)

        if not archive:
            return {"message": "No keys to archive for this date"}

        return {
            "success": True,
            "archive_id": archive.archive_id,
            "key_count": archive.key_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/archives", response_model=List[ArchiveResponse])
async def get_archives(
    limit: int = Query(30, ge=1, le=100),
    session: Session = Depends(get_session)
):
    """Get list of archives."""
    try:
        archival_service = get_archival_service(session)
        archives = archival_service.list_archives(limit=limit, session=session)
        return archives
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/archives/{archive_id}", response_model=ArchiveResponse)
async def get_archive(
    archive_id: str,
    session: Session = Depends(get_session)
):
    """Get a specific archive by ID."""
    archive = session.query(GenesisKeyArchive).filter(
        GenesisKeyArchive.archive_id == archive_id
    ).first()

    if not archive:
        raise HTTPException(status_code=404, detail="Archive not found")

    return archive


@router.get("/archives/{archive_id}/report")
async def get_archive_report(
    archive_id: str,
    format: str = Query("text", pattern="^(text|json)$"),
    session: Session = Depends(get_session)
):
    """Get archive report in text or JSON format."""
    archive = session.query(GenesisKeyArchive).filter(
        GenesisKeyArchive.archive_id == archive_id
    ).first()

    if not archive:
        raise HTTPException(status_code=404, detail="Archive not found")

    if format == "text":
        return {"report": archive.report_summary}
    else:  # json
        return {"report": archive.report_data}


@router.get("/stats")
async def get_genesis_stats(session: Session = Depends(get_session)):
    """Get overall Genesis Key statistics."""
    try:
        total_keys = session.query(GenesisKey).count()
        total_errors = session.query(GenesisKey).filter(GenesisKey.is_error == True).count()
        total_fixes = session.query(GenesisKey).filter(GenesisKey.key_type == GenesisKeyType.FIX).count()
        total_users = session.query(UserProfile).count()
        total_archives = session.query(GenesisKeyArchive).count()

        # Recent activity (last 24 hours)
        from datetime import timedelta
        yesterday = datetime.now() - timedelta(days=1)
        recent_keys = session.query(GenesisKey).filter(
            GenesisKey.when_timestamp >= yesterday
        ).count()

        return {
            "total_keys": total_keys,
            "total_errors": total_errors,
            "total_fixes": total_fixes,
            "total_users": total_users,
            "total_archives": total_archives,
            "keys_last_24h": recent_keys
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
