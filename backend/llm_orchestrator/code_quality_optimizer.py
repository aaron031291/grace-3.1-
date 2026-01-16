"""
Code Quality Optimizer for Grace
=================================

Enables Grace to produce Claude/Cursor-quality code using only
local open-source LLMs (DeepSeek, Qwen, Llama, Mistral) via Ollama.

Key Strategies:
1. Multi-stage code generation with iterative refinement
2. Chain-of-thought reasoning for complex tasks
3. Self-critique and improvement loops
4. Code-aware quality scoring
5. Best-of-N sampling with quality ranking
6. Model ensemble for consensus
7. DeepSeek-specific optimizations

NO third-party API dependencies - all inference through Ollama.
"""

import logging
import asyncio
import json
import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class CodeQualityDimension(str, Enum):
    """Dimensions of code quality to optimize."""
    CORRECTNESS = "correctness"       # Does it work?
    COMPLETENESS = "completeness"     # Is it complete?
    READABILITY = "readability"       # Is it readable?
    EFFICIENCY = "efficiency"         # Is it performant?
    MAINTAINABILITY = "maintainability"  # Can it be maintained?
    SECURITY = "security"             # Is it secure?
    BEST_PRACTICES = "best_practices" # Follows conventions?
    DOCUMENTATION = "documentation"   # Well documented?


class RefinementStrategy(str, Enum):
    """Strategies for code refinement."""
    SELF_CRITIQUE = "self_critique"       # Model critiques own output
    MULTI_MODEL = "multi_model"           # Multiple models review
    ITERATIVE = "iterative"               # Multiple refinement passes
    BEST_OF_N = "best_of_n"               # Generate N, pick best
    CHAIN_OF_THOUGHT = "chain_of_thought" # Step-by-step reasoning
    DEBATE = "debate"                     # Models debate best approach


@dataclass
class QualityScore:
    """Quality assessment of generated code."""
    overall_score: float  # 0.0 - 1.0
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    issues_found: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""


@dataclass
class RefinementResult:
    """Result of a code refinement iteration."""
    iteration: int
    original_code: str
    refined_code: str
    quality_before: QualityScore
    quality_after: QualityScore
    changes_made: List[str] = field(default_factory=list)
    time_ms: float = 0.0


@dataclass
class CodeGenerationResult:
    """Final result of optimized code generation."""
    code: str
    quality_score: QualityScore
    reasoning_chain: List[str] = field(default_factory=list)
    refinement_history: List[RefinementResult] = field(default_factory=list)
    models_used: List[str] = field(default_factory=list)
    total_iterations: int = 0
    generation_time_ms: float = 0.0
    genesis_key_id: Optional[str] = None


