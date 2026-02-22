# Multi Llm Client

**File:** `llm_orchestrator/multi_llm_client.py`

## Overview

Multi-LLM Client - Manages multiple open-source LLMs via Ollama

Supports:
- DeepSeek Coder (code generation, debugging)
- Qwen 2.5 Coder (code understanding)
- DeepSeek-R1 (reasoning)
- Mistral Small (fast queries)
- Llama 3.x (general purpose)
- Gemma 2 (validation tasks)

Features:
- Model selection based on task type
- Load balancing
- Failover with automatic retry
- Performance tracking
- Rate limiting
- Response caching
- Production-ready error handling

## Classes

- `RateLimiter`
- `LRUCache`
- `RetryConfig`
- `TaskType`
- `ModelCapability`
- `LLMModel`
- `MultiLLMClient`

## Key Methods

- `acquire()`
- `get_status()`
- `get()`
- `set()`
- `clear()`
- `get_stats()`
- `get_delay()`
- `should_retry()`
- `select_model()`
- `generate()`
- `generate_multiple()`
- `get_available_models()`
- `get_model_stats()`
- `reset_stats()`
- `get_system_status()`
- `clear_cache()`
- `shutdown()`
- `get_multi_llm_client()`

## Database Tables

None

## Connects To

Self-contained

---
*Documentation for Grace 3.1*
