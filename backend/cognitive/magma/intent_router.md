# Intent Router

**File:** `cognitive/magma/intent_router.py`

## Overview

Magma Memory - Intent-Aware Router

Routes queries to appropriate retrieval strategies based on:
1. Intent Classification - What type of information is being sought
2. Anchor Identification - Key concepts/entities in the query
3. Graph Selection - Which relation graphs to query
4. Retrieval Policy - How to traverse and combine results

This is the entry point for the Magma query process.

## Classes

- `QueryIntent`
- `AnchorType`
- `Anchor`
- `QueryAnalysis`
- `IntentClassifier`
- `AnchorIdentifier`
- `GraphSelector`
- `RetrievalPolicySelector`
- `IntentAwareRouter`

## Key Methods

- `classify()`
- `identify()`
- `select()`
- `select()`
- `analyze_query()`
- `route()`
- `get_anchor_embeddings_needed()`

---
*Grace 3.1*
