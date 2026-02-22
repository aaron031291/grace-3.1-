# Query Intelligence

**File:** `retrieval/query_intelligence.py`

## Overview

Multi-Tier Query Intelligence System

Orchestrates intelligent query handling with three-tier fallback:
1. Tier 1 - VectorDB Search: Query Qdrant for relevant information
2. Tier 2 - Model Knowledge: Use model's built-in knowledge if VectorDB fails
3. Tier 3 - User Context Request: Request specific context from user

Each tier has quality/confidence thresholds that trigger fallback to next tier.

## Classes

- `QueryTier`
- `ConfidenceMetrics`
- `KnowledgeGap`
- `QueryResult`
- `MultiTierQueryHandler`

## Key Methods

- `is_high_quality()`
- `to_dict()`
- `to_dict()`
- `handle_query()`

## Database Tables

None

## Connects To

- `embedding`
- `ingestion.service`
- `retrieval.reranker`

---
*Documentation for Grace 3.1*
