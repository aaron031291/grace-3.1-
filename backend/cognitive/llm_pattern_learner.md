# Llm Pattern Learner

**File:** `cognitive/llm_pattern_learner.py`

## Overview

LLM Pattern Learner

Extracts reusable patterns from tracked LLM interactions to progressively
reduce dependency on external LLMs. This is the core "learning from Kimi"
system.

How it works:
1. Analyzes all recorded LLM interactions (from LLMInteractionTracker)
2. Identifies recurring reasoning patterns across similar tasks
3. Extracts deterministic action sequences from successful interactions
4. Builds a pattern library that Grace can use instead of calling the LLM
5. Validates patterns by comparing autonomous results to LLM results
6. Gradually expands the set of tasks Grace handles independently

Key Concepts:
- Pattern Signature: The abstract shape of a reasoning chain (action types)
- Pattern Confidence: How often this pattern leads to success
- Pattern Utility: How frequently this pattern is needed
- Replaceability Score: Whether Grace can handle this without an LLM

## Classes

- `LLMPatternLearner`

## Key Methods

- `extract_patterns()`
- `can_handle_autonomously()`
- `apply_pattern()`
- `get_pattern_stats()`
- `get_learning_progress()`
- `get_llm_pattern_learner()`

---
*Grace 3.1*
