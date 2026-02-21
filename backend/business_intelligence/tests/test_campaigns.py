"""Tests for campaign management, waitlist, validation, and ad components."""

import pytest
from datetime import datetime, timedelta

from business_intelligence.campaigns.waitlist_manager import WaitlistManager
from business_intelligence.campaigns.campaign_manager import CampaignManager
from business_intelligence.campaigns.validation_engine import ValidationEngine
from business_intelligence.campaigns.ad_copy_generator import AdCopyGenerator
from business_intelligence.campaigns.ad_optimizer import AdOptimizer
from business_intelligence.campaigns.lookalike_engine import LookalikeEngine
from business_intelligence.campaigns.dynamic_creative import DynamicCreativeEngine
from business_intelligence.models.data_models import (
    MarketOpportunity, PainPoint, CampaignResult, WaitlistEntry, ProductConcept,
)


class TestWaitlistManager:
    def setup_method(self):
        self.wl = WaitlistManager(validation_threshold=10)

    @pytest.mark.asyncio
    async def test_add_signup_with_consent(self):
        result = await self.wl.add_signup(
            email="test@example.com",
            consent_given=True,
            consent_text="I agree",
        )
        assert result["status"] == "added"
        assert result["waitlist_position"] == 1

    @pytest.mark.asyncio
    async def test_reject_without_consent(self):
        result = await self.wl.add_signup(email="test@example.com", consent_given=False)
        assert result["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_reject_duplicate(self):
        await self.wl.add_signup(email="dup@example.com", consent_given=True)
        result = await self.wl.add_signup(email="dup@example.com", consent_given=True)
        assert result["status"] == "duplicate"

    @pytest.mark.asyncio
    async def test_opt_out(self):
        await self.wl.add_signup(email="out@example.com", consent_given=True)
        result = await self.wl.opt_out("out@example.com")
        assert result["status"] == "opted_out"

    @pytest.mark.asyncio
    async def test_validation_threshold(self):
        for i in range(10):
            await self.wl.add_signup(email=f"user{i}@test.com", consent_given=True)
        stats = await self.wl.get_stats()
        assert stats.validation_reached

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        await self.wl.add_signup(
            email="fb@test.com", consent_given=True,
            source_platform="facebook", source_campaign="camp1",
        )
        stats = await self.wl.get_stats()
        assert stats.active_signups == 1
        assert "facebook" in stats.by_source_platform

    @pytest.mark.asyncio
    async def test_anonymize_old_entries(self):
        entry = WaitlistEntry(
            email="old@test.com", consent_given=True,
            signup_date=datetime.utcnow() - timedelta(days=100),
        )
        self.wl.entries.append(entry)
        result = await self.wl.anonymize_old_entries(retention_days=90)
        assert result["anonymized"] == 1
        assert "anonymized_" in entry.email


class TestCampaignManager:
    def setup_method(self):
        self.cm = CampaignManager()

    @pytest.mark.asyncio
    async def test_create_plan(self):
        plan = await self.cm.create_campaign_plan(
            name="Test Campaign",
            platforms=["meta", "tiktok"],
            daily_budget=20.0,
            total_budget=200.0,
        )
        assert plan.status == "pending_approval"
        assert plan.requires_approval

    @pytest.mark.asyncio
    async def test_budget_cap(self):
        plan = await self.cm.create_campaign_plan(
            name="Over Budget",
            platforms=["meta"],
            daily_budget=1000.0,
            total_budget=100000.0,
        )
        assert plan.daily_budget <= CampaignManager.MAX_DAILY_BUDGET
        assert plan.total_budget <= CampaignManager.MAX_TOTAL_BUDGET

    @pytest.mark.asyncio
    async def test_approve_campaign(self):
        plan = await self.cm.create_campaign_plan(name="Test", platforms=["meta"])
        result = await self.cm.approve_campaign(plan.id)
        assert result["status"] == "approved"

    @pytest.mark.asyncio
    async def test_record_result(self):
        plan = await self.cm.create_campaign_plan(name="Test", platforms=["meta"])
        result = await self.cm.record_result(
            campaign_id=plan.id, platform="meta",
            impressions=1000, clicks=50, signups=10, ad_spend=50.0,
        )
        assert result.cost_per_acquisition == 5.0
        assert result.cost_per_click == 1.0

    @pytest.mark.asyncio
    async def test_ab_analysis(self):
        plan = await self.cm.create_campaign_plan(name="AB Test", platforms=["meta"])
        await self.cm.record_result(plan.id, "meta", impressions=1000, clicks=50, signups=10, ad_spend=50.0, ad_copy_variant="A")
        await self.cm.record_result(plan.id, "meta", impressions=1000, clicks=30, signups=3, ad_spend=50.0, ad_copy_variant="B")
        analysis = await self.cm.analyze_ab_results(plan.id)
        assert "winner" in analysis


class TestValidationEngine:
    @pytest.mark.asyncio
    async def test_insufficient_data(self):
        wl = WaitlistManager(validation_threshold=500)
        cm = CampaignManager()
        ve = ValidationEngine(wl, cm)
        verdict = await ve.evaluate()
        assert verdict.status == "insufficient_data"

    @pytest.mark.asyncio
    async def test_go_verdict(self):
        wl = WaitlistManager(validation_threshold=10)
        cm = CampaignManager()
        for i in range(15):
            await wl.add_signup(email=f"u{i}@t.com", consent_given=True)
        plan = await cm.create_campaign_plan(name="T", platforms=["meta"])
        await cm.record_result(plan.id, "meta", signups=15, ad_spend=30.0, impressions=1000, clicks=100)
        ve = ValidationEngine(wl, cm, min_signups=10, target_cpa=5.0)
        verdict = await ve.evaluate()
        assert verdict.status == "go"
        assert len(verdict.recommendations) > 0


class TestAdCopyGenerator:
    @pytest.mark.asyncio
    async def test_generate_variants(self):
        gen = AdCopyGenerator()
        opp = MarketOpportunity(
            title="AI Automation",
            niche="ai tools",
            pain_points=[
                PainPoint(description="Manual data entry is tedious"),
                PainPoint(description="Reports take hours to create"),
            ],
        )
        copies = await gen.generate_copy(opp, platform="facebook", num_variants=2)
        assert len(copies) >= 2
        for copy in copies:
            assert copy.headline != ""
            assert len(copy.compliance_notes) > 0

    @pytest.mark.asyncio
    async def test_landing_page_copy(self):
        gen = AdCopyGenerator()
        opp = MarketOpportunity(
            title="Test Product",
            pain_points=[PainPoint(description="problem 1"), PainPoint(description="problem 2")],
        )
        copy = await gen.generate_landing_page_copy(opp)
        assert "hero_headline" in copy
        assert "cta_button" in copy


class TestAdOptimizer:
    @pytest.mark.asyncio
    async def test_no_data(self):
        opt = AdOptimizer()
        analysis = await opt.analyze_performance([])
        assert analysis["campaigns_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_detects_high_cpa(self):
        opt = AdOptimizer(target_cpa=5.0)
        results = [
            CampaignResult(platform="meta", ad_spend=100, signups=2, impressions=1000, clicks=50,
                           cost_per_acquisition=50.0, ab_variant="A"),
        ]
        analysis = await opt.analyze_performance(results)
        alerts = [a for a in analysis["alerts"] if a["type"] == "cpa_spike"]
        assert len(alerts) > 0


class TestLookalikeEngine:
    def setup_method(self):
        self.engine = LookalikeEngine()

    def test_hash_email(self):
        h1 = self.engine.hash_email("Test@Example.com")
        h2 = self.engine.hash_email("test@example.com")
        assert h1 == h2
        assert len(h1) == 64

    @pytest.mark.asyncio
    async def test_insufficient_seed(self):
        entries = [
            WaitlistEntry(email=f"u{i}@t.com", consent_given=True)
            for i in range(5)
        ]
        result = await self.engine.prepare_seed_audience(entries, min_size=100)
        assert result["status"] == "insufficient_seed"

    @pytest.mark.asyncio
    async def test_sufficient_seed(self):
        entries = [
            WaitlistEntry(email=f"u{i}@t.com", consent_given=True)
            for i in range(150)
        ]
        result = await self.engine.prepare_seed_audience(entries, min_size=100)
        assert result["status"] == "ready"
        assert result["seed_size"] == 150

    @pytest.mark.asyncio
    async def test_excludes_opted_out(self):
        entries = [
            WaitlistEntry(email=f"u{i}@t.com", consent_given=True, opted_out=(i < 50))
            for i in range(100)
        ]
        result = await self.engine.prepare_seed_audience(entries, min_size=10)
        assert result["seed_size"] == 50


class TestDynamicCreativeEngine:
    def setup_method(self):
        self.engine = DynamicCreativeEngine()

    @pytest.mark.asyncio
    async def test_generate_meta_dco(self):
        spec = await self.engine.generate_meta_dynamic_creative(
            headlines=["H1", "H2", "H3"],
            body_texts=["Body 1", "Body 2"],
            descriptions=["Desc 1"],
        )
        assert spec.asset_feed["titles"][0]["text"] == "H1"
        assert spec.platform_specs["total_combinations"] > 0

    @pytest.mark.asyncio
    async def test_generate_creative_variations(self):
        variation = await self.engine.generate_creative_variations(
            pain_points=["slow loading", "crashes often"],
            product_name="SpeedApp",
            platform="meta",
        )
        assert len(variation.headlines) > 0
        assert len(variation.body_texts) > 0
        assert variation.platform == "meta"

    @pytest.mark.asyncio
    async def test_build_creative_pipeline(self):
        pipeline = await self.engine.build_creative_pipeline(
            pain_points=["problem 1", "problem 2"],
            product_name="TestProd",
            platforms=["meta", "tiktok", "google"],
        )
        assert "meta" in pipeline["platforms"]
        assert "tiktok" in pipeline["platforms"]
        assert pipeline["total_combinations"] > 0
        assert len(pipeline["creative_tools"]) > 0
