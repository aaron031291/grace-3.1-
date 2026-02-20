# Relation Graphs

**File:** `cognitive/magma/relation_graphs.py`

## Overview

Magma Memory - Relation Graphs

Four interconnected graph types for rich memory relationships:
1. Semantic Graph - Meaning relationships between concepts
2. Temporal Graph - Time-based relationships and sequences
3. Causal Graph - Cause-effect relationships
4. Entity Graph - Entity relationships and co-occurrences

These graphs work together with the existing Memory Mesh to provide
graph-based retrieval and relationship traversal.

## Classes

- `RelationType`
- `GraphNode`
- `GraphEdge`
- `BaseRelationGraph`
- `SemanticGraph`
- `TemporalGraph`
- `CausalGraph`
- `EntityGraph`
- `MagmaRelationGraphs`

## Key Methods

- `add_node()`
- `add_edge()`
- `get_node()`
- `get_edge()`
- `get_neighbors()`
- `find_path()`
- `get_subgraph()`
- `calculate_node_importance()`
- `get_stats()`
- `add_concept()`
- `find_related_concepts()`
- `add_event()`
- `get_events_in_range()`
- `get_event_sequence()`
- `add_causal_link()`

---
*Grace 3.1*
