"""
GRACE REASONING INTEGRATION

The key insight: Grace doesn't need to BE a reasoning LLM.
Grace ORCHESTRATES reasoning using:

┌─────────────────────────────────────────────────────────────┐
│                    GRACE REASONING STACK                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Layer 4: Natural Language Understanding (existing Grace)   │
│           ↓ Parse intent, extract problem                   │
│                                                              │
│  Layer 3: Problem Classification                             │
│           ↓ Route to appropriate solver                     │
│                                                              │
│  Layer 2: Computational Solvers                              │
│           • SymPy (symbolic math)                           │
│           • Code Execution (Python)                         │
│           • Logic Engine (Z3)                               │
│           • Knowledge Retrieval (Qdrant)                    │
│                                                              │
│  Layer 1: Verification & Explanation                         │
│           ↑ Verify answer, generate explanation             │
│                                                              │
└─────────────────────────────────────────────────────────────┘

This is HYBRID AI:
- Neural (Grace) for understanding
- Symbolic (solvers) for computation
- Retrieval for knowledge
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import components
try:
    from cognitive_engine import CognitiveEngine, solve as cognitive_solve
    COGNITIVE_AVAILABLE = True
except ImportError:
    COGNITIVE_AVAILABLE = False
    logger.warning("Cognitive engine not available")

try:
    from reasoning_knowledge import ReasoningKnowledgeBase
    RETRIEVAL_AVAILABLE = True
except ImportError:
    RETRIEVAL_AVAILABLE = False
    logger.warning("Reasoning knowledge base not available")


@dataclass
class ReasoningResult:
    """Result from Grace's reasoning system."""
    
    success: bool
    answer: Any
    confidence: float
    method: str  # "cognitive", "retrieval", "hybrid", "fallback"
    explanation: str
    steps: List[str]
    verified: bool
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "answer": self.answer,
            "confidence": self.confidence,
            "method": self.method,
            "explanation": self.explanation,
            "steps": self.steps,
            "verified": self.verified,
        }


class GraceReasoning:
    """
    Grace's unified reasoning interface.
    
    Strategy:
    1. Try cognitive engine (direct computation) FIRST
    2. If low confidence, augment with retrieval
    3. Cross-verify between methods
    4. Return best answer with explanation
    """
    
    def __init__(self):
        self.cognitive = CognitiveEngine() if COGNITIVE_AVAILABLE else None
        self.retrieval = ReasoningKnowledgeBase() if RETRIEVAL_AVAILABLE else None
        
        logger.info(f"Grace Reasoning initialized:")
        logger.info(f"  Cognitive Engine: {'✓' if self.cognitive else '✗'}")
        logger.info(f"  Retrieval System: {'✓' if self.retrieval else '✗'}")
    
    def reason(self, problem: str, prefer_method: str = "auto") -> ReasoningResult:
        """
        Solve a reasoning problem.
        
        Args:
            problem: The problem to solve
            prefer_method: "cognitive", "retrieval", "hybrid", or "auto"
            
        Returns:
            ReasoningResult with answer and explanation
        """
        
        results = []
        
        # Try cognitive engine
        if self.cognitive and prefer_method in ["cognitive", "hybrid", "auto"]:
            cognitive_result = self._try_cognitive(problem)
            if cognitive_result:
                results.append(cognitive_result)
        
        # Try retrieval
        if self.retrieval and prefer_method in ["retrieval", "hybrid", "auto"]:
            retrieval_result = self._try_retrieval(problem)
            if retrieval_result:
                results.append(retrieval_result)
        
        # Select best result
        if not results:
            return ReasoningResult(
                success=False,
                answer=None,
                confidence=0.0,
                method="none",
                explanation="No reasoning method available",
                steps=[],
                verified=False,
            )
        
        # Sort by confidence and verification
        results.sort(key=lambda r: (r.verified, r.confidence), reverse=True)
        best = results[0]
        
        # If hybrid mode and both available, try to cross-verify
        if len(results) >= 2 and prefer_method in ["hybrid", "auto"]:
            best = self._cross_verify(results)
        
        return best
    
    def _try_cognitive(self, problem: str) -> Optional[ReasoningResult]:
        """Try cognitive engine."""
        
        try:
            result = self.cognitive.solve(problem)
            
            if result["solved"]:
                return ReasoningResult(
                    success=True,
                    answer=result["answer"],
                    confidence=result["confidence"],
                    method="cognitive",
                    explanation=f"Computed using {result['method']}",
                    steps=result["steps"],
                    verified=result["verified"],
                )
        except Exception as e:
            logger.warning(f"Cognitive engine error: {e}")
        
        return None
    
    def _try_retrieval(self, problem: str) -> Optional[ReasoningResult]:
        """Try retrieval-based reasoning."""
        
        try:
            result = self.retrieval.solve_by_retrieval(problem)
            
            if result.get("solved"):
                return ReasoningResult(
                    success=True,
                    answer=result["predicted_answer"],
                    confidence=result["confidence"],
                    method="retrieval",
                    explanation=f"Found similar problem in knowledge base",
                    steps=["Retrieved from: " + 
                           result["similar_problems"][0]["source"] 
                           if result.get("similar_problems") else "knowledge base"],
                    verified=False,  # Retrieval can't verify
                )
        except Exception as e:
            logger.warning(f"Retrieval error: {e}")
        
        return None
    
    def _cross_verify(self, results: List[ReasoningResult]) -> ReasoningResult:
        """Cross-verify between methods."""
        
        # If both agree, boost confidence
        answers = [r.answer for r in results]
        
        def close_enough(a, b, tolerance=0.01):
            try:
                return abs(float(a) - float(b)) < tolerance
            except:
                return str(a) == str(b)
        
        if len(answers) >= 2 and close_enough(answers[0], answers[1]):
            # Both methods agree!
            best = results[0]
            return ReasoningResult(
                success=True,
                answer=best.answer,
                confidence=min(best.confidence + 0.1, 1.0),  # Boost confidence
                method="hybrid",
                explanation="Verified by both computation and retrieval",
                steps=best.steps + ["Cross-verified with knowledge base"],
                verified=True,
            )
        
        # Prefer cognitive (actual computation) over retrieval
        for r in results:
            if r.method == "cognitive" and r.verified:
                return r
        
        return results[0]
    
    def explain(self, problem: str) -> str:
        """Get a detailed explanation."""
        
        result = self.reason(problem)
        
        lines = [
            "=" * 60,
            "GRACE REASONING ANALYSIS",
            "=" * 60,
            f"\nProblem: {problem}",
            f"\nMethod: {result.method}",
            f"Answer: {result.answer}",
            f"Confidence: {result.confidence:.0%}",
            f"Verified: {'✓' if result.verified else '✗'}",
            "\nSteps:",
        ]
        
        for step in result.steps:
            lines.append(f"  → {step}")
        
        lines.extend([
            f"\nExplanation: {result.explanation}",
            "=" * 60,
        ])
        
        return "\n".join(lines)


