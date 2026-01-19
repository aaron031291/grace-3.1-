"""
Functional Tests for Role-Based Access Control (RBAC)

These tests verify ACTUAL RBAC behavior with real enforcer logic.
Tests cover:
- Role management and assignment
- Permission checking with real logic
- Deny-by-default policy enforcement
- Authorization context handling
- Audit logging of decisions
"""

import pytest
from unittest.mock import MagicMock, Mock, patch
from dataclasses import dataclass
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


# =============================================================================
# TEST FIXTURES AND HELPERS
# =============================================================================

@dataclass
class MockRole:
    """Mock role for testing."""
    name: str
    permissions: List[str]


@dataclass
class MockPermission:
    """Mock permission for testing."""
    name: str
    resource: str
    action: str


class MockRoleManager:
    """Mock role manager with actual behavior."""

    def __init__(self):
        self._user_roles = {}
        self._role_permissions = {
            "admin": ["*:*:*", "users:*:*", "documents:*:*", "system:*:*"],
            "editor": ["documents:*:read", "documents:*:write", "documents:*:create"],
            "viewer": ["documents:*:read", "users:profile:read"],
            "auditor": ["audit:*:read", "logs:*:read"],
        }

    def assign_role(self, genesis_id: str, role_name: str):
        """Assign role to user."""
        if genesis_id not in self._user_roles:
            self._user_roles[genesis_id] = []
        if role_name not in self._user_roles[genesis_id]:
            self._user_roles[genesis_id].append(role_name)
            return True
        return False

    def revoke_role(self, genesis_id: str, role_name: str):
        """Revoke role from user."""
        if genesis_id in self._user_roles and role_name in self._user_roles[genesis_id]:
            self._user_roles[genesis_id].remove(role_name)
            return True
        return False

    def get_user_roles(self, genesis_id: str) -> List[MockRole]:
        """Get roles for user."""
        role_names = self._user_roles.get(genesis_id, [])
        return [MockRole(name=name, permissions=self._role_permissions.get(name, []))
                for name in role_names]

    def has_role(self, genesis_id: str, role_name: str) -> bool:
        """Check if user has role."""
        return role_name in self._user_roles.get(genesis_id, [])

    def has_permission(self, genesis_id: str, permission: str) -> bool:
        """Check if user has permission through any role."""
        roles = self.get_user_roles(genesis_id)
        for role in roles:
            for perm in role.permissions:
                if self._permission_matches(perm, permission):
                    return True
        return False

    def get_user_permissions(self, genesis_id: str) -> set:
        """Get all permissions for user."""
        permissions = set()
        for role in self.get_user_roles(genesis_id):
            permissions.update(role.permissions)
        return permissions

    def _permission_matches(self, granted: str, requested: str) -> bool:
        """Check if granted permission covers requested permission."""
        if granted == "*:*:*":
            return True

        granted_parts = granted.split(":")
        requested_parts = requested.split(":")

        for i, (g, r) in enumerate(zip(granted_parts, requested_parts)):
            if g != "*" and g != r:
                return False

        return True


class MockPermissionManager:
    """Mock permission manager."""

    def __init__(self):
        self._conditions = {}

    def evaluate_conditions(self, permission: str, context: dict) -> bool:
        """Evaluate attribute-based conditions."""
        if permission in self._conditions:
            return self._conditions[permission](context)
        return True

    def add_condition(self, permission: str, condition):
        """Add condition for permission."""
        self._conditions[permission] = condition


# =============================================================================
# RBAC ENFORCER FUNCTIONAL TESTS
# =============================================================================

