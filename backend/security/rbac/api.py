"""
RBAC Admin API Endpoints for GRACE.

Provides:
- CRUD operations for roles and permissions
- Role assignment endpoints
- Permission checking endpoints
- Audit trail queries
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_403_FORBIDDEN

from database.session import get_db as get_db_session
from sqlalchemy.orm import Session

from .models import Role, UserRole, Permission, AuthorizationContext
from .roles import get_role_manager, BuiltInRole
from .permissions import get_permission_manager
from .enforcer import (
    get_enforcer,
    create_permission_dependency,
    get_permission_checker
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rbac", tags=["rbac"])


class RoleCreate(BaseModel):
    """Request model for creating a role."""
    name: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = None
    description: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    parent_role_name: Optional[str] = None
    priority: int = Field(default=200, ge=0, le=999)
    metadata: Optional[Dict[str, Any]] = None


class RoleUpdate(BaseModel):
    """Request model for updating a role."""
    display_name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[List[str]] = None
    is_active: Optional[bool] = None


class RoleResponse(BaseModel):
    """Response model for a role."""
    role_id: str
    name: str
    display_name: Optional[str]
    description: Optional[str]
    permissions: List[str]
    parent_role_id: Optional[str]
    is_system: bool
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RoleAssignment(BaseModel):
    """Request model for assigning a role."""
    genesis_id: str
    role_name: str
    reason: Optional[str] = None
    expires_in_hours: Optional[int] = None
    expires_at: Optional[datetime] = None
    scope: Optional[Dict[str, Any]] = None


class RoleRevocation(BaseModel):
    """Request model for revoking a role."""
    genesis_id: str
    role_name: str
    reason: Optional[str] = None


class UserRoleResponse(BaseModel):
    """Response model for a user role assignment."""
    assignment_id: str
    genesis_id: str
    role_id: str
    role_name: str
    granted_by: Optional[str]
    granted_at: datetime
    expires_at: Optional[datetime]
    is_active: bool
    reason: Optional[str]

    class Config:
        from_attributes = True


class PermissionCreate(BaseModel):
    """Request model for creating a permission."""
    name: str = Field(..., min_length=1, max_length=255)
    resource: str
    action: str
    sub_resource: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None


class PermissionResponse(BaseModel):
    """Response model for a permission."""
    permission_id: str
    name: str
    description: Optional[str]
    resource: str
    sub_resource: Optional[str]
    action: str
    is_system: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PermissionCheckRequest(BaseModel):
    """Request model for checking permissions."""
    genesis_id: str
    permission: str
    resource_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class PermissionCheckResponse(BaseModel):
    """Response model for permission check result."""
    allowed: bool
    permission: str
    resource: str
    action: str
    genesis_id: str
    roles: List[str]
    reason: str
    conditions_met: bool
    checked_at: datetime


def get_db() -> Session:
    """Get database session."""
    return next(get_db_session())


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    include_inactive: bool = Query(False),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """List all roles."""
    genesis_id = request.cookies.get("genesis_id") or request.headers.get("X-Genesis-ID")
    if genesis_id:
        enforcer = get_enforcer(db)
        result = enforcer.check_permission(genesis_id, "roles:*:read")
        if not result.allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=result.reason)
    
    role_manager = get_role_manager(db)
    roles = role_manager.list_roles(include_inactive=include_inactive)
    
    return [
        RoleResponse(
            role_id=r.role_id,
            name=r.name,
            display_name=r.display_name,
            description=r.description,
            permissions=r.permissions or [],
            parent_role_id=r.parent_role_id,
            is_system=r.is_system,
            is_active=r.is_active,
            priority=r.priority,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        for r in roles
    ]


@router.get("/roles/{role_name}", response_model=RoleResponse)
async def get_role(
    role_name: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get a specific role."""
    genesis_id = request.cookies.get("genesis_id") or request.headers.get("X-Genesis-ID")
    if genesis_id:
        enforcer = get_enforcer(db)
        result = enforcer.check_permission(genesis_id, "roles:*:read")
        if not result.allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=result.reason)
    
    role_manager = get_role_manager(db)
    role = role_manager.get_role(role_name)
    
    if not role:
        raise HTTPException(
            status_code=HTTP_404_NOT_FOUND,
            detail=f"Role '{role_name}' not found"
        )
    
    return RoleResponse(
        role_id=role.role_id,
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        permissions=role.permissions or [],
        parent_role_id=role.parent_role_id,
        is_system=role.is_system,
        is_active=role.is_active,
        priority=role.priority,
        created_at=role.created_at,
        updated_at=role.updated_at
    )


