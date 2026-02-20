# Active Learning Sampler

**File:** `ml_intelligence/active_learning_sampler.py`

## Overview

Active Learning Sampler - Optimal Training Example Selection

Intelligently selects the most valuable examples for training to
maximize learning efficiency with minimal data.

Strategies:
- Uncertainty Sampling
- Query-by-Committee
- Expected Model Change
- Diversity Sampling
- Core-Set Selection
- Adversarial Sampling

## Classes

- `SamplingStrategy`
- `SampleScore`
- `UncertaintySampler`
- `EntropySampler`
- `MarginSampler`
- `QueryByCommittee`
- `ExpectedModelChangeSampler`
- `DiversitySampler`
- `CoreSetSampler`
- `ActiveLearningSampler`

## Key Methods

- `compute_uncertainty()`
- `select_samples()`
- `compute_entropy()`
- `select_samples()`
- `compute_margin()`
- `select_samples()`
- `compute_disagreement()`
- `select_samples()`
- `compute_gradient_magnitude()`
- `select_samples()`
- `select_samples()`
- `select_samples()`
- `select_samples()`
- `hybrid_selection()`
- `get_active_sampler()`

---
*Grace 3.1*
