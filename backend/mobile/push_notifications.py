"""
Push Notification Service

Sends push notifications from Grace to the user's phone via
Firebase Cloud Messaging (FCM). Handles notification priority,
categories, and action buttons.

Notification categories:
- PERMISSION_REQUIRED: Grace needs human approval (campaign, budget, etc)
- GRACE_QUESTION: Grace needs information or clarification
- DAILY_BRIEFING: Morning intelligence briefing
- ALERT_CRITICAL: Budget exceeded, CPA spike, system error
- ALERT_WARNING: Competitor change, trend shift, audience fatigue
- MILESTONE: Waitlist threshold hit, campaign completed, opportunity found
- TASK_UPDATE: Task status change (processing -> complete)
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationPriority(Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationCategory(Enum):
    PERMISSION_REQUIRED = "permission_required"
    GRACE_QUESTION = "grace_question"
    DAILY_BRIEFING = "daily_briefing"
    ALERT_CRITICAL = "alert_critical"
    ALERT_WARNING = "alert_warning"
    MILESTONE = "milestone"
    TASK_UPDATE = "task_update"
    BI_INSIGHT = "bi_insight"
    KNOWLEDGE_REQUEST = "knowledge_request"


CATEGORY_PRIORITY = {
    NotificationCategory.ALERT_CRITICAL: NotificationPriority.CRITICAL,
    NotificationCategory.PERMISSION_REQUIRED: NotificationPriority.HIGH,
    NotificationCategory.GRACE_QUESTION: NotificationPriority.HIGH,
    NotificationCategory.KNOWLEDGE_REQUEST: NotificationPriority.HIGH,
    NotificationCategory.MILESTONE: NotificationPriority.NORMAL,
    NotificationCategory.ALERT_WARNING: NotificationPriority.NORMAL,
    NotificationCategory.DAILY_BRIEFING: NotificationPriority.NORMAL,
    NotificationCategory.TASK_UPDATE: NotificationPriority.LOW,
    NotificationCategory.BI_INSIGHT: NotificationPriority.LOW,
}


@dataclass
class PushNotification:
    """A push notification to send to the user's device."""
    id: str = ""
    title: str = ""
    body: str = ""
    category: NotificationCategory = NotificationCategory.TASK_UPDATE
    priority: NotificationPriority = NotificationPriority.NORMAL
    actions: List[Dict[str, str]] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    sent: bool = False
    read: bool = False
    responded: bool = False
    response: Optional[Dict[str, Any]] = None


@dataclass
class DeviceRegistration:
    """A registered mobile device for push notifications."""
    device_id: str = ""
    fcm_token: str = ""
    platform: str = ""  # ios, android
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    notification_preferences: Dict[str, bool] = field(default_factory=lambda: {
        "permission_required": True,
        "grace_question": True,
        "daily_briefing": True,
        "alert_critical": True,
        "alert_warning": True,
        "milestone": True,
        "task_update": True,
        "bi_insight": True,
    })


