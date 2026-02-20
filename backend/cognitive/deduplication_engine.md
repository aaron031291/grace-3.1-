# Deduplication Engine

**File:** `cognitive/deduplication_engine.py`

## Purpose

Multi-layer deduplication preventing duplicate data at every level

## Overview

Deduplication Engine

Multi-layer deduplication to prevent duplicate data from entering
any part of the system:

Layer 1 — File-level: SHA256 hash of raw file content (ingestion service)
Layer 2 — Chunk-level: Hash of chunk text before embedding (ingestion)
Layer 3 — Semantic-level: Cosine similarity check against existing vectors
Layer 4 — Oracle-level: Unified intelligence record dedup
Layer 5 — Pipeline-level: Processed seeds set (neighbor expansion)

This engine adds Layer 3 (semantic) and Layer 4 (Oracle) which were missing.

## Classes

- `DeduplicationEngine`

## Key Methods

- `check_file_duplicate()`
- `check_semantic_duplicate()`
- `check_title_duplicate()`
- `check_oracle_record_duplicate()`
- `get_stats()`
- `get_dedup_engine()`

## Database Tables

None (no DB tables)

## Dataclasses

None

## Connects To

- `genesis.unified_intelligence`
- `retrieval.retriever`

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