class CodeQualityOptimizer:
    """
    Optimizes code generation quality to match Claude/Cursor level
    using only local open-source LLMs.

    Key capabilities:
    - Multi-stage generation with iterative refinement
    - Chain-of-thought reasoning for complex tasks
    - Self-critique and improvement loops
    - Code-aware quality scoring
    - Best-of-N sampling with ranking
    - Model ensemble for consensus
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

        # Quality thresholds
        self.quality_thresholds = {
            "minimum_acceptable": 0.7,
            "good": 0.8,
            "excellent": 0.9,
            "production_ready": 0.85
        }

        # Refinement config
        self.refinement_config = {
            "max_iterations": 3,
            "improvement_threshold": 0.05,  # Min improvement to continue
            "best_of_n_count": 3,
            "timeout_seconds": 120
        }

        # Model preferences for code tasks
        self.code_models = {
            "primary": "deepseek-coder:33b-instruct",
            "secondary": "qwen2.5-coder:32b-instruct",
            "validator": "deepseek-coder:6.7b-instruct",
            "reasoning": "deepseek-r1:70b",
            "fast": "qwen2.5-coder:7b-instruct"
        }

        # Metrics
        self.metrics = {
            "generations": 0,
            "refinements": 0,
            "quality_improvements": 0,
            "avg_final_quality": 0.0,
            "best_quality_achieved": 0.0
        }

        logger.info("[CODE-OPTIMIZER] Initialized for Claude/Cursor-level quality")

    async def generate_code(
        self,
        task: str,
        context: Optional[str] = None,
        language: str = "python",
        requirements: Optional[List[str]] = None,
        strategy: RefinementStrategy = RefinementStrategy.CHAIN_OF_THOUGHT,
        min_quality: float = 0.8
    ) -> CodeGenerationResult:
        """
        Generate high-quality code using optimized multi-stage process.

        Args:
            task: Description of what to implement
            context: Additional context (existing code, requirements)
            language: Target programming language
            requirements: Specific requirements to meet
            strategy: Refinement strategy to use
            min_quality: Minimum acceptable quality score

        Returns:
            CodeGenerationResult with optimized code
        """
        start_time = datetime.now()
        self.metrics["generations"] += 1

        result = CodeGenerationResult(
            code="",
            quality_score=QualityScore(overall_score=0.0),
            reasoning_chain=[],
            models_used=[]
        )

        try:
            # Stage 1: Chain-of-Thought Planning
            logger.info("[CODE-OPTIMIZER] Stage 1: Planning with chain-of-thought")
            plan = await self._plan_with_cot(task, context, language, requirements)
            result.reasoning_chain.append(f"Plan: {plan['summary']}")

            # Stage 2: Initial Generation
            logger.info("[CODE-OPTIMIZER] Stage 2: Initial code generation")
            initial_code = await self._generate_initial(
                task, plan, context, language, requirements
            )
            result.code = initial_code
            result.models_used.append(self.code_models["primary"])

            # Stage 3: Quality Assessment
            logger.info("[CODE-OPTIMIZER] Stage 3: Quality assessment")
            quality = await self._assess_quality(initial_code, task, language)
            result.quality_score = quality

            # Stage 4: Iterative Refinement (if needed)
            if quality.overall_score < min_quality:
                logger.info(f"[CODE-OPTIMIZER] Stage 4: Refinement needed (score: {quality.overall_score:.2f})")
                refined = await self._refine_code(
                    initial_code, task, quality, language, strategy, min_quality
                )
                result.code = refined.refined_code
                result.quality_score = refined.quality_after
                result.refinement_history.append(refined)
                result.total_iterations = refined.iteration
                self.metrics["refinements"] += refined.iteration

            # Stage 5: Final Validation
            logger.info("[CODE-OPTIMIZER] Stage 5: Final validation")
            final_quality = await self._final_validation(result.code, task, language)
            result.quality_score = final_quality

            # Update metrics
            self._update_metrics(result.quality_score.overall_score)

            # Calculate generation time
            result.generation_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(f"[CODE-OPTIMIZER] Complete: quality={result.quality_score.overall_score:.2f}, iterations={result.total_iterations}")

        except Exception as e:
            logger.error(f"[CODE-OPTIMIZER] Generation failed: {e}")
            result.reasoning_chain.append(f"Error: {str(e)}")

        return result

    async def _plan_with_cot(
        self,
        task: str,
        context: Optional[str],
        language: str,
        requirements: Optional[List[str]]
    ) -> Dict[str, Any]:
        """
        Create a detailed plan using chain-of-thought reasoning.
        This is key to matching Claude/Cursor quality.
        """
        cot_prompt = self._build_cot_planning_prompt(task, context, language, requirements)

        if not self.multi_llm_client:
            # Fallback to basic planning
            return {
                "summary": "Direct implementation",
                "steps": [task],
                "considerations": [],
                "approach": "standard"
            }

        try:
            response = await self.multi_llm_client.generate(
                prompt=cot_prompt,
                model=self.code_models.get("reasoning", self.code_models["primary"]),
                temperature=0.3,  # Low for consistent reasoning
                max_tokens=2000
            )

            # Parse the plan from response
            return self._parse_cot_plan(response.get("response", ""))

        except Exception as e:
            logger.warning(f"[CODE-OPTIMIZER] COT planning failed: {e}")
            return {
                "summary": task,
                "steps": [task],
                "considerations": [],
                "approach": "direct"
            }

    def _build_cot_planning_prompt(
        self,
        task: str,
        context: Optional[str],
        language: str,
        requirements: Optional[List[str]]
    ) -> str:
        """Build chain-of-thought planning prompt."""
        req_text = "\n".join(f"- {r}" for r in (requirements or []))

        return f"""You are an expert {language} developer planning a coding task.

