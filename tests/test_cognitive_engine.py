"""
Tests for Cognitive Engine

Tests:
1. Problem parsing
2. Entity extraction
3. Relationship detection
4. Arithmetic solving
5. Algebra solving (SymPy)
6. Percentage calculations
7. Statistics
8. Code execution
9. Cross-verification
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestProblemParser:
    """Tests for problem parsing and classification."""
    
    @pytest.fixture
    def parser(self):
        from cognitive_engine import ProblemParser
        return ProblemParser()
    
    def test_detect_word_problem(self, parser):
        """Test word problem detection."""
        from cognitive_engine import ProblemType
        
        result = parser.parse("John has 5 apples. He buys 3 more.")
        assert result.problem_type == ProblemType.WORD_PROBLEM
    
    def test_detect_algebra(self, parser):
        """Test algebra problem detection."""
        from cognitive_engine import ProblemType
        
        result = parser.parse("Solve for x: 2x + 5 = 15")
        assert result.problem_type == ProblemType.ALGEBRA
    
    def test_detect_arithmetic(self, parser):
        """Test arithmetic detection."""
        from cognitive_engine import ProblemType
        
        result = parser.parse("5 + 3 * 2")
        assert result.problem_type == ProblemType.ARITHMETIC
    
    def test_detect_percentage(self, parser):
        """Test percentage detection."""
        from cognitive_engine import ProblemType
        
        result = parser.parse("What is 15% of 80?")
        assert result.problem_type == ProblemType.ARITHMETIC
    
    def test_detect_statistics(self, parser):
        """Test statistics problem detection."""
        from cognitive_engine import ProblemType
        
        result = parser.parse("Find the average of 10, 20, 30")
        assert result.problem_type == ProblemType.STATISTICS
    
    def test_detect_factual(self, parser):
        """Test factual question detection."""
        from cognitive_engine import ProblemType
        
        result = parser.parse("What is the capital of France?")
        assert result.problem_type == ProblemType.FACTUAL
    
    def test_extract_entities_word_problem(self, parser):
        """Test entity extraction from word problem."""
        result = parser.parse("John has 5 apples. He buys 3 more apples.")
        
        # Should extract the numbers
        assert any(v == 5 for v in result.entities.values())
        assert any(v == 3 for v in result.entities.values())
    
    def test_extract_relationships_addition(self, parser):
        """Test relationship detection for addition."""
        result = parser.parse("John has 5 apples. He buys 3 more.")
        
        assert 'add' in result.relationships
    
    def test_extract_relationships_subtraction(self, parser):
        """Test relationship detection for subtraction."""
        result = parser.parse("Sarah has 10 cookies. She gives away 3.")
        
        assert 'subtract' in result.relationships
    
    def test_extract_relationships_multiplication(self, parser):
        """Test relationship detection for multiplication."""
        result = parser.parse("12 boxes with 8 items each.")
        
        assert 'multiply' in result.relationships


class TestCognitiveEngine:
    """Tests for the main cognitive engine."""
    
    @pytest.fixture
    def engine(self):
        from cognitive_engine import CognitiveEngine
        return CognitiveEngine()
    
    # ==========================================================================
    # WORD PROBLEMS
    # ==========================================================================
    
    def test_solve_addition_word_problem(self, engine):
        """Test solving addition word problem."""
        result = engine.solve("John has 5 apples. He buys 3 more. How many?")
        
        assert result["solved"] == True
        assert result["answer"] == 8
    
    def test_solve_subtraction_word_problem(self, engine):
        """Test solving subtraction word problem."""
        result = engine.solve("Sarah has 20 cookies. She gives away 7. How many left?")
        
        assert result["solved"] == True
        assert result["answer"] == 13
    
    def test_solve_multiplication_word_problem(self, engine):
        """Test solving multiplication word problem."""
        result = engine.solve("A store has 12 boxes with 8 items each. What is the total?")
        
        assert result["solved"] == True
        assert result["answer"] == 96
    
    # ==========================================================================
    # ARITHMETIC
    # ==========================================================================
    
    def test_solve_simple_arithmetic(self, engine):
        """Test simple arithmetic."""
        result = engine.solve("5 + 3")
        
        assert result["solved"] == True
        assert result["answer"] == 8.0
    
    def test_solve_arithmetic_with_order(self, engine):
        """Test order of operations."""
        result = engine.solve("5 + 3 * 2")
        
        assert result["solved"] == True
        assert result["answer"] == 11.0
    
    def test_solve_division(self, engine):
        """Test division."""
        result = engine.solve("100 / 4")
        
        assert result["solved"] == True
        assert result["answer"] == 25.0
    
    # ==========================================================================
    # PERCENTAGES
    # ==========================================================================
    
    def test_solve_percentage_of(self, engine):
        """Test percentage calculation."""
        result = engine.solve("What is 15% of 80?")
        
        assert result["solved"] == True
        assert result["answer"] == 12.0
    
    def test_solve_percentage_word(self, engine):
        """Test percentage with word 'percent'."""
        result = engine.solve("What is 25 percent of 200?")
        
        assert result["solved"] == True
        assert abs(result["answer"] - 50.0) < 0.01
    
    # ==========================================================================
    # ALGEBRA
    # ==========================================================================
    
    def test_solve_linear_equation_add(self, engine):
        """Test solving linear equation with addition."""
        result = engine.solve("Solve for x: 2x + 5 = 15")
        
        assert result["solved"] == True
        assert result["answer"] == 5
    
    def test_solve_linear_equation_subtract(self, engine):
        """Test solving linear equation with subtraction."""
        result = engine.solve("What is x if 3x - 7 = 20?")
        
        assert result["solved"] == True
        assert result["answer"] == 9
    
    # ==========================================================================
    # STATISTICS
    # ==========================================================================
    
    def test_solve_average(self, engine):
        """Test average calculation."""
        result = engine.solve("Find the average of 10, 20, 30, 40, 50")
        
        assert result["solved"] == True
        assert result["answer"] == 30
    
    # ==========================================================================
    # VERIFICATION
    # ==========================================================================
    
    def test_verified_when_computed(self, engine):
        """Test that computed answers are verified."""
        result = engine.solve("5 + 3")
        
        assert result["verified"] == True
    
    def test_confidence_high_for_computed(self, engine):
        """Test high confidence for computed answers."""
        result = engine.solve("2 + 2")
        
        assert result["confidence"] >= 0.9


class TestArithmeticSolver:
    """Tests for arithmetic solver."""
    
    @pytest.fixture
    def solver(self):
        from cognitive_engine import ArithmeticSolver
        return ArithmeticSolver()
    
    def test_can_solve_arithmetic(self, solver):
        from cognitive_engine import ParsedProblem, ProblemType
        
        problem = ParsedProblem(
            original="5 + 3",
            problem_type=ProblemType.ARITHMETIC,
            entities={"num_0": 5, "num_1": 3},
            relationships=["add"],
            question="result",
            constraints=[],
        )
        
        assert solver.can_solve(problem) == True
    
    def test_solve_addition(self, solver):
        from cognitive_engine import ParsedProblem, ProblemType
        
        problem = ParsedProblem(
            original="5 + 3",
            problem_type=ProblemType.ARITHMETIC,
            entities={"a": 5, "b": 3},
            relationships=["add"],
            question="result",
            constraints=[],
        )
        
        result = solver.solve(problem)
        assert result.answer == 8


class TestSymbolicMathSolver:
    """Tests for SymPy solver."""
    
    @pytest.fixture
    def solver(self):
        from cognitive_engine import SymbolicMathSolver
        return SymbolicMathSolver()
    
    def test_can_solve_algebra(self, solver):
        from cognitive_engine import ParsedProblem, ProblemType
        
        problem = ParsedProblem(
            original="Solve 2x + 5 = 15",
            problem_type=ProblemType.ALGEBRA,
            entities={},
            relationships=[],
            question="x",
            constraints=[],
        )
        
        assert solver.can_solve(problem) == True
    
    def test_solve_equation(self, solver):
        from cognitive_engine import ParsedProblem, ProblemType
        
        problem = ParsedProblem(
            original="2x + 5 = 15",
            problem_type=ProblemType.ALGEBRA,
            entities={},
            relationships=[],
            question="x",
            constraints=[],
        )
        
        result = solver.solve(problem)
        assert result.answer == 5


class TestCodeExecutionSolver:
    """Tests for code execution solver."""
    
    @pytest.fixture
    def solver(self):
        from cognitive_engine import CodeExecutionSolver
        return CodeExecutionSolver()
    
    def test_can_solve_with_executable(self, solver):
        from cognitive_engine import ParsedProblem, ProblemType
        
        problem = ParsedProblem(
            original="5 + 3",
            problem_type=ProblemType.ARITHMETIC,
            entities={"a": 5, "b": 3},
            relationships=["add"],
            question="result",
            constraints=[],
            executable_form="a = 5\nb = 3\nresult = a + b\nprint(result)",
        )
        
        assert solver.can_solve(problem) == True
    
    def test_execute_code(self, solver):
        from cognitive_engine import ParsedProblem, ProblemType
        
        problem = ParsedProblem(
            original="5 + 3",
            problem_type=ProblemType.ARITHMETIC,
            entities={},
            relationships=[],
            question="result",
            constraints=[],
            executable_form="result = 5 + 3\nprint(result)",
        )
        
        result = solver.solve(problem)
        assert result.answer == 8


class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_solve_function(self):
        from cognitive_engine import solve
        
        result = solve("5 + 3")
        assert result["answer"] == 8.0
    
    def test_explain_function(self):
        from cognitive_engine import explain
        
        explanation = explain("5 + 3")
        assert "8" in explanation
        assert "COGNITIVE ENGINE" in explanation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
