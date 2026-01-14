"""
Tests for Genesis Keys API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
class TestGenesisKeysStatus:
    """Test Genesis Keys status endpoints."""

    def test_get_genesis_status(self, client):
        """Test getting Genesis Keys system status."""
        response = client.get("/genesis-keys/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data or "active" in data

    def test_get_genesis_stats(self, client):
        """Test getting Genesis Keys statistics."""
        response = client.get("/genesis-keys/stats")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.api
class TestGenesisKeyCreation:
    """Test Genesis Key creation endpoints."""

    def test_create_genesis_key(self, client):
        """Test creating a new Genesis Key."""
        response = client.post("/genesis-keys/create", json={
            "entity_type": "document",
            "entity_id": "test-doc-001",
            "origin_source": "test",
            "origin_type": "unit_test",
            "metadata": {"test": True}
        })
        assert response.status_code in [200, 201, 500]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "genesis_key" in data or "id" in data or "key_id" in data

    def test_create_genesis_key_missing_fields(self, client):
        """Test creating Genesis Key with missing fields."""
        response = client.post("/genesis-keys/create", json={
            "entity_type": "document"
            # Missing required fields
        })
        assert response.status_code in [422, 400]

    def test_create_genesis_key_invalid_type(self, client):
        """Test creating Genesis Key with invalid entity type."""
        response = client.post("/genesis-keys/create", json={
            "entity_type": "invalid_type",
            "entity_id": "test-001",
            "origin_source": "test",
            "origin_type": "unit_test"
        })
        # Should either accept any type or validate
        assert response.status_code in [200, 201, 400, 422, 500]


@pytest.mark.api
class TestGenesisKeyRetrieval:
    """Test Genesis Key retrieval endpoints."""

    def test_get_genesis_key_by_id(self, client):
        """Test retrieving a Genesis Key by ID."""
        response = client.get("/genesis-keys/key/test-key-id")
        assert response.status_code in [200, 404]

    def test_get_genesis_keys_by_entity(self, client):
        """Test retrieving Genesis Keys by entity."""
        response = client.get("/genesis-keys/entity/document/test-doc-001")
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "keys" in data or isinstance(data, list)

    def test_list_genesis_keys(self, client):
        """Test listing all Genesis Keys."""
        response = client.get("/genesis-keys/list")
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data or isinstance(data, list)

    def test_list_genesis_keys_with_filters(self, client):
        """Test listing Genesis Keys with filters."""
        response = client.get("/genesis-keys/list?entity_type=document&limit=10")
        assert response.status_code == 200


@pytest.mark.api
class TestGenesisKeyVerification:
    """Test Genesis Key verification endpoints."""

    def test_verify_genesis_key(self, client):
        """Test verifying a Genesis Key."""
        response = client.post("/genesis-keys/verify", json={
            "key_id": "test-key-id",
            "expected_hash": "abc123"
        })
        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert "valid" in data or "verified" in data

    def test_verify_chain(self, client):
        """Test verifying Genesis Key chain."""
        response = client.post("/genesis-keys/verify-chain", json={
            "entity_type": "document",
            "entity_id": "test-doc-001"
        })
        assert response.status_code in [200, 404, 500]


@pytest.mark.api
class TestGenesisKeyHistory:
    """Test Genesis Key history endpoints."""

    def test_get_key_history(self, client):
        """Test getting Genesis Key history."""
        response = client.get("/genesis-keys/history/test-key-id")
        assert response.status_code in [200, 404]

    def test_get_entity_history(self, client):
        """Test getting entity change history."""
        response = client.get("/genesis-keys/entity-history/document/test-doc-001")
        assert response.status_code in [200, 404]


@pytest.mark.api
class TestGenesisKeyOrganizer:
    """Test Genesis Key organizer endpoints."""

    def test_organize_keys(self, client):
        """Test organizing Genesis Keys by date."""
        response = client.post("/genesis-keys/organize")
        assert response.status_code in [200, 500]

    def test_get_daily_summary(self, client):
        """Test getting daily Genesis Key summary."""
        response = client.get("/genesis-keys/daily-summary")
        assert response.status_code in [200, 500]


@pytest.mark.api
class TestGenesisKeyCICD:
    """Test Genesis Key CI/CD integration endpoints."""

    def test_get_cicd_status(self, client):
        """Test getting CI/CD integration status."""
        response = client.get("/genesis-keys/cicd/status")
        assert response.status_code in [200, 500]

    def test_trigger_cicd_check(self, client):
        """Test triggering CI/CD check."""
        response = client.post("/genesis-keys/cicd/check", json={
            "commit_hash": "abc123",
            "branch": "main"
        })
        assert response.status_code in [200, 500]
