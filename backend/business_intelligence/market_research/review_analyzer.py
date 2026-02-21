"""
Review Analyzer

Reads product reviews from Amazon, Trustpilot, G2, and other platforms.
Extracts structured intelligence from negative reviews specifically --
these are the gold mine for product improvement opportunities.

The core insight: a 1-star review is a customer telling you exactly
what to build. Grace reads thousands of these and synthesizes them.
"""

import logging
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from business_intelligence.models.data_models import (
    ReviewAnalysis,
    PainPoint,
    CompetitorProduct,
    DataSource,
    Sentiment,
)

logger = logging.getLogger(__name__)


@dataclass
class ReviewIntelligence:
    """Synthesized intelligence from a batch of reviews."""
    product_name: str = ""
    total_reviews_analyzed: int = 0
    avg_rating: float = 0.0
    sentiment_distribution: Dict[str, int] = field(default_factory=dict)
    top_pain_points: List[str] = field(default_factory=list)
    top_praise_points: List[str] = field(default_factory=list)
    feature_requests: List[str] = field(default_factory=list)
    competitive_weaknesses: List[str] = field(default_factory=list)
    improvement_opportunities: List[str] = field(default_factory=list)
    price_complaints: int = 0
    quality_complaints: int = 0
    support_complaints: int = 0
    demographic_signals: Dict[str, int] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


NEGATION_WORDS = {"not", "no", "never", "don't", "doesn't", "didn't", "won't", "can't", "couldn't", "isn't", "aren't", "wasn't", "weren't"}

FEATURE_REQUEST_PATTERNS = [
    re.compile(r"wish (?:it|they|this) (?:had|would|could) (.+?)(?:\.|,|!|$)", re.IGNORECASE),
    re.compile(r"if only (?:it|they|this) (.+?)(?:\.|,|!|$)", re.IGNORECASE),
    re.compile(r"(?:need|want|looking for) (?:a |an )?(.+?)(?:\.|,|!|$)", re.IGNORECASE),
    re.compile(r"should (?:have|include|add|support) (.+?)(?:\.|,|!|$)", re.IGNORECASE),
    re.compile(r"would be (?:great|nice|better|perfect) if (.+?)(?:\.|,|!|$)", re.IGNORECASE),
]

COMPLAINT_CATEGORIES = {
    "price": [r"expensiv", r"overpriced", r"cost(s|ed)? too much", r"not worth the (price|money)", r"cheap(er)? alternative"],
    "quality": [r"broke", r"fell apart", r"cheap(ly)? made", r"poor quality", r"flimsy", r"defective"],
    "support": [r"customer (service|support)", r"no (help|response|reply)", r"terrible support", r"can't reach"],
    "usability": [r"confusing", r"hard to", r"complicated", r"unintuitive", r"steep learning"],
    "performance": [r"slow", r"laggy", r"crashes?", r"freeze", r"unresponsive", r"bug(gy|s)?"],
    "delivery": [r"shipping", r"deliver", r"arrived (late|damaged|broken)", r"packaging"],
    "misleading": [r"misleading", r"false advertis", r"not as described", r"different from (picture|photo|image|ad)"],
}


