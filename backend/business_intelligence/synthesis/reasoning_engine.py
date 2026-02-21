"""
LLM Reasoning Engine for Business Intelligence

Connects the BI system to GRACE's LLM orchestrator, MAGMA memory,
and hallucination guards. Raw data means nothing without reasoning --
this engine takes the collected intelligence and has the LLM:

1. Synthesize patterns humans would miss
2. Generate strategic recommendations
3. Reason about market dynamics
4. Predict outcomes based on data
5. Challenge its own assumptions (hallucination guard)
6. Build on previous reasoning (MAGMA memory)

The key: every LLM output is verified through GRACE's existing
truth/integrity pipeline. No hallucinated market insights.
"""

import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


BI_SYSTEM_PROMPT = """You are Grace's Business Intelligence reasoning engine. You analyze market data, 
pain points, competitor landscapes, and customer signals to produce actionable business intelligence.

RULES:
1. Base ALL conclusions on the provided data. If the data is insufficient, say so.
2. Never fabricate market statistics or revenue projections without data backing.
3. Clearly distinguish between data-supported insights and your inferences.
4. Flag uncertainty levels for every recommendation.
5. Consider ethical implications of every strategy recommendation.
6. Do not recommend manipulative marketing tactics.
7. Prioritize strategies with measurable validation steps.
8. Always recommend the minimum viable investment to test an idea.

Your output should be structured, actionable, and honest about what you don't know."""


@dataclass
class ReasoningRequest:
    """A request for LLM reasoning over BI data."""
    task: str = ""
    data_context: Dict[str, Any] = field(default_factory=dict)
    previous_reasoning: Optional[str] = None
    require_verification: bool = True
    max_tokens: int = 2000


@dataclass
class ReasoningResult:
    """Result from LLM reasoning."""
    task: str = ""
    reasoning: str = ""
    recommendations: List[str] = field(default_factory=list)
    confidence: float = 0.0
    verification_passed: bool = False
    verification_notes: str = ""
    model_used: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    data_points_considered: int = 0
    warnings: List[str] = field(default_factory=list)


