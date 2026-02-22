# Engine

**File:** `librarian/engine.py`

## Overview

LibrarianEngine - Central Orchestrator

Coordinates all librarian components to provide comprehensive file management:
- Rule-based categorization
- AI content analysis (via LLM Orchestrator)
- Tag management
- Relationship detection
- Approval workflow

FULLY INTEGRATED with:
- LLM Orchestrator for AI operations
- Cognitive Framework (OODA Loop + 12 Invariants)
- Genesis Key tracking
- Layer 1 Message Bus

This is the main entry point for the librarian system.

## Classes

- `LibrarianEngine`

## Key Methods

- `process_document()`
- `process_batch()`
- `reprocess_all_documents()`
- `get_system_statistics()`
- `health_check()`

---
*Grace 3.1*
