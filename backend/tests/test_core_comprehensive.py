"""
Comprehensive Test Suite for Core Module
=========================================
Tests for BaseComponent, ComponentRegistry, and GraceLoopOutput.

Coverage:
- ComponentState and ComponentRole enums
- ComponentManifest dataclass
- BaseComponent lifecycle management
- ComponentRegistry registration and lookup
- GraceLoopOutput reasoning chains
- Loop lifecycle management
- Serialization/deserialization
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import uuid

import sys
sys.path.insert(0, '/home/user/grace-3.1-/backend')

from core.base_component import (
    ComponentState,
    ComponentRole,
    ComponentManifest,
    BaseComponent,
)
from core.registry import (
    RegistryEntry,
    ComponentRegistry,
    get_component_registry,
    reset_registry,
)
from core.loop_output import (
    LoopType,
    LoopStatus,
    ReasoningStep,
    LoopMetadata,
    GraceLoopOutput,
)


# =============================================================================
# ComponentState Enum Tests
# =============================================================================

class TestComponentState:
    """Test ComponentState enum."""

    def test_all_states_defined(self):
        """Test all expected states are defined."""
        expected = [
            'UNINITIALIZED', 'INITIALIZING', 'ACTIVE', 'PAUSED',
            'DEGRADED', 'ERROR', 'STOPPING', 'STOPPED'
        ]
        for state in expected:
            assert hasattr(ComponentState, state)

    def test_state_values(self):
        """Test state string values."""
        assert ComponentState.UNINITIALIZED.value == "uninitialized"
        assert ComponentState.INITIALIZING.value == "initializing"
        assert ComponentState.ACTIVE.value == "active"
        assert ComponentState.PAUSED.value == "paused"
        assert ComponentState.DEGRADED.value == "degraded"
        assert ComponentState.ERROR.value == "error"
        assert ComponentState.STOPPING.value == "stopping"
        assert ComponentState.STOPPED.value == "stopped"

    def test_state_iteration(self):
        """Test iterating over states."""
        states = list(ComponentState)
        assert len(states) == 8


# =============================================================================
# ComponentRole Enum Tests
# =============================================================================

class TestComponentRole:
    """Test ComponentRole enum."""

    def test_all_roles_defined(self):
        """Test all expected roles are defined."""
        expected = [
            'COGNITIVE', 'MEMORY', 'EXECUTION', 'LEARNING',
            'GOVERNANCE', 'ORCHESTRATION', 'INTEGRATION', 'INFRASTRUCTURE'
        ]
        for role in expected:
            assert hasattr(ComponentRole, role)

    def test_role_values(self):
        """Test role string values."""
        assert ComponentRole.COGNITIVE.value == "cognitive"
        assert ComponentRole.MEMORY.value == "memory"
        assert ComponentRole.EXECUTION.value == "execution"
        assert ComponentRole.LEARNING.value == "learning"
        assert ComponentRole.GOVERNANCE.value == "governance"
        assert ComponentRole.ORCHESTRATION.value == "orchestration"
        assert ComponentRole.INTEGRATION.value == "integration"
        assert ComponentRole.INFRASTRUCTURE.value == "infrastructure"


# =============================================================================
# ComponentManifest Tests
# =============================================================================

class TestComponentManifest:
    """Test ComponentManifest dataclass."""

    def test_basic_manifest(self):
        """Test basic manifest creation."""
        manifest = ComponentManifest(
            component_id="test-001",
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="A test component"
        )
        assert manifest.component_id == "test-001"
        assert manifest.name == "TestComponent"
        assert manifest.version == "1.0.0"
        assert manifest.role == ComponentRole.COGNITIVE
        assert manifest.description == "A test component"

    def test_default_values(self):
        """Test default manifest values."""
        manifest = ComponentManifest(
            component_id="test-001",
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.MEMORY,
            description="Test"
        )
        assert manifest.trust_level == 0.5
        assert manifest.is_trusted is False
        assert manifest.requires_governance is True
        assert manifest.capabilities == set()
        assert manifest.dependencies == set()
        assert manifest.tags == set()
        assert manifest.last_active_at is None

    def test_manifest_with_capabilities(self):
        """Test manifest with capabilities."""
        manifest = ComponentManifest(
            component_id="test-001",
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.MEMORY,
            description="Test",
            capabilities={"vector_store", "embeddings", "search"}
        )
        assert "vector_store" in manifest.capabilities
        assert "embeddings" in manifest.capabilities
        assert len(manifest.capabilities) == 3

    def test_manifest_to_dict(self):
        """Test manifest serialization."""
        manifest = ComponentManifest(
            component_id="test-001",
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test",
            trust_level=0.8,
            is_trusted=True,
            capabilities={"analyze", "reason"},
            tags={"core", "critical"}
        )
        data = manifest.to_dict()

        assert data["component_id"] == "test-001"
        assert data["name"] == "TestComponent"
        assert data["role"] == "cognitive"
        assert data["trust_level"] == 0.8
        assert data["is_trusted"] is True
        assert "analyze" in data["capabilities"]
        assert "core" in data["tags"]
        assert "created_at" in data


# =============================================================================
# BaseComponent Tests
# =============================================================================

class ConcreteComponent(BaseComponent):
    """Concrete implementation for testing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.activate_called = False
        self.deactivate_called = False

    async def _do_activate(self):
        self.activate_called = True

    async def _do_deactivate(self):
        self.deactivate_called = True


