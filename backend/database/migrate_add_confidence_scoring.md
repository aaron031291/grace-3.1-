# Migrate Add Confidence Scoring

**File:** `database/migrate_add_confidence_scoring.py`

## Overview

Migration script to add confidence scoring columns to documents and document_chunks tables.

This migration adds the following columns:

For documents table:
- confidence_score: Main confidence score (0.0-1.0)
- source_reliability: Source reliability component
- content_quality: Content quality component
- consensus_score: Consensus with existing knowledge
- recency_score: Recency component
- confidence_metadata: JSON field with detailed calculation data

For document_chunks table:
- confidence_score: Chunk-level confidence score
- consensus_similarity_scores: JSON array of similarity scores

The migration also drops the old trust_score column from documents table
and updates indexes for the new confidence_score column.

## Classes

None

## Key Methods

- `migrate_add_confidence_scoring()`

---
*Grace 3.1*
