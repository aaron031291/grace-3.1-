"""
Enterprise determinism — single source of truth for reproducible, auditable behavior.

Design principles:
  - No random, no model in ID or gate logic; same inputs ⇒ same outputs.
  - Configurable via env (DETERMINISM_*) for compliance and tuning without code change.
  - Structured logging at DEBUG for audit trails (who decided what, why).
  - Explicit encoding (UTF-8) and bounded inputs for security and portability.

Use everywhere that must be reproducible: pipeline run IDs, trace IDs, LLM gates,
model selection, temperature, and Genesis key alignment.

API version: 1.0 — bump when hashing or gate semantics change.
"""

import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Constants (enterprise: no magic numbers, env-overridable) ─────────────────

DETERMINISM_API_VERSION = "1.0"
DEFAULT_HASH_ALGORITHM = "sha256"
DEFAULT_ENCODING = "utf-8"
RUN_ID_PREFIX = "PIPE-"
RUN_ID_HEX_LEN = 8
TRACE_ID_HEX_LEN = 16
KEY_ID_HEX_LEN = 32
TASK_TRUNCATE = 200
TEMPERATURE_DETERMINISTIC = 0.0
TEMPERATURE_NONDETERMINISTIC_CAP = 0.3


def _config_float(key: str, default: float) -> float:
    """Read float from env for tunable constants."""
    val = os.environ.get(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _hash_payload(payload: str, hex_len: int = 32) -> str:
    """Single canonical hash: UTF-8, SHA-256, deterministic."""
    raw = payload.encode(DEFAULT_ENCODING, errors="replace")
    return hashlib.sha256(raw).hexdigest()[:hex_len]


# ── Public API ─────────────────────────────────────────────────────────────────

def deterministic_choice(options: List[Any], seed: str = "") -> Optional[Any]:
    """
    Pick one option deterministically from seed (no random).

    Args:
        options: Non-empty list of choices.
        seed: Deterministic seed; same seed ⇒ same choice.

    Returns:
        One element from options, or None if options is empty.

    Example:
        >>> deterministic_choice(["a", "b", "c"], "task-1")
        'b'
    """
    if not options:
        return None
    seed_safe = seed if seed is not None else ""
    idx = int(_hash_payload(seed_safe, 16), 16) % len(options)
    return options[idx]


def deterministic_run_id(task: str, bucket_minutes: bool = True) -> str:
    """
    Deterministic pipeline run ID: same task in same time bucket ⇒ same ID.

    Args:
        task: Task description (truncated to TASK_TRUNCATE).
        bucket_minutes: If True, bucket by minute (default); if False, by second.

    Returns:
        Run ID like PIPE-<8 hex chars>.
    """
    fmt = "%Y-%m-%d-%H-%M" if bucket_minutes else "%Y-%m-%d-%H-%M-%S"
    bucket = datetime.now(timezone.utc).strftime(fmt)
    task_safe = (task or "")[:TASK_TRUNCATE]
    payload = f"{RUN_ID_PREFIX.strip('-')}|{task_safe}|{bucket}"
    return f"{RUN_ID_PREFIX}{_hash_payload(payload, RUN_ID_HEX_LEN)}"


def deterministic_trace_id(path: str = "", name: str = "", bucket_minutes: bool = True) -> str:
    """
    Deterministic trace ID from path/name + time bucket (no UUID).

    Args:
        path: Request path or scope.
        name: Span or operation name.
        bucket_minutes: If True, same minute ⇒ same ID for same path/name.

    Returns:
        16-char hex trace ID.
    """
    fmt = "%Y%m%d%H%M" if bucket_minutes else "%Y%m%d%H%M%S"
    bucket = datetime.now(timezone.utc).strftime(fmt)
    seed = f"{path or ''}|{name or ''}|{bucket}"
    return _hash_payload(seed, TRACE_ID_HEX_LEN)


def should_use_llm(
    phase0_result: Optional[Dict[str, Any]] = None,
    task: str = "",
    layer_name: str = "",
    force_deterministic: bool = False,
) -> bool:
    """
    Gate: should this step use the LLM or stay deterministic?

    Returns False when deterministic path is sufficient (Phase 0 handled it or
    force_deterministic is set). Logs at DEBUG for audit.

    Args:
        phase0_result: Result from deterministic-first loop; handoff_to_llm drives decision.
        task: Task description (for logging).
        layer_name: Pipeline layer name (for logging).
        force_deterministic: If True, always return False.

    Returns:
        True if LLM should be used, False otherwise.
    """
    if force_deterministic:
        logger.debug(
            "determinism.gate should_use_llm=False reason=force_deterministic layer=%s",
            layer_name or "",
            extra={"gate": "should_use_llm", "decision": False, "reason": "force_deterministic", "layer": layer_name},
        )
        return False
    if phase0_result is not None and not phase0_result.get("handoff_to_llm", True):
        logger.debug(
            "determinism.gate should_use_llm=False reason=phase0_no_handoff layer=%s",
            layer_name or "",
            extra={"gate": "should_use_llm", "decision": False, "reason": "phase0_no_handoff", "layer": layer_name},
        )
        return False
    return True


def deterministic_temperature(for_deterministic: bool = True) -> float:
    """
    Temperature for LLM calls: 0 when deterministic, else capped value.

    Override via env: DETERMINISM_TEMPERATURE_CAPPED (default 0.3).
    """
    if for_deterministic:
        return TEMPERATURE_DETERMINISTIC
    cap = _config_float("DETERMINISM_TEMPERATURE_CAPPED", TEMPERATURE_NONDETERMINISTIC_CAP)
    return cap


def llm_kwargs_for_determinism(use_deterministic: bool, **kwargs: Any) -> Dict[str, Any]:
    """Merge temperature into kwargs for LLM calls (deterministic ⇒ 0)."""
    out = dict(kwargs)
    out["temperature"] = deterministic_temperature(use_deterministic)
    return out


def deterministic_model_choice(available_models: List[str], task_seed: str = "") -> str:
    """Pick one model deterministically (same task_seed ⇒ same model)."""
    if not available_models:
        return ""
    return deterministic_choice(available_models, task_seed or "default") or ""


def get_determinism_info() -> Dict[str, Any]:
    """Return version and config for health/docs (enterprise observability)."""
    return {
        "api_version": DETERMINISM_API_VERSION,
        "hash_algorithm": DEFAULT_HASH_ALGORITHM,
        "encoding": DEFAULT_ENCODING,
        "temperature_deterministic": TEMPERATURE_DETERMINISTIC,
        "temperature_capped": _config_float("DETERMINISM_TEMPERATURE_CAPPED", TEMPERATURE_NONDETERMINISTIC_CAP),
    }
