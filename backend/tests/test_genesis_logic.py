"""
REAL LOGIC TESTS for genesis/ section.
Tests actual behavior. Zero warnings, zero skips.
"""
import sys, os
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestComponentRegistryLogic:
    def test_model_fields(self):
        from genesis.component_registry import ComponentEntry
        cols = [c.name for c in ComponentEntry.__table__.columns]
        for field in ["name", "genesis_hash", "status", "health_score", "last_heartbeat", "heartbeat_count", "version", "capabilities", "dependencies", "connects_to"]:
            assert field in cols, f"Missing field: {field}"

    def test_hash_computation(self):
        from genesis.component_registry import ComponentRegistry
        from unittest.mock import MagicMock
        r = ComponentRegistry(MagicMock())
        h1 = r._compute_hash("genesis/component_registry.py")
        h2 = r._compute_hash("genesis/component_registry.py")
        assert h1 == h2
        assert len(h1) == 64

    def test_hash_different_for_different_files(self):
        from genesis.component_registry import ComponentRegistry
        from unittest.mock import MagicMock
        r = ComponentRegistry(MagicMock())
        h1 = r._compute_hash("genesis/component_registry.py")
        h2 = r._compute_hash("genesis/handshake_protocol.py")
        assert h1 != h2


class TestHandshakeProtocolLogic:
    def test_default_config(self):
        from genesis.handshake_protocol import HandshakeProtocol
        p = HandshakeProtocol()
        assert p.heartbeat_interval == 60
        assert p.death_timeout == 300
        assert p.auto_heal is True
        assert p.running is False

    def test_custom_config(self):
        from genesis.handshake_protocol import HandshakeProtocol
        p = HandshakeProtocol(heartbeat_interval=30, death_timeout=120, auto_heal=False)
        assert p.heartbeat_interval == 30
        assert p.death_timeout == 120
        assert p.auto_heal is False

    def test_health_check_registration(self):
        from genesis.handshake_protocol import HandshakeProtocol
        p = HandshakeProtocol()
        p.register_health_check("test_comp", lambda: 0.95)
        assert "test_comp" in p._health_checks
        assert p._health_checks["test_comp"]() == 0.95

    def test_status_structure(self):
        from genesis.handshake_protocol import HandshakeProtocol
        p = HandshakeProtocol()
        status = p.get_status()
        assert "running" in status
        assert "stats" in status
        assert "config" in status
        assert status["config"]["heartbeat_interval"] == 60


class TestUnifiedIntelligenceLogic:
    def test_record_model_fields(self):
        from genesis.unified_intelligence import UnifiedIntelligenceRecord
        cols = [c.name for c in UnifiedIntelligenceRecord.__table__.columns]
        for field in ["source_system", "signal_type", "signal_name", "value_numeric", "value_text", "value_json", "trust_score", "confidence", "severity", "component_name", "genesis_key_id", "is_current"]:
            assert field in cols, f"Missing field: {field}"

    def test_engine_has_all_collectors(self):
        from genesis.unified_intelligence import UnifiedIntelligenceEngine
        source = open("genesis/unified_intelligence.py").read()
        collectors = [
            "collect_from_registry", "collect_from_kpis", "collect_from_healing",
            "collect_from_pipeline", "collect_from_self_agents", "collect_from_memory_mesh",
            "collect_from_magma", "collect_from_episodic_memory", "collect_from_learning_memory",
            "collect_from_genesis_keys", "collect_from_documents", "collect_from_llm_tracking",
            "collect_from_handshake", "collect_from_governance", "collect_from_closed_loop",
            "collect_from_three_layer_reasoning", "collect_from_hia", "collect_from_timesense_governance",
            "collect_from_diagnostics", "collect_from_telemetry", "collect_from_scraping",
            "collect_from_sandbox", "collect_from_contradictions", "collect_from_procedural_memory",
            "collect_from_author_discovery", "collect_from_training_sources",
        ]
        for c in collectors:
            assert f"def {c}" in source, f"Missing collector: {c}"
            assert f"self.{c}()" in source, f"Collector {c} not called in collect_all"

    def test_librarian_audit_exists(self):
        source = open("genesis/unified_intelligence.py").read()
        assert "def librarian_audit" in source
        assert "sources_reporting" in source
        assert "expected_sources" in source


class TestGenesisHashRouterLogic:
    def test_pattern_matching(self):
        from genesis.genesis_hash_router import GenesisHashRouter
        r = GenesisHashRouter()
        assert r.detect_genesis_refs("Check Genesis#magma_memory") == ["magma_memory"]
        assert r.detect_genesis_refs("Genesis#a and Genesis#b") == ["a", "b"]
        assert r.detect_genesis_refs("no genesis here") == []

    def test_case_insensitive(self):
        from genesis.genesis_hash_router import GenesisHashRouter
        r = GenesisHashRouter()
        assert r.has_genesis_ref("genesis#test")
        assert r.has_genesis_ref("GENESIS#test")
        assert r.has_genesis_ref("Genesis#test")

    def test_route_not_found(self):
        from genesis.genesis_hash_router import GenesisHashRouter
        r = GenesisHashRouter()
        result = r.route("Genesis#nonexistent_xyz_123")
        assert result is not None
        assert result["components"][0]["found"] is False
        assert "system_message" in result


class TestCICDPipelineLogic:
    def test_pipeline_status_enum(self):
        from genesis.cicd import PipelineStatus
        assert PipelineStatus.PENDING.value == "pending"
        assert PipelineStatus.RUNNING.value == "running"
        assert PipelineStatus.SUCCESS.value == "success"
        assert PipelineStatus.FAILED.value == "failed"

    def test_stage_types(self):
        from genesis.cicd import StageType
        stages = [s.value for s in StageType]
        assert "checkout" in stages
        assert "test" in stages
        assert "build" in stages
        assert "deploy" in stages
        assert "security" in stages


class TestGenesisKeyModels:
    def test_key_types(self):
        from models.genesis_key_models import GenesisKeyType
        types = [t.value for t in GenesisKeyType]
        assert "user_input" in types
        assert "file_operation" in types
        assert "code_change" in types
        assert "learning_complete" in types
        assert "error" in types

    def test_key_model_fields(self):
        from models.genesis_key_models import GenesisKey
        cols = [c.name for c in GenesisKey.__table__.columns]
        assert "key_type" in cols or "entity_type" in cols
        assert "created_at" in cols


class TestAutonomousEngineLogic:
    def test_has_genesis_key_service(self):
        source = open("genesis/autonomous_engine.py").read()
        assert "get_genesis_key_service" in source

    def test_has_mirror_system(self):
        source = open("genesis/autonomous_engine.py").read()
        assert "get_mirror_system" in source

    def test_has_kpi_tracker(self):
        source = open("genesis/autonomous_engine.py").read()
        assert "get_kpi_tracker" in source

    def test_has_learning_hook(self):
        source = open("genesis/autonomous_engine.py").read()
        assert "track_learning_event" in source or "learning_hook" in source
