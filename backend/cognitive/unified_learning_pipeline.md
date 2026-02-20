# Unified Learning Pipeline

**File:** `cognitive/unified_learning_pipeline.py`

## Purpose

24/7 continuous data pipeline with neighbor-by-neighbor topic expansion

## Overview

Unified Learning Pipeline - Neighbor-by-Neighbor Topic Expansion

Connects Oracle ML predictions, ingestion pipeline, and learning memory
into a continuous 24/7 data pipeline that:

1. Takes training data from Oracle (ingested documents)
2. Performs neighbor-by-neighbor search for related topics
3. Expands knowledge graph through semantic proximity
4. Feeds discoveries back into the learning system
5. Runs perpetually as a background daemon

This is the "push it as far as we can" module for the learning system.

## Classes

- `TopicNode`
- `ExpansionResult`
- `NeighborByNeighborEngine`
- `UnifiedLearningPipeline`

## Key Methods

- `retriever()`
- `expand_from_seed()`
- `get_knowledge_graph()`
- `start()`
- `stop()`
- `add_seed()`
- `get_status()`
- `get_unified_pipeline()`

## Database Tables

None (no DB tables)

## Dataclasses

- `TopicNode`
- `ExpansionResult`

## Connects To

- `cognitive.knn_subagent_engine`
- `cognitive.learning_memory`
- `cognitive.predictive_context_loader`
- `genesis.unified_intelligence`
- `retrieval.retriever`

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