TASK: {task}

{f"CONTEXT:{chr(10)}{context}" if context else ""}

{f"REQUIREMENTS:{chr(10)}{req_text}" if requirements else ""}

Think through this step-by-step:

1. UNDERSTAND: What exactly needs to be built? What are the inputs and outputs?

2. DECOMPOSE: Break down into smaller sub-tasks. What are the components?

3. DESIGN: What's the best architecture? What patterns should we use?

4. EDGE CASES: What edge cases need handling? What could go wrong?

5. QUALITY: How do we ensure correctness, readability, and maintainability?

6. APPROACH: What's the implementation approach?

Provide your analysis in this format:

UNDERSTANDING:
[Your understanding of the task]

DECOMPOSITION:
1. [Sub-task 1]
2. [Sub-task 2]
...

DESIGN:
[Architecture and patterns]

EDGE_CASES:
- [Edge case 1]
- [Edge case 2]
...

QUALITY_CONSIDERATIONS:
- [Consideration 1]
- [Consideration 2]
...

IMPLEMENTATION_APPROACH:
[Step-by-step approach]

SUMMARY:
[One-sentence summary of the plan]"""

    def _parse_cot_plan(self, response: str) -> Dict[str, Any]:
        """Parse chain-of-thought plan from response."""
        plan = {
            "summary": "",
            "understanding": "",
            "steps": [],
            "design": "",
            "edge_cases": [],
            "considerations": [],
            "approach": ""
        }

        sections = {
            "UNDERSTANDING:": "understanding",
            "DECOMPOSITION:": "steps",
            "DESIGN:": "design",
            "EDGE_CASES:": "edge_cases",
            "QUALITY_CONSIDERATIONS:": "considerations",
            "IMPLEMENTATION_APPROACH:": "approach",
            "SUMMARY:": "summary"
        }

        current_section = None
        current_content = []

        for line in response.split("\n"):
            line = line.strip()

            # Check for section headers
            for header, key in sections.items():
                if line.startswith(header):
                    # Save previous section
                    if current_section:
                        self._save_section(plan, current_section, current_content)
                    current_section = key
                    current_content = []
                    break
            else:
                if current_section and line:
                    current_content.append(line)

        # Save last section
        if current_section:
            self._save_section(plan, current_section, current_content)

        return plan

    def _save_section(self, plan: Dict, section: str, content: List[str]):
        """Save parsed section to plan."""
        if section in ["steps", "edge_cases", "considerations"]:
            # Parse as list items
            items = []
            for line in content:
                # Remove list markers
                cleaned = re.sub(r'^[\d\-\*\.\)]+\s*', '', line)
                if cleaned:
                    items.append(cleaned)
            plan[section] = items
        else:
            plan[section] = "\n".join(content)

    async def _generate_initial(
        self,
        task: str,
        plan: Dict[str, Any],
        context: Optional[str],
        language: str,
        requirements: Optional[List[str]]
    ) -> str:
        """Generate initial code based on plan."""
        prompt = self._build_generation_prompt(task, plan, context, language, requirements)

        if not self.multi_llm_client:
            return f"# TODO: Implement {task}\npass"

        try:
            response = await self.multi_llm_client.generate(
                prompt=prompt,
                model=self.code_models["primary"],
                temperature=0.5,  # Balanced creativity/consistency
                max_tokens=4000
            )

            code = self._extract_code(response.get("response", ""), language)
            return code

        except Exception as e:
            logger.error(f"[CODE-OPTIMIZER] Initial generation failed: {e}")
            return f"# Error during generation: {e}\npass"

    def _build_generation_prompt(
        self,
        task: str,
        plan: Dict[str, Any],
        context: Optional[str],
        language: str,
        requirements: Optional[List[str]]
    ) -> str:
        """Build code generation prompt with plan context."""
        req_text = "\n".join(f"- {r}" for r in (requirements or []))
        steps_text = "\n".join(f"- {s}" for s in plan.get("steps", []))
        edge_cases = "\n".join(f"- {e}" for e in plan.get("edge_cases", []))

        return f"""You are an expert {language} developer. Write production-quality code.

