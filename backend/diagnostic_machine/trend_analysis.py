"""
Historical Trend Analysis for Diagnostic Machine

Provides:
- Time-series storage of diagnostic metrics
- Trend detection and visualization data
- Predictive alerting based on trends
- Baseline auto-calibration from historical data
- Anomaly detection using historical context
"""

import json
import logging
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


class TrendDirection(str, Enum):
    """Direction of a trend."""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    VOLATILE = "volatile"


class TrendSignificance(str, Enum):
    """Significance level of a trend."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MetricPoint:
    """A single metric data point."""
    timestamp: datetime
    value: float
    metric_name: str
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class TrendResult:
    """Result of trend analysis."""
    metric_name: str
    direction: TrendDirection
    significance: TrendSignificance
    change_percent: float
    current_value: float
    baseline_value: float
    trend_slope: float
    data_points: int
    time_window_hours: int
    prediction: Optional[float] = None
    alert_threshold_breached: bool = False
    recommendation: str = ""


@dataclass
class HistoricalSummary:
    """Summary of historical metrics."""
    metric_name: str
    min_value: float
    max_value: float
    avg_value: float
    std_dev: float
    percentile_25: float
    percentile_50: float
    percentile_75: float
    percentile_95: float
    data_points: int
    time_range_hours: int


class TimeSeriesStore:
    """
    Stores time-series diagnostic metrics for trend analysis.

    Features:
    - Efficient time-based storage
    - Automatic data retention/cleanup
    - Fast retrieval by time range
    """

    def __init__(
        self,
        storage_dir: str = None,
        retention_days: int = 30,
        max_points_per_metric: int = 10000
    ):
        self.storage_dir = Path(storage_dir) if storage_dir else \
            Path(__file__).parent.parent / "data" / "diagnostic_metrics"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.retention_days = retention_days
        self.max_points = max_points_per_metric

        # In-memory cache for recent data
        self._cache: Dict[str, List[MetricPoint]] = defaultdict(list)
        self._cache_max_size = 1000

    def store(self, metric_name: str, value: float, tags: Dict[str, str] = None):
        """Store a metric data point."""
        point = MetricPoint(
            timestamp=datetime.now(timezone.utc),
            value=value,
            metric_name=metric_name,
            tags=tags or {},
        )

        # Add to cache
        self._cache[metric_name].append(point)

        # Trim cache if needed
        if len(self._cache[metric_name]) > self._cache_max_size:
            self._cache[metric_name] = self._cache[metric_name][-self._cache_max_size:]

        # Persist to disk periodically (every 100 points)
        if len(self._cache[metric_name]) % 100 == 0:
            self._persist_metric(metric_name)

    def store_batch(self, metrics: Dict[str, float], tags: Dict[str, str] = None):
        """Store multiple metrics at once."""
        for metric_name, value in metrics.items():
            self.store(metric_name, value, tags)

    def retrieve(
        self,
        metric_name: str,
        hours: int = 24,
        end_time: datetime = None
    ) -> List[MetricPoint]:
        """Retrieve metric points within time range."""
        end_time = end_time or datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)

        # Get from cache first
        points = [
            p for p in self._cache.get(metric_name, [])
            if start_time <= p.timestamp <= end_time
        ]

        # Load from disk if needed
        if len(points) < 10:  # If cache has few points, check disk
            disk_points = self._load_metric(metric_name, start_time, end_time)
            points = self._merge_points(points, disk_points)

        return sorted(points, key=lambda p: p.timestamp)

    def get_latest(self, metric_name: str) -> Optional[MetricPoint]:
        """Get the most recent data point for a metric."""
        if metric_name in self._cache and self._cache[metric_name]:
            return self._cache[metric_name][-1]
        return None

    def _persist_metric(self, metric_name: str):
        """Persist metric data to disk."""
        try:
            # Create daily file
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            safe_name = metric_name.replace('/', '_').replace(' ', '_')
            file_path = self.storage_dir / f"{safe_name}_{today}.jsonl"

            points_to_write = self._cache.get(metric_name, [])[-100:]

            with open(file_path, 'a') as f:
                for point in points_to_write:
                    f.write(json.dumps({
                        'timestamp': point.timestamp.isoformat(),
                        'value': point.value,
                        'tags': point.tags,
                    }) + '\n')

        except Exception as e:
            logger.error(f"Failed to persist metric {metric_name}: {e}")

    def _load_metric(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[MetricPoint]:
        """Load metric data from disk."""
        points = []
        try:
            safe_name = metric_name.replace('/', '_').replace(' ', '_')

            # Find relevant files
            for file_path in self.storage_dir.glob(f"{safe_name}_*.jsonl"):
                try:
                    with open(file_path, 'r') as f:
                        for line in f:
                            try:
                                data = json.loads(line)
                                timestamp = datetime.fromisoformat(data['timestamp'])
                                if start_time <= timestamp <= end_time:
                                    points.append(MetricPoint(
                                        timestamp=timestamp,
                                        value=data['value'],
                                        metric_name=metric_name,
                                        tags=data.get('tags', {}),
                                    ))
                            except (json.JSONDecodeError, KeyError):
                                continue
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Failed to load metric {metric_name}: {e}")

        return points

    def _merge_points(
        self,
        points1: List[MetricPoint],
        points2: List[MetricPoint]
    ) -> List[MetricPoint]:
        """Merge two lists of points, removing duplicates."""
        seen = set()
        merged = []

        for p in points1 + points2:
            key = (p.timestamp.isoformat(), p.metric_name)
            if key not in seen:
                seen.add(key)
                merged.append(p)

        return merged

    def cleanup_old_data(self):
        """Remove data older than retention period."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
            cutoff_str = cutoff.strftime("%Y-%m-%d")

            for file_path in self.storage_dir.glob("*.jsonl"):
                # Extract date from filename
                try:
                    date_part = file_path.stem.split('_')[-1]
                    if date_part < cutoff_str:
                        file_path.unlink()
                        logger.info(f"Cleaned up old metric file: {file_path}")
                except Exception:
                    continue

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")


