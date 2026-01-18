"""
Policy Enforcement for GRACE RBAC System.

Provides:
- FastAPI dependency for endpoint protection
- Decorator for function-level authorization
- Context-aware permission checking
- Deny-by-default policy
- Comprehensive audit logging of all authorization decisions
"""

import functools
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable, Union
from fastapi import Request, HTTPException, Depends
from starlette.status import HTTP_403_FORBIDDEN, HTTP_401_UNAUTHORIZED
from sqlalchemy.orm import Session

from .models import (
    Permission, AuthorizationContext, PermissionCheck,
    PolicyDocument, ResourceType, ActionType
)
from .roles import RoleManager, get_role_manager
from .permissions import PermissionManager, get_permission_manager

logger = logging.getLogger(__name__)


class RBACEnforcer:
    """
    Central policy enforcement for RBAC.
    
    Implements deny-by-default policy with comprehensive audit logging.
    All authorization decisions (allowed and denied) are logged.
    """
    
    def __init__(self, session: Session):
        self.session = session
        self.role_manager = get_role_manager(session)
        self.permission_manager = get_permission_manager(session)
        self._audit_storage = None
        self._enabled = True
        
    def _get_audit_storage(self):
        """Lazy load audit storage to avoid circular imports."""
        if self._audit_storage is None:
            try:
                from genesis.immutable_audit_storage import (
                    get_immutable_audit_storage,
                    ImmutableAuditType
                )
                self._audit_storage = get_immutable_audit_storage(self.session)
                self._ImmutableAuditType = ImmutableAuditType
            except ImportError:
                logger.warning("[RBAC] Could not import immutable audit storage")
                self._audit_storage = None
        return self._audit_storage
    
    def check_permission(
        self,
        genesis_id: str,
        permission: str,
        context: Optional[AuthorizationContext] = None,
        resource_id: Optional[str] = None
    ) -> PermissionCheck:
        """
        Check if a Genesis ID has permission for an action.
        
        This is the core authorization check. It:
        1. Gets all roles for the user
        2. Checks if any role grants the permission
        3. Evaluates attribute-based conditions if present
        4. Logs the decision to immutable audit
        5. Returns detailed result
        """
        if not self._enabled:
            return PermissionCheck(
                allowed=True,
                permission=permission,
                resource=permission.split(":")[0],
                action=permission.split(":")[-1],
                genesis_id=genesis_id,
                roles=["rbac_disabled"],
                reason="RBAC enforcement disabled"
            )
        
        roles = self.role_manager.get_user_roles(genesis_id)
        role_names = [r.name for r in roles]
        
        if not roles:
            result = PermissionCheck(
                allowed=False,
                permission=permission,
                resource=permission.split(":")[0],
                action=permission.split(":")[-1],
                genesis_id=genesis_id,
                roles=[],
                reason="No roles assigned"
            )
            self._log_authorization_decision(result, context)
            return result
        
        has_perm = self.role_manager.has_permission(genesis_id, permission)
        
        if not has_perm:
            result = PermissionCheck(
                allowed=False,
                permission=permission,
                resource=permission.split(":")[0],
                action=permission.split(":")[-1],
                genesis_id=genesis_id,
                roles=role_names,
                reason=f"Permission '{permission}' not granted by any role"
            )
            self._log_authorization_decision(result, context)
            return result
        
        conditions_met = True
        if context:
            eval_context = context.to_evaluation_context()
            conditions_met = self.permission_manager.evaluate_conditions(
                permission, eval_context
            )
        
        if not conditions_met:
            result = PermissionCheck(
                allowed=False,
                permission=permission,
                resource=permission.split(":")[0],
                action=permission.split(":")[-1],
                genesis_id=genesis_id,
                roles=role_names,
                reason="Attribute-based conditions not met",
                conditions_met=False
            )
            self._log_authorization_decision(result, context)
            return result
        
        result = PermissionCheck(
            allowed=True,
            permission=permission,
            resource=permission.split(":")[0],
            action=permission.split(":")[-1],
            genesis_id=genesis_id,
            roles=role_names,
            reason="Permission granted",
            conditions_met=True
        )
        self._log_authorization_decision(result, context)
        return result
    
    def require_permission(
        self,
        genesis_id: str,
        permission: str,
        context: Optional[AuthorizationContext] = None
    ) -> None:
        """
        Require permission, raising exception if denied.
        
        Use this for imperative authorization checks.
        """
        result = self.check_permission(genesis_id, permission, context)
        
        if not result.allowed:
            raise HTTPException(
                status_code=HTTP_403_FORBIDDEN,
                detail={
                    "error": "Access denied",
                    "permission": permission,
                    "reason": result.reason
                }
            )
    
    def require_any_permission(
        self,
        genesis_id: str,
        permissions: List[str],
        context: Optional[AuthorizationContext] = None
    ) -> PermissionCheck:
        """Require any one of the listed permissions."""
        for permission in permissions:
            result = self.check_permission(genesis_id, permission, context)
            if result.allowed:
                return result
        
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN,
            detail={
                "error": "Access denied",
                "required_permissions": permissions,
                "reason": "None of the required permissions granted"
            }
        )
    
    def require_all_permissions(
        self,
        genesis_id: str,
        permissions: List[str],
        context: Optional[AuthorizationContext] = None
    ) -> List[PermissionCheck]:
        """Require all of the listed permissions."""
        results = []
        for permission in permissions:
            result = self.check_permission(genesis_id, permission, context)
            if not result.allowed:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail={
                        "error": "Access denied",
                        "permission": permission,
                        "reason": result.reason
                    }
                )
            results.append(result)
        return results
    
    def _log_authorization_decision(
        self,
        result: PermissionCheck,
        context: Optional[AuthorizationContext] = None
    ) -> None:
        """Log authorization decision to immutable audit."""
        audit_storage = self._get_audit_storage()
        
        if audit_storage:
            try:
                audit_storage.record(
                    audit_type=self._ImmutableAuditType.PERMISSION_CHANGE if result.allowed else self._ImmutableAuditType.ACCESS_DENIED,
                    action_description=f"Authorization {'granted' if result.allowed else 'denied'}: {result.permission}",
                    actor_type="user",
                    actor_id=result.genesis_id,
                    session_id=context.session_id if context else None,
                    severity="info" if result.allowed else "warning",
                    component="rbac.enforcer",
                    action_data=result.to_dict(),
                    context={
                        "client_ip": context.client_ip if context else None,
                        "request_path": context.request_path if context else None,
                        "request_method": context.request_method if context else None,
                    } if context else None
                )
            except Exception as e:
                logger.error(f"[RBAC] Failed to log authorization decision: {e}")
        
        log_level = logging.INFO if result.allowed else logging.WARNING
        logger.log(
            log_level,
            f"[RBAC] Authorization {'GRANTED' if result.allowed else 'DENIED'}: "
            f"user={result.genesis_id}, permission={result.permission}, "
            f"roles={result.roles}, reason={result.reason}"
        )
    
    def disable(self) -> None:
        """Disable RBAC enforcement (for testing/emergencies)."""
        self._enabled = False
        logger.warning("[RBAC] Enforcement DISABLED")
    
    def enable(self) -> None:
        """Enable RBAC enforcement."""
        self._enabled = True
        logger.info("[RBAC] Enforcement ENABLED")
    
    @property
    def is_enabled(self) -> bool:
        """Check if RBAC enforcement is enabled."""
        return self._enabled


