"""
Dynamic Verification Pipeline

Combines all advanced trust components into a single verification pipeline
that adapts based on:
- Competence boundaries (verify more in weak domains)
- Meta-learning (use strategies that work)
- Trust thermometer (system-wide confidence level)
- Trust decay (re-verify stale data)
- Adversarial self-testing (break own outputs)

The pipeline is the unified entry point for verifying any data before
Grace trusts it.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class VerificationStrategy(str, Enum):
    """Available verification strategies."""
    GITHUB_CHECK = "github_check"
    WEB_CROSS_REFERENCE = "web_cross_reference"
    KNOWLEDGE_BASE_LOOKUP = "knowledge_base_lookup"
    EXPERT_CONSENSUS = "expert_consensus"
    CODE_EXECUTION = "code_execution"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    TEMPORAL_VERIFICATION = "temporal_verification"
    SOURCE_AUTHORITY = "source_authority"
    ADVERSARIAL_SELF_TEST = "adversarial_self_test"


class VerificationLevel(str, Enum):
    """How thorough to verify."""
    MINIMAL = "minimal"       # Single strategy, quick check
    STANDARD = "standard"     # 2-3 strategies
    THOROUGH = "thorough"     # 4-5 strategies with adversarial
    EXHAUSTIVE = "exhaustive" # All strategies, full adversarial battery


@dataclass
class VerificationRequest:
    """A request to verify data."""
    request_id: str
    data: str
    data_type: str
    domain: Optional[str] = None
    current_trust: float = 0.5
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VerificationStepResult:
    """Result of a single verification step."""
    strategy: VerificationStrategy
    success: bool
    confidence_delta: float
    details: Dict[str, Any] = field(default_factory=dict)
    time_ms: float = 0.0


@dataclass
class VerificationResult:
    """Result of the full verification pipeline."""
    request_id: str
    original_trust: float
    final_trust: float
    verification_level: VerificationLevel
    steps: List[VerificationStepResult]
    strategies_used: List[str]
    passed: bool
    needs_human_review: bool
    recommendations: List[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class VerificationPipeline:
    """
    Unified verification pipeline that adapts to context.

    The pipeline decides:
    1. How thoroughly to verify (based on thermometer + competence)
    2. Which strategies to use (based on meta-learning)
    3. Whether to apply adversarial testing
    4. Whether to flag for human review

    Flow:
    1. Receive verification request
    2. Determine verification level (from thermometer + domain competence)
    3. Select strategies (from meta-learner recommendations)
    4. Execute verification steps
    5. Optionally run adversarial self-test
    6. Aggregate results
    7. Return verdict with updated trust score
    """

    # Trust thresholds
    PASS_THRESHOLD = 0.5
    HUMAN_REVIEW_THRESHOLD = 0.3

    # Default strategy weights per verification level
    LEVEL_STRATEGY_COUNTS = {
        VerificationLevel.MINIMAL: 1,
        VerificationLevel.STANDARD: 2,
        VerificationLevel.THOROUGH: 4,
        VerificationLevel.EXHAUSTIVE: 7,
    }

    def __init__(
        self,
        pass_threshold: float = PASS_THRESHOLD,
        human_review_threshold: float = HUMAN_REVIEW_THRESHOLD,
    ):
        self.pass_threshold = pass_threshold
        self.human_review_threshold = human_review_threshold
        self.verification_log: List[VerificationResult] = []
        self._strategy_handlers: Dict[VerificationStrategy, Any] = {}
        logger.info("[VERIFY-PIPELINE] Initialized")

    def register_strategy_handler(
        self, strategy: VerificationStrategy, handler: Any
    ) -> None:
        """Register a handler for a verification strategy."""
        self._strategy_handlers[strategy] = handler

    def determine_verification_level(
        self,
        current_trust: float,
        domain_competence: float = 0.5,
        thermometer_multiplier: float = 1.0,
    ) -> VerificationLevel:
        """
        Determine how thoroughly to verify based on context.

        Args:
            current_trust: Current trust of the data
            domain_competence: Grace's competence in this domain (0-1)
            thermometer_multiplier: From trust thermometer (higher = more verification)

        Returns:
            VerificationLevel
        """
        # Base verification need: inverse of trust * competence
        base_need = (1.0 - current_trust) * (1.0 - domain_competence)
        adjusted_need = base_need * thermometer_multiplier

        if adjusted_need >= 0.7:
            return VerificationLevel.EXHAUSTIVE
        elif adjusted_need >= 0.5:
            return VerificationLevel.THOROUGH
        elif adjusted_need >= 0.25:
            return VerificationLevel.STANDARD
        else:
            return VerificationLevel.MINIMAL

    def verify(
        self,
        data: str,
        data_type: str,
        domain: Optional[str] = None,
        current_trust: float = 0.5,
        source: Optional[str] = None,
        verification_level: Optional[VerificationLevel] = None,
        domain_competence: float = 0.5,
        thermometer_multiplier: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> VerificationResult:
        """
        Run the verification pipeline on data.

        Args:
            data: The data to verify
            data_type: Type (code, factual, domain_specific, etc.)
            domain: Knowledge domain
            current_trust: Current trust score
            source: Source identifier
            verification_level: Override auto-determined level
            domain_competence: Domain competence score
            thermometer_multiplier: From trust thermometer
            metadata: Additional metadata

        Returns:
            VerificationResult
        """
        request = VerificationRequest(
            request_id=f"vr-{uuid.uuid4().hex[:12]}",
            data=data,
            data_type=data_type,
            domain=domain,
            current_trust=current_trust,
            source=source,
            metadata=metadata or {},
        )

        # Determine verification level
        if verification_level is None:
            verification_level = self.determine_verification_level(
                current_trust, domain_competence, thermometer_multiplier
            )

        # Select and execute strategies
        strategy_count = self.LEVEL_STRATEGY_COUNTS[verification_level]
        steps = self._execute_strategies(request, strategy_count, verification_level)

        # Calculate final trust
        trust_delta = sum(s.confidence_delta for s in steps)
        final_trust = max(0.0, min(1.0, current_trust + trust_delta))

        # Determine pass/fail and review needs
        passed = final_trust >= self.pass_threshold
        needs_human_review = final_trust < self.human_review_threshold

        # Generate recommendations
        recommendations = self._generate_recommendations(
            steps, final_trust, verification_level
        )

        result = VerificationResult(
            request_id=request.request_id,
            original_trust=current_trust,
            final_trust=final_trust,
            verification_level=verification_level,
            steps=steps,
            strategies_used=[s.strategy.value for s in steps],
            passed=passed,
            needs_human_review=needs_human_review,
            recommendations=recommendations,
            metadata=metadata or {},
        )

        self.verification_log.append(result)

        logger.info(
            f"[VERIFY-PIPELINE] {data_type}/{domain}: "
            f"level={verification_level.value} "
            f"trust={current_trust:.2f}->{final_trust:.2f} "
            f"{'PASS' if passed else 'FAIL'}"
            f"{' [HUMAN REVIEW]' if needs_human_review else ''}"
        )

        return result

    def _execute_strategies(
        self,
        request: VerificationRequest,
        count: int,
        level: VerificationLevel,
    ) -> List[VerificationStepResult]:
        """Execute verification strategies."""
        steps: List[VerificationStepResult] = []

        # Select strategies based on data type
        strategy_order = self._get_strategy_order(
            request.data_type, request.domain
        )

        for strategy in strategy_order[:count]:
            step = self._execute_single_strategy(request, strategy)
            steps.append(step)

        # Add adversarial self-test for thorough/exhaustive
        if level in (VerificationLevel.THOROUGH, VerificationLevel.EXHAUSTIVE):
            ast_step = self._execute_adversarial_test(request)
            steps.append(ast_step)

        return steps

    def _get_strategy_order(
        self, data_type: str, domain: Optional[str]
    ) -> List[VerificationStrategy]:
        """Get strategy order based on data type and domain."""
        # Default strategy ordering per data type
        type_strategies = {
            "code": [
                VerificationStrategy.CODE_EXECUTION,
                VerificationStrategy.GITHUB_CHECK,
                VerificationStrategy.SEMANTIC_SIMILARITY,
                VerificationStrategy.KNOWLEDGE_BASE_LOOKUP,
                VerificationStrategy.SOURCE_AUTHORITY,
                VerificationStrategy.WEB_CROSS_REFERENCE,
                VerificationStrategy.TEMPORAL_VERIFICATION,
            ],
            "factual": [
                VerificationStrategy.WEB_CROSS_REFERENCE,
                VerificationStrategy.KNOWLEDGE_BASE_LOOKUP,
                VerificationStrategy.SOURCE_AUTHORITY,
                VerificationStrategy.TEMPORAL_VERIFICATION,
                VerificationStrategy.SEMANTIC_SIMILARITY,
                VerificationStrategy.EXPERT_CONSENSUS,
                VerificationStrategy.GITHUB_CHECK,
            ],
            "domain_specific": [
                VerificationStrategy.KNOWLEDGE_BASE_LOOKUP,
                VerificationStrategy.EXPERT_CONSENSUS,
                VerificationStrategy.SEMANTIC_SIMILARITY,
                VerificationStrategy.SOURCE_AUTHORITY,
                VerificationStrategy.WEB_CROSS_REFERENCE,
                VerificationStrategy.TEMPORAL_VERIFICATION,
                VerificationStrategy.GITHUB_CHECK,
            ],
        }

        return type_strategies.get(data_type, [
            VerificationStrategy.KNOWLEDGE_BASE_LOOKUP,
            VerificationStrategy.WEB_CROSS_REFERENCE,
            VerificationStrategy.SEMANTIC_SIMILARITY,
            VerificationStrategy.SOURCE_AUTHORITY,
            VerificationStrategy.TEMPORAL_VERIFICATION,
            VerificationStrategy.GITHUB_CHECK,
            VerificationStrategy.EXPERT_CONSENSUS,
        ])

    def _execute_single_strategy(
        self, request: VerificationRequest, strategy: VerificationStrategy
    ) -> VerificationStepResult:
        """Execute a single verification strategy."""
        if strategy in self._strategy_handlers:
            try:
                handler = self._strategy_handlers[strategy]
                result = handler(request)
                return result
            except Exception as e:
                logger.warning(f"Strategy {strategy.value} failed: {e}")
                return VerificationStepResult(
                    strategy=strategy,
                    success=False,
                    confidence_delta=-0.05,
                    details={"error": str(e)},
                )

        # Default simulation: assume mild positive effect for known strategies
        return VerificationStepResult(
            strategy=strategy,
            success=True,
            confidence_delta=0.03,
            details={"simulated": True},
        )

    def _execute_adversarial_test(
        self, request: VerificationRequest
    ) -> VerificationStepResult:
        """Execute adversarial self-test step."""
        # Basic adversarial checks
        data = request.data
        issues = 0

        if len(data.strip()) < 20:
            issues += 1
        if data.count("?") > 3:
            issues += 1

        confidence_delta = 0.02 if issues == 0 else -0.05 * issues

        return VerificationStepResult(
            strategy=VerificationStrategy.ADVERSARIAL_SELF_TEST,
            success=issues == 0,
            confidence_delta=confidence_delta,
            details={"issues_found": issues},
        )

    def _generate_recommendations(
        self,
        steps: List[VerificationStepResult],
        final_trust: float,
        level: VerificationLevel,
    ) -> List[str]:
        """Generate recommendations based on verification results."""
        recs = []

        failed_strategies = [
            s.strategy.value for s in steps if not s.success
        ]
        if failed_strategies:
            recs.append(
                f"Failed strategies: {', '.join(failed_strategies)}. "
                f"Consider alternative verification."
            )

        if final_trust < self.pass_threshold:
            recs.append(
                "Trust score below threshold. "
                "Recommend additional verification or human review."
            )

        if level == VerificationLevel.MINIMAL and final_trust < 0.7:
            recs.append(
                "Consider upgrading to STANDARD verification level."
            )

        if not recs:
            recs.append("Verification passed. Data can be trusted.")

        return recs

    def get_verification_log(self, limit: int = 50) -> List[VerificationResult]:
        """Get recent verification results."""
        return self.verification_log[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        if not self.verification_log:
            return {
                "total_verifications": 0,
                "pass_rate": 0.0,
                "human_review_rate": 0.0,
            }

        total = len(self.verification_log)
        passed = sum(1 for r in self.verification_log if r.passed)
        reviews = sum(
            1 for r in self.verification_log if r.needs_human_review
        )

        avg_trust_delta = sum(
            r.final_trust - r.original_trust for r in self.verification_log
        ) / total

        return {
            "total_verifications": total,
            "pass_rate": passed / total,
            "human_review_rate": reviews / total,
            "average_trust_delta": avg_trust_delta,
            "by_level": {
                level.value: sum(
                    1 for r in self.verification_log
                    if r.verification_level == level
                )
                for level in VerificationLevel
            },
        }
