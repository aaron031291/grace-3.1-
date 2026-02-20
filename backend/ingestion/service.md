# Service

**File:** `ingestion/service.py`

## Overview

Text ingestion service for processing documents and storing embeddings.
Handles chunking, embedding generation, and vector storage.

## Classes

- `TextChunker`
- `TextIngestionService`

## Key Methods

- `cognitive_operation()`
- `chunk_text()`
- `compute_file_hash()`
- `ingest_text_fast()`
- `ingest_text()`
- `search_documents()`
- `get_document_info()`
- `list_documents()`
- `delete_document()`

## Database Tables

None

## Connects To

- `cognitive.decorators`
- `cognitive.learning_hook`
- `cognitive.timesense_governance`
- `cognitive.unified_learning_pipeline`
- `confidence_scorer`
- `database`
- `database.session`
- `embedding`
- `models.database_models`
- `vector_db.client`

---
*Documentation for Grace 3.1*
