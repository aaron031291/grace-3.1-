"""
Validation Engine

The decision engine that determines whether we have enough evidence
to proceed from "idea" to "build". Combines waitlist data, campaign
performance, and market research into a go/no-go decision.

Validation criteria:
- 500+ waitlist signups (configurable threshold)
- CPA below target (default: 5 GBP)
- Positive trend in signup rate
- Multiple traffic sources converting
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from business_intelligence.campaigns.waitlist_manager import WaitlistManager, WaitlistStats
from business_intelligence.campaigns.campaign_manager import CampaignManager
from business_intelligence.models.data_models import (
    MarketOpportunity,
    ProductConcept,
    CampaignResult,
)

logger = logging.getLogger(__name__)


@dataclass
class ValidationVerdict:
    """The verdict on whether to proceed to build."""
    status: str = "insufficient_data"  # go, no_go, insufficient_data, promising
    confidence: float = 0.0
    waitlist_score: float = 0.0
    campaign_score: float = 0.0
    market_score: float = 0.0
    overall_score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ValidationEngine:
    """Determines if demand has been sufficiently validated."""

    def __init__(
        self,
        waitlist_manager: WaitlistManager,
        campaign_manager: CampaignManager,
        min_signups: int = 500,
        target_cpa: float = 5.0,
    ):
        self.waitlist = waitlist_manager
        self.campaigns = campaign_manager
        self.min_signups = min_signups
        self.target_cpa = target_cpa

    async def evaluate(
        self,
        opportunity: Optional[MarketOpportunity] = None,
    ) -> ValidationVerdict:
        """Run validation evaluation."""
        verdict = ValidationVerdict()

        waitlist_stats = await self.waitlist.get_stats()
        verdict.waitlist_score = self._score_waitlist(waitlist_stats)

        campaign_summary = await self.campaigns.get_campaign_summary()
        verdict.campaign_score = self._score_campaigns(campaign_summary)

        if opportunity:
            verdict.market_score = self._score_market(opportunity)
        else:
            verdict.market_score = 0.5

        verdict.overall_score = (
            verdict.waitlist_score * 0.4 +
            verdict.campaign_score * 0.3 +
            verdict.market_score * 0.3
        )

        verdict.status = self._determine_status(verdict, waitlist_stats)
        verdict.confidence = self._calculate_confidence(
            verdict, waitlist_stats, campaign_summary
        )

        self._add_reasons(verdict, waitlist_stats, campaign_summary)
        self._add_recommendations(verdict, waitlist_stats, campaign_summary)

        return verdict

    def _score_waitlist(self, stats: WaitlistStats) -> float:
        """Score the waitlist performance."""
        if stats.active_signups >= self.min_signups:
            return 1.0
        elif stats.active_signups >= self.min_signups * 0.5:
            return 0.7
        elif stats.active_signups >= self.min_signups * 0.2:
            return 0.4
        elif stats.active_signups > 0:
            return 0.2
        return 0.0

    def _score_campaigns(self, summary: Dict[str, Any]) -> float:
        """Score campaign performance."""
        if not summary.get("total_campaigns"):
            return 0.0

        cpa = summary.get("overall_cpa", 0)
        signups = summary.get("total_signups", 0)

        score = 0.3
        if signups > 0:
            score += 0.2
        if signups > 100:
            score += 0.2

        if cpa > 0 and cpa <= self.target_cpa:
            score += 0.3
        elif cpa > 0 and cpa <= self.target_cpa * 2:
            score += 0.15

        return min(score, 1.0)

    def _score_market(self, opp: MarketOpportunity) -> float:
        """Score the underlying market opportunity."""
        return min(opp.opportunity_score + opp.confidence_score, 1.0) / 2

    def _determine_status(
        self,
        verdict: ValidationVerdict,
        stats: WaitlistStats,
    ) -> str:
        if verdict.overall_score >= 0.7 and stats.active_signups >= self.min_signups:
            return "go"
        elif verdict.overall_score >= 0.5 or stats.active_signups >= self.min_signups * 0.5:
            return "promising"
        elif verdict.overall_score < 0.3 and stats.active_signups > 0:
            return "no_go"
        else:
            return "insufficient_data"

    def _calculate_confidence(
        self,
        verdict: ValidationVerdict,
        stats: WaitlistStats,
        summary: Dict,
    ) -> float:
        confidence = 0.2

        if stats.active_signups >= 100:
            confidence += 0.3
        elif stats.active_signups >= 50:
            confidence += 0.2
        elif stats.active_signups >= 10:
            confidence += 0.1

        if summary.get("total_campaigns", 0) >= 2:
            confidence += 0.2
        elif summary.get("total_campaigns", 0) >= 1:
            confidence += 0.1

        platforms = len(summary.get("platforms_used", []))
        if platforms >= 2:
            confidence += 0.15
        elif platforms >= 1:
            confidence += 0.1

        if stats.growth_rate > 0:
            confidence += 0.15

        return min(confidence, 1.0)

    def _add_reasons(
        self,
        verdict: ValidationVerdict,
        stats: WaitlistStats,
        summary: Dict,
    ):
        if stats.active_signups >= self.min_signups:
            verdict.reasons.append(
                f"Waitlist target reached: {stats.active_signups}/{self.min_signups}"
            )
        elif stats.active_signups > 0:
            verdict.reasons.append(
                f"Waitlist progress: {stats.active_signups}/{self.min_signups} "
                f"({stats.active_signups / self.min_signups * 100:.0f}%)"
            )

        cpa = summary.get("overall_cpa", 0)
        if cpa > 0:
            if cpa <= self.target_cpa:
                verdict.reasons.append(f"CPA is on target: {cpa:.2f} GBP (target: {self.target_cpa})")
            else:
                verdict.blockers.append(
                    f"CPA too high: {cpa:.2f} GBP (target: {self.target_cpa}). "
                    "Optimize ad copy or targeting."
                )

        if stats.growth_rate > 20:
            verdict.reasons.append(f"Strong growth: {stats.growth_rate:.0f}% week-over-week")
        elif stats.growth_rate < 0:
            verdict.blockers.append(f"Declining signups: {stats.growth_rate:.0f}% week-over-week")

        if not summary.get("total_campaigns"):
            verdict.blockers.append("No campaigns run yet. Cannot validate demand without advertising.")

    def _add_recommendations(
        self,
        verdict: ValidationVerdict,
        stats: WaitlistStats,
        summary: Dict,
    ):
        if verdict.status == "go":
            verdict.recommendations = [
                "Proceed to product build phase.",
                "Maintain waitlist engagement with update emails.",
                "Start building MVP targeting the top pain points.",
                f"Current waitlist of {stats.active_signups} represents your initial customer base.",
            ]
        elif verdict.status == "promising":
            remaining = self.min_signups - stats.active_signups
            verdict.recommendations = [
                f"Need {remaining} more signups to reach validation threshold.",
                "Continue running campaigns -- optimize based on A/B test winners.",
                "Consider expanding to additional platforms.",
            ]
            if stats.days_to_threshold:
                verdict.recommendations.append(
                    f"At current rate, threshold will be reached in ~{stats.days_to_threshold} days."
                )
        elif verdict.status == "no_go":
            verdict.recommendations = [
                "Demand signal is weak. Consider:",
                "1. Pivoting the value proposition or target audience",
                "2. Testing different pain points in ad copy",
                "3. Investigating a different niche entirely",
                "4. Checking if the landing page clearly communicates value",
            ]
        else:
            verdict.recommendations = [
                "Start with a small ad campaign (50-100 GBP) to test demand.",
                "Create A/B ad variants targeting different pain points.",
                "Build a simple landing page with waitlist signup form.",
            ]
