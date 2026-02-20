# Llm Learning Api

**File:** `api/llm_learning_api.py`

## Overview

LLM Learning and Tracking API

REST API endpoints for the LLM interaction tracking, pattern learning,
command routing, and dependency reduction systems.

Endpoints:
- /llm-learning/track         - Record LLM interactions
- /llm-learning/route         - Route tasks via Kimi command router
- /llm-learning/patterns      - View and manage extracted patterns
- /llm-learning/dependency    - View dependency metrics and trends
- /llm-learning/training-data - Export training data for local models
- /llm-learning/progress      - View learning progress
- /llm-learning/coding-tasks  - Track coding task delegation

## Classes

- `RecordInteractionRequest`
- `UpdateInteractionRequest`
- `RouteTaskRequest`
- `RecordCodingTaskRequest`
- `UpdateCodingTaskRequest`
- `ToolCallRequest`
- `ParallelToolCallRequest`
- `KimiAnalyzeRequest`
- `UserConfirmationRequest`

## Key Methods

- `get_tracker()`
- `get_router_instance()`
- `get_learner()`
- `get_reducer()`
- `get_tool_executor()`
- `get_brain()`
- `get_executor_instance()`
- `get_verification_engine()`

---
*Grace 3.1*
