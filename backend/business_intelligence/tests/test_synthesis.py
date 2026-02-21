"""Tests for intelligence synthesis engine components."""

import pytest
from datetime import datetime, timedelta

from business_intelligence.synthesis.trend_detector import TrendDetector, TrendSignal
from business_intelligence.synthesis.opportunity_scorer import OpportunityScorer, ScoringWeights
from business_intelligence.models.data_models import (
    MarketDataPoint, MarketOpportunity, PainPoint, CompetitorProduct,
    ProductType, DataSource, KeywordMetric,
)


class TestTrendDetector:
    def setup_method(self):
        self.detector = TrendDetector(min_data_points=3)

    @pytest.mark.asyncio
    async def test_detect_rising_trend(self):
        now = datetime.utcnow()
        points = [
            MarketDataPoint(
                metric_value=float(i * 10 + 10),
                keywords=["rising"],
                timestamp=now - timedelta(days=10 - i),
            )
            for i in range(10)
        ]
        signals = await self.detector.detect_trends(points, ["rising"])
        assert len(signals) > 0
        assert signals[0].direction == "rising"

    @pytest.mark.asyncio
    async def test_detect_declining_trend(self):
        now = datetime.utcnow()
        points = [
            MarketDataPoint(
                metric_value=float(100 - i * 10),
                keywords=["declining"],
                timestamp=now - timedelta(days=10 - i),
            )
            for i in range(10)
        ]
        signals = await self.detector.detect_trends(points, ["declining"])
        assert len(signals) > 0
        assert signals[0].direction == "declining"

    @pytest.mark.asyncio
    async def test_detect_stable_trend(self):
        now = datetime.utcnow()
        points = [
            MarketDataPoint(
                metric_value=50.0,
                keywords=["stable"],
                timestamp=now - timedelta(days=10 - i),
            )
            for i in range(10)
        ]
        signals = await self.detector.detect_trends(points, ["stable"])
        assert len(signals) > 0
        assert signals[0].direction == "stable"

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        points = [
            MarketDataPoint(metric_value=10.0, keywords=["few"]),
        ]
        signals = await self.detector.detect_trends(points, ["few"])
        assert len(signals) == 0

    @pytest.mark.asyncio
    async def test_from_keyword_metrics(self):
        metrics = [
            KeywordMetric(keyword="test", trend_direction="rising", trend_percentage=30.0),
            KeywordMetric(keyword="declining", trend_direction="declining", trend_percentage=-25.0),
        ]
        signals = await self.detector.detect_from_keyword_metrics(metrics)
        assert len(signals) == 2
        assert signals[0].keyword == "test"


class TestOpportunityScorer:
    def setup_method(self):
        self.scorer = OpportunityScorer()

    @pytest.mark.asyncio
    async def test_score_empty_opportunities(self):
        scored = await self.scorer.score_opportunities([])
        assert len(scored) == 0

    @pytest.mark.asyncio
    async def test_score_single_opportunity(self):
        opp = MarketOpportunity(
            title="Test Opp",
            niche="test",
            pain_points=[PainPoint(severity=0.8, frequency=10)],
            opportunity_score=0.7,
            confidence_score=0.6,
        )
        scored = await self.scorer.score_opportunities([opp])
        assert len(scored) == 1
        assert scored[0].total_score > 0
        assert scored[0].verdict != ""
        assert scored[0].recommended_action != ""

    @pytest.mark.asyncio
    async def test_scoring_ranks_correctly(self):
        strong = MarketOpportunity(
            title="Strong",
            pain_points=[PainPoint(severity=0.9, frequency=20)],
            opportunity_score=0.8,
            confidence_score=0.8,
        )
        weak = MarketOpportunity(
            title="Weak",
            pain_points=[PainPoint(severity=0.2, frequency=1)],
            opportunity_score=0.2,
            confidence_score=0.2,
        )
        scored = await self.scorer.score_opportunities([weak, strong])
        assert scored[0].opportunity.title == "Strong"
        assert scored[0].total_score > scored[1].total_score

    @pytest.mark.asyncio
    async def test_trend_affects_score(self):
        opp = MarketOpportunity(
            title="Trending",
            niche="trending_niche",
            pain_points=[PainPoint(severity=0.5, frequency=5)],
        )
        rising = TrendSignal(keyword="trending_niche", niche="trending_niche", direction="rising", strength=0.8)
        declining = TrendSignal(keyword="trending_niche", niche="trending_niche", direction="declining", strength=0.8)

        scored_rising = await self.scorer.score_opportunities([opp], trends=[rising])
        scored_declining = await self.scorer.score_opportunities([opp], trends=[declining])

        assert scored_rising[0].trend_score > scored_declining[0].trend_score

    def test_weights_validate(self):
        weights = ScoringWeights()
        weights.validate()

    def test_weights_invalid(self):
        weights = ScoringWeights(pain_severity=0.5, market_size=0.5)
        with pytest.raises(AssertionError):
            weights.validate()


class TestScoringDimensions:
    def setup_method(self):
        self.scorer = OpportunityScorer()

    @pytest.mark.asyncio
    async def test_feasibility_easy_product(self):
        opp = MarketOpportunity(
            title="Easy",
            pain_points=[PainPoint(severity=0.5, frequency=5)],
            recommended_product_types=[ProductType.EBOOK_PDF],
        )
        scored = await self.scorer.score_opportunities([opp])
        assert scored[0].feasibility_score > 0.5

    @pytest.mark.asyncio
    async def test_feasibility_hard_product(self):
        opp = MarketOpportunity(
            title="Hard",
            pain_points=[PainPoint(severity=0.5, frequency=5)],
            entry_barriers=["regulation", "high capital", "patents", "expertise"],
            time_to_market_days=365,
            estimated_initial_investment=50000,
        )
        scored = await self.scorer.score_opportunities([opp])
        assert scored[0].feasibility_score < 0.5

    @pytest.mark.asyncio
    async def test_revenue_recurring_bonus(self):
        recurring = MarketOpportunity(
            title="SaaS",
            pain_points=[PainPoint(severity=0.5)],
            recommended_product_types=[ProductType.SAAS],
        )
        one_time = MarketOpportunity(
            title="PDF",
            pain_points=[PainPoint(severity=0.5)],
            recommended_product_types=[ProductType.EBOOK_PDF],
        )
        scored = await self.scorer.score_opportunities([recurring, one_time])
        saas = next(s for s in scored if s.opportunity.title == "SaaS")
        pdf = next(s for s in scored if s.opportunity.title == "PDF")
        assert saas.revenue_score > pdf.revenue_score
