"""
Reasoning Router — Tiered Intelligence Allocation

Automatically classifies every incoming request into the right reasoning
tier so the system is fast when it can be and deep when it needs to be.

Tier 0 — INSTANT (< 1s):
  Greetings, thanks, simple lookups, cache hits.
  No LLM call at all. Direct response or retrieval only.

Tier 1 — STANDARD (3-8s):
  Normal questions answerable from knowledge base.
  Single model + RAG. This is the default 80% path.

Tier 2 — CONSENSUS (10-30s):
  Complex or ambiguous queries where a single model might hallucinate.
  Layer 1 only (2+ models in parallel), pick the consensus.

Tier 3 — DEEP REASONING (30-180s):
  High-stakes decisions, contradictions detected, explicit user request,
  code changes to production, self-healing above Level 4.
  Full 3-layer pipeline: L1 parallel → L2 synthesis → L3 Grace verify.

Classification signals:
- Query length and complexity
- Ambiguity score from ChatIntelligence
- Confidence from initial RAG retrieval
- Action risk level (read-only vs write vs delete)
- User explicit request ("think deeply", "analyze carefully")
- Contradiction detection between sources
- Self-* agent requesting code/config changes

Classes:
- `ReasoningTier`
- `RoutingDecision`
- `ReasoningRouter`

Key Methods:
- `tier_name()`
- `classify()`
- `classify_self_agent_action()`
- `get_stats()`
- `get_reasoning_router()`

Database Tables:
None (no DB tables)

Connects To:
- `cognitive.learning_hook`
"""

import logging
import re
import time
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import IntEnum
from datetime import datetime

logger = logging.getLogger(__name__)

def _track_routing(desc, **kw):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event("reasoning_router", desc, **kw)
    except Exception:
        pass


class ReasoningTier(IntEnum):
    """Reasoning tiers ordered by depth and cost."""
    INSTANT = 0     # No LLM, direct response
    STANDARD = 1    # Single model + RAG
    CONSENSUS = 2   # L1 parallel (2+ models)
    DEEP = 3        # Full 3-layer (L1 + L2 + L3)


@dataclass
class RoutingDecision:
    """Result of the routing classification."""
    tier: ReasoningTier
    reason: str
    signals: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.8
    estimated_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def tier_name(self) -> str:
        return ["INSTANT", "STANDARD", "CONSENSUS", "DEEP"][self.tier]


