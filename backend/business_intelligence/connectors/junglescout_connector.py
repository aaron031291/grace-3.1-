"""
Jungle Scout API Connector

Purpose-built Amazon product research data. Jungle Scout provides what
Amazon's PA-API doesn't:
- Estimated monthly sales volume per product
- Revenue estimates
- Keyword search volume on Amazon specifically
- Competition scores (opportunity scores)
- Product tracking over time
- Niche analysis with demand/competition metrics

This is the correct tool for Amazon market research -- PA-API gives you
product listings, Jungle Scout tells you if they're actually selling.
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


class JungleScoutConnector(BaseConnector):
    """Connector for Jungle Scout's Product & Keyword Research API."""

    connector_name = "jungle_scout"
    connector_version = "1.0.0"

    API_BASE = "https://developer.junglescout.com/api"
    API_VERSION = "2024-03-01"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.api_key = config.api_key
        self.api_name = config.extra.get("api_name", "")
        self.marketplace = config.extra.get("marketplace", "us")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"{self.api_name}:{self.api_key}",
            "X-API-Type": "junglescout",
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.junglescout.v1+json",
        }

    async def test_connection(self) -> bool:
        if not self.config.is_configured:
            return False
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.API_BASE}/keywords/keywords_by_keyword_query",
                    headers=self._get_headers(),
                    params={"marketplace": self.marketplace, "search_terms": "test"},
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return resp.status in (200, 401)
        except Exception as e:
            logger.error(f"Jungle Scout connection test failed: {e}")
            return False

    async def keyword_research(
        self,
        search_terms: str,
        marketplace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get Amazon keyword data: search volume, trend, competition."""
        if not self.config.is_configured:
            return {}

        try:
            import aiohttp
            mp = marketplace or self.marketplace

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.API_BASE}/keywords/keywords_by_keyword_query",
                    headers=self._get_headers(),
                    params={
                        "marketplace": mp,
                        "search_terms": search_terms,
                        "sort": "-monthly_search_volume_exact",
                    },
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"JS keyword API error: {resp.status}")
                        return {}
                    return await resp.json()

        except Exception as e:
            logger.error(f"Jungle Scout keyword research failed: {e}")
            return {}

    async def product_database(
        self,
        keywords: Optional[str] = None,
        category: Optional[str] = None,
        min_revenue: Optional[int] = None,
        max_revenue: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_reviews: Optional[int] = None,
        max_reviews: Optional[int] = None,
        marketplace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search Jungle Scout's product database with filters.

        This is the gold mine: estimated revenue, sales velocity,
        review counts, and competition levels per product.
        """
        if not self.config.is_configured:
            return {}

        try:
            import aiohttp
            mp = marketplace or self.marketplace

            params: Dict[str, Any] = {
                "marketplace": mp,
                "sort": "-estimated_monthly_revenue",
                "page[size]": 50,
            }
            if keywords:
                params["include_keywords"] = keywords
            if category:
                params["categories"] = category
            if min_revenue is not None:
                params["min_monthly_revenue"] = min_revenue
            if max_revenue is not None:
                params["max_monthly_revenue"] = max_revenue
            if min_price is not None:
                params["min_price"] = min_price
            if max_price is not None:
                params["max_price"] = max_price
            if min_reviews is not None:
                params["min_reviews"] = min_reviews
            if max_reviews is not None:
                params["max_reviews"] = max_reviews

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.API_BASE}/product_database_query",
                    headers=self._get_headers(),
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"JS product DB error: {resp.status}")
                        return {}
                    return await resp.json()

        except Exception as e:
            logger.error(f"Jungle Scout product database failed: {e}")
            return {}

    async def niche_analysis(
        self,
        keyword: str,
        marketplace: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get Jungle Scout's niche opportunity score for a keyword.

        Returns demand vs competition analysis -- exactly what we
        need to decide if a niche is worth entering on Amazon.
        """
        if not self.config.is_configured:
            return {}

        try:
            import aiohttp
            mp = marketplace or self.marketplace

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.API_BASE}/keywords/keywords_by_keyword_query",
                    headers=self._get_headers(),
                    params={
                        "marketplace": mp,
                        "search_terms": keyword,
                    },
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        return {}

                    data = await resp.json()
                    keywords_data = data.get("data", [])

                    if not keywords_data:
                        return {"keyword": keyword, "opportunity": "no_data"}

                    primary = keywords_data[0].get("attributes", {})
                    return {
                        "keyword": keyword,
                        "monthly_search_volume": primary.get("monthly_search_volume_exact", 0),
                        "monthly_trend": primary.get("monthly_trend", []),
                        "dominant_category": primary.get("dominant_category", ""),
                        "recommended_promotions": primary.get("recommended_promotions", 0),
                        "organic_product_count": primary.get("organic_product_count", 0),
                        "sponsored_product_count": primary.get("sponsored_product_count", 0),
                    }

        except Exception as e:
            logger.error(f"Jungle Scout niche analysis failed: {e}")
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

        for keyword in keywords:
            kw_data = await self.keyword_research(keyword)
            kw_items = kw_data.get("data", [])

            for item in kw_items[:10]:
                attrs = item.get("attributes", {})
                volume = attrs.get("monthly_search_volume_exact", 0)
                trend = attrs.get("monthly_trend", [])

                trend_direction = "stable"
                if len(trend) >= 2:
                    recent = sum(trend[-3:]) / max(len(trend[-3:]), 1)
                    earlier = sum(trend[:3]) / max(len(trend[:3]), 1)
                    if earlier > 0:
                        change = ((recent - earlier) / earlier) * 100
                        if change > 15:
                            trend_direction = "rising"
                        elif change < -15:
                            trend_direction = "declining"

                data_points.append(
                    MarketDataPoint(
                        source=DataSource.AMAZON,
                        category="amazon_keyword",
                        metric_name="search_volume",
                        metric_value=float(volume),
                        unit="monthly_searches",
                        niche=niche,
                        keywords=[attrs.get("name", keyword)],
                        metadata={
                            "monthly_search_volume": volume,
                            "trend_direction": trend_direction,
                            "monthly_trend": trend[-6:] if trend else [],
                            "dominant_category": attrs.get("dominant_category", ""),
                            "organic_count": attrs.get("organic_product_count", 0),
                            "sponsored_count": attrs.get("sponsored_product_count", 0),
                            "source": "jungle_scout",
                        },
                    )
                )

            product_data = await self.product_database(keywords=keyword)
            products = product_data.get("data", [])

            for prod in products[:10]:
                attrs = prod.get("attributes", {})
                est_revenue = attrs.get("approximate_30_day_revenue", 0)
                est_units = attrs.get("approximate_30_day_units_sold", 0)
                price = attrs.get("price", 0)
                rating = attrs.get("rating", 0)
                reviews = attrs.get("reviews", 0)
                title = attrs.get("title", "")

                data_points.append(
                    MarketDataPoint(
                        source=DataSource.AMAZON,
                        category="amazon_product",
                        metric_name="estimated_monthly_revenue",
                        metric_value=float(est_revenue),
                        unit="USD",
                        niche=niche,
                        keywords=[keyword],
                        metadata={
                            "title": title,
                            "price": price,
                            "rating": rating,
                            "reviews": reviews,
                            "estimated_units_sold": est_units,
                            "estimated_revenue": est_revenue,
                            "asin": attrs.get("asin", ""),
                            "category": attrs.get("category", ""),
                            "seller_type": attrs.get("seller_type", ""),
                            "source": "jungle_scout",
                        },
                    )
                )

        return data_points

    async def collect_keyword_metrics(
        self, keywords: List[str]
    ) -> List[KeywordMetric]:
        if not self.config.is_configured:
            return []

        metrics = []
        for keyword in keywords:
            kw_data = await self.keyword_research(keyword)
            items = kw_data.get("data", [])

            for item in items[:5]:
                attrs = item.get("attributes", {})
                volume = attrs.get("monthly_search_volume_exact", 0)
                trend = attrs.get("monthly_trend", [])

                trend_direction = "stable"
                trend_pct = 0.0
                if len(trend) >= 2:
                    recent = sum(trend[-3:]) / max(len(trend[-3:]), 1)
                    earlier = sum(trend[:3]) / max(len(trend[:3]), 1)
                    if earlier > 0:
                        trend_pct = ((recent - earlier) / earlier) * 100
                        trend_direction = "rising" if trend_pct > 15 else ("declining" if trend_pct < -15 else "stable")

                related = [
                    r.get("attributes", {}).get("name", "")
                    for r in items[1:6]
                    if r.get("attributes", {}).get("name")
                ]

                metrics.append(
                    KeywordMetric(
                        keyword=attrs.get("name", keyword),
                        search_volume=volume,
                        competition=min(attrs.get("organic_product_count", 0) / 1000, 1.0),
                        trend_direction=trend_direction,
                        trend_percentage=round(trend_pct, 2),
                        related_keywords=related,
                        source=DataSource.AMAZON,
                    )
                )

        return metrics

    async def find_competitor_products(
        self,
        keyword: str,
        max_results: int = 20,
    ) -> List[CompetitorProduct]:
        """Find competitor products on Amazon with sales data."""
        product_data = await self.product_database(keywords=keyword)
        products = product_data.get("data", [])

        competitors = []
        for prod in products[:max_results]:
            attrs = prod.get("attributes", {})
            competitors.append(
                CompetitorProduct(
                    name=attrs.get("title", ""),
                    company=attrs.get("brand", attrs.get("seller", "")),
                    platform="amazon",
                    url=f"https://www.amazon.com/dp/{attrs.get('asin', '')}",
                    price=float(attrs.get("price", 0)),
                    currency="USD",
                    rating=float(attrs.get("rating", 0)),
                    review_count=int(attrs.get("reviews", 0)),
                    category=attrs.get("category", keyword),
                    strengths=[
                        f"Est. monthly revenue: ${attrs.get('approximate_30_day_revenue', 0):,.0f}",
                        f"Est. monthly units: {attrs.get('approximate_30_day_units_sold', 0):,}",
                    ],
                    market_share_estimate=0.0,
                )
            )

        return competitors

    def _degraded_data(
        self, keywords: List[str], niche: str
    ) -> List[MarketDataPoint]:
        return [
            MarketDataPoint(
                source=DataSource.AMAZON,
                category="system",
                metric_name="connector_status",
                metric_value=0.0,
                unit="status",
                niche=niche,
                keywords=keywords,
                confidence=0.0,
                metadata={
                    "message": "Jungle Scout API not configured. Set JUNGLESCOUT_API_KEY and JUNGLESCOUT_API_NAME.",
                    "action_required": "Get API credentials from junglescout.com/api",
                    "connector": "jungle_scout",
                },
            )
        ]
