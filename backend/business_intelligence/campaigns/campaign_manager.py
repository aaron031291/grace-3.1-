"""
Campaign Manager

Manages advertising campaigns across platforms (Meta, TikTok, YouTube).
Creates, tracks, and analyzes campaigns with built-in budget controls
and A/B test management.

Key principle: minimum viable ad spend to validate demand.
We're not trying to make money from ads -- we're testing if
people want what we're building.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import uuid

from business_intelligence.models.data_models import CampaignResult

logger = logging.getLogger(__name__)


@dataclass
class CampaignPlan:
    """A campaign plan ready for execution."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    objective: str = "waitlist_signups"
    platforms: List[str] = field(default_factory=list)
    daily_budget: float = 10.0
    total_budget: float = 100.0
    duration_days: int = 7
    target_audience: Dict[str, Any] = field(default_factory=dict)
    ad_copies: List[Dict] = field(default_factory=list)
    ab_test_enabled: bool = True
    landing_page_url: str = ""
    status: str = "draft"
    requires_approval: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


class CampaignManager:
    """Manages advertising campaigns for demand validation."""

    MAX_DAILY_BUDGET = 50.0
    MAX_TOTAL_BUDGET = 500.0

    def __init__(self):
        self.campaigns: List[CampaignPlan] = []
        self.results: List[CampaignResult] = []

    async def create_campaign_plan(
        self,
        name: str,
        platforms: List[str],
        daily_budget: float = 10.0,
        total_budget: float = 100.0,
        duration_days: int = 7,
        target_audience: Optional[Dict] = None,
        ad_copies: Optional[List[Dict]] = None,
        landing_page_url: str = "",
    ) -> CampaignPlan:
        """Create a campaign plan. Does NOT execute -- requires human approval."""
        daily_budget = min(daily_budget, self.MAX_DAILY_BUDGET)
        total_budget = min(total_budget, self.MAX_TOTAL_BUDGET)

        plan = CampaignPlan(
            name=name,
            platforms=platforms,
            daily_budget=daily_budget,
            total_budget=total_budget,
            duration_days=duration_days,
            target_audience=target_audience or {},
            ad_copies=ad_copies or [],
            landing_page_url=landing_page_url,
            status="pending_approval",
            requires_approval=True,
        )

        self.campaigns.append(plan)
        logger.info(
            f"Campaign plan created: {name} "
            f"(budget: {total_budget}, platforms: {platforms}). "
            "Awaiting human approval."
        )

        return plan

    async def approve_campaign(self, campaign_id: str) -> Dict[str, Any]:
        """Human approves a campaign plan for execution."""
        campaign = next(
            (c for c in self.campaigns if c.id == campaign_id), None
        )
        if not campaign:
            return {"status": "not_found"}

        campaign.status = "approved"
        campaign.requires_approval = False

        logger.info(f"Campaign approved: {campaign.name}")
        return {
            "status": "approved",
            "campaign_id": campaign_id,
            "message": "Campaign approved. Ready for platform submission.",
            "next_step": "Submit to ad platforms via their respective APIs.",
        }

    async def record_result(
        self,
        campaign_id: str,
        platform: str,
        impressions: int = 0,
        clicks: int = 0,
        conversions: int = 0,
        signups: int = 0,
        ad_spend: float = 0.0,
        ad_copy_variant: str = "",
    ) -> CampaignResult:
        """Record campaign results from a platform."""
        cpc = ad_spend / clicks if clicks > 0 else 0.0
        cpa = ad_spend / signups if signups > 0 else 0.0
        ctr = (clicks / impressions * 100) if impressions > 0 else 0.0
        conv_rate = (conversions / clicks * 100) if clicks > 0 else 0.0

        campaign = next(
            (c for c in self.campaigns if c.id == campaign_id), None
        )

        result = CampaignResult(
            campaign_name=campaign.name if campaign else campaign_id,
            platform=platform,
            ad_spend=ad_spend,
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
            signups=signups,
            cost_per_click=round(cpc, 2),
            cost_per_acquisition=round(cpa, 2),
            conversion_rate=round(conv_rate, 2),
            ab_variant=ad_copy_variant,
        )

        self.results.append(result)
        logger.info(
            f"Campaign result recorded: {result.campaign_name} on {platform}. "
            f"Spend: {ad_spend}, Signups: {signups}, CPA: {cpa:.2f}"
        )

        return result

    async def analyze_ab_results(
        self, campaign_id: str
    ) -> Dict[str, Any]:
        """Analyze A/B test results for a campaign."""
        campaign_results = [
            r for r in self.results
            if r.campaign_name == campaign_id or any(
                c.id == campaign_id and c.name == r.campaign_name
                for c in self.campaigns
            )
        ]

        if not campaign_results:
            return {"status": "no_data"}

        variants: Dict[str, List[CampaignResult]] = {}
        for r in campaign_results:
            v = r.ab_variant or "default"
            variants.setdefault(v, []).append(r)

        analysis = {"variants": {}}

        for variant, results in variants.items():
            total_spend = sum(r.ad_spend for r in results)
            total_clicks = sum(r.clicks for r in results)
            total_signups = sum(r.signups for r in results)
            total_impressions = sum(r.impressions for r in results)

            analysis["variants"][variant] = {
                "total_spend": total_spend,
                "total_impressions": total_impressions,
                "total_clicks": total_clicks,
                "total_signups": total_signups,
                "avg_cpc": total_spend / total_clicks if total_clicks > 0 else 0,
                "avg_cpa": total_spend / total_signups if total_signups > 0 else 0,
                "ctr": (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
                "signup_rate": (total_signups / total_clicks * 100) if total_clicks > 0 else 0,
            }

        if len(analysis["variants"]) >= 2:
            best = min(
                analysis["variants"].items(),
                key=lambda x: x[1]["avg_cpa"] if x[1]["avg_cpa"] > 0 else float("inf"),
            )
            analysis["winner"] = best[0]
            analysis["recommendation"] = (
                f"Variant '{best[0]}' has the lowest CPA ({best[1]['avg_cpa']:.2f}). "
                "Scale budget towards this variant."
            )

        return analysis

    async def get_campaign_summary(self) -> Dict[str, Any]:
        """Get summary of all campaigns."""
        total_spend = sum(r.ad_spend for r in self.results)
        total_signups = sum(r.signups for r in self.results)

        return {
            "total_campaigns": len(self.campaigns),
            "active_campaigns": sum(
                1 for c in self.campaigns if c.status in ("approved", "running")
            ),
            "pending_approval": sum(
                1 for c in self.campaigns if c.status == "pending_approval"
            ),
            "total_spend": round(total_spend, 2),
            "total_signups": total_signups,
            "overall_cpa": round(total_spend / total_signups, 2) if total_signups > 0 else 0,
            "platforms_used": list(set(r.platform for r in self.results)),
            "campaigns": [
                {
                    "id": c.id,
                    "name": c.name,
                    "status": c.status,
                    "budget": c.total_budget,
                    "platforms": c.platforms,
                }
                for c in self.campaigns
            ],
        }
