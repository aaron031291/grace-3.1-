"""
Tests for the Clarity Framework - Grace-Aligned Coding Agent.
"""

import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestClarityFrameworkBasic:
    """Basic tests for Clarity Framework."""
    
    def test_import(self):
        """Test that Clarity Framework can be imported."""
        from cognitive.clarity_framework import (
            ClarityFramework,
            get_clarity_framework,
            ClarityTemplateCompiler,
            ClarityVerificationGate,
            ClarityTrustManager
        )
        assert ClarityFramework is not None
        assert get_clarity_framework is not None
    
    def test_template_compiler_init(self):
        """Test template compiler initialization."""
        from cognitive.clarity_framework import ClarityTemplateCompiler
        
        compiler = ClarityTemplateCompiler()
        assert len(compiler.templates) > 0
        assert "math_factorial" in compiler.templates
        assert "list_filter" in compiler.templates
    
    def test_verification_gate(self):
        """Test verification gate."""
        from cognitive.clarity_framework import ClarityVerificationGate
        
        gate = ClarityVerificationGate()
        
        # Valid code
        report = gate.verify("def hello(): return 'world'", "python")
        assert report.syntax_valid
        assert report.ast_parseable
        assert report.passed
        
        # Invalid syntax
        report = gate.verify("def hello( return 'world'", "python")
        assert not report.syntax_valid
        assert not report.passed
    
    def test_trust_manager(self):
        """Test trust manager."""
        from cognitive.clarity_framework import (
            ClarityTrustManager, 
            TemplateMatch, 
            VerificationReport,
            TrustGate
        )
        
        manager = ClarityTrustManager()
        
        # High trust scenario
        template = TemplateMatch(
            template_id="test",
            template_name="Test",
            match_score=0.9,
            required_params=[],
            filled_params={},
            category="test",
            historical_success_rate=0.95
        )
        
        verification = VerificationReport(verification_id="test")
        verification.syntax_valid = True
        verification.ast_parseable = True
        verification.security_safe = True
        verification.tests_passed = True
        verification.anti_hallucination_passed = True
        
        decision = manager.calculate_trust(template, verification)
        assert decision.trust_score > 0.8
        assert decision.gate == TrustGate.AUTONOMOUS


class TestClarityFrameworkSolve:
    """Tests for solving tasks."""
    
    def test_solve_factorial(self):
        """Test solving factorial problem."""
        from cognitive.clarity_framework import ClarityFramework
        
        framework = ClarityFramework(enable_llm_fallback=False)
        
        result = framework.solve(
            description="Write a function that calculates the factorial of n",
            language="python",
            test_cases=["assert factorial(5) == 120", "assert factorial(0) == 1"],
            function_name="factorial"
        )
        
        assert result["success"]
        assert result["code"] is not None
        assert not result["llm_used"]
        assert "factorial" in result["template_used"].lower()
    
    def test_solve_fibonacci(self):
        """Test solving fibonacci problem."""
        from cognitive.clarity_framework import ClarityFramework
        
        framework = ClarityFramework(enable_llm_fallback=False)
        
        result = framework.solve(
            description="Write a function that returns the nth fibonacci number",
            language="python",
            test_cases=["assert fib(10) == 55", "assert fib(1) == 1"],
            function_name="fib"
        )
        
        assert result["success"]
        assert not result["llm_used"]
    
    def test_solve_prime_check(self):
        """Test solving prime check problem."""
        from cognitive.clarity_framework import ClarityFramework
        
        framework = ClarityFramework(enable_llm_fallback=False)
        
        result = framework.solve(
            description="Write a function to check if a number is prime",
            language="python",
            test_cases=["assert is_prime(7) == True", "assert is_prime(4) == False"],
            function_name="is_prime"
        )
        
        assert result["success"]
        assert not result["llm_used"]
    
    def test_solve_gcd(self):
        """Test solving GCD problem."""
        from cognitive.clarity_framework import ClarityFramework
        
        framework = ClarityFramework(enable_llm_fallback=False)
        
        result = framework.solve(
            description="Write a function to find the greatest common divisor of two numbers",
            language="python",
            test_cases=["assert gcd(12, 8) == 4"],
            function_name="gcd"
        )
        
        assert result["success"]
        assert not result["llm_used"]


class TestClarityFrameworkKPI:
    """Tests for KPI tracking."""
    
    def test_kpi_dashboard(self):
        """Test KPI dashboard."""
        from cognitive.clarity_framework import ClarityFramework
        
        framework = ClarityFramework(enable_llm_fallback=False)
        
        # Solve a few tasks
        framework.solve(
            description="Calculate factorial",
            test_cases=["assert factorial(5) == 120"],
            function_name="factorial"
        )
        
        dashboard = framework.get_kpi_dashboard()
        
        assert "summary" in dashboard
        assert "template_coverage" in dashboard
        assert "grace_integration" in dashboard
        assert dashboard["summary"]["total_tasks"] >= 1


class TestClarityFrameworkTemplates:
    """Tests for template matching."""
    
    def test_template_matching(self):
        """Test template matching."""
        from cognitive.clarity_framework import (
            ClarityTemplateCompiler, 
            ClarityIntent
        )
        
        compiler = ClarityTemplateCompiler()
        
        intent = ClarityIntent(
            intent_id="test",
            task_type="code_generation",
            language="python",
            framework=None,
            target_symbols=["factorial"],
            desired_behavior="Calculate the factorial of a number n!",
            constraints={}
        )
        
        matches = compiler.match_templates(intent)
        
        assert len(matches) > 0
        # Should match factorial template
        template_ids = [m.template_id for m in matches]
        assert "math_factorial" in template_ids
    
    def test_template_synthesis(self):
        """Test template synthesis."""
        from cognitive.clarity_framework import (
            ClarityTemplateCompiler, 
            TemplateMatch
        )
        
        compiler = ClarityTemplateCompiler()
        
        match = TemplateMatch(
            template_id="math_factorial",
            template_name="Factorial",
            match_score=0.9,
            required_params=["function_name"],
            filled_params={},
            category="math_operations",
            historical_success_rate=0.98
        )
        
        code = compiler.synthesize(match, {"function_name": "my_factorial"})
        
        assert code is not None
        assert "my_factorial" in code
        assert "def" in code


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