class ReasoningRouter:
    """
    Classifies requests into reasoning tiers.

    Fast classification (< 5ms) so it doesn't add latency.
    Uses heuristics first, ML predictions when available.
    """

    # Patterns that trigger Tier 0 (no LLM needed)
    INSTANT_PATTERNS = re.compile(
        r"^(hi|hello|hey|hola|yo|sup|thanks|thank you|bye|goodbye|"
        r"good\s+(morning|afternoon|evening)|see\s+ya|cheers|ok|okay|"
        r"what time|what date|who are you|what is your name)\b",
        re.IGNORECASE
    )

    # Patterns that trigger Tier 3 (deep reasoning required)
    DEEP_PATTERNS = re.compile(
        r"(think\s+(deeply|carefully|hard)|analyze\s+(carefully|thoroughly|in\s+depth)|"
        r"reason\s+(about|through)|compare\s+and\s+contrast|"
        r"what\s+are\s+the\s+pros\s+and\s+cons|"
        r"should\s+I|is\s+it\s+better\s+to|"
        r"debug\s+this|find\s+the\s+(root\s+cause|bug)|"
        r"architect|design\s+pattern|system\s+design|"
        r"refactor\s+the\s+entire|rewrite\s+from\s+scratch|"
        r"critical\s+decision|production\s+deploy|"
        r"why\s+is\s+.{5,}\s+not\s+working|"
        r"explain\s+the\s+difference\s+between\s+.+\s+and\s+)",
        re.IGNORECASE
    )

    # Patterns that suggest Tier 2 (consensus needed)
    CONSENSUS_PATTERNS = re.compile(
        r"(how\s+should|what\s+approach|best\s+practice|"
        r"implement\s+.{10,}|build\s+.{10,}|create\s+.{10,}|"
        r"is\s+this\s+correct|verify\s+this|"
        r"multiple\s+ways|different\s+approaches|"
        r"trade.?offs?|advantages\s+and\s+disadvantages)",
        re.IGNORECASE
    )

    # Risk levels that escalate the tier
    HIGH_RISK_ACTIONS = {
        "delete", "remove", "drop", "destroy", "format",
        "overwrite", "replace_all", "production", "deploy",
        "rollback", "shutdown", "restart", "migrate",
    }

    def __init__(self):
        self.stats = {
            "total_routed": 0,
            "tier_0": 0,
            "tier_1": 0,
            "tier_2": 0,
            "tier_3": 0,
        }

    def classify(
        self,
        query: str,
        ambiguity_score: float = 0.0,
        rag_confidence: float = 0.0,
        action_type: str = "read",
        is_self_agent: bool = False,
        force_tier: Optional[int] = None,
    ) -> RoutingDecision:
        """
        Classify a query into a reasoning tier.

        Args:
            query: The user query or action description
            ambiguity_score: From ChatIntelligence ambiguity detection (0-1)
            rag_confidence: Confidence from initial RAG retrieval (0-1)
            action_type: read/write/delete/execute
            is_self_agent: Whether this is a self-* agent action
            force_tier: Override tier (for explicit user requests)
        """
        self.stats["total_routed"] += 1

        if force_tier is not None:
            tier = ReasoningTier(min(force_tier, 3))
            decision = RoutingDecision(tier=tier, reason="forced_override", confidence=1.0)
            self._record(decision)
            return decision

        signals = {
            "query_length": len(query),
            "word_count": len(query.split()),
            "ambiguity_score": ambiguity_score,
            "rag_confidence": rag_confidence,
            "action_type": action_type,
            "is_self_agent": is_self_agent,
        }

        # Tier 0: Instant
        if self.INSTANT_PATTERNS.match(query.strip()):
            decision = RoutingDecision(
                tier=ReasoningTier.INSTANT,
                reason="greeting_or_simple",
                signals=signals,
                confidence=0.95,
                estimated_time_ms=50,
            )
            self.stats["tier_0"] += 1
            self._record(decision)
            return decision

        # Tier 3: Deep reasoning triggers
        tier3_score = 0.0
        tier3_reasons = []

        if self.DEEP_PATTERNS.search(query):
            tier3_score += 0.5
            tier3_reasons.append("deep_pattern_match")

        if ambiguity_score >= 0.7:
            tier3_score += 0.3
            tier3_reasons.append("high_ambiguity")

        if action_type in ("delete", "execute") and is_self_agent:
            tier3_score += 0.4
            tier3_reasons.append("self_agent_risky_action")

        query_lower = query.lower()
        if any(risk in query_lower for risk in self.HIGH_RISK_ACTIONS):
            tier3_score += 0.3
            tier3_reasons.append("high_risk_keywords")

        if rag_confidence > 0 and rag_confidence < 0.3:
            tier3_score += 0.2
            tier3_reasons.append("low_rag_confidence")

        if len(query.split()) > 50:
            tier3_score += 0.1
            tier3_reasons.append("complex_query")

        if tier3_score >= 0.5:
            decision = RoutingDecision(
                tier=ReasoningTier.DEEP,
                reason="+".join(tier3_reasons),
                signals=signals,
                confidence=min(tier3_score, 1.0),
                estimated_time_ms=90000,
            )
            self.stats["tier_3"] += 1
            self._record(decision)
            return decision

        # Tier 2: Consensus triggers
        tier2_score = 0.0
        tier2_reasons = []

        if self.CONSENSUS_PATTERNS.search(query):
            tier2_score += 0.4
            tier2_reasons.append("consensus_pattern_match")

        if ambiguity_score >= 0.4:
            tier2_score += 0.3
            tier2_reasons.append("moderate_ambiguity")

        if action_type == "write":
            tier2_score += 0.2
            tier2_reasons.append("write_action")

        if len(query.split()) > 25:
            tier2_score += 0.1
            tier2_reasons.append("moderately_complex")

        if tier2_score >= 0.4:
            decision = RoutingDecision(
                tier=ReasoningTier.CONSENSUS,
                reason="+".join(tier2_reasons),
                signals=signals,
                confidence=min(tier2_score, 1.0),
                estimated_time_ms=20000,
            )
            self.stats["tier_2"] += 1
            self._record(decision)
            return decision

        # Tier 1: Standard (default)
        decision = RoutingDecision(
            tier=ReasoningTier.STANDARD,
            reason="default_standard",
            signals=signals,
            confidence=0.8,
            estimated_time_ms=5000,
        )
        self.stats["tier_1"] += 1
        self._record(decision)
        return decision

    def classify_self_agent_action(
        self,
        agent_name: str,
        action_type: str,
        risk_level: str = "low",
    ) -> RoutingDecision:
        """
        Classify a self-* agent action into a reasoning tier.

        Low risk (read, observe, analyze) -> Tier 0-1
        Medium risk (learn, practice) -> Tier 1
        High risk (modify code, change config) -> Tier 2-3
        Critical risk (delete, production deploy) -> Tier 3
        """
        if risk_level == "critical":
            return self.classify(
                f"{agent_name} wants to {action_type}",
                action_type="execute",
                is_self_agent=True,
                force_tier=3,
            )
        elif risk_level == "high":
            return self.classify(
                f"{agent_name} wants to {action_type}",
                action_type="write",
                is_self_agent=True,
            )
        elif risk_level == "medium":
            return self.classify(
                f"{agent_name} wants to {action_type}",
                action_type="read",
                is_self_agent=True,
            )
        else:
            return RoutingDecision(
                tier=ReasoningTier.STANDARD,
                reason=f"low_risk_self_agent_{agent_name}",
                confidence=0.9,
                estimated_time_ms=5000,
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics."""
        total = max(self.stats["total_routed"], 1)
        return {
            **self.stats,
            "tier_distribution": {
                "instant": round(self.stats["tier_0"] / total, 3),
                "standard": round(self.stats["tier_1"] / total, 3),
                "consensus": round(self.stats["tier_2"] / total, 3),
                "deep": round(self.stats["tier_3"] / total, 3),
            }
        }

    def _record(self, decision: RoutingDecision):
        """Record routing decision for learning."""
        _track_routing(
            f"Tier {decision.tier_name}: {decision.reason}",
            confidence=decision.confidence,
        )


_router: Optional[ReasoningRouter] = None

def get_reasoning_router() -> ReasoningRouter:
    """Get the reasoning router singleton."""
    global _router
    if _router is None:
        _router = ReasoningRouter()
    return _router