@router.post("/roles", response_model=RoleResponse)
async def create_role(
    role_data: RoleCreate,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Create a new role."""
    genesis_id = request.cookies.get("genesis_id") or request.headers.get("X-Genesis-ID")
    if genesis_id:
        enforcer = get_enforcer(db)
        result = enforcer.check_permission(genesis_id, "roles:*:create")
        if not result.allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=result.reason)
    
    role_manager = get_role_manager(db)
    
    try:
        role = role_manager.create_role(
            name=role_data.name,
            permissions=role_data.permissions,
            display_name=role_data.display_name,
            description=role_data.description,
            parent_role_name=role_data.parent_role_name,
            priority=role_data.priority,
            created_by=genesis_id,
            metadata=role_data.metadata
        )
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    
    _log_admin_action(db, genesis_id, "role_created", {"role_name": role.name})
    
    return RoleResponse(
        role_id=role.role_id,
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        permissions=role.permissions or [],
        parent_role_id=role.parent_role_id,
        is_system=role.is_system,
        is_active=role.is_active,
        priority=role.priority,
        created_at=role.created_at,
        updated_at=role.updated_at
    )


@router.put("/roles/{role_name}", response_model=RoleResponse)
async def update_role(
    role_name: str,
    role_data: RoleUpdate,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Update an existing role."""
    genesis_id = request.cookies.get("genesis_id") or request.headers.get("X-Genesis-ID")
    if genesis_id:
        enforcer = get_enforcer(db)
        result = enforcer.check_permission(genesis_id, "roles:*:update")
        if not result.allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=result.reason)
    
    role_manager = get_role_manager(db)
    
    try:
        role = role_manager.update_role(
            role_name=role_name,
            permissions=role_data.permissions,
            display_name=role_data.display_name,
            description=role_data.description,
            is_active=role_data.is_active
        )
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    
    _log_admin_action(db, genesis_id, "role_updated", {"role_name": role_name})
    
    return RoleResponse(
        role_id=role.role_id,
        name=role.name,
        display_name=role.display_name,
        description=role.description,
        permissions=role.permissions or [],
        parent_role_id=role.parent_role_id,
        is_system=role.is_system,
        is_active=role.is_active,
        priority=role.priority,
        created_at=role.created_at,
        updated_at=role.updated_at
    )


@router.delete("/roles/{role_name}")
async def delete_role(
    role_name: str,
    force: bool = Query(False),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Delete a role."""
    genesis_id = request.cookies.get("genesis_id") or request.headers.get("X-Genesis-ID")
    if genesis_id:
        enforcer = get_enforcer(db)
        result = enforcer.check_permission(genesis_id, "roles:*:delete")
        if not result.allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=result.reason)
    
    role_manager = get_role_manager(db)
    
    try:
        role_manager.delete_role(role_name, force=force)
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    
    _log_admin_action(db, genesis_id, "role_deleted", {"role_name": role_name, "force": force})
    
    return {"status": "deleted", "role_name": role_name}


@router.post("/roles/assign", response_model=UserRoleResponse)
async def assign_role(
    assignment: RoleAssignment,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Assign a role to a user."""
    genesis_id = request.cookies.get("genesis_id") or request.headers.get("X-Genesis-ID")
    if genesis_id:
        enforcer = get_enforcer(db)
        result = enforcer.check_permission(genesis_id, "roles:*:update")
        if not result.allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=result.reason)
    
    role_manager = get_role_manager(db)
    
    try:
        user_role = role_manager.assign_role(
            genesis_id=assignment.genesis_id,
            role_name=assignment.role_name,
            granted_by=genesis_id,
            expires_at=assignment.expires_at,
            expires_in_hours=assignment.expires_in_hours,
            reason=assignment.reason,
            scope=assignment.scope
        )
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    
    role = role_manager.get_role(assignment.role_name)
    
    _log_admin_action(db, genesis_id, "role_assigned", {
        "target_user": assignment.genesis_id,
        "role_name": assignment.role_name,
        "expires_at": str(user_role.expires_at) if user_role.expires_at else None
    })
    
    return UserRoleResponse(
        assignment_id=user_role.assignment_id,
        genesis_id=user_role.genesis_id,
        role_id=user_role.role_id,
        role_name=role.name if role else assignment.role_name,
        granted_by=user_role.granted_by,
        granted_at=user_role.granted_at,
        expires_at=user_role.expires_at,
        is_active=user_role.is_active,
        reason=user_role.reason
    )


