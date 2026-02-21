"""Tests for BI connectors -- base, registry, and degraded mode behavior."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from business_intelligence.connectors.base import BaseConnector, ConnectorRegistry, ConnectorHealth
from business_intelligence.config import ConnectorConfig, ConnectorStatus
from business_intelligence.models.data_models import MarketDataPoint, DataSource


class MockConnector(BaseConnector):
    connector_name = "mock"

    async def test_connection(self):
        return True

    async def collect_market_data(self, keywords, niche="", date_from=None, date_to=None):
        return [
            MarketDataPoint(
                source=DataSource.MANUAL,
                metric_name="test",
                metric_value=42.0,
                keywords=keywords,
                niche=niche,
            )
        ]

    async def collect_keyword_metrics(self, keywords):
        return []


class TestBaseConnector:
    def test_active_when_configured(self):
        config = ConnectorConfig(name="test", api_key="key123")
        conn = MockConnector(config)
        assert conn.is_available
        assert conn.health.status == ConnectorStatus.ACTIVE

    def test_degraded_when_no_key(self):
        config = ConnectorConfig(name="test")
        conn = MockConnector(config)
        assert conn.is_available
        assert conn.health.status == ConnectorStatus.DEGRADED

    def test_disabled(self):
        config = ConnectorConfig(name="test", enabled=False)
        conn = MockConnector(config)
        assert not conn.is_available
        assert conn.health.status == ConnectorStatus.DISABLED

    @pytest.mark.asyncio
    async def test_safe_collect_success(self):
        config = ConnectorConfig(name="test", api_key="key")
        conn = MockConnector(config)
        results = await conn.safe_collect(["test_keyword"])
        assert len(results) == 1
        assert conn.health.total_data_points == 1
        assert conn.health.last_successful_pull is not None

    @pytest.mark.asyncio
    async def test_safe_collect_error_handling(self):
        config = ConnectorConfig(name="test", api_key="key")
        conn = MockConnector(config)
        conn.collect_market_data = AsyncMock(side_effect=Exception("API Error"))
        results = await conn.safe_collect(["test"])
        assert results == []
        assert conn.health.error_count == 1
        assert conn.health.last_error == "API Error"

    @pytest.mark.asyncio
    async def test_safe_collect_error_threshold(self):
        config = ConnectorConfig(name="test", api_key="key")
        conn = MockConnector(config)
        conn.collect_market_data = AsyncMock(side_effect=Exception("fail"))
        for _ in range(5):
            await conn.safe_collect(["test"])
        assert conn.health.status == ConnectorStatus.ERROR
        assert conn.health.error_count == 5

    def test_health_report(self):
        config = ConnectorConfig(name="test", api_key="key")
        conn = MockConnector(config)
        report = conn.get_health_report()
        assert report["connector"] == "mock"
        assert report["status"] == "active"
        assert report["total_data_points"] == 0


class TestConnectorRegistry:
    def setup_method(self):
        ConnectorRegistry.reset()

    def test_register_and_get(self):
        config = ConnectorConfig(name="test", api_key="key")
        conn = MockConnector(config)
        ConnectorRegistry.register("test", conn)
        assert ConnectorRegistry.get("test") is conn

    def test_get_nonexistent(self):
        assert ConnectorRegistry.get("nonexistent") is None

    def test_get_all(self):
        for i in range(3):
            config = ConnectorConfig(name=f"test_{i}", api_key="key")
            ConnectorRegistry.register(f"test_{i}", MockConnector(config))
        assert len(ConnectorRegistry.get_all()) == 3

    def test_get_active(self):
        active_config = ConnectorConfig(name="active", api_key="key")
        disabled_config = ConnectorConfig(name="disabled", enabled=False)
        ConnectorRegistry.register("active", MockConnector(active_config))
        ConnectorRegistry.register("disabled", MockConnector(disabled_config))
        active = ConnectorRegistry.get_active()
        assert "active" in active
        assert "disabled" not in active

    @pytest.mark.asyncio
    async def test_collect_all(self):
        for i in range(2):
            config = ConnectorConfig(name=f"c{i}", api_key="key")
            ConnectorRegistry.register(f"c{i}", MockConnector(config))
        results = await ConnectorRegistry.collect_all(["test"])
        assert len(results) == 2

    def test_health_report(self):
        config = ConnectorConfig(name="test", api_key="key")
        ConnectorRegistry.register("test", MockConnector(config))
        report = ConnectorRegistry.health_report()
        assert "test" in report

    def test_reset(self):
        config = ConnectorConfig(name="test", api_key="key")
        ConnectorRegistry.register("test", MockConnector(config))
        ConnectorRegistry.reset()
        assert len(ConnectorRegistry.get_all()) == 0


class TestDegradedConnectors:
    """Verify every real connector returns degraded data without credentials."""

    @pytest.mark.asyncio
    async def test_google_analytics_degraded(self):
        from business_intelligence.connectors.google_analytics import GoogleAnalyticsConnector
        config = ConnectorConfig(name="ga")
        conn = GoogleAnalyticsConnector(config)
        results = await conn.collect_market_data(["test"], niche="test")
        assert len(results) == 1
        assert results[0].confidence == 0.0

    @pytest.mark.asyncio
    async def test_shopify_degraded(self):
        from business_intelligence.connectors.shopify_connector import ShopifyConnector
        config = ConnectorConfig(name="shopify")
        conn = ShopifyConnector(config)
        results = await conn.collect_market_data(["test"])
        assert len(results) == 1
        assert results[0].confidence == 0.0

    @pytest.mark.asyncio
    async def test_amazon_degraded(self):
        from business_intelligence.connectors.amazon_connector import AmazonConnector
        config = ConnectorConfig(name="amazon")
        conn = AmazonConnector(config)
        results = await conn.collect_market_data(["test"])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_meta_degraded(self):
        from business_intelligence.connectors.meta_connector import MetaConnector
        config = ConnectorConfig(name="meta")
        conn = MetaConnector(config)
        results = await conn.collect_market_data(["test"])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_tiktok_degraded(self):
        from business_intelligence.connectors.tiktok_connector import TikTokConnector
        config = ConnectorConfig(name="tiktok")
        conn = TikTokConnector(config)
        results = await conn.collect_market_data(["test"])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_serpapi_degraded(self):
        from business_intelligence.connectors.serpapi_connector import SerpAPIConnector
        config = ConnectorConfig(name="serp")
        conn = SerpAPIConnector(config)
        results = await conn.collect_market_data(["test"])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_junglescout_degraded(self):
        from business_intelligence.connectors.junglescout_connector import JungleScoutConnector
        config = ConnectorConfig(name="js")
        conn = JungleScoutConnector(config)
        results = await conn.collect_market_data(["test"])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_youtube_degraded(self):
        from business_intelligence.connectors.youtube_connector import YouTubeConnector
        config = ConnectorConfig(name="yt")
        conn = YouTubeConnector(config)
        results = await conn.collect_market_data(["test"])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_instagram_degraded(self):
        from business_intelligence.connectors.instagram_connector import InstagramConnector
        config = ConnectorConfig(name="ig")
        conn = InstagramConnector(config)
        results = await conn.collect_market_data(["test"])
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_web_scraping_always_active(self):
        from business_intelligence.connectors.web_scraping_connector import WebScrapingConnector
        config = ConnectorConfig(name="ws")
        conn = WebScrapingConnector(config)
        assert conn.is_available
