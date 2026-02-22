# Chat Integration

**File:** `cognitive/magma/chat_integration.py`

## Overview

Magma Chat Integration

Wires Magma's intent-aware retrieval into Grace's chat endpoints.
Instead of using the basic retriever, chat queries go through:
1. Magma's intent classifier (what type of question is this?)
2. Graph-based retrieval (semantic + temporal + causal + entity)
3. RRF fusion (combine results from multiple graphs)
4. Context synthesis (generate LLM-ready context)

This replaces the basic retriever in the multi-tier integration.

## Classes

None

## Key Methods

- `get_magma_enhanced_context()`
- `enrich_rag_context()`
- `ingest_chat_interaction()`

---
*Grace 3.1*
