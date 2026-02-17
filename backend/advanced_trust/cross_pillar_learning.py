"""
Cross-Pillar Learning Engine

Right now each pillar tracks itself independently. But self-healing should
learn from self-building's failures. If self-building keeps failing on a
certain type of code change, self-healing should pre-emptively prepare a
rollback. If self-learning keeps hitting the same knowledge gap,
self-governing should auto-prioritize filling it.

The pillars should teach each other.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class PillarType(str, Enum):
    """The four pillars of Grace's autonomy."""
    SELF_BUILDING = "self_building"
    SELF_HEALING = "self_healing"
    SELF_LEARNING = "self_learning"
    SELF_GOVERNING = "self_governing"


class InsightType(str, Enum):
    """Types of cross-pillar insights."""
    FAILURE_PATTERN = "failure_pattern"
    SUCCESS_PATTERN = "success_pattern"
    KNOWLEDGE_GAP = "knowledge_gap"
    PREEMPTIVE_ACTION = "preemptive_action"
    PRIORITY_SHIFT = "priority_shift"
    CORRELATION = "correlation"


class ActionType(str, Enum):
    """Types of cross-pillar actions."""
    PREPARE_ROLLBACK = "prepare_rollback"
    FILL_KNOWLEDGE_GAP = "fill_knowledge_gap"
    INCREASE_MONITORING = "increase_monitoring"
    ADJUST_PRIORITY = "adjust_priority"
    SHARE_PATTERN = "share_pattern"
    PREEMPTIVE_HEAL = "preemptive_heal"


