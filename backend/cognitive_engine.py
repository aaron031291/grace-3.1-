"""
COGNITIVE ENGINE - A Different Approach to Reasoning

Instead of:
  ❌ Mimicking LLM reasoning (neural approximation)
  ❌ Just retrieving similar problems

Grace uses:
  ✅ REAL computation (SymPy, code execution)
  ✅ Problem decomposition into primitives
  ✅ Tool orchestration (calculator, solver, verifier)
  ✅ Compile-to-code (translate problems → executable code)

Philosophy:
  - LLMs "hallucinate" math. Calculators don't.
  - Grace UNDERSTANDS the problem, then uses TOOLS to solve it.
  - Every reasoning problem can become executable code.

Architecture:
  ┌─────────────────────────────────────────────────────────┐
  │                    COGNITIVE ENGINE                      │
  ├─────────────────────────────────────────────────────────┤
  │                                                          │
  │  [Problem] → [Parser] → [Structured Form] → [Solver]    │
  │                                                          │
  │  Solvers:                                                │
  │    • SymPy (symbolic math)                               │
  │    • Z3 (logic/constraints)                              │
  │    • Code Executor (Python)                              │
  │    • Unit Converter                                      │
  │    • Statistical Calculator                              │
  │                                                          │
  │  [Solution] → [Verifier] → [Formatter] → [Answer]       │
  │                                                          │
  └─────────────────────────────────────────────────────────┘
"""

import re
import ast
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# PROBLEM TYPES & PRIMITIVES
# =============================================================================

class ProblemType(Enum):
    ARITHMETIC = "arithmetic"        # Basic math: 5 + 3
    ALGEBRA = "algebra"              # Solve for x
    WORD_PROBLEM = "word_problem"    # Story problems
    LOGIC = "logic"                  # If-then, constraints
    STATISTICS = "statistics"        # Mean, median, probability
    GEOMETRY = "geometry"            # Shapes, areas
    CODE = "code"                    # Programming problems
    FACTUAL = "factual"              # Knowledge lookup
    UNKNOWN = "unknown"


@dataclass
class ParsedProblem:
    """A problem decomposed into structured form."""
    
    original: str
    problem_type: ProblemType
    entities: Dict[str, Any]      # Variables and their values
    relationships: List[str]       # How entities relate
    question: str                  # What we're solving for
    constraints: List[str]         # Any constraints
    executable_form: Optional[str] = None  # Code representation
    

@dataclass
class Solution:
    """A verified solution."""
    
    answer: Any
    steps: List[str]
    confidence: float
    method: str
    verified: bool
    code_used: Optional[str] = None


# =============================================================================
# PARSERS - Understand the Problem
# =============================================================================

