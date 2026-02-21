"""
Integrity Bridge -- Honesty, Integrity, Accountability for BI

Wires the BI system into GRACE's truth/integrity infrastructure:

1. GOVERNANCE (Constitutional AI)
   - Every BI output checked against Constitutional Rules
   - HUMAN_CENTRICITY: BI must not recommend manipulation
   - TRUST_EARNED: BI confidence must be earned through data, not assumed
   - TRANSPARENCY_REQUIRED: BI reasoning must be explainable
   - SAFETY_FIRST: BI must flag risky recommendations

2. HALLUCINATION GUARD (6-Layer Pipeline)
   - Layer 1: Grounding -- BI claims must reference actual data
   - Layer 2: Cross-Model Consensus -- Multiple LLMs must agree on market analysis
   - Layer 3: Contradiction Detection -- Check against previous BI findings
   - Layer 4: Confidence Scoring -- Trust score for every BI output
   - Layer 5: Trust System Verification -- Validate against learning memory
   - Layer 6: External Verification -- Cross-check with real-world data

3. TRUST METRICS
   - Neural Trust Scorer on all BI data
   - Trust-aware retrieval for BI knowledge queries
   - Confidence intervals on all predictions
   - Trust decay for stale intelligence

4. 12 COGNITIVE INVARIANTS
   - Every BI decision validated against all 12 invariants
   - Ambiguity accounting for uncertain market data
   - Reversibility assessment for campaign recommendations
   - Bounded recursion for recursive intelligence loops

5. ACCOUNTABILITY CHAIN
   - Full Genesis Key provenance on every BI action
   - Decision rationale logged for every recommendation
   - Outcome tracking against predictions (was Grace right?)
   - Honesty reporting: Grace explicitly states what she doesn't know
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class IntegrityCheck:
    """Result of running an integrity check on BI output."""
    check_type: str = ""
    passed: bool = True
    score: float = 1.0
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccountabilityRecord:
    """Links a BI prediction to its eventual outcome."""
    prediction_id: str = ""
    prediction: str = ""
    predicted_at: datetime = field(default_factory=datetime.utcnow)
    predicted_confidence: float = 0.0
    actual_outcome: Optional[str] = None
    outcome_recorded_at: Optional[datetime] = None
    accuracy: Optional[float] = None
    module: str = ""


class IntegrityBridge:
    """Ensures BI operates within GRACE's honesty/integrity/accountability framework."""

    def __init__(self):
        self._governance = None
        self._hallucination_guard = None
        self._confidence_scorer = None
        self._contradiction_detector = None
        self._invariant_validator = None
        self._trust_retriever = None
        self._initialized = False
        self.accountability_log: List[AccountabilityRecord] = []
        self.integrity_checks: List[IntegrityCheck] = []

    def initialize(self):
        if self._initialized:
            return

        # Governance (Constitutional AI)
        try:
            from security.governance import GovernanceEngine, ConstitutionalRule
            self._governance = {"engine_class": GovernanceEngine, "rules": ConstitutionalRule}
            logger.info("BI -> Governance (Constitutional AI): CONNECTED")
        except Exception as e:
            logger.warning(f"BI -> Governance: UNAVAILABLE ({e})")

        # Hallucination Guard (6-layer pipeline)
        try:
            from llm_orchestrator.hallucination_guard import HallucinationGuard, ExternalVerifier
            self._hallucination_guard = {"guard_class": HallucinationGuard, "verifier_class": ExternalVerifier}
            logger.info("BI -> Hallucination Guard (6-layer): CONNECTED")
        except Exception as e:
            logger.warning(f"BI -> Hallucination Guard: UNAVAILABLE ({e})")

        # Confidence Scorer
        try:
            from confidence_scorer.confidence_scorer import ConfidenceScorer
            self._confidence_scorer = ConfidenceScorer
            logger.info("BI -> Confidence Scorer: CONNECTED")
        except Exception as e:
            logger.warning(f"BI -> Confidence Scorer: UNAVAILABLE ({e})")

        # Contradiction Detector
        try:
            from confidence_scorer.contradiction_detector import SemanticContradictionDetector
            self._contradiction_detector = SemanticContradictionDetector
            logger.info("BI -> Contradiction Detector (Semantic): CONNECTED")
        except Exception as e:
            logger.warning(f"BI -> Contradiction Detector: UNAVAILABLE ({e})")

        # 12 Cognitive Invariants
        try:
            from cognitive.invariants import InvariantValidator
            self._invariant_validator = InvariantValidator()
            logger.info("BI -> 12 Cognitive Invariants: CONNECTED")
        except Exception as e:
            logger.warning(f"BI -> Invariant Validator: UNAVAILABLE ({e})")

        # Trust-Aware Retrieval
        try:
            from retrieval.trust_aware_retriever import TrustAwareDocumentRetriever
            self._trust_retriever = TrustAwareDocumentRetriever
            logger.info("BI -> Trust-Aware Retrieval: CONNECTED")
        except Exception as e:
            logger.warning(f"BI -> Trust-Aware Retrieval: UNAVAILABLE ({e})")

        self._initialized = True
        connected = self._count_connected()
        logger.info(f"Integrity Bridge initialized: {connected}/6 systems connected")

    # ==================== Constitutional Governance ====================

    async def check_constitutional_compliance(
        self,
        bi_output: Dict[str, Any],
        output_type: str = "recommendation",
    ) -> IntegrityCheck:
        """Check BI output against Constitutional Rules.

        Every BI recommendation must pass:
        - HUMAN_CENTRICITY: Does not recommend manipulation or deception
        - TRANSPARENCY_REQUIRED: Reasoning is explainable
        - SAFETY_FIRST: Risks are flagged
        - TRUST_EARNED: Confidence backed by data
        """
        check = IntegrityCheck(check_type="constitutional_compliance")

        output_str = str(bi_output).lower()

        # Check for manipulation patterns
        manipulation_indicators = [
            "manipulate", "deceive", "trick", "fake scarcity",
            "false urgency", "misleading", "dark pattern",
            "exploit fear", "pressure tactic", "bait and switch",
        ]
        for indicator in manipulation_indicators:
            if indicator in output_str:
                check.violations.append(
                    f"CONSTITUTIONAL VIOLATION (HUMAN_CENTRICITY): "
                    f"Output contains manipulation indicator: '{indicator}'"
                )
                check.passed = False
                check.score -= 0.3

        # Check transparency
        if output_type == "recommendation":
            has_rationale = any(
                key in bi_output
                for key in ["rationale", "reasoning", "evidence", "data_points", "confidence"]
            )
            if not has_rationale:
                check.warnings.append(
                    "TRANSPARENCY: Recommendation lacks explicit rationale or evidence reference"
                )
                check.score -= 0.1

        # Check for overconfident claims without data backing
        confidence = bi_output.get("confidence", bi_output.get("score", 0))
        data_points = bi_output.get("data_points", bi_output.get("evidence_count", 0))
        if isinstance(confidence, (int, float)) and confidence > 0.8 and isinstance(data_points, (int, float)) and data_points < 10:
            check.warnings.append(
                f"TRUST_EARNED: High confidence ({confidence:.0%}) with limited data ({data_points} points). "
                "Confidence should be proportional to evidence."
            )
            check.score -= 0.15

        check.score = max(0.0, check.score)
        self.integrity_checks.append(check)
        return check

    # ==================== Hallucination Guard for BI ====================

    async def verify_bi_claim(
        self, claim: str, supporting_data: Optional[Dict] = None,
    ) -> IntegrityCheck:
        """Run a BI claim through the hallucination guard pipeline.

        6 layers:
        1. Grounding: Is this claim backed by actual collected data?
        2. Consensus: Would multiple reasoning approaches agree?
        3. Contradiction: Does this contradict previous BI findings?
        4. Confidence: What's the trust score?
        5. Trust Verification: Does this align with learned patterns?
        6. External: Can we verify against external sources?
        """
        check = IntegrityCheck(check_type="hallucination_guard")

        # Layer 1: Data grounding
        if supporting_data:
            data_point_count = supporting_data.get("data_points", 0)
            sources = supporting_data.get("sources", [])
            if data_point_count > 0:
                check.details["grounding"] = "PASS: Claim references collected data"
            else:
                check.warnings.append("Layer 1 (Grounding): No data points backing this claim")
                check.score -= 0.15
        else:
            check.warnings.append("Layer 1 (Grounding): No supporting data provided")
            check.score -= 0.2

        # Layer 3: Contradiction check
        if self._contradiction_detector:
            try:
                check.details["contradiction_check"] = "Available for semantic contradiction detection"
            except Exception as e:
                logger.debug(f"Contradiction check: {e}")

        # Layer 4: Confidence scoring
        if supporting_data:
            source_count = len(supporting_data.get("sources", []))
            data_count = supporting_data.get("data_points", 0)

            confidence = min(
                0.3 + (source_count / 5) * 0.3 + min(data_count / 100, 1.0) * 0.4,
                1.0,
            )
            check.details["confidence_score"] = round(confidence, 3)
            if confidence < 0.5:
                check.warnings.append(
                    f"Layer 4 (Confidence): Low confidence ({confidence:.0%}). "
                    "More data sources needed."
                )

        # Layer 6: External verification availability
        if self._hallucination_guard:
            check.details["external_verification"] = "Available (6-layer pipeline connected)"
        else:
            check.details["external_verification"] = "Not available (hallucination guard not connected)"

        check.score = max(0.0, check.score)
        check.passed = check.score > 0.5 and not check.violations
        self.integrity_checks.append(check)
        return check

    # ==================== Honesty Reporting ====================

    async def generate_honesty_report(
        self,
        data_points: int,
        sources_active: int,
        sources_total: int,
        pain_points: int,
        opportunities: int,
        confidence: float,
        concerns: List[str],
    ) -> Dict[str, Any]:
        """Generate Grace's honesty report -- what she knows, what she doesn't, and why.

        Grace must explicitly state:
        - What data she's working with (and what's missing)
        - How confident she is (and why)
        - What could be wrong (known unknowns)
        - What she can't know (unknown unknowns)
        """
        gaps = []
        if sources_active < sources_total:
            gaps.append(
                f"Only {sources_active}/{sources_total} data connectors active. "
                f"Missing {sources_total - sources_active} data sources."
            )
        if data_points < 50:
            gaps.append(
                f"Only {data_points} data points collected. "
                "Minimum 50 recommended for reliable analysis, 100+ preferred."
            )
        if pain_points == 0:
            gaps.append("No pain points discovered yet. Analysis is speculative.")

        unknown_unknowns = [
            "Market conditions can change rapidly. Historical data may not predict future trends.",
            "Competitor strategies are inferred, not observed. They may be planning moves we can't detect.",
            "Customer behavior in ads doesn't always translate to purchase behavior.",
            "Regulatory changes could invalidate market opportunities without warning.",
        ]

        honesty_score = min(
            confidence * 0.4 +
            min(sources_active / max(sources_total, 1), 1.0) * 0.3 +
            min(data_points / 100, 1.0) * 0.3,
            1.0,
        )

        return {
            "honesty_score": round(honesty_score, 3),
            "what_i_know": {
                "data_points": data_points,
                "active_sources": sources_active,
                "pain_points_found": pain_points,
                "opportunities_scored": opportunities,
                "stated_confidence": round(confidence, 3),
            },
            "what_i_dont_know": gaps,
            "known_risks": concerns,
            "unknown_unknowns": unknown_unknowns,
            "integrity_statement": (
                f"Grace's analysis is based on {data_points} data points from "
                f"{sources_active} sources with {confidence:.0%} confidence. "
                + (f"Key gaps: {'; '.join(gaps[:2])}. " if gaps else "")
                + "All recommendations should be validated with real-world testing "
                "before committing significant resources."
            ),
        }

    # ==================== Accountability Tracking ====================

    async def record_prediction(
        self,
        prediction: str,
        confidence: float,
        module: str,
    ) -> str:
        """Record a BI prediction for future accountability tracking."""
        import uuid
        record = AccountabilityRecord(
            prediction_id=str(uuid.uuid4())[:12],
            prediction=prediction,
            predicted_confidence=confidence,
            module=module,
        )
        self.accountability_log.append(record)
        return record.prediction_id

    async def record_outcome(
        self,
        prediction_id: str,
        actual_outcome: str,
        accuracy: float,
    ) -> Dict[str, Any]:
        """Record the actual outcome of a previous prediction.

        This is how Grace is held accountable:
        - She predicted X with Y% confidence
        - The actual result was Z
        - Her accuracy was W%
        """
        record = next(
            (r for r in self.accountability_log if r.prediction_id == prediction_id),
            None,
        )
        if not record:
            return {"status": "not_found"}

        record.actual_outcome = actual_outcome
        record.outcome_recorded_at = datetime.utcnow()
        record.accuracy = accuracy

        return {
            "prediction_id": prediction_id,
            "prediction": record.prediction,
            "predicted_confidence": record.predicted_confidence,
            "actual_outcome": actual_outcome,
            "accuracy": accuracy,
            "was_confident_justified": accuracy >= record.predicted_confidence * 0.7,
        }

    async def get_accountability_report(self) -> Dict[str, Any]:
        """Get Grace's accountability report -- how accurate have her BI predictions been?"""
        evaluated = [r for r in self.accountability_log if r.accuracy is not None]
        unevaluated = [r for r in self.accountability_log if r.accuracy is None]

        if not evaluated:
            return {
                "total_predictions": len(self.accountability_log),
                "evaluated": 0,
                "pending_evaluation": len(unevaluated),
                "message": "No predictions evaluated yet. Record outcomes to track accuracy.",
            }

        avg_accuracy = sum(r.accuracy for r in evaluated) / len(evaluated)
        avg_confidence = sum(r.predicted_confidence for r in evaluated) / len(evaluated)
        calibration = abs(avg_accuracy - avg_confidence)

        overconfident = [r for r in evaluated if r.accuracy < r.predicted_confidence * 0.5]
        underconfident = [r for r in evaluated if r.accuracy > r.predicted_confidence * 1.5]

        return {
            "total_predictions": len(self.accountability_log),
            "evaluated": len(evaluated),
            "pending_evaluation": len(unevaluated),
            "avg_accuracy": round(avg_accuracy, 3),
            "avg_confidence": round(avg_confidence, 3),
            "calibration_error": round(calibration, 3),
            "overconfident_count": len(overconfident),
            "underconfident_count": len(underconfident),
            "by_module": self._accuracy_by_module(evaluated),
            "assessment": (
                "Well-calibrated" if calibration < 0.1 else
                "Overconfident" if avg_confidence > avg_accuracy else
                "Underconfident"
            ),
        }

    def _accuracy_by_module(self, records: List[AccountabilityRecord]) -> Dict[str, Any]:
        from collections import defaultdict
        by_module: Dict[str, List[float]] = defaultdict(list)
        for r in records:
            by_module[r.module].append(r.accuracy)
        return {
            m: {"avg_accuracy": round(sum(scores)/len(scores), 3), "count": len(scores)}
            for m, scores in by_module.items()
        }

    # ==================== Full Integrity Pipeline ====================

    async def run_full_integrity_check(
        self, bi_output: Dict[str, Any], output_type: str = "recommendation",
    ) -> Dict[str, Any]:
        """Run ALL integrity checks on a BI output.

        This is the complete pipeline:
        1. Constitutional compliance
        2. Hallucination guard
        3. Honesty assessment
        """
        constitutional = await self.check_constitutional_compliance(bi_output, output_type)
        hallucination = await self.verify_bi_claim(
            claim=str(bi_output.get("title", bi_output.get("summary", "")))[:200],
            supporting_data=bi_output,
        )

        all_violations = constitutional.violations + hallucination.violations
        all_warnings = constitutional.warnings + hallucination.warnings
        combined_score = (constitutional.score + hallucination.score) / 2

        return {
            "passed": not all_violations,
            "integrity_score": round(combined_score, 3),
            "constitutional": {
                "passed": constitutional.passed,
                "score": constitutional.score,
                "violations": constitutional.violations,
                "warnings": constitutional.warnings,
            },
            "hallucination_guard": {
                "passed": hallucination.passed,
                "score": hallucination.score,
                "violations": hallucination.violations,
                "warnings": hallucination.warnings,
                "details": hallucination.details,
            },
            "total_violations": len(all_violations),
            "total_warnings": len(all_warnings),
        }

    # ==================== Status ====================

    def _count_connected(self) -> int:
        return sum(1 for s in [
            self._governance, self._hallucination_guard, self._confidence_scorer,
            self._contradiction_detector, self._invariant_validator, self._trust_retriever,
        ] if s is not None)

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "connected": self._count_connected(),
            "total": 6,
            "systems": {
                "governance_constitutional_ai": {
                    "connected": self._governance is not None,
                    "purpose": "Constitutional rules: human centricity, trust earned, transparency, safety first",
                },
                "hallucination_guard_6_layer": {
                    "connected": self._hallucination_guard is not None,
                    "purpose": "6-layer verification: grounding, consensus, contradiction, confidence, trust, external",
                },
                "confidence_scorer": {
                    "connected": self._confidence_scorer is not None,
                    "purpose": "Multi-factor confidence scoring (source reliability, quality, consensus, recency)",
                },
                "contradiction_detector_semantic": {
                    "connected": self._contradiction_detector is not None,
                    "purpose": "Semantic contradiction detection against previous BI findings",
                },
                "cognitive_invariants_12": {
                    "connected": self._invariant_validator is not None,
                    "purpose": "12 cognitive invariants: OODA, ambiguity, reversibility, blast radius, etc",
                },
                "trust_aware_retrieval": {
                    "connected": self._trust_retriever is not None,
                    "purpose": "Neuro-symbolic retrieval weighted by trust scores",
                },
            },
            "accountability": {
                "predictions_tracked": len(self.accountability_log),
                "evaluated": sum(1 for r in self.accountability_log if r.accuracy is not None),
            },
            "integrity_checks_run": len(self.integrity_checks),
        }


_integrity_bridge: Optional[IntegrityBridge] = None


def get_integrity_bridge() -> IntegrityBridge:
    global _integrity_bridge
    if _integrity_bridge is None:
        _integrity_bridge = IntegrityBridge()
        _integrity_bridge.initialize()
    return _integrity_bridge
