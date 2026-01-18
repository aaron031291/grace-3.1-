# ML Intelligence Module

Advanced ML/DL enhancements for Grace's autonomous learning system.

## Overview

This module replaces rule-based heuristics with learned neural models across Grace's autonomous learning pipeline, enabling:

- **Smarter trust scoring** via deep learning
- **Continuous model improvement** through online learning
- **Optimal topic selection** using multi-armed bandits
- **Hyperparameter optimization** via meta-learning
- **Calibrated confidence** through uncertainty quantification
- **Efficient data usage** via active learning
- **Better representations** using contrastive learning

## Components

### 1. Neural Trust Scorer (`neural_trust_scorer.py`)

Replaces rule-based trust scoring with a learned neural network.

**Features:**
- Multi-layer feedforward network with attention
- Online learning with experience replay
- Monte Carlo dropout for uncertainty
- Adversarial robustness testing
- Feature engineering from learning examples

**Usage:**
```python
from ml_intelligence import get_neural_trust_scorer

scorer = get_neural_trust_scorer()

# Predict trust score
trust_score, uncertainty = scorer.predict_trust(learning_example, return_uncertainty=True)

# Update from observed outcome
scorer.update_from_outcome(learning_example, outcome_success=True)

# Save model
scorer.save_model()
```

**Architecture:**
- Input: 12 features + optional 384-dim embedding
- Hidden layers: [256, 128, 64] with residual connections
- Multi-head attention (4 heads)
- Dropout: 0.3 for uncertainty estimation
- Output: Trust score [0, 1] + uncertainty estimate

### 2. Online Learning Pipeline (`online_learning_pipeline.py`)

Enables continuous model updates without catastrophic forgetting.

**Features:**
- Streaming mini-batch updates
- Elastic Weight Consolidation (EWC) for forgetting prevention
- Incremental embedding adaptation
- Automatic checkpointing

**Usage:**
```python
from ml_intelligence import OnlineLearningPipeline, StreamingBatch

pipeline = OnlineLearningPipeline(model=my_model, use_ewc=True)

# Update with new batch
batch = StreamingBatch(features=X, labels=y)
metrics = pipeline.update(batch)

# When transitioning to new task, update EWC
pipeline.update_ewc(calibration_dataloader)
```

**EWC Formula:**
```
Loss = Primary_Loss + λ * Σ F_i * (θ_i - θ*_i)²

where:
- F_i: Fisher information for parameter i
- θ_i: Current parameter value
- θ*_i: Optimal value from previous task
- λ: EWC importance (default: 1000)
```

### 3. Multi-Armed Bandit (`multi_armed_bandit.py`)

Intelligently balances exploration vs exploitation for topic selection.

**Algorithms:**
- **UCB1**: Upper Confidence Bound
- **Thompson Sampling**: Bayesian approach (default)
- **Epsilon-Greedy**: Simple exploration
- **Contextual Bandits**: Context-aware selection
- **Exp3**: For non-stationary environments

**Usage:**
```python
from ml_intelligence import get_bandit, BanditAlgorithm, BanditContext

bandit = get_bandit(algorithm=BanditAlgorithm.THOMPSON_SAMPLING)

# Add learning topics
bandit.add_arm(topic_id="python_async", topic_name="Python Async Programming")
bandit.add_arm(topic_id="rust_ownership", topic_name="Rust Ownership")

# Select next topic (with optional context)
context = BanditContext(
    knowledge_gaps={"python_async": 0.8, "rust_ownership": 0.5},
    recent_failures=["python_async"],
    user_interests={"rust_ownership": 0.9},
    time_of_day=14,
    learning_velocity=1.2
)

topic_id = bandit.select_arm(context=context)

# Update with observed reward
bandit.update_reward(topic_id, reward=0.85, context=context)

# Get recommendations
recommendations = bandit.recommend_next_topics(k=3, context=context)
```

**Thompson Sampling:**
```
For each arm i:
  1. Sample θ_i ~ Beta(successes_i, failures_i)
  2. Select arm with highest θ_i
```

### 4. Meta-Learning (`meta_learning.py`)

Learns optimal learning strategies across tasks.

**Features:**
- MAML (Model-Agnostic Meta-Learning)
- Reptile (first-order MAML)
- Hyperparameter optimization
- Task similarity detection

**Usage:**
```python
from ml_intelligence import get_meta_learner

meta_learner = get_meta_learner()

# Get hyperparameter recommendations
recommendations = meta_learner.get_learning_recommendations(
    task_type="classification",
    task_metadata={"num_classes": 10, "input_dim": 784}
)

# Suggested: learning_rate, batch_size, num_epochs, dropout, weight_decay
hyperparams = recommendations['suggested_hyperparams']

# After training, update with results
meta_learner.hyperparam_optimizer.update_from_result(
    task_type="classification",
    hyperparams=hyperparams,
    performance=0.95  # Accuracy or other metric
)
```

**MAML Inner Loop:**
```
1. Clone base model
2. Adapt on support set for K steps:
   θ' = θ - α ∇_θ L_support(θ)
3. Evaluate on query set
```

