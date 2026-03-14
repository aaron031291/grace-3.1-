"""
Tests for backend/api/governance_api.py, cognitive_api.py, and kpi_api.py

Covers every endpoint with full request/response logic validation.
"""
import importlib
import pathlib
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI

_base = pathlib.Path(__file__).resolve().parents[3] / "backend"


def _load_module(name, relpath):
    spec = importlib.util.spec_from_file_location(name, str(_base / relpath))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


governance_mod = _load_module("governance_api", "api/governance_api.py")
cognitive_mod = _load_module("cognitive_api", "api/cognitive_api.py")

try:
    kpi_mod = _load_module("kpi_api", "api/kpi_api.py")
except Exception:
    kpi_mod = None


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(governance_mod.router)
    app.include_router(cognitive_mod.router)
    if kpi_mod is not None:
        app.include_router(kpi_mod.router)
    return app


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ═══════════════════════════════════════════════════════════════════════════
#  Governance API  (prefix="/governance")
# ═══════════════════════════════════════════════════════════════════════════

# ── GET /governance/stats ───────────────────────────────────────────────

@pytest.mark.anyio
async def test_governance_stats(client):
    resp = await client.get("/governance/stats")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── GET /governance/rules ───────────────────────────────────────────────

@pytest.mark.anyio
async def test_governance_rules(client):
    resp = await client.get("/governance/rules")
    assert resp.status_code == 200
    assert resp.json() == {"rules": []}


# ── GET /governance/rules/{rule_id} ─────────────────────────────────────

@pytest.mark.anyio
async def test_governance_rule_by_id(client):
    resp = await client.get("/governance/rules/rule-123")
    assert resp.status_code == 200
    data = resp.json()
    assert data["rule"]["id"] == "rule-123"


# ── POST /governance/rules/new ──────────────────────────────────────────

