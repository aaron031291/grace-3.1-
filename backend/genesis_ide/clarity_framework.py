import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import uuid
logger = logging.getLogger(__name__)

class ClarityLevel(str, Enum):
    """Levels of clarity for an action."""
    CRYSTAL = "crystal"     # Fully clear, verified, documented
    CLEAR = "clear"         # Clear intent, good traceability
    PARTIAL = "partial"     # Some ambiguity or gaps
    UNCLEAR = "unclear"     # Needs clarification
    OPAQUE = "opaque"       # Cannot determine intent


@dataclass
class ClarityContext:
    """
    Context for ensuring clarity in an action.

    Captures:
    - What: The action being performed
    - Why: The reason/intent
    - Who: The actor (user, system, etc.)
    - When: Timestamp
    - How: The method/approach
    - Expected: Expected outcome
    - Actual: Actual outcome
    """
    context_id: str
    what: str
    why: str
    who: str
    when: datetime = field(default_factory=datetime.utcnow)
    how: Optional[str] = None
    expected_outcome: Optional[str] = None
    actual_outcome: Optional[str] = None
    clarity_level: ClarityLevel = ClarityLevel.PARTIAL
    genesis_key_id: Optional[str] = None
    verification_status: str = "pending"  # pending, verified, failed
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_id": self.context_id,
            "what": self.what,
            "why": self.why,
            "who": self.who,
            "when": self.when.isoformat(),
            "how": self.how,
            "expected_outcome": self.expected_outcome,
            "actual_outcome": self.actual_outcome,
            "clarity_level": self.clarity_level.value,
            "genesis_key_id": self.genesis_key_id,
            "verification_status": self.verification_status,
            "evidence": self.evidence
        }


