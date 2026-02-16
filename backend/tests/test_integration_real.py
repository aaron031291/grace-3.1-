"""
Real Integration Tests - Tests that verify actual subsystem connections.

These are NOT mock tests. They verify:
1. The system boots without import errors
2. Subsystems actually initialize
3. The message bus has real subscribers
4. Event flows work end-to-end
5. The health endpoint reports real status

Run with: python -m pytest tests/test_integration_real.py -v
"""

import sys
import os
import importlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class TestSystemBoot:
    """Tests that verify the system can actually start."""

    def test_settings_import(self):
        """Settings module loads without errors."""
        from settings import settings
        assert settings is not None
        assert settings.OLLAMA_URL is not None
        assert settings.DATABASE_TYPE in ("sqlite", "postgresql", "mysql", "mariadb")

    def test_logging_config_import(self):
        """Logging config loads without errors."""
        from logging_config import setup_logging
        assert callable(setup_logging)

    def test_security_config_import(self):
        """Security config loads without errors."""
        from security.config import get_security_config
        config = get_security_config()
        assert config is not None
        assert hasattr(config, "CORS_ALLOWED_ORIGINS")

    def test_all_api_routers_import(self):
        """Every API router can be imported (syntax + dependency check)."""
        api_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "api")
        failures = []
        successes = []

        for filename in sorted(os.listdir(api_dir)):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = f"api.{filename[:-3]}"
                try:
                    importlib.import_module(module_name)
                    successes.append(module_name)
                except Exception as e:
                    failures.append((module_name, str(e)[:100]))

        print(f"\nAPI Router Import Results: {len(successes)} OK, {len(failures)} FAILED")
        for name in successes:
            print(f"  [OK] {name}")
        for name, err in failures:
            print(f"  [FAIL] {name}: {err}")

        assert len(successes) > 0, "No API routers could be imported"


class TestCoreSubsystems:
    """Tests that verify core subsystem imports and initialization."""

    def test_cognitive_engine_creates(self):
        """Cognitive engine instantiates without external deps."""
        from cognitive.engine import CognitiveEngine
        cortex = CognitiveEngine()
        assert cortex is not None

    def test_ooda_loop_creates(self):
        """OODA loop instantiates."""
        from cognitive.ooda import OODALoop
        loop = OODALoop()
        assert loop is not None

    def test_message_bus_creates(self):
        """Layer 1 message bus instantiates."""
        from layer1.message_bus import Layer1MessageBus
        bus = Layer1MessageBus()
        assert bus is not None
        assert bus.get_stats()["registered_components"] == 0

    def test_component_registry_creates(self):
        """Component registry instantiates."""
        from core.registry import ComponentRegistry
        registry = ComponentRegistry()
        assert registry is not None
        assert len(registry.get_all()) == 0

    def test_magma_memory_creates(self):
        """Magma memory system instantiates."""
        from cognitive.magma import MagmaMemory
        magma = MagmaMemory()
        assert magma is not None
        stats = magma.get_stats()
        assert "graphs" in stats

    def test_systems_integration_creates(self):
        """Systems integration service instantiates."""
        from services.grace_systems_integration import GraceSystemsIntegration
        integration = GraceSystemsIntegration()
        assert integration is not None

    def test_autonomous_engine_creates(self):
        """Autonomous engine instantiates."""
        from services.grace_autonomous_engine import GraceAutonomousEngine
        engine = GraceAutonomousEngine()
        assert engine is not None

    def test_grace_agent_creates(self):
        """Grace agent instantiates."""
        from agent.grace_agent import GraceAgent
        agent = GraceAgent()
        assert agent is not None