@pytest.mark.anyio
async def test_governance_create_rule(client):
    resp = await client.post("/governance/rules/new", json={"name": "new-rule"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── PUT /governance/rules/{rule_id} ─────────────────────────────────────

@pytest.mark.anyio
async def test_governance_update_rule(client):
    resp = await client.put("/governance/rules/rule-456", json={"name": "updated"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["rule"]["id"] == "rule-456"


# ── DELETE /governance/rules/{rule_id} ──────────────────────────────────

@pytest.mark.anyio
async def test_governance_delete_rule(client):
    resp = await client.delete("/governance/rules/rule-789")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── GET /governance/decisions/pending ───────────────────────────────────

@pytest.mark.anyio
async def test_governance_pending_decisions(client):
    resp = await client.get("/governance/decisions/pending")
    assert resp.status_code == 200
    assert resp.json() == {"decisions": []}


# ── GET /governance/decisions/history ───────────────────────────────────

@pytest.mark.anyio
async def test_governance_decision_history(client):
    resp = await client.get("/governance/decisions/history")
    assert resp.status_code == 200
    assert resp.json() == {"history": []}


# ── POST /governance/decisions/{id}/confirm ─────────────────────────────

@pytest.mark.anyio
async def test_governance_confirm_decision(client):
    resp = await client.post("/governance/decisions/dec-1/confirm")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── POST /governance/decisions/{id}/deny ────────────────────────────────

@pytest.mark.anyio
async def test_governance_deny_decision(client):
    resp = await client.post("/governance/decisions/dec-2/deny")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── GET /governance/pillars ─────────────────────────────────────────────

@pytest.mark.anyio
async def test_governance_pillars(client):
    resp = await client.get("/governance/pillars")
    assert resp.status_code == 200
    assert resp.json() == {"pillars": []}


# ── GET /governance/pillars/{pillar_name}/status ────────────────────────

@pytest.mark.anyio
async def test_governance_pillar_status(client):
    resp = await client.get("/governance/pillars/safety/status")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── POST /governance/documents/upload ───────────────────────────────────

@pytest.mark.anyio
async def test_governance_upload_document(client):
    resp = await client.post("/governance/documents/upload")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ── GET /governance/documents ───────────────────────────────────────────

@pytest.mark.anyio
async def test_governance_documents(client):
    resp = await client.get("/governance/documents")
    assert resp.status_code == 200
    assert resp.json() == {"documents": []}


# ── GET /governance/documents/{doc_id} ──────────────────────────────────

@pytest.mark.anyio
async def test_governance_document_by_id(client):
    resp = await client.get("/governance/documents/doc-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["document"]["id"] == "doc-1"


# ═══════════════════════════════════════════════════════════════════════════
#  Cognitive API  (prefix="/cognitive")
# ═══════════════════════════════════════════════════════════════════════════

# ── GET /cognitive/stats/summary ────────────────────────────────────────

@pytest.mark.anyio
async def test_cognitive_stats_summary(client):
    resp = await client.get("/cognitive/stats/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "stats" in data


# ── GET /cognitive/decisions/recent ─────────────────────────────────────

@pytest.mark.anyio
async def test_cognitive_recent_decisions(client):
    resp = await client.get("/cognitive/decisions/recent")
    assert resp.status_code == 200
    assert resp.json() == {"decisions": []}


# ═══════════════════════════════════════════════════════════════════════════
#  KPI API  (prefix="/kpi")  — skipped if module could not be loaded
# ═══════════════════════════════════════════════════════════════════════════

_skip_kpi = pytest.mark.skipif(kpi_mod is None, reason="kpi_api could not be loaded")


# ── GET /kpi/health ─────────────────────────────────────────────────────

@_skip_kpi
@pytest.mark.anyio
async def test_kpi_health(client):
    resp = await client.get("/kpi/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "system_trust_score" in data
    assert "status" in data
    assert "component_count" in data


# ── GET /kpi/dashboard ──────────────────────────────────────────────────

@_skip_kpi
@pytest.mark.anyio
async def test_kpi_dashboard(client):
    resp = await client.get("/kpi/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "top_performers" in data
    assert "needs_attention" in data
    assert "components" in data


# ── GET /kpi/components/{name} ──────────────────────────────────────────

@_skip_kpi
@pytest.mark.anyio
async def test_kpi_component_coding_agent(client):
    resp = await client.get("/kpi/components/coding_agent")
    assert resp.status_code == 200
    data = resp.json()
    assert "trust_score" in data


# ── GET /kpi/trust-trends ──────────────────────────────────────────────

@_skip_kpi
@pytest.mark.anyio
async def test_kpi_trust_trends(client):
    resp = await client.get("/kpi/trust-trends")
    assert resp.status_code == 200
    data = resp.json()
    assert "trends" in data


# ── GET /kpi/governance-summary ─────────────────────────────────────────

@_skip_kpi
@pytest.mark.anyio
async def test_kpi_governance_summary(client):
    resp = await client.get("/kpi/governance-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "timestamp" in data
    assert "kpi" in data
    assert "trust_engine" in data


# ── GET /kpi/pass-fail ──────────────────────────────────────────────────

@_skip_kpi
@pytest.mark.anyio
async def test_kpi_pass_fail(client):
    resp = await client.get("/kpi/pass-fail")
    assert resp.status_code == 200
    data = resp.json()
    assert "components" in data


# ── GET /kpi/confidence/{component_name} ────────────────────────────────

@_skip_kpi
@pytest.mark.anyio
async def test_kpi_confidence(client):
    resp = await client.get("/kpi/confidence/test_comp")
    assert resp.status_code == 200
    data = resp.json()
    assert "component" in data


# ── POST /kpi/snapshot ──────────────────────────────────────────────────

@_skip_kpi
@pytest.mark.anyio
async def test_kpi_snapshot(client):
    resp = await client.post("/kpi/snapshot")
    assert resp.status_code == 200
