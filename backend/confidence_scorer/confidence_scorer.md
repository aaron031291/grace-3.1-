# Confidence Scorer

**File:** `confidence_scorer/confidence_scorer.py`

## Overview

Confidence scoring system for knowledge quality assessment.

Calculates confidence scores based on multiple factors:
- source_reliability: Type and trustworthiness of the source
- content_quality: Quality indicators of the content itself
- consensus_score: Agreement with existing knowledge base (with contradiction detection)
- recency: How recent the information is

Formula:
confidence_score = (
    source_reliability * 0.35 +
    content_quality * 0.25 +
    consensus_score * 0.25 +
    recency * 0.10
)

Now includes semantic contradiction detection to prevent contradictory chunks
from artificially boosting consensus scores.

## Classes

- `ConfidenceScorer`

## Key Methods

- `calculate_source_reliability()`
- `calculate_content_quality()`
- `calculate_consensus_score()`
- `calculate_recency()`
- `calculate_confidence_score()`

---
*Grace 3.1*
