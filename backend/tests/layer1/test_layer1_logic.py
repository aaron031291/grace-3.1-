"""
Layer 1 Logic Tests — Message Bus, Connectors, and Component Integration.

Tests real behavior: publish/subscribe routing, request/response patterns,
autonomous action registration, component registration, connector init,
and error handling. All external deps (DB, Qdrant, LLMs) are mocked.
"""

import asyncio
import os
import sys
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone

# Ensure backend is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ.update({
    "SKIP_EMBEDDING_LOAD": "true",
    "SKIP_QDRANT_CHECK": "true",
    "SKIP_OLLAMA_CHECK": "true",
    "SKIP_AUTO_INGESTION": "true",
    "DISABLE_CONTINUOUS_LEARNING": "true",
    "SKIP_LLM_CHECK": "true",
    "LIGHTWEIGHT_MODE": "true",
    "DATABASE_PATH": ":memory:",
})

from backend.layer1.message_bus import (
    Layer1MessageBus,
    Message,
    MessageType,
    ComponentType,
    AutonomousAction,
    get_message_bus,
    reset_message_bus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def fresh_bus():
    """Reset the global singleton before every test."""
    reset_message_bus()
    yield
    reset_message_bus()


@pytest.fixture
def bus():
    return Layer1MessageBus()


@pytest.fixture
def make_message():
    """Helper to build a Message without boilerplate."""
    def _make(topic="test.topic", payload=None, **kw):
        defaults = dict(
            message_id="msg-test-001",
            message_type=MessageType.EVENT,
            from_component=ComponentType.RAG,
            to_component=None,
            topic=topic,
            payload=payload or {},
            timestamp=datetime.now(timezone.utc),
        )
        defaults.update(kw)
        return Message(**defaults)
    return _make


# ===================================================================
# 1. MESSAGE BUS — CORE MECHANICS
# ===================================================================

class TestMessageBusPublishSubscribe:
    """Verify publish fans out to subscribers and ignores unrelated topics."""

    @pytest.mark.asyncio
    async def test_publish_reaches_subscriber(self, bus, make_message):
        received = []

        async def handler(msg):
            received.append(msg)

        bus.subscribe("chat.new", handler)
        await bus.publish(
            topic="chat.new",
            payload={"text": "hello"},
            from_component=ComponentType.RAG,
        )

        assert len(received) == 1
        assert received[0].payload["text"] == "hello"
        assert received[0].topic == "chat.new"

    @pytest.mark.asyncio
    async def test_publish_does_not_reach_other_topics(self, bus):
        received = []

        async def handler(msg):
            received.append(msg)

        bus.subscribe("topic.A", handler)
        await bus.publish(
            topic="topic.B",
            payload={},
            from_component=ComponentType.INGESTION,
        )

        assert received == []

    @pytest.mark.asyncio
    async def test_multiple_subscribers_all_called(self, bus):
        calls = {"a": 0, "b": 0}

        async def handler_a(msg):
            calls["a"] += 1

        async def handler_b(msg):
            calls["b"] += 1

        bus.subscribe("shared.topic", handler_a)
        bus.subscribe("shared.topic", handler_b)
        await bus.publish(
            topic="shared.topic",
            payload={},
            from_component=ComponentType.RAG,
        )

        assert calls == {"a": 1, "b": 1}

    @pytest.mark.asyncio
    async def test_publish_increments_stats(self, bus):
        await bus.publish(
            topic="x", payload={}, from_component=ComponentType.RAG
        )
        await bus.publish(
            topic="y", payload={}, from_component=ComponentType.RAG
        )
        stats = bus.get_stats()
        assert stats["total_messages"] == 2
        assert stats["events"] == 2


class TestMessageBusUnsubscribe:
    """Verify that removing a subscriber prevents future delivery."""

    @pytest.mark.asyncio
    async def test_unsubscribe_removes_handler(self, bus):
        received = []

        async def handler(msg):
            received.append(msg)

        bus.subscribe("evt", handler)
        # manually remove (the bus exposes _subscribers)
        bus._subscribers["evt"].remove(handler)

        await bus.publish(
            topic="evt", payload={}, from_component=ComponentType.RAG
        )
        assert received == []


class TestMessageBusRequestResponse:
    """Verify the request → handler → response pipeline."""

    @pytest.mark.asyncio
    async def test_request_returns_handler_result(self, bus):
        async def handler(msg):
            return {"answer": msg.payload["q"] + "!"}

        bus.register_request_handler(
            ComponentType.MEMORY_MESH, "echo", handler
        )

        result = await bus.request(
            to_component=ComponentType.MEMORY_MESH,
            topic="echo",
            payload={"q": "hi"},
            from_component=ComponentType.RAG,
            timeout=5.0,
        )
        assert result == {"answer": "hi!"}

    @pytest.mark.asyncio
    async def test_request_missing_handler_raises(self, bus):
        with pytest.raises(Exception):
            await bus.request(
                to_component=ComponentType.INGESTION,
                topic="nonexistent",
                payload={},
                from_component=ComponentType.RAG,
                timeout=2.0,
            )

    @pytest.mark.asyncio
    async def test_request_updates_stats(self, bus):
        async def handler(msg):
            return {"ok": True}

        bus.register_request_handler(
            ComponentType.GENESIS_KEYS, "ping", handler
        )
        await bus.request(
            to_component=ComponentType.GENESIS_KEYS,
            topic="ping",
            payload={},
            from_component=ComponentType.RAG,
            timeout=5.0,
        )
        stats = bus.get_stats()
        assert stats["requests"] >= 1
        assert stats["total_messages"] >= 1


class TestMessageBusSendCommand:
    """Verify command dispatch (fire-and-forget)."""

    @pytest.mark.asyncio
    async def test_command_calls_handler(self, bus):
        called = {}

        async def handler(msg):
            called["payload"] = msg.payload

        bus.register_request_handler(
            ComponentType.LLM_ORCHESTRATION, "do_thing", handler
        )
        await bus.send_command(
            to_component=ComponentType.LLM_ORCHESTRATION,
            command="do_thing",
            payload={"x": 1},
            from_component=ComponentType.MEMORY_MESH,
        )
        assert called["payload"] == {"x": 1}

    @pytest.mark.asyncio
    async def test_command_increments_stats(self, bus):
        await bus.send_command(
            to_component=ComponentType.RAG,
            command="noop",
            payload={},
            from_component=ComponentType.INGESTION,
        )
        assert bus.get_stats()["commands"] == 1


# ===================================================================
# 2. COMPONENT REGISTRATION & HISTORY
# ===================================================================

class TestComponentRegistration:

    def test_register_and_get_component(self, bus):
        sentinel = object()
        bus.register_component(ComponentType.RAG, sentinel)
        assert bus.get_component(ComponentType.RAG) is sentinel

    def test_get_unregistered_returns_none(self, bus):
        assert bus.get_component(ComponentType.WORLD_MODEL) is None

    def test_stats_reflect_registered_count(self, bus):
        bus.register_component(ComponentType.RAG, "r")
        bus.register_component(ComponentType.INGESTION, "i")
        stats = bus.get_stats()
        assert stats["registered_components"] == 2
        assert set(stats["components"]) == {"rag", "ingestion"}


class TestMessageHistory:

    @pytest.mark.asyncio
    async def test_history_records_published_messages(self, bus):
        await bus.publish(
            topic="h.test", payload={"v": 1}, from_component=ComponentType.RAG
        )
        history = bus.get_message_history()
        assert len(history) == 1
        assert history[0].topic == "h.test"

    @pytest.mark.asyncio
    async def test_history_filter_by_component(self, bus):
        await bus.publish(
            topic="a", payload={}, from_component=ComponentType.RAG
        )
        await bus.publish(
            topic="b", payload={}, from_component=ComponentType.INGESTION
        )
        rag_history = bus.get_message_history(component=ComponentType.RAG)
        assert all(
            m.from_component == ComponentType.RAG or m.to_component == ComponentType.RAG
            for m in rag_history
        )

    @pytest.mark.asyncio
    async def test_history_filter_by_message_type(self, bus):
        await bus.publish(
            topic="ev", payload={}, from_component=ComponentType.RAG
        )
        events = bus.get_message_history(message_type=MessageType.EVENT)
        assert all(m.message_type == MessageType.EVENT for m in events)

    @pytest.mark.asyncio
    async def test_history_respects_max_limit(self, bus):
        bus._max_history = 5
        for i in range(10):
            await bus.publish(
                topic=f"t{i}", payload={}, from_component=ComponentType.RAG
            )
        assert len(bus._message_history) == 5


# ===================================================================
# 3. AUTONOMOUS ACTIONS
# ===================================================================

class TestAutonomousActions:

    @pytest.mark.asyncio
    async def test_register_and_trigger_action(self, bus):
        triggered = {"count": 0}

        async def action(msg):
            triggered["count"] += 1

        action_id = bus.register_autonomous_action(
            trigger_event="file.uploaded",
            action=action,
            component=ComponentType.INGESTION,
            description="test action",
        )
        assert action_id.startswith("action-")

        await bus.publish(
            topic="file.uploaded",
            payload={},
            from_component=ComponentType.INGESTION,
        )
        assert triggered["count"] == 1

    @pytest.mark.asyncio
    async def test_disabled_action_does_not_fire(self, bus):
        triggered = {"count": 0}

        async def action(msg):
            triggered["count"] += 1

        action_id = bus.register_autonomous_action(
            trigger_event="x.y",
            action=action,
            component=ComponentType.RAG,
            description="disableable",
        )
        bus.disable_autonomous_action(action_id)

        await bus.publish(
            topic="x.y", payload={}, from_component=ComponentType.RAG
        )
        assert triggered["count"] == 0

    @pytest.mark.asyncio
    async def test_enable_after_disable_fires(self, bus):
        triggered = {"count": 0}

        async def action(msg):
            triggered["count"] += 1

        aid = bus.register_autonomous_action(
            trigger_event="toggle",
            action=action,
            component=ComponentType.RAG,
            description="toggled",
        )
        bus.disable_autonomous_action(aid)
        bus.enable_autonomous_action(aid)

        await bus.publish(
            topic="toggle", payload={}, from_component=ComponentType.RAG
        )
        assert triggered["count"] == 1

    @pytest.mark.asyncio
    async def test_condition_prevents_action(self, bus):
        triggered = {"count": 0}

        async def action(msg):
            triggered["count"] += 1

        bus.register_autonomous_action(
            trigger_event="cond",
            action=action,
            component=ComponentType.RAG,
            description="conditional",
            conditions=[lambda msg: msg.payload.get("score", 0) > 0.9],
        )

        # condition NOT met
        await bus.publish(
            topic="cond",
            payload={"score": 0.5},
            from_component=ComponentType.RAG,
        )
        assert triggered["count"] == 0

        # condition met
        await bus.publish(
            topic="cond",
            payload={"score": 0.95},
            from_component=ComponentType.RAG,
        )
        assert triggered["count"] == 1

    def test_get_autonomous_actions_list(self, bus):
        bus.register_autonomous_action(
            trigger_event="t1",
            action=AsyncMock(),
            component=ComponentType.INGESTION,
            description="desc1",
        )
        actions = bus.get_autonomous_actions()
        assert len(actions) == 1
        assert actions[0]["description"] == "desc1"
        assert actions[0]["component"] == "ingestion"
        assert actions[0]["enabled"] is True

    @pytest.mark.asyncio
    async def test_action_error_does_not_crash_bus(self, bus):
        """If an action raises, the bus keeps running."""

        async def bad_action(msg):
            raise RuntimeError("boom")

        bus.register_autonomous_action(
            trigger_event="err",
            action=bad_action,
            component=ComponentType.RAG,
            description="explodes",
        )
        # should not raise
        await bus.publish(
            topic="err", payload={}, from_component=ComponentType.RAG
        )


class TestTrigger:

    @pytest.mark.asyncio
    async def test_trigger_publishes_prefixed_topic(self, bus):
        received = []

        async def handler(msg):
            received.append(msg.topic)

        bus.subscribe("trigger.my_trigger", handler)

        await bus.trigger(
            trigger_name="my_trigger",
            payload={"a": 1},
            from_component=ComponentType.RAG,
        )
        assert received == ["trigger.my_trigger"]


# ===================================================================
# 4. GLOBAL SINGLETON
# ===================================================================

class TestGlobalSingleton:

    def test_get_message_bus_returns_same_instance(self):
        a = get_message_bus()
        b = get_message_bus()
        assert a is b

    def test_reset_clears_singleton(self):
        a = get_message_bus()
        reset_message_bus()
        b = get_message_bus()
        assert a is not b


# ===================================================================
# 5. CONNECTOR TESTS (with all external deps mocked)
# ===================================================================

# -- helpers for mocking the heavy imports the connectors pull in --------

def _mock_retriever():
    r = MagicMock()
    r.retrieve.return_value = [
        {"chunk_id": "c1", "text": "hello world", "score": 0.95},
        {"chunk_id": "c2", "text": "bye world", "score": 0.80},
    ]
    return r


def _mock_ingestion_service():
    return MagicMock()


def _mock_memory_mesh():
    mm = MagicMock()
    mm.get_memory_mesh_stats.return_value = {
        "total_learning": 42,
        "episodic": 10,
        "procedural": 5,
    }
    mm.ingest_learning_experience.return_value = "learn-001"
    mm.session = MagicMock()
    return mm


# ===================================================================
# 5a. RAG CONNECTOR
# ===================================================================

class TestRAGConnector:

    @pytest.fixture
    def rag(self):
        bus = Layer1MessageBus()
        retriever = _mock_retriever()
        from backend.layer1.components.rag_connector import RAGConnector
        connector = RAGConnector(
            retriever=retriever,
            message_bus=bus,
            use_trust_aware=False,
        )
        # The connector registers using its own ComponentType import;
        # grab the actual keys so assertions match enum identity.
        self._ct_rag = [k for k in bus._registered_components if k.value == "rag"][0]
        return connector, bus, retriever

    def _rag_ct(self, bus):
        return next(k for k in bus._registered_components if k.value == "rag")

    def _rag_handlers(self, bus):
        return next(
            (v for k, v in bus._request_handlers.items() if k.value == "rag"), {}
        )

    def test_registers_component(self, rag):
        connector, bus, retriever = rag
        ct = self._rag_ct(bus)
        assert bus.get_component(ct) is retriever

    def test_registers_request_handlers(self, rag):
        _, bus, _ = rag
        handlers = self._rag_handlers(bus)
        assert "retrieve" in handlers
        assert "retrieve_with_context" in handlers

    def test_registers_autonomous_actions(self, rag):
        _, bus, _ = rag
        actions = bus.get_autonomous_actions()
        rag_descs = [a["description"] for a in actions if a["component"] == "rag"]
        assert len(rag_descs) >= 4

    @pytest.mark.asyncio
    async def test_handle_retrieve_returns_results(self, rag, make_message):
        connector, bus, retriever = rag
        handlers = self._rag_handlers(bus)
        msg = make_message(
            topic="retrieve",
            payload={"query": "test query", "top_k": 2},
            to_component=ComponentType.RAG,
        )
        result = await handlers["retrieve"](msg)
        assert "results" in result
        assert len(result["results"]) == 2
        assert result["results"][0]["content"] == "hello world"

    @pytest.mark.asyncio
    async def test_handle_retrieve_empty_results(self, rag, make_message):
        connector, bus, retriever = rag
        retriever.retrieve.return_value = []
        handlers = self._rag_handlers(bus)
        msg = make_message(
            topic="retrieve",
            payload={"query": "nothing", "top_k": 5},
            to_component=ComponentType.RAG,
        )
        result = await handlers["retrieve"](msg)
        assert result["results"] == []


# ===================================================================
# 5b. GENESIS KEYS CONNECTOR
# ===================================================================

class TestGenesisKeysConnector:

    @pytest.fixture
    def gk(self):
        bus = Layer1MessageBus()
        mock_session = MagicMock()
        from backend.layer1.components.genesis_keys_connector import GenesisKeysConnector
        connector = GenesisKeysConnector(
            session=mock_session,
            kb_path="/fake/kb",
            message_bus=bus,
        )
        return connector, bus, mock_session

    def _gk_ct(self, bus):
        return next(k for k in bus._registered_components if k.value == "genesis_keys")

    def _gk_handlers(self, bus):
        return next(
            (v for k, v in bus._request_handlers.items() if k.value == "genesis_keys"), {}
        )

    def test_registers_component(self, gk):
        connector, bus, _ = gk
        ct = self._gk_ct(bus)
        assert bus.get_component(ct) is connector

    def test_registers_request_handlers(self, gk):
        _, bus, _ = gk
        handlers = self._gk_handlers(bus)
        assert "get_genesis_key" in handlers
        assert "get_user_contributions" in handlers
        assert "create_file_key" in handlers

    def test_registers_autonomous_actions(self, gk):
        _, bus, _ = gk
        actions = bus.get_autonomous_actions()
        gk_descs = [a for a in actions if a["component"] == "genesis_keys"]
        assert len(gk_descs) >= 3

    def test_create_genesis_key_format(self, gk):
        connector, _, session = gk
        with patch(
            "backend.layer1.components.genesis_keys_connector.GenesisKey",
            create=True,
        ):
            # Patch the import inside the method
            with patch.dict("sys.modules", {
                "models.genesis_key_models": MagicMock(),
            }):
                key_id = connector._create_genesis_key(
                    key_type="ingestion",
                    entity_type="pdf",
                    entity_id="doc-123",
                    metadata={"file_path": "/a.pdf"},
                )
        assert key_id.startswith("GK-ingestion-pdf-")
        session.add.assert_called_once()
        session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_file_ingested_publishes_event(self, gk, make_message):
        connector, bus, session = gk
        received = []

        async def spy(msg):
            received.append(msg.topic)

        bus.subscribe("genesis_keys.new_file_key", spy)

        msg = make_message(
            topic="ingestion.file_processed",
            payload={
                "file_path": "/test.txt",
                "file_type": "txt",
                "document_id": "doc-1",
            },
        )
        with patch.dict("sys.modules", {
            "models.genesis_key_models": MagicMock(),
        }):
            await connector._on_file_ingested(msg)

        assert "genesis_keys.new_file_key" in received


# ===================================================================
# 5c. MEMORY MESH CONNECTOR
# ===================================================================

class TestMemoryMeshConnector:

    @pytest.fixture
    def mmc(self):
        bus = Layer1MessageBus()
        mm = _mock_memory_mesh()
        from backend.layer1.components.memory_mesh_connector import MemoryMeshConnector
        connector = MemoryMeshConnector(
            memory_mesh=mm,
            message_bus=bus,
        )
        return connector, bus, mm

    def _mm_ct(self, bus):
        return next(k for k in bus._registered_components if k.value == "memory_mesh")

    def _mm_handlers(self, bus):
        return next(
            (v for k, v in bus._request_handlers.items() if k.value == "memory_mesh"), {}
        )

    def test_registers_component(self, mmc):
        _, bus, mm = mmc
        ct = self._mm_ct(bus)
        assert bus.get_component(ct) is mm

    def test_registers_request_handlers(self, mmc):
        _, bus, _ = mmc
        handlers = self._mm_handlers(bus)
        assert "get_memory_stats" in handlers
        assert "get_procedures_for_context" in handlers
        assert "get_learning_by_genesis_key" in handlers

    def test_registers_autonomous_actions(self, mmc):
        _, bus, _ = mmc
        actions = bus.get_autonomous_actions()
        mm_actions = [a for a in actions if a["component"] == "memory_mesh"]
        assert len(mm_actions) >= 5

    @pytest.mark.asyncio
    async def test_handle_get_memory_stats(self, mmc, make_message):
        connector, bus, mm = mmc
        handlers = self._mm_handlers(bus)
        msg = make_message(topic="get_memory_stats", payload={})
        result = await handlers["get_memory_stats"](msg)
        assert "stats" in result
        assert result["stats"]["total_learning"] == 42

    @pytest.mark.asyncio
    async def test_on_new_genesis_key_publishes(self, mmc, make_message):
        connector, bus, _ = mmc
        received = []

        async def spy(msg):
            received.append(msg.topic)

        bus.subscribe("memory_mesh.genesis_key_linked", spy)

        msg = make_message(
            topic="genesis_keys.new_learning_key",
            payload={
                "genesis_key_id": "GK-learn-1",
                "learning_type": "episodic",
                "user_id": "u1",
            },
        )
        await connector._on_new_genesis_key(msg)
        assert "memory_mesh.genesis_key_linked" in received

    @pytest.mark.asyncio
    async def test_on_rag_feedback_no_crash(self, mmc, make_message):
        connector, bus, _ = mmc
        msg = make_message(
            topic="rag.feedback",
            payload={"query": "q", "success": True, "quality_score": 0.9},
        )
        await connector._on_rag_feedback(msg)  # should not raise


# ===================================================================
# 5d. INGESTION CONNECTOR
# ===================================================================

class TestIngestionConnector:

    @pytest.fixture
    def ic(self):
        bus = Layer1MessageBus()
        svc = _mock_ingestion_service()
        from backend.layer1.components.ingestion_connector import IngestionConnector
        connector = IngestionConnector(
            ingestion_service=svc,
            message_bus=bus,
        )
        return connector, bus, svc

    def _ing_ct(self, bus):
        return next(k for k in bus._registered_components if k.value == "ingestion")

    def _ing_handlers(self, bus):
        return next(
            (v for k, v in bus._request_handlers.items() if k.value == "ingestion"), {}
        )

    def test_registers_component(self, ic):
        _, bus, svc = ic
        ct = self._ing_ct(bus)
        assert bus.get_component(ct) is svc

    def test_registers_request_handlers(self, ic):
        _, bus, _ = ic
        handlers = self._ing_handlers(bus)
        assert "ingest_file" in handlers
        assert "get_ingestion_status" in handlers

    def test_registers_autonomous_actions(self, ic):
        _, bus, _ = ic
        actions = bus.get_autonomous_actions()
        ic_actions = [a for a in actions if a["component"] == "ingestion"]
        assert len(ic_actions) >= 3

    @pytest.mark.asyncio
    async def test_handle_ingest_file_returns_success(self, ic, make_message):
        connector, bus, _ = ic
        handlers = self._ing_handlers(bus)
        msg = make_message(
            topic="ingest_file",
            payload={"file_path": "/a.txt", "file_type": "txt", "user_id": "u1"},
        )
        result = await handlers["ingest_file"](msg)
        assert result["success"] is True
        assert "document_id" in result

    @pytest.mark.asyncio
    async def test_on_file_processed_publishes_rag_ready(self, ic, make_message):
        connector, bus, _ = ic
        received = []

        async def spy(msg):
            received.append(msg.topic)

        bus.subscribe("rag.document_ready", spy)

        msg = make_message(
            topic="ingestion.file_processed",
            payload={
                "file_path": "/b.pdf",
                "document_id": "doc-99",
                "genesis_key_id": "GK-1",
                "chunks_created": 5,
            },
        )
        await connector._on_file_processed(msg)
        assert "rag.document_ready" in received

    @pytest.mark.asyncio
    async def test_on_processing_failed_publishes_learning(self, ic, make_message):
        connector, bus, _ = ic
        received = []

        async def spy(msg):
            received.append(msg.topic)

        bus.subscribe("autonomous_learning.ingestion_failure", spy)

        msg = make_message(
            topic="ingestion.processing_failed",
            payload={
                "file_path": "/bad.bin",
                "error": "unsupported format",
                "file_type": "bin",
            },
        )
        await connector._on_processing_failed(msg)
        assert "autonomous_learning.ingestion_failure" in received


# ===================================================================
# 6. DATA MODEL TESTS
# ===================================================================

class TestMessageDataclass:

    def test_message_defaults(self, make_message):
        msg = make_message()
        assert msg.priority == 5
        assert msg.requires_response is False
        assert msg.metadata == {}

    def test_message_custom_priority(self, make_message):
        msg = make_message(priority=10)
        assert msg.priority == 10


class TestEnums:

    def test_message_type_values(self):
        assert MessageType.REQUEST.value == "request"
        assert MessageType.EVENT.value == "event"
        assert MessageType.COMMAND.value == "command"
        assert MessageType.TRIGGER.value == "trigger"

    def test_component_type_values(self):
        assert ComponentType.RAG.value == "rag"
        assert ComponentType.GENESIS_KEYS.value == "genesis_keys"
        assert ComponentType.MEMORY_MESH.value == "memory_mesh"
        assert ComponentType.INGESTION.value == "ingestion"
        assert ComponentType.LLM_ORCHESTRATION.value == "llm_orchestration"


class TestAutonomousActionDataclass:

    def test_autonomous_action_defaults(self):
        aa = AutonomousAction(
            action_id="a1",
            trigger_event="t",
            conditions=[],
            action=AsyncMock(),
            component=ComponentType.RAG,
            description="d",
        )
        assert aa.enabled is True


# ===================================================================
# 7. HANDLER ERROR RESILIENCE
# ===================================================================

class TestHandlerErrorResilience:

    @pytest.mark.asyncio
    async def test_subscriber_error_does_not_block_others(self, bus):
        results = []

        async def bad(msg):
            raise ValueError("fail")

        async def good(msg):
            results.append("ok")

        bus.subscribe("resilience", bad)
        bus.subscribe("resilience", good)

        await bus.publish(
            topic="resilience", payload={}, from_component=ComponentType.RAG
        )
        assert results == ["ok"]
