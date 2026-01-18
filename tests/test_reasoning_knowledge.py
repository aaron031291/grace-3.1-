"""
Tests for Reasoning Knowledge Base

Tests:
1. Pattern extraction (GSM8K, MATH, ARC, HumanEval)
2. Knowledge storage
3. Similarity search
4. Retrieval-based solving
5. ID generation
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestReasoningPattern:
    """Tests for ReasoningPattern dataclass."""
    
    def test_pattern_creation(self):
        """Test creating a reasoning pattern."""
        from reasoning_knowledge import ReasoningPattern
        
        pattern = ReasoningPattern(
            id="test123",
            problem_type="math",
            problem_text="5 + 3 = ?",
            solution_text="5 + 3 = 8",
            solution_steps=["Add 5 and 3", "Result is 8"],
            final_answer="8",
            source_dataset="gsm8k",
            difficulty="easy",
            tags=["arithmetic"]
        )
        
        assert pattern.id == "test123"
        assert pattern.final_answer == "8"
    
    def test_pattern_to_dict(self):
        """Test pattern serialization."""
        from reasoning_knowledge import ReasoningPattern
        
        pattern = ReasoningPattern(
            id="test123",
            problem_type="math",
            problem_text="5 + 3 = ?",
            solution_text="5 + 3 = 8",
            solution_steps=["Add 5 and 3"],
            final_answer="8",
            source_dataset="gsm8k",
            difficulty="easy",
            tags=["arithmetic"]
        )
        
        d = pattern.to_dict()
        assert d["id"] == "test123"
        assert d["problem_type"] == "math"


class TestPatternExtraction:
    """Tests for pattern extraction from datasets."""
    
    @pytest.fixture
    def kb(self):
        """Create knowledge base with mocked dependencies."""
        with patch('reasoning_knowledge.get_embedding_model'):
            with patch('reasoning_knowledge.get_qdrant_client'):
                from reasoning_knowledge import ReasoningKnowledgeBase
                kb = ReasoningKnowledgeBase()
                return kb
    
    def test_extract_gsm8k_pattern(self, kb):
        """Test GSM8K pattern extraction."""
        problem = {
            "question": "John has 5 apples. He buys 3 more. How many?",
            "answer": "John now has 5 + 3 = 8 apples\n#### 8"
        }
        
        pattern = kb.extract_gsm8k_pattern(problem)
        
        assert pattern.problem_type == "math"
        assert pattern.final_answer == "8"
        assert pattern.source_dataset == "gsm8k"
        assert len(pattern.solution_steps) > 0
    
    def test_extract_math_pattern(self, kb):
        """Test MATH dataset pattern extraction."""
        problem = {
            "problem": "Solve for x: 2x = 10",
            "solution": "Divide both sides by 2: x = \\boxed{5}",
            "level": "Level 1",
            "type": "algebra"
        }
        
        pattern = kb.extract_math_pattern(problem)
        
        assert pattern.problem_type == "math"
        assert pattern.final_answer == "5"
        assert pattern.source_dataset == "math"
    
    def test_extract_arc_pattern(self, kb):
        """Test ARC pattern extraction."""
        problem = {
            "question": "What causes day and night?",
            "choices": {
                "text": ["The Sun moving", "Earth rotating", "Moon phases"],
                "label": ["A", "B", "C"]
            },
            "answerKey": "B"
        }
        
        pattern = kb.extract_arc_pattern(problem)
        
        assert pattern.problem_type == "reasoning"
        assert pattern.final_answer == "B"
        assert pattern.source_dataset == "arc"
    
    def test_extract_code_pattern(self, kb):
        """Test HumanEval pattern extraction."""
        problem = {
            "prompt": "def factorial(n):",
            "canonical_solution": "    if n <= 1: return 1\n    return n * factorial(n-1)",
            "task_id": "HumanEval/1"
        }
        
        pattern = kb.extract_code_pattern(problem)
        
        assert pattern.problem_type == "code"
        assert pattern.source_dataset == "humaneval"


class TestIdGeneration:
    """Tests for ID generation."""
    
    @pytest.fixture
    def kb(self):
        with patch('reasoning_knowledge.get_embedding_model'):
            with patch('reasoning_knowledge.get_qdrant_client'):
                from reasoning_knowledge import ReasoningKnowledgeBase
                return ReasoningKnowledgeBase()
    
    def test_generate_id_deterministic(self, kb):
        """Test that same text produces same ID."""
        id1 = kb._generate_id("test problem")
        id2 = kb._generate_id("test problem")
        
        assert id1 == id2
    
    def test_generate_id_different_for_different_text(self, kb):
        """Test that different text produces different ID."""
        id1 = kb._generate_id("problem 1")
        id2 = kb._generate_id("problem 2")
        
        assert id1 != id2


class TestRetrievalBasedSolving:
    """Tests for retrieval-based problem solving."""
    
    @pytest.fixture
    def kb_with_patterns(self):
        """Create KB with some patterns loaded."""
        with patch('reasoning_knowledge.get_embedding_model'):
            with patch('reasoning_knowledge.get_qdrant_client'):
                from reasoning_knowledge import ReasoningKnowledgeBase, ReasoningPattern
                kb = ReasoningKnowledgeBase()
                
                # Add some patterns manually
                kb.patterns = [
                    ReasoningPattern(
                        id="1",
                        problem_type="math",
                        problem_text="Mary has 4 oranges. She gets 2 more. How many?",
                        solution_text="4 + 2 = 6",
                        solution_steps=["Add 4 and 2"],
                        final_answer="6",
                        source_dataset="gsm8k",
                        difficulty="easy",
                        tags=["addition"]
                    ),
                    ReasoningPattern(
                        id="2",
                        problem_type="math",
                        problem_text="Bob has 10 cookies. He eats 3. How many left?",
                        solution_text="10 - 3 = 7",
                        solution_steps=["Subtract 3 from 10"],
                        final_answer="7",
                        source_dataset="gsm8k",
                        difficulty="easy",
                        tags=["subtraction"]
                    ),
                ]
                
                return kb
    
    def test_find_similar_local(self, kb_with_patterns):
        """Test local similarity search."""
        results = kb_with_patterns._find_similar_local(
            "John has 5 apples, buys 3 more",
            top_k=2,
            problem_type=None
        )
        
        assert len(results) > 0
        # Should return pattern and score
        assert len(results[0]) == 2
    
    def test_solve_by_retrieval_when_no_patterns(self):
        """Test solve_by_retrieval with no patterns."""
        with patch('reasoning_knowledge.get_embedding_model'):
            with patch('reasoning_knowledge.get_qdrant_client'):
                from reasoning_knowledge import ReasoningKnowledgeBase
                kb = ReasoningKnowledgeBase()
                kb.patterns = []  # No patterns
                
                result = kb.solve_by_retrieval("5 + 3?")
                
                # Should indicate no patterns found
                assert result.get("solved") == False or "similar_problems" not in result


class TestKnowledgeBaseStats:
    """Tests for knowledge base statistics."""
    
    def test_get_stats(self):
        """Test getting KB stats."""
        with patch('reasoning_knowledge.get_embedding_model'):
            with patch('reasoning_knowledge.get_qdrant_client') as mock_qdrant:
                # Mock Qdrant response
                mock_client = MagicMock()
                mock_qdrant.return_value = mock_client
                
                from reasoning_knowledge import ReasoningKnowledgeBase
                kb = ReasoningKnowledgeBase()
                kb.patterns = [Mock(), Mock()]  # 2 patterns
                
                stats = kb.get_stats()
                
                assert stats["in_memory_patterns"] == 2


class TestGSM8KAnswerParsing:
    """Tests for GSM8K answer format parsing."""
    
    @pytest.fixture
    def kb(self):
        with patch('reasoning_knowledge.get_embedding_model'):
            with patch('reasoning_knowledge.get_qdrant_client'):
                from reasoning_knowledge import ReasoningKnowledgeBase
                return ReasoningKnowledgeBase()
    
    def test_parse_standard_gsm8k_format(self, kb):
        """Test parsing standard #### format."""
        problem = {
            "question": "test",
            "answer": "Some reasoning steps\n#### 42"
        }
        
        pattern = kb.extract_gsm8k_pattern(problem)
        
        assert pattern.final_answer == "42"
    
    def test_parse_gsm8k_with_decimal(self, kb):
        """Test parsing decimal answer."""
        problem = {
            "question": "test",
            "answer": "Steps here\n#### 3.14"
        }
        
        pattern = kb.extract_gsm8k_pattern(problem)
        
        assert pattern.final_answer == "3.14"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
