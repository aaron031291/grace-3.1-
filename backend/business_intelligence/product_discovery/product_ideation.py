"""
Product Ideation Engine

Takes validated market opportunities and pain points and generates
concrete product concepts. Each concept includes features, pricing,
unique value proposition, and development estimates.

Product types Grace can build:
- SaaS products (code agent capabilities)
- Online courses / tutorials
- Ebooks / PDFs / digital content
- AI automation tools
- Templates / toolkits
- Community memberships
- Consulting services

The key insight: Grace takes negative review feedback and designs
products that specifically address those failures.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import uuid

from business_intelligence.models.data_models import (
    ProductConcept,
    ProductType,
    MarketOpportunity,
    PainPoint,
    CompetitorProduct,
    OpportunityType,
)

logger = logging.getLogger(__name__)


PRODUCT_TEMPLATES = {
    ProductType.SAAS: {
        "development_days": 60,
        "pricing_model": "monthly_subscription",
        "base_price_gbp": 29.00,
        "features_template": [
            "Dashboard with key metrics",
            "Automated workflows",
            "API integrations",
            "Real-time notifications",
            "Data export/import",
        ],
        "uvp_template": "Automate {pain_point} with AI-powered {niche} tools",
    },
    ProductType.ONLINE_COURSE: {
        "development_days": 14,
        "pricing_model": "one_time",
        "base_price_gbp": 97.00,
        "features_template": [
            "Step-by-step video modules",
            "Downloadable resources",
            "Community access",
            "Certificate of completion",
            "Lifetime updates",
        ],
        "uvp_template": "Master {niche} -- from zero to confident in 30 days",
    },
    ProductType.EBOOK_PDF: {
        "development_days": 7,
        "pricing_model": "one_time",
        "base_price_gbp": 19.00,
        "features_template": [
            "Comprehensive guide",
            "Actionable checklists",
            "Real-world examples",
            "Templates included",
            "Free updates",
        ],
        "uvp_template": "The complete {niche} playbook -- everything you need in one place",
    },
    ProductType.AI_AUTOMATION: {
        "development_days": 30,
        "pricing_model": "monthly_subscription",
        "base_price_gbp": 49.00,
        "features_template": [
            "AI-powered automation",
            "Custom workflow builder",
            "Integration with popular tools",
            "Usage analytics",
            "Priority support",
        ],
        "uvp_template": "Let AI handle your {pain_point} -- save hours every week",
    },
    ProductType.TEMPLATE_TOOLKIT: {
        "development_days": 5,
        "pricing_model": "one_time",
        "base_price_gbp": 39.00,
        "features_template": [
            "Ready-to-use templates",
            "Customization guide",
            "Video walkthrough",
            "Regular updates",
            "Bonus resources",
        ],
        "uvp_template": "Professional {niche} templates -- start in minutes, not weeks",
    },
    ProductType.COMMUNITY_MEMBERSHIP: {
        "development_days": 10,
        "pricing_model": "monthly_subscription",
        "base_price_gbp": 19.00,
        "features_template": [
            "Private community access",
            "Weekly live sessions",
            "Resource library",
            "Expert Q&A",
            "Networking opportunities",
        ],
        "uvp_template": "Join the {niche} community -- learn, grow, and connect with peers",
    },
}


class ProductIdeationEngine:
    """Generates product concepts from market intelligence."""

    async def generate_concepts(
        self,
        opportunities: List[MarketOpportunity],
        product_types: Optional[List[ProductType]] = None,
        max_concepts: int = 5,
    ) -> List[ProductConcept]:
        """Generate product concepts from scored opportunities."""
        concepts = []

        for opp in opportunities[:max_concepts]:
            types = product_types or opp.recommended_product_types
            if not types:
                types = [ProductType.ONLINE_COURSE, ProductType.EBOOK_PDF]

            for pt in types[:2]:
                concept = self._create_concept(opp, pt)
                concepts.append(concept)

        concepts.sort(key=lambda c: c.validation_score, reverse=True)
        return concepts[:max_concepts]

    def _create_concept(
        self,
        opportunity: MarketOpportunity,
        product_type: ProductType,
    ) -> ProductConcept:
        """Create a single product concept from an opportunity."""
        template = PRODUCT_TEMPLATES.get(product_type, PRODUCT_TEMPLATES[ProductType.ONLINE_COURSE])

        primary_pain = ""
        if opportunity.pain_points:
            primary_pain = opportunity.pain_points[0].description[:50]

        features = list(template["features_template"])

        for pp in opportunity.pain_points[:3]:
            solution = self._pain_to_feature(pp)
            if solution:
                features.insert(0, solution)

        if opportunity.competitors:
            for comp in opportunity.competitors[:2]:
                for weakness in comp.weaknesses[:1]:
                    features.append(f"Solves: {weakness[:50]}")

        uvp = template["uvp_template"].format(
            niche=opportunity.niche,
            pain_point=primary_pain or opportunity.niche,
        )

        price = self._calculate_price(
            template["base_price_gbp"],
            opportunity,
            product_type,
        )

        advantages = self._identify_advantages(opportunity)

        dev_days = template["development_days"]
        if product_type in (ProductType.SAAS, ProductType.AI_AUTOMATION):
            if len(opportunity.pain_points) > 5:
                dev_days = int(dev_days * 1.5)

        validation_score = self._score_concept(opportunity, product_type)

        name = self._generate_name(opportunity.niche, product_type)

        return ProductConcept(
            name=name,
            description=(
                f"A {product_type.value.replace('_', ' ')} that addresses "
                f"the top pain points in {opportunity.niche}. "
                f"Based on analysis of {len(opportunity.pain_points)} validated pain points "
                f"and {len(opportunity.competitors)} competitor products."
            ),
            product_type=product_type,
            target_niche=opportunity.niche,
            pain_points_addressed=opportunity.pain_points[:5],
            key_features=features[:8],
            unique_value_proposition=uvp,
            pricing_model=template["pricing_model"],
            estimated_price=price,
            currency="GBP",
            competitive_advantages=advantages,
            estimated_development_days=dev_days,
            validation_status="concept",
            validation_score=validation_score,
            supporting_opportunity=opportunity,
        )

    def _pain_to_feature(self, pain_point: PainPoint) -> Optional[str]:
        """Convert a pain point into a product feature."""
        desc = pain_point.description[:100].strip(".")

        category_to_feature = {
            "frustration": f"Eliminates: {desc}",
            "failure": f"Reliable: addresses '{desc}'",
            "waste": f"Cost-effective: solves '{desc}'",
            "missing_feature": f"Includes: {desc}",
            "poor_quality": f"Premium quality: fixes '{desc}'",
            "bad_ux": f"Intuitive design: addresses '{desc}'",
            "slow": f"Fast and responsive: no more '{desc}'",
            "support": f"Dedicated support: fixes '{desc}'",
        }

        return category_to_feature.get(
            pain_point.category, f"Addresses: {desc}"
        )

    def _calculate_price(
        self,
        base_price: float,
        opportunity: MarketOpportunity,
        product_type: ProductType,
    ) -> float:
        """Calculate suggested price based on market data."""
        price = base_price

        if opportunity.competitors:
            competitor_prices = [
                c.price for c in opportunity.competitors if c.price > 0
            ]
            if competitor_prices:
                avg_competitor_price = sum(competitor_prices) / len(competitor_prices)
                if product_type in (ProductType.SAAS, ProductType.AI_AUTOMATION):
                    price = avg_competitor_price * 0.8
                else:
                    price = avg_competitor_price * 0.7

        price = max(price, base_price * 0.5)
        price = min(price, base_price * 3)

        return round(price, 2)

    def _identify_advantages(
        self, opportunity: MarketOpportunity
    ) -> List[str]:
        """Identify competitive advantages based on market gaps."""
        advantages = []

        if opportunity.pain_points:
            top_pain = opportunity.pain_points[0]
            if top_pain.solution_gaps:
                advantages.append(
                    f"Fills solution gap: {top_pain.solution_gaps[0]}"
                )
            if top_pain.severity > 0.7:
                advantages.append(
                    "Addresses a high-severity pain point that competitors ignore"
                )

        if opportunity.competitors:
            low_rated = [c for c in opportunity.competitors if c.rating < 3.5]
            if len(low_rated) > len(opportunity.competitors) * 0.5:
                advantages.append("Competitors have poor customer satisfaction")

        advantages.append("Built from actual customer complaint data, not assumptions")
        advantages.append("AI-powered continuous improvement based on user feedback")

        return advantages[:5]

    def _score_concept(
        self,
        opportunity: MarketOpportunity,
        product_type: ProductType,
    ) -> float:
        """Score a product concept for prioritization."""
        score = opportunity.opportunity_score * 0.5

        quick_build = {
            ProductType.EBOOK_PDF, ProductType.TEMPLATE_TOOLKIT,
        }
        medium_build = {
            ProductType.ONLINE_COURSE, ProductType.COMMUNITY_MEMBERSHIP,
        }

        if product_type in quick_build:
            score += 0.2
        elif product_type in medium_build:
            score += 0.1

        recurring = {ProductType.SAAS, ProductType.COMMUNITY_MEMBERSHIP, ProductType.AI_AUTOMATION}
        if product_type in recurring:
            score += 0.15

        if opportunity.pain_points:
            avg_pain = sum(p.pain_score for p in opportunity.pain_points) / len(opportunity.pain_points)
            score += avg_pain * 0.15

        return min(round(score, 3), 1.0)

    def _generate_name(self, niche: str, product_type: ProductType) -> str:
        """Generate a working product name."""
        niche_word = niche.split()[0].title() if niche else "Smart"

        type_suffixes = {
            ProductType.SAAS: "Pro",
            ProductType.ONLINE_COURSE: "Academy",
            ProductType.EBOOK_PDF: "Guide",
            ProductType.AI_AUTOMATION: "AI",
            ProductType.TEMPLATE_TOOLKIT: "Toolkit",
            ProductType.COMMUNITY_MEMBERSHIP: "Hub",
            ProductType.CONSULTING_SERVICE: "Consulting",
            ProductType.PHYSICAL_PRODUCT: "Pro",
        }

        suffix = type_suffixes.get(product_type, "Solution")
        return f"{niche_word} {suffix}"

    async def refine_concept(
        self,
        concept: ProductConcept,
        additional_pain_points: Optional[List[PainPoint]] = None,
        competitor_weaknesses: Optional[List[str]] = None,
    ) -> ProductConcept:
        """Refine an existing concept with new intelligence."""
        if additional_pain_points:
            concept.pain_points_addressed.extend(additional_pain_points[:3])
            for pp in additional_pain_points[:3]:
                feature = self._pain_to_feature(pp)
                if feature:
                    concept.key_features.append(feature)

        if competitor_weaknesses:
            for weakness in competitor_weaknesses[:3]:
                concept.competitive_advantages.append(
                    f"Addresses competitor weakness: {weakness}"
                )

        concept.validation_status = "refined"
        return concept

    async def generate_product_ladder(
        self,
        niche: str,
        opportunity: MarketOpportunity,
    ) -> List[ProductConcept]:
        """Generate a product ladder -- multiple products at different price
        points that feed into each other.

        The "all three things" from the requirements: course + SaaS + content
        where each seeds the next.
        """
        ladder = []

        lead_magnet = self._create_concept(
            opportunity, ProductType.EBOOK_PDF
        )
        lead_magnet.estimated_price = 0.0
        lead_magnet.pricing_model = "free_lead_magnet"
        lead_magnet.description = (
            f"Free resource that demonstrates expertise in {niche}. "
            "Used to build the email list and establish trust."
        )
        ladder.append(lead_magnet)

        mid_ticket = self._create_concept(
            opportunity, ProductType.ONLINE_COURSE
        )
        ladder.append(mid_ticket)

        high_ticket = self._create_concept(
            opportunity, ProductType.SAAS
        )
        ladder.append(high_ticket)

        community = self._create_concept(
            opportunity, ProductType.COMMUNITY_MEMBERSHIP
        )
        ladder.append(community)

        return ladder
