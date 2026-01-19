"""
COVI-SHIELD Repair Engine

Automatically generates and validates fixes for detected issues.

Strategies:
- Template-based repair
- Program synthesis
- Constraint-based repair
- Pattern-matching repair
"""

import ast
import re
import hashlib
import logging
import time
import difflib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .models import (
    RepairSuggestion,
    RepairStrategy,
    BugCategory,
    RiskLevel
)

logger = logging.getLogger(__name__)


# ============================================================================
# REPAIR TEMPLATES
# ============================================================================

REPAIR_TEMPLATES: Dict[str, Dict[str, Any]] = {
    # Security fixes
    "SEC-001": {
        "name": "SQL Injection Fix",
        "pattern": r'execute\s*\(\s*["\']([^"\']*%s[^"\']*)["\']',
        "template": "execute({query}, {params})",
        "description": "Use parameterized query to prevent SQL injection"
    },
    "SEC-002": {
        "name": "Shell Injection Fix",
        "pattern": r'shell\s*=\s*True',
        "replacement": "shell=False",
        "description": "Disable shell to prevent command injection"
    },
    "SEC-003": {
        "name": "Hardcoded Credentials Fix",
        "pattern": r'(password|api_key|secret)\s*=\s*["\'][^"\']+["\']',
        "template": '{var} = os.environ.get("{VAR}")',
        "description": "Use environment variable for credentials"
    },
    "SEC-004": {
        "name": "Pickle Deserialization Fix",
        "pattern": r'pickle\.loads?\(',
        "replacement": "json.loads(",
        "description": "Use json.loads instead of pickle for untrusted data"
    },

    # Syntax fixes
    "SYN-001": {
        "name": "Bare Except Fix",
        "pattern": r'except\s*:',
        "replacement": "except Exception as e:",
        "description": "Specify exception type"
    },
    "SYN-002": {
        "name": "Mutable Default Fix",
        "pattern": r'def\s+(\w+)\s*\([^)]*=\s*(\[\]|\{\})',
        "template": "def {func}({args}=None):\n    if {arg} is None:\n        {arg} = {default}",
        "description": "Use None as default for mutable arguments"
    },

    # Logic fixes
    "LOGIC-003": {
        "name": "None Comparison Fix",
        "pattern": r'==\s*None',
        "replacement": "is None",
        "description": "Use 'is None' for None comparison"
    },
    "LOGIC-003-NEQ": {
        "name": "Not None Comparison Fix",
        "pattern": r'!=\s*None',
        "replacement": "is not None",
        "description": "Use 'is not None' for None comparison"
    },

    # Memory fixes
    "MEM-001": {
        "name": "Resource Leak Fix",
        "pattern": r'(\w+)\s*=\s*open\s*\(([^)]+)\)',
        "template": "with open({args}) as {var}:",
        "description": "Use context manager for resource management"
    },

    # Numerical fixes
    "NUM-001": {
        "name": "Division by Zero Fix",
        "pattern": r'/\s*(\w+)',
        "template": "/ ({var} if {var} != 0 else 1)",
        "description": "Add zero check before division"
    },
    "NUM-002": {
        "name": "Float Comparison Fix",
        "pattern": r'==\s*(\d+\.\d+)',
        "template": "math.isclose(, {value})",
        "description": "Use math.isclose for float comparison"
    },
    "NUM-003": {
        "name": "Gradient Clipping Fix",
        "pattern": r'\.backward\(\)',
        "template": ".backward()\ntorch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)",
        "description": "Add gradient clipping after backward"
    },

    # API fixes
    "API-001": {
        "name": "Deprecated API Fix",
        "pattern": r'@asyncio\.coroutine',
        "replacement": "async def",
        "description": "Use async def instead of @coroutine"
    },
    "API-002": {
        "name": "Missing Error Handling Fix",
        "pattern": r'requests\.(get|post|put|delete)\s*\(',
        "template": "try:\n    response = requests.{method}({args})\n    response.raise_for_status()\nexcept requests.RequestException as e:\n    logger.error(f'Request failed: {e}')\n    raise",
        "description": "Add error handling for HTTP requests"
    },
}


# ============================================================================
# REPAIR ENGINE
# ============================================================================

