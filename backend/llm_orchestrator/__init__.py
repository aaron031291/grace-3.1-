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

import logging
logger = logging.getLogger(__name__)

# Core LLM components - imported with fallbacks
try:
    from .multi_llm_client import MultiLLMClient, LLMModel
except ImportError as e:
    logger.warning(f"Could not import multi_llm_client: {e}")
    MultiLLMClient = None
    LLMModel = None

try:
    from .repo_access import RepositoryAccessLayer
except ImportError as e:
    logger.warning(f"Could not import repo_access: {e}")
    RepositoryAccessLayer = None

try:
    from .hallucination_guard import HallucinationGuard, ConsensusResult
except ImportError as e:
    logger.warning(f"Could not import hallucination_guard: {e}")
    HallucinationGuard = None
    ConsensusResult = None

try:
    from .cognitive_enforcer import CognitiveEnforcer
except ImportError as e:
    logger.warning(f"Could not import cognitive_enforcer: {e}")
    CognitiveEnforcer = None

try:
    from .llm_collaboration import LLMCollaborationHub
except ImportError as e:
    logger.warning(f"Could not import llm_collaboration: {e}")
    LLMCollaborationHub = None

try:
    from .learning_integration import LearningIntegration
except ImportError as e:
    logger.warning(f"Could not import learning_integration: {e}")
    LearningIntegration = None

# Enhanced quality systems for Claude/Cursor-level output
try:
    from .code_quality_optimizer import (
        CodeQualityOptimizer,
        CodeGenerationResult,
        QualityScore,
        RefinementStrategy,
        DeepSeekOptimizer
    )
except ImportError as e:
    logger.warning(f"Could not import code_quality_optimizer: {e}")
    CodeQualityOptimizer = None
    CodeGenerationResult = None
    QualityScore = None
    RefinementStrategy = None
    DeepSeekOptimizer = None

try:
    from .chain_of_thought import (
        ChainOfThoughtReasoner,
        ReasoningChain,
        ReasoningMode,
        ThinkingStep
    )
except ImportError as e:
    logger.warning(f"Could not import chain_of_thought: {e}")
    ChainOfThoughtReasoner = None
    ReasoningChain = None
    ReasoningMode = None
    ThinkingStep = None

try:
    from .competitive_benchmark import (
        CompetitiveBenchmark,
        BenchmarkResult,
        QualityTier,
        CodePattern
    )
except ImportError as e:
    logger.warning(f"Could not import competitive_benchmark: {e}")
    CompetitiveBenchmark = None
    BenchmarkResult = None
    QualityTier = None
    CodePattern = None

try:
    from .parliament_governance import (
        ParliamentGovernance,
        ParliamentSession,
        DecisionType,
        GovernanceLevel,
        ModelTrust,
        KPIMetrics,
        VoteType
    )
except ImportError as e:
    logger.warning(f"Could not import parliament_governance: {e}")
    ParliamentGovernance = None
    ParliamentSession = None
    DecisionType = None
    GovernanceLevel = None
    ModelTrust = None
    KPIMetrics = None
    VoteType = None

try:
    from .enhanced_orchestrator import (
        EnhancedOrchestrator,
        EnhancedGenerationResult,
        QualityMode,
        generate_high_quality_code,
        generate_claude_level_code
    )
except ImportError as e:
    logger.warning(f"Could not import enhanced_orchestrator: {e}")
    EnhancedOrchestrator = None
    EnhancedGenerationResult = None
    QualityMode = None
    generate_high_quality_code = None
    generate_claude_level_code = None

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
