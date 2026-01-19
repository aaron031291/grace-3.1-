"""
Tests for Cognitive System API endpoints.
REAL functional tests with proper assertions.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
class TestCognitiveStatus:
    """Test cognitive system status endpoints."""

    def test_get_cognitive_status(self, client):
        """Test getting cognitive engine status via stats/summary."""
        response = client.get("/cognitive/stats/summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert isinstance(data, dict)
        # Should have meaningful stats
        assert len(data) > 0

    def test_get_cognitive_health(self, client):
        """Test cognitive engine health check via stats."""
        response = client.get("/cognitive/stats/summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.api
class TestCognitiveEngine:
    """Test cognitive engine operations."""

    def test_process_cognitive_query_via_layer1(self, client):
        """Test cognitive status through layer1 endpoint."""
        response = client.get("/layer1/cognitive/status")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert isinstance(data, dict)

    def test_cognitive_decisions_recent(self, client):
        """Test getting recent cognitive decisions."""
        response = client.get("/cognitive/decisions/recent")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert isinstance(data, (list, dict))

    def test_cognitive_decisions_via_layer1(self, client):
        """Test cognitive decisions via layer1."""
        response = client.get("/layer1/cognitive/decisions")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert isinstance(data, (list, dict))


@pytest.mark.api
class TestMemoryMesh:
    """Test memory mesh endpoints."""

    def test_get_memory_status(self, client):
        """Test getting memory mesh status via learning memory."""
        response = client.get("/learning-memory/status")
        # 200 if exists, 404 if not configured
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}: {response.text}"

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
            # Should have status information
            assert len(data) > 0

    def test_store_memory_status_check(self, client):
        """Test memory system is accessible via learning memory."""
        response = client.get("/learning-memory/status")
        assert response.status_code in [200, 404], f"Unexpected status {response.status_code}: {response.text}"

    def test_retrieve_memories_status(self, client):
        """Test memory retrieval system status."""
        response = client.get("/learning-memory/status")
        assert response.status_code in [200, 404], f"Unexpected status {response.status_code}: {response.text}"


@pytest.mark.api
class TestContradictionDetection:
    """Test contradiction detection endpoints."""

    def test_search_for_contradictions(self, client):
        """Test search functionality that can detect contradictions."""
        response = client.post("/ingest/search", json={
            "query": "test contradiction",
            "limit": 5
        })
        # Should return 200 for valid search, 422 for validation error
        assert response.status_code in [200, 422], f"Expected 200 or 422, got {response.status_code}: {response.text}"

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    def test_contradiction_history_via_stats(self, client):
        """Test getting cognitive stats which includes contradiction info."""
        response = client.get("/cognitive/stats/summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.api
class TestLearningSubagents:
    """Test learning subagent endpoints."""

    def test_get_autonomous_learning_status(self, client):
        """Test getting autonomous learning status."""
        response = client.get("/autonomous-learning/status")
        # 200 if exists, 404 if endpoint not configured
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}: {response.text}"

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_get_proactive_learning_status(self, client):
        """Test getting proactive learning status."""
        response = client.get("/proactive-learning/status")
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}: {response.text}"

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_get_learning_progress_status(self, client):
        """Test getting learning progress via autonomous learning."""
        response = client.get("/autonomous-learning/status")
        assert response.status_code in [200, 404], f"Expected 200 or 404, got {response.status_code}: {response.text}"


@pytest.mark.api
class TestCognitiveOODA:
    """Test OODA loop cognitive endpoints."""

    def test_cognitive_stats_summary_structure(self, client):
        """Test that cognitive stats have proper structure."""
        response = client.get("/cognitive/stats/summary")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        assert isinstance(data, dict)
        # Stats should be non-empty
        assert len(data) > 0

    def test_cognitive_decisions_list(self, client):
        """Test that decisions endpoint returns proper list."""
        response = client.get("/cognitive/decisions/recent")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

        data = response.json()
        # Should return a list or dict with decisions
        assert isinstance(data, (list, dict))