# =============================================================================
# BENCHMARK INTEGRATION
# =============================================================================

class ReasoningBenchmark:
    """
    Benchmark Grace's reasoning against standard datasets.
    
    Uses the same datasets as LLM benchmarks, but Grace solves them
    using computation, not neural approximation.
    """
    
    def __init__(self):
        self.reasoner = GraceReasoning()
    
    def run_gsm8k(self, problems: List[Dict], max_problems: int = 100) -> Dict:
        """Run GSM8K benchmark."""
        
        import re
        
        correct = 0
        results = []
        
        for i, problem in enumerate(problems[:max_problems]):
            question = problem.get("question", "")
            expected_answer = problem.get("answer", "")
            
            # Extract expected number
            match = re.search(r'####\s*(-?\d+\.?\d*)', expected_answer)
            expected = float(match.group(1)) if match else None
            
            # Grace solves it
            result = self.reasoner.reason(question)
            predicted = result.answer
            
            # Compare
            try:
                is_correct = abs(float(predicted) - float(expected)) < 0.01
            except:
                is_correct = str(predicted) == str(expected)
            
            if is_correct:
                correct += 1
            
            results.append({
                "problem": question[:100],
                "expected": expected,
                "predicted": predicted,
                "correct": is_correct,
                "method": result.method,
                "confidence": result.confidence,
            })
            
            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i+1}/{max_problems} | Accuracy: {correct/(i+1)*100:.1f}%")
        
        return {
            "benchmark": "gsm8k",
            "total": len(results),
            "correct": correct,
            "accuracy": correct / len(results) * 100,
            "results": results[:10],  # Sample
        }


# =============================================================================
# SINGLETON & API
# =============================================================================

_reasoner = None

def get_reasoner() -> GraceReasoning:
    """Get singleton reasoner."""
    global _reasoner
    if _reasoner is None:
        _reasoner = GraceReasoning()
    return _reasoner


def reason(problem: str) -> Dict:
    """Solve a reasoning problem."""
    return get_reasoner().reason(problem).to_dict()


def explain(problem: str) -> str:
    """Get explanation."""
    return get_reasoner().explain(problem)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Demo Grace reasoning."""
    
    reasoner = GraceReasoning()
    
    test_problems = [
        "John has 5 apples. He buys 3 more. How many apples does he have?",
        "What is 15% of 80?",
        "Solve for x: 2x + 5 = 15",
        "A store sells 12 boxes with 8 items each. What's the total?",
        "If Sarah has 100 dollars and spends 35 dollars, how much is left?",
        "Find the average of 10, 20, 30, 40, 50",
    ]
    
    print("\n" + "=" * 60)
    print("GRACE REASONING DEMO")
    print("=" * 60)
    
    for problem in test_problems:
        print(f"\n📝 {problem}")
        
        result = reasoner.reason(problem)
        
        status = "✅" if result.success else "❌"
        print(f"{status} Answer: {result.answer}")
        print(f"   Method: {result.method} | Confidence: {result.confidence:.0%}")
    
    print("\n" + "=" * 60)
    print("DETAILED EXPLANATION EXAMPLE")
    print(reasoner.explain("John has 5 apples. He buys 3 more. How many?"))


if __name__ == "__main__":
    main()
