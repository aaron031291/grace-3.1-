"""
LLM Orchestration System for GRACE

Manages multiple open-source LLMs with:
- Read-only repository access
- Cognitive framework enforcement
- Hallucination mitigation
- Layer 1 + Learning Memory integration
- Inter-LLM collaboration
- Autonomous learning loops

Enhanced for Claude/Cursor-level quality with:
- Code Quality Optimizer
- Chain-of-Thought Reasoning
- Competitive Benchmarking
- Parliament Governance (multi-model consensus)
- KPI & Trust Scoring
- Anti-Hallucination Verification

NO THIRD-PARTY API DEPENDENCIES - ALL LOCAL INFERENCE VIA OLLAMA.
"""

from .multi_llm_client import MultiLLMClient, LLMModel
from .repo_access import RepositoryAccessLayer
from .hallucination_guard import HallucinationGuard, ConsensusResult
from .cognitive_enforcer import CognitiveEnforcer
from .llm_collaboration import LLMCollaborationHub
from .learning_integration import LearningIntegration

# Enhanced quality systems for Claude/Cursor-level output
from .code_quality_optimizer import (
    CodeQualityOptimizer,
    CodeGenerationResult,
    QualityScore,
    RefinementStrategy,
    DeepSeekOptimizer
)
from .chain_of_thought import (
    ChainOfThoughtReasoner,
    ReasoningChain,
    ReasoningMode,
    ThinkingStep
)
from .competitive_benchmark import (
    CompetitiveBenchmark,
    BenchmarkResult,
    QualityTier,
    CodePattern
)
from .parliament_governance import (
    ParliamentGovernance,
    ParliamentSession,
    DecisionType,
    GovernanceLevel,
    ModelTrust,
    KPIMetrics,
    VoteType
)
from .enhanced_orchestrator import (
    EnhancedOrchestrator,
    EnhancedGenerationResult,
    QualityMode,
    generate_high_quality_code,
    generate_claude_level_code
)

__all__ = [
    # Core LLM components
    'MultiLLMClient',
    'LLMModel',
    'RepositoryAccessLayer',
    'HallucinationGuard',
    'ConsensusResult',
    'CognitiveEnforcer',
    'LLMCollaborationHub',
    'LearningIntegration',

    # Code Quality Optimizer
    'CodeQualityOptimizer',
    'CodeGenerationResult',
    'QualityScore',
    'RefinementStrategy',
    'DeepSeekOptimizer',

    # Chain-of-Thought Reasoning
    'ChainOfThoughtReasoner',
    'ReasoningChain',
    'ReasoningMode',
    'ThinkingStep',

    # Competitive Benchmarking
    'CompetitiveBenchmark',
    'BenchmarkResult',
    'QualityTier',
    'CodePattern',

    # Parliament Governance
    'ParliamentGovernance',
    'ParliamentSession',
    'DecisionType',
    'GovernanceLevel',
    'ModelTrust',
    'KPIMetrics',
    'VoteType',

    # Enhanced Orchestrator
    'EnhancedOrchestrator',
    'EnhancedGenerationResult',
    'QualityMode',
    'generate_high_quality_code',
    'generate_claude_level_code',
]
