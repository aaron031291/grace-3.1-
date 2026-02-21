"""Tests for BI data models."""

import pytest
from datetime import datetime

from business_intelligence.models.data_models import (
    MarketDataPoint, PainPoint, CompetitorProduct, MarketOpportunity,
    CustomerArchetype, CampaignResult, WaitlistEntry, ProductConcept,
    IntelligenceSnapshot, ReviewAnalysis, KeywordMetric, TrafficSource,
    DataSource, Sentiment, OpportunityType, ProductType,
)


class TestMarketDataPoint:
    def test_defaults(self):
        dp = MarketDataPoint()
        assert dp.source == DataSource.MANUAL
        assert dp.confidence == 1.0
        assert dp.id is not None
        assert isinstance(dp.timestamp, datetime)

    def test_with_data(self):
        dp = MarketDataPoint(
            source=DataSource.AMAZON,
            category="product",
            metric_name="price",
            metric_value=29.99,
            unit="GBP",
            niche="ai tools",
            keywords=["ai", "automation"],
        )
        assert dp.metric_value == 29.99
        assert dp.niche == "ai tools"
        assert len(dp.keywords) == 2


class TestPainPoint:
    def test_pain_score_calculation(self):
        pp = PainPoint(severity=0.8, frequency=10)
        assert pp.pain_score == 0.8 * 1.0  # min(10/10, 1.0) = 1.0

    def test_pain_score_low_frequency(self):
        pp = PainPoint(severity=0.5, frequency=3)
        assert pp.pain_score == 0.5 * 0.3  # min(3/10, 1.0) = 0.3

    def test_pain_score_zero_severity(self):
        pp = PainPoint(severity=0.0, frequency=100)
        assert pp.pain_score == 0.0


class TestCompetitorProduct:
    def test_defaults(self):
        cp = CompetitorProduct(name="Test Product", price=49.99)
        assert cp.currency == "GBP"
        assert cp.rating == 0.0
        assert cp.features == []


class TestMarketOpportunity:
    def test_viability_score_no_pain_points(self):
        opp = MarketOpportunity()
        assert opp.viability_score == 0.0

    def test_viability_score_with_pain_points(self):
        opp = MarketOpportunity(
            pain_points=[PainPoint(severity=0.8, frequency=10)],
            confidence_score=0.7,
            opportunity_score=0.6,
        )
        score = opp.viability_score
        assert 0.0 < score <= 1.0

    def test_viability_score_barrier_penalty(self):
        opp_no_barriers = MarketOpportunity(
            pain_points=[PainPoint(severity=0.8, frequency=10)],
            confidence_score=0.7,
            opportunity_score=0.6,
        )
        opp_with_barriers = MarketOpportunity(
            pain_points=[PainPoint(severity=0.8, frequency=10)],
            confidence_score=0.7,
            opportunity_score=0.6,
            entry_barriers=["high capital", "regulation", "patents"],
        )
        assert opp_no_barriers.viability_score > opp_with_barriers.viability_score


class TestCampaignResult:
    def test_roi_indicator(self):
        cr = CampaignResult(ad_spend=100.0, signups=50)
        assert cr.roi_indicator == 0.5

    def test_roi_indicator_zero_spend(self):
        cr = CampaignResult(ad_spend=0.0, signups=50)
        assert cr.roi_indicator == 0.0


class TestWaitlistEntry:
    def test_consent_required(self):
        entry = WaitlistEntry(email="test@example.com", consent_given=False)
        assert not entry.consent_given

    def test_with_consent(self):
        entry = WaitlistEntry(
            email="test@example.com",
            consent_given=True,
            consent_timestamp=datetime.utcnow(),
        )
        assert entry.consent_given
        assert entry.consent_timestamp is not None


class TestProductConcept:
    def test_product_types(self):
        for pt in ProductType:
            concept = ProductConcept(product_type=pt)
            assert concept.product_type == pt


class TestSentiment:
    def test_ordering(self):
        assert Sentiment.VERY_NEGATIVE.value < Sentiment.NEGATIVE.value
        assert Sentiment.NEGATIVE.value < Sentiment.NEUTRAL.value
        assert Sentiment.NEUTRAL.value < Sentiment.POSITIVE.value
        assert Sentiment.POSITIVE.value < Sentiment.VERY_POSITIVE.value
