"""
Google Analytics connector.

Connects to GA4 via the Google Analytics Data API to pull traffic,
audience, and conversion metrics for market intelligence.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from business_intelligence.connectors.base import BaseConnector
from business_intelligence.config import ConnectorConfig
from business_intelligence.models.data_models import (
    MarketDataPoint,
    KeywordMetric,
    TrafficSource,
    DataSource,
)

logger = logging.getLogger(__name__)


class GoogleAnalyticsConnector(BaseConnector):
    connector_name = "google_analytics"
    connector_version = "1.0.0"

    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.property_id = config.extra.get("property_id")
        self.credentials_path = config.extra.get("credentials_path")
        self._client = None

    async def _get_client(self):
        """Lazily initialize the GA4 client."""
        if self._client is not None:
            return self._client

        if not self.config.is_configured:
            return None

        try:
            from google.analytics.data_v1beta import BetaAnalyticsDataClient
            from google.oauth2 import service_account

            if self.credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=["https://www.googleapis.com/auth/analytics.readonly"],
                )
                self._client = BetaAnalyticsDataClient(credentials=credentials)
            else:
                self._client = BetaAnalyticsDataClient()

            return self._client
        except ImportError:
            logger.warning(
                "google-analytics-data package not installed. "
                "Install with: pip install google-analytics-data"
            )
            return None
        except Exception as e:
            logger.error(f"Failed to initialize GA4 client: {e}")
            return None

    async def test_connection(self) -> bool:
        client = await self._get_client()
        if not client or not self.property_id:
            return False
        try:
            from google.analytics.data_v1beta.types import (
                RunReportRequest,
                DateRange,
                Metric,
            )

            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[DateRange(start_date="yesterday", end_date="today")],
                metrics=[Metric(name="activeUsers")],
            )
            client.run_report(request)
            return True
        except Exception as e:
            logger.error(f"GA4 connection test failed: {e}")
            return False

    async def collect_market_data(
        self,
        keywords: List[str],
        niche: str = "",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[MarketDataPoint]:
        client = await self._get_client()
        if not client or not self.property_id:
            return self._generate_degraded_data(keywords, niche)

        date_from = date_from or datetime.utcnow() - timedelta(days=30)
        date_to = date_to or datetime.utcnow()

        try:
            from google.analytics.data_v1beta.types import (
                RunReportRequest,
                DateRange,
                Dimension,
                Metric,
            )

            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                date_ranges=[
                    DateRange(
                        start_date=date_from.strftime("%Y-%m-%d"),
                        end_date=date_to.strftime("%Y-%m-%d"),
                    )
                ],
                dimensions=[
                    Dimension(name="sessionSource"),
                    Dimension(name="sessionMedium"),
                ],
                metrics=[
                    Metric(name="sessions"),
                    Metric(name="activeUsers"),
                    Metric(name="bounceRate"),
                    Metric(name="conversions"),
                ],
            )

            response = client.run_report(request)
            data_points = []

            for row in response.rows:
                source = row.dimension_values[0].value
                medium = row.dimension_values[1].value
                sessions = float(row.metric_values[0].value)
                users = float(row.metric_values[1].value)
                bounce_rate = float(row.metric_values[2].value)
                conversions = float(row.metric_values[3].value)

                data_points.append(
                    MarketDataPoint(
                        source=DataSource.GOOGLE_ANALYTICS,
                        category="traffic",
                        metric_name="sessions",
                        metric_value=sessions,
                        unit="count",
                        niche=niche,
                        keywords=keywords,
                        metadata={
                            "source": source,
                            "medium": medium,
                            "users": users,
                            "bounce_rate": bounce_rate,
                            "conversions": conversions,
                        },
                    )
                )

            return data_points

        except Exception as e:
            logger.error(f"GA4 data collection failed: {e}")
            return self._generate_degraded_data(keywords, niche)

    async def collect_keyword_metrics(
        self,
        keywords: List[str],
    ) -> List[KeywordMetric]:
        """GA4 doesn't directly provide keyword search volume.
        Returns empty list -- use SerpAPI for keyword metrics."""
        return []

    async def get_traffic_sources(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[TrafficSource]:
        data_points = await self.collect_market_data(
            keywords=[], niche="", date_from=date_from, date_to=date_to
        )
        sources = []
        for dp in data_points:
            sources.append(
                TrafficSource(
                    source_name=dp.metadata.get("source", "unknown"),
                    medium=dp.metadata.get("medium", "unknown"),
                    sessions=int(dp.metric_value),
                    users=int(dp.metadata.get("users", 0)),
                    bounce_rate=dp.metadata.get("bounce_rate", 0.0),
                    conversion_rate=dp.metadata.get("conversions", 0.0),
                    timestamp=dp.timestamp,
                )
            )
        return sources

    def _generate_degraded_data(
        self, keywords: List[str], niche: str
    ) -> List[MarketDataPoint]:
        """When GA4 is not configured, return a marker data point
        indicating that real analytics data is needed."""
        return [
            MarketDataPoint(
                source=DataSource.GOOGLE_ANALYTICS,
                category="system",
                metric_name="connector_status",
                metric_value=0.0,
                unit="status",
                niche=niche,
                keywords=keywords,
                confidence=0.0,
                metadata={
                    "message": "GA4 not configured. Set GA_API_KEY and GA_PROPERTY_ID.",
                    "action_required": "Configure Google Analytics credentials",
                },
            )
        ]
