# Topological Retrieval

**File:** `cognitive/magma/topological_retrieval.py`

## Overview

Magma Memory - Adaptive Topological Retrieval

Graph-based retrieval with adaptive traversal policies:
1. Starts from anchor nodes identified by Intent Router
2. Traverses relation graphs based on retrieval policy
3. Adapts traversal depth and breadth based on result quality
4. Combines graph traversal with vector similarity

Traversal Policies:
- BFS (Breadth-First): Explore neighbors at each level
- DFS (Depth-First): Deep exploration of single paths
- Best-First: Follow highest-weight edges
- Adaptive: Dynamically adjust based on results

## Classes

- `TraversalPolicy`
- `TraversalConfig`
- `TraversalState`
- `TraversalResult`
- `GraphTraverser`
- `AdaptiveTopologicalRetriever`

## Key Methods

- `bfs_traverse()`
- `best_first_traverse()`
- `bidirectional_traverse()`
- `retrieve()`
- `retrieve_neighbors()`

---
*Grace 3.1*
