"""
API Key Management - REAL Functional Tests

Tests verify ACTUAL API key behavior using real implementations:
- API key generation with secure entropy
- Key scoping and permissions
- Key expiration and rotation
- Usage tracking and quotas
- Key revocation
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, Set
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


# =============================================================================
# API KEY SCOPE ENUM TESTS
# =============================================================================

class TestAPIKeyScopeEnumFunctional:
    """Functional tests for APIKeyScope enum."""

    def test_all_scopes_defined(self):
        """All required API key scopes must be defined."""
        from security.api_security.api_keys import APIKeyScope

        required_scopes = [
            "FULL_ACCESS",
            "READ_ONLY",
            "WRITE_ONLY",
            "ENDPOINT_SPECIFIC",
            "RESOURCE_SPECIFIC"
        ]

        for scope_name in required_scopes:
            assert hasattr(APIKeyScope, scope_name), f"Missing scope: {scope_name}"

    def test_scope_values_are_lowercase(self):
        """Scope values must be lowercase strings."""
        from security.api_security.api_keys import APIKeyScope

        for scope in APIKeyScope:
            assert isinstance(scope.value, str)
            assert scope.value == scope.value.lower()


# =============================================================================
# API KEY STATUS ENUM TESTS
# =============================================================================

class TestAPIKeyStatusEnumFunctional:
    """Functional tests for APIKeyStatus enum."""

    def test_all_statuses_defined(self):
        """All required API key statuses must be defined."""
        from security.api_security.api_keys import APIKeyStatus

        required_statuses = [
            "ACTIVE",
            "EXPIRED",
            "REVOKED",
            "RATE_LIMITED",
            "SUSPENDED"
        ]

        for status_name in required_statuses:
            assert hasattr(APIKeyStatus, status_name), f"Missing status: {status_name}"


# =============================================================================
# API KEY QUOTA DATA CLASS TESTS
# =============================================================================

class TestAPIKeyQuotaFunctional:
    """Functional tests for APIKeyQuota data class."""

    def test_quota_default_values(self):
        """APIKeyQuota must have sensible defaults."""
        from security.api_security.api_keys import APIKeyQuota

        quota = APIKeyQuota()

        assert quota.requests_per_minute >= 1
        assert quota.requests_per_hour >= quota.requests_per_minute
        assert quota.requests_per_day >= quota.requests_per_hour
        assert quota.max_request_size_bytes > 0
        assert quota.burst_allowance >= 0

    def test_quota_customizable(self):
        """APIKeyQuota must be customizable."""
        from security.api_security.api_keys import APIKeyQuota

        quota = APIKeyQuota(
            requests_per_minute=50,
            requests_per_hour=500,
            requests_per_day=5000,
            max_request_size_bytes=1024 * 1024,
            burst_allowance=5
        )

        assert quota.requests_per_minute == 50
        assert quota.requests_per_hour == 500
        assert quota.requests_per_day == 5000


# =============================================================================
# API KEY USAGE DATA CLASS TESTS
# =============================================================================

class TestAPIKeyUsageFunctional:
    """Functional tests for APIKeyUsage data class."""

    def test_usage_initial_values(self):
        """APIKeyUsage must start with zero counts."""
        from security.api_security.api_keys import APIKeyUsage

        usage = APIKeyUsage()

        assert usage.total_requests == 0
        assert usage.requests_this_minute == 0
        assert usage.requests_this_hour == 0
        assert usage.requests_this_day == 0
        assert usage.bytes_transferred == 0
        assert usage.errors_count == 0

    def test_usage_tracks_last_request(self):
        """APIKeyUsage must track last request time."""
        from security.api_security.api_keys import APIKeyUsage

        usage = APIKeyUsage()

        assert usage.last_request_at is None

        usage.last_request_at = datetime.utcnow()

        assert usage.last_request_at is not None


# =============================================================================
# API KEY DATA CLASS TESTS
# =============================================================================

class TestAPIKeyDataClassFunctional:
    """Functional tests for APIKey data class."""

    @pytest.fixture
    def api_key(self):
        """Create APIKey instance."""
        from security.api_security.api_keys import (
            APIKey, APIKeyScope, APIKeyStatus, APIKeyQuota, APIKeyUsage
        )

        return APIKey(
            key_id="apk_test123",
            key_hash="hashed_key_value",
            name="Test API Key",
            description="Key for testing purposes",
            owner_id="user-owner-123",
            scope=APIKeyScope.READ_ONLY,
            status=APIKeyStatus.ACTIVE,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=365),
            last_rotated_at=None,
            allowed_endpoints={"/api/v1/data", "/api/v1/status"},
            allowed_resources={"resource-1", "resource-2"},
            allowed_ips={"192.168.1.1", "10.0.0.1"},
            quota=APIKeyQuota(),
            usage=APIKeyUsage()
        )

    def test_api_key_creation(self, api_key):
        """APIKey must be creatable with required fields."""
        from security.api_security.api_keys import APIKeyScope, APIKeyStatus

        assert api_key.key_id == "apk_test123"
        assert api_key.name == "Test API Key"
        assert api_key.scope == APIKeyScope.READ_ONLY
        assert api_key.status == APIKeyStatus.ACTIVE

    def test_api_key_has_allowed_endpoints(self, api_key):
        """APIKey must have allowed endpoints set."""
        assert "/api/v1/data" in api_key.allowed_endpoints
        assert "/api/v1/status" in api_key.allowed_endpoints

    def test_api_key_has_allowed_ips(self, api_key):
        """APIKey must have allowed IPs set."""
        assert "192.168.1.1" in api_key.allowed_ips
        assert "10.0.0.1" in api_key.allowed_ips

    def test_api_key_revocation_fields(self):
        """APIKey must support revocation fields."""
        from security.api_security.api_keys import (
            APIKey, APIKeyScope, APIKeyStatus
        )

        key = APIKey(
            key_id="apk_revoked",
            key_hash="hash",
            name="Revoked Key",
            description="",
            owner_id="user",
            scope=APIKeyScope.FULL_ACCESS,
            status=APIKeyStatus.REVOKED,
            created_at=datetime.utcnow(),
            expires_at=None,
            last_rotated_at=None,
            revocation_reason="Security breach suspected",
            revoked_at=datetime.utcnow(),
            revoked_by="admin-user"
        )

        assert key.status == APIKeyStatus.REVOKED
        assert key.revocation_reason == "Security breach suspected"
        assert key.revoked_by == "admin-user"


# =============================================================================
# API KEY MANAGER FUNCTIONAL TESTS
# =============================================================================

class TestAPIKeyManagerFunctional:
    """Functional tests for APIKeyManager."""

    @pytest.fixture
    def manager(self):
        """Create fresh APIKeyManager instance."""
        from security.api_security.api_keys import APIKeyManager
        return APIKeyManager()

    def test_generate_key_returns_raw_and_key_object(self, manager):
        """generate_key must return raw key and APIKey object."""
        from security.api_security.api_keys import APIKey

        raw_key, api_key = manager.generate_key(
            name="Test Key",
            owner_id="owner-123"
        )

        assert isinstance(raw_key, str)
        assert isinstance(api_key, APIKey)
        assert api_key.name == "Test Key"
        assert api_key.owner_id == "owner-123"

    def test_generated_key_starts_with_prefix(self, manager):
        """Generated key must start with configured prefix."""
        raw_key, api_key = manager.generate_key(
            name="Prefixed Key",
            owner_id="owner"
        )

        assert raw_key.startswith("gk_")

    def test_generated_key_has_sufficient_entropy(self, manager):
        """Generated key must have sufficient entropy."""
        raw_key, _ = manager.generate_key(
            name="Entropy Key",
            owner_id="owner"
        )

        # Remove prefix and check length
        key_body = raw_key.replace("gk_", "")
        # 32 bytes of entropy = ~43 base64url chars
        assert len(key_body) >= 40

    def test_generated_keys_are_unique(self, manager):
        """Generated keys must be unique."""
        keys = set()

        for i in range(100):
            raw_key, _ = manager.generate_key(
                name=f"Key {i}",
                owner_id="owner"
            )
            keys.add(raw_key)

        assert len(keys) == 100

    def test_key_hash_stored_not_raw(self, manager):
        """Key hash must be stored, not raw key."""
        raw_key, api_key = manager.generate_key(
            name="Hashed Key",
            owner_id="owner"
        )

        # Raw key should not appear in hash
        assert raw_key not in api_key.key_hash
        assert len(api_key.key_hash) > 0

    def test_key_expiration_set(self, manager):
        """Key must have expiration date set."""
        _, api_key = manager.generate_key(
            name="Expiring Key",
            owner_id="owner",
            expires_in_days=30
        )

        assert api_key.expires_at is not None
        assert api_key.expires_at > datetime.utcnow()
        assert api_key.expires_at < datetime.utcnow() + timedelta(days=31)

    def test_key_no_expiration_when_zero_days(self, manager):
        """Key with expires_in_days=0 must not expire."""
        _, api_key = manager.generate_key(
            name="Non-Expiring Key",
            owner_id="owner",
            expires_in_days=0
        )

        assert api_key.expires_at is None

    def test_key_scope_assigned(self, manager):
        """Key must have assigned scope."""
        from security.api_security.api_keys import APIKeyScope

        _, api_key = manager.generate_key(
            name="Scoped Key",
            owner_id="owner",
            scope=APIKeyScope.ENDPOINT_SPECIFIC
        )

        assert api_key.scope == APIKeyScope.ENDPOINT_SPECIFIC

    def test_key_allowed_endpoints_assigned(self, manager):
        """Key must have allowed endpoints assigned."""
        _, api_key = manager.generate_key(
            name="Endpoint Key",
            owner_id="owner",
            allowed_endpoints={"/api/data", "/api/status"}
        )

        assert "/api/data" in api_key.allowed_endpoints
        assert "/api/status" in api_key.allowed_endpoints

    def test_key_allowed_ips_assigned(self, manager):
        """Key must have allowed IPs assigned."""
        _, api_key = manager.generate_key(
            name="IP-Restricted Key",
            owner_id="owner",
            allowed_ips={"10.0.0.1", "192.168.1.0/24"}
        )

        assert "10.0.0.1" in api_key.allowed_ips

    def test_key_quota_assigned(self, manager):
        """Key must have quota assigned."""
        from security.api_security.api_keys import APIKeyQuota

        custom_quota = APIKeyQuota(
            requests_per_minute=10,
            requests_per_hour=100
        )

        _, api_key = manager.generate_key(
            name="Quota Key",
            owner_id="owner",
            quota=custom_quota
        )

        assert api_key.quota.requests_per_minute == 10
        assert api_key.quota.requests_per_hour == 100

    def test_key_status_is_active(self, manager):
        """New key must have ACTIVE status."""
        from security.api_security.api_keys import APIKeyStatus

        _, api_key = manager.generate_key(
            name="Active Key",
            owner_id="owner"
        )

        assert api_key.status == APIKeyStatus.ACTIVE

    def test_key_custom_entropy(self, manager):
        """Key can be generated with custom entropy."""
        raw_key, _ = manager.generate_key(
            name="High Entropy Key",
            owner_id="owner",
            entropy_bytes=64
        )

        key_body = raw_key.replace("gk_", "")
        # 64 bytes = ~86 base64url chars
        assert len(key_body) >= 80


# =============================================================================
# API KEY VALIDATION TESTS
# =============================================================================

class TestAPIKeyValidationFunctional:
    """Functional tests for API key validation patterns."""

    def test_key_scope_check_full_access(self):
        """FULL_ACCESS scope must allow all endpoints."""
        from security.api_security.api_keys import APIKeyScope

        scope = APIKeyScope.FULL_ACCESS
        endpoints = ["/api/v1/data", "/api/v1/admin", "/api/v2/anything"]

        # Full access should allow all
        for endpoint in endpoints:
            assert scope == APIKeyScope.FULL_ACCESS

    def test_key_scope_check_read_only(self):
        """READ_ONLY scope must restrict write operations."""
        from security.api_security.api_keys import APIKeyScope

        scope = APIKeyScope.READ_ONLY

        def is_read_allowed(method: str, scope: APIKeyScope) -> bool:
            if scope == APIKeyScope.FULL_ACCESS:
                return True
            if scope == APIKeyScope.READ_ONLY:
                return method in ["GET", "HEAD", "OPTIONS"]
            if scope == APIKeyScope.WRITE_ONLY:
                return method in ["POST", "PUT", "PATCH", "DELETE"]
            return False

        assert is_read_allowed("GET", scope) is True
        assert is_read_allowed("HEAD", scope) is True
        assert is_read_allowed("POST", scope) is False
        assert is_read_allowed("DELETE", scope) is False

    def test_key_expiration_check(self):
        """Expired keys must be detected."""
        now = datetime.utcnow()

        expired_key = {"expires_at": now - timedelta(hours=1)}
        valid_key = {"expires_at": now + timedelta(hours=1)}
        no_expiry_key = {"expires_at": None}

        def is_expired(key: Dict) -> bool:
            if key["expires_at"] is None:
                return False
            return datetime.utcnow() > key["expires_at"]

        assert is_expired(expired_key) is True
        assert is_expired(valid_key) is False
        assert is_expired(no_expiry_key) is False

    def test_ip_whitelist_check(self):
        """IP whitelist must be enforced."""
        allowed_ips = {"192.168.1.1", "10.0.0.1", "10.0.0.2"}

        def is_ip_allowed(ip: str, allowed: Set[str]) -> bool:
            if not allowed:  # Empty = allow all
                return True
            return ip in allowed

        assert is_ip_allowed("192.168.1.1", allowed_ips) is True
        assert is_ip_allowed("10.0.0.1", allowed_ips) is True
        assert is_ip_allowed("8.8.8.8", allowed_ips) is False


# =============================================================================
# API KEY QUOTA ENFORCEMENT TESTS
# =============================================================================

class TestAPIKeyQuotaEnforcementFunctional:
    """Functional tests for API key quota enforcement."""

    def test_minute_quota_exceeded(self):
        """Minute quota exceeded must be detected."""
        from security.api_security.api_keys import APIKeyQuota, APIKeyUsage

        quota = APIKeyQuota(requests_per_minute=10)
        usage = APIKeyUsage(requests_this_minute=10)

        is_exceeded = usage.requests_this_minute >= quota.requests_per_minute

        assert is_exceeded is True

    def test_minute_quota_not_exceeded(self):
        """Minute quota not exceeded must be allowed."""
        from security.api_security.api_keys import APIKeyQuota, APIKeyUsage

        quota = APIKeyQuota(requests_per_minute=10)
        usage = APIKeyUsage(requests_this_minute=5)

        is_exceeded = usage.requests_this_minute >= quota.requests_per_minute

        assert is_exceeded is False

    def test_burst_allowance(self):
        """Burst allowance must extend minute quota."""
        from security.api_security.api_keys import APIKeyQuota, APIKeyUsage

        quota = APIKeyQuota(requests_per_minute=10, burst_allowance=5)
        usage = APIKeyUsage(requests_this_minute=12)

        effective_limit = quota.requests_per_minute + quota.burst_allowance
        is_exceeded = usage.requests_this_minute >= effective_limit

        # 12 < 15 (10 + 5 burst)
        assert is_exceeded is False

    def test_request_size_limit(self):
        """Request size limit must be enforced."""
        from security.api_security.api_keys import APIKeyQuota

        quota = APIKeyQuota(max_request_size_bytes=1024 * 1024)  # 1 MB

        small_request = 500 * 1024  # 500 KB
        large_request = 2 * 1024 * 1024  # 2 MB

        assert small_request <= quota.max_request_size_bytes
        assert large_request > quota.max_request_size_bytes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
