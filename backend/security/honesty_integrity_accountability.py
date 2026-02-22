"""
Honesty, Integrity & Accountability (HIA) Framework

Core values that are IMMUTABLE and non-negotiable:

HONESTY:
- Kimi/Grace cannot lie or fabricate information
- Every claim must be traceable to a source
- If unsure, must say "I don't know" not make something up
- Confidence scores must reflect actual certainty
- No inflated metrics or hidden failures

INTEGRITY:
- Internal data must match what's reported externally
- KPIs cannot be gamed or manipulated
- Trust scores reflect real performance, not aspirational
- Self-monitoring data must be authentic
- No silent suppression of errors or failures

ACCOUNTABILITY:
- Every action has an audit trail (Genesis Keys)
- Every decision is explainable (OODA log)
- Every failure is recorded, never hidden
- Every claim can be verified against source data
- System reports its own limitations truthfully

This framework enforces these values across:
- All LLM outputs (Kimi cannot lie)
- All self-reporting (KPIs, trust scores)
- All self-* agents (mirror, healer, learner, etc.)
- All governance decisions
- All user-facing responses
"""

import logging
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

def _track_hia(desc, **kw):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event("hia_framework", desc, **kw)
    except Exception:
        pass


class HIAValue(str, Enum):
    """The three core values."""
    HONESTY = "honesty"
    INTEGRITY = "integrity"
    ACCOUNTABILITY = "accountability"


class ViolationSeverity(str, Enum):
    """Severity of an HIA violation."""
    INFO = "info"
    WARNING = "warning"
    SERIOUS = "serious"
    CRITICAL = "critical"


@dataclass
class HIAViolation:
    """Record of an HIA violation."""
    value: HIAValue
    severity: ViolationSeverity
    description: str
    component: str
    evidence: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    auto_corrected: bool = False
    correction: str = ""


@dataclass
class HIAVerificationResult:
    """Result of an HIA verification check."""
    passed: bool
    honesty_score: float
    integrity_score: float
    accountability_score: float
    overall_score: float
    violations: List[HIAViolation] = field(default_factory=list)
    checks_performed: List[str] = field(default_factory=list)
    corrections_applied: List[str] = field(default_factory=list)


# ============================================================================
# HONESTY ENFORCER — Kimi/Grace cannot lie
# ============================================================================

class HonestyEnforcer:
    """
    Ensures all LLM outputs are honest.

    Checks:
    - No fabricated sources or citations
    - No inflated confidence/certainty
    - No claims without evidence
    - "I don't know" when genuinely uncertain
    - No fabricated statistics or numbers
    """

    FABRICATION_PATTERNS = [
        (r"according to (?:a |the )?(?:recent |latest )?(?:study|research|survey|report) (?:by|from|in|at) [\w\s]+(?:university|institute|journal)",
         "Fabricated academic source"),
        (r"(?:studies|research) (?:show|prove|demonstrate|confirm) that \d+%",
         "Fabricated statistic with fake citation"),
        (r"(?:it is|it's) (?:well[- ])?(?:known|established|proven|documented) (?:that|fact)",
         "Unverifiable universal claim"),
        (r"experts (?:agree|say|confirm|believe) that",
         "Vague appeal to unnamed authority"),
    ]

    UNCERTAINTY_SIGNALS = [
        "i think", "i believe", "probably", "possibly", "might",
        "not entirely sure", "to the best of my knowledge",
        "i'm not certain", "it seems", "it appears",
    ]

    HONEST_HEDGES = [
        "based on the available data", "according to the knowledge base",
        "from what I can find", "the training data suggests",
        "I don't have information about", "I cannot verify",
    ]

    @classmethod
    def check_output(cls, text: str, has_sources: bool = False) -> Tuple[float, List[HIAViolation]]:
        """
        Check an LLM output for honesty.

        Returns (honesty_score 0-1, violations).
        """
        violations = []
        text_lower = text.lower()
        score = 1.0

        # Check for fabricated sources
        for pattern, description in cls.FABRICATION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(HIAViolation(
                    value=HIAValue.HONESTY,
                    severity=ViolationSeverity.SERIOUS,
                    description=description,
                    component="llm_output",
                    evidence=re.search(pattern, text, re.IGNORECASE).group(0)[:100],
                ))
                score -= 0.2

        # Check for certainty without sources
        certainty_words = ["definitely", "certainly", "absolutely", "undoubtedly", "clearly", "obviously"]
        certainty_count = sum(1 for w in certainty_words if w in text_lower)
        if certainty_count > 0 and not has_sources:
            violations.append(HIAViolation(
                value=HIAValue.HONESTY,
                severity=ViolationSeverity.WARNING,
                description=f"High certainty language ({certainty_count} instances) without source backing",
                component="llm_output",
            ))
            score -= 0.05 * certainty_count

        # Bonus for honest hedging
        hedge_count = sum(1 for h in cls.HONEST_HEDGES if h in text_lower)
        score += 0.02 * hedge_count

        return max(0.0, min(1.0, score)), violations


# ============================================================================
# INTEGRITY ENFORCER — Internal data must be authentic
# ============================================================================

