"""Tests for customer intelligence module."""

import pytest
from datetime import datetime

from business_intelligence.customer_intelligence.archetype_engine import ArchetypeEngine
from business_intelligence.customer_intelligence.pattern_analyzer import CrossPatternAnalyzer
from business_intelligence.models.data_models import (
    WaitlistEntry, CampaignResult, MarketOpportunity, PainPoint, CustomerArchetype,
)


class TestArchetypeEngine:
    def setup_method(self):
        self.engine = ArchetypeEngine(min_cluster_size=3)

    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        entries = [WaitlistEntry(email="a@t.com", consent_given=True)]
        archetypes = await self.engine.build_archetypes(entries)
        assert len(archetypes) == 0

    @pytest.mark.asyncio
    async def test_builds_archetypes(self):
        entries = [
            WaitlistEntry(
                email=f"u{i}@t.com",
                consent_given=True,
                interests=["ai", "automation"],
                source_platform="facebook",
            )
            for i in range(10)
        ]
        archetypes = await self.engine.build_archetypes(entries)
        assert len(archetypes) > 0
        assert archetypes[0].sample_size >= 3
        assert archetypes[0].consent_verified

    @pytest.mark.asyncio
    async def test_excludes_opted_out(self):
        entries = [
            WaitlistEntry(email=f"u{i}@t.com", consent_given=True, opted_out=True, interests=["x"])
            for i in range(10)
        ]
        archetypes = await self.engine.build_archetypes(entries)
        assert len(archetypes) == 0

    @pytest.mark.asyncio
    async def test_multiple_archetypes(self):
        group_a = [
            WaitlistEntry(email=f"a{i}@t.com", consent_given=True, interests=["marketing"])
            for i in range(12)
        ]
        group_b = [
            WaitlistEntry(email=f"b{i}@t.com", consent_given=True, interests=["coding"])
            for i in range(12)
        ]
        archetypes = await self.engine.build_archetypes(group_a + group_b)
        assert len(archetypes) == 2

    @pytest.mark.asyncio
    async def test_targeting_recommendations(self):
        entries = [
            WaitlistEntry(email=f"u{i}@t.com", consent_given=True, interests=["ai"], source_platform="meta")
            for i in range(10)
        ]
        await self.engine.build_archetypes(entries)
        recs = await self.engine.get_targeting_recommendations()
        assert len(recs) > 0
        assert recs[0]["archetype"] != ""

    @pytest.mark.asyncio
    async def test_cross_domain_patterns(self):
        group_a = [
            WaitlistEntry(email=f"a{i}@t.com", consent_given=True, interests=["ai", "coding"])
            for i in range(12)
        ]
        group_b = [
            WaitlistEntry(email=f"b{i}@t.com", consent_given=True, interests=["marketing", "sales"])
            for i in range(12)
        ]
        await self.engine.build_archetypes(group_a + group_b)
        patterns = await self.engine.find_cross_domain_patterns()
        assert "archetypes_analyzed" in patterns
        assert patterns["archetypes_analyzed"] >= 2


class TestCrossPatternAnalyzer:
    def setup_method(self):
        self.analyzer = CrossPatternAnalyzer()

    @pytest.mark.asyncio
    async def test_empty_opportunities(self):
        domain_map = await self.analyzer.analyze_domain_connections([])
        assert len(domain_map.domains) == 0

    @pytest.mark.asyncio
    async def test_finds_connections(self):
        opps = [
            MarketOpportunity(
                title="AI Tools", niche="ai tools",
                pain_points=[PainPoint(description="automation is hard")],
                opportunity_score=0.7,
            ),
            MarketOpportunity(
                title="Automation Software", niche="automation software",
                pain_points=[PainPoint(description="automation workflow is hard")],
                opportunity_score=0.6,
            ),
        ]
        domain_map = await self.analyzer.analyze_domain_connections(opps)
        assert len(domain_map.domains) == 2

    @pytest.mark.asyncio
    async def test_expansion_strategy(self):
        opps = [
            MarketOpportunity(title="A", niche="niche_a", pain_points=[PainPoint(description="shared problem")], opportunity_score=0.8),
            MarketOpportunity(title="B", niche="niche_b", pain_points=[PainPoint(description="shared problem")], opportunity_score=0.5),
        ]
        domain_map = await self.analyzer.analyze_domain_connections(opps)
        strategy = await self.analyzer.generate_expansion_strategy(domain_map)
        assert "entry_point" in strategy
        assert "phases" in strategy
