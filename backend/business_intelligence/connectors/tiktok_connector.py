"""
TikTok Business API connector.

Connects to TikTok Marketing API for ad performance tracking and
TikTok Shop analytics for product performance data.
"""

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


class TikTokConnector(BaseConnector):
    connector_name = "tiktok"
    connector_version = "1.0.0"

    BUSINESS_API_BASE = "https://business-api.tiktok.com/open_api/v1.3"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.access_token = config.access_token
        self.advertiser_id = config.extra.get("advertiser_id")

    async def test_connection(self) -> bool:
        if not self.config.is_configured:
            return False
        try:
            import aiohttp

            url = f"{self.BUSINESS_API_BASE}/advertiser/info/"
            headers = {"Access-Token": self.access_token}
            params = {"advertiser_ids": [self.advertiser_id]}

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
                    return data.get("code", -1) == 0
        except Exception as e:
            logger.error(f"TikTok API connection test failed: {e}")
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

        date_from = date_from or datetime.utcnow() - timedelta(days=30)
        date_to = date_to or datetime.utcnow()
        data_points = []

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                ad_data = await self._fetch_ad_report(session, date_from, date_to)
                data_points.extend(ad_data)

        except ImportError:
            logger.warning("aiohttp not installed for TikTok connector")
        except Exception as e:
            logger.error(f"TikTok data collection failed: {e}")

        return data_points or self._degraded_data(keywords, niche)

    async def _fetch_ad_report(
        self,
        session,
        date_from: datetime,
        date_to: datetime,
    ) -> List[MarketDataPoint]:
        """Fetch ad campaign report from TikTok."""
        if not self.advertiser_id:
            return []

        try:
            import json

            url = f"{self.BUSINESS_API_BASE}/report/integrated/get/"
            headers = {"Access-Token": self.access_token, "Content-Type": "application/json"}
            payload = {
                "advertiser_id": self.advertiser_id,
                "report_type": "BASIC",
                "dimensions": ["campaign_id"],
                "metrics": [
                    "spend", "impressions", "clicks", "conversions",
                    "cpc", "cpm", "ctr", "conversion_rate",
                ],
                "data_level": "AUCTION_CAMPAIGN",
                "start_date": date_from.strftime("%Y-%m-%d"),
                "end_date": date_to.strftime("%Y-%m-%d"),
            }

            async with session.post(
                url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                data = await resp.json()
                if data.get("code") != 0:
                    logger.error(f"TikTok API error: {data.get('message')}")
                    return []

                results = []
                for row in data.get("data", {}).get("list", []):
                    metrics = row.get("metrics", {})
                    results.append(
                        MarketDataPoint(
                            source=DataSource.TIKTOK,
                            category="ad_performance",
                            metric_name="campaign_metrics",
                            metric_value=float(metrics.get("impressions", 0)),
                            unit="impressions",
                            metadata={
                                "spend": float(metrics.get("spend", 0)),
                                "clicks": int(metrics.get("clicks", 0)),
                                "conversions": int(metrics.get("conversions", 0)),
                                "cpc": float(metrics.get("cpc", 0)),
                                "ctr": float(metrics.get("ctr", 0)),
                                "campaign_id": row.get("dimensions", {}).get("campaign_id"),
                            },
                        )
                    )
                return results

        except Exception as e:
            logger.error(f"Failed to fetch TikTok ad report: {e}")
            return []

    async def collect_keyword_metrics(self, keywords: List[str]) -> List[KeywordMetric]:
        return []

    def _degraded_data(
        self, keywords: List[str], niche: str
    ) -> List[MarketDataPoint]:
        return [
            MarketDataPoint(
                source=DataSource.TIKTOK,
                category="system",
                metric_name="connector_status",
                metric_value=0.0,
                unit="status",
                niche=niche,
                keywords=keywords,
                confidence=0.0,
                metadata={
                    "message": "TikTok Business API not configured. Set TIKTOK_ACCESS_TOKEN, TIKTOK_ADVERTISER_ID.",
                    "action_required": "Configure TikTok Business API credentials",
                },
            )
        ]
