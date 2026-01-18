"""
GRACE Zero-Trust Policy Engine

Implements policy-as-code with:
- Policy definitions in JSON/YAML
- Conditional access policies
- Risk-based access decisions
- Policy versioning and audit trail
- Real-time policy evaluation

All policy decisions are logged to the immutable audit system.
"""

import hashlib
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Union

import yaml

logger = logging.getLogger(__name__)


class PolicyAction(str, Enum):
    """Actions a policy can take."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_MFA = "require_mfa"
    REQUIRE_STEP_UP = "require_step_up"
    RATE_LIMIT = "rate_limit"
    LOG_ONLY = "log_only"
    NOTIFY = "notify"
    QUARANTINE = "quarantine"


class PolicyConditionOperator(str, Enum):
    """Operators for policy conditions."""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    MATCHES = "matches"  # Regex
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"


@dataclass
class PolicyCondition:
    """A condition for policy evaluation."""
    field: str  # e.g., "context.risk_score", "user.roles"
    operator: PolicyConditionOperator
    value: Any = None
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate the condition against the context."""
        # Navigate to the field value
        field_value = self._get_field_value(context, self.field)
        
        # Apply operator
        if self.operator == PolicyConditionOperator.EQUALS:
            return field_value == self.value
        elif self.operator == PolicyConditionOperator.NOT_EQUALS:
            return field_value != self.value
        elif self.operator == PolicyConditionOperator.CONTAINS:
            return self.value in field_value if field_value else False
        elif self.operator == PolicyConditionOperator.NOT_CONTAINS:
            return self.value not in field_value if field_value else True
        elif self.operator == PolicyConditionOperator.IN:
            return field_value in self.value if self.value else False
        elif self.operator == PolicyConditionOperator.NOT_IN:
            return field_value not in self.value if self.value else True
        elif self.operator == PolicyConditionOperator.GREATER_THAN:
            return field_value > self.value if field_value is not None else False
        elif self.operator == PolicyConditionOperator.LESS_THAN:
            return field_value < self.value if field_value is not None else False
        elif self.operator == PolicyConditionOperator.GREATER_THAN_OR_EQUAL:
            return field_value >= self.value if field_value is not None else False
        elif self.operator == PolicyConditionOperator.LESS_THAN_OR_EQUAL:
            return field_value <= self.value if field_value is not None else False
        elif self.operator == PolicyConditionOperator.MATCHES:
            if field_value is None:
                return False
            return bool(re.match(self.value, str(field_value)))
        elif self.operator == PolicyConditionOperator.EXISTS:
            return field_value is not None
        elif self.operator == PolicyConditionOperator.NOT_EXISTS:
            return field_value is None
        elif self.operator == PolicyConditionOperator.IS_TRUE:
            return bool(field_value)
        elif self.operator == PolicyConditionOperator.IS_FALSE:
            return not bool(field_value)
        
        return False
    
    def _get_field_value(self, context: Dict[str, Any], field_path: str) -> Any:
        """Get nested field value using dot notation."""
        parts = field_path.split(".")
        value = context
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None
        
        return value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "field": self.field,
            "operator": self.operator.value,
            "value": self.value,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PolicyCondition":
        """Create from dictionary."""
        return cls(
            field=data["field"],
            operator=PolicyConditionOperator(data["operator"]),
            value=data.get("value"),
        )


@dataclass
class Policy:
    """A zero-trust access policy."""
    policy_id: str
    name: str
    description: str
    enabled: bool = True
    priority: int = 100  # Lower number = higher priority
    
    # Conditions (all must match for policy to apply)
    conditions: List[PolicyCondition] = field(default_factory=list)
    
    # Actions to take when policy matches
    action: PolicyAction = PolicyAction.ALLOW
    action_params: Dict[str, Any] = field(default_factory=dict)
    
    # Scope
    resources: List[str] = field(default_factory=list)  # Resource patterns
    roles: List[str] = field(default_factory=list)  # Applicable roles
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    version: int = 1
    tags: List[str] = field(default_factory=list)
    
    def matches(self, context: Dict[str, Any], resource: Optional[str] = None) -> bool:
        """Check if policy matches the context."""
        # Check if policy is enabled
        if not self.enabled:
            return False
        
        # Check resource scope
        if self.resources and resource:
            if not self._matches_resource(resource):
                return False
        
        # Check role scope
        if self.roles:
            user_roles = context.get("user", {}).get("roles", [])
            if not any(role in self.roles for role in user_roles):
                return False
        
        # Evaluate all conditions (AND logic)
        return all(condition.evaluate(context) for condition in self.conditions)
    
    def _matches_resource(self, resource: str) -> bool:
        """Check if resource matches any pattern."""
        for pattern in self.resources:
            if pattern == "*":
                return True
            if pattern.endswith("*"):
                if resource.startswith(pattern[:-1]):
                    return True
            elif pattern == resource:
                return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.priority,
            "conditions": [c.to_dict() for c in self.conditions],
            "action": self.action.value,
            "action_params": self.action_params,
            "resources": self.resources,
            "roles": self.roles,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "version": self.version,
            "tags": self.tags,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Policy":
        """Create from dictionary."""
        return cls(
            policy_id=data.get("policy_id", str(uuid.uuid4())),
            name=data["name"],
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 100),
            conditions=[PolicyCondition.from_dict(c) for c in data.get("conditions", [])],
            action=PolicyAction(data.get("action", "allow")),
            action_params=data.get("action_params", {}),
            resources=data.get("resources", []),
            roles=data.get("roles", []),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.utcnow(),
            created_by=data.get("created_by"),
            version=data.get("version", 1),
            tags=data.get("tags", []),
        )


