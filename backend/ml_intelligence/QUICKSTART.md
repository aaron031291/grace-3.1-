# ML Intelligence Quick Start Guide

Get Grace's ML/DL enhancements running in 5 minutes.

## Installation

### 1. Install Dependencies

```bash
cd backend/ml_intelligence
pip install -r requirements.txt
```

**Required packages:**
- torch>=2.0.0
- numpy>=1.20.0
- scikit-learn>=1.0.0
- sentence-transformers>=2.2.0

### 2. Verify Installation

```python
python -c "import torch; print(f'PyTorch {torch.__version__} installed')"
```

## Usage Options

### Option 1: One-Line Integration (Recommended)

```python
from ml_intelligence.integration_orchestrator import enhance_learning_memory_with_ml

# Enable all ML enhancements with one line
orchestrator = enhance_learning_memory_with_ml()
```

**Output:**
```
[ML Intelligence] Neural Trust Scorer initialized
[ML Intelligence] Multi-Armed Bandit initialized (Thompson Sampling)
[ML Intelligence] Meta-Learning Module initialized
[ML Intelligence] All components initialized successfully
[ML Intelligence] Enhanced learning memory system with ML/DL components
[ML Intelligence] Features enabled:
  ✓ neural_trust_scoring
  ✓ bandit_exploration
  ✓ meta_learning
  ✓ uncertainty_estimation
  ✓ active_learning
```

### Option 2: Selective Features

```python
from ml_intelligence import get_ml_orchestrator

orchestrator = get_ml_orchestrator()

# Disable features you don't need
orchestrator.enabled_features = {
    'neural_trust_scoring': True,   # Keep this
    'bandit_exploration': False,    # Disable this
    'meta_learning': True,          # Keep this
    'uncertainty_estimation': False, # Disable this
    'active_learning': False        # Disable this
}

orchestrator.initialize()
```

### Option 3: Individual Components

```python
from ml_intelligence import (
    get_neural_trust_scorer,
    get_bandit,
    get_meta_learner
)

# Use only what you need
trust_scorer = get_neural_trust_scorer()
bandit = get_bandit()
meta_learner = get_meta_learner()
```

## Common Use Cases

### Use Case 1: Better Trust Scoring

**Problem:** Need more accurate trust scores for learning examples

```python
from ml_intelligence import get_neural_trust_scorer

scorer = get_neural_trust_scorer()

# Your learning example
example = {
    'input_context': 'How to use Python async/await',
    'expected_output': 'Use async def and await keywords',
    'source_reliability': 0.9,
    'outcome_quality': 0.85,
    'consistency_score': 0.8,
    'times_validated': 5,
    'times_invalidated': 1,
    'times_referenced': 10,
    'created_at': '2024-01-01T00:00:00'
}

# Get trust score with uncertainty
trust, uncertainty = scorer.predict_trust(example, return_uncertainty=True)

print(f"Trust: {trust:.3f} ± {uncertainty:.3f}")
# Output: Trust: 0.823 ± 0.042

# Update when you observe outcome
scorer.update_from_outcome(example, outcome_success=True)
```

### Use Case 2: Smarter Topic Selection

**Problem:** Want to learn topics in optimal order

```python
from ml_intelligence import get_bandit, BanditContext

bandit = get_bandit()

# Define topics
topics = [
    {"topic_id": "python_async", "topic_name": "Python Async"},
    {"topic_id": "rust_ownership", "topic_name": "Rust Ownership"},
    {"topic_id": "react_hooks", "topic_name": "React Hooks"}
]

# Add topics to bandit
for topic in topics:
    bandit.add_arm(topic['topic_id'], topic['topic_name'])

# Select next topic
selected = bandit.select_arm()
print(f"Learn next: {selected}")

# After learning, update with reward
success = True  # Did learning succeed?
bandit.update_reward(selected, reward=1.0 if success else 0.0)
```

### Use Case 3: Optimal Hyperparameters

**Problem:** Need to tune learning hyperparameters

```python
from ml_intelligence import get_meta_learner

meta_learner = get_meta_learner()

# Get recommendations for your task
recommendations = meta_learner.get_learning_recommendations(
    task_type="classification",
    task_metadata={"num_classes": 10}
)

hyperparams = recommendations['suggested_hyperparams']

print(f"Use learning rate: {hyperparams['learning_rate']}")
print(f"Use batch size: {hyperparams['batch_size']}")
print(f"Use epochs: {hyperparams['num_epochs']}")

# After training, report results
meta_learner.hyperparam_optimizer.update_from_result(
    task_type="classification",
    hyperparams=hyperparams,
    performance=0.92  # Your accuracy
)
```

### Use Case 4: Know Your Uncertainty

**Problem:** Need confidence estimates on predictions

