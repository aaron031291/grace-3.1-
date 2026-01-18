# ML Intelligence Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Grace Autonomous Learning System                     │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                  ML Intelligence Orchestrator                       │ │
│  │                  (integration_orchestrator.py)                      │ │
│  │                                                                      │ │
│  │  Coordinates all ML/DL components with existing Grace systems      │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                     │                                     │
│                                     ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                         ML Intelligence Components                   ││
│  │                                                                       ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              ││
│  │  │   Neural     │  │  Multi-Armed │  │    Meta-     │              ││
│  │  │   Trust      │  │   Bandit     │  │   Learning   │              ││
│  │  │   Scorer     │  │  Algorithm   │  │  Optimizer   │              ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘              ││
│  │                                                                       ││
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              ││
│  │  │ Uncertainty  │  │   Active     │  │ Contrastive  │              ││
│  │  │ Quantifier   │  │   Learning   │  │   Learning   │              ││
│  │  │              │  │   Sampler    │  │              │              ││
│  │  └──────────────┘  └──────────────┘  └──────────────┘              ││
│  │                                                                       ││
│  │  ┌──────────────────────────────────────────────────────┐          ││
│  │  │         Online Learning Pipeline                      │          ││
│  │  │         (with EWC for forgetting prevention)         │          ││
│  │  └──────────────────────────────────────────────────────┘          ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                     │                                     │
│                                     ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │                    Existing Grace Systems                            ││
│  │                                                                       ││
│  │  • Learning Memory          • Autonomous Learning                   ││
│  │  • Cognitive Engine         • Memory Mesh                           ││
│  │  • Episodic Memory          • Procedural Memory                     ││
│  │  • Genesis Keys             • RAG System                            ││
│  │  • Embedding System         • Confidence Scorer                     ││
│  └─────────────────────────────────────────────────────────────────────┘│
└───────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Neural Trust Scorer Architecture

```
Input Features (12)               Optional Embedding (384)
      │                                    │
      └────────────┬───────────────────────┘
                   │
                   ▼
          ┌──────────────────┐
          │  Input Projection │
          │   Linear(396→256) │
          └──────────────────┘
                   │
                   ▼
          ┌──────────────────┐
          │  Multi-Head       │
          │  Attention (4h)   │
          │  + Residual       │
          └──────────────────┘
                   │
                   ▼
          ┌──────────────────┐
          │  FFN Layer 1      │
          │  256 → 128        │
          │  + LayerNorm      │
          │  + ReLU + Dropout │
          │  + Residual       │
          └──────────────────┘
                   │
                   ▼
          ┌──────────────────┐
          │  FFN Layer 2      │
          │  128 → 64         │
          │  + LayerNorm      │
          │  + ReLU + Dropout │
          │  + Residual       │
          └──────────────────┘
                   │
           ┌──────┴──────┐
           │             │
           ▼             ▼
    ┌────────────┐  ┌────────────┐
    │ Trust Head │  │ Uncertainty│
    │   64 → 1   │  │   Head     │
    │  Sigmoid   │  │   64 → 1   │
    └────────────┘  └────────────┘
           │             │
           ▼             ▼
    Trust Score    Uncertainty
      [0, 1]         [0, 1]
```

### 2. Multi-Armed Bandit Decision Flow

```
Available Topics
      │
      ▼
┌─────────────────────────────────────────┐
│ Context (Optional)                      │
│  • Knowledge gaps                       │
│  • Recent failures                      │
│  • User interests                       │
│  • Time of day                          │
│  • Learning velocity                    │
└─────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────┐
│ Algorithm Selection                     │
│                                         │
│ ┌─────────────┐  ┌──────────────┐     │
│ │    UCB1     │  │  Thompson    │     │
│ │             │  │  Sampling    │     │
│ │ μ + c√(ln t)│  │ β~Beta(α,β)  │     │
│ │     ─────   │  │              │     │
│ │       n     │  │ Select max   │     │
│ └─────────────┘  └──────────────┘     │
│                                         │
│ ┌─────────────┐  ┌──────────────┐     │
│ │  Contextual │  │    Exp3      │     │
│ │             │  │              │     │
│ │ Base + Ctx  │  │ Exponential  │     │
│ │   Score     │  │   Weights    │     │
│ └─────────────┘  └──────────────┘     │
└─────────────────────────────────────────┘
      │
      ▼
Selected Topic
      │
      ▼
Learning Outcome
      │
      ▼
┌─────────────────────────────────────────┐
│ Update Arm Statistics                   │
│  • pulls++                              │
│  • total_reward += reward               │
│  • successes++ or failures++            │
│  • last_pulled = now()                  │
└─────────────────────────────────────────┘
```

