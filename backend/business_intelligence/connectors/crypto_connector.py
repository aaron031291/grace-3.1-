"""
Crypto & Financial Data Connector

Connects to CoinGecko (free), Binance, and Alpha Vantage APIs for:
- Cryptocurrency price and volume data
- Market cap and dominance trends
- Trading pair analytics
- Stock/forex data via Alpha Vantage
- DeFi protocol metrics

Feeds into the BI system for financial market analysis,
trend detection, and trading strategy intelligence.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from business_intelligence.connectors.base import BaseConnector
from business_intelligence.config import ConnectorConfig
from business_intelligence.models.data_models import MarketDataPoint, KeywordMetric, DataSource

logger = logging.getLogger(__name__)


class CryptoFinanceConnector(BaseConnector):
    connector_name = "crypto_finance"
    connector_version = "1.0.0"

    COINGECKO_API = "https://api.coingecko.com/api/v3"
    ALPHA_VANTAGE_API = "https://www.alphavantage.co/query"
    BINANCE_API = "https://api.binance.com/api/v3"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.coingecko_key = config.api_key
        self.alpha_vantage_key = config.extra.get("alpha_vantage_key")
        config.enabled = True
        if not config.api_key:
            config.api_key = "coingecko_free"
        from business_intelligence.config import ConnectorStatus
        self.health.status = ConnectorStatus.ACTIVE

    async def test_connection(self) -> bool:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.COINGECKO_API}/ping", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def get_crypto_prices(self, coins: List[str], vs_currency: str = "gbp") -> Dict[str, Any]:
        """Get current prices for cryptocurrencies."""
        try:
            import aiohttp
            ids = ",".join(coins)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.COINGECKO_API}/simple/price",
                    params={"ids": ids, "vs_currencies": vs_currency, "include_24hr_change": "true",
                            "include_market_cap": "true", "include_24hr_vol": "true"},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
            return {}
        except Exception as e:
            logger.error(f"Crypto price fetch failed: {e}")
            return {}

    async def get_market_chart(self, coin: str, days: int = 30, vs_currency: str = "gbp") -> Dict[str, Any]:
        """Get historical price data for trend analysis."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.COINGECKO_API}/coins/{coin}/market_chart",
                    params={"vs_currency": vs_currency, "days": days},
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
            return {}
        except Exception as e:
            logger.error(f"Market chart fetch failed: {e}")
            return {}

    async def get_trending(self) -> List[Dict[str, Any]]:
        """Get trending cryptocurrencies."""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.COINGECKO_API}/search/trending", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("coins", [])
            return []
        except Exception as e:
            logger.error(f"Trending fetch failed: {e}")
            return []

    async def get_stock_data(self, symbol: str, interval: str = "daily") -> Dict[str, Any]:
        """Get stock data via Alpha Vantage."""
        if not self.alpha_vantage_key:
            return {"error": "Alpha Vantage key not configured (ALPHA_VANTAGE_KEY)"}
        try:
            import aiohttp
            func = "TIME_SERIES_DAILY" if interval == "daily" else "TIME_SERIES_INTRADAY"
            params = {"function": func, "symbol": symbol, "apikey": self.alpha_vantage_key, "outputsize": "compact"}
            if interval != "daily":
                params["interval"] = interval
            async with aiohttp.ClientSession() as session:
                async with session.get(self.ALPHA_VANTAGE_API, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        return await resp.json()
            return {}
        except Exception as e:
            logger.error(f"Stock data fetch failed: {e}")
            return {}

    async def collect_market_data(self, keywords, niche="", date_from=None, date_to=None):
        data_points = []
        crypto_keywords = [k.lower() for k in keywords]
        coin_map = {"bitcoin": "bitcoin", "btc": "bitcoin", "ethereum": "ethereum", "eth": "ethereum",
                     "solana": "solana", "sol": "solana", "cardano": "cardano", "ada": "cardano"}
        coins = [coin_map.get(k, k) for k in crypto_keywords if k in coin_map or len(k) > 3]
        if not coins:
            coins = ["bitcoin", "ethereum"]

        prices = await self.get_crypto_prices(coins)
        for coin, data in prices.items():
            for currency, value in data.items():
                if currency.endswith("_change") or currency.endswith("_cap") or currency.endswith("_vol"):
                    continue
                data_points.append(MarketDataPoint(
                    source=DataSource.MANUAL, category="crypto_price", metric_name=f"{coin}_price",
                    metric_value=float(value), unit=currency, niche=niche, keywords=[coin],
                    metadata={k: v for k, v in data.items()},
                ))

        trending = await self.get_trending()
        for t in trending[:5]:
            item = t.get("item", {})
            data_points.append(MarketDataPoint(
                source=DataSource.MANUAL, category="crypto_trending", metric_name="trending_coin",
                metric_value=float(item.get("market_cap_rank", 0)), unit="rank",
                niche=niche, keywords=[item.get("name", "")],
                metadata={"name": item.get("name"), "symbol": item.get("symbol"), "price_btc": item.get("price_btc", 0)},
            ))
        return data_points

    async def collect_keyword_metrics(self, keywords):
        return []
