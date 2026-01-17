import logging
import asyncio
import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid
logger = logging.getLogger(__name__)


class ReasoningMode(str, Enum):
    """Types of reasoning approaches."""
    SEQUENTIAL = "sequential"       # Step-by-step linear reasoning
    TREE = "tree"                   # Tree of thought (multiple branches)
    SELF_CONSISTENCY = "self_consistency"  # Multiple samples, vote on answer
    DECOMPOSE = "decompose"         # Break into sub-problems
    VERIFY = "verify"               # Reason then verify
    DEBATE = "debate"               # Argue multiple perspectives


class ThinkingStep(str, Enum):
    """Steps in structured thinking."""
    UNDERSTAND = "understand"       # Understand the problem
    PLAN = "plan"                   # Plan the approach
    DECOMPOSE = "decompose"         # Break into parts
    ANALYZE = "analyze"             # Analyze each part
    SYNTHESIZE = "synthesize"       # Combine insights
    VERIFY = "verify"               # Verify solution
    REFINE = "refine"               # Improve solution


@dataclass
class ReasoningStep:
    """A single step in the reasoning chain."""
    step_id: str
    step_type: ThinkingStep
    content: str
    confidence: float = 0.0
    verified: bool = False
    children: List[str] = field(default_factory=list)  # For tree reasoning
    parent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningChain:
    """Complete reasoning chain for a task."""
    chain_id: str
    task: str
    steps: List[ReasoningStep] = field(default_factory=list)
    mode: ReasoningMode = ReasoningMode.SEQUENTIAL
    final_answer: str = ""
    confidence: float = 0.0
    verified: bool = False
    alternatives: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "task": self.task,
            "steps": [
                {
                    "step_id": s.step_id,
                    "type": s.step_type.value,
                    "content": s.content,
                    "confidence": s.confidence,
                    "verified": s.verified
                }
                for s in self.steps
            ],
            "mode": self.mode.value,
            "final_answer": self.final_answer,
            "confidence": self.confidence,
            "verified": self.verified,
            "alternatives": self.alternatives
        }


