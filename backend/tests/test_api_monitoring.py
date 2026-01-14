"""
Tests for Monitoring API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
class TestMonitoringOrgans:
    """Test monitoring organs (development progress) endpoints."""

    def test_get_organs_status(self, client):
        """Test getting organs development status."""
        response = client.get("/monitoring/organs")
        assert response.status_code == 200
        data = response.json()
        assert "organs" in data
        assert "overall_progress" in data
        assert isinstance(data["organs"], list)

        # Verify organ structure
        if data["organs"]:
            organ = data["organs"][0]
            assert "id" in organ
            assert "name" in organ
            assert "percentage" in organ
            assert "status" in organ


@pytest.mark.api
class TestMonitoringHealth:
    """Test monitoring health endpoints."""

    def test_get_system_health(self, client):
        """Test getting system health."""
        response = client.get("/monitoring/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert data["status"] in ["healthy", "degraded", "partial", "unhealthy"]


@pytest.mark.api
class TestMonitoringMetrics:
    """Test monitoring metrics endpoints."""

    def test_get_realtime_metrics(self, client):
        """Test getting real-time metrics."""
        response = client.get("/monitoring/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "cpu_usage" in data
        assert "memory_usage" in data
        assert "disk_usage" in data
        assert "timestamp" in data


@pytest.mark.api
class TestMonitoringComponents:
    """Test monitoring component status endpoints."""

    def test_get_component_status(self, client):
        """Test getting component status."""
        response = client.get("/monitoring/components")
        assert response.status_code == 200
        data = response.json()
        assert "components" in data
        assert "total" in data
        assert "healthy" in data


@pytest.mark.api
class TestMonitoringActivity:
    """Test monitoring activity endpoints."""

    def test_get_recent_activity(self, client):
        """Test getting recent activity."""
        response = client.get("/monitoring/activity")
        assert response.status_code == 200
        data = response.json()
        assert "activities" in data
        assert isinstance(data["activities"], list)

    def test_get_activity_with_limit(self, client):
        """Test getting activity with limit."""
        response = client.get("/monitoring/activity?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["activities"]) <= 5
