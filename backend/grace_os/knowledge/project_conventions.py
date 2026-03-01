"""
Grace OS — Project Conventions

Learned style rules, coding patterns, and anti-patterns.
Captures project-specific conventions from past sessions
for consistent code generation.
"""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ProjectConventions:
    """
    Stores and retrieves learned project conventions.
    Used by L6 (Codegen) and L8 (Verification) to enforce consistency.
    """

    def __init__(self):
        # rule_id -> convention record
        self._conventions: Dict[str, Dict[str, Any]] = {}
        self._counter = 0

    def record_convention(
        self,
        rule: str,
        source: str = "learned",
        confidence: float = 0.8,
        category: str = "general",
        examples: Optional[List[str]] = None,
    ) -> str:
        """
        Record a style/pattern convention.
        Returns the rule ID.
        """
        self._counter += 1
        rule_id = f"conv_{self._counter}"

        self._conventions[rule_id] = {
            "rule_id": rule_id,
            "rule": rule,
            "source": source,
            "confidence": confidence,
            "category": category,
            "examples": examples or [],
            "created": time.time(),
            "enforced_count": 0,
            "violated_count": 0,
        }

        logger.debug(f"[ProjectConventions] Recorded: {rule[:50]}...")
        return rule_id

    def get_conventions(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all conventions, optionally filtered by category."""
        conventions = list(self._conventions.values())
        if category:
            conventions = [c for c in conventions if c["category"] == category]
        return sorted(conventions, key=lambda c: c["confidence"], reverse=True)

    def get_convention(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific convention by ID."""
        return self._conventions.get(rule_id)

    def check_violation(self, code_snippet: str) -> List[Dict[str, Any]]:
        """
        Check if a code snippet violates any known conventions.
        Returns list of potentially violated conventions.
        Simple keyword-based check — in production, use AST analysis.
        """
        violations = []
        for conv in self._conventions.values():
            rule_lower = conv["rule"].lower()
            # Simple heuristic: check for anti-pattern keywords
            if "never" in rule_lower or "avoid" in rule_lower or "don't" in rule_lower:
                # Check if the code might contain the thing to avoid
                for example in conv.get("examples", []):
                    if example.lower() in code_snippet.lower():
                        violations.append(conv)
                        break
        return violations

    def record_enforcement(self, rule_id: str, was_violated: bool = False):
        """Track when a convention was enforced or violated."""
        if rule_id in self._conventions:
            if was_violated:
                self._conventions[rule_id]["violated_count"] += 1
            else:
                self._conventions[rule_id]["enforced_count"] += 1

    def get_categories(self) -> List[str]:
        """List all convention categories."""
        return list(set(c["category"] for c in self._conventions.values()))
