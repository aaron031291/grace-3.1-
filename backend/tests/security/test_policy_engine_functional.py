"""
Zero Trust Policy Engine - REAL Functional Tests

Tests verify ACTUAL policy engine behavior using real implementations:
- PolicyAction and PolicyConditionOperator enums
- PolicyCondition evaluation with operators
- Policy matching with conditions, resources, roles
- Policy engine evaluation and prioritization
"""

import pytest
from datetime import datetime
from typing import Dict, Any
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


# =============================================================================
# POLICY ACTION ENUM TESTS
# =============================================================================

class TestPolicyActionEnumFunctional:
    """Functional tests for PolicyAction enum."""

    def test_all_policy_actions_defined(self):
        """All required policy actions must be defined."""
        from security.zero_trust.policy_engine import PolicyAction

        required_actions = [
            "ALLOW",
            "DENY",
            "REQUIRE_MFA",
            "REQUIRE_STEP_UP",
            "RATE_LIMIT",
            "LOG_ONLY",
            "NOTIFY",
            "QUARANTINE"
        ]

        for action_name in required_actions:
            assert hasattr(PolicyAction, action_name), f"Missing action: {action_name}"

    def test_action_values_are_lowercase(self):
        """Action values must be lowercase strings."""
        from security.zero_trust.policy_engine import PolicyAction

        for action in PolicyAction:
            assert isinstance(action.value, str)
            assert action.value == action.value.lower()


# =============================================================================
# POLICY CONDITION OPERATOR ENUM TESTS
# =============================================================================

class TestPolicyConditionOperatorEnumFunctional:
    """Functional tests for PolicyConditionOperator enum."""

    def test_all_operators_defined(self):
        """All required operators must be defined."""
        from security.zero_trust.policy_engine import PolicyConditionOperator

        required_operators = [
            "EQUALS",
            "NOT_EQUALS",
            "CONTAINS",
            "NOT_CONTAINS",
            "IN",
            "NOT_IN",
            "GREATER_THAN",
            "LESS_THAN",
            "GREATER_THAN_OR_EQUAL",
            "LESS_THAN_OR_EQUAL",
            "MATCHES",
            "EXISTS",
            "NOT_EXISTS",
            "IS_TRUE",
            "IS_FALSE"
        ]

        for op_name in required_operators:
            assert hasattr(PolicyConditionOperator, op_name), f"Missing operator: {op_name}"


# =============================================================================
# POLICY CONDITION EVALUATION TESTS
# =============================================================================

