"""
Opportunity Scorer

Takes all intelligence signals (pain points, trends, competition,
customer data) and produces a single composite score for each
market opportunity. This is the decision engine that tells Grace
where to focus.

Scoring dimensions:
1. Pain severity (how badly do people need this?)
2. Market size (how many people need it?)
3. Competition gap (how poorly is it currently served?)
4. Trend momentum (is demand growing?)
5. Entry feasibility (can we actually build this?)
6. Revenue potential (can we make money?)
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from business_intelligence.models.data_models import (
    MarketOpportunity,
    PainPoint,
    CompetitorProduct,
    ProductType,
    OpportunityType,
)
from business_intelligence.synthesis.trend_detector import TrendSignal

logger = logging.getLogger(__name__)


@dataclass
class ScoringWeights:
    """Configurable weights for opportunity scoring dimensions."""
    pain_severity: float = 0.25
    market_size: float = 0.15
    competition_gap: float = 0.20
    trend_momentum: float = 0.15
    entry_feasibility: float = 0.15
    revenue_potential: float = 0.10

    def validate(self):
        total = (
            self.pain_severity + self.market_size + self.competition_gap +
            self.trend_momentum + self.entry_feasibility + self.revenue_potential
        )
        assert abs(total - 1.0) < 0.01, f"Weights must sum to 1.0, got {total}"


@dataclass
class ScoredOpportunity:
    """An opportunity with a detailed scoring breakdown."""
    opportunity: MarketOpportunity
    total_score: float = 0.0
    pain_score: float = 0.0
    market_score: float = 0.0
    competition_score: float = 0.0
    trend_score: float = 0.0
    feasibility_score: float = 0.0
    revenue_score: float = 0.0
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    verdict: str = ""
    recommended_action: str = ""
    estimated_time_to_validate: str = ""


class OpportunityScorer:
    """Scores and ranks market opportunities."""

    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()
        self.weights.validate()

    async def score_opportunities(
        self,
        opportunities: List[MarketOpportunity],
        trends: Optional[List[TrendSignal]] = None,
        market_data_volume: int = 0,
    ) -> List[ScoredOpportunity]:
        """Score all opportunities and return them ranked."""
        scored = []

        for opp in opportunities:
            trend_for_opp = self._find_matching_trend(opp, trends or [])
            s = self._score_single(opp, trend_for_opp, market_data_volume)
            scored.append(s)

        scored.sort(key=lambda s: s.total_score, reverse=True)

        for idx, s in enumerate(scored):
            s.verdict = self._generate_verdict(s, idx + 1, len(scored))
            s.recommended_action = self._recommend_action(s)
            s.estimated_time_to_validate = self._estimate_validation_time(s)

        return scored

    def _score_single(
        self,
        opp: MarketOpportunity,
        trend: Optional[TrendSignal],
        data_volume: int,
    ) -> ScoredOpportunity:
        """Score a single opportunity across all dimensions."""
        pain = self._score_pain(opp)
        market = self._score_market_size(opp, data_volume)
        competition = self._score_competition(opp)
        trend_score = self._score_trend(trend)
        feasibility = self._score_feasibility(opp)
        revenue = self._score_revenue(opp)

        total = (
            pain * self.weights.pain_severity +
            market * self.weights.market_size +
            competition * self.weights.competition_gap +
            trend_score * self.weights.trend_momentum +
            feasibility * self.weights.entry_feasibility +
            revenue * self.weights.revenue_potential
        )

        return ScoredOpportunity(
            opportunity=opp,
            total_score=round(total, 4),
            pain_score=round(pain, 3),
            market_score=round(market, 3),
            competition_score=round(competition, 3),
            trend_score=round(trend_score, 3),
            feasibility_score=round(feasibility, 3),
            revenue_score=round(revenue, 3),
            score_breakdown={
                "pain_severity": round(pain * self.weights.pain_severity, 4),
                "market_size": round(market * self.weights.market_size, 4),
                "competition_gap": round(competition * self.weights.competition_gap, 4),
                "trend_momentum": round(trend_score * self.weights.trend_momentum, 4),
                "entry_feasibility": round(feasibility * self.weights.entry_feasibility, 4),
                "revenue_potential": round(revenue * self.weights.revenue_potential, 4),
            },
        )

    def _score_pain(self, opp: MarketOpportunity) -> float:
        if not opp.pain_points:
            return 0.3
        avg_pain = sum(p.pain_score for p in opp.pain_points) / len(opp.pain_points)
        frequency_bonus = min(
            sum(p.frequency for p in opp.pain_points) / 50, 0.3
        )
        return min(avg_pain + frequency_bonus, 1.0)

    def _score_market_size(
        self, opp: MarketOpportunity, data_volume: int
    ) -> float:
        if opp.estimated_market_size > 0:
            if opp.estimated_market_size > 1_000_000:
                return 0.9
            elif opp.estimated_market_size > 100_000:
                return 0.7
            elif opp.estimated_market_size > 10_000:
                return 0.5
            else:
                return 0.3

        if data_volume > 200:
            return 0.5
        elif data_volume > 50:
            return 0.4
        return 0.3

    def _score_competition(self, opp: MarketOpportunity) -> float:
        if not opp.competitors:
            return 0.7  # no visible competition is often good

        num = len(opp.competitors)
        avg_rating = sum(c.rating for c in opp.competitors if c.rating > 0)
        avg_rating = avg_rating / max(sum(1 for c in opp.competitors if c.rating > 0), 1)

        score = 0.5
        if num < 5:
            score += 0.2
        elif num > 20:
            score -= 0.2

        if avg_rating < 3.5:
            score += 0.2
        elif avg_rating > 4.5:
            score -= 0.15

        solution_gaps = sum(len(p.solution_gaps) for p in opp.pain_points)
        if solution_gaps > 3:
            score += 0.15

        return max(0.0, min(score, 1.0))

    def _score_trend(self, trend: Optional[TrendSignal]) -> float:
        if not trend:
            return 0.5

        base = 0.5

        if trend.direction == "rising":
            base += trend.strength * 0.4
        elif trend.direction == "declining":
            base -= trend.strength * 0.3
        elif trend.direction == "volatile":
            base -= 0.1

        if trend.inflection_detected:
            base -= 0.1

        return max(0.0, min(base, 1.0))

    def _score_feasibility(self, opp: MarketOpportunity) -> float:
        score = 0.7

        barriers = len(opp.entry_barriers)
        score -= min(barriers * 0.1, 0.4)

        if opp.time_to_market_days > 0:
            if opp.time_to_market_days > 180:
                score -= 0.2
            elif opp.time_to_market_days > 90:
                score -= 0.1

        if opp.estimated_initial_investment > 0:
            if opp.estimated_initial_investment > 10_000:
                score -= 0.15
            elif opp.estimated_initial_investment > 5_000:
                score -= 0.1

        easy_types = {
            ProductType.ONLINE_COURSE, ProductType.EBOOK_PDF,
            ProductType.TEMPLATE_TOOLKIT, ProductType.AI_AUTOMATION,
        }
        if opp.recommended_product_types:
            if any(pt in easy_types for pt in opp.recommended_product_types):
                score += 0.1

        return max(0.0, min(score, 1.0))

    def _score_revenue(self, opp: MarketOpportunity) -> float:
        score = 0.5

        recurring_types = {ProductType.SAAS, ProductType.COMMUNITY_MEMBERSHIP}
        if opp.recommended_product_types:
            if any(pt in recurring_types for pt in opp.recommended_product_types):
                score += 0.2

        if opp.estimated_market_size > 100_000:
            score += 0.15
        elif opp.estimated_market_size > 10_000:
            score += 0.1

        if opp.pain_points:
            avg_severity = sum(p.severity for p in opp.pain_points) / len(opp.pain_points)
            if avg_severity > 0.7:
                score += 0.15

        return max(0.0, min(score, 1.0))

    def _find_matching_trend(
        self, opp: MarketOpportunity, trends: List[TrendSignal]
    ) -> Optional[TrendSignal]:
        niche_lower = opp.niche.lower()
        for trend in trends:
            if trend.keyword.lower() in niche_lower or niche_lower in trend.keyword.lower():
                return trend
            if trend.niche and trend.niche.lower() == niche_lower:
                return trend
        return None

    def _generate_verdict(
        self, scored: ScoredOpportunity, rank: int, total: int
    ) -> str:
        score = scored.total_score

        if score >= 0.75:
            tier = "STRONG OPPORTUNITY"
        elif score >= 0.55:
            tier = "WORTH INVESTIGATING"
        elif score >= 0.35:
            tier = "MARGINAL"
        else:
            tier = "WEAK"

        factors = []
        if scored.pain_score > 0.7:
            factors.append("high pain severity")
        if scored.competition_score > 0.7:
            factors.append("low competition")
        if scored.trend_score > 0.7:
            factors.append("strong upward trend")
        if scored.feasibility_score > 0.7:
            factors.append("easy to build")

        concerns = []
        if scored.pain_score < 0.3:
            concerns.append("weak pain signal")
        if scored.competition_score < 0.3:
            concerns.append("heavy competition")
        if scored.trend_score < 0.3:
            concerns.append("declining demand")

        verdict = f"[{tier}] Ranked #{rank}/{total} (score: {score:.2f}). "
        if factors:
            verdict += f"Strengths: {', '.join(factors)}. "
        if concerns:
            verdict += f"Concerns: {', '.join(concerns)}."

        return verdict

    def _recommend_action(self, scored: ScoredOpportunity) -> str:
        if scored.total_score >= 0.75:
            return (
                "Proceed to validation: build a landing page, run a small ad campaign "
                "(budget: ~100-200 GBP), collect waitlist signups. "
                "Target: 500+ signups to confirm demand."
            )
        elif scored.total_score >= 0.55:
            return (
                "Conduct deeper research: analyze top 5 competitor reviews in detail, "
                "run SerpAPI trends analysis for related keywords, validate with a "
                "micro-test (50 GBP ad spend)."
            )
        elif scored.total_score >= 0.35:
            return (
                "Park and monitor: add keywords to tracking, set up trend alerts, "
                "revisit in 30 days with more data."
            )
        else:
            return "Deprioritize. Focus resources on higher-scoring opportunities."

    def _estimate_validation_time(self, scored: ScoredOpportunity) -> str:
        if scored.feasibility_score > 0.7:
            return "1-2 weeks for landing page + ad test"
        elif scored.feasibility_score > 0.5:
            return "2-4 weeks for research + validation"
        else:
            return "4-8 weeks (complex build or high barriers)"