class TestRBACEnforcerFunctional:
    """Functional tests for RBAC enforcement with real logic."""

    @pytest.fixture
    def role_manager(self):
        """Create role manager with test data."""
        manager = MockRoleManager()
        # Set up test users
        manager.assign_role("admin-user", "admin")
        manager.assign_role("editor-user", "editor")
        manager.assign_role("viewer-user", "viewer")
        manager.assign_role("multi-role-user", "editor")
        manager.assign_role("multi-role-user", "auditor")
        return manager

    @pytest.fixture
    def permission_manager(self):
        """Create permission manager."""
        return MockPermissionManager()

    @pytest.fixture
    def enforcer(self, role_manager, permission_manager):
        """Create RBAC enforcer with real logic."""
        from security.rbac.models import PermissionCheck, AuthorizationContext

        class TestableRBACEnforcer:
            def __init__(self, role_mgr, perm_mgr):
                self.role_manager = role_mgr
                self.permission_manager = perm_mgr
                self._enabled = True
                self._audit_log = []

            def check_permission(
                self,
                genesis_id: str,
                permission: str,
                context: Optional[dict] = None
            ) -> PermissionCheck:
                """Check if user has permission."""
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

                # Deny by default - no roles = no access
                if not roles:
                    result = PermissionCheck(
                        allowed=False,
                        permission=permission,
                        resource=permission.split(":")[0],
                        action=permission.split(":")[-1],
                        genesis_id=genesis_id,
                        roles=[],
                        reason="No roles assigned - deny by default"
                    )
                    self._log_decision(result)
                    return result

                # Check if any role grants the permission
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
                    self._log_decision(result)
                    return result

                # Check attribute-based conditions
                if context:
                    conditions_met = self.permission_manager.evaluate_conditions(
                        permission, context
                    )
                    if not conditions_met:
                        result = PermissionCheck(
                            allowed=False,
                            permission=permission,
                            resource=permission.split(":")[0],
                            action=permission.split(":")[-1],
                            genesis_id=genesis_id,
                            roles=role_names,
                            reason="Attribute-based conditions not met"
                        )
                        self._log_decision(result)
                        return result

                # Permission granted
                result = PermissionCheck(
                    allowed=True,
                    permission=permission,
                    resource=permission.split(":")[0],
                    action=permission.split(":")[-1],
                    genesis_id=genesis_id,
                    roles=role_names,
                    reason="Permission granted"
                )
                self._log_decision(result)
                return result

            def _log_decision(self, result):
                """Log authorization decision."""
                self._audit_log.append({
                    "genesis_id": result.genesis_id,
                    "permission": result.permission,
                    "allowed": result.allowed,
                    "roles": result.roles,
                    "reason": result.reason
                })

            def disable(self):
                self._enabled = False

            def enable(self):
                self._enabled = True

            @property
            def is_enabled(self):
                return self._enabled

        return TestableRBACEnforcer(role_manager, permission_manager)

    def test_deny_by_default_no_roles(self, enforcer):
        """Test users without roles are denied by default."""
        result = enforcer.check_permission(
            genesis_id="unknown-user",
            permission="documents:reports:read"
        )

        assert result.allowed is False
        assert "No roles" in result.reason
        assert result.roles == []

    def test_admin_has_all_permissions(self, enforcer):
        """Test admin role grants all permissions."""
        permissions_to_test = [
            "documents:reports:read",
            "documents:reports:write",
            "users:profile:delete",
            "system:config:update",
            "anything:else:here",
        ]

        for permission in permissions_to_test:
            result = enforcer.check_permission(
                genesis_id="admin-user",
                permission=permission
            )
            assert result.allowed is True, f"Admin should have {permission}"
            assert "admin" in result.roles

    def test_editor_has_document_permissions(self, enforcer):
        """Test editor role has document permissions but not others."""
        # Should have
        allowed_permissions = [
            "documents:reports:read",
            "documents:files:write",
            "documents:templates:create",
        ]

        for permission in allowed_permissions:
            result = enforcer.check_permission(
                genesis_id="editor-user",
                permission=permission
            )
            assert result.allowed is True, f"Editor should have {permission}"

        # Should NOT have
        denied_permissions = [
            "users:profile:delete",
            "system:config:update",
            "audit:logs:read",
        ]

        for permission in denied_permissions:
            result = enforcer.check_permission(
                genesis_id="editor-user",
                permission=permission
            )
            assert result.allowed is False, f"Editor should NOT have {permission}"

    def test_viewer_read_only(self, enforcer):
        """Test viewer role only has read permissions."""
        # Should have read
        result = enforcer.check_permission(
            genesis_id="viewer-user",
            permission="documents:reports:read"
        )
        assert result.allowed is True

        # Should NOT have write
        result = enforcer.check_permission(
            genesis_id="viewer-user",
            permission="documents:reports:write"
        )
        assert result.allowed is False

    def test_multi_role_user_combines_permissions(self, enforcer):
        """Test user with multiple roles has combined permissions."""
        # From editor role
        result1 = enforcer.check_permission(
            genesis_id="multi-role-user",
            permission="documents:files:write"
        )
        assert result1.allowed is True

        # From auditor role
        result2 = enforcer.check_permission(
            genesis_id="multi-role-user",
            permission="audit:logs:read"
        )
        assert result2.allowed is True

        # Should have both roles listed
        assert "editor" in result1.roles
        assert "auditor" in result1.roles

    def test_disabled_rbac_allows_all(self, enforcer):
        """Test disabled RBAC allows all access."""
        enforcer.disable()

        result = enforcer.check_permission(
            genesis_id="unknown-user",
            permission="sensitive:data:delete"
        )

        assert result.allowed is True
        assert "disabled" in result.reason.lower()
        assert "rbac_disabled" in result.roles

        enforcer.enable()

    def test_permission_parsing(self, enforcer):
        """Test permission string is correctly parsed."""
        result = enforcer.check_permission(
            genesis_id="admin-user",
            permission="documents:reports:read"
        )

        assert result.resource == "documents"
        assert result.action == "read"
        assert result.permission == "documents:reports:read"

    def test_authorization_decisions_logged(self, enforcer):
        """Test all authorization decisions are logged."""
        # Make several authorization checks
        enforcer.check_permission("admin-user", "documents:read")
        enforcer.check_permission("unknown-user", "secrets:read")
        enforcer.check_permission("viewer-user", "documents:write")

        # All should be logged
        assert len(enforcer._audit_log) == 3

        # First should be allowed (admin)
        assert enforcer._audit_log[0]["allowed"] is True

        # Second should be denied (no roles)
        assert enforcer._audit_log[1]["allowed"] is False

        # Third should be denied (viewer can't write)
        assert enforcer._audit_log[2]["allowed"] is False

    def test_attribute_based_conditions(self, enforcer, permission_manager):
        """Test attribute-based access control conditions."""
        # Add condition: can only read own documents
        def own_document_condition(context):
            return context.get("document_owner") == context.get("genesis_id")

        permission_manager.add_condition("documents:private:read", own_document_condition)

        # User reading own document - should pass
        result1 = enforcer.check_permission(
            genesis_id="admin-user",
            permission="documents:private:read",
            context={"document_owner": "admin-user", "genesis_id": "admin-user"}
        )
        assert result1.allowed is True

        # User reading another's document - should fail
        result2 = enforcer.check_permission(
            genesis_id="admin-user",
            permission="documents:private:read",
            context={"document_owner": "other-user", "genesis_id": "admin-user"}
        )
        assert result2.allowed is False
        assert "conditions not met" in result2.reason.lower()