@dataclass
class PillarEvent:
    """An event from a pillar."""
    event_id: str
    pillar: PillarType
    event_type: str  # success, failure, warning, info
    category: str
    description: str
    severity: float = 0.5  # 0-1
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CrossPillarInsight:
    """An insight derived from cross-pillar analysis."""
    insight_id: str
    insight_type: InsightType
    source_pillar: PillarType
    target_pillars: List[PillarType]
    description: str
    confidence: float
    recommended_actions: List[Dict[str, Any]]
    evidence: List[str]  # event_ids that led to this insight
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class CrossPillarAction:
    """An action triggered by cross-pillar learning."""
    action_id: str
    action_type: ActionType
    source_pillar: PillarType
    target_pillar: PillarType
    description: str
    trigger_insight_id: str
    status: str = "pending"  # pending, executed, skipped
    result: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CrossPillarLearningEngine:
    """
    Enables pillars to teach each other.

    Analyzes patterns across pillars and generates actionable insights:
    - Building failures -> Healing prepares rollbacks
    - Learning gaps -> Governing auto-prioritizes
    - Healing patterns -> Building avoids known-bad patterns
    - Governing policies -> Learning adjusts focus

    Cross-Pillar Rules:
    1. BUILDING failure pattern -> HEALING pre-stages rollback
    2. BUILDING repeated failure type -> LEARNING fills skill gap
    3. LEARNING knowledge gap -> GOVERNING re-prioritizes
    4. LEARNING success pattern -> BUILDING uses validated approaches
    5. HEALING frequent fix type -> BUILDING avoids that pattern
    6. GOVERNING policy change -> all pillars adjust behavior
    """

    PATTERN_THRESHOLD = 3  # Minimum occurrences to detect a pattern
    CORRELATION_WINDOW = timedelta(hours=24)

    def __init__(
        self,
        pattern_threshold: int = PATTERN_THRESHOLD,
    ):
        self.pattern_threshold = pattern_threshold
        self.events: Dict[PillarType, List[PillarEvent]] = {
            p: [] for p in PillarType
        }
        self.insights: List[CrossPillarInsight] = []
        self.actions: List[CrossPillarAction] = []
        self._pattern_counts: Dict[str, int] = defaultdict(int)
        self._failure_categories: Dict[PillarType, Dict[str, int]] = {
            p: defaultdict(int) for p in PillarType
        }
        logger.info("[CROSS-PILLAR] Learning Engine initialized")

    def record_event(self, event: PillarEvent) -> List[CrossPillarInsight]:
        """
        Record a pillar event and check for cross-pillar insights.

        Args:
            event: The pillar event

        Returns:
            List of new insights generated
        """
        self.events[event.pillar].append(event)

        if event.event_type == "failure":
            self._failure_categories[event.pillar][event.category] += 1

        # Track pattern key
        pattern_key = f"{event.pillar.value}:{event.event_type}:{event.category}"
        self._pattern_counts[pattern_key] += 1

        # Analyze for cross-pillar insights
        new_insights = self._analyze_for_insights(event)
        self.insights.extend(new_insights)

        return new_insights

    def _analyze_for_insights(
        self, event: PillarEvent
    ) -> List[CrossPillarInsight]:
        """Analyze event for cross-pillar patterns."""
        insights: List[CrossPillarInsight] = []

        # Rule 1: Building failure -> Healing prepares rollback
        if (
            event.pillar == PillarType.SELF_BUILDING
            and event.event_type == "failure"
        ):
            count = self._failure_categories[PillarType.SELF_BUILDING][
                event.category
            ]
            if count >= self.pattern_threshold:
                insight = CrossPillarInsight(
                    insight_id=f"cpi-{uuid.uuid4().hex[:12]}",
                    insight_type=InsightType.FAILURE_PATTERN,
                    source_pillar=PillarType.SELF_BUILDING,
                    target_pillars=[PillarType.SELF_HEALING],
                    description=(
                        f"Building has failed {count}x on '{event.category}'. "
                        f"Healing should pre-stage rollback."
                    ),
                    confidence=min(0.5 + (count * 0.1), 0.95),
                    recommended_actions=[
                        {
                            "action": ActionType.PREPARE_ROLLBACK.value,
                            "target": PillarType.SELF_HEALING.value,
                            "category": event.category,
                        }
                    ],
                    evidence=[event.event_id],
                )
                insights.append(insight)
                self._generate_action(insight)

        # Rule 2: Building repeated failures -> Learning fills gap
        if (
            event.pillar == PillarType.SELF_BUILDING
            and event.event_type == "failure"
        ):
            count = self._failure_categories[PillarType.SELF_BUILDING][
                event.category
            ]
            if count >= self.pattern_threshold + 1:
                insight = CrossPillarInsight(
                    insight_id=f"cpi-{uuid.uuid4().hex[:12]}",
                    insight_type=InsightType.KNOWLEDGE_GAP,
                    source_pillar=PillarType.SELF_BUILDING,
                    target_pillars=[PillarType.SELF_LEARNING],
                    description=(
                        f"Building keeps failing on '{event.category}' "
                        f"({count}x). Learning should fill this skill gap."
                    ),
                    confidence=min(0.5 + (count * 0.08), 0.90),
                    recommended_actions=[
                        {
                            "action": ActionType.FILL_KNOWLEDGE_GAP.value,
                            "target": PillarType.SELF_LEARNING.value,
                            "category": event.category,
                        }
                    ],
                    evidence=[event.event_id],
                )
                insights.append(insight)
                self._generate_action(insight)

        # Rule 3: Learning knowledge gap -> Governing re-prioritizes
        if (
            event.pillar == PillarType.SELF_LEARNING
            and event.event_type == "failure"
            and event.category == "knowledge_gap"
        ):
            count = self._failure_categories[PillarType.SELF_LEARNING][
                "knowledge_gap"
            ]
            if count >= self.pattern_threshold:
                insight = CrossPillarInsight(
                    insight_id=f"cpi-{uuid.uuid4().hex[:12]}",
                    insight_type=InsightType.PRIORITY_SHIFT,
                    source_pillar=PillarType.SELF_LEARNING,
                    target_pillars=[PillarType.SELF_GOVERNING],
                    description=(
                        f"Learning has hit knowledge gaps {count}x. "
                        f"Governing should auto-prioritize filling them."
                    ),
                    confidence=min(0.6 + (count * 0.07), 0.90),
                    recommended_actions=[
                        {
                            "action": ActionType.ADJUST_PRIORITY.value,
                            "target": PillarType.SELF_GOVERNING.value,
                            "gap_type": event.data.get("gap_type", "unknown"),
                        }
                    ],
                    evidence=[event.event_id],
                )
                insights.append(insight)
                self._generate_action(insight)

        # Rule 4: Healing frequent fix type -> Building avoids pattern
        if (
            event.pillar == PillarType.SELF_HEALING
            and event.event_type == "success"
        ):
            count = self._pattern_counts[
                f"{PillarType.SELF_HEALING.value}:success:{event.category}"
            ]
            if count >= self.pattern_threshold:
                insight = CrossPillarInsight(
                    insight_id=f"cpi-{uuid.uuid4().hex[:12]}",
                    insight_type=InsightType.SUCCESS_PATTERN,
                    source_pillar=PillarType.SELF_HEALING,
                    target_pillars=[PillarType.SELF_BUILDING],
                    description=(
                        f"Healing frequently fixes '{event.category}' "
                        f"({count}x). Building should avoid this pattern."
                    ),
                    confidence=min(0.5 + (count * 0.1), 0.90),
                    recommended_actions=[
                        {
                            "action": ActionType.SHARE_PATTERN.value,
                            "target": PillarType.SELF_BUILDING.value,
                            "avoid_pattern": event.category,
                        }
                    ],
                    evidence=[event.event_id],
                )
                insights.append(insight)
                self._generate_action(insight)

        # Rule 5: Governing policy triggers cross-pillar action
        if (
            event.pillar == PillarType.SELF_GOVERNING
            and event.event_type == "policy_change"
        ):
            insight = CrossPillarInsight(
                insight_id=f"cpi-{uuid.uuid4().hex[:12]}",
                insight_type=InsightType.PRIORITY_SHIFT,
                source_pillar=PillarType.SELF_GOVERNING,
                target_pillars=[
                    PillarType.SELF_BUILDING,
                    PillarType.SELF_HEALING,
                    PillarType.SELF_LEARNING,
                ],
                description=(
                    f"Governing policy change: {event.description}. "
                    f"All pillars should adjust behavior."
                ),
                confidence=0.85,
                recommended_actions=[
                    {
                        "action": ActionType.ADJUST_PRIORITY.value,
                        "target": "all",
                        "policy": event.data.get("policy", {}),
                    }
                ],
                evidence=[event.event_id],
            )
            insights.append(insight)

        return insights

    def _generate_action(self, insight: CrossPillarInsight) -> None:
        """Generate action from insight."""
        for rec in insight.recommended_actions:
            action_type_str = rec.get("action", "share_pattern")
            try:
                action_type = ActionType(action_type_str)
            except ValueError:
                action_type = ActionType.SHARE_PATTERN

            target_str = rec.get("target", "self_healing")
            try:
                target_pillar = PillarType(target_str)
            except ValueError:
                continue

            action = CrossPillarAction(
                action_id=f"cpa-{uuid.uuid4().hex[:12]}",
                action_type=action_type,
                source_pillar=insight.source_pillar,
                target_pillar=target_pillar,
                description=insight.description,
                trigger_insight_id=insight.insight_id,
            )
            self.actions.append(action)

    def get_pending_actions(
        self, target_pillar: Optional[PillarType] = None
    ) -> List[CrossPillarAction]:
        """Get pending actions, optionally filtered by target."""
        actions = [a for a in self.actions if a.status == "pending"]
        if target_pillar:
            actions = [a for a in actions if a.target_pillar == target_pillar]
        return actions

    def mark_action_executed(
        self, action_id: str, result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Mark an action as executed."""
        for action in self.actions:
            if action.action_id == action_id:
                action.status = "executed"
                action.result = result or {}
                return True
        return False

    def get_insights_for_pillar(
        self, pillar: PillarType, limit: int = 20
    ) -> List[CrossPillarInsight]:
        """Get insights relevant to a pillar."""
        relevant = [
            i for i in self.insights if pillar in i.target_pillars
        ]
        return relevant[-limit:]

    def get_failure_patterns(self) -> Dict[str, Dict[str, int]]:
        """Get failure patterns across all pillars."""
        return {
            p.value: dict(cats) for p, cats in self._failure_categories.items()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_events": sum(len(e) for e in self.events.values()),
            "events_by_pillar": {
                p.value: len(e) for p, e in self.events.items()
            },
            "total_insights": len(self.insights),
            "total_actions": len(self.actions),
            "pending_actions": sum(
                1 for a in self.actions if a.status == "pending"
            ),
            "executed_actions": sum(
                1 for a in self.actions if a.status == "executed"
            ),
            "failure_patterns": self.get_failure_patterns(),
        }
