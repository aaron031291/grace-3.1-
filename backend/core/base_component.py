"""
Base Component - Unified Component Abstraction

Addresses Clarity Class 1 (Structural Ambiguity):
- Consistent component definitions
- Clear lifecycle methods
- Standardized status reporting
- Trust and role tracking

All Grace components should inherit from BaseComponent.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from layer1.message_bus import Layer1MessageBus

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class ComponentState(Enum):
    """Component lifecycle states."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    DEGRADED = "degraded"  # Partially functional
    ERROR = "error"
    STOPPING = "stopping"
    STOPPED = "stopped"


class ComponentRole(Enum):
    """Component functional roles in the Grace system."""
    COGNITIVE = "cognitive"           # Thinking/reasoning (OODA, etc.)
    MEMORY = "memory"                 # Storage/retrieval
    EXECUTION = "execution"           # Action execution
    LEARNING = "learning"             # Pattern learning
    GOVERNANCE = "governance"         # Policy enforcement
    ORCHESTRATION = "orchestration"   # Coordination
    INTEGRATION = "integration"       # External interfaces
    INFRASTRUCTURE = "infrastructure" # Supporting services


# =============================================================================
# COMPONENT MANIFEST
# =============================================================================

@dataclass
class ComponentManifest:
    """
    Metadata describing a component.

    Addresses Clarity Class 4 (Subsystem Activation Ambiguity):
    - Trust flags
    - Active state tracking
    - Role tags
    - Capability declarations
    """
    component_id: str
    name: str
    version: str
    role: ComponentRole
    description: str

    # Trust and permissions
    trust_level: float = 0.5  # 0.0 - 1.0
    is_trusted: bool = False  # Has earned trust
    requires_governance: bool = True

    # Capabilities this component provides
    capabilities: Set[str] = field(default_factory=set)

    # Dependencies (other component IDs)
    dependencies: Set[str] = field(default_factory=set)

    # Tags for filtering/discovery
    tags: Set[str] = field(default_factory=set)

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_active_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "name": self.name,
            "version": self.version,
            "role": self.role.value,
            "description": self.description,
            "trust_level": self.trust_level,
            "is_trusted": self.is_trusted,
            "requires_governance": self.requires_governance,
            "capabilities": list(self.capabilities),
            "dependencies": list(self.dependencies),
            "tags": list(self.tags),
            "created_at": self.created_at.isoformat(),
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
        }


# =============================================================================
# BASE COMPONENT
# =============================================================================

