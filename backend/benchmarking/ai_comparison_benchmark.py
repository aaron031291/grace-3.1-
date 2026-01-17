"""
AI Comparison Benchmark System

Tests Grace's output (Coding Agent & Self-Healing) against:
- Claude (Anthropic)
- Gemini (Google)
- Cursor (Cursor AI)
- ChatGPT (OpenAI)
- DeepSeek

Compares on:
- Code Quality
- Correctness
- Speed
- Resource Usage
- Best Practices
- Error Handling
"""

import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    """AI providers to benchmark."""
    GRACE_CODING_AGENT = "grace_coding_agent"
    GRACE_SELF_HEALING = "grace_self_healing"
    CLAUDE = "claude"
    GEMINI = "gemini"
    CURSOR = "cursor"
    CHATGPT = "chatgpt"
    DEEPSEEK = "deepseek"


@dataclass
class BenchmarkTask:
    """A task to benchmark across all AI systems."""
    task_id: str
    task_type: str  # "code_generation", "code_fix", "code_review", "explanation"
    prompt: str
    context: Dict[str, Any] = field(default_factory=dict)
    expected_output: Optional[str] = None
    test_cases: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AIResponse:
    """Response from an AI system."""
    provider: AIProvider
    task_id: str
    response: str
    duration_ms: float
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityScore:
    """Quality score for an AI response."""
    provider: AIProvider
    task_id: str
    correctness: float = 0.0  # 0-1
    code_quality: float = 0.0  # 0-1
    best_practices: float = 0.0  # 0-1
    error_handling: float = 0.0  # 0-1
    documentation: float = 0.0  # 0-1
    performance: float = 0.0  # 0-1
    overall_score: float = 0.0  # 0-1
    feedback: str = ""


@dataclass
class BenchmarkResult:
    """Complete benchmark result."""
    task: BenchmarkTask
    responses: Dict[AIProvider, AIResponse] = field(default_factory=dict)
    quality_scores: Dict[AIProvider, QualityScore] = field(default_factory=dict)
    rankings: Dict[str, List[AIProvider]] = field(default_factory=dict)
    summary: Dict[str, Any] = field(default_factory=dict)


