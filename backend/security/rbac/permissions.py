"""
Permission Definitions for GRACE RBAC System.

Provides:
- Fine-grained permission definitions
- Resource and action type mappings
- Permission string parsing and matching
- Attribute-based conditions for contextual access
"""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Set, Tuple
from sqlalchemy.orm import Session

from .models import (
    Permission, ResourceType, ActionType, PolicyDocument,
    Condition, ConditionOperator
)

logger = logging.getLogger(__name__)


PERMISSION_DEFINITIONS = {
    "code:*:read": {
        "description": "Read all code files",
        "resource": ResourceType.CODE,
        "action": ActionType.READ,
    },
    "code:*:create": {
        "description": "Create new code files",
        "resource": ResourceType.CODE,
        "action": ActionType.CREATE,
    },
    "code:*:update": {
        "description": "Update existing code files",
        "resource": ResourceType.CODE,
        "action": ActionType.UPDATE,
    },
    "code:*:delete": {
        "description": "Delete code files",
        "resource": ResourceType.CODE,
        "action": ActionType.DELETE,
    },
    "code:*:execute": {
        "description": "Execute code",
        "resource": ResourceType.CODE,
        "action": ActionType.EXECUTE,
    },
    "code:healing:approve": {
        "description": "Approve self-healing code changes",
        "resource": ResourceType.CODE,
        "sub_resource": "healing",
        "action": ActionType.APPROVE,
    },
    "code:healing:execute": {
        "description": "Execute healing operations",
        "resource": ResourceType.CODE,
        "sub_resource": "healing",
        "action": ActionType.EXECUTE,
    },
    "code:test:execute": {
        "description": "Execute tests",
        "resource": ResourceType.CODE,
        "sub_resource": "test",
        "action": ActionType.EXECUTE,
    },
    "code:public:read": {
        "description": "Read public code only",
        "resource": ResourceType.CODE,
        "sub_resource": "public",
        "action": ActionType.READ,
    },
    
    "knowledge_base:*:read": {
        "description": "Read knowledge base entries",
        "resource": ResourceType.KNOWLEDGE_BASE,
        "action": ActionType.READ,
    },
    "knowledge_base:*:create": {
        "description": "Create knowledge base entries",
        "resource": ResourceType.KNOWLEDGE_BASE,
        "action": ActionType.CREATE,
    },
    "knowledge_base:*:update": {
        "description": "Update knowledge base entries",
        "resource": ResourceType.KNOWLEDGE_BASE,
        "action": ActionType.UPDATE,
    },
    "knowledge_base:*:delete": {
        "description": "Delete knowledge base entries",
        "resource": ResourceType.KNOWLEDGE_BASE,
        "action": ActionType.DELETE,
    },
    "knowledge_base:docs:update": {
        "description": "Update documentation",
        "resource": ResourceType.KNOWLEDGE_BASE,
        "sub_resource": "docs",
        "action": ActionType.UPDATE,
    },
    "knowledge_base:public:read": {
        "description": "Read public knowledge base entries",
        "resource": ResourceType.KNOWLEDGE_BASE,
        "sub_resource": "public",
        "action": ActionType.READ,
    },
    
    "audit:*:read": {
        "description": "Read audit records",
        "resource": ResourceType.AUDIT,
        "action": ActionType.READ,
    },
    "audit:*:export": {
        "description": "Export audit records",
        "resource": ResourceType.AUDIT,
        "action": ActionType.EXPORT,
    },
    "audit:sensitive:read": {
        "description": "Read sensitive audit records",
        "resource": ResourceType.AUDIT,
        "sub_resource": "sensitive",
        "action": ActionType.READ,
    },
    "audit:reports:export": {
        "description": "Export audit reports",
        "resource": ResourceType.AUDIT,
        "sub_resource": "reports",
        "action": ActionType.EXPORT,
    },
    
    "genesis_keys:*:read": {
        "description": "Read Genesis Keys",
        "resource": ResourceType.GENESIS_KEYS,
        "action": ActionType.READ,
    },
    "genesis_keys:*:create": {
        "description": "Create Genesis Keys",
        "resource": ResourceType.GENESIS_KEYS,
        "action": ActionType.CREATE,
    },
    "genesis_keys:*:update": {
        "description": "Update Genesis Keys",
        "resource": ResourceType.GENESIS_KEYS,
        "action": ActionType.UPDATE,
    },
    "genesis_keys:*:delete": {
        "description": "Delete Genesis Keys",
        "resource": ResourceType.GENESIS_KEYS,
        "action": ActionType.DELETE,
    },
    "genesis_keys:*:approve": {
        "description": "Approve Genesis Key operations",
        "resource": ResourceType.GENESIS_KEYS,
        "action": ActionType.APPROVE,
    },
    
    "system:config:read": {
        "description": "Read system configuration",
        "resource": ResourceType.SYSTEM,
        "sub_resource": "config",
        "action": ActionType.READ,
    },
    "system:config:update": {
        "description": "Update system configuration",
        "resource": ResourceType.SYSTEM,
        "sub_resource": "config",
        "action": ActionType.UPDATE,
    },
    "system:status:read": {
        "description": "Read system status",
        "resource": ResourceType.SYSTEM,
        "sub_resource": "status",
        "action": ActionType.READ,
    },
    "system:logs:read": {
        "description": "Read system logs",
        "resource": ResourceType.SYSTEM,
        "sub_resource": "logs",
        "action": ActionType.READ,
    },
    "system:metrics:read": {
        "description": "Read system metrics",
        "resource": ResourceType.SYSTEM,
        "sub_resource": "metrics",
        "action": ActionType.READ,
    },
    "system:*:admin": {
        "description": "Full system administration",
        "resource": ResourceType.SYSTEM,
        "action": ActionType.ADMIN,
    },
    
    "api:*:read": {
        "description": "Read API endpoints",
        "resource": ResourceType.API,
        "action": ActionType.READ,
    },
    "api:*:execute": {
        "description": "Execute API endpoints",
        "resource": ResourceType.API,
        "action": ActionType.EXECUTE,
    },
    "api:public:read": {
        "description": "Read public API endpoints",
        "resource": ResourceType.API,
        "sub_resource": "public",
        "action": ActionType.READ,
    },
    "api:dev:execute": {
        "description": "Execute development API endpoints",
        "resource": ResourceType.API,
        "sub_resource": "dev",
        "action": ActionType.EXECUTE,
    },
    
    "users:*:read": {
        "description": "Read user information",
        "resource": ResourceType.USERS,
        "action": ActionType.READ,
    },
    "users:*:create": {
        "description": "Create users",
        "resource": ResourceType.USERS,
        "action": ActionType.CREATE,
    },
    "users:*:update": {
        "description": "Update users",
        "resource": ResourceType.USERS,
        "action": ActionType.UPDATE,
    },
    "users:*:delete": {
        "description": "Delete users",
        "resource": ResourceType.USERS,
        "action": ActionType.DELETE,
    },
    
    "secrets:*:read": {
        "description": "Read secrets",
        "resource": ResourceType.SECRETS,
        "action": ActionType.READ,
    },
    "secrets:*:create": {
        "description": "Create secrets",
        "resource": ResourceType.SECRETS,
        "action": ActionType.CREATE,
    },
    "secrets:*:update": {
        "description": "Update secrets",
        "resource": ResourceType.SECRETS,
        "action": ActionType.UPDATE,
    },
    "secrets:*:delete": {
        "description": "Delete secrets",
        "resource": ResourceType.SECRETS,
        "action": ActionType.DELETE,
    },
    
    "roles:*:read": {
        "description": "Read roles",
        "resource": ResourceType.ROLES,
        "action": ActionType.READ,
    },
    "roles:*:create": {
        "description": "Create roles",
        "resource": ResourceType.ROLES,
        "action": ActionType.CREATE,
    },
    "roles:*:update": {
        "description": "Update roles",
        "resource": ResourceType.ROLES,
        "action": ActionType.UPDATE,
    },
    "roles:*:delete": {
        "description": "Delete roles",
        "resource": ResourceType.ROLES,
        "action": ActionType.DELETE,
    },
    
    "permissions:*:read": {
        "description": "Read permissions",
        "resource": ResourceType.PERMISSIONS,
        "action": ActionType.READ,
    },
    
    "models:*:read": {
        "description": "Read ML models",
        "resource": ResourceType.MODELS,
        "action": ActionType.READ,
    },
    "models:*:execute": {
        "description": "Execute ML models",
        "resource": ResourceType.MODELS,
        "action": ActionType.EXECUTE,
    },
    "models:*:create": {
        "description": "Create/train ML models",
        "resource": ResourceType.MODELS,
        "action": ActionType.CREATE,
    },
    "models:*:update": {
        "description": "Update ML models",
        "resource": ResourceType.MODELS,
        "action": ActionType.UPDATE,
    },
    
    "pipelines:*:read": {
        "description": "Read pipelines",
        "resource": ResourceType.PIPELINES,
        "action": ActionType.READ,
    },
    "pipelines:*:execute": {
        "description": "Execute pipelines",
        "resource": ResourceType.PIPELINES,
        "action": ActionType.EXECUTE,
    },
    "pipelines:*:create": {
        "description": "Create pipelines",
        "resource": ResourceType.PIPELINES,
        "action": ActionType.CREATE,
    },
    "pipelines:*:update": {
        "description": "Update pipelines",
        "resource": ResourceType.PIPELINES,
        "action": ActionType.UPDATE,
    },
    "pipelines:dev:execute": {
        "description": "Execute development pipelines",
        "resource": ResourceType.PIPELINES,
        "sub_resource": "dev",
        "action": ActionType.EXECUTE,
    },
}

