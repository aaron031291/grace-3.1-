"""
Instagram Graph API Connector

Provides access to Instagram business analytics and content insights.

Capabilities:
- Account-level insights (impressions, reach, followers, profile views)
- Media-level insights (engagement, reach, saves per post/reel/story)
- Audience demographics (age, gender, city, country)
- Content performance analysis for competitor research
- Hashtag research and trending content

Requirements:
- Instagram Business or Creator account
- Meta Developer Account
- Permissions: instagram_basic, instagram_manage_insights, pages_show_list
- Access token via OAuth flow

Note: Instagram API is part of Meta's Graph API ecosystem.
The access token is the same META_ACCESS_TOKEN used for Facebook.
Instagram-specific config is the business account ID.
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


class InstagramConnector(BaseConnector):
    connector_name = "instagram"
    connector_version = "1.0.0"

    GRAPH_API_BASE = "https://graph.facebook.com/v19.0"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.access_token = config.access_token
        self.business_account_id = config.extra.get("business_account_id")

    async def test_connection(self) -> bool:
        if not self.access_token or not self.business_account_id:
            return False
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.GRAPH_API_BASE}/{self.business_account_id}",
                    params={
                        "fields": "id,username,followers_count",
                        "access_token": self.access_token,
                    },
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"Instagram connection test failed: {e}")
            return False

    async def get_account_insights(
        self,
        period: str = "day",
        metrics: Optional[List[str]] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get account-level insights (impressions, reach, followers, profile views)."""
        if not self.access_token or not self.business_account_id:
            return {}

        metrics_list = metrics or [
            "impressions", "reach", "follower_count", "profile_views",
        ]

        try:
            import aiohttp
            params = {
                "metric": ",".join(metrics_list),
                "period": period,
                "access_token": self.access_token,
            }
            if since:
                params["since"] = int(since.timestamp())
            if until:
                params["until"] = int(until.timestamp())

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.GRAPH_API_BASE}/{self.business_account_id}/insights",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        error = await resp.text()
                        logger.error(f"Instagram insights error: {resp.status} - {error}")
                        return {}
                    return await resp.json()
        except Exception as e:
            logger.error(f"Instagram insights failed: {e}")
            return {}

    async def get_media_insights(
        self, media_id: str
    ) -> Dict[str, Any]:
        """Get insights for a specific post/reel/story."""
        if not self.access_token:
            return {}

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.GRAPH_API_BASE}/{media_id}/insights",
                    params={
                        "metric": "engagement,impressions,reach,saved",
                        "access_token": self.access_token,
                    },
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return {}
                    return await resp.json()
        except Exception as e:
            logger.error(f"Instagram media insights failed: {e}")
            return {}

    async def get_audience_demographics(self) -> Dict[str, Any]:
        """Get audience demographics (age, gender, city, country)."""
        if not self.access_token or not self.business_account_id:
            return {}

        try:
            import aiohttp
            results = {}

            for metric in ["audience_gender_age", "audience_locale", "audience_country", "audience_city"]:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.GRAPH_API_BASE}/{self.business_account_id}/insights",
                        params={
                            "metric": metric,
                            "period": "lifetime",
                            "access_token": self.access_token,
                        },
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            items = data.get("data", [])
                            if items:
                                results[metric] = items[0].get("values", [{}])[0].get("value", {})

            return results
        except Exception as e:
            logger.error(f"Instagram demographics failed: {e}")
            return {}

    async def get_recent_media(
        self, limit: int = 25
    ) -> List[Dict[str, Any]]:
        """Get recent media posts with performance data."""
        if not self.access_token or not self.business_account_id:
            return []

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.GRAPH_API_BASE}/{self.business_account_id}/media",
                    params={
                        "fields": "id,caption,media_type,timestamp,like_count,comments_count,permalink",
                        "limit": min(limit, 100),
                        "access_token": self.access_token,
                    },
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    return data.get("data", [])
        except Exception as e:
            logger.error(f"Instagram media fetch failed: {e}")
            return []

    async def search_hashtag(
        self, hashtag: str
    ) -> Dict[str, Any]:
        """Search for hashtag and get associated media count."""
        if not self.access_token or not self.business_account_id:
            return {}

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.GRAPH_API_BASE}/ig_hashtag_search",
                    params={
                        "q": hashtag,
                        "user_id": self.business_account_id,
                        "access_token": self.access_token,
                    },
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return {}
                    data = await resp.json()
                    hashtag_data = data.get("data", [])

                    if not hashtag_data:
                        return {"hashtag": hashtag, "found": False}

                    hashtag_id = hashtag_data[0].get("id")

                    async with session.get(
                        f"{self.GRAPH_API_BASE}/{hashtag_id}",
                        params={
                            "fields": "id,name,media_count",
                            "access_token": self.access_token,
                        },
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp2:
                        if resp2.status == 200:
                            return await resp2.json()
                        return {"hashtag": hashtag, "id": hashtag_id}
        except Exception as e:
            logger.error(f"Instagram hashtag search failed: {e}")
            return {}

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

        insights = await self.get_account_insights(
            since=date_from, until=date_to
        )
        if insights and "data" in insights:
            for metric_data in insights["data"]:
                metric_name = metric_data.get("name", "")
                values = metric_data.get("values", [])
                for val in values:
                    data_points.append(MarketDataPoint(
                        source=DataSource.INSTAGRAM,
                        category="account_insights",
                        metric_name=metric_name,
                        metric_value=float(val.get("value", 0)),
                        unit="count",
                        niche=niche,
                        keywords=keywords,
                        metadata={"end_time": val.get("end_time", "")},
                    ))

        for keyword in keywords:
            hashtag_data = await self.search_hashtag(keyword.replace(" ", ""))
            if hashtag_data.get("media_count"):
                data_points.append(MarketDataPoint(
                    source=DataSource.INSTAGRAM,
                    category="hashtag_research",
                    metric_name="hashtag_volume",
                    metric_value=float(hashtag_data["media_count"]),
                    unit="posts",
                    niche=niche,
                    keywords=[keyword],
                    metadata={
                        "hashtag": hashtag_data.get("name", keyword),
                        "hashtag_id": hashtag_data.get("id", ""),
                    },
                ))

        demographics = await self.get_audience_demographics()
        if demographics:
            data_points.append(MarketDataPoint(
                source=DataSource.INSTAGRAM,
                category="audience",
                metric_name="demographics",
                metric_value=1.0,
                unit="report",
                niche=niche,
                keywords=keywords,
                metadata=demographics,
            ))

        return data_points or self._degraded_data(keywords, niche)

    async def collect_keyword_metrics(self, keywords: List[str]) -> List[KeywordMetric]:
        return []

    def _degraded_data(self, keywords: List[str], niche: str) -> List[MarketDataPoint]:
        return [MarketDataPoint(
            source=DataSource.INSTAGRAM,
            category="system",
            metric_name="connector_status",
            metric_value=0.0,
            unit="status",
            niche=niche,
            keywords=keywords,
            confidence=0.0,
            metadata={
                "message": "Instagram Graph API not configured. Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ID.",
                "action_required": "Requires Instagram Business Account + Meta Developer App",
                "note": "Instagram API uses the same Meta access token infrastructure as Facebook ads.",
            },
        )]