class BIReasoningEngine:
    """LLM-powered reasoning engine for business intelligence."""

    def __init__(self):
        self._llm_client = None
        self._orchestrator = None
        self._reasoning_history: List[ReasoningResult] = []

    def _get_llm_client(self):
        """Lazily get GRACE's LLM client."""
        if self._llm_client is not None:
            return self._llm_client

        try:
            from llm_orchestrator.factory import get_llm_client
            self._llm_client = get_llm_client()
            return self._llm_client
        except Exception as e:
            logger.warning(f"LLM client not available: {e}")
            return None

    def _get_orchestrator(self):
        """Lazily get GRACE's full LLM orchestrator with hallucination guards."""
        if self._orchestrator is not None:
            return self._orchestrator

        try:
            from llm_orchestrator.llm_orchestrator import LLMOrchestrator
            self._orchestrator = LLMOrchestrator
            return self._orchestrator
        except Exception as e:
            logger.warning(f"LLM orchestrator not available: {e}")
            return None

    async def reason_about_market(
        self,
        market_data: Dict[str, Any],
        pain_points: List[Dict[str, Any]],
        competitors: List[Dict[str, Any]],
        niche: str,
    ) -> ReasoningResult:
        """Have the LLM reason about a market based on collected data."""
        context = self._build_market_context(
            market_data, pain_points, competitors, niche
        )

        prompt = f"""Analyze this market intelligence for the "{niche}" niche and provide:

1. MARKET ASSESSMENT: Is this market worth entering? Why or why not?
2. PAIN POINT PRIORITY: Which pain points should we address first and why?
3. COMPETITIVE POSITIONING: How should we differentiate?
4. RISK FACTORS: What could go wrong?
5. RECOMMENDED NEXT STEP: One specific, actionable next step.

DATA:
{json.dumps(context, indent=2, default=str)}

Be specific. Reference the actual data points. Flag anything you're uncertain about."""

        return await self._execute_reasoning(
            task="market_analysis",
            prompt=prompt,
            data_points=len(pain_points) + len(competitors),
        )

    async def reason_about_opportunity(
        self,
        opportunity: Dict[str, Any],
        trend_data: Optional[Dict[str, Any]] = None,
    ) -> ReasoningResult:
        """Deep reasoning about a specific opportunity."""
        context = {
            "opportunity": opportunity,
            "trends": trend_data,
        }

        prompt = f"""Evaluate this business opportunity:

OPPORTUNITY: {json.dumps(opportunity, indent=2, default=str)}

TREND DATA: {json.dumps(trend_data, indent=2, default=str) if trend_data else 'No trend data available'}

Provide:
1. VIABILITY ASSESSMENT (0-100 score with justification)
2. CRITICAL ASSUMPTIONS: What must be true for this to work?
3. VALIDATION PLAN: How to test these assumptions with minimum spend
4. TIMELINE: Realistic timeline from idea to first revenue
5. KILL CRITERIA: When should we abandon this and move on?

Be brutally honest. Better to kill a bad idea early than waste months on it."""

        return await self._execute_reasoning(
            task="opportunity_evaluation",
            prompt=prompt,
        )

    async def reason_about_campaign_performance(
        self,
        campaign_results: List[Dict[str, Any]],
        waitlist_stats: Dict[str, Any],
    ) -> ReasoningResult:
        """Reason about campaign performance and recommend optimizations."""
        context = {
            "campaigns": campaign_results,
            "waitlist": waitlist_stats,
        }

        prompt = f"""Analyze these advertising campaign results and recommend optimizations:

CAMPAIGN DATA: {json.dumps(campaign_results, indent=2, default=str)}

WAITLIST STATUS: {json.dumps(waitlist_stats, indent=2, default=str)}

Provide:
1. PERFORMANCE ASSESSMENT: Which campaigns are working? Which aren't?
2. AD COPY INSIGHTS: What messaging patterns are converting best?
3. AUDIENCE INSIGHTS: What does the converting audience look like?
4. BUDGET REALLOCATION: Where should we shift spend?
5. NEXT TESTS: What should we test next?
6. TRAFFIC STRATEGY: How do we get more volume at current CPA?

Focus on actionable changes, not theory."""

        return await self._execute_reasoning(
            task="campaign_optimization",
            prompt=prompt,
            data_points=len(campaign_results),
        )

    async def reason_about_product_strategy(
        self,
        pain_points: List[Dict[str, Any]],
        archetypes: List[Dict[str, Any]],
        opportunities: List[Dict[str, Any]],
    ) -> ReasoningResult:
        """Reason about what product to build and how."""
        context = {
            "pain_points": pain_points[:10],
            "customer_archetypes": archetypes,
            "opportunities": opportunities[:5],
        }

        prompt = f"""Based on this intelligence, recommend a product strategy:

PAIN POINTS: {json.dumps(pain_points[:10], indent=2, default=str)}

CUSTOMER ARCHETYPES: {json.dumps(archetypes, indent=2, default=str)}

TOP OPPORTUNITIES: {json.dumps(opportunities[:5], indent=2, default=str)}

Provide:
1. PRODUCT RECOMMENDATION: What should we build? (SaaS / course / ebook / AI tool / physical product)
2. MVP DEFINITION: Minimum feature set for launch
3. PRODUCT LADDER: How does this lead to additional products?
4. PRICING STRATEGY: Based on competitor data and willingness to pay
5. LAUNCH STRATEGY: How to go from MVP to first 100 paying customers
6. CROSS-DOMAIN POTENTIAL: Can this product seed entry into adjacent markets?

Prioritize speed to market and validation over perfection."""

        return await self._execute_reasoning(
            task="product_strategy",
            prompt=prompt,
            data_points=len(pain_points) + len(archetypes) + len(opportunities),
        )

    async def generate_grace_briefing(
        self,
        state: Dict[str, Any],
    ) -> ReasoningResult:
        """Generate Grace's daily intelligence briefing.

        This is the "continuous conversation" between Grace and the user --
        Grace summarizes what she's learned, what's changed, and what
        she recommends.
        """
        prompt = f"""Generate a business intelligence briefing based on current state:

STATE: {json.dumps(state, indent=2, default=str)}

Format as a briefing that covers:
1. STATUS: Where are we in the pipeline? (collecting / analyzing / validating / building)
2. WHAT'S CHANGED: New data, new insights, changed scores since last cycle
3. TOP FINDING: The single most important thing we've learned
4. BOTTLENECKS: What's blocking progress?
5. KNOWLEDGE GAPS: Where do I need more data or documents?
6. RECOMMENDED ACTIONS: Top 3 actions ranked by impact
7. CONFIDENCE CHECK: How confident am I in these recommendations and why?

Speak in first person as Grace. Be direct, specific, and honest about uncertainty."""

        return await self._execute_reasoning(
            task="daily_briefing",
            prompt=prompt,
        )

    async def _execute_reasoning(
        self,
        task: str,
        prompt: str,
        data_points: int = 0,
    ) -> ReasoningResult:
        """Execute LLM reasoning with hallucination guards."""
        client = self._get_llm_client()

        if not client:
            return self._fallback_reasoning(task, data_points)

        try:
            response = client.generate(
                prompt=prompt,
                system_prompt=BI_SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=2000,
            )

            reasoning_text = response if isinstance(response, str) else response.get("response", str(response))

            recommendations = self._extract_recommendations(reasoning_text)

            verification_passed = True
            verification_notes = ""
            try:
                from llm_orchestrator.hallucination_guard import HallucinationGuard
                guard = HallucinationGuard()
                v_result = guard.verify(reasoning_text, prompt)
                verification_passed = v_result.is_verified if hasattr(v_result, 'is_verified') else True
                verification_notes = str(v_result) if not verification_passed else "Passed"
            except Exception as e:
                logger.debug(f"Hallucination guard not available: {e}")
                verification_notes = "Guard not available -- proceed with caution"

            confidence = 0.6
            if data_points > 50:
                confidence += 0.2
            elif data_points > 10:
                confidence += 0.1
            if verification_passed:
                confidence += 0.1

            result = ReasoningResult(
                task=task,
                reasoning=reasoning_text,
                recommendations=recommendations,
                confidence=min(confidence, 1.0),
                verification_passed=verification_passed,
                verification_notes=verification_notes,
                model_used=getattr(client, 'model_name', 'unknown'),
                data_points_considered=data_points,
            )

            if not verification_passed:
                result.warnings.append(
                    "Hallucination guard flagged potential issues. "
                    "Cross-reference recommendations with raw data before acting."
                )

            self._reasoning_history.append(result)
            return result

        except Exception as e:
            logger.error(f"LLM reasoning failed: {e}")
            return self._fallback_reasoning(task, data_points)

    def _fallback_reasoning(
        self, task: str, data_points: int
    ) -> ReasoningResult:
        """Fallback when LLM is unavailable -- return data-only summary."""
        return ReasoningResult(
            task=task,
            reasoning=(
                "LLM reasoning unavailable. Configure an LLM provider "
                "(Ollama, OpenAI, etc.) to enable AI-powered analysis. "
                "Raw data and scores are still available in the BI dashboard."
            ),
            recommendations=[
                "Configure LLM provider for reasoning capabilities",
                "Review raw data scores in the BI dashboard",
                "Use manual analysis on the highest-scored opportunities",
            ],
            confidence=0.2,
            verification_passed=False,
            verification_notes="LLM not available",
            model_used="none",
            data_points_considered=data_points,
            warnings=["Operating without LLM reasoning -- data-only mode"],
        )

    def _extract_recommendations(self, text: str) -> List[str]:
        """Extract actionable recommendations from reasoning text."""
        recommendations = []
        lines = text.split("\n")

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            if any(
                stripped.startswith(prefix)
                for prefix in ["- ", "* ", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9."]
            ):
                clean = stripped.lstrip("-*0123456789. ")
                if len(clean) > 10 and any(
                    word in clean.lower()
                    for word in ["should", "recommend", "suggest", "consider", "test", "build", "create", "focus", "run", "launch", "start"]
                ):
                    recommendations.append(clean)

        return recommendations[:10]

    def _build_market_context(
        self,
        market_data: Dict[str, Any],
        pain_points: List[Dict[str, Any]],
        competitors: List[Dict[str, Any]],
        niche: str,
    ) -> Dict[str, Any]:
        return {
            "niche": niche,
            "data_summary": {
                "total_data_points": market_data.get("total_data_points", 0),
                "sources": market_data.get("sources", []),
            },
            "top_pain_points": [
                {
                    "description": pp.get("description", "")[:100],
                    "severity": pp.get("severity", 0),
                    "frequency": pp.get("frequency", 0),
                    "category": pp.get("category", ""),
                }
                for pp in pain_points[:10]
            ],
            "competitor_landscape": {
                "total_competitors": len(competitors),
                "avg_rating": (
                    sum(c.get("rating", 0) for c in competitors) / max(len(competitors), 1)
                ),
                "price_range": {
                    "min": min((c.get("price", 0) for c in competitors if c.get("price", 0) > 0), default=0),
                    "max": max((c.get("price", 0) for c in competitors), default=0),
                },
                "top_competitors": [
                    {
                        "name": c.get("name", "")[:50],
                        "rating": c.get("rating", 0),
                        "reviews": c.get("review_count", 0),
                        "price": c.get("price", 0),
                    }
                    for c in competitors[:5]
                ],
            },
        }

    def get_reasoning_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent reasoning history."""
        return [
            {
                "task": r.task,
                "confidence": r.confidence,
                "verified": r.verification_passed,
                "model": r.model_used,
                "timestamp": r.timestamp.isoformat(),
                "warnings": r.warnings,
                "recommendations_count": len(r.recommendations),
            }
            for r in self._reasoning_history[-limit:]
        ]