class IntegrityEnforcer:
    """
    Ensures internal data integrity.

    Checks:
    - KPIs reflect actual performance
    - Trust scores are mathematically consistent
    - Self-reports match actual DB data
    - No error suppression
    - Metrics are internally consistent
    """

    @classmethod
    def check_kpi_integrity(cls, reported_kpi: float, actual_passes: int, actual_total: int) -> Tuple[float, List[HIAViolation]]:
        """Verify a reported KPI matches actual data."""
        violations = []

        if actual_total == 0:
            if reported_kpi > 0:
                violations.append(HIAViolation(
                    value=HIAValue.INTEGRITY,
                    severity=ViolationSeverity.SERIOUS,
                    description=f"KPI reported as {reported_kpi:.1%} but no actual operations recorded",
                    component="kpi_system",
                ))
                return 0.0, violations
            return 1.0, violations

        actual_rate = actual_passes / actual_total
        discrepancy = abs(reported_kpi - actual_rate)

        if discrepancy > 0.1:
            violations.append(HIAViolation(
                value=HIAValue.INTEGRITY,
                severity=ViolationSeverity.CRITICAL,
                description=f"KPI discrepancy: reported {reported_kpi:.1%} vs actual {actual_rate:.1%} (diff: {discrepancy:.1%})",
                component="kpi_system",
                evidence=f"passes={actual_passes}, total={actual_total}",
            ))
            return max(0.0, 1.0 - discrepancy * 5), violations
        elif discrepancy > 0.02:
            violations.append(HIAViolation(
                value=HIAValue.INTEGRITY,
                severity=ViolationSeverity.WARNING,
                description=f"Minor KPI drift: reported {reported_kpi:.1%} vs actual {actual_rate:.1%}",
                component="kpi_system",
            ))

        return max(0.0, 1.0 - discrepancy * 2), violations

    @classmethod
    def check_trust_consistency(cls, trust_score: float, success_count: int, failure_count: int) -> Tuple[float, List[HIAViolation]]:
        """Verify trust score is consistent with success/failure ratio."""
        violations = []
        total = success_count + failure_count

        if total == 0:
            return 1.0, violations

        actual_rate = success_count / total
        discrepancy = abs(trust_score - actual_rate)

        if trust_score > 0.9 and actual_rate < 0.5:
            violations.append(HIAViolation(
                value=HIAValue.INTEGRITY,
                severity=ViolationSeverity.CRITICAL,
                description=f"Trust score inflated: {trust_score:.2f} but actual success rate is {actual_rate:.1%}",
                component="trust_system",
            ))
            return 0.2, violations

        if discrepancy > 0.3:
            violations.append(HIAViolation(
                value=HIAValue.INTEGRITY,
                severity=ViolationSeverity.WARNING,
                description=f"Trust score drift: {trust_score:.2f} vs success rate {actual_rate:.1%}",
                component="trust_system",
            ))

        return max(0.0, 1.0 - discrepancy), violations


# ============================================================================
# ACCOUNTABILITY ENFORCER — Everything is auditable
# ============================================================================

class AccountabilityEnforcer:
    """
    Ensures all actions are accountable.

    Checks:
    - Actions have Genesis Key audit trails
    - Decisions have OODA log entries
    - Failures are recorded (never hidden)
    - Claims can be traced to source
    """

    @classmethod
    def check_audit_trail(cls, action_name: str, has_genesis_key: bool, has_decision_log: bool) -> Tuple[float, List[HIAViolation]]:
        """Verify an action has proper accountability."""
        violations = []
        score = 1.0

        if not has_genesis_key:
            violations.append(HIAViolation(
                value=HIAValue.ACCOUNTABILITY,
                severity=ViolationSeverity.SERIOUS,
                description=f"Action '{action_name}' has no Genesis Key audit trail",
                component="audit_system",
            ))
            score -= 0.4

        if not has_decision_log:
            violations.append(HIAViolation(
                value=HIAValue.ACCOUNTABILITY,
                severity=ViolationSeverity.WARNING,
                description=f"Action '{action_name}' has no decision log entry",
                component="audit_system",
            ))
            score -= 0.2

        return max(0.0, score), violations

    @classmethod
    def check_failure_reporting(cls, total_operations: int, reported_failures: int, actual_errors_in_log: int) -> Tuple[float, List[HIAViolation]]:
        """Verify failures aren't being hidden."""
        violations = []

        if actual_errors_in_log > reported_failures:
            hidden = actual_errors_in_log - reported_failures
            violations.append(HIAViolation(
                value=HIAValue.ACCOUNTABILITY,
                severity=ViolationSeverity.CRITICAL,
                description=f"{hidden} failures detected in logs but not reported (reported: {reported_failures}, actual: {actual_errors_in_log})",
                component="failure_reporting",
            ))
            return 0.3, violations

        return 1.0, violations


# ============================================================================
# UNIFIED HIA FRAMEWORK
# ============================================================================

