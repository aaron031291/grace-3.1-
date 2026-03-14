"""
Tests for backend/api/layer1_api.py

Covers every endpoint with full request/response logic validation.
"""
import sys
import importlib
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

# Import the module directly to avoid pulling the entire backend.api package
# (which has transitive dependencies that may not be installed in test env).
_spec = importlib.util.spec_from_file_location(
    "layer1_api",
    str(__import__("pathlib").Path(__file__).resolve().parents[3] / "backend" / "api" / "layer1_api.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
router = _mod.router


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── POST /layer1/user-input ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_user_input_returns_ok(client):
    resp = await client.post("/layer1/user-input", json={"message": "hello"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_user_input_empty_payload(client):
    resp = await client.post("/layer1/user-input", json={})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── GET /layer1/stats ───────────────────────────────────────────────────

@pytest.mark.anyio
async def test_stats(client):
    resp = await client.get("/layer1/stats")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── GET /layer1/verify ──────────────────────────────────────────────────

@pytest.mark.anyio
async def test_verify(client):
    resp = await client.get("/layer1/verify")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── GET /layer1/cognitive/status ─────────────────────────────────────────

@pytest.mark.anyio
async def test_cognitive_status(client):
    resp = await client.get("/layer1/cognitive/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["active"] is True


# ── GET /layer1/cognitive/decisions ──────────────────────────────────────

@pytest.mark.anyio
async def test_cognitive_decisions(client):
    resp = await client.get("/layer1/cognitive/decisions")
    assert resp.status_code == 200
    assert resp.json() == {"decisions": []}


# ── GET /layer1/cognitive/active ─────────────────────────────────────────

@pytest.mark.anyio
async def test_active_decisions(client):
    resp = await client.get("/layer1/cognitive/active")
    assert resp.status_code == 200
    assert resp.json() == {"decisions": []}


# ── GET /layer1/whitelist ────────────────────────────────────────────────

@pytest.mark.anyio
async def test_get_whitelist(client):
    resp = await client.get("/layer1/whitelist")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_entries"] == 0
    assert data["domains"] == []
    assert data["paths"] == []
    assert data["patterns"] == []
    assert data["domains_count"] == 0
    assert data["paths_count"] == 0
    assert data["patterns_count"] == 0


# ── GET /layer1/whitelist/logs ───────────────────────────────────────────

@pytest.mark.anyio
async def test_whitelist_logs(client):
    resp = await client.get("/layer1/whitelist/logs")
    assert resp.status_code == 200
    assert resp.json() == {"logs": []}


# ── POST /layer1/whitelist ───────────────────────────────────────────────

@pytest.mark.anyio
async def test_add_whitelist_entry(client):
    resp = await client.post("/layer1/whitelist", json={"domain": "example.com"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── PATCH /layer1/whitelist/domains/{domain_id} ─────────────────────────

@pytest.mark.anyio
async def test_patch_domain_with_status(client):
    resp = await client.patch(
        "/layer1/whitelist/domains/d-123",
        json={"status": "blocked"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["entry"]["status"] == "blocked"


@pytest.mark.anyio
async def test_patch_domain_without_status_key(client):
    resp = await client.patch(
        "/layer1/whitelist/domains/d-456",
        json={"other": "value"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["entry"]["status"] is None


# ── PATCH /layer1/whitelist/invalid_type/{id} ────────────────────────────

@pytest.mark.anyio
async def test_patch_invalid_type_returns_400(client):
    resp = await client.patch(
        "/layer1/whitelist/invalid_type/x-1",
        json={"status": "active"},
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid type"


# ── DELETE /layer1/whitelist/domains/{domain_id} ─────────────────────────

@pytest.mark.anyio
async def test_delete_domain_returns_404(client):
    resp = await client.delete("/layer1/whitelist/domains/d-999")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Not found"


# ── DELETE /layer1/whitelist/invalid_type/{id} ───────────────────────────

@pytest.mark.anyio
async def test_delete_invalid_type_returns_400(client):
    resp = await client.delete("/layer1/whitelist/invalid_type/x-1")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Invalid type"


# ── POST /layer1/external-api ───────────────────────────────────────────

@pytest.mark.anyio
async def test_external_api(client):
    resp = await client.post("/layer1/external-api", json={"url": "https://api.example.com"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── POST /layer1/memory-mesh ────────────────────────────────────────────

@pytest.mark.anyio
async def test_memory_mesh(client):
    resp = await client.post("/layer1/memory-mesh", json={"mesh_data": [1, 2, 3]})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── POST /layer1/system-event ───────────────────────────────────────────

@pytest.mark.anyio
async def test_system_event(client):
    resp = await client.post("/layer1/system-event", json={"event": "restart"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
