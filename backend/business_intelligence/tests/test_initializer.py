"""Tests for BI system initialization."""

import pytest
from unittest.mock import patch

from business_intelligence.utils.initializer import BISystem, get_bi_system
from business_intelligence.connectors.base import ConnectorRegistry


class TestBISystem:
    def test_initialization(self):
        bi = BISystem()
        assert not bi.is_initialized
        bi.initialize()
        assert bi.is_initialized

    def test_double_init_safe(self):
        bi = BISystem()
        bi.initialize()
        bi.initialize()  # should not crash
        assert bi.is_initialized

    def test_all_engines_created(self):
        bi = BISystem()
        bi.initialize()
        assert bi.intelligence_engine is not None
        assert bi.reasoning_engine is not None
        assert bi.waitlist_manager is not None
        assert bi.campaign_manager is not None
        assert bi.ad_copy_generator is not None
        assert bi.validation_engine is not None
        assert bi.lookalike_engine is not None
        assert bi.ad_optimizer is not None
        assert bi.dynamic_creative is not None
        assert bi.archetype_engine is not None
        assert bi.pattern_analyzer is not None
        assert bi.product_ideation is not None
        assert bi.niche_finder is not None
        assert bi.data_store is not None
        assert bi.secrets_vault is not None

    def test_all_connectors_registered(self):
        bi = BISystem()
        bi.initialize()
        all_connectors = ConnectorRegistry.get_all()
        expected = [
            "google_analytics", "shopify", "amazon", "meta",
            "tiktok", "serpapi", "jungle_scout", "youtube",
            "instagram", "web_scraping",
        ]
        for name in expected:
            assert name in all_connectors, f"Missing connector: {name}"

    def test_web_scraping_always_active(self):
        bi = BISystem()
        bi.initialize()
        ws = ConnectorRegistry.get("web_scraping")
        assert ws is not None
        assert ws.is_available

    def test_get_status(self):
        bi = BISystem()
        bi.initialize()
        status = bi.get_status()
        assert status["initialized"]
        assert "connectors" in status
        assert status["total_connectors"] >= 10
        assert "reasoning_engine" in status
        assert "secrets_vault" in status

    def test_get_bi_system_singleton(self):
        import business_intelligence.utils.initializer as mod
        mod._bi_system = None
        bi1 = get_bi_system()
        bi2 = get_bi_system()
        assert bi1 is bi2
        mod._bi_system = None
