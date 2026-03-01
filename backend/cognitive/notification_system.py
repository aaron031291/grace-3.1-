"""
Notification System — Alerts via console, file, and webhook.

Channels:
  - Console: prints to server logs
  - File: writes to data/notifications/
  - Webhook: POST to configured URL (Slack, Discord, etc.)
  - UI: pushed to event bus → Activity Feed
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

NOTIF_DIR = Path(__file__).parent.parent / "data" / "notifications"
WEBHOOK_URL = os.getenv("GRACE_WEBHOOK_URL", "")


class NotificationSystem:
    _instance = None
    
    def __init__(self):
        self._history: List[Dict] = []

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def alert(self, title: str, message: str, severity: str = "info",
              channel: str = "all") -> Dict:
        """Send an alert through all configured channels."""
        notif = {
            "id": f"notif_{int(time.time()*1000)}",
            "title": title,
            "message": message,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat(),
            "channels_sent": [],
        }

        # Console
        if channel in ("all", "console"):
            icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "ℹ️"}.get(severity, "📢")
            logger.warning(f"[ALERT] {icon} [{severity.upper()}] {title}: {message}")
            notif["channels_sent"].append("console")

        # File
        if channel in ("all", "file"):
            NOTIF_DIR.mkdir(parents=True, exist_ok=True)
            ts = datetime.utcnow().strftime("%Y%m%d")
            log_file = NOTIF_DIR / f"alerts_{ts}.jsonl"
            with open(log_file, "a") as f:
                f.write(json.dumps(notif) + "\n")
            notif["channels_sent"].append("file")

        # Event bus → UI Activity Feed
        if channel in ("all", "ui"):
            try:
                from cognitive.event_bus import publish
                publish("notification.alert", {
                    "title": title, "message": message, "severity": severity,
                }, source="notification_system")
                notif["channels_sent"].append("ui")
            except Exception:
                pass

        # Webhook (Slack, Discord, etc.)
        if channel in ("all", "webhook") and WEBHOOK_URL:
            try:
                import requests
                requests.post(WEBHOOK_URL, json={
                    "text": f"[{severity.upper()}] {title}\n{message}",
                }, timeout=5)
                notif["channels_sent"].append("webhook")
            except Exception:
                pass

        self._history.append(notif)
        if len(self._history) > 200:
            self._history = self._history[-100:]

        return notif

    def get_recent(self, limit: int = 20) -> List[Dict]:
        return list(reversed(self._history[-limit:]))

    def get_today(self) -> List[Dict]:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return [n for n in self._history if n["timestamp"][:10] == today]


def get_notifications():
    return NotificationSystem.get_instance()
