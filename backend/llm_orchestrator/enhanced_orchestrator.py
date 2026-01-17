import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
from code_quality_optimizer import CodeQualityOptimizer, CodeGenerationResult, RefinementStrategy
from chain_of_thought import ChainOfThoughtReasoner, ReasoningChain, ReasoningMode
from competitive_benchmark import CompetitiveBenchmark, BenchmarkResult, QualityTier
from parliament_governance import ParliamentGovernance, ParliamentSession, DecisionType, GovernanceLevel
class QualityMode(str, Enum):
    logger = logging.getLogger(__name__)
    """Quality mode for code generation."""
    FAST = "fast"           # Minimal quality checks, speed priority
    STANDARD = "standard"   # Standard quality with basic refinement
    HIGH = "high"           # High quality with full refinement
    MAXIMUM = "maximum"     # Maximum quality with parliament governance


@dataclass
class EnhancedGenerationResult:
    """Complete result from enhanced code generation."""
    # Generated output
    code: str
    language: str
    task: str

    # Quality metrics
    quality_score: float
    quality_tier: QualityTier
    benchmark_result: Optional[BenchmarkResult] = None

    # Reasoning
    reasoning_chain: Optional[ReasoningChain] = None
    reasoning_summary: str = ""

    # Governance
    parliament_session: Optional[ParliamentSession] = None
    governance_approved: bool = False
    anti_hallucination_passed: bool = True

    # Performance
    generation_time_ms: float = 0.0
    refinement_iterations: int = 0
    models_used: List[str] = field(default_factory=list)

    # Metadata
    result_id: str = ""
    genesis_key_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "code": self.code,
            "language": self.language,
            "task": self.task[:200],
            "quality": {
                "score": self.quality_score,
                "tier": self.quality_tier.value,
                "benchmark": self.benchmark_result.to_dict() if self.benchmark_result else None
            },
            "reasoning": {
                "chain_id": self.reasoning_chain.chain_id if self.reasoning_chain else None,
                "summary": self.reasoning_summary,
                "steps": len(self.reasoning_chain.steps) if self.reasoning_chain else 0
            },
            "governance": {
                "session_id": self.parliament_session.session_id if self.parliament_session else None,
                "approved": self.governance_approved,
                "anti_hallucination": self.anti_hallucination_passed
            },
            "performance": {
                "time_ms": self.generation_time_ms,
                "iterations": self.refinement_iterations,
                "models": self.models_used
            },
            "genesis_key_id": self.genesis_key_id,
            "created_at": self.created_at.isoformat()
        }


