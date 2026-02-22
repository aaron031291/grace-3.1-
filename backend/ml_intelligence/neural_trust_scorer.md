# Neural Trust Scorer

**File:** `ml_intelligence/neural_trust_scorer.py`

## Overview

Neural Trust Scorer - Deep Learning-based Trust Scoring System

Replaces rule-based trust scoring with a learned neural network that
adapts based on observed outcomes and feedback.

Features:
- Multi-layer feedforward network with attention
- Online learning with experience replay
- Confidence intervals via Monte Carlo dropout
- Feature engineering from learning examples
- Adversarial robustness testing

## Classes

- `TrustFeatures`
- `TrainingExample`
- `TrustScorerNetwork`
- `ExperienceReplay`
- `NeuralTrustScorer`

## Key Methods

- `forward()`
- `predict_with_uncertainty()`
- `add()`
- `sample()`
- `extract_features()`
- `features_to_tensor()`
- `predict_trust()`
- `update_from_outcome()`
- `train_step()`
- `adversarial_test()`
- `save_model()`
- `load_model()`
- `get_stats()`
- `get_neural_trust_scorer()`

---
*Grace 3.1*
