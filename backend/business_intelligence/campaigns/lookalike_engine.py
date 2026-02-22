"""
Lookalike Audience Engine

Implements the Facebook/Meta "lookalike" audience strategy:
1. Take our customer list (emails from waitlist/purchases)
2. Hash them (SHA256 -- Meta requires this)
3. Upload to Meta as a Custom Audience
4. Meta matches against their ~3B user base
5. Meta finds people with identical behavioral patterns
6. We target ads at those lookalikes

The result: dramatically lower CPA because Meta's algorithm does the
heavy lifting of finding the right people. We just need ~1,000 seed
customers for this to work well.

This also handles:
- Audience sizing (1%, 3%, 5%, 10% of country population)
- Audience exclusion (don't target existing customers)
- Multi-platform lookalike strategies (Meta, TikTok, Google)
"""

import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from business_intelligence.models.data_models import (
    WaitlistEntry,
    CustomerArchetype,
    CampaignResult,
)

logger = logging.getLogger(__name__)


LOOKALIKE_MIN_SEED_SIZE = 100
LOOKALIKE_OPTIMAL_SEED_SIZE = 1000
LOOKALIKE_MAX_SEED_SIZE = 10000


@dataclass
class LookalikeAudience:
    """A lookalike audience definition ready for platform upload."""
    id: str = ""
    name: str = ""
    platform: str = ""
    seed_size: int = 0
    seed_source: str = ""
    audience_percentage: float = 1.0  # 1% of country population
    country: str = "GB"
    estimated_reach: int = 0
    hashed_emails: List[str] = field(default_factory=list)
    archetype_filter: Optional[str] = None
    status: str = "draft"
    platform_audience_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    exclusion_list: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class TrafficStrategy:
    """Traffic acquisition strategy combining paid and organic channels."""
    paid_channels: List[Dict[str, Any]] = field(default_factory=list)
    organic_channels: List[Dict[str, Any]] = field(default_factory=list)
    owned_channels: List[Dict[str, Any]] = field(default_factory=list)
    total_estimated_budget: float = 0.0
    estimated_monthly_reach: int = 0
    priority_order: List[str] = field(default_factory=list)
    timeline: List[Dict[str, Any]] = field(default_factory=list)


POPULATION_ESTIMATES = {
    "GB": 67_000_000,
    "US": 330_000_000,
    "CA": 38_000_000,
    "AU": 26_000_000,
    "DE": 83_000_000,
    "FR": 67_000_000,
}


