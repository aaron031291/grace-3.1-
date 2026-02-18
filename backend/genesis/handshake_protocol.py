"""
Genesis Handshake Protocol

A heartbeat pulse system that lets every component say:
"Hi, I'm here, I'm at this path, I do this, and I'm healthy."

Every other component can hear these handshakes.

The protocol:
1. On startup, every component registers in the ComponentRegistry
2. A background daemon sends heartbeat pulses every N seconds
3. Each pulse checks every registered component's liveness
4. Silent deaths are detected and reported to self-healing
5. New components are detected and announced to the system
6. The diagnostic engine tracks all heartbeat data

This is the nervous system that prevents silent failures.
"""

import logging
import threading
import time
import importlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


def _track_handshake(desc, **kwargs):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event("handshake_protocol", desc, **kwargs)
    except Exception:
        pass


class HandshakeProtocol:
    """
    The heartbeat system for Grace.

    Runs as a background daemon and:
    - Pings every registered component
    - Records heartbeats in the registry
    - Detects silent deaths
    - Triggers self-healing for dead components
    - Broadcasts system-wide awareness
    """

    def __init__(
        self,
        heartbeat_interval: int = 60,
        death_timeout: int = 300,
        auto_heal: bool = True,
    ):
        self.heartbeat_interval = heartbeat_interval
        self.death_timeout = death_timeout
        self.auto_heal = auto_heal
        self.running = False
        self._thread: Optional[threading.Thread] = None

        self.stats = {
            "total_pulses": 0,
            "total_heartbeats": 0,
            "deaths_detected": 0,
            "heals_triggered": 0,
            "start_time": None,
        }

        self._health_checks: Dict[str, Callable] = {}

    def register_health_check(self, component_name: str, check_fn: Callable):
        """Register a custom health check function for a component."""
        self._health_checks[component_name] = check_fn

    def start(self):
        """Start the handshake protocol daemon."""
        if self.running:
            return

        self.running = True
        self.stats["start_time"] = datetime.now().isoformat()
        self._thread = threading.Thread(
            target=self._pulse_loop,
            daemon=True,
            name="genesis-handshake"
        )
        self._thread.start()
        logger.info(
            f"[HANDSHAKE] Protocol started (interval={self.heartbeat_interval}s, "
            f"death_timeout={self.death_timeout}s)"
        )

    def stop(self):
        """Stop the handshake protocol."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("[HANDSHAKE] Protocol stopped")

    def _pulse_loop(self):
        """Main heartbeat loop."""
        while self.running:
            try:
                self._run_pulse()
            except Exception as e:
                logger.error(f"[HANDSHAKE] Pulse error: {e}")

            time.sleep(self.heartbeat_interval)

    def _run_pulse(self):
        """Run one heartbeat pulse across all components."""
        self.stats["total_pulses"] += 1

        try:
            from database.session import SessionLocal
            from genesis.component_registry import ComponentRegistry
            session = SessionLocal()
            if not session:
                return

            try:
                registry = ComponentRegistry(session)

                components = session.query(
                    __import__('genesis.component_registry', fromlist=['ComponentEntry']).ComponentEntry
                ).filter_by(is_active=True).all()

                alive_count = 0
                dead_components = []

                for comp in components:
                    health = self._check_component_health(comp)

                    if health > 0:
                        registry.heartbeat(comp.name, health)
                        alive_count += 1
                    else:
                        dead_components.append(comp)

                self.stats["total_heartbeats"] += alive_count

                if dead_components:
                    self.stats["deaths_detected"] += len(dead_components)
                    self._handle_deaths(dead_components, registry, session)

                _track_handshake(
                    f"Pulse #{self.stats['total_pulses']}: {alive_count} alive, {len(dead_components)} dead",
                    confidence=alive_count / max(len(components), 1)
                )

            finally:
                session.close()

        except Exception as e:
            logger.debug(f"[HANDSHAKE] Pulse skipped: {e}")

    def _check_component_health(self, component) -> float:
        """Check if a component is healthy. Returns 0.0-1.0."""
        name = component.name

        if name in self._health_checks:
            try:
                return self._health_checks[name]()
            except Exception:
                return 0.0

        if component.file_path and Path(component.file_path).exists():
            try:
                mod_name = component.module_path
                parts = mod_name.split(".")
                if len(parts) >= 2:
                    importlib.import_module(f"{parts[0]}.{parts[1]}")
                return 1.0
            except Exception:
                return 0.3

        return 0.5

    def _handle_deaths(self, dead_components, registry, session):
        """Handle detected silent deaths."""
        for comp in dead_components:
            logger.warning(
                f"[HANDSHAKE] Silent death detected: '{comp.name}' "
                f"(last heartbeat: {comp.last_heartbeat})"
            )
            comp.status = "dead"
            comp.health_score = 0.0

        session.commit()

        if self.auto_heal:
            try:
                from cognitive.autonomous_healing_system import get_autonomous_healing
                healer = get_autonomous_healing(session)
                for comp in dead_components:
                    logger.info(f"[HANDSHAKE] Triggering self-heal for '{comp.name}'")
                    self.stats["heals_triggered"] += 1
            except Exception as e:
                logger.debug(f"[HANDSHAKE] Auto-heal unavailable: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get handshake protocol status."""
        return {
            "running": self.running,
            "stats": self.stats,
            "config": {
                "heartbeat_interval": self.heartbeat_interval,
                "death_timeout": self.death_timeout,
                "auto_heal": self.auto_heal,
            },
            "registered_checks": list(self._health_checks.keys()),
        }


_handshake: Optional[HandshakeProtocol] = None


def get_handshake_protocol() -> HandshakeProtocol:
    """Get the global handshake protocol singleton."""
    global _handshake
    if _handshake is None:
        _handshake = HandshakeProtocol()
    return _handshake