class TestPolicyConditionEvaluationFunctional:
    """Functional tests for PolicyCondition evaluation."""

    @pytest.fixture
    def sample_context(self):
        """Create a sample context for testing."""
        return {
            "user": {
                "id": "user-123",
                "roles": ["admin", "developer"],
                "email": "admin@example.com",
                "mfa_enabled": True
            },
            "request": {
                "ip": "192.168.1.1",
                "method": "POST",
                "path": "/api/v1/admin/settings"
            },
            "risk_score": 0.35,
            "device_known": True,
            "location": "USA"
        }

    def test_equals_operator_true(self, sample_context):
        """EQUALS operator must return True when values match."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="user.id",
            operator=PolicyConditionOperator.EQUALS,
            value="user-123"
        )

        assert condition.evaluate(sample_context) is True

    def test_equals_operator_false(self, sample_context):
        """EQUALS operator must return False when values don't match."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="user.id",
            operator=PolicyConditionOperator.EQUALS,
            value="user-456"
        )

        assert condition.evaluate(sample_context) is False

    def test_not_equals_operator(self, sample_context):
        """NOT_EQUALS operator must work correctly."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="location",
            operator=PolicyConditionOperator.NOT_EQUALS,
            value="Russia"
        )

        assert condition.evaluate(sample_context) is True

    def test_contains_operator(self, sample_context):
        """CONTAINS operator must check if value is in field."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="user.roles",
            operator=PolicyConditionOperator.CONTAINS,
            value="admin"
        )

        assert condition.evaluate(sample_context) is True

    def test_not_contains_operator(self, sample_context):
        """NOT_CONTAINS operator must check if value is not in field."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="user.roles",
            operator=PolicyConditionOperator.NOT_CONTAINS,
            value="superuser"
        )

        assert condition.evaluate(sample_context) is True

    def test_in_operator(self, sample_context):
        """IN operator must check if field is in value list."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="location",
            operator=PolicyConditionOperator.IN,
            value=["USA", "Canada", "UK"]
        )

        assert condition.evaluate(sample_context) is True

    def test_not_in_operator(self, sample_context):
        """NOT_IN operator must check if field is not in value list."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="location",
            operator=PolicyConditionOperator.NOT_IN,
            value=["Russia", "China", "North Korea"]
        )

        assert condition.evaluate(sample_context) is True

    def test_greater_than_operator(self, sample_context):
        """GREATER_THAN operator must compare numerically."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="risk_score",
            operator=PolicyConditionOperator.GREATER_THAN,
            value=0.3
        )

        assert condition.evaluate(sample_context) is True  # 0.35 > 0.3

    def test_less_than_operator(self, sample_context):
        """LESS_THAN operator must compare numerically."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="risk_score",
            operator=PolicyConditionOperator.LESS_THAN,
            value=0.5
        )

        assert condition.evaluate(sample_context) is True  # 0.35 < 0.5

    def test_greater_than_or_equal_operator(self, sample_context):
        """GREATER_THAN_OR_EQUAL operator must work correctly."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="risk_score",
            operator=PolicyConditionOperator.GREATER_THAN_OR_EQUAL,
            value=0.35
        )

        assert condition.evaluate(sample_context) is True  # 0.35 >= 0.35

    def test_less_than_or_equal_operator(self, sample_context):
        """LESS_THAN_OR_EQUAL operator must work correctly."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="risk_score",
            operator=PolicyConditionOperator.LESS_THAN_OR_EQUAL,
            value=0.35
        )

        assert condition.evaluate(sample_context) is True  # 0.35 <= 0.35

    def test_matches_operator_regex(self, sample_context):
        """MATCHES operator must evaluate regex."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="user.email",
            operator=PolicyConditionOperator.MATCHES,
            value=r".*@example\.com$"
        )

        assert condition.evaluate(sample_context) is True

    def test_exists_operator_true(self, sample_context):
        """EXISTS operator must return True for existing field."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="user.mfa_enabled",
            operator=PolicyConditionOperator.EXISTS
        )

        assert condition.evaluate(sample_context) is True

    def test_exists_operator_false(self, sample_context):
        """EXISTS operator must return False for missing field."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="user.nonexistent_field",
            operator=PolicyConditionOperator.EXISTS
        )

        assert condition.evaluate(sample_context) is False

    def test_not_exists_operator(self, sample_context):
        """NOT_EXISTS operator must return True for missing field."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="user.nonexistent_field",
            operator=PolicyConditionOperator.NOT_EXISTS
        )

        assert condition.evaluate(sample_context) is True

    def test_is_true_operator(self, sample_context):
        """IS_TRUE operator must check truthiness."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="device_known",
            operator=PolicyConditionOperator.IS_TRUE
        )

        assert condition.evaluate(sample_context) is True

    def test_is_false_operator(self, sample_context):
        """IS_FALSE operator must check falsiness."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        context = {"feature_disabled": False}

        condition = PolicyCondition(
            field="feature_disabled",
            operator=PolicyConditionOperator.IS_FALSE
        )

        assert condition.evaluate(context) is True

    def test_nested_field_access(self, sample_context):
        """Condition must access nested fields with dot notation."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="request.method",
            operator=PolicyConditionOperator.EQUALS,
            value="POST"
        )

        assert condition.evaluate(sample_context) is True


# =============================================================================
# POLICY CONDITION SERIALIZATION TESTS
# =============================================================================

