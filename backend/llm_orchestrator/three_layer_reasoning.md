# Three-Layer Reasoning Pipeline

**File:** `llm_orchestrator/three_layer_reasoning.py`

## Purpose

L1 parallel → L2 synthesis → L3 Grace verification

## Overview

Three-Layer Reasoning Pipeline

Layer 1 (Parallel Reasoning):
  All available LLMs receive the SAME data + prompt simultaneously.
  Each reasons independently using its own model/architecture.
  They cannot see each other's output yet.
  Output: N independent reasoning chains.

Layer 2 (Synthesis Reasoning):
  Each LLM receives ALL Layer 1 outputs combined.
  Each re-reasons on the SAME data but now informed by what everyone else thought.
  They synthesize, challenge, and refine their reasoning.
  Output: N synthesized conclusions that have been cross-examined.

Layer 3 (Grace Verification):
  Grace's cognitive engine verifies the synthesized outputs.
  Checks against: training data, knowledge base, trust scores, governance rules.
  Produces a final verified answer with confidence score.
  Output: Single verified truth.

The LLM orchestration system has access to:
- Training data (via retrieval/RAG)
- Kimi (primary LLM for complex tasks)
- All other available models
- Knowledge base for grounding

## Classes

- `ReasoningOutput`
- `LayerResult`
- `VerifiedResult`
- `ThreeLayerReasoning`

## Key Methods

- `client()`
- `get_available_models()`
- `get_training_context()`
- `layer1_parallel_reasoning()`
- `layer2_synthesis_reasoning()`
- `layer3_grace_verification()`
- `reason()`
- `get_three_layer_reasoning()`

## Database Tables

None (no DB tables)

## Dataclasses

- `ReasoningOutput`
- `LayerResult`
- `VerifiedResult`

## Connects To

- `cognitive.learning_hook`
- `cognitive.timesense_governance`
- `cognitive.unified_learning_pipeline`
- `genesis.unified_intelligence`
- `retrieval.retriever`
- `security.governance_middleware`
- `security.honesty_integrity_accountability`

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
