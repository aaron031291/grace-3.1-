"""
Market Research Orchestrator

Coordinates the full market research pipeline:
1. Collect raw data from all connectors
2. Extract and cluster pain points
3. Analyze competitors
4. Analyze reviews
5. Score and rank opportunities
6. Generate actionable research report

This is what Grace runs when she says "I need to research this market".
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from business_intelligence.connectors.base import ConnectorRegistry
from business_intelligence.market_research.pain_point_engine import PainPointEngine
from business_intelligence.market_research.review_analyzer import ReviewAnalyzer
from business_intelligence.market_research.competitor_analyzer import CompetitorAnalyzer
from business_intelligence.models.data_models import (
    MarketDataPoint,
    PainPoint,
    CompetitorProduct,
    MarketOpportunity,
    ReviewAnalysis,
    DataSource,
)

logger = logging.getLogger(__name__)


@dataclass
class ResearchReport:
    """Complete market research report for a niche."""
    niche: str = ""
    keywords: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    status: str = "pending"

    # Data collection
    total_data_points: int = 0
    data_sources_used: List[str] = field(default_factory=list)
    connectors_failed: List[str] = field(default_factory=list)

    # Pain points
    pain_points: List[PainPoint] = field(default_factory=list)
    pain_point_clusters: List[Dict] = field(default_factory=list)

    # Competition
    competitors_found: int = 0
    competitor_landscape: Optional[Dict] = None

    # Reviews
    reviews_analyzed: int = 0
    review_intelligence: Optional[Dict] = None

    # Opportunities
    opportunities: List[MarketOpportunity] = field(default_factory=list)
    top_opportunity: Optional[MarketOpportunity] = None

    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    next_actions: List[str] = field(default_factory=list)

    # Grace's assessment
    grace_confidence: float = 0.0
    grace_summary: str = ""
    grace_concerns: List[str] = field(default_factory=list)


class MarketResearchOrchestrator:
    """Orchestrates the full market research pipeline."""

    def __init__(self):
        self.pain_point_engine = PainPointEngine()
        self.review_analyzer = ReviewAnalyzer()
        self.competitor_analyzer = CompetitorAnalyzer()

    async def run_research(
        self,
        niche: str,
        keywords: List[str],
        depth: str = "standard",
    ) -> ResearchReport:
        """Execute a complete market research cycle.

        Args:
            niche: The market niche to research
            keywords: Search keywords for data collection
            depth: "quick" (1 pass), "standard" (multi-source), "deep" (exhaustive)
        """
        report = ResearchReport(niche=niche, keywords=keywords, status="running")
        logger.info(f"Starting {depth} market research for niche: {niche}")

        # Phase 1: Collect data from all available connectors
        all_data = await self._collect_data(report, keywords, niche)

        # Phase 2: Extract and cluster pain points
        await self._analyze_pain_points(report, all_data, niche)

        # Phase 3: Analyze competitors
        await self._analyze_competitors(report, all_data, niche, keywords)

        # Phase 4: Score opportunities
        await self._score_opportunities(report)

        # Phase 5: Generate recommendations
        self._generate_recommendations(report)

        # Phase 6: Grace's assessment
        self._grace_assessment(report)

        report.status = "completed"
        logger.info(
            f"Research complete for '{niche}': {report.total_data_points} data points, "
            f"{len(report.pain_points)} pain points, "
            f"{len(report.opportunities)} opportunities identified"
        )

        return report

    async def _collect_data(
        self,
        report: ResearchReport,
        keywords: List[str],
        niche: str,
    ) -> List[MarketDataPoint]:
        """Collect data from all available connectors."""
        all_data = await ConnectorRegistry.collect_all(
            keywords=keywords, niche=niche
        )

        report.total_data_points = len(all_data)

        sources_used = set()
        for dp in all_data:
            if dp.confidence > 0:
                sources_used.add(dp.source.value)

        report.data_sources_used = list(sources_used)

        health = ConnectorRegistry.health_report()
        report.connectors_failed = [
            name for name, h in health.items()
            if h.get("status") in ("error", "disabled")
        ]

        return all_data

    async def _analyze_pain_points(
        self,
        report: ResearchReport,
        data: List[MarketDataPoint],
        niche: str,
    ):
        """Extract and cluster pain points from collected data."""
        pain_points = await self.pain_point_engine.extract_pain_points(
            data_points=data, niche=niche
        )

        report.pain_points = pain_points

        clusters = await self.pain_point_engine.cluster_pain_points(pain_points)
        ranked = await self.pain_point_engine.rank_opportunities(clusters)
        report.pain_point_clusters = ranked

    async def _analyze_competitors(
        self,
        report: ResearchReport,
        data: List[MarketDataPoint],
        niche: str,
        keywords: List[str],
    ):
        """Analyze competitive landscape."""
        competitor_data = [
            dp for dp in data
            if dp.category in ("competitor_product", "shopping", "product_listing")
        ]

        competitors = []
        for dp in competitor_data:
            meta = dp.metadata
            comp = CompetitorProduct(
                name=meta.get("product_name", meta.get("title", "")),
                platform=dp.source.value,
                url=meta.get("url", meta.get("link", "")),
                price=meta.get("price", dp.metric_value) if dp.unit in ("GBP", "USD") else 0.0,
                rating=meta.get("rating", dp.metric_value) if dp.unit == "rating" else 0.0,
                review_count=int(meta.get("review_count", meta.get("reviews", 0)) or 0),
                category=niche,
            )
            if comp.name:
                competitors.append(comp)

        report.competitors_found = len(competitors)

        if competitors:
            landscape = await self.competitor_analyzer.analyze_landscape(
                niche=niche,
                competitors=competitors,
                market_data=data,
            )

            report.competitor_landscape = {
                "total_products": landscape.total_products,
                "avg_price": landscape.avg_price,
                "price_range": landscape.price_range,
                "avg_rating": landscape.avg_rating,
                "entry_difficulty": landscape.entry_difficulty,
                "pricing_gaps": landscape.pricing_gaps,
                "feature_gaps": landscape.feature_gaps[:5],
                "underserved_segments": landscape.underserved_segments,
                "recommendations": landscape.recommendations,
            }

            opp_from_landscape = await self.competitor_analyzer.find_opportunities(
                landscape, report.pain_points
            )
            report.opportunities.extend(opp_from_landscape)

    async def _score_opportunities(self, report: ResearchReport):
        """Score and rank all identified opportunities."""
        for opp in report.opportunities:
            data_quality_bonus = min(report.total_data_points / 100, 0.2)
            pain_point_bonus = min(len(report.pain_points) / 20, 0.2)
            opp.opportunity_score = min(
                opp.opportunity_score + data_quality_bonus + pain_point_bonus,
                1.0,
            )
            opp.confidence_score = min(
                opp.confidence_score + data_quality_bonus,
                1.0,
            )

        report.opportunities.sort(
            key=lambda o: o.opportunity_score, reverse=True
        )

        if report.opportunities:
            report.top_opportunity = report.opportunities[0]

    def _generate_recommendations(self, report: ResearchReport):
        """Generate actionable next steps."""
        recs = []

        if report.total_data_points < 50:
            recs.append(
                "PRIORITY: More data needed. Configure additional connectors "
                f"(currently using {len(report.data_sources_used)} sources). "
                "Minimum 100 data points recommended for reliable analysis."
            )
            report.next_actions.append("Configure missing API connectors")

        if report.connectors_failed:
            recs.append(
                f"WARNING: {len(report.connectors_failed)} connectors unavailable: "
                f"{', '.join(report.connectors_failed)}. "
                "Research is based on incomplete data."
            )

        if report.pain_point_clusters:
            top_cluster = report.pain_point_clusters[0]
            recs.append(
                f"TOP PAIN POINT: '{top_cluster['theme']}' with score "
                f"{top_cluster['composite_score']:.2f}. "
                f"Mentioned {top_cluster['total_mentions']}x across "
                f"{len(top_cluster['sources'])} sources."
            )

        if report.top_opportunity:
            opp = report.top_opportunity
            recs.append(
                f"TOP OPPORTUNITY: {opp.title} "
                f"(score: {opp.opportunity_score:.2f}, confidence: {opp.confidence_score:.2f})"
            )
            report.next_actions.append(
                f"Validate demand for: {opp.title} -- run a small ad test"
            )

        if report.competitors_found > 0:
            landscape = report.competitor_landscape or {}
            if landscape.get("entry_difficulty", 0) < 0.3:
                recs.append(
                    "Market entry looks feasible. Low competitive barriers detected."
                )
            elif landscape.get("entry_difficulty", 0) > 0.7:
                recs.append(
                    "High competitive barriers. Consider a niche-within-niche strategy "
                    "or unique differentiation angle."
                )

        report.recommendations = recs

        if report.pain_points and not report.next_actions:
            report.next_actions = [
                "Run validation campaign on top opportunity",
                "Deep-dive reviews on top 3 competitors",
                "Build landing page for waitlist collection",
            ]

    def _grace_assessment(self, report: ResearchReport):
        """Grace's self-assessment of research quality and confidence."""
        confidence = 0.0
        concerns = []

        if report.total_data_points >= 100:
            confidence += 0.3
        elif report.total_data_points >= 50:
            confidence += 0.2
        elif report.total_data_points >= 10:
            confidence += 0.1
        else:
            concerns.append("Very limited data. Conclusions are speculative.")

        if len(report.data_sources_used) >= 3:
            confidence += 0.2
        elif len(report.data_sources_used) >= 2:
            confidence += 0.1
        else:
            concerns.append("Single data source. Cross-validation not possible.")

        if report.pain_points:
            confidence += 0.15
            if len(report.pain_points) >= 10:
                confidence += 0.1
        else:
            concerns.append("No pain points found. Either the niche is too broad or data is insufficient.")

        if report.competitors_found >= 5:
            confidence += 0.15
        elif report.competitors_found >= 2:
            confidence += 0.1
        else:
            concerns.append("Few competitors found. Market may be too niche or data collection insufficient.")

        if report.opportunities:
            confidence += 0.1

        report.grace_confidence = min(confidence, 1.0)
        report.grace_concerns = concerns

        confidence_label = "low"
        if report.grace_confidence > 0.7:
            confidence_label = "high"
        elif report.grace_confidence > 0.4:
            confidence_label = "moderate"

        report.grace_summary = (
            f"Research complete for '{report.niche}' with {confidence_label} confidence "
            f"({report.grace_confidence:.0%}). "
            f"Analyzed {report.total_data_points} data points from "
            f"{len(report.data_sources_used)} sources. "
            f"Found {len(report.pain_points)} pain points and "
            f"{len(report.opportunities)} opportunities. "
        )

        if concerns:
            report.grace_summary += f"Concerns: {'; '.join(concerns)}"
        elif report.top_opportunity:
            report.grace_summary += (
                f"Top opportunity: {report.top_opportunity.title} "
                f"(score: {report.top_opportunity.opportunity_score:.2f}). "
                "Ready for validation phase."
            )

    async def quick_scan(
        self,
        niche: str,
        keywords: List[str],
    ) -> Dict[str, Any]:
        """Run a lightweight scan -- faster but less thorough."""
        report = await self.run_research(niche, keywords, depth="quick")
        return {
            "niche": report.niche,
            "data_points": report.total_data_points,
            "pain_points": len(report.pain_points),
            "competitors": report.competitors_found,
            "opportunities": len(report.opportunities),
            "top_opportunity": (
                {
                    "title": report.top_opportunity.title,
                    "score": report.top_opportunity.opportunity_score,
                }
                if report.top_opportunity
                else None
            ),
            "confidence": report.grace_confidence,
            "summary": report.grace_summary,
            "next_actions": report.next_actions,
        }
