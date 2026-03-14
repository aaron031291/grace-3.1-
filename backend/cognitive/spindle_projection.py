"""
Spindle CQRS Projection — Read-optimized views built from the event stream.
Materializes queryable state from append-only Spindle events.
"""
import logging
import time
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ComponentStatus:
    """Materialized status of a component from event history."""
    component: str
    last_action: str = ""
    last_result: str = ""
    last_proof_hash: str = ""
    last_updated: float = 0.0
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    rollbacks: int = 0

    @property
    def success_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions


@dataclass
class AuditEntry:
    """A single entry in the audit trail."""
    timestamp: float
    topic: str
    action: str
    result: str
    proof_hash: str = ""
    component: str = ""


class SpindleProjection:
    """
    Builds read-optimized views from the Spindle event stream.

    Projections:
    - Component status: current state of each component
    - Audit trail: chronological list of all actions
    - Verification stats: SAT/UNSAT/UNKNOWN ratios
    """

    def __init__(self):
        self._component_status: Dict[str, ComponentStatus] = {}
        self._audit_trail: List[AuditEntry] = []
        self._verification_stats = {
            "SAT": 0, "UNSAT": 0, "UNKNOWN": 0,
            "EXECUTED": 0, "FAILED": 0,
        }
        self._last_sequence: int = 0
        self._lock = threading.Lock()
        self._max_audit = 5000
        self._bg_thread: Optional[threading.Thread] = None
        self._bg_running = False
        self._update_interval = 5.0

    # -- full / incremental replay ------------------------------------------

    def rebuild(self):
        """Rebuild projections from the event store (full replay)."""
        try:
            from backend.cognitive.spindle_event_store import get_event_store
            store = get_event_store()
            events = store.replay(after_sequence=0)

            with self._lock:
                self._component_status.clear()
                self._audit_trail.clear()
                self._verification_stats = {
                    "SAT": 0, "UNSAT": 0, "UNKNOWN": 0,
                    "EXECUTED": 0, "FAILED": 0,
                }
                self._last_sequence = 0

                for event in events:
                    self._apply_event(event)

            logger.info("[PROJECTION] Rebuilt from %d events", len(events))
        except Exception as exc:
            logger.error("[PROJECTION] Rebuild failed: %s", exc)

    def update(self):
        """Incremental update — only process new events since last update."""
        try:
            from backend.cognitive.spindle_event_store import get_event_store
            store = get_event_store()
            events = store.replay(after_sequence=self._last_sequence)

            with self._lock:
                for event in events:
                    self._apply_event(event)

            if events:
                logger.debug("[PROJECTION] Applied %d new events", len(events))
        except Exception as exc:
            logger.error("[PROJECTION] Update failed: %s", exc)

    # -- internal projection logic ------------------------------------------

    def _coerce_timestamp(self, ts) -> float:
        """Convert a datetime or ISO-string timestamp to epoch float."""
        if isinstance(ts, float):
            return ts
        if isinstance(ts, (int,)):
            return float(ts)
        # datetime objects
        if hasattr(ts, "timestamp"):
            return ts.timestamp()
        # ISO-format string
        if isinstance(ts, str):
            try:
                from datetime import datetime
                return datetime.fromisoformat(ts).timestamp()
            except Exception:
                pass
        return time.time()

    def _apply_event(self, event: dict):
        """Apply a single event to update projections."""
        payload = event.get("payload") or {}
        topic = event.get("topic", "")
        result = event.get("result", "")
        proof_hash = event.get("proof_hash", "")
        timestamp = self._coerce_timestamp(event.get("timestamp", time.time()))
        seq = event.get("sequence_id", 0)

        # Update sequence tracking
        if seq > self._last_sequence:
            self._last_sequence = seq

        # Update verification stats
        if result in self._verification_stats:
            self._verification_stats[result] += 1

        # Extract component name
        component = payload.get("component", payload.get("target", ""))
        if not component and "." in topic:
            parts = topic.split(".")
            if len(parts) >= 3:
                component = parts[-1]

        # Update component status
        if component:
            if component not in self._component_status:
                self._component_status[component] = ComponentStatus(
                    component=component,
                )

            cs = self._component_status[component]
            cs.last_updated = timestamp
            cs.last_proof_hash = proof_hash or cs.last_proof_hash

            if result in ("EXECUTED", "FAILED", "SAT", "UNSAT"):
                cs.last_result = result

            if result == "EXECUTED":
                cs.total_executions += 1
                cs.successful_executions += 1
                cs.last_action = payload.get(
                    "action_taken", payload.get("action", ""),
                )
            elif result == "FAILED":
                cs.total_executions += 1
                cs.failed_executions += 1

            if result == "ROLLED_BACK":
                cs.rollbacks += 1

        # Append to audit trail
        self._audit_trail.append(AuditEntry(
            timestamp=timestamp,
            topic=topic,
            action=payload.get("action", payload.get("action_taken", result)),
            result=result,
            proof_hash=proof_hash,
            component=component,
        ))

        if len(self._audit_trail) > self._max_audit:
            self._audit_trail = self._audit_trail[-self._max_audit:]

    # ── Background update & event subscription ─────────────

    def start_background_update(self, interval: float = 5.0):
        """Start background thread that auto-updates projections."""
        if self._bg_thread is not None and self._bg_thread.is_alive():
            return
        self._update_interval = interval
        self._bg_running = True
        self._bg_thread = threading.Thread(
            target=self._bg_loop, daemon=True, name="spindle-projection-bg"
        )
        self._bg_thread.start()
        logger.info("[PROJECTION] Background update started (interval=%.1fs)", interval)

    def stop_background_update(self):
        """Stop the background update thread."""
        self._bg_running = False
        if self._bg_thread:
            self._bg_thread.join(timeout=10)
            self._bg_thread = None
        logger.info("[PROJECTION] Background update stopped")

    def _bg_loop(self):
        """Background loop: periodically update projections."""
        while self._bg_running:
            try:
                self.update()
            except Exception as e:
                logger.debug("[PROJECTION] Background update error: %s", e)
            time.sleep(self._update_interval)

    def subscribe_to_events(self):
        """Subscribe to cognitive event bus for real-time projection updates."""
        if getattr(self, "_subscribed", False):
            return
        try:
            from cognitive.event_bus import subscribe as cog_subscribe, Event

            def _on_spindle_event(event: Event):
                """Apply spindle events to projection in real-time."""
                if event.topic.startswith("spindle."):
                    with self._lock:
                        self._apply_event({
                            "topic": event.topic,
                            "payload": event.data,
                            "result": event.data.get("result", ""),
                            "proof_hash": event.data.get("proof_hash", ""),
                            "timestamp": event.timestamp,
                            "sequence_id": self._last_sequence + 1,
                        })

            cog_subscribe("spindle.*", _on_spindle_event)
            self._subscribed = True
            logger.info("[PROJECTION] Subscribed to cognitive event bus")
        except Exception as e:
            logger.warning("[PROJECTION] Event bus subscription failed: %s", e)

    # ── Query API ─────────────────────────────────────────

    def get_component_status(self, component: str = None) -> Any:
        """Get status of one or all components."""
        with self._lock:
            if component:
                cs = self._component_status.get(component)
                if cs:
                    return {
                        "component": cs.component,
                        "last_action": cs.last_action,
                        "last_result": cs.last_result,
                        "success_rate": cs.success_rate,
                        "total_executions": cs.total_executions,
                        "rollbacks": cs.rollbacks,
                        "last_updated": cs.last_updated,
                    }
                return None
            return {
                name: {
                    "last_action": cs.last_action,
                    "last_result": cs.last_result,
                    "success_rate": cs.success_rate,
                    "total_executions": cs.total_executions,
                    "rollbacks": cs.rollbacks,
                }
                for name, cs in self._component_status.items()
            }

    def get_audit_trail(
        self,
        component: str = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get audit trail, optionally filtered by component."""
        with self._lock:
            trail = self._audit_trail
            if component:
                trail = [e for e in trail if e.component == component]
            return [
                {
                    "timestamp": e.timestamp,
                    "topic": e.topic,
                    "action": e.action,
                    "result": e.result,
                    "proof_hash": e.proof_hash,
                    "component": e.component,
                }
                for e in reversed(trail[-limit:])
            ]

    def get_verification_stats(self) -> Dict[str, Any]:
        """Get verification outcome statistics."""
        with self._lock:
            total = sum(self._verification_stats.values())
            stats = dict(self._verification_stats)
            stats["total"] = total
            if total > 0:
                stats["sat_ratio"] = stats["SAT"] / total
                stats["rejection_ratio"] = stats["UNSAT"] / total
            else:
                stats["sat_ratio"] = 0.0
                stats["rejection_ratio"] = 0.0
            return stats

    def get_dashboard(self) -> Dict[str, Any]:
        """Get a complete dashboard summary."""
        self.update()  # Ensure latest data
        return {
            "components": self.get_component_status(),
            "verification_stats": self.get_verification_stats(),
            "recent_audit": self.get_audit_trail(limit=20),
            "last_sequence": self._last_sequence,
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_projection: Optional[SpindleProjection] = None
_projection_lock = threading.Lock()


def get_spindle_projection(auto_start: bool = True) -> SpindleProjection:
    """Return (or create) the singleton SpindleProjection."""
    global _projection
    if _projection is None:
        with _projection_lock:
            if _projection is None:
                _projection = SpindleProjection()
                if auto_start:
                    _projection.start_background_update()
                    _projection.subscribe_to_events()
    return _projection
