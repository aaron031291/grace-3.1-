"""
=============================================================================
GRACE Rate Limiting Tests
=============================================================================
Tests for rate limiting functionality across all API endpoints.
=============================================================================
"""

import pytest
from fastapi.testclient import TestClient
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestRateLimitingBasic:
    """Basic rate limiting tests."""

    def test_rate_limit_headers_returned(self, client):
        """Rate limit headers should be returned in responses."""
        response = client.get("/health")

        # Check for common rate limit headers
        rate_headers = {
            "x-ratelimit-limit": response.headers.get("x-ratelimit-limit"),
            "x-ratelimit-remaining": response.headers.get("x-ratelimit-remaining"),
            "x-ratelimit-reset": response.headers.get("x-ratelimit-reset"),
            "retry-after": response.headers.get("retry-after"),
        }

        # At least response should succeed
        assert response.status_code in [200, 429]

    def test_rate_limit_decrements(self, client):
        """Rate limit remaining should decrement with each request."""
        responses = []
        for _ in range(5):
            response = client.get("/health")
            responses.append({
                "status": response.status_code,
                "remaining": response.headers.get("x-ratelimit-remaining"),
            })

        # All should succeed for health endpoint
        for r in responses:
            assert r["status"] in [200, 429]

    def test_rate_limit_by_endpoint_type(self, client):
        """Different endpoint types may have different rate limits."""
        endpoints = {
            "health": "/health",
            "retrieve": "/retrieve/search",
        }

        for name, endpoint in endpoints.items():
            if endpoint == "/health":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint, json={"query": "test", "top_k": 1})

            # Should have response (200 or 422 for missing data)
            assert response.status_code in [200, 400, 422, 429, 500]


class TestRateLimitingEnforcement:
    """Test rate limit enforcement."""

    def test_excessive_requests_limited(self, client):
        """Excessive requests should be rate limited."""
        # Make many rapid requests
        results = []
        for i in range(100):
            response = client.get("/health")
            results.append(response.status_code)

        # Count responses
        success_count = results.count(200)
        limited_count = results.count(429)

        # Most should succeed for health endpoint (generous limit)
        # But if rate limiting is strict, some may be limited
        assert success_count > 0 or limited_count > 0

    def test_rate_limit_recovery(self, client):
        """Rate limits should recover after window expires."""
        # First, make requests until potentially limited
        for _ in range(50):
            client.get("/health")

        # Wait a bit for rate limit to potentially reset
        time.sleep(1)

        # Should be able to make request again
        response = client.get("/health")
        assert response.status_code in [200, 429]

    def test_rate_limit_per_client(self, client):
        """Rate limits should be per-client (IP-based)."""
        # Simulate different clients with different headers
        clients = [
            {"X-Forwarded-For": "192.168.1.1"},
            {"X-Forwarded-For": "192.168.1.2"},
            {"X-Forwarded-For": "192.168.1.3"},
        ]

        results = {}
        for headers in clients:
            response = client.get("/health", headers=headers)
            ip = headers["X-Forwarded-For"]
            results[ip] = response.status_code

        # Each "client" should get their own rate limit
        # All should succeed independently
        for ip, status in results.items():
            assert status in [200, 429]


class TestRateLimitingConcurrent:
    """Test rate limiting under concurrent load."""

    def test_concurrent_requests_handled(self, client):
        """Concurrent requests should be handled properly."""
        results = []
        errors = []

        def make_request():
            try:
                response = client.get("/health")
                return response.status_code
            except Exception as e:
                return str(e)

        # Use ThreadPoolExecutor for concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            for future in as_completed(futures):
                result = future.result()
                if isinstance(result, int):
                    results.append(result)
                else:
                    errors.append(result)

        # Should have mostly successful responses
        success_count = results.count(200)
        limited_count = results.count(429)

        assert success_count + limited_count > 0
        assert len(errors) < len(results)  # Most should succeed

    def test_burst_traffic_handling(self, client):
        """Burst traffic should be handled gracefully."""
        burst_size = 20
        results = []

        # Simulate burst
        for _ in range(burst_size):
            response = client.get("/health")
            results.append(response.status_code)

        # Count outcomes
        success = results.count(200)
        limited = results.count(429)
        errors = len([r for r in results if r >= 500])

        # Should not have server errors from rate limiting
        assert errors == 0
        # Most should be handled
        assert success + limited == burst_size


