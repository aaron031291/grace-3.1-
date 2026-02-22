"""
Trend Detector

Analyzes time-series market data to detect emerging trends,
declining markets, seasonal patterns, and inflection points.
Grace uses this to time market entry and avoid dying niches.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field

from business_intelligence.models.data_models import MarketDataPoint, KeywordMetric

logger = logging.getLogger(__name__)


@dataclass
class TrendSignal:
    """A detected trend in market data."""
    keyword: str = ""
    niche: str = ""
    direction: str = "stable"  # rising, declining, stable, volatile, seasonal
    strength: float = 0.0  # 0-1
    change_rate: float = 0.0  # percentage change per period
    confidence: float = 0.0
    data_points: int = 0
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    inflection_detected: bool = False
    seasonal_pattern: Optional[str] = None
    recommendation: str = ""


class TrendDetector:
    """Detects market trends from time-series data."""

    def __init__(
        self,
        min_data_points: int = 5,
        rising_threshold: float = 15.0,
        declining_threshold: float = -15.0,
    ):
        self.min_data_points = min_data_points
        self.rising_threshold = rising_threshold
        self.declining_threshold = declining_threshold

    async def detect_trends(
        self,
        data_points: List[MarketDataPoint],
        keywords: Optional[List[str]] = None,
    ) -> List[TrendSignal]:
        """Detect trends across all provided data points."""
        grouped = self._group_by_keyword(data_points)
        signals = []

        for keyword, points in grouped.items():
            if keywords and keyword not in keywords:
                continue
            if len(points) < self.min_data_points:
                continue

            signal = self._analyze_series(keyword, points)
            if signal:
                signals.append(signal)

        signals.sort(key=lambda s: abs(s.strength), reverse=True)
        return signals

    async def detect_from_keyword_metrics(
        self,
        metrics: List[KeywordMetric],
    ) -> List[TrendSignal]:
        """Create trend signals from keyword metric data."""
        signals = []
        for m in metrics:
            direction = m.trend_direction
            strength = min(abs(m.trend_percentage) / 100, 1.0)

            recommendation = "Monitor"
            if direction == "rising" and strength > 0.3:
                recommendation = "Strong upward trend -- good entry timing"
            elif direction == "rising":
                recommendation = "Moderate growth -- worth investigating"
            elif direction == "declining" and strength > 0.3:
                recommendation = "Strong decline -- avoid unless you have a unique angle"
            elif direction == "declining":
                recommendation = "Slight decline -- validate demand before committing"

            signals.append(
                TrendSignal(
                    keyword=m.keyword,
                    direction=direction,
                    strength=strength,
                    change_rate=m.trend_percentage,
                    confidence=0.6 if strength > 0.1 else 0.3,
                    data_points=1,
                    recommendation=recommendation,
                )
            )

        return signals

    def _group_by_keyword(
        self, data_points: List[MarketDataPoint]
    ) -> Dict[str, List[MarketDataPoint]]:
        grouped: Dict[str, List[MarketDataPoint]] = defaultdict(list)
        for dp in data_points:
            for kw in dp.keywords:
                grouped[kw].append(dp)
            if not dp.keywords and dp.niche:
                grouped[dp.niche].append(dp)
        return grouped

    def _analyze_series(
        self, keyword: str, points: List[MarketDataPoint]
    ) -> Optional[TrendSignal]:
        """Analyze a time series of data points for a single keyword."""
        sorted_points = sorted(points, key=lambda p: p.timestamp)

        values = [p.metric_value for p in sorted_points]
        if not values or all(v == 0 for v in values):
            return None

        n = len(values)
        first_third = values[: n // 3] or values[:1]
        last_third = values[-(n // 3) :] or values[-1:]

        avg_first = sum(first_third) / len(first_third)
        avg_last = sum(last_third) / len(last_third)

        if avg_first != 0:
            change_rate = ((avg_last - avg_first) / abs(avg_first)) * 100
        elif avg_last != 0:
            change_rate = 100.0
        else:
            change_rate = 0.0

        if change_rate > self.rising_threshold:
            direction = "rising"
        elif change_rate < self.declining_threshold:
            direction = "declining"
        else:
            direction = "stable"

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5
        cv = std_dev / mean if mean != 0 else 0

        if cv > 0.5 and direction == "stable":
            direction = "volatile"

        strength = min(abs(change_rate) / 100, 1.0)

        confidence = min(0.3 + (n / 30) * 0.4 + (1 - cv) * 0.3, 1.0)

        inflection = self._detect_inflection(values)

        seasonal = self._detect_seasonality(sorted_points)

        recommendation = self._generate_recommendation(
            direction, strength, confidence, inflection
        )

        niche = sorted_points[0].niche if sorted_points else ""

        return TrendSignal(
            keyword=keyword,
            niche=niche,
            direction=direction,
            strength=strength,
            change_rate=round(change_rate, 2),
            confidence=round(confidence, 3),
            data_points=n,
            period_start=sorted_points[0].timestamp,
            period_end=sorted_points[-1].timestamp,
            inflection_detected=inflection,
            seasonal_pattern=seasonal,
            recommendation=recommendation,
        )

    def _detect_inflection(self, values: List[float]) -> bool:
        """Detect if there's a significant change in trend direction."""
        if len(values) < 6:
            return False

        mid = len(values) // 2
        first_half = values[:mid]
        second_half = values[mid:]

        first_trend = first_half[-1] - first_half[0]
        second_trend = second_half[-1] - second_half[0]

        return (first_trend > 0 and second_trend < 0) or (
            first_trend < 0 and second_trend > 0
        )

    def _detect_seasonality(
        self, points: List[MarketDataPoint]
    ) -> Optional[str]:
        """Basic seasonality detection based on timestamp patterns."""
        if len(points) < 12:
            return None

        monthly_avg: Dict[int, List[float]] = defaultdict(list)
        for p in points:
            monthly_avg[p.timestamp.month].append(p.metric_value)

        if len(monthly_avg) < 4:
            return None

        month_means = {
            m: sum(vals) / len(vals) for m, vals in monthly_avg.items()
        }

        overall_mean = sum(month_means.values()) / len(month_means)
        if overall_mean == 0:
            return None

        high_months = [
            m for m, v in month_means.items() if v > overall_mean * 1.3
        ]
        low_months = [
            m for m, v in month_means.items() if v < overall_mean * 0.7
        ]

        if high_months and low_months:
            month_names = {
                1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
                7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
            }
            peaks = ", ".join(month_names.get(m, str(m)) for m in sorted(high_months))
            return f"Seasonal peaks in {peaks}"

        return None

    def _generate_recommendation(
        self,
        direction: str,
        strength: float,
        confidence: float,
        inflection: bool,
    ) -> str:
        if confidence < 0.3:
            return "Insufficient data for reliable trend analysis. Collect more data points."

        if inflection:
            return (
                "Inflection point detected -- trend is reversing. "
                "Watch closely before committing resources."
            )

        if direction == "rising":
            if strength > 0.5:
                return "Strong upward trend. Good timing for market entry if validated."
            else:
                return "Moderate growth. Worth investigating further."
        elif direction == "declining":
            if strength > 0.5:
                return "Strong decline. Avoid unless you have a fundamentally different approach."
            else:
                return "Slight decline. Could still be viable with strong differentiation."
        elif direction == "volatile":
            return "High volatility. Market may be immature or driven by hype cycles."
        else:
            return "Stable market. Competition is the primary concern, not timing."
