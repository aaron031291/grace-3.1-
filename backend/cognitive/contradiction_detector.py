"""
Contradiction Detector - Cognitive Consistency Enforcement

Addresses Clarity Class 10 (Contradiction Detection):
- Detect logical contradictions in reasoning
- Identify drift from established patterns
- Flag conflicting outputs
- Trigger AVN (Ambiguity/Validation/Negotiation) fallback

Contradiction types:
1. Logical: Direct logical contradictions in reasoning
2. Temporal: Contradictions with previous outputs
3. Constitutional: Contradictions with core rules
4. Pattern: Drift from learned patterns
5. Confidence: Overconfident claims without support
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Set, Tuple

from core.base_component import BaseComponent, ComponentRole
from core.loop_output import GraceLoopOutput, ReasoningStep

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND TYPES
# =============================================================================

class ContradictionType(Enum):
    """Types of contradictions."""
    LOGICAL = "logical"           # Direct logical contradiction
    TEMPORAL = "temporal"         # Contradicts previous output
    CONSTITUTIONAL = "constitutional"  # Contradicts core rules
    PATTERN = "pattern"           # Drifts from learned patterns
    CONFIDENCE = "confidence"     # Overconfident without support
    SEMANTIC = "semantic"         # Semantic inconsistency


class ContradictionSeverity(Enum):
    """Severity levels for contradictions."""
    LOW = "low"           # Minor inconsistency
    MEDIUM = "medium"     # Notable contradiction
    HIGH = "high"         # Significant contradiction
    CRITICAL = "critical" # Blocks operation


class AVNAction(Enum):
    """Actions for Ambiguity/Validation/Negotiation fallback."""
    ACCEPT = "accept"           # Accept despite contradiction
    REJECT = "reject"           # Reject due to contradiction
    CLARIFY = "clarify"         # Request clarification
    NEGOTIATE = "negotiate"     # Propose alternative
    ESCALATE = "escalate"       # Escalate to human


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Contradiction:
    """A detected contradiction."""
    contradiction_id: str
    contradiction_type: ContradictionType
    severity: ContradictionSeverity
    description: str
    source_a: str  # First conflicting element
    source_b: str  # Second conflicting element
    context: Dict[str, Any] = field(default_factory=dict)
    suggested_resolution: Optional[str] = None
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contradiction_id": self.contradiction_id,
            "type": self.contradiction_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "source_a": self.source_a,
            "source_b": self.source_b,
            "context": self.context,
            "suggested_resolution": self.suggested_resolution,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class AVNResult:
    """Result of AVN fallback processing."""
    action: AVNAction
    reasoning: str
    modified_output: Optional[Dict[str, Any]] = None
    contradictions_resolved: List[str] = field(default_factory=list)
    requires_human_review: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "reasoning": self.reasoning,
            "modified_output": self.modified_output,
            "contradictions_resolved": self.contradictions_resolved,
            "requires_human_review": self.requires_human_review,
        }


@dataclass
class LintResult:
    """Result of cognition linting."""
    passed: bool
    contradictions: List[Contradiction] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    avn_result: Optional[AVNResult] = None
    lint_time_ms: float = 0.0

    @property
    def has_critical(self) -> bool:
        return any(c.severity == ContradictionSeverity.CRITICAL for c in self.contradictions)

    @property
    def has_high(self) -> bool:
        return any(c.severity == ContradictionSeverity.HIGH for c in self.contradictions)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "contradictions": [c.to_dict() for c in self.contradictions],
            "warnings": self.warnings,
            "suggestions": self.suggestions,
            "avn_result": self.avn_result.to_dict() if self.avn_result else None,
            "lint_time_ms": self.lint_time_ms,
            "has_critical": self.has_critical,
            "has_high": self.has_high,
        }


# =============================================================================
# CONTRADICTION DETECTOR
# =============================================================================

class GraceCognitionLinter(BaseComponent):
    """
    Lints cognitive outputs for contradictions and inconsistencies.

    Provides:
    - Logical contradiction detection
    - Temporal consistency checking
    - Constitutional alignment verification
    - Pattern drift detection
    - Confidence validation
    - AVN fallback handling

    Usage:
        linter = GraceCognitionLinter()
        await linter.activate()

        result = await linter.lint(loop_output)

        if not result.passed:
            # Handle contradictions
            if result.has_critical:
                # Block operation
                pass
            elif result.avn_result:
                # Apply AVN resolution
                pass
    """

    def __init__(self):
        super().__init__(
            name="CognitionLinter",
            version="1.0.0",
            role=ComponentRole.GOVERNANCE,
            description="Detects contradictions and ensures cognitive consistency",
            capabilities={"contradiction_detection", "cognition_linting", "avn_fallback"},
            tags={"clarity", "consistency", "governance"},
        )

        # History for temporal checks
        self._output_history: deque = deque(maxlen=1000)
        self._claim_history: deque = deque(maxlen=5000)

        # Constitutional rules (loaded from governance)
        self._constitutional_claims: Set[str] = set()
        self._load_constitutional_claims()

        # Pattern baselines (would be loaded from learning system)
        self._pattern_baselines: Dict[str, Dict[str, float]] = {}

        # Stats
        self._lint_stats = {
            "total_lints": 0,
            "passed": 0,
            "failed": 0,
            "contradictions_found": 0,
            "avn_invocations": 0,
        }

    async def _do_activate(self):
        """Initialize the linter."""
        logger.info("[LINTER] Cognition linter activated")

    async def _do_deactivate(self):
        """Cleanup."""
        logger.info("[LINTER] Cognition linter deactivated")

    # =========================================================================
    # MAIN LINTING
    # =========================================================================

    async def lint(
        self,
        output: GraceLoopOutput,
        context: Optional[Dict[str, Any]] = None,
    ) -> LintResult:
        """
        Lint a cognitive loop output for contradictions.

        Args:
            output: The loop output to lint
            context: Additional context for linting

        Returns:
            LintResult with contradictions and recommendations
        """
        import time
        start_time = time.time()

        self._lint_stats["total_lints"] += 1
        contradictions: List[Contradiction] = []
        warnings: List[str] = []
        suggestions: List[str] = []

        # Run all contradiction checks
        contradictions.extend(await self._check_logical_contradictions(output))
        contradictions.extend(await self._check_temporal_contradictions(output))
        contradictions.extend(await self._check_constitutional_alignment(output))
        contradictions.extend(await self._check_confidence_validity(output))
        contradictions.extend(await self._check_pattern_drift(output))

        # Process results
        self._lint_stats["contradictions_found"] += len(contradictions)

        # Determine if passed
        has_critical = any(c.severity == ContradictionSeverity.CRITICAL for c in contradictions)
        has_high = any(c.severity == ContradictionSeverity.HIGH for c in contradictions)
        passed = not has_critical and not has_high

        if not passed:
            self._lint_stats["failed"] += 1
        else:
            self._lint_stats["passed"] += 1

        # Generate suggestions
        for c in contradictions:
            if c.suggested_resolution:
                suggestions.append(c.suggested_resolution)

        # Invoke AVN if needed
        avn_result = None
        if contradictions and not passed:
            self._lint_stats["avn_invocations"] += 1
            avn_result = await self._invoke_avn(output, contradictions)

        # Store in history for future temporal checks
        self._store_output(output)

        lint_time = (time.time() - start_time) * 1000

        return LintResult(
            passed=passed,
            contradictions=contradictions,
            warnings=warnings,
            suggestions=suggestions,
            avn_result=avn_result,
            lint_time_ms=lint_time,
        )

    # =========================================================================
    # CONTRADICTION CHECKS
    # =========================================================================

    async def _check_logical_contradictions(
        self,
        output: GraceLoopOutput
    ) -> List[Contradiction]:
        """Check for logical contradictions within the output."""
        contradictions = []

        # Extract claims from reasoning steps
        claims = self._extract_claims(output)

        # Check for direct negations
        for i, claim_a in enumerate(claims):
            for claim_b in claims[i+1:]:
                if self._are_contradictory(claim_a, claim_b):
                    contradictions.append(Contradiction(
                        contradiction_id=f"logical-{output.loop_id}-{len(contradictions)}",
                        contradiction_type=ContradictionType.LOGICAL,
                        severity=ContradictionSeverity.HIGH,
                        description=f"Contradictory claims in reasoning",
                        source_a=claim_a,
                        source_b=claim_b,
                        suggested_resolution="Resolve conflicting claims before proceeding",
                    ))

        return contradictions

    async def _check_temporal_contradictions(
        self,
        output: GraceLoopOutput
    ) -> List[Contradiction]:
        """Check for contradictions with recent outputs."""
        contradictions = []

        # Get recent outputs of same type
        recent = [
            o for o in self._output_history
            if o.loop_type == output.loop_type
            and (datetime.now() - o.completed_at) < timedelta(hours=1)
        ]

        if not recent:
            return contradictions

        # Compare current claims with recent claims
        current_claims = self._extract_claims(output)

        for prev_output in recent[-10:]:  # Check last 10
            prev_claims = self._extract_claims(prev_output)

            for current_claim in current_claims:
                for prev_claim in prev_claims:
                    if self._are_temporally_contradictory(current_claim, prev_claim):
                        contradictions.append(Contradiction(
                            contradiction_id=f"temporal-{output.loop_id}-{len(contradictions)}",
                            contradiction_type=ContradictionType.TEMPORAL,
                            severity=ContradictionSeverity.MEDIUM,
                            description=f"Contradicts previous output from {prev_output.loop_id}",
                            source_a=current_claim,
                            source_b=prev_claim,
                            context={
                                "previous_loop_id": prev_output.loop_id,
                                "time_delta_seconds": (datetime.now() - prev_output.completed_at).total_seconds(),
                            },
                            suggested_resolution="Explain or acknowledge the change from previous position",
                        ))

        return contradictions

    async def _check_constitutional_alignment(
        self,
        output: GraceLoopOutput
    ) -> List[Contradiction]:
        """Check for contradictions with constitutional rules."""
        contradictions = []

        # Extract claims
        claims = self._extract_claims(output)
        result_text = str(output.result) + " " + output.result_summary

        # Check against constitutional claims
        for claim in claims:
            violation = self._check_constitutional_violation(claim)
            if violation:
                contradictions.append(Contradiction(
                    contradiction_id=f"constitutional-{output.loop_id}-{len(contradictions)}",
                    contradiction_type=ContradictionType.CONSTITUTIONAL,
                    severity=ContradictionSeverity.CRITICAL,
                    description=f"Violates constitutional rule: {violation}",
                    source_a=claim,
                    source_b=violation,
                    suggested_resolution="Action must not violate constitutional rules",
                ))

        # Check result for safety violations
        safety_patterns = [
            (r"bypass\s+(safety|security)", "Attempting to bypass safety measures"),
            (r"ignore\s+(warning|constraint)", "Ignoring safety constraints"),
            (r"override\s+(governance|policy)", "Overriding governance"),
        ]

        for pattern, violation_type in safety_patterns:
            if re.search(pattern, result_text, re.IGNORECASE):
                contradictions.append(Contradiction(
                    contradiction_id=f"constitutional-{output.loop_id}-{len(contradictions)}",
                    contradiction_type=ContradictionType.CONSTITUTIONAL,
                    severity=ContradictionSeverity.CRITICAL,
                    description=violation_type,
                    source_a=result_text[:200],
                    source_b="Constitutional safety requirements",
                    suggested_resolution="Remove safety-violating content",
                ))

        return contradictions

    async def _check_confidence_validity(
        self,
        output: GraceLoopOutput
    ) -> List[Contradiction]:
        """Check for overconfident claims without support."""
        contradictions = []

        # Check overall confidence vs support
        if output.confidence > 0.9 and output.step_count < 2:
            contradictions.append(Contradiction(
                contradiction_id=f"confidence-{output.loop_id}-0",
                contradiction_type=ContradictionType.CONFIDENCE,
                severity=ContradictionSeverity.MEDIUM,
                description="High confidence with minimal reasoning support",
                source_a=f"Confidence: {output.confidence}",
                source_b=f"Reasoning steps: {output.step_count}",
                suggested_resolution="Add more reasoning steps or reduce confidence",
            ))

        # Check step confidence consistency
        if output.reasoning_steps:
            step_confidences = [s.confidence for s in output.reasoning_steps]
            avg_step_conf = sum(step_confidences) / len(step_confidences)

            # Final confidence shouldn't be much higher than step average
            if output.confidence > avg_step_conf + 0.3:
                contradictions.append(Contradiction(
                    contradiction_id=f"confidence-{output.loop_id}-1",
                    contradiction_type=ContradictionType.CONFIDENCE,
                    severity=ContradictionSeverity.LOW,
                    description="Final confidence exceeds reasoning support",
                    source_a=f"Final confidence: {output.confidence:.2f}",
                    source_b=f"Average step confidence: {avg_step_conf:.2f}",
                    suggested_resolution="Align final confidence with reasoning support",
                ))

        return contradictions

    async def _check_pattern_drift(
        self,
        output: GraceLoopOutput
    ) -> List[Contradiction]:
        """Check for drift from established patterns."""
        contradictions = []

        # Get pattern baseline for this loop type
        baseline = self._pattern_baselines.get(output.loop_type.value)
        if not baseline:
            return contradictions

        # Check step count deviation
        if "avg_steps" in baseline:
            expected_steps = baseline["avg_steps"]
            if output.step_count < expected_steps * 0.3:
                contradictions.append(Contradiction(
                    contradiction_id=f"pattern-{output.loop_id}-0",
                    contradiction_type=ContradictionType.PATTERN,
                    severity=ContradictionSeverity.LOW,
                    description="Significantly fewer reasoning steps than typical",
                    source_a=f"Current steps: {output.step_count}",
                    source_b=f"Typical steps: {expected_steps:.1f}",
                    suggested_resolution="Consider if sufficient reasoning was applied",
                ))

        # Check duration deviation
        if "avg_duration_ms" in baseline:
            expected_duration = baseline["avg_duration_ms"]
            if output.duration_ms < expected_duration * 0.1:
                contradictions.append(Contradiction(
                    contradiction_id=f"pattern-{output.loop_id}-1",
                    contradiction_type=ContradictionType.PATTERN,
                    severity=ContradictionSeverity.LOW,
                    description="Unusually fast execution may indicate shallow processing",
                    source_a=f"Current duration: {output.duration_ms:.0f}ms",
                    source_b=f"Typical duration: {expected_duration:.0f}ms",
                ))

        return contradictions

    # =========================================================================
    # AVN FALLBACK
    # =========================================================================

    async def _invoke_avn(
        self,
        output: GraceLoopOutput,
        contradictions: List[Contradiction]
    ) -> AVNResult:
        """
        Invoke Ambiguity/Validation/Negotiation fallback.

        Decides how to handle contradictions:
        - Accept with warning
        - Reject entirely
        - Request clarification
        - Propose alternative
        - Escalate to human
        """
        # Count by severity
        critical_count = sum(1 for c in contradictions if c.severity == ContradictionSeverity.CRITICAL)
        high_count = sum(1 for c in contradictions if c.severity == ContradictionSeverity.HIGH)

        # Determine action
        if critical_count > 0:
            # Constitutional violations - escalate or reject
            if any(c.contradiction_type == ContradictionType.CONSTITUTIONAL for c in contradictions):
                return AVNResult(
                    action=AVNAction.REJECT,
                    reasoning=f"Output violates {critical_count} constitutional rules",
                    requires_human_review=True,
                    contradictions_resolved=[],
                )
            else:
                return AVNResult(
                    action=AVNAction.ESCALATE,
                    reasoning=f"Critical contradictions require human review",
                    requires_human_review=True,
                    contradictions_resolved=[],
                )

        elif high_count > 0:
            # High severity - negotiate or clarify
            logical = [c for c in contradictions if c.contradiction_type == ContradictionType.LOGICAL]
            if logical:
                return AVNResult(
                    action=AVNAction.CLARIFY,
                    reasoning="Logical contradictions in reasoning need resolution",
                    requires_human_review=False,
                    contradictions_resolved=[],
                )
            else:
                return AVNResult(
                    action=AVNAction.NEGOTIATE,
                    reasoning="Attempting to resolve high-severity contradictions",
                    modified_output=self._attempt_resolution(output, contradictions),
                    contradictions_resolved=[c.contradiction_id for c in contradictions if c.severity == ContradictionSeverity.HIGH],
                    requires_human_review=False,
                )

        else:
            # Low/medium - accept with warning
            return AVNResult(
                action=AVNAction.ACCEPT,
                reasoning=f"Accepting with {len(contradictions)} low/medium warnings",
                requires_human_review=False,
                contradictions_resolved=[],
            )

    def _attempt_resolution(
        self,
        output: GraceLoopOutput,
        contradictions: List[Contradiction]
    ) -> Dict[str, Any]:
        """Attempt automatic resolution of contradictions."""
        modified = output.to_dict()

        # Lower confidence if confidence-related
        confidence_issues = [c for c in contradictions if c.contradiction_type == ContradictionType.CONFIDENCE]
        if confidence_issues:
            modified["confidence"] = min(output.confidence, output.average_step_confidence)

        # Add warning to summary
        warnings = [c.description for c in contradictions]
        modified["result_summary"] = f"{output.result_summary} [WARNINGS: {'; '.join(warnings[:3])}]"

        return modified

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _extract_claims(self, output: GraceLoopOutput) -> List[str]:
        """Extract claims from loop output."""
        claims = []

        # From reasoning steps
        for step in output.reasoning_steps:
            if step.output:
                # Split into sentences
                sentences = re.split(r'[.!?]', step.output)
                claims.extend([s.strip() for s in sentences if s.strip()])

        # From result summary
        if output.result_summary:
            sentences = re.split(r'[.!?]', output.result_summary)
            claims.extend([s.strip() for s in sentences if s.strip()])

        return claims[:50]  # Limit to 50 claims

    def _are_contradictory(self, claim_a: str, claim_b: str) -> bool:
        """Check if two claims are logically contradictory."""
        a_lower = claim_a.lower()
        b_lower = claim_b.lower()

        # Simple negation patterns
        negation_pairs = [
            ("is not", "is"),
            ("cannot", "can"),
            ("won't", "will"),
            ("doesn't", "does"),
            ("isn't", "is"),
            ("never", "always"),
            ("false", "true"),
            ("no", "yes"),
        ]

        for neg, pos in negation_pairs:
            if neg in a_lower and pos in b_lower:
                # Check if they're about the same subject
                # Simple overlap check
                a_words = set(a_lower.split())
                b_words = set(b_lower.split())
                overlap = len(a_words & b_words)
                if overlap > 2:
                    return True

        return False

    def _are_temporally_contradictory(self, current: str, previous: str) -> bool:
        """Check if current claim contradicts a previous one."""
        # Similar to _are_contradictory but more lenient
        # Only flag if clearly contradictory about same topic
        return self._are_contradictory(current, previous)

    def _check_constitutional_violation(self, claim: str) -> Optional[str]:
        """Check if claim violates constitutional rules."""
        claim_lower = claim.lower()

        # Constitutional violation patterns
        violations = {
            "harm human": "Human Centricity",
            "ignore safety": "Safety First",
            "bypass governance": "Transparency Required",
            "hide from audit": "Transparency Required",
            "act without permission": "Trust Earned",
        }

        for pattern, rule in violations.items():
            if pattern in claim_lower:
                return rule

        return None

    def _load_constitutional_claims(self):
        """Load constitutional claims from governance."""
        self._constitutional_claims = {
            "human_wellbeing_priority",
            "safety_first",
            "transparency_required",
            "trust_earned",
            "reversibility_preferred",
        }

    def _store_output(self, output: GraceLoopOutput):
        """Store output in history for temporal checks."""
        if output.completed_at:
            self._output_history.append(output)

    def update_pattern_baseline(self, loop_type: str, metrics: Dict[str, float]):
        """Update pattern baseline for a loop type."""
        self._pattern_baselines[loop_type] = metrics

    def get_stats(self) -> Dict[str, Any]:
        """Get linting statistics."""
        return {
            **self._lint_stats,
            "history_size": len(self._output_history),
            "claim_history_size": len(self._claim_history),
            "pattern_baselines": list(self._pattern_baselines.keys()),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_linter: Optional[GraceCognitionLinter] = None


def get_cognition_linter() -> GraceCognitionLinter:
    """Get or create the global cognition linter."""
    global _linter
    if _linter is None:
        _linter = GraceCognitionLinter()
        logger.info("[LINTER] Created global Cognition Linter")
    return _linter


def reset_linter():
    """Reset linter (for testing)."""
    global _linter
    _linter = None