TASK: {task}

{f"EXISTING CONTEXT:{chr(10)}```{language}{chr(10)}{context}{chr(10)}```" if context else ""}

{f"REQUIREMENTS:{chr(10)}{req_text}" if requirements else ""}

IMPLEMENTATION PLAN:
{plan.get('approach', 'Direct implementation')}

SUB-TASKS:
{steps_text}

EDGE CASES TO HANDLE:
{edge_cases}

QUALITY STANDARDS:
1. Write clean, readable, well-documented code
2. Handle all edge cases properly
3. Use appropriate error handling
4. Follow {language} best practices and idioms
5. Include type hints/annotations where applicable
6. Make the code maintainable and extensible

Generate the complete implementation:

```{language}
"""

    def _extract_code(self, response: str, language: str) -> str:
        """Extract code from LLM response."""
        # Look for code blocks
        patterns = [
            rf"```{language}\n(.*?)```",
            r"```\n(.*?)```",
            rf"```{language}(.*?)```",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
            if matches:
                return matches[0].strip()

        # If no code block, try to find code-like content
        lines = response.split("\n")
        code_lines = []
        in_code = False

        for line in lines:
            # Heuristic: lines starting with common code patterns
            if (line.startswith(("def ", "class ", "import ", "from ", "async ", "#", "    ", "\t")) or
                in_code and line.strip()):
                code_lines.append(line)
                in_code = True
            elif in_code and not line.strip():
                code_lines.append(line)

        if code_lines:
            return "\n".join(code_lines).strip()

        return response.strip()

    async def _assess_quality(
        self,
        code: str,
        task: str,
        language: str
    ) -> QualityScore:
        """Assess code quality across multiple dimensions."""
        quality = QualityScore(overall_score=0.0)

        # Static analysis (syntax, structure)
        static_score = self._static_analysis(code, language)
        quality.dimension_scores["static"] = static_score

        # LLM-based quality assessment
        if self.multi_llm_client:
            llm_assessment = await self._llm_quality_check(code, task, language)
            quality.dimension_scores.update(llm_assessment.get("scores", {}))
            quality.issues_found = llm_assessment.get("issues", [])
            quality.suggestions = llm_assessment.get("suggestions", [])
            quality.reasoning = llm_assessment.get("reasoning", "")

        # Calculate overall score
        if quality.dimension_scores:
            quality.overall_score = sum(quality.dimension_scores.values()) / len(quality.dimension_scores)
        else:
            quality.overall_score = static_score

        quality.confidence = min(0.9, 0.5 + len(quality.dimension_scores) * 0.1)

        return quality

    def _static_analysis(self, code: str, language: str) -> float:
        """Perform static code analysis."""
        score = 0.5  # Base score

        # Check for basic quality indicators
        lines = code.split("\n")
        non_empty_lines = [l for l in lines if l.strip()]

        if not non_empty_lines:
            return 0.0

        # Has content
        if len(non_empty_lines) > 0:
            score += 0.1

        # Has documentation/comments
        comment_chars = {"python": "#", "javascript": "//", "typescript": "//", "java": "//", "go": "//"}
        comment_char = comment_chars.get(language.lower(), "#")
        has_comments = any(comment_char in line for line in lines)
        if has_comments:
            score += 0.1

        # Has docstrings (Python)
        if language.lower() == "python":
            if '"""' in code or "'''" in code:
                score += 0.1

        # Reasonable line length
        long_lines = sum(1 for line in lines if len(line) > 120)
        if long_lines < len(lines) * 0.1:
            score += 0.1

        # Not just TODO/pass
        if "TODO" not in code.upper() or "pass" != code.strip():
            score += 0.1

        return min(1.0, score)

    async def _llm_quality_check(
        self,
        code: str,
        task: str,
        language: str
    ) -> Dict[str, Any]:
        """Use LLM to assess code quality."""
        prompt = f"""You are a senior code reviewer. Analyze this {language} code for quality.

TASK DESCRIPTION: {task}

CODE:
```{language}
{code}
```

Rate each dimension from 0.0 to 1.0 and explain:

1. CORRECTNESS: Does it correctly implement the task?
2. COMPLETENESS: Is the implementation complete?
3. READABILITY: Is it easy to read and understand?
4. EFFICIENCY: Is it reasonably efficient?
5. MAINTAINABILITY: Is it easy to maintain and extend?
6. BEST_PRACTICES: Does it follow {language} best practices?
7. ERROR_HANDLING: Does it handle errors appropriately?

Provide your assessment in this JSON format:
```json
{{
    "scores": {{
        "correctness": 0.0,
        "completeness": 0.0,
        "readability": 0.0,
        "efficiency": 0.0,
        "maintainability": 0.0,
        "best_practices": 0.0,
        "error_handling": 0.0
    }},
    "issues": ["issue1", "issue2"],
    "suggestions": ["suggestion1", "suggestion2"],
    "reasoning": "Brief explanation of scores"
}}
```"""

        try:
            response = await self.multi_llm_client.generate(
                prompt=prompt,
                model=self.code_models.get("validator", self.code_models["fast"]),
                temperature=0.2,  # Low for consistent scoring
                max_tokens=1500
            )

            # Parse JSON from response
            json_match = re.search(r'```json\s*(.*?)\s*```', response.get("response", ""), re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # Try direct JSON parse
            return json.loads(response.get("response", "{}"))

        except Exception as e:
            logger.warning(f"[CODE-OPTIMIZER] LLM quality check failed: {e}")
            return {"scores": {}, "issues": [], "suggestions": []}

    async def _refine_code(
        self,
        code: str,
        task: str,
        quality: QualityScore,
        language: str,
        strategy: RefinementStrategy,
        min_quality: float
    ) -> RefinementResult:
        """Refine code to improve quality."""
        result = RefinementResult(
            iteration=0,
            original_code=code,
            refined_code=code,
            quality_before=quality,
            quality_after=quality
        )

        current_code = code
        current_quality = quality

        for iteration in range(1, self.refinement_config["max_iterations"] + 1):
            result.iteration = iteration
            self.metrics["quality_improvements"] += 1

            # Apply refinement strategy
            if strategy == RefinementStrategy.SELF_CRITIQUE:
                refined = await self._self_critique_refinement(
                    current_code, task, current_quality, language
                )
            elif strategy == RefinementStrategy.CHAIN_OF_THOUGHT:
                refined = await self._cot_refinement(
                    current_code, task, current_quality, language
                )
            elif strategy == RefinementStrategy.BEST_OF_N:
                refined = await self._best_of_n_refinement(
                    task, language, self.refinement_config["best_of_n_count"]
                )
            else:
                refined = await self._self_critique_refinement(
                    current_code, task, current_quality, language
                )

            # Assess refined code
            new_quality = await self._assess_quality(refined, task, language)

            # Check if improvement is significant
            improvement = new_quality.overall_score - current_quality.overall_score

            if improvement > self.refinement_config["improvement_threshold"]:
                current_code = refined
                current_quality = new_quality
                result.changes_made.append(f"Iteration {iteration}: +{improvement:.2f} quality")
                logger.info(f"[CODE-OPTIMIZER] Refinement iteration {iteration}: {current_quality.overall_score:.2f}")
            else:
                logger.info(f"[CODE-OPTIMIZER] Minimal improvement ({improvement:.2f}), stopping refinement")
                break

            # Check if we've reached target quality
            if current_quality.overall_score >= min_quality:
                logger.info(f"[CODE-OPTIMIZER] Target quality reached: {current_quality.overall_score:.2f}")
                break

        result.refined_code = current_code
        result.quality_after = current_quality

        return result

    async def _self_critique_refinement(
        self,
        code: str,
        task: str,
        quality: QualityScore,
        language: str
    ) -> str:
        """Refine code using self-critique approach."""
        issues_text = "\n".join(f"- {issue}" for issue in quality.issues_found)
        suggestions_text = "\n".join(f"- {s}" for s in quality.suggestions)

        prompt = f"""You are improving {language} code. Review and fix the issues.

ORIGINAL TASK: {task}

CURRENT CODE:
```{language}
{code}
```

IDENTIFIED ISSUES:
{issues_text if issues_text else "- General improvements needed"}

SUGGESTIONS:
{suggestions_text if suggestions_text else "- Improve code quality"}

CURRENT QUALITY SCORE: {quality.overall_score:.2f}/1.0

Fix all issues and improve the code. Maintain the same functionality but with better quality.

```{language}
"""

        if not self.multi_llm_client:
            return code

        try:
            response = await self.multi_llm_client.generate(
                prompt=prompt,
                model=self.code_models["primary"],
                temperature=0.4,
                max_tokens=4000
            )

            return self._extract_code(response.get("response", ""), language)

        except Exception as e:
            logger.warning(f"[CODE-OPTIMIZER] Self-critique refinement failed: {e}")
            return code

    async def _cot_refinement(
        self,
        code: str,
        task: str,
        quality: QualityScore,
        language: str
    ) -> str:
        """Refine code using chain-of-thought reasoning."""
        prompt = f"""You are improving {language} code using step-by-step reasoning.

