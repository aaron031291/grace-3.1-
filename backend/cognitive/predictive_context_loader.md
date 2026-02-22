# Predictive Context Loader

**File:** `cognitive/predictive_context_loader.py`

## Overview

Predictive Context Loader - Proactive Knowledge Fetching

Grace doesn't just wait for queries - she thinks ahead!

When Grace encounters a whitelisted trigger (e.g., "REST API design"),
she proactively pre-fetches related topics and brings them into context
BEFORE they're explicitly requested.

This is deterministic preemptive fetching:
1. Detect trigger topic
2. Identify neighboring/related topics
3. Pre-fetch relevant knowledge
4. Cache in active context
5. Ready when needed

## Classes

- `PreFetchedContext`
- `TopicRelationshipGraph`
- `WhitelistTrigger`
- `PredictiveContextLoader`

## Key Methods

- `get_related_topics()`
- `learn_relationship()`
- `should_prefetch()`
- `get_prefetch_depth()`
- `process_query()`
- `get_cached_context()`
- `warmup_topics()`
- `clear_expired_cache()`
- `get_statistics()`

## Database Tables

None

## Connects To

- `cognitive.learning_memory`
- `retrieval.retriever`

---
*Documentation for Grace 3.1*
