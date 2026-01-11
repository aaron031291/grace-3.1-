"""
ML Intelligence Module

Advanced machine learning and deep learning components for
autonomous learning enhancement.

Components:
- Neural Trust Scorer: Deep learning-based trust scoring
- Online Learning Pipeline: Continuous model updates
- Multi-Armed Bandit: Intelligent exploration/exploitation
- Meta-Learning: Learning optimization strategies
- Uncertainty Quantification: Bayesian confidence estimation
- Active Learning Sampler: Optimal training example selection
- Contrastive Learning: Better representation learning
"""

from .neural_trust_scorer import NeuralTrustScorer, get_neural_trust_scorer
from .online_learning_pipeline import (
    OnlineLearningPipeline,
    IncrementalEmbeddingLearner,
    get_online_learning_pipeline,
    get_incremental_embedder
)
from .multi_armed_bandit import (
    MultiArmedBandit,
    BanditAlgorithm,
    BanditContext,
    get_bandit
)
from .meta_learning import (
    MetaLearningOrchestrator,
    HyperparameterOptimizer,
    TaskSimilarityDetector,
    get_meta_learner
)
from .uncertainty_quantification import (
    UncertaintyQuantifier,
    BayesianNeuralNetwork,
    MCDropoutNetwork,
    UncertaintyEstimate,
    get_uncertainty_quantifier
)
from .active_learning_sampler import (
    ActiveLearningSampler,
    SamplingStrategy,
    get_active_sampler
)
from .contrastive_learning import (
    ContrastiveLearner,
    NTXentLoss,
    TripletLoss,
    SupervisedContrastiveLoss,
    get_contrastive_learner
)
from .trust_aware_embedding import (
    TrustAwareEmbeddingModel,
    TrustContext,
    get_trust_aware_embedding_model
)
from .neural_to_symbolic_rule_generator import (
    NeuralToSymbolicRuleGenerator,
    NeuralPattern,
    SymbolicRule,
    get_neural_to_symbolic_generator
)
from .neuro_symbolic_reasoner import (
    NeuroSymbolicReasoner,
    ReasoningResult,
    get_neuro_symbolic_reasoner
)
from .rule_storage import (
    RuleStorage,
    get_rule_storage
)

__all__ = [
    # Neural Trust Scorer
    'NeuralTrustScorer',
    'get_neural_trust_scorer',

    # Online Learning
    'OnlineLearningPipeline',
    'IncrementalEmbeddingLearner',
    'get_online_learning_pipeline',
    'get_incremental_embedder',

    # Multi-Armed Bandit
    'MultiArmedBandit',
    'BanditAlgorithm',
    'BanditContext',
    'get_bandit',

    # Meta-Learning
    'MetaLearningOrchestrator',
    'HyperparameterOptimizer',
    'TaskSimilarityDetector',
    'get_meta_learner',

    # Uncertainty Quantification
    'UncertaintyQuantifier',
    'BayesianNeuralNetwork',
    'MCDropoutNetwork',
    'UncertaintyEstimate',
    'get_uncertainty_quantifier',

    # Active Learning
    'ActiveLearningSampler',
    'SamplingStrategy',
    'get_active_sampler',

    # Contrastive Learning
    'ContrastiveLearner',
    'NTXentLoss',
    'TripletLoss',
    'SupervisedContrastiveLoss',
    'get_contrastive_learner',

    # Neuro-Symbolic Integration
    'TrustAwareEmbeddingModel',
    'TrustContext',
    'get_trust_aware_embedding_model',
    'NeuralToSymbolicRuleGenerator',
    'NeuralPattern',
    'SymbolicRule',
    'get_neural_to_symbolic_generator',
    'NeuroSymbolicReasoner',
    'ReasoningResult',
    'get_neuro_symbolic_reasoner',
    'RuleStorage',
    'get_rule_storage',
    # KPI Tracking
    'KPITracker',
    'KPI',
    'ComponentKPIs',
    'get_kpi_tracker',
]