TASK: {task}

CURRENT CODE:
```{language}
{code}
```

QUALITY ANALYSIS:
- Overall Score: {quality.overall_score:.2f}/1.0
- Issues: {', '.join(quality.issues_found) if quality.issues_found else 'Minor improvements needed'}

Think through improvements step-by-step:

1. IDENTIFY: What are the main issues with this code?

2. PRIORITIZE: Which issues are most important to fix?

3. PLAN: How will you fix each issue?

4. IMPLEMENT: Write the improved code.

Step through your reasoning, then provide the improved code:

REASONING:
[Your step-by-step analysis]

IMPROVED CODE:
```{language}
[Your improved code here]
```"""

        if not self.multi_llm_client:
            return code

        try:
            response = await self.multi_llm_client.generate(
                prompt=prompt,
                model=self.code_models.get("reasoning", self.code_models["primary"]),
                temperature=0.3,
                max_tokens=4000
            )

            return self._extract_code(response.get("response", ""), language)

        except Exception as e:
            logger.warning(f"[CODE-OPTIMIZER] COT refinement failed: {e}")
            return code

    async def _best_of_n_refinement(
        self,
        task: str,
        language: str,
        n: int
    ) -> str:
        """Generate N versions and pick the best one."""
        if not self.multi_llm_client:
            return f"# TODO: {task}\npass"

        candidates = []

        # Generate N candidates with varied temperatures
        temperatures = [0.3, 0.5, 0.7][:n]

        for temp in temperatures:
            try:
                prompt = f"""Write high-quality {language} code for this task:

