"""
Genesis IDE - Full Intelligence-Integrated Development Environment
===================================================================

Genesis IDE integrates ALL of Grace's cognitive capabilities into the IDE:

- Layer 1/2 Intelligence: Universal input/output with cognitive processing
- Cognitive Framework: OODA loop, multi-plane reasoning, problem-solving
- Clarity Framework: Clear intentions, traceable actions, verified outcomes
- Genesis Keys: Every action tracked, versioned, and auditable
- VectorDB Learning: Store failures, broken code, training data
- Librarian: Document curation and knowledge management
- File Manager: Intelligent file operations with genesis tracking
- Version Control: Mutation tracking after genesis key creation
- CI/CD Pipeline: Autonomous build, test, deploy
- Autonomous Actions: Self-healing, self-improving, self-updating

This is the "whole damn system" - everything is trackable and traceable.
"""

from .core_integration import GenesisIDECore
from .layer_intelligence import Layer1Intelligence, Layer2Intelligence
from .cognitive_ide import CognitiveIDEFramework
from .clarity_framework import ClarityFramework, ClarityContext
from .failure_learning import FailureLearningSystem
from .mutation_tracker import MutationTracker
from .self_updater import SelfUpdater

__all__ = [
    'GenesisIDECore',
    'Layer1Intelligence',
    'Layer2Intelligence',
    'CognitiveIDEFramework',
    'ClarityFramework',
    'ClarityContext',
    'FailureLearningSystem',
    'MutationTracker',
    'SelfUpdater',
]

__version__ = "1.0.0"
