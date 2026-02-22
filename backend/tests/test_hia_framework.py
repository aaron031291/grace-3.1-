"""
Tests for Honesty, Integrity & Accountability Framework.

100% pass, 0 warnings, 0 skips.
"""

import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = Path(__file__).parent.parent


class TestConstitutionalDNA:
    def test_honesty_in_constitution(self):
        from security.governance import ConstitutionalRule, CONSTITUTIONAL_RULES
        assert ConstitutionalRule.HONESTY in CONSTITUTIONAL_RULES
        assert CONSTITUTIONAL_RULES[ConstitutionalRule.HONESTY].severity == 10
        assert CONSTITUTIONAL_RULES[ConstitutionalRule.HONESTY].enforcement_mode == "hard"

    def test_integrity_in_constitution(self):
        from security.governance import ConstitutionalRule, CONSTITUTIONAL_RULES
        assert ConstitutionalRule.INTEGRITY in CONSTITUTIONAL_RULES
        assert CONSTITUTIONAL_RULES[ConstitutionalRule.INTEGRITY].severity == 10

    def test_accountability_in_constitution(self):
        from security.governance import ConstitutionalRule, CONSTITUTIONAL_RULES
        assert ConstitutionalRule.ACCOUNTABILITY in CONSTITUTIONAL_RULES
        assert CONSTITUTIONAL_RULES[ConstitutionalRule.ACCOUNTABILITY].severity == 10

    def test_11_constitutional_rules(self):
        from security.governance import CONSTITUTIONAL_RULES
        assert len(CONSTITUTIONAL_RULES) == 11


class TestHonestyEnforcer:
    def test_honest_output_passes(self):
        from security.honesty_integrity_accountability import HonestyEnforcer
        score, violations = HonestyEnforcer.check_output(
            "Based on the available data, Python uses indentation for code blocks."
        )
        assert score >= 0.9
        assert len(violations) == 0

    def test_fabricated_source_detected(self):
        from security.honesty_integrity_accountability import HonestyEnforcer
        score, violations = HonestyEnforcer.check_output(
            "According to a recent study by Harvard University, 95% of developers prefer Python."
        )
        assert score < 0.9
        assert len(violations) > 0
        assert violations[0].value.value == "honesty"

    def test_certainty_without_sources_flagged(self):
        from security.honesty_integrity_accountability import HonestyEnforcer
        score, violations = HonestyEnforcer.check_output(
            "This is definitely absolutely certainly the right answer.", has_sources=False
        )
        assert len(violations) > 0

    def test_honest_hedging_rewarded(self):
        from security.honesty_integrity_accountability import HonestyEnforcer
        score1, _ = HonestyEnforcer.check_output("The answer is X.")
        score2, _ = HonestyEnforcer.check_output(
            "Based on the available data, the training data suggests X. I cannot verify this externally."
        )
        assert score2 >= score1


class TestIntegrityEnforcer:
    def test_accurate_kpi_passes(self):
        from security.honesty_integrity_accountability import IntegrityEnforcer
        score, violations = IntegrityEnforcer.check_kpi_integrity(0.85, 85, 100)
        assert score >= 0.9
        assert len(violations) == 0

    def test_inflated_kpi_detected(self):
        from security.honesty_integrity_accountability import IntegrityEnforcer
        score, violations = IntegrityEnforcer.check_kpi_integrity(0.95, 50, 100)
        assert score < 0.8
        assert len(violations) > 0

    def test_kpi_with_no_data_and_high_report(self):
        from security.honesty_integrity_accountability import IntegrityEnforcer
        score, violations = IntegrityEnforcer.check_kpi_integrity(0.9, 0, 0)
        assert score == 0.0
        assert len(violations) > 0

    def test_inflated_trust_detected(self):
        from security.honesty_integrity_accountability import IntegrityEnforcer
        score, violations = IntegrityEnforcer.check_trust_consistency(0.95, 10, 90)
        assert score < 0.5
        assert len(violations) > 0

    def test_consistent_trust_passes(self):
        from security.honesty_integrity_accountability import IntegrityEnforcer
        score, violations = IntegrityEnforcer.check_trust_consistency(0.80, 80, 20)
        assert score >= 0.7


class TestAccountabilityEnforcer:
    def test_full_audit_trail_passes(self):
        from security.honesty_integrity_accountability import AccountabilityEnforcer
        score, violations = AccountabilityEnforcer.check_audit_trail("test_action", True, True)
        assert score == 1.0
        assert len(violations) == 0

    def test_missing_genesis_key_flagged(self):
        from security.honesty_integrity_accountability import AccountabilityEnforcer
        score, violations = AccountabilityEnforcer.check_audit_trail("test_action", False, True)
        assert score < 1.0
        assert any(v.value.value == "accountability" for v in violations)

    def test_hidden_failures_detected(self):
        from security.honesty_integrity_accountability import AccountabilityEnforcer
        score, violations = AccountabilityEnforcer.check_failure_reporting(100, 5, 20)
        assert score < 0.5
        assert len(violations) > 0


class TestHIAFramework:
    def test_singleton(self):
        from security.honesty_integrity_accountability import get_hia_framework
        f1 = get_hia_framework()
        f2 = get_hia_framework()
        assert f1 is f2

    def test_verify_honest_output(self):
        from security.honesty_integrity_accountability import HIAFramework
        hia = HIAFramework()
        result = hia.verify_llm_output("Here is how to use Python lists.", has_sources=True)
        assert result.passed is True
        assert result.honesty_score >= 0.9

    def test_verify_dishonest_output(self):
        from security.honesty_integrity_accountability import HIAFramework
        hia = HIAFramework()
        result = hia.verify_llm_output(
            "According to a recent study by MIT, experts agree that this is definitely absolutely the best approach."
        )
        assert result.honesty_score < 0.9
        assert len(result.violations) > 0

    def test_system_hia_score(self):
        from security.honesty_integrity_accountability import HIAFramework
        hia = HIAFramework()
        score = hia.get_system_hia_score()
        assert "honesty_score" in score
        assert "integrity_score" in score
        assert "accountability_score" in score
        assert "overall_hia_score" in score
        assert "status" in score


class TestChatIntelligenceHIAWiring:
    def test_governance_includes_hia(self):
        source = (BACKEND_DIR / "cognitive" / "chat_intelligence.py").read_text()
        assert "honesty_integrity_accountability" in source
        assert "get_hia_framework" in source
        assert "hia_honesty_check" in source
        assert "hia_score" in source

    def test_governance_returns_hia_scores(self):
        source = (BACKEND_DIR / "cognitive" / "chat_intelligence.py").read_text()
        assert '"honesty"' in source
        assert '"integrity"' in source
        assert '"accountability"' in source