class LookalikeEngine:
    """Creates and manages lookalike audiences across platforms."""

    def __init__(self):
        self.audiences: List[LookalikeAudience] = []

    def hash_email(self, email: str) -> str:
        """SHA256 hash an email for platform upload (Meta requirement)."""
        normalized = email.strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    async def prepare_seed_audience(
        self,
        entries: List[WaitlistEntry],
        archetype_filter: Optional[str] = None,
        min_size: int = LOOKALIKE_MIN_SEED_SIZE,
    ) -> Dict[str, Any]:
        """Prepare a seed audience from waitlist entries.

        Filters to consented-only entries and hashes emails.
        """
        eligible = [
            e for e in entries
            if e.consent_given and not e.opted_out and e.email
        ]

        if archetype_filter:
            eligible = [
                e for e in eligible
                if archetype_filter.lower() in " ".join(e.interests).lower()
            ]

        if len(eligible) < min_size:
            return {
                "status": "insufficient_seed",
                "current_size": len(eligible),
                "required_size": min_size,
                "optimal_size": LOOKALIKE_OPTIMAL_SEED_SIZE,
                "message": (
                    f"Need at least {min_size} consented entries for a lookalike audience. "
                    f"Currently have {len(eligible)}. Optimal is {LOOKALIKE_OPTIMAL_SEED_SIZE}+."
                ),
            }

        hashed = [self.hash_email(e.email) for e in eligible]

        quality = "low"
        if len(eligible) >= LOOKALIKE_OPTIMAL_SEED_SIZE:
            quality = "high"
        elif len(eligible) >= LOOKALIKE_MIN_SEED_SIZE * 5:
            quality = "medium"

        source_breakdown = {}
        for e in eligible:
            src = e.source_platform or "direct"
            source_breakdown[src] = source_breakdown.get(src, 0) + 1

        return {
            "status": "ready",
            "seed_size": len(eligible),
            "quality": quality,
            "hashed_count": len(hashed),
            "source_breakdown": source_breakdown,
            "archetype_filter": archetype_filter,
            "hashed_emails": hashed,
            "message": (
                f"Seed audience ready: {len(eligible)} entries ({quality} quality). "
                "Upload to Meta/TikTok to create lookalike audiences."
            ),
        }

    async def create_lookalike_audience(
        self,
        seed_data: Dict[str, Any],
        platform: str = "meta",
        audience_percentage: float = 1.0,
        country: str = "GB",
        name: str = "",
    ) -> LookalikeAudience:
        """Create a lookalike audience definition.

        Does NOT upload to the platform -- generates the spec for
        human review before submission.
        """
        if seed_data.get("status") != "ready":
            raise ValueError("Seed audience not ready")

        population = POPULATION_ESTIMATES.get(country, 67_000_000)
        estimated_reach = int(population * (audience_percentage / 100))

        aud_name = name or f"Lookalike_{platform}_{audience_percentage}pct_{country}_{datetime.utcnow().strftime('%Y%m%d')}"

        audience = LookalikeAudience(
            id=f"la_{platform}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            name=aud_name,
            platform=platform,
            seed_size=seed_data["seed_size"],
            seed_source="waitlist",
            audience_percentage=audience_percentage,
            country=country,
            estimated_reach=estimated_reach,
            hashed_emails=seed_data.get("hashed_emails", []),
            archetype_filter=seed_data.get("archetype_filter"),
            status="pending_upload",
            notes=[
                f"Quality: {seed_data['quality']}",
                f"Source breakdown: {seed_data['source_breakdown']}",
                f"Estimated reach: {estimated_reach:,} people",
                "Requires human approval before platform upload.",
            ],
        )

        self.audiences.append(audience)

        logger.info(
            f"Lookalike audience created: {aud_name} "
            f"(seed: {audience.seed_size}, reach: {estimated_reach:,})"
        )

        return audience

    async def recommend_audience_strategy(
        self,
        seed_size: int,
        budget: float,
        archetypes: Optional[List[CustomerArchetype]] = None,
    ) -> Dict[str, Any]:
        """Recommend a lookalike audience strategy based on available data."""
        recommendations = []

        if seed_size < LOOKALIKE_MIN_SEED_SIZE:
            return {
                "status": "need_more_data",
                "seed_size": seed_size,
                "needed": LOOKALIKE_MIN_SEED_SIZE,
                "recommendations": [
                    f"Need {LOOKALIKE_MIN_SEED_SIZE - seed_size} more customers/signups before lookalike audiences become viable.",
                    "Focus on direct acquisition campaigns in the meantime.",
                    "Use interest-based targeting as a stopgap.",
                ],
            }

        if seed_size >= LOOKALIKE_OPTIMAL_SEED_SIZE:
            recommendations.append({
                "strategy": "multi_tier_lookalike",
                "description": "Create 3 audience tiers: 1% (closest match), 3% (broader), 5% (widest reach)",
                "audiences": [
                    {"percentage": 1.0, "use": "Highest value campaigns, retargeting"},
                    {"percentage": 3.0, "use": "Standard prospecting campaigns"},
                    {"percentage": 5.0, "use": "Awareness and reach campaigns"},
                ],
                "budget_split": {"1pct": 50, "3pct": 30, "5pct": 20},
            })
        else:
            recommendations.append({
                "strategy": "single_tier_lookalike",
                "description": f"With {seed_size} seeds, start with a 1% lookalike for best match quality",
                "audiences": [
                    {"percentage": 1.0, "use": "All campaigns until seed grows"},
                ],
                "budget_split": {"1pct": 100},
            })

        if archetypes and len(archetypes) >= 2:
            recommendations.append({
                "strategy": "archetype_segmented",
                "description": "Create separate lookalike audiences per customer archetype for tailored messaging",
                "archetypes": [
                    {"name": a.name, "sample_size": a.sample_size}
                    for a in archetypes
                    if a.sample_size >= 50
                ],
            })

        recommendations.append({
            "strategy": "exclusion_targeting",
            "description": "Always exclude existing customers from prospecting campaigns to avoid wasted spend",
        })

        platforms = ["meta"]
        if budget > 200:
            platforms.append("tiktok")
        if budget > 500:
            platforms.append("google")

        return {
            "status": "ready",
            "seed_size": seed_size,
            "seed_quality": "high" if seed_size >= LOOKALIKE_OPTIMAL_SEED_SIZE else "medium",
            "recommended_platforms": platforms,
            "strategies": recommendations,
            "estimated_cpa_improvement": "40-60% lower CPA compared to interest-based targeting",
        }

    async def generate_traffic_strategy(
        self,
        budget: float,
        niche: str,
        seed_size: int = 0,
        archetypes: Optional[List[CustomerArchetype]] = None,
    ) -> TrafficStrategy:
        """Generate a complete traffic acquisition strategy.

        Addresses the core problem: Grace doesn't own the traffic.
        Meta/Google/TikTok do. Strategy is to leverage their traffic
        efficiently and build owned channels to reduce dependence.
        """
        strategy = TrafficStrategy()

        # Paid channels -- using platform traffic
        if seed_size >= LOOKALIKE_MIN_SEED_SIZE:
            strategy.paid_channels.append({
                "channel": "Meta Lookalike Ads",
                "priority": 1,
                "budget_percentage": 40,
                "estimated_cpa": 3.0,
                "rationale": "Lookalike audiences from customer data. Best ROI with sufficient seed.",
                "setup": "Upload hashed emails -> Create 1% lookalike -> Run conversion campaign",
            })
        else:
            strategy.paid_channels.append({
                "channel": "Meta Interest-Based Ads",
                "priority": 1,
                "budget_percentage": 30,
                "estimated_cpa": 7.0,
                "rationale": "Interest targeting until we have enough data for lookalikes.",
                "setup": "Target interests related to niche pain points",
            })

        strategy.paid_channels.append({
            "channel": "TikTok Ads",
            "priority": 2,
            "budget_percentage": 20,
            "estimated_cpa": 4.0,
            "rationale": "Lower CPMs, younger demographic, viral potential.",
            "setup": "Create short-form video content highlighting pain points",
        })

        strategy.paid_channels.append({
            "channel": "Google Search Ads",
            "priority": 3,
            "budget_percentage": 15,
            "estimated_cpa": 8.0,
            "rationale": "Captures high-intent searches but higher CPC.",
            "setup": "Target pain-point keywords identified in research",
        })

        strategy.paid_channels.append({
            "channel": "YouTube Pre-Roll",
            "priority": 4,
            "budget_percentage": 15,
            "estimated_cpa": 5.0,
            "rationale": "Video content that educates and converts.",
            "setup": "Create educational content, target niche-related channels",
        })

        # Organic channels -- building authority
        strategy.organic_channels = [
            {
                "channel": "SEO Content",
                "priority": 1,
                "cost": "Time only (Grace generates content)",
                "timeline": "3-6 months for results",
                "rationale": "Long-term traffic source. Grace can produce SEO-optimized articles from research data.",
            },
            {
                "channel": "Reddit/Forum Engagement",
                "priority": 2,
                "cost": "Time only",
                "timeline": "Immediate engagement, 1-3 months for trust",
                "rationale": "Genuine participation in niche communities. NOT spam -- actual value contribution.",
            },
            {
                "channel": "YouTube Organic",
                "priority": 3,
                "cost": "Content production",
                "timeline": "3-6 months",
                "rationale": "Educational content series. Position as authority.",
            },
            {
                "channel": "TikTok Organic",
                "priority": 4,
                "cost": "Content production",
                "timeline": "1-3 months",
                "rationale": "Short-form educational/entertaining content. Viral potential.",
            },
        ]

        # Owned channels -- reducing platform dependence
        strategy.owned_channels = [
            {
                "channel": "Email List",
                "priority": 1,
                "value": "Highest value owned asset",
                "rationale": "Every ad dollar should drive to email capture. 3x more likely to convert repeat buyers.",
                "growth_target": "Add 100+ emails/week from all sources",
            },
            {
                "channel": "Community (Discord/Circle)",
                "priority": 2,
                "value": "High engagement, direct feedback",
                "rationale": "Build direct relationship with customers. Free market research.",
            },
            {
                "channel": "Blog/Website",
                "priority": 3,
                "value": "SEO + Authority",
                "rationale": "Central hub for all content. Reduces dependence on social platforms.",
            },
        ]

        total_budget = budget
        for channel in strategy.paid_channels:
            channel["estimated_budget"] = round(
                total_budget * channel["budget_percentage"] / 100, 2
            )

        strategy.total_estimated_budget = budget
        strategy.estimated_monthly_reach = int(budget / 5 * 1000)

        strategy.priority_order = [
            "1. Email list building (every visitor -> email capture)",
            "2. Meta ads (lookalike if data available, interest if not)",
            "3. TikTok ads (low CPM, high volume)",
            "4. SEO content (Grace-generated, long-term play)",
            "5. Community building (direct customer relationship)",
            "6. Google/YouTube ads (high-intent but expensive)",
        ]

        strategy.timeline = [
            {"week": "1-2", "focus": "Set up landing page + waitlist + initial Meta campaign"},
            {"week": "3-4", "focus": "Analyze results, optimize ad copy, start TikTok test"},
            {"week": "5-8", "focus": "Scale winning channels, start content production"},
            {"week": "9-12", "focus": "Build lookalike audiences, launch organic strategy"},
            {"month": "4-6", "focus": "SEO starts compounding, reduce paid reliance"},
        ]

        return strategy
