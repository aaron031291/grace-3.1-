# Rrf Fusion

**File:** `cognitive/magma/rrf_fusion.py`

## Overview

Magma Memory - RRF Fusion (Reciprocal Rank Fusion)

Combines results from multiple retrieval sources:
1. Multiple relation graphs (semantic, temporal, causal, entity)
2. Vector similarity search
3. Keyword/BM25 search
4. Graph traversal results

RRF formula: score(d) = Σ 1 / (k + rank_i(d))
where k is a constant (typically 60) and rank_i(d) is the rank of document d in result list i.

This provides a robust way to merge rankings without requiring score normalization.

## Classes

- `RetrievalResult`
- `FusedResult`
- `FusionMethod`
- `RRFFusion`
- `WeightedRRFFusion`
- `CombSUMFusion`
- `CombMNZFusion`
- `InterleavingFusion`
- `MagmaFusion`

## Key Methods

- `fuse()`
- `set_source_weight()`
- `set_source_weights()`
- `fuse()`
- `fuse()`
- `fuse()`
- `fuse()`
- `fuse()`
- `fuse_with_limit()`
- `set_method()`
- `set_source_weight()`
- `create_retrieval_results()`

---
*Grace 3.1*
