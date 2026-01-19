"""
Notification Channels for Diagnostic Machine

Supports multiple notification channels:
- Webhook (HTTP POST to configurable endpoints)
- Slack (via webhook or API)
- Email (via SMTP)
- Console/Log (for debugging)

All notifications are non-blocking and include retry logic.
"""

import os
import json
import logging
import smtplib
import asyncio
from email.mime.text import MIMEText

# Optional async HTTP client
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    aiohttp = None
    HAS_AIOHTTP = False
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import threading
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(str, Enum):
    """Status of notification delivery."""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    RETRYING = "retrying"


@dataclass
class NotificationPayload:
    """Payload for a notification."""
    notification_id: str
    title: str
    message: str
    priority: NotificationPriority
    source: str = "diagnostic_machine"
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)


@dataclass
class NotificationResult:
    """Result of sending a notification."""
    notification_id: str
    channel: str
    status: NotificationStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0
    error: Optional[str] = None


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""

    @abstractmethod
    def send(self, payload: NotificationPayload) -> NotificationResult:
        """Send a notification through this channel."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the channel is properly configured."""
        pass


class WebhookChannel(NotificationChannel):
    """Webhook notification channel - sends HTTP POST to configured endpoints."""

    def __init__(
        self,
        webhook_url: str = None,
        headers: Dict[str, str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.webhook_url = webhook_url or os.getenv("DIAGNOSTIC_WEBHOOK_URL")
        self.headers = headers or {
            "Content-Type": "application/json",
            "User-Agent": "GRACE-DiagnosticMachine/1.0"
        }
        self.timeout = timeout
        self.max_retries = max_retries

    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    def send(self, payload: NotificationPayload) -> NotificationResult:
        if not self.is_configured():
            return NotificationResult(
                notification_id=payload.notification_id,
                channel="webhook",
                status=NotificationStatus.FAILED,
                message="Webhook URL not configured",
            )

        import requests

        data = {
            "notification_id": payload.notification_id,
            "title": payload.title,
            "message": payload.message,
            "priority": payload.priority.value,
            "source": payload.source,
            "details": payload.details,
            "timestamp": payload.timestamp.isoformat(),
            "tags": payload.tags,
        }

        for retry in range(self.max_retries):
            try:
                response = requests.post(
                    self.webhook_url,
                    json=data,
                    headers=self.headers,
                    timeout=self.timeout
                )

                if response.status_code in [200, 201, 202, 204]:
                    return NotificationResult(
                        notification_id=payload.notification_id,
                        channel="webhook",
                        status=NotificationStatus.SENT,
                        message=f"Webhook delivered (status {response.status_code})",
                        retry_count=retry,
                    )
                else:
                    logger.warning(f"Webhook returned {response.status_code}: {response.text[:200]}")

            except requests.exceptions.Timeout:
                logger.warning(f"Webhook timeout (attempt {retry + 1}/{self.max_retries})")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Webhook error: {e}")

        return NotificationResult(
            notification_id=payload.notification_id,
            channel="webhook",
            status=NotificationStatus.FAILED,
            message=f"Failed after {self.max_retries} retries",
            retry_count=self.max_retries,
        )


class SlackChannel(NotificationChannel):
    """Slack notification channel - sends messages via Slack webhook or API."""

    # Priority to emoji mapping
    PRIORITY_EMOJI = {
        NotificationPriority.LOW: ":information_source:",
        NotificationPriority.MEDIUM: ":warning:",
        NotificationPriority.HIGH: ":exclamation:",
        NotificationPriority.CRITICAL: ":rotating_light:",
    }

    # Priority to color mapping
    PRIORITY_COLOR = {
        NotificationPriority.LOW: "#36a64f",  # green
        NotificationPriority.MEDIUM: "#daa520",  # gold
        NotificationPriority.HIGH: "#ff8c00",  # orange
        NotificationPriority.CRITICAL: "#dc143c",  # crimson
    }

    def __init__(
        self,
        webhook_url: str = None,
        channel: str = None,
        username: str = "GRACE Diagnostic",
        icon_emoji: str = ":robot_face:",
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.webhook_url = webhook_url or os.getenv("SLACK_WEBHOOK_URL")
        self.channel = channel or os.getenv("SLACK_CHANNEL", "#grace-alerts")
        self.username = username
        self.icon_emoji = icon_emoji
        self.timeout = timeout
        self.max_retries = max_retries

    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    def send(self, payload: NotificationPayload) -> NotificationResult:
        if not self.is_configured():
            return NotificationResult(
                notification_id=payload.notification_id,
                channel="slack",
                status=NotificationStatus.FAILED,
                message="Slack webhook URL not configured",
            )

        import requests

        # Build Slack message with blocks for rich formatting
        emoji = self.PRIORITY_EMOJI.get(payload.priority, ":bell:")
        color = self.PRIORITY_COLOR.get(payload.priority, "#808080")

        slack_payload = {
            "channel": self.channel,
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"{emoji} {payload.title}",
                                "emoji": True
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": payload.message
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"*Priority:* {payload.priority.value} | *Source:* {payload.source} | *Time:* {payload.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        # Add details as fields if present
        if payload.details:
            fields = []
            for key, value in list(payload.details.items())[:10]:  # Limit to 10 fields
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*{key}:* {value}"
                })

            if fields:
                slack_payload["attachments"][0]["blocks"].append({
                    "type": "section",
                    "fields": fields[:10]
                })

        for retry in range(self.max_retries):
            try:
                response = requests.post(
                    self.webhook_url,
                    json=slack_payload,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    return NotificationResult(
                        notification_id=payload.notification_id,
                        channel="slack",
                        status=NotificationStatus.SENT,
                        message="Slack message delivered",
                        retry_count=retry,
                    )
                else:
                    logger.warning(f"Slack returned {response.status_code}: {response.text[:200]}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Slack error: {e}")

        return NotificationResult(
            notification_id=payload.notification_id,
            channel="slack",
            status=NotificationStatus.FAILED,
            message=f"Failed after {self.max_retries} retries",
            retry_count=self.max_retries,
        )


class EmailChannel(NotificationChannel):
    """Email notification channel - sends emails via SMTP."""

    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_password: str = None,
        from_email: str = None,
        to_emails: List[str] = None,
        use_tls: bool = True,
        timeout: int = 30,
        max_retries: int = 3
    ):
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.from_email = from_email or os.getenv("SMTP_FROM", "grace@example.com")
        self.to_emails = to_emails or os.getenv("ALERT_EMAILS", "").split(",")
        self.use_tls = use_tls
        self.timeout = timeout
        self.max_retries = max_retries

    def is_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_password and self.to_emails)

    def send(self, payload: NotificationPayload) -> NotificationResult:
        if not self.is_configured():
            return NotificationResult(
                notification_id=payload.notification_id,
                channel="email",
                status=NotificationStatus.FAILED,
                message="Email not configured (missing SMTP credentials or recipients)",
            )

        # Build email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[GRACE {payload.priority.value.upper()}] {payload.title}"
        msg['From'] = self.from_email
        msg['To'] = ", ".join([e for e in self.to_emails if e])

        # Plain text version
        text_content = f"""
GRACE Diagnostic Alert
======================

Title: {payload.title}
Priority: {payload.priority.value}
Source: {payload.source}
Time: {payload.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

Message:
{payload.message}

Details:
{json.dumps(payload.details, indent=2) if payload.details else 'None'}

---
This is an automated message from GRACE Diagnostic Machine.
"""

        # HTML version
        html_content = f"""
<html>
<head>
<style>
    body {{ font-family: Arial, sans-serif; margin: 20px; }}
    .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
    .content {{ padding: 20px; background: #ecf0f1; border-radius: 5px; margin-top: 10px; }}
    .details {{ background: #fff; padding: 15px; border-radius: 5px; margin-top: 10px; }}
    .priority-critical {{ border-left: 5px solid #e74c3c; }}
    .priority-high {{ border-left: 5px solid #e67e22; }}
    .priority-medium {{ border-left: 5px solid #f39c12; }}
    .priority-low {{ border-left: 5px solid #27ae60; }}
    code {{ background: #eee; padding: 2px 5px; border-radius: 3px; }}
</style>
</head>
<body>
<div class="header">
    <h1>GRACE Diagnostic Alert</h1>
</div>
<div class="content priority-{payload.priority.value}">
    <h2>{payload.title}</h2>
    <p><strong>Priority:</strong> {payload.priority.value}</p>
    <p><strong>Source:</strong> {payload.source}</p>
    <p><strong>Time:</strong> {payload.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    <h3>Message</h3>
    <p>{payload.message}</p>
</div>
<div class="details">
    <h3>Details</h3>
    <pre>{json.dumps(payload.details, indent=2) if payload.details else 'None'}</pre>
</div>
<hr>
<p><small>This is an automated message from GRACE Diagnostic Machine.</small></p>
</body>
</html>
"""

        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))

        for retry in range(self.max_retries):
            try:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=self.timeout) as server:
                    if self.use_tls:
                        server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)

                return NotificationResult(
                    notification_id=payload.notification_id,
                    channel="email",
                    status=NotificationStatus.SENT,
                    message=f"Email sent to {len(self.to_emails)} recipients",
                    retry_count=retry,
                )

            except smtplib.SMTPException as e:
                logger.warning(f"SMTP error: {e}")
            except Exception as e:
                logger.warning(f"Email error: {e}")

        return NotificationResult(
            notification_id=payload.notification_id,
            channel="email",
            status=NotificationStatus.FAILED,
            message=f"Failed after {self.max_retries} retries",
            retry_count=self.max_retries,
        )