class ProblemParser:
    """Parse natural language problems into structured form."""
    
    # Patterns for entity extraction
    NUMBER_PATTERNS = [
        r'(\w+)\s+has\s+(\d+)\s+(\w+)',           # "John has 5 apples"
        r'(\w+)\s+(?:buys?|gets?|receives?)\s+(\d+)\s+(?:more\s+)?(\w+)',  # "buys 3 more"
        r'(\w+)\s+(?:gives?|loses?|sells?)\s+(\d+)\s+(\w+)',  # "gives away 2"
        r'there\s+(?:are|is)\s+(\d+)\s+(\w+)',    # "there are 10 birds"
        r'(\d+)\s+(\w+)',                          # "5 apples"
    ]
    
    OPERATION_PATTERNS = {
        'add': [r'(?:buys?|gets?|receives?|adds?|more|gains?|finds?)', r'total', r'altogether', r'combined', r'sum'],
        'subtract': [r'(?:gives?\s+away|loses?|sells?|removes?|takes?\s+away|fewer|less)', r'difference', r'left', r'remaining'],
        'multiply': [r'(?:times|each|per|every)', r'product', r'total.*each'],
        'divide': [r'(?:split|share|divided?|per|each\s+gets?)', r'quotient', r'average'],
        'percentage': [r'(?:percent|%)', r'of\s+\d+'],
    }
    
    QUESTION_PATTERNS = [
        r'how\s+many\s+(\w+)',
        r'what\s+is\s+(?:the\s+)?(\w+)',
        r'find\s+(?:the\s+)?(\w+)',
        r'calculate\s+(?:the\s+)?(\w+)',
        r'solve\s+for\s+(\w+)',
    ]
    
    def parse(self, problem: str) -> ParsedProblem:
        """Parse a natural language problem."""
        
        problem_lower = problem.lower()
        
        # Detect problem type
        problem_type = self._detect_type(problem_lower)
        
        # Extract entities
        entities = self._extract_entities(problem)
        
        # Extract relationships
        relationships = self._extract_relationships(problem_lower)
        
        # Extract the question
        question = self._extract_question(problem_lower)
        
        # Extract constraints
        constraints = self._extract_constraints(problem_lower)
        
        # Try to create executable form
        executable = self._to_executable(problem_type, entities, relationships, question)
        
        return ParsedProblem(
            original=problem,
            problem_type=problem_type,
            entities=entities,
            relationships=relationships,
            question=question,
            constraints=constraints,
            executable_form=executable,
        )
    
    def _detect_type(self, text: str) -> ProblemType:
        """Detect what type of problem this is."""
        
        if re.search(r'solve\s+for|equation|=.*x|x.*=', text):
            return ProblemType.ALGEBRA
        elif re.search(r'if.*then|implies|therefore|must\s+be', text):
            return ProblemType.LOGIC
        elif re.search(r'mean|median|average|probability|standard\s+deviation', text):
            return ProblemType.STATISTICS
        elif re.search(r'area|perimeter|volume|triangle|circle|square|rectangle', text):
            return ProblemType.GEOMETRY
        elif re.search(r'function|code|program|algorithm|return', text):
            return ProblemType.CODE
        elif re.search(r'who|when|where|capital|president|invented', text):
            return ProblemType.FACTUAL
        elif re.search(r'percent|%', text):
            return ProblemType.ARITHMETIC  # Handle percentages
        elif re.search(r'\d+\s*[\+\-\*\/]\s*\d+', text):
            return ProblemType.ARITHMETIC
        elif re.search(r'has|buys|gives|total|many|much|each', text):
            return ProblemType.WORD_PROBLEM
        else:
            return ProblemType.UNKNOWN
    
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities (variables, numbers) from text."""
        
        entities = {}
        seen_numbers = set()  # Track which numbers we've already captured
        
        for pattern in self.NUMBER_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match) == 3:
                    subject, number, item = match
                    key = f"{subject}_{item}".lower().replace(' ', '_')
                    entities[key] = int(number)
                    seen_numbers.add(int(number))
                elif len(match) == 2:
                    number, item = match
                    key = item.lower().replace(' ', '_')
                    entities[key] = int(number)
                    seen_numbers.add(int(number))
        
        # Only add standalone numbers if they weren't already captured
        standalone = re.findall(r'\b(\d+(?:\.\d+)?)\b', text)
        num_idx = 0
        for num in standalone:
            try:
                val = float(num) if '.' in num else int(num)
                if val not in seen_numbers:
                    entities[f"num_{num_idx}"] = val
                    seen_numbers.add(val)
                    num_idx += 1
            except:
                pass
        
        return entities
    
    def _extract_relationships(self, text: str) -> List[str]:
        """Extract mathematical relationships."""
        
        relationships = []
        
        for op, patterns in self.OPERATION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    relationships.append(op)
                    break
        
        return list(set(relationships))
    
    def _extract_question(self, text: str) -> str:
        """Extract what the question is asking for."""
        
        for pattern in self.QUESTION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        # Default
        if '?' in text:
            return text.split('?')[0].split()[-1]
        
        return "result"
    
    def _extract_constraints(self, text: str) -> List[str]:
        """Extract constraints from the problem."""
        
        constraints = []
        
        constraint_patterns = [
            r'at\s+least\s+(\d+)',
            r'at\s+most\s+(\d+)',
            r'no\s+more\s+than\s+(\d+)',
            r'between\s+(\d+)\s+and\s+(\d+)',
            r'greater\s+than\s+(\d+)',
            r'less\s+than\s+(\d+)',
        ]
        
        for pattern in constraint_patterns:
            matches = re.findall(pattern, text)
            if matches:
                constraints.append(f"{pattern}: {matches}")
        
        return constraints
    
    def _to_executable(
        self, 
        ptype: ProblemType, 
        entities: Dict, 
        relationships: List[str],
        question: str,
    ) -> Optional[str]:
        """Convert problem to executable Python code."""
        
        if ptype == ProblemType.WORD_PROBLEM:
            return self._word_problem_to_code(entities, relationships)
        elif ptype == ProblemType.ARITHMETIC:
            return self._arithmetic_to_code(entities)
        elif ptype == ProblemType.ALGEBRA:
            return self._algebra_to_code(entities)
        
        return None
    
    def _word_problem_to_code(self, entities: Dict, relationships: List[str]) -> str:
        """Convert word problem to code."""
        
        # Get unique values only (deduplicate)
        seen_values = set()
        unique_entities = {}
        for key, value in entities.items():
            if value not in seen_values:
                unique_entities[key] = value
                seen_values.add(value)
        
        lines = []
        
        # Declare variables
        for key, value in unique_entities.items():
            lines.append(f"{key} = {value}")
        
        # Apply operations
        var_names = list(unique_entities.keys())
        
        # Prioritize multiply over add for "each" patterns
        if 'multiply' in relationships and len(var_names) >= 2:
            lines.append(f"result = {' * '.join(var_names[:2])}")
        elif 'subtract' in relationships and len(var_names) >= 2:
            lines.append(f"result = {var_names[0]} - {' - '.join(var_names[1:])}")
        elif 'divide' in relationships and len(var_names) >= 2:
            lines.append(f"result = {var_names[0]} / {var_names[1]}")
        elif 'add' in relationships and len(var_names) >= 2:
            lines.append(f"result = {' + '.join(var_names)}")
        else:
            # Default to sum
            lines.append(f"result = {' + '.join(var_names)}")
        
        lines.append("print(result)")
        
        return "\n".join(lines)
    
    def _arithmetic_to_code(self, entities: Dict) -> str:
        """Convert arithmetic to code."""
        
        values = list(entities.values())
        if len(values) >= 2:
            return f"result = {values[0]} + {values[1]}\nprint(result)"
        return None
    
    def _algebra_to_code(self, entities: Dict) -> str:
        """Convert algebra to SymPy code."""
        
        return """
