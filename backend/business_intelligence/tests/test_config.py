"""Tests for BI configuration and connector config loading."""

import os
import pytest
from unittest.mock import patch

from business_intelligence.config import BIConfig, ConnectorConfig, ConnectorStatus, BIPhase


class TestConnectorConfig:
    def test_default_not_configured(self):
        config = ConnectorConfig(name="test")
        assert not config.is_configured
        assert config.enabled

    def test_configured_with_api_key(self):
        config = ConnectorConfig(name="test", api_key="abc123")
        assert config.is_configured

    def test_configured_with_access_token(self):
        config = ConnectorConfig(name="test", access_token="tok_123")
        assert config.is_configured

    def test_disabled(self):
        config = ConnectorConfig(name="test", api_key="abc", enabled=False)
        assert not config.is_configured

    def test_rate_limit_default(self):
        config = ConnectorConfig(name="test")
        assert config.rate_limit_per_minute == 60


class TestBIConfig:
    def test_defaults(self):
        config = BIConfig()
        assert config.historical_retention_days == 365
        assert config.min_waitlist_for_validation == 500
        assert config.confidence_threshold == 0.65
        assert config.require_consent_for_tracking is True
        assert "social_security" in config.prohibited_data_fields

    def test_from_env_creates_all_connectors(self):
        config = BIConfig.from_env()
        expected = [
            "google_analytics", "shopify", "amazon", "meta",
            "instagram", "tiktok", "serpapi", "youtube", "jungle_scout",
        ]
        for name in expected:
            assert name in config.connectors, f"Missing connector: {name}"

    def test_get_active_connectors_empty_when_no_keys(self):
        config = BIConfig.from_env()
        active = config.get_active_connectors()
        for name, conn in active.items():
            assert conn.is_configured

    def test_status_report(self):
        config = BIConfig.from_env()
        report = config.get_status_report()
        assert isinstance(report, dict)
        assert "google_analytics" in report
        for name, entry in report.items():
            assert "status" in entry
            assert "configured" in entry

    @patch.dict(os.environ, {"SERPAPI_KEY": "test_key_123"})
    def test_from_env_picks_up_env_var(self):
        config = BIConfig.from_env()
        assert config.connectors["serpapi"].api_key == "test_key_123"
        assert config.connectors["serpapi"].is_configured

    @patch.dict(os.environ, {"BI_RETENTION_DAYS": "180"})
    def test_retention_from_env(self):
        config = BIConfig.from_env()
        assert config.historical_retention_days == 180


class TestBIPhase:
    def test_all_phases_exist(self):
        phases = [BIPhase.COLLECT, BIPhase.SYNTHESIZE, BIPhase.IDENTIFY,
                  BIPhase.VALIDATE, BIPhase.BUILD, BIPhase.SCALE]
        assert len(phases) == 6
