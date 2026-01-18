import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import asyncio
logger = logging.getLogger(__name__)

class ReasoningPlane(str, Enum):
    logger = logging.getLogger(__name__)
    """The 4 reasoning planes Grace operates on."""
    REPOSITORY = "repository"   # Macro: architecture, system integrity
    FOLDER = "folder"           # Meso: module boundaries, cohesion
    FILE = "file"               # Micro: code logic, types, edge cases
    GENESIS_KEY = "genesis_key" # Temporal: intent, context, trajectory


class ReasoningApproach(str, Enum):
    """Different approaches to problem-solving."""
    LINEAR = "linear"           # Sequential step-by-step
    DIVERGENT = "divergent"     # Generate many possibilities
    CONVERGENT = "convergent"   # Narrow down to best solution
    LATERAL = "lateral"         # Indirect, creative approaches
    REVERSE = "reverse"         # Start from solution, work back
    ANALOGICAL = "analogical"   # Pattern matching from other domains


@dataclass
class ReasoningContext:
    """Context for a reasoning session."""
    query: str
    target_path: Optional[str] = None
    active_planes: List[ReasoningPlane] = field(default_factory=list)
    approach: ReasoningApproach = ReasoningApproach.DIVERGENT
    max_depth: int = 3
    collected_insights: Dict[ReasoningPlane, List[Dict]] = field(default_factory=dict)
    synthesis: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "target_path": self.target_path,
            "active_planes": [p.value for p in self.active_planes],
            "approach": self.approach.value,
            "max_depth": self.max_depth,
            "collected_insights": {
                k.value: v for k, v in self.collected_insights.items()
            },
            "synthesis": self.synthesis
        }


@dataclass
class PlaneInsight:
    """An insight from a specific reasoning plane."""
    plane: ReasoningPlane
    insight_type: str  # observation, pattern, concern, suggestion
    content: str
    confidence: float
    evidence: List[str] = field(default_factory=list)
    related_paths: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plane": self.plane.value,
            "type": self.insight_type,
            "content": self.content,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "related_paths": self.related_paths,
            "timestamp": self.timestamp.isoformat()
        }


