"""
Tests for notification methods in ActionRouter.

Tests webhook, email, and Slack notification functionality
with mocked network calls.
"""

import sys
sys.path.insert(0, 'backend')

import pytest
from unittest.mock import patch, MagicMock, Mock
from requests.exceptions import RequestException, Timeout

from diagnostic_machine.action_router import ActionRouter, AlertConfig


class TestWebhookNotification:
    """Tests for _send_webhook_notification method."""

    def test_sends_post_request_to_configured_url(self):
        """Webhook sends POST request to configured URL with alert payload."""
        router = ActionRouter(webhook_url="https://example.com/webhook")
        alert_payload = {
            "alert_id": "ALERT-001",
            "severity": "critical",
            "reason": "Test alert"
        }

        with patch("diagnostic_machine.action_router.requests.post") as mock_post:
            mock_post.return_value.raise_for_status = Mock()
            result = router._send_webhook_notification(alert_payload)

            assert result is True
            mock_post.assert_called_once_with(
                "https://example.com/webhook",
                json=alert_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

    def test_returns_true_on_success(self):
        """Webhook returns True when request succeeds."""
        router = ActionRouter(webhook_url="https://example.com/webhook")

        with patch("diagnostic_machine.action_router.requests.post") as mock_post:
            mock_post.return_value.raise_for_status = Mock()
            result = router._send_webhook_notification({"test": "data"})

            assert result is True

    def test_returns_false_on_failure(self):
        """Webhook returns False when request fails."""
        router = ActionRouter(webhook_url="https://example.com/webhook")

        with patch("diagnostic_machine.action_router.requests.post") as mock_post:
            mock_post.side_effect = RequestException("Connection failed")
            result = router._send_webhook_notification({"test": "data"})

            assert result is False

    def test_handles_timeout(self):
        """Webhook returns False on timeout."""
        router = ActionRouter(webhook_url="https://example.com/webhook")

        with patch("diagnostic_machine.action_router.requests.post") as mock_post:
            mock_post.side_effect = Timeout("Request timed out")
            result = router._send_webhook_notification({"test": "data"})

            assert result is False

    def test_returns_false_when_no_url_configured(self):
        """Webhook returns False when no URL is configured."""
        router = ActionRouter(webhook_url=None)
        result = router._send_webhook_notification({"test": "data"})

        assert result is False

    def test_returns_false_on_http_error_status(self):
        """Webhook returns False when server returns error status."""
        router = ActionRouter(webhook_url="https://example.com/webhook")

        with patch("diagnostic_machine.action_router.requests.post") as mock_post:
            mock_post.return_value.raise_for_status.side_effect = RequestException("500 Server Error")
            result = router._send_webhook_notification({"test": "data"})

            assert result is False


class TestEmailNotification:
    """Tests for _send_email_notification method."""

    def test_sends_email_via_smtp(self):
        """Email is sent via SMTP with correct configuration."""
        email_config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "smtp_user": "user@example.com",
            "smtp_password": "password123",
            "to_emails": ["recipient@example.com"]
        }
        router = ActionRouter(email_config=email_config)
        alert_payload = {
            "alert_id": "ALERT-001",
            "severity": "critical",
            "reason": "Test alert",
            "timestamp": "2026-01-18T12:00:00",
            "health_status": "degraded",
            "health_score": 0.7,
            "critical_components": ["database"],
            "degraded_components": ["cache"],
            "avn_alerts": 2,
            "risk_vectors": 1
        }

        with patch("diagnostic_machine.action_router.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            result = router._send_email_notification(alert_payload)

            assert result is True
            mock_smtp.assert_called_once_with("smtp.example.com", 587)
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("user@example.com", "password123")
            mock_server.sendmail.assert_called_once()

    def test_returns_true_on_success(self):
        """Email returns True when SMTP succeeds."""
        email_config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "to_emails": ["recipient@example.com"]
        }
        router = ActionRouter(email_config=email_config)

        with patch("diagnostic_machine.action_router.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__.return_value = MagicMock()
            result = router._send_email_notification({"alert_id": "TEST", "severity": "warning"})

            assert result is True

    def test_handles_smtp_errors_gracefully(self):
        """Email returns False on SMTP error without raising."""
        email_config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "to_emails": ["recipient@example.com"]
        }
        router = ActionRouter(email_config=email_config)

        with patch("diagnostic_machine.action_router.smtplib.SMTP") as mock_smtp:
            mock_smtp.side_effect = Exception("SMTP connection failed")
            result = router._send_email_notification({"alert_id": "TEST"})

            assert result is False

    def test_returns_false_when_no_config(self):
        """Email returns False when no email config is set."""
        router = ActionRouter(email_config=None)
        result = router._send_email_notification({"test": "data"})

        assert result is False

    def test_returns_false_when_missing_smtp_host(self):
        """Email returns False when smtp_host is missing."""
        email_config = {"to_emails": ["recipient@example.com"]}
        router = ActionRouter(email_config=email_config)
        result = router._send_email_notification({"test": "data"})

        assert result is False

    def test_returns_false_when_no_recipients(self):
        """Email returns False when to_emails is empty."""
        email_config = {"smtp_host": "smtp.example.com", "to_emails": []}
        router = ActionRouter(email_config=email_config)
        result = router._send_email_notification({"test": "data"})

        assert result is False

    def test_skips_login_when_no_credentials(self):
        """Email sends without login when no credentials provided."""
        email_config = {
            "smtp_host": "smtp.example.com",
            "smtp_port": 25,
            "to_emails": ["recipient@example.com"]
        }
        router = ActionRouter(email_config=email_config)

        with patch("diagnostic_machine.action_router.smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            result = router._send_email_notification({"alert_id": "TEST", "severity": "info"})

            assert result is True
            mock_server.login.assert_not_called()


class TestSlackNotification:
    """Tests for _send_slack_notification method."""

    def test_sends_to_slack_webhook(self):
        """Slack notification sends POST to webhook URL."""
        router = ActionRouter(slack_webhook_url="https://hooks.slack.com/services/XXX")
        alert_payload = {
            "alert_id": "ALERT-001",
            "severity": "critical",
            "reason": "Test alert",
            "health_score": 0.5,
            "health_status": "critical",
            "timestamp": "2026-01-18T12:00:00"
        }

        with patch("diagnostic_machine.action_router.requests.post") as mock_post:
            mock_post.return_value.raise_for_status = Mock()
            result = router._send_slack_notification(alert_payload)

            assert result is True
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://hooks.slack.com/services/XXX"
            assert call_args[1]["headers"] == {"Content-Type": "application/json"}
            assert call_args[1]["timeout"] == 10

    def test_formats_message_correctly(self):
        """Slack message is formatted with attachments and fields."""
        router = ActionRouter(slack_webhook_url="https://hooks.slack.com/services/XXX")
        alert_payload = {
            "alert_id": "ALERT-001",
            "severity": "critical",
            "reason": "Database connection lost",
            "health_score": 0.3,
            "health_status": "critical",
            "timestamp": "2026-01-18T12:00:00",
            "critical_components": ["database", "cache"]
        }

        with patch("diagnostic_machine.action_router.requests.post") as mock_post:
            mock_post.return_value.raise_for_status = Mock()
            router._send_slack_notification(alert_payload)

            call_args = mock_post.call_args
            slack_message = call_args[1]["json"]

            assert "attachments" in slack_message
            attachment = slack_message["attachments"][0]
            assert attachment["color"] == "#dc3545"  # Red for critical
            assert "ALERT-001" in attachment["title"]
            assert attachment["text"] == "Database connection lost"
            assert any(f["title"] == "Severity" and f["value"] == "CRITICAL" for f in attachment["fields"])
            assert any(f["title"] == "Critical Components" for f in attachment["fields"])

    def test_uses_warning_color_for_non_critical(self):
        """Slack uses orange color for warning severity."""
        router = ActionRouter(slack_webhook_url="https://hooks.slack.com/services/XXX")
        alert_payload = {
            "alert_id": "ALERT-002",
            "severity": "warning",
            "reason": "High memory usage"
        }

        with patch("diagnostic_machine.action_router.requests.post") as mock_post:
            mock_post.return_value.raise_for_status = Mock()
            router._send_slack_notification(alert_payload)

            slack_message = mock_post.call_args[1]["json"]
            assert slack_message["attachments"][0]["color"] == "#ffc107"  # Orange for warning

    def test_returns_true_on_success(self):
        """Slack returns True when webhook call succeeds."""
        router = ActionRouter(slack_webhook_url="https://hooks.slack.com/services/XXX")

        with patch("diagnostic_machine.action_router.requests.post") as mock_post:
            mock_post.return_value.raise_for_status = Mock()
            result = router._send_slack_notification({"alert_id": "TEST", "severity": "info"})

            assert result is True

    def test_returns_false_on_failure(self):
        """Slack returns False when webhook call fails."""
        router = ActionRouter(slack_webhook_url="https://hooks.slack.com/services/XXX")

        with patch("diagnostic_machine.action_router.requests.post") as mock_post:
            mock_post.side_effect = RequestException("Webhook failed")
            result = router._send_slack_notification({"alert_id": "TEST"})

            assert result is False

    def test_returns_false_when_no_url_configured(self):
        """Slack returns False when no webhook URL is configured."""
        router = ActionRouter(slack_webhook_url=None)
        result = router._send_slack_notification({"test": "data"})

        assert result is False


class TestConfigurationLoading:
    """Tests for configuration loading from environment variables."""

    def test_loads_webhook_url_from_env(self):
        """Webhook URL is loaded from GRACE_WEBHOOK_URL env var."""
        with patch.dict("os.environ", {"GRACE_WEBHOOK_URL": "https://env-webhook.example.com"}):
            router = ActionRouter()
            assert router.webhook_url == "https://env-webhook.example.com"

    def test_loads_slack_url_from_env(self):
        """Slack webhook URL is loaded from GRACE_SLACK_WEBHOOK_URL env var."""
        with patch.dict("os.environ", {"GRACE_SLACK_WEBHOOK_URL": "https://hooks.slack.com/env"}):
            router = ActionRouter()
            assert router.slack_webhook_url == "https://hooks.slack.com/env"

    def test_loads_email_config_from_env(self):
        """Email config is loaded from GRACE_SMTP_* env vars."""
        env_vars = {
            "GRACE_SMTP_HOST": "smtp.env.example.com",
            "GRACE_SMTP_PORT": "465",
            "GRACE_SMTP_USER": "envuser@example.com",
            "GRACE_SMTP_PASSWORD": "envpassword",
            "GRACE_ALERT_EMAILS": "admin@example.com, ops@example.com"
        }
        with patch.dict("os.environ", env_vars, clear=False):
            router = ActionRouter()
            assert router.email_config is not None
            assert router.email_config["smtp_host"] == "smtp.env.example.com"
            assert router.email_config["smtp_port"] == 465
            assert router.email_config["smtp_user"] == "envuser@example.com"
            assert router.email_config["smtp_password"] == "envpassword"
            assert "admin@example.com" in router.email_config["to_emails"]
            assert "ops@example.com" in router.email_config["to_emails"]

    def test_uses_defaults_when_not_configured(self):
        """Uses None/defaults when env vars are not set."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("os.getenv", return_value=None):
                router = ActionRouter()
                assert router.webhook_url is None
                assert router.slack_webhook_url is None

    def test_constructor_params_override_env(self):
        """Constructor parameters override environment variables."""
        with patch.dict("os.environ", {"GRACE_WEBHOOK_URL": "https://env.example.com"}):
            router = ActionRouter(webhook_url="https://param.example.com")
            assert router.webhook_url == "https://param.example.com"

    def test_default_smtp_port_is_587(self):
        """Default SMTP port is 587 when not specified."""
        env_vars = {
            "GRACE_SMTP_HOST": "smtp.example.com",
            "GRACE_ALERT_EMAILS": "admin@example.com"
        }
        with patch.dict("os.environ", env_vars, clear=False):
            router = ActionRouter()
            assert router.email_config["smtp_port"] == 587

    def test_email_config_none_when_no_smtp_host(self):
        """Email config is None when GRACE_SMTP_HOST is not set."""
        with patch.dict("os.environ", {}, clear=True):
            with patch("os.getenv", return_value=None):
                router = ActionRouter()
                assert router.email_config is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
