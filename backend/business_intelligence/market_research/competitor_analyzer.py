"""
Competitor Analysis Engine

Systematically analyzes competitors in a given niche:
- Product features and pricing
- Market positioning
- Strengths and weaknesses from reviews
- Content and SEO strategy
- Gap identification
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import Counter

from business_intelligence.models.data_models import (
    CompetitorProduct,
    MarketDataPoint,
    PainPoint,
    MarketOpportunity,
    OpportunityType,
    DataSource,
)

logger = logging.getLogger(__name__)


@dataclass
class CompetitorLandscape:
    """Complete competitive landscape for a niche."""
    niche: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    competitors: List[CompetitorProduct] = field(default_factory=list)
    total_products: int = 0
    avg_price: float = 0.0
    price_range: Dict[str, float] = field(default_factory=dict)
    avg_rating: float = 0.0
    market_concentration: float = 0.0  # 0 = fragmented, 1 = monopolized
    pricing_gaps: List[Dict] = field(default_factory=list)
    feature_gaps: List[str] = field(default_factory=list)
    underserved_segments: List[str] = field(default_factory=list)
    content_gaps: List[str] = field(default_factory=list)
    entry_difficulty: float = 0.0  # 0 = easy, 1 = very hard
    recommendations: List[str] = field(default_factory=list)


class CompetitorAnalyzer:
    """Analyzes competitor landscape in a market niche."""

    async def analyze_landscape(
        self,
        niche: str,
        competitors: List[CompetitorProduct],
        market_data: Optional[List[MarketDataPoint]] = None,
    ) -> CompetitorLandscape:
        """Build a complete competitive landscape analysis."""
        if not competitors:
            return CompetitorLandscape(niche=niche)

        landscape = CompetitorLandscape(
            niche=niche,
            competitors=competitors,
            total_products=len(competitors),
        )

        self._analyze_pricing(landscape)
        self._analyze_ratings(landscape)
        self._analyze_features(landscape)
        self._assess_entry_difficulty(landscape)
        self._generate_recommendations(landscape)

        if market_data:
            self._enrich_with_market_data(landscape, market_data)

        return landscape

    def _analyze_pricing(self, landscape: CompetitorLandscape):
        """Analyze pricing structure and find gaps."""
        prices = [c.price for c in landscape.competitors if c.price > 0]
        if not prices:
            return

        landscape.avg_price = sum(prices) / len(prices)
        landscape.price_range = {
            "min": min(prices),
            "max": max(prices),
            "median": sorted(prices)[len(prices) // 2],
        }

        sorted_prices = sorted(prices)
        for i in range(len(sorted_prices) - 1):
            gap = sorted_prices[i + 1] - sorted_prices[i]
            if gap > landscape.avg_price * 0.3:
                landscape.pricing_gaps.append({
                    "lower_bound": sorted_prices[i],
                    "upper_bound": sorted_prices[i + 1],
                    "gap_size": gap,
                    "opportunity": f"Price point between {sorted_prices[i]:.2f} and {sorted_prices[i + 1]:.2f} is unoccupied",
                })

        budget_count = sum(1 for p in prices if p < landscape.avg_price * 0.5)
        premium_count = sum(1 for p in prices if p > landscape.avg_price * 1.5)

        if budget_count < len(prices) * 0.1:
            landscape.pricing_gaps.append({
                "segment": "budget",
                "opportunity": "Budget segment is underserved",
                "suggested_price": landscape.price_range["min"] * 0.6,
            })

        if premium_count < len(prices) * 0.1:
            landscape.pricing_gaps.append({
                "segment": "premium",
                "opportunity": "Premium segment has few options",
                "suggested_price": landscape.price_range["max"] * 1.3,
            })

    def _analyze_ratings(self, landscape: CompetitorLandscape):
        """Analyze customer satisfaction across competitors."""
        ratings = [c.rating for c in landscape.competitors if c.rating > 0]
        if not ratings:
            return

        landscape.avg_rating = sum(ratings) / len(ratings)

        if landscape.avg_rating < 3.5:
            landscape.recommendations.append(
                f"Market avg rating is low ({landscape.avg_rating:.1f}). "
                "Strong quality play could capture market share."
            )

        low_rated = [
            c for c in landscape.competitors
            if 0 < c.rating < 3.0
        ]
        if len(low_rated) > len(landscape.competitors) * 0.3:
            landscape.underserved_segments.append(
                "High proportion of low-rated products -- customers want better quality"
            )

    def _analyze_features(self, landscape: CompetitorLandscape):
        """Identify feature gaps across competitors."""
        feature_counter: Counter = Counter()
        weakness_counter: Counter = Counter()

        for comp in landscape.competitors:
            for feat in comp.features:
                feature_counter[feat.lower().strip()] += 1
            for weak in comp.weaknesses:
                weakness_counter[weak.lower().strip()] += 1
            for neg in comp.negative_review_themes:
                weakness_counter[neg.lower().strip()] += 1

        num_competitors = len(landscape.competitors)

        for feature, count in feature_counter.items():
            if count < num_competitors * 0.3 and len(feature) > 3:
                landscape.feature_gaps.append(
                    f"Only {count}/{num_competitors} competitors offer: {feature}"
                )

        for weakness, count in weakness_counter.most_common(10):
            if count >= max(2, num_competitors * 0.3) and len(weakness) > 3:
                landscape.feature_gaps.append(
                    f"Common weakness ({count} competitors): {weakness}"
                )

    def _assess_entry_difficulty(self, landscape: CompetitorLandscape):
        """Estimate how hard it is to enter this market."""
        difficulty = 0.0
        num = landscape.total_products

        if num > 50:
            difficulty += 0.3
        elif num > 20:
            difficulty += 0.2
        elif num > 5:
            difficulty += 0.1

        if landscape.avg_rating > 4.0:
            difficulty += 0.2

        review_counts = [c.review_count for c in landscape.competitors if c.review_count > 0]
        if review_counts:
            avg_reviews = sum(review_counts) / len(review_counts)
            if avg_reviews > 1000:
                difficulty += 0.2
            elif avg_reviews > 100:
                difficulty += 0.1

        if not landscape.pricing_gaps:
            difficulty += 0.15

        landscape.entry_difficulty = min(difficulty, 1.0)

    def _generate_recommendations(self, landscape: CompetitorLandscape):
        """Generate strategic recommendations based on analysis."""
        if landscape.entry_difficulty < 0.3:
            landscape.recommendations.append(
                "Low barrier to entry -- move fast, first-mover advantage matters"
            )
        elif landscape.entry_difficulty > 0.7:
            landscape.recommendations.append(
                "High barrier to entry -- differentiation through unique features or niche targeting is essential"
            )

        if landscape.pricing_gaps:
            best_gap = max(
                [g for g in landscape.pricing_gaps if "gap_size" in g],
                key=lambda g: g.get("gap_size", 0),
                default=None,
            )
            if best_gap:
                landscape.recommendations.append(
                    f"Pricing opportunity: {best_gap['opportunity']}"
                )

        if landscape.feature_gaps:
            landscape.recommendations.append(
                f"Top feature gap: {landscape.feature_gaps[0]}"
            )

        if landscape.avg_rating < 3.5:
            landscape.recommendations.append(
                "Quality play: this market tolerates poor products. A well-built alternative wins."
            )

    def _enrich_with_market_data(
        self,
        landscape: CompetitorLandscape,
        market_data: List[MarketDataPoint],
    ):
        """Enrich landscape with additional market data."""
        trend_data = [
            dp for dp in market_data
            if dp.category == "trends"
        ]
        for trend in trend_data:
            direction = trend.metadata.get("trend_direction", "stable")
            if direction == "rising":
                landscape.recommendations.append(
                    f"Rising search interest for '{', '.join(trend.keywords)}' -- timing is good"
                )
            elif direction == "declining":
                landscape.recommendations.append(
                    f"Declining search interest for '{', '.join(trend.keywords)}' -- validate demand before investing"
                )

    async def find_opportunities(
        self,
        landscape: CompetitorLandscape,
        pain_points: Optional[List[PainPoint]] = None,
    ) -> List[MarketOpportunity]:
        """Convert landscape analysis into scored opportunities."""
        opportunities = []

        for gap in landscape.pricing_gaps:
            opp = MarketOpportunity(
                title=f"Pricing Gap: {gap.get('opportunity', 'Unoccupied price point')}",
                description=str(gap),
                niche=landscape.niche,
                opportunity_type=OpportunityType.PRICING_GAP,
                confidence_score=0.6,
                opportunity_score=0.5,
                entry_barriers=[
                    f"Entry difficulty: {landscape.entry_difficulty:.0%}"
                ],
            )
            opportunities.append(opp)

        for gap_desc in landscape.feature_gaps[:5]:
            opp = MarketOpportunity(
                title=f"Feature Gap: {gap_desc[:100]}",
                description=gap_desc,
                niche=landscape.niche,
                opportunity_type=OpportunityType.FEATURE_GAP,
                confidence_score=0.55,
                opportunity_score=0.6,
            )
            if pain_points:
                related_pps = [
                    pp for pp in pain_points
                    if any(kw in gap_desc.lower() for kw in pp.description.lower().split()[:5])
                ]
                opp.pain_points = related_pps[:3]

            opportunities.append(opp)

        if landscape.avg_rating < 3.5:
            opp = MarketOpportunity(
                title=f"Quality Opportunity in {landscape.niche}",
                description=f"Market average rating is {landscape.avg_rating:.1f}. A quality-focused product could dominate.",
                niche=landscape.niche,
                opportunity_type=OpportunityType.PRODUCT_IMPROVEMENT,
                confidence_score=0.7,
                opportunity_score=0.75,
                pain_points=pain_points[:5] if pain_points else [],
            )
            opportunities.append(opp)

        opportunities.sort(key=lambda o: o.opportunity_score, reverse=True)
        return opportunities