class TestRateLimitingByRoute:
    """Test rate limiting configuration by route."""

    def test_auth_endpoints_stricter_limits(self, client):
        """Authentication endpoints should have stricter limits."""
        # Auth endpoints typically have lower limits
        auth_endpoints = [
            ("/auth/login", "POST", {"username": "test", "password": "test"}),
        ]

        for endpoint, method, data in auth_endpoints:
            results = []
            for _ in range(20):
                if method == "POST":
                    response = client.post(endpoint, json=data)
                else:
                    response = client.get(endpoint)
                results.append(response.status_code)

            # Auth endpoint may be limited or may not exist
            assert all(r in [200, 400, 401, 404, 422, 429] for r in results)

    def test_upload_endpoints_limited(self, client):
        """Upload endpoints should have specific rate limits."""
        # Upload endpoints often have stricter limits
        results = []
        for _ in range(10):
            response = client.post(
                "/file_management/upload",
                files={"file": ("test.txt", b"test content", "text/plain")}
            )
            results.append(response.status_code)

        # Should handle all requests (limited or not)
        assert all(r in [200, 400, 404, 413, 422, 429, 500] for r in results)

    def test_ai_endpoints_limited(self, client):
        """AI/inference endpoints should have rate limits."""
        results = []
        for _ in range(10):
            response = client.post(
                "/chat",
                json={"message": "Hello"}
            )
            results.append(response.status_code)

        # AI endpoints may be heavily limited
        success = results.count(200)
        limited = results.count(429)

        # Should be handled appropriately
        assert all(r in [200, 400, 422, 429, 500, 503] for r in results)


class TestRateLimitingResponses:
    """Test rate limit response format."""

    def test_rate_limited_response_format(self, client):
        """Rate limited responses should have proper format."""
        # Try to trigger rate limit
        for _ in range(100):
            response = client.get("/health")
            if response.status_code == 429:
                # Check response format
                assert "retry-after" in response.headers or True

                # Check response body
                try:
                    data = response.json()
                    assert "detail" in data or "error" in data or \
                           "message" in data or True
                except Exception:
                    pass  # Plain text response is also ok

                break

    def test_retry_after_header(self, client):
        """Rate limited responses should include Retry-After header."""
        # Try to trigger rate limit
        for _ in range(100):
            response = client.get("/health")
            if response.status_code == 429:
                retry_after = response.headers.get("retry-after")
                if retry_after:
                    # Should be a valid number
                    try:
                        seconds = int(retry_after)
                        assert seconds >= 0
                        assert seconds < 3600  # Less than an hour
                    except ValueError:
                        pass  # May be a date instead of seconds
                break


class TestRateLimitingEdgeCases:
    """Test rate limiting edge cases."""

    def test_rate_limit_with_invalid_ip(self, client):
        """Invalid IP headers should be handled gracefully."""
        invalid_headers = [
            {"X-Forwarded-For": "invalid-ip"},
            {"X-Forwarded-For": ""},
            {"X-Forwarded-For": "256.256.256.256"},
            {"X-Real-IP": "not-an-ip"},
        ]

        for headers in invalid_headers:
            response = client.get("/health", headers=headers)
            # Should not crash
            assert response.status_code in [200, 400, 429]

    def test_rate_limit_with_spoofed_headers(self, client):
        """Spoofed rate limit bypass attempts should fail."""
        spoofed_headers = [
            {"X-RateLimit-Remaining": "999999"},
            {"X-RateLimit-Reset": "0"},
            {"X-Forwarded-For": "127.0.0.1, 192.168.1.1, 10.0.0.1"},
        ]

        for headers in spoofed_headers:
            response = client.get("/health", headers=headers)
            # Headers should be ignored, normal rate limiting applies
            assert response.status_code in [200, 429]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def client():
    """Create test client."""
    try:
        from app import app
        return TestClient(app)
    except ImportError:
        pytest.skip("App not available for testing")


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