_enforcer: Optional[RBACEnforcer] = None


def get_enforcer(session: Session) -> RBACEnforcer:
    """Get or create the RBAC enforcer singleton."""
    global _enforcer
    if _enforcer is None:
        _enforcer = RBACEnforcer(session)
    return _enforcer


def create_permission_dependency(
    permission: str,
    allow_service_accounts: bool = True
):
    """
    Create a FastAPI dependency that requires a specific permission.
    
    Usage:
        @app.get("/admin/users", dependencies=[Depends(require_permission("users:*:read"))])
        def list_users():
            ...
    """
    async def permission_dependency(request: Request):
        genesis_id = getattr(request.state, "genesis_id", None)
        
        if not genesis_id:
            genesis_id = request.cookies.get("genesis_id")
        if not genesis_id:
            genesis_id = request.headers.get("X-Genesis-ID")
        
        if not genesis_id:
            raise HTTPException(
                status_code=HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        context = AuthorizationContext(
            genesis_id=genesis_id,
            session_id=getattr(request.state, "session_id", None),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
            request_path=str(request.url.path),
            request_method=request.method
        )
        
        from database.session import get_db
        session = next(get_db())
        
        try:
            enforcer = get_enforcer(session)
            result = enforcer.check_permission(genesis_id, permission, context)
            
            if not result.allowed:
                raise HTTPException(
                    status_code=HTTP_403_FORBIDDEN,
                    detail={
                        "error": "Access denied",
                        "permission": permission,
                        "reason": result.reason
                    }
                )
            
            request.state.rbac_check = result
            return result
        finally:
            session.close()
    
    return permission_dependency


def require_permission(permission: str):
    """
    Decorator factory to require a specific permission for a function.
    
    Usage:
        @require_permission("code:healing:approve")
        def approve_healing_action(genesis_id: str, action_id: str):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            genesis_id = kwargs.get("genesis_id")
            if not genesis_id and args:
                genesis_id = args[0]
            
            if not genesis_id:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="genesis_id required for authorization"
                )
            
            context = AuthorizationContext(genesis_id=genesis_id)
            
            from database.session import get_db
            session = next(get_db())
            
            try:
                enforcer = get_enforcer(session)
                enforcer.require_permission(genesis_id, permission, context)
                return func(*args, **kwargs)
            finally:
                session.close()
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            genesis_id = kwargs.get("genesis_id")
            if not genesis_id and args:
                genesis_id = args[0]
            
            if not genesis_id:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="genesis_id required for authorization"
                )
            
            context = AuthorizationContext(genesis_id=genesis_id)
            
            from database.session import get_db
            session = next(get_db())
            
            try:
                enforcer = get_enforcer(session)
                enforcer.require_permission(genesis_id, permission, context)
                return await func(*args, **kwargs)
            finally:
                session.close()
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


def require_any(*permissions: str):
    """
    Decorator to require any one of multiple permissions.
    
    Usage:
        @require_any("code:*:update", "code:healing:approve")
        def update_code(genesis_id: str, file_path: str):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            genesis_id = kwargs.get("genesis_id")
            if not genesis_id and args:
                genesis_id = args[0]
            
            if not genesis_id:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="genesis_id required for authorization"
                )
            
            context = AuthorizationContext(genesis_id=genesis_id)
            
            from database.session import get_db
            session = next(get_db())
            
            try:
                enforcer = get_enforcer(session)
                enforcer.require_any_permission(
                    genesis_id, list(permissions), context
                )
                return func(*args, **kwargs)
            finally:
                session.close()
        
        return wrapper
    
    return decorator


