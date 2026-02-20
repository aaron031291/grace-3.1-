# Memory Mesh Cache

**File:** `cognitive/memory_mesh_cache.py`

## Overview

Memory Mesh Caching Layer

Multi-tier caching for Memory Mesh scalability:
- Tier 1: LRU cache for high-trust learning examples
- Tier 2: Procedure match cache
- Tier 3: Stats cache

Performance Improvement: 5-10x faster for cached queries

## Classes

- `MemoryMeshCache`

## Key Methods

- `invalidate_all()`
- `get_cache_stats()`
- `get_high_trust_learning()`
- `get_or_compute_stats()`
- `find_similar_examples()`
- `find_matching_procedure()`
- `get_memory_mesh_cache()`
- `invalidate_memory_mesh_cache()`

## Database Tables

None

## Connects To

- `models.database_models`

---
*Documentation for Grace 3.1*
