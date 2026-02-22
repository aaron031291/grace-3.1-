"""
Recursive Intelligence Loops

This is where the BI system becomes genuinely intelligent rather than
just a data pipeline. Each loop takes outputs from one module, feeds
them back as inputs to another, creating compounding intelligence.

The loops:

1. RESEARCH-VALIDATE-REFINE: Research findings feed validation campaigns,
   campaign results refine research focus. Each cycle narrows the target.

2. CUSTOMER-TARGET-ACQUIRE: Customer archetypes feed ad targeting,
   new acquisitions refine archetypes. Each cycle improves targeting accuracy.

3. PAIN-PRODUCT-FEEDBACK: Pain points drive product features,
   customer feedback reveals new pain points. Each cycle improves product-market fit.

4. CONTENT-ENGAGE-DISCOVER: Content created from research generates engagement,
   engagement data reveals new topics and pain points. Knowledge compounds.

5. PRICE-TEST-OPTIMIZE: Pricing set from competitor data, tested with real
   customers, optimized from conversion data. Revenue per customer increases.

6. COMPETE-MONITOR-ADAPT: Competitor analysis drives positioning,
   continuous monitoring detects changes, positioning adapts. Always ahead.

7. SENTIMENT-PREDICT-ACT: Sentiment analysis tracks market mood,
   velocity predicts shifts before they happen, actions taken preemptively.

These loops run automatically during each intelligence cycle.
Grace tracks which loop produced which insight for audit/explanation.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter

from business_intelligence.models.data_models import (
    MarketDataPoint, PainPoint, MarketOpportunity, CustomerArchetype,
    CampaignResult, ProductConcept, CompetitorProduct, WaitlistEntry,
    DataSource, Sentiment,
)

logger = logging.getLogger(__name__)


@dataclass
class LoopCycle:
    """Record of a single loop execution."""
    loop_name: str = ""
    cycle_number: int = 0
    inputs_used: int = 0
    outputs_generated: int = 0
    insights: List[str] = field(default_factory=list)
    refinements: List[str] = field(default_factory=list)
    confidence_delta: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LoopState:
    """Persistent state for all recursive loops."""
    total_cycles: int = 0
    loop_history: List[LoopCycle] = field(default_factory=list)
    cumulative_insights: List[str] = field(default_factory=list)
    knowledge_graph: Dict[str, List[str]] = field(default_factory=dict)
    confidence_trend: List[float] = field(default_factory=list)
    feedback_signals: List[Dict[str, Any]] = field(default_factory=list)


class RecursiveIntelligenceEngine:
    """Manages recursive feedback loops that compound intelligence over time."""

    def __init__(self):
        self.state = LoopState()

    async def run_all_loops(
        self,
        data_points: List[MarketDataPoint],
        pain_points: List[PainPoint],
        opportunities: List[MarketOpportunity],
        archetypes: List[CustomerArchetype],
        campaign_results: List[CampaignResult],
        waitlist_entries: List[WaitlistEntry],
        product_concepts: List[ProductConcept],
    ) -> Dict[str, Any]:
        """Execute all recursive loops and return compounded insights."""
        self.state.total_cycles += 1
        cycle_results = {}

        cycle_results["research_validate_refine"] = await self._loop_research_validate_refine(
            data_points, pain_points, campaign_results, opportunities
        )

        cycle_results["customer_target_acquire"] = await self._loop_customer_target_acquire(
            archetypes, campaign_results, waitlist_entries
        )

        cycle_results["pain_product_feedback"] = await self._loop_pain_product_feedback(
            pain_points, product_concepts, campaign_results
        )

        cycle_results["content_engage_discover"] = await self._loop_content_engage_discover(
            data_points, pain_points
        )

        cycle_results["price_test_optimize"] = await self._loop_price_test_optimize(
            opportunities, campaign_results
        )

        cycle_results["compete_monitor_adapt"] = await self._loop_compete_monitor_adapt(
            data_points, opportunities
        )

        cycle_results["sentiment_predict_act"] = await self._loop_sentiment_predict_act(
            data_points, pain_points
        )

        cross_loop = self._cross_pollinate_loops(cycle_results)

        overall_confidence = self._calculate_confidence_trend()

        return {
            "cycle_number": self.state.total_cycles,
            "loops_executed": len(cycle_results),
            "loop_results": cycle_results,
            "cross_loop_insights": cross_loop,
            "cumulative_insights": len(self.state.cumulative_insights),
            "knowledge_nodes": len(self.state.knowledge_graph),
            "confidence_trend": self.state.confidence_trend[-10:],
            "overall_confidence": overall_confidence,
        }

    async def _loop_research_validate_refine(
        self, data_points, pain_points, campaign_results, opportunities,
    ) -> Dict[str, Any]:
        """Loop 1: Research findings -> Validation campaigns -> Refined research focus."""
        cycle = LoopCycle(loop_name="research_validate_refine", cycle_number=self.state.total_cycles)

        validated_pain_points = []
        unvalidated_pain_points = []

        if campaign_results:
            converting_keywords = set()
            for cr in campaign_results:
                if cr.signups > 0 and cr.cost_per_acquisition < 10:
                    if cr.ad_copy_used:
                        words = cr.ad_copy_used.lower().split()
                        converting_keywords.update(w for w in words if len(w) > 4)

            for pp in pain_points:
                pp_words = set(pp.description.lower().split())
                if pp_words & converting_keywords:
                    validated_pain_points.append(pp)
                    pp.confidence = min(pp.confidence + 0.1, 1.0)
                else:
                    unvalidated_pain_points.append(pp)

        insights = []
        if validated_pain_points:
            insights.append(
                f"Campaign data validates {len(validated_pain_points)} pain points. "
                "These should be prioritized in product development."
            )
        if unvalidated_pain_points and campaign_results:
            insights.append(
                f"{len(unvalidated_pain_points)} pain points lack campaign validation. "
                "Consider testing these in next ad cycle."
            )

        refinements = []
        if opportunities and campaign_results:
            best_cpa_opp = None
            for opp in opportunities:
                opp_keywords = set()
                for pp in opp.pain_points:
                    opp_keywords.update(pp.description.lower().split()[:3])
                matching_results = [
                    cr for cr in campaign_results
                    if any(kw in (cr.ad_copy_used or "").lower() for kw in opp_keywords)
                ]
                if matching_results:
                    avg_cpa = sum(cr.cost_per_acquisition for cr in matching_results) / len(matching_results)
                    if best_cpa_opp is None or avg_cpa < best_cpa_opp[1]:
                        best_cpa_opp = (opp.title, avg_cpa)

            if best_cpa_opp:
                refinements.append(f"Focus research on '{best_cpa_opp[0]}' -- lowest CPA at {best_cpa_opp[1]:.2f}")

        cycle.inputs_used = len(data_points) + len(campaign_results)
        cycle.outputs_generated = len(insights) + len(refinements)
        cycle.insights = insights
        cycle.refinements = refinements
        self.state.loop_history.append(cycle)
        self.state.cumulative_insights.extend(insights)

        self._update_knowledge_graph("research_validate", insights + refinements)

        return {"insights": insights, "refinements": refinements,
                "validated_pain_points": len(validated_pain_points),
                "unvalidated": len(unvalidated_pain_points)}

    async def _loop_customer_target_acquire(
        self, archetypes, campaign_results, waitlist_entries,
    ) -> Dict[str, Any]:
        """Loop 2: Customer archetypes -> Better targeting -> Better customers -> Refined archetypes."""
        cycle = LoopCycle(loop_name="customer_target_acquire", cycle_number=self.state.total_cycles)
        insights = []
        refinements = []

        if archetypes and campaign_results:
            platform_performance = {}
            for cr in campaign_results:
                if cr.platform not in platform_performance:
                    platform_performance[cr.platform] = {"spend": 0, "signups": 0}
                platform_performance[cr.platform]["spend"] += cr.ad_spend
                platform_performance[cr.platform]["signups"] += cr.signups

            for arch in archetypes:
                arch_channels = arch.preferred_channels
                for channel in arch_channels:
                    perf = platform_performance.get(channel)
                    if perf and perf["signups"] > 0:
                        cpa = perf["spend"] / perf["signups"]
                        arch.acquisition_cost_estimate = cpa
                        insights.append(
                            f"Archetype '{arch.name}' acquires at {cpa:.2f} on {channel}"
                        )

        if waitlist_entries:
            source_counter = Counter(e.source_platform for e in waitlist_entries if e.source_platform and not e.opted_out)
            if source_counter:
                top_source = source_counter.most_common(1)[0]
                insights.append(f"Top acquisition channel: {top_source[0]} ({top_source[1]} signups)")
                refinements.append(f"Increase budget allocation to {top_source[0]}")

        opt_out_rate = sum(1 for e in waitlist_entries if e.opted_out) / max(len(waitlist_entries), 1)
        if opt_out_rate > 0.1:
            insights.append(f"High opt-out rate ({opt_out_rate:.0%}). Review messaging alignment with actual product.")

        cycle.insights = insights
        cycle.refinements = refinements
        self.state.loop_history.append(cycle)
        self.state.cumulative_insights.extend(insights)
        self._update_knowledge_graph("customer_targeting", insights + refinements)

        return {"insights": insights, "refinements": refinements}

    async def _loop_pain_product_feedback(
        self, pain_points, product_concepts, campaign_results,
    ) -> Dict[str, Any]:
        """Loop 3: Pain points -> Product features -> Customer feedback -> New pain points."""
        insights = []
        refinements = []

        if product_concepts and pain_points:
            addressed = set()
            unaddressed = []
            for concept in product_concepts:
                for pp in concept.pain_points_addressed:
                    addressed.add(pp.description[:50])

            for pp in pain_points:
                if pp.description[:50] not in addressed:
                    unaddressed.append(pp)

            if unaddressed:
                top_unaddressed = sorted(unaddressed, key=lambda p: p.pain_score, reverse=True)[:3]
                for pp in top_unaddressed:
                    refinements.append(f"Unaddressed high-pain: '{pp.description[:60]}' (score: {pp.pain_score:.2f})")

            insights.append(
                f"{len(addressed)} pain points addressed by products, "
                f"{len(unaddressed)} still unaddressed"
            )

        if campaign_results:
            high_conversion_copy = [
                cr.ad_copy_used for cr in campaign_results
                if cr.signups > 0 and cr.cost_per_acquisition < 5 and cr.ad_copy_used
            ]
            if high_conversion_copy:
                insights.append(
                    f"{len(high_conversion_copy)} ad copies converted well -- "
                    "the pain points they reference are validated by spending behavior"
                )

        self.state.cumulative_insights.extend(insights)
        self._update_knowledge_graph("pain_product", insights + refinements)

        return {"insights": insights, "refinements": refinements}

    async def _loop_content_engage_discover(
        self, data_points, pain_points,
    ) -> Dict[str, Any]:
        """Loop 4: Content from research -> Engagement data -> New topic discovery."""
        insights = []

        forum_data = [dp for dp in data_points if dp.source in (DataSource.FORUM, DataSource.REVIEW_SITE)]
        if forum_data:
            high_engagement = [dp for dp in forum_data if dp.metric_value > 50]
            topic_counter = Counter()
            for dp in high_engagement:
                for kw in dp.keywords:
                    topic_counter[kw] += 1

            if topic_counter:
                top_topics = topic_counter.most_common(5)
                insights.append(
                    f"High-engagement topics: {', '.join(t[0] for t in top_topics)}. "
                    "Create content around these for organic traffic."
                )

        if pain_points:
            category_counter = Counter(pp.category for pp in pain_points)
            if category_counter:
                top_category = category_counter.most_common(1)[0]
                insights.append(
                    f"Most common pain category: '{top_category[0]}' ({top_category[1]} instances). "
                    "Create educational content addressing this category."
                )

        self.state.cumulative_insights.extend(insights)
        self._update_knowledge_graph("content_discovery", insights)
        return {"insights": insights, "content_opportunities": len(insights)}

    async def _loop_price_test_optimize(
        self, opportunities, campaign_results,
    ) -> Dict[str, Any]:
        """Loop 5: Competitor pricing -> Price testing -> Conversion optimization."""
        insights = []
        refinements = []

        if opportunities:
            for opp in opportunities[:3]:
                if opp.competitors:
                    prices = [c.price for c in opp.competitors if c.price > 0]
                    if prices:
                        avg = sum(prices) / len(prices)
                        suggested = avg * 0.85
                        insights.append(
                            f"'{opp.niche}' market avg price: {avg:.2f}. "
                            f"Suggested entry: {suggested:.2f} (15% undercut)"
                        )

        if campaign_results:
            by_variant = {}
            for cr in campaign_results:
                v = cr.ab_variant or "default"
                by_variant.setdefault(v, []).append(cr)
            for variant, results in by_variant.items():
                total_signups = sum(r.signups for r in results)
                total_spend = sum(r.ad_spend for r in results)
                if total_signups > 0:
                    cpa = total_spend / total_signups
                    refinements.append(f"Variant '{variant}': CPA {cpa:.2f}, {total_signups} signups")

        self.state.cumulative_insights.extend(insights)
        self._update_knowledge_graph("pricing", insights + refinements)
        return {"insights": insights, "refinements": refinements}

    async def _loop_compete_monitor_adapt(
        self, data_points, opportunities,
    ) -> Dict[str, Any]:
        """Loop 6: Competitor analysis -> Continuous monitoring -> Positioning adaptation."""
        insights = []

        competitor_data = [dp for dp in data_points if dp.category in ("competitor_product", "amazon_product", "shopping")]
        if len(competitor_data) >= 2:
            price_changes = {}
            for dp in competitor_data:
                name = dp.metadata.get("product_name", dp.metadata.get("title", ""))
                if name and dp.metric_value > 0:
                    price_changes.setdefault(name, []).append(dp.metric_value)

            for name, prices in price_changes.items():
                if len(prices) >= 2 and prices[-1] != prices[0]:
                    change = ((prices[-1] - prices[0]) / prices[0]) * 100
                    if abs(change) > 5:
                        insights.append(
                            f"Competitor '{name[:30]}' price changed {change:+.1f}%. "
                            "Adjust positioning if needed."
                        )

        self.state.cumulative_insights.extend(insights)
        self._update_knowledge_graph("competitor_monitoring", insights)
        return {"insights": insights, "competitors_tracked": len(set(
            dp.metadata.get("title", "") for dp in competitor_data if dp.metadata.get("title")
        ))}

    async def _loop_sentiment_predict_act(
        self, data_points, pain_points,
    ) -> Dict[str, Any]:
        """Loop 7: Sentiment analysis -> Velocity tracking -> Predictive action."""
        insights = []

        if len(pain_points) >= 5:
            recent = [pp for pp in pain_points if (datetime.utcnow() - pp.timestamp).days < 7]
            older = [pp for pp in pain_points if (datetime.utcnow() - pp.timestamp).days >= 7]

            if recent and older:
                recent_avg_sev = sum(p.severity for p in recent) / len(recent)
                older_avg_sev = sum(p.severity for p in older) / len(older)

                if recent_avg_sev > older_avg_sev * 1.2:
                    insights.append(
                        f"Sentiment DETERIORATING: recent pain severity ({recent_avg_sev:.2f}) "
                        f"is {((recent_avg_sev - older_avg_sev) / older_avg_sev * 100):.0f}% higher than historical ({older_avg_sev:.2f}). "
                        "Market frustration is growing -- opportunity window expanding."
                    )
                elif recent_avg_sev < older_avg_sev * 0.8:
                    insights.append(
                        "Sentiment IMPROVING: pain severity is declining. "
                        "Competitors may be addressing issues. Validate urgency."
                    )

            category_velocity = {}
            for pp in recent:
                category_velocity[pp.category] = category_velocity.get(pp.category, 0) + 1
            if category_velocity:
                fastest = max(category_velocity, key=category_velocity.get)
                insights.append(
                    f"Fastest growing complaint category: '{fastest}' "
                    f"({category_velocity[fastest]} new mentions this week)"
                )

        self.state.cumulative_insights.extend(insights)
        self._update_knowledge_graph("sentiment_prediction", insights)
        return {"insights": insights}

    def _cross_pollinate_loops(self, cycle_results: Dict[str, Any]) -> List[str]:
        """Find insights that span multiple loops."""
        cross_insights = []

        all_insights = []
        for loop_name, result in cycle_results.items():
            for insight in result.get("insights", []):
                all_insights.append((loop_name, insight))

        if len(all_insights) >= 3:
            cross_insights.append(
                f"Cross-loop synthesis: {len(all_insights)} insights generated across "
                f"{len(cycle_results)} loops in cycle #{self.state.total_cycles}. "
                "Intelligence is compounding."
            )

        validated = cycle_results.get("research_validate_refine", {}).get("validated_pain_points", 0)
        archetypes = cycle_results.get("customer_target_acquire", {}).get("insights", [])
        if validated > 0 and archetypes:
            cross_insights.append(
                f"Convergence: {validated} validated pain points + archetype data = "
                "high-confidence targeting. Ready for scaled campaign."
            )

        return cross_insights

    def _calculate_confidence_trend(self) -> float:
        """Track overall system confidence over cycles."""
        if not self.state.loop_history:
            return 0.0

        recent_loops = self.state.loop_history[-20:]
        insights_per_cycle = {}
        for lc in recent_loops:
            insights_per_cycle.setdefault(lc.cycle_number, 0)
            insights_per_cycle[lc.cycle_number] += len(lc.insights)

        if not insights_per_cycle:
            return 0.3

        avg_insights = sum(insights_per_cycle.values()) / len(insights_per_cycle)
        confidence = min(0.3 + avg_insights * 0.05 + self.state.total_cycles * 0.02, 1.0)
        self.state.confidence_trend.append(confidence)
        return confidence

    def _update_knowledge_graph(self, source: str, insights: List[str]):
        """Build a knowledge graph connecting insights across domains."""
        if source not in self.state.knowledge_graph:
            self.state.knowledge_graph[source] = []
        self.state.knowledge_graph[source].extend(insights[-5:])
        if len(self.state.knowledge_graph[source]) > 50:
            self.state.knowledge_graph[source] = self.state.knowledge_graph[source][-50:]

    def get_knowledge_summary(self) -> Dict[str, Any]:
        """Get summary of accumulated knowledge across all loops."""
        return {
            "total_cycles": self.state.total_cycles,
            "total_insights": len(self.state.cumulative_insights),
            "knowledge_domains": list(self.state.knowledge_graph.keys()),
            "insights_per_domain": {k: len(v) for k, v in self.state.knowledge_graph.items()},
            "confidence_trend": self.state.confidence_trend[-20:],
            "latest_insights": self.state.cumulative_insights[-10:],
            "loop_execution_count": len(self.state.loop_history),
        }
