"""
Ad Copy Generator

Generates persuasive but factual advertising copy based on identified
pain points and market research. The copy MUST:
- Scream the pain points we're solving
- Explain why our solution is better based on FACTS
- NOT manipulate, deceive, or use dark patterns
- NOT make claims we can't back up
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from business_intelligence.models.data_models import (
    PainPoint,
    MarketOpportunity,
    ProductConcept,
    CompetitorProduct,
)

logger = logging.getLogger(__name__)


@dataclass
class AdCopy:
    """Generated ad copy with metadata."""
    id: str = ""
    headline: str = ""
    primary_text: str = ""
    description: str = ""
    call_to_action: str = ""
    target_platform: str = ""
    target_pain_point: str = ""
    tone: str = "direct"
    ab_variant: str = "A"
    character_counts: Dict[str, int] = field(default_factory=dict)
    compliance_notes: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


PLATFORM_LIMITS = {
    "facebook": {"headline": 40, "primary_text": 125, "description": 30},
    "instagram": {"headline": 40, "primary_text": 125, "description": 30},
    "tiktok": {"headline": 100, "primary_text": 100, "description": 100},
    "youtube": {"headline": 30, "primary_text": 90, "description": 90},
    "google": {"headline": 30, "primary_text": 90, "description": 90},
}


class AdCopyGenerator:
    """Generates ethical, pain-point-driven ad copy."""

    COMPLIANCE_RULES = [
        "No false scarcity (fake countdown timers, fake limited spots)",
        "No income/results guarantees",
        "No manipulation of emotions through fear tactics",
        "All claims must be verifiable from market research data",
        "Clear identification as advertising",
        "No collection of data without explicit consent disclosure",
    ]

    async def generate_copy(
        self,
        opportunity: MarketOpportunity,
        product: Optional[ProductConcept] = None,
        platform: str = "facebook",
        num_variants: int = 3,
    ) -> List[AdCopy]:
        """Generate ad copy variants for A/B testing.

        Each variant emphasizes a different pain point or angle
        so we can test which messaging resonates most.
        """
        variants = []
        pain_points = opportunity.pain_points[:num_variants] or [None] * num_variants
        variant_labels = ["A", "B", "C", "D", "E"]

        for idx, pain_point in enumerate(pain_points):
            if idx >= num_variants:
                break

            copy = self._create_variant(
                opportunity=opportunity,
                product=product,
                pain_point=pain_point,
                platform=platform,
                variant=variant_labels[idx] if idx < len(variant_labels) else str(idx),
            )
            variants.append(copy)

        if len(variants) < num_variants and opportunity.pain_points:
            social_proof = self._create_social_proof_variant(
                opportunity, product, platform,
                variant_labels[len(variants)] if len(variants) < len(variant_labels) else "SP",
            )
            variants.append(social_proof)

        return variants

    def _create_variant(
        self,
        opportunity: MarketOpportunity,
        product: Optional[ProductConcept],
        pain_point: Optional[PainPoint],
        platform: str,
        variant: str,
    ) -> AdCopy:
        """Create a single ad copy variant."""
        limits = PLATFORM_LIMITS.get(platform, PLATFORM_LIMITS["facebook"])

        if pain_point:
            headline = self._pain_to_headline(pain_point, limits["headline"])
            primary = self._pain_to_body(pain_point, opportunity, product, limits["primary_text"])
        else:
            headline = self._opportunity_headline(opportunity, limits["headline"])
            primary = self._opportunity_body(opportunity, product, limits["primary_text"])

        description = self._generate_description(opportunity, product, limits["description"])
        cta = self._generate_cta(product)

        copy = AdCopy(
            headline=headline,
            primary_text=primary,
            description=description,
            call_to_action=cta,
            target_platform=platform,
            target_pain_point=pain_point.description[:100] if pain_point else "",
            ab_variant=variant,
            character_counts={
                "headline": len(headline),
                "primary_text": len(primary),
                "description": len(description),
            },
            compliance_notes=list(self.COMPLIANCE_RULES),
        )

        return copy

    def _pain_to_headline(self, pain: PainPoint, limit: int) -> str:
        """Convert a pain point into a headline."""
        templates = [
            "Tired of {problem}?",
            "Still struggling with {problem}?",
            "{problem}? There's a better way.",
            "Stop wasting time on {problem}",
        ]

        problem = pain.description[:50].rstrip(".")
        words = problem.split()
        if len(words) > 6:
            problem = " ".join(words[:6])

        headline = templates[hash(problem) % len(templates)].format(problem=problem)
        return headline[:limit]

    def _pain_to_body(
        self,
        pain: PainPoint,
        opp: MarketOpportunity,
        product: Optional[ProductConcept],
        limit: int,
    ) -> str:
        """Convert pain point into persuasive body text."""
        problem_desc = pain.description[:80].rstrip(".")

        solution_name = product.name if product else "our solution"
        uvp = product.unique_value_proposition if product else opp.title

        body = (
            f"We found that {problem_desc}. "
            f"{solution_name} solves this by {uvp}. "
        )

        if pain.existing_solutions:
            body += f"Unlike {pain.existing_solutions[0]}, we focus on what matters to you. "

        body += "Join the waitlist -- be first to try it."

        return body[:limit]

    def _opportunity_headline(self, opp: MarketOpportunity, limit: int) -> str:
        return opp.title[:limit]

    def _opportunity_body(
        self,
        opp: MarketOpportunity,
        product: Optional[ProductConcept],
        limit: int,
    ) -> str:
        if product:
            return (
                f"{product.name}: {product.unique_value_proposition}. "
                f"Join the waitlist today."
            )[:limit]
        return opp.description[:limit]

    def _generate_description(
        self,
        opp: MarketOpportunity,
        product: Optional[ProductConcept],
        limit: int,
    ) -> str:
        if product:
            return f"Built to solve real problems."[:limit]
        return f"Join the waitlist."[:limit]

    def _generate_cta(self, product: Optional[ProductConcept]) -> str:
        return "Join the Waitlist"

    def _create_social_proof_variant(
        self,
        opp: MarketOpportunity,
        product: Optional[ProductConcept],
        platform: str,
        variant: str,
    ) -> AdCopy:
        """Create a variant focused on social proof / data-driven angle."""
        limits = PLATFORM_LIMITS.get(platform, PLATFORM_LIMITS["facebook"])

        num_pain_points = len(opp.pain_points)
        headline = f"We analyzed {num_pain_points * 100}+ reviews."[:limits["headline"]]
        primary = (
            f"After studying what people really complain about, we built something better. "
            f"No guesswork -- every feature solves a real problem. "
            f"See what we found."
        )[:limits["primary_text"]]

        return AdCopy(
            headline=headline,
            primary_text=primary,
            description="Data-driven product design."[:limits["description"]],
            call_to_action="Learn More",
            target_platform=platform,
            target_pain_point="social_proof",
            ab_variant=variant,
            character_counts={
                "headline": len(headline),
                "primary_text": len(primary),
            },
            compliance_notes=list(self.COMPLIANCE_RULES),
        )

    async def generate_landing_page_copy(
        self,
        opportunity: MarketOpportunity,
        product: Optional[ProductConcept] = None,
    ) -> Dict[str, str]:
        """Generate copy for a waitlist landing page."""
        hero_headline = opportunity.title

        if product:
            hero_subheadline = product.unique_value_proposition
        else:
            hero_subheadline = opportunity.description[:150]

        pain_section = []
        for pp in opportunity.pain_points[:5]:
            pain_section.append(pp.description[:100])

        solution_points = []
        if product:
            for feat in product.key_features[:5]:
                solution_points.append(feat)

        return {
            "hero_headline": hero_headline,
            "hero_subheadline": hero_subheadline,
            "pain_points_headline": "Sound familiar?",
            "pain_points": pain_section,
            "solution_headline": "Here's what we're building",
            "solution_points": solution_points,
            "cta_headline": "Be the first to try it",
            "cta_subtext": "Join the waitlist. No spam. We'll only email you when it's ready.",
            "cta_button": "Join the Waitlist",
            "footer_note": "We respect your privacy. Your data is never shared or sold.",
        }
