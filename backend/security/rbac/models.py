"""
RBAC Data Models for GRACE.

Defines the core data structures for Role-Based Access Control:
- Role: Named collection of permissions with optional inheritance
- Permission: Fine-grained access control definition
- UserRole: Association between Genesis IDs and roles
- PolicyDocument: Attribute-based conditions for context-aware access
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, Set
from enum import Enum
from dataclasses import dataclass, field, asdict
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text, Boolean, Index, ForeignKey
from sqlalchemy.orm import relationship
from database.base import BaseModel


class ResourceType(str, Enum):
    """Types of resources that can be protected."""
    CODE = "code"
    KNOWLEDGE_BASE = "knowledge_base"
    AUDIT = "audit"
    GENESIS_KEYS = "genesis_keys"
    SYSTEM = "system"
    API = "api"
    USERS = "users"
    SECRETS = "secrets"
    ROLES = "roles"
    PERMISSIONS = "permissions"
    CONFIG = "config"
    MODELS = "models"
    PIPELINES = "pipelines"


class ActionType(str, Enum):
    """Types of actions that can be performed on resources."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    APPROVE = "approve"
    EXPORT = "export"
    IMPORT = "import"
    ADMIN = "admin"
    LIST = "list"


class ConditionOperator(str, Enum):
    """Operators for attribute-based conditions."""
    EQUALS = "eq"
    NOT_EQUALS = "neq"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    CONTAINS = "contains"
    IN = "in"
    NOT_IN = "not_in"
    MATCHES = "matches"
    BETWEEN = "between"


@dataclass
class Condition:
    """
    A single condition for attribute-based access control.
    
    Examples:
        - Time-based: {"attribute": "time.hour", "operator": "between", "value": [9, 17]}
        - IP-based: {"attribute": "client.ip", "operator": "in", "value": ["10.0.0.0/8"]}
        - Owner-based: {"attribute": "resource.owner", "operator": "eq", "value": "${user.id}"}
    """
    attribute: str
    operator: ConditionOperator
    value: Any
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "attribute": self.attribute,
            "operator": self.operator.value if isinstance(self.operator, ConditionOperator) else self.operator,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Condition":
        return cls(
            attribute=data["attribute"],
            operator=ConditionOperator(data["operator"]) if isinstance(data["operator"], str) else data["operator"],
            value=data["value"]
        )


