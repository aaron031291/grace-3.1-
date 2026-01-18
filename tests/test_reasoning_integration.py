"""
Tests for Unified Reasoning Integration

Tests:
1. OODA phase progression
2. Bidirectional flow (Cognitive ↔ Reasoning)
3. Clarity ambiguity detection
4. Multi-source verification
5. Answer agreement detection
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestReasoningContext:
    """Tests for ReasoningContext."""
    
    def test_context_creation(self):
        from cognitive.reasoning_integration import ReasoningContext, ReasoningPhase
        
        ctx = ReasoningContext(problem="5 + 3")
        
        assert ctx.problem == "5 + 3"
        assert ctx.ooda_phase == ReasoningPhase.OBSERVE
        assert ctx.verified == False
    
    def test_context_defaults(self):
        from cognitive.reasoning_integration import ReasoningContext
        
        ctx = ReasoningContext(problem="test")
        
        assert ctx.confidence == 0.0
        assert ctx.ambiguity_level == "low"
        assert len(ctx.verification_sources) == 0


class TestUnifiedReasoningEngine:
    """Tests for the unified reasoning engine."""
    
    @pytest.fixture
    def engine(self):
        from cognitive.reasoning_integration import UnifiedReasoningEngine
        return UnifiedReasoningEngine()
    
    # ==========================================================================
    # OODA PHASE TESTS
    # ==========================================================================
    
    def test_observe_phase_parses_problem(self, engine):
        """Test that OBSERVE phase parses the problem."""
        from cognitive.reasoning_integration import ReasoningContext, ReasoningPhase
        
        ctx = ReasoningContext(problem="John has 5 apples")
        ctx = engine._observe(ctx)
        
        assert ctx.ooda_phase == ReasoningPhase.OBSERVE
        assert "problem_type" in ctx.observations
    
    def test_orient_phase_detects_solvers(self, engine):
        """Test that ORIENT phase identifies available solvers."""
        from cognitive.reasoning_integration import ReasoningContext
        
        ctx = ReasoningContext(problem="5 + 3")
        ctx = engine._observe(ctx)
        ctx = engine._orient(ctx)
        
        assert "available_solvers" in ctx.orientation
        assert len(ctx.orientation["available_solvers"]) > 0
    
    def test_decide_phase_selects_strategy(self, engine):
        """Test that DECIDE phase selects a strategy."""
        from cognitive.reasoning_integration import ReasoningContext
        
        ctx = ReasoningContext(problem="5 + 3")
        ctx = engine._observe(ctx)
        ctx = engine._orient(ctx)
        ctx = engine._decide(ctx)
        
        assert ctx.decision is not None
        assert "strategy" in ctx.decision
        assert "primary_solver" in ctx.decision
    
    # ==========================================================================
    # MATH REASONING TESTS
    # ==========================================================================
    
    def test_math_uses_compute_primary(self, engine):
        """Test that math problems use compute as primary."""
        from cognitive.reasoning_integration import ReasoningContext
        
        ctx = ReasoningContext(problem="5 + 3")
        ctx = engine._observe(ctx)
        ctx = engine._orient(ctx)
        ctx = engine._decide(ctx)
        
        assert ctx.decision["primary_solver"] == "compute"
    
    def test_solve_addition(self, engine):
        """Test solving addition."""
        ctx = engine.reason("5 + 3")
        
        assert ctx.final_answer == 8.0 or ctx.final_answer == 8
        assert ctx.verified == True
    
    def test_solve_percentage(self, engine):
        """Test solving percentage."""
        ctx = engine.reason("What is 15% of 80?")
        
        assert ctx.final_answer == 12.0
        assert ctx.verified == True
    
    def test_solve_algebra(self, engine):
        """Test solving algebra."""
        ctx = engine.reason("Solve for x: 2x + 5 = 15")
        
        assert ctx.final_answer == 5
        assert ctx.verified == True
    
    # ==========================================================================
    # VERIFICATION TESTS
    # ==========================================================================
    
    def test_answers_match_numeric(self, engine):
        """Test numeric answer matching."""
        assert engine._answers_match(8, 8) == True
        assert engine._answers_match(8.0, 8) == True
        assert engine._answers_match(8, 9) == False
    
    def test_answers_match_string(self, engine):
        """Test string answer matching."""
        assert engine._answers_match("Paris", "Paris") == True
        assert engine._answers_match("paris", "PARIS") == True
    
    def test_verified_when_sources_agree(self, engine):
        """Test that verified=True when sources agree."""
        ctx = engine.reason("5 + 3")
        
        # Compute and LLM should both get 8
        if "compute" in ctx.verification_sources and "llm" in ctx.verification_sources:
            assert ctx.verified == True
    
    # ==========================================================================
    # CLARITY TESTS
    # ==========================================================================
    
    def test_clarity_low_for_clear_problem(self, engine):
        """Test low ambiguity for clear problems."""
        result = engine._check_clarity("What is 5 + 3?")
        
        assert result["level"] == "low"
    
    def test_clarity_detects_ambiguous(self, engine):
        """Test ambiguity detection."""
        result = engine._check_clarity("What is it that they want from that thing?")
        
        # "it", "they", "that" are ambiguous
        assert result["level"] in ["medium", "high"]
        assert len(result["clarifications"]) > 0
    
    # ==========================================================================
    # FACTUAL QUESTION TESTS
    # ==========================================================================
    
    def test_factual_uses_llm_primary(self, engine):
        """Test that factual questions use LLM as primary."""
        from cognitive.reasoning_integration import ReasoningContext
        
        ctx = ReasoningContext(problem="What is the capital of France?")
        ctx = engine._observe(ctx)
        ctx = engine._orient(ctx)
        ctx = engine._decide(ctx)
        
        assert ctx.decision["primary_solver"] == "llm"


class TestConvenienceAPI:
    """Tests for convenience API."""
    
    def test_reason_function(self):
        from cognitive.reasoning_integration import reason
        
        result = reason("5 + 3")
        
        assert "answer" in result
        assert "verified" in result
        assert result["answer"] == 8 or result["answer"] == 8.0
    
    def test_get_unified_engine_singleton(self):
        from cognitive.reasoning_integration import get_unified_engine
        
        e1 = get_unified_engine()
        e2 = get_unified_engine()
        
        assert e1 is e2


class TestBidirectionalFlow:
    """Tests for bidirectional Cognitive ↔ Reasoning flow."""
    
    @pytest.fixture
    def engine(self):
        from cognitive.reasoning_integration import UnifiedReasoningEngine
        return UnifiedReasoningEngine()
    
    def test_compute_informs_verify(self, engine):
        """Test that compute results inform verification."""
        ctx = engine.reason("2 * 6")
        
        # Compute should provide high-confidence answer
        if ctx.compute_result:
            assert ctx.compute_result["confidence"] >= 0.9
    
    def test_llm_informs_compute(self, engine):
        """Test that when compute fails, LLM can provide answer."""
        ctx = engine.reason("What is the meaning of life?")
        
        # This should fall to LLM since compute can't handle it
        if ctx.llm_result:
            assert "llm" in ctx.verification_sources


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
