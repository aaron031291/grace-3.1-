"""
Meta Loop Orchestrator — Coordinates all background loops

Single coordinator that:
  - Gathers status from Ouroboros, continuous learning, diagnostic engine,
    proactive healing, autonomous CICD
  - Periodically invokes LoopOrchestrator composite (system_maintenance)
  - Exposes unified meta status for health/observability
  - Runs on its own schedule (default 60s) independent of sub-loops

Flow:
  META_HEARTBEAT (every 60s) → GATHER_STATUS → SYSTEM_MAINTENANCE (every 3rd cycle)
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_meta_instance: Optional["MetaLoopOrchestrator"] = None
_meta_lock = threading.Lock()


@dataclass
class MetaStatus:
    """Unified status from all coordinated loops."""
    autonomous_loop: Dict[str, Any] = field(default_factory=dict)
    continuous_learning: Dict[str, Any] = field(default_factory=dict)
    diagnostic_engine: Dict[str, Any] = field(default_factory=dict)
    loop_orchestrator: Dict[str, Any] = field(default_factory=dict)
    last_maintenance: Optional[str] = None
    cycle_count: int = 0
    running: bool = False


class MetaLoopOrchestrator:
    """Meta coordinator for all background loops."""

    def __init__(self, interval_sec: float = 60.0, maintenance_every_n: int = 3):
        self.interval_sec = interval_sec
        self.maintenance_every_n = maintenance_every_n
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._cycle_count = 0
        self._last_maintenance: Optional[datetime] = None
        self._status = MetaStatus()

    def start(self) -> None:
        """Start the meta loop background thread."""
        with _meta_lock:
            if self._running:
                return
            self._running = True
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._meta_loop,
                daemon=True,
                name="meta-loop-orchestrator"
            )
            self._thread.start()
            logger.info(
                f"[META_LOOP] Started (interval={self.interval_sec}s, "
                f"maintenance every {self.maintenance_every_n} cycles)"
            )

    def stop(self) -> None:
        """Stop the meta loop."""
        self._running = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._status.running = False
        logger.info("[META_LOOP] Stopped")

    def get_status(self) -> Dict[str, Any]:
        """Return current meta status for health/observability."""
        return {
            "meta_cycle_count": self._cycle_count,
            "last_maintenance": (
                self._last_maintenance.isoformat() if self._last_maintenance else None
            ),
            "running": self._running,
            "autonomous_loop": self._status.autonomous_loop,
            "continuous_learning": self._status.continuous_learning,
            "diagnostic_engine": self._status.diagnostic_engine,
            "loop_orchestrator": self._status.loop_orchestrator,
        }

    def _gather_status(self) -> None:
        """Gather status from all coordinated subsystems."""
        # Autonomous loop (Ouroboros)
        try:
            from api.autonomous_loop_api import _loop_state
            self._status.autonomous_loop = dict(_loop_state)
        except Exception as e:
            self._status.autonomous_loop = {"error": str(e)}

        # Continuous learning
        try:
            from cognitive.continuous_learning_orchestrator import get_continuous_learning_status
            self._status.continuous_learning = get_continuous_learning_status()
        except Exception as e:
            self._status.continuous_learning = {"error": str(e)}

        # Diagnostic engine
        try:
            from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
            de = get_diagnostic_engine()
            self._status.diagnostic_engine = {
                "running": getattr(de, "running", False),
                "last_heartbeat": getattr(de, "last_heartbeat", None),
            }
        except Exception as e:
            self._status.diagnostic_engine = {"error": str(e)}

        # Loop orchestrator (composite definitions)
        try:
            from cognitive.loop_orchestrator import LoopOrchestrator
            lo = LoopOrchestrator.get_instance()
            self._status.loop_orchestrator = {
                "composites": list(
                    lo.get_composite_definitions().keys() if hasattr(lo, "get_composite_definitions") else []
                ),
            }
        except Exception as e:
            self._status.loop_orchestrator = {"error": str(e)}

    def _run_maintenance(self) -> None:
        """Invoke system_maintenance composite via LoopOrchestrator."""
        try:
            from cognitive.loop_orchestrator import LoopOrchestrator
            lo = LoopOrchestrator.get_instance()
            result = lo.execute_composite("system_maintenance", context={"source": "meta_loop"})
            self._last_maintenance = datetime.now(timezone.utc)
            self._status.last_maintenance = self._last_maintenance.isoformat()
            logger.info(
                f"[META_LOOP] System maintenance: {result.verdict} "
                f"({result.loops_passed}/{result.loops_executed} passed)"
            )
        except Exception as e:
            logger.warning(f"[META_LOOP] System maintenance error: {e}")

    def _meta_loop(self) -> None:
        """Background loop: gather status, optionally run maintenance."""
        while not self._stop_event.is_set():
            try:
                self._cycle_count += 1
                self._status.cycle_count = self._cycle_count
                self._status.running = self._running

                self._gather_status()

                if self._cycle_count % self.maintenance_every_n == 0:
                    self._run_maintenance()

            except Exception as e:
                logger.warning(f"[META_LOOP] Cycle error: {e}")

            self._stop_event.wait(timeout=self.interval_sec)


def get_meta_loop_orchestrator() -> MetaLoopOrchestrator:
    """Return the singleton meta loop orchestrator."""
    global _meta_instance
    with _meta_lock:
        if _meta_instance is None:
            _meta_instance = MetaLoopOrchestrator(interval_sec=60.0, maintenance_every_n=3)
        return _meta_instance


def start_meta_loop() -> None:
    """Start the meta loop coordinator."""
    get_meta_loop_orchestrator().start()


def stop_meta_loop() -> None:
    """Stop the meta loop coordinator."""
    get_meta_loop_orchestrator().stop()


def get_meta_loop_status() -> Dict[str, Any]:
    """Return current meta loop status."""
    return get_meta_loop_orchestrator().get_status()