class RepairEngine:
    """
    COVI-SHIELD Repair Engine.

    Automatically generates fixes using:
    - Template-based repair for known patterns
    - AST transformation for structural fixes
    - Diff generation for validation
    """

    def __init__(self):
        self.templates = REPAIR_TEMPLATES
        self.stats = {
            "total_repairs": 0,
            "successful_repairs": 0,
            "failed_repairs": 0,
            "repairs_by_type": {}
        }
        logger.info(f"[COVI-SHIELD] Repair Engine initialized with {len(self.templates)} templates")

    def generate_repair(
        self,
        code: str,
        issue: Dict[str, Any],
        strategy: RepairStrategy = RepairStrategy.TEMPLATE,
        genesis_key_id: Optional[str] = None
    ) -> RepairSuggestion:
        """
        Generate a repair suggestion for an issue.

        Args:
            code: Original source code
            issue: Issue dict with pattern_id, line, etc.
            strategy: Repair strategy to use
            genesis_key_id: Associated Genesis Key

        Returns:
            RepairSuggestion with fix details
        """
        start_time = time.time()
        self.stats["total_repairs"] += 1

        pattern_id = issue.get("pattern_id", "")
        line_num = issue.get("line", 0)

        suggestion = RepairSuggestion(
            genesis_key_id=genesis_key_id,
            issue_id=pattern_id,
            strategy=strategy,
            title=issue.get("name", "Fix"),
            description=issue.get("description", ""),
            original_code=code
        )

        if strategy == RepairStrategy.TEMPLATE:
            repaired_code, confidence = self._template_repair(code, issue)
        elif strategy == RepairStrategy.SYNTHESIS:
            repaired_code, confidence = self._synthesis_repair(code, issue)
        elif strategy == RepairStrategy.CONSTRAINT:
            repaired_code, confidence = self._constraint_repair(code, issue)
        else:
            repaired_code, confidence = self._template_repair(code, issue)

        if repaired_code and repaired_code != code:
            suggestion.repaired_code = repaired_code
            suggestion.confidence = confidence
            suggestion.diff = self._generate_diff(code, repaired_code)
            suggestion.validation_passed = self._validate_repair(repaired_code)

            if suggestion.validation_passed:
                self.stats["successful_repairs"] += 1
            else:
                self.stats["failed_repairs"] += 1

            # Track by type
            self.stats["repairs_by_type"][pattern_id] = \
                self.stats["repairs_by_type"].get(pattern_id, 0) + 1

        logger.info(
            f"[COVI-SHIELD] Generated repair for {pattern_id}: "
            f"confidence={confidence:.2f}, valid={suggestion.validation_passed}"
        )

        return suggestion

    def _template_repair(
        self,
        code: str,
        issue: Dict[str, Any]
    ) -> Tuple[str, float]:
        """Apply template-based repair."""
        pattern_id = issue.get("pattern_id", "")
        template = self.templates.get(pattern_id)

        if not template:
            # Try generic pattern matching
            return self._generic_repair(code, issue)

        lines = code.split("\n")
        line_num = issue.get("line", 0)

        if "replacement" in template:
            # Simple replacement
            pattern = template["pattern"]
            replacement = template["replacement"]

            repaired_code = re.sub(pattern, replacement, code)
            return repaired_code, 0.9 if repaired_code != code else 0.0

        elif "template" in template:
            # Template-based transformation
            # Extract variables from match
            pattern = template["pattern"]
            match = re.search(pattern, code)

            if match:
                # Apply template with captured groups
                repaired_code = code
                # This would need more sophisticated template application
                return self._apply_template(code, template, match), 0.85

        return code, 0.0

    def _apply_template(
        self,
        code: str,
        template: Dict[str, Any],
        match: re.Match
    ) -> str:
        """Apply a template to generate fixed code."""
        # Extract groups from match
        groups = match.groups() if match else ()

        if template.get("template"):
            # For now, do simple replacement
            replacement = template.get("replacement", template.get("template", ""))
            return code[:match.start()] + replacement + code[match.end():]

        return code

    def _generic_repair(
        self,
        code: str,
        issue: Dict[str, Any]
    ) -> Tuple[str, float]:
        """Apply generic repair based on issue type."""
        category = issue.get("category", "")
        line_num = issue.get("line", 0)
        repair_template = issue.get("repair_template", "")

        if not repair_template:
            return code, 0.0

        lines = code.split("\n")

        if 0 < line_num <= len(lines):
            # Generate a comment with the fix suggestion
            original_line = lines[line_num - 1]
            indent = len(original_line) - len(original_line.lstrip())
            comment = f"{' ' * indent}# COVI-SHIELD: {repair_template}"

            # Insert comment above the problematic line
            lines.insert(line_num - 1, comment)

            return "\n".join(lines), 0.5

        return code, 0.0

    def _synthesis_repair(
        self,
        code: str,
        issue: Dict[str, Any]
    ) -> Tuple[str, float]:
        """Apply program synthesis repair."""
        # Simplified: use constraint-based approach
        return self._constraint_repair(code, issue)

    def _constraint_repair(
        self,
        code: str,
        issue: Dict[str, Any]
    ) -> Tuple[str, float]:
        """Apply constraint-based repair."""
        pattern_id = issue.get("pattern_id", "")

        # Specific constraint-based fixes
        if pattern_id == "NUM-001":
            # Division by zero - add guard
            return self._fix_division_by_zero(code, issue)

        elif pattern_id == "MEM-001":
            # Resource leak - convert to context manager
            return self._fix_resource_leak(code, issue)

        elif pattern_id.startswith("SEC-"):
            # Security issues
            return self._fix_security_issue(code, issue)

        return self._template_repair(code, issue)

    def _fix_division_by_zero(
        self,
        code: str,
        issue: Dict[str, Any]
    ) -> Tuple[str, float]:
        """Fix potential division by zero."""
        line_num = issue.get("line", 0)
        lines = code.split("\n")

        if 0 < line_num <= len(lines):
            line = lines[line_num - 1]

            # Find division operation
            div_match = re.search(r'/\s*(\w+)', line)
            if div_match:
                var_name = div_match.group(1)
                # Add check before division
                indent = len(line) - len(line.lstrip())
                guard = f"{' ' * indent}if {var_name} == 0:\n{' ' * indent}    raise ValueError(f'{var_name} cannot be zero')"

                lines.insert(line_num - 1, guard)
                return "\n".join(lines), 0.85

        return code, 0.0

    def _fix_resource_leak(
        self,
        code: str,
        issue: Dict[str, Any]
    ) -> Tuple[str, float]:
        """Fix resource leak by converting to context manager."""
        # Find open() calls not in with statement
        pattern = r'(\w+)\s*=\s*open\s*\(([^)]+)\)'
        match = re.search(pattern, code)

        if match:
            var_name = match.group(1)
            args = match.group(2)

            # Find the scope of the file usage (simplified)
            # Replace with context manager
            replacement = f"with open({args}) as {var_name}:"

            # This is simplified - real implementation would restructure code
            repaired = code.replace(match.group(0), replacement)
            return repaired, 0.7

        return code, 0.0

    def _fix_security_issue(
        self,
        code: str,
        issue: Dict[str, Any]
    ) -> Tuple[str, float]:
        """Fix security issues."""
        pattern_id = issue.get("pattern_id", "")

        if pattern_id == "SEC-001":
            # SQL injection - parameterize queries
            pattern = r'execute\s*\(\s*["\']([^"\']*%s[^"\']*)["\']'
            if re.search(pattern, code):
                # Add comment about parameterization
                return code.replace(
                    "execute(",
                    "# COVI-SHIELD: Use parameterized queries\n# execute(sql, (param,)) instead of string formatting\nexecute("
                ), 0.6

        elif pattern_id == "SEC-002":
            # Shell injection
            return code.replace("shell=True", "shell=False"), 0.9

        elif pattern_id == "SEC-004":
            # Pickle
            repaired = code.replace("pickle.loads(", "json.loads(")
            repaired = repaired.replace("pickle.load(", "json.load(")
            if repaired != code:
                # Add import if needed
                if "import json" not in repaired:
                    repaired = "import json\n" + repaired
                return repaired, 0.85

        return self._template_repair(code, issue)

    def _generate_diff(self, original: str, repaired: str) -> str:
        """Generate unified diff between original and repaired code."""
        original_lines = original.split("\n")
        repaired_lines = repaired.split("\n")

        diff = difflib.unified_diff(
            original_lines,
            repaired_lines,
            fromfile="original",
            tofile="repaired",
            lineterm=""
        )

        return "\n".join(diff)

    def _validate_repair(self, code: str) -> bool:
        """Validate that repaired code is syntactically correct."""
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def repair_all(
        self,
        code: str,
        issues: List[Dict[str, Any]],
        genesis_key_id: Optional[str] = None
    ) -> Tuple[str, List[RepairSuggestion]]:
        """
        Apply all possible repairs to code.

        Args:
            code: Original code
            issues: List of issues to fix
            genesis_key_id: Associated Genesis Key

        Returns:
            Tuple of (repaired_code, list of suggestions)
        """
        suggestions = []
        current_code = code

        # Sort issues by line number descending to avoid offset issues
        sorted_issues = sorted(
            issues,
            key=lambda x: x.get("line", 0),
            reverse=True
        )

        for issue in sorted_issues:
            suggestion = self.generate_repair(
                current_code,
                issue,
                genesis_key_id=genesis_key_id
            )

            if suggestion.validation_passed and suggestion.repaired_code:
                current_code = suggestion.repaired_code
                suggestions.append(suggestion)

        return current_code, suggestions

    def add_template(self, pattern_id: str, template: Dict[str, Any]) -> None:
        """Add a new repair template."""
        self.templates[pattern_id] = template
        logger.info(f"[COVI-SHIELD] Added repair template: {pattern_id}")

    def get_stats(self) -> Dict[str, Any]:
        """Get repair engine statistics."""
        success_rate = (
            self.stats["successful_repairs"] / self.stats["total_repairs"]
            if self.stats["total_repairs"] > 0 else 0
        )
        return {
            **self.stats,
            "success_rate": success_rate,
            "templates_available": len(self.templates)
        }
