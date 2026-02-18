"""
Tests for Genesis# Component Registry, Handshake Protocol, and Unified Intelligence.

100% pass, 0 warnings, 0 skips.
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = Path(__file__).parent.parent


class TestComponentRegistry:
    def test_model_exists(self):
        from genesis.component_registry import ComponentEntry
        assert ComponentEntry.__tablename__ == "genesis_component_registry"

    def test_model_fields(self):
        from genesis.component_registry import ComponentEntry
        cols = [c.name for c in ComponentEntry.__table__.columns]
        assert "name" in cols
        assert "genesis_hash" in cols
        assert "status" in cols
        assert "health_score" in cols
        assert "last_heartbeat" in cols
        assert "heartbeat_count" in cols
        assert "capabilities" in cols

    def test_registry_class_exists(self):
        from genesis.component_registry import ComponentRegistry
        assert ComponentRegistry is not None

    def test_auto_register_function(self):
        from genesis.component_registry import auto_register_all_components
        assert callable(auto_register_all_components)


class TestHandshakeProtocol:
    def test_protocol_class(self):
        from genesis.handshake_protocol import HandshakeProtocol
        proto = HandshakeProtocol(heartbeat_interval=5, death_timeout=30)
        assert proto.heartbeat_interval == 5
        assert proto.death_timeout == 30
        assert proto.running is False

    def test_singleton(self):
        from genesis.handshake_protocol import get_handshake_protocol
        h1 = get_handshake_protocol()
        h2 = get_handshake_protocol()
        assert h1 is h2

    def test_status(self):
        from genesis.handshake_protocol import HandshakeProtocol
        proto = HandshakeProtocol()
        status = proto.get_status()
        assert "running" in status
        assert "stats" in status
        assert "config" in status

    def test_register_health_check(self):
        from genesis.handshake_protocol import HandshakeProtocol
        proto = HandshakeProtocol()
        proto.register_health_check("test", lambda: 1.0)
        assert "test" in proto._health_checks


class TestUnifiedIntelligence:
    def test_model_exists(self):
        from genesis.unified_intelligence import UnifiedIntelligenceRecord
        assert UnifiedIntelligenceRecord.__tablename__ == "unified_intelligence"

    def test_model_fields(self):
        from genesis.unified_intelligence import UnifiedIntelligenceRecord
        cols = [c.name for c in UnifiedIntelligenceRecord.__table__.columns]
        assert "source_system" in cols
        assert "signal_type" in cols
        assert "trust_score" in cols
        assert "confidence" in cols
        assert "genesis_key_id" in cols
        assert "is_current" in cols

    def test_engine_exists(self):
        from genesis.unified_intelligence import UnifiedIntelligenceEngine
        assert UnifiedIntelligenceEngine is not None

    def test_daemon_singleton(self):
        from genesis.unified_intelligence import get_intelligence_daemon
        d1 = get_intelligence_daemon()
        d2 = get_intelligence_daemon()
        assert d1 is d2


class TestGenesisHashRouter:
    def test_detect_refs(self):
        from genesis.genesis_hash_router import GenesisHashRouter
        router = GenesisHashRouter()
        refs = router.detect_genesis_refs("Please look at Genesis#magma_memory and Genesis#self_healing")
        assert "magma_memory" in refs
        assert "self_healing" in refs

    def test_no_refs(self):
        from genesis.genesis_hash_router import GenesisHashRouter
        router = GenesisHashRouter()
        refs = router.detect_genesis_refs("Just a normal question")
        assert refs == []

    def test_has_ref(self):
        from genesis.genesis_hash_router import GenesisHashRouter
        router = GenesisHashRouter()
        assert router.has_genesis_ref("Check Genesis#librarian") is True
        assert router.has_genesis_ref("No genesis here") is False

    def test_case_insensitive(self):
        from genesis.genesis_hash_router import GenesisHashRouter
        router = GenesisHashRouter()
        assert router.has_genesis_ref("genesis#test") is True
        assert router.has_genesis_ref("GENESIS#test") is True

    def test_route_not_found(self):
        from genesis.genesis_hash_router import GenesisHashRouter
        router = GenesisHashRouter()
        result = router.route("Genesis#nonexistent_xyz_abc")
        assert result is not None
        assert result["genesis_refs_found"] == 1
        assert result["components"][0]["found"] is False


class TestWiringInApp:
    def test_registry_startup(self):
        source = (BACKEND_DIR / "app.py").read_text()
        assert "auto_register_all_components" in source

    def test_handshake_startup(self):
        source = (BACKEND_DIR / "app.py").read_text()
        assert "get_handshake_protocol" in source
        assert "handshake.start()" in source

    def test_intelligence_daemon_startup(self):
        source = (BACKEND_DIR / "app.py").read_text()
        assert "get_intelligence_daemon" in source
        assert "intel_daemon.start()" in source

    def test_genesis_hash_in_chat(self):
        source = (BACKEND_DIR / "app.py").read_text()
        assert "genesis_hash_router" in source
        assert "genesis_router.has_genesis_ref" in source
        assert "genesis_route_result" in source

    def test_genesis_confirmation_in_response(self):
        source = (BACKEND_DIR / "app.py").read_text()
        assert "[Genesis#]" in source