```python
from ml_intelligence import MCDropoutNetwork, UncertaintyQuantifier
import torch

# Your model (with dropout)
model = MCDropoutNetwork(input_dim=100, dropout_rate=0.3)

# Wrap with uncertainty quantifier
quantifier = UncertaintyQuantifier(model, method='mc_dropout')

# Predict with uncertainty
x_test = torch.randn(1, 100)
estimate = quantifier.predict_with_uncertainty(x_test, num_samples=50)

print(f"Prediction: {estimate.prediction:.3f}")
print(f"Uncertainty: {estimate.total_uncertainty:.3f}")
print(f"95% CI: {estimate.confidence_interval}")
print(f"Reliable: {estimate.is_reliable}")
```

### Use Case 5: Efficient Data Selection

**Problem:** Have lots of unlabeled data, want to label most valuable examples

```python
from ml_intelligence import get_active_sampler, SamplingStrategy
import torch

# Your model
model = MyModel()

# Active learning sampler
sampler = get_active_sampler(model, strategy=SamplingStrategy.UNCERTAINTY)

# Your unlabeled data pool
unlabeled_pool = torch.randn(10000, 100)  # 10k examples

# Select 100 most valuable
selected_indices = sampler.select_samples(unlabeled_pool, n_samples=100)

# Now label only these 100 instead of all 10k
valuable_samples = unlabeled_pool[selected_indices]
```

## Integration with Existing Grace Code

### Integrate with Learning Memory

```python
# In backend/cognitive/learning_memory.py

from ml_intelligence import get_ml_orchestrator

class LearningMemory:
    def __init__(self):
        self.ml_orchestrator = get_ml_orchestrator()
        # ... existing code ...

    def calculate_trust_score(self, example: LearningExample) -> float:
        # Convert to dict
        example_dict = {
            'input_context': example.input_context,
            'expected_output': example.expected_output,
            # ... other fields ...
        }

        # Use ML trust scorer with fallback
        trust, uncertainty = self.ml_orchestrator.compute_trust_score(
            example_dict,
            fallback_to_rules=True
        )

        # Store uncertainty for later use
        example.uncertainty = uncertainty

        return trust
```

### Integrate with Autonomous Learning

```python
# In backend/cognitive/autonomous_learning.py

from ml_intelligence import get_ml_orchestrator

class AutonomousLearning:
    def __init__(self):
        self.ml_orchestrator = get_ml_orchestrator()
        # ... existing code ...

    def select_next_topic(self) -> str:
        # Get available topics
        topics = self.get_available_topics()

        # Build context
        context = {
            'knowledge_gaps': self.get_knowledge_gaps(),
            'recent_failures': self.get_recent_failures(),
            'learning_velocity': self.calculate_learning_velocity()
        }

        # Use bandit algorithm
        selected = self.ml_orchestrator.select_next_learning_topic(
            topics,
            context=context
        )

        return selected

    def update_learning_outcome(self, topic_id: str, success: bool):
        # Update bandit
        context = self.build_context()
        self.ml_orchestrator.update_topic_reward(topic_id, success, context)
```

## Running Examples

### Run All Examples

```bash
cd backend/ml_intelligence
python example_usage.py
```

**Expected output:**
```
============================================================
ML INTELLIGENCE MODULE - COMPREHENSIVE EXAMPLES
============================================================

============================================================
Example 1: Neural Trust Scorer
============================================================

Trust Score: 0.823
Uncertainty: 0.042

Updated model with positive outcome

Robustness Score: 0.956
Max Deviation: 0.023

... (more examples)

============================================================
ALL EXAMPLES COMPLETED SUCCESSFULLY!
============================================================
```

### Run Individual Examples

```python
# Just trust scorer
from ml_intelligence.example_usage import example_neural_trust_scorer
example_neural_trust_scorer()

# Just bandit
from ml_intelligence.example_usage import example_bandit
example_bandit()
```

## Monitoring & Debugging

### Check System Status

```python
orchestrator = get_ml_orchestrator()
stats = orchestrator.get_statistics()

print(f"Enabled features: {stats['enabled_features']}")
print(f"Usage stats: {stats['usage_stats']}")

# Component-specific stats
if 'neural_trust_scorer' in stats:
    print(f"Trust scorer updates: {stats['neural_trust_scorer']['total_updates']}")
    print(f"Recent loss: {stats['neural_trust_scorer']['recent_avg_loss']:.4f}")

if 'bandit' in stats:
    print(f"Total topic selections: {stats['bandit']['total_pulls']}")
    print(f"Number of topics: {stats['bandit']['num_arms']}")
```

### Enable Verbose Logging

```python
import logging

logging.basicConfig(level=logging.INFO)

# Now you'll see detailed logs
orchestrator = get_ml_orchestrator()
```

### Troubleshooting

