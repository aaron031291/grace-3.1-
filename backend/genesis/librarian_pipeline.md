# Librarian Pipeline

**File:** `genesis/librarian_pipeline.py`

## Overview

Librarian Ingestion Pipeline
============================
Full data ingestion flow with Genesis Key tracking.
Data comes in → Genesis Key → Indexed → Files created/named → Saved in memory → Shows in UI

Integrations:
- Genesis Key Service: Every ingestion gets a properly tracked Genesis Key
- Mirror Self-Modeling: Ingestions are observed for pattern learning
- Cognitive Framework: Decisions about filing and categorization
- Trust Scores: Ingestion reliability tracking
- Version Control: All ingestions are version controlled

## Classes

- `IngestionStatus`
- `ContentType`
- `IngestionRecord`
- `IngestionResult`
- `LibrarianPipeline`

## Key Methods

- `get_genesis_key_service()`
- `get_mirror_system()`
- `add_listener()`
- `remove_listener()`
- `get_ingestion()`
- `get_ingestions_by_genesis_key()`
- `list_ingestions()`
- `get_statistics()`
- `search_library()`
- `get_librarian_pipeline()`

## DB Tables

None

---
*Grace 3.1 Documentation*