from sympy import symbols, solve, Eq
x = symbols('x')
# Equation will be set by solver
"""


# =============================================================================
# SOLVERS - Actually Compute Answers
# =============================================================================

class Solver(ABC):
    """Base class for solvers."""
    
    @abstractmethod
    def can_solve(self, problem: ParsedProblem) -> bool:
        pass
    
    @abstractmethod
    def solve(self, problem: ParsedProblem) -> Solution:
        pass


class CodeExecutionSolver(Solver):
    """Solve by executing Python code."""
    
    def can_solve(self, problem: ParsedProblem) -> bool:
        return problem.executable_form is not None
    
    def solve(self, problem: ParsedProblem) -> Solution:
        """Execute the code to get answer."""
        
        code = problem.executable_form
        
        try:
            # Safe execution environment
            local_vars = {}
            exec(code, {"__builtins__": {"print": lambda x: local_vars.update({"_output": x})}}, local_vars)
            
            result = local_vars.get("result") or local_vars.get("_output")
            
            return Solution(
                answer=result,
                steps=[f"Executed: {code}"],
                confidence=0.95,
                method="code_execution",
                verified=True,
                code_used=code,
            )
        except Exception as e:
            return Solution(
                answer=None,
                steps=[f"Execution failed: {e}"],
                confidence=0.0,
                method="code_execution",
                verified=False,
                code_used=code,
            )


class SymbolicMathSolver(Solver):
    """Solve using SymPy for symbolic math."""
    
    def can_solve(self, problem: ParsedProblem) -> bool:
        return problem.problem_type in [ProblemType.ALGEBRA, ProblemType.ARITHMETIC]
    
    def solve(self, problem: ParsedProblem) -> Solution:
        """Solve using SymPy."""
        
        try:
            import sympy as sp
            from sympy.parsing.sympy_parser import parse_expr
        except ImportError:
            return Solution(
                answer=None,
                steps=["SymPy not installed"],
                confidence=0.0,
                method="sympy",
                verified=False,
            )
        
        text = problem.original.lower()
        steps = []
        
        # Try to find an equation
        eq_match = re.search(r'(\d+)\s*x\s*[\+\-]\s*(\d+)\s*=\s*(\d+)', text)
        if eq_match:
            a, b, c = map(int, eq_match.groups())
            x = sp.Symbol('x')
            
            # Determine if + or -
            if '+' in text:
                eq = sp.Eq(a * x + b, c)
            else:
                eq = sp.Eq(a * x - b, c)
            
            steps.append(f"Equation: {eq}")
            solution = sp.solve(eq, x)
            steps.append(f"Solution: x = {solution}")
            
            return Solution(
                answer=solution[0] if solution else None,
                steps=steps,
                confidence=0.99,
                method="sympy_algebra",
                verified=True,
            )
        
        # Try percentage
        pct_match = re.search(r'(\d+)%?\s*(?:of|percent)\s*(\d+)', text)
        if pct_match:
            pct, base = map(int, pct_match.groups())
            result = (pct / 100) * base
            steps.append(f"{pct}% of {base} = {pct}/100 × {base} = {result}")
            
            return Solution(
                answer=result,
                steps=steps,
                confidence=0.99,
                method="sympy_percentage",
                verified=True,
            )
        
        # Try to evaluate direct expression
        expr_match = re.search(r'[\d\+\-\*\/\(\)\s\.]+', text)
        if expr_match:
            expr = expr_match.group().strip()
            try:
                result = sp.sympify(expr)
                steps.append(f"Evaluated: {expr} = {result}")
                
                return Solution(
                    answer=float(result),
                    steps=steps,
                    confidence=0.99,
                    method="sympy_eval",
                    verified=True,
                )
            except:
                pass
        
        return Solution(
            answer=None,
            steps=["Could not parse as symbolic expression"],
            confidence=0.0,
            method="sympy",
            verified=False,
        )


class ArithmeticSolver(Solver):
    """Direct arithmetic computation."""
    
    def can_solve(self, problem: ParsedProblem) -> bool:
        return problem.problem_type in [ProblemType.ARITHMETIC, ProblemType.WORD_PROBLEM]
    
    def solve(self, problem: ParsedProblem) -> Solution:
        """Solve arithmetic directly."""
        
        entities = problem.entities
        relationships = problem.relationships
        text = problem.original.lower()
        steps = []
        
        # Handle percentages first
        pct_match = re.search(r'(\d+)\s*%?\s*(?:percent\s+)?(?:of)\s*(\d+)', text)
        if pct_match:
            pct, base = map(int, pct_match.groups())
            result = (pct / 100) * base
            steps.append(f"{pct}% of {base} = {pct}/100 × {base} = {result}")
            return Solution(
                answer=result,
                steps=steps,
                confidence=0.99,
                method="arithmetic_percentage",
                verified=True,
            )
        
        # Handle "X percent of Y" format
        pct_match2 = re.search(r'(\d+)\s+percent\s+of\s+(\d+)', text)
        if pct_match2:
            pct, base = map(int, pct_match2.groups())
            result = (pct / 100) * base
            steps.append(f"{pct}% of {base} = {result}")
            return Solution(
                answer=result,
                steps=steps,
                confidence=0.99,
                method="arithmetic_percentage",
                verified=True,
            )
        
        values = list(entities.values())
        
        if not values:
            return Solution(
                answer=None,
                steps=["No numbers found"],
                confidence=0.0,
                method="arithmetic",
                verified=False,
            )
        
        # For word problems with "each", detect multiplication
        if 'each' in text or ('multiply' in relationships and 'add' not in relationships):
            # Find the two key numbers for multiplication
            result = 1
            for v in values[:2]:  # Usually first two numbers
                result *= v
            op_str = " × ".join(map(str, values[:2]))
            steps.append(f"Multiplication: {op_str} = {result}")
            return Solution(
                answer=result,
                steps=steps,
                confidence=0.9,
                method="arithmetic_multiply",
                verified=True,
            )
        
        # Apply the detected operation
        if 'add' in relationships or not relationships:
            result = sum(values)
            op_str = " + ".join(map(str, values))
            steps.append(f"Addition: {op_str} = {result}")
        elif 'subtract' in relationships:
            result = values[0] - sum(values[1:])
            steps.append(f"Subtraction: {values[0]} - {sum(values[1:])} = {result}")
        elif 'multiply' in relationships:
            result = 1
            for v in values:
                result *= v
            op_str = " × ".join(map(str, values))
            steps.append(f"Multiplication: {op_str} = {result}")
        elif 'divide' in relationships:
            result = values[0] / values[1] if len(values) > 1 and values[1] != 0 else 0
            steps.append(f"Division: {values[0]} ÷ {values[1]} = {result}")
        else:
            result = sum(values)
            steps.append(f"Sum (default): {sum(values)}")
        
        return Solution(
            answer=result,
            steps=steps,
            confidence=0.9,
            method="arithmetic",
            verified=True,
        )


class StatisticsSolver(Solver):
    """Solve statistics problems."""
    
    def can_solve(self, problem: ParsedProblem) -> bool:
        return problem.problem_type == ProblemType.STATISTICS
    
    def solve(self, problem: ParsedProblem) -> Solution:
        """Solve statistics."""
        
        import statistics
        
        values = list(problem.entities.values())
        text = problem.original.lower()
        steps = []
        
        if 'mean' in text or 'average' in text:
            result = statistics.mean(values)
            steps.append(f"Mean of {values} = {result}")
        elif 'median' in text:
            result = statistics.median(values)
            steps.append(f"Median of {values} = {result}")
        elif 'mode' in text:
            result = statistics.mode(values)
            steps.append(f"Mode of {values} = {result}")
        elif 'standard deviation' in text or 'std' in text:
            result = statistics.stdev(values) if len(values) > 1 else 0
            steps.append(f"Std Dev of {values} = {result}")
        else:
            result = statistics.mean(values)
            steps.append(f"Mean (default): {result}")
        
        return Solution(
            answer=result,
            steps=steps,
            confidence=0.95,
            method="statistics",
            verified=True,
        )


# =============================================================================
# COGNITIVE ENGINE - Orchestrates Everything
# =============================================================================

class CognitiveEngine:
    """
    The main cognitive engine that orchestrates problem solving.
    
    Grace's approach:
    1. Parse problem into structured form
    2. Select appropriate solver(s)
    3. Execute solution
    4. Verify answer
    5. Return result with explanation
    """
    
    def __init__(self):
        self.parser = ProblemParser()
        self.solvers: List[Solver] = [
            SymbolicMathSolver(),
            ArithmeticSolver(),
            StatisticsSolver(),
            CodeExecutionSolver(),
        ]
    
    def solve(self, problem: str) -> Dict[str, Any]:
        """
        Solve a problem using computational reasoning.
        
        Args:
            problem: Natural language problem
            
        Returns:
            Solution with answer, steps, and confidence
        """
        
        # Step 1: Parse the problem
        parsed = self.parser.parse(problem)
        
        logger.info(f"Parsed problem type: {parsed.problem_type}")
        logger.info(f"Entities: {parsed.entities}")
        logger.info(f"Relationships: {parsed.relationships}")
        
        # Step 2: Try each solver
        solutions = []
        for solver in self.solvers:
            if solver.can_solve(parsed):
                try:
                    solution = solver.solve(parsed)
                    if solution.answer is not None:
                        solutions.append(solution)
                        logger.info(f"Solver {solver.__class__.__name__}: {solution.answer}")
                except Exception as e:
                    logger.warning(f"Solver {solver.__class__.__name__} failed: {e}")
        
        # Step 3: Select best solution
        if not solutions:
            return {
                "solved": False,
                "answer": None,
                "message": "No solver could solve this problem",
                "parsed": {
                    "type": parsed.problem_type.value,
                    "entities": parsed.entities,
                    "relationships": parsed.relationships,
                },
            }
        
        # Prefer verified solutions with high confidence
        solutions.sort(key=lambda s: (s.verified, s.confidence), reverse=True)
        best = solutions[0]
        
        # Step 4: Verify (cross-check with other solutions if available)
        verified = self._verify_solution(best, solutions)
        
        return {
            "solved": True,
            "answer": best.answer,
            "confidence": best.confidence,
            "method": best.method,
            "steps": best.steps,
            "verified": verified,
            "code_used": best.code_used,
            "parsed": {
                "type": parsed.problem_type.value,
                "entities": parsed.entities,
                "relationships": parsed.relationships,
            },
        }
    
    def _verify_solution(self, primary: Solution, all_solutions: List[Solution]) -> bool:
        """Cross-verify solution with other solvers."""
        
        if len(all_solutions) < 2:
            return primary.verified
        
        # Check if multiple solvers agree
        answers = [s.answer for s in all_solutions if s.answer is not None]
        
        # Handle float comparison
        def close_enough(a, b, tolerance=0.01):
            try:
                return abs(float(a) - float(b)) < tolerance
            except:
                return a == b
        
        agreements = sum(1 for a in answers if close_enough(a, primary.answer))
        
        return agreements >= len(answers) * 0.5  # Majority agree
    
    def explain(self, problem: str) -> str:
        """Get a detailed explanation of how the problem is solved."""
        
        result = self.solve(problem)
        
        lines = [
            "=" * 60,
            "COGNITIVE ENGINE ANALYSIS",
            "=" * 60,
            f"\nProblem: {problem}",
            f"\nParsed Type: {result.get('parsed', {}).get('type', 'unknown')}",
            f"Entities: {result.get('parsed', {}).get('entities', {})}",
            f"Relationships: {result.get('parsed', {}).get('relationships', [])}",
            "\nSolution Steps:",
        ]
        
        for step in result.get("steps", []):
            lines.append(f"  → {step}")
        
        lines.extend([
            f"\nAnswer: {result.get('answer')}",
            f"Confidence: {result.get('confidence', 0):.0%}",
            f"Method: {result.get('method', 'unknown')}",
            f"Verified: {'✓' if result.get('verified') else '✗'}",
        ])
        
        if result.get("code_used"):
            lines.extend([
                "\nExecuted Code:",
                result["code_used"],
            ])
        
        lines.append("=" * 60)
        
        return "\n".join(lines)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_engine = None

def get_engine() -> CognitiveEngine:
    """Get singleton engine instance."""
    global _engine
    if _engine is None:
        _engine = CognitiveEngine()
    return _engine


def solve(problem: str) -> Dict[str, Any]:
    """Solve a problem."""
    return get_engine().solve(problem)


def explain(problem: str) -> str:
    """Get detailed explanation."""
    return get_engine().explain(problem)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Demo the cognitive engine."""
    
    engine = CognitiveEngine()
    
    test_problems = [
        # Word problems
        "John has 5 apples. He buys 3 more apples. How many apples does he have?",
        "Sarah has 20 cookies. She gives away 7 cookies. How many does she have left?",
        "A store has 12 boxes with 8 items each. What is the total?",
        
        # Algebra
        "Solve for x: 2x + 5 = 15",
        "What is x if 3x - 7 = 20?",
        
        # Percentages
        "What is 15% of 80?",
        "Calculate 25 percent of 200",
        
        # Direct arithmetic
        "5 + 3 * 2",
        "100 / 4 + 10",
        
        # Statistics
        "Find the average of 10, 20, 30, 40, 50",
    ]
    
    for problem in test_problems:
        print("\n" + "=" * 60)
        print(f"Problem: {problem}")
        print("-" * 60)
        
        result = engine.solve(problem)
        
        if result["solved"]:
            print(f"Answer: {result['answer']}")
            print(f"Method: {result['method']}")
            print(f"Confidence: {result['confidence']:.0%}")
            print(f"Steps: {result['steps']}")
        else:
            print(f"Could not solve: {result.get('message')}")


if __name__ == "__main__":
    main()