class ConsoleChannel(NotificationChannel):
    """Console/Log notification channel - for debugging and local development."""

    def __init__(self, log_level: int = logging.INFO):
        self.log_level = log_level

    def is_configured(self) -> bool:
        return True

    def send(self, payload: NotificationPayload) -> NotificationResult:
        priority_markers = {
            NotificationPriority.LOW: "[INFO]",
            NotificationPriority.MEDIUM: "[WARN]",
            NotificationPriority.HIGH: "[HIGH]",
            NotificationPriority.CRITICAL: "[CRIT]",
        }

        marker = priority_markers.get(payload.priority, "[????]")

        log_message = f"""
{'='*60}
{marker} DIAGNOSTIC NOTIFICATION
{'='*60}
ID: {payload.notification_id}
Title: {payload.title}
Priority: {payload.priority.value}
Source: {payload.source}
Time: {payload.timestamp.isoformat()}

Message:
{payload.message}

Details: {json.dumps(payload.details, indent=2) if payload.details else 'None'}
{'='*60}
"""

        logger.log(self.log_level, log_message)

        return NotificationResult(
            notification_id=payload.notification_id,
            channel="console",
            status=NotificationStatus.SENT,
            message="Logged to console",
        )


class NotificationManager:
    """
    Manages multiple notification channels and dispatches alerts.

    Supports:
    - Multiple channels (webhook, slack, email, console)
    - Async/background sending
    - Priority-based channel selection
    - Retry logic per channel
    """

    def __init__(
        self,
        enable_webhook: bool = True,
        enable_slack: bool = True,
        enable_email: bool = True,
        enable_console: bool = True,
        async_mode: bool = True
    ):
        self.channels: Dict[str, NotificationChannel] = {}
        self.async_mode = async_mode
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._notification_counter = 0
        self._results: List[NotificationResult] = []

        # Initialize channels
        if enable_webhook:
            self.channels['webhook'] = WebhookChannel()
        if enable_slack:
            self.channels['slack'] = SlackChannel()
        if enable_email:
            self.channels['email'] = EmailChannel()
        if enable_console:
            self.channels['console'] = ConsoleChannel()

    def add_channel(self, name: str, channel: NotificationChannel):
        """Add a custom notification channel."""
        self.channels[name] = channel

    def remove_channel(self, name: str):
        """Remove a notification channel."""
        self.channels.pop(name, None)

    def get_configured_channels(self) -> List[str]:
        """Get list of configured channels."""
        return [name for name, channel in self.channels.items() if channel.is_configured()]

    def notify(
        self,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        details: Dict[str, Any] = None,
        channels: List[str] = None,
        tags: List[str] = None
    ) -> List[NotificationResult]:
        """
        Send notification to specified channels.

        Args:
            title: Notification title
            message: Notification message
            priority: Priority level
            details: Additional details dict
            channels: List of channels to use (None = all configured)
            tags: Tags for categorization

        Returns:
            List of NotificationResult for each channel
        """
        self._notification_counter += 1

        payload = NotificationPayload(
            notification_id=f"NOTIF-{self._notification_counter:06d}",
            title=title,
            message=message,
            priority=priority,
            details=details or {},
            tags=tags or [],
        )

        # Determine which channels to use
        target_channels = channels or self.get_configured_channels()

        # Filter to only include channels in our registry
        target_channels = [c for c in target_channels if c in self.channels]

        if not target_channels:
            logger.warning("No configured channels available for notification")
            return []

        results = []

        if self.async_mode:
            # Send asynchronously
            futures = []
            for channel_name in target_channels:
                channel = self.channels[channel_name]
                future = self._executor.submit(channel.send, payload)
                futures.append((channel_name, future))

            for channel_name, future in futures:
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                except Exception as e:
                    results.append(NotificationResult(
                        notification_id=payload.notification_id,
                        channel=channel_name,
                        status=NotificationStatus.FAILED,
                        message=f"Exception: {str(e)}",
                        error=str(e),
                    ))
        else:
            # Send synchronously
            for channel_name in target_channels:
                channel = self.channels[channel_name]
                try:
                    result = channel.send(payload)
                    results.append(result)
                except Exception as e:
                    results.append(NotificationResult(
                        notification_id=payload.notification_id,
                        channel=channel_name,
                        status=NotificationStatus.FAILED,
                        message=f"Exception: {str(e)}",
                        error=str(e),
                    ))

        self._results.extend(results)
        return results

    def notify_alert(
        self,
        alert_id: str,
        severity: str,
        message: str,
        details: Dict[str, Any] = None
    ) -> List[NotificationResult]:
        """Send diagnostic alert notification."""
        priority_map = {
            'info': NotificationPriority.LOW,
            'warning': NotificationPriority.MEDIUM,
            'high': NotificationPriority.HIGH,
            'critical': NotificationPriority.CRITICAL,
        }

        priority = priority_map.get(severity.lower(), NotificationPriority.MEDIUM)

        return self.notify(
            title=f"Diagnostic Alert: {alert_id}",
            message=message,
            priority=priority,
            details=details,
            tags=['diagnostic', 'alert', severity],
        )

    def notify_health_change(
        self,
        previous_status: str,
        current_status: str,
        health_score: float,
        details: Dict[str, Any] = None
    ) -> List[NotificationResult]:
        """Send health status change notification."""
        priority = NotificationPriority.MEDIUM
        if current_status == 'critical':
            priority = NotificationPriority.CRITICAL
        elif current_status == 'degraded':
            priority = NotificationPriority.HIGH

        return self.notify(
            title=f"Health Status Changed: {previous_status} → {current_status}",
            message=f"System health changed from {previous_status} to {current_status}. Health score: {health_score:.1%}",
            priority=priority,
            details=details,
            tags=['diagnostic', 'health', current_status],
        )

    def notify_healing_action(
        self,
        action_name: str,
        target_component: str,
        success: bool,
        details: Dict[str, Any] = None
    ) -> List[NotificationResult]:
        """Send healing action notification."""
        status_msg = "succeeded" if success else "failed"
        priority = NotificationPriority.LOW if success else NotificationPriority.HIGH

        return self.notify(
            title=f"Self-Healing {status_msg.title()}: {action_name}",
            message=f"Healing action '{action_name}' on {target_component} {status_msg}",
            priority=priority,
            details=details,
            tags=['diagnostic', 'healing', status_msg],
        )

    def notify_freeze(
        self,
        reason: str,
        affected_components: List[str],
        details: Dict[str, Any] = None
    ) -> List[NotificationResult]:
        """Send system freeze notification."""
        return self.notify(
            title="SYSTEM FREEZE ACTIVATED",
            message=f"System has been frozen. Reason: {reason}. Affected: {', '.join(affected_components)}",
            priority=NotificationPriority.CRITICAL,
            details=details,
            tags=['diagnostic', 'freeze', 'critical'],
        )

    def get_recent_results(self, limit: int = 50) -> List[NotificationResult]:
        """Get recent notification results."""
        return self._results[-limit:]

    def shutdown(self):
        """Shutdown the notification manager."""
        self._executor.shutdown(wait=True)


# Global notification manager instance
_notification_manager: Optional[NotificationManager] = None


def get_notification_manager() -> NotificationManager:
    """Get or create the global notification manager."""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager
