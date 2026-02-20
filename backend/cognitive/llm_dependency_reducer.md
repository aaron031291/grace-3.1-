# Llm Dependency Reducer

**File:** `cognitive/llm_dependency_reducer.py`

## Overview

LLM Dependency Reducer

Measures, tracks, and actively works toward reducing Grace's dependency
on external LLMs. This is the strategic layer that coordinates:

1. Dependency Metrics: How much does Grace rely on LLMs?
2. Reduction Tracking: How is dependency changing over time?
3. Training Data Export: Package learned patterns for local model training
4. Autonomy Scoring: Which domains can Grace handle independently?
5. Cost Analysis: How much is being saved by autonomous handling?

The goal: Over time, Grace should need Kimi (and other LLMs) less and
less for common tasks, eventually reaching a state where LLMs are only
needed for truly novel or complex situations.

## Classes

- `LLMDependencyReducer`

## Key Methods

- `calculate_dependency_metrics()`
- `get_dependency_trend()`
- `get_domain_autonomy_scores()`
- `export_training_data()`
- `get_reduction_recommendations()`
- `get_llm_dependency_reducer()`

---
*Grace 3.1*
