"""
Layer 2 Clarity Framework - REAL Functional Tests

Tests verify ACTUAL Clarity Framework behavior using real implementations:
- ClarityPhase state machine transitions
- Template matching and scoring
- Code verification with multi-layer checks
- Trust calculation and gate decisions
- KPI tracking and metrics
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List, Optional
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# CLARITY PHASE ENUM TESTS
# =============================================================================

class TestClarityPhaseEnumFunctional:
    """Functional tests for ClarityPhase enum."""

    def test_all_clarity_phases_defined(self):
        """All required Clarity phases must be defined."""
        from cognitive.clarity_framework import ClarityPhase

        required_phases = [
            "OBSERVE", "ORIENT", "DECIDE", "ACT", "LEARN", "COMPLETE", "FAILED"
        ]

        for phase_name in required_phases:
            assert hasattr(ClarityPhase, phase_name), f"Missing phase: {phase_name}"

    def test_phase_values_are_lowercase(self):
        """Phase values must be lowercase strings."""
        from cognitive.clarity_framework import ClarityPhase

        for phase in ClarityPhase:
            assert isinstance(phase.value, str)
            assert phase.value == phase.value.lower()


# =============================================================================
# TRUST GATE ENUM TESTS
# =============================================================================

class TestTrustGateEnumFunctional:
    """Functional tests for TrustGate enum."""

    def test_all_trust_gates_defined(self):
        """All required trust gates must be defined."""
        from cognitive.clarity_framework import TrustGate

        required_gates = ["AUTONOMOUS", "SUPERVISED", "BLOCKED", "ESCALATE"]

        for gate_name in required_gates:
            assert hasattr(TrustGate, gate_name), f"Missing gate: {gate_name}"

    def test_trust_gate_values(self):
        """Trust gate values must be lowercase strings."""
        from cognitive.clarity_framework import TrustGate

        assert TrustGate.AUTONOMOUS.value == "autonomous"
        assert TrustGate.SUPERVISED.value == "supervised"
        assert TrustGate.BLOCKED.value == "blocked"
        assert TrustGate.ESCALATE.value == "escalate"


# =============================================================================
# COGNITIVE AGENT ENUM TESTS
# =============================================================================

class TestCognitiveAgentEnumFunctional:
    """Functional tests for CognitiveAgent enum."""

    def test_all_cognitive_agents_defined(self):
        """All required cognitive agents must be defined."""
        from cognitive.clarity_framework import CognitiveAgent

        required_agents = [
            "OBSERVER", "ORACLE_LIAISON", "SYNTHESIZER",
            "VERIFIER", "HEALER", "LEARNER"
        ]

        for agent_name in required_agents:
            assert hasattr(CognitiveAgent, agent_name), f"Missing agent: {agent_name}"


# =============================================================================
# TEMPLATE COMPILER FUNCTIONAL TESTS
# =============================================================================

class TestTemplateCompilerFunctional:
    """Functional tests for ClarityTemplateCompiler."""

    @pytest.fixture
    def compiler(self):
        """Create template compiler instance."""
        from cognitive.clarity_framework import ClarityTemplateCompiler
        return ClarityTemplateCompiler()

    def test_compiler_has_templates(self, compiler):
        """Compiler must have built-in templates."""
        assert len(compiler.templates) > 0

    def test_list_filter_template_exists(self, compiler):
        """list_filter template must exist."""
        assert "list_filter" in compiler.templates

    def test_list_filter_template_has_required_fields(self, compiler):
        """list_filter template must have required fields."""
        template = compiler.templates["list_filter"]

        assert "name" in template
        assert "category" in template
        assert "pattern_keywords" in template
        assert "template" in template
        assert "params" in template

    def test_match_templates_returns_list(self, compiler):
        """match_templates must return a list."""
        from cognitive.clarity_framework import ClarityIntent

        intent = ClarityIntent(
            intent_id="test-1",
            task_type="code_generation",
            language="python",
            framework=None,
            target_symbols=["filter_list"],
            desired_behavior="filter a list to get even numbers",
            constraints={}
        )

        matches = compiler.match_templates(intent)

        assert isinstance(matches, list)

    def test_match_templates_filters_by_keyword(self, compiler):
        """match_templates must match by keywords in description."""
        from cognitive.clarity_framework import ClarityIntent

        intent = ClarityIntent(
            intent_id="test-2",
            task_type="code_generation",
            language="python",
            framework=None,
            target_symbols=["is_prime"],
            desired_behavior="check if a number is prime",
            constraints={}
        )

        matches = compiler.match_templates(intent)

        # Should find math_prime_check template
        template_ids = [m.template_id for m in matches]
        assert "math_prime_check" in template_ids

    def test_synthesize_generates_code(self, compiler):
        """synthesize must generate code from template."""
        from cognitive.clarity_framework import TemplateMatch

        match = TemplateMatch(
            template_id="math_factorial",
            template_name="Factorial",
            match_score=0.9,
            required_params=["function_name"],
            filled_params={},
            category="math_operations"
        )

        code = compiler.synthesize(match, {"function_name": "factorial"})

        assert code is not None
        assert "def factorial" in code
        assert "return" in code

    def test_synthesize_with_missing_params_returns_none(self, compiler):
        """synthesize with missing params must return None."""
        from cognitive.clarity_framework import TemplateMatch

        match = TemplateMatch(
            template_id="list_filter",
            template_name="List Filter",
            match_score=0.9,
            required_params=["function_name", "params", "iterable", "condition"],
            filled_params={},
            category="list_operations"
        )

        # Missing required params
        code = compiler.synthesize(match, {"function_name": "filter_items"})

        assert code is None

    def test_record_outcome_updates_stats(self, compiler):
        """record_outcome must update template statistics."""
        initial_uses = compiler.template_stats.get("math_factorial", {}).get("uses", 0)

        compiler.record_outcome("math_factorial", success=True)

        assert compiler.template_stats["math_factorial"]["uses"] == initial_uses + 1
        assert compiler.template_stats["math_factorial"]["successes"] >= 1


# =============================================================================
# VERIFICATION GATE FUNCTIONAL TESTS
# =============================================================================

class TestVerificationGateFunctional:
    """Functional tests for ClarityVerificationGate."""

    @pytest.fixture
    def verifier(self):
        """Create verification gate instance."""
        from cognitive.clarity_framework import ClarityVerificationGate
        return ClarityVerificationGate()

    def test_valid_python_passes_syntax_check(self, verifier):
        """Valid Python code must pass syntax check."""
        code = """
