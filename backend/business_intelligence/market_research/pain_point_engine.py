"""
Pain Point Discovery Engine

Extracts, clusters, and ranks customer pain points from multiple data sources.
This is the heart of the "read negative reviews and make it better" strategy.

The engine:
1. Collects raw complaint/frustration signals from forums, reviews, social
2. Clusters similar complaints into pain point themes
3. Scores pain points by severity * frequency * market size
4. Identifies solution gaps where no adequate solution exists
5. Ranks opportunities by pain_score * solution_gap_size
"""

import logging
import re
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from business_intelligence.models.data_models import (
    PainPoint,
    ReviewAnalysis,
    MarketDataPoint,
    DataSource,
    Sentiment,
)

logger = logging.getLogger(__name__)


@dataclass
class PainPointCluster:
    """A cluster of related pain points."""
    theme: str = ""
    pain_points: List[PainPoint] = field(default_factory=list)
    total_frequency: int = 0
    avg_severity: float = 0.0
    composite_score: float = 0.0
    keywords: List[str] = field(default_factory=list)
    solution_gap: float = 0.0
    sources: List[str] = field(default_factory=list)


PAIN_PATTERNS = {
    "frustration": [
        r"frustrat\w*", r"annoy\w*", r"infuriat\w*", r"maddening",
        r"drives? me (crazy|nuts|insane)", r"can'?t stand",
    ],
    "failure": [
        r"doesn'?t work", r"broke\w*", r"stopped working", r"malfunction\w*",
        r"defective", r"failed", r"crash\w*", r"bug\w*",
    ],
    "waste": [
        r"waste of (money|time)", r"rip[ -]?off", r"overpriced", r"not worth",
        r"refund", r"return\w* it", r"money back",
    ],
    "missing_feature": [
        r"wish (it|they) (had|would|could)", r"if only", r"need\w* a",
        r"looking for (a |an )?alternative", r"missing", r"lacks?",
        r"doesn'?t (have|support|include)", r"no (way to|option)",
    ],
    "poor_quality": [
        r"cheap(ly)?[ -]?made", r"fell apart", r"poor quality",
        r"flimsy", r"\bthin\b", r"fragile", r"shoddy", r"junky",
    ],
    "bad_ux": [
        r"confusing", r"complicated", r"hard to (use|understand|setup|figure)",
        r"unintuitive", r"clunky", r"ugly", r"terrible (ui|ux|interface|design)",
    ],
    "slow": [
        r"slow", r"takes forever", r"laggy", r"sluggish",
        r"loading", r"buffering", r"unresponsive",
    ],
    "support": [
        r"no (help|support|response)", r"terrible (support|service|customer)",
        r"ignored", r"no one (responded|replied|helped)",
        r"waited (hours|days|weeks)", r"ghosted",
    ],
}

SEVERITY_MULTIPLIERS = {
    "frustration": 0.7,
    "failure": 0.9,
    "waste": 0.8,
    "missing_feature": 0.6,
    "poor_quality": 0.85,
    "bad_ux": 0.65,
    "slow": 0.5,
    "support": 0.75,
}


