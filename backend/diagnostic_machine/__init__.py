"""
GRACE Diagnostic Machine - 4-Layer Autonomous Diagnostic System

Integrates with:
- Test results (passed/failed/skipped)
- Genesis Keys (provenance tracking)
- Cognitive Framework (learning/memory)
- GRACE Mirror (self-reflection)
- Tail logs and metrics

Architecture:
- Layer 1: Sensors (data collection)
- Layer 2: Interpreters (pattern analysis)
- Layer 3: Judgement (decision making)
- Layer 4: Action Routing (response execution)
"""

from .sensors import SensorLayer, SensorData
from .interpreters import InterpreterLayer, InterpretedData
from .judgement import JudgementLayer, JudgementResult
from .action_router import ActionRouter, ActionDecision
from .diagnostic_engine import DiagnosticEngine

__all__ = [
    'SensorLayer',
    'SensorData',
    'InterpreterLayer',
    'InterpretedData',
    'JudgementLayer',
    'JudgementResult',
    'ActionRouter',
    'ActionDecision',
    'DiagnosticEngine',
]
