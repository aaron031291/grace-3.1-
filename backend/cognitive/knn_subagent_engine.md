# KNN Sub-Agent Swarm

**File:** `cognitive/knn_subagent_engine.py`

## Purpose

Parallel multi-threaded knowledge discovery with 4 sub-agents

## Overview

KNN Sub-Agent Engine — Parallel, Multi-Threaded Knowledge Discovery

Upgrades the KNN expansion from a single-threaded BFS to a swarm of
parallel sub-agents that simultaneously explore different branches
of the knowledge graph.

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                   KNN ORCHESTRATOR                           │
│                                                               │
│  Distributes seeds across sub-agents, merges discoveries     │
│                                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ Vector   │ │ Web      │ │ API      │ │ Cross    │       │
│  │ Search   │ │ Search   │ │ Search   │ │ Domain   │       │
│  │ Agent    │ │ Agent    │ │ Agent    │ │ Agent    │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│       │             │            │             │             │
│       ▼             ▼            ▼             ▼             │
│  Qdrant KNN    SerpAPI/Web   GitHub/PyPI   Domain folders   │
│  neighbors     results       READMEs      cross-reference   │
│                                                               │
│  All results → Merge → Deduplicate → Score → Feed Oracle    │
└─────────────────────────────────────────────────────────────┘

Sub-Agents:
1. VectorSearchAgent — KNN on Qdrant (existing, now parallel)
2. WebSearchAgent — SerpAPI/web scraping for external knowledge
3. APISearchAgent — GitHub API, PyPI, npm for package docs
4. CrossDomainAgent — Finds connections between different domain folders

All run in parallel via ThreadPoolExecutor.

## Classes

- `Discovery`
- `SwarmResult`
- `VectorSearchAgent`
- `WebSearchAgent`
- `APISearchAgent`
- `CrossDomainAgent`
- `KNNSubAgentOrchestrator`

## Key Methods

- `search()`
- `search()`
- `search()`
- `search()`
- `swarm_expand()`
- `get_stats()`
- `get_knn_orchestrator()`

## Database Tables

None (no DB tables)

## Dataclasses

- `Discovery`
- `SwarmResult`

## Connects To

- `cognitive.learning_hook`
- `cognitive.swarm_comms`
- `cognitive.unified_learning_pipeline`
- `genesis.unified_intelligence`
- `librarian.knowledge_organizer`
- `retrieval.retriever`

## How It Works

This module is part of Grace 3.1's autonomous intelligence system.
See the source code docstring and inline comments for detailed logic.

---
*Auto-generated documentation for Grace 3.1 rocketdev branch*
