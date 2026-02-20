# Async Consolidation

**File:** `cognitive/magma/async_consolidation.py`

## Overview

Magma Memory - Async Consolidation Pipeline

Asynchronous processing for:
1. Async Queue - Buffer for pending operations
2. Neighbor Retrieval - Graph-based neighbor fetching
3. Context Synthesizer - Linearized context generation for LLM
4. Background Consolidation - Periodic graph optimization

This handles the "Asynchronous Consolidation" box in the Magma architecture.

## Classes

- `OperationType`
- `OperationPriority`
- `QueuedOperation`
- `OperationResult`
- `AsyncOperationQueue`
- `NeighborRetriever`
- `ContextSynthesizer`
- `ConsolidationWorker`

## Key Methods

- `enqueue()`
- `dequeue()`
- `peek()`
- `store_result()`
- `get_result()`
- `get_queue_sizes()`
- `total_pending()`
- `get_neighbors()`
- `get_multi_hop_neighbors()`
- `synthesize()`
- `synthesize_with_structure()`
- `start()`
- `stop()`

---
*Grace 3.1*