@dataclass
class PolicyDocument:
    """
    Policy document for attribute-based access control conditions.
    
    Combines multiple conditions with AND/OR logic.
    """
    conditions: List[Condition] = field(default_factory=list)
    logic: str = "AND"
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "conditions": [c.to_dict() for c in self.conditions],
            "logic": self.logic,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolicyDocument":
        return cls(
            conditions=[Condition.from_dict(c) for c in data.get("conditions", [])],
            logic=data.get("logic", "AND"),
            description=data.get("description")
        )
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate the policy against a context."""
        if not self.conditions:
            return True
        
        results = []
        for condition in self.conditions:
            result = self._evaluate_condition(condition, context)
            results.append(result)
        
        if self.logic == "AND":
            return all(results)
        elif self.logic == "OR":
            return any(results)
        return False
    
    def _evaluate_condition(self, condition: Condition, context: Dict[str, Any]) -> bool:
        """Evaluate a single condition."""
        attr_value = self._get_nested_value(context, condition.attribute)
        compare_value = condition.value
        
        if isinstance(compare_value, str) and compare_value.startswith("${"):
            ref = compare_value[2:-1]
            compare_value = self._get_nested_value(context, ref)
        
        op = condition.operator
        if op == ConditionOperator.EQUALS:
            return attr_value == compare_value
        elif op == ConditionOperator.NOT_EQUALS:
            return attr_value != compare_value
        elif op == ConditionOperator.GREATER_THAN:
            return attr_value > compare_value if attr_value is not None else False
        elif op == ConditionOperator.LESS_THAN:
            return attr_value < compare_value if attr_value is not None else False
        elif op == ConditionOperator.CONTAINS:
            return compare_value in attr_value if attr_value else False
        elif op == ConditionOperator.IN:
            return attr_value in compare_value if compare_value else False
        elif op == ConditionOperator.NOT_IN:
            return attr_value not in compare_value if compare_value else True
        elif op == ConditionOperator.BETWEEN:
            if attr_value is None or len(compare_value) != 2:
                return False
            return compare_value[0] <= attr_value <= compare_value[1]
        elif op == ConditionOperator.MATCHES:
            import re
            return bool(re.match(compare_value, str(attr_value))) if attr_value else False
        
        return False
    
    def _get_nested_value(self, data: Dict, path: str) -> Any:
        """Get a nested value from a dictionary using dot notation."""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value


class Permission(BaseModel):
    """
    Permission definition for fine-grained access control.
    
    Format: resource:sub-resource:action
    Examples:
        - code:healing:approve
        - audit:export:sensitive
        - genesis_keys:*:read
        - system:config:update
    """
    __tablename__ = "rbac_permissions"
    
    permission_id = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    resource = Column(String(100), nullable=False, index=True)
    sub_resource = Column(String(100), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    
    conditions = Column(JSON, nullable=True)
    
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_rbac_perm_resource_action', 'resource', 'action'),
        Index('idx_rbac_perm_full', 'resource', 'sub_resource', 'action'),
    )
    
    def __repr__(self):
        return f"<Permission({self.name}: {self.resource}:{self.sub_resource or '*'}:{self.action})>"
    
    @property
    def permission_string(self) -> str:
        """Get the full permission string."""
        if self.sub_resource:
            return f"{self.resource}:{self.sub_resource}:{self.action}"
        return f"{self.resource}:*:{self.action}"
    
    def matches(self, resource: str, action: str, sub_resource: Optional[str] = None) -> bool:
        """Check if this permission matches a request."""
        if self.resource != resource and self.resource != "*":
            return False
        
        if self.action != action and self.action != "*":
            return False
        
        if self.sub_resource and sub_resource:
            if self.sub_resource != sub_resource and self.sub_resource != "*":
                return False
        
        return True
    
    def get_policy(self) -> Optional[PolicyDocument]:
        """Get the policy document if conditions exist."""
        if self.conditions:
            return PolicyDocument.from_dict(self.conditions)
        return None


class Role(BaseModel):
    """
    Role definition with hierarchical inheritance.
    
    Roles can inherit permissions from parent roles, enabling
    a hierarchical permission structure.
    """
    __tablename__ = "rbac_roles"
    
    role_id = Column(String(64), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    display_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    
    parent_role_id = Column(String(64), ForeignKey("rbac_roles.role_id"), nullable=True, index=True)
    
    permissions = Column(JSON, default=list)
    
    is_system = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)
    
    metadata_ = Column("metadata", JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(64), nullable=True)
    
    __table_args__ = (
        Index('idx_rbac_role_parent', 'parent_role_id'),
        Index('idx_rbac_role_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Role({self.name}, permissions={len(self.permissions or [])})>"
    
    def has_permission(self, permission_string: str) -> bool:
        """Check if this role directly has a permission."""
        if not self.permissions:
            return False
        
        parts = permission_string.split(":")
        if len(parts) < 2:
            return False
        
        resource = parts[0]
        action = parts[-1]
        sub_resource = parts[1] if len(parts) > 2 else None
        
        for perm in self.permissions:
            if isinstance(perm, str):
                perm_parts = perm.split(":")
                perm_resource = perm_parts[0]
                perm_action = perm_parts[-1]
                perm_sub = perm_parts[1] if len(perm_parts) > 2 else None
                
                if perm_resource == "*" or perm_resource == resource:
                    if perm_action == "*" or perm_action == action:
                        if perm_sub is None or perm_sub == "*" or perm_sub == sub_resource:
                            return True
        
        return False


class UserRole(BaseModel):
    """
    Association between Genesis IDs and roles.
    
    Supports temporal access with expiration and tracks
    who granted the role and when.
    """
    __tablename__ = "rbac_user_roles"
    
    assignment_id = Column(String(64), nullable=False, unique=True, index=True)
    genesis_id = Column(String(64), nullable=False, index=True)
    role_id = Column(String(64), ForeignKey("rbac_roles.role_id"), nullable=False, index=True)
    
    granted_by = Column(String(64), nullable=True)
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True, index=True)
    
    is_active = Column(Boolean, default=True, index=True)
    reason = Column(Text, nullable=True)
    
    scope = Column(JSON, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict)
    
    revoked_at = Column(DateTime, nullable=True)
    revoked_by = Column(String(64), nullable=True)
    revoke_reason = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_rbac_user_role', 'genesis_id', 'role_id'),
        Index('idx_rbac_user_active', 'genesis_id', 'is_active'),
        Index('idx_rbac_user_expiry', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<UserRole(genesis_id={self.genesis_id}, role_id={self.role_id})>"
    
    @property
    def is_expired(self) -> bool:
        """Check if the role assignment has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if the role assignment is currently valid."""
        return self.is_active and not self.is_expired


@dataclass
class PermissionCheck:
    """Result of a permission check."""
    allowed: bool
    permission: str
    resource: str
    action: str
    genesis_id: str
    roles: List[str]
    reason: str
    conditions_met: bool = True
    checked_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "permission": self.permission,
            "resource": self.resource,
            "action": self.action,
            "genesis_id": self.genesis_id,
            "roles": self.roles,
            "reason": self.reason,
            "conditions_met": self.conditions_met,
            "checked_at": self.checked_at.isoformat()
        }


@dataclass
class AuthorizationContext:
    """Context for authorization decisions."""
    genesis_id: str
    session_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    resource_owner: Optional[str] = None
    resource_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    custom_attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_evaluation_context(self) -> Dict[str, Any]:
        """Convert to a context dictionary for policy evaluation."""
        return {
            "user": {
                "id": self.genesis_id,
                "session_id": self.session_id
            },
            "client": {
                "ip": self.client_ip,
                "user_agent": self.user_agent
            },
            "request": {
                "path": self.request_path,
                "method": self.request_method
            },
            "resource": {
                "owner": self.resource_owner,
                "id": self.resource_id
            },
            "time": {
                "hour": self.timestamp.hour,
                "day": self.timestamp.weekday(),
                "timestamp": self.timestamp.isoformat()
            },
            **self.custom_attributes
        }
