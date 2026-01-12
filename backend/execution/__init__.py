"""
Grace Execution Layer

Bridges Grace's cognitive systems with code execution capabilities.
Uses OpenHands-style runtime for sandboxed execution.
"""

from .actions import GraceAction, ActionResult
from .bridge import ExecutionBridge
from .feedback import FeedbackProcessor

__all__ = [
    "GraceAction",
    "ActionResult",
    "ExecutionBridge",
    "FeedbackProcessor",
]
