"""
Base connector interface and registry for the BI system.

All data connectors inherit from BaseConnector and register themselves
with ConnectorRegistry. The registry provides a single point of access
for the synthesis engine to pull data from all available sources.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Type
from dataclasses import dataclass, field

from business_intelligence.config import ConnectorConfig, ConnectorStatus
from business_intelligence.models.data_models import MarketDataPoint, KeywordMetric

logger = logging.getLogger(__name__)


@dataclass
class ConnectorHealth:
    status: ConnectorStatus = ConnectorStatus.DISABLED
    last_successful_pull: Optional[datetime] = None
    last_error: Optional[str] = None
    total_data_points: int = 0
    error_count: int = 0
    rate_limit_remaining: Optional[int] = None


class BaseConnector(ABC):
    """Abstract base for all data connectors."""

    connector_name: str = "base"
    connector_version: str = "1.0.0"

    def __init__(self, config: ConnectorConfig):
        self.config = config
        self.health = ConnectorHealth()
        self._logger = logging.getLogger(f"bi.connector.{self.connector_name}")

        if config.is_configured:
            self.health.status = ConnectorStatus.ACTIVE
        elif config.enabled:
            self.health.status = ConnectorStatus.DEGRADED
            self._logger.warning(
                f"{self.connector_name} enabled but missing credentials -- running in degraded mode"
            )

    @property
    def is_available(self) -> bool:
        return self.health.status in (ConnectorStatus.ACTIVE, ConnectorStatus.DEGRADED)

    @abstractmethod
    async def test_connection(self) -> bool:
        """Verify that the connector can reach its target API."""
        ...

    @abstractmethod
    async def collect_market_data(
        self,
        keywords: List[str],
        niche: str = "",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[MarketDataPoint]:
        """Pull market data points for given keywords/niche."""
        ...

    @abstractmethod
    async def collect_keyword_metrics(
        self,
        keywords: List[str],
    ) -> List[KeywordMetric]:
        """Pull keyword-level performance metrics."""
        ...

    async def safe_collect(
        self,
        keywords: List[str],
        niche: str = "",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[MarketDataPoint]:
        """Wrapper that catches errors and updates health."""
        if not self.is_available:
            return []
        try:
            results = await self.collect_market_data(keywords, niche, date_from, date_to)
            self.health.last_successful_pull = datetime.utcnow()
            self.health.total_data_points += len(results)
            return results
        except Exception as e:
            self.health.error_count += 1
            self.health.last_error = str(e)
            self._logger.error(f"Collection failed: {e}")
            if self.health.error_count >= 5:
                self.health.status = ConnectorStatus.ERROR
            return []

    def get_health_report(self) -> Dict[str, Any]:
        return {
            "connector": self.connector_name,
            "version": self.connector_version,
            "status": self.health.status.value,
            "last_successful_pull": (
                self.health.last_successful_pull.isoformat()
                if self.health.last_successful_pull
                else None
            ),
            "total_data_points": self.health.total_data_points,
            "error_count": self.health.error_count,
            "last_error": self.health.last_error,
        }


class ConnectorRegistry:
    """Registry of all available data connectors."""

    _connectors: Dict[str, BaseConnector] = {}

    @classmethod
    def register(cls, name: str, connector: BaseConnector):
        cls._connectors[name] = connector
        logger.info(
            f"Registered connector: {name} (status: {connector.health.status.value})"
        )

    @classmethod
    def get(cls, name: str) -> Optional[BaseConnector]:
        return cls._connectors.get(name)

    @classmethod
    def get_all(cls) -> Dict[str, BaseConnector]:
        return dict(cls._connectors)

    @classmethod
    def get_active(cls) -> Dict[str, BaseConnector]:
        return {
            k: v for k, v in cls._connectors.items() if v.is_available
        }

    @classmethod
    def health_report(cls) -> Dict[str, Dict]:
        return {
            name: conn.get_health_report()
            for name, conn in cls._connectors.items()
        }

    @classmethod
    async def collect_all(
        cls,
        keywords: List[str],
        niche: str = "",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[MarketDataPoint]:
        """Pull data from all active connectors."""
        all_data = []
        for name, connector in cls.get_active().items():
            data = await connector.safe_collect(keywords, niche, date_from, date_to)
            all_data.extend(data)
            logger.info(f"Collected {len(data)} data points from {name}")
        return all_data

    @classmethod
    def reset(cls):
        cls._connectors.clear()