def require_all(*permissions: str):
    """
    Decorator to require all of multiple permissions.
    
    Usage:
        @require_all("code:*:read", "audit:*:read")
        def code_audit_report(genesis_id: str):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            genesis_id = kwargs.get("genesis_id")
            if not genesis_id and args:
                genesis_id = args[0]
            
            if not genesis_id:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="genesis_id required for authorization"
                )
            
            context = AuthorizationContext(genesis_id=genesis_id)
            
            from database.session import get_db
            session = next(get_db())
            
            try:
                enforcer = get_enforcer(session)
                enforcer.require_all_permissions(
                    genesis_id, list(permissions), context
                )
                return func(*args, **kwargs)
            finally:
                session.close()
        
        return wrapper
    
    return decorator


class PermissionChecker:
    """
    Utility class for checking permissions without enforcement.
    
    Useful for conditional logic based on permissions.
    """
    
    def __init__(self, session: Session, genesis_id: str):
        self.session = session
        self.genesis_id = genesis_id
        self.enforcer = get_enforcer(session)
        self._context = AuthorizationContext(genesis_id=genesis_id)
    
    def can(self, permission: str) -> bool:
        """Check if user can perform action (doesn't raise)."""
        result = self.enforcer.check_permission(
            self.genesis_id, permission, self._context
        )
        return result.allowed
    
    def can_any(self, *permissions: str) -> bool:
        """Check if user has any of the permissions."""
        return any(self.can(p) for p in permissions)
    
    def can_all(self, *permissions: str) -> bool:
        """Check if user has all of the permissions."""
        return all(self.can(p) for p in permissions)
    
    def get_permissions(self) -> List[str]:
        """Get all permissions for the user."""
        role_manager = get_role_manager(self.session)
        return list(role_manager.get_user_permissions(self.genesis_id))
    
    def get_roles(self) -> List[str]:
        """Get all roles for the user."""
        role_manager = get_role_manager(self.session)
        roles = role_manager.get_user_roles(self.genesis_id)
        return [r.name for r in roles]


def get_permission_checker(
    session: Session,
    genesis_id: str
) -> PermissionChecker:
    """Create a permission checker for a user."""
    return PermissionChecker(session, genesis_id)