class ChainOfThoughtReasoner:
    """
    Advanced chain-of-thought reasoning for complex coding tasks.

    Enables local LLMs to match Claude/Cursor quality by:
    1. Breaking problems into manageable steps
    2. Explicit step-by-step reasoning
    3. Self-verification at each step
    4. Multi-path exploration
    5. Synthesis of best solution
    """

    def __init__(
        self,
        multi_llm_client=None,
        session=None
    ):
        self.multi_llm_client = multi_llm_client
        self.session = session

        # Reasoning configuration
        self.config = {
            "max_steps": 10,
            "max_depth": 5,  # For tree reasoning
            "verification_threshold": 0.7,
            "self_consistency_samples": 3,
            "timeout_seconds": 180
        }

        # Model preferences
        self.models = {
            "reasoning": "deepseek-r1:70b",
            "coding": "deepseek-coder:33b-instruct",
            "verification": "qwen2.5-coder:7b-instruct",
            "fast": "mistral:7b"
        }

        # Metrics
        self.metrics = {
            "chains_created": 0,
            "steps_total": 0,
            "verifications_passed": 0,
            "avg_chain_length": 0.0
        }

        logger.info("[COT-REASONER] Chain-of-thought reasoning initialized")

    async def reason(
        self,
        task: str,
        context: Optional[str] = None,
        mode: ReasoningMode = ReasoningMode.SEQUENTIAL,
        max_steps: Optional[int] = None
    ) -> ReasoningChain:
        """
        Perform chain-of-thought reasoning on a task.

        Args:
            task: The problem/task to reason about
            context: Additional context
            mode: Reasoning mode to use
            max_steps: Maximum reasoning steps

        Returns:
            Complete reasoning chain with solution
        """
        chain = ReasoningChain(
            chain_id=f"COT-{uuid.uuid4().hex[:12]}",
            task=task,
            mode=mode
        )

        self.metrics["chains_created"] += 1
        max_steps = max_steps or self.config["max_steps"]

        try:
            if mode == ReasoningMode.SEQUENTIAL:
                chain = await self._sequential_reasoning(chain, task, context)
            elif mode == ReasoningMode.TREE:
                chain = await self._tree_reasoning(chain, task, context)
            elif mode == ReasoningMode.SELF_CONSISTENCY:
                chain = await self._self_consistency_reasoning(chain, task, context)
            elif mode == ReasoningMode.DECOMPOSE:
                chain = await self._decomposition_reasoning(chain, task, context)
            elif mode == ReasoningMode.VERIFY:
                chain = await self._verify_reasoning(chain, task, context)
            else:
                chain = await self._sequential_reasoning(chain, task, context)

            # Update metrics
            self.metrics["steps_total"] += len(chain.steps)
            self._update_avg_chain_length(len(chain.steps))

        except Exception as e:
            logger.error(f"[COT-REASONER] Reasoning failed: {e}")
            chain.steps.append(ReasoningStep(
                step_id=f"ERROR-{uuid.uuid4().hex[:8]}",
                step_type=ThinkingStep.UNDERSTAND,
                content=f"Reasoning error: {str(e)}",
                confidence=0.0
            ))

        return chain

    async def _sequential_reasoning(
        self,
        chain: ReasoningChain,
        task: str,
        context: Optional[str]
    ) -> ReasoningChain:
        """Sequential step-by-step reasoning."""

        # Step 1: Understand
        understand = await self._think_step(
            ThinkingStep.UNDERSTAND,
            f"Understand this task:\n{task}\n\n{context or ''}",
            "What exactly is being asked? What are the requirements?"
        )
        chain.steps.append(understand)

        # Step 2: Plan
        plan = await self._think_step(
            ThinkingStep.PLAN,
            f"Task: {task}\nUnderstanding: {understand.content}",
            "What approach should we take? What are the steps?"
        )
        chain.steps.append(plan)

        # Step 3: Decompose
        decompose = await self._think_step(
            ThinkingStep.DECOMPOSE,
            f"Task: {task}\nPlan: {plan.content}",
            "Break this into smaller sub-problems. What are the components?"
        )
        chain.steps.append(decompose)

        # Step 4: Analyze
        analyze = await self._think_step(
            ThinkingStep.ANALYZE,
            f"Task: {task}\nComponents: {decompose.content}",
            "Analyze each component. What are the challenges and solutions?"
        )
        chain.steps.append(analyze)

        # Step 5: Synthesize
        synthesize = await self._think_step(
            ThinkingStep.SYNTHESIZE,
            f"Task: {task}\nAnalysis: {analyze.content}",
            "Combine all insights into a complete solution."
        )
        chain.steps.append(synthesize)

        # Step 6: Verify
        verify = await self._think_step(
            ThinkingStep.VERIFY,
            f"Solution: {synthesize.content}\nOriginal Task: {task}",
            "Verify the solution is correct and complete. Check for issues."
        )
        chain.steps.append(verify)

        # Set final answer
        chain.final_answer = synthesize.content
        chain.confidence = sum(s.confidence for s in chain.steps) / len(chain.steps)
        chain.verified = verify.verified

        return chain

    async def _tree_reasoning(
        self,
        chain: ReasoningChain,
        task: str,
        context: Optional[str]
    ) -> ReasoningChain:
        """Tree-of-thought reasoning with multiple branches."""

        # Root: Understand
        root = await self._think_step(
            ThinkingStep.UNDERSTAND,
            f"Task: {task}\n{context or ''}",
            "What is the core problem?"
        )
        chain.steps.append(root)

        # Generate multiple approaches (branches)
        approaches = await self._generate_approaches(task, root.content)

        best_approach = None
        best_score = 0.0

        for i, approach in enumerate(approaches[:3]):  # Limit to 3 branches
            branch_id = f"BRANCH-{i}"

            # Explore branch
            branch_step = await self._think_step(
                ThinkingStep.ANALYZE,
                f"Task: {task}\nApproach: {approach}",
                f"Analyze this approach. What are the pros/cons?"
            )
            branch_step.step_id = f"{branch_step.step_id}-{branch_id}"
            branch_step.parent = root.step_id
            chain.steps.append(branch_step)

            # Evaluate branch
            score = await self._evaluate_approach(task, approach, branch_step.content)

            if score > best_score:
                best_score = score
                best_approach = (approach, branch_step.content)

        if best_approach:
            # Synthesize best approach
            synthesize = await self._think_step(
                ThinkingStep.SYNTHESIZE,
                f"Task: {task}\nBest Approach: {best_approach[0]}\nAnalysis: {best_approach[1]}",
                "Implement the complete solution using this approach."
            )
            chain.steps.append(synthesize)
            chain.final_answer = synthesize.content
            chain.confidence = best_score

        return chain

    async def _self_consistency_reasoning(
        self,
        chain: ReasoningChain,
        task: str,
        context: Optional[str]
    ) -> ReasoningChain:
        """Generate multiple solutions and vote on the best."""

        solutions = []
        n_samples = self.config["self_consistency_samples"]

        for i in range(n_samples):
            # Generate solution with varied temperature
            temp = 0.3 + (i * 0.2)

            solution = await self._generate_solution(task, context, temp)
            solutions.append(solution)

            step = ReasoningStep(
                step_id=f"SAMPLE-{i}-{uuid.uuid4().hex[:8]}",
                step_type=ThinkingStep.SYNTHESIZE,
                content=solution,
                confidence=1.0 / n_samples
            )
            chain.steps.append(step)

        # Vote/select best solution
        best = await self._vote_on_solutions(task, solutions)

        chain.final_answer = best
        chain.confidence = 0.8  # Multiple samples increase confidence
        chain.alternatives = [s for s in solutions if s != best]

        return chain

    async def _decomposition_reasoning(
        self,
        chain: ReasoningChain,
        task: str,
        context: Optional[str]
    ) -> ReasoningChain:
        """Break problem into sub-problems, solve each, combine."""

        # Decompose
        decompose = await self._think_step(
            ThinkingStep.DECOMPOSE,
            f"Task: {task}\n{context or ''}",
            "Break this into independent sub-problems."
        )
        chain.steps.append(decompose)

        # Parse sub-problems
        sub_problems = self._parse_sub_problems(decompose.content)

        sub_solutions = []
        for i, sub in enumerate(sub_problems[:5]):  # Limit sub-problems
            solution = await self._think_step(
                ThinkingStep.ANALYZE,
                f"Sub-problem: {sub}\nMain task context: {task}",
                "Solve this specific sub-problem."
            )
            solution.step_id = f"SUB-{i}-{solution.step_id}"
            chain.steps.append(solution)
            sub_solutions.append(solution.content)

        # Combine solutions
        combine = await self._think_step(
            ThinkingStep.SYNTHESIZE,
            f"Main Task: {task}\nSub-solutions:\n" + "\n".join(f"- {s}" for s in sub_solutions),
            "Combine all sub-solutions into a complete solution."
        )
        chain.steps.append(combine)

        chain.final_answer = combine.content
        chain.confidence = sum(s.confidence for s in chain.steps) / len(chain.steps)

        return chain

    async def _verify_reasoning(
        self,
        chain: ReasoningChain,
        task: str,
        context: Optional[str]
    ) -> ReasoningChain:
        """Generate solution then verify step-by-step."""

        # Generate initial solution
        solution = await self._think_step(
            ThinkingStep.SYNTHESIZE,
            f"Task: {task}\n{context or ''}",
            "Generate a complete solution."
        )
        chain.steps.append(solution)

        # Verify each aspect
        verifications = [
            ("correctness", "Does this correctly solve the problem?"),
            ("completeness", "Is the solution complete?"),
            ("edge_cases", "Are edge cases handled?"),
            ("efficiency", "Is it reasonably efficient?")
        ]

        all_verified = True
        for aspect, question in verifications:
            verify = await self._think_step(
                ThinkingStep.VERIFY,
                f"Solution: {solution.content}\nTask: {task}",
                f"Verify {aspect}: {question}"
            )
            verify.step_id = f"VERIFY-{aspect}-{verify.step_id}"
            chain.steps.append(verify)

            if not verify.verified or verify.confidence < self.config["verification_threshold"]:
                all_verified = False

        # Refine if issues found
        if not all_verified:
            refine = await self._think_step(
                ThinkingStep.REFINE,
                f"Original solution: {solution.content}\nIssues found during verification",
                "Fix any issues and improve the solution."
            )
            chain.steps.append(refine)
            chain.final_answer = refine.content
        else:
            chain.final_answer = solution.content

        chain.verified = all_verified
        chain.confidence = sum(s.confidence for s in chain.steps) / len(chain.steps)

        return chain

    async def _think_step(
        self,
        step_type: ThinkingStep,
        context: str,
        instruction: str
    ) -> ReasoningStep:
        """Execute a single thinking step."""
        step = ReasoningStep(
            step_id=f"{step_type.value}-{uuid.uuid4().hex[:8]}",
            step_type=step_type
        )

        prompt = self._build_thinking_prompt(step_type, context, instruction)

        if not self.multi_llm_client:
            step.content = f"[{step_type.value}] {instruction}"
            step.confidence = 0.5
            return step

        try:
            response = await self.multi_llm_client.generate(
                prompt=prompt,
                model=self.models.get("reasoning", self.models["coding"]),
                temperature=0.3,
                max_tokens=2000
            )

            content = response.get("response", "")
            step.content = self._clean_response(content)
            step.confidence = self._assess_step_confidence(step.content)
            step.verified = step.confidence >= self.config["verification_threshold"]

        except Exception as e:
            logger.warning(f"[COT-REASONER] Think step failed: {e}")
            step.content = f"Error in {step_type.value}: {str(e)}"
            step.confidence = 0.0

        return step

    def _build_thinking_prompt(
        self,
        step_type: ThinkingStep,
        context: str,
        instruction: str
    ) -> str:
        """Build prompt for thinking step."""
        step_prompts = {
            ThinkingStep.UNDERSTAND: "You are analyzing a problem to fully understand it.",
            ThinkingStep.PLAN: "You are creating a plan to solve a problem.",
            ThinkingStep.DECOMPOSE: "You are breaking a problem into smaller parts.",
            ThinkingStep.ANALYZE: "You are analyzing a specific aspect of a problem.",
            ThinkingStep.SYNTHESIZE: "You are combining insights into a solution.",
            ThinkingStep.VERIFY: "You are verifying if a solution is correct.",
            ThinkingStep.REFINE: "You are improving and refining a solution."
        }

        system_context = step_prompts.get(step_type, "You are reasoning carefully.")

        return f"""{system_context}

CONTEXT:
{context}

INSTRUCTION:
{instruction}

Think step-by-step and provide a clear, detailed response. Be thorough but concise.

RESPONSE:
"""

    def _clean_response(self, response: str) -> str:
        """Clean and extract core content from response."""
        # Remove common prefixes
        prefixes = ["RESPONSE:", "Here's", "I'll", "Let me"]
        for prefix in prefixes:
            if response.strip().startswith(prefix):
                response = response.strip()[len(prefix):].strip()

        return response.strip()

    def _assess_step_confidence(self, content: str) -> float:
        """Assess confidence of a reasoning step."""
        confidence = 0.5  # Base confidence

        # Indicators of good reasoning
        if len(content) > 50:
            confidence += 0.1
        if any(word in content.lower() for word in ["because", "therefore", "since"]):
            confidence += 0.1
        if "1." in content or "- " in content:  # Has structure
            confidence += 0.1
        if "however" in content.lower() or "but" in content.lower():  # Considers alternatives
            confidence += 0.1

        # Indicators of uncertainty
        uncertain_words = ["maybe", "might", "possibly", "uncertain", "not sure"]
        if any(word in content.lower() for word in uncertain_words):
            confidence -= 0.15

        return max(0.0, min(1.0, confidence))

    async def _generate_approaches(self, task: str, understanding: str) -> List[str]:
        """Generate multiple approaches to a problem."""
        prompt = f"""Task: {task}

Understanding: {understanding}

Generate 3 different approaches to solve this problem. For each approach:
1. Brief description
2. Key advantage
3. Potential challenge

Format:
APPROACH 1: [description]
APPROACH 2: [description]
APPROACH 3: [description]"""

        if not self.multi_llm_client:
            return ["Direct implementation", "Modular approach", "Iterative refinement"]

        try:
            response = await self.multi_llm_client.generate(
                prompt=prompt,
                model=self.models["reasoning"],
                temperature=0.5,
                max_tokens=1500
            )

            content = response.get("response", "")
            approaches = re.findall(r'APPROACH \d+:\s*(.+?)(?=APPROACH \d+:|$)', content, re.DOTALL)

            if approaches:
                return [a.strip() for a in approaches]

        except Exception as e:
            logger.warning(f"[COT-REASONER] Approach generation failed: {e}")

        return ["Standard implementation approach"]

    async def _evaluate_approach(self, task: str, approach: str, analysis: str) -> float:
        """Evaluate the quality of an approach."""
        prompt = f"""Task: {task}
Approach: {approach}
Analysis: {analysis}

Rate this approach from 0.0 to 1.0 based on:
- Feasibility (can it be implemented?)
- Correctness (will it solve the problem?)
- Efficiency (is it reasonably efficient?)
- Maintainability (is the result maintainable?)

Provide just a single number between 0.0 and 1.0:"""

        if not self.multi_llm_client:
            return 0.7

        try:
            response = await self.multi_llm_client.generate(
                prompt=prompt,
                model=self.models["fast"],
                temperature=0.1,
                max_tokens=50
            )

            content = response.get("response", "")
            # Extract number
            match = re.search(r'(\d+\.?\d*)', content)
            if match:
                score = float(match.group(1))
                return max(0.0, min(1.0, score))

        except Exception:
            pass

        return 0.5

    async def _generate_solution(
        self,
        task: str,
        context: Optional[str],
        temperature: float
    ) -> str:
        """Generate a solution with specific temperature."""
        prompt = f"""Task: {task}

{f"Context: {context}" if context else ""}

Provide a complete, well-reasoned solution:"""

        if not self.multi_llm_client:
            return f"Solution for: {task}"

        try:
            response = await self.multi_llm_client.generate(
                prompt=prompt,
                model=self.models["coding"],
                temperature=temperature,
                max_tokens=3000
            )

            return response.get("response", "")

        except Exception as e:
            return f"Error generating solution: {e}"

    async def _vote_on_solutions(self, task: str, solutions: List[str]) -> str:
        """Select the best solution from multiple candidates."""
        if not solutions:
            return ""
        if len(solutions) == 1:
            return solutions[0]

        # Build voting prompt
        solutions_text = "\n\n".join(f"SOLUTION {i+1}:\n{s[:1000]}" for i, s in enumerate(solutions))

        prompt = f"""Task: {task}

Here are {len(solutions)} candidate solutions:

{solutions_text}

Which solution is best? Consider:
- Correctness
- Completeness
- Code quality

Answer with just the number (1, 2, or 3):"""

        if not self.multi_llm_client:
            return solutions[0]

        try:
            response = await self.multi_llm_client.generate(
                prompt=prompt,
                model=self.models["fast"],
                temperature=0.1,
                max_tokens=50
            )

            content = response.get("response", "")
            match = re.search(r'(\d+)', content)
            if match:
                idx = int(match.group(1)) - 1
                if 0 <= idx < len(solutions):
                    return solutions[idx]

        except Exception:
            pass

        return solutions[0]

    def _parse_sub_problems(self, decomposition: str) -> List[str]:
        """Parse sub-problems from decomposition text."""
        # Look for numbered or bulleted items
        items = re.findall(r'(?:^\d+\.|^-|^\*)\s*(.+)$', decomposition, re.MULTILINE)

        if items:
            return [item.strip() for item in items if item.strip()]

        # Fallback: split by newlines
        lines = [l.strip() for l in decomposition.split("\n") if l.strip()]
        return lines[:5]  # Limit to 5

    def _update_avg_chain_length(self, new_length: int):
        """Update average chain length metric."""
        total = self.metrics["chains_created"]
        if total > 1:
            self.metrics["avg_chain_length"] = (
                (self.metrics["avg_chain_length"] * (total - 1) + new_length) / total
            )
        else:
            self.metrics["avg_chain_length"] = float(new_length)

    async def reason_for_code(
        self,
        task: str,
        language: str,
        context: Optional[str] = None,
        complexity: str = "medium"
    ) -> ReasoningChain:
        """
        Specialized reasoning for code generation tasks.

        Optimized for producing high-quality code by:
        1. Understanding the coding task
        2. Planning the implementation
        3. Considering language-specific best practices
        4. Handling edge cases
        5. Ensuring code quality
        """
        coding_context = f"""
PROGRAMMING LANGUAGE: {language}
TASK COMPLEXITY: {complexity}

{f"EXISTING CODE/CONTEXT:{chr(10)}{context}" if context else ""}

TASK: {task}
"""

        # Choose mode based on complexity
        mode_map = {
            "simple": ReasoningMode.SEQUENTIAL,
            "medium": ReasoningMode.VERIFY,
            "complex": ReasoningMode.TREE,
            "very_complex": ReasoningMode.DECOMPOSE
        }

        mode = mode_map.get(complexity, ReasoningMode.VERIFY)

        return await self.reason(task, coding_context, mode)

    def get_metrics(self) -> Dict[str, Any]:
        """Get reasoner metrics."""
        return {
            **self.metrics,
            "verification_threshold": self.config["verification_threshold"],
            "max_steps": self.config["max_steps"]
        }
