"""
Customer Archetype Engine

Builds customer archetypes from aggregate behavioral data. An archetype is
NOT an individual profile -- it's a pattern that represents a segment of
customers who share characteristics.

The insight from the requirements: once we have a list of buyers, we look at
the archetypes (age ranges, pain points, buying motivations) and create
targeting algorithms for like-for-like people.

Legal boundaries:
- Only uses data explicitly provided by customers (signup forms, surveys)
- Does NOT scrape individual social media profiles
- Does NOT build individual-level profiles without explicit consent
- All analysis is aggregate (minimum group size enforced)
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict
from dataclasses import dataclass, field
import uuid

from business_intelligence.models.data_models import (
    CustomerArchetype,
    WaitlistEntry,
    CampaignResult,
)

logger = logging.getLogger(__name__)


MINIMUM_CLUSTER_SIZE = 10  # Privacy: never create archetypes from fewer than 10 people


@dataclass
class ArchetypeCluster:
    """Raw cluster before it becomes an archetype."""
    members: List[Dict[str, Any]] = field(default_factory=list)
    common_interests: List[str] = field(default_factory=list)
    common_sources: List[str] = field(default_factory=list)
    size: int = 0


class ArchetypeEngine:
    """Builds and manages customer archetypes from aggregate data."""

    def __init__(self, min_cluster_size: int = MINIMUM_CLUSTER_SIZE):
        self.min_cluster_size = max(min_cluster_size, MINIMUM_CLUSTER_SIZE)
        self.archetypes: List[CustomerArchetype] = []

    async def build_archetypes(
        self,
        waitlist_entries: List[WaitlistEntry],
        campaign_results: Optional[List[CampaignResult]] = None,
    ) -> List[CustomerArchetype]:
        """Build customer archetypes from waitlist and campaign data.

        Groups customers by shared characteristics and creates
        aggregate profiles (archetypes) for targeting optimization.
        """
        if len(waitlist_entries) < self.min_cluster_size:
            logger.info(
                f"Need at least {self.min_cluster_size} entries to build archetypes. "
                f"Currently have {len(waitlist_entries)}."
            )
            return []

        clusters = self._cluster_by_interests(waitlist_entries)

        if campaign_results:
            self._enrich_with_campaign_data(clusters, campaign_results)

        archetypes = []
        for idx, cluster in enumerate(clusters):
            if cluster.size < self.min_cluster_size:
                continue

            archetype = self._cluster_to_archetype(cluster, idx + 1)
            archetypes.append(archetype)

        archetypes.sort(key=lambda a: a.sample_size, reverse=True)
        self.archetypes = archetypes

        logger.info(
            f"Built {len(archetypes)} archetypes from "
            f"{len(waitlist_entries)} entries"
        )

        return archetypes

    def _cluster_by_interests(
        self, entries: List[WaitlistEntry]
    ) -> List[ArchetypeCluster]:
        """Cluster entries by shared interests."""
        interest_groups: Dict[frozenset, List[WaitlistEntry]] = defaultdict(list)

        for entry in entries:
            if not entry.consent_given or entry.opted_out:
                continue

            key = frozenset(sorted(entry.interests)) if entry.interests else frozenset(["general"])
            interest_groups[key].append(entry)

        clusters = []
        for interests, members in interest_groups.items():
            source_counter = Counter(e.source_platform for e in members if e.source_platform)
            clusters.append(
                ArchetypeCluster(
                    members=[
                        {
                            "source_platform": e.source_platform,
                            "source_campaign": e.source_campaign,
                            "interests": e.interests,
                            "signup_date": e.signup_date.isoformat(),
                        }
                        for e in members
                    ],
                    common_interests=sorted(interests),
                    common_sources=[s for s, _ in source_counter.most_common(5)],
                    size=len(members),
                )
            )

        return clusters

    def _enrich_with_campaign_data(
        self,
        clusters: List[ArchetypeCluster],
        results: List[CampaignResult],
    ):
        """Enrich clusters with campaign performance data."""
        platform_cpa: Dict[str, float] = {}
        for r in results:
            if r.cost_per_acquisition > 0:
                platform_cpa[r.platform] = r.cost_per_acquisition

        for cluster in clusters:
            for source in cluster.common_sources:
                if source in platform_cpa:
                    for member in cluster.members:
                        member["acquisition_cost_estimate"] = platform_cpa[source]

    def _cluster_to_archetype(
        self, cluster: ArchetypeCluster, index: int
    ) -> CustomerArchetype:
        """Convert a raw cluster into a named archetype."""
        interests = cluster.common_interests
        name = self._generate_archetype_name(interests, index)

        source_counter = Counter(cluster.common_sources)
        preferred_channels = [s for s, _ in source_counter.most_common(3)]

        acq_costs = [
            m.get("acquisition_cost_estimate", 0)
            for m in cluster.members
            if m.get("acquisition_cost_estimate")
        ]
        avg_acq_cost = sum(acq_costs) / len(acq_costs) if acq_costs else 0.0

        return CustomerArchetype(
            name=name,
            description=f"Customers interested in: {', '.join(interests[:5])}",
            demographics={
                "interest_profile": interests[:10],
                "primary_channels": preferred_channels,
            },
            pain_points=interests[:5],
            preferred_channels=preferred_channels,
            acquisition_cost_estimate=round(avg_acq_cost, 2),
            sample_size=cluster.size,
            confidence=min(cluster.size / 100, 1.0),
            consent_verified=True,
        )

    def _generate_archetype_name(
        self, interests: List[str], index: int
    ) -> str:
        """Generate a descriptive name for an archetype."""
        if not interests or interests == ["general"]:
            return f"General Audience #{index}"

        primary = interests[0].title() if interests else "Unknown"
        if len(interests) > 1:
            return f"{primary} & {interests[1].title()} Seekers"
        return f"{primary} Enthusiasts"

    async def get_targeting_recommendations(
        self,
    ) -> List[Dict[str, Any]]:
        """Generate targeting recommendations for ad campaigns.

        Based on archetypes, recommend which segments to target
        on which platforms with what messaging.
        """
        if not self.archetypes:
            return [{
                "message": "No archetypes built yet. Need minimum 10 waitlist entries.",
                "action": "Continue collecting waitlist signups",
            }]

        recommendations = []
        for arch in self.archetypes:
            rec = {
                "archetype": arch.name,
                "sample_size": arch.sample_size,
                "confidence": arch.confidence,
                "target_platforms": arch.preferred_channels,
                "messaging_focus": arch.pain_points[:3],
                "estimated_cpa": arch.acquisition_cost_estimate,
            }

            if arch.acquisition_cost_estimate > 0:
                rec["budget_recommendation"] = (
                    f"Estimated {arch.acquisition_cost_estimate:.2f} GBP per acquisition. "
                    f"For 100 new signups: ~{arch.acquisition_cost_estimate * 100:.0f} GBP."
                )

            recommendations.append(rec)

        return recommendations

    async def find_cross_domain_patterns(
        self,
    ) -> Dict[str, Any]:
        """Find patterns that span multiple archetypes.

        This is the "cross pattern domains" concept from requirements --
        finding commonalities across different customer segments that
        could enable cross-selling or unified campaigns.
        """
        if len(self.archetypes) < 2:
            return {"message": "Need at least 2 archetypes for cross-domain analysis"}

        all_interests: Counter = Counter()
        all_channels: Counter = Counter()

        for arch in self.archetypes:
            all_interests.update(arch.pain_points)
            all_channels.update(arch.preferred_channels)

        shared_interests = [
            interest for interest, count in all_interests.items()
            if count >= len(self.archetypes) * 0.5
        ]

        universal_channels = [
            ch for ch, count in all_channels.items()
            if count >= len(self.archetypes) * 0.7
        ]

        return {
            "archetypes_analyzed": len(self.archetypes),
            "shared_interests": shared_interests,
            "universal_channels": universal_channels,
            "cross_sell_opportunities": [
                {
                    "from": self.archetypes[i].name,
                    "to": self.archetypes[j].name,
                    "shared": list(
                        set(self.archetypes[i].pain_points)
                        & set(self.archetypes[j].pain_points)
                    ),
                }
                for i in range(len(self.archetypes))
                for j in range(i + 1, len(self.archetypes))
                if set(self.archetypes[i].pain_points) & set(self.archetypes[j].pain_points)
            ],
            "recommendation": (
                f"Shared interests across segments: {', '.join(shared_interests[:5])}. "
                f"Universal channels: {', '.join(universal_channels[:3])}. "
                "These overlaps enable unified campaigns that reach multiple segments."
            ) if shared_interests else "Segments are distinct -- target each separately.",
        }
