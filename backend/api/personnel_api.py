"""
GRACE Personnel Tracking API

REST API endpoints for personnel tracking:
- Session management (login/logout)
- Activity tracking
- Analytics and reporting
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/personnel", tags=["personnel"])


# Request/Response Models
class LoginRequest(BaseModel):
    genesis_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_fingerprint: Optional[str] = None
    location: Optional[dict] = None
    metadata: Optional[dict] = None


class LoginResponse(BaseModel):
    session_id: str
    genesis_id: str
    login_time: str
    message: str


class LogoutRequest(BaseModel):
    reason: str = "user_initiated"


class ActivityRequest(BaseModel):
    activity_type: str
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    endpoint: Optional[str] = None
    duration_ms: int = 0
    metadata: Optional[dict] = None


class ActivityResponse(BaseModel):
    activity_id: str
    session_id: str
    recorded_at: str


class SessionResponse(BaseModel):
    session_id: str
    genesis_id: str
    login_time: str
    last_activity: str
    activity_count: int


class ActivitySummaryResponse(BaseModel):
    genesis_id: str
    date: str
    total_activities: int
    total_input_size: int
    total_output_size: int
    activity_types: dict
    peak_hour: int
    current_session: Optional[dict]


class StorageStatsResponse(BaseModel):
    active_sessions: int
    users_with_events: int
    total_session_events: int
    realtime_records: int
    hourly_rollups: int
    daily_rollups: int
    estimated_memory_kb: float


# Endpoints
@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, http_request: Request):
    """Record a personnel login."""
    from genesis.personnel_tracker import get_personnel_tracker
    
    tracker = get_personnel_tracker()
    
    # Auto-detect IP and user agent if not provided
    ip_address = request.ip_address
    if not ip_address:
        forwarded = http_request.headers.get("X-Forwarded-For")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        elif http_request.client:
            ip_address = http_request.client.host
    
    user_agent = request.user_agent or http_request.headers.get("User-Agent")
    
    session_id = tracker.record_login(
        genesis_id=request.genesis_id,
        ip_address=ip_address,
        user_agent=user_agent,
        device_fingerprint=request.device_fingerprint,
        location=request.location,
        metadata=request.metadata,
    )
    
    return LoginResponse(
        session_id=session_id,
        genesis_id=request.genesis_id,
        login_time=datetime.utcnow().isoformat(),
        message=f"Welcome! Session {session_id} started.",
    )


@router.post("/logout/{session_id}")
async def logout(session_id: str, request: LogoutRequest):
    """Record a personnel logout."""
    from genesis.personnel_tracker import get_personnel_tracker
    
    tracker = get_personnel_tracker()
    
    success = tracker.record_logout(session_id, reason=request.reason)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "status": "logged_out",
        "session_id": session_id,
        "logout_time": datetime.utcnow().isoformat(),
    }


@router.post("/activity/{session_id}", response_model=ActivityResponse)
async def record_activity(session_id: str, request: ActivityRequest):
    """Record an activity for a session."""
    from genesis.personnel_tracker import get_personnel_tracker, ActivityType
    
    tracker = get_personnel_tracker()
    
    try:
        activity_type = ActivityType(request.activity_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid activity type: {request.activity_type}",
        )
    
    activity_id = tracker.record_activity(
        session_id=session_id,
        activity_type=activity_type,
        input_data=request.input_data,
        output_data=request.output_data,
        endpoint=request.endpoint,
        duration_ms=request.duration_ms,
        metadata=request.metadata,
    )
    
    if not activity_id:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return ActivityResponse(
        activity_id=activity_id,
        session_id=session_id,
        recorded_at=datetime.utcnow().isoformat(),
    )


@router.get("/session/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """Get session information."""
    from genesis.personnel_tracker import get_personnel_tracker
    
    tracker = get_personnel_tracker()
    session = tracker.get_session_info(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionResponse(
        session_id=session_id,
        genesis_id=session["genesis_id"],
        login_time=session["login_time"].isoformat(),
        last_activity=session["last_activity"].isoformat(),
        activity_count=session["activity_count"],
    )


@router.get("/sessions/active", response_model=List[SessionResponse])
async def list_active_sessions():
    """List all active sessions."""
    from genesis.personnel_tracker import get_personnel_tracker
    
    tracker = get_personnel_tracker()
    sessions = tracker.get_active_sessions()
    
    return [
        SessionResponse(
            session_id=s["session_id"],
            genesis_id=s["genesis_id"],
            login_time=s["login_time"],
            last_activity=s["last_activity"],
            activity_count=s["activity_count"],
        )
        for s in sessions
    ]


@router.get("/user/{genesis_id}/summary")
async def get_user_summary(
    genesis_id: str,
    date: Optional[str] = Query(None, description="Date (YYYY-MM-DD)"),
):
    """Get activity summary for a user."""
    from genesis.personnel_tracker import get_personnel_tracker
    
    tracker = get_personnel_tracker()
    
    target_date = None
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    
    summary = tracker.get_user_activity_summary(genesis_id, target_date)
    
    return summary


@router.get("/user/{genesis_id}/sessions")
async def get_user_sessions(genesis_id: str):
    """Get session history for a user."""
    from genesis.personnel_tracker import get_personnel_tracker
    
    tracker = get_personnel_tracker()
    events = tracker.get_user_sessions(genesis_id)
    
    return [e.to_dict() for e in events]


@router.get("/stats", response_model=StorageStatsResponse)
async def get_storage_stats():
    """Get storage statistics."""
    from genesis.personnel_tracker import get_personnel_tracker
    
    tracker = get_personnel_tracker()
    stats = tracker.get_storage_stats()
    
    vc = stats["version_control"]
    
    return StorageStatsResponse(
        active_sessions=stats["active_sessions"],
        users_with_events=stats["users_with_events"],
        total_session_events=stats["total_session_events"],
        realtime_records=vc["realtime_records"],
        hourly_rollups=vc["hourly_rollups"],
        daily_rollups=vc["daily_rollups"],
        estimated_memory_kb=vc["estimated_memory_kb"],
    )


@router.post("/cleanup")
async def cleanup_sessions(
    inactive_minutes: int = Query(30, description="Cleanup sessions inactive for this many minutes"),
):
    """Cleanup inactive sessions."""
    from genesis.personnel_tracker import get_personnel_tracker
    
    tracker = get_personnel_tracker()
    cleaned = tracker.cleanup_inactive_sessions(inactive_minutes)
    
    return {
        "status": "success",
        "sessions_cleaned": cleaned,
    }


@router.post("/archive")
async def archive_old_data(
    older_than_days: int = Query(30, description="Archive data older than this many days"),
):
    """Archive old tracking data."""
    from genesis.personnel_tracker import get_personnel_tracker
    
    tracker = get_personnel_tracker()
    result = tracker.archive_old_data(older_than_days)
    
    return {
        "status": "success",
        **result,
    }


@router.get("/activity-types")
async def list_activity_types():
    """List available activity types."""
    from genesis.personnel_tracker import ActivityType
    
    return {
        "activity_types": [t.value for t in ActivityType],
    }
