"""
Executive Watchdog — monitors CognitiveEngine and consensus execution.

If the executive layer hangs (no heartbeat within timeout), triggers
failover to SAFE_MODE: read-only, human-approval-required operation.
"""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ExecWatchdog:
    """
    Watchdog timer for the executive layer.
    Monitors heartbeats and triggers SAFE_MODE on timeout.
    """

    _instance = None

    def __init__(self, timeout_seconds: float = 300, check_interval: float = 30):
        self._timeout = timeout_seconds
        self._check_interval = check_interval
        self._last_heartbeat = time.time()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._in_safe_mode = False
        self._safe_mode_reason: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "ExecWatchdog":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def heartbeat(self):
        """Called by executive layer to signal it's alive."""
        self._last_heartbeat = time.time()
        if self._in_safe_mode:
            logger.info("[WATCHDOG] Heartbeat received while in SAFE_MODE — recovering")
            self._in_safe_mode = False
            self._safe_mode_reason = None
            try:
                from cognitive.event_bus import publish
                publish("watchdog.recovered", {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }, source="exec_watchdog")
            except Exception:
                pass

    def start(self):
        """Start the watchdog background thread."""
        if self._running:
            return
        self._running = True
        self._last_heartbeat = time.time()
        self._thread = threading.Thread(
            target=self._monitor_loop, daemon=True, name="grace-exec-watchdog"
        )
        self._thread.start()
        logger.info(f"[WATCHDOG] Started (timeout={self._timeout}s, check={self._check_interval}s)")

    def stop(self):
        """Stop the watchdog."""
        self._running = False

    def is_safe_mode(self) -> bool:
        """Check if system is in SAFE_MODE due to watchdog timeout."""
        return self._in_safe_mode

    def get_status(self) -> Dict[str, Any]:
        """Get watchdog status."""
        elapsed = time.time() - self._last_heartbeat
        return {
            "running": self._running,
            "safe_mode": self._in_safe_mode,
            "safe_mode_reason": self._safe_mode_reason,
            "last_heartbeat_ago_s": round(elapsed, 1),
            "timeout_s": self._timeout,
            "healthy": elapsed < self._timeout,
        }

    def _monitor_loop(self):
        """Background loop checking for heartbeat timeout."""
        while self._running:
            try:
                elapsed = time.time() - self._last_heartbeat
                if elapsed > self._timeout and not self._in_safe_mode:
                    self._trigger_safe_mode(
                        f"No heartbeat for {elapsed:.0f}s (timeout={self._timeout}s)"
                    )
            except Exception as e:
                logger.debug(f"[WATCHDOG] Monitor error: {e}")
            time.sleep(self._check_interval)

    def _trigger_safe_mode(self, reason: str):
        """Enter SAFE_MODE — restrict to read-only, require human approval."""
        self._in_safe_mode = True
        self._safe_mode_reason = reason
        logger.warning(f"[WATCHDOG] ⚠ SAFE_MODE triggered: {reason}")

        # Publish event
        try:
            from cognitive.event_bus import publish
            publish("watchdog.safe_mode", {
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }, source="exec_watchdog")
        except Exception:
            pass

        # Track via Genesis
        try:
            from api._genesis_tracker import track
            track(
                key_type="system_event",
                what=f"SAFE_MODE triggered: {reason}",
                how="exec_watchdog",
                is_error=True,
                tags=["watchdog", "safe_mode", "failover"],
            )
        except Exception:
            pass

        # Notify governance
        try:
            from security.governance import get_governance_engine
            gov = get_governance_engine()
            if hasattr(gov, 'escalate'):
                gov.escalate("SAFE_MODE", reason)
        except Exception:
            pass


def get_exec_watchdog() -> ExecWatchdog:
    return ExecWatchdog.get_instance()
