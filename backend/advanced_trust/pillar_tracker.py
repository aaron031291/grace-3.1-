"""
Pillar Tracking System

Tracks the four pillars of Grace's autonomy:
- Self-Building: Code generation, testing, deployment
- Self-Healing: Error detection, diagnosis, repair
- Self-Learning: Knowledge acquisition, skill development
- Self-Governing: Policy enforcement, resource management

Each pillar has its own KPI dashboard, success/failure rates, and feeds
into the System-Wide Trust Thermometer.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class Pillar(str, Enum):
    """The four pillars."""
    SELF_BUILDING = "self_building"
    SELF_HEALING = "self_healing"
    SELF_LEARNING = "self_learning"
    SELF_GOVERNING = "self_governing"


class EventSeverity(str, Enum):
    """Severity of a pillar event."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class PillarEvent:
    """An event recorded for a pillar."""
    event_id: str
    pillar: Pillar
    event_type: str  # success, failure, warning, info
    category: str
    description: str
    severity: EventSeverity = EventSeverity.INFO
    duration_ms: Optional[float] = None
    data: Dict[str, Any] = field(default_factory=dict)
    genesis_key_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PillarKPI:
    """KPIs for a single pillar."""
    pillar: Pillar
    total_events: int = 0
    successes: int = 0
    failures: int = 0
    warnings: int = 0
    success_rate: float = 0.0
    avg_duration_ms: float = 0.0
    total_duration_ms: float = 0.0
    last_event: Optional[datetime] = None
    streak_type: str = "none"  # success, failure
    streak_count: int = 0
    categories: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: {"success": 0, "failure": 0, "total": 0})
    )


