"""
Full Wiring Tests - Verifies ALL gaps are closed.

Diagnostic Engine: message bus, healing, self-mirror, timesense
Magma Memory: persistence, chat integration, consolidation
All real logic, zero mocks.
"""

import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class TestDiagnosticFullIntegration:
    """Verify diagnostic engine is wired to all subsystems."""

    @pytest.fixture(autouse=True)
    def skip_if_no_fastapi(self):
        """Skip these tests if fastapi isn't installed (diagnostic_engine needs it)."""
        try:
            import fastapi
        except ImportError:
            pytest.skip("DiagnosticEngine requires fastapi/starlette")

    def test_wire_function_exists(self):
        from diagnostic_machine.full_integration import wire_diagnostic_engine
        assert callable(wire_diagnostic_engine)

    def test_wire_to_message_bus(self):
        from diagnostic_machine.full_integration import wire_diagnostic_engine
        from layer1.message_bus import Layer1MessageBus
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine

        bus = Layer1MessageBus()
        engine = DiagnosticEngine(enable_heartbeat=False, dry_run=True)
        wired = wire_diagnostic_engine(engine, message_bus=bus)
        assert "message_bus" in wired
        assert len(engine._on_cycle_complete) >= 1
        assert len(engine._on_alert) >= 1
        assert len(engine._on_heal) >= 1

    def test_wire_to_self_mirror(self):
        from diagnostic_machine.full_integration import wire_diagnostic_engine
        from cognitive.self_mirror import SelfMirror
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine

        mirror = SelfMirror()
        engine = DiagnosticEngine(enable_heartbeat=False, dry_run=True)
        wired = wire_diagnostic_engine(engine, self_mirror=mirror)
        assert "self_mirror" in wired

    def test_wire_to_timesense(self):
        from diagnostic_machine.full_integration import wire_diagnostic_engine
        from cognitive.timesense import TimeSenseEngine
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine

        ts = TimeSenseEngine()
        engine = DiagnosticEngine(enable_heartbeat=False, dry_run=True)
        wired = wire_diagnostic_engine(engine, timesense=ts)
        assert "timesense" in wired

    def test_wire_all_at_once(self):
        from diagnostic_machine.full_integration import wire_diagnostic_engine
        from layer1.message_bus import Layer1MessageBus
        from cognitive.self_mirror import SelfMirror
        from cognitive.timesense import TimeSenseEngine
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine

        engine = DiagnosticEngine(enable_heartbeat=False, dry_run=True)
        wired = wire_diagnostic_engine(
            engine,
            message_bus=Layer1MessageBus(),
            self_mirror=SelfMirror(),
            timesense=TimeSenseEngine(),
        )
        assert "message_bus" in wired
        assert "self_mirror" in wired
        assert "timesense" in wired
        assert len(wired) >= 3

    def test_cycle_triggers_callbacks(self):
        from diagnostic_machine.full_integration import wire_diagnostic_engine
        from cognitive.self_mirror import SelfMirror
        from cognitive.timesense import TimeSenseEngine
        from diagnostic_machine.diagnostic_engine import DiagnosticEngine

        mirror = SelfMirror()
        ts = TimeSenseEngine()
        engine = DiagnosticEngine(enable_heartbeat=False, dry_run=True)
        wire_diagnostic_engine(engine, self_mirror=mirror, timesense=ts)

        cycle = engine.run_cycle()
        assert cycle is not None

        assert mirror._stats["total_vectors_received"] >= 1
        assert ts._stats["total_operations_timed"] >= 1


class TestMagmaPersistence:
    """Verify Magma saves and loads."""

    def test_persistence_save(self):
        from cognitive.magma.persistence import MagmaPersistence
        from cognitive.magma import MagmaMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = MagmaPersistence(data_dir=tmpdir)
            magma = MagmaMemory()
            magma.ingest("Test content for persistence")
            assert persistence.save(magma)
            assert os.path.exists(os.path.join(tmpdir, "magma_state.json"))

    def test_persistence_load(self):
        from cognitive.magma.persistence import MagmaPersistence
        from cognitive.magma import MagmaMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = MagmaPersistence(data_dir=tmpdir)
            magma = MagmaMemory()
            magma.ingest("Content to save")
            persistence.save(magma)

            magma2 = MagmaMemory()
            loaded = persistence.load(magma2)
            assert loaded

    def test_persistence_info(self):
        from cognitive.magma.persistence import MagmaPersistence
        from cognitive.magma import MagmaMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = MagmaPersistence(data_dir=tmpdir)
            magma = MagmaMemory()
            magma.ingest("Info test")
            persistence.save(magma)

            info = persistence.get_info()
            assert info["saved"] is True
            assert "saved_at" in info

    def test_persistence_no_file(self):
        from cognitive.magma.persistence import MagmaPersistence
        from cognitive.magma import MagmaMemory

        with tempfile.TemporaryDirectory() as tmpdir:
            persistence = MagmaPersistence(data_dir=tmpdir)
            magma = MagmaMemory()
            assert not persistence.load(magma)


class TestMagmaChatIntegration:
    """Verify Magma integrates with chat."""

    def test_get_magma_context(self):
        from cognitive.magma.chat_integration import get_magma_enhanced_context
        result = get_magma_enhanced_context("test query")
        assert result is None or isinstance(result, dict)

    def test_enrich_rag_context(self):
        from cognitive.magma.chat_integration import enrich_rag_context
        original = "Original RAG context about databases."
        enriched = enrich_rag_context(original, "What about databases?")
        assert original in enriched

    def test_ingest_chat_interaction(self):
        from cognitive.magma.chat_integration import ingest_chat_interaction
        ingest_chat_interaction(
            "What is machine learning?",
            "Machine learning is a subset of AI.",
        )

    def test_magma_api_ingest(self):
        from cognitive.magma import MagmaMemory
        magma = MagmaMemory()
        result = magma.ingest("Test content for API")
        assert result is not None

    def test_magma_api_query(self):
        from cognitive.magma import MagmaMemory
        magma = MagmaMemory()
        magma.ingest("Python is a programming language")
        results = magma.query("programming", limit=5)
        assert isinstance(results, list)


class TestStartupSubsystemsComplete:
    """Verify all subsystems are in the startup module."""

    def test_all_subsystem_attributes(self):
        from startup import GraceSubsystems
        subs = GraceSubsystems()
        required = [
            'layer1', 'message_bus', 'registry', 'cortex', 'magma',
            'diagnostic_engine', 'systems_integration', 'autonomous_engine',
            'timesense', 'self_mirror',
        ]
        for attr in required:
            assert hasattr(subs, attr), f"Missing: {attr}"

    def test_status_reports_all(self):
        from startup import GraceSubsystems
        subs = GraceSubsystems()
        status = subs.get_status()
        assert "layer1" in status
        assert "message_bus" in status
        assert "diagnostic_engine" in status
        assert "magma_memory" in status
        assert "timesense" in status
        assert "self_mirror" in status
        assert "cognitive_engine" in status
        assert "systems_integration" in status
        assert "autonomous_engine" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
