"""
GRACE Native CI/CD System
==========================

Self-contained testing and automation within GRACE.
No external services required.
"""

from .native_test_runner import NativeTestRunner, TestStatus, TestResult
from .auto_actions import AutoActionsManager, Action, ActionType, TriggerType

__all__ = [
    'NativeTestRunner',
    'TestStatus',
    'TestResult',
    'AutoActionsManager',
    'Action',
    'ActionType',
    'TriggerType',
]