@dataclass
class PillarReport:
    """Report for all pillars."""
    pillars: Dict[Pillar, PillarKPI]
    overall_health: float
    strongest_pillar: Optional[Pillar]
    weakest_pillar: Optional[Pillar]
    total_events: int
    overall_success_rate: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PillarTracker:
    """
    Tracks KPIs, events, and health for all four pillars.

    Each pillar independently tracks:
    - Success/failure counts and rates
    - Event categories and patterns
    - Duration metrics
    - Streaks (consecutive successes/failures)

    The tracker provides:
    - Per-pillar KPI dashboards
    - Cross-pillar health reports
    - Trend analysis per pillar
    - Integration with Trust Thermometer
    """

    def __init__(self):
        self.kpis: Dict[Pillar, PillarKPI] = {
            p: PillarKPI(pillar=p) for p in Pillar
        }
        self.events: Dict[Pillar, List[PillarEvent]] = {
            p: [] for p in Pillar
        }
        logger.info("[PILLAR-TRACKER] Initialized tracking for all 4 pillars")

    def record_event(
        self,
        pillar: Pillar,
        event_type: str,
        category: str,
        description: str,
        severity: EventSeverity = EventSeverity.INFO,
        duration_ms: Optional[float] = None,
        data: Optional[Dict[str, Any]] = None,
        genesis_key_id: Optional[str] = None,
    ) -> PillarEvent:
        """
        Record an event for a pillar.

        Args:
            pillar: Which pillar
            event_type: success, failure, warning, info
            category: Category of the event
            description: Human-readable description
            severity: Severity level
            duration_ms: Duration in milliseconds
            data: Additional data
            genesis_key_id: Link to Genesis Key

        Returns:
            PillarEvent
        """
        event = PillarEvent(
            event_id=f"pe-{uuid.uuid4().hex[:12]}",
            pillar=pillar,
            event_type=event_type,
            category=category,
            description=description,
            severity=severity,
            duration_ms=duration_ms,
            data=data or {},
            genesis_key_id=genesis_key_id,
        )

        self.events[pillar].append(event)
        self._update_kpi(pillar, event)

        return event

    def record_success(
        self,
        pillar: Pillar,
        category: str,
        description: str,
        duration_ms: Optional[float] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> PillarEvent:
        """Convenience: record a success event."""
        return self.record_event(
            pillar=pillar,
            event_type="success",
            category=category,
            description=description,
            severity=EventSeverity.INFO,
            duration_ms=duration_ms,
            data=data,
        )

    def record_failure(
        self,
        pillar: Pillar,
        category: str,
        description: str,
        severity: EventSeverity = EventSeverity.ERROR,
        duration_ms: Optional[float] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> PillarEvent:
        """Convenience: record a failure event."""
        return self.record_event(
            pillar=pillar,
            event_type="failure",
            category=category,
            description=description,
            severity=severity,
            duration_ms=duration_ms,
            data=data,
        )

    def _update_kpi(self, pillar: Pillar, event: PillarEvent) -> None:
        """Update KPIs based on new event."""
        kpi = self.kpis[pillar]
        kpi.total_events += 1
        kpi.last_event = event.timestamp

        if event.event_type == "success":
            kpi.successes += 1
            if kpi.streak_type == "success":
                kpi.streak_count += 1
            else:
                kpi.streak_type = "success"
                kpi.streak_count = 1
        elif event.event_type == "failure":
            kpi.failures += 1
            if kpi.streak_type == "failure":
                kpi.streak_count += 1
            else:
                kpi.streak_type = "failure"
                kpi.streak_count = 1
        elif event.event_type == "warning":
            kpi.warnings += 1

        # Update success rate
        total_decisive = kpi.successes + kpi.failures
        if total_decisive > 0:
            kpi.success_rate = kpi.successes / total_decisive

        # Update duration
        if event.duration_ms is not None:
            kpi.total_duration_ms += event.duration_ms
            events_with_duration = sum(
                1 for e in self.events[pillar] if e.duration_ms is not None
            )
            if events_with_duration > 0:
                kpi.avg_duration_ms = kpi.total_duration_ms / events_with_duration

        # Update category stats
        cat_stats = kpi.categories[event.category]
        cat_stats["total"] = cat_stats.get("total", 0) + 1
        if event.event_type == "success":
            cat_stats["success"] = cat_stats.get("success", 0) + 1
        elif event.event_type == "failure":
            cat_stats["failure"] = cat_stats.get("failure", 0) + 1

    def get_pillar_kpi(self, pillar: Pillar) -> PillarKPI:
        """Get KPIs for a specific pillar."""
        return self.kpis[pillar]

    def get_pillar_success_rate(self, pillar: Pillar) -> float:
        """Get success rate for a pillar."""
        return self.kpis[pillar].success_rate

    def get_pillar_events(
        self,
        pillar: Pillar,
        event_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[PillarEvent]:
        """Get events for a pillar."""
        events = self.events[pillar]
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return events[-limit:]

    def get_report(self) -> PillarReport:
        """Generate a comprehensive pillar report."""
        total_events = sum(k.total_events for k in self.kpis.values())
        total_successes = sum(k.successes for k in self.kpis.values())
        total_failures = sum(k.failures for k in self.kpis.values())
        total_decisive = total_successes + total_failures

        overall_success_rate = (
            total_successes / total_decisive if total_decisive > 0 else 0.0
        )

        # Calculate overall health (weighted success rate)
        rates = {
            p: k.success_rate for p, k in self.kpis.items()
            if (k.successes + k.failures) > 0
        }
        overall_health = (
            sum(rates.values()) / len(rates) if rates else 0.5
        )

        # Strongest and weakest
        if rates:
            strongest = max(rates.items(), key=lambda x: x[1])[0]
            weakest = min(rates.items(), key=lambda x: x[1])[0]
        else:
            strongest = None
            weakest = None

        return PillarReport(
            pillars=dict(self.kpis),
            overall_health=overall_health,
            strongest_pillar=strongest,
            weakest_pillar=weakest,
            total_events=total_events,
            overall_success_rate=overall_success_rate,
        )

    def get_pillar_trend(
        self, pillar: Pillar, window: int = 20
    ) -> str:
        """Get trend for a pillar (improving/stable/declining)."""
        events = self.events[pillar]
        decisive = [
            e for e in events if e.event_type in ("success", "failure")
        ]

        if len(decisive) < window:
            return "insufficient_data"

        recent = decisive[-window:]
        first_half = recent[: window // 2]
        second_half = recent[window // 2:]

        first_rate = sum(
            1 for e in first_half if e.event_type == "success"
        ) / len(first_half)
        second_rate = sum(
            1 for e in second_half if e.event_type == "success"
        ) / len(second_half)

        diff = second_rate - first_rate
        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "declining"
        return "stable"

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics."""
        report = self.get_report()
        return {
            "overall_health": report.overall_health,
            "overall_success_rate": report.overall_success_rate,
            "total_events": report.total_events,
            "strongest_pillar": (
                report.strongest_pillar.value if report.strongest_pillar else None
            ),
            "weakest_pillar": (
                report.weakest_pillar.value if report.weakest_pillar else None
            ),
            "pillars": {
                p.value: {
                    "total_events": k.total_events,
                    "successes": k.successes,
                    "failures": k.failures,
                    "success_rate": k.success_rate,
                    "streak": f"{k.streak_type}:{k.streak_count}",
                }
                for p, k in self.kpis.items()
            },
        }
