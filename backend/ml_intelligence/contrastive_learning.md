# Contrastive Learning

**File:** `ml_intelligence/contrastive_learning.py`

## Overview

Contrastive Learning - Better Representation Learning

Learns better embeddings by contrasting similar vs dissimilar examples.

Implementations:
- SimCLR: Contrastive learning with data augmentation
- Supervised Contrastive Learning
- Triplet Loss
- N-Pair Loss
- Hard Negative Mining

## Classes

- `ContrastiveBatch`
- `NTXentLoss`
- `TripletLoss`
- `SupervisedContrastiveLoss`
- `HardNegativeMiner`
- `ContrastiveLearner`

## Key Methods

- `forward()`
- `compute_distance()`
- `forward()`
- `forward()`
- `compute_pairwise_distances()`
- `mine_hard_negatives()`
- `forward()`
- `train_step()`
- `encode()`
- `compute_similarity()`
- `get_training_stats()`
- `save_model()`
- `load_model()`
- `get_contrastive_learner()`

---
*Grace 3.1*