{task}

Requirements:
- Clean, readable code
- Proper error handling
- Good documentation
- Follow best practices

```{language}
"""
                response = await self.multi_llm_client.generate(
                    prompt=prompt,
                    model=self.code_models["primary"],
                    temperature=temp,
                    max_tokens=4000
                )

                code = self._extract_code(response.get("response", ""), language)
                quality = await self._assess_quality(code, task, language)
                candidates.append((code, quality))

            except Exception as e:
                logger.warning(f"[CODE-OPTIMIZER] Candidate generation failed: {e}")

        if not candidates:
            return f"# TODO: {task}\npass"

        # Pick best candidate
        best = max(candidates, key=lambda x: x[1].overall_score)
        logger.info(f"[CODE-OPTIMIZER] Best-of-{len(candidates)}: selected with score {best[1].overall_score:.2f}")

        return best[0]

    async def _final_validation(
        self,
        code: str,
        task: str,
        language: str
    ) -> QualityScore:
        """Perform final validation of the code."""
        # Run comprehensive quality assessment
        quality = await self._assess_quality(code, task, language)

        # Additional validation checks
        validation_checks = []

        # Syntax check (basic)
        if language.lower() == "python":
            try:
                compile(code, "<string>", "exec")
                validation_checks.append(("syntax", True))
            except SyntaxError as e:
                validation_checks.append(("syntax", False))
                quality.issues_found.append(f"Syntax error: {e}")

        # Check for common issues
        if "TODO" in code.upper():
            quality.issues_found.append("Contains TODO markers")
            quality.dimension_scores["completeness"] = quality.dimension_scores.get("completeness", 0.5) * 0.9

        if "pass" == code.strip() or code.strip().endswith("pass"):
            quality.issues_found.append("Contains placeholder pass statement")
            quality.dimension_scores["completeness"] = quality.dimension_scores.get("completeness", 0.5) * 0.5

        # Recalculate overall score
        if quality.dimension_scores:
            quality.overall_score = sum(quality.dimension_scores.values()) / len(quality.dimension_scores)

        return quality

    def _update_metrics(self, final_quality: float):
        """Update optimizer metrics."""
        # Update average
        total_gens = self.metrics["generations"]
        if total_gens > 1:
            self.metrics["avg_final_quality"] = (
                (self.metrics["avg_final_quality"] * (total_gens - 1) + final_quality) / total_gens
            )
        else:
            self.metrics["avg_final_quality"] = final_quality

        # Update best
        if final_quality > self.metrics["best_quality_achieved"]:
            self.metrics["best_quality_achieved"] = final_quality

    def get_metrics(self) -> Dict[str, Any]:
        """Get optimizer metrics."""
        return {
            **self.metrics,
            "quality_threshold": self.quality_thresholds["production_ready"],
            "max_iterations": self.refinement_config["max_iterations"]
        }


class DeepSeekOptimizer:
    """
    DeepSeek-specific optimizations for maximum code quality.

    DeepSeek models have specific strengths we can leverage:
    - Strong reasoning capabilities
    - Excellent code understanding
    - Good at following structured prompts
    """

    # DeepSeek-optimized prompt templates
    PROMPT_TEMPLATES = {
        "code_generation": """<|begin_of_sentence|>You are an expert programmer.

Task: {task}

{context}

Requirements:
{requirements}

Write clean, efficient, well-documented {language} code. Include:
1. Clear variable names
2. Proper error handling
3. Type hints
4. Docstrings
5. Edge case handling

```{language}
""",

        "code_review": """<|begin_of_sentence|>You are a senior code reviewer.