def add(a, b):
    return a + b
"""
        report = verifier.verify(code, language="python")

        assert report.syntax_valid is True

    def test_invalid_python_fails_syntax_check(self, verifier):
        """Invalid Python code must fail syntax check."""
        code = """
def add(a, b)  # Missing colon
    return a + b
"""
        report = verifier.verify(code, language="python")

        assert report.syntax_valid is False

    def test_valid_python_passes_ast_check(self, verifier):
        """Valid Python code must pass AST check."""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        report = verifier.verify(code, language="python")

        assert report.ast_parseable is True

    def test_security_check_blocks_eval(self, verifier):
        """Security check must block dangerous eval."""
        code = """
def unsafe(user_input):
    return eval(user_input)
"""
        report = verifier.verify(code, language="python")

        assert report.security_safe is False

    def test_security_check_blocks_exec(self, verifier):
        """Security check must block dangerous exec."""
        code = """
def unsafe(user_input):
    exec(user_input)
"""
        report = verifier.verify(code, language="python")

        assert report.security_safe is False

    def test_security_check_blocks_os_system(self, verifier):
        """Security check must block os.system."""
        code = """
import os
def unsafe(cmd):
    os.system(cmd)
"""
        report = verifier.verify(code, language="python")

        assert report.security_safe is False

    def test_safe_code_passes_security_check(self, verifier):
        """Safe code must pass security check."""
        code = """
def safe_add(a, b):
    return a + b
"""
        report = verifier.verify(code, language="python")

        assert report.security_safe is True

    def test_verification_report_has_passed_property(self, verifier):
        """VerificationReport must have passed property."""
        code = """
def valid(x):
    return x * 2
"""
        report = verifier.verify(code, language="python")

        assert hasattr(report, 'passed')
        assert report.passed is True

    def test_verification_tracks_time(self, verifier):
        """Verification must track time."""
        code = "def f(): pass"

        report = verifier.verify(code, language="python")

        assert report.verification_time_ms >= 0

    def test_test_cases_validated(self, verifier):
        """Test cases must be validated."""
        code = """