class ClarityFramework:
    """
    Framework for ensuring clarity in all IDE actions.

    Every action goes through:
    1. Intent Declaration: State what and why
    2. Execution Tracking: Record how
    3. Outcome Verification: Validate results
    """

    def __init__(
        self,
        session=None,
        genesis_service=None
    ):
        self.session = session
        self._genesis_service = genesis_service

        # Active clarity contexts
        self._active_contexts: Dict[str, ClarityContext] = {}

        # Completed contexts (for learning)
        self._completed_contexts: List[ClarityContext] = []

        # Clarity rules
        self._clarity_rules: List[Dict[str, Any]] = []

        # Metrics
        self.metrics = {
            "contexts_created": 0,
            "contexts_verified": 0,
            "contexts_failed": 0,
            "average_clarity": 0.0
        }

        self._load_clarity_rules()

        logger.info("[CLARITY] Framework initialized")

    def _load_clarity_rules(self):
        """Load clarity rules for validation."""
        self._clarity_rules = [
            {
                "name": "intent_required",
                "description": "Every action must have a clear intent (why)",
                "check": lambda ctx: bool(ctx.why and len(ctx.why) > 5)
            },
            {
                "name": "actor_identified",
                "description": "Every action must identify who is performing it",
                "check": lambda ctx: bool(ctx.who)
            },
            {
                "name": "expected_outcome",
                "description": "Actions should have expected outcomes",
                "check": lambda ctx: bool(ctx.expected_outcome)
            },
            {
                "name": "genesis_tracked",
                "description": "Actions should be tracked with Genesis Keys",
                "check": lambda ctx: bool(ctx.genesis_key_id)
            }
        ]

    def create_context(
        self,
        what: str,
        why: str,
        who: str,
        how: Optional[str] = None,
        expected_outcome: Optional[str] = None
    ) -> ClarityContext:
        """
        Create a clarity context for an action.

        Args:
            what: What action is being performed
            why: Why it's being performed
            who: Who is performing it
            how: How it will be done
            expected_outcome: What outcome is expected

        Returns:
            ClarityContext for tracking
        """
        context = ClarityContext(
            context_id=f"CLARITY-{uuid.uuid4().hex[:12]}",
            what=what,
            why=why,
            who=who,
            how=how,
            expected_outcome=expected_outcome
        )

        # Create Genesis Key
        if self._genesis_service:
            from models.genesis_key_models import GenesisKeyType
            genesis_key = self._genesis_service.create_key(
                key_type=GenesisKeyType.CLARITY_CONTEXT,
                what_description=what,
                who_actor=who,
                why_reason=why,
                how_method=how or "Not specified",
                context_data={
                    "context_id": context.context_id,
                    "expected_outcome": expected_outcome
                },
                session=self.session
            )
            context.genesis_key_id = genesis_key.key_id

        # Calculate initial clarity level
        context.clarity_level = self._assess_clarity(context)

        self._active_contexts[context.context_id] = context
        self.metrics["contexts_created"] += 1

        logger.debug(f"[CLARITY] Created context {context.context_id}: {what[:50]}")

        return context

    def update_context(
        self,
        context_id: str,
        actual_outcome: Optional[str] = None,
        evidence: Optional[List[str]] = None
    ) -> Optional[ClarityContext]:
        """Update a clarity context with outcomes."""
        if context_id not in self._active_contexts:
            return None

        context = self._active_contexts[context_id]

        if actual_outcome:
            context.actual_outcome = actual_outcome

        if evidence:
            context.evidence.extend(evidence)

        # Re-assess clarity
        context.clarity_level = self._assess_clarity(context)

        return context

    def verify_context(self, context_id: str) -> Dict[str, Any]:
        """
        Verify that a context's outcome matches expectations.

        Returns verification result with details.
        """
        if context_id not in self._active_contexts:
            return {"error": "Context not found"}

        context = self._active_contexts[context_id]

        # Check clarity rules
        rule_results = []
        for rule in self._clarity_rules:
            passed = rule["check"](context)
            rule_results.append({
                "rule": rule["name"],
                "passed": passed,
                "description": rule["description"]
            })

        all_passed = all(r["passed"] for r in rule_results)

        # Check outcome match
        outcome_match = True
        if context.expected_outcome and context.actual_outcome:
            # Simple keyword matching
            expected_words = set(context.expected_outcome.lower().split())
            actual_words = set(context.actual_outcome.lower().split())
            overlap = len(expected_words & actual_words) / max(len(expected_words), 1)
            outcome_match = overlap > 0.3

        # Determine verification status
        if all_passed and outcome_match:
            context.verification_status = "verified"
            self.metrics["contexts_verified"] += 1
        else:
            context.verification_status = "failed"
            self.metrics["contexts_failed"] += 1

        # Move to completed
        del self._active_contexts[context_id]
        self._completed_contexts.append(context)

        # Update average clarity
        clarity_values = {
            ClarityLevel.CRYSTAL: 1.0,
            ClarityLevel.CLEAR: 0.8,
            ClarityLevel.PARTIAL: 0.5,
            ClarityLevel.UNCLEAR: 0.2,
            ClarityLevel.OPAQUE: 0.0
        }
        total_clarity = sum(
            clarity_values.get(c.clarity_level, 0.5)
            for c in self._completed_contexts[-100:]
        )
        self.metrics["average_clarity"] = total_clarity / min(len(self._completed_contexts), 100)

        return {
            "context_id": context_id,
            "verification_status": context.verification_status,
            "clarity_level": context.clarity_level.value,
            "rule_results": rule_results,
            "outcome_match": outcome_match,
            "evidence": context.evidence
        }

    def _assess_clarity(self, context: ClarityContext) -> ClarityLevel:
        """Assess the clarity level of a context."""
        score = 0

        # Check each aspect
        if context.what and len(context.what) > 10:
            score += 1
        if context.why and len(context.why) > 10:
            score += 1
        if context.who:
            score += 1
        if context.how:
            score += 1
        if context.expected_outcome:
            score += 1
        if context.genesis_key_id:
            score += 1
        if context.actual_outcome:
            score += 1
        if context.evidence:
            score += 1

        # Map score to clarity level
        if score >= 7:
            return ClarityLevel.CRYSTAL
        elif score >= 5:
            return ClarityLevel.CLEAR
        elif score >= 3:
            return ClarityLevel.PARTIAL
        elif score >= 1:
            return ClarityLevel.UNCLEAR
        else:
            return ClarityLevel.OPAQUE

    def get_active_contexts(self) -> List[Dict[str, Any]]:
        """Get all active clarity contexts."""
        return [c.to_dict() for c in self._active_contexts.values()]

    def get_metrics(self) -> Dict[str, Any]:
        """Get clarity framework metrics."""
        return {
            **self.metrics,
            "active_contexts": len(self._active_contexts),
            "completed_contexts": len(self._completed_contexts)
        }

    def generate_clarity_report(self) -> Dict[str, Any]:
        """Generate a clarity report for recent actions."""
        recent = self._completed_contexts[-50:]

        if not recent:
            return {"message": "No completed contexts to report on"}

        clarity_distribution = {}
        verification_distribution = {"verified": 0, "failed": 0, "pending": 0}

        for ctx in recent:
            clarity_distribution[ctx.clarity_level.value] = \
                clarity_distribution.get(ctx.clarity_level.value, 0) + 1
            verification_distribution[ctx.verification_status] += 1

        return {
            "total_contexts": len(recent),
            "clarity_distribution": clarity_distribution,
            "verification_distribution": verification_distribution,
            "average_clarity": self.metrics["average_clarity"],
            "recommendations": self._generate_recommendations(clarity_distribution)
        }

    def _generate_recommendations(self, distribution: Dict[str, int]) -> List[str]:
        """Generate recommendations based on clarity distribution."""
        recommendations = []

        unclear_count = distribution.get("unclear", 0) + distribution.get("opaque", 0)
        total = sum(distribution.values()) or 1

        if unclear_count / total > 0.3:
            recommendations.append(
                "High number of unclear actions. Consider adding more explicit intents (why)."
            )

        if distribution.get("partial", 0) / total > 0.5:
            recommendations.append(
                "Many actions have partial clarity. Consider adding expected outcomes."
            )

        if not recommendations:
            recommendations.append("Clarity levels are good. Keep up the clear documentation!")

        return recommendations