@dataclass
class PolicyVersion:
    """A version of a policy for audit trail."""
    version_id: str
    policy_id: str
    version: int
    policy_data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    change_reason: Optional[str] = None
    
    def compute_hash(self) -> str:
        """Compute hash of policy data."""
        data_str = json.dumps(self.policy_data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()


@dataclass
class PolicyEvaluationResult:
    """Result of policy evaluation."""
    allowed: bool
    action: PolicyAction
    matched_policies: List[str]
    denied_by: Optional[str] = None
    required_actions: List[str] = field(default_factory=list)
    action_params: Dict[str, Any] = field(default_factory=dict)
    evaluation_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "allowed": self.allowed,
            "action": self.action.value,
            "matched_policies": self.matched_policies,
            "denied_by": self.denied_by,
            "required_actions": self.required_actions,
            "action_params": self.action_params,
            "evaluation_time_ms": self.evaluation_time_ms,
        }


class PolicyEngine:
    """
    Zero-Trust Policy Engine
    
    Evaluates policies against security context to make
    risk-based access decisions.
    """
    
    def __init__(
        self,
        policies_path: Optional[Path] = None,
        default_action: PolicyAction = PolicyAction.DENY,
    ):
        self.default_action = default_action
        self.policies_path = policies_path
        
        # Policy storage
        self._policies: Dict[str, Policy] = {}
        self._policy_versions: Dict[str, List[PolicyVersion]] = {}
        
        # Custom condition evaluators
        self._custom_evaluators: Dict[str, Callable] = {}
        
        # Load default policies
        self._load_default_policies()
        
        # Load from file if path provided
        if policies_path and policies_path.exists():
            self.load_policies_from_file(policies_path)
        
        logger.info(f"[ZERO-TRUST-POLICY] Policy engine initialized with {len(self._policies)} policies")
    
    def evaluate(
        self,
        context: Dict[str, Any],
        resource: Optional[str] = None,
        action: Optional[str] = None,
    ) -> PolicyEvaluationResult:
        """
        Evaluate all policies against the context.
        
        Returns the result with the action to take.
        """
        import time
        start_time = time.perf_counter()
        
        matched_policies = []
        final_action = self.default_action
        denied_by = None
        required_actions = []
        action_params = {}
        
        # Get applicable policies sorted by priority
        applicable_policies = sorted(
            [p for p in self._policies.values() if p.enabled],
            key=lambda p: p.priority,
        )
        
        for policy in applicable_policies:
            if policy.matches(context, resource):
                matched_policies.append(policy.policy_id)
                
                # Handle action based on policy
                if policy.action == PolicyAction.DENY:
                    final_action = PolicyAction.DENY
                    denied_by = policy.policy_id
                    break  # Deny takes precedence
                elif policy.action == PolicyAction.REQUIRE_MFA:
                    required_actions.append("mfa")
                    action_params.update(policy.action_params)
                elif policy.action == PolicyAction.REQUIRE_STEP_UP:
                    required_actions.append("step_up")
                    action_params.update(policy.action_params)
                elif policy.action == PolicyAction.RATE_LIMIT:
                    required_actions.append("rate_limit")
                    action_params.update(policy.action_params)
                elif policy.action == PolicyAction.QUARANTINE:
                    final_action = PolicyAction.QUARANTINE
                    denied_by = policy.policy_id
                elif policy.action == PolicyAction.ALLOW:
                    final_action = PolicyAction.ALLOW
        
        # Determine if allowed
        allowed = final_action in [PolicyAction.ALLOW, PolicyAction.LOG_ONLY]
        
        evaluation_time_ms = (time.perf_counter() - start_time) * 1000
        
        result = PolicyEvaluationResult(
            allowed=allowed,
            action=final_action,
            matched_policies=matched_policies,
            denied_by=denied_by,
            required_actions=required_actions,
            action_params=action_params,
            evaluation_time_ms=evaluation_time_ms,
        )
        
        # Audit the decision
        self._audit_decision(context, resource, result)
        
        return result
    
    def add_policy(
        self,
        policy: Policy,
        created_by: Optional[str] = None,
        change_reason: Optional[str] = None,
    ):
        """Add or update a policy."""
        existing = self._policies.get(policy.policy_id)
        
        if existing:
            # Create new version
            policy.version = existing.version + 1
            policy.updated_at = datetime.utcnow()
        
        policy.created_by = created_by or policy.created_by
        
        # Store policy
        self._policies[policy.policy_id] = policy
        
        # Store version for audit trail
        self._add_version(policy, created_by, change_reason)
        
        logger.info(f"[ZERO-TRUST-POLICY] Policy added/updated: {policy.name} (v{policy.version})")
    
    def remove_policy(self, policy_id: str, removed_by: Optional[str] = None):
        """Remove a policy (soft delete by disabling)."""
        policy = self._policies.get(policy_id)
        if policy:
            policy.enabled = False
            policy.updated_at = datetime.utcnow()
            self._add_version(policy, removed_by, "Policy disabled")
            logger.info(f"[ZERO-TRUST-POLICY] Policy disabled: {policy.name}")
    
    def get_policy(self, policy_id: str) -> Optional[Policy]:
        """Get a policy by ID."""
        return self._policies.get(policy_id)
    
    def list_policies(
        self,
        enabled_only: bool = True,
        tags: Optional[List[str]] = None,
    ) -> List[Policy]:
        """List all policies."""
        policies = list(self._policies.values())
        
        if enabled_only:
            policies = [p for p in policies if p.enabled]
        
        if tags:
            policies = [p for p in policies if any(t in p.tags for t in tags)]
        
        return sorted(policies, key=lambda p: p.priority)
    
    def get_policy_versions(self, policy_id: str) -> List[PolicyVersion]:
        """Get version history for a policy."""
        return self._policy_versions.get(policy_id, [])
    
    def load_policies_from_file(self, path: Path):
        """Load policies from JSON or YAML file."""
        try:
            with open(path, "r") as f:
                if path.suffix in [".yaml", ".yml"]:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            policies = data.get("policies", [])
            for policy_data in policies:
                policy = Policy.from_dict(policy_data)
                self._policies[policy.policy_id] = policy
            
            logger.info(f"[ZERO-TRUST-POLICY] Loaded {len(policies)} policies from {path}")
        except Exception as e:
            logger.error(f"[ZERO-TRUST-POLICY] Failed to load policies: {e}")
    
    def save_policies_to_file(self, path: Path):
        """Save policies to file."""
        try:
            data = {
                "version": "1.0",
                "updated_at": datetime.utcnow().isoformat(),
                "policies": [p.to_dict() for p in self._policies.values()],
            }
            
            with open(path, "w") as f:
                if path.suffix in [".yaml", ".yml"]:
                    yaml.dump(data, f, default_flow_style=False)
                else:
                    json.dump(data, f, indent=2, default=str)
            
            logger.info(f"[ZERO-TRUST-POLICY] Saved {len(self._policies)} policies to {path}")
        except Exception as e:
            logger.error(f"[ZERO-TRUST-POLICY] Failed to save policies: {e}")
    
    def register_custom_evaluator(self, name: str, evaluator: Callable[[Dict[str, Any]], bool]):
        """Register a custom condition evaluator."""
        self._custom_evaluators[name] = evaluator
    
    def _load_default_policies(self):
        """Load default security policies."""
        default_policies = [
            # Block high-risk requests
            Policy(
                policy_id="default-block-high-risk",
                name="Block High Risk",
                description="Block requests with critical risk score",
                priority=1,
                conditions=[
                    PolicyCondition(
                        field="context.risk_score",
                        operator=PolicyConditionOperator.GREATER_THAN,
                        value=0.9,
                    ),
                ],
                action=PolicyAction.DENY,
                tags=["default", "risk"],
            ),
            # Require MFA for high-risk
            Policy(
                policy_id="default-mfa-high-risk",
                name="Require MFA for High Risk",
                description="Require MFA for high risk requests",
                priority=10,
                conditions=[
                    PolicyCondition(
                        field="context.risk_score",
                        operator=PolicyConditionOperator.GREATER_THAN,
                        value=0.6,
                    ),
                ],
                action=PolicyAction.REQUIRE_MFA,
                tags=["default", "mfa", "risk"],
            ),
            # Rate limit unauthenticated requests
            Policy(
                policy_id="default-rate-limit-unauth",
                name="Rate Limit Unauthenticated",
                description="Rate limit unauthenticated requests",
                priority=20,
                conditions=[
                    PolicyCondition(
                        field="context.is_authenticated",
                        operator=PolicyConditionOperator.IS_FALSE,
                    ),
                    PolicyCondition(
                        field="context.requests_in_window",
                        operator=PolicyConditionOperator.GREATER_THAN,
                        value=50,
                    ),
                ],
                action=PolicyAction.RATE_LIMIT,
                action_params={"requests_per_minute": 10},
                tags=["default", "rate-limit"],
            ),
            # Block Tor traffic for sensitive resources
            Policy(
                policy_id="default-block-tor-sensitive",
                name="Block Tor for Sensitive",
                description="Block Tor exit nodes from sensitive resources",
                priority=5,
                conditions=[
                    PolicyCondition(
                        field="context.geo_location.is_tor",
                        operator=PolicyConditionOperator.IS_TRUE,
                    ),
                ],
                action=PolicyAction.DENY,
                resources=["/api/admin/*", "/api/secrets/*", "/api/config/*"],
                tags=["default", "tor", "sensitive"],
            ),
            # Allow authenticated users by default
            Policy(
                policy_id="default-allow-authenticated",
                name="Allow Authenticated Users",
                description="Allow authenticated users with low risk",
                priority=100,
                conditions=[
                    PolicyCondition(
                        field="context.is_authenticated",
                        operator=PolicyConditionOperator.IS_TRUE,
                    ),
                    PolicyCondition(
                        field="context.risk_score",
                        operator=PolicyConditionOperator.LESS_THAN,
                        value=0.6,
                    ),
                ],
                action=PolicyAction.ALLOW,
                tags=["default", "allow"],
            ),
        ]
        
        for policy in default_policies:
            self._policies[policy.policy_id] = policy
    
    def _add_version(
        self,
        policy: Policy,
        created_by: Optional[str],
        change_reason: Optional[str],
    ):
        """Add a version entry for audit trail."""
        version = PolicyVersion(
            version_id=str(uuid.uuid4()),
            policy_id=policy.policy_id,
            version=policy.version,
            policy_data=policy.to_dict(),
            created_by=created_by,
            change_reason=change_reason,
        )
        
        if policy.policy_id not in self._policy_versions:
            self._policy_versions[policy.policy_id] = []
        
        self._policy_versions[policy.policy_id].append(version)
        
        # Audit the version
        self._audit_policy_change(policy, version)
    
    def _audit_decision(
        self,
        context: Dict[str, Any],
        resource: Optional[str],
        result: PolicyEvaluationResult,
    ):
        """Audit policy decision to immutable log."""
        try:
            from genesis.immutable_audit_storage import (
                ImmutableAuditType,
                get_immutable_audit_storage,
            )
            from database.session_manager import get_db_session
            
            with get_db_session() as session:
                storage = get_immutable_audit_storage(session)
                storage.record(
                    audit_type=ImmutableAuditType.ACCESS_DENIED if not result.allowed else ImmutableAuditType.DATA_ACCESS,
                    action_description=f"Policy evaluation: {result.action.value}",
                    actor_type="security",
                    actor_id="zero-trust-policy",
                    session_id=context.get("session_id"),
                    severity="warning" if not result.allowed else "info",
                    component="zero_trust.policy_engine",
                    context={
                        "resource": resource,
                        "allowed": result.allowed,
                        "action": result.action.value,
                        "matched_policies": result.matched_policies,
                        "denied_by": result.denied_by,
                        "evaluation_time_ms": result.evaluation_time_ms,
                    },
                )
        except Exception as e:
            logger.warning(f"[ZERO-TRUST-POLICY] Audit logging failed: {e}")
    
    def _audit_policy_change(self, policy: Policy, version: PolicyVersion):
        """Audit policy changes to immutable log."""
        try:
            from genesis.immutable_audit_storage import (
                ImmutableAuditType,
                get_immutable_audit_storage,
            )
            from database.session_manager import get_db_session
            
            with get_db_session() as session:
                storage = get_immutable_audit_storage(session)
                storage.record(
                    audit_type=ImmutableAuditType.SYSTEM_CONFIG_CHANGE,
                    action_description=f"Policy updated: {policy.name} v{policy.version}",
                    actor_type="admin",
                    actor_id=version.created_by or "system",
                    severity="info",
                    component="zero_trust.policy_engine",
                    reason=version.change_reason,
                    context={
                        "policy_id": policy.policy_id,
                        "version": policy.version,
                        "policy_hash": version.compute_hash(),
                    },
                )
        except Exception as e:
            logger.warning(f"[ZERO-TRUST-POLICY] Audit logging failed: {e}")


# Singleton instance
_policy_engine: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    """Get the policy engine singleton."""
    global _policy_engine
    if _policy_engine is None:
        _policy_engine = PolicyEngine()
    return _policy_engine
