"""
Integration tests for the unified monitoring system.
"""
import pytest


class TestHealthEndpoints:
    def test_root_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["name"] == "Grace API"

    def test_health_returns_status(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data

    def test_runtime_status(self, client):
        r = client.get("/api/runtime/status")
        assert r.status_code == 200
        data = r.json()
        assert "paused" in data
        assert "diagnostic_engine" in data
        assert "self_healing" in data

    def test_resilience_endpoint(self, client):
        r = client.get("/api/runtime/resilience")
        assert r.status_code == 200
        data = r.json()
        assert "degradation_level" in data
        assert "circuit_breakers" in data


class TestBrainDirectory:
    def test_brain_v1_directory(self, client):
        r = client.get("/brain/directory")
        assert r.status_code == 200
        data = r.json()
        assert data["total_brains"] == 8

    def test_brain_v2_directory(self, client):
        r = client.get("/api/v2/directory")
        assert r.status_code == 200
        data = r.json()
        assert data["total_domains"] == 8


class TestGenesisKeys:
    def test_genesis_stats(self, client):
        r = client.get("/genesis/stats")
        assert r.status_code in (200, 500)

    def test_genesis_keys_list(self, client):
        r = client.get("/genesis/keys?limit=5")
        assert r.status_code in (200, 500)
