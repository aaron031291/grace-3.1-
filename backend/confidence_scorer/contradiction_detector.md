# Contradiction Detector

**File:** `confidence_scorer/contradiction_detector.py`

## Overview

Semantic contradiction detection using NLP.

Uses cross-encoder/nli-deberta-large model for accurate entailment detection.
Instead of hardcoded keyword checks, uses semantic understanding to detect
when two chunks express contradictory claims.

## Classes

- `SemanticContradictionDetector`

## Key Methods

- `detect_contradiction()`
- `batch_detect_contradictions()`
- `adjust_consensus_for_contradictions()`
- `analyze_claim_agreement()`

---
*Grace 3.1*
