"""
Real logic tests for critical GRACE API endpoints.
Uses FastAPI TestClient with mocked external dependencies.
"""
import sys
import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from starlette.testclient import TestClient


# ─── 1. Health API (/health) ──────────────────────────────────────────────

class TestHealthAPI:
    """Tests for api/health.py"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from api.health import router
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_liveness_returns_alive(self):
        resp = self.client.get("/health/live")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "alive"
        assert "timestamp" in body

    @patch("api.health.check_llm")
    @patch("api.health.check_database")
    @patch("api.health.check_qdrant")
    @patch("api.health.check_embedding_model")
    @patch("api.health.check_memory")
    @patch("api.health.check_disk")
    def test_full_health_all_healthy(self, mock_disk, mock_mem, mock_embed,
                                     mock_qdrant, mock_db, mock_llm):
        from api.health import ServiceHealth
        healthy = ServiceHealth(name="test", status="healthy", latency_ms=1.0)
        for m in [mock_llm, mock_db, mock_qdrant, mock_embed, mock_mem, mock_disk]:
            m.return_value = healthy

        resp = self.client.get("/health/full")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["summary"]["healthy"] == 6
        assert body["summary"]["unhealthy"] == 0
        assert "uptime_seconds" in body

    @patch("api.health.check_llm")
    @patch("api.health.check_database")
    @patch("api.health.check_qdrant")
    @patch("api.health.check_embedding_model")
    @patch("api.health.check_memory")
    @patch("api.health.check_disk")
    def test_full_health_degraded_when_one_unhealthy(self, mock_disk, mock_mem,
                                                      mock_embed, mock_qdrant,
                                                      mock_db, mock_llm):
        from api.health import ServiceHealth
        healthy = ServiceHealth(name="ok", status="healthy", latency_ms=1.0)
        sick = ServiceHealth(name="db", status="unhealthy", message="down")
        mock_llm.return_value = healthy
        mock_db.return_value = sick
        mock_qdrant.return_value = healthy
        mock_embed.return_value = healthy
        mock_mem.return_value = healthy
        mock_disk.return_value = healthy

        resp = self.client.get("/health/full")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "unhealthy"
        assert body["summary"]["unhealthy"] == 1

    def test_readiness_fails_when_db_down(self):
        mock_mod = MagicMock()
        mock_mod.SessionLocal.side_effect = Exception("DB down")
        with patch.dict(sys.modules, {"database.session": mock_mod, "sqlalchemy": MagicMock()}):
            resp = self.client.get("/health/ready")
            assert resp.status_code == 503


# ─── 2. System Health API (/api/system-health) ───────────────────────────

class TestSystemHealthAPI:
    """Tests for api/system_health_api.py"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from api.system_health_api import router
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_dashboard_returns_structure(self):
        mem = MagicMock(percent=45.0, used=8*(1024**3), total=16*(1024**3))
        disk = MagicMock(percent=50.0, used=100*(1024**3), total=500*(1024**3))
        with patch("api.system_health_api.psutil") as mp:
            mp.cpu_percent.return_value = 25.0
            mp.cpu_count.return_value = 8
            mp.virtual_memory.return_value = mem
            mp.disk_usage.return_value = disk
            resp = self.client.get("/api/system-health/dashboard")
        assert resp.status_code == 200
        body = resp.json()
        assert body["overall"] == "healthy"
        assert "resources" in body
        assert body["resources"]["memory_total_gb"] == 16.0

    def test_full_returns_diagnostic_structure(self):
        resp = self.client.get("/api/system-health/full")
        assert resp.status_code == 200
        body = resp.json()
        assert "diagnostic_sensors" in body
        assert "diagnostic_healing" in body
        assert "diagnostic_trends" in body
        assert body["diagnostic_sensors"]["last_error"] == "None"

    def test_processes_returns_list(self):
        with patch("api.system_health_api.psutil") as mp:
            mp.process_iter.return_value = []
            resp = self.client.get("/api/system-health/processes")
        assert resp.status_code == 200
        assert "processes" in resp.json()


# ─── 3. Layer 1 API (/layer1) ────────────────────────────────────────────