@router.post("/roles/revoke")
async def revoke_role(
    revocation: RoleRevocation,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Revoke a role from a user."""
    genesis_id = request.cookies.get("genesis_id") or request.headers.get("X-Genesis-ID")
    if genesis_id:
        enforcer = get_enforcer(db)
        result = enforcer.check_permission(genesis_id, "roles:*:update")
        if not result.allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=result.reason)
    
    role_manager = get_role_manager(db)
    
    try:
        role_manager.revoke_role(
            genesis_id=revocation.genesis_id,
            role_name=revocation.role_name,
            revoked_by=genesis_id,
            reason=revocation.reason
        )
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    
    _log_admin_action(db, genesis_id, "role_revoked", {
        "target_user": revocation.genesis_id,
        "role_name": revocation.role_name,
        "reason": revocation.reason
    })
    
    return {
        "status": "revoked",
        "genesis_id": revocation.genesis_id,
        "role_name": revocation.role_name
    }


@router.get("/users/{user_genesis_id}/roles", response_model=List[RoleResponse])
async def get_user_roles(
    user_genesis_id: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get all roles for a user."""
    genesis_id = request.cookies.get("genesis_id") or request.headers.get("X-Genesis-ID")
    if genesis_id and genesis_id != user_genesis_id:
        enforcer = get_enforcer(db)
        result = enforcer.check_permission(genesis_id, "users:*:read")
        if not result.allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=result.reason)
    
    role_manager = get_role_manager(db)
    roles = role_manager.get_user_roles(user_genesis_id)
    
    return [
        RoleResponse(
            role_id=r.role_id,
            name=r.name,
            display_name=r.display_name,
            description=r.description,
            permissions=r.permissions or [],
            parent_role_id=r.parent_role_id,
            is_system=r.is_system,
            is_active=r.is_active,
            priority=r.priority,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        for r in roles
    ]


@router.get("/users/{user_genesis_id}/permissions", response_model=List[str])
async def get_user_permissions(
    user_genesis_id: str,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get all effective permissions for a user."""
    genesis_id = request.cookies.get("genesis_id") or request.headers.get("X-Genesis-ID")
    if genesis_id and genesis_id != user_genesis_id:
        enforcer = get_enforcer(db)
        result = enforcer.check_permission(genesis_id, "users:*:read")
        if not result.allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=result.reason)
    
    role_manager = get_role_manager(db)
    permissions = role_manager.get_user_permissions(user_genesis_id)
    
    return sorted(list(permissions))


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    resource: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """List all permissions."""
    genesis_id = request.cookies.get("genesis_id") or request.headers.get("X-Genesis-ID")
    if genesis_id:
        enforcer = get_enforcer(db)
        result = enforcer.check_permission(genesis_id, "permissions:*:read")
        if not result.allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=result.reason)
    
    perm_manager = get_permission_manager(db)
    permissions = perm_manager.list_permissions(resource=resource, action=action)
    
    return [
        PermissionResponse(
            permission_id=p.permission_id,
            name=p.name,
            description=p.description,
            resource=p.resource,
            sub_resource=p.sub_resource,
            action=p.action,
            is_system=p.is_system,
            is_active=p.is_active,
            created_at=p.created_at
        )
        for p in permissions
    ]


@router.post("/permissions", response_model=PermissionResponse)
async def create_permission(
    perm_data: PermissionCreate,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Create a new permission."""
    genesis_id = request.cookies.get("genesis_id") or request.headers.get("X-Genesis-ID")
    if genesis_id:
        enforcer = get_enforcer(db)
        result = enforcer.check_permission(genesis_id, "permissions:*:create")
        if not result.allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=result.reason)
    
    from .models import PolicyDocument
    
    perm_manager = get_permission_manager(db)
    
    conditions = None
    if perm_data.conditions:
        conditions = PolicyDocument.from_dict(perm_data.conditions)
    
    try:
        perm = perm_manager.create_permission(
            name=perm_data.name,
            resource=perm_data.resource,
            action=perm_data.action,
            sub_resource=perm_data.sub_resource,
            description=perm_data.description,
            conditions=conditions
        )
    except ValueError as e:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail=str(e))
    
    _log_admin_action(db, genesis_id, "permission_created", {"permission_name": perm.name})
    
    return PermissionResponse(
        permission_id=perm.permission_id,
        name=perm.name,
        description=perm.description,
        resource=perm.resource,
        sub_resource=perm.sub_resource,
        action=perm.action,
        is_system=perm.is_system,
        is_active=perm.is_active,
        created_at=perm.created_at
    )


