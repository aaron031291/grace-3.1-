from __future__ import annotations
import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Set, Type, TYPE_CHECKING
from base_component import BaseComponent, ComponentState, ComponentRole, ComponentManifest
logger = logging.getLogger(__name__)

class RegistryEntry:
    """Entry in the component registry."""
    component: BaseComponent
    registered_at: datetime = field(default_factory=datetime.utcnow)
    auto_start: bool = True
    priority: int = 5  # 1-10, higher = starts first


class ComponentRegistry:
    """
    Central registry for all Grace components.

    Provides:
    - Component registration and discovery
    - Dependency-aware lifecycle management
    - Health monitoring across all components
    - Role-based component lookup
    - Message bus integration

    Usage:
        registry = get_component_registry()

        # Register components
        registry.register(my_component, auto_start=True, priority=8)

        # Start all components (respects dependencies)
        await registry.start_all()

        # Find components
        cognitive_components = registry.get_by_role(ComponentRole.COGNITIVE)
        memory_component = registry.get_by_capability("vector_store")

        # Stop all components
        await registry.stop_all()
    """

    def __init__(self, message_bus: Optional['Layer1MessageBus'] = None):
        # Component storage
        self._components: Dict[str, RegistryEntry] = {}

        # Indexes for fast lookup
        self._by_role: Dict[ComponentRole, Set[str]] = defaultdict(set)
        self._by_capability: Dict[str, Set[str]] = defaultdict(set)
        self._by_tag: Dict[str, Set[str]] = defaultdict(set)

        # Message bus for system events
        self._message_bus = message_bus

        # Registry stats
        self._stats = {
            "total_registered": 0,
            "active": 0,
            "failed": 0,
            "start_operations": 0,
            "stop_operations": 0,
        }

        logger.info("[REGISTRY] Component Registry initialized")

    # =========================================================================
    # REGISTRATION
    # =========================================================================

    def register(
        self,
        component: BaseComponent,
        auto_start: bool = True,
        priority: int = 5,
    ) -> str:
        """
        Register a component with the registry.

        Args:
            component: Component to register
            auto_start: Whether to auto-start on start_all()
            priority: Start priority (1-10, higher = starts first)

        Returns:
            Component ID
        """
        component_id = component.component_id

        if component_id in self._components:
            logger.warning(f"[REGISTRY] Component already registered: {component_id}")
            return component_id

        # Set message bus
        if self._message_bus:
            component.set_message_bus(self._message_bus)

        # Create entry
        entry = RegistryEntry(
            component=component,
            auto_start=auto_start,
            priority=priority,
        )
        self._components[component_id] = entry

        # Update indexes
        manifest = component.manifest
        self._by_role[manifest.role].add(component_id)

        for capability in manifest.capabilities:
            self._by_capability[capability].add(component_id)

        for tag in manifest.tags:
            self._by_tag[tag].add(component_id)

        self._stats["total_registered"] += 1

        logger.info(
            f"[REGISTRY] Registered: {component.name} "
            f"(id={component_id}, role={manifest.role.value}, priority={priority})"
        )

        return component_id

    def unregister(self, component_id: str) -> bool:
        """Unregister a component."""
        if component_id not in self._components:
            logger.warning(f"[REGISTRY] Component not found: {component_id}")
            return False

        entry = self._components[component_id]
        manifest = entry.component.manifest

        # Remove from indexes
        self._by_role[manifest.role].discard(component_id)

        for capability in manifest.capabilities:
            self._by_capability[capability].discard(component_id)

        for tag in manifest.tags:
            self._by_tag[tag].discard(component_id)

        del self._components[component_id]

        logger.info(f"[REGISTRY] Unregistered: {entry.component.name}")
        return True

    # =========================================================================
    # LOOKUP
    # =========================================================================

    def get(self, component_id: str) -> Optional[BaseComponent]:
        """Get component by ID."""
        entry = self._components.get(component_id)
        return entry.component if entry else None

    def get_by_name(self, name: str) -> Optional[BaseComponent]:
        """Get component by name (first match)."""
        for entry in self._components.values():
            if entry.component.name == name:
                return entry.component
        return None

    def get_by_role(self, role: ComponentRole) -> List[BaseComponent]:
        """Get all components with a specific role."""
        component_ids = self._by_role.get(role, set())
        return [
            self._components[cid].component
            for cid in component_ids
            if cid in self._components
        ]

    def get_by_capability(self, capability: str) -> List[BaseComponent]:
        """Get all components with a specific capability."""
        component_ids = self._by_capability.get(capability, set())
        return [
            self._components[cid].component
            for cid in component_ids
            if cid in self._components
        ]

    def get_by_tag(self, tag: str) -> List[BaseComponent]:
        """Get all components with a specific tag."""
        component_ids = self._by_tag.get(tag, set())
        return [
            self._components[cid].component
            for cid in component_ids
            if cid in self._components
        ]

    def get_active(self) -> List[BaseComponent]:
        """Get all active components."""
        return [
            entry.component
            for entry in self._components.values()
            if entry.component.is_active
        ]

    def get_all(self) -> List[BaseComponent]:
        """Get all registered components."""
        return [entry.component for entry in self._components.values()]

    # =========================================================================
    # LIFECYCLE MANAGEMENT
    # =========================================================================

    async def start_all(self) -> Dict[str, bool]:
        """
        Start all auto-start components in priority order.

        Returns dict of component_id -> success
        """
        self._stats["start_operations"] += 1
        results = {}

        # Sort by priority (higher first)
        entries = sorted(
            [(cid, entry) for cid, entry in self._components.items() if entry.auto_start],
            key=lambda x: x[1].priority,
            reverse=True,
        )

        # Check dependencies and reorder
        ordered_entries = self._dependency_order(entries)

        for component_id, entry in ordered_entries:
            component = entry.component

            # Check dependencies are satisfied
            if not self._dependencies_satisfied(component):
                logger.warning(
                    f"[REGISTRY] Skipping {component.name}: dependencies not satisfied"
                )
                results[component_id] = False
                continue

            # Activate
            success = await component.activate()
            results[component_id] = success

            if success:
                self._stats["active"] += 1
            else:
                self._stats["failed"] += 1

        logger.info(
            f"[REGISTRY] Started {sum(results.values())}/{len(results)} components"
        )

        return results

    async def stop_all(self) -> Dict[str, bool]:
        """
        Stop all components in reverse priority order.

        Returns dict of component_id -> success
        """
        self._stats["stop_operations"] += 1
        results = {}

        # Sort by priority (lower first - stop dependencies last)
        entries = sorted(
            self._components.items(),
            key=lambda x: x[1].priority,
        )

        for component_id, entry in entries:
            component = entry.component

            if component.state in [ComponentState.STOPPED, ComponentState.UNINITIALIZED]:
                results[component_id] = True
                continue

            success = await component.deactivate()
            results[component_id] = success

            if success:
                self._stats["active"] = max(0, self._stats["active"] - 1)

        logger.info(
            f"[REGISTRY] Stopped {sum(results.values())}/{len(results)} components"
        )

        return results

    async def restart(self, component_id: str) -> bool:
        """Restart a specific component."""
        component = self.get(component_id)
        if not component:
            logger.warning(f"[REGISTRY] Component not found: {component_id}")
            return False

        await component.deactivate()
        return await component.activate()

    def _dependencies_satisfied(self, component: BaseComponent) -> bool:
        """Check if all dependencies are active."""
        for dep_id in component.manifest.dependencies:
            dep_component = self.get(dep_id)
            if not dep_component or not dep_component.is_active:
                return False
        return True

    def _dependency_order(
        self,
        entries: List[tuple[str, RegistryEntry]]
    ) -> List[tuple[str, RegistryEntry]]:
        """Reorder entries to respect dependencies (simple topological sort)."""
        # Build dependency graph
        ordered = []
        remaining = list(entries)
        started = set()
        max_iterations = len(entries) * 2  # Prevent infinite loops

        iteration = 0
        while remaining and iteration < max_iterations:
            iteration += 1
            for item in remaining[:]:
                cid, entry = item
                deps = entry.component.manifest.dependencies

                # Can start if no deps or all deps started
                if not deps or deps.issubset(started):
                    ordered.append(item)
                    remaining.remove(item)
                    started.add(cid)

        # Add any remaining (circular dependencies)
        ordered.extend(remaining)

        return ordered

    # =========================================================================
    # HEALTH MONITORING
    # =========================================================================

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Run health checks on all components."""
        results = {}

        for component_id, entry in self._components.items():
            try:
                health = await entry.component.health_check()
                results[component_id] = health
            except Exception as e:
                results[component_id] = {
                    "component_id": component_id,
                    "healthy": False,
                    "error": str(e),
                }

        return results

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health summary."""
        total = len(self._components)
        active = sum(1 for e in self._components.values() if e.component.is_active)
        degraded = sum(
            1 for e in self._components.values()
            if e.component.state == ComponentState.DEGRADED
        )
        failed = sum(
            1 for e in self._components.values()
            if e.component.state == ComponentState.ERROR
        )

        # Calculate health score
        if total == 0:
            health_score = 1.0
        else:
            health_score = (active + degraded * 0.5) / total

        return {
            "total_components": total,
            "active": active,
            "degraded": degraded,
            "failed": failed,
            "stopped": total - active - degraded - failed,
            "health_score": health_score,
            "status": "healthy" if health_score >= 0.9 else "degraded" if health_score >= 0.5 else "critical",
        }

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return {
            **self._stats,
            "components_by_role": {
                role.value: len(ids)
                for role, ids in self._by_role.items()
            },
            "capabilities_registered": len(self._by_capability),
            "tags_registered": len(self._by_tag),
        }

    def get_manifests(self) -> List[Dict[str, Any]]:
        """Get all component manifests."""
        return [
            {
                **entry.component.manifest.to_dict(),
                "state": entry.component.state.value,
                "auto_start": entry.auto_start,
                "priority": entry.priority,
            }
            for entry in self._components.values()
        ]

    # =========================================================================
    # MESSAGE BUS
    # =========================================================================

    def set_message_bus(self, message_bus: 'Layer1MessageBus'):
        """Set message bus for all components."""
        self._message_bus = message_bus

        for entry in self._components.values():
            entry.component.set_message_bus(message_bus)


# =============================================================================
# SINGLETON
# =============================================================================

_registry: Optional[ComponentRegistry] = None


def get_component_registry() -> ComponentRegistry:
    """Get or create the global component registry."""
    global _registry
    if _registry is None:
        _registry = ComponentRegistry()
        logger.info("[REGISTRY] Created global Component Registry")
    return _registry


def reset_registry():
    """Reset the registry (for testing)."""
    global _registry
    _registry = None
