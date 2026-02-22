# Kimi Knowledge Feedback Loop

**File:** `cognitive/kimi_knowledge_feedback.py`

## Purpose

Embeds Kimi's high-quality answers back into the vector DB

## Overview

Kimi Knowledge Feedback Loop

Every time Kimi generates a high-quality answer, it gets embedded back
into the Qdrant vector DB so that:

1. KNN can discover edges from Kimi's synthesized knowledge
2. RAG retrieval can use Kimi's past answers (no repeating work)
3. Self-agents can find Kimi's insights in vector search
4. The knowledge base grows from BOTH books AND Kimi's reasoning

Quality gate: Only answers with confidence >= 0.7 and length >= 200
characters get vectorized. Low-quality or short answers are filtered out.

This creates a knowledge flywheel:
  User asks question -> Kimi synthesizes answer -> Answer embedded ->
  KNN discovers connections -> Next question gets BETTER context ->
  Kimi gives BETTER answer -> Embedded -> KNN expands further -> ...

## Classes

- `KimiKnowledgeFeedback`

## Key Methods

- `ingestion()`
- `feed_answer()`
- `get_stats()`
- `get_kimi_feedback()`

## Database Tables

None (no DB tables)

## Dataclasses

None

## Connects To

- `cognitive.learning_hook`
- `ingestion.service`

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
