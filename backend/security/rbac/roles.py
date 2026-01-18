"""
Role Management for GRACE RBAC System.

Provides:
- Built-in role definitions
- Role hierarchy with permission inheritance
- Dynamic role creation and management
- Role assignment to Genesis IDs
- Temporal roles with time-limited access
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set
from enum import Enum
from dataclasses import dataclass
from sqlalchemy.orm import Session

from .models import Role, UserRole, Permission, ResourceType, ActionType

logger = logging.getLogger(__name__)


class BuiltInRole(str, Enum):
    """Built-in system roles with predefined permissions."""
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    OPERATOR = "operator"
    DEVELOPER = "developer"
    ANALYST = "analyst"
    READONLY = "readonly"
    AUDITOR = "auditor"
    SERVICE_ACCOUNT = "service_account"
    GUEST = "guest"


ROLE_HIERARCHY = {
    BuiltInRole.SUPER_ADMIN: None,
    BuiltInRole.ADMIN: BuiltInRole.SUPER_ADMIN,
    BuiltInRole.OPERATOR: BuiltInRole.ADMIN,
    BuiltInRole.DEVELOPER: BuiltInRole.OPERATOR,
    BuiltInRole.ANALYST: BuiltInRole.OPERATOR,
    BuiltInRole.AUDITOR: BuiltInRole.ADMIN,
    BuiltInRole.READONLY: None,
    BuiltInRole.SERVICE_ACCOUNT: None,
    BuiltInRole.GUEST: None,
}

BUILT_IN_ROLE_DEFINITIONS = {
    BuiltInRole.SUPER_ADMIN: {
        "display_name": "Super Administrator",
        "description": "Full system access with all permissions. Use sparingly.",
        "permissions": ["*:*:*"],
        "priority": 1000,
        "is_system": True,
    },
    BuiltInRole.ADMIN: {
        "display_name": "Administrator",
        "description": "Administrative access to manage users, roles, and system configuration.",
        "permissions": [
            "users:*:*",
            "roles:*:*",
            "permissions:*:read",
            "system:config:read",
            "system:config:update",
            "api:*:*",
            "audit:*:read",
            "audit:*:export",
            "code:*:read",
            "knowledge_base:*:*",
        ],
        "priority": 900,
        "is_system": True,
    },
    BuiltInRole.OPERATOR: {
        "display_name": "Operator",
        "description": "Operational access to manage code, pipelines, and system operations.",
        "permissions": [
            "code:*:read",
            "code:*:update",
            "code:*:execute",
            "code:healing:approve",
            "pipelines:*:*",
            "system:status:read",
            "system:logs:read",
            "knowledge_base:*:read",
            "knowledge_base:*:update",
            "models:*:read",
            "models:*:execute",
            "api:*:read",
            "api:*:execute",
        ],
        "priority": 700,
        "is_system": True,
    },
    BuiltInRole.DEVELOPER: {
        "display_name": "Developer",
        "description": "Development access for code changes and testing.",
        "permissions": [
            "code:*:read",
            "code:*:create",
            "code:*:update",
            "code:test:execute",
            "knowledge_base:*:read",
            "knowledge_base:docs:update",
            "api:*:read",
            "api:dev:execute",
            "models:*:read",
            "pipelines:*:read",
            "pipelines:dev:execute",
        ],
        "priority": 500,
        "is_system": True,
    },
    BuiltInRole.ANALYST: {
        "display_name": "Analyst",
        "description": "Read access for analysis and reporting.",
        "permissions": [
            "code:*:read",
            "knowledge_base:*:read",
            "audit:*:read",
            "audit:reports:export",
            "models:*:read",
            "pipelines:*:read",
            "system:status:read",
            "system:metrics:read",
        ],
        "priority": 400,
        "is_system": True,
    },
    BuiltInRole.AUDITOR: {
        "display_name": "Auditor",
        "description": "Full read access to audit trails and compliance data.",
        "permissions": [
            "audit:*:read",
            "audit:*:export",
            "audit:sensitive:read",
            "code:*:read",
            "users:*:read",
            "roles:*:read",
            "system:logs:read",
            "system:config:read",
            "genesis_keys:*:read",
        ],
        "priority": 600,
        "is_system": True,
    },
    BuiltInRole.READONLY: {
        "display_name": "Read Only",
        "description": "Basic read-only access to public resources.",
        "permissions": [
            "code:public:read",
            "knowledge_base:public:read",
            "api:public:read",
            "system:status:read",
        ],
        "priority": 100,
        "is_system": True,
    },
    BuiltInRole.SERVICE_ACCOUNT: {
        "display_name": "Service Account",
        "description": "For automated services and integrations.",
        "permissions": [
            "api:*:execute",
            "code:*:read",
            "knowledge_base:*:read",
            "models:*:execute",
            "pipelines:*:execute",
        ],
        "priority": 300,
        "is_system": True,
    },
    BuiltInRole.GUEST: {
        "display_name": "Guest",
        "description": "Minimal access for unauthenticated or guest users.",
        "permissions": [
            "system:status:read",
            "api:public:read",
        ],
        "priority": 0,
        "is_system": True,
    },
}


class RoleManager:
    """
    Manages roles and role assignments for GRACE.
    
    Features:
    - Built-in role initialization
    - Role hierarchy with permission inheritance
    - Dynamic role creation
    - Role assignment with temporal access
    - Efficient permission caching
    """
    
    def __init__(self, session: Session):
        self.session = session
        self._permission_cache: Dict[str, Set[str]] = {}
        self._role_cache: Dict[str, Role] = {}
        self._cache_ttl = 300
        self._cache_updated_at: Optional[datetime] = None
        
    def initialize_built_in_roles(self) -> List[Role]:
        """Initialize all built-in roles in the database."""
        created_roles = []
        
        for role_enum, definition in BUILT_IN_ROLE_DEFINITIONS.items():
            existing = self.session.query(Role).filter(
                Role.name == role_enum.value
            ).first()
            
            if existing:
                existing.permissions = definition["permissions"]
                existing.display_name = definition["display_name"]
                existing.description = definition["description"]
                existing.priority = definition["priority"]
                existing.is_system = definition["is_system"]
                created_roles.append(existing)
            else:
                parent_enum = ROLE_HIERARCHY.get(role_enum)
                parent_role_id = None
                if parent_enum:
                    parent = self.session.query(Role).filter(
                        Role.name == parent_enum.value
                    ).first()
                    if parent:
                        parent_role_id = parent.role_id
                
                role = Role(
                    role_id=f"role-{role_enum.value}",
                    name=role_enum.value,
                    display_name=definition["display_name"],
                    description=definition["description"],
                    parent_role_id=parent_role_id,
                    permissions=definition["permissions"],
                    priority=definition["priority"],
                    is_system=definition["is_system"],
                    is_active=True
                )
                self.session.add(role)
                created_roles.append(role)
        
        self.session.commit()
        self._invalidate_cache()
        
        logger.info(f"[RBAC] Initialized {len(created_roles)} built-in roles")
        return created_roles
    
    def create_role(
        self,
        name: str,
        permissions: List[str],
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        parent_role_name: Optional[str] = None,
        priority: int = 200,
        created_by: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Role:
        """Create a new custom role."""
        existing = self.session.query(Role).filter(Role.name == name).first()
        if existing:
            raise ValueError(f"Role '{name}' already exists")
        
        parent_role_id = None
        if parent_role_name:
            parent = self.session.query(Role).filter(
                Role.name == parent_role_name
            ).first()
            if not parent:
                raise ValueError(f"Parent role '{parent_role_name}' not found")
            parent_role_id = parent.role_id
        
        role = Role(
            role_id=f"role-{uuid.uuid4().hex[:12]}",
            name=name,
            display_name=display_name or name,
            description=description,
            parent_role_id=parent_role_id,
            permissions=permissions,
            priority=priority,
            is_system=False,
            is_active=True,
            created_by=created_by,
            metadata_=metadata or {}
        )
        
        self.session.add(role)
        self.session.commit()
        self._invalidate_cache()
        
        logger.info(f"[RBAC] Created role: {name} with {len(permissions)} permissions")
        return role
    
    def update_role(
        self,
        role_name: str,
        permissions: Optional[List[str]] = None,
        display_name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Role:
        """Update an existing role."""
        role = self.session.query(Role).filter(Role.name == role_name).first()
        if not role:
            raise ValueError(f"Role '{role_name}' not found")
        
        if role.is_system:
            logger.warning(f"[RBAC] Modifying system role: {role_name}")
        
        if permissions is not None:
            role.permissions = permissions
        if display_name is not None:
            role.display_name = display_name
        if description is not None:
            role.description = description
        if is_active is not None:
            role.is_active = is_active
        
        role.updated_at = datetime.utcnow()
        self.session.commit()
        self._invalidate_cache()
        
        logger.info(f"[RBAC] Updated role: {role_name}")
        return role
    
    def delete_role(self, role_name: str, force: bool = False) -> bool:
        """Delete a role (soft delete unless force=True)."""
        role = self.session.query(Role).filter(Role.name == role_name).first()
        if not role:
            raise ValueError(f"Role '{role_name}' not found")
        
        if role.is_system and not force:
            raise ValueError(f"Cannot delete system role '{role_name}' without force=True")
        
        assignments = self.session.query(UserRole).filter(
            UserRole.role_id == role.role_id,
            UserRole.is_active == True
        ).count()
        
        if assignments > 0 and not force:
            raise ValueError(
                f"Role '{role_name}' has {assignments} active assignments. "
                "Remove assignments first or use force=True"
            )
        
        if force:
            self.session.query(UserRole).filter(
                UserRole.role_id == role.role_id
            ).update({"is_active": False, "revoked_at": datetime.utcnow()})
            self.session.delete(role)
        else:
            role.is_active = False
        
        self.session.commit()
        self._invalidate_cache()
        
        logger.info(f"[RBAC] Deleted role: {role_name} (force={force})")
        return True
    
    def get_role(self, role_name: str) -> Optional[Role]:
        """Get a role by name."""
        return self.session.query(Role).filter(
            Role.name == role_name,
            Role.is_active == True
        ).first()
    
    def get_role_by_id(self, role_id: str) -> Optional[Role]:
        """Get a role by ID."""
        return self.session.query(Role).filter(
            Role.role_id == role_id,
            Role.is_active == True
        ).first()
    
    def list_roles(self, include_inactive: bool = False) -> List[Role]:
        """List all roles."""
        query = self.session.query(Role)
        if not include_inactive:
            query = query.filter(Role.is_active == True)
        return query.order_by(Role.priority.desc()).all()
    
    def assign_role(
        self,
        genesis_id: str,
        role_name: str,
        granted_by: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        expires_in_hours: Optional[int] = None,
        reason: Optional[str] = None,
        scope: Optional[Dict] = None
    ) -> UserRole:
        """Assign a role to a Genesis ID."""
        role = self.get_role(role_name)
        if not role:
            raise ValueError(f"Role '{role_name}' not found")
        
        existing = self.session.query(UserRole).filter(
            UserRole.genesis_id == genesis_id,
            UserRole.role_id == role.role_id,
            UserRole.is_active == True
        ).first()
        
        if existing:
            if existing.expires_at:
                existing.expires_at = expires_at or (
                    datetime.utcnow() + timedelta(hours=expires_in_hours)
                    if expires_in_hours else None
                )
                self.session.commit()
                return existing
            raise ValueError(f"User already has role '{role_name}'")
        
        if expires_in_hours and not expires_at:
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
        assignment = UserRole(
            assignment_id=f"assign-{uuid.uuid4().hex[:12]}",
            genesis_id=genesis_id,
            role_id=role.role_id,
            granted_by=granted_by,
            granted_at=datetime.utcnow(),
            expires_at=expires_at,
            is_active=True,
            reason=reason,
            scope=scope
        )
        
        self.session.add(assignment)
        self.session.commit()
        self._invalidate_user_cache(genesis_id)
        
        logger.info(
            f"[RBAC] Assigned role '{role_name}' to {genesis_id} "
            f"(expires: {expires_at or 'never'})"
        )
        return assignment
    
    def revoke_role(
        self,
        genesis_id: str,
        role_name: str,
        revoked_by: Optional[str] = None,
        reason: Optional[str] = None
    ) -> bool:
        """Revoke a role from a Genesis ID."""
        role = self.get_role(role_name)
        if not role:
            raise ValueError(f"Role '{role_name}' not found")
        
        assignment = self.session.query(UserRole).filter(
            UserRole.genesis_id == genesis_id,
            UserRole.role_id == role.role_id,
            UserRole.is_active == True
        ).first()
        
        if not assignment:
            raise ValueError(f"User does not have role '{role_name}'")
        
        assignment.is_active = False
        assignment.revoked_at = datetime.utcnow()
        assignment.revoked_by = revoked_by
        assignment.revoke_reason = reason
        
        self.session.commit()
        self._invalidate_user_cache(genesis_id)
        
        logger.info(f"[RBAC] Revoked role '{role_name}' from {genesis_id}")
        return True
    
    def get_user_roles(self, genesis_id: str) -> List[Role]:
        """Get all active roles for a Genesis ID."""
        now = datetime.utcnow()
        
        assignments = self.session.query(UserRole).filter(
            UserRole.genesis_id == genesis_id,
            UserRole.is_active == True
        ).all()
        
        roles = []
        for assignment in assignments:
            if assignment.expires_at and assignment.expires_at < now:
                assignment.is_active = False
                continue
            
            role = self.get_role_by_id(assignment.role_id)
            if role and role.is_active:
                roles.append(role)
        
        self.session.commit()
        
        roles.sort(key=lambda r: r.priority, reverse=True)
        return roles
    
    def get_user_permissions(self, genesis_id: str) -> Set[str]:
        """Get all effective permissions for a Genesis ID."""
        cache_key = f"perms:{genesis_id}"
        
        if self._is_cache_valid() and cache_key in self._permission_cache:
            return self._permission_cache[cache_key]
        
        roles = self.get_user_roles(genesis_id)
        permissions = set()
        
        for role in roles:
            role_perms = self._get_role_permissions_with_inheritance(role)
            permissions.update(role_perms)
        
        self._permission_cache[cache_key] = permissions
        return permissions
    
    def _get_role_permissions_with_inheritance(self, role: Role) -> Set[str]:
        """Get all permissions for a role including inherited ones."""
        permissions = set(role.permissions or [])
        
        if role.parent_role_id:
            parent = self.get_role_by_id(role.parent_role_id)
            if parent:
                parent_perms = self._get_role_permissions_with_inheritance(parent)
                permissions.update(parent_perms)
        
        return permissions
    
    def has_permission(
        self,
        genesis_id: str,
        permission: str
    ) -> bool:
        """Check if a Genesis ID has a specific permission."""
        user_permissions = self.get_user_permissions(genesis_id)
        
        if "*:*:*" in user_permissions:
            return True
        
        parts = permission.split(":")
        if len(parts) < 2:
            return False
        
        resource = parts[0]
        action = parts[-1]
        sub_resource = parts[1] if len(parts) > 2 else "*"
        
        checks = [
            permission,
            f"{resource}:*:*",
            f"{resource}:{sub_resource}:*",
            f"{resource}:*:{action}",
            f"*:*:{action}",
        ]
        
        for check in checks:
            if check in user_permissions:
                return True
        
        return False
    
    def get_users_with_role(self, role_name: str) -> List[str]:
        """Get all Genesis IDs with a specific role."""
        role = self.get_role(role_name)
        if not role:
            return []
        
        assignments = self.session.query(UserRole).filter(
            UserRole.role_id == role.role_id,
            UserRole.is_active == True
        ).all()
        
        now = datetime.utcnow()
        return [
            a.genesis_id for a in assignments
            if not a.expires_at or a.expires_at > now
        ]
    
    def cleanup_expired_assignments(self) -> int:
        """Deactivate all expired role assignments."""
        now = datetime.utcnow()
        
        expired = self.session.query(UserRole).filter(
            UserRole.is_active == True,
            UserRole.expires_at != None,
            UserRole.expires_at < now
        ).all()
        
        count = 0
        for assignment in expired:
            assignment.is_active = False
            self._invalidate_user_cache(assignment.genesis_id)
            count += 1
        
        self.session.commit()
        
        if count > 0:
            logger.info(f"[RBAC] Cleaned up {count} expired role assignments")
        
        return count
    
    def _invalidate_cache(self):
        """Invalidate the entire permission cache."""
        self._permission_cache.clear()
        self._role_cache.clear()
        self._cache_updated_at = None
    
    def _invalidate_user_cache(self, genesis_id: str):
        """Invalidate cache for a specific user."""
        cache_key = f"perms:{genesis_id}"
        self._permission_cache.pop(cache_key, None)
    
    def _is_cache_valid(self) -> bool:
        """Check if the cache is still valid."""
        if not self._cache_updated_at:
            self._cache_updated_at = datetime.utcnow()
            return False
        
        age = (datetime.utcnow() - self._cache_updated_at).total_seconds()
        return age < self._cache_ttl


_role_manager: Optional[RoleManager] = None


def get_role_manager(session: Session) -> RoleManager:
    """Get or create the role manager singleton."""
    global _role_manager
    if _role_manager is None:
        _role_manager = RoleManager(session)
    return _role_manager
