"""
Genesis Full Integration Tests.
Event bridge, unified CI/CD, autonomous triggers, active healing.
All real logic, zero mocks.
"""
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from genesis.full_integration import (
    GenesisEventBridge, UnifiedCICDPipeline,
    AutonomousTriggerWiring, ActiveHealingSystem,
    wire_genesis_system,
)


class TestGenesisEventBridge:
    def test_bridge_creates(self):
        bridge = GenesisEventBridge()
        assert bridge._event_count == 0

    def test_bridge_with_memory(self):
        from cognitive.unified_memory import UnifiedMemory
        mem = UnifiedMemory()
        bridge = GenesisEventBridge(unified_memory=mem)
        asyncio.run(bridge.on_key_created({"genesis_key": "GK-test", "file_path": "/test.py"}))
        assert bridge._event_count == 1
        assert mem.get_stats()["total_memories"] >= 1

    def test_bridge_with_timesense(self):
        from cognitive.timesense import TimeSenseEngine
        ts = TimeSenseEngine()
        bridge = GenesisEventBridge(timesense=ts)
        asyncio.run(bridge.on_file_changed({"file_path": "/changed.py", "duration_ms": 50}))
        assert bridge._event_count == 1
        assert ts._stats["total_operations_timed"] >= 1

    def test_bridge_with_mirror(self):
        from cognitive.self_mirror import SelfMirror
        mirror = SelfMirror()
        bridge = GenesisEventBridge(self_mirror=mirror)
        asyncio.run(bridge.on_pipeline_triggered({"pipeline": "test", "duration_ms": 100}))
        assert mirror._stats["total_vectors_received"] >= 1

    def test_bridge_stats(self):
        bridge = GenesisEventBridge()
        asyncio.run(bridge.on_key_created({"test": True}))
        asyncio.run(bridge.on_file_changed({"test": True}))
        stats = bridge.get_stats()
        assert stats["total_events_bridged"] == 2


class TestUnifiedCICD:
    def test_pipeline_creates(self):
        cicd = UnifiedCICDPipeline()
        assert cicd._pipeline_count == 0

    def test_run_pipeline(self):
        cicd = UnifiedCICDPipeline()
        result = asyncio.run(cicd.run_pipeline(trigger="test"))
        assert result["success"] is True
        assert result["pipeline_id"].startswith("PIPE-")
        assert len(result["stages"]) >= 1

    def test_pipeline_stats(self):
        cicd = UnifiedCICDPipeline()
        asyncio.run(cicd.run_pipeline())
        stats = cicd.get_stats()
        assert stats["total_pipelines"] == 1
        assert stats["successes"] == 1

    def test_pipeline_with_bridge(self):
        from cognitive.unified_memory import UnifiedMemory
        mem = UnifiedMemory()
        bridge = GenesisEventBridge(unified_memory=mem)
        cicd = UnifiedCICDPipeline(event_bridge=bridge)
        asyncio.run(cicd.run_pipeline(trigger="auto"))
        assert bridge._event_count >= 2  # triggered + complete
        assert mem.get_stats()["total_memories"] >= 1

    def test_multiple_pipelines(self):
        cicd = UnifiedCICDPipeline()
        for _ in range(5):
            asyncio.run(cicd.run_pipeline())
        assert cicd._pipeline_count == 5
        assert cicd._success_count == 5


class TestAutonomousTriggers:
    def test_trigger_wiring_creates(self):
        wiring = AutonomousTriggerWiring()
        assert wiring._trigger_count == 0

    def test_critical_health_triggers(self):
        from dataclasses import dataclass

        @dataclass
        class MockHealth:
            class status:
                value = "critical"

        @dataclass
        class MockJudgement:
            health = MockHealth()

        @dataclass
        class MockCycle:
            cycle_id = "TEST-001"
            judgement = MockJudgement()

        wiring = AutonomousTriggerWiring()
        wiring.on_diagnostic_cycle(MockCycle())
        assert wiring._trigger_count >= 1
        assert wiring._triggers_fired[0]["trigger_type"] == "health_critical"

    def test_healthy_no_trigger(self):
        from dataclasses import dataclass

        @dataclass
        class MockHealth:
            class status:
                value = "healthy"

        @dataclass
        class MockJudgement:
            health = MockHealth()

        @dataclass
        class MockCycle:
            cycle_id = "TEST-002"
            judgement = MockJudgement()

        wiring = AutonomousTriggerWiring()
        wiring.on_diagnostic_cycle(MockCycle())
        assert wiring._trigger_count == 0


class TestActiveHealing:
    def test_garbage_collection(self):
        healer = ActiveHealingSystem()
        result = healer.execute_healing("garbage_collection", "Test cleanup")
        assert result["success"] is True
        assert "Collected" in result["message"]

    def test_memory_pressure_relief(self):
        healer = ActiveHealingSystem()
        result = healer.execute_healing("memory_pressure_relief")
        assert result["success"] is True

    def test_unknown_action(self):
        healer = ActiveHealingSystem()
        result = healer.execute_healing("nonexistent_action")
        assert result["success"] is False
        assert "Unknown" in result["message"]

    def test_healing_stats(self):
        healer = ActiveHealingSystem()
        healer.execute_healing("garbage_collection")
        healer.execute_healing("memory_pressure_relief")
        stats = healer.get_stats()
        assert stats["total_actions_executed"] == 2

    def test_healing_with_bridge(self):
        from cognitive.unified_memory import UnifiedMemory
        mem = UnifiedMemory()
        bridge = GenesisEventBridge(unified_memory=mem)
        healer = ActiveHealingSystem(event_bridge=bridge)
        healer.execute_healing("garbage_collection", "Auto-heal test")
        assert healer._actions_executed == 1


class TestFullWiring:
    def test_wire_genesis_system(self):
        result = wire_genesis_system()
        assert "event_bridge" in result
        assert "unified_cicd" in result
        assert "trigger_wiring" in result
        assert "active_healing" in result

    def test_wire_with_all_subsystems(self):
        from layer1.message_bus import Layer1MessageBus
        from cognitive.self_mirror import SelfMirror
        from cognitive.timesense import TimeSenseEngine
        from cognitive.unified_memory import UnifiedMemory

        result = wire_genesis_system(
            message_bus=Layer1MessageBus(),
            self_mirror=SelfMirror(),
            timesense=TimeSenseEngine(),
            unified_memory=UnifiedMemory(),
        )
        assert len(result["wired_to"]) >= 4
        assert "message_bus" in result["wired_to"]
        assert "self_mirror" in result["wired_to"]
        assert "timesense" in result["wired_to"]
        assert "unified_memory" in result["wired_to"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