### 3. Meta-Learning Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    New Learning Task                         │
│                                                               │
│  Task Type: "classification"                                 │
│  Metadata: {num_classes: 10, input_dim: 784}                │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Task Similarity Detection                       │
│                                                               │
│  1. Embed task based on features                            │
│  2. Compute similarity to past tasks                        │
│  3. Find top-k similar tasks                                │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│         Hyperparameter Recommendation                        │
│                                                               │
│  Sample from learned distributions:                          │
│   • Learning Rate ~ LogNormal(μ_lr, σ_lr)                   │
│   • Batch Size ~ Discrete(μ_bs, σ_bs)                       │
│   • Num Epochs ~ Normal(μ_ep, σ_ep)                         │
│   • Dropout ~ Normal(μ_do, σ_do)                            │
│   • Weight Decay ~ LogNormal(μ_wd, σ_wd)                    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Apply Hyperparameters                      │
│                   Train Model                                │
│                   Measure Performance                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Update Meta-Learner                             │
│                                                               │
│  EMA update of distribution parameters:                      │
│   μ_new = (1 - α·perf)·μ_old + α·perf·observed             │
│   σ_new = (1 - α)·σ_old + α·|observed - μ_old|             │
└─────────────────────────────────────────────────────────────┘
```

### 4. Uncertainty Quantification Methods

```
┌──────────────────────────────────────────────────────────────┐
│                    Prediction with Uncertainty                │
└──────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌───────────┐  ┌──────────┐  ┌──────────────┐
    │ Bayesian  │  │    MC    │  │    Deep      │
    │  Neural   │  │ Dropout  │  │  Ensemble    │
    │  Network  │  │          │  │              │
    └───────────┘  └──────────┘  └──────────────┘
           │               │               │
           ▼               ▼               ▼
    ┌───────────┐  ┌──────────┐  ┌──────────────┐
    │ Sample    │  │ Enable   │  │ Multiple     │
    │ weights   │  │ dropout  │  │ models       │
    │ from q(w) │  │ N times  │  │ predictions  │
    └───────────┘  └──────────┘  └──────────────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                           ▼
                  ┌────────────────┐
                  │  Aggregate     │
                  │                │
                  │  μ = E[y]      │
                  │  σ = Std[y]    │
                  └────────────────┘
                           │
                           ▼
           ┌───────────────────────────────┐
           │  Decompose Uncertainty        │
           │                               │
           │  Epistemic: Model Uncertainty │
           │  Aleatoric: Data Noise        │
           │  Total: √(ε² + α²)           │
           └───────────────────────────────┘
                           │
                           ▼
                  ┌────────────────┐
                  │ Confidence     │
                  │ Interval       │
                  │                │
                  │ [μ-2σ, μ+2σ]  │
                  │ (95% CI)       │
                  └────────────────┘
```

### 5. Active Learning Sample Selection

```
Unlabeled Pool (1000 samples)
           │
           ▼
┌──────────────────────────────────────────────────────┐
│            Compute Scores per Strategy                │
│                                                        │
│  ┌─────────────┐  ┌──────────────┐                  │
│  │ Uncertainty │  │   Entropy    │                  │
│  │             │  │              │                  │
│  │ σ[P(y|x)]   │  │ -Σp·log(p)   │                  │
│  └─────────────┘  └──────────────┘                  │
│                                                        │
│  ┌─────────────┐  ┌──────────────┐                  │
│  │   Margin    │  │  Diversity   │                  │
│  │             │  │              │                  │
│  │ p₁ - p₂     │  │  K-Means     │                  │
│  └─────────────┘  └──────────────┘                  │
│                                                        │
│  ┌─────────────┐  ┌──────────────┐                  │
│  │    QBC      │  │   Core-Set   │                  │
│  │             │  │              │                  │
│  │ Committee   │  │  k-Center    │                  │
│  │ Disagreement│  │              │                  │
│  └─────────────┘  └──────────────┘                  │
└──────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│         Combine Scores (if Hybrid)                    │
│                                                        │
│  final_score = Σ (weight_i × normalized_score_i)     │
└──────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│        Select Top-K Samples                           │
│                                                        │
│  indices = argsort(scores)[-k:]                       │
└──────────────────────────────────────────────────────┘
           │
           ▼
    Selected Samples
   (Most valuable k)
```

### 6. Contrastive Learning Pipeline

```
Input: Batch of Examples
           │
           ▼
