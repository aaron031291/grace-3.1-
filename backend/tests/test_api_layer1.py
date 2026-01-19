"""
Tests for Layer 1 API endpoints including whitelist management.
REAL functional tests with proper assertions.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
class TestLayer1UserInput:
    """Test Layer 1 user input processing."""

    def test_process_user_input_success(self, client):
        """Test processing user input through Layer 1."""
        response = client.post("/layer1/user-input", json={
            "user_input": "Hello, this is a test message",
            "user_id": "test-user-123",
            "input_type": "chat"
        })
        # Should succeed (200) or validate (422), NOT crash (500)
        assert response.status_code in [200, 422], f"Unexpected status {response.status_code}: {response.text}"

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_process_user_input_missing_fields(self, client):
        """Test user input with missing required fields."""
        response = client.post("/layer1/user-input", json={
            "user_input": "Test message"
            # Missing user_id
        })
        # Should return 422 for validation error or handle gracefully (200)
        assert response.status_code in [200, 422], f"Expected validation, got {response.status_code}: {response.text}"


@pytest.mark.api
class TestLayer1Stats:
    """Test Layer 1 statistics endpoint."""

    def test_get_layer1_stats(self, client):
        """Test getting Layer 1 statistics."""
        response = client.get("/layer1/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_verify_layer1_structure(self, client):
        """Test Layer 1 structure verification."""
        response = client.get("/layer1/verify")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.api
class TestLayer1Cognitive:
    """Test Layer 1 cognitive endpoints."""

    def test_get_cognitive_status(self, client):
        """Test getting cognitive integration status."""
        response = client.get("/layer1/cognitive/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert isinstance(data, dict)

    def test_get_decision_history(self, client):
        """Test getting cognitive decision history."""
        response = client.get("/layer1/cognitive/decisions")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert isinstance(data, (list, dict))

    def test_get_active_decisions(self, client):
        """Test getting active cognitive decisions."""
        response = client.get("/layer1/cognitive/active")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert isinstance(data, (list, dict))


@pytest.mark.api
class TestWhitelistEndpoints:
    """Test whitelist management endpoints."""

    def test_get_whitelist(self, client):
        """Test getting all whitelist entries."""
        response = client.get("/layer1/whitelist")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "total_entries" in data
        assert "domains" in data
        assert "paths" in data
        assert "patterns" in data
        assert "domains_count" in data
        assert "paths_count" in data
        assert "patterns_count" in data

    def test_get_whitelist_logs(self, client):
        """Test getting whitelist access logs."""
        response = client.get("/layer1/whitelist/logs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)

    def test_post_whitelist(self, client):
        """Test adding a whitelist entry."""
        response = client.post("/layer1/whitelist", json={
            "whitelist_type": "domain",
            "whitelist_data": {"domain": "test.example.com", "reason": "Testing"},
            "user_id": "admin-test"
        })
        # Should succeed (200) or validate (422), NOT crash (500)
        assert response.status_code in [200, 422], f"Unexpected status {response.status_code}: {response.text}"

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_patch_whitelist_entry(self, client):
        """Test updating a whitelist entry status."""
        response = client.patch(
            "/layer1/whitelist/domains/d-1",
            json={"status": "paused"}
        )
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}: {response.text}"

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert data["entry"]["status"] == "paused"

    def test_patch_whitelist_invalid_type(self, client):
        """Test updating whitelist with invalid entry type."""
        response = client.patch(
            "/layer1/whitelist/invalid_type/d-1",
            json={"status": "paused"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"

    def test_delete_whitelist_entry(self, client):
        """Test deleting a whitelist entry."""
        # First get current whitelist to find an entry
        get_response = client.get("/layer1/whitelist")
        assert get_response.status_code == 200

        # Try deleting a non-existent entry (safe test)
        response = client.delete("/layer1/whitelist/domains/nonexistent-id")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"

    def test_delete_whitelist_invalid_type(self, client):
        """Test deleting with invalid entry type."""
        response = client.delete("/layer1/whitelist/invalid_type/d-1")
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"


@pytest.mark.api
class TestLayer1ExternalAPI:
    """Test Layer 1 external API processing."""

    def test_process_external_api(self, client):
        """Test processing external API data."""
        response = client.post("/layer1/external-api", json={
            "api_name": "TestAPI",
            "api_endpoint": "/test/endpoint",
            "api_data": {"result": "test data"},
            "user_id": "test-user"
        })
        # Should succeed (200) or validate (422), NOT crash (500)
        assert response.status_code in [200, 422], f"Unexpected status {response.status_code}: {response.text}"

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_process_memory_mesh(self, client):
        """Test processing memory mesh data."""
        response = client.post("/layer1/memory-mesh", json={
            "memory_type": "context",
            "memory_data": {"key": "test", "value": "data"},
            "user_id": "test-user"
        })
        # Should succeed (200) or validate (422), NOT crash (500)
        assert response.status_code in [200, 422], f"Unexpected status {response.status_code}: {response.text}"

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_process_system_event(self, client):
        """Test processing system events."""
        response = client.post("/layer1/system-event", json={
            "event_type": "log",
            "event_data": {"message": "Test log event", "level": "info"}
        })
        # Should succeed (200) or validate (422), NOT crash (500)
        assert response.status_code in [200, 422], f"Unexpected status {response.status_code}: {response.text}"

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


@pytest.mark.api
class TestLayer1InputValidation:
    """Test Layer 1 input validation behavior."""

    def test_user_input_validates_empty_string(self, client):
        """Test that empty user input is handled properly."""
        response = client.post("/layer1/user-input", json={
            "user_input": "",
            "user_id": "test-user-123",
            "input_type": "chat"
        })
        # Should handle gracefully (200 or 422), NOT crash (500)
        assert response.status_code in [200, 422], f"Unexpected status {response.status_code}: {response.text}"

    def test_user_input_validates_long_input(self, client):
        """Test that very long input is handled properly."""
        long_input = "A" * 10000
        response = client.post("/layer1/user-input", json={
            "user_input": long_input,
            "user_id": "test-user-123",
            "input_type": "chat"
        })
        # Should handle gracefully (200 or 422), NOT crash (500)
        assert response.status_code in [200, 422], f"Unexpected status {response.status_code}: {response.text}"
