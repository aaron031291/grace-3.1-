# Repo Access

**File:** `llm_orchestrator/repo_access.py`

## Overview

Repository Access Layer - Read-Only Access to GRACE Systems

Provides LLMs with read-only access to:
- Source code repository (file tree, contents)
- Genesis Keys (universal tracking)
- Librarian (semantic organization)
- Immutable Memory (episodic, procedural, patterns)
- RAG System (document retrieval)
- World Model (system state)
- Mesh Memory (learning memory, episodes, procedures)
- Ingestion Data (training data, learning examples)

All access is READ-ONLY and logged for audit.

## Classes

- `RepositoryAccessLayer`

## Key Methods

- `get_file_tree()`
- `read_file()`
- `search_code()`
- `get_genesis_key()`
- `search_genesis_keys()`
- `get_librarian_tags()`
- `get_librarian_relationships()`
- `rag_query()`
- `get_document()`
- `get_document_chunks()`
- `get_learning_examples()`
- `get_learning_patterns()`
- `get_system_stats()`
- `get_access_log()`
- `clear_access_log()`

---
*Grace 3.1*
