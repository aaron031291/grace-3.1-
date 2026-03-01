"""
Grace OS — Error Patterns

Known error → fix mappings. Records patterns from past sessions so
Grace can recognize and apply proven fixes automatically.
"""

import logging
import time
from typing import Any, Dict, List, Optional, Tuple
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class ErrorPatterns:
    """
    Stores and retrieves known error patterns with their fixes.
    Supports fuzzy matching for error signature lookup.
    """

    def __init__(self):
        # error_signature -> pattern record
        self._patterns: Dict[str, Dict[str, Any]] = {}

    def record_pattern(
        self,
        error_signature: str,
        fix_description: str,
        success_rate: float = 1.0,
        context: Optional[Dict] = None,
    ):
        """Record a new error→fix mapping or update an existing one."""
        key = self._normalize(error_signature)

        if key in self._patterns:
            existing = self._patterns[key]
            existing["occurrences"] += 1
            existing["success_rate"] = (
                (existing["success_rate"] * (existing["occurrences"] - 1) + success_rate)
                / existing["occurrences"]
            )
            existing["last_seen"] = time.time()
            if fix_description not in existing["fixes"]:
                existing["fixes"].append(fix_description)
        else:
            self._patterns[key] = {
                "error_signature": error_signature,
                "fixes": [fix_description],
                "success_rate": success_rate,
                "occurrences": 1,
                "first_seen": time.time(),
                "last_seen": time.time(),
                "context": context or {},
            }

        logger.debug(f"[ErrorPatterns] Recorded pattern: {error_signature[:50]}...")

    def find_fix(self, error_signature: str, threshold: float = 0.6) -> Optional[Dict[str, Any]]:
        """
        Find a fix for an error. Uses fuzzy matching if exact match not found.
        Returns the best matching pattern or None.
        """
        key = self._normalize(error_signature)

        # Exact match
        if key in self._patterns:
            return self._patterns[key]

        # Fuzzy match
        best_match = None
        best_score = 0.0

        for stored_key, pattern in self._patterns.items():
            score = SequenceMatcher(None, key, stored_key).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = pattern

        return best_match

    def get_top_patterns(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get the most frequently occurring error patterns."""
        sorted_patterns = sorted(
            self._patterns.values(),
            key=lambda p: p["occurrences"],
            reverse=True,
        )
        return sorted_patterns[:n]

    def get_all_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Get all recorded patterns."""
        return dict(self._patterns)

    def _normalize(self, signature: str) -> str:
        """Normalize an error signature for matching."""
        return signature.strip().lower()
