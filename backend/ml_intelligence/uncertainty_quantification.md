# Uncertainty Quantification

**File:** `ml_intelligence/uncertainty_quantification.py`

## Overview

Uncertainty Quantification - Bayesian Confidence Estimation

Provides calibrated confidence estimates for predictions using:
- Bayesian Neural Networks
- Monte Carlo Dropout
- Deep Ensembles
- Conformal Prediction
- Epistemic vs Aleatoric Uncertainty

Helps the system know when it doesn't know something.

## Classes

- `UncertaintyEstimate`
- `BayesianLinear`
- `BayesianNeuralNetwork`
- `MCDropoutNetwork`
- `DeepEnsemble`
- `ConformalPredictor`
- `UncertaintyQuantifier`

## Key Methods

- `reset_parameters()`
- `forward()`
- `kl_divergence()`
- `forward()`
- `kl_divergence()`
- `predict_with_uncertainty()`
- `forward()`
- `predict_with_uncertainty()`
- `train_ensemble()`
- `predict_with_uncertainty()`
- `calibrate()`
- `predict_interval()`
- `predict_with_uncertainty()`
- `calibrate()`
- `create_bayesian_network()`

---
*Grace 3.1*
