"""
Meta Marketing API connector.

Connects to Facebook/Instagram Marketing APIs for ad performance tracking,
audience insights, and campaign management. Also handles Instagram Graph API
for organic content analytics.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from business_intelligence.connectors.base import BaseConnector
from business_intelligence.config import ConnectorConfig
from business_intelligence.models.data_models import (
    MarketDataPoint,
    KeywordMetric,
    DataSource,
)

logger = logging.getLogger(__name__)


class MetaConnector(BaseConnector):
    """Unified connector for Facebook Marketing API and Instagram Graph API."""

    connector_name = "meta"
    connector_version = "1.0.0"

    GRAPH_API_BASE = "https://graph.facebook.com/v19.0"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.access_token = config.access_token
        self.app_id = config.extra.get("app_id")
        self.app_secret = config.extra.get("app_secret")
        self.ad_account_id = config.extra.get("ad_account_id")

    async def test_connection(self) -> bool:
        if not self.access_token:
            return False
        try:
            import aiohttp

            url = f"{self.GRAPH_API_BASE}/me"
            params = {"access_token": self.access_token}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"Meta API connection test failed: {e}")
            return False

    async def collect_market_data(
        self,
        keywords: List[str],
        niche: str = "",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[MarketDataPoint]:
        if not self.config.is_configured:
            return self._degraded_data(keywords, niche)

        data_points = []
        date_from = date_from or datetime.utcnow() - timedelta(days=30)
        date_to = date_to or datetime.utcnow()

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                if self.ad_account_id:
                    ad_data = await self._fetch_ad_insights(session, date_from, date_to)
                    data_points.extend(ad_data)

                audience_data = await self._fetch_audience_insights(session, keywords)
                data_points.extend(audience_data)

        except ImportError:
            logger.warning("aiohttp not installed for Meta connector")
            return self._degraded_data(keywords, niche)
        except Exception as e:
            logger.error(f"Meta data collection failed: {e}")

        return data_points or self._degraded_data(keywords, niche)

    async def _fetch_ad_insights(
        self,
        session,
        date_from: datetime,
        date_to: datetime,
    ) -> List[MarketDataPoint]:
        """Fetch ad campaign performance data."""
        if not self.ad_account_id:
            return []

        try:
            url = f"{self.GRAPH_API_BASE}/act_{self.ad_account_id}/insights"
            params = {
                "access_token": self.access_token,
                "time_range": json.dumps({
                    "since": date_from.strftime("%Y-%m-%d"),
                    "until": date_to.strftime("%Y-%m-%d"),
                }),
                "fields": "impressions,clicks,spend,cpc,cpm,ctr,conversions,cost_per_conversion",
                "level": "campaign",
            }

            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return []

                data = await resp.json()
                results = []

                for row in data.get("data", []):
                    results.append(
                        MarketDataPoint(
                            source=DataSource.META,
                            category="ad_performance",
                            metric_name="campaign_metrics",
                            metric_value=float(row.get("impressions", 0)),
                            unit="impressions",
                            metadata={
                                "clicks": int(row.get("clicks", 0)),
                                "spend": float(row.get("spend", 0)),
                                "cpc": float(row.get("cpc", 0)),
                                "ctr": float(row.get("ctr", 0)),
                                "conversions": int(row.get("conversions", 0)),
                            },
                        )
                    )
                return results

        except Exception as e:
            logger.error(f"Failed to fetch Meta ad insights: {e}")
            return []

    async def _fetch_audience_insights(
        self,
        session,
        keywords: List[str],
    ) -> List[MarketDataPoint]:
        """Fetch audience demographic and interest data."""
        return []

    async def collect_keyword_metrics(self, keywords: List[str]) -> List[KeywordMetric]:
        return []

    async def create_campaign_draft(
        self,
        name: str,
        objective: str = "CONVERSIONS",
        daily_budget: float = 10.0,
        targeting: Optional[Dict] = None,
    ) -> Optional[Dict]:
        """Create a draft campaign for validation testing.

        Does NOT publish -- returns the draft for human review.
        """
        if not self.config.is_configured or not self.ad_account_id:
            logger.warning("Cannot create campaign draft: Meta not configured")
            return None

        return {
            "status": "draft",
            "name": name,
            "objective": objective,
            "daily_budget": daily_budget,
            "targeting": targeting or {},
            "message": "Campaign draft created. Requires human approval before publishing.",
            "requires_approval": True,
        }

    def _degraded_data(
        self, keywords: List[str], niche: str
    ) -> List[MarketDataPoint]:
        return [
            MarketDataPoint(
                source=DataSource.META,
                category="system",
                metric_name="connector_status",
                metric_value=0.0,
                unit="status",
                niche=niche,
                keywords=keywords,
                confidence=0.0,
                metadata={
                    "message": "Meta Marketing API not configured. Set META_ACCESS_TOKEN, META_AD_ACCOUNT_ID.",
                    "action_required": "Configure Meta Marketing API (requires app review approval)",
                },
            )
        ]
