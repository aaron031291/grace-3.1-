# Online Learning Pipeline

**File:** `ml_intelligence/online_learning_pipeline.py`

## Overview

Online Learning Pipeline - Continuous Model Updates

Enables real-time model updates as new data arrives, without
requiring full retraining. Supports incremental learning for
embeddings, classifiers, and other models.

Features:
- Streaming mini-batch updates
- Catastrophic forgetting prevention (EWC)
- Dynamic model expansion
- Continuous evaluation
- Automatic checkpointing

## Classes

- `StreamingBatch`
- `ModelCheckpoint`
- `ElasticWeightConsolidation`
- `OnlineLearningPipeline`
- `IncrementalEmbeddingLearner`

## Key Methods

- `compute_fisher_information()`
- `penalty()`
- `update()`
- `update_ewc()`
- `checkpoint()`
- `load_checkpoint()`
- `get_metrics_summary()`
- `adapt_embedding()`
- `learn_from_positive_pair()`
- `save_adapter()`
- `load_adapter()`
- `get_online_learning_pipeline()`
- `get_incremental_embedder()`

---
*Grace 3.1*
