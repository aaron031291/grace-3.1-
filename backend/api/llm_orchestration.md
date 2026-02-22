# Llm Orchestration

**File:** `api/llm_orchestration.py`

## Overview

LLM Orchestration API Endpoints

Provides REST API access to the multi-LLM orchestration system.

All endpoints:
- Track with Genesis Keys
- Enforce cognitive framework
- Verify outputs through 5-layer pipeline
- Integrate with learning memory
- Log for audit

## Classes

- `LLMTaskRequest`
- `LLMTaskResponse`
- `ModelListResponse`
- `StatsResponse`
- `RepoQueryRequest`
- `RepoQueryResponse`
- `DebateRequest`
- `ConsensusRequest`
- `DelegateRequest`
- `ReviewRequest`
- `FineTuneDatasetRequest`
- `NearZeroVerifyRequest`

## Key Methods

- `get_or_create_embedding_model()`
- `get_orchestrator()`

---
*Grace 3.1*
