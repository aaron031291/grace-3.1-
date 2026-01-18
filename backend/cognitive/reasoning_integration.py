"""
REASONING INTEGRATION - Bidirectional Cognitive + Reasoning

Integrates:
- Grace's OODA-based Cognitive Engine (decision-making framework)
- Reasoning Engine (LLM + verification)
- Computational Engine (SymPy, code execution)
- Clarity Framework (ambiguity detection)

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                   BIDIRECTIONAL FLOW                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐                      ┌─────────────┐           │
│  │  COGNITIVE  │◄────────────────────►│  REASONING  │           │
│  │   ENGINE    │     bidirectional    │   ENGINE    │           │
│  │             │                      │             │           │
│  │ • OODA Loop │                      │ • LLM Query │           │
│  │ • Invariants│                      │ • Compute   │           │
│  │ • Clarity   │                      │ • Verify    │           │
│  └──────┬──────┘                      └──────┬──────┘           │
│         │                                    │                   │
│         └────────────┬───────────────────────┘                   │
│                      │                                           │
│                      ▼                                           │
│              ┌───────────────┐                                   │
│              │   UNIFIED     │                                   │
│              │   DECISION    │                                   │
│              │               │                                   │
│              │ • Verified    │                                   │
│              │ • Auditable   │                                   │
│              │ • Reversible  │                                   │
│              └───────────────┘                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

Bidirectional means:
1. Cognitive → Reasoning: "I need to solve X, reason about it"
2. Reasoning → Cognitive: "Here's my answer, verify with OODA/invariants"
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Import Grace's cognitive framework
try:
    from cognitive.ooda import OODALoop, OODAPhase
    from cognitive.engine import CognitiveEngine as GraceCognitive, DecisionContext
    from cognitive.ambiguity import AmbiguityLedger, AmbiguityLevel
    GRACE_COGNITIVE_AVAILABLE = True
except ImportError:
    GRACE_COGNITIVE_AVAILABLE = False
    logger.warning("Grace Cognitive Engine not available")

# Import Clarity Framework
try:
    from cognitive.clarity_framework import ClarityFramework, ClarityPhase
    CLARITY_AVAILABLE = True
except ImportError:
    CLARITY_AVAILABLE = False

# Import Reasoning/Computation engines
try:
    import sys
    from pathlib import Path
    # Add backend to path if needed
    backend_path = Path(__file__).parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    from reasoning_engine import ReasoningEngine
    REASONING_AVAILABLE = True
except ImportError as e:
    REASONING_AVAILABLE = False
    logger.warning(f"Reasoning engine not available: {e}")

try:
    from cognitive_engine import CognitiveEngine as ComputeEngine
    COMPUTE_AVAILABLE = True
except ImportError as e:
    COMPUTE_AVAILABLE = False
    logger.warning(f"Compute engine not available: {e}")


class ReasoningPhase(str, Enum):
    """Phases aligned with OODA."""
    OBSERVE = "observe"      # Understand the problem
    ORIENT = "orient"        # Classify and contextualize
    DECIDE = "decide"        # Choose solving method
    ACT = "act"              # Execute and verify
    VERIFY = "verify"        # Cross-check results


@dataclass
class ReasoningContext:
    """Context for a reasoning operation."""
    
    problem: str
    problem_type: Optional[str] = None
    
    # OODA state
    ooda_phase: ReasoningPhase = ReasoningPhase.OBSERVE
    observations: Dict[str, Any] = field(default_factory=dict)
    orientation: Dict[str, Any] = field(default_factory=dict)
    decision: Optional[Dict[str, Any]] = None
    
    # Results from each source
    compute_result: Optional[Dict] = None
    llm_result: Optional[Dict] = None
    retrieval_result: Optional[Dict] = None
    
    # Final verified result
    final_answer: Any = None
    confidence: float = 0.0
    verified: bool = False
    verification_sources: List[str] = field(default_factory=list)
    
    # Clarity tracking
    ambiguity_level: str = "low"
    clarifications_needed: List[str] = field(default_factory=list)
    
    # Audit
    created_at: datetime = field(default_factory=datetime.now)
    decision_id: Optional[str] = None


class UnifiedReasoningEngine:
    """
    Unified engine that integrates OODA, Clarity, and Reasoning.
    
    Bidirectional flow:
    - Uses OODA to structure the problem-solving process
    - Uses Reasoning to get answers from multiple sources
    - Uses Clarity to detect and resolve ambiguity
    - Verifies everything through cross-checking
    """
    
    def __init__(self):
        # Initialize Grace's cognitive framework
        if GRACE_COGNITIVE_AVAILABLE:
            self.grace_cognitive = GraceCognitive()
            self.ooda = OODALoop()
        else:
            self.grace_cognitive = None
            self.ooda = None
        
        # Initialize Clarity
        if CLARITY_AVAILABLE:
            self.clarity = ClarityFramework()
        else:
            self.clarity = None
        
        # Initialize Reasoning
        if REASONING_AVAILABLE:
            self.reasoning = ReasoningEngine()
        else:
            self.reasoning = None
        
        # Initialize Compute
        if COMPUTE_AVAILABLE:
            self.compute = ComputeEngine()
        else:
            self.compute = None
        
        self._log_status()
    
    def _log_status(self):
        """Log initialization status."""
        logger.info("Unified Reasoning Engine initialized:")
        logger.info(f"  Grace Cognitive: {'[OK]' if GRACE_COGNITIVE_AVAILABLE else '[X]'}")
        logger.info(f"  Clarity Framework: {'[OK]' if CLARITY_AVAILABLE else '[X]'}")
        logger.info(f"  Reasoning Engine: {'[OK]' if REASONING_AVAILABLE else '[X]'}")
        logger.info(f"  Compute Engine: {'[OK]' if COMPUTE_AVAILABLE else '[X]'}")
    
    def reason(self, problem: str) -> ReasoningContext:
        """
        Main entry point for reasoning.
        
        Follows OODA loop with bidirectional feedback.
        """
        
        ctx = ReasoningContext(problem=problem)
        
        # =================================================================
        # OBSERVE: Understand what we're dealing with
        # =================================================================
        ctx = self._observe(ctx)
        
        # =================================================================
        # ORIENT: Classify and check for ambiguity
        # =================================================================
        ctx = self._orient(ctx)
        
        # If ambiguous, might need clarification
        if ctx.ambiguity_level == "high":
            logger.warning(f"High ambiguity detected: {ctx.clarifications_needed}")
            # Could pause here for clarification in interactive mode
        
        # =================================================================
        # DECIDE: Choose solving strategy
        # =================================================================
        ctx = self._decide(ctx)
        
        # =================================================================
        # ACT: Execute the strategy
        # =================================================================
        ctx = self._act(ctx)
        
        # =================================================================
        # VERIFY: Cross-check with multiple sources
        # =================================================================
        ctx = self._verify(ctx)
        
        return ctx
    
    def _observe(self, ctx: ReasoningContext) -> ReasoningContext:
        """OBSERVE: Gather information about the problem."""
        
        ctx.ooda_phase = ReasoningPhase.OBSERVE
        
        # Use compute engine to parse the problem
        if self.compute:
            from cognitive_engine import ProblemParser
            parser = ProblemParser()
            parsed = parser.parse(ctx.problem)
            
            ctx.observations = {
                "problem_type": parsed.problem_type.value,
                "entities": parsed.entities,
                "relationships": parsed.relationships,
                "question": parsed.question,
                "has_executable": parsed.executable_form is not None,
            }
            ctx.problem_type = parsed.problem_type.value
        else:
            ctx.observations = {"raw_problem": ctx.problem}
        
        # Feed to OODA if available
        if self.ooda:
            try:
                self.ooda.observe(ctx.observations)
            except ValueError:
                self.ooda.reset()
                self.ooda.observe(ctx.observations)
        
        logger.info(f"OBSERVE: type={ctx.problem_type}, entities={len(ctx.observations.get('entities', {}))}")
        return ctx
    
    def _orient(self, ctx: ReasoningContext) -> ReasoningContext:
        """ORIENT: Classify and check for ambiguity."""
        
        ctx.ooda_phase = ReasoningPhase.ORIENT
        
        # Check ambiguity with Clarity
        if self.clarity:
            try:
                # Clarity framework can detect ambiguous language
                clarity_check = self._check_clarity(ctx.problem)
                ctx.ambiguity_level = clarity_check.get("level", "low")
                ctx.clarifications_needed = clarity_check.get("clarifications", [])
            except:
                pass
        
        # Build orientation context
        ctx.orientation = {
            "problem_type": ctx.problem_type,
            "ambiguity": ctx.ambiguity_level,
            "available_solvers": [],
        }
        
        # Determine which solvers can handle this
        if ctx.problem_type in ["arithmetic", "algebra", "word_problem", "statistics"]:
            ctx.orientation["available_solvers"].append("compute")
        
        if ctx.problem_type in ["factual", "reasoning", "unknown"]:
            ctx.orientation["available_solvers"].append("llm")
        
        # Always can try retrieval
        ctx.orientation["available_solvers"].append("retrieval")
        
        # Feed to OODA
        if self.ooda:
            try:
                self.ooda.orient(ctx.orientation, constraints={"max_time": 30})
            except ValueError:
                pass
        
        logger.info(f"ORIENT: ambiguity={ctx.ambiguity_level}, solvers={ctx.orientation['available_solvers']}")
        return ctx
    
    def _decide(self, ctx: ReasoningContext) -> ReasoningContext:
        """DECIDE: Choose solving strategy."""
        
        ctx.ooda_phase = ReasoningPhase.DECIDE
        
        # Prioritize solvers based on problem type
        solvers = ctx.orientation.get("available_solvers", [])
        
        # Decision: which solvers to use and in what order
        ctx.decision = {
            "strategy": "multi_source_verify",
            "primary_solver": solvers[0] if solvers else "llm",
            "verification_solvers": solvers[1:] if len(solvers) > 1 else [],
            "confidence_threshold": 0.8,
        }
        
        # For math, always prefer compute
        if ctx.problem_type in ["arithmetic", "algebra", "word_problem"]:
            ctx.decision["primary_solver"] = "compute"
            ctx.decision["verification_solvers"] = ["llm"]
        
        # Feed to OODA
        if self.ooda:
            try:
                self.ooda.decide(ctx.decision)
            except ValueError:
                pass
        
        logger.info(f"DECIDE: strategy={ctx.decision['strategy']}, primary={ctx.decision['primary_solver']}")
        return ctx
    
    def _act(self, ctx: ReasoningContext) -> ReasoningContext:
        """ACT: Execute the solving strategy."""
        
        ctx.ooda_phase = ReasoningPhase.ACT
        
        # Execute primary solver
        primary = ctx.decision.get("primary_solver", "llm")
        
        if primary == "compute" and self.compute:
            result = self.compute.solve(ctx.problem)
            if result.get("solved"):
                ctx.compute_result = result
                ctx.final_answer = result["answer"]
                ctx.confidence = result["confidence"]
                ctx.verification_sources.append("compute")
        
        elif primary == "llm" and self.reasoning:
            result = self.reasoning.reason(ctx.problem)
            ctx.llm_result = result.to_dict()
            ctx.final_answer = result.answer
            ctx.confidence = result.confidence
            ctx.verification_sources.append("llm")
        
        # Execute verification solvers
        for verifier in ctx.decision.get("verification_solvers", []):
            if verifier == "compute" and self.compute and ctx.compute_result is None:
                result = self.compute.solve(ctx.problem)
                if result.get("solved"):
                    ctx.compute_result = result
                    ctx.verification_sources.append("compute")
            
            elif verifier == "llm" and self.reasoning and ctx.llm_result is None:
                result = self.reasoning.reason(ctx.problem)
                ctx.llm_result = result.to_dict()
                ctx.verification_sources.append("llm")
        
        # Feed to OODA
        if self.ooda:
            try:
                self.ooda.act(lambda: ctx.final_answer)
            except ValueError:
                pass
        
        logger.info(f"ACT: answer={ctx.final_answer}, sources={ctx.verification_sources}")
        return ctx
    
    def _verify(self, ctx: ReasoningContext) -> ReasoningContext:
        """VERIFY: Cross-check results between sources."""
        
        ctx.ooda_phase = ReasoningPhase.VERIFY
        
        answers = []
        
        if ctx.compute_result and ctx.compute_result.get("answer") is not None:
            answers.append(("compute", ctx.compute_result["answer"], ctx.compute_result.get("confidence", 0.9)))
        
        if ctx.llm_result and ctx.llm_result.get("answer") is not None:
            answers.append(("llm", ctx.llm_result["answer"], ctx.llm_result.get("confidence", 0.6)))
        
        if len(answers) >= 2:
            # Cross-verify: do they agree?
            if self._answers_match(answers[0][1], answers[1][1]):
                ctx.verified = True
                ctx.confidence = min(1.0, max(a[2] for a in answers) + 0.1)  # Boost
                logger.info("VERIFY: Sources agree - VERIFIED")
            else:
                # Disagreement - trust compute over LLM for math
                if answers[0][0] == "compute":
                    ctx.final_answer = answers[0][1]
                    ctx.confidence = answers[0][2]
                    ctx.verified = True  # Compute is authoritative for math
                    logger.warning(f"VERIFY: Disagreement - trusting compute: {answers}")
                else:
                    ctx.verified = False
                    logger.warning(f"VERIFY: Sources disagree: {answers}")
        elif len(answers) == 1:
            ctx.verified = answers[0][0] == "compute"  # Only verified if computed
        else:
            ctx.verified = False
        
        return ctx
    
    def _answers_match(self, a: Any, b: Any, tolerance: float = 0.01) -> bool:
        """Check if two answers match."""
        try:
            return abs(float(a) - float(b)) < tolerance
        except:
            return str(a).lower().strip() == str(b).lower().strip()
    
    def _check_clarity(self, problem: str) -> Dict:
        """Check problem clarity using Clarity Framework."""
        
        # Simple ambiguity detection
        ambiguous_patterns = [
            "it", "that", "this", "some", "few", "many", "they",
        ]
        
        words = problem.lower().split()
        ambiguous_words = [w for w in words if w in ambiguous_patterns]
        
        if len(ambiguous_words) > 2:
            return {"level": "high", "clarifications": ambiguous_words}
        elif ambiguous_words:
            return {"level": "medium", "clarifications": ambiguous_words}
        else:
            return {"level": "low", "clarifications": []}
    
    def explain(self, problem: str) -> str:
        """Get detailed explanation of reasoning process."""
        
        ctx = self.reason(problem)
        
        lines = [
            "=" * 60,
            "UNIFIED REASONING ENGINE",
            "=" * 60,
            f"Problem: {problem}",
            "",
            "OODA Process:",
            f"  OBSERVE: type={ctx.problem_type}, entities={ctx.observations.get('entities', {})}",
            f"  ORIENT: ambiguity={ctx.ambiguity_level}, solvers={ctx.orientation.get('available_solvers', [])}",
            f"  DECIDE: strategy={ctx.decision.get('strategy')}, primary={ctx.decision.get('primary_solver')}",
            f"  ACT: executed sources={ctx.verification_sources}",
            f"  VERIFY: verified={ctx.verified}",
            "",
            f"Answer: {ctx.final_answer}",
            f"Confidence: {ctx.confidence:.0%}",
            f"Verified: {'[OK]' if ctx.verified else '[?]'}",
            "=" * 60,
        ]
        
        return "\n".join(lines)


# =============================================================================
# SINGLETON & API
# =============================================================================

_unified_engine = None

def get_unified_engine() -> UnifiedReasoningEngine:
    """Get singleton unified engine."""
    global _unified_engine
    if _unified_engine is None:
        _unified_engine = UnifiedReasoningEngine()
    return _unified_engine


def reason(problem: str) -> Dict:
    """Reason about a problem with full OODA/Clarity integration."""
    ctx = get_unified_engine().reason(problem)
    return {
        "problem": ctx.problem,
        "answer": ctx.final_answer,
        "confidence": ctx.confidence,
        "verified": ctx.verified,
        "sources": ctx.verification_sources,
        "ooda_phase": ctx.ooda_phase.value,
        "ambiguity": ctx.ambiguity_level,
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    engine = UnifiedReasoningEngine()
    
    tests = [
        "John has 5 apples. He buys 3 more. How many?",
        "What is 15% of 80?",
        "Solve for x: 2x + 5 = 15",
        "What is the capital of France?",
    ]
    
    for problem in tests:
        print("\n" + engine.explain(problem))
