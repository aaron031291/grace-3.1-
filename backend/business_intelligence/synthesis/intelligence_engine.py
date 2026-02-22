"""
Intelligence Engine

The central synthesis layer that connects all BI components.
Aggregates data from connectors, runs trend analysis, scores opportunities,
and produces actionable intelligence snapshots.

This is the engine that Grace calls when she needs to "think" about
the business landscape. It maintains state over time, building
an increasingly rich picture of each market.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from business_intelligence.config import BIConfig, BIPhase
from business_intelligence.connectors.base import ConnectorRegistry
from business_intelligence.synthesis.trend_detector import TrendDetector, TrendSignal
from business_intelligence.synthesis.opportunity_scorer import OpportunityScorer, ScoredOpportunity
from business_intelligence.market_research.research_orchestrator import (
    MarketResearchOrchestrator,
    ResearchReport,
)
from business_intelligence.models.data_models import (
    MarketDataPoint,
    MarketOpportunity,
    IntelligenceSnapshot,
    PainPoint,
    ProductConcept,
    ProductType,
)

logger = logging.getLogger(__name__)


@dataclass
class IntelligenceState:
    """Grace's current business intelligence state.

    This persists between cycles, allowing Grace to build understanding
    over weeks and months.
    """
    current_phase: BIPhase = BIPhase.COLLECT
    niches_under_investigation: List[str] = field(default_factory=list)
    all_data_points: List[MarketDataPoint] = field(default_factory=list)
    all_pain_points: List[PainPoint] = field(default_factory=list)
    trend_signals: List[TrendSignal] = field(default_factory=list)
    scored_opportunities: List[ScoredOpportunity] = field(default_factory=list)
    research_reports: List[ResearchReport] = field(default_factory=list)
    product_concepts: List[ProductConcept] = field(default_factory=list)
    snapshots: List[IntelligenceSnapshot] = field(default_factory=list)
    last_collection_time: Optional[datetime] = None
    total_cycles_run: int = 0
    grace_notes: List[str] = field(default_factory=list)


class IntelligenceEngine:
    """Central intelligence engine for the BI system."""

    def __init__(self, config: Optional[BIConfig] = None):
        self.config = config or BIConfig.from_env()
        self.trend_detector = TrendDetector(
            min_data_points=self.config.min_data_points_for_trend
        )
        self.opportunity_scorer = OpportunityScorer()
        self.research_orchestrator = MarketResearchOrchestrator()
        self.state = IntelligenceState()

    async def run_intelligence_cycle(
        self,
        niches: List[str],
        keywords: Dict[str, List[str]],
        force_collection: bool = False,
    ) -> IntelligenceSnapshot:
        """Run a full intelligence collection and analysis cycle.

        Args:
            niches: Market niches to investigate
            keywords: Dict mapping niche -> list of keywords
            force_collection: Skip time checks and collect immediately
        """
        logger.info(f"Starting intelligence cycle #{self.state.total_cycles_run + 1}")
        self.state.niches_under_investigation = niches

        should_collect = force_collection or self._should_collect()

        if should_collect:
            await self._collect_phase(keywords)

        await self._analyze_phase()

        await self._synthesize_phase(niches, keywords)

        snapshot = self._create_snapshot()
        self.state.snapshots.append(snapshot)
        self.state.total_cycles_run += 1

        logger.info(
            f"Intelligence cycle #{self.state.total_cycles_run} complete. "
            f"Phase: {self.state.current_phase.value}, "
            f"Data points: {len(self.state.all_data_points)}, "
            f"Opportunities: {len(self.state.scored_opportunities)}"
        )

        return snapshot

    async def _collect_phase(self, keywords: Dict[str, List[str]]):
        """Phase 1: Collect data from all connectors."""
        self.state.current_phase = BIPhase.COLLECT

        all_keywords = []
        for kw_list in keywords.values():
            all_keywords.extend(kw_list)
        all_keywords = list(set(all_keywords))

        for niche, kw_list in keywords.items():
            new_data = await ConnectorRegistry.collect_all(
                keywords=kw_list, niche=niche
            )
            self.state.all_data_points.extend(new_data)

        self.state.last_collection_time = datetime.utcnow()
        self._prune_old_data()

        logger.info(
            f"Collection complete: {len(self.state.all_data_points)} total data points"
        )

    async def _analyze_phase(self):
        """Phase 2: Analyze trends and patterns."""
        self.state.current_phase = BIPhase.SYNTHESIZE

        trend_data = [
            dp for dp in self.state.all_data_points
            if dp.category in ("trends", "search_results", "traffic", "ad_performance")
        ]

        if trend_data:
            self.state.trend_signals = await self.trend_detector.detect_trends(
                trend_data
            )

    async def _synthesize_phase(
        self,
        niches: List[str],
        keywords: Dict[str, List[str]],
    ):
        """Phase 3: Run market research and score opportunities."""
        self.state.current_phase = BIPhase.IDENTIFY

        for niche in niches:
            kws = keywords.get(niche, [niche])
            report = await self.research_orchestrator.run_research(
                niche=niche,
                keywords=kws,
                depth="standard",
            )
            self.state.research_reports.append(report)
            self.state.all_pain_points.extend(report.pain_points)

        all_opps = []
        for report in self.state.research_reports:
            all_opps.extend(report.opportunities)

        if all_opps:
            self.state.scored_opportunities = await self.opportunity_scorer.score_opportunities(
                opportunities=all_opps,
                trends=self.state.trend_signals,
                market_data_volume=len(self.state.all_data_points),
            )

        self._auto_advance_phase()

    def _should_collect(self) -> bool:
        """Check if enough time has passed since last collection."""
        if not self.state.last_collection_time:
            return True
        elapsed = datetime.utcnow() - self.state.last_collection_time
        return elapsed > timedelta(hours=self.config.snapshot_interval_hours)

    def _prune_old_data(self):
        """Remove data points older than retention period."""
        cutoff = datetime.utcnow() - timedelta(
            days=self.config.historical_retention_days
        )
        self.state.all_data_points = [
            dp for dp in self.state.all_data_points
            if dp.timestamp > cutoff
        ]

    def _auto_advance_phase(self):
        """Automatically advance the BI phase based on data sufficiency."""
        if not self.state.scored_opportunities:
            self.state.current_phase = BIPhase.COLLECT
            self.state.grace_notes.append(
                f"[{datetime.utcnow().isoformat()}] Still collecting -- "
                "no scored opportunities yet."
            )
            return

        top = self.state.scored_opportunities[0]
        if top.total_score >= self.config.opportunity_score_threshold:
            self.state.current_phase = BIPhase.VALIDATE
            self.state.grace_notes.append(
                f"[{datetime.utcnow().isoformat()}] Moving to VALIDATE phase. "
                f"Top opportunity: {top.opportunity.title} (score: {top.total_score:.2f})"
            )
        else:
            self.state.current_phase = BIPhase.IDENTIFY
            self.state.grace_notes.append(
                f"[{datetime.utcnow().isoformat()}] Staying in IDENTIFY phase. "
                f"Best score is {top.total_score:.2f}, need {self.config.opportunity_score_threshold:.2f}."
            )

    def _create_snapshot(self) -> IntelligenceSnapshot:
        """Create a point-in-time snapshot of intelligence state."""
        top_opps = [
            s.opportunity for s in self.state.scored_opportunities[:5]
        ]
        top_pps = sorted(
            self.state.all_pain_points,
            key=lambda p: p.pain_score,
            reverse=True,
        )[:10]

        recommendations = []
        for s in self.state.scored_opportunities[:3]:
            recommendations.append(f"{s.verdict} -> {s.recommended_action}")

        if not recommendations:
            recommendations = [
                "Continue data collection. Configure more connectors for richer data.",
                "Focus keyword research on specific niches.",
            ]

        health = ConnectorRegistry.health_report()

        return IntelligenceSnapshot(
            data_points_collected=len(self.state.all_data_points),
            active_niches=self.state.niches_under_investigation,
            top_opportunities=top_opps,
            top_pain_points=top_pps,
            product_concepts=self.state.product_concepts,
            connectors_status={
                k: v.get("status", "unknown") for k, v in health.items()
            },
            phase=self.state.current_phase.value,
            summary=self._generate_summary(),
            recommendations=recommendations,
        )

    def _generate_summary(self) -> str:
        """Generate a human-readable summary of current intelligence state."""
        parts = [
            f"Intelligence cycle #{self.state.total_cycles_run}.",
            f"Phase: {self.state.current_phase.value}.",
            f"Tracking {len(self.state.niches_under_investigation)} niches.",
            f"{len(self.state.all_data_points)} data points collected.",
            f"{len(self.state.all_pain_points)} pain points identified.",
            f"{len(self.state.scored_opportunities)} opportunities scored.",
        ]

        active_connectors = ConnectorRegistry.get_active()
        parts.append(f"{len(active_connectors)} connectors active.")

        if self.state.scored_opportunities:
            top = self.state.scored_opportunities[0]
            parts.append(
                f"Top opportunity: {top.opportunity.title} "
                f"(score: {top.total_score:.2f})."
            )

        rising_trends = [
            t for t in self.state.trend_signals if t.direction == "rising"
        ]
        if rising_trends:
            keywords = [t.keyword for t in rising_trends[:3]]
            parts.append(f"Rising trends: {', '.join(keywords)}.")

        return " ".join(parts)

    async def get_status(self) -> Dict[str, Any]:
        """Get current engine status for API consumption."""
        return {
            "phase": self.state.current_phase.value,
            "total_cycles": self.state.total_cycles_run,
            "niches": self.state.niches_under_investigation,
            "data_points": len(self.state.all_data_points),
            "pain_points": len(self.state.all_pain_points),
            "opportunities": len(self.state.scored_opportunities),
            "trend_signals": len(self.state.trend_signals),
            "research_reports": len(self.state.research_reports),
            "connectors": ConnectorRegistry.health_report(),
            "last_collection": (
                self.state.last_collection_time.isoformat()
                if self.state.last_collection_time
                else None
            ),
            "summary": self._generate_summary(),
            "top_opportunities": [
                {
                    "title": s.opportunity.title,
                    "score": s.total_score,
                    "verdict": s.verdict,
                    "action": s.recommended_action,
                }
                for s in self.state.scored_opportunities[:5]
            ],
            "grace_notes": self.state.grace_notes[-10:],
        }

    async def add_knowledge_request(
        self, topic: str, reason: str
    ) -> Dict[str, Any]:
        """Grace requests additional knowledge or documents.

        This is the "I need more knowledge, can you give me documents
        about X" mechanism described in the requirements.
        """
        note = (
            f"[{datetime.utcnow().isoformat()}] KNOWLEDGE REQUEST: "
            f"Topic: {topic}. Reason: {reason}."
        )
        self.state.grace_notes.append(note)

        return {
            "status": "knowledge_requested",
            "topic": topic,
            "reason": reason,
            "message": (
                f"Grace needs additional knowledge about '{topic}'. "
                f"Reason: {reason}. "
                "Please provide relevant documents, data, or configure "
                "additional data connectors for this domain."
            ),
        }