**MAML Outer Loop:**
```
Update meta-parameters:
θ = θ - β ∇_θ Σ L_query(θ')
```

### 5. Uncertainty Quantification (`uncertainty_quantification.py`)

Provides calibrated confidence estimates for predictions.

**Methods:**
- **Bayesian Neural Networks**: Variational inference
- **MC Dropout**: Dropout at test time
- **Deep Ensembles**: Multiple model averaging
- **Conformal Prediction**: Statistically valid intervals

**Usage:**
```python
from ml_intelligence import (
    UncertaintyQuantifier,
    BayesianNeuralNetwork,
    MCDropoutNetwork
)

# Create Bayesian network
model = BayesianNeuralNetwork(input_dim=100, hidden_dims=[128, 64])

# Or MC Dropout network
model = MCDropoutNetwork(input_dim=100, dropout_rate=0.3)

# Quantifier
quantifier = UncertaintyQuantifier(model, method='bayesian')

# Predict with uncertainty
estimate = quantifier.predict_with_uncertainty(x, num_samples=50)

print(f"Prediction: {estimate.prediction}")
print(f"Epistemic uncertainty: {estimate.epistemic_uncertainty}")
print(f"Aleatoric uncertainty: {estimate.aleatoric_uncertainty}")
print(f"95% CI: {estimate.confidence_interval}")
print(f"Reliable: {estimate.is_reliable}")
```

**Uncertainty Types:**
- **Epistemic**: Model uncertainty (reducible with more data)
- **Aleatoric**: Data noise (irreducible)
- **Total**: sqrt(epistemic² + aleatoric²)

### 6. Active Learning Sampler (`active_learning_sampler.py`)

Selects most valuable training examples.

**Strategies:**
- **Uncertainty Sampling**: Most uncertain examples
- **Entropy Sampling**: Maximum prediction entropy
- **Margin Sampling**: Smallest top-2 margin
- **Query-by-Committee**: Committee disagreement
- **Expected Model Change**: Largest gradient magnitude
- **Diversity Sampling**: K-Means diversity
- **Core-Set Selection**: k-Center algorithm

**Usage:**
```python
from ml_intelligence import get_active_sampler, SamplingStrategy

sampler = get_active_sampler(
    model=my_model,
    strategy=SamplingStrategy.UNCERTAINTY
)

# Select most valuable samples
unlabeled_pool = torch.randn(1000, 100)  # 1000 unlabeled examples
selected_indices = sampler.select_samples(unlabeled_pool, n_samples=10)

# Hybrid selection
selected_indices = sampler.hybrid_selection(
    unlabeled_pool,
    n_samples=10,
    weights={
        SamplingStrategy.UNCERTAINTY: 0.6,
        SamplingStrategy.DIVERSITY: 0.4
    }
)
```

**Uncertainty Sampling:**
```
Select x where Var[P(y|x)] is maximal
```

**Query-by-Committee:**
```
Select x where committee disagreement is maximal:
disagreement = -Σ P(y) log P(y)
where P(y) = vote distribution
```

### 7. Contrastive Learning (`contrastive_learning.py`)

Learns better representations by contrasting examples.

**Loss Functions:**
- **NT-Xent**: Normalized Temperature-scaled Cross-Entropy
- **Triplet Loss**: Anchor-positive-negative triplets
- **Supervised Contrastive**: Label-aware contrastive

**Usage:**
```python
from ml_intelligence import ContrastiveLearner, ContrastiveBatch

# Create learner
learner = ContrastiveLearner(
    encoder=my_encoder,
    loss_type='ntxent',  # or 'triplet', 'supervised'
    temperature=0.5
)

# Train
batch = ContrastiveBatch(
    anchors=X_anchors,
    positives=X_positives,
    negatives=X_negatives  # For triplet loss
)

metrics = learner.train_step(batch)

# Encode and compute similarity
similarity = learner.compute_similarity(x1, x2, metric='cosine')
```

**NT-Xent Loss:**
```
L = -log( exp(sim(z_i, z_j) / τ) / Σ exp(sim(z_i, z_k) / τ) )

where:
- z_i, z_j: Positive pair embeddings
- z_k: All other embeddings
- τ: Temperature (default: 0.5)
- sim: Cosine similarity
```

## Integration with Grace

### Quick Start

```python
from ml_intelligence.integration_orchestrator import enhance_learning_memory_with_ml

# Initialize ML enhancements
orchestrator = enhance_learning_memory_with_ml()
```

### Detailed Integration