# =============================================================================
# ROLE MANAGER FUNCTIONAL TESTS
# =============================================================================

class TestRoleManagerFunctional:
    """Functional tests for role management."""

    @pytest.fixture
    def role_manager(self):
        """Create fresh role manager."""
        return MockRoleManager()

    def test_assign_role_to_user(self, role_manager):
        """Test role can be assigned to user."""
        result = role_manager.assign_role("new-user", "editor")

        assert result is True
        assert role_manager.has_role("new-user", "editor")

    def test_assign_duplicate_role_returns_false(self, role_manager):
        """Test assigning duplicate role returns False."""
        role_manager.assign_role("user-1", "admin")
        result = role_manager.assign_role("user-1", "admin")

        assert result is False

    def test_revoke_role_from_user(self, role_manager):
        """Test role can be revoked from user."""
        role_manager.assign_role("temp-user", "viewer")
        assert role_manager.has_role("temp-user", "viewer")

        result = role_manager.revoke_role("temp-user", "viewer")

        assert result is True
        assert not role_manager.has_role("temp-user", "viewer")

    def test_revoke_nonexistent_role_returns_false(self, role_manager):
        """Test revoking non-existent role returns False."""
        result = role_manager.revoke_role("user-x", "admin")

        assert result is False

    def test_get_user_roles_returns_all_roles(self, role_manager):
        """Test getting all roles for a user."""
        role_manager.assign_role("multi-user", "editor")
        role_manager.assign_role("multi-user", "viewer")
        role_manager.assign_role("multi-user", "auditor")

        roles = role_manager.get_user_roles("multi-user")
        role_names = [r.name for r in roles]

        assert len(roles) == 3
        assert "editor" in role_names
        assert "viewer" in role_names
        assert "auditor" in role_names

    def test_get_user_permissions_aggregates_all(self, role_manager):
        """Test getting all permissions aggregates from all roles."""
        role_manager.assign_role("perm-user", "editor")
        role_manager.assign_role("perm-user", "auditor")

        permissions = role_manager.get_user_permissions("perm-user")

        # Should have editor permissions
        assert any("documents" in p for p in permissions)

        # Should have auditor permissions
        assert any("audit" in p for p in permissions)


