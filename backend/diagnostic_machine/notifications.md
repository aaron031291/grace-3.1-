# Notifications

**File:** `diagnostic_machine/notifications.py`

## Overview

Notification Channels for Diagnostic Machine

Supports multiple notification channels:
- Webhook (HTTP POST to configurable endpoints)
- Slack (via webhook or API)
- Email (via SMTP)
- Console/Log (for debugging)

All notifications are non-blocking and include retry logic.

## Classes

- `NotificationPriority`
- `NotificationStatus`
- `NotificationPayload`
- `NotificationResult`
- `NotificationChannel`
- `WebhookChannel`
- `SlackChannel`
- `EmailChannel`
- `ConsoleChannel`
- `NotificationManager`

## Key Methods

- `send()`
- `is_configured()`
- `is_configured()`
- `send()`
- `is_configured()`
- `send()`
- `is_configured()`
- `send()`
- `is_configured()`
- `send()`
- `add_channel()`
- `remove_channel()`
- `get_configured_channels()`
- `notify()`
- `notify_alert()`

---
*Grace 3.1*
