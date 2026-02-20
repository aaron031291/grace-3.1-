# Episodic Memory

**File:** `cognitive/episodic_memory.py`

## Overview

Episodic Memory - Concrete Experiences

Stores what happened, when it happened, and what the outcome was.
This is different from semantic knowledge - it's experiential.

OPTIMIZED: Now supports semantic similarity using embeddings

## Classes

- `Episode`
- `EpisodicBuffer`

## Key Methods

- `embedder()`
- `record_episode()`
- `recall_similar()`
- `generate_episode_embedding()`
- `index_all_episodes()`
- `recall_by_topic()`

## Database Tables

- `episodes`

## Connects To

- `database.base`
- `embedding`

---
*Documentation for Grace 3.1*
