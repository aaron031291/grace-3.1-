"""
Genesis Key Real-Time Event System

Makes genesis keys tell Grace about things AS THEY HAPPEN:
1. Event watchers — register callbacks for specific key types
2. Alerting — threshold-based alerts (3 errors in 1 minute)
3. Streaming aggregation — detect acceleration/deceleration
4. Direct integration with immune system for instant response

Instead of polling every 10-300 seconds, the immune system
gets notified IMMEDIATELY when an error key is created.
"""

import logging
import time
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from collections import deque

from core.datetime_utils import as_naive_utc
from threading import Lock

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    alert_type: str
    message: str
    severity: float
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    acknowledged: bool = False


class GenesisRealtimeEngine:
    """
    Watches genesis key creation in real-time.
    Fires callbacks, detects patterns, triggers alerts.
    """

    def __init__(self):
        self._watchers: Dict[str, List[Callable]] = {}
        self._recent_keys: deque = deque(maxlen=1000)
        self._error_window: deque = deque(maxlen=200)
        self._alerts: List[Alert] = []
        self._alert_rules: List[Dict] = [
            {"type": "error_spike", "threshold": 3, "window_seconds": 60, "severity": 0.8},
            {"type": "error_burst", "threshold": 10, "window_seconds": 300, "severity": 0.9},
            {"type": "high_error_rate", "threshold_pct": 20, "window_seconds": 120, "severity": 0.7},
        ]
        self._lock = Lock()
        self._stats = {
            "total_events": 0,
            "total_errors": 0,
            "total_alerts": 0,
            "watchers_registered": 0,
        }

    # ── Event ingestion ────────────────────────────────────────────────

    def on_key_created(self, key_type: str, what: str, who: str = "system",
                       where: str = "", is_error: bool = False,
                       error_type: str = "", error_message: str = "",
                       data: Dict = None):
        """
        Called every time a genesis key is created.
        This is the real-time hook — fires instantly, no polling.
        """
        now = datetime.now(timezone.utc)
        event = {
            "key_type": key_type,
            "what": what,
            "who": who,
            "where": where,
            "is_error": is_error,
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": now.isoformat(),
            "epoch": time.time(),
            "data": data or {},
        }

        with self._lock:
            self._recent_keys.append(event)
            self._stats["total_events"] += 1

            if is_error:
                self._error_window.append(event)
                self._stats["total_errors"] += 1

        # Fire watchers
        self._fire_watchers(key_type, event)
        if is_error:
            self._fire_watchers("__error__", event)

        # Check alert rules
        self._check_alerts(event)

    # ── Watcher registration ───────────────────────────────────────────

    def watch(self, key_type: str, callback: Callable):
        """
        Register a callback for a specific key type.
        Use '__error__' to watch all errors.
        Use '__all__' to watch everything.
        """
        if key_type not in self._watchers:
            self._watchers[key_type] = []
        self._watchers[key_type].append(callback)
        self._stats["watchers_registered"] += 1

    def _fire_watchers(self, key_type: str, event: Dict):
        for cb in self._watchers.get(key_type, []):
            try:
                cb(event)
            except Exception as e:
                logger.debug(f"Watcher callback failed: {e}")
        for cb in self._watchers.get("__all__", []):
            try:
                cb(event)
            except Exception:
                pass

    # ── Alert system ───────────────────────────────────────────────────

    def _check_alerts(self, event: Dict):
        if not event["is_error"]:
            return

        now = time.time()

        for rule in self._alert_rules:
            window = rule.get("window_seconds", 60)
            cutoff = now - window

            with self._lock:
                recent_errors = [e for e in self._error_window if e["epoch"] > cutoff]

            if rule["type"] == "error_spike" and len(recent_errors) >= rule["threshold"]:
                self._create_alert(
                    "error_spike",
                    f"{len(recent_errors)} errors in {window}s (threshold: {rule['threshold']})",
                    rule["severity"],
                    {"error_count": len(recent_errors), "window": window,
                     "recent": [e["what"][:100] for e in recent_errors[-3:]]}
                )

            elif rule["type"] == "error_burst" and len(recent_errors) >= rule["threshold"]:
                self._create_alert(
                    "error_burst",
                    f"Error burst: {len(recent_errors)} errors in {window}s",
                    rule["severity"],
                    {"error_count": len(recent_errors)}
                )

            elif rule["type"] == "high_error_rate":
                with self._lock:
                    recent_all = [e for e in self._recent_keys if e["epoch"] > cutoff]
                if len(recent_all) > 5:
                    rate = len(recent_errors) / len(recent_all) * 100
                    if rate >= rule["threshold_pct"]:
                        self._create_alert(
                            "high_error_rate",
                            f"Error rate: {rate:.0f}% ({len(recent_errors)}/{len(recent_all)} in {window}s)",
                            rule["severity"],
                            {"error_rate": rate, "errors": len(recent_errors), "total": len(recent_all)}
                        )

    def _create_alert(self, alert_type: str, message: str, severity: float, data: Dict):
        # Dedup: don't fire same alert within 30 seconds
        for existing in self._alerts[-10:]:
            if existing.alert_type == alert_type and not existing.acknowledged:
                ts = as_naive_utc(datetime.fromisoformat(existing.timestamp))
                if ts and (datetime.now(timezone.utc) - ts).seconds < 30:
                    return

        alert = Alert(
            alert_type=alert_type,
            message=message,
            severity=severity,
            data=data,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        self._alerts.append(alert)
        self._stats["total_alerts"] += 1

        # Fire alert watchers
        self._fire_watchers("__alert__", {
            "type": alert_type, "message": message,
            "severity": severity, "data": data,
        })

        logger.warning(f"[GENESIS ALERT] {alert_type}: {message}")

    # ── Streaming aggregation ──────────────────────────────────────────

    def get_stream_stats(self, window_seconds: int = 60) -> Dict[str, Any]:
        """Real-time streaming stats — are errors accelerating?"""
        now = time.time()
        cutoff = now - window_seconds
        half = now - window_seconds / 2

        with self._lock:
            recent = [e for e in self._recent_keys if e["epoch"] > cutoff]
            first_half = [e for e in recent if e["epoch"] < half]
            second_half = [e for e in recent if e["epoch"] >= half]

        first_errors = sum(1 for e in first_half if e["is_error"])
        second_errors = sum(1 for e in second_half if e["is_error"])

        trend = "stable"
        if second_errors > first_errors * 1.5:
            trend = "accelerating"
        elif second_errors < first_errors * 0.5 and first_errors > 0:
            trend = "decelerating"

        return {
            "window_seconds": window_seconds,
            "total_events": len(recent),
            "total_errors": first_errors + second_errors,
            "error_rate": round((first_errors + second_errors) / max(len(recent), 1) * 100, 1),
            "trend": trend,
            "first_half_errors": first_errors,
            "second_half_errors": second_errors,
        }

    # ── Query ──────────────────────────────────────────────────────────

    def get_recent(self, limit: int = 20, errors_only: bool = False) -> List[Dict]:
        with self._lock:
            items = list(self._recent_keys)
        if errors_only:
            items = [e for e in items if e["is_error"]]
        return items[-limit:]

    def get_alerts(self, unacknowledged_only: bool = True) -> List[Dict]:
        alerts = self._alerts[-50:]
        if unacknowledged_only:
            alerts = [a for a in alerts if not a.acknowledged]
        return [{"type": a.alert_type, "message": a.message, "severity": a.severity,
                 "data": a.data, "timestamp": a.timestamp} for a in alerts]

    def acknowledge_alerts(self):
        for a in self._alerts:
            a.acknowledged = True

    def get_stats(self) -> Dict:
        return {**self._stats, "alert_count": len([a for a in self._alerts if not a.acknowledged])}


# Singleton
_engine = None

def get_realtime_engine() -> GenesisRealtimeEngine:
    global _engine
    if _engine is None:
        _engine = GenesisRealtimeEngine()
    return _engine