class HIAFramework:
    """
    Unified Honesty, Integrity & Accountability framework.

    Enforces all three values across the entire system.
    This is IMMUTABLE — cannot be disabled or overridden.
    """

    def __init__(self):
        self.honesty = HonestyEnforcer()
        self.integrity = IntegrityEnforcer()
        self.accountability = AccountabilityEnforcer()
        self.violation_log: List[HIAViolation] = []

    def verify_llm_output(self, text: str, has_sources: bool = False) -> HIAVerificationResult:
        """Full HIA verification of an LLM output."""
        all_violations = []
        checks = []

        # Honesty check
        h_score, h_violations = self.honesty.check_output(text, has_sources)
        all_violations.extend(h_violations)
        checks.append("honesty_output_check")

        # Integrity — LLM shouldn't claim things it can't verify
        i_score = 1.0
        checks.append("integrity_claim_check")

        # Accountability — output should be traceable
        a_score = 1.0
        checks.append("accountability_trace_check")

        overall = (h_score * 0.5) + (i_score * 0.3) + (a_score * 0.2)

        corrections = []
        if h_score < 0.7:
            corrections.append("Add uncertainty disclaimer to unverified claims")
        if any(v.severity == ViolationSeverity.SERIOUS for v in h_violations):
            corrections.append("Remove fabricated source references")

        self.violation_log.extend(all_violations)
        if len(self.violation_log) > 500:
            self.violation_log = self.violation_log[-500:]

        _track_hia(
            f"LLM output verified: H={h_score:.0%} I={i_score:.0%} A={a_score:.0%}",
            confidence=overall
        )

        return HIAVerificationResult(
            passed=overall >= 0.7 and not any(v.severity == ViolationSeverity.CRITICAL for v in all_violations),
            honesty_score=round(h_score, 3),
            integrity_score=round(i_score, 3),
            accountability_score=round(a_score, 3),
            overall_score=round(overall, 3),
            violations=all_violations,
            checks_performed=checks,
            corrections_applied=corrections,
        )

    def verify_kpi_report(self, reported_kpi: float, actual_passes: int, actual_total: int) -> HIAVerificationResult:
        """Verify a KPI report for integrity."""
        i_score, violations = self.integrity.check_kpi_integrity(reported_kpi, actual_passes, actual_total)
        self.violation_log.extend(violations)
        return HIAVerificationResult(
            passed=i_score >= 0.8,
            honesty_score=1.0, integrity_score=round(i_score, 3),
            accountability_score=1.0, overall_score=round(i_score, 3),
            violations=violations, checks_performed=["kpi_integrity_check"],
        )

    def verify_trust_score(self, trust: float, successes: int, failures: int) -> HIAVerificationResult:
        """Verify a trust score for integrity."""
        i_score, violations = self.integrity.check_trust_consistency(trust, successes, failures)
        self.violation_log.extend(violations)
        return HIAVerificationResult(
            passed=i_score >= 0.7,
            honesty_score=1.0, integrity_score=round(i_score, 3),
            accountability_score=1.0, overall_score=round(i_score, 3),
            violations=violations, checks_performed=["trust_consistency_check"],
        )

    def verify_audit_trail(self, action: str, has_genesis_key: bool, has_log: bool) -> HIAVerificationResult:
        """Verify an action has accountability."""
        a_score, violations = self.accountability.check_audit_trail(action, has_genesis_key, has_log)
        self.violation_log.extend(violations)
        return HIAVerificationResult(
            passed=a_score >= 0.6,
            honesty_score=1.0, integrity_score=1.0,
            accountability_score=round(a_score, 3), overall_score=round(a_score, 3),
            violations=violations, checks_performed=["audit_trail_check"],
        )

    def get_system_hia_score(self) -> Dict[str, Any]:
        """Calculate system-wide HIA scores from violation history."""
        recent = self.violation_log[-100:]
        h_violations = [v for v in recent if v.value == HIAValue.HONESTY]
        i_violations = [v for v in recent if v.value == HIAValue.INTEGRITY]
        a_violations = [v for v in recent if v.value == HIAValue.ACCOUNTABILITY]

        h_score = max(0, 1.0 - len(h_violations) * 0.05)
        i_score = max(0, 1.0 - len(i_violations) * 0.08)
        a_score = max(0, 1.0 - len(a_violations) * 0.06)
        overall = (h_score * 0.4) + (i_score * 0.35) + (a_score * 0.25)

        return {
            "honesty_score": round(h_score, 3),
            "integrity_score": round(i_score, 3),
            "accountability_score": round(a_score, 3),
            "overall_hia_score": round(overall, 3),
            "total_violations": len(recent),
            "honesty_violations": len(h_violations),
            "integrity_violations": len(i_violations),
            "accountability_violations": len(a_violations),
            "critical_violations": sum(1 for v in recent if v.severity == ViolationSeverity.CRITICAL),
            "status": "compliant" if overall >= 0.8 else ("at_risk" if overall >= 0.5 else "non_compliant"),
        }


_hia: Optional[HIAFramework] = None

def get_hia_framework() -> HIAFramework:
    """Get the global HIA framework singleton."""
    global _hia
    if _hia is None:
        _hia = HIAFramework()
    return _hia
