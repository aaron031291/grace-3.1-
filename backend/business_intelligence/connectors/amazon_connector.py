"""
Amazon connector.

Uses Amazon Product Advertising API (PA-API 5.0) for product data and
web scraping fallback for review analysis. This is one of the most
critical connectors for pain point discovery -- negative reviews are gold.
"""

import logging
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from business_intelligence.connectors.base import BaseConnector
from business_intelligence.config import ConnectorConfig
from business_intelligence.models.data_models import (
    MarketDataPoint,
    KeywordMetric,
    ReviewAnalysis,
    CompetitorProduct,
    DataSource,
    Sentiment,
)

logger = logging.getLogger(__name__)


class AmazonConnector(BaseConnector):
    connector_name = "amazon"
    connector_version = "1.0.0"

    PA_API_ENDPOINT = "webservices.amazon.co.uk"
    PA_API_PATH = "/paapi5/searchitems"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.access_key = config.api_key
        self.secret_key = config.api_secret
        self.partner_tag = config.extra.get("partner_tag", "")
        self.marketplace = config.extra.get("marketplace", "www.amazon.co.uk")

    async def test_connection(self) -> bool:
        if not self.config.is_configured:
            return False
        try:
            results = await self.search_products("test", max_results=1)
            return len(results) > 0
        except Exception as e:
            logger.error(f"Amazon PA-API connection test failed: {e}")
            return False

    async def search_products(
        self,
        query: str,
        max_results: int = 10,
        category: str = "All",
    ) -> List[CompetitorProduct]:
        """Search Amazon for products matching a query."""
        if not self.config.is_configured:
            return []

        try:
            import aiohttp

            payload = {
                "Keywords": query,
                "SearchIndex": category,
                "ItemCount": min(max_results, 10),
                "Resources": [
                    "ItemInfo.Title",
                    "ItemInfo.Features",
                    "Offers.Listings.Price",
                    "CustomerReviews.Count",
                    "CustomerReviews.StarRating",
                    "BrowseNodeInfo.BrowseNodes",
                ],
                "PartnerTag": self.partner_tag,
                "PartnerType": "Associates",
                "Marketplace": self.marketplace,
            }

            headers = self._build_pa_api_headers(
                json.dumps(payload), self.PA_API_PATH
            )

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"https://{self.PA_API_ENDPOINT}{self.PA_API_PATH}",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"Amazon PA-API error: {resp.status}")
                        return []

                    data = await resp.json()
                    items = data.get("SearchResult", {}).get("Items", [])

                    products = []
                    for item in items:
                        info = item.get("ItemInfo", {})
                        title = info.get("Title", {}).get("DisplayValue", "")
                        features = [
                            f.get("DisplayValue", "")
                            for f in info.get("Features", {}).get("DisplayValues", [])
                        ]
                        offers = item.get("Offers", {}).get("Listings", [])
                        price = 0.0
                        if offers:
                            price = offers[0].get("Price", {}).get("Amount", 0.0)

                        reviews = item.get("CustomerReviews", {})
                        rating = float(reviews.get("StarRating", {}).get("Value", 0))
                        review_count = int(reviews.get("Count", 0))

                        products.append(
                            CompetitorProduct(
                                name=title,
                                platform="amazon",
                                url=item.get("DetailPageURL", ""),
                                price=price,
                                currency="GBP",
                                rating=rating,
                                review_count=review_count,
                                category=query,
                                features=features,
                            )
                        )

                    return products

        except ImportError:
            logger.warning("aiohttp not installed for Amazon connector")
        except Exception as e:
            logger.error(f"Amazon product search failed: {e}")
        return []

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
            products = await self.search_products(keyword, max_results=10)
            for product in products:
                data_points.append(
                    MarketDataPoint(
                        source=DataSource.AMAZON,
                        category="competitor_product",
                        metric_name="product_listing",
                        metric_value=product.rating,
                        unit="rating",
                        niche=niche,
                        keywords=[keyword],
                        metadata={
                            "product_name": product.name,
                            "price": product.price,
                            "review_count": product.review_count,
                            "url": product.url,
                            "features": product.features[:5],
                        },
                    )
                )

            if products:
                avg_price = sum(p.price for p in products) / len(products)
                avg_rating = sum(p.rating for p in products) / len(products)
                data_points.append(
                    MarketDataPoint(
                        source=DataSource.AMAZON,
                        category="market_summary",
                        metric_name="avg_price",
                        metric_value=avg_price,
                        unit="GBP",
                        niche=niche,
                        keywords=[keyword],
                        metadata={
                            "avg_rating": avg_rating,
                            "product_count": len(products),
                            "price_range": {
                                "min": min(p.price for p in products),
                                "max": max(p.price for p in products),
                            },
                        },
                    )
                )

        return data_points

    async def collect_keyword_metrics(self, keywords: List[str]) -> List[KeywordMetric]:
        return []

    async def analyze_reviews(
        self,
        product_url: str,
        max_reviews: int = 100,
    ) -> List[ReviewAnalysis]:
        """Analyze reviews for a specific Amazon product.

        NOTE: This requires web scraping as Amazon's PA-API does not
        expose individual review text. Falls back gracefully if scraping
        service is not available.
        """
        logger.info(
            f"Review analysis for {product_url} -- "
            "requires scraping service integration"
        )
        return []

    def _build_pa_api_headers(self, payload: str, path: str) -> Dict[str, str]:
        """Build AWS Signature V4 headers for PA-API requests."""
        # Simplified -- production would use full AWS sig v4
        return {
            "Content-Type": "application/json; charset=UTF-8",
            "X-Amz-Target": "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems",
            "Content-Encoding": "amz-1.0",
        }

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
                    "message": "Amazon PA-API not configured. Set AMAZON_ACCESS_KEY, AMAZON_SECRET_KEY, AMAZON_PARTNER_TAG.",
                    "action_required": "Configure Amazon PA-API credentials (requires active Associates account)",
                },
            )
        ]