class TestLayer1API:
    """Tests for api/layer1_api.py — lightweight stub endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from api.layer1_api import router
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_stats_ok(self):
        resp = self.client.get("/layer1/stats")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_verify_ok(self):
        resp = self.client.get("/layer1/verify")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_cognitive_status(self):
        resp = self.client.get("/layer1/cognitive/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["active"] is True

    def test_whitelist_returns_structure(self):
        resp = self.client.get("/layer1/whitelist")
        assert resp.status_code == 200
        body = resp.json()
        assert "total_entries" in body
        assert "domains" in body
        assert body["total_entries"] == 0

    def test_user_input_post(self):
        resp = self.client.post("/layer1/user-input", json={"text": "hello"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_delete_domain_returns_404(self):
        resp = self.client.delete("/layer1/whitelist/domains/abc")
        assert resp.status_code == 404

    def test_patch_invalid_type_returns_400(self):
        resp = self.client.patch("/layer1/whitelist/invalid_type/123", json={"status": "blocked"})
        assert resp.status_code == 400


# ─── 4. KPI API (/kpi) ───────────────────────────────────────────────────

class TestKPIAPI:
    """Tests for api/kpi_api.py"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from api.kpi_api import router
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_health_fallback(self):
        # When tracker import fails inside handler, returns fallback values
        mock_mod = MagicMock()
        mock_mod.get_kpi_tracker.side_effect = Exception("no tracker")
        with patch.dict(sys.modules, {"ml_intelligence.kpi_tracker": mock_mod}):
            resp = self.client.get("/kpi/health")
        assert resp.status_code == 200
        body = resp.json()
        assert "system_trust_score" in body
        assert "status" in body

    @patch("api.kpi_api._get_live_components", return_value=None)
    def test_dashboard_uses_fallback_components(self, _):
        resp = self.client.get("/kpi/dashboard")
        assert resp.status_code == 200
        body = resp.json()
        assert "components" in body
        assert "top_performers" in body
        assert "needs_attention" in body
        assert len(body["components"]) == 5  # _FALLBACK_COMPONENTS count

    def test_component_kpis_unknown_name(self):
        resp = self.client.get("/kpi/components/nonexistent_comp")
        assert resp.status_code == 200
        body = resp.json()
        assert "trust_score" in body
        assert body["trust_score"] == 0.0

    def test_trust_trends_no_tracker(self):
        resp = self.client.get("/kpi/trust-trends")
        assert resp.status_code == 200
        body = resp.json()
        assert "trends" in body

    def test_pass_fail_no_tracker(self):
        resp = self.client.get("/kpi/pass-fail")
        assert resp.status_code == 200
        body = resp.json()
        assert "components" in body


# ─── 5. Validation API (/api/validation) ─────────────────────────────────