**Issue: ImportError**
```python
# Make sure backend is in path
import sys
sys.path.insert(0, 'path/to/grace/backend')
from ml_intelligence import get_ml_orchestrator
```

**Issue: CUDA out of memory**
```python
# Force CPU usage
import os
os.environ['CUDA_VISIBLE_DEVICES'] = ''

# Or reduce batch sizes
scorer = get_neural_trust_scorer()
scorer.batch_size = 16  # Default is 32
```

**Issue: Slow predictions**
```python
# Reduce MC samples
estimate = quantifier.predict_with_uncertainty(x, num_samples=10)  # Instead of 50
```

## Saving & Loading Models

### Auto-Save

Models auto-save periodically:
- Neural trust scorer: Every 100 predictions
- Bandit: Every 10 rewards
- Meta-learner: After each update

### Manual Save

```python
orchestrator = get_ml_orchestrator()
orchestrator.save_all_models()
# Saves all models to backend/models/
```

### Load Existing Models

```python
# Models auto-load on initialization
orchestrator = get_ml_orchestrator()
# Automatically loads from backend/models/ if files exist
```

### Check Model Locations

```bash
ls backend/models/
# neural_trust_scorer.pt
# bandit_state.json
# meta_learning/
# checkpoints/
```

## Performance Tips

### 1. Use GPU if Available

```python
import torch
print(f"GPU available: {torch.cuda.is_available()}")

# Models automatically use GPU if available
```

### 2. Batch Predictions

```python
# Instead of:
for example in examples:
    score = scorer.predict_trust(example)

# Do:
scores = [scorer.predict_trust(ex) for ex in examples]  # Still sequential but faster
```

### 3. Reduce Uncertainty Samples

```python
# Fast (10 samples): ~10ms
estimate = quantifier.predict_with_uncertainty(x, num_samples=10)

# Medium (50 samples): ~50ms (default)
estimate = quantifier.predict_with_uncertainty(x, num_samples=50)

# Slow (100 samples): ~100ms
estimate = quantifier.predict_with_uncertainty(x, num_samples=100)
```

### 4. Disable Features You Don't Need

```python
orchestrator.enabled_features = {
    'neural_trust_scoring': True,
    'bandit_exploration': True,
    'meta_learning': False,        # Disable if not needed
    'uncertainty_estimation': False, # Disable if not needed
    'active_learning': False        # Disable if not needed
}
```

## Next Steps

1. **Read the full documentation**: [README.md](README.md)
2. **Understand the architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
3. **Review implementation details**: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
4. **Run examples**: `python example_usage.py`
5. **Integrate with your code**: See integration examples above

## Common Patterns

### Pattern: Enhance Existing Function

```python
# Before
def my_function():
    result = rule_based_calculation()
    return result

# After
from ml_intelligence import get_ml_orchestrator

orchestrator = get_ml_orchestrator()

def my_function():
    result = orchestrator.compute_with_ml(
        data,
        fallback_to_rules=True
    )
    return result
```

### Pattern: Add New Capability

```python
# New function using ML
from ml_intelligence import get_ml_orchestrator

orchestrator = get_ml_orchestrator()

def smart_select_examples(unlabeled_data):
    return orchestrator.select_training_examples(
        unlabeled_data,
        n_samples=100
    )
```

### Pattern: Gradual Rollout

```python
# Use flag to control rollout
USE_ML_ENHANCEMENTS = os.environ.get('USE_ML', 'true').lower() == 'true'

if USE_ML_ENHANCEMENTS:
    orchestrator = get_ml_orchestrator()
    score = orchestrator.compute_trust_score(example)
else:
    score = legacy_trust_calculation(example)
```

## Support & Contributions

- **Documentation**: See README.md for detailed API docs
- **Examples**: Run example_usage.py for live demos
- **Architecture**: See ARCHITECTURE.md for system design
- **Implementation**: See IMPLEMENTATION_SUMMARY.md for details

## Quick Reference

| Component | Import | Main Method |
|-----------|--------|-------------|
| Trust Scorer | `get_neural_trust_scorer()` | `predict_trust(example)` |
| Bandit | `get_bandit()` | `select_arm(context)` |
| Meta-Learner | `get_meta_learner()` | `get_learning_recommendations(task_type)` |
| Uncertainty | `UncertaintyQuantifier(model)` | `predict_with_uncertainty(x)` |
| Active Learning | `get_active_sampler(model)` | `select_samples(pool, n)` |
| Orchestrator | `get_ml_orchestrator()` | All-in-one interface |

---

**Ready to enhance Grace with ML/DL capabilities? Start with the one-line integration!**

```python
from ml_intelligence.integration_orchestrator import enhance_learning_memory_with_ml
orchestrator = enhance_learning_memory_with_ml()
```
