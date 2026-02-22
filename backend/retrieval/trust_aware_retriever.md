# Trust Aware Retriever

**File:** `retrieval/trust_aware_retriever.py`

## Overview

Trust-Aware Document Retriever - Neuro-Symbolic Integration

Extends DocumentRetriever with trust-aware embeddings and trust-weighted similarity.
This creates a neuro-symbolic retrieval system where neural embeddings respect
symbolic trust scores from the knowledge base.

## Classes

- `TrustAwareDocumentRetriever`

## Key Methods

- `retrieve()`
- `retrieve_hybrid()`
- `retrieve_by_document()`
- `retrieve_by_source()`
- `build_context()`
- `collection_name()`
- `embedding_model()`
- `close()`
- `get_trust_aware_retriever()`

## Database Tables

None

## Connects To

- `embedding`
- `ml_intelligence.trust_aware_embedding`
- `retrieval.retriever`

---
*Documentation for Grace 3.1*