BUSINESS_HOURS_POLICY = PolicyDocument(
    conditions=[
        Condition(
            attribute="time.hour",
            operator=ConditionOperator.BETWEEN,
            value=[9, 17]
        ),
        Condition(
            attribute="time.day",
            operator=ConditionOperator.IN,
            value=[0, 1, 2, 3, 4]
        ),
    ],
    logic="AND",
    description="Allow only during business hours (9 AM - 5 PM, Monday-Friday)"
)

INTERNAL_NETWORK_POLICY = PolicyDocument(
    conditions=[
        Condition(
            attribute="client.ip",
            operator=ConditionOperator.MATCHES,
            value=r"^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.)"
        ),
    ],
    logic="AND",
    description="Allow only from internal network (RFC 1918 addresses)"
)

OWNER_ONLY_POLICY = PolicyDocument(
    conditions=[
        Condition(
            attribute="resource.owner",
            operator=ConditionOperator.EQUALS,
            value="${user.id}"
        ),
    ],
    logic="AND",
    description="Allow only for resource owner"
)


class PermissionManager:
    """
    Manages permission definitions and matching.
    
    Features:
    - Permission initialization
    - Permission string parsing
    - Permission matching with wildcards
    - Condition evaluation
    """
    
    def __init__(self, session: Session):
        self.session = session
        
    def initialize_permissions(self) -> List[Permission]:
        """Initialize all permission definitions in the database."""
        created = []
        
        for perm_string, definition in PERMISSION_DEFINITIONS.items():
            parts = perm_string.split(":")
            resource = parts[0]
            action = parts[-1]
            sub_resource = parts[1] if len(parts) > 2 and parts[1] != "*" else None
            
            existing = self.session.query(Permission).filter(
                Permission.name == perm_string
            ).first()
            
            if existing:
                existing.description = definition.get("description", "")
                created.append(existing)
            else:
                perm = Permission(
                    permission_id=f"perm-{uuid.uuid4().hex[:12]}",
                    name=perm_string,
                    description=definition.get("description", ""),
                    resource=resource,
                    sub_resource=sub_resource,
                    action=action,
                    is_system=True,
                    is_active=True
                )
                self.session.add(perm)
                created.append(perm)
        
        self.session.commit()
        logger.info(f"[RBAC] Initialized {len(created)} permissions")
        return created
    
    def create_permission(
        self,
        name: str,
        resource: str,
        action: str,
        sub_resource: Optional[str] = None,
        description: Optional[str] = None,
        conditions: Optional[PolicyDocument] = None
    ) -> Permission:
        """Create a new custom permission."""
        existing = self.session.query(Permission).filter(
            Permission.name == name
        ).first()
        
        if existing:
            raise ValueError(f"Permission '{name}' already exists")
        
        perm = Permission(
            permission_id=f"perm-{uuid.uuid4().hex[:12]}",
            name=name,
            description=description,
            resource=resource,
            sub_resource=sub_resource,
            action=action,
            conditions=conditions.to_dict() if conditions else None,
            is_system=False,
            is_active=True
        )
        
        self.session.add(perm)
        self.session.commit()
        
        logger.info(f"[RBAC] Created permission: {name}")
        return perm
    
    def get_permission(self, name: str) -> Optional[Permission]:
        """Get a permission by name."""
        return self.session.query(Permission).filter(
            Permission.name == name,
            Permission.is_active == True
        ).first()
    
    def list_permissions(
        self,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        include_inactive: bool = False
    ) -> List[Permission]:
        """List permissions with optional filters."""
        query = self.session.query(Permission)
        
        if not include_inactive:
            query = query.filter(Permission.is_active == True)
        
        if resource:
            query = query.filter(Permission.resource == resource)
        
        if action:
            query = query.filter(Permission.action == action)
        
        return query.order_by(Permission.resource, Permission.action).all()
    
    def delete_permission(self, name: str, force: bool = False) -> bool:
        """Delete a permission."""
        perm = self.session.query(Permission).filter(
            Permission.name == name
        ).first()
        
        if not perm:
            raise ValueError(f"Permission '{name}' not found")
        
        if perm.is_system and not force:
            raise ValueError(f"Cannot delete system permission '{name}' without force=True")
        
        if force:
            self.session.delete(perm)
        else:
            perm.is_active = False
        
        self.session.commit()
        logger.info(f"[RBAC] Deleted permission: {name}")
        return True
    
    @staticmethod
    def parse_permission(permission_string: str) -> Tuple[str, Optional[str], str]:
        """
        Parse a permission string into components.
        
        Format: resource:sub_resource:action or resource:action
        Returns: (resource, sub_resource, action)
        """
        parts = permission_string.split(":")
        
        if len(parts) == 2:
            return (parts[0], None, parts[1])
        elif len(parts) == 3:
            return (parts[0], parts[1] if parts[1] != "*" else None, parts[2])
        elif len(parts) > 3:
            return (parts[0], ":".join(parts[1:-1]), parts[-1])
        else:
            raise ValueError(f"Invalid permission string: {permission_string}")
    
    @staticmethod
    def build_permission(
        resource: str,
        action: str,
        sub_resource: Optional[str] = None
    ) -> str:
        """Build a permission string from components."""
        if sub_resource:
            return f"{resource}:{sub_resource}:{action}"
        return f"{resource}:*:{action}"
    
    @staticmethod
    def matches_permission(
        user_permission: str,
        required_permission: str
    ) -> bool:
        """
        Check if a user permission matches a required permission.
        
        Supports wildcards (*) for resource, sub_resource, and action.
        """
        user_parts = user_permission.split(":")
        req_parts = required_permission.split(":")
        
        while len(user_parts) < 3:
            user_parts.insert(1, "*")
        while len(req_parts) < 3:
            req_parts.insert(1, "*")
        
        for user_part, req_part in zip(user_parts, req_parts):
            if user_part == "*":
                continue
            if user_part != req_part:
                return False
        
        return True
    
    def evaluate_conditions(
        self,
        permission_name: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        Evaluate conditions for a permission.
        
        Returns True if all conditions are met or no conditions exist.
        """
        perm = self.get_permission(permission_name)
        if not perm or not perm.conditions:
            return True
        
        policy = PolicyDocument.from_dict(perm.conditions)
        return policy.evaluate(context)
    
    def get_resources(self) -> List[str]:
        """Get all unique resource types."""
        resources = self.session.query(Permission.resource).distinct().all()
        return sorted([r[0] for r in resources])
    
    def get_actions(self) -> List[str]:
        """Get all unique action types."""
        actions = self.session.query(Permission.action).distinct().all()
        return sorted([a[0] for a in actions])


_permission_manager: Optional[PermissionManager] = None


def get_permission_manager(session: Session) -> PermissionManager:
    """Get or create the permission manager singleton."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager(session)
    return _permission_manager