class BaseComponent(ABC):
    """
    Abstract base class for all Grace components.

    Provides:
    - Unified lifecycle management (activate, deactivate, pause, resume)
    - Standardized status reporting
    - Health checking
    - Message bus integration
    - Trust tracking

    Usage:
        class MyComponent(BaseComponent):
            def __init__(self):
                super().__init__(
                    name="MyComponent",
                    version="1.0.0",
                    role=ComponentRole.COGNITIVE,
                    description="Does something useful",
                )

            async def _do_activate(self):
                # Component-specific activation logic
                pass

            async def _do_deactivate(self):
                # Component-specific cleanup
                pass
    """

    def __init__(
        self,
        name: str,
        version: str,
        role: ComponentRole,
        description: str,
        requires_governance: bool = True,
        capabilities: Optional[Set[str]] = None,
        dependencies: Optional[Set[str]] = None,
        tags: Optional[Set[str]] = None,
    ):
        # Generate unique ID
        self._component_id = f"{name.lower().replace(' ', '_')}-{uuid.uuid4().hex[:8]}"

        # Build manifest
        self._manifest = ComponentManifest(
            component_id=self._component_id,
            name=name,
            version=version,
            role=role,
            description=description,
            requires_governance=requires_governance,
            capabilities=capabilities or set(),
            dependencies=dependencies or set(),
            tags=tags or set(),
        )

        # State tracking
        self._state = ComponentState.UNINITIALIZED
        self._state_history: List[Dict[str, Any]] = []
        self._error_message: Optional[str] = None

        # Statistics
        self._stats = {
            "activations": 0,
            "deactivations": 0,
            "errors": 0,
            "operations": 0,
            "successes": 0,
            "failures": 0,
        }

        # Message bus (set during registration)
        self._message_bus: Optional['Layer1MessageBus'] = None

        logger.debug(f"[{name}] BaseComponent initialized: {self._component_id}")

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def component_id(self) -> str:
        """Unique component identifier."""
        return self._component_id

    @property
    def name(self) -> str:
        """Human-readable component name."""
        return self._manifest.name

    @property
    def manifest(self) -> ComponentManifest:
        """Component manifest with metadata."""
        return self._manifest

    @property
    def state(self) -> ComponentState:
        """Current component state."""
        return self._state

    @property
    def is_active(self) -> bool:
        """Whether component is active and ready."""
        return self._state == ComponentState.ACTIVE

    @property
    def is_available(self) -> bool:
        """Whether component can accept operations."""
        return self._state in [ComponentState.ACTIVE, ComponentState.DEGRADED]

    @property
    def trust_level(self) -> float:
        """Current trust level."""
        return self._manifest.trust_level

    # =========================================================================
    # LIFECYCLE MANAGEMENT
    # =========================================================================

    async def activate(self) -> bool:
        """
        Activate the component.

        Returns True if activation succeeded.
        """
        if self._state == ComponentState.ACTIVE:
            logger.debug(f"[{self.name}] Already active")
            return True

        if self._state == ComponentState.STOPPING:
            logger.warning(f"[{self.name}] Cannot activate while stopping")
            return False

        try:
            self._set_state(ComponentState.INITIALIZING)
            logger.info(f"[{self.name}] Activating...")

            # Call subclass implementation
            await self._do_activate()

            self._set_state(ComponentState.ACTIVE)
            self._manifest.last_active_at = datetime.utcnow()
            self._stats["activations"] += 1

            logger.info(f"[{self.name}] Activated successfully")
            return True

        except Exception as e:
            self._error_message = str(e)
            self._set_state(ComponentState.ERROR)
            self._stats["errors"] += 1
            logger.exception(f"[{self.name}] Activation failed: {e}")
            return False

    async def deactivate(self) -> bool:
        """
        Deactivate the component gracefully.

        Returns True if deactivation succeeded.
        """
        if self._state == ComponentState.STOPPED:
            logger.debug(f"[{self.name}] Already stopped")
            return True

        try:
            self._set_state(ComponentState.STOPPING)
            logger.info(f"[{self.name}] Deactivating...")

            # Call subclass implementation
            await self._do_deactivate()

            self._set_state(ComponentState.STOPPED)
            self._stats["deactivations"] += 1

            logger.info(f"[{self.name}] Deactivated successfully")
            return True

        except Exception as e:
            self._error_message = str(e)
            self._set_state(ComponentState.ERROR)
            self._stats["errors"] += 1
            logger.exception(f"[{self.name}] Deactivation failed: {e}")
            return False

    async def pause(self) -> bool:
        """Pause component operations (can resume)."""
        if not self.is_active:
            logger.warning(f"[{self.name}] Cannot pause - not active")
            return False

        self._set_state(ComponentState.PAUSED)
        logger.info(f"[{self.name}] Paused")
        return True

    async def resume(self) -> bool:
        """Resume paused component."""
        if self._state != ComponentState.PAUSED:
            logger.warning(f"[{self.name}] Cannot resume - not paused")
            return False

        self._set_state(ComponentState.ACTIVE)
        logger.info(f"[{self.name}] Resumed")
        return True

    async def mark_degraded(self, reason: str):
        """Mark component as degraded but functional."""
        self._set_state(ComponentState.DEGRADED)
        self._error_message = reason
        logger.warning(f"[{self.name}] Degraded: {reason}")

    # =========================================================================
    # ABSTRACT METHODS (Subclass Implementation)
    # =========================================================================

    @abstractmethod
    async def _do_activate(self):
        """
        Component-specific activation logic.

        Override this in subclasses to:
        - Initialize resources
        - Connect to dependencies
        - Start background tasks
        """
        pass

    @abstractmethod
    async def _do_deactivate(self):
        """
        Component-specific deactivation logic.

        Override this in subclasses to:
        - Release resources
        - Stop background tasks
        - Flush buffers
        """
        pass

    # =========================================================================
    # STATUS AND HEALTH
    # =========================================================================

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive component status."""
        return {
            "component_id": self._component_id,
            "name": self.name,
            "state": self._state.value,
            "is_active": self.is_active,
            "is_available": self.is_available,
            "error": self._error_message,
            "trust_level": self._manifest.trust_level,
            "stats": self._stats.copy(),
            "manifest": self._manifest.to_dict(),
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.

        Override in subclasses for specific health checks.
        """
        healthy = self.is_available and self._error_message is None

        return {
            "component_id": self._component_id,
            "healthy": healthy,
            "state": self._state.value,
            "error": self._error_message,
            "uptime_seconds": self._get_uptime_seconds(),
        }

    def _get_uptime_seconds(self) -> float:
        """Calculate uptime since last activation."""
        if not self._manifest.last_active_at:
            return 0.0
        return (datetime.utcnow() - self._manifest.last_active_at).total_seconds()

    # =========================================================================
    # TRUST MANAGEMENT
    # =========================================================================

    def adjust_trust(self, delta: float):
        """Adjust trust level (clamped to 0.0-1.0)."""
        old_trust = self._manifest.trust_level
        self._manifest.trust_level = max(0.0, min(1.0, old_trust + delta))

        # Mark as trusted if above threshold
        if self._manifest.trust_level >= 0.8:
            self._manifest.is_trusted = True

        logger.debug(
            f"[{self.name}] Trust adjusted: {old_trust:.3f} -> {self._manifest.trust_level:.3f}"
        )

    def set_trusted(self, trusted: bool):
        """Explicitly set trusted status."""
        self._manifest.is_trusted = trusted

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def record_operation(self, success: bool):
        """Record an operation result."""
        self._stats["operations"] += 1
        if success:
            self._stats["successes"] += 1
        else:
            self._stats["failures"] += 1

    def get_success_rate(self) -> float:
        """Get operation success rate."""
        total = self._stats["operations"]
        if total == 0:
            return 1.0
        return self._stats["successes"] / total

    # =========================================================================
    # MESSAGE BUS INTEGRATION
    # =========================================================================

    def set_message_bus(self, message_bus: 'Layer1MessageBus'):
        """Set message bus for event publishing."""
        self._message_bus = message_bus

    async def publish_event(self, topic: str, payload: Dict[str, Any]):
        """Publish event to message bus."""
        if not self._message_bus:
            logger.warning(f"[{self.name}] No message bus configured")
            return

        from layer1.message_bus import ComponentType

        # Map role to component type
        role_to_type = {
            ComponentRole.COGNITIVE: ComponentType.COGNITIVE_ENGINE,
            ComponentRole.MEMORY: ComponentType.MEMORY_MESH,
            ComponentRole.LEARNING: ComponentType.LEARNING_MEMORY,
            ComponentRole.GOVERNANCE: ComponentType.GENESIS_KEYS,
        }

        component_type = role_to_type.get(
            self._manifest.role,
            ComponentType.COGNITIVE_ENGINE
        )

        await self._message_bus.publish(
            topic=topic,
            payload={
                "component_id": self._component_id,
                **payload,
            },
            from_component=component_type,
        )

    # =========================================================================
    # INTERNAL HELPERS
    # =========================================================================

    def _set_state(self, new_state: ComponentState):
        """Set component state with history tracking."""
        old_state = self._state
        self._state = new_state

        # Clear error on successful state transition
        if new_state == ComponentState.ACTIVE:
            self._error_message = None

        # Track state history
        self._state_history.append({
            "from_state": old_state.value,
            "to_state": new_state.value,
            "timestamp": datetime.utcnow().isoformat(),
        })

        # Keep history bounded
        if len(self._state_history) > 100:
            self._state_history = self._state_history[-100:]

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.name}, state={self._state.value})>"
