"""
Niche Finder

Identifies profitable niches by cross-referencing search trends,
pain point density, competition levels, and audience size.

The strategy from the requirements: Grace should find the path of
least resistance to start generating revenue. She picks niches
within her training knowledge or where she has data advantages.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from business_intelligence.models.data_models import (
    MarketDataPoint,
    PainPoint,
    MarketOpportunity,
    OpportunityType,
    ProductType,
    DataSource,
)
from business_intelligence.synthesis.trend_detector import TrendSignal

logger = logging.getLogger(__name__)


@dataclass
class NicheCandidate:
    """A potential niche to target."""
    name: str = ""
    keywords: List[str] = field(default_factory=list)
    pain_point_density: float = 0.0  # pain points per keyword
    competition_level: float = 0.0  # 0-1
    trend_direction: str = "stable"
    search_volume_signal: float = 0.0
    audience_accessibility: float = 0.0  # how easy to reach the audience
    grace_advantage: float = 0.0  # Grace's inherent advantage in this niche
    overall_score: float = 0.0
    rationale: str = ""
    recommended_products: List[ProductType] = field(default_factory=list)


GRACE_ADVANTAGE_DOMAINS = {
    "ai": 0.9,
    "artificial intelligence": 0.9,
    "machine learning": 0.85,
    "automation": 0.85,
    "programming": 0.8,
    "coding": 0.8,
    "software": 0.8,
    "data": 0.8,
    "analytics": 0.8,
    "crypto": 0.7,
    "trading": 0.7,
    "finance": 0.7,
    "marketing": 0.65,
    "seo": 0.65,
    "content creation": 0.6,
    "ecommerce": 0.6,
    "saas": 0.8,
    "no-code": 0.7,
    "productivity": 0.6,
    "education": 0.6,
    "tutoring": 0.6,
}


class NicheFinder:
    """Identifies and scores potential market niches."""

    async def find_niches(
        self,
        data_points: List[MarketDataPoint],
        pain_points: List[PainPoint],
        trends: Optional[List[TrendSignal]] = None,
    ) -> List[NicheCandidate]:
        """Find and score potential niches from collected data."""
        niche_data: Dict[str, Dict[str, Any]] = {}

        for dp in data_points:
            niche = dp.niche or "unknown"
            if niche not in niche_data:
                niche_data[niche] = {
                    "keywords": set(),
                    "data_points": 0,
                    "sources": set(),
                    "prices": [],
                    "ratings": [],
                }
            niche_data[niche]["keywords"].update(dp.keywords)
            niche_data[niche]["data_points"] += 1
            niche_data[niche]["sources"].add(dp.source.value)

            if dp.unit in ("GBP", "USD") and dp.metric_value > 0:
                niche_data[niche]["prices"].append(dp.metric_value)
            if dp.unit == "rating" and dp.metric_value > 0:
                niche_data[niche]["ratings"].append(dp.metric_value)

        niche_pains: Dict[str, List[PainPoint]] = {}
        for pp in pain_points:
            niche = pp.niche or "unknown"
            niche_pains.setdefault(niche, []).append(pp)

        niche_trends: Dict[str, TrendSignal] = {}
        if trends:
            for t in trends:
                if t.niche:
                    niche_trends[t.niche] = t

        candidates = []
        for niche, data in niche_data.items():
            if niche == "unknown":
                continue

            candidate = self._score_niche(
                niche, data, niche_pains.get(niche, []),
                niche_trends.get(niche),
            )
            candidates.append(candidate)

        candidates.sort(key=lambda c: c.overall_score, reverse=True)
        return candidates

    def _score_niche(
        self,
        niche: str,
        data: Dict[str, Any],
        pain_points: List[PainPoint],
        trend: Optional[TrendSignal],
    ) -> NicheCandidate:
        """Score a single niche candidate."""
        keywords = list(data["keywords"])

        pp_density = len(pain_points) / max(len(keywords), 1)
        pp_score = min(pp_density / 3, 1.0)

        ratings = data.get("ratings", [])
        avg_rating = sum(ratings) / len(ratings) if ratings else 3.5
        competition_score = 1.0 - (avg_rating / 5.0)

        trend_dir = "stable"
        trend_score = 0.5
        if trend:
            trend_dir = trend.direction
            if trend.direction == "rising":
                trend_score = 0.5 + trend.strength * 0.5
            elif trend.direction == "declining":
                trend_score = 0.5 - trend.strength * 0.3
            elif trend.direction == "volatile":
                trend_score = 0.4

        source_count = len(data["sources"])
        accessibility = min(source_count / 5, 1.0)

        grace_adv = self._calculate_grace_advantage(niche, keywords)

        overall = (
            pp_score * 0.25 +
            competition_score * 0.15 +
            trend_score * 0.20 +
            accessibility * 0.15 +
            grace_adv * 0.25
        )

        products = self._recommend_product_types(niche, pain_points, grace_adv)

        rationale = self._generate_rationale(
            niche, pp_score, competition_score, trend_dir, grace_adv, products
        )

        return NicheCandidate(
            name=niche,
            keywords=keywords,
            pain_point_density=round(pp_density, 3),
            competition_level=round(1 - competition_score, 3),
            trend_direction=trend_dir,
            search_volume_signal=round(trend_score, 3),
            audience_accessibility=round(accessibility, 3),
            grace_advantage=round(grace_adv, 3),
            overall_score=round(overall, 4),
            rationale=rationale,
            recommended_products=products,
        )

    def _calculate_grace_advantage(
        self, niche: str, keywords: List[str]
    ) -> float:
        """Calculate Grace's inherent advantage in this niche."""
        niche_lower = niche.lower()
        best_match = 0.0

        for domain, score in GRACE_ADVANTAGE_DOMAINS.items():
            if domain in niche_lower:
                best_match = max(best_match, score)

        for kw in keywords:
            for domain, score in GRACE_ADVANTAGE_DOMAINS.items():
                if domain in kw.lower():
                    best_match = max(best_match, score * 0.8)

        if best_match == 0:
            best_match = 0.3

        return best_match

    def _recommend_product_types(
        self,
        niche: str,
        pain_points: List[PainPoint],
        grace_advantage: float,
    ) -> List[ProductType]:
        """Recommend product types based on niche and Grace's capabilities."""
        recommendations = []

        if grace_advantage > 0.7:
            recommendations.append(ProductType.AI_AUTOMATION)
            recommendations.append(ProductType.SAAS)

        if pain_points:
            avg_severity = sum(p.severity for p in pain_points) / len(pain_points)
            if avg_severity > 0.6:
                recommendations.append(ProductType.SAAS)
            recommendations.append(ProductType.ONLINE_COURSE)
            recommendations.append(ProductType.EBOOK_PDF)

        if not recommendations:
            recommendations = [ProductType.ONLINE_COURSE, ProductType.EBOOK_PDF]

        recommendations.append(ProductType.TEMPLATE_TOOLKIT)

        seen = set()
        unique = []
        for r in recommendations:
            if r not in seen:
                seen.add(r)
                unique.append(r)

        return unique[:4]

    def _generate_rationale(
        self,
        niche: str,
        pp_score: float,
        comp_score: float,
        trend: str,
        grace_adv: float,
        products: List[ProductType],
    ) -> str:
        """Generate human-readable rationale for niche selection."""
        parts = []

        if pp_score > 0.6:
            parts.append(f"High pain point density in {niche}")
        elif pp_score > 0.3:
            parts.append(f"Moderate pain points in {niche}")
        else:
            parts.append(f"Low pain signal in {niche}")

        if comp_score > 0.5:
            parts.append("competition appears weak")
        else:
            parts.append("competition is moderate-strong")

        if trend == "rising":
            parts.append("demand is growing")
        elif trend == "declining":
            parts.append("but demand is declining -- caution advised")

        if grace_adv > 0.7:
            parts.append("Grace has strong domain advantage here")
        elif grace_adv > 0.5:
            parts.append("Grace has moderate domain knowledge")

        product_names = [p.value.replace("_", " ") for p in products[:3]]
        parts.append(f"recommended products: {', '.join(product_names)}")

        return ". ".join(parts).capitalize() + "."