```python
from ml_intelligence import get_ml_orchestrator

orchestrator = get_ml_orchestrator()

# 1. Trust Scoring
trust_score, uncertainty = orchestrator.compute_trust_score(learning_example)

# 2. Update from outcome
orchestrator.update_trust_from_outcome(learning_example, outcome_success=True)

# 3. Topic Selection
available_topics = [
    {"topic_id": "python_async", "topic_name": "Async Programming"},
    {"topic_id": "rust_ownership", "topic_name": "Rust Ownership"}
]

context = {
    "knowledge_gaps": {"python_async": 0.8},
    "recent_failures": [],
    "learning_velocity": 1.0
}

topic_id = orchestrator.select_next_learning_topic(
    available_topics,
    context=context
)

# 4. Update topic reward
orchestrator.update_topic_reward(topic_id, success=True, context=context)

# 5. Get meta-learning recommendations
recommendations = orchestrator.get_learning_recommendations(
    task_type="classification",
    task_metadata={"num_classes": 5}
)

# 6. Uncertainty estimation
uncertainty_info = orchestrator.get_uncertainty_estimate(
    model=my_model,
    input_data=X_test
)

# 7. Active learning
selected_indices = orchestrator.select_training_examples(
    unlabeled_pool=X_unlabeled,
    n_samples=10,
    model=my_model
)

# 8. Save all models
orchestrator.save_all_models()

# 9. Get statistics
stats = orchestrator.get_statistics()
```

## Performance Impact

### Memory Usage
- Neural Trust Scorer: ~15 MB
- Bandit State: <1 MB
- Meta-Learning: ~5 MB
- Uncertainty Quantifier: Depends on base model
- **Total Overhead**: ~20-50 MB

### Speed
- Trust scoring: ~5ms per prediction (GPU) / ~15ms (CPU)
- Bandit selection: <1ms
- Meta-learning recommendations: <1ms
- Uncertainty estimation: ~100ms (50 MC samples)
- Active learning: ~50-200ms depending on strategy

### Training
- Neural Trust Scorer: Updates online, ~10ms per batch
- Online Learning: ~20ms per batch with EWC
- Contrastive Learning: ~50ms per batch

## Requirements

```
torch>=2.0.0
numpy>=1.20.0
scikit-learn>=1.0.0
sentence-transformers>=2.2.0
```

## Model Persistence

Models are automatically saved to:
```
backend/models/
  ├── neural_trust_scorer.pt
  ├── bandit_state.json
  ├── meta_learning/
  │   ├── meta_learning_state.json
  │   └── maml_model.pt
  └── checkpoints/
      └── online_learning/
          ├── checkpoint_batch_100.pt
          ├── checkpoint_batch_200.pt
          └── latest.pt
```

## Configuration

Enable/disable features in `integration_orchestrator.py`:

```python
self.enabled_features = {
    'neural_trust_scoring': True,
    'bandit_exploration': True,
    'meta_learning': True,
    'uncertainty_estimation': True,
    'active_learning': True
}
```

## Monitoring

Get real-time statistics:

```python
stats = orchestrator.get_statistics()

# Output:
{
    'enabled_features': {...},
    'usage_stats': {
        'neural_trust_predictions': 1523,
        'bandit_selections': 342,
        'meta_learning_recommendations': 45,
        'uncertainty_estimates': 234,
        'active_samples_selected': 120
    },
    'neural_trust_scorer': {
        'total_updates': 1000,
        'replay_buffer_size': 1523,
        'recent_avg_loss': 0.023
    },
    'bandit': {
        'total_pulls': 342,
        'num_arms': 15,
        'top_performers': [...]
    }
}
```

## Troubleshooting

### ImportError
Ensure `backend/ml_intelligence` is in Python path:
```python
import sys
sys.path.insert(0, 'path/to/backend')
```

### GPU Memory Issues
Reduce batch sizes or use CPU:
```python
# Force CPU
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
```

### Slow Inference
Reduce MC samples for uncertainty:
```python
estimate = quantifier.predict_with_uncertainty(x, num_samples=10)  # Instead of 50
```

## Advanced Usage

### Custom Neural Trust Scorer Architecture

```python
from ml_intelligence.neural_trust_scorer import TrustScorerNetwork

custom_network = TrustScorerNetwork(
    feature_dim=12,
    embedding_dim=384,
    hidden_dims=[512, 256, 128],
    num_attention_heads=8,
    dropout_rate=0.4
)

scorer = NeuralTrustScorer(model_path="custom_scorer.pt")
scorer.network = custom_network
```

### Custom Bandit Algorithm

```python
from ml_intelligence import MultiArmedBandit, BanditAlgorithm

# Try different algorithms
for algo in [BanditAlgorithm.UCB1, BanditAlgorithm.THOMPSON_SAMPLING, BanditAlgorithm.EXP3]:
    bandit = MultiArmedBandit(algorithm=algo)
    # ... experiment
```

### Transfer Learning with Meta-Learning

```python
# Find similar tasks
similar_tasks = meta_learner.task_similarity.find_similar_tasks(
    current_task,
    top_k=5
)

# Use hyperparameters from most similar task
best_match_id, similarity = similar_tasks[0]
best_hyperparams = meta_learner.hyperparam_optimizer.get_best_hyperparameters(
    best_match_id,
    top_k=1
)[0]
```

## Citation

```
@software{grace_ml_intelligence,
  title = {ML Intelligence Module for Grace Autonomous Learning},
  author = {Grace Team},
  year = {2026},
  description = {Deep learning enhancements for autonomous learning systems}
}
```

## License

Part of the Grace autonomous learning system.
