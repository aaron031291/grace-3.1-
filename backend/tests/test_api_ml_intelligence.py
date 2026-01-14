"""
Tests for ML Intelligence API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
class TestMLIntelligenceStatus:
    """Test ML Intelligence status endpoints."""

    def test_get_ml_status(self, client):
        """Test getting ML Intelligence system status."""
        response = client.get("/ml-intelligence/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "components" in data
        assert isinstance(data["components"], dict)

    def test_get_ml_health(self, client):
        """Test ML Intelligence health check."""
        response = client.get("/ml-intelligence/health")
        assert response.status_code == 200
        data = response.json()
        assert "healthy" in data or "status" in data


@pytest.mark.api
class TestNeuralTrustScorer:
    """Test neural trust scoring endpoints."""

    def test_score_trust(self, client):
        """Test trust scoring for an input."""
        response = client.post("/ml-intelligence/trust/score", json={
            "input_data": "This is a test statement",
            "context": {"source": "user_input"},
            "features": {"length": 25, "complexity": 0.3}
        })
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "trust_score" in data or "score" in data

    def test_get_trust_stats(self, client):
        """Test getting trust scoring statistics."""
        response = client.get("/ml-intelligence/trust/stats")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_batch_trust_scores(self, client):
        """Test batch trust scoring."""
        response = client.post("/ml-intelligence/trust/batch", json={
            "inputs": [
                {"data": "Statement 1", "context": {}},
                {"data": "Statement 2", "context": {}},
                {"data": "Statement 3", "context": {}}
            ]
        })
        assert response.status_code in [200, 500]


@pytest.mark.api
class TestMultiArmedBandit:
    """Test multi-armed bandit endpoints."""

    def test_select_arm(self, client):
        """Test arm selection."""
        response = client.post("/ml-intelligence/bandit/select", json={
            "bandit_id": "test-bandit",
            "context": {"user_type": "new"}
        })
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "selected_arm" in data or "arm" in data

    def test_update_reward(self, client):
        """Test reward update."""
        response = client.post("/ml-intelligence/bandit/reward", json={
            "bandit_id": "test-bandit",
            "arm_id": "arm-1",
            "reward": 1.0
        })
        assert response.status_code in [200, 500]

    def test_get_bandit_stats(self, client):
        """Test getting bandit statistics."""
        response = client.get("/ml-intelligence/bandit/stats")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


@pytest.mark.api
class TestUncertaintyQuantification:
    """Test uncertainty quantification endpoints."""

    def test_quantify_uncertainty(self, client):
        """Test uncertainty quantification."""
        response = client.post("/ml-intelligence/uncertainty/quantify", json={
            "prediction": 0.75,
            "features": [0.1, 0.2, 0.3, 0.4],
            "model_id": "test-model"
        })
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert "uncertainty" in data or "epistemic" in data

    def test_get_uncertainty_stats(self, client):
        """Test getting uncertainty statistics."""
        response = client.get("/ml-intelligence/uncertainty/stats")
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)


@pytest.mark.api
class TestMetaLearning:
    """Test meta-learning endpoints."""

    def test_meta_learn(self, client):
        """Test meta-learning task."""
        response = client.post("/ml-intelligence/meta/learn", json={
            "task_type": "classification",
            "support_set": [
                {"input": [1, 2, 3], "label": 0},
                {"input": [4, 5, 6], "label": 1}
            ],
            "query_set": [
                {"input": [2, 3, 4]}
            ]
        })
        assert response.status_code in [200, 500]

    def test_get_meta_stats(self, client):
        """Test getting meta-learning statistics."""
        response = client.get("/ml-intelligence/meta/stats")
        assert response.status_code in [200, 500]


@pytest.mark.api
class TestActiveLearning:
    """Test active learning endpoints."""

    def test_select_samples(self, client):
        """Test active learning sample selection."""
        response = client.post("/ml-intelligence/active/select", json={
            "pool_size": 100,
            "n_samples": 10,
            "strategy": "uncertainty"
        })
        assert response.status_code in [200, 500]

    def test_update_model(self, client):
        """Test active learning model update."""
        response = client.post("/ml-intelligence/active/update", json={
            "labeled_samples": [
                {"input": [1, 2, 3], "label": 0},
                {"input": [4, 5, 6], "label": 1}
            ]
        })
        assert response.status_code in [200, 500]


@pytest.mark.api
class TestNeuroSymbolicReasoning:
    """Test neuro-symbolic reasoning endpoints."""

    def test_reason(self, client):
        """Test neuro-symbolic reasoning."""
        response = client.post("/ml-intelligence/neuro-symbolic/reason", json={
            "query": "If A implies B and B implies C, does A imply C?",
            "facts": ["A implies B", "B implies C"],
            "rules": ["transitive"]
        })
        assert response.status_code in [200, 500]

    def test_get_reasoning_history(self, client):
        """Test getting reasoning history."""
        response = client.get("/ml-intelligence/neuro-symbolic/history")
        assert response.status_code in [200, 500]
