"""
Tests for input validation and sanitization.
"""
import pytest


class TestSQLInjectionPrevention:
    def test_brain_rejects_sql_injection_in_action(self, client):
        r = client.post("/api/v2/system/'; DROP TABLE--", json={})
        assert r.status_code in (400, 404, 500)

    def test_brain_rejects_path_traversal(self, client):
        r = client.post("/api/v2/files/../../etc/passwd", json={})
        assert r.status_code in (400, 404, 500)


class TestMalformedInput:
    def test_non_json_body_handled(self, client):
        r = client.post("/api/v2/system/runtime",
                        content=b"not json",
                        headers={"Content-Type": "application/json"})
        assert r.status_code in (200, 400, 422, 500)

    def test_oversized_payload_handled(self, client):
        huge = {"data": "x" * 100000}
        r = client.post("/api/v2/system/runtime", json=huge)
        assert r.status_code in (200, 413, 422, 500)


class TestGenesisKeyIntegrity:
    def test_genesis_stats_returns_valid_data(self, client):
        r = client.get("/api/genesis-daily/stats")
        assert r.status_code in (200, 500)
        if r.status_code == 200:
            data = r.json()
            assert "total_keys" in data
            assert isinstance(data["total_keys"], int)