class PainPointEngine:
    """Discovers and scores customer pain points from market data."""

    def __init__(self, min_cluster_size: int = 3):
        self.min_cluster_size = min_cluster_size
        self._compiled_patterns = {
            category: [re.compile(p, re.IGNORECASE) for p in patterns]
            for category, patterns in PAIN_PATTERNS.items()
        }

    async def extract_pain_points(
        self,
        data_points: List[MarketDataPoint],
        reviews: Optional[List[ReviewAnalysis]] = None,
        niche: str = "",
    ) -> List[PainPoint]:
        """Extract pain points from raw market data and reviews."""
        pain_points = []

        for dp in data_points:
            texts = self._extract_texts(dp)
            for text in texts:
                matches = self._match_pain_patterns(text)
                if matches:
                    severity = self._calculate_severity(matches)
                    pain_points.append(
                        PainPoint(
                            description=text[:300],
                            category=max(matches, key=lambda k: matches[k]),
                            niche=niche or dp.niche,
                            severity=severity,
                            frequency=1,
                            sources=[dp.source],
                            evidence=[text[:500]],
                        )
                    )

        if reviews:
            for review in reviews:
                if review.sentiment in (Sentiment.NEGATIVE, Sentiment.VERY_NEGATIVE):
                    matches = self._match_pain_patterns(review.review_text)
                    severity = self._calculate_severity(matches) if matches else 0.5

                    if review.rating <= 2:
                        severity = max(severity, 0.7)

                    pain_points.append(
                        PainPoint(
                            description=review.review_text[:300],
                            category=max(matches, key=lambda k: matches[k]) if matches else "general_complaint",
                            niche=niche,
                            severity=severity,
                            frequency=1,
                            sources=[review.source],
                            evidence=[review.review_text[:500]],
                            existing_solutions=[review.product_name],
                        )
                    )

                    for pp_text in review.pain_points_extracted:
                        pain_points.append(
                            PainPoint(
                                description=pp_text,
                                category="review_extracted",
                                niche=niche,
                                severity=severity,
                                frequency=1,
                                sources=[review.source],
                                evidence=[review.review_text[:200]],
                                existing_solutions=[review.product_name],
                            )
                        )

        return pain_points

    async def cluster_pain_points(
        self, pain_points: List[PainPoint]
    ) -> List[PainPointCluster]:
        """Group related pain points into thematic clusters."""
        category_groups: Dict[str, List[PainPoint]] = defaultdict(list)

        for pp in pain_points:
            category_groups[pp.category].append(pp)

        clusters = []
        for category, pps in category_groups.items():
            if len(pps) < self.min_cluster_size:
                continue

            total_freq = sum(p.frequency for p in pps)
            avg_sev = sum(p.severity for p in pps) / len(pps)
            all_keywords = []
            all_sources = set()
            for p in pps:
                all_sources.update(s.value for s in p.sources)

            keyword_counter = Counter()
            for p in pps:
                words = p.description.lower().split()
                keyword_counter.update(
                    w for w in words if len(w) > 3 and w.isalpha()
                )

            solution_options = set()
            for p in pps:
                solution_options.update(p.existing_solutions)

            solution_gap = 1.0 - min(len(solution_options) * 0.15, 0.8)

            composite = avg_sev * min(total_freq / 10, 1.0) * (0.5 + solution_gap * 0.5)

            clusters.append(
                PainPointCluster(
                    theme=category,
                    pain_points=pps,
                    total_frequency=total_freq,
                    avg_severity=avg_sev,
                    composite_score=composite,
                    keywords=[w for w, _ in keyword_counter.most_common(10)],
                    solution_gap=solution_gap,
                    sources=list(all_sources),
                )
            )

        clusters.sort(key=lambda c: c.composite_score, reverse=True)
        return clusters

    async def rank_opportunities(
        self, clusters: List[PainPointCluster]
    ) -> List[Dict[str, Any]]:
        """Rank pain point clusters as business opportunities."""
        opportunities = []
        for idx, cluster in enumerate(clusters):
            opportunities.append({
                "rank": idx + 1,
                "theme": cluster.theme,
                "composite_score": round(cluster.composite_score, 3),
                "total_mentions": cluster.total_frequency,
                "avg_severity": round(cluster.avg_severity, 3),
                "solution_gap": round(cluster.solution_gap, 3),
                "top_keywords": cluster.keywords[:5],
                "evidence_count": len(cluster.pain_points),
                "sources": cluster.sources,
                "summary": self._generate_summary(cluster),
            })
        return opportunities

    def _extract_texts(self, dp: MarketDataPoint) -> List[str]:
        texts = []
        meta = dp.metadata

        for key in ["title", "text_preview", "snippet", "description", "review_text"]:
            val = meta.get(key, "")
            if val and isinstance(val, str) and len(val) > 10:
                texts.append(val)

        return texts

    def _match_pain_patterns(self, text: str) -> Dict[str, int]:
        matches: Dict[str, int] = {}
        for category, patterns in self._compiled_patterns.items():
            count = sum(1 for p in patterns if p.search(text))
            if count > 0:
                matches[category] = count
        return matches

    def _calculate_severity(self, matches: Dict[str, int]) -> float:
        if not matches:
            return 0.0
        weighted_sum = sum(
            count * SEVERITY_MULTIPLIERS.get(cat, 0.5)
            for cat, count in matches.items()
        )
        max_possible = sum(
            len(self._compiled_patterns[cat]) * SEVERITY_MULTIPLIERS.get(cat, 0.5)
            for cat in matches
        )
        return min(weighted_sum / max(max_possible * 0.3, 1), 1.0)

    def _generate_summary(self, cluster: PainPointCluster) -> str:
        severity_label = "low"
        if cluster.avg_severity > 0.7:
            severity_label = "high"
        elif cluster.avg_severity > 0.4:
            severity_label = "medium"

        gap_label = "saturated"
        if cluster.solution_gap > 0.7:
            gap_label = "wide open"
        elif cluster.solution_gap > 0.4:
            gap_label = "partially addressed"

        return (
            f"{severity_label.title()}-severity '{cluster.theme}' pain point with "
            f"{cluster.total_frequency} mentions across {len(cluster.sources)} sources. "
            f"Solution gap is {gap_label} (score: {cluster.solution_gap:.2f}). "
            f"Key terms: {', '.join(cluster.keywords[:5])}."
        )
