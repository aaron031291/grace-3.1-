"""
Oracle Intelligence System for Grace
======================================

The Oracle is Grace's predictive intelligence system that enables:
1. 7-step forward simulation (thinking ahead like chess)
2. Cascading failure prediction and prevention
3. Proactive learning from all interactions
4. AI research storage with Genesis key tracking
5. User intent prediction
6. Pattern recognition and learning

Components:
- OracleCore: Central intelligence hub
- CascadingFailurePredictor: Predicts and prevents cascade failures
- ProactiveLearningSystem: Real-time learning pipeline

The Oracle sees what others miss, predicts issues before they happen,
and continuously improves through learning.
"""

from .oracle_core import (
    OracleCore,
    OracleInsight,
    InsightType,
    ConfidenceLevel,
    ResearchEntry,
    ForwardSimulation
)

from .cascading_failure_predictor import (
    CascadingFailurePredictor,
    CascadeAnalysis,
    CascadeChain,
    ComponentNode,
    FailureMode,
    PropagationPattern,
    RiskLevel
)

from .proactive_learning import (
    ProactiveLearningSystem,
    LearningEvent,
    LearningPriority,
    LearningItem,
    LearnedPattern,
    UserIntentModel
)

__all__ = [
    # Oracle Core
    'OracleCore',
    'OracleInsight',
    'InsightType',
    'ConfidenceLevel',
    'ResearchEntry',
    'ForwardSimulation',

    # Cascading Failure Predictor
    'CascadingFailurePredictor',
    'CascadeAnalysis',
    'CascadeChain',
    'ComponentNode',
    'FailureMode',
    'PropagationPattern',
    'RiskLevel',

    # Proactive Learning
    'ProactiveLearningSystem',
    'LearningEvent',
    'LearningPriority',
    'LearningItem',
    'LearnedPattern',
    'UserIntentModel',
]
