# Retriever

**File:** `retrieval/retriever.py`

## Overview

Document retriever module for RAG (Retrieval-Augmented Generation).
Retrieves relevant document chunks based on semantic similarity to queries.

## Classes

- `DocumentRetriever`

## Key Methods

- `retrieve()`
- `retrieve_hybrid()`
- `retrieve_by_document()`
- `retrieve_by_source()`
- `build_context()`
- `close()`
- `get_retriever()`

## Database Tables

None

## Connects To

- `database`
- `database.session`
- `embedding`
- `models.database_models`
- `vector_db.client`

---
*Documentation for Grace 3.1*
