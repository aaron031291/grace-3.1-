# Enterprise Determinism

Determinism in Grace means **same inputs ⇒ same outputs** for IDs, gates, and choices. No random, no model in the core logic. This supports auditability, compliance, and reproducible runs.

## Principles

1. **Single source of truth** — `core/determinism.py` is the only place for deterministic IDs and gates.
2. **Configurable** — Env vars (e.g. `DETERMINISM_TEMPERATURE_CAPPED`) allow tuning without code change.
3. **Auditable** — Gate decisions log at DEBUG with structured `extra` for SIEM or log aggregation.
4. **Bounded & encoded** — Inputs truncated (e.g. task to 200 chars), UTF-8 encoding explicit.

## API (v1.0)

| Function | Purpose |
|----------|--------|
| `deterministic_choice(options, seed)` | Pick one from list by hash(seed). |
| `deterministic_run_id(task)` | Pipeline run ID: `PIPE-` + 8 hex (task + minute bucket). |
| `deterministic_trace_id(path, name)` | Trace ID: 16 hex (path/name + minute bucket). |
| `should_use_llm(phase0_result, task, layer_name, force_deterministic)` | Gate: use LLM only when Phase 0 hands off. |
| `deterministic_temperature(for_deterministic)` | 0.0 when deterministic, else capped (default 0.3). |
| `llm_kwargs_for_determinism(use_deterministic, **kwargs)` | Merge temperature into LLM kwargs. |
| `deterministic_model_choice(available_models, task_seed)` | Same task_seed ⇒ same model. |
| `get_determinism_info()` | Version and config for health/observability. |

## Configuration

| Env | Default | Description |
|-----|---------|-------------|
| `DETERMINISM_TEMPERATURE_CAPPED` | 0.3 | Max temperature when not in deterministic mode. |

## Observability

- **Health / status** — Call `get_determinism_info()` to expose API version and effective config.
- **Audit** — Enable DEBUG for `core.determinism` to log every `should_use_llm` decision with reason and layer.

## Tests

Run the validation suite:

```bash
pytest tests/test_determinism_validation.py -v
```

All tests assert same-seed ⇒ same result and correct gate behavior.