class EnhancedOrchestrator:
    """
    Enhanced LLM Orchestrator for Claude/Cursor-level quality.

    Combines all quality systems into a unified interface that:
    1. Uses chain-of-thought reasoning for complex tasks
    2. Applies iterative refinement for quality improvement
    3. Benchmarks against competitive standards
    4. Uses parliament governance for critical decisions
    5. Tracks trust and KPIs for continuous improvement
    """

    def __init__(
        self,
        multi_llm_client=None,
        session=None,
        genesis_service=None
    ):
        self.multi_llm_client = multi_llm_client
        self.session = session
        self._genesis_service = genesis_service

        # Initialize quality systems
        self.quality_optimizer = CodeQualityOptimizer(
            multi_llm_client=multi_llm_client,
            session=session,
            genesis_service=genesis_service
        )

        self.cot_reasoner = ChainOfThoughtReasoner(
            multi_llm_client=multi_llm_client,
            session=session
        )

        self.benchmark = CompetitiveBenchmark(
            multi_llm_client=multi_llm_client,
            session=session
        )

        self.parliament = ParliamentGovernance(
            multi_llm_client=multi_llm_client,
            session=session,
            genesis_service=genesis_service
        )

        # Quality mode thresholds
        self.mode_config = {
            QualityMode.FAST: {
                "min_quality": 0.6,
                "max_iterations": 1,
                "use_reasoning": False,
                "use_parliament": False,
                "governance_level": GovernanceLevel.MINIMAL
            },
            QualityMode.STANDARD: {
                "min_quality": 0.75,
                "max_iterations": 2,
                "use_reasoning": True,
                "use_parliament": False,
                "governance_level": GovernanceLevel.STANDARD
            },
            QualityMode.HIGH: {
                "min_quality": 0.85,
                "max_iterations": 3,
                "use_reasoning": True,
                "use_parliament": False,
                "governance_level": GovernanceLevel.STRICT
            },
            QualityMode.MAXIMUM: {
                "min_quality": 0.90,
                "max_iterations": 4,
                "use_reasoning": True,
                "use_parliament": True,
                "governance_level": GovernanceLevel.CRITICAL
            }
        }

        # Metrics
        self.metrics = {
            "total_generations": 0,
            "quality_mode_usage": {mode.value: 0 for mode in QualityMode},
            "avg_quality_score": 0.0,
            "claude_level_rate": 0.0,  # Rate of ELITE tier
            "parliament_approval_rate": 0.0,
            "avg_generation_time_ms": 0.0
        }

        logger.info("[ENHANCED-ORCHESTRATOR] Initialized for Claude/Cursor-level quality")

    async def generate_code(
        self,
        task: str,
        language: str = "python",
        context: Optional[str] = None,
        requirements: Optional[List[str]] = None,
        quality_mode: QualityMode = QualityMode.STANDARD
    ) -> EnhancedGenerationResult:
        """
        Generate high-quality code using enhanced orchestration.

        Args:
            task: What to implement
            language: Programming language
            context: Additional context
            requirements: Specific requirements
            quality_mode: Quality level to target

        Returns:
            EnhancedGenerationResult with code and quality analysis
        """
        start_time = datetime.now()
        config = self.mode_config[quality_mode]

        self.metrics["total_generations"] += 1
        self.metrics["quality_mode_usage"][quality_mode.value] += 1

        result = EnhancedGenerationResult(
            result_id=f"GEN-{uuid.uuid4().hex[:12]}",
            code="",
            language=language,
            task=task,
            quality_score=0.0,
            quality_tier=QualityTier.NEEDS_WORK
        )

        try:
            # Step 1: Chain-of-Thought Reasoning (if enabled)
            if config["use_reasoning"]:
                logger.info("[ENHANCED-ORCHESTRATOR] Step 1: Chain-of-thought reasoning")
                complexity = self._assess_complexity(task)
                reasoning = await self.cot_reasoner.reason_for_code(
                    task=task,
                    language=language,
                    context=context,
                    complexity=complexity
                )
                result.reasoning_chain = reasoning
                result.reasoning_summary = reasoning.final_answer[:500] if reasoning.final_answer else ""

            # Step 2: Generate Code with Quality Optimizer
            logger.info("[ENHANCED-ORCHESTRATOR] Step 2: Code generation with quality optimization")

            # Determine refinement strategy based on mode
            if quality_mode == QualityMode.MAXIMUM:
                strategy = RefinementStrategy.BEST_OF_N
            elif quality_mode == QualityMode.HIGH:
                strategy = RefinementStrategy.CHAIN_OF_THOUGHT
            else:
                strategy = RefinementStrategy.SELF_CRITIQUE

            gen_result = await self.quality_optimizer.generate_code(
                task=task,
                context=context,
                language=language,
                requirements=requirements,
                strategy=strategy,
                min_quality=config["min_quality"]
            )

            result.code = gen_result.code
            result.quality_score = gen_result.quality_score.overall_score
            result.refinement_iterations = gen_result.total_iterations
            result.models_used = gen_result.models_used

            # Step 3: Benchmark against Claude/Cursor standards
            logger.info("[ENHANCED-ORCHESTRATOR] Step 3: Competitive benchmarking")
            benchmark_result = await self.benchmark.benchmark(
                code=result.code,
                task=task,
                language=language
            )
            result.benchmark_result = benchmark_result
            result.quality_tier = benchmark_result.quality_tier
            result.quality_score = benchmark_result.overall_score  # Use benchmark score

            # Step 4: Parliament Governance (if enabled and code passes threshold)
            if config["use_parliament"] and result.quality_score >= 0.7:
                logger.info("[ENHANCED-ORCHESTRATOR] Step 4: Parliament governance review")
                parliament_session = await self.parliament.code_quality_parliament(
                    code=result.code,
                    task=task,
                    language=language
                )
                result.parliament_session = parliament_session
                result.governance_approved = parliament_session.final_decision is not None
                result.anti_hallucination_passed = parliament_session.anti_hallucination_passed

                # If parliament rejects, attempt refinement
                if not result.governance_approved and result.refinement_iterations < config["max_iterations"]:
                    logger.info("[ENHANCED-ORCHESTRATOR] Parliament rejected, refining...")
                    # Extract feedback from parliament
                    feedback = self._extract_parliament_feedback(parliament_session)
                    refined = await self._refine_with_feedback(result.code, feedback, language)
                    if refined:
                        result.code = refined
                        result.refinement_iterations += 1

                        # Re-benchmark
                        benchmark_result = await self.benchmark.benchmark(
                            code=result.code,
                            task=task,
                            language=language
                        )
                        result.benchmark_result = benchmark_result
                        result.quality_tier = benchmark_result.quality_tier
                        result.quality_score = benchmark_result.overall_score

            # Calculate generation time
            result.generation_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Update metrics
            self._update_metrics(result)

            logger.info(
                f"[ENHANCED-ORCHESTRATOR] Complete: "
                f"tier={result.quality_tier.value}, "
                f"score={result.quality_score:.2f}, "
                f"time={result.generation_time_ms:.0f}ms"
            )

        except Exception as e:
            logger.error(f"[ENHANCED-ORCHESTRATOR] Generation failed: {e}")
            result.code = f"# Error during generation: {e}"
            result.quality_score = 0.0

        return result

    def _assess_complexity(self, task: str) -> str:
        """Assess task complexity for reasoning mode selection."""
        # Simple heuristics for complexity
        indicators = {
            "complex": ["algorithm", "optimize", "architecture", "design pattern", "multi-", "system"],
            "medium": ["implement", "create", "build", "function", "class", "api"],
            "simple": ["fix", "update", "add", "change", "modify", "return"]
        }

        task_lower = task.lower()

        for complexity, keywords in indicators.items():
            if any(kw in task_lower for kw in keywords):
                if complexity == "complex":
                    return "complex" if len(task) > 200 else "medium"
                return complexity

        # Default based on length
        if len(task) > 300:
            return "complex"
        elif len(task) > 100:
            return "medium"
        return "simple"

    def _extract_parliament_feedback(self, session: ParliamentSession) -> str:
        """Extract actionable feedback from parliament session."""
        feedback_parts = []

        for vote in session.votes:
            if vote.reasoning:
                feedback_parts.append(vote.reasoning)
            if vote.amendments:
                feedback_parts.append(f"Suggested fix: {vote.amendments}")

        return "\n".join(feedback_parts[:3])  # Limit to top 3

    async def _refine_with_feedback(
        self,
        code: str,
        feedback: str,
        language: str
    ) -> Optional[str]:
        """Refine code based on parliament feedback."""
        if not self.multi_llm_client or not feedback:
            return None

        prompt = f"""Improve this {language} code based on feedback:

CURRENT CODE:
```{language}
{code}
```

FEEDBACK:
{feedback}

Fix all issues mentioned in the feedback. Provide only the improved code.

```{language}
"""

        try:
            response = await self.multi_llm_client.generate(
                prompt=prompt,
                model="deepseek-coder:33b-instruct",
                temperature=0.4,
                max_tokens=4000
            )

            # Extract code from response
            content = response.get("response", "")
            import re
            code_match = re.search(rf"```{language}\n(.*?)```", content, re.DOTALL)
            if code_match:
                return code_match.group(1).strip()

            return content.strip()

        except Exception as e:
            logger.warning(f"[ENHANCED-ORCHESTRATOR] Refinement failed: {e}")
            return None

    def _update_metrics(self, result: EnhancedGenerationResult):
        """Update orchestrator metrics."""
        n = self.metrics["total_generations"]

        # Update average quality score
        self.metrics["avg_quality_score"] = (
            (self.metrics["avg_quality_score"] * (n - 1) + result.quality_score) / n
        )

        # Update Claude-level rate (ELITE tier)
        if result.quality_tier == QualityTier.ELITE:
            self.metrics["claude_level_rate"] = (
                (self.metrics["claude_level_rate"] * (n - 1) + 1.0) / n
            )
        else:
            self.metrics["claude_level_rate"] = (
                (self.metrics["claude_level_rate"] * (n - 1)) / n
            )

        # Update parliament approval rate
        if result.parliament_session:
            if result.governance_approved:
                self.metrics["parliament_approval_rate"] = (
                    (self.metrics["parliament_approval_rate"] * (n - 1) + 1.0) / n
                )
            else:
                self.metrics["parliament_approval_rate"] = (
                    (self.metrics["parliament_approval_rate"] * (n - 1)) / n
                )

        # Update average generation time
        self.metrics["avg_generation_time_ms"] = (
            (self.metrics["avg_generation_time_ms"] * (n - 1) + result.generation_time_ms) / n
        )

    async def quick_generate(
        self,
        task: str,
        language: str = "python"
    ) -> str:
        """Quick generation without full quality pipeline."""
        result = await self.generate_code(
            task=task,
            language=language,
            quality_mode=QualityMode.FAST
        )
        return result.code

    async def premium_generate(
        self,
        task: str,
        language: str = "python",
        context: Optional[str] = None,
        requirements: Optional[List[str]] = None
    ) -> EnhancedGenerationResult:
        """Premium quality generation with full pipeline."""
        return await self.generate_code(
            task=task,
            language=language,
            context=context,
            requirements=requirements,
            quality_mode=QualityMode.MAXIMUM
        )

    async def verify_code(
        self,
        code: str,
        claims: Optional[List[str]] = None
    ) -> ParliamentSession:
        """Verify code for hallucinations and correctness."""
        return await self.parliament.anti_hallucination_review(
            content=code,
            claims=claims
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestrator metrics."""
        return {
            "orchestrator": self.metrics,
            "quality_optimizer": self.quality_optimizer.get_metrics(),
            "cot_reasoner": self.cot_reasoner.get_metrics(),
            "benchmark": self.benchmark.get_metrics(),
            "parliament": self.parliament.get_kpis(),
            "improvement_report": self.benchmark.get_improvement_report()
        }

    def get_competitive_status(self) -> Dict[str, Any]:
        """Get status vs Claude/Cursor competition."""
        improvement = self.benchmark.get_improvement_report()

        return {
            "current_avg_score": self.metrics["avg_quality_score"],
            "claude_level_rate": self.metrics["claude_level_rate"],
            "gaps": improvement.get("competitive_gaps", {}),
            "trend": improvement.get("trend", {}),
            "top_improvements_needed": improvement.get("top_gaps", []),
            "strengths": improvement.get("top_strengths", []),
            "recommendation": improvement.get("recommendation", "")
        }

    def get_governance_status(self) -> Dict[str, Any]:
        """Get governance and trust status."""
        return {
            "kpis": self.parliament.get_kpis(),
            "trust_report": self.parliament.get_trust_report(),
            "governance_summary": self.parliament.get_governance_summary()
        }


# Convenience functions for direct use
async def generate_high_quality_code(
    task: str,
    language: str = "python",
    context: Optional[str] = None,
    multi_llm_client=None
) -> EnhancedGenerationResult:
    """
    Convenience function for high-quality code generation.

    Uses the enhanced orchestrator with HIGH quality mode.
    """
    orchestrator = EnhancedOrchestrator(multi_llm_client=multi_llm_client)
    return await orchestrator.generate_code(
        task=task,
        language=language,
        context=context,
        quality_mode=QualityMode.HIGH
    )


async def generate_claude_level_code(
    task: str,
    language: str = "python",
    context: Optional[str] = None,
    requirements: Optional[List[str]] = None,
    multi_llm_client=None
) -> EnhancedGenerationResult:
    """
    Convenience function for Claude-level code generation.

    Uses the enhanced orchestrator with MAXIMUM quality mode
    including full parliament governance.
    """
    orchestrator = EnhancedOrchestrator(multi_llm_client=multi_llm_client)
    return await orchestrator.premium_generate(
        task=task,
        language=language,
        context=context,
        requirements=requirements
    )