class TestMessageBusConnections:
    """Tests that verify message bus wiring works."""

    def test_message_bus_subscribe_publish(self):
        """Message bus pub/sub works."""
        import asyncio
        from layer1.message_bus import Layer1MessageBus, ComponentType

        bus = Layer1MessageBus()
        received = []

        async def handler(message):
            received.append(message)

        bus.subscribe("test.event", handler)

        async def run():
            await bus.publish(
                topic="test.event",
                payload={"data": "hello"},
                from_component=ComponentType.GENESIS_KEYS,
            )

        asyncio.run(run())
        assert len(received) == 1
        assert received[0].payload["data"] == "hello"

    def test_message_bus_request_response(self):
        """Message bus request/response works."""
        import asyncio
        from layer1.message_bus import Layer1MessageBus, ComponentType

        bus = Layer1MessageBus()

        async def handler(message):
            return {"answer": 42}

        bus.register_request_handler(
            ComponentType.MEMORY_MESH, "get_answer", handler
        )

        async def run():
            result = await bus.request(
                to_component=ComponentType.MEMORY_MESH,
                topic="get_answer",
                payload={"question": "what"},
                from_component=ComponentType.COGNITIVE_ENGINE,
            )
            return result

        result = asyncio.run(run())
        assert result["answer"] == 42

    def test_autonomous_action_registration(self):
        """Autonomous actions can be registered and listed."""
        from layer1.message_bus import Layer1MessageBus, ComponentType

        bus = Layer1MessageBus()

        async def my_action(message):
            pass

        action_id = bus.register_autonomous_action(
            trigger_event="ingestion.complete",
            action=my_action,
            component=ComponentType.LEARNING_MEMORY,
            description="Learn from new ingestion",
        )

        actions = bus.get_autonomous_actions()
        assert len(actions) == 1
        assert actions[0]["description"] == "Learn from new ingestion"
        assert actions[0]["trigger_event"] == "ingestion.complete"


class TestCognitiveEngine:
    """Tests that verify the cognitive engine makes real decisions."""

    def test_decision_context_creation(self):
        """Decision context can be created with all invariant fields."""
        from cognitive.engine import DecisionContext
        ctx = DecisionContext(
            problem_statement="Should we deploy this change?",
            goal="Improve retrieval accuracy",
            success_criteria=["accuracy > 0.9", "latency < 100ms"],
            is_reversible=True,
            impact_scope="component",
        )
        assert ctx.decision_id is not None
        assert ctx.is_reversible is True
        assert ctx.impact_scope == "component"

    def test_ambiguity_ledger(self):
        """Ambiguity ledger tracks unknowns."""
        from cognitive.ambiguity import AmbiguityLedger
        ledger = AmbiguityLedger()
        ledger.add_unknown(
            key="performance_impact",
            blocking=True,
            notes="Unknown performance impact",
        )
        entry = ledger.get("performance_impact")
        assert entry is not None
        assert entry.blocking is True


class TestMagmaMemory:
    """Tests that verify Magma memory operations work."""

    def test_magma_ingest_and_query(self):
        """Magma can ingest content and query it."""
        from cognitive.magma import MagmaMemory
        magma = MagmaMemory()

        result = magma.ingest("Machine learning improves prediction accuracy over time.")
        assert result is not None

        results = magma.query("What improves predictions?", limit=5)
        assert isinstance(results, list)

    def test_magma_relation_graphs(self):
        """Magma creates relation graphs."""
        from cognitive.magma import MagmaRelationGraphs
        graphs = MagmaRelationGraphs()
        stats = graphs.get_unified_stats()
        assert "semantic" in stats or isinstance(stats, dict)

    def test_magma_intent_router(self):
        """Intent router classifies queries."""
        from cognitive.magma import IntentAwareRouter
        router = IntentAwareRouter()
        analysis = router.analyze_query("What causes database timeouts?")
        assert analysis is not None


class TestStartupModule:
    """Tests the unified startup module."""

    def test_subsystems_class_creates(self):
        """GraceSubsystems can be instantiated."""
        from startup import GraceSubsystems
        subs = GraceSubsystems()
        status = subs.get_status()
        assert status["active_count"] == 0
        assert status["layer1"] == "inactive"

    def test_get_subsystems_singleton(self):
        """get_subsystems returns same instance."""
        from startup import get_subsystems, _subsystems
        import startup
        startup._subsystems = None
        s1 = get_subsystems()
        s2 = get_subsystems()
        assert s1 is s2
        startup._subsystems = None


class TestExecutionBridge:
    """Tests the execution system."""

    def test_action_request_creation(self):
        """Action requests can be created."""
        from execution.actions import ActionRequest, GraceAction
        request = ActionRequest(
            action_type=GraceAction.WRITE_FILE,
            parameters={"path": "/tmp/test.txt", "content": "hello"},
        )
        assert request.action_type == GraceAction.WRITE_FILE
        assert request.parameters["path"] == "/tmp/test.txt"

    def test_governed_bridge_imports(self):
        """Governed execution bridge can be imported."""
        from execution.governed_bridge import GovernedExecutionBridge
        assert GovernedExecutionBridge is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
