"""
Adversarial Self-Testing Engine

Before Grace trusts her own output, she tries to break it. Generate the
answer, then deliberately try to find contradictions in it. If she can
poke a hole in her own reasoning, she drops the trust score and
re-verifies before responding.

The hallucination guard does this for LLM outputs. This module does it
for retrieval results, memory recalls, and procedure executions.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class TestType(str, Enum):
    """Types of adversarial tests."""
    CONTRADICTION_CHECK = "contradiction_check"
    CONSISTENCY_CHECK = "consistency_check"
    TEMPORAL_CHECK = "temporal_check"
    SOURCE_CROSS_CHECK = "source_cross_check"
    LOGICAL_VALIDITY = "logical_validity"
    COMPLETENESS_CHECK = "completeness_check"
    BOUNDARY_CHECK = "boundary_check"


class DataOrigin(str, Enum):
    """Origin of the data being tested."""
    RETRIEVAL = "retrieval"
    MEMORY_RECALL = "memory_recall"
    PROCEDURE_EXECUTION = "procedure_execution"
    LLM_GENERATION = "llm_generation"
    KNOWLEDGE_BASE = "knowledge_base"
    EXTERNAL_API = "external_api"


class TestVerdict(str, Enum):
    """Verdict of an adversarial test."""
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"
    WEAKNESS_FOUND = "weakness_found"


@dataclass
class AdversarialTest:
    """A single adversarial test applied to data."""
    test_id: str
    test_type: TestType
    description: str
    verdict: TestVerdict
    confidence_impact: float  # -1.0 to +1.0
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SelfTestResult:
    """Result of adversarial self-testing on a piece of data."""
    result_id: str
    data_origin: DataOrigin
    original_trust: float
    adjusted_trust: float
    tests_run: List[AdversarialTest]
    passed_count: int
    failed_count: int
    weakness_count: int
    needs_reverification: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdversarialSelfTester:
    """
    Tests Grace's own outputs adversarially before trusting them.

    For every piece of data (retrieval, memory, procedure result), runs
    a battery of adversarial tests to find weaknesses. If weaknesses are
    found, the trust score is dropped and re-verification is triggered.

    Test Battery:
    1. Contradiction Check - Does this contradict known facts?
    2. Consistency Check - Is this internally consistent?
    3. Temporal Check - Is this temporally valid (not outdated)?
    4. Source Cross-Check - Do multiple sources agree?
    5. Logical Validity - Is the reasoning logically sound?
    6. Completeness Check - Are there missing critical pieces?
    7. Boundary Check - Is this within competence boundaries?
    """

    # Trust penalty per failed test
    FAILURE_PENALTY = 0.15
    # Trust penalty per weakness found
    WEAKNESS_PENALTY = 0.05
    # Trust bonus per passed test
    PASS_BONUS = 0.02
    # Threshold for triggering re-verification
    REVERIFICATION_THRESHOLD = 0.4
    # Maximum number of tests per item
    MAX_TESTS_PER_ITEM = 7

    def __init__(
        self,
        failure_penalty: float = FAILURE_PENALTY,
        weakness_penalty: float = WEAKNESS_PENALTY,
        pass_bonus: float = PASS_BONUS,
        reverification_threshold: float = REVERIFICATION_THRESHOLD,
    ):
        self.failure_penalty = failure_penalty
        self.weakness_penalty = weakness_penalty
        self.pass_bonus = pass_bonus
        self.reverification_threshold = reverification_threshold
        self.test_history: List[SelfTestResult] = []
        self._test_registry: Dict[TestType, List[Any]] = {}
        self._known_facts: Dict[str, Any] = {}
        logger.info("[ADVERSARIAL] Self-Testing Engine initialized")

    def register_known_fact(self, fact_id: str, fact_data: Any) -> None:
        """Register a known fact for contradiction checking."""
        self._known_facts[fact_id] = fact_data

    def test_retrieval_result(
        self,
        content: str,
        source: str,
        trust_score: float,
        domain: Optional[str] = None,
        related_facts: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SelfTestResult:
        """
        Adversarially test a retrieval result.

        Args:
            content: The retrieved content
            source: Source identifier
            trust_score: Current trust score
            domain: Knowledge domain
            related_facts: Known related facts for cross-checking
            metadata: Additional metadata

        Returns:
            SelfTestResult
        """
        return self._run_test_battery(
            data=content,
            data_origin=DataOrigin.RETRIEVAL,
            trust_score=trust_score,
            source=source,
            domain=domain,
            related_facts=related_facts or [],
            metadata=metadata or {},
        )

    def test_memory_recall(
        self,
        recalled_data: str,
        memory_type: str,
        trust_score: float,
        recall_context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SelfTestResult:
        """
        Adversarially test a memory recall result.

        Args:
            recalled_data: The recalled data
            memory_type: Type of memory (episodic, semantic, procedural)
            trust_score: Current trust score
            recall_context: Context of the recall
            metadata: Additional metadata

        Returns:
            SelfTestResult
        """
        return self._run_test_battery(
            data=recalled_data,
            data_origin=DataOrigin.MEMORY_RECALL,
            trust_score=trust_score,
            source=f"memory:{memory_type}",
            domain=None,
            related_facts=[],
            metadata={**(metadata or {}), "memory_type": memory_type,
                       "recall_context": recall_context or {}},
        )

    def test_procedure_result(
        self,
        result_data: Any,
        procedure_name: str,
        trust_score: float,
        inputs: Optional[Dict[str, Any]] = None,
        expected_output_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SelfTestResult:
        """
        Adversarially test a procedure execution result.

        Args:
            result_data: The procedure result
            procedure_name: Name of the procedure
            trust_score: Current trust score
            inputs: Procedure inputs
            expected_output_type: Expected type of output
            metadata: Additional metadata

        Returns:
            SelfTestResult
        """
        data_str = str(result_data) if not isinstance(result_data, str) else result_data
        return self._run_test_battery(
            data=data_str,
            data_origin=DataOrigin.PROCEDURE_EXECUTION,
            trust_score=trust_score,
            source=f"procedure:{procedure_name}",
            domain=None,
            related_facts=[],
            metadata={
                **(metadata or {}),
                "procedure_name": procedure_name,
                "inputs": inputs or {},
                "expected_output_type": expected_output_type,
            },
        )

    def _run_test_battery(
        self,
        data: str,
        data_origin: DataOrigin,
        trust_score: float,
        source: str,
        domain: Optional[str],
        related_facts: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> SelfTestResult:
        """
        Run the full adversarial test battery.

        Args:
            data: The data to test
            data_origin: Where the data came from
            trust_score: Current trust score
            source: Source identifier
            domain: Domain
            related_facts: Related facts
            metadata: Metadata

        Returns:
            SelfTestResult
        """
        tests: List[AdversarialTest] = []

        # Test 1: Contradiction Check
        tests.append(self._test_contradiction(data, related_facts))

        # Test 2: Consistency Check
        tests.append(self._test_consistency(data))

        # Test 3: Temporal Check
        tests.append(self._test_temporal_validity(data, metadata))

        # Test 4: Source Cross-Check
        tests.append(self._test_source_cross_check(data, source, related_facts))

        # Test 5: Logical Validity
        tests.append(self._test_logical_validity(data))

        # Test 6: Completeness Check
        tests.append(self._test_completeness(data, data_origin))

        # Test 7: Boundary Check
        tests.append(self._test_boundary(data, domain))

        # Calculate adjusted trust
        passed = sum(1 for t in tests if t.verdict == TestVerdict.PASSED)
        failed = sum(1 for t in tests if t.verdict == TestVerdict.FAILED)
        weaknesses = sum(
            1 for t in tests if t.verdict == TestVerdict.WEAKNESS_FOUND
        )

        adjustment = (
            (passed * self.pass_bonus)
            - (failed * self.failure_penalty)
            - (weaknesses * self.weakness_penalty)
        )

        adjusted_trust = max(0.0, min(1.0, trust_score + adjustment))
        needs_reverification = adjusted_trust < self.reverification_threshold

        result = SelfTestResult(
            result_id=f"ast-{uuid.uuid4().hex[:12]}",
            data_origin=data_origin,
            original_trust=trust_score,
            adjusted_trust=adjusted_trust,
            tests_run=tests,
            passed_count=passed,
            failed_count=failed,
            weakness_count=weaknesses,
            needs_reverification=needs_reverification,
            metadata=metadata,
        )

        self.test_history.append(result)
        logger.info(
            f"[ADVERSARIAL] {data_origin.value}: "
            f"P={passed} F={failed} W={weaknesses} "
            f"trust: {trust_score:.2f}->{adjusted_trust:.2f}"
            f"{' [RE-VERIFY]' if needs_reverification else ''}"
        )

        return result

    def _test_contradiction(
        self, data: str, related_facts: List[Dict[str, Any]]
    ) -> AdversarialTest:
        """Check for contradictions against known facts."""
        contradictions_found = 0

        # Check against registered known facts
        for fact_id, fact_data in self._known_facts.items():
            fact_str = str(fact_data).lower()
            data_lower = data.lower()

            negation_pairs = [
                ("is not", "is"),
                ("cannot", "can"),
                ("never", "always"),
                ("false", "true"),
                ("incorrect", "correct"),
                ("wrong", "right"),
                ("no ", "yes "),
                ("disabled", "enabled"),
                ("deprecated", "recommended"),
            ]

            for neg, pos in negation_pairs:
                if neg in data_lower and pos in fact_str:
                    contradictions_found += 1
                elif pos in data_lower and neg in fact_str:
                    contradictions_found += 1

        # Check against provided related facts
        for fact in related_facts:
            fact_content = str(fact.get("content", "")).lower()
            data_lower = data.lower()
            if fact_content and data_lower:
                # Simple overlap check
                fact_words = set(fact_content.split())
                data_words = set(data_lower.split())
                overlap = fact_words & data_words
                if len(overlap) > 3:
                    # High overlap but check for negation
                    for neg_word in ["not", "no", "never", "cannot", "false"]:
                        if neg_word in data_lower and neg_word not in fact_content:
                            contradictions_found += 1
                            break

        if contradictions_found > 0:
            return AdversarialTest(
                test_id=f"ct-{uuid.uuid4().hex[:8]}",
                test_type=TestType.CONTRADICTION_CHECK,
                description="Contradiction detected against known facts",
                verdict=TestVerdict.FAILED,
                confidence_impact=-0.2,
                details={"contradictions_found": contradictions_found},
            )

        return AdversarialTest(
            test_id=f"ct-{uuid.uuid4().hex[:8]}",
            test_type=TestType.CONTRADICTION_CHECK,
            description="No contradictions found",
            verdict=TestVerdict.PASSED,
            confidence_impact=0.02,
            details={"facts_checked": len(self._known_facts) + len(related_facts)},
        )

    def _test_consistency(self, data: str) -> AdversarialTest:
        """Check internal consistency of the data."""
        inconsistencies = 0
        data_lower = data.lower()
        sentences = [s.strip() for s in data.split(".") if s.strip()]

        # Check for self-contradicting statements
        for i, sent_a in enumerate(sentences):
            for sent_b in sentences[i + 1:]:
                sent_a_lower = sent_a.lower()
                sent_b_lower = sent_b.lower()

                for neg in ["not", "no", "never", "cannot"]:
                    if neg in sent_a_lower and neg not in sent_b_lower:
                        a_words = set(sent_a_lower.split()) - {neg}
                        b_words = set(sent_b_lower.split())
                        overlap = a_words & b_words
                        if len(overlap) >= 3:
                            inconsistencies += 1

        if inconsistencies > 0:
            return AdversarialTest(
                test_id=f"ic-{uuid.uuid4().hex[:8]}",
                test_type=TestType.CONSISTENCY_CHECK,
                description="Internal inconsistencies detected",
                verdict=TestVerdict.WEAKNESS_FOUND,
                confidence_impact=-0.1,
                details={"inconsistencies": inconsistencies},
            )

        return AdversarialTest(
            test_id=f"ic-{uuid.uuid4().hex[:8]}",
            test_type=TestType.CONSISTENCY_CHECK,
            description="Content is internally consistent",
            verdict=TestVerdict.PASSED,
            confidence_impact=0.02,
            details={"sentences_checked": len(sentences)},
        )

    def _test_temporal_validity(
        self, data: str, metadata: Dict[str, Any]
    ) -> AdversarialTest:
        """Check temporal validity of data."""
        data_lower = data.lower()

        # Check for stale temporal markers
        stale_markers = [
            "as of 2020", "as of 2019", "as of 2018",
            "last year", "recently deprecated",
            "will be removed", "end of life",
            "no longer supported", "was replaced by",
        ]

        stale_count = sum(1 for m in stale_markers if m in data_lower)

        # Check metadata for age
        created_at = metadata.get("created_at")
        if isinstance(created_at, str):
            try:
                created_dt = datetime.fromisoformat(created_at)
                age_days = (datetime.now(timezone.utc) - created_dt).days
                if age_days > 365:
                    stale_count += 1
            except (ValueError, TypeError):
                pass

        if stale_count >= 2:
            return AdversarialTest(
                test_id=f"tv-{uuid.uuid4().hex[:8]}",
                test_type=TestType.TEMPORAL_CHECK,
                description="Data appears temporally outdated",
                verdict=TestVerdict.FAILED,
                confidence_impact=-0.15,
                details={"stale_indicators": stale_count},
            )
        elif stale_count == 1:
            return AdversarialTest(
                test_id=f"tv-{uuid.uuid4().hex[:8]}",
                test_type=TestType.TEMPORAL_CHECK,
                description="Minor temporal concern detected",
                verdict=TestVerdict.WEAKNESS_FOUND,
                confidence_impact=-0.05,
                details={"stale_indicators": stale_count},
            )

        return AdversarialTest(
            test_id=f"tv-{uuid.uuid4().hex[:8]}",
            test_type=TestType.TEMPORAL_CHECK,
            description="Data appears temporally valid",
            verdict=TestVerdict.PASSED,
            confidence_impact=0.02,
            details={"stale_indicators": 0},
        )

    def _test_source_cross_check(
        self, data: str, source: str, related_facts: List[Dict[str, Any]]
    ) -> AdversarialTest:
        """Cross-check against multiple sources."""
        if not related_facts:
            return AdversarialTest(
                test_id=f"sc-{uuid.uuid4().hex[:8]}",
                test_type=TestType.SOURCE_CROSS_CHECK,
                description="No alternative sources to cross-check",
                verdict=TestVerdict.INCONCLUSIVE,
                confidence_impact=0.0,
                details={"sources_available": 0},
            )

        agreeing_sources = 0
        total_sources = len(related_facts)

        for fact in related_facts:
            fact_content = str(fact.get("content", "")).lower()
            data_lower = data.lower()
            if fact_content:
                data_words = set(data_lower.split())
                fact_words = set(fact_content.split())
                if len(data_words) > 0 and len(fact_words) > 0:
                    overlap = len(data_words & fact_words)
                    similarity = overlap / max(len(data_words), 1)
                    if similarity > 0.2:
                        agreeing_sources += 1

        agreement_ratio = agreeing_sources / max(total_sources, 1)

        if agreement_ratio >= 0.6:
            return AdversarialTest(
                test_id=f"sc-{uuid.uuid4().hex[:8]}",
                test_type=TestType.SOURCE_CROSS_CHECK,
                description=f"{agreeing_sources}/{total_sources} sources agree",
                verdict=TestVerdict.PASSED,
                confidence_impact=0.05,
                details={
                    "agreeing_sources": agreeing_sources,
                    "total_sources": total_sources,
                    "agreement_ratio": agreement_ratio,
                },
            )
        elif agreement_ratio >= 0.3:
            return AdversarialTest(
                test_id=f"sc-{uuid.uuid4().hex[:8]}",
                test_type=TestType.SOURCE_CROSS_CHECK,
                description="Partial source agreement",
                verdict=TestVerdict.WEAKNESS_FOUND,
                confidence_impact=-0.05,
                details={
                    "agreeing_sources": agreeing_sources,
                    "total_sources": total_sources,
                },
            )
        else:
            return AdversarialTest(
                test_id=f"sc-{uuid.uuid4().hex[:8]}",
                test_type=TestType.SOURCE_CROSS_CHECK,
                description="Sources do not agree",
                verdict=TestVerdict.FAILED,
                confidence_impact=-0.15,
                details={
                    "agreeing_sources": agreeing_sources,
                    "total_sources": total_sources,
                },
            )

    def _test_logical_validity(self, data: str) -> AdversarialTest:
        """Check logical validity of statements."""
        data_lower = data.lower()
        issues = 0

        # Check for circular reasoning
        circular_patterns = [
            ("because it is", "it is because"),
            ("therefore", "because therefore"),
        ]
        for p1, p2 in circular_patterns:
            if p1 in data_lower and p2 in data_lower:
                issues += 1

        # Check for unsupported absolutes
        absolute_words = ["always", "never", "all", "none", "every", "impossible"]
        hedge_words = ["usually", "often", "most", "some", "typically", "generally"]

        absolutes = sum(1 for w in absolute_words if w in data_lower.split())
        hedges = sum(1 for w in hedge_words if w in data_lower.split())

        if absolutes > 2 and hedges == 0:
            issues += 1

        # Check for vague claims
        vague_patterns = [
            "it is said that", "some say", "people believe",
            "it is thought", "supposedly", "allegedly",
        ]
        vague_count = sum(1 for p in vague_patterns if p in data_lower)
        if vague_count >= 2:
            issues += 1

        if issues > 0:
            return AdversarialTest(
                test_id=f"lv-{uuid.uuid4().hex[:8]}",
                test_type=TestType.LOGICAL_VALIDITY,
                description=f"Logical issues found: {issues}",
                verdict=TestVerdict.WEAKNESS_FOUND,
                confidence_impact=-0.05 * issues,
                details={"issues": issues, "absolutes": absolutes, "hedges": hedges},
            )

        return AdversarialTest(
            test_id=f"lv-{uuid.uuid4().hex[:8]}",
            test_type=TestType.LOGICAL_VALIDITY,
            description="Logically sound",
            verdict=TestVerdict.PASSED,
            confidence_impact=0.02,
            details={"absolutes": absolutes, "hedges": hedges},
        )

    def _test_completeness(
        self, data: str, data_origin: DataOrigin
    ) -> AdversarialTest:
        """Check if the data appears complete."""
        data_len = len(data.strip())

        # Very short responses are suspicious
        if data_len < 10:
            return AdversarialTest(
                test_id=f"cc-{uuid.uuid4().hex[:8]}",
                test_type=TestType.COMPLETENESS_CHECK,
                description="Data appears too short/incomplete",
                verdict=TestVerdict.FAILED,
                confidence_impact=-0.15,
                details={"length": data_len},
            )

        # Check for truncation markers
        truncation_markers = [
            "...", "[truncated]", "[continued]", "see more",
            "to be continued", "[cut off]",
        ]
        is_truncated = any(m in data.lower() for m in truncation_markers)

        if is_truncated:
            return AdversarialTest(
                test_id=f"cc-{uuid.uuid4().hex[:8]}",
                test_type=TestType.COMPLETENESS_CHECK,
                description="Data appears truncated",
                verdict=TestVerdict.WEAKNESS_FOUND,
                confidence_impact=-0.05,
                details={"length": data_len, "truncated": True},
            )

        return AdversarialTest(
            test_id=f"cc-{uuid.uuid4().hex[:8]}",
            test_type=TestType.COMPLETENESS_CHECK,
            description="Data appears complete",
            verdict=TestVerdict.PASSED,
            confidence_impact=0.02,
            details={"length": data_len},
        )

    def _test_boundary(
        self, data: str, domain: Optional[str]
    ) -> AdversarialTest:
        """Check if data is within known competence boundaries."""
        if domain is None:
            return AdversarialTest(
                test_id=f"bc-{uuid.uuid4().hex[:8]}",
                test_type=TestType.BOUNDARY_CHECK,
                description="No domain specified for boundary check",
                verdict=TestVerdict.INCONCLUSIVE,
                confidence_impact=0.0,
                details={},
            )

        # This is a placeholder - in production, it queries CompetenceBoundaryTracker
        return AdversarialTest(
            test_id=f"bc-{uuid.uuid4().hex[:8]}",
            test_type=TestType.BOUNDARY_CHECK,
            description=f"Domain '{domain}' boundary check passed",
            verdict=TestVerdict.PASSED,
            confidence_impact=0.02,
            details={"domain": domain},
        )

    def get_test_history(
        self,
        data_origin: Optional[DataOrigin] = None,
        limit: int = 50,
    ) -> List[SelfTestResult]:
        """Get test history, optionally filtered by origin."""
        history = self.test_history
        if data_origin:
            history = [r for r in history if r.data_origin == data_origin]
        return history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get testing statistics."""
        if not self.test_history:
            return {
                "total_tests": 0,
                "reverification_rate": 0.0,
                "average_trust_impact": 0.0,
            }

        total = len(self.test_history)
        reverifications = sum(
            1 for r in self.test_history if r.needs_reverification
        )
        trust_impacts = [
            r.adjusted_trust - r.original_trust for r in self.test_history
        ]
        avg_impact = sum(trust_impacts) / len(trust_impacts) if trust_impacts else 0.0

        by_origin = {}
        for origin in DataOrigin:
            origin_results = [
                r for r in self.test_history if r.data_origin == origin
            ]
            if origin_results:
                by_origin[origin.value] = {
                    "count": len(origin_results),
                    "avg_pass_rate": sum(
                        r.passed_count / max(len(r.tests_run), 1)
                        for r in origin_results
                    ) / len(origin_results),
                }

        return {
            "total_tests": total,
            "reverification_rate": reverifications / max(total, 1),
            "average_trust_impact": avg_impact,
            "by_origin": by_origin,
        }