class AIComparisonBenchmark:
    """
    Benchmark Grace against other AI systems.
    
    Tests:
    1. Code Generation
    2. Code Fixing
    3. Code Review
    4. Explanation Quality
    5. Best Practices
    """
    
    def __init__(
        self,
        session=None,
        coding_agent=None,
        self_healing=None,
        enable_claude: bool = True,
        enable_gemini: bool = True,
        enable_cursor: bool = True,
        enable_chatgpt: bool = True,
        enable_deepseek: bool = True
    ):
        """Initialize benchmark system."""
        self.session = session
        self.coding_agent = coding_agent
        self.self_healing = self_healing
        
        # Provider flags
        self.enable_claude = enable_claude
        self.enable_gemini = enable_gemini
        self.enable_cursor = enable_cursor
        self.enable_chatgpt = enable_chatgpt
        self.enable_deepseek = enable_deepseek
        
        # Results storage
        self.results: List[BenchmarkResult] = []
        
        logger.info("[BENCHMARK] AI Comparison Benchmark initialized")
    
    # ==================== TASK EXECUTION ====================
    
    async def run_benchmark(
        self,
        task: BenchmarkTask
    ) -> BenchmarkResult:
        """
        Run benchmark task across all AI systems.
        
        Returns:
            BenchmarkResult with all responses and scores
        """
        logger.info(f"[BENCHMARK] Running task: {task.task_id}")
        
        result = BenchmarkResult(task=task)
        
        # Run all providers in parallel
        tasks = []
        
        # Grace Coding Agent
        if self.coding_agent:
            tasks.append(self._run_grace_coding_agent(task))
        
        # Grace Self-Healing
        if self.self_healing:
            tasks.append(self._run_grace_self_healing(task))
        
        # External providers
        if self.enable_claude:
            tasks.append(self._run_claude(task))
        
        if self.enable_gemini:
            tasks.append(self._run_gemini(task))
        
        if self.enable_cursor:
            tasks.append(self._run_cursor(task))
        
        if self.enable_chatgpt:
            tasks.append(self._run_chatgpt(task))
        
        if self.enable_deepseek:
            tasks.append(self._run_deepseek(task))
        
        # Execute all in parallel
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process responses
        for response in responses:
            if isinstance(response, Exception):
                logger.error(f"[BENCHMARK] Error: {response}")
                continue
            
            if response:
                result.responses[response.provider] = response
        
        # Score all responses
        for provider, ai_response in result.responses.items():
            score = self._score_response(task, ai_response)
            result.quality_scores[provider] = score
        
        # Generate rankings
        result.rankings = self._generate_rankings(result)
        
        # Generate summary
        result.summary = self._generate_summary(result)
        
        self.results.append(result)
        
        return result
    
    # ==================== PROVIDER EXECUTION ====================
    
    async def _run_grace_coding_agent(
        self,
        task: BenchmarkTask
    ) -> Optional[AIResponse]:
        """Run task on Grace Coding Agent."""
        try:
            start_time = time.time()
            
            # Create coding task
            task_type_map = {
                "code_generation": "code_generation",
                "code_fix": "code_fix",
                "code_review": "code_review",
                "explanation": "code_explanation"
            }
            
            task_type = task_type_map.get(task.task_type, "code_generation")
            
            # Execute task
            coding_task = self.coding_agent.create_task(
                task_type=task_type,
                description=task.prompt,
                context=task.context
            )
            
            execution_result = self.coding_agent.execute_task(coding_task.task_id)
            
            duration_ms = (time.time() - start_time) * 1000
            
            response_text = ""
            if execution_result.get("success"):
                generation = execution_result.get("result", {}).get("generation")
                if generation:
                    response_text = generation.code_after if hasattr(generation, 'code_after') else str(generation)
            
            return AIResponse(
                provider=AIProvider.GRACE_CODING_AGENT,
                task_id=task.task_id,
                response=response_text,
                duration_ms=duration_ms,
                metadata={
                    "task_id": coding_task.task_id,
                    "success": execution_result.get("success", False),
                    "quality_level": execution_result.get("result", {}).get("generation", {}).get("quality_level", "unknown")
                }
            )
        except Exception as e:
            logger.error(f"[BENCHMARK] Grace Coding Agent error: {e}")
            return AIResponse(
                provider=AIProvider.GRACE_CODING_AGENT,
                task_id=task.task_id,
                response="",
                duration_ms=0,
                error=str(e)
            )
    
    async def _run_grace_self_healing(
        self,
        task: BenchmarkTask
    ) -> Optional[AIResponse]:
        """Run task on Grace Self-Healing."""
        try:
            start_time = time.time()
            
            # For code fixing tasks, use self-healing
            if task.task_type == "code_fix":
                # Create a test file with the broken code
                test_file = Path("benchmark_test_file.py")
                test_file.write_text(task.context.get("broken_code", ""))
                
                # Run healing
                healing_result = self.self_healing.run_monitoring_cycle()
                
                # Read fixed file
                fixed_code = test_file.read_text() if test_file.exists() else ""
                
                duration_ms = (time.time() - start_time) * 1000
                
                return AIResponse(
                    provider=AIProvider.GRACE_SELF_HEALING,
                    task_id=task.task_id,
                    response=fixed_code,
                    duration_ms=duration_ms,
                    metadata={
                        "health_status": healing_result.get("health_status", "unknown"),
                        "actions_executed": healing_result.get("actions_executed", 0)
                    }
                )
            else:
                return None
        except Exception as e:
            logger.error(f"[BENCHMARK] Grace Self-Healing error: {e}")
            return AIResponse(
                provider=AIProvider.GRACE_SELF_HEALING,
                task_id=task.task_id,
                response="",
                duration_ms=0,
                error=str(e)
            )
    
    async def _run_claude(
        self,
        task: BenchmarkTask
    ) -> Optional[AIResponse]:
        """Run task on Claude."""
        try:
            start_time = time.time()
            
            # TODO: Implement Claude API call
            # For now, return placeholder
            await asyncio.sleep(0.1)  # Simulate API call
            
            duration_ms = (time.time() - start_time) * 1000
            
            return AIResponse(
                provider=AIProvider.CLAUDE,
                task_id=task.task_id,
                response="[Claude response - API integration needed]",
                duration_ms=duration_ms,
                metadata={"api_integration": "pending"}
            )
        except Exception as e:
            logger.error(f"[BENCHMARK] Claude error: {e}")
            return None
    
    async def _run_gemini(
        self,
        task: BenchmarkTask
    ) -> Optional[AIResponse]:
        """Run task on Gemini."""
        try:
            start_time = time.time()
            
            # TODO: Implement Gemini API call
            await asyncio.sleep(0.1)
            
            duration_ms = (time.time() - start_time) * 1000
            
            return AIResponse(
                provider=AIProvider.GEMINI,
                task_id=task.task_id,
                response="[Gemini response - API integration needed]",
                duration_ms=duration_ms,
                metadata={"api_integration": "pending"}
            )
        except Exception as e:
            logger.error(f"[BENCHMARK] Gemini error: {e}")
            return None
    
    async def _run_cursor(
        self,
        task: BenchmarkTask
    ) -> Optional[AIResponse]:
        """Run task on Cursor."""
        try:
            start_time = time.time()
            
            # TODO: Implement Cursor API call
            await asyncio.sleep(0.1)
            
            duration_ms = (time.time() - start_time) * 1000
            
            return AIResponse(
                provider=AIProvider.CURSOR,
                task_id=task.task_id,
                response="[Cursor response - API integration needed]",
                duration_ms=duration_ms,
                metadata={"api_integration": "pending"}
            )
        except Exception as e:
            logger.error(f"[BENCHMARK] Cursor error: {e}")
            return None
    
    async def _run_chatgpt(
        self,
        task: BenchmarkTask
    ) -> Optional[AIResponse]:
        """Run task on ChatGPT."""
        try:
            start_time = time.time()
            
            # TODO: Implement ChatGPT API call
            await asyncio.sleep(0.1)
            
            duration_ms = (time.time() - start_time) * 1000
            
            return AIResponse(
                provider=AIProvider.CHATGPT,
                task_id=task.task_id,
                response="[ChatGPT response - API integration needed]",
                duration_ms=duration_ms,
                metadata={"api_integration": "pending"}
            )
        except Exception as e:
            logger.error(f"[BENCHMARK] ChatGPT error: {e}")
            return None
    
    async def _run_deepseek(
        self,
        task: BenchmarkTask
    ) -> Optional[AIResponse]:
        """Run task on DeepSeek."""
        try:
            start_time = time.time()
            
            # TODO: Implement DeepSeek API call
            await asyncio.sleep(0.1)
            
            duration_ms = (time.time() - start_time) * 1000
            
            return AIResponse(
                provider=AIProvider.DEEPSEEK,
                task_id=task.task_id,
                response="[DeepSeek response - API integration needed]",
                duration_ms=duration_ms,
                metadata={"api_integration": "pending"}
            )
        except Exception as e:
            logger.error(f"[BENCHMARK] DeepSeek error: {e}")
            return None
    
    # ==================== SCORING ====================
    
    def _score_response(
        self,
        task: BenchmarkTask,
        response: AIResponse
    ) -> QualityScore:
        """Score an AI response."""
        # Use LLM to score (or rule-based for now)
        # For now, use simple heuristics
        
        score = QualityScore(
            provider=response.provider,
            task_id=task.task_id
        )
        
        if response.error:
            return score  # All scores remain 0
        
        # Simple scoring (can be enhanced with LLM evaluation)
        response_text = response.response.lower()
        
        # Correctness (basic check)
        if task.expected_output:
            if task.expected_output.lower() in response_text:
                score.correctness = 0.8
            else:
                score.correctness = 0.3
        
        # Code quality indicators
        quality_indicators = [
            "def ", "class ", "try:", "except", "async def",
            "type hints", "docstring", "error handling"
        ]
        found_indicators = sum(1 for ind in quality_indicators if ind in response_text)
        score.code_quality = min(1.0, found_indicators / len(quality_indicators))
        
        # Best practices
        best_practice_indicators = [
            "def ", "async", "type", "docstring", "error", "test"
        ]
        found_practices = sum(1 for ind in best_practice_indicators if ind in response_text)
        score.best_practices = min(1.0, found_practices / len(best_practice_indicators))
        
        # Error handling
        if "try:" in response_text or "except" in response_text:
            score.error_handling = 0.8
        else:
            score.error_handling = 0.3
        
        # Documentation
        if '"""' in response_text or "docstring" in response_text:
            score.documentation = 0.7
        else:
            score.documentation = 0.2
        
        # Performance (speed)
        if response.duration_ms < 1000:
            score.performance = 1.0
        elif response.duration_ms < 5000:
            score.performance = 0.7
        else:
            score.performance = 0.3
        
        # Overall score (weighted average)
        weights = {
            "correctness": 0.3,
            "code_quality": 0.25,
            "best_practices": 0.15,
            "error_handling": 0.15,
            "documentation": 0.1,
            "performance": 0.05
        }
        
        score.overall_score = (
            score.correctness * weights["correctness"] +
            score.code_quality * weights["code_quality"] +
            score.best_practices * weights["best_practices"] +
            score.error_handling * weights["error_handling"] +
            score.documentation * weights["documentation"] +
            score.performance * weights["performance"]
        )
        
        score.feedback = f"Overall score: {score.overall_score:.2f}"
        
        return score
    
    # ==================== RANKINGS ====================
    
    def _generate_rankings(
        self,
        result: BenchmarkResult
    ) -> Dict[str, List[AIProvider]]:
        """Generate rankings by metric."""
        rankings = {}
        
        # Overall ranking
        sorted_providers = sorted(
            result.quality_scores.items(),
            key=lambda x: x[1].overall_score,
            reverse=True
        )
        rankings["overall"] = [p[0] for p in sorted_providers]
        
        # By metric
        metrics = ["correctness", "code_quality", "best_practices", "error_handling", "documentation", "performance"]
        
        for metric in metrics:
            sorted_providers = sorted(
                result.quality_scores.items(),
                key=lambda x: getattr(x[1], metric),
                reverse=True
            )
            rankings[metric] = [p[0] for p in sorted_providers]
        
        return rankings
    
    # ==================== SUMMARY ====================
    
    def _generate_summary(
        self,
        result: BenchmarkResult
    ) -> Dict[str, Any]:
        """Generate summary statistics."""
        if not result.quality_scores:
            return {}
        
        # Average scores
        avg_scores = {}
        metrics = ["correctness", "code_quality", "best_practices", "error_handling", "documentation", "performance", "overall_score"]
        
        for metric in metrics:
            scores = [getattr(score, metric) for score in result.quality_scores.values()]
            avg_scores[metric] = sum(scores) / len(scores) if scores else 0.0
        
        # Best performer
        best_overall = max(
            result.quality_scores.items(),
            key=lambda x: x[1].overall_score
        )
        
        # Fastest
        fastest = min(
            result.responses.items(),
            key=lambda x: x[1].duration_ms
        )
        
        return {
            "average_scores": avg_scores,
            "best_performer": {
                "provider": best_overall[0].value,
                "score": best_overall[1].overall_score
            },
            "fastest": {
                "provider": fastest[0].value,
                "duration_ms": fastest[1].duration_ms
            },
            "total_providers": len(result.responses),
            "total_scored": len(result.quality_scores)
        }
    
    # ==================== REPORTING ====================
    
    def generate_report(
        self,
        output_path: Optional[Path] = None
    ) -> str:
        """Generate benchmark report."""
        if not self.results:
            return "No benchmark results available."
        
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("AI COMPARISON BENCHMARK REPORT")
        report_lines.append("=" * 80)
        report_lines.append()
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Total Tasks: {len(self.results)}")
        report_lines.append()
        
        # Overall summary
        report_lines.append("OVERALL SUMMARY")
        report_lines.append("-" * 80)
        
        # Aggregate scores across all tasks
        all_scores = {}
        for result in self.results:
            for provider, score in result.quality_scores.items():
                if provider not in all_scores:
                    all_scores[provider] = []
                all_scores[provider].append(score.overall_score)
        
        # Average scores per provider
        report_lines.append("\nAverage Overall Scores:")
        avg_scores = {
            provider: sum(scores) / len(scores)
            for provider, scores in all_scores.items()
        }
        
        sorted_providers = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
        for provider, avg_score in sorted_providers:
            report_lines.append(f"  {provider.value}: {avg_score:.3f}")
        
        report_lines.append()
        
        # Per-task details
        for i, result in enumerate(self.results, 1):
            report_lines.append(f"TASK {i}: {result.task.task_id}")
            report_lines.append("-" * 80)
            report_lines.append(f"Type: {result.task.task_type}")
            report_lines.append(f"Prompt: {result.task.prompt[:100]}...")
            report_lines.append()
            
            # Rankings
            if result.rankings:
                report_lines.append("Rankings:")
                for metric, ranking in result.rankings.items():
                    if metric == "overall":
                        report_lines.append(f"  Overall: {', '.join([p.value for p in ranking])}")
            
            report_lines.append()
            
            # Scores
            report_lines.append("Scores:")
            sorted_scores = sorted(
                result.quality_scores.items(),
                key=lambda x: x[1].overall_score,
                reverse=True
            )
            for provider, score in sorted_scores:
                report_lines.append(f"  {provider.value}:")
                report_lines.append(f"    Overall: {score.overall_score:.3f}")
                report_lines.append(f"    Correctness: {score.correctness:.3f}")
                report_lines.append(f"    Code Quality: {score.code_quality:.3f}")
                report_lines.append(f"    Best Practices: {score.best_practices:.3f}")
                report_lines.append(f"    Error Handling: {score.error_handling:.3f}")
                report_lines.append(f"    Documentation: {score.documentation:.3f}")
                report_lines.append(f"    Performance: {score.performance:.3f}")
            
            report_lines.append()
        
        report_lines.append("=" * 80)
        
        report_text = "\n".join(report_lines)
        
        # Save to file if path provided
        if output_path:
            output_path.write_text(report_text)
            logger.info(f"[BENCHMARK] Report saved to {output_path}")
        
        return report_text


def get_ai_comparison_benchmark(
    session=None,
    coding_agent=None,
    self_healing=None,
    **kwargs
) -> AIComparisonBenchmark:
    """Factory function to get AI Comparison Benchmark."""
    return AIComparisonBenchmark(
        session=session,
        coding_agent=coding_agent,
        self_healing=self_healing,
        **kwargs
    )