@router.post("/check", response_model=PermissionCheckResponse)
async def check_permission(
    check_request: PermissionCheckRequest,
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Check if a user has a specific permission."""
    genesis_id = request.cookies.get("genesis_id") or request.headers.get("X-Genesis-ID")
    
    if genesis_id and genesis_id != check_request.genesis_id:
        enforcer = get_enforcer(db)
        result = enforcer.check_permission(genesis_id, "permissions:*:read")
        if not result.allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=result.reason)
    
    enforcer = get_enforcer(db)
    
    context = None
    if check_request.context:
        context = AuthorizationContext(
            genesis_id=check_request.genesis_id,
            resource_id=check_request.resource_id,
            custom_attributes=check_request.context
        )
    
    result = enforcer.check_permission(
        genesis_id=check_request.genesis_id,
        permission=check_request.permission,
        context=context,
        resource_id=check_request.resource_id
    )
    
    return PermissionCheckResponse(
        allowed=result.allowed,
        permission=result.permission,
        resource=result.resource,
        action=result.action,
        genesis_id=result.genesis_id,
        roles=result.roles,
        reason=result.reason,
        conditions_met=result.conditions_met,
        checked_at=result.checked_at
    )


@router.post("/initialize")
async def initialize_rbac(
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Initialize built-in roles and permissions."""
    genesis_id = request.cookies.get("genesis_id") or request.headers.get("X-Genesis-ID")
    if genesis_id:
        enforcer = get_enforcer(db)
        result = enforcer.check_permission(genesis_id, "system:*:admin")
        if not result.allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=result.reason)
    
    role_manager = get_role_manager(db)
    perm_manager = get_permission_manager(db)
    
    permissions = perm_manager.initialize_permissions()
    roles = role_manager.initialize_built_in_roles()
    
    _log_admin_action(db, genesis_id, "rbac_initialized", {
        "roles_count": len(roles),
        "permissions_count": len(permissions)
    })
    
    return {
        "status": "initialized",
        "roles_created": len(roles),
        "permissions_created": len(permissions),
        "roles": [r.name for r in roles],
    }


@router.get("/audit")
async def get_rbac_audit(
    genesis_id: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Get RBAC-related audit records."""
    requesting_user = request.cookies.get("genesis_id") or request.headers.get("X-Genesis-ID")
    if requesting_user:
        enforcer = get_enforcer(db)
        result = enforcer.check_permission(requesting_user, "audit:*:read")
        if not result.allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=result.reason)
    
    try:
        from genesis.immutable_audit_storage import (
            get_immutable_audit_storage,
            ImmutableAuditType
        )
        
        audit_storage = get_immutable_audit_storage(db)
        
        records = audit_storage.get_audit_trail(
            audit_types=[
                ImmutableAuditType.PERMISSION_CHANGE,
                ImmutableAuditType.ACCESS_DENIED
            ],
            actor_id=genesis_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        return {
            "count": len(records),
            "records": [
                {
                    "record_id": r.record_id,
                    "audit_type": r.audit_type,
                    "actor_id": r.actor_id,
                    "action_description": r.action_description,
                    "severity": r.severity,
                    "event_timestamp": r.event_timestamp.isoformat() if r.event_timestamp else None,
                    "action_data": r.action_data
                }
                for r in records
            ]
        }
        
    except ImportError:
        return {"error": "Audit storage not available", "records": []}


@router.post("/cleanup")
async def cleanup_expired(
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Cleanup expired role assignments."""
    genesis_id = request.cookies.get("genesis_id") or request.headers.get("X-Genesis-ID")
    if genesis_id:
        enforcer = get_enforcer(db)
        result = enforcer.check_permission(genesis_id, "system:*:admin")
        if not result.allowed:
            raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail=result.reason)
    
    role_manager = get_role_manager(db)
    count = role_manager.cleanup_expired_assignments()
    
    _log_admin_action(db, genesis_id, "rbac_cleanup", {"expired_count": count})
    
    return {"status": "cleaned", "expired_assignments_removed": count}


def _log_admin_action(
    db: Session,
    actor_id: Optional[str],
    action: str,
    details: Dict[str, Any]
) -> None:
    """Log an administrative action to the audit system."""
    try:
        from genesis.immutable_audit_storage import (
            get_immutable_audit_storage,
            ImmutableAuditType
        )
        
        audit_storage = get_immutable_audit_storage(db)
        audit_storage.record(
            audit_type=ImmutableAuditType.PERMISSION_CHANGE,
            action_description=f"RBAC Admin: {action}",
            actor_type="user",
            actor_id=actor_id,
            severity="info",
            component="rbac.api",
            action_data=details
        )
    except Exception as e:
        logger.error(f"[RBAC-API] Failed to log admin action: {e}")
