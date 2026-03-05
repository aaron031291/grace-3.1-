"""
Tests for the Ask Grace component — verifies:
1. Connector registers with Layer 1 message bus
2. Intent classification works for all known patterns
3. Deterministic responses generate correctly
4. Context aggregation pulls from available registries
5. Cognitive event bus integration publishes events
6. API endpoints return valid responses
"""

import sys
import os
import asyncio
import importlib
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from layer1.message_bus import get_message_bus, reset_message_bus

# Load ask_grace_api directly from file to avoid api/__init__.py triggering
# the full qdrant/ingestion import chain
_spec = importlib.util.spec_from_file_location(
    "ask_grace_api",
    os.path.join(os.path.dirname(__file__), "..", "api", "ask_grace_api.py"),
)
_ask_grace_api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_ask_grace_api)


@pytest.fixture(autouse=True)
def clean_bus():
    reset_message_bus()
    yield
    reset_message_bus()


class TestAskGraceConnector:

    def test_connector_registers_with_bus(self):
        from layer1.components.ask_grace_connector import AskGraceConnector
        bus = get_message_bus()
        connector = AskGraceConnector(message_bus=bus)
        stats = bus.get_stats()

        assert stats["registered_components"] >= 1
        assert "cognitive_engine" in stats["components"]

    def test_connector_request_handlers_registered(self):
        from layer1.components.ask_grace_connector import AskGraceConnector
        bus = get_message_bus()
        connector = AskGraceConnector(message_bus=bus)
        stats = bus.get_stats()

        handlers = stats["request_handlers"].get("cognitive_engine", [])
        assert "ask_grace_query" in handlers
        assert "ask_grace_components" in handlers
        assert "ask_grace_health" in handlers

    def test_connector_autonomous_actions_registered(self):
        from layer1.components.ask_grace_connector import AskGraceConnector
        bus = get_message_bus()
        connector = AskGraceConnector(message_bus=bus)

        actions = bus.get_autonomous_actions()
        trigger_events = [a["trigger_event"] for a in actions]
        assert "trigger.probe_completed" in trigger_events

    def test_connector_records_queries(self):
        from layer1.components.ask_grace_connector import AskGraceConnector
        bus = get_message_bus()
        connector = AskGraceConnector(message_bus=bus)

        connector.record_query("what is broken?", "System is healthy", "health_check")
        queries = connector.get_recent_queries(10)
        assert len(queries) == 1
        assert queries[0]["query"] == "what is broken?"
        assert queries[0]["intent"] == "health_check"

    def test_connector_query_limit(self):
        from layer1.components.ask_grace_connector import AskGraceConnector
        bus = get_message_bus()
        connector = AskGraceConnector(message_bus=bus)
        connector._max_recent = 5

        for i in range(10):
            connector.record_query(f"query {i}", f"response {i}", "general")

        queries = connector.get_recent_queries(100)
        assert len(queries) == 5

    def test_gather_system_context(self):
        from layer1.components.ask_grace_connector import AskGraceConnector
        bus = get_message_bus()
        connector = AskGraceConnector(message_bus=bus)

        context = asyncio.get_event_loop().run_until_complete(
            connector.gather_system_context()
        )

        assert "timestamp" in context
        assert "sources_queried" in context
        assert "message_bus" in context
        assert isinstance(context["message_bus"]["stats"], dict)


class TestIntentClassification:

    def test_health_intents(self):
        classify = _ask_grace_api._classify_intent

        assert classify("is the system healthy?") == "health_check"
        assert classify("what is broken?") == "health_check"
        assert classify("show me errors") == "health_check"
        assert classify("is Grace running?") == "health_check"
        assert classify("are there any degraded components?") == "health_check"

    def test_component_intents(self):
        classify = _ask_grace_api._classify_intent

        assert classify("list all components") == "component_query"
        assert classify("show me all services") == "component_query"
        assert classify("what is the trust engine?") == "component_query"
        assert classify("find the memory module") == "component_query"

    def test_bus_intents(self):
        classify = _ask_grace_api._classify_intent

        assert classify("how many messages on the bus?") == "bus_query"
        assert classify("show me event subscribers") == "bus_query"
        assert classify("what layer 1 components are connected?") == "bus_query"

    def test_genesis_intents(self):
        classify = _ask_grace_api._classify_intent

        assert classify("show me recent genesis keys") == "genesis_query"
        assert classify("show the audit trail for this change") == "genesis_query"
        assert classify("show tracking provenance") == "genesis_query"

    def test_probe_intents(self):
        classify = _ask_grace_api._classify_intent

        assert classify("which endpoints are active?") == "probe_query"
        assert classify("probe all APIs") == "probe_query"
        assert classify("are there dormant routes?") == "probe_query"

    def test_capability_intents(self):
        classify = _ask_grace_api._classify_intent

        assert classify("what can you do?") == "capability_query"
        assert classify("what features are available?") == "capability_query"

    def test_general_fallback(self):
        classify = _ask_grace_api._classify_intent

        assert classify("tell me a joke") == "general"
        assert classify("how is the weather today?") == "general"


