"""
Grace Execution Layer

Bridges Grace's cognitive systems with code execution capabilities.
Uses OpenHands-style runtime for sandboxed execution.

Components:
- ExecutionBridge: Core execution without governance
- GovernedExecutionBridge: Execution with constitutional governance
- FeedbackProcessor: Learning signal generation
"""

from .actions import (
    GraceAction,
    ActionRequest,
    ActionResult,
    ActionStatus,
    create_action,
)
from .bridge import ExecutionBridge, ExecutionConfig, get_execution_bridge
from .governed_bridge import (
    GovernedExecutionBridge,
    get_governed_execution_bridge,
    ACTION_GOVERNANCE_MAP,
)
from .feedback import FeedbackProcessor

__all__ = [
    # Actions
    "GraceAction",
    "ActionRequest",
    "ActionResult",
    "ActionStatus",
    "create_action",
    # Bridges
    "ExecutionBridge",
    "ExecutionConfig",
    "get_execution_bridge",
    "GovernedExecutionBridge",
    "get_governed_execution_bridge",
    "ACTION_GOVERNANCE_MAP",
    # Feedback
    "FeedbackProcessor",
]
