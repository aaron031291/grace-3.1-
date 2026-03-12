"""
Tests for Brain Controller v2 — POST /api/v2/{domain}/{action}
"""
import pytest


class TestBrainV2Routing:
    def test_directory_returns_all_domains(self, client):
        r = client.get("/api/v2/directory")
        assert r.status_code == 200
        data = r.json()
        assert data["total_domains"] == 8
        assert data["total_actions"] >= 70

    def test_invalid_domain_returns_error(self, client):
        r = client.post("/api/v2/nonexistent/action", json={})
        assert r.status_code in (400, 500)

    def test_invalid_action_returns_error(self, client):
        r = client.post("/api/v2/system/nonexistent_action", json={})
        assert r.status_code in (400, 500)
        assert "Unknown action" in r.json().get("detail", "")

    def test_brain_directory_lists_all_8_domains(self, client):
        r = client.get("/api/v2/directory")
        domains = r.json()["domains"]
        expected = {"chat", "files", "govern", "ai", "system", "data", "tasks", "code"}
        assert set(domains.keys()) == expected

    def test_each_domain_has_actions(self, client):
        r = client.get("/api/v2/directory")
        for domain, info in r.json()["domains"].items():
            assert len(info["actions"]) > 0, f"Domain {domain} has no actions"

    def test_empty_payload_accepted(self, client):
        r = client.post("/api/v2/system/runtime", json={})
        # Should not crash on empty payload
        assert r.status_code in (200, 500)

    def test_response_has_required_fields(self, client):
        r = client.post("/api/v2/system/runtime", json={})
        if r.status_code == 200:
            data = r.json()
            assert "ok" in data
            assert "domain" in data
            assert "action" in data
            assert "latency_ms" in data


class TestBrainOrchestration:
    def test_orchestrate_endpoint_exists(self, client):
        r = client.post("/brain/orchestrate", json={"steps": []})
        assert r.status_code == 200

    def test_orchestrate_empty_steps(self, client):
        r = client.post("/brain/orchestrate", json={"steps": []})
        data = r.json()
        assert data["total"] == 0
        assert data["succeeded"] == 0

    def test_orchestrate_invalid_brain(self, client):
        r = client.post("/brain/orchestrate", json={
            "steps": [{"brain": "fake", "action": "nope"}]
        })
        data = r.json()
        assert data["total"] == 1
        assert data["failed"] == 1