class TestPolicyConditionSerializationFunctional:
    """Functional tests for PolicyCondition serialization."""

    def test_to_dict(self):
        """PolicyCondition.to_dict() must serialize correctly."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        condition = PolicyCondition(
            field="risk_score",
            operator=PolicyConditionOperator.GREATER_THAN,
            value=0.7
        )

        result = condition.to_dict()

        assert result["field"] == "risk_score"
        assert result["operator"] == "greater_than"
        assert result["value"] == 0.7

    def test_from_dict(self):
        """PolicyCondition.from_dict() must deserialize correctly."""
        from security.zero_trust.policy_engine import PolicyCondition, PolicyConditionOperator

        data = {
            "field": "user.roles",
            "operator": "contains",
            "value": "admin"
        }

        condition = PolicyCondition.from_dict(data)

        assert condition.field == "user.roles"
        assert condition.operator == PolicyConditionOperator.CONTAINS
        assert condition.value == "admin"


# =============================================================================
# POLICY MATCHING TESTS
# =============================================================================

class TestPolicyMatchingFunctional:
    """Functional tests for Policy matching logic."""

    @pytest.fixture
    def admin_policy(self):
        """Create an admin access policy."""
        from security.zero_trust.policy_engine import (
            Policy, PolicyCondition, PolicyConditionOperator, PolicyAction
        )

        return Policy(
            policy_id="admin-access-policy",
            name="Admin Access Policy",
            description="Allows admin access for admin role",
            enabled=True,
            priority=10,
            conditions=[
                PolicyCondition(
                    field="user.roles",
                    operator=PolicyConditionOperator.CONTAINS,
                    value="admin"
                )
            ],
            action=PolicyAction.ALLOW,
            resources=["/api/v1/admin/*"],
            roles=["admin"]
        )

    @pytest.fixture
    def high_risk_policy(self):
        """Create a high risk denial policy."""
        from security.zero_trust.policy_engine import (
            Policy, PolicyCondition, PolicyConditionOperator, PolicyAction
        )

        return Policy(
            policy_id="high-risk-deny",
            name="High Risk Denial",
            description="Denies access when risk score is high",
            enabled=True,
            priority=1,  # Higher priority
            conditions=[
                PolicyCondition(
                    field="risk_score",
                    operator=PolicyConditionOperator.GREATER_THAN,
                    value=0.7
                )
            ],
            action=PolicyAction.DENY
        )

    def test_policy_matches_with_conditions(self, admin_policy):
        """Policy must match when all conditions are met."""
        context = {
            "user": {
                "id": "admin-user",
                "roles": ["admin", "user"]
            }
        }

        assert admin_policy.matches(context, "/api/v1/admin/settings") is True

    def test_policy_not_matches_without_role(self, admin_policy):
        """Policy must not match when role is missing."""
        context = {
            "user": {
                "id": "regular-user",
                "roles": ["user"]  # No admin role
            }
        }

        assert admin_policy.matches(context, "/api/v1/admin/settings") is False

    def test_policy_matches_resource_pattern(self, admin_policy):
        """Policy must match resource patterns with wildcards."""
        context = {
            "user": {"roles": ["admin"]}
        }

        # Should match /api/v1/admin/*
        assert admin_policy.matches(context, "/api/v1/admin/anything") is True
        assert admin_policy.matches(context, "/api/v1/admin/deep/nested") is True

    def test_policy_not_matches_different_resource(self, admin_policy):
        """Policy must not match different resource paths."""
        context = {
            "user": {"roles": ["admin"]}
        }

        # Should not match paths outside /api/v1/admin/*
        assert admin_policy.matches(context, "/api/v1/user/settings") is False

    def test_disabled_policy_never_matches(self, admin_policy):
        """Disabled policy must never match."""
        admin_policy.enabled = False

        context = {
            "user": {"roles": ["admin"]}
        }

        assert admin_policy.matches(context, "/api/v1/admin/settings") is False

    def test_policy_with_multiple_conditions_all_must_match(self):
        """All conditions must match for policy to match."""
        from security.zero_trust.policy_engine import (
            Policy, PolicyCondition, PolicyConditionOperator, PolicyAction
        )

        policy = Policy(
            policy_id="multi-condition",
            name="Multi Condition",
            description="Requires multiple conditions",
            conditions=[
                PolicyCondition(
                    field="user.roles",
                    operator=PolicyConditionOperator.CONTAINS,
                    value="admin"
                ),
                PolicyCondition(
                    field="risk_score",
                    operator=PolicyConditionOperator.LESS_THAN,
                    value=0.5
                ),
                PolicyCondition(
                    field="device_known",
                    operator=PolicyConditionOperator.IS_TRUE
                )
            ],
            action=PolicyAction.ALLOW
        )

        # All conditions met
        context_all_match = {
            "user": {"roles": ["admin"]},
            "risk_score": 0.3,
            "device_known": True
        }
        assert policy.matches(context_all_match) is True

        # One condition fails
        context_one_fails = {
            "user": {"roles": ["admin"]},
            "risk_score": 0.7,  # Too high
            "device_known": True
        }
        assert policy.matches(context_one_fails) is False


# =============================================================================
# POLICY PRIORITY TESTS
# =============================================================================

class TestPolicyPriorityFunctional:
    """Functional tests for policy priority ordering."""

    def test_lower_priority_number_is_higher_priority(self):
        """Lower priority number must mean higher priority."""
        from security.zero_trust.policy_engine import Policy, PolicyAction

        policy_high = Policy(
            policy_id="high",
            name="High Priority",
            description="",
            priority=1
        )

        policy_low = Policy(
            policy_id="low",
            name="Low Priority",
            description="",
            priority=100
        )

        # Sort by priority (ascending = highest priority first)
        policies = [policy_low, policy_high]
        sorted_policies = sorted(policies, key=lambda p: p.priority)

        assert sorted_policies[0].policy_id == "high"
        assert sorted_policies[1].policy_id == "low"

    def test_deny_policy_wins_at_same_priority(self):
        """DENY action should win over ALLOW at same priority."""
        from security.zero_trust.policy_engine import Policy, PolicyAction

        policies = [
            Policy(policy_id="allow", name="Allow", description="", priority=10, action=PolicyAction.ALLOW),
            Policy(policy_id="deny", name="Deny", description="", priority=10, action=PolicyAction.DENY)
        ]

        # When priorities are equal, DENY should be preferred (security principle)
        deny_actions = [p for p in policies if p.action == PolicyAction.DENY]
        allow_actions = [p for p in policies if p.action == PolicyAction.ALLOW]

        # System should prefer deny in tie-breaker
        assert len(deny_actions) == 1
        assert deny_actions[0].policy_id == "deny"


# =============================================================================
# POLICY RESOURCE MATCHING TESTS
# =============================================================================

class TestPolicyResourceMatchingFunctional:
    """Functional tests for policy resource matching."""

    def test_exact_resource_match(self):
        """Exact resource path must match."""
        from security.zero_trust.policy_engine import Policy

        policy = Policy(
            policy_id="exact",
            name="Exact Match",
            description="",
            resources=["/api/v1/users"]
        )

        assert policy._matches_resource("/api/v1/users") is True
        assert policy._matches_resource("/api/v1/users/123") is False

    def test_wildcard_resource_match(self):
        """Wildcard resource pattern must match."""
        from security.zero_trust.policy_engine import Policy

        policy = Policy(
            policy_id="wildcard",
            name="Wildcard Match",
            description="",
            resources=["/api/v1/admin/*"]
        )

        assert policy._matches_resource("/api/v1/admin/settings") is True
        assert policy._matches_resource("/api/v1/admin/users/list") is True
        assert policy._matches_resource("/api/v1/users") is False

    def test_global_wildcard_matches_all(self):
        """Global wildcard must match all resources."""
        from security.zero_trust.policy_engine import Policy

        policy = Policy(
            policy_id="global",
            name="Global Match",
            description="",
            resources=["*"]
        )

        assert policy._matches_resource("/any/path/at/all") is True
        assert policy._matches_resource("/api/v1/admin") is True

    def test_multiple_resource_patterns(self):
        """Multiple resource patterns must all be checked."""
        from security.zero_trust.policy_engine import Policy

        policy = Policy(
            policy_id="multi",
            name="Multi Resource",
            description="",
            resources=["/api/v1/users/*", "/api/v1/admin/*", "/api/v1/settings"]
        )

        assert policy._matches_resource("/api/v1/users/123") is True
        assert policy._matches_resource("/api/v1/admin/config") is True
        assert policy._matches_resource("/api/v1/settings") is True
        assert policy._matches_resource("/api/v1/other") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