class TestValidationAPI:
    """Tests for api/validation_api.py"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from api.validation_api import router
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    @patch("api.validation_api._get_kpi_snapshot", return_value={"available": False})
    @patch("api.validation_api._get_recent_verification_results", return_value=[])
    @patch("api.validation_api._get_healing_stats", return_value={})
    @patch("api.validation_api._get_memory_alignment", return_value={})
    def test_status_returns_structure(self, *_):
        resp = self.client.get("/api/validation/status")
        assert resp.status_code == 200
        body = resp.json()
        assert "timestamp" in body
        assert "kpis" in body
        assert "recent_verifications" in body
        assert "healing_stats" in body

    @patch("api.validation_api._get_kpi_snapshot", return_value={"available": False, "components": {}})
    def test_trust_returns_scores(self, _):
        resp = self.client.get("/api/validation/trust")
        assert resp.status_code == 200
        body = resp.json()
        assert "scores" in body
        assert "overall" in body

    @patch("api.validation_api._get_kpi_snapshot", return_value={"available": False})
    def test_kpis_endpoint(self, _):
        resp = self.client.get("/api/validation/kpis")
        assert resp.status_code == 200
        assert resp.json()["available"] is False

    @patch("api.validation_api._get_recent_verification_results", return_value=[{"id": "1", "description": "test"}])
    def test_verifications_recent(self, _):
        resp = self.client.get("/api/validation/verifications/recent?limit=5")
        assert resp.status_code == 200
        body = resp.json()
        assert "results" in body
        assert len(body["results"]) == 1


# ─── 6. Governance Healing API (/governance/healing) ──────────────────────

class TestGovernanceHealingAPI:
    """Tests for api/governance_healing_api.py"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from api.governance_healing_api import router
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_status_graceful_on_import_error(self):
        mock_mod = MagicMock()
        mock_mod.get_governance_healing_bridge.side_effect = Exception("no bridge")
        with patch.dict(sys.modules, {"cognitive.governance_healing_bridge": mock_mod}):
            resp = self.client.get("/governance/healing/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["running"] is False
        assert "error" in body

    def test_history_graceful_on_import_error(self):
        mock_mod = MagicMock()
        mock_mod.get_governance_healing_bridge.side_effect = Exception("no bridge")
        with patch.dict(sys.modules, {"cognitive.governance_healing_bridge": mock_mod}):
            resp = self.client.get("/governance/healing/history?limit=10")
        assert resp.status_code == 200
        body = resp.json()
        assert body["triggers"] == []
        assert body["count"] == 0

    def test_status_returns_bridge_data(self):
        mock_bridge = MagicMock()
        mock_bridge.get_status.return_value = {"running": True, "thresholds": {"critical": 0.3}}
        mock_mod = MagicMock()
        mock_mod.get_governance_healing_bridge.return_value = mock_bridge
        with patch.dict(sys.modules, {"cognitive.governance_healing_bridge": mock_mod}):
            resp = self.client.get("/governance/healing/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["running"] is True

    def test_evaluate_calls_force_evaluate(self):
        mock_bridge = MagicMock()
        mock_bridge.force_evaluate.return_value = {"status": "evaluated", "heals_triggered": 0}
        mock_mod = MagicMock()
        mock_mod.get_governance_healing_bridge.return_value = mock_bridge
        with patch.dict(sys.modules, {"cognitive.governance_healing_bridge": mock_mod}):
            resp = self.client.post("/governance/healing/evaluate")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "evaluated"


# ─── 7. Genesis Daily API (/api/genesis-daily) ───────────────────────────

class TestGenesisDailyAPI:
    """Tests for api/genesis_daily_api.py"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from api.genesis_daily_api import router
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def _mock_db_module(self, session_scope_side_effect=None, session_scope_return=None):
        """Create mocked database.session module for inline imports."""
        mock_db = MagicMock()
        if session_scope_side_effect:
            mock_db.session_scope.side_effect = session_scope_side_effect
        elif session_scope_return is not None:
            mock_db.session_scope.return_value = session_scope_return
        return {"database.session": mock_db, "models.genesis_key_models": MagicMock()}

    def test_folders_returns_empty_on_error(self):
        mods = self._mock_db_module(session_scope_side_effect=Exception("no db"))
        with patch.dict(sys.modules, mods):
            resp = self.client.get("/api/genesis-daily/folders?days=7")
        assert resp.status_code == 200
        assert resp.json()["folders"] == []

    def test_stats_returns_zeros_on_error(self):
        mods = self._mock_db_module(session_scope_side_effect=Exception("no db"))
        with patch.dict(sys.modules, mods):
            resp = self.client.get("/api/genesis-daily/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_keys"] == 0
        assert body["today_keys"] == 0

    def test_folder_invalid_date_returns_400(self):
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=MagicMock())
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_db = MagicMock()
        mock_db.session_scope.return_value = mock_ctx
        mods = {"database.session": mock_db, "models.genesis_key_models": MagicMock()}
        with patch.dict(sys.modules, mods):
            resp = self.client.get("/api/genesis-daily/folder/not-a-date")
        assert resp.status_code == 400

    def test_key_not_found_returns_404(self):
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_session)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_db = MagicMock()
        mock_db.session_scope.return_value = mock_ctx
        mods = {"database.session": mock_db, "models.genesis_key_models": MagicMock()}
        with patch.dict(sys.modules, mods):
            resp = self.client.get("/api/genesis-daily/key/nonexistent-key-id")
        assert resp.status_code == 404


# ─── 8. Brain API v2 (/brain) ────────────────────────────────────────────

class TestBrainAPIv2:
    """Tests for api/brain_api_v2.py — tests _call routing and unknown actions."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from api.brain_api_v2 import router
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_directory_returns_brains(self):
        resp = self.client.get("/brain/directory")
        assert resp.status_code == 200
        body = resp.json()
        assert "brains" in body
        assert "total_brains" in body
        assert body["total_brains"] >= 1

    def test_unknown_action_returns_error(self):
        resp = self.client.post("/brain/system", json={
            "action": "completely_nonexistent_action_xyz",
            "payload": {}
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is False
        assert "Unknown action" in body["error"]

    def test_orchestrate_empty_steps(self):
        resp = self.client.post("/brain/orchestrate", json={"steps": []})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["succeeded"] == 0

    def test_orchestrate_with_unknown_brain(self):
        resp = self.client.post("/brain/orchestrate", json={
            "steps": [{"brain": "nonexistent_brain_xyz", "action": "test"}]
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["failed"] == 1


# ─── 9. Learning Memory API (/api/learning-memory) ───────────────────────

class TestLearningMemoryAPI:
    """Tests for api/learning_memory_api.py"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from api.learning_memory_api import router
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_knowledge_gap_sources_returns_list(self):
        resp = self.client.get("/api/learning-memory/knowledge-gap-sources")
        assert resp.status_code == 200
        body = resp.json()
        assert "sources" in body
        assert len(body["sources"]) > 0
        first = body["sources"][0]
        assert "id" in first
        assert "name" in first
        assert "enabled" in first

    def test_knowledge_gaps_fails_gracefully(self):
        mock_brain = MagicMock()
        mock_brain.call_brain.return_value = {"ok": False, "error": "brain offline"}
        with patch.dict(sys.modules, {"api.brain_api_v2": mock_brain}):
            resp = self.client.get("/api/learning-memory/knowledge-gaps")
        assert resp.status_code == 500

    def test_knowledge_gaps_success(self):
        mock_brain = MagicMock()
        mock_brain.call_brain.return_value = {"ok": True, "data": {"gaps": []}}
        with patch.dict(sys.modules, {"api.brain_api_v2": mock_brain}):
            resp = self.client.get("/api/learning-memory/knowledge-gaps")
        assert resp.status_code == 200
        assert resp.json() == {"gaps": []}


# ─── 10. Sandbox API (/sandbox) ──────────────────────────────────────────

class TestSandboxAPI:
    """Tests for api/sandbox_api.py"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from api.sandbox_api import router, active_experiments
        active_experiments.clear()
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_start_experiment_returns_id(self):
        resp = self.client.post("/sandbox/experiment", json={
            "hypothesis": "Test hypothesis",
            "target_sources": ["github", "arxiv"],
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "experiment_id" in body
        assert body["status"] == "pending"
        assert body["experiment_id"].startswith("EXP-")

    def test_stream_nonexistent_experiment_returns_404(self):
        resp = self.client.get("/sandbox/stream/NONEXISTENT")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_experiment_creates_active_entry(self):
        from api.sandbox_api import active_experiments
        resp = self.client.post("/sandbox/experiment", json={
            "hypothesis": "Another test",
            "target_sources": ["wikipedia"],
        })
        exp_id = resp.json()["experiment_id"]
        assert exp_id in active_experiments
        assert active_experiments[exp_id]["hypothesis"] == "Another test"


# ─── 11. Helper function unit tests ──────────────────────────────────────

class TestBrainHelpers:
    """Unit tests for brain_api_v2 helper functions."""

    def test_genesis_safe_payload_truncates(self):
        from api.brain_api_v2 import _genesis_safe_payload
        long_str = "x" * 1000
        result = _genesis_safe_payload(long_str, max_str=100)
        assert len(result) == 100

    def test_genesis_safe_payload_handles_none(self):
        from api.brain_api_v2 import _genesis_safe_payload
        assert _genesis_safe_payload(None) is None

    def test_genesis_safe_payload_handles_nested_dict(self):
        from api.brain_api_v2 import _genesis_safe_payload
        data = {"a": {"b": "hello"}, "c": [1, 2, 3]}
        result = _genesis_safe_payload(data)
        assert result["a"]["b"] == "hello"
        assert result["c"] == [1, 2, 3]

    def test_genesis_safe_payload_handles_coroutine(self):
        import asyncio
        from api.brain_api_v2 import _genesis_safe_payload

        async def dummy():
            pass

        coro = dummy()
        result = _genesis_safe_payload(coro)
        assert result == "<coroutine not awaited>"
        coro.close()


class TestValidationHelpers:
    """Unit tests for validation_api helper functions."""

    def test_compute_overall_trust_empty(self):
        from api.validation_api import _compute_overall_trust
        assert _compute_overall_trust({}) is None

    def test_compute_overall_trust_calculates_average(self):
        from api.validation_api import _compute_overall_trust
        comps = {
            "a": {"trust_score": 0.8},
            "b": {"trust_score": 0.6},
        }
        result = _compute_overall_trust(comps)
        assert result == 0.7

    def test_compute_overall_trust_skips_none(self):
        from api.validation_api import _compute_overall_trust
        comps = {
            "a": {"trust_score": 0.9},
            "b": {"trust_score": None},
            "c": {"error": "unavailable"},
        }
        result = _compute_overall_trust(comps)
        assert result == 0.9


class TestGenesisDailyHelpers:
    """Unit tests for genesis_daily_api helper functions."""

    def test_folder_item_formats_date(self):
        from api.genesis_daily_api import _folder_item
        item = _folder_item({"date": "2025-03-14", "key_count": 42, "error_count": 3})
        assert item["date"] == "2025-03-14"
        assert item["key_count"] == 42
        assert item["error_count"] == 3
        assert "Mar" in item["label"]

    def test_type_icon_known(self):
        from api.genesis_daily_api import _type_icon
        assert _type_icon("error") == "❌"
        assert _type_icon("api_request") == "🌐"

    def test_type_icon_unknown_fallback(self):
        from api.genesis_daily_api import _type_icon
        assert _type_icon("some_weird_type") == "🔑"
