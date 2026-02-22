# Learning Memory

**File:** `cognitive/learning_memory.py`

## Overview

Learning Memory System - Connects to Memory Mesh

Manages training data from learning memory folders and feeds it
to the memory mesh with trust scores for continuous improvement.

## Classes

- `LearningExample`
- `LearningPattern`
- `TrustScorer`
- `LearningMemoryManager`

## Key Methods

- `calculate_trust_score()`
- `update_trust_on_validation()`
- `ingest_learning_data()`
- `get_training_data()`
- `update_trust_on_usage()`
- `decay_trust_scores()`

## Database Tables

- `learning_examples`
- `learning_patterns`

## Connects To

- `database.base`

---
*Documentation for Grace 3.1*