class MultiPlaneReasoner:
    """
    Multi-plane, non-linear reasoning system.

    Enables Grace to think about problems from multiple dimensions:
    - Repository: "How does this affect the overall architecture?"
    - Folder: "Does this fit with the module's responsibility?"
    - File: "Is the code correct and handling edge cases?"
    - Genesis: "What was the original intent and where are we headed?"
    """

    def __init__(
        self,
        session=None,
        repo_path: Optional[Path] = None
    ):
        self.session = session
        self.repo_path = repo_path or Path.cwd()

        # Initialize services
        self._genesis_service = None
        self._llm_orchestrator = None

        # Reasoning history for pattern learning
        self.reasoning_history: List[ReasoningContext] = []

        # Cached architectural knowledge
        self._arch_cache: Dict[str, Any] = {}
        self._module_cache: Dict[str, Any] = {}

        logger.info("[REASONER] Multi-plane reasoner initialized")

    async def initialize(self):
        """Initialize connections to dependent systems."""
        try:
            from genesis.genesis_key_service import GenesisKeyService
            self._genesis_service = GenesisKeyService(
                session=self.session,
                repo_path=str(self.repo_path)
            )

            from llm_orchestrator.llm_orchestrator import LLMOrchestrator
            self._llm_orchestrator = LLMOrchestrator(session=self.session)

            return True
        except Exception as e:
            logger.warning(f"[REASONER] Partial initialization: {e}")
            return False

    async def reason(
        self,
        query: str,
        target_path: Optional[str] = None,
        approach: ReasoningApproach = ReasoningApproach.DIVERGENT,
        planes: Optional[List[ReasoningPlane]] = None
    ) -> Dict[str, Any]:
        """
        Perform multi-plane reasoning on a query.

        Args:
            query: The question or problem to reason about
            target_path: Optional specific file/folder to focus on
            approach: The reasoning approach to use
            planes: Which planes to activate (default: all)

        Returns:
            Comprehensive reasoning result with insights from all planes
        """
        # Default to all planes
        if planes is None:
            planes = list(ReasoningPlane)

        context = ReasoningContext(
            query=query,
            target_path=target_path,
            active_planes=planes,
            approach=approach,
            collected_insights={plane: [] for plane in planes}
        )

        logger.info(f"[REASONER] Starting multi-plane reasoning: '{query[:50]}...'")

        # Gather insights from each plane in parallel
        tasks = []
        for plane in planes:
            tasks.append(self._reason_on_plane(plane, context))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect insights
        for i, plane in enumerate(planes):
            if isinstance(results[i], Exception):
                logger.warning(f"[REASONER] Plane {plane.value} failed: {results[i]}")
            else:
                context.collected_insights[plane] = results[i]

        # Synthesize insights across planes
        synthesis = await self._synthesize_insights(context)
        context.synthesis = synthesis

        # Store in history for learning
        self.reasoning_history.append(context)
        if len(self.reasoning_history) > 100:
            self.reasoning_history = self.reasoning_history[-100:]

        return {
            "query": query,
            "approach": approach.value,
            "insights": {
                plane.value: [i.to_dict() for i in insights]
                for plane, insights in context.collected_insights.items()
            },
            "synthesis": synthesis,
            "confidence": self._calculate_overall_confidence(context)
        }

    async def explain(
        self,
        target: Optional[str],
        query: str
    ) -> Dict[str, Any]:
        """
        Explain code or concept using multi-plane reasoning.

        Returns a human-readable explanation from multiple perspectives.
        """
        result = await self.reason(
            query=f"Explain: {query}",
            target_path=target,
            approach=ReasoningApproach.DIVERGENT
        )

        # Format for human consumption
        explanation = {
            "summary": result.get("synthesis", ""),
            "perspectives": {}
        }

        for plane, insights in result.get("insights", {}).items():
            if insights:
                perspective_text = "\n".join([
                    f"- {i.get('content', '')}"
                    for i in insights[:3]
                ])
                explanation["perspectives"][plane] = perspective_text

        return explanation

    async def solve_problem(
        self,
        problem: str,
        constraints: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Solve a problem using multiple reasoning approaches.

        Tries different approaches and synthesizes the best solution.
        """
        constraints = constraints or {}

        # Try multiple approaches
        approaches = [
            ReasoningApproach.LINEAR,
            ReasoningApproach.REVERSE,
            ReasoningApproach.LATERAL,
            ReasoningApproach.ANALOGICAL
        ]

        solutions = []
        for approach in approaches:
            try:
                result = await self.reason(
                    query=problem,
                    approach=approach
                )
                solutions.append({
                    "approach": approach.value,
                    "solution": result.get("synthesis"),
                    "confidence": result.get("confidence", 0)
                })
            except Exception as e:
                logger.warning(f"[REASONER] Approach {approach.value} failed: {e}")

        # Rank solutions by confidence
        solutions.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return {
            "problem": problem,
            "best_solution": solutions[0] if solutions else None,
            "alternatives": solutions[1:3] if len(solutions) > 1 else [],
            "reasoning_depth": len(approaches)
        }

    # =========================================================================
    # Plane-Specific Reasoning
    # =========================================================================

    async def _reason_on_plane(
        self,
        plane: ReasoningPlane,
        context: ReasoningContext
    ) -> List[PlaneInsight]:
        """Reason on a specific plane."""
        if plane == ReasoningPlane.REPOSITORY:
            return await self._reason_repository(context)
        elif plane == ReasoningPlane.FOLDER:
            return await self._reason_folder(context)
        elif plane == ReasoningPlane.FILE:
            return await self._reason_file(context)
        elif plane == ReasoningPlane.GENESIS_KEY:
            return await self._reason_genesis(context)
        else:
            return []

    async def _reason_repository(self, context: ReasoningContext) -> List[PlaneInsight]:
        """
        Repository-level reasoning: architectural integrity, system evolution.
        """
        insights = []

        # Analyze overall structure
        structure = await self._analyze_repository_structure()

        # Check architectural patterns
        arch_insight = PlaneInsight(
            plane=ReasoningPlane.REPOSITORY,
            insight_type="observation",
            content=f"Repository has {len(structure.get('modules', []))} main modules",
            confidence=0.9,
            evidence=[str(m) for m in structure.get('modules', [])[:5]]
        )
        insights.append(arch_insight)

        # Check for architectural concerns related to query
        if context.target_path:
            target = Path(context.target_path)

            # Check layer boundaries
            if "layer1" in str(target):
                insights.append(PlaneInsight(
                    plane=ReasoningPlane.REPOSITORY,
                    insight_type="concern",
                    content="Target is in Layer 1 (universal input/output). Changes may affect all downstream systems.",
                    confidence=0.85,
                    related_paths=[str(target)]
                ))

            # Check core vs peripheral
            if any(core in str(target) for core in ["cognitive", "genesis", "core"]):
                insights.append(PlaneInsight(
                    plane=ReasoningPlane.REPOSITORY,
                    insight_type="concern",
                    content="Target is in core cognitive/genesis systems. High-impact area requiring careful consideration.",
                    confidence=0.9,
                    related_paths=[str(target)]
                ))

        # Use LLM for deeper architectural reasoning
        if self._llm_orchestrator:
            try:
                arch_prompt = f"""As an architect, analyze this query in the context of a large codebase:

Query: {context.query}
Target: {context.target_path or 'Not specified'}

Repository structure:
- Modules: {', '.join(structure.get('modules', [])[:10])}
- Total files: {structure.get('total_files', 'Unknown')}

Provide architectural insights as JSON:
{{
    "patterns": ["relevant architectural patterns"],
    "concerns": ["potential architectural concerns"],
    "recommendations": ["architectural recommendations"]
}}"""

                response = await self._llm_orchestrator.generate(
                    prompt=arch_prompt,
                    skill="architecture",
                    temperature=0.3,
                    response_format="json"
                )

                arch_analysis = self._parse_json(response)

                for concern in arch_analysis.get("concerns", []):
                    insights.append(PlaneInsight(
                        plane=ReasoningPlane.REPOSITORY,
                        insight_type="concern",
                        content=concern,
                        confidence=0.7
                    ))

                for rec in arch_analysis.get("recommendations", []):
                    insights.append(PlaneInsight(
                        plane=ReasoningPlane.REPOSITORY,
                        insight_type="suggestion",
                        content=rec,
                        confidence=0.75
                    ))

            except Exception as e:
                logger.warning(f"[REASONER] LLM arch analysis failed: {e}")

        return insights

    async def _reason_folder(self, context: ReasoningContext) -> List[PlaneInsight]:
        """
        Folder-level reasoning: module responsibility, cohesion.
        """
        insights = []

        if not context.target_path:
            return insights

        target = Path(context.target_path)

        if target.is_file():
            folder = target.parent
        else:
            folder = target

        # Analyze folder contents
        if folder.exists() and folder.is_dir():
            folder_files = list(folder.glob("*.py"))

            insights.append(PlaneInsight(
                plane=ReasoningPlane.FOLDER,
                insight_type="observation",
                content=f"Folder '{folder.name}' contains {len(folder_files)} Python files",
                confidence=1.0,
                related_paths=[str(f) for f in folder_files[:5]]
            ))

            # Check for module cohesion
            if len(folder_files) > 20:
                insights.append(PlaneInsight(
                    plane=ReasoningPlane.FOLDER,
                    insight_type="concern",
                    content=f"Large module with {len(folder_files)} files may need decomposition",
                    confidence=0.7
                ))

            # Check for __init__.py (proper module)
            if not (folder / "__init__.py").exists():
                insights.append(PlaneInsight(
                    plane=ReasoningPlane.FOLDER,
                    insight_type="concern",
                    content="Missing __init__.py - folder is not a proper Python module",
                    confidence=0.9
                ))

            # Analyze naming conventions
            naming_patterns = self._analyze_naming_patterns(folder_files)
            if naming_patterns.get("inconsistent"):
                insights.append(PlaneInsight(
                    plane=ReasoningPlane.FOLDER,
                    insight_type="observation",
                    content=f"Naming patterns: {naming_patterns.get('pattern', 'mixed')}",
                    confidence=0.8
                ))

        return insights

    async def _reason_file(self, context: ReasoningContext) -> List[PlaneInsight]:
        """
        File-level reasoning: code correctness, logic, edge cases.
        """
        insights = []

        if not context.target_path:
            return insights

        target = Path(context.target_path)
        if not target.exists() or not target.is_file():
            return insights

        try:
            content = target.read_text()
        except Exception as e:
            insights.append(PlaneInsight(
                plane=ReasoningPlane.FILE,
                insight_type="concern",
                content=f"Could not read file: {e}",
                confidence=1.0
            ))
            return insights

        lines = content.splitlines()

        # Basic file analysis
        insights.append(PlaneInsight(
            plane=ReasoningPlane.FILE,
            insight_type="observation",
            content=f"File has {len(lines)} lines of code",
            confidence=1.0
        ))

        # Check for complexity indicators
        complexity_indicators = {
            "nested_loops": sum(1 for line in lines if "for " in line or "while " in line),
            "conditionals": sum(1 for line in lines if "if " in line or "elif " in line),
            "try_blocks": sum(1 for line in lines if "try:" in line),
            "functions": sum(1 for line in lines if line.strip().startswith("def ")),
            "classes": sum(1 for line in lines if line.strip().startswith("class "))
        }

        if complexity_indicators["nested_loops"] > 5:
            insights.append(PlaneInsight(
                plane=ReasoningPlane.FILE,
                insight_type="concern",
                content=f"High loop count ({complexity_indicators['nested_loops']}). Check for algorithmic complexity.",
                confidence=0.75
            ))

        if complexity_indicators["try_blocks"] > 10:
            insights.append(PlaneInsight(
                plane=ReasoningPlane.FILE,
                insight_type="observation",
                content=f"Many try-except blocks ({complexity_indicators['try_blocks']}). Robust error handling present.",
                confidence=0.8
            ))

        # Check for common issues
        for i, line in enumerate(lines, 1):
            # Long lines
            if len(line) > 120:
                insights.append(PlaneInsight(
                    plane=ReasoningPlane.FILE,
                    insight_type="concern",
                    content=f"Line {i} exceeds 120 characters",
                    confidence=0.9,
                    evidence=[line[:50] + "..."]
                ))
                break  # Only report first occurrence

            # Magic numbers
            if any(magic in line for magic in ["= 42", "= 100", "= 1000"]):
                insights.append(PlaneInsight(
                    plane=ReasoningPlane.FILE,
                    insight_type="concern",
                    content=f"Possible magic number on line {i}. Consider using constants.",
                    confidence=0.6
                ))

        # Use LLM for deeper code analysis
        if self._llm_orchestrator and len(content) < 5000:
            try:
                code_prompt = f"""Analyze this Python code for:
1. Logic correctness
2. Edge cases
3. Error handling
4. Type safety

Query context: {context.query}

Code:
```python
{content[:3000]}
```

Output as JSON:
{{
    "correctness_issues": ["list of logic issues"],
    "edge_cases": ["unhandled edge cases"],
    "suggestions": ["improvement suggestions"]
}}"""

                response = await self._llm_orchestrator.generate(
                    prompt=code_prompt,
                    skill="code_review",
                    temperature=0.2,
                    response_format="json"
                )

                analysis = self._parse_json(response)

                for issue in analysis.get("correctness_issues", []):
                    insights.append(PlaneInsight(
                        plane=ReasoningPlane.FILE,
                        insight_type="concern",
                        content=issue,
                        confidence=0.7
                    ))

                for edge_case in analysis.get("edge_cases", []):
                    insights.append(PlaneInsight(
                        plane=ReasoningPlane.FILE,
                        insight_type="concern",
                        content=f"Unhandled edge case: {edge_case}",
                        confidence=0.65
                    ))

            except Exception as e:
                logger.warning(f"[REASONER] LLM code analysis failed: {e}")

        return insights

    async def _reason_genesis(self, context: ReasoningContext) -> List[PlaneInsight]:
        """
        Genesis-Key reasoning: temporal/causal continuity, trajectory.
        """
        insights = []

        if not self._genesis_service:
            return insights

        # Query genesis keys for target
        if context.target_path:
            try:
                from models.genesis_key_models import GenesisKey
                keys = self.session.query(GenesisKey).filter(
                    GenesisKey.file_path == context.target_path
                ).order_by(
                    GenesisKey.when_timestamp.desc()
                ).limit(20).all()

                if keys:
                    insights.append(PlaneInsight(
                        plane=ReasoningPlane.GENESIS_KEY,
                        insight_type="observation",
                        content=f"Found {len(keys)} genesis keys for this file. Last modified: {keys[0].when_timestamp}",
                        confidence=1.0,
                        evidence=[k.key_id for k in keys[:5]]
                    ))

                    # Analyze change patterns
                    change_types = {}
                    for key in keys:
                        t = key.key_type.value if hasattr(key.key_type, 'value') else str(key.key_type)
                        change_types[t] = change_types.get(t, 0) + 1

                    if change_types:
                        most_common = max(change_types, key=change_types.get)
                        insights.append(PlaneInsight(
                            plane=ReasoningPlane.GENESIS_KEY,
                            insight_type="pattern",
                            content=f"Most common change type: {most_common} ({change_types[most_common]} occurrences)",
                            confidence=0.85
                        ))

                    # Check for error history
                    error_keys = [k for k in keys if k.is_error]
                    if error_keys:
                        insights.append(PlaneInsight(
                            plane=ReasoningPlane.GENESIS_KEY,
                            insight_type="concern",
                            content=f"{len(error_keys)} error events in history. This file may be fragile.",
                            confidence=0.8,
                            evidence=[k.error_message for k in error_keys[:3] if k.error_message]
                        ))

                    # Analyze trajectory
                    if len(keys) >= 5:
                        recent = keys[:5]
                        # Check if recent changes are fixes or features
                        fix_count = sum(1 for k in recent if 'fix' in (k.what_description or '').lower())
                        if fix_count >= 3:
                            insights.append(PlaneInsight(
                                plane=ReasoningPlane.GENESIS_KEY,
                                insight_type="concern",
                                content="Recent trajectory shows repeated fixes. Consider deeper refactoring.",
                                confidence=0.75
                            ))

            except Exception as e:
                logger.warning(f"[REASONER] Genesis key query failed: {e}")

        # Analyze overall intent patterns
        try:
            from models.genesis_key_models import GenesisKey
            recent_keys = self.session.query(GenesisKey).order_by(
                GenesisKey.when_timestamp.desc()
            ).limit(50).all()

            if recent_keys:
                # Extract common intents/themes
                whys = [k.why_reason for k in recent_keys if k.why_reason]
                if whys:
                    insights.append(PlaneInsight(
                        plane=ReasoningPlane.GENESIS_KEY,
                        insight_type="observation",
                        content=f"Recent project activity: {len(recent_keys)} actions tracked",
                        confidence=0.9
                    ))

        except Exception as e:
            logger.warning(f"[REASONER] Recent keys analysis failed: {e}")

        return insights

    # =========================================================================
    # Synthesis
    # =========================================================================

    async def _synthesize_insights(self, context: ReasoningContext) -> str:
        """Synthesize insights from all planes into coherent understanding."""
        all_insights = []
        for plane, insights in context.collected_insights.items():
            for insight in insights:
                all_insights.append(f"[{plane.value}] {insight.content}")

        if not all_insights:
            return "No significant insights gathered."

        # Use LLM for synthesis if available
        if self._llm_orchestrator:
            try:
                synthesis_prompt = f"""Synthesize these insights from multiple perspectives:

Query: {context.query}
Approach: {context.approach.value}

Insights:
{chr(10).join(all_insights[:20])}

Provide a unified understanding that:
1. Identifies common themes across perspectives
2. Highlights key concerns
3. Suggests next steps

Keep it concise (2-3 paragraphs)."""

                synthesis = await self._llm_orchestrator.generate(
                    prompt=synthesis_prompt,
                    skill="reasoning",
                    temperature=0.4
                )

                return synthesis

            except Exception as e:
                logger.warning(f"[REASONER] LLM synthesis failed: {e}")

        # Fallback: simple aggregation
        concerns = [i for i in all_insights if "concern" in i.lower() or "issue" in i.lower()]
        observations = [i for i in all_insights if i not in concerns]

        synthesis = f"Analysis of '{context.query[:50]}...':\n\n"
        if concerns:
            synthesis += f"Concerns ({len(concerns)}): {'; '.join(c[c.find(']')+2:] for c in concerns[:3])}\n\n"
        if observations:
            synthesis += f"Observations: {'; '.join(o[o.find(']')+2:] for o in observations[:3])}"

        return synthesis

    # =========================================================================
    # Helpers
    # =========================================================================

    async def _analyze_repository_structure(self) -> Dict[str, Any]:
        """Analyze repository structure."""
        if self._arch_cache:
            return self._arch_cache

        structure = {
            "modules": [],
            "total_files": 0,
            "total_lines": 0
        }

        try:
            backend = self.repo_path / "backend"
            if backend.exists():
                for item in backend.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):
                        structure["modules"].append(item.name)

                py_files = list(backend.rglob("*.py"))
                structure["total_files"] = len(py_files)

            self._arch_cache = structure

        except Exception as e:
            logger.warning(f"[REASONER] Repository analysis failed: {e}")

        return structure

    def _analyze_naming_patterns(self, files: List[Path]) -> Dict[str, Any]:
        """Analyze file naming patterns."""
        patterns = {
            "snake_case": 0,
            "camelCase": 0,
            "PascalCase": 0,
            "other": 0
        }

        for f in files:
            name = f.stem
            if "_" in name:
                patterns["snake_case"] += 1
            elif name[0].isupper():
                patterns["PascalCase"] += 1
            elif any(c.isupper() for c in name):
                patterns["camelCase"] += 1
            else:
                patterns["other"] += 1

        dominant = max(patterns, key=patterns.get)
        inconsistent = patterns[dominant] < len(files) * 0.8

        return {
            "pattern": dominant,
            "inconsistent": inconsistent,
            "distribution": patterns
        }

    def _calculate_overall_confidence(self, context: ReasoningContext) -> float:
        """Calculate overall confidence from all insights."""
        all_confidences = []
        for insights in context.collected_insights.values():
            for insight in insights:
                all_confidences.append(insight.confidence)

        if not all_confidences:
            return 0.5

        return sum(all_confidences) / len(all_confidences)

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON from text, handling markdown code blocks."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                if end > start:
                    return json.loads(text[start:end])
            elif "```" in text:
                start = text.find("```") + 3
                end = text.find("```", start)
                if end > start:
                    return json.loads(text[start:end])
            return {}
