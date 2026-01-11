"""
Authentication API with Genesis Key integration.

Provides login/session management using Genesis IDs.
"""
from fastapi import APIRouter, HTTPException, Depends, Response, Cookie
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from database.session import get_session
from genesis.genesis_key_service import get_genesis_service
from genesis.kb_integration import get_kb_integration
from models.genesis_key_models import GenesisKeyType

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ==================== Pydantic Models ====================

class LoginRequest(BaseModel):
    """Request to login or get Genesis ID."""
    username: Optional[str] = Field(None, description="Optional username")
    email: Optional[str] = Field(None, description="Optional email")
    existing_genesis_id: Optional[str] = Field(None, description="Existing Genesis ID to resume")


class LoginResponse(BaseModel):
    """Response with Genesis ID and session info."""
    genesis_id: str = Field(..., description="Genesis user ID")
    session_id: str = Field(..., description="Session ID")
    username: str = Field(..., description="Username")
    is_new_user: bool = Field(..., description="Whether this is a new user")
    message: str = Field(..., description="Welcome message")


class SessionInfoResponse(BaseModel):
    """Current session information."""
    genesis_id: str
    session_id: str
    username: str
    total_actions: int
    total_errors: int
    total_fixes: int
    first_seen: datetime
    last_seen: datetime


# ==================== Endpoints ====================

@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    response: Response,
    session: Session = Depends(get_session)
):
    """
    Login or create a Genesis ID.

    This is the entry point for all users. On first access:
    - Creates a Genesis ID (GU-prefix)
    - Creates user profile
    - Starts tracking session
    - Saves to knowledge base

    Returns Genesis ID to be used for all subsequent requests.
    """
    genesis_service = get_genesis_service(session)
    kb_integration = get_kb_integration()

    is_new_user = False
    user = None

    # Check if resuming with existing Genesis ID
    if request.existing_genesis_id:
        try:
            user = genesis_service.get_or_create_user(
                user_id=request.existing_genesis_id,
                session=session
            )
        except:
            pass

    # Create new user if needed
    if not user:
        is_new_user = True
        identifier = request.email or request.username
        user = genesis_service.get_or_create_user(
            username=request.username or f"User_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            email=request.email,
            session=session
        )

    # Generate session ID
    import uuid
    session_id = f"SS-{uuid.uuid4().hex[:16]}"

    # Create login Genesis Key
    genesis_service.create_key(
        key_type=GenesisKeyType.USER_INPUT,
        what_description="User login" if not is_new_user else "New user registration",
        who_actor=user.username,
        where_location="/auth/login",
        why_reason="User authentication",
        how_method="Genesis ID login system",
        user_id=user.user_id,
        session_id=session_id,
        input_data={
            "username": user.username,
            "email": user.email,
            "is_new_user": is_new_user
        },
        tags=["login", "authentication", "session_start"],
        session=session
    )

    # Save user profile to knowledge base
    kb_integration.save_user_profile(
        user_id=user.user_id,
        profile_data={
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "total_actions": user.total_actions,
            "total_errors": user.total_errors,
            "total_fixes": user.total_fixes,
            "first_seen": user.first_seen.isoformat(),
            "last_seen": user.last_seen.isoformat(),
            "current_session_id": session_id
        }
    )

    # Set cookies for Genesis ID and Session ID
    response.set_cookie(
        key="genesis_id",
        value=user.user_id,
        max_age=365 * 24 * 60 * 60,  # 1 year
        httponly=True,
        samesite="lax"
    )

    response.set_cookie(
        key="session_id",
        value=session_id,
        max_age=24 * 60 * 60,  # 24 hours
        httponly=True,
        samesite="lax"
    )

    message = (
        f"Welcome {user.username}! You've been assigned Genesis ID: {user.user_id}"
        if is_new_user
        else f"Welcome back {user.username}!"
    )

    return LoginResponse(
        genesis_id=user.user_id,
        session_id=session_id,
        username=user.username,
        is_new_user=is_new_user,
        message=message
    )


@router.post("/logout")
async def logout(
    response: Response,
    genesis_id: Optional[str] = Cookie(None),
    session_id: Optional[str] = Cookie(None),
    session: Session = Depends(get_session)
):
    """Logout and create logout Genesis Key."""
    if genesis_id:
        genesis_service = get_genesis_service(session)

        # Create logout Genesis Key
        try:
            genesis_service.create_key(
                key_type=GenesisKeyType.USER_INPUT,
                what_description="User logout",
                who_actor=genesis_id,
                where_location="/auth/logout",
                why_reason="User session end",
                how_method="Logout endpoint",
                user_id=genesis_id,
                session_id=session_id,
                tags=["logout", "session_end"],
                session=session
            )
        except Exception as e:
            print(f"Failed to create logout key: {e}")

    # Clear cookies
    response.delete_cookie(key="genesis_id")
    response.delete_cookie(key="session_id")

    return {"message": "Logged out successfully"}


@router.get("/session", response_model=SessionInfoResponse)
async def get_session_info(
    genesis_id: Optional[str] = Cookie(None),
    session_id: Optional[str] = Cookie(None),
    session: Session = Depends(get_session)
):
    """Get current session information."""
    if not genesis_id:
        raise HTTPException(status_code=401, detail="No Genesis ID found. Please login.")

    genesis_service = get_genesis_service(session)

    try:
        user = genesis_service.get_or_create_user(user_id=genesis_id, session=session)

        return SessionInfoResponse(
            genesis_id=user.user_id,
            session_id=session_id or "No active session",
            username=user.username,
            total_actions=user.total_actions,
            total_errors=user.total_errors,
            total_fixes=user.total_fixes,
            first_seen=user.first_seen,
            last_seen=user.last_seen
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"User not found: {str(e)}")


@router.get("/whoami")
async def whoami(
    genesis_id: Optional[str] = Cookie(None),
    session: Session = Depends(get_session)
):
    """Quick endpoint to get current Genesis ID."""
    if not genesis_id:
        return {
            "genesis_id": None,
            "message": "No Genesis ID found. Call /auth/login to get one."
        }

    genesis_service = get_genesis_service(session)

    try:
        user = genesis_service.get_or_create_user(user_id=genesis_id, session=session)
        return {
            "genesis_id": user.user_id,
            "username": user.username,
            "total_actions": user.total_actions,
            "message": f"You are {user.username}"
        }
    except:
        return {
            "genesis_id": genesis_id,
            "message": "Genesis ID found but user profile not loaded"
        }
