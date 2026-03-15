"""
Spindle Problems Projection — Caches blackbox reports and autonomous actions
received from the Spindle daemon via the ZMQ bridge / event bus.

The Spindle daemon runs in a separate process and publishes full reports
over ZMQ. The host event bus receives them as local events. This projection
stores them so REST endpoints can serve fresh data without hitting a
process-local scanner that hasn't actually run any scans.
"""

import logging
import threading
import time
from typing import Any, Dict, List, Optional

from cognitive.event_bus import subscribe

logger = logging.getLogger(__name__)

_PREFIX = "[PROBLEMS-PROJECTION]"


class SpindleProblemsProjection:
    """In-memory projection of Spindle blackbox reports and autonomous actions."""

    def __init__(self):
        self._latest_report: Optional[Dict[str, Any]] = None
        self._recent_actions: List[Dict[str, Any]] = []
        self._updated_at: Optional[str] = None
        self._lock = threading.Lock()
        self._max_actions = 100
        self._subscribed = False

    def start(self):
        """Subscribe to event bus topics. Call once during app startup."""
        if self._subscribed:
            return
        subscribe("spindle.blackbox.report", self._on_report)
        subscribe("audit.spindle", self._on_audit)
        self._subscribed = True
        logger.info("%s Subscribed to spindle.blackbox.report and audit.spindle", _PREFIX)

    def _on_report(self, event):
        """Handle incoming blackbox report from the Spindle daemon."""
        data = getattr(event, "data", {})
        if not data:
            return
        with self._lock:
            self._latest_report = data
            self._updated_at = getattr(event, "timestamp", None)
        logger.info(
            "%s Cached blackbox report: %d issues (%d critical)",
            _PREFIX,
            data.get("total_issues", 0),
            data.get("critical_count", 0),
        )

    def _on_audit(self, event):
        """Handle incoming audit.spindle events (autonomous actions, decisions)."""
        data = getattr(event, "data", {})
        if not data:
            return
        entry = {
            **data,
            "timestamp": getattr(event, "timestamp", None),
            "source": getattr(event, "source", "spindle"),
        }
        with self._lock:
            self._recent_actions.insert(0, entry)
            if len(self._recent_actions) > self._max_actions:
                self._recent_actions = self._recent_actions[:self._max_actions]

    def get_report(self) -> Optional[Dict[str, Any]]:
        """Return the latest cached report, or None if no scan has run."""
        with self._lock:
            return self._latest_report

    def get_actions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return recent autonomous actions."""
        with self._lock:
            return list(self._recent_actions[:limit])

    def get_problems_summary(self) -> Dict[str, Any]:
        """Combined view for the Problems tab."""
        with self._lock:
            return {
                "report": self._latest_report,
                "recent_actions": list(self._recent_actions[:30]),
                "updated_at": self._updated_at,
            }


# ── Singleton ────────────────────────────────────────────────────────────────

_projection: Optional[SpindleProblemsProjection] = None
_projection_lock = threading.Lock()


def get_problems_projection() -> SpindleProblemsProjection:
    """Return (or create and start) the module-level singleton."""
    global _projection
    if _projection is None:
        with _projection_lock:
            if _projection is None:
                _projection = SpindleProblemsProjection()
                _projection.start()
    return _projection