Review this {language} code:
```{language}
{code}
```

Analyze for:
1. Correctness - Does it work as intended?
2. Security - Any vulnerabilities?
3. Performance - Any inefficiencies?
4. Maintainability - Is it readable and maintainable?
5. Best practices - Following language conventions?

Provide specific, actionable feedback.""",

        "code_fix": """<|begin_of_sentence|>You are a debugging expert.

Original code:
```{language}
{code}
```

Issues to fix:
{issues}

Fix all issues while maintaining functionality. Explain each fix.

Fixed code:
```{language}
""",

        "reasoning": """<|begin_of_sentence|>You are solving a complex problem step-by-step.

Problem: {task}

Think through this carefully:

Step 1: Understand the requirements
{step1}

Step 2: Identify the approach
{step2}

Step 3: Consider edge cases
{step3}

Step 4: Implement the solution
{step4}

Final answer:
"""
    }

    @classmethod
    def get_prompt(
        cls,
        template_name: str,
        **kwargs
    ) -> str:
        """Get optimized prompt for DeepSeek models."""
        template = cls.PROMPT_TEMPLATES.get(template_name, cls.PROMPT_TEMPLATES["code_generation"])
        return template.format(**kwargs)

    @classmethod
    def get_optimal_params(
        cls,
        task_type: str
    ) -> Dict[str, Any]:
        """Get optimal generation parameters for DeepSeek."""
        params = {
            "code_generation": {
                "temperature": 0.5,
                "top_p": 0.9,
                "top_k": 40,
                "repeat_penalty": 1.1,
                "max_tokens": 4096
            },
            "code_review": {
                "temperature": 0.3,
                "top_p": 0.8,
                "top_k": 30,
                "repeat_penalty": 1.0,
                "max_tokens": 2048
            },
            "reasoning": {
                "temperature": 0.2,
                "top_p": 0.85,
                "top_k": 20,
                "repeat_penalty": 1.0,
                "max_tokens": 3000
            },
            "creative": {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 50,
                "repeat_penalty": 1.1,
                "max_tokens": 4096
            }
        }
        return params.get(task_type, params["code_generation"])
