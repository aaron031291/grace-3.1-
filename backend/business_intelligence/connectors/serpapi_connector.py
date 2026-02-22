"""
SerpAPI connector.

This is the most immediately useful connector -- it works with just an API key
and gives us search volume estimates, keyword competition, trending topics,
and competitor visibility. Bridges to the existing SerpAPI service in GRACE.
"""

import logging
from datetime import datetime
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


class SerpAPIConnector(BaseConnector):
    connector_name = "serpapi"
    connector_version = "1.0.0"

    BASE_URL = "https://serpapi.com/search"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.api_key = config.api_key

    async def test_connection(self) -> bool:
        if not self.api_key:
            return False
        try:
            results = await self._search("test query", num_results=1)
            return len(results) > 0
        except Exception:
            return False

    async def _search(
        self,
        query: str,
        num_results: int = 10,
        location: str = "United Kingdom",
        engine: str = "google",
    ) -> List[Dict]:
        """Execute a search via SerpAPI."""
        try:
            import aiohttp

            params = {
                "q": query,
                "api_key": self.api_key,
                "num": num_results,
                "location": location,
                "engine": engine,
                "hl": "en",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"SerpAPI error: {resp.status}")
                        return []

                    data = await resp.json()
                    return data.get("organic_results", [])

        except ImportError:
            import requests

            params = {
                "q": query,
                "api_key": self.api_key,
                "num": num_results,
                "location": location,
                "engine": engine,
                "hl": "en",
            }
            resp = requests.get(self.BASE_URL, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json().get("organic_results", [])
            return []

    async def _search_shopping(
        self, query: str, location: str = "United Kingdom"
    ) -> List[Dict]:
        """Search Google Shopping for product listings."""
        try:
            import aiohttp

            params = {
                "q": query,
                "api_key": self.api_key,
                "engine": "google_shopping",
                "location": location,
                "hl": "en",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return []
                    data = await resp.json()
                    return data.get("shopping_results", [])

        except Exception as e:
            logger.error(f"SerpAPI shopping search failed: {e}")
            return []

    async def _search_trends(self, keyword: str) -> Dict:
        """Get Google Trends data for a keyword."""
        try:
            import aiohttp

            params = {
                "q": keyword,
                "api_key": self.api_key,
                "engine": "google_trends",
                "data_type": "TIMESERIES",
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return {}
                    return await resp.json()

        except Exception as e:
            logger.error(f"SerpAPI trends search failed: {e}")
            return {}

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
            organic = await self._search(keyword, num_results=10)
            for idx, result in enumerate(organic):
                data_points.append(
                    MarketDataPoint(
                        source=DataSource.SERPAPI,
                        category="search_results",
                        metric_name="organic_position",
                        metric_value=float(result.get("position", idx + 1)),
                        unit="position",
                        niche=niche,
                        keywords=[keyword],
                        metadata={
                            "title": result.get("title", ""),
                            "link": result.get("link", ""),
                            "snippet": result.get("snippet", ""),
                            "displayed_link": result.get("displayed_link", ""),
                        },
                    )
                )

            shopping = await self._search_shopping(keyword)
            for item in shopping[:10]:
                data_points.append(
                    MarketDataPoint(
                        source=DataSource.SERPAPI,
                        category="shopping",
                        metric_name="product_listing",
                        metric_value=self._parse_price(item.get("price", "0")),
                        unit="GBP",
                        niche=niche,
                        keywords=[keyword],
                        metadata={
                            "title": item.get("title", ""),
                            "link": item.get("link", ""),
                            "source": item.get("source", ""),
                            "rating": item.get("rating"),
                            "reviews": item.get("reviews"),
                            "price_raw": item.get("price", ""),
                        },
                    )
                )

            trends = await self._search_trends(keyword)
            timeline = trends.get("interest_over_time", {}).get("timeline_data", [])
            if timeline:
                latest = timeline[-1] if timeline else {}
                values = latest.get("values", [{}])
                trend_value = int(values[0].get("value", 0)) if values else 0

                first = timeline[0] if timeline else {}
                first_values = first.get("values", [{}])
                first_value = int(first_values[0].get("value", 0)) if first_values else 0

                trend_direction = "stable"
                if first_value > 0:
                    change = ((trend_value - first_value) / first_value) * 100
                    if change > 10:
                        trend_direction = "rising"
                    elif change < -10:
                        trend_direction = "declining"
                else:
                    change = 0.0

                data_points.append(
                    MarketDataPoint(
                        source=DataSource.SERPAPI,
                        category="trends",
                        metric_name="search_interest",
                        metric_value=float(trend_value),
                        unit="interest_score",
                        niche=niche,
                        keywords=[keyword],
                        metadata={
                            "trend_direction": trend_direction,
                            "change_percentage": change,
                            "data_points": len(timeline),
                        },
                    )
                )

        return data_points

    async def collect_keyword_metrics(
        self, keywords: List[str]
    ) -> List[KeywordMetric]:
        if not self.api_key:
            return []

        metrics = []
        for keyword in keywords:
            trends = await self._search_trends(keyword)
            timeline = trends.get("interest_over_time", {}).get("timeline_data", [])

            trend_direction = "stable"
            trend_pct = 0.0
            if len(timeline) >= 2:
                first_vals = timeline[0].get("values", [{}])
                last_vals = timeline[-1].get("values", [{}])
                first_v = int(first_vals[0].get("value", 0)) if first_vals else 0
                last_v = int(last_vals[0].get("value", 0)) if last_vals else 0
                if first_v > 0:
                    trend_pct = ((last_v - first_v) / first_v) * 100
                    trend_direction = "rising" if trend_pct > 10 else ("declining" if trend_pct < -10 else "stable")

            related = trends.get("related_queries", {})
            related_kws = [
                q.get("query", "")
                for q in related.get("rising", [])[:5]
            ]

            metrics.append(
                KeywordMetric(
                    keyword=keyword,
                    trend_direction=trend_direction,
                    trend_percentage=trend_pct,
                    related_keywords=related_kws,
                    source=DataSource.SERPAPI,
                )
            )

        return metrics

    async def find_competitors(
        self, niche_keywords: List[str]
    ) -> List[CompetitorProduct]:
        """Find competitor products via Google Shopping."""
        products = []
        for kw in niche_keywords:
            shopping = await self._search_shopping(kw)
            for item in shopping[:5]:
                products.append(
                    CompetitorProduct(
                        name=item.get("title", ""),
                        platform="google_shopping",
                        url=item.get("link", ""),
                        price=self._parse_price(item.get("price", "0")),
                        currency="GBP",
                        rating=float(item.get("rating", 0) or 0),
                        review_count=int(item.get("reviews", 0) or 0),
                        category=kw,
                    )
                )
        return products

    def _parse_price(self, price_str: str) -> float:
        try:
            cleaned = "".join(c for c in str(price_str) if c.isdigit() or c == ".")
            return float(cleaned) if cleaned else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _degraded_data(
        self, keywords: List[str], niche: str
    ) -> List[MarketDataPoint]:
        return [
            MarketDataPoint(
                source=DataSource.SERPAPI,
                category="system",
                metric_name="connector_status",
                metric_value=0.0,
                unit="status",
                niche=niche,
                keywords=keywords,
                confidence=0.0,
                metadata={
                    "message": "SerpAPI not configured. Set SERPAPI_KEY.",
                    "action_required": "Get API key from serpapi.com",
                },
            )
        ]
