import logging
import json
import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from pathlib import Path
import uuid
logger = logging.getLogger(__name__)

class QualityTier(str, Enum):
    """Quality tiers for comparison."""
    ELITE = "elite"           # Top 5% - Claude/Cursor level
    EXCELLENT = "excellent"   # Top 20%
    GOOD = "good"             # Top 50%
    ACCEPTABLE = "acceptable" # Passing
    NEEDS_WORK = "needs_work" # Below standard


class CodePattern(str, Enum):
    """Patterns that indicate high-quality code."""
    CLEAR_NAMING = "clear_naming"
    PROPER_STRUCTURE = "proper_structure"
    ERROR_HANDLING = "error_handling"
    DOCUMENTATION = "documentation"
    TYPE_HINTS = "type_hints"
    EDGE_CASES = "edge_cases"
    MODULARITY = "modularity"
    DRY_PRINCIPLE = "dry_principle"
    SINGLE_RESPONSIBILITY = "single_responsibility"
    DEFENSIVE_CODING = "defensive_coding"


@dataclass
class BenchmarkResult:
    """Result of benchmarking a code generation."""
    benchmark_id: str
    task: str
    generated_code: str
    quality_tier: QualityTier
    overall_score: float  # 0.0 - 1.0
    pattern_scores: Dict[str, float] = field(default_factory=dict)
    gaps: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    improvement_suggestions: List[str] = field(default_factory=list)
    competitive_position: str = ""  # vs Claude/Cursor
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "task": self.task[:100],
            "quality_tier": self.quality_tier.value,
            "overall_score": self.overall_score,
            "pattern_scores": self.pattern_scores,
            "gaps": self.gaps,
            "strengths": self.strengths,
            "improvement_suggestions": self.improvement_suggestions,
            "competitive_position": self.competitive_position,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class QualityPattern:
    """A quality pattern to check for."""
    name: str
    description: str
    check_function: str  # Name of method to call
    weight: float = 1.0
    language_specific: bool = False
    languages: List[str] = field(default_factory=list)