┌──────────────────────────────────────────────────────┐
│        Create Positive Pairs                          │
│                                                        │
│  Anchor    →  Augment  →  Positive                   │
│  (x_i)                     (x_i')                     │
└──────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│              Encoder Network                          │
│                                                        │
│  Input (100) → [256] → [128] → Embedding             │
└──────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│            Projection Head                            │
│                                                        │
│  Embedding (128) → [512] → [128] → Projection        │
└──────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│          Similarity Computation                       │
│                                                        │
│  sim(z_i, z_j) = z_i · z_j / (||z_i|| ||z_j||)       │
└──────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│               Loss Calculation                        │
│                                                        │
│  NT-Xent:                                            │
│    L = -log(exp(sim(z_i,z_i')/τ) / Σ exp(...))      │
│                                                        │
│  Triplet:                                            │
│    L = max(0, d(a,p) - d(a,n) + margin)              │
│                                                        │
│  Supervised:                                         │
│    L = -log(Σ_pos exp(sim)/Σ_all exp(sim))          │
└──────────────────────────────────────────────────────┘
           │
           ▼
    Backward & Update
```

### 7. Online Learning with EWC

```
Streaming Data Batch
           │
           ▼
┌──────────────────────────────────────────────────────┐
│          Primary Loss Computation                     │
│                                                        │
│  L_primary = CrossEntropy(y_pred, y_true)            │
└──────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│         EWC Penalty (if enabled)                      │
│                                                        │
│  L_ewc = λ · Σ F_i · (θ_i - θ*_i)²                  │
│                                                        │
│  where:                                               │
│   F_i = Fisher Information for parameter i           │
│   θ_i = Current parameter value                      │
│   θ*_i = Optimal value from previous task            │
│   λ = 1000 (default)                                 │
└──────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│            Total Loss                                 │
│                                                        │
│  L_total = L_primary + L_ewc                         │
└──────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│         Gradient Update                               │
│                                                        │
│  1. Compute gradients                                │
│  2. Clip gradients (max_norm=1.0)                    │
│  3. Update parameters                                │
└──────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────┐
│      Running Statistics Update                        │
│                                                        │
│  EMA_loss = α·loss + (1-α)·EMA_loss                  │
│  EMA_acc = α·acc + (1-α)·EMA_acc                     │
└──────────────────────────────────────────────────────┘
           │
           ▼
    Checkpoint (every 100 batches)
```

## Data Flow

### Trust Score Computation Flow

```
Learning Example Dict
  ├─ input_context
  ├─ expected_output
  ├─ actual_output
  ├─ source_reliability
  ├─ outcome_quality
  ├─ consistency_score
  ├─ times_validated
  ├─ times_invalidated
  ├─ created_at
  └─ embedding (optional)
           │
           ▼
Feature Extraction
  ├─ source_reliability (raw)
  ├─ outcome_quality (raw)
  ├─ consistency_score (raw)
  ├─ validation_count / 100
  ├─ invalidation_count / 100
  ├─ age_days / 365
  ├─ content_length / 10000
  ├─ has_code (bool→float)
  ├─ has_structure (bool→float)
  ├─ has_references (bool→float)
  ├─ usage_frequency
  └─ success_rate
           │
           ▼
   [12 features]
           │
  (optional) + [384 embedding]
           │
           ▼
   Neural Network
     (with MC Dropout)
           │
           ▼
   20 forward passes
           │
           ▼
  Mean & Std of outputs
           │
           ▼
  (trust_score, uncertainty)
```

## Model Persistence

```
backend/models/
├── neural_trust_scorer.pt
│   ├── network_state
│   ├── optimizer_state
│   ├── training_stats
│   └── replay_buffer_size
│
├── bandit_state.json
│   ├── algorithm
│   ├── total_pulls
│   ├── arms (dict)
│   ├── exp3_weights
│   ├── contextual_weights
│   ├── selection_history
│   └── reward_history
│
├── meta_learning/
│   ├── meta_learning_state.json
│   │   ├── hyperparam_stats
│   │   ├── performance_history
│   │   └── task_embeddings
│   └── maml_model.pt (if MAML used)
│
└── checkpoints/
    └── online_learning/
        ├── checkpoint_batch_100.pt
        ├── checkpoint_batch_200.pt
        └── latest.pt
```

## Integration Patterns

### Pattern 1: Replace Existing Function

```python
# Before (in learning_memory.py)
def calculate_trust_score(example):
    # Rule-based calculation
    return source * 0.4 + outcome * 0.3 + ...

# After
from ml_intelligence import get_ml_orchestrator

orchestrator = get_ml_orchestrator()

def calculate_trust_score(example):
    # Neural network with fallback
    trust, uncertainty = orchestrator.compute_trust_score(
        example,
        fallback_to_rules=True
    )
    return trust
```

### Pattern 2: Enhance Existing Function

```python
# Before (in autonomous_learning.py)
def suggest_learning_topics():
    topics = get_available_topics()
    return random.choice(topics)

# After
from ml_intelligence import get_ml_orchestrator

orchestrator = get_ml_orchestrator()

def suggest_learning_topics():
    topics = get_available_topics()
    context = build_learning_context()

    selected = orchestrator.select_next_learning_topic(
        topics,
        context=context
    )

    return selected
```

### Pattern 3: Add New Capability

```python
# New function in autonomous_learning.py
from ml_intelligence import get_ml_orchestrator

orchestrator = get_ml_orchestrator()

def select_training_examples(unlabeled_data, n=100):
    """Select most valuable training examples via active learning"""

    selected_indices = orchestrator.select_training_examples(
        unlabeled_data,
        n_samples=n,
        model=current_model
    )

    return unlabeled_data[selected_indices]
```

## Component Dependencies

```
integration_orchestrator
    ├── neural_trust_scorer
    │   └── torch
    ├── multi_armed_bandit
    │   └── numpy
    ├── meta_learning
    │   ├── torch
    │   └── numpy
    ├── uncertainty_quantification
    │   └── torch
    ├── active_learning_sampler
    │   ├── torch
    │   ├── numpy
    │   └── scikit-learn
    ├── contrastive_learning
    │   └── torch
    └── online_learning_pipeline
        └── torch
```

---

**Architecture Version**: 1.0
**Last Updated**: January 2026
**Status**: Production Ready