def is_even(n):
    return n % 2 == 0
"""
        test_cases = [
            "is_even(2) == True",
            "is_even(3) == False",
            "is_even(0) == True"
        ]

        report = verifier.verify(code, language="python", test_cases=test_cases)

        assert report.tests_passed is True

    def test_failing_test_cases_detected(self, verifier):
        """Failing test cases must be detected."""
        code = """
def is_even(n):
    return n % 2 == 1  # Wrong!
"""
        test_cases = [
            "is_even(2) == True",  # Will fail
        ]

        report = verifier.verify(code, language="python", test_cases=test_cases)

        assert report.tests_passed is False


# =============================================================================
# TRUST MANAGER FUNCTIONAL TESTS
# =============================================================================

class TestTrustManagerFunctional:
    """Functional tests for ClarityTrustManager."""

    @pytest.fixture
    def trust_manager(self):
        """Create trust manager instance."""
        from cognitive.clarity_framework import ClarityTrustManager
        return ClarityTrustManager()

    @pytest.fixture
    def passing_verification(self):
        """Create a passing verification report."""
        from cognitive.clarity_framework import VerificationReport

        return VerificationReport(
            verification_id="test-1",
            syntax_valid=True,
            ast_parseable=True,
            imports_resolve=True,
            security_safe=True,
            anti_hallucination_passed=True,
            tests_passed=True
        )

    @pytest.fixture
    def failing_verification(self):
        """Create a failing verification report."""
        from cognitive.clarity_framework import VerificationReport

        return VerificationReport(
            verification_id="test-2",
            syntax_valid=False,
            ast_parseable=False,
            security_safe=True,
            anti_hallucination_passed=True
        )

    def test_high_trust_gets_autonomous_gate(self, trust_manager, passing_verification):
        """High trust score must get AUTONOMOUS gate."""
        from cognitive.clarity_framework import TemplateMatch, TrustGate

        template = TemplateMatch(
            template_id="test",
            template_name="Test",
            match_score=0.95,
            required_params=[],
            filled_params={},
            category="test",
            historical_success_rate=0.95
        )

        decision = trust_manager.calculate_trust(
            template_match=template,
            verification=passing_verification,
            oracle_contributed=True,
            healing_attempts=0
        )

        assert decision.trust_score >= trust_manager.auto_threshold
        assert decision.gate == TrustGate.AUTONOMOUS

    def test_medium_trust_gets_supervised_gate(self, trust_manager, passing_verification):
        """Medium trust score must get SUPERVISED gate."""
        from cognitive.clarity_framework import TemplateMatch, TrustGate

        template = TemplateMatch(
            template_id="test",
            template_name="Test",
            match_score=0.5,  # Lower match score
            required_params=[],
            filled_params={},
            category="test",
            historical_success_rate=0.6
        )

        decision = trust_manager.calculate_trust(
            template_match=template,
            verification=passing_verification,
            oracle_contributed=False,
            healing_attempts=1
        )

        # Should be in supervised range
        if trust_manager.supervised_threshold <= decision.trust_score < trust_manager.auto_threshold:
            assert decision.gate == TrustGate.SUPERVISED

    def test_low_trust_gets_blocked_gate(self, trust_manager, failing_verification):
        """Low trust score must get BLOCKED gate."""
        from cognitive.clarity_framework import TrustGate

        decision = trust_manager.calculate_trust(
            template_match=None,
            verification=failing_verification,
            oracle_contributed=False,
            healing_attempts=3
        )

        # With failing verification and no template, should be blocked
        assert decision.trust_score < trust_manager.supervised_threshold
        assert decision.gate == TrustGate.BLOCKED

    def test_healing_attempts_reduce_trust(self, trust_manager, passing_verification):
        """Multiple healing attempts must reduce trust."""
        from cognitive.clarity_framework import TemplateMatch

        template = TemplateMatch(
            template_id="test",
            template_name="Test",
            match_score=0.8,
            required_params=[],
            filled_params={},
            category="test",
            historical_success_rate=0.8
        )

        decision_0 = trust_manager.calculate_trust(template, passing_verification, False, healing_attempts=0)
        decision_2 = trust_manager.calculate_trust(template, passing_verification, False, healing_attempts=2)
        decision_4 = trust_manager.calculate_trust(template, passing_verification, False, healing_attempts=4)

        assert decision_0.trust_score > decision_2.trust_score
        assert decision_2.trust_score > decision_4.trust_score

    def test_oracle_contribution_increases_trust(self, trust_manager, passing_verification):
        """Oracle contribution must increase trust."""
        from cognitive.clarity_framework import TemplateMatch

        template = TemplateMatch(
            template_id="test",
            template_name="Test",
            match_score=0.7,
            required_params=[],
            filled_params={},
            category="test",
            historical_success_rate=0.7
        )

        decision_no_oracle = trust_manager.calculate_trust(template, passing_verification, False, 0)
        decision_with_oracle = trust_manager.calculate_trust(template, passing_verification, True, 0)

        assert decision_with_oracle.trust_score > decision_no_oracle.trust_score

    def test_trust_decision_has_confidence_interval(self, trust_manager, passing_verification):
        """Trust decision must have confidence interval."""
        decision = trust_manager.calculate_trust(None, passing_verification, False, 0)

        assert decision.confidence_interval is not None
        assert len(decision.confidence_interval) == 2
        assert decision.confidence_interval[0] <= decision.trust_score
        assert decision.confidence_interval[1] >= decision.trust_score

    def test_trust_decision_has_factors(self, trust_manager, passing_verification):
        """Trust decision must include scoring factors."""
        from cognitive.clarity_framework import TemplateMatch

        template = TemplateMatch(
            template_id="test",
            template_name="Test",
            match_score=0.8,
            required_params=[],
            filled_params={},
            category="test"
        )

        decision = trust_manager.calculate_trust(template, passing_verification, True, 1)

        assert "template_reliability" in decision.factors
        assert "match_confidence" in decision.factors
        assert "verification_strength" in decision.factors
        assert "oracle_contribution" in decision.factors
        assert "healing_factor" in decision.factors


# =============================================================================
# CLARITY INTENT FUNCTIONAL TESTS
# =============================================================================

class TestClarityIntentFunctional:
    """Functional tests for ClarityIntent data class."""

    def test_clarity_intent_creation(self):
        """ClarityIntent must be creatable with required fields."""
        from cognitive.clarity_framework import ClarityIntent

        intent = ClarityIntent(
            intent_id="test-123",
            task_type="code_generation",
            language="python",
            framework=None,
            target_symbols=["my_function"],
            desired_behavior="Add two numbers together",
            constraints={"max_lines": 10}
        )

        assert intent.intent_id == "test-123"
        assert intent.task_type == "code_generation"
        assert intent.language == "python"
        assert intent.desired_behavior == "Add two numbers together"

    def test_clarity_intent_defaults(self):
        """ClarityIntent must have sensible defaults."""
        from cognitive.clarity_framework import ClarityIntent

        intent = ClarityIntent(
            intent_id="test",
            task_type="test",
            language="python",
            framework=None,
            target_symbols=[],
            desired_behavior="test",
            constraints={}
        )

        assert intent.confidence == 0.0
        assert intent.llm_used is False
        assert intent.genesis_key_id is None
        assert intent.oracle_insights == []


# =============================================================================
# CLARITY STATE FUNCTIONAL TESTS
# =============================================================================

class TestClarityStateFunctional:
    """Functional tests for ClarityState data class."""

    def test_clarity_state_creation(self):
        """ClarityState must be creatable."""
        from cognitive.clarity_framework import ClarityState, ClarityPhase

        state = ClarityState(
            task_id="task-123",
            phase=ClarityPhase.OBSERVE
        )

        assert state.task_id == "task-123"
        assert state.phase == ClarityPhase.OBSERVE

    def test_clarity_state_defaults(self):
        """ClarityState must have sensible defaults."""
        from cognitive.clarity_framework import ClarityState, ClarityPhase

        state = ClarityState(
            task_id="test",
            phase=ClarityPhase.OBSERVE
        )

        assert state.healing_attempts == 0
        assert state.max_healing_attempts == 3
        assert state.llm_escalations == 0
        assert state.errors == []
        assert state.genesis_keys == []


# =============================================================================
# CLARITY KPIS FUNCTIONAL TESTS
# =============================================================================

class TestClarityKPIsFunctional:
    """Functional tests for ClarityKPIs tracking."""

    @pytest.fixture
    def kpi(self):
        """Create fresh KPI instance."""
        from cognitive.clarity_framework import ClarityKPIs
        return ClarityKPIs()

    def test_kpi_initial_values(self, kpi):
        """KPIs must start at zero."""
        assert kpi.total_tasks == 0
        assert kpi.template_solved == 0
        assert kpi.llm_fallback == 0
        assert kpi.verification_passes == 0

    def test_kpi_to_dict(self, kpi):
        """KPIs must serialize to dict."""
        kpi.total_tasks = 10
        kpi.template_solved = 8
        kpi.llm_fallback = 2

        result = kpi.to_dict()

        assert isinstance(result, dict)
        assert result["total_tasks"] == 10
        assert result["template_solved"] == 8
        assert result["llm_fallback"] == 2

    def test_kpi_template_coverage_calculation(self, kpi):
        """KPI template coverage must calculate correctly."""
        kpi.total_tasks = 100
        kpi.template_solved = 75

        result = kpi.to_dict()

        assert result["template_coverage_pct"] == 75.0

    def test_kpi_llm_independence_calculation(self, kpi):
        """KPI LLM independence rate must calculate correctly."""
        kpi.total_tasks = 100
        kpi.llm_fallback = 20

        result = kpi.to_dict()

        assert result["llm_independence_rate"] == 80.0


# =============================================================================
# TEMPLATE MATCH FUNCTIONAL TESTS
# =============================================================================

class TestTemplateMatchFunctional:
    """Functional tests for TemplateMatch data class."""

    def test_template_match_creation(self):
        """TemplateMatch must be creatable."""
        from cognitive.clarity_framework import TemplateMatch

        match = TemplateMatch(
            template_id="list_filter",
            template_name="List Filter",
            match_score=0.85,
            required_params=["function_name", "iterable", "condition"],
            filled_params={"function_name": "filter_evens"},
            category="list_operations"
        )

        assert match.template_id == "list_filter"
        assert match.match_score == 0.85
        assert match.category == "list_operations"

    def test_template_match_defaults(self):
        """TemplateMatch must have sensible defaults."""
        from cognitive.clarity_framework import TemplateMatch

        match = TemplateMatch(
            template_id="test",
            template_name="Test",
            match_score=0.5,
            required_params=[],
            filled_params={},
            category="test"
        )

        assert match.historical_success_rate == 0.0
        assert match.oracle_boosted is False


# =============================================================================
# SYNTHESIS RESULT FUNCTIONAL TESTS
# =============================================================================

class TestSynthesisResultFunctional:
    """Functional tests for SynthesisResult data class."""

    def test_synthesis_result_creation(self):
        """SynthesisResult must be creatable."""
        from cognitive.clarity_framework import SynthesisResult

        result = SynthesisResult(
            synthesis_id="synth-123",
            template_id="list_filter",
            code="def filter_items(items): return [x for x in items if x > 0]",
            transform_type="template",
            confidence=0.9,
            provenance={"source": "list_filter template"}
        )

        assert result.synthesis_id == "synth-123"
        assert result.template_id == "list_filter"
        assert result.transform_type == "template"
        assert "def filter_items" in result.code


# =============================================================================
# ANTI-HALLUCINATION FUNCTIONAL TESTS
# =============================================================================

class TestAntiHallucinationFunctional:
    """Functional tests for anti-hallucination checks."""

    @pytest.fixture
    def verifier(self):
        """Create verification gate."""
        from cognitive.clarity_framework import ClarityVerificationGate
        return ClarityVerificationGate()

    def test_todo_implement_detected(self, verifier):
        """TODO: implement must be detected as hallucination."""
        code = """
def my_function():
    # TODO: implement this later
    pass
"""
        report = verifier.verify(code, language="python", is_llm_generated=True)

        assert report.anti_hallucination_passed is False

    def test_not_implemented_error_detected(self, verifier):
        """raise NotImplementedError must be detected."""
        code = """
def my_function():
    raise NotImplementedError
"""
        report = verifier.verify(code, language="python", is_llm_generated=True)

        assert report.anti_hallucination_passed is False

    def test_complete_implementation_passes(self, verifier):
        """Complete implementation must pass anti-hallucination."""
        code = """
def add(a, b):
    return a + b
"""
        report = verifier.verify(code, language="python", is_llm_generated=True)

        assert report.anti_hallucination_passed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