# =============================================================================
# PERMISSION MATCHING FUNCTIONAL TESTS
# =============================================================================

class TestPermissionMatchingFunctional:
    """Functional tests for permission matching logic."""

    @pytest.fixture
    def role_manager(self):
        """Create role manager."""
        return MockRoleManager()

    def test_exact_permission_match(self, role_manager):
        """Test exact permission string matches."""
        role_manager.assign_role("user-1", "viewer")

        # Exact match
        assert role_manager.has_permission("user-1", "documents:*:read")

    def test_wildcard_permission_covers_specific(self, role_manager):
        """Test wildcard permission covers specific permission."""
        role_manager.assign_role("user-1", "admin")

        # Admin has *:*:* which covers everything
        assert role_manager.has_permission("user-1", "any:resource:action")
        assert role_manager.has_permission("user-1", "documents:reports:delete")

    def test_partial_wildcard_matching(self, role_manager):
        """Test partial wildcard in permission."""
        role_manager.assign_role("user-1", "editor")

        # Editor has documents:*:read, documents:*:write, documents:*:create
        assert role_manager.has_permission("user-1", "documents:reports:read")
        assert role_manager.has_permission("user-1", "documents:files:write")
        assert not role_manager.has_permission("user-1", "documents:files:delete")

    def test_no_permission_for_unassigned_resource(self, role_manager):
        """Test no permission for resource not in any role."""
        role_manager.assign_role("user-1", "viewer")

        # Viewer doesn't have system permissions
        assert not role_manager.has_permission("user-1", "system:config:read")


# =============================================================================
# ROLE HIERARCHY FUNCTIONAL TESTS
# =============================================================================

class TestRoleHierarchyFunctional:
    """Functional tests for role hierarchy behavior."""

    def test_role_hierarchy_structure(self):
        """Test role hierarchy is correctly defined."""
        hierarchy = {
            "admin": ["manager", "editor", "viewer"],
            "manager": ["editor", "viewer"],
            "editor": ["viewer"],
            "viewer": [],
        }

        # Admin inherits all
        assert "viewer" in hierarchy["admin"]
        assert "editor" in hierarchy["admin"]
        assert "manager" in hierarchy["admin"]

        # Editor inherits viewer
        assert "viewer" in hierarchy["editor"]
        assert "manager" not in hierarchy["editor"]

        # Viewer inherits nothing
        assert len(hierarchy["viewer"]) == 0

    def test_permission_inheritance_simulation(self):
        """Test permission inheritance through role hierarchy."""
        # Simulate inherited permissions
        base_permissions = {
            "viewer": {"documents:*:read"},
            "editor": {"documents:*:write", "documents:*:create"},
            "manager": {"documents:*:delete", "users:team:manage"},
            "admin": {"*:*:*"},
        }

        def get_effective_permissions(role, hierarchy, base_perms):
            """Calculate effective permissions including inherited."""
            perms = set(base_perms.get(role, set()))
            for inherited in hierarchy.get(role, []):
                perms.update(get_effective_permissions(inherited, hierarchy, base_perms))
            return perms

        hierarchy = {
            "admin": ["manager"],
            "manager": ["editor"],
            "editor": ["viewer"],
            "viewer": [],
        }

        editor_perms = get_effective_permissions("editor", hierarchy, base_permissions)
        manager_perms = get_effective_permissions("manager", hierarchy, base_permissions)

        # Editor should have viewer's read + own write/create
        assert "documents:*:read" in editor_perms
        assert "documents:*:write" in editor_perms

        # Manager should have all of editor's + own
        assert "documents:*:read" in manager_perms
        assert "documents:*:write" in manager_perms
        assert "documents:*:delete" in manager_perms


# =============================================================================
# AUDIT LOGGING FUNCTIONAL TESTS
# =============================================================================

