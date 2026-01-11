"""
LLM Orchestration System for GRACE

Manages multiple open-source LLMs with:
- Read-only repository access
- Cognitive framework enforcement
- Hallucination mitigation
- Layer 1 + Learning Memory integration
- Inter-LLM collaboration
- Autonomous learning loops
"""

from .multi_llm_client import MultiLLMClient, LLMModel
from .repo_access import RepositoryAccessLayer
from .hallucination_guard import HallucinationGuard, ConsensusResult
from .cognitive_enforcer import CognitiveEnforcer
from .llm_collaboration import LLMCollaborationHub
from .learning_integration import LearningIntegration

__all__ = [
    'MultiLLMClient',
    'LLMModel',
    'RepositoryAccessLayer',
    'HallucinationGuard',
    'ConsensusResult',
    'CognitiveEnforcer',
    'LLMCollaborationHub',
    'LearningIntegration',
]
