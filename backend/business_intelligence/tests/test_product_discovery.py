"""Tests for product discovery pipeline."""

import pytest

from business_intelligence.product_discovery.niche_finder import NicheFinder, GRACE_ADVANTAGE_DOMAINS
from business_intelligence.product_discovery.product_ideation import ProductIdeationEngine
from business_intelligence.models.data_models import (
    MarketDataPoint, PainPoint, MarketOpportunity, ProductType, DataSource,
)


class TestNicheFinder:
    def setup_method(self):
        self.finder = NicheFinder()

    @pytest.mark.asyncio
    async def test_find_niches_from_data(self):
        data = [
            MarketDataPoint(niche="ai tools", keywords=["ai"], metric_value=100, source=DataSource.SERPAPI),
            MarketDataPoint(niche="ai tools", keywords=["automation"], metric_value=50, source=DataSource.AMAZON),
        ]
        pain_points = [PainPoint(niche="ai tools", severity=0.7, frequency=5)]
        niches = await self.finder.find_niches(data, pain_points)
        assert len(niches) > 0
        assert niches[0].name == "ai tools"
        assert niches[0].overall_score > 0

    @pytest.mark.asyncio
    async def test_grace_advantage_ai(self):
        data = [MarketDataPoint(niche="artificial intelligence", keywords=["ai"], source=DataSource.SERPAPI)]
        niches = await self.finder.find_niches(data, [])
        assert niches[0].grace_advantage > 0.7

    @pytest.mark.asyncio
    async def test_grace_advantage_unknown(self):
        data = [MarketDataPoint(niche="exotic bird breeding", keywords=["parrots"], source=DataSource.SERPAPI)]
        niches = await self.finder.find_niches(data, [])
        assert niches[0].grace_advantage <= 0.3

    @pytest.mark.asyncio
    async def test_empty_data(self):
        niches = await self.finder.find_niches([], [])
        assert len(niches) == 0

    @pytest.mark.asyncio
    async def test_recommends_product_types(self):
        data = [MarketDataPoint(niche="coding", keywords=["python"], source=DataSource.SERPAPI)]
        pain_points = [PainPoint(niche="coding", severity=0.8)]
        niches = await self.finder.find_niches(data, pain_points)
        assert len(niches[0].recommended_products) > 0

    def test_grace_domains_populated(self):
        assert len(GRACE_ADVANTAGE_DOMAINS) > 10
        assert "ai" in GRACE_ADVANTAGE_DOMAINS
        assert "trading" in GRACE_ADVANTAGE_DOMAINS


class TestProductIdeation:
    def setup_method(self):
        self.engine = ProductIdeationEngine()

    @pytest.mark.asyncio
    async def test_generate_concepts(self):
        opps = [
            MarketOpportunity(
                title="AI Automation Gap",
                niche="ai automation",
                pain_points=[PainPoint(description="manual processes", severity=0.8)],
                opportunity_score=0.7,
                recommended_product_types=[ProductType.SAAS],
            ),
        ]
        concepts = await self.engine.generate_concepts(opps, max_concepts=3)
        assert len(concepts) > 0
        assert concepts[0].name != ""
        assert concepts[0].estimated_price > 0
        assert len(concepts[0].key_features) > 0

    @pytest.mark.asyncio
    async def test_product_ladder(self):
        opp = MarketOpportunity(
            title="Test",
            niche="test niche",
            pain_points=[PainPoint(description="problem")],
        )
        ladder = await self.engine.generate_product_ladder("test niche", opp)
        assert len(ladder) == 4
        assert ladder[0].estimated_price == 0.0  # free lead magnet
        assert ladder[1].product_type == ProductType.ONLINE_COURSE
        assert ladder[2].product_type == ProductType.SAAS
        assert ladder[3].product_type == ProductType.COMMUNITY_MEMBERSHIP

    @pytest.mark.asyncio
    async def test_concept_includes_pain_features(self):
        opp = MarketOpportunity(
            title="Test",
            niche="test",
            pain_points=[
                PainPoint(description="slow loading times", category="slow"),
                PainPoint(description="crashes frequently", category="failure"),
            ],
            recommended_product_types=[ProductType.SAAS],
        )
        concepts = await self.engine.generate_concepts([opp])
        features = " ".join(concepts[0].key_features).lower()
        assert "slow" in features or "crash" in features or "address" in features

    @pytest.mark.asyncio
    async def test_refine_concept(self):
        concept = (await self.engine.generate_concepts([
            MarketOpportunity(title="T", niche="t", pain_points=[PainPoint(description="p")],
                              recommended_product_types=[ProductType.EBOOK_PDF])
        ]))[0]
        refined = await self.engine.refine_concept(
            concept,
            additional_pain_points=[PainPoint(description="new problem")],
            competitor_weaknesses=["bad support"],
        )
        assert refined.validation_status == "refined"
        assert len(refined.competitive_advantages) > len(concept.competitive_advantages) - 1
