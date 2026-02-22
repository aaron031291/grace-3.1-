"""
YouTube Connector

Integrates with YouTube Data API v3 and YouTube Analytics API.

Data API v3 capabilities:
- Search for videos/channels by keyword
- Get video statistics (views, likes, comments)
- Get channel statistics (subscribers, total views)
- Content analysis for competitor research

Analytics API capabilities (requires channel ownership):
- View counts and watch time
- Audience demographics (age, gender, geography)
- Traffic source analysis
- Viewer retention metrics

For BI: we use Data API v3 for market research (finding what content
exists in a niche, what's performing, competitor analysis) and
Analytics API for tracking our own channel performance.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from business_intelligence.connectors.base import BaseConnector
from business_intelligence.config import ConnectorConfig
from business_intelligence.models.data_models import (
    MarketDataPoint,
    KeywordMetric,
    CompetitorProduct,
    DataSource,
)

logger = logging.getLogger(__name__)


class YouTubeConnector(BaseConnector):
    connector_name = "youtube"
    connector_version = "1.0.0"

    DATA_API_BASE = "https://www.googleapis.com/youtube/v3"
    ANALYTICS_API_BASE = "https://youtubeanalytics.googleapis.com/v2"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self.channel_id = config.extra.get("channel_id")
        self.oauth_token = config.access_token

    async def test_connection(self) -> bool:
        if not self.api_key:
            return False
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.DATA_API_BASE}/search",
                    params={"part": "snippet", "q": "test", "maxResults": 1, "key": self.api_key},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"YouTube connection test failed: {e}")
            return False

    async def search_videos(
        self,
        query: str,
        max_results: int = 25,
        order: str = "relevance",
        published_after: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Search YouTube for videos matching a query."""
        if not self.api_key:
            return []

        try:
            import aiohttp
            params = {
                "part": "snippet",
                "q": query,
                "type": "video",
                "maxResults": min(max_results, 50),
                "order": order,
                "key": self.api_key,
            }
            if published_after:
                params["publishedAfter"] = published_after.strftime("%Y-%m-%dT%H:%M:%SZ")

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.DATA_API_BASE}/search",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"YouTube search error: {resp.status}")
                        return []
                    data = await resp.json()
                    return data.get("items", [])
        except Exception as e:
            logger.error(f"YouTube search failed: {e}")
            return []

    async def get_video_statistics(
        self, video_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Get statistics for specific videos (views, likes, comments)."""
        if not self.api_key or not video_ids:
            return []

        try:
            import aiohttp
            ids_str = ",".join(video_ids[:50])
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.DATA_API_BASE}/videos",
                    params={
                        "part": "statistics,snippet,contentDetails",
                        "id": ids_str,
                        "key": self.api_key,
                    },
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    return data.get("items", [])
        except Exception as e:
            logger.error(f"YouTube video stats failed: {e}")
            return []

    async def get_channel_statistics(
        self, channel_ids: Optional[List[str]] = None, usernames: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get channel statistics (subscribers, views, video count)."""
        if not self.api_key:
            return []

        try:
            import aiohttp
            params = {
                "part": "statistics,snippet,brandingSettings",
                "key": self.api_key,
            }
            if channel_ids:
                params["id"] = ",".join(channel_ids[:50])
            elif usernames:
                params["forUsername"] = usernames[0]
            else:
                return []

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.DATA_API_BASE}/channels",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    return data.get("items", [])
        except Exception as e:
            logger.error(f"YouTube channel stats failed: {e}")
            return []

    async def get_channel_analytics(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        metrics: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get analytics for OUR channel (requires OAuth token)."""
        if not self.oauth_token or not self.channel_id:
            return {"error": "OAuth token and channel_id required for analytics"}

        date_from = date_from or datetime.utcnow() - timedelta(days=30)
        date_to = date_to or datetime.utcnow()
        metrics_str = ",".join(metrics or [
            "views", "estimatedMinutesWatched", "averageViewDuration",
            "likes", "subscribersGained", "subscribersLost",
        ])

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.ANALYTICS_API_BASE}/reports",
                    params={
                        "ids": f"channel=={self.channel_id}",
                        "startDate": date_from.strftime("%Y-%m-%d"),
                        "endDate": date_to.strftime("%Y-%m-%d"),
                        "metrics": metrics_str,
                        "dimensions": "day",
                    },
                    headers={"Authorization": f"Bearer {self.oauth_token}"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        error = await resp.text()
                        logger.error(f"YouTube Analytics error: {resp.status} - {error}")
                        return {}
                    return await resp.json()
        except Exception as e:
            logger.error(f"YouTube analytics failed: {e}")
            return {}

    async def get_audience_demographics(self) -> Dict[str, Any]:
        """Get audience demographics for our channel."""
        if not self.oauth_token or not self.channel_id:
            return {}

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                results = {}
                for dimension in ["ageGroup,gender", "country"]:
                    async with session.get(
                        f"{self.ANALYTICS_API_BASE}/reports",
                        params={
                            "ids": f"channel=={self.channel_id}",
                            "startDate": (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d"),
                            "endDate": datetime.utcnow().strftime("%Y-%m-%d"),
                            "metrics": "viewerPercentage",
                            "dimensions": dimension,
                        },
                        headers={"Authorization": f"Bearer {self.oauth_token}"},
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            results[dimension] = data
                return results
        except Exception as e:
            logger.error(f"YouTube demographics failed: {e}")
            return {}

    async def analyze_niche_content(
        self, keyword: str, max_videos: int = 20
    ) -> Dict[str, Any]:
        """Analyze content landscape for a niche on YouTube.

        Finds top videos, analyzes view counts, engagement rates,
        and content gaps.
        """
        videos = await self.search_videos(keyword, max_results=max_videos, order="viewCount")
        if not videos:
            return {"keyword": keyword, "videos_found": 0}

        video_ids = [v["id"]["videoId"] for v in videos if "videoId" in v.get("id", {})]
        stats = await self.get_video_statistics(video_ids)

        analysis = {
            "keyword": keyword,
            "videos_found": len(stats),
            "total_views": 0,
            "avg_views": 0,
            "avg_likes": 0,
            "avg_comments": 0,
            "top_channels": {},
            "content_themes": [],
            "engagement_rate": 0,
        }

        for item in stats:
            s = item.get("statistics", {})
            views = int(s.get("viewCount", 0))
            likes = int(s.get("likeCount", 0))
            comments = int(s.get("commentCount", 0))

            analysis["total_views"] += views
            analysis["avg_likes"] += likes
            analysis["avg_comments"] += comments

            channel = item.get("snippet", {}).get("channelTitle", "Unknown")
            analysis["top_channels"][channel] = analysis["top_channels"].get(channel, 0) + 1

        n = max(len(stats), 1)
        analysis["avg_views"] = analysis["total_views"] // n
        analysis["avg_likes"] = analysis["avg_likes"] // n
        analysis["avg_comments"] = analysis["avg_comments"] // n

        if analysis["total_views"] > 0:
            total_engagement = analysis["avg_likes"] * n + analysis["avg_comments"] * n
            analysis["engagement_rate"] = round(
                total_engagement / analysis["total_views"] * 100, 3
            )

        analysis["top_channels"] = dict(
            sorted(analysis["top_channels"].items(), key=lambda x: x[1], reverse=True)[:10]
        )

        return analysis

    async def collect_market_data(
        self,
        keywords: List[str],
        niche: str = "",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[MarketDataPoint]:
        if not self.api_key:
            return self._degraded_data(keywords, niche)

        data_points = []

        for keyword in keywords:
            niche_data = await self.analyze_niche_content(keyword)

            if niche_data.get("videos_found", 0) > 0:
                data_points.append(MarketDataPoint(
                    source=DataSource.YOUTUBE,
                    category="content_landscape",
                    metric_name="niche_content_analysis",
                    metric_value=float(niche_data["total_views"]),
                    unit="total_views",
                    niche=niche,
                    keywords=[keyword],
                    metadata={
                        "videos_found": niche_data["videos_found"],
                        "avg_views": niche_data["avg_views"],
                        "avg_likes": niche_data["avg_likes"],
                        "avg_comments": niche_data["avg_comments"],
                        "engagement_rate": niche_data["engagement_rate"],
                        "top_channels": niche_data["top_channels"],
                    },
                ))

            if self.oauth_token and self.channel_id:
                analytics = await self.get_channel_analytics(date_from, date_to)
                if analytics and "rows" in analytics:
                    for row in analytics["rows"]:
                        data_points.append(MarketDataPoint(
                            source=DataSource.YOUTUBE,
                            category="channel_analytics",
                            metric_name="daily_views",
                            metric_value=float(row[1]) if len(row) > 1 else 0,
                            unit="views",
                            niche=niche,
                            keywords=keywords,
                            metadata={"date": row[0] if row else "", "raw": row},
                        ))

        return data_points or self._degraded_data(keywords, niche)

    async def collect_keyword_metrics(self, keywords: List[str]) -> List[KeywordMetric]:
        return []

    def _degraded_data(self, keywords: List[str], niche: str) -> List[MarketDataPoint]:
        return [MarketDataPoint(
            source=DataSource.YOUTUBE,
            category="system",
            metric_name="connector_status",
            metric_value=0.0,
            unit="status",
            niche=niche,
            keywords=keywords,
            confidence=0.0,
            metadata={
                "message": "YouTube API not configured. Set YOUTUBE_API_KEY.",
                "action_required": "Get API key from console.cloud.google.com (YouTube Data API v3)",
                "oauth_note": "For channel analytics, also set YOUTUBE_OAUTH_TOKEN and YOUTUBE_CHANNEL_ID.",
            },
        )]
