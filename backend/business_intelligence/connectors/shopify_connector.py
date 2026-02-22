"""
Shopify connector.

Connects to Shopify Admin API to pull product performance, sales data,
customer demographics, and order analytics for market intelligence.
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


class ShopifyConnector(BaseConnector):
    connector_name = "shopify"
    connector_version = "1.0.0"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.store_url = config.base_url
        self.access_token = config.access_token
        self._session = None

    def _get_headers(self) -> Dict[str, str]:
        return {
            "X-Shopify-Access-Token": self.access_token or "",
            "Content-Type": "application/json",
        }

    def _api_url(self, endpoint: str) -> str:
        base = (self.store_url or "").rstrip("/")
        return f"{base}/admin/api/2024-01/{endpoint}.json"

    async def test_connection(self) -> bool:
        if not self.config.is_configured or not self.store_url:
            return False
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self._api_url("shop"),
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.error(f"Shopify connection test failed: {e}")
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
                products = await self._fetch_products(session)
                orders = await self._fetch_orders(session, date_from, date_to)

                for product in products:
                    title = product.get("title", "")
                    relevant = not keywords or any(
                        kw.lower() in title.lower() for kw in keywords
                    )
                    if not relevant:
                        continue

                    product_orders = [
                        o for o in orders
                        if any(
                            li.get("product_id") == product.get("id")
                            for li in o.get("line_items", [])
                        )
                    ]

                    data_points.append(
                        MarketDataPoint(
                            source=DataSource.SHOPIFY,
                            category="product_performance",
                            metric_name="units_sold",
                            metric_value=float(len(product_orders)),
                            unit="orders",
                            niche=niche,
                            keywords=keywords,
                            metadata={
                                "product_id": product.get("id"),
                                "product_title": title,
                                "price": product.get("variants", [{}])[0].get("price", "0"),
                                "inventory": sum(
                                    v.get("inventory_quantity", 0)
                                    for v in product.get("variants", [])
                                ),
                                "created_at": product.get("created_at"),
                            },
                        )
                    )

                total_revenue = sum(
                    float(o.get("total_price", 0)) for o in orders
                )
                data_points.append(
                    MarketDataPoint(
                        source=DataSource.SHOPIFY,
                        category="revenue",
                        metric_name="total_revenue",
                        metric_value=total_revenue,
                        unit="GBP",
                        niche=niche,
                        keywords=keywords,
                        metadata={
                            "order_count": len(orders),
                            "period_start": date_from.isoformat(),
                            "period_end": date_to.isoformat(),
                        },
                    )
                )

        except ImportError:
            logger.warning("aiohttp not installed for Shopify connector")
            return self._degraded_data(keywords, niche)
        except Exception as e:
            logger.error(f"Shopify data collection failed: {e}")
            return self._degraded_data(keywords, niche)

        return data_points

    async def _fetch_products(self, session) -> List[Dict]:
        try:
            async with session.get(
                self._api_url("products"),
                headers=self._get_headers(),
                params={"limit": 250},
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("products", [])
        except Exception as e:
            logger.error(f"Failed to fetch Shopify products: {e}")
        return []

    async def _fetch_orders(
        self, session, date_from: datetime, date_to: datetime
    ) -> List[Dict]:
        try:
            async with session.get(
                self._api_url("orders"),
                headers=self._get_headers(),
                params={
                    "status": "any",
                    "created_at_min": date_from.isoformat(),
                    "created_at_max": date_to.isoformat(),
                    "limit": 250,
                },
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("orders", [])
        except Exception as e:
            logger.error(f"Failed to fetch Shopify orders: {e}")
        return []

    async def collect_keyword_metrics(self, keywords: List[str]) -> List[KeywordMetric]:
        return []

    def _degraded_data(
        self, keywords: List[str], niche: str
    ) -> List[MarketDataPoint]:
        return [
            MarketDataPoint(
                source=DataSource.SHOPIFY,
                category="system",
                metric_name="connector_status",
                metric_value=0.0,
                unit="status",
                niche=niche,
                keywords=keywords,
                confidence=0.0,
                metadata={
                    "message": "Shopify not configured. Set SHOPIFY_API_KEY, SHOPIFY_ACCESS_TOKEN, SHOPIFY_STORE_URL.",
                    "action_required": "Configure Shopify credentials",
                },
            )
        ]
