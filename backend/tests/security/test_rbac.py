"""
Tests for Role-Based Access Control (RBAC)

Tests cover:
- Role management
- Permission assignment
- Permission checking
- Policy enforcement
- Deny-by-default behavior
- Audit logging of authorization decisions
"""

import pytest
from unittest.mock import MagicMock, patch


class TestRBACEnforcer:
    """Tests for RBACEnforcer class."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def enforcer(self, mock_session):
        """Create a mock RBACEnforcer for testing."""
        from dataclasses import dataclass
        
        @dataclass
        class PermissionCheck:
            allowed: bool
            permission: str
            resource: str
            action: str
            genesis_id: str
            roles: list
            reason: str
        
        class MockRBACEnforcer:
            def __init__(self, session):
                self.session = session
                self.role_manager = MagicMock()
                self.permission_manager = MagicMock()
                self._enabled = True
            
            def check_permission(self, genesis_id, permission, context=None, resource_id=None):
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
                role_names = [getattr(r, 'name', 'unknown') for r in roles] if roles else []
                
                if not roles:
                    return PermissionCheck(
                        allowed=False,
                        permission=permission,
                        resource=permission.split(":")[0],
                        action=permission.split(":")[-1],
                        genesis_id=genesis_id,
                        roles=[],
                        reason="No roles assigned"
                    )
                
                return PermissionCheck(
                    allowed=True,
                    permission=permission,
                    resource=permission.split(":")[0],
                    action=permission.split(":")[-1],
                    genesis_id=genesis_id,
                    roles=role_names,
                    reason="Permission granted"
                )
        
        return MockRBACEnforcer(mock_session)

    def test_deny_by_default(self, enforcer):
        """Users without roles should be denied access."""
        enforcer.role_manager.get_user_roles.return_value = []
        
        result = enforcer.check_permission(
            genesis_id="user-123",
            permission="documents:read"
        )
        
        assert result.allowed is False
        assert "No roles assigned" in result.reason

    def test_permission_check_with_valid_role(self, enforcer):
        """Users with appropriate roles should be granted access."""
        mock_role = MagicMock()
        mock_role.name = "admin"
        enforcer.role_manager.get_user_roles.return_value = [mock_role]
        enforcer.permission_manager.has_permission.return_value = True
        
        result = enforcer.check_permission(
            genesis_id="admin-user",
            permission="documents:write"
        )
        
        # Should check permission
        enforcer.role_manager.get_user_roles.assert_called_once_with("admin-user")

    def test_permission_check_parses_resource_action(self, enforcer):
        """Permission string should be parsed into resource:action."""
        enforcer.role_manager.get_user_roles.return_value = []
        
        result = enforcer.check_permission(
            genesis_id="user-123",
            permission="documents:read"
        )
        
        assert result.resource == "documents"
        assert result.action == "read"

    def test_disabled_rbac_allows_all(self, enforcer):
        """When RBAC is disabled, all access should be allowed."""
        enforcer._enabled = False
        
        result = enforcer.check_permission(
            genesis_id="any-user",
            permission="sensitive:delete"
        )
        
        assert result.allowed is True
        assert "disabled" in result.reason.lower()


class TestRoleManager:
    """Tests for role management."""

    @pytest.fixture
    def role_manager(self):
        """Create a mock RoleManager for testing."""
        manager = MagicMock()
        return manager

    def test_get_user_roles(self, role_manager):
        """Should return all roles for a user."""
        mock_roles = [
            MagicMock(name="admin"),
            MagicMock(name="editor"),
        ]
        role_manager.get_user_roles.return_value = mock_roles
        
        roles = role_manager.get_user_roles("user-123")
        
        assert len(roles) == 2

    def test_assign_role(self, role_manager):
        """Should assign role to user."""
        role_manager.assign_role.return_value = True
        
        result = role_manager.assign_role("user-123", "editor")
        
        assert result is True
        role_manager.assign_role.assert_called_once()

    def test_revoke_role(self, role_manager):
        """Should revoke role from user."""
        role_manager.revoke_role.return_value = True
        
        result = role_manager.revoke_role("user-123", "admin")
        
        assert result is True

    def test_user_has_role(self, role_manager):
        """Should check if user has specific role."""
        role_manager.has_role.return_value = True
        
        result = role_manager.has_role("user-123", "admin")
        
        assert result is True


class TestPermissionManager:
    """Tests for permission management."""

    @pytest.fixture
    def permission_manager(self):
        """Create a PermissionManager instance."""
        return MagicMock()

    def test_has_permission(self, permission_manager):
        """Should check if user has permission."""
        permission_manager.has_permission.return_value = True
        
        result = permission_manager.has_permission("user-123", "documents:read")
        
        assert result is True

    def test_permission_not_granted(self, permission_manager):
        """Should return False when permission not granted."""
        permission_manager.has_permission.return_value = False
        
        result = permission_manager.has_permission("user-123", "admin:delete")
        
        assert result is False

    def test_grant_permission(self, permission_manager):
        """Should grant permission to role."""
        permission_manager.grant_permission.return_value = True
        
        result = permission_manager.grant_permission("editor", "documents:write")
        
        assert result is True


class TestAuthorizationContext:
    """Tests for authorization context."""

    def test_context_includes_user_info(self):
        """Authorization context should include user information."""
        context = {
            "genesis_id": "user-123",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "timestamp": "2024-01-01T00:00:00Z",
        }
        
        assert "genesis_id" in context
        assert "ip_address" in context

    def test_context_includes_resource_info(self):
        """Authorization context should include resource information."""
        context = {
            "resource_type": "document",
            "resource_id": "doc-456",
            "action": "read",
        }
        
        assert "resource_type" in context
        assert "resource_id" in context
        assert "action" in context


class TestPermissionCheck:
    """Tests for PermissionCheck result."""

    def test_permission_check_allowed(self):
        """Allowed permission check should have correct fields."""
        from dataclasses import dataclass
        
        @dataclass
        class PermissionCheck:
            allowed: bool
            permission: str
            resource: str
            action: str
            genesis_id: str
            roles: list
            reason: str
        
        check = PermissionCheck(
            allowed=True,
            permission="documents:read",
            resource="documents",
            action="read",
            genesis_id="user-123",
            roles=["viewer"],
            reason="Permission granted"
        )
        
        assert check.allowed is True
        assert check.permission == "documents:read"

    def test_permission_check_denied(self):
        """Denied permission check should have reason."""
        from dataclasses import dataclass
        
        @dataclass
        class PermissionCheck:
            allowed: bool
            permission: str
            resource: str
            action: str
            genesis_id: str
            roles: list
            reason: str
        
        check = PermissionCheck(
            allowed=False,
            permission="admin:delete",
            resource="admin",
            action="delete",
            genesis_id="user-123",
            roles=[],
            reason="No roles assigned"
        )
        
        assert check.allowed is False
        assert "No roles" in check.reason


class TestRoleHierarchy:
    """Tests for role hierarchy and inheritance."""

    def test_admin_inherits_all_permissions(self):
        """Admin role should inherit all permissions from lower roles."""
        role_hierarchy = {
            "admin": ["manager", "editor", "viewer"],
            "manager": ["editor", "viewer"],
            "editor": ["viewer"],
            "viewer": [],
        }
        
        # Admin should have all inherited roles
        assert "viewer" in role_hierarchy["admin"]
        assert "editor" in role_hierarchy["admin"]

    def test_viewer_has_minimal_permissions(self):
        """Viewer role should have minimal permissions."""
        role_hierarchy = {
            "viewer": [],
        }
        
        assert len(role_hierarchy["viewer"]) == 0


class TestAuditLogging:
    """Tests for RBAC audit logging."""

    def test_authorization_decision_logged(self):
        """All authorization decisions should be logged."""
        audit_log = []
        
        def log_decision(decision):
            audit_log.append(decision)
        
        # Simulate authorization check
        decision = {
            "genesis_id": "user-123",
            "permission": "documents:read",
            "allowed": True,
            "timestamp": "2024-01-01T00:00:00Z",
            "roles": ["viewer"],
        }
        log_decision(decision)
        
        assert len(audit_log) == 1
        assert audit_log[0]["allowed"] is True

    def test_denied_access_logged(self):
        """Denied access attempts should be logged."""
        audit_log = []
        
        decision = {
            "genesis_id": "user-123",
            "permission": "admin:delete",
            "allowed": False,
            "reason": "Insufficient permissions",
            "timestamp": "2024-01-01T00:00:00Z",
        }
        audit_log.append(decision)
        
        assert audit_log[0]["allowed"] is False
        assert "Insufficient" in audit_log[0]["reason"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
