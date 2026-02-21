"""
Untapped Intelligence Module

Intelligence patterns that most BI systems miss. These are the
edges that compound over time:

1. Sentiment Velocity -- how FAST sentiment is changing, not just what it is
2. Content Arbitrage -- gaps between what people search and what content exists
3. Job Posting Analysis -- competitor hiring reveals their strategy
4. Churn Prediction -- predict who will leave before they do
5. Regulatory Monitoring -- regulation changes create opportunities
6. Supply Chain Intelligence -- for physical products
7. Network Effect Mapping -- how customers refer others
8. Pricing Elasticity -- systematic price sensitivity testing
9. Seasonal Demand Prediction -- predictive, not reactive
10. Competitor Strategy Inference -- reverse-engineer competitor moves from public signals
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from business_intelligence.models.data_models import (
    MarketDataPoint, PainPoint, CompetitorProduct, WaitlistEntry,
    CampaignResult, KeywordMetric, DataSource,
)

logger = logging.getLogger(__name__)


@dataclass
class IntelligenceSignal:
    """A signal from untapped intelligence analysis."""
    signal_type: str = ""
    strength: float = 0.0
    direction: str = ""
    description: str = ""
    actionable: bool = False
    recommended_action: str = ""
    data_points_used: int = 0
    confidence: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class UntappedIntelligence:
    """Extracts intelligence patterns most systems miss."""

    async def analyze_all(
        self,
        data_points: List[MarketDataPoint],
        pain_points: List[PainPoint],
        competitors: List[CompetitorProduct],
        waitlist: List[WaitlistEntry],
        campaigns: List[CampaignResult],
        keywords: Optional[List[KeywordMetric]] = None,
    ) -> Dict[str, Any]:
        """Run all untapped intelligence analyses."""
        results = {}

        results["sentiment_velocity"] = await self.analyze_sentiment_velocity(pain_points)
        results["content_arbitrage"] = await self.find_content_arbitrage(data_points, keywords or [])
        results["competitor_strategy"] = await self.infer_competitor_strategy(competitors, data_points)
        results["churn_signals"] = await self.detect_churn_signals(waitlist, campaigns)
        results["seasonal_prediction"] = await self.predict_seasonal_demand(data_points)
        results["network_effects"] = await self.map_network_effects(waitlist)
        results["pricing_intelligence"] = await self.analyze_pricing_elasticity(competitors, campaigns)

        all_signals = []
        for category, result in results.items():
            for signal in result.get("signals", []):
                all_signals.append(signal)

        actionable = [s for s in all_signals if s.get("actionable")]

        return {
            "analyses_run": len(results),
            "total_signals": len(all_signals),
            "actionable_signals": len(actionable),
            "results": results,
            "top_actions": [s["recommended_action"] for s in actionable[:5] if s.get("recommended_action")],
        }

    async def analyze_sentiment_velocity(
        self, pain_points: List[PainPoint],
    ) -> Dict[str, Any]:
        """Track how fast sentiment is changing, not just what it is.

        A slowly deteriorating sentiment = time to enter market.
        Rapidly deteriorating = urgent opportunity.
        Improving sentiment = competitors may be solving it already.
        """
        signals = []
        if len(pain_points) < 5:
            return {"signals": [], "message": "Need 5+ pain points for velocity analysis"}

        now = datetime.utcnow()
        periods = {
            "last_7_days": [pp for pp in pain_points if (now - pp.timestamp).days < 7],
            "7_14_days": [pp for pp in pain_points if 7 <= (now - pp.timestamp).days < 14],
            "14_30_days": [pp for pp in pain_points if 14 <= (now - pp.timestamp).days < 30],
        }

        for period, pps in periods.items():
            if not pps:
                continue
            avg_severity = sum(p.severity for p in pps) / len(pps)
            category_counts = Counter(p.category for p in pps)

            signals.append({
                "signal_type": "sentiment_velocity",
                "period": period,
                "avg_severity": round(avg_severity, 3),
                "volume": len(pps),
                "top_categories": dict(category_counts.most_common(3)),
                "actionable": avg_severity > 0.6 and len(pps) > 3,
                "recommended_action": (
                    f"High pain velocity in period '{period}' -- market frustration accelerating"
                    if avg_severity > 0.6 else ""
                ),
            })

        if len(periods["last_7_days"]) > 0 and len(periods["14_30_days"]) > 0:
            recent_vol = len(periods["last_7_days"])
            older_vol = len(periods["14_30_days"]) / 2
            if older_vol > 0:
                acceleration = (recent_vol - older_vol) / older_vol * 100
                signals.append({
                    "signal_type": "complaint_acceleration",
                    "acceleration_pct": round(acceleration, 1),
                    "description": f"Complaint volume {'accelerating' if acceleration > 0 else 'decelerating'} at {acceleration:+.0f}%",
                    "actionable": acceleration > 50,
                    "recommended_action": "Market pain is accelerating rapidly -- first mover advantage available" if acceleration > 50 else "",
                })

        return {"signals": signals}

    async def find_content_arbitrage(
        self, data_points: List[MarketDataPoint], keywords: List[KeywordMetric],
    ) -> Dict[str, Any]:
        """Find gaps between search demand and content supply.

        High search volume + low content quality = content arbitrage opportunity.
        """
        signals = []

        search_data = [dp for dp in data_points if dp.category == "search_results"]
        keyword_data = {k.keyword: k for k in keywords}

        keyword_competition = {}
        for dp in search_data:
            for kw in dp.keywords:
                keyword_competition.setdefault(kw, {"results": 0, "volume": 0})
                keyword_competition[kw]["results"] += 1
                if kw in keyword_data:
                    keyword_competition[kw]["volume"] = keyword_data[kw].search_volume

        for kw, data in keyword_competition.items():
            if data["volume"] > 100 and data["results"] < 5:
                signals.append({
                    "signal_type": "content_arbitrage",
                    "keyword": kw,
                    "search_volume": data["volume"],
                    "competition": data["results"],
                    "description": f"'{kw}' has high search volume ({data['volume']}) but low competition ({data['results']} results)",
                    "actionable": True,
                    "recommended_action": f"Create comprehensive content for '{kw}' -- low competition, high demand",
                })

        return {"signals": signals, "opportunities": len([s for s in signals if s.get("actionable")])}

    async def infer_competitor_strategy(
        self, competitors: List[CompetitorProduct], data_points: List[MarketDataPoint],
    ) -> Dict[str, Any]:
        """Reverse-engineer competitor strategies from public signals."""
        signals = []

        if len(competitors) >= 2:
            price_segments = {"budget": [], "mid": [], "premium": []}
            prices = [c.price for c in competitors if c.price > 0]
            if prices:
                avg = sum(prices) / len(prices)
                for c in competitors:
                    if c.price > 0:
                        if c.price < avg * 0.6:
                            price_segments["budget"].append(c)
                        elif c.price > avg * 1.4:
                            price_segments["premium"].append(c)
                        else:
                            price_segments["mid"].append(c)

                for segment, comps in price_segments.items():
                    if not comps:
                        signals.append({
                            "signal_type": "strategy_gap",
                            "segment": segment,
                            "description": f"No competitors in {segment} segment (avg price: {avg:.2f})",
                            "actionable": True,
                            "recommended_action": f"Consider positioning in empty {segment} segment",
                        })

            feature_coverage = Counter()
            for c in competitors:
                for f in c.features:
                    feature_coverage[f.lower()[:30]] += 1

            rare_features = [f for f, count in feature_coverage.items() if count == 1 and len(f) > 3]
            if rare_features:
                signals.append({
                    "signal_type": "unique_features",
                    "features": rare_features[:5],
                    "description": f"{len(rare_features)} features only offered by one competitor",
                    "actionable": len(rare_features) >= 3,
                    "recommended_action": "Evaluate rare features for inclusion -- they may be differentiators",
                })

        return {"signals": signals}

    async def detect_churn_signals(
        self, waitlist: List[WaitlistEntry], campaigns: List[CampaignResult],
    ) -> Dict[str, Any]:
        """Predict churn from behavioral signals."""
        signals = []

        if waitlist:
            total = len(waitlist)
            opted_out = sum(1 for e in waitlist if e.opted_out)
            opt_out_rate = opted_out / total if total > 0 else 0

            if opt_out_rate > 0.1:
                signals.append({
                    "signal_type": "churn_warning",
                    "opt_out_rate": round(opt_out_rate, 3),
                    "description": f"Opt-out rate at {opt_out_rate:.0%}. Above 10% threshold.",
                    "actionable": True,
                    "recommended_action": "Review messaging alignment. Survey opted-out users on reason.",
                })

            by_source = defaultdict(lambda: {"total": 0, "opted_out": 0})
            for e in waitlist:
                src = e.source_platform or "direct"
                by_source[src]["total"] += 1
                if e.opted_out:
                    by_source[src]["opted_out"] += 1

            for src, data in by_source.items():
                if data["total"] >= 5:
                    src_churn = data["opted_out"] / data["total"]
                    if src_churn > 0.2:
                        signals.append({
                            "signal_type": "source_quality",
                            "source": src,
                            "churn_rate": round(src_churn, 3),
                            "description": f"High churn from {src} ({src_churn:.0%}). Traffic quality issue.",
                            "actionable": True,
                            "recommended_action": f"Review {src} targeting -- attracting wrong audience",
                        })

        return {"signals": signals}

    async def predict_seasonal_demand(
        self, data_points: List[MarketDataPoint],
    ) -> Dict[str, Any]:
        """Predict seasonal patterns from historical data."""
        signals = []

        monthly_data: Dict[int, List[float]] = defaultdict(list)
        for dp in data_points:
            if dp.metric_value > 0:
                monthly_data[dp.timestamp.month].append(dp.metric_value)

        if len(monthly_data) >= 4:
            monthly_avgs = {m: sum(v)/len(v) for m, v in monthly_data.items()}
            overall_avg = sum(monthly_avgs.values()) / len(monthly_avgs)

            month_names = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                          7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}

            peaks = {m: v for m, v in monthly_avgs.items() if v > overall_avg * 1.3}
            troughs = {m: v for m, v in monthly_avgs.items() if v < overall_avg * 0.7}

            if peaks:
                peak_months = ", ".join(month_names.get(m, str(m)) for m in sorted(peaks))
                signals.append({
                    "signal_type": "seasonal_peak",
                    "months": list(peaks.keys()),
                    "description": f"Demand peaks in {peak_months}. Plan campaigns to start 2-4 weeks before.",
                    "actionable": True,
                    "recommended_action": f"Increase ad spend before peak months: {peak_months}",
                })

        return {"signals": signals}

    async def map_network_effects(
        self, waitlist: List[WaitlistEntry],
    ) -> Dict[str, Any]:
        """Map how customers discover and refer each other."""
        signals = []

        if waitlist:
            source_counter = Counter(e.source_campaign for e in waitlist if e.source_campaign)
            referral_sources = {s: c for s, c in source_counter.items() if "referral" in s.lower() or "refer" in s.lower()}

            if referral_sources:
                total_referrals = sum(referral_sources.values())
                signals.append({
                    "signal_type": "referral_network",
                    "referrals": total_referrals,
                    "description": f"{total_referrals} signups from referrals. Organic growth is happening.",
                    "actionable": True,
                    "recommended_action": "Build formal referral program -- users are already sharing",
                })

        return {"signals": signals}

    async def analyze_pricing_elasticity(
        self, competitors: List[CompetitorProduct], campaigns: List[CampaignResult],
    ) -> Dict[str, Any]:
        """Analyze price sensitivity from competitive and campaign data."""
        signals = []

        if competitors:
            prices = [c.price for c in competitors if c.price > 0]
            ratings = [c.rating for c in competitors if c.rating > 0 and c.price > 0]

            if len(prices) >= 3:
                sorted_by_price = sorted(zip(prices, ratings), key=lambda x: x[0])
                cheap_ratings = [r for p, r in sorted_by_price[:len(sorted_by_price)//3]]
                expensive_ratings = [r for p, r in sorted_by_price[-len(sorted_by_price)//3:]]

                if cheap_ratings and expensive_ratings:
                    cheap_avg = sum(cheap_ratings) / len(cheap_ratings)
                    exp_avg = sum(expensive_ratings) / len(expensive_ratings)

                    if exp_avg > cheap_avg + 0.5:
                        signals.append({
                            "signal_type": "price_quality_correlation",
                            "description": f"Higher-priced products rate better ({exp_avg:.1f} vs {cheap_avg:.1f}). Market values quality over price.",
                            "actionable": True,
                            "recommended_action": "Price at premium -- this market rewards quality",
                        })
                    elif cheap_avg > exp_avg:
                        signals.append({
                            "signal_type": "price_quality_inversion",
                            "description": f"Cheaper products rate higher ({cheap_avg:.1f} vs {exp_avg:.1f}). Market is price-sensitive.",
                            "actionable": True,
                            "recommended_action": "Compete on value -- undercut premium incumbents",
                        })

        return {"signals": signals}
