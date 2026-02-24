import pytest
import asyncio
from typing import Any, Dict

from grace_os.kernel.message_bus import MessageBus
from grace_os.kernel.layer_registry import LayerRegistry
from grace_os.kernel.message_protocol import LayerMessage, LayerResponse
from grace_os.layers.base_layer import BaseLayer

class MockLayerA(BaseLayer):
    @property
    def layer_name(self) -> str:
        return "L_A"

    @property
    def capabilities(self) -> list[str]:
        return ["cap_a"]

    @property
    def accepted_message_types(self) -> list[str]:
        return ["msg_for_a"]

    async def handle_message(self, message: LayerMessage) -> LayerResponse:
        return LayerResponse(
            message_id=message.id,
            from_layer=self.layer_name,
            status="success",
            payload={"msg": "hello from A", "received": message.payload},
            trust_score=95.0
        )

class MockLayerB(BaseLayer):
    @property
    def layer_name(self) -> str:
        return "L_B"

    @property
    def capabilities(self) -> list[str]:
        return ["cap_b"]

    @property
    def accepted_message_types(self) -> list[str]:
        return ["msg_for_b", "broadcast_msg"]

    async def handle_message(self, message: LayerMessage) -> LayerResponse:
        if message.message_type == "msg_for_b":
            # Send a message back to A just to test chaining
            return await self.send_message(
                to_layer="L_A",
                message_type="msg_for_a",
                payload={"from": "B"},
                trace_id=message.trace_id,
                parent_message_id=message.id,
                current_depth=message.max_depth
            )
        elif message.message_type == "broadcast_msg":
             return LayerResponse(
                message_id=message.id,
                from_layer=self.layer_name,
                status="success",
                payload={"msg": "B got broadcast"},
            )

class MockFailingLayer(BaseLayer):
    def __init__(self, bus, registry, fail_count):
        super().__init__(bus, registry)
        self.fail_count = fail_count
        self.attempts = 0

    @property
    def layer_name(self) -> str: return "L_Fail"

    @property
    def capabilities(self) -> list[str]: return []

    @property
    def accepted_message_types(self) -> list[str]: return ["fail_test"]

    async def handle_message(self, message: LayerMessage) -> LayerResponse:
        self.attempts += 1
        if self.attempts <= self.fail_count:
            raise ValueError("Intentional failure")
        return LayerResponse(message_id=message.id, from_layer=self.layer_name, status="success", payload={})


class MockCycleLayer(BaseLayer):
    @property
    def layer_name(self) -> str: return "L_Cycle"

    @property
    def capabilities(self) -> list[str]: return []

    @property
    def accepted_message_types(self) -> list[str]: return ["cycle"]

    async def handle_message(self, message: LayerMessage) -> LayerResponse:
        # Calls itself infinitely, relying on max_depth to stop it
        return await self.send_message(
            to_layer="L_Cycle", 
            message_type="cycle", 
            payload={},
            current_depth=message.max_depth
        )


@pytest.fixture
def bus_and_registry():
    bus = MessageBus()
    # Speed up tests
    bus._base_backoff_ms = 1
    registry = LayerRegistry()
    return bus, registry

@pytest.mark.asyncio
async def test_successful_point_to_point(bus_and_registry):
    bus, registry = bus_and_registry
    layer_a = MockLayerA(bus, registry)
    layer_a.start()

    msg = LayerMessage(from_layer="Test", to_layer="L_A", message_type="msg_for_a", payload={"data": 123})
    response = await bus.send(msg)
    
    assert response.status == "success"
    assert response.payload["received"]["data"] == 123
    assert response.trust_score == 95.0

@pytest.mark.asyncio
async def test_chained_messages(bus_and_registry):
    bus, registry = bus_and_registry
    layer_a = MockLayerA(bus, registry)
    layer_b = MockLayerB(bus, registry)
    layer_a.start()
    layer_b.start()

    msg = LayerMessage(from_layer="Test", to_layer="L_B", message_type="msg_for_b", payload={})
    
    # Send to B, B should send to A, A responds to B, B returns A's response
    response = await bus.send(msg)
    
    assert response.status == "success"
    assert response.from_layer == "L_A"
    assert response.payload["received"]["from"] == "B"

@pytest.mark.asyncio
async def test_exponential_backoff_retries(bus_and_registry):
    bus, registry = bus_and_registry
    class RetryFailLayer(MockFailingLayer):
        @property
        def layer_name(self) -> str: return "L_Retry"
        @property
        def accepted_message_types(self) -> list[str]: return ["retry_test"]

    # Should fail twice, succeed on third attempt
    layer_fail = RetryFailLayer(bus, registry, fail_count=2)
    layer_fail.start()

    msg = LayerMessage(from_layer="Test", to_layer="L_Retry", message_type="retry_test", payload={})
    response = await bus.send(msg)

    # MockFailingLayer receives initial try (fail 1), retry 1 (fail 2), retry 2 (success).
    # Since fail_count is 2, it fails on attempt 1 and attempt 2. Succeeds on attempt 3.
    assert response.status == "success"
    assert layer_fail.attempts == 3

@pytest.mark.asyncio
async def test_exponential_backoff_exhaustion(bus_and_registry):
    bus, registry = bus_and_registry
    
    class ExhaustFailLayer(MockFailingLayer):
        @property
        def layer_name(self) -> str: return "L_Exhaust"
        @property
        def accepted_message_types(self) -> list[str]: return ["exhaust_test"]
    
    # Fails 5 times (bus max retries is 3)
    layer_fail = ExhaustFailLayer(bus, registry, fail_count=5)
    layer_fail.start()

    msg = LayerMessage(from_layer="Test", to_layer="L_Exhaust", message_type="exhaust_test", payload={})
    response = await bus.send(msg)

    print(f"FAILED RESPONSE WAS: {response}")
    assert response.status == "failure"
    assert "Handler exception" in response.payload["error"]
    assert layer_fail.attempts == 4 # 1 Initial + 3 Retries

@pytest.mark.asyncio
async def test_cycle_detection(bus_and_registry):
    bus, registry = bus_and_registry
    layer_cycle = MockCycleLayer(bus, registry)
    layer_cycle.start()

    # Budget of 3 recursion calls
    msg = LayerMessage(from_layer="Test", to_layer="L_Cycle", message_type="cycle", payload={}, max_depth=3)
    response = await bus.send(msg)

    assert response.status == "failure"
    assert "Max recursion depth exceeded" in response.payload["error"]

@pytest.mark.asyncio
async def test_broadcast(bus_and_registry):
    bus, registry = bus_and_registry
    layer_b1 = MockLayerB(bus, registry)
    layer_b2 = MockLayerB(bus, registry) # same class, different instances
    layer_b1.start()
    layer_b2.start()

    msg = LayerMessage(from_layer="Test", to_layer="*", message_type="broadcast_msg", payload={})
    responses = await bus.broadcast(msg)

    assert len(responses) == 2
    for r in responses:
        assert r.status == "success"
        assert r.payload["msg"] == "B got broadcast"
