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

# Track availability of ML components
ML_INTELLIGENCE_AVAILABLE = False

try:
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
    from .kpi_tracker import (
        KPITracker,
        KPI,
        ComponentKPIs,
        get_kpi_tracker
    )
    ML_INTELLIGENCE_AVAILABLE = True
except ImportError as e:
    import logging
    logging.getLogger(__name__).warning(f"ML Intelligence components not available: {e}")
    # Define placeholders when ML components are not available
    NeuralTrustScorer = None
    get_neural_trust_scorer = None
    OnlineLearningPipeline = None
    IncrementalEmbeddingLearner = None
    get_online_learning_pipeline = None
    get_incremental_embedder = None
    MultiArmedBandit = None
    BanditAlgorithm = None
    BanditContext = None
    get_bandit = None
    MetaLearningOrchestrator = None
    HyperparameterOptimizer = None
    TaskSimilarityDetector = None
    get_meta_learner = None
    UncertaintyQuantifier = None
    BayesianNeuralNetwork = None
    MCDropoutNetwork = None
    UncertaintyEstimate = None
    get_uncertainty_quantifier = None
    ActiveLearningSampler = None
    SamplingStrategy = None
    get_active_sampler = None
    ContrastiveLearner = None
    NTXentLoss = None
    TripletLoss = None
    SupervisedContrastiveLoss = None
    get_contrastive_learner = None
    TrustAwareEmbeddingModel = None
    TrustContext = None
    get_trust_aware_embedding_model = None
    NeuralToSymbolicRuleGenerator = None
    NeuralPattern = None
    SymbolicRule = None
    get_neural_to_symbolic_generator = None
    NeuroSymbolicReasoner = None
    ReasoningResult = None
    get_neuro_symbolic_reasoner = None
    RuleStorage = None
    get_rule_storage = None
    KPITracker = None
    KPI = None
    ComponentKPIs = None
    get_kpi_tracker = None

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