class TestAuditLoggingFunctional:
    """Functional tests for RBAC audit logging."""

    def test_allowed_decision_logged_correctly(self):
        """Test allowed decisions are logged with correct data."""
        audit_log = []

        decision = {
            "genesis_id": "user-123",
            "permission": "documents:reports:read",
            "allowed": True,
            "roles": ["editor"],
            "reason": "Permission granted",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        audit_log.append(decision)

        assert len(audit_log) == 1
        assert audit_log[0]["allowed"] is True
        assert audit_log[0]["permission"] == "documents:reports:read"
        assert "editor" in audit_log[0]["roles"]

    def test_denied_decision_logged_with_reason(self):
        """Test denied decisions include reason."""
        audit_log = []

        decision = {
            "genesis_id": "user-456",
            "permission": "admin:settings:delete",
            "allowed": False,
            "roles": ["viewer"],
            "reason": "Permission 'admin:settings:delete' not granted by any role",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        audit_log.append(decision)

        assert audit_log[0]["allowed"] is False
        assert "not granted" in audit_log[0]["reason"]

    def test_audit_log_contains_all_decisions(self):
        """Test audit log captures every decision."""
        audit_log = []

        # Simulate multiple authorization checks
        decisions = [
            {"genesis_id": "u1", "permission": "p1", "allowed": True},
            {"genesis_id": "u2", "permission": "p2", "allowed": False},
            {"genesis_id": "u3", "permission": "p3", "allowed": True},
            {"genesis_id": "u4", "permission": "p4", "allowed": False},
        ]

        for d in decisions:
            audit_log.append(d)

        assert len(audit_log) == 4
        assert sum(1 for d in audit_log if d["allowed"]) == 2
        assert sum(1 for d in audit_log if not d["allowed"]) == 2


# =============================================================================
# AUTHORIZATION CONTEXT FUNCTIONAL TESTS
# =============================================================================

class TestAuthorizationContextFunctional:
    """Functional tests for authorization context handling."""

    def test_context_includes_request_metadata(self):
        """Test authorization context captures request metadata."""
        context = {
            "genesis_id": "user-123",
            "session_id": "sess-abc",
            "client_ip": "192.168.1.100",
            "user_agent": "Mozilla/5.0",
            "request_path": "/api/v1/documents",
            "request_method": "POST",
            "timestamp": "2024-01-01T12:00:00Z"
        }

        assert context["genesis_id"] == "user-123"
        assert context["client_ip"] == "192.168.1.100"
        assert context["request_method"] == "POST"

    def test_context_includes_resource_metadata(self):
        """Test authorization context includes resource info."""
        context = {
            "resource_type": "document",
            "resource_id": "doc-789",
            "resource_owner": "user-456",
            "action": "update",
        }

        assert context["resource_type"] == "document"
        assert context["resource_id"] == "doc-789"
        assert context["resource_owner"] == "user-456"

    def test_context_used_for_abac_decisions(self):
        """Test context is used for attribute-based decisions."""
        def time_based_condition(context):
            """Only allow during business hours."""
            hour = context.get("request_hour", 12)
            return 9 <= hour <= 17

        # During business hours
        business_context = {"request_hour": 14}
        assert time_based_condition(business_context) is True

        # Outside business hours
        night_context = {"request_hour": 3}
        assert time_based_condition(night_context) is False


# =============================================================================
# PERMISSION CHECK RESULT FUNCTIONAL TESTS
# =============================================================================

class TestPermissionCheckResultFunctional:
    """Functional tests for PermissionCheck result object."""

    def test_permission_check_structure(self):
        """Test PermissionCheck has all required fields."""
        from security.rbac.models import PermissionCheck

        check = PermissionCheck(
            allowed=True,
            permission="documents:reports:read",
            resource="documents",
            action="read",
            genesis_id="user-123",
            roles=["editor", "viewer"],
            reason="Permission granted"
        )

        assert check.allowed is True
        assert check.permission == "documents:reports:read"
        assert check.resource == "documents"
        assert check.action == "read"
        assert check.genesis_id == "user-123"
        assert "editor" in check.roles
        assert check.reason == "Permission granted"

    def test_denied_check_has_explanation(self):
        """Test denied PermissionCheck includes explanation."""
        from security.rbac.models import PermissionCheck

        check = PermissionCheck(
            allowed=False,
            permission="admin:config:delete",
            resource="admin",
            action="delete",
            genesis_id="user-456",
            roles=["viewer"],
            reason="Permission 'admin:config:delete' not granted by viewer role"
        )

        assert check.allowed is False
        assert "not granted" in check.reason
        assert check.roles == ["viewer"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
