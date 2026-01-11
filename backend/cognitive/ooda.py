"""
OODA Loop Implementation for Grace.

Implements Invariant 1: OODA as the Primary Control Loop.
All execution flows through Observe → Orient → Decide → Act.
"""
from enum import Enum
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from datetime import datetime


class OODAPhase(str, Enum):
    """Phases of the OODA loop."""
    OBSERVE = "observe"
    ORIENT = "orient"
    DECIDE = "decide"
    ACT = "act"
    COMPLETED = "completed"


@dataclass
class OODAState:
    """State of the OODA loop execution."""
    current_phase: OODAPhase = OODAPhase.OBSERVE
    observations: Dict[str, Any] = field(default_factory=dict)
    orientation: Dict[str, Any] = field(default_factory=dict)
    decision: Optional[Dict[str, Any]] = None
    action_result: Optional[Any] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class OODALoop:
    """
    OODA (Observe-Orient-Decide-Act) Loop controller.

    Ensures all operations follow the canonical control loop pattern.
    No direct execution paths bypass this loop.
    """

    def __init__(self):
        self.state = OODAState()
        self._phase_history: list[OODAPhase] = []

    def observe(self, observations: Dict[str, Any]) -> None:
        """
        OBSERVE: Gather information about the problem.

        What is the actual problem? What facts do we have?

        Args:
            observations: Dictionary of observed facts
        """
        if self.state.current_phase != OODAPhase.OBSERVE:
            raise ValueError(
                f"Cannot observe in phase {self.state.current_phase}. "
                "OODA loop must start with OBSERVE."
            )

        self.state.observations = observations
        self._advance_phase(OODAPhase.ORIENT)

    def orient(
        self,
        context: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        ORIENT: Understand the context and constraints.

        What context matters? What are the constraints?

        Args:
            context: Contextual information
            constraints: Constraints on the solution space
        """
        if self.state.current_phase != OODAPhase.ORIENT:
            raise ValueError(
                f"Cannot orient in phase {self.state.current_phase}. "
                "Must complete OBSERVE first."
            )

        self.state.orientation = {
            'context': context,
            'constraints': constraints or {}
        }
        self._advance_phase(OODAPhase.DECIDE)

    def decide(self, decision: Dict[str, Any]) -> None:
        """
        DECIDE: Choose a plan of action.

        What is the plan? What are the alternatives?

        Args:
            decision: The selected decision/plan
        """
        if self.state.current_phase != OODAPhase.DECIDE:
            raise ValueError(
                f"Cannot decide in phase {self.state.current_phase}. "
                "Must complete OBSERVE and ORIENT first."
            )

        self.state.decision = decision
        self._advance_phase(OODAPhase.ACT)

    def act(self, action: Callable[[], Any]) -> Any:
        """
        ACT: Execute the decided action with monitoring.

        Args:
            action: Function to execute

        Returns:
            Result of action execution
        """
        if self.state.current_phase != OODAPhase.ACT:
            raise ValueError(
                f"Cannot act in phase {self.state.current_phase}. "
                "Must complete OBSERVE, ORIENT, and DECIDE first."
            )

        result = action()
        self.state.action_result = result
        self._advance_phase(OODAPhase.COMPLETED)

        return result

    def reset(self) -> None:
        """Reset the OODA loop for a new cycle."""
        self.state = OODAState()
        self._phase_history = []

    def _advance_phase(self, next_phase: OODAPhase) -> None:
        """
        Advance to the next phase.

        Args:
            next_phase: Phase to advance to
        """
        self._phase_history.append(self.state.current_phase)
        self.state.current_phase = next_phase

        if next_phase == OODAPhase.COMPLETED:
            self.state.completed_at = datetime.utcnow()

    def get_phase_history(self) -> list[OODAPhase]:
        """
        Get the history of phases executed.

        Returns:
            List of phases in order
        """
        return self._phase_history.copy()

    def is_complete(self) -> bool:
        """
        Check if the OODA loop has completed.

        Returns:
            True if all phases completed
        """
        return self.state.current_phase == OODAPhase.COMPLETED

    def validate_completion(self) -> bool:
        """
        Validate that all phases were executed in order.

        Returns:
            True if loop executed correctly
        """
        expected_phases = [
            OODAPhase.OBSERVE,
            OODAPhase.ORIENT,
            OODAPhase.DECIDE,
            OODAPhase.ACT
        ]

        return self._phase_history == expected_phases
