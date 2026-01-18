"""
Tests for Reasoning Engine

Tests:
1. Source initialization
2. LLM integration
3. Cognitive verification
4. Oracle verification
5. Answer extraction
6. Cross-verification
7. Confidence calculation
8. API convenience functions
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestReasoningEngineInit:
    """Tests for ReasoningEngine initialization."""
    
    def test_init_creates_sources(self):
        """Test that init creates cognitive engine."""
        with patch('reasoning_engine.requests') as mock_requests:
            mock_requests.get.return_value.ok = False
            
            from reasoning_engine import ReasoningEngine
            engine = ReasoningEngine()
            
            # Should have cognitive engine (or None if import failed)
            assert hasattr(engine, 'cognitive')
    
    def test_init_checks_llm_availability(self):
        """Test that init checks for Ollama."""
        with patch('reasoning_engine.requests') as mock_requests:
            mock_requests.get.return_value.ok = True
            
            from reasoning_engine import ReasoningEngine
            engine = ReasoningEngine()
            
            assert engine.has_llm == True


class TestReasoningResult:
    """Tests for ReasoningResult dataclass."""
    
    def test_to_dict(self):
        """Test result serialization."""
        from reasoning_engine import ReasoningResult
        
        result = ReasoningResult(
            question="5 + 3?",
            answer=8,
            confidence=0.95,
            verified=True,
            reasoning="Computed",
            verifications=[{"source": "cognitive", "answer": 8}]
        )
        
        d = result.to_dict()
        assert d["answer"] == 8
        assert d["verified"] == True
        assert d["confidence"] == 0.95


class TestAnswerExtraction:
    """Tests for answer extraction from LLM responses."""
    
    @pytest.fixture
    def engine(self):
        with patch('reasoning_engine.requests') as mock_requests:
            mock_requests.get.return_value.ok = False
            
            from reasoning_engine import ReasoningEngine
            return ReasoningEngine()
    
    def test_extract_numeric_answer_with_equals(self, engine):
        """Test extracting answer with = sign."""
        text = "Let me calculate... 5 + 3 = 8"
        answer = engine._extract_answer(text)
        assert answer == 8.0
    
    def test_extract_answer_is_pattern(self, engine):
        """Test extracting 'answer is X' pattern."""
        text = "The answer is 42"
        answer = engine._extract_answer(text)
        assert answer == 42.0
    
    def test_extract_last_number(self, engine):
        """Test falling back to last number."""
        text = "First we have 5, then 3, so total is 8"
        answer = engine._extract_answer(text)
        assert answer == 8.0
    
    def test_extract_capital_city(self, engine):
        """Test extracting text answer for factual."""
        text = "The capital of France is Paris."
        answer = engine._extract_answer(text)
        assert answer == "Paris"


class TestCognitiveVerification:
    """Tests for cognitive engine verification."""
    
    def test_cognitive_verification_math(self):
        """Test that cognitive engine verifies math."""
        with patch('reasoning_engine.requests') as mock_requests:
            mock_requests.get.return_value.ok = False
            
            from reasoning_engine import ReasoningEngine
            engine = ReasoningEngine()
            
            if engine.cognitive:
                result = engine.reason("5 + 3")
                
                # Should have cognitive source
                sources = [v["source"] for v in result.verifications]
                assert "cognitive" in sources
    
    def test_cognitive_gives_high_confidence(self):
        """Test cognitive verification boosts confidence."""
        with patch('reasoning_engine.requests') as mock_requests:
            mock_requests.get.return_value.ok = False
            
            from reasoning_engine import ReasoningEngine
            engine = ReasoningEngine()
            
            if engine.cognitive:
                result = engine.reason("2 + 2")
                
                # Cognitive should give high confidence
                assert result.confidence >= 0.9


class TestDetermineAnswer:
    """Tests for answer determination logic."""
    
    @pytest.fixture
    def engine(self):
        with patch('reasoning_engine.requests') as mock_requests:
            mock_requests.get.return_value.ok = False
            
            from reasoning_engine import ReasoningEngine
            return ReasoningEngine()
    
    def test_prefer_cognitive_over_llm(self, engine):
        """Test that cognitive is preferred over LLM."""
        verifications = [
            {"source": "llm", "answer": 9, "confidence": 0.6},
            {"source": "cognitive", "answer": 8, "confidence": 0.95},
        ]
        
        answer, confidence, verified = engine._determine_answer(verifications)
        
        assert answer == 8
        assert verified == True
    
    def test_boost_confidence_on_agreement(self, engine):
        """Test confidence boost when sources agree."""
        verifications = [
            {"source": "llm", "answer": 8, "confidence": 0.6},
            {"source": "cognitive", "answer": 8, "confidence": 0.9},
        ]
        
        answer, confidence, verified = engine._determine_answer(verifications)
        
        # Should boost confidence
        assert confidence > 0.9
    
    def test_verified_when_cognitive(self, engine):
        """Test verified is True when cognitive source."""
        verifications = [
            {"source": "cognitive", "answer": 8, "confidence": 0.95},
        ]
        
        answer, confidence, verified = engine._determine_answer(verifications)
        
        assert verified == True
    
    def test_not_verified_when_llm_only(self, engine):
        """Test verified is False when only LLM."""
        verifications = [
            {"source": "llm", "answer": "Paris", "confidence": 0.6},
        ]
        
        answer, confidence, verified = engine._determine_answer(verifications)
        
        assert verified == False


class TestAnswerMatching:
    """Tests for answer comparison."""
    
    @pytest.fixture
    def engine(self):
        with patch('reasoning_engine.requests') as mock_requests:
            mock_requests.get.return_value.ok = False
            
            from reasoning_engine import ReasoningEngine
            return ReasoningEngine()
    
    def test_match_numeric_exact(self, engine):
        """Test matching exact numbers."""
        assert engine._answers_match(8, 8) == True
    
    def test_match_numeric_close(self, engine):
        """Test matching close numbers."""
        assert engine._answers_match(8.0, 8.001) == True
    
    def test_match_numeric_different(self, engine):
        """Test non-matching numbers."""
        assert engine._answers_match(8, 9) == False
    
    def test_match_string_exact(self, engine):
        """Test matching exact strings."""
        assert engine._answers_match("Paris", "Paris") == True
    
    def test_match_string_case_insensitive(self, engine):
        """Test case-insensitive string matching."""
        assert engine._answers_match("paris", "Paris") == True


class TestFactualQuestions:
    """Tests for factual question detection."""
    
    @pytest.fixture
    def engine(self):
        with patch('reasoning_engine.requests') as mock_requests:
            mock_requests.get.return_value.ok = False
            
            from reasoning_engine import ReasoningEngine
            return ReasoningEngine()
    
    def test_detect_capital_question(self, engine):
        """Test detecting capital question."""
        assert engine._is_factual("What is the capital of France?") == True
    
    def test_detect_who_question(self, engine):
        """Test detecting who question."""
        assert engine._is_factual("Who invented the telephone?") == True
    
    def test_math_not_factual(self, engine):
        """Test that pure math is not factual."""
        # Note: "What is" can trigger factual detection
        # Use pure arithmetic expression
        assert engine._is_factual("5 + 3") == False


class TestConvenienceAPI:
    """Tests for convenience API functions."""
    
    def test_reason_function(self):
        """Test the reason() convenience function."""
        with patch('reasoning_engine.requests') as mock_requests:
            mock_requests.get.return_value.ok = False
            
            from reasoning_engine import reason
            
            result = reason("5 + 3")
            
            assert "answer" in result
            assert "confidence" in result
    
    def test_get_engine_singleton(self):
        """Test get_engine returns singleton."""
        with patch('reasoning_engine.requests') as mock_requests:
            mock_requests.get.return_value.ok = False
            
            from reasoning_engine import get_engine
            
            e1 = get_engine()
            e2 = get_engine()
            
            assert e1 is e2


class TestIntegration:
    """Integration tests for full reasoning flow."""
    
    def test_full_math_reasoning(self):
        """Test complete math reasoning flow."""
        with patch('reasoning_engine.requests') as mock_requests:
            mock_requests.get.return_value.ok = False
            
            from reasoning_engine import ReasoningEngine
            engine = ReasoningEngine()
            
            result = engine.reason("John has 5 apples, buys 3 more. How many?")
            
            assert result.answer == 8
            assert result.verified == True
    
    def test_full_algebra_reasoning(self):
        """Test complete algebra reasoning flow."""
        with patch('reasoning_engine.requests') as mock_requests:
            mock_requests.get.return_value.ok = False
            
            from reasoning_engine import ReasoningEngine
            engine = ReasoningEngine()
            
            result = engine.reason("Solve for x: 2x + 5 = 15")
            
            assert result.answer == 5
            assert result.verified == True
    
    def test_full_percentage_reasoning(self):
        """Test complete percentage reasoning flow."""
        with patch('reasoning_engine.requests') as mock_requests:
            mock_requests.get.return_value.ok = False
            
            from reasoning_engine import ReasoningEngine
            engine = ReasoningEngine()
            
            result = engine.reason("What is 15% of 80?")
            
            assert result.answer == 12.0
            assert result.verified == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
