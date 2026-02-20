# Integration Orchestrator

**File:** `ml_intelligence/integration_orchestrator.py`

## Overview

ML Intelligence Integration Orchestrator

Integrates all ML/DL components with Grace's existing autonomous learning system.

Features:
- Replaces rule-based trust scoring with neural trust scorer
- Adds online learning to embedding models
- Uses bandit algorithms for topic selection
- Applies meta-learning for hyperparameter optimization
- Provides uncertainty estimates for predictions
- Selects optimal training examples via active learning
- Improves representations with contrastive learning

## Classes

- `MLIntelligenceOrchestrator`

## Key Methods

- `initialize()`
- `compute_trust_score()`
- `update_trust_from_outcome()`
- `select_next_learning_topic()`
- `update_topic_reward()`
- `get_learning_recommendations()`
- `get_uncertainty_estimate()`
- `select_training_examples()`
- `get_statistics()`
- `save_all_models()`
- `get_ml_orchestrator()`
- `enhance_learning_memory_with_ml()`

---
*Grace 3.1*