class CompetitiveBenchmark:
    """
    Benchmarks code quality against Claude/Cursor standards.

    Uses a library of quality patterns derived from analyzing
    high-quality code outputs to score and compare.
    """

    def __init__(
        self,
        multi_llm_client=None,
        session=None
    ):
        self.multi_llm_client = multi_llm_client
        self.session = session

        # Quality thresholds (based on Claude/Cursor analysis)
        self.tier_thresholds = {
            QualityTier.ELITE: 0.90,
            QualityTier.EXCELLENT: 0.80,
            QualityTier.GOOD: 0.65,
            QualityTier.ACCEPTABLE: 0.50,
            QualityTier.NEEDS_WORK: 0.0
        }

        # Pattern library - patterns that indicate Claude/Cursor-level quality
        self.quality_patterns = self._init_quality_patterns()

        # Benchmark history
        self._benchmarks: Dict[str, BenchmarkResult] = {}

        # Improvement tracking
        self.improvement_metrics = {
            "total_benchmarks": 0,
            "elite_count": 0,
            "excellent_count": 0,
            "avg_score": 0.0,
            "score_trend": [],  # Last 100 scores for trend
            "common_gaps": {},
            "common_strengths": {}
        }

        # Claude/Cursor quality baseline (derived from analysis)
        self.competitive_baseline = {
            "claude": {
                "avg_score": 0.88,
                "patterns": {
                    "clear_naming": 0.92,
                    "proper_structure": 0.90,
                    "error_handling": 0.85,
                    "documentation": 0.88,
                    "type_hints": 0.82,
                    "edge_cases": 0.80,
                    "modularity": 0.85
                }
            },
            "cursor": {
                "avg_score": 0.85,
                "patterns": {
                    "clear_naming": 0.88,
                    "proper_structure": 0.87,
                    "error_handling": 0.82,
                    "documentation": 0.80,
                    "type_hints": 0.85,
                    "edge_cases": 0.78,
                    "modularity": 0.83
                }
            }
        }

        logger.info("[BENCHMARK] Competitive benchmarking initialized")

    def _init_quality_patterns(self) -> Dict[str, QualityPattern]:
        """Initialize quality pattern library."""
        return {
            "clear_naming": QualityPattern(
                name="Clear Naming",
                description="Variables, functions, and classes have clear, descriptive names",
                check_function="_check_clear_naming",
                weight=1.2
            ),
            "proper_structure": QualityPattern(
                name="Proper Structure",
                description="Code is well-organized with logical structure",
                check_function="_check_proper_structure",
                weight=1.3
            ),
            "error_handling": QualityPattern(
                name="Error Handling",
                description="Appropriate error handling and edge cases",
                check_function="_check_error_handling",
                weight=1.2
            ),
            "documentation": QualityPattern(
                name="Documentation",
                description="Clear docstrings and comments where needed",
                check_function="_check_documentation",
                weight=1.0
            ),
            "type_hints": QualityPattern(
                name="Type Hints",
                description="Type annotations for clarity",
                check_function="_check_type_hints",
                weight=0.8,
                language_specific=True,
                languages=["python", "typescript"]
            ),
            "edge_cases": QualityPattern(
                name="Edge Cases",
                description="Handles edge cases and boundary conditions",
                check_function="_check_edge_cases",
                weight=1.1
            ),
            "modularity": QualityPattern(
                name="Modularity",
                description="Code is modular and follows single responsibility",
                check_function="_check_modularity",
                weight=1.0
            ),
            "dry_principle": QualityPattern(
                name="DRY Principle",
                description="No unnecessary code repetition",
                check_function="_check_dry",
                weight=0.9
            ),
            "defensive_coding": QualityPattern(
                name="Defensive Coding",
                description="Input validation and defensive checks",
                check_function="_check_defensive",
                weight=1.0
            ),
            "readability": QualityPattern(
                name="Readability",
                description="Code is easy to read and understand",
                check_function="_check_readability",
                weight=1.1
            )
        }

    async def benchmark(
        self,
        code: str,
        task: str,
        language: str = "python"
    ) -> BenchmarkResult:
        """
        Benchmark code against Claude/Cursor quality standards.

        Args:
            code: The generated code to benchmark
            task: The task description
            language: Programming language

        Returns:
            BenchmarkResult with scores and analysis
        """
        result = BenchmarkResult(
            benchmark_id=f"BENCH-{uuid.uuid4().hex[:12]}",
            task=task,
            generated_code=code
        )

        self.improvement_metrics["total_benchmarks"] += 1

        # Check each quality pattern
        for pattern_name, pattern in self.quality_patterns.items():
            # Skip language-specific patterns if not applicable
            if pattern.language_specific and language.lower() not in pattern.languages:
                continue

            score = await self._check_pattern(pattern, code, language)
            result.pattern_scores[pattern_name] = score

        # Calculate overall score (weighted average)
        total_weight = sum(
            p.weight for p in self.quality_patterns.values()
            if not p.language_specific or language.lower() in p.languages
        )
        weighted_sum = sum(
            score * self.quality_patterns[name].weight
            for name, score in result.pattern_scores.items()
        )
        result.overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Determine quality tier
        result.quality_tier = self._determine_tier(result.overall_score)

        # Identify gaps and strengths
        result.gaps = self._identify_gaps(result.pattern_scores)
        result.strengths = self._identify_strengths(result.pattern_scores)

        # Generate improvement suggestions
        result.improvement_suggestions = await self._generate_suggestions(
            code, result.gaps, language
        )

        # Competitive position
        result.competitive_position = self._calculate_competitive_position(
            result.overall_score, result.pattern_scores
        )

        # Update metrics
        self._update_metrics(result)

        # Store benchmark
        self._benchmarks[result.benchmark_id] = result

        logger.info(f"[BENCHMARK] Score: {result.overall_score:.2f}, Tier: {result.quality_tier.value}")

        return result

    async def _check_pattern(
        self,
        pattern: QualityPattern,
        code: str,
        language: str
    ) -> float:
        """Check a specific quality pattern."""
        check_method = getattr(self, pattern.check_function, None)

        if check_method:
            return check_method(code, language)

        return 0.5  # Default if no specific check

    def _check_clear_naming(self, code: str, language: str) -> float:
        """Check for clear, descriptive naming."""
        score = 0.5

        # Check for single-letter variables (bad practice)
        single_letter = len(re.findall(r'\b[a-z]\s*=', code))
        if single_letter == 0:
            score += 0.2
        elif single_letter < 3:
            score += 0.1

        # Check for descriptive function names
        if language == "python":
            functions = re.findall(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', code)
        else:
            functions = re.findall(r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', code)

        if functions:
            # Score based on name length (longer = more descriptive)
            avg_len = sum(len(f) for f in functions) / len(functions)
            if avg_len > 10:
                score += 0.2
            elif avg_len > 6:
                score += 0.1

        # Check for snake_case or camelCase consistency
        if language == "python":
            if all('_' in f or f.islower() for f in functions):
                score += 0.1

        return min(1.0, score)

    def _check_proper_structure(self, code: str, language: str) -> float:
        """Check for proper code structure."""
        score = 0.5

        lines = code.split("\n")

        # Check for reasonable line length
        long_lines = sum(1 for line in lines if len(line) > 100)
        if long_lines == 0:
            score += 0.15
        elif long_lines < len(lines) * 0.1:
            score += 0.08

        # Check for proper indentation
        if language == "python":
            if all(not line or line.startswith(" " * 4) or not line.startswith(" ")
                   for line in lines):
                score += 0.15

        # Check for logical grouping (blank lines between sections)
        blank_lines = sum(1 for line in lines if not line.strip())
        if 0.05 < blank_lines / max(1, len(lines)) < 0.2:
            score += 0.1

        # Check for imports at top (Python)
        if language == "python":
            import_lines = [i for i, line in enumerate(lines) if line.strip().startswith(("import ", "from "))]
            if import_lines and max(import_lines) < len(lines) * 0.2:
                score += 0.1

        return min(1.0, score)

    def _check_error_handling(self, code: str, language: str) -> float:
        """Check for error handling."""
        score = 0.3

        if language == "python":
            has_try = "try:" in code
            has_except = "except" in code
            has_raise = "raise" in code
            has_assertions = "assert" in code
        else:
            has_try = "try {" in code or "try{" in code
            has_except = "catch" in code
            has_raise = "throw" in code
            has_assertions = "assert" in code.lower() or "expect" in code

        if has_try and has_except:
            score += 0.3

        if has_raise:
            score += 0.2

        # Check for specific exception handling (not bare except)
        if language == "python":
            specific_except = re.findall(r'except\s+\w+', code)
            bare_except = re.findall(r'except\s*:', code)
            if specific_except and not bare_except:
                score += 0.2

        return min(1.0, score)

    def _check_documentation(self, code: str, language: str) -> float:
        """Check for documentation."""
        score = 0.3

        lines = code.split("\n")
        total_lines = len([l for l in lines if l.strip()])

        if language == "python":
            # Docstrings
            docstrings = code.count('"""') // 2 + code.count("'''") // 2
            if docstrings > 0:
                score += 0.3
            if docstrings >= 2:
                score += 0.1

            # Comments
            comments = sum(1 for line in lines if line.strip().startswith("#"))
        else:
            # JSDoc or regular comments
            jsdoc = code.count("/**")
            if jsdoc > 0:
                score += 0.3

            comments = sum(1 for line in lines if "//" in line or "/*" in line)

        # Comment ratio
        comment_ratio = comments / max(1, total_lines)
        if 0.05 < comment_ratio < 0.3:
            score += 0.2
        elif comment_ratio > 0:
            score += 0.1

        return min(1.0, score)

    def _check_type_hints(self, code: str, language: str) -> float:
        """Check for type hints/annotations."""
        score = 0.3

        if language == "python":
            # Function signatures with types
            typed_funcs = len(re.findall(r'def\s+\w+\s*\([^)]*:\s*\w+', code))
            # Return type hints
            return_types = len(re.findall(r'\)\s*->\s*\w+', code))
            # Variable annotations
            var_types = len(re.findall(r':\s*(str|int|float|bool|List|Dict|Optional|Any)\s*=', code))

            if typed_funcs > 0:
                score += 0.3
            if return_types > 0:
                score += 0.2
            if var_types > 0:
                score += 0.2

        elif language == "typescript":
            # TypeScript type annotations
            type_annotations = len(re.findall(r':\s*\w+[\[\]<>]*', code))
            if type_annotations > 3:
                score += 0.5
            elif type_annotations > 0:
                score += 0.3

        return min(1.0, score)

    def _check_edge_cases(self, code: str, language: str) -> float:
        """Check for edge case handling."""
        score = 0.3

        # Check for null/None checks
        null_checks = (
            code.count("is None") +
            code.count("is not None") +
            code.count("!= None") +
            code.count("== None") +
            code.count("!== null") +
            code.count("=== null") +
            code.count("!== undefined")
        )
        if null_checks > 0:
            score += 0.2

        # Check for empty checks
        empty_checks = (
            code.count("not ") +
            code.count("len(") +
            code.count(".length") +
            code.count("isEmpty")
        )
        if empty_checks > 1:
            score += 0.2

        # Check for boundary checks
        boundary_checks = (
            code.count(" < 0") +
            code.count(" <= 0") +
            code.count(" > ") +
            code.count(" >= ")
        )
        if boundary_checks > 0:
            score += 0.15

        # Check for default values
        defaults = code.count(" or ") + code.count("??") + code.count("||")
        if defaults > 0:
            score += 0.15

        return min(1.0, score)

    def _check_modularity(self, code: str, language: str) -> float:
        """Check for modular code structure."""
        score = 0.4

        lines = code.split("\n")
        total_lines = len([l for l in lines if l.strip()])

        if language == "python":
            # Count functions
            functions = len(re.findall(r'def\s+\w+', code))
            # Count classes
            classes = len(re.findall(r'class\s+\w+', code))
        else:
            functions = len(re.findall(r'function\s+\w+', code)) + len(re.findall(r'const\s+\w+\s*=\s*\(', code))
            classes = len(re.findall(r'class\s+\w+', code))

        # Good ratio of functions to code length
        if total_lines > 20 and functions > 1:
            score += 0.2
        if total_lines > 50 and functions > 3:
            score += 0.2
        if classes > 0:
            score += 0.1

        # Check for helper functions (small, focused functions)
        small_functions = 0
        in_function = False
        function_lines = 0
        for line in lines:
            if re.match(r'\s*def\s+', line) or re.match(r'\s*function\s+', line):
                if in_function and function_lines < 15:
                    small_functions += 1
                in_function = True
                function_lines = 0
            elif in_function:
                function_lines += 1

        if small_functions > 0:
            score += 0.1

        return min(1.0, score)

    def _check_dry(self, code: str, language: str) -> float:
        """Check for DRY principle (no repetition)."""
        score = 0.6

        lines = [l.strip() for l in code.split("\n") if l.strip()]

        # Check for duplicate lines
        duplicates = len(lines) - len(set(lines))
        dup_ratio = duplicates / max(1, len(lines))

        if dup_ratio == 0:
            score += 0.2
        elif dup_ratio < 0.05:
            score += 0.1
        elif dup_ratio > 0.15:
            score -= 0.2

        # Check for repeated string literals
        strings = re.findall(r'["\'][^"\']+["\']', code)
        if strings:
            unique_strings = len(set(strings))
            string_ratio = unique_strings / len(strings)
            if string_ratio > 0.8:
                score += 0.2

        return max(0.0, min(1.0, score))

    def _check_defensive(self, code: str, language: str) -> float:
        """Check for defensive coding practices."""
        score = 0.4

        # Input validation
        validation_patterns = [
            r'if\s+not\s+\w+',
            r'if\s+\w+\s+is\s+None',
            r'isinstance\(',
            r'typeof\s+',
            r'\.isValid\(',
            r'validate'
        ]

        for pattern in validation_patterns:
            if re.search(pattern, code):
                score += 0.1

        # Guard clauses (early returns)
        early_returns = len(re.findall(r'^\s{4,8}return\s', code, re.MULTILINE))
        if early_returns > 0:
            score += 0.1

        return min(1.0, score)

    def _check_readability(self, code: str, language: str) -> float:
        """Check for overall readability."""
        score = 0.5

        lines = code.split("\n")

        # Average line length
        non_empty_lines = [l for l in lines if l.strip()]
        if non_empty_lines:
            avg_line_length = sum(len(l) for l in non_empty_lines) / len(non_empty_lines)
            if avg_line_length < 60:
                score += 0.2
            elif avg_line_length < 80:
                score += 0.1

        # Nested depth (less nesting = more readable)
        max_indent = max((len(l) - len(l.lstrip())) for l in lines if l.strip())
        if max_indent < 16:  # 4 levels of nesting
            score += 0.15
        elif max_indent < 24:
            score += 0.08

        # Consistent spacing
        if all("  " not in l.replace("    ", "") for l in lines):  # No double spaces (except indent)
            score += 0.1

        return min(1.0, score)

    def _determine_tier(self, score: float) -> QualityTier:
        """Determine quality tier from score."""
        for tier in [QualityTier.ELITE, QualityTier.EXCELLENT, QualityTier.GOOD, QualityTier.ACCEPTABLE]:
            if score >= self.tier_thresholds[tier]:
                return tier
        return QualityTier.NEEDS_WORK

    def _identify_gaps(self, pattern_scores: Dict[str, float]) -> List[str]:
        """Identify patterns where we're below Claude/Cursor baseline."""
        gaps = []
        claude_patterns = self.competitive_baseline["claude"]["patterns"]

        for pattern, score in pattern_scores.items():
            if pattern in claude_patterns:
                if score < claude_patterns[pattern] - 0.1:  # More than 10% below
                    gaps.append(f"{pattern}: {score:.2f} vs Claude's {claude_patterns[pattern]:.2f}")

        return gaps

    def _identify_strengths(self, pattern_scores: Dict[str, float]) -> List[str]:
        """Identify patterns where we're at or above Claude/Cursor level."""
        strengths = []
        claude_patterns = self.competitive_baseline["claude"]["patterns"]

        for pattern, score in pattern_scores.items():
            if pattern in claude_patterns:
                if score >= claude_patterns[pattern]:
                    strengths.append(f"{pattern}: {score:.2f} (at Claude level)")
            elif score >= 0.8:
                strengths.append(f"{pattern}: {score:.2f}")

        return strengths

    async def _generate_suggestions(
        self,
        code: str,
        gaps: List[str],
        language: str
    ) -> List[str]:
        """Generate improvement suggestions based on gaps."""
        suggestions = []

        for gap in gaps[:3]:  # Top 3 gaps
            pattern = gap.split(":")[0]

            suggestion_map = {
                "clear_naming": "Use more descriptive variable and function names",
                "proper_structure": "Improve code organization with logical grouping",
                "error_handling": "Add try/except blocks and handle edge cases",
                "documentation": "Add docstrings and clarifying comments",
                "type_hints": f"Add type annotations for better clarity",
                "edge_cases": "Add checks for null, empty, and boundary conditions",
                "modularity": "Break large functions into smaller, focused ones",
                "dry_principle": "Extract repeated code into reusable functions",
                "defensive_coding": "Add input validation and guard clauses",
                "readability": "Reduce line length and nesting depth"
            }

            if pattern in suggestion_map:
                suggestions.append(suggestion_map[pattern])

        return suggestions

    def _calculate_competitive_position(
        self,
        score: float,
        pattern_scores: Dict[str, float]
    ) -> str:
        """Calculate competitive position vs Claude/Cursor."""
        claude_avg = self.competitive_baseline["claude"]["avg_score"]
        cursor_avg = self.competitive_baseline["cursor"]["avg_score"]

        if score >= claude_avg:
            return f"ABOVE Claude level ({score:.2f} vs {claude_avg:.2f})"
        elif score >= cursor_avg:
            return f"Above Cursor, approaching Claude ({score:.2f})"
        elif score >= cursor_avg - 0.1:
            return f"Near Cursor level ({score:.2f} vs {cursor_avg:.2f})"
        else:
            gap = cursor_avg - score
            return f"Below Cursor by {gap:.2f} points"

    def _update_metrics(self, result: BenchmarkResult):
        """Update improvement metrics."""
        # Update tier counts
        if result.quality_tier == QualityTier.ELITE:
            self.improvement_metrics["elite_count"] += 1
        elif result.quality_tier == QualityTier.EXCELLENT:
            self.improvement_metrics["excellent_count"] += 1

        # Update average score
        total = self.improvement_metrics["total_benchmarks"]
        old_avg = self.improvement_metrics["avg_score"]
        self.improvement_metrics["avg_score"] = (old_avg * (total - 1) + result.overall_score) / total

        # Update trend
        self.improvement_metrics["score_trend"].append(result.overall_score)
        if len(self.improvement_metrics["score_trend"]) > 100:
            self.improvement_metrics["score_trend"] = self.improvement_metrics["score_trend"][-100:]

        # Update common gaps
        for gap in result.gaps:
            pattern = gap.split(":")[0]
            self.improvement_metrics["common_gaps"][pattern] = \
                self.improvement_metrics["common_gaps"].get(pattern, 0) + 1

        # Update common strengths
        for strength in result.strengths:
            pattern = strength.split(":")[0]
            self.improvement_metrics["common_strengths"][pattern] = \
                self.improvement_metrics["common_strengths"].get(pattern, 0) + 1

    def get_improvement_report(self) -> Dict[str, Any]:
        """Get a report on quality improvement over time."""
        trend = self.improvement_metrics["score_trend"]

        if len(trend) < 2:
            trend_direction = "insufficient_data"
            trend_value = 0.0
        else:
            recent_avg = sum(trend[-20:]) / len(trend[-20:])
            older_avg = sum(trend[:-20]) / len(trend[:-20]) if len(trend) > 20 else trend[0]
            trend_value = recent_avg - older_avg

            if trend_value > 0.05:
                trend_direction = "improving"
            elif trend_value < -0.05:
                trend_direction = "declining"
            else:
                trend_direction = "stable"

        # Calculate Claude/Cursor gap
        claude_gap = self.competitive_baseline["claude"]["avg_score"] - self.improvement_metrics["avg_score"]
        cursor_gap = self.competitive_baseline["cursor"]["avg_score"] - self.improvement_metrics["avg_score"]

        return {
            "total_benchmarks": self.improvement_metrics["total_benchmarks"],
            "elite_rate": self.improvement_metrics["elite_count"] / max(1, self.improvement_metrics["total_benchmarks"]),
            "excellent_rate": self.improvement_metrics["excellent_count"] / max(1, self.improvement_metrics["total_benchmarks"]),
            "average_score": self.improvement_metrics["avg_score"],
            "trend": {
                "direction": trend_direction,
                "value": trend_value
            },
            "competitive_gaps": {
                "vs_claude": claude_gap,
                "vs_cursor": cursor_gap
            },
            "top_gaps": sorted(
                self.improvement_metrics["common_gaps"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "top_strengths": sorted(
                self.improvement_metrics["common_strengths"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            "recommendation": self._generate_recommendation()
        }

    def _generate_recommendation(self) -> str:
        """Generate a recommendation based on metrics."""
        gaps = self.improvement_metrics["common_gaps"]

        if not gaps:
            return "Continue current approach - no data yet"

        top_gap = max(gaps.items(), key=lambda x: x[1])[0]

        recommendations = {
            "error_handling": "Focus on adding comprehensive error handling and edge case coverage",
            "documentation": "Improve documentation with clear docstrings and inline comments",
            "type_hints": "Add type annotations to function signatures and variables",
            "edge_cases": "Add more checks for null, empty, and boundary conditions",
            "modularity": "Break down large functions into smaller, focused units",
            "clear_naming": "Use more descriptive names for variables and functions",
            "proper_structure": "Improve code organization and logical grouping"
        }

        return recommendations.get(top_gap, f"Focus on improving {top_gap}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get benchmark metrics."""
        return {
            **self.improvement_metrics,
            "benchmarks_stored": len(self._benchmarks),
            "target_baseline": {
                "claude": self.competitive_baseline["claude"]["avg_score"],
                "cursor": self.competitive_baseline["cursor"]["avg_score"]
            }
        }
