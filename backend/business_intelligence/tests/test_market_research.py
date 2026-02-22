"""Tests for market research engine components."""

import pytest
from datetime import datetime

from business_intelligence.market_research.pain_point_engine import PainPointEngine, PainPointCluster
from business_intelligence.market_research.review_analyzer import ReviewAnalyzer
from business_intelligence.market_research.competitor_analyzer import CompetitorAnalyzer
from business_intelligence.models.data_models import (
    MarketDataPoint, PainPoint, CompetitorProduct, ReviewAnalysis,
    DataSource, Sentiment,
)


class TestPainPointEngine:
    def setup_method(self):
        self.engine = PainPointEngine(min_cluster_size=2)

    @pytest.mark.asyncio
    async def test_extract_from_frustration_text(self):
        data = [MarketDataPoint(
            source=DataSource.FORUM,
            category="forum_discussion",
            metric_name="reddit_post",
            metric_value=50,
            metadata={"title": "This product is so frustrating and annoying to use"},
        )]
        points = await self.engine.extract_pain_points(data)
        assert len(points) > 0
        assert points[0].severity > 0

    @pytest.mark.asyncio
    async def test_extract_from_failure_text(self):
        data = [MarketDataPoint(
            source=DataSource.FORUM,
            metadata={"title": "It broke after one week, completely stopped working"},
        )]
        points = await self.engine.extract_pain_points(data)
        assert len(points) > 0

    @pytest.mark.asyncio
    async def test_extract_from_waste_text(self):
        data = [MarketDataPoint(
            source=DataSource.REVIEW_SITE,
            metadata={"snippet": "Total waste of money, I want a refund immediately"},
        )]
        points = await self.engine.extract_pain_points(data)
        assert len(points) > 0

    @pytest.mark.asyncio
    async def test_no_pain_from_positive_text(self):
        data = [MarketDataPoint(
            source=DataSource.FORUM,
            metadata={"title": "Great product, love everything about it"},
        )]
        points = await self.engine.extract_pain_points(data)
        assert len(points) == 0

    @pytest.mark.asyncio
    async def test_cluster_pain_points(self):
        points = [
            PainPoint(category="frustration", description=f"frustrating issue {i}", severity=0.5, frequency=1)
            for i in range(5)
        ]
        clusters = await self.engine.cluster_pain_points(points)
        assert len(clusters) > 0
        assert clusters[0].total_frequency == 5

    @pytest.mark.asyncio
    async def test_cluster_min_size_enforced(self):
        engine = PainPointEngine(min_cluster_size=10)
        points = [PainPoint(category="test", description=f"issue {i}") for i in range(3)]
        clusters = await engine.cluster_pain_points(points)
        assert len(clusters) == 0

    @pytest.mark.asyncio
    async def test_rank_opportunities(self):
        clusters = [
            PainPointCluster(theme="high", avg_severity=0.9, total_frequency=20, solution_gap=0.8, pain_points=[], sources=["forum"]),
            PainPointCluster(theme="low", avg_severity=0.2, total_frequency=2, solution_gap=0.1, pain_points=[], sources=["forum"]),
        ]
        for c in clusters:
            c.composite_score = c.avg_severity * min(c.total_frequency / 10, 1.0) * (0.5 + c.solution_gap * 0.5)
        ranked = await self.engine.rank_opportunities(clusters)
        assert ranked[0]["theme"] == "high"
        assert ranked[0]["composite_score"] > ranked[1]["composite_score"]


class TestReviewAnalyzer:
    def setup_method(self):
        self.analyzer = ReviewAnalyzer()

    @pytest.mark.asyncio
    async def test_analyze_negative_reviews(self):
        reviews = [
            {"text": "Terrible product, broke after a week. Waste of money.", "rating": 1, "product_name": "Widget X"},
            {"text": "Overpriced and poor quality. Customer support is useless.", "rating": 2, "product_name": "Widget X"},
        ]
        intel = await self.analyzer.analyze_reviews(reviews, "Widget X")
        assert intel.total_reviews_analyzed == 2
        assert intel.avg_rating < 3.0
        assert len(intel.top_pain_points) > 0

    @pytest.mark.asyncio
    async def test_analyze_positive_reviews(self):
        reviews = [
            {"text": "Amazing product, love everything about it!", "rating": 5},
            {"text": "Best purchase I've ever made. Perfect quality.", "rating": 5},
        ]
        intel = await self.analyzer.analyze_reviews(reviews, "Good Widget")
        assert intel.avg_rating == 5.0
        assert "VERY_POSITIVE" in intel.sentiment_distribution

    @pytest.mark.asyncio
    async def test_feature_request_extraction(self):
        reviews = [
            {"text": "I wish it had better battery life. If only it could connect to bluetooth.", "rating": 3},
        ]
        intel = await self.analyzer.analyze_reviews(reviews)
        assert len(intel.feature_requests) > 0

    @pytest.mark.asyncio
    async def test_empty_reviews(self):
        intel = await self.analyzer.analyze_reviews([], "Empty")
        assert intel.total_reviews_analyzed == 0

    @pytest.mark.asyncio
    async def test_competitor_comparison(self):
        products = {
            "Product A": [{"text": "Terrible, broke immediately", "rating": 1}],
            "Product B": [{"text": "Pretty good but expensive", "rating": 4}],
        }
        comparison = await self.analyzer.compare_competitors(products)
        assert comparison["products_analyzed"] == 2
        assert "Product A" in comparison["products"]


class TestCompetitorAnalyzer:
    def setup_method(self):
        self.analyzer = CompetitorAnalyzer()

    @pytest.mark.asyncio
    async def test_analyze_empty_landscape(self):
        landscape = await self.analyzer.analyze_landscape("test niche", [])
        assert landscape.total_products == 0

    @pytest.mark.asyncio
    async def test_pricing_analysis(self):
        competitors = [
            CompetitorProduct(name="A", price=10.0, rating=4.0),
            CompetitorProduct(name="B", price=50.0, rating=3.5),
            CompetitorProduct(name="C", price=100.0, rating=4.5),
        ]
        landscape = await self.analyzer.analyze_landscape("test", competitors)
        assert landscape.avg_price > 0
        assert landscape.price_range["min"] == 10.0
        assert landscape.price_range["max"] == 100.0

    @pytest.mark.asyncio
    async def test_entry_difficulty_low(self):
        competitors = [CompetitorProduct(name="A", price=10.0, rating=2.0, review_count=5)]
        landscape = await self.analyzer.analyze_landscape("easy market", competitors)
        assert landscape.entry_difficulty < 0.5

    @pytest.mark.asyncio
    async def test_entry_difficulty_high(self):
        competitors = [
            CompetitorProduct(name=f"C{i}", price=50.0, rating=4.5, review_count=5000)
            for i in range(30)
        ]
        landscape = await self.analyzer.analyze_landscape("hard market", competitors)
        assert landscape.entry_difficulty > 0.5

    @pytest.mark.asyncio
    async def test_find_opportunities(self):
        competitors = [
            CompetitorProduct(name="Bad Product", price=50, rating=2.0, review_count=100),
        ]
        landscape = await self.analyzer.analyze_landscape("test", competitors)
        opps = await self.analyzer.find_opportunities(landscape)
        assert len(opps) > 0