class TrendAnalyzer:
    """
    Analyzes trends in diagnostic metrics.

    Features:
    - Linear regression for trend detection
    - Volatility analysis
    - Predictive alerting
    - Baseline comparison
    """

    def __init__(
        self,
        store: TimeSeriesStore = None,
        baseline_window_hours: int = 168,  # 1 week
        alert_thresholds: Dict[str, float] = None
    ):
        self.store = store or TimeSeriesStore()
        self.baseline_window = baseline_window_hours

        # Default alert thresholds (percent change from baseline)
        self.alert_thresholds = alert_thresholds or {
            'health_score': -20,  # Alert if drops more than 20%
            'pass_rate': -15,
            'cpu_percent': 30,
            'memory_percent': 25,
            'error_count': 50,
        }

    def analyze_trend(
        self,
        metric_name: str,
        window_hours: int = 24
    ) -> TrendResult:
        """Analyze trend for a metric over specified window."""
        # Get recent data
        recent_points = self.store.retrieve(metric_name, hours=window_hours)

        if len(recent_points) < 3:
            return TrendResult(
                metric_name=metric_name,
                direction=TrendDirection.STABLE,
                significance=TrendSignificance.NONE,
                change_percent=0.0,
                current_value=recent_points[-1].value if recent_points else 0.0,
                baseline_value=0.0,
                trend_slope=0.0,
                data_points=len(recent_points),
                time_window_hours=window_hours,
                recommendation="Insufficient data for trend analysis",
            )

        # Get baseline data
        baseline_points = self.store.retrieve(metric_name, hours=self.baseline_window)
        baseline_values = [p.value for p in baseline_points]
        baseline_avg = statistics.mean(baseline_values) if baseline_values else 0.0

        # Calculate current value (average of last few points)
        recent_values = [p.value for p in recent_points[-5:]]
        current_value = statistics.mean(recent_values)

        # Calculate trend slope using linear regression
        slope = self._calculate_slope(recent_points)

        # Calculate change from baseline
        if baseline_avg > 0:
            change_percent = ((current_value - baseline_avg) / baseline_avg) * 100
        else:
            change_percent = 0.0

        # Determine trend direction
        direction = self._determine_direction(slope, change_percent)

        # Determine significance
        significance = self._determine_significance(change_percent, metric_name)

        # Check alert threshold
        threshold = self.alert_thresholds.get(metric_name, 30)
        alert_breached = abs(change_percent) >= abs(threshold)

        # Generate prediction (simple linear extrapolation)
        prediction = current_value + (slope * 24)  # 24 hours ahead

        # Generate recommendation
        recommendation = self._generate_recommendation(
            metric_name, direction, significance, change_percent
        )

        return TrendResult(
            metric_name=metric_name,
            direction=direction,
            significance=significance,
            change_percent=change_percent,
            current_value=current_value,
            baseline_value=baseline_avg,
            trend_slope=slope,
            data_points=len(recent_points),
            time_window_hours=window_hours,
            prediction=prediction,
            alert_threshold_breached=alert_breached,
            recommendation=recommendation,
        )

    def get_historical_summary(
        self,
        metric_name: str,
        hours: int = 168
    ) -> HistoricalSummary:
        """Get summary statistics for a metric."""
        points = self.store.retrieve(metric_name, hours=hours)

        if not points:
            return HistoricalSummary(
                metric_name=metric_name,
                min_value=0, max_value=0, avg_value=0, std_dev=0,
                percentile_25=0, percentile_50=0, percentile_75=0, percentile_95=0,
                data_points=0, time_range_hours=hours,
            )

        values = sorted([p.value for p in points])

        return HistoricalSummary(
            metric_name=metric_name,
            min_value=min(values),
            max_value=max(values),
            avg_value=statistics.mean(values),
            std_dev=statistics.stdev(values) if len(values) > 1 else 0,
            percentile_25=self._percentile(values, 25),
            percentile_50=self._percentile(values, 50),
            percentile_75=self._percentile(values, 75),
            percentile_95=self._percentile(values, 95),
            data_points=len(points),
            time_range_hours=hours,
        )

    def calibrate_baseline(self, metric_name: str) -> Dict[str, float]:
        """Auto-calibrate baseline from historical data."""
        summary = self.get_historical_summary(metric_name, hours=self.baseline_window)

        return {
            'recommended_baseline': summary.avg_value,
            'recommended_warning_threshold': summary.percentile_75,
            'recommended_critical_threshold': summary.percentile_95,
            'volatility': summary.std_dev / summary.avg_value if summary.avg_value > 0 else 0,
        }

    def detect_anomalies(
        self,
        metric_name: str,
        hours: int = 24,
        std_threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """Detect anomalies using statistical methods."""
        summary = self.get_historical_summary(metric_name, hours=self.baseline_window)
        recent_points = self.store.retrieve(metric_name, hours=hours)

        anomalies = []
        for point in recent_points:
            if summary.std_dev > 0:
                z_score = abs(point.value - summary.avg_value) / summary.std_dev
                if z_score > std_threshold:
                    anomalies.append({
                        'timestamp': point.timestamp.isoformat(),
                        'value': point.value,
                        'z_score': z_score,
                        'expected_range': (
                            summary.avg_value - (std_threshold * summary.std_dev),
                            summary.avg_value + (std_threshold * summary.std_dev)
                        ),
                    })

        return anomalies

    def _calculate_slope(self, points: List[MetricPoint]) -> float:
        """Calculate linear regression slope."""
        if len(points) < 2:
            return 0.0

        # Use hours from first point as x values
        first_time = points[0].timestamp
        x_values = [
            (p.timestamp - first_time).total_seconds() / 3600
            for p in points
        ]
        y_values = [p.value for p in points]

        n = len(points)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_xx = sum(x * x for x in x_values)

        denominator = n * sum_xx - sum_x * sum_x
        if denominator == 0:
            return 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        return slope

    def _determine_direction(self, slope: float, change_percent: float) -> TrendDirection:
        """Determine trend direction from slope and change."""
        if abs(slope) < 0.01 and abs(change_percent) < 5:
            return TrendDirection.STABLE

        # Check for volatility (large slope but small net change)
        if abs(slope) > 0.1 and abs(change_percent) < 10:
            return TrendDirection.VOLATILE

        if change_percent > 5 or slope > 0.01:
            return TrendDirection.IMPROVING
        elif change_percent < -5 or slope < -0.01:
            return TrendDirection.DEGRADING

        return TrendDirection.STABLE

    def _determine_significance(
        self,
        change_percent: float,
        metric_name: str
    ) -> TrendSignificance:
        """Determine significance of the trend."""
        abs_change = abs(change_percent)

        # Use metric-specific thresholds if available
        threshold = abs(self.alert_thresholds.get(metric_name, 30))

        if abs_change >= threshold * 2:
            return TrendSignificance.CRITICAL
        elif abs_change >= threshold:
            return TrendSignificance.HIGH
        elif abs_change >= threshold * 0.5:
            return TrendSignificance.MEDIUM
        elif abs_change >= threshold * 0.25:
            return TrendSignificance.LOW

        return TrendSignificance.NONE

    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile of sorted values."""
        if not sorted_values:
            return 0.0

        k = (len(sorted_values) - 1) * percentile / 100
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_values) else f

        return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)

    def _generate_recommendation(
        self,
        metric_name: str,
        direction: TrendDirection,
        significance: TrendSignificance,
        change_percent: float
    ) -> str:
        """Generate human-readable recommendation."""
        if significance == TrendSignificance.NONE:
            return "Metric is stable, no action needed"

        recommendations = {
            TrendDirection.DEGRADING: {
                TrendSignificance.CRITICAL: f"URGENT: {metric_name} has degraded by {change_percent:.1f}%. Immediate investigation required.",
                TrendSignificance.HIGH: f"{metric_name} is showing concerning degradation ({change_percent:.1f}%). Review recent changes.",
                TrendSignificance.MEDIUM: f"{metric_name} is trending downward. Monitor closely.",
                TrendSignificance.LOW: f"Minor degradation in {metric_name}. Continue monitoring.",
            },
            TrendDirection.IMPROVING: {
                TrendSignificance.CRITICAL: f"{metric_name} has improved significantly ({change_percent:.1f}%). Consider updating baselines.",
                TrendSignificance.HIGH: f"{metric_name} is showing strong improvement.",
                TrendSignificance.MEDIUM: f"Positive trend in {metric_name}.",
                TrendSignificance.LOW: f"Slight improvement in {metric_name}.",
            },
            TrendDirection.VOLATILE: {
                TrendSignificance.CRITICAL: f"ALERT: {metric_name} is highly volatile. System may be unstable.",
                TrendSignificance.HIGH: f"{metric_name} showing high volatility. Investigate cause.",
                TrendSignificance.MEDIUM: f"Moderate volatility in {metric_name}.",
                TrendSignificance.LOW: f"Minor fluctuations in {metric_name}.",
            },
        }

        return recommendations.get(direction, {}).get(
            significance,
            f"Trend detected in {metric_name}"
        )


class DiagnosticMetricsCollector:
    """
    Collects and stores diagnostic metrics for trend analysis.

    Automatically extracts key metrics from diagnostic cycles.
    """

    TRACKED_METRICS = [
        'health_score',
        'pass_rate',
        'cpu_percent',
        'memory_percent',
        'disk_percent',
        'confidence_score',
        'anomaly_count',
        'pattern_count',
        'error_count',
        'warning_count',
        'cycle_duration_ms',
        'sensors_available',
    ]

    def __init__(self, store: TimeSeriesStore = None):
        self.store = store or TimeSeriesStore()

    def collect_from_cycle(
        self,
        cycle_id: str,
        sensor_data: Dict,
        interpreted_data: Dict,
        judgement: Dict,
        cycle_duration_ms: float
    ):
        """Extract and store metrics from a diagnostic cycle."""
        tags = {'cycle_id': cycle_id}

        metrics = {}

        # Health metrics
        if judgement:
            health = judgement.get('health', {})
            metrics['health_score'] = health.get('overall_score', 0) * 100
            metrics['confidence_score'] = judgement.get('confidence', {}).get('overall_confidence', 0) * 100

        # Sensor metrics
        if sensor_data:
            test_results = sensor_data.get('test_results', {})
            metrics['pass_rate'] = test_results.get('pass_rate', 0) * 100

            metrics_data = sensor_data.get('metrics', {})
            metrics['cpu_percent'] = metrics_data.get('cpu_percent', 0)
            metrics['memory_percent'] = metrics_data.get('memory_percent', 0)
            metrics['disk_percent'] = metrics_data.get('disk_percent', 0)

            metrics['sensors_available'] = len(sensor_data.get('sensors_available', []))

            logs = sensor_data.get('logs', {})
            metrics['error_count'] = logs.get('error_count', 0)
            metrics['warning_count'] = logs.get('warning_count', 0)

        # Interpreted metrics
        if interpreted_data:
            metrics['anomaly_count'] = len(interpreted_data.get('anomalies', []))
            metrics['pattern_count'] = len(interpreted_data.get('patterns', []))

        # Cycle metrics
        metrics['cycle_duration_ms'] = cycle_duration_ms

        # Store all metrics
        for metric_name, value in metrics.items():
            if value is not None:
                self.store.store(metric_name, value, tags)

    def get_all_trends(self, window_hours: int = 24) -> Dict[str, TrendResult]:
        """Get trend analysis for all tracked metrics."""
        analyzer = TrendAnalyzer(self.store)
        trends = {}

        for metric_name in self.TRACKED_METRICS:
            trends[metric_name] = analyzer.analyze_trend(metric_name, window_hours)

        return trends


# Global instances
_time_series_store: Optional[TimeSeriesStore] = None
_trend_analyzer: Optional[TrendAnalyzer] = None
_metrics_collector: Optional[DiagnosticMetricsCollector] = None


def get_time_series_store() -> TimeSeriesStore:
    """Get or create global time series store."""
    global _time_series_store
    if _time_series_store is None:
        _time_series_store = TimeSeriesStore()
    return _time_series_store


def get_trend_analyzer() -> TrendAnalyzer:
    """Get or create global trend analyzer."""
    global _trend_analyzer
    if _trend_analyzer is None:
        _trend_analyzer = TrendAnalyzer(get_time_series_store())
    return _trend_analyzer


def get_metrics_collector() -> DiagnosticMetricsCollector:
    """Get or create global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = DiagnosticMetricsCollector(get_time_series_store())
    return _metrics_collector