class ReviewAnalyzer:
    """Analyzes product reviews for pain points and opportunities."""

    def __init__(self):
        self._compiled_complaints = {
            cat: [re.compile(p, re.IGNORECASE) for p in patterns]
            for cat, patterns in COMPLAINT_CATEGORIES.items()
        }

    async def analyze_reviews(
        self,
        reviews: List[Dict[str, Any]],
        product_name: str = "",
    ) -> ReviewIntelligence:
        """Analyze a batch of reviews and produce intelligence."""
        analyzed = []
        for review in reviews:
            analyzed.append(self._analyze_single_review(review))

        return self._synthesize(analyzed, product_name)

    def _analyze_single_review(self, review: Dict[str, Any]) -> ReviewAnalysis:
        """Analyze a single review for sentiment and pain points."""
        text = review.get("text", review.get("body", review.get("content", "")))
        rating = float(review.get("rating", review.get("stars", 3)))
        title = review.get("title", "")

        full_text = f"{title} {text}".strip()

        sentiment = self._classify_sentiment(rating, full_text)
        pain_points = self._extract_pain_points(full_text) if sentiment.value < 0 else []
        feature_requests = self._extract_feature_requests(full_text)
        praise_points = self._extract_praise_points(full_text) if sentiment.value > 0 else []

        return ReviewAnalysis(
            product_name=review.get("product_name", ""),
            platform=review.get("platform", "unknown"),
            rating=rating,
            review_text=full_text,
            sentiment=sentiment,
            pain_points_extracted=pain_points,
            feature_requests=feature_requests,
            praise_points=praise_points,
            reviewer_demographics=self._extract_demographics(full_text),
        )

    def _classify_sentiment(self, rating: float, text: str) -> Sentiment:
        if rating <= 1.5:
            return Sentiment.VERY_NEGATIVE
        elif rating <= 2.5:
            return Sentiment.NEGATIVE
        elif rating <= 3.5:
            return Sentiment.NEUTRAL
        elif rating <= 4.5:
            return Sentiment.POSITIVE
        else:
            return Sentiment.VERY_POSITIVE

    def _extract_pain_points(self, text: str) -> List[str]:
        """Extract specific complaints from review text."""
        pain_points = []

        for category, patterns in self._compiled_complaints.items():
            for pattern in patterns:
                matches = pattern.finditer(text)
                for match in matches:
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 100)
                    context = text[start:end].strip()
                    pain_points.append(f"[{category}] {context}")

        return pain_points[:10]

    def _extract_feature_requests(self, text: str) -> List[str]:
        """Extract feature requests and wishes from review text."""
        requests = []
        for pattern in FEATURE_REQUEST_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                cleaned = match.strip()
                if len(cleaned) > 5:
                    requests.append(cleaned[:200])
        return requests[:5]

    def _extract_praise_points(self, text: str) -> List[str]:
        """Extract what customers love -- important for knowing what to keep."""
        praise_patterns = [
            re.compile(r"(?:love|great|excellent|amazing|perfect|best) (.+?)(?:\.|,|!|$)", re.IGNORECASE),
            re.compile(r"(?:exactly what|just what) (?:I|we) (?:needed|wanted|was looking for)", re.IGNORECASE),
        ]

        praises = []
        for pattern in praise_patterns:
            matches = pattern.findall(text)
            for match in matches:
                if isinstance(match, str) and len(match) > 3:
                    praises.append(match.strip()[:200])
        return praises[:5]

    def _extract_demographics(self, text: str) -> Dict[str, Any]:
        """Extract demographic signals from review text.
        Only captures self-disclosed, non-PII information."""
        demographics = {}

        profession_patterns = [
            (r"as a (\w+ \w+)", "self_identified_role"),
            (r"I('m| am) a (\w+)", "self_identified_role"),
            (r"for my (\w+) business", "business_type"),
        ]

        for pattern, key in profession_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                demographics[key] = match.group(1) if match.lastindex == 1 else match.group(2)

        usage_patterns = {
            "beginner": r"beginner|new to|first time|just started",
            "professional": r"professional|expert|years of experience|advanced",
            "small_business": r"small business|startup|entrepreneur|freelanc",
            "enterprise": r"enterprise|large (team|company|organization)",
        }

        for level, pattern in usage_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                demographics["usage_level"] = level
                break

        return demographics

    def _synthesize(
        self,
        analyses: List[ReviewAnalysis],
        product_name: str,
    ) -> ReviewIntelligence:
        """Synthesize individual analyses into aggregate intelligence."""
        if not analyses:
            return ReviewIntelligence(product_name=product_name)

        sentiment_dist = Counter(a.sentiment.name for a in analyses)
        all_pain_points = []
        all_praise = []
        all_feature_requests = []
        price_complaints = 0
        quality_complaints = 0
        support_complaints = 0
        demographic_counter: Counter = Counter()

        for a in analyses:
            all_pain_points.extend(a.pain_points_extracted)
            all_praise.extend(a.praise_points)
            all_feature_requests.extend(a.feature_requests)

            for pp in a.pain_points_extracted:
                if "[price]" in pp.lower():
                    price_complaints += 1
                if "[quality]" in pp.lower():
                    quality_complaints += 1
                if "[support]" in pp.lower():
                    support_complaints += 1

            for key, val in a.reviewer_demographics.items():
                if isinstance(val, str):
                    demographic_counter[f"{key}:{val}"] += 1

        pain_counter = Counter(all_pain_points)
        praise_counter = Counter(all_praise)
        feature_counter = Counter(all_feature_requests)

        avg_rating = sum(a.rating for a in analyses) / len(analyses)

        weaknesses = []
        negative_analyses = [a for a in analyses if a.sentiment.value < 0]
        if negative_analyses:
            neg_ratio = len(negative_analyses) / len(analyses)
            if neg_ratio > 0.3:
                weaknesses.append(f"High negative sentiment: {neg_ratio:.0%} of reviews are negative")
            if price_complaints > len(analyses) * 0.2:
                weaknesses.append("Frequent price complaints")
            if quality_complaints > len(analyses) * 0.15:
                weaknesses.append("Quality issues reported")
            if support_complaints > len(analyses) * 0.1:
                weaknesses.append("Customer support problems")

        improvements = []
        for pp, count in pain_counter.most_common(5):
            improvements.append(f"Address: {pp} (mentioned {count}x)")
        for fr, count in feature_counter.most_common(3):
            improvements.append(f"Add feature: {fr} (requested {count}x)")

        return ReviewIntelligence(
            product_name=product_name,
            total_reviews_analyzed=len(analyses),
            avg_rating=round(avg_rating, 2),
            sentiment_distribution=dict(sentiment_dist),
            top_pain_points=[pp for pp, _ in pain_counter.most_common(10)],
            top_praise_points=[p for p, _ in praise_counter.most_common(5)],
            feature_requests=[fr for fr, _ in feature_counter.most_common(5)],
            competitive_weaknesses=weaknesses,
            improvement_opportunities=improvements,
            price_complaints=price_complaints,
            quality_complaints=quality_complaints,
            support_complaints=support_complaints,
            demographic_signals=dict(demographic_counter.most_common(10)),
        )

    async def compare_competitors(
        self,
        product_reviews: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        """Compare review intelligence across competing products.

        Returns a competitive landscape analysis showing where each
        product excels and fails, revealing gaps in the market.
        """
        intelligences: Dict[str, ReviewIntelligence] = {}

        for product_name, reviews in product_reviews.items():
            intel = await self.analyze_reviews(reviews, product_name)
            intelligences[product_name] = intel

        comparison = {
            "products_analyzed": len(intelligences),
            "products": {},
            "market_gaps": [],
            "universal_pain_points": [],
            "best_in_class_features": [],
        }

        all_pain_points: Counter = Counter()
        all_praises: Counter = Counter()

        for name, intel in intelligences.items():
            comparison["products"][name] = {
                "avg_rating": intel.avg_rating,
                "review_count": intel.total_reviews_analyzed,
                "top_weaknesses": intel.competitive_weaknesses[:3],
                "top_strengths": intel.top_praise_points[:3],
                "feature_requests": intel.feature_requests[:3],
            }

            for pp in intel.top_pain_points:
                all_pain_points[pp] += 1
            for praise in intel.top_praise_points:
                all_praises[praise] += 1

        num_products = len(intelligences)
        for pp, count in all_pain_points.most_common(10):
            if count >= max(2, num_products * 0.5):
                comparison["universal_pain_points"].append({
                    "pain_point": pp,
                    "affected_products": count,
                    "opportunity": "Nobody is solving this well",
                })

        for praise, count in all_praises.most_common(5):
            if count <= 1:
                comparison["best_in_class_features"].append({
                    "feature": praise,
                    "unique_to": count,
                    "note": "Only one competitor does this well",
                })

        return comparison
