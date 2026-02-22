# Hallucination Guard

**File:** `llm_orchestrator/hallucination_guard.py`

## Overview

Hallucination Mitigation Pipeline

Multi-layered approach to minimize LLM hallucinations:

Layer 1: Repository Grounding - Claims must reference actual files/code
Layer 2: Cross-Model Consensus - Multiple LLMs must agree
Layer 3: Contradiction Detection - Check against existing knowledge
Layer 4: Confidence Scoring - Trust score calculation
Layer 5: Trust System Verification - Validate against learning memory
Layer 6: External Verification - Web search and documentation lookup

All operations are tracked and logged.

## Classes

- `ExternalVerifier`
- `ConsensusResult`
- `VerificationResult`
- `HallucinationGuard`

## Key Methods

- `verify_technical_claim()`
- `verify_factual_claim()`
- `get_cache_stats()`
- `clear_cache()`
- `verify_repository_grounding()`
- `check_cross_model_consensus()`
- `verify_external()`
- `check_contradictions()`
- `calculate_confidence_score()`
- `verify_against_trust_system()`
- `verify_content()`
- `get_verification_log()`
- `get_verification_stats()`
- `get_hallucination_guard()`

## Database Tables

None

## Connects To

- `confidence_scorer.confidence_scorer`
- `confidence_scorer.contradiction_detector`

---
*Documentation for Grace 3.1*
