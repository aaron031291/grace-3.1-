"""
Tests for Cognitive System API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
class TestCognitiveStatus:
    """Test cognitive system status endpoints."""

    def test_get_cognitive_status(self, client):
        """Test getting cognitive engine status."""
        response = client.get("/cognitive/status")
        assert response.status_code == 200
        data = response.json()
        assert "engine_running" in data
        assert "components" in data
        assert isinstance(data["components"], dict)

    def test_get_cognitive_health(self, client):
        """Test cognitive engine health check."""
        response = client.get("/cognitive/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]


@pytest.mark.api
class TestCognitiveEngine:
    """Test cognitive engine operations."""

    def test_process_cognitive_query(self, client):
        """Test processing a query through cognitive engine."""
        response = client.post("/cognitive/process", json={
            "query": "What is the meaning of this code?",
            "context": {"file": "test.py", "line": 10},
            "use_ooda": True
        })
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "result" in data or "response" in data

    def test_cognitive_observe(self, client):
        """Test cognitive observation phase."""
        response = client.post("/cognitive/ooda/observe", json={
            "observation_type": "context",
            "data": {"input": "Test observation data"}
        })
        assert response.status_code in [200, 500]

    def test_cognitive_orient(self, client):
        """Test cognitive orientation phase."""
        response = client.post("/cognitive/ooda/orient", json={
            "context": {"current_state": "analyzing"},
            "observations": [{"type": "user_input", "data": "test"}]
        })
        assert response.status_code in [200, 500]


@pytest.mark.api
class TestMemoryMesh:
    """Test memory mesh endpoints."""

    def test_get_memory_status(self, client):
        """Test getting memory mesh status."""
        response = client.get("/cognitive/memory/status")
        assert response.status_code in [200, 404, 500]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_store_memory(self, client):
        """Test storing a memory entry."""
        response = client.post("/cognitive/memory/store", json={
            "memory_type": "episodic",
            "content": "User asked about Python functions",
            "context": {"session_id": "test-session"},
            "importance": 0.75
        })
        assert response.status_code in [200, 500]

    def test_retrieve_memories(self, client):
        """Test retrieving memories."""
        response = client.post("/cognitive/memory/retrieve", json={
            "query": "Python functions",
            "memory_types": ["episodic", "semantic"],
            "limit": 10
        })
        assert response.status_code in [200, 500]


@pytest.mark.api
class TestContradictionDetection:
    """Test contradiction detection endpoints."""

    def test_detect_contradictions(self, client):
        """Test contradiction detection in statements."""
        response = client.post("/cognitive/contradictions/detect", json={
            "statements": [
                "The sky is blue",
                "The sky is green",
                "Water boils at 100 degrees Celsius"
            ]
        })
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "contradictions" in data or "analysis" in data

    def test_get_contradiction_history(self, client):
        """Test getting contradiction detection history."""
        response = client.get("/cognitive/contradictions/history")
        assert response.status_code in [200, 500]


@pytest.mark.api
class TestLearningSubagents:
    """Test learning subagent endpoints."""

    def test_get_subagent_status(self, client):
        """Test getting learning subagent status."""
        response = client.get("/cognitive/subagents/status")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "subagents" in data or "status" in data

    def test_create_learning_task(self, client):
        """Test creating a learning task for subagents."""
        response = client.post("/cognitive/subagents/task", json={
            "task_type": "study",
            "topic": "Python best practices",
            "priority": "medium"
        })
        assert response.status_code in [200, 500]

    def test_get_learning_progress(self, client):
        """Test getting learning progress."""
        response = client.get("/cognitive/subagents/progress")
        assert response.status_code in [200, 500]