class PushNotificationService:
    """Manages push notifications from Grace to the user's phone."""

    def __init__(self):
        self.devices: List[DeviceRegistration] = []
        self.notifications: List[PushNotification] = []
        self._fcm_key: Optional[str] = None
        self._initialized = False

    def initialize(self, fcm_key: Optional[str] = None):
        import os
        self._fcm_key = fcm_key or os.getenv("FCM_SERVER_KEY")
        self._initialized = True

    async def register_device(
        self, device_id: str, fcm_token: str, platform: str = "android",
    ) -> Dict[str, Any]:
        """Register a mobile device for push notifications."""
        existing = next((d for d in self.devices if d.device_id == device_id), None)
        if existing:
            existing.fcm_token = fcm_token
            existing.last_seen = datetime.utcnow()
            return {"status": "updated", "device_id": device_id}

        self.devices.append(DeviceRegistration(
            device_id=device_id, fcm_token=fcm_token, platform=platform,
        ))
        logger.info(f"Mobile device registered: {device_id} ({platform})")
        return {"status": "registered", "device_id": device_id}

    async def send_notification(
        self,
        title: str,
        body: str,
        category: NotificationCategory,
        actions: Optional[List[Dict[str, str]]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> PushNotification:
        """Send a push notification to all registered devices."""
        import uuid
        priority = CATEGORY_PRIORITY.get(category, NotificationPriority.NORMAL)

        notification = PushNotification(
            id=str(uuid.uuid4())[:12],
            title=title,
            body=body,
            category=category,
            priority=priority,
            actions=actions or [],
            data=data or {},
        )

        for device in self.devices:
            prefs = device.notification_preferences
            if prefs.get(category.value, True):
                sent = await self._send_fcm(device.fcm_token, notification)
                if sent:
                    notification.sent = True

        if not self.devices:
            logger.info(f"Notification queued (no devices registered): {title}")

        self.notifications.append(notification)
        return notification

    async def _send_fcm(self, token: str, notification: PushNotification) -> bool:
        """Send via Firebase Cloud Messaging."""
        if not self._fcm_key:
            logger.debug("FCM key not configured -- notification queued locally")
            return False

        try:
            import aiohttp
            payload = {
                "to": token,
                "priority": "high" if notification.priority in (NotificationPriority.HIGH, NotificationPriority.CRITICAL) else "normal",
                "notification": {
                    "title": notification.title,
                    "body": notification.body,
                    "sound": "default" if notification.priority != NotificationPriority.LOW else None,
                    "badge": 1,
                },
                "data": {
                    "notification_id": notification.id,
                    "category": notification.category.value,
                    "priority": notification.priority.value,
                    "actions": json.dumps(notification.actions),
                    **{k: str(v) for k, v in notification.data.items()},
                },
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://fcm.googleapis.com/fcm/send",
                    headers={
                        "Authorization": f"key={self._fcm_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return resp.status == 200

        except Exception as e:
            logger.error(f"FCM send failed: {e}")
            return False

    # ==================== Grace-Initiated Notifications ====================

    async def notify_permission_needed(
        self, action: str, details: str, action_id: str,
    ) -> PushNotification:
        """Grace needs human approval for something."""
        return await self.send_notification(
            title=f"Grace needs approval: {action}",
            body=details[:200],
            category=NotificationCategory.PERMISSION_REQUIRED,
            actions=[
                {"action": "approve", "title": "Approve", "id": action_id},
                {"action": "reject", "title": "Reject", "id": action_id},
                {"action": "modify", "title": "Modify", "id": action_id},
            ],
            data={"action_id": action_id, "action_type": action},
        )

    async def notify_daily_briefing(self, briefing: str) -> PushNotification:
        """Send Grace's daily BI briefing."""
        return await self.send_notification(
            title="Grace's Daily Intelligence Briefing",
            body=briefing[:300],
            category=NotificationCategory.DAILY_BRIEFING,
            data={"full_briefing": briefing},
        )

    async def notify_critical_alert(
        self, alert_type: str, message: str, data: Optional[Dict] = None,
    ) -> PushNotification:
        """Critical alert -- budget exceeded, CPA spike, system error."""
        return await self.send_notification(
            title=f"ALERT: {alert_type}",
            body=message[:200],
            category=NotificationCategory.ALERT_CRITICAL,
            data=data or {},
        )

    async def notify_milestone(
        self, milestone: str, details: str,
    ) -> PushNotification:
        """Milestone reached -- waitlist target, campaign complete, etc."""
        return await self.send_notification(
            title=f"Milestone: {milestone}",
            body=details[:200],
            category=NotificationCategory.MILESTONE,
        )

    async def notify_knowledge_request(
        self, topic: str, reason: str,
    ) -> PushNotification:
        """Grace needs more knowledge or documents."""
        return await self.send_notification(
            title=f"Grace needs knowledge: {topic}",
            body=f"Reason: {reason[:150]}",
            category=NotificationCategory.KNOWLEDGE_REQUEST,
            actions=[
                {"action": "provide", "title": "Provide Info"},
                {"action": "later", "title": "Later"},
            ],
            data={"topic": topic, "reason": reason},
        )

    async def notify_question(
        self, question: str, context: str = "",
    ) -> PushNotification:
        """Grace has a question for the user."""
        return await self.send_notification(
            title="Grace has a question",
            body=question[:200],
            category=NotificationCategory.GRACE_QUESTION,
            actions=[
                {"action": "reply", "title": "Reply"},
                {"action": "voice", "title": "Voice Reply"},
            ],
            data={"question": question, "context": context},
        )

    # ==================== Response Handling ====================

    async def record_response(
        self, notification_id: str, action: str, response_data: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Record user's response to a notification."""
        notif = next((n for n in self.notifications if n.id == notification_id), None)
        if not notif:
            return {"status": "not_found"}

        notif.responded = True
        notif.read = True
        notif.response = {"action": action, "data": response_data or {}, "responded_at": datetime.utcnow().isoformat()}

        logger.info(f"Notification {notification_id} responded: {action}")
        return {"status": "recorded", "action": action}

    async def get_pending_notifications(self) -> List[Dict[str, Any]]:
        """Get all unread/unresponded notifications."""
        pending = [n for n in self.notifications if not n.read]
        return [
            {
                "id": n.id,
                "title": n.title,
                "body": n.body,
                "category": n.category.value,
                "priority": n.priority.value,
                "actions": n.actions,
                "created_at": n.created_at.isoformat(),
                "requires_response": n.category in (
                    NotificationCategory.PERMISSION_REQUIRED,
                    NotificationCategory.GRACE_QUESTION,
                    NotificationCategory.KNOWLEDGE_REQUEST,
                ),
            }
            for n in sorted(pending, key=lambda n: n.created_at, reverse=True)
        ]

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "fcm_configured": self._fcm_key is not None,
            "registered_devices": len(self.devices),
            "total_notifications": len(self.notifications),
            "pending": sum(1 for n in self.notifications if not n.read),
            "awaiting_response": sum(1 for n in self.notifications if not n.responded and n.category in (
                NotificationCategory.PERMISSION_REQUIRED,
                NotificationCategory.GRACE_QUESTION,
            )),
        }
