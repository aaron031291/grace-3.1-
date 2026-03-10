"""
Ambiguity Accounting System for Grace.

Implements Invariant 2: Explicit Ambiguity Accounting.
Tracks what is known, inferred, assumed, and unknown.
"""
from datetime import timezone
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


class AmbiguityLevel(str, Enum):
    """Classification of information certainty."""
    KNOWN = "known"  # Facts we have verified
    INFERRED = "inferred"  # Derived from known facts
    ASSUMED = "assumed"  # Assumptions we're making
    UNKNOWN = "unknown"  # Gaps in knowledge


@dataclass
class AmbiguityEntry:
    """A single entry in the ambiguity ledger."""
    key: str
    value: Any
    level: AmbiguityLevel
    confidence: Optional[float] = None  # 0.0 to 1.0 for inferences
    blocking: bool = False  # Does this block irreversible actions?
    notes: str = ""
    created_at: str = field(default_factory=lambda: str(__import__('datetime').datetime.now(timezone.utc)))


class AmbiguityLedger:
    """
    Tracks the ambiguity state of all information in a decision.

    Implements Invariant 2: All decisions must account for ambiguity.
    Unknowns that block irreversible steps halt execution.
    """

    def __init__(self):
        self._entries: Dict[str, AmbiguityEntry] = {}

    def add_known(self, key: str, value: Any, notes: str = "") -> None:
        """
        Add a known fact.

        Args:
            key: Identifier for this fact
            value: The known value
            notes: Optional notes about this fact
        """
        entry = AmbiguityEntry(
            key=key,
            value=value,
            level=AmbiguityLevel.KNOWN,
            confidence=1.0,
            blocking=False,
            notes=notes
        )
        self._entries[key] = entry

    def add_inferred(
        self,
        key: str,
        value: Any,
        confidence: float,
        notes: str = ""
    ) -> None:
        """
        Add an inferred fact.

        Args:
            key: Identifier for this inference
            value: The inferred value
            confidence: Confidence level (0.0 to 1.0)
            notes: Optional notes about the inference
        """
        entry = AmbiguityEntry(
            key=key,
            value=value,
            level=AmbiguityLevel.INFERRED,
            confidence=confidence,
            blocking=confidence < 0.7,  # Low confidence inferences block
            notes=notes
        )
        self._entries[key] = entry

    def add_assumed(
        self,
        key: str,
        value: Any,
        must_validate: bool = True,
        notes: str = ""
    ) -> None:
        """
        Add an assumption.

        Args:
            key: Identifier for this assumption
            value: The assumed value
            must_validate: If True, this must be validated before irreversible action
            notes: Optional notes about the assumption
        """
        entry = AmbiguityEntry(
            key=key,
            value=value,
            level=AmbiguityLevel.ASSUMED,
            confidence=None,
            blocking=must_validate,
            notes=notes
        )
        self._entries[key] = entry

    def add_unknown(
        self,
        key: str,
        blocking: bool = True,
        notes: str = ""
    ) -> None:
        """
        Record an unknown (gap in knowledge).

        Args:
            key: Identifier for this unknown
            blocking: If True, blocks irreversible actions
            notes: Optional notes about what's unknown
        """
        entry = AmbiguityEntry(
            key=key,
            value=None,
            level=AmbiguityLevel.UNKNOWN,
            confidence=None,
            blocking=blocking,
            notes=notes
        )
        self._entries[key] = entry

    def get(self, key: str) -> Optional[AmbiguityEntry]:
        """
        Get an ambiguity entry by key.

        Args:
            key: Identifier to lookup

        Returns:
            AmbiguityEntry or None if not found
        """
        return self._entries.get(key)

    def get_all(self) -> Dict[str, AmbiguityEntry]:
        """
        Get all ambiguity entries.

        Returns:
            Dictionary of all entries
        """
        return self._entries.copy()

    def get_by_level(self, level: AmbiguityLevel) -> List[AmbiguityEntry]:
        """
        Get all entries at a specific ambiguity level.

        Args:
            level: Ambiguity level to filter by

        Returns:
            List of entries at that level
        """
        return [
            entry for entry in self._entries.values()
            if entry.level == level
        ]

    def get_blocking_unknowns(self) -> List[AmbiguityEntry]:
        """
        Get all unknowns that block irreversible actions.

        Returns:
            List of blocking unknown entries
        """
        return [
            entry for entry in self._entries.values()
            if entry.level == AmbiguityLevel.UNKNOWN and entry.blocking
        ]

    def get_blocking_items(self) -> List[AmbiguityEntry]:
        """
        Get all items (of any level) that block irreversible actions.

        Returns:
            List of blocking entries
        """
        return [
            entry for entry in self._entries.values()
            if entry.blocking
        ]

    def has_blocking_unknowns(self) -> bool:
        """
        Check if there are any blocking unknowns.

        Returns:
            True if blocking unknowns exist
        """
        return len(self.get_blocking_unknowns()) > 0

    def promote_to_known(self, key: str, value: Any) -> None:
        """
        Promote an unknown/assumed/inferred item to known.

        Args:
            key: Identifier to promote
            value: The now-known value
        """
        if key in self._entries:
            old_entry = self._entries[key]
            self._entries[key] = AmbiguityEntry(
                key=key,
                value=value,
                level=AmbiguityLevel.KNOWN,
                confidence=1.0,
                blocking=False,
                notes=f"Promoted from {old_entry.level}. {old_entry.notes}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ledger to dictionary format.

        Returns:
            Dictionary representation
        """
        return {
            'known': {
                e.key: e.value
                for e in self.get_by_level(AmbiguityLevel.KNOWN)
            },
            'inferred': [
                {
                    'key': e.key,
                    'value': e.value,
                    'confidence': e.confidence,
                    'notes': e.notes
                }
                for e in self.get_by_level(AmbiguityLevel.INFERRED)
            ],
            'assumed': [
                {
                    'key': e.key,
                    'value': e.value,
                    'must_validate': e.blocking,
                    'notes': e.notes
                }
                for e in self.get_by_level(AmbiguityLevel.ASSUMED)
            ],
            'unknown': [
                {
                    'key': e.key,
                    'blocking': e.blocking,
                    'notes': e.notes
                }
                for e in self.get_by_level(AmbiguityLevel.UNKNOWN)
            ]
        }

    def summary(self) -> str:
        """
        Get a human-readable summary of the ambiguity state.

        Returns:
            Summary string
        """
        known_count = len(self.get_by_level(AmbiguityLevel.KNOWN))
        inferred_count = len(self.get_by_level(AmbiguityLevel.INFERRED))
        assumed_count = len(self.get_by_level(AmbiguityLevel.ASSUMED))
        unknown_count = len(self.get_by_level(AmbiguityLevel.UNKNOWN))
        blocking_count = len(self.get_blocking_items())

        return (
            f"Ambiguity State: "
            f"{known_count} known, "
            f"{inferred_count} inferred, "
            f"{assumed_count} assumed, "
            f"{unknown_count} unknown "
            f"({blocking_count} blocking)"
        )