class TestBaseComponent:
    """Test BaseComponent class."""

    def test_initialization(self):
        """Test component initialization."""
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="A test component"
        )

        assert component.name == "TestComponent"
        assert component.state == ComponentState.UNINITIALIZED
        assert not component.is_active
        assert component.trust_level == 0.5

    def test_component_id_generation(self):
        """Test component ID is generated."""
        component = ConcreteComponent(
            name="My Component",
            version="1.0.0",
            role=ComponentRole.MEMORY,
            description="Test"
        )

        assert "my_component" in component.component_id
        assert len(component.component_id.split("-")) == 2

    def test_initialization_with_capabilities(self):
        """Test initialization with capabilities."""
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.MEMORY,
            description="Test",
            capabilities={"store", "retrieve"},
            dependencies={"database"},
            tags={"core"}
        )

        assert "store" in component.manifest.capabilities
        assert "database" in component.manifest.dependencies
        assert "core" in component.manifest.tags

    @pytest.mark.asyncio
    async def test_activate(self):
        """Test component activation."""
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        result = await component.activate()

        assert result is True
        assert component.state == ComponentState.ACTIVE
        assert component.is_active is True
        assert component.activate_called is True
        assert component._stats["activations"] == 1

    @pytest.mark.asyncio
    async def test_activate_already_active(self):
        """Test activating already active component."""
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        await component.activate()
        result = await component.activate()  # Second activation

        assert result is True
        assert component._stats["activations"] == 1  # Not incremented

    @pytest.mark.asyncio
    async def test_deactivate(self):
        """Test component deactivation."""
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        await component.activate()
        result = await component.deactivate()

        assert result is True
        assert component.state == ComponentState.STOPPED
        assert component.is_active is False
        assert component.deactivate_called is True
        assert component._stats["deactivations"] == 1

    @pytest.mark.asyncio
    async def test_pause_and_resume(self):
        """Test pause and resume."""
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        await component.activate()

        # Pause
        result = await component.pause()
        assert result is True
        assert component.state == ComponentState.PAUSED

        # Resume
        result = await component.resume()
        assert result is True
        assert component.state == ComponentState.ACTIVE

    @pytest.mark.asyncio
    async def test_pause_not_active(self):
        """Test pause when not active."""
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        result = await component.pause()
        assert result is False

    @pytest.mark.asyncio
    async def test_resume_not_paused(self):
        """Test resume when not paused."""
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        await component.activate()
        result = await component.resume()
        assert result is False

    @pytest.mark.asyncio
    async def test_mark_degraded(self):
        """Test marking component as degraded."""
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        await component.activate()
        await component.mark_degraded("Partial functionality")

        assert component.state == ComponentState.DEGRADED
        assert component.is_available is True  # Degraded is still available
        assert component._error_message == "Partial functionality"

    def test_trust_adjustment(self):
        """Test trust level adjustment."""
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        assert component.trust_level == 0.5

        component.adjust_trust(0.2)
        assert abs(component.trust_level - 0.7) < 0.01

        component.adjust_trust(0.2)
        assert abs(component.trust_level - 0.9) < 0.01
        # is_trusted becomes True when trust_level >= 0.8
        assert component.manifest.is_trusted is True

    def test_trust_clamping(self):
        """Test trust level is clamped to 0-1."""
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        component.adjust_trust(1.0)
        assert component.trust_level == 1.0

        component.adjust_trust(-2.0)
        assert component.trust_level == 0.0

    def test_set_trusted(self):
        """Test explicitly setting trusted status."""
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        assert component.manifest.is_trusted is False

        component.set_trusted(True)
        assert component.manifest.is_trusted is True

    def test_record_operation(self):
        """Test recording operations."""
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        component.record_operation(success=True)
        component.record_operation(success=True)
        component.record_operation(success=False)

        assert component._stats["operations"] == 3
        assert component._stats["successes"] == 2
        assert component._stats["failures"] == 1
        assert component.get_success_rate() == 2/3

    def test_get_status(self):
        """Test status retrieval."""
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        status = component.get_status()

        assert "component_id" in status
        assert status["name"] == "TestComponent"
        assert status["state"] == "uninitialized"
        assert "stats" in status
        assert "manifest" in status

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check."""
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        await component.activate()
        health = await component.health_check()

        assert health["healthy"] is True
        assert health["state"] == "active"
        assert "uptime_seconds" in health

    @pytest.mark.asyncio
    async def test_activation_error(self):
        """Test activation error handling."""
        class FailingComponent(BaseComponent):
            async def _do_activate(self):
                raise Exception("Activation failed")

            async def _do_deactivate(self):
                pass

        component = FailingComponent(
            name="FailComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        result = await component.activate()

        assert result is False
        assert component.state == ComponentState.ERROR
        assert component._stats["errors"] == 1


# =============================================================================
# ComponentRegistry Tests
# =============================================================================

class TestComponentRegistry:
    """Test ComponentRegistry class."""

    def setup_method(self):
        """Reset registry before each test."""
        reset_registry()

    def test_registry_initialization(self):
        """Test registry initialization."""
        registry = ComponentRegistry()

        assert len(registry._components) == 0
        assert registry._stats["total_registered"] == 0

    def test_register_component(self):
        """Test component registration."""
        registry = ComponentRegistry()
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        component_id = registry.register(component)

        assert component_id == component.component_id
        assert component_id in registry._components
        assert registry._stats["total_registered"] == 1

    def test_register_with_priority(self):
        """Test registration with priority."""
        registry = ComponentRegistry()
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        registry.register(component, auto_start=True, priority=8)

        entry = registry._components[component.component_id]
        assert entry.priority == 8
        assert entry.auto_start is True

    def test_register_duplicate(self):
        """Test registering same component twice."""
        registry = ComponentRegistry()
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        registry.register(component)
        registry.register(component)  # Duplicate

        assert registry._stats["total_registered"] == 1

    def test_unregister_component(self):
        """Test component unregistration."""
        registry = ComponentRegistry()
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test",
            capabilities={"analyze"}
        )

        registry.register(component)
        result = registry.unregister(component.component_id)

        assert result is True
        assert component.component_id not in registry._components

    def test_get_component(self):
        """Test getting component by ID."""
        registry = ComponentRegistry()
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        registry.register(component)

        retrieved = registry.get(component.component_id)
        assert retrieved == component

        missing = registry.get("nonexistent")
        assert missing is None

    def test_get_by_name(self):
        """Test getting component by name."""
        registry = ComponentRegistry()
        component = ConcreteComponent(
            name="TestComponent",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Test"
        )

        registry.register(component)

        retrieved = registry.get_by_name("TestComponent")
        assert retrieved == component

    def test_get_by_role(self):
        """Test getting components by role."""
        registry = ComponentRegistry()

        comp1 = ConcreteComponent(
            name="Cognitive1", version="1.0.0",
            role=ComponentRole.COGNITIVE, description="Test"
        )
        comp2 = ConcreteComponent(
            name="Cognitive2", version="1.0.0",
            role=ComponentRole.COGNITIVE, description="Test"
        )
        comp3 = ConcreteComponent(
            name="Memory1", version="1.0.0",
            role=ComponentRole.MEMORY, description="Test"
        )

        registry.register(comp1)
        registry.register(comp2)
        registry.register(comp3)

        cognitive = registry.get_by_role(ComponentRole.COGNITIVE)
        assert len(cognitive) == 2

        memory = registry.get_by_role(ComponentRole.MEMORY)
        assert len(memory) == 1

    def test_get_by_capability(self):
        """Test getting components by capability."""
        registry = ComponentRegistry()

        comp1 = ConcreteComponent(
            name="Component1", version="1.0.0",
            role=ComponentRole.MEMORY, description="Test",
            capabilities={"vector_store", "search"}
        )
        comp2 = ConcreteComponent(
            name="Component2", version="1.0.0",
            role=ComponentRole.MEMORY, description="Test",
            capabilities={"search"}
        )

        registry.register(comp1)
        registry.register(comp2)

        vector = registry.get_by_capability("vector_store")
        assert len(vector) == 1

        search = registry.get_by_capability("search")
        assert len(search) == 2

    def test_get_by_tag(self):
        """Test getting components by tag."""
        registry = ComponentRegistry()

        comp1 = ConcreteComponent(
            name="Component1", version="1.0.0",
            role=ComponentRole.COGNITIVE, description="Test",
            tags={"core", "critical"}
        )
        comp2 = ConcreteComponent(
            name="Component2", version="1.0.0",
            role=ComponentRole.MEMORY, description="Test",
            tags={"core"}
        )

        registry.register(comp1)
        registry.register(comp2)

        core = registry.get_by_tag("core")
        assert len(core) == 2

        critical = registry.get_by_tag("critical")
        assert len(critical) == 1

    @pytest.mark.asyncio
    async def test_start_all(self):
        """Test starting all components."""
        registry = ComponentRegistry()

        comp1 = ConcreteComponent(
            name="Component1", version="1.0.0",
            role=ComponentRole.COGNITIVE, description="Test"
        )
        comp2 = ConcreteComponent(
            name="Component2", version="1.0.0",
            role=ComponentRole.MEMORY, description="Test"
        )

        registry.register(comp1, priority=5)
        registry.register(comp2, priority=10)

        results = await registry.start_all()

        assert len(results) == 2
        assert all(results.values())
        assert comp1.is_active
        assert comp2.is_active

    @pytest.mark.asyncio
    async def test_stop_all(self):
        """Test stopping all components."""
        registry = ComponentRegistry()

        comp1 = ConcreteComponent(
            name="Component1", version="1.0.0",
            role=ComponentRole.COGNITIVE, description="Test"
        )
        comp2 = ConcreteComponent(
            name="Component2", version="1.0.0",
            role=ComponentRole.MEMORY, description="Test"
        )

        registry.register(comp1)
        registry.register(comp2)
        await registry.start_all()

        results = await registry.stop_all()

        assert len(results) == 2
        assert all(results.values())
        assert comp1.state == ComponentState.STOPPED
        assert comp2.state == ComponentState.STOPPED

    @pytest.mark.asyncio
    async def test_restart_component(self):
        """Test restarting a component."""
        registry = ComponentRegistry()

        component = ConcreteComponent(
            name="Component1", version="1.0.0",
            role=ComponentRole.COGNITIVE, description="Test"
        )

        registry.register(component)
        await registry.start_all()

        assert component.is_active

        result = await registry.restart(component.component_id)

        assert result is True
        assert component.is_active

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """Test health check on all components."""
        registry = ComponentRegistry()

        comp1 = ConcreteComponent(
            name="Component1", version="1.0.0",
            role=ComponentRole.COGNITIVE, description="Test"
        )
        comp2 = ConcreteComponent(
            name="Component2", version="1.0.0",
            role=ComponentRole.MEMORY, description="Test"
        )

        registry.register(comp1)
        registry.register(comp2)
        await registry.start_all()

        results = await registry.health_check_all()

        assert len(results) == 2
        for cid, health in results.items():
            assert health["healthy"] is True

    def test_get_system_health(self):
        """Test system health summary."""
        registry = ComponentRegistry()

        comp1 = ConcreteComponent(
            name="Component1", version="1.0.0",
            role=ComponentRole.COGNITIVE, description="Test"
        )

        registry.register(comp1)

        health = registry.get_system_health()

        assert health["total_components"] == 1
        assert "health_score" in health
        assert health["status"] in ["healthy", "degraded", "critical"]

    def test_get_stats(self):
        """Test registry statistics."""
        registry = ComponentRegistry()

        comp1 = ConcreteComponent(
            name="Component1", version="1.0.0",
            role=ComponentRole.COGNITIVE, description="Test",
            capabilities={"analyze"}
        )

        registry.register(comp1)

        stats = registry.get_stats()

        assert stats["total_registered"] == 1
        assert "components_by_role" in stats
        assert stats["capabilities_registered"] == 1

    def test_get_manifests(self):
        """Test getting all manifests."""
        registry = ComponentRegistry()

        comp1 = ConcreteComponent(
            name="Component1", version="1.0.0",
            role=ComponentRole.COGNITIVE, description="Test"
        )

        registry.register(comp1, priority=8)

        manifests = registry.get_manifests()

        assert len(manifests) == 1
        assert manifests[0]["name"] == "Component1"
        assert manifests[0]["priority"] == 8

    def test_global_registry(self):
        """Test global registry singleton."""
        reset_registry()

        reg1 = get_component_registry()
        reg2 = get_component_registry()

        assert reg1 is reg2


# =============================================================================
# LoopType and LoopStatus Tests
# =============================================================================

class TestLoopEnums:
    """Test loop-related enums."""

    def test_loop_types(self):
        """Test LoopType enum."""
        expected = ['OODA', 'REFLECTION', 'LEARNING', 'PLANNING',
                    'EXECUTION', 'GOVERNANCE', 'MEMORY', 'REASONING']
        for loop_type in expected:
            assert hasattr(LoopType, loop_type)

    def test_loop_statuses(self):
        """Test LoopStatus enum."""
        expected = ['PENDING', 'RUNNING', 'COMPLETED', 'FAILED',
                    'INTERRUPTED', 'TIMEOUT']
        for status in expected:
            assert hasattr(LoopStatus, status)


# =============================================================================
# ReasoningStep Tests
# =============================================================================

class TestReasoningStep:
    """Test ReasoningStep dataclass."""

    def test_default_step(self):
        """Test default reasoning step."""
        step = ReasoningStep()

        assert step.step_id.startswith("step-")
        assert step.step_number == 0
        assert step.description == ""
        assert step.output == ""
        assert step.confidence == 0.5
        assert step.duration_ms == 0.0

    def test_step_with_values(self):
        """Test step with custom values."""
        step = ReasoningStep(
            step_number=1,
            description="Analyze input",
            output="Input is valid JSON",
            confidence=0.95,
            duration_ms=150.5,
            metadata={"tokens": 100}
        )

        assert step.step_number == 1
        assert step.description == "Analyze input"
        assert step.confidence == 0.95
        assert step.metadata["tokens"] == 100

    def test_step_to_dict(self):
        """Test step serialization."""
        step = ReasoningStep(
            step_number=1,
            description="Test step",
            confidence=0.8
        )

        data = step.to_dict()

        assert data["step_number"] == 1
        assert data["description"] == "Test step"
        assert data["confidence"] == 0.8
        assert "step_id" in data


# =============================================================================
# LoopMetadata Tests
# =============================================================================

class TestLoopMetadata:
    """Test LoopMetadata dataclass."""

    def test_default_metadata(self):
        """Test default metadata values."""
        meta = LoopMetadata()

        assert meta.triggered_by == "system"
        assert meta.parent_loop_id is None
        assert meta.governance_approved is True
        assert meta.autonomy_tier == "tier_0_supervised"
        assert meta.learnable is True
        assert meta.patterns_extracted == 0
        assert meta.tokens_used == 0

    def test_metadata_to_dict(self):
        """Test metadata serialization."""
        meta = LoopMetadata(
            triggered_by="user",
            governance_decision_id="GOV-123",
            tokens_used=500,
            tags=["important", "learning"]
        )

        data = meta.to_dict()

        assert data["triggered_by"] == "user"
        assert data["governance_decision_id"] == "GOV-123"
        assert data["tokens_used"] == 500
        assert "important" in data["tags"]


# =============================================================================
# GraceLoopOutput Tests
# =============================================================================

class TestGraceLoopOutput:
    """Test GraceLoopOutput dataclass."""

    def test_default_output(self):
        """Test default loop output."""
        output = GraceLoopOutput()

        assert output.loop_id.startswith("loop-")
        assert output.reasoning_chain_id.startswith("chain-")
        assert output.loop_type == LoopType.REASONING
        assert output.status == LoopStatus.PENDING
        assert output.confidence == 0.0
        assert len(output.reasoning_steps) == 0

    def test_output_with_type(self):
        """Test output with specific loop type."""
        output = GraceLoopOutput(
            loop_type=LoopType.OODA,
            input_context={"query": "What is the status?"}
        )

        assert output.loop_type == LoopType.OODA
        assert output.input_context["query"] == "What is the status?"

    def test_add_reasoning_step(self):
        """Test adding reasoning steps."""
        output = GraceLoopOutput(loop_type=LoopType.OODA)

        step1 = output.add_reasoning_step(
            description="Observe current state",
            output="System is running normally",
            confidence=0.9
        )

        step2 = output.add_reasoning_step(
            description="Orient to context",
            output="No anomalies detected",
            confidence=0.85
        )

        assert len(output.reasoning_steps) == 2
        assert step1.step_number == 1
        assert step2.step_number == 2
        assert output.step_count == 2

    def test_get_reasoning_trace(self):
        """Test getting human-readable trace."""
        output = GraceLoopOutput(loop_type=LoopType.OODA)

        output.add_reasoning_step(
            description="Step 1",
            output="Result 1",
            confidence=0.9
        )
        output.add_reasoning_step(
            description="Step 2",
            output="Result 2",
            confidence=0.8
        )

        trace = output.get_reasoning_trace()

        assert "ooda" in trace.lower()
        assert "Step 1" in trace
        assert "Step 2" in trace
        assert "0.90" in trace

    def test_lifecycle_start(self):
        """Test loop start."""
        output = GraceLoopOutput()
        output.start()

        assert output.status == LoopStatus.RUNNING

    def test_lifecycle_complete(self):
        """Test loop completion."""
        output = GraceLoopOutput()
        output.start()
        output.complete(
            result={"status": "healthy"},
            confidence=0.95,
            summary="Determined system is healthy"
        )

        assert output.status == LoopStatus.COMPLETED
        assert output.result["status"] == "healthy"
        assert output.confidence == 0.95
        assert output.result_summary == "Determined system is healthy"
        assert output.completed_at is not None
        assert output.duration_ms > 0
        assert output.success is True

    def test_lifecycle_fail(self):
        """Test loop failure."""
        output = GraceLoopOutput()
        output.start()
        output.fail(
            error="Processing failed",
            details={"code": 500, "reason": "timeout"}
        )

        assert output.status == LoopStatus.FAILED
        assert output.error == "Processing failed"
        assert output.error_details["code"] == 500
        assert output.failed is True

    def test_lifecycle_interrupt(self):
        """Test loop interruption."""
        output = GraceLoopOutput()
        output.start()
        output.interrupt("User cancelled")

        assert output.status == LoopStatus.INTERRUPTED
        assert "User cancelled" in output.error

    def test_average_step_confidence(self):
        """Test average confidence calculation."""
        output = GraceLoopOutput()

        output.add_reasoning_step(description="S1", confidence=0.9)
        output.add_reasoning_step(description="S2", confidence=0.8)
        output.add_reasoning_step(description="S3", confidence=0.7)

        assert abs(output.average_step_confidence - 0.8) < 0.01

    def test_average_step_confidence_empty(self):
        """Test average confidence with no steps."""
        output = GraceLoopOutput()
        assert output.average_step_confidence == 0.0

    def test_to_dict(self):
        """Test output serialization."""
        output = GraceLoopOutput(
            loop_type=LoopType.OODA,
            input_context={"query": "test"}
        )
        output.start()
        output.add_reasoning_step(description="Step 1", confidence=0.9)
        output.complete(result={"answer": "yes"}, confidence=0.85)

        data = output.to_dict()

        assert "loop_id" in data
        assert data["loop_type"] == "ooda"
        assert data["status"] == "completed"
        assert data["input_context"]["query"] == "test"
        assert len(data["reasoning_steps"]) == 1
        assert data["result"]["answer"] == "yes"
        assert data["confidence"] == 0.85
        assert "metadata" in data

    def test_from_dict(self):
        """Test output deserialization."""
        data = {
            "loop_id": "loop-test123",
            "reasoning_chain_id": "chain-test",
            "loop_type": "ooda",
            "status": "completed",
            "input_context": {"query": "test"},
            "reasoning_steps": [
                {
                    "step_id": "step-1",
                    "step_number": 1,
                    "description": "Observe",
                    "output": "System OK",
                    "confidence": 0.9,
                    "duration_ms": 100,
                    "metadata": {}
                }
            ],
            "result": {"status": "healthy"},
            "result_summary": "All systems operational",
            "confidence": 0.95,
            "started_at": "2024-01-01T12:00:00",
            "completed_at": "2024-01-01T12:00:01",
            "duration_ms": 1000,
            "metadata": {
                "triggered_by": "user",
                "tokens_used": 500
            }
        }

        output = GraceLoopOutput.from_dict(data)

        assert output.loop_id == "loop-test123"
        assert output.loop_type == LoopType.OODA
        assert output.status == LoopStatus.COMPLETED
        assert len(output.reasoning_steps) == 1
        assert output.reasoning_steps[0].description == "Observe"
        assert output.confidence == 0.95
        assert output.metadata.triggered_by == "user"
        assert output.metadata.tokens_used == 500

    def test_repr(self):
        """Test string representation."""
        output = GraceLoopOutput(loop_type=LoopType.OODA)
        output.add_reasoning_step(description="Step 1", confidence=0.9)
        output.complete(result={}, confidence=0.85)

        repr_str = repr(output)

        assert "GraceLoopOutput" in repr_str
        assert "ooda" in repr_str
        assert "completed" in repr_str


# =============================================================================
# Integration Tests
# =============================================================================

class TestCoreIntegration:
    """Integration tests for core module."""

    def setup_method(self):
        """Reset state before each test."""
        reset_registry()

    @pytest.mark.asyncio
    async def test_full_component_lifecycle(self):
        """Test complete component lifecycle through registry."""
        registry = get_component_registry()

        # Create components with dependencies
        base_component = ConcreteComponent(
            name="BaseService",
            version="1.0.0",
            role=ComponentRole.INFRASTRUCTURE,
            description="Base infrastructure"
        )

        dependent_component = ConcreteComponent(
            name="DependentService",
            version="1.0.0",
            role=ComponentRole.COGNITIVE,
            description="Depends on base",
            dependencies={base_component.component_id}
        )

        # Register
        registry.register(base_component, priority=10)
        registry.register(dependent_component, priority=5)

        # Start
        results = await registry.start_all()
        assert all(results.values())

        # Health check
        health = await registry.health_check_all()
        assert all(h["healthy"] for h in health.values())

        # Stop
        results = await registry.stop_all()
        assert all(results.values())

    @pytest.mark.asyncio
    async def test_loop_output_in_component(self):
        """Test using GraceLoopOutput in component operations."""
        class LoopComponent(BaseComponent):
            def __init__(self):
                super().__init__(
                    name="LoopComponent",
                    version="1.0.0",
                    role=ComponentRole.COGNITIVE,
                    description="Uses loops"
                )
                self.last_output = None

            async def _do_activate(self):
                pass

            async def _do_deactivate(self):
                pass

            async def process(self, query: str) -> GraceLoopOutput:
                output = GraceLoopOutput(
                    loop_type=LoopType.OODA,
                    input_context={"query": query}
                )
                output.start()

                output.add_reasoning_step(
                    description="Observe query",
                    output=f"Query received: {query}",
                    confidence=1.0
                )

                output.add_reasoning_step(
                    description="Process query",
                    output="Query processed successfully",
                    confidence=0.95
                )

                output.complete(
                    result={"processed": True},
                    confidence=0.95,
                    summary="Query processed"
                )

                self.last_output = output
                self.record_operation(success=True)
                return output

        component = LoopComponent()
        await component.activate()

        output = await component.process("test query")

        assert output.success
        assert output.step_count == 2
        assert component.get_success_rate() == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