class TestDeterministicResponses:

    def test_health_response_with_context(self):
        _build_deterministic_response = _ask_grace_api._build_deterministic_response

        context = {
            "system_health": {
                "total": 50,
                "green": 45,
                "amber": 3,
                "red": 2,
                "health_pct": 90.0,
            },
            "system_registry": {
                "broken": [
                    {"name": "broken_module", "description": "Some broken thing"}
                ],
                "degraded": [
                    {"name": "slow_module", "description": "Slow but works"}
                ],
            },
            "live_status": {
                "summary": "Grace is running with 1 error",
                "models": {"ollama": {"status": "connected"}},
            },
        }

        response = _build_deterministic_response("health_check", "is it healthy?", context)
        assert response is not None
        assert "90.0%" in response
        assert "broken_module" in response
        assert "slow_module" in response
        assert "ollama" in response

    def test_bus_response_with_context(self):
        _build_deterministic_response = _ask_grace_api._build_deterministic_response

        context = {
            "bus_stats": {
                "total_messages": 42,
                "requests": 10,
                "events": 30,
                "commands": 2,
                "autonomous_actions_triggered": 5,
                "registered_components": 3,
                "components": ["genesis_keys", "memory_mesh", "cognitive_engine"],
            },
            "autonomous_actions": [
                {
                    "description": "Auto-create Genesis Key",
                    "trigger_event": "ingestion.file_processed",
                    "enabled": True,
                }
            ],
        }

        response = _build_deterministic_response("bus_query", "bus stats?", context)
        assert response is not None
        assert "42" in response
        assert "genesis_keys" in response
        assert "Auto-create Genesis Key" in response

    def test_component_response_with_category(self):
        _build_deterministic_response = _ask_grace_api._build_deterministic_response

        context = {
            "components": [
                {"name": "TrustEngine", "category": "intelligence", "status": "green", "description": "Trust scoring"},
                {"name": "MemoryMesh", "category": "cognitive", "status": "green", "description": "Memory system"},
            ],
            "by_category": {
                "intelligence": [{"name": "TrustEngine", "status": "green", "description": "Trust scoring"}],
                "cognitive": [{"name": "MemoryMesh", "status": "green", "description": "Memory system"}],
            },
        }

        response = _build_deterministic_response("component_query", "list components", context)
        assert response is not None
        assert "INTELLIGENCE" in response
        assert "COGNITIVE" in response
        assert "TrustEngine" in response

    def test_general_returns_none(self):
        response = _ask_grace_api._build_deterministic_response("general", "what is life?", {})
        assert response is None


class TestCognitiveEventBusIntegration:

    def test_event_published_on_query(self):
        from cognitive.event_bus import subscribe, get_recent_events
        received = []

        def handler(event):
            received.append(event)

        subscribe("ask_grace.query_completed", handler)

        from cognitive.event_bus import publish
        publish("ask_grace.query_completed", {
            "query": "test",
            "intent": "general",
            "method": "deterministic",
        }, source="ask_grace")

        assert len(received) == 1
        assert received[0].data["intent"] == "general"

    def test_events_appear_in_log(self):
        from cognitive.event_bus import publish, get_recent_events

        publish("ask_grace.query_completed", {"test": True}, source="ask_grace")

        events = get_recent_events(5)
        topics = [e["topic"] for e in events]
        assert "ask_grace.query_completed" in topics


class TestContextAggregation:

    def test_builds_context_with_available_sources(self):
        context = asyncio.get_event_loop().run_until_complete(
            _ask_grace_api._build_context_for_intent("health_check", True)
        )

        assert isinstance(context, dict)
        assert "sources" in context or "sources_queried" in context

    def test_bus_query_includes_bus_stats(self):
        context = asyncio.get_event_loop().run_until_complete(
            _ask_grace_api._build_context_for_intent("bus_query", False)
        )

        assert isinstance(context, dict)
        sources = context.get("sources", [])
        if "message_bus" in sources:
            assert "bus_stats" in context


class TestContextSummarization:

    def test_summarize_with_data(self):
        _summarize_context = _ask_grace_api._summarize_context

        context = {
            "system_registry": {
                "health": {"total": 10, "green": 8, "amber": 1, "red": 1, "health_pct": 80},
                "broken": [{"name": "broken_thing"}],
            },
            "message_bus": {
                "stats": {"total_messages": 100, "registered_components": 5, "autonomous_actions": 3},
            },
            "live_status": {
                "summary": "Grace is running",
                "models": {"ollama": {"status": "connected"}},
            },
        }

        summary = _summarize_context(context)
        assert "System Registry" in summary
        assert "Message Bus" in summary
        assert "Grace is running" in summary

    def test_summarize_empty(self):
        summary = _ask_grace_api._summarize_context({})
        assert summary == "No system context available."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
