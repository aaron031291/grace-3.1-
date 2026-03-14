"""
Shared Ollama model resolution: exact existence check and fallback chain.

Used by consensus_engine and factory so the same resolved model name is used
everywhere (avoids "model not found" when the configured tag is not pulled).
"""

import logging

logger = logging.getLogger(__name__)

# Fallback lists (in order). Qwen3.5 (MoE, 256K ctx, agentic RL) → Qwen3-Coder → Qwen3.
CODE_FALLBACKS = ["qwen3.5:35b", "qwen3-coder", "qwen3.5:27b", "qwen3.5:9b", "qwen3:32b"]
REASON_FALLBACKS = ["qwen3.5:35b", "qwen3.5:27b", "qwen3.5:9b", "qwen3:32b"]
FAST_FALLBACKS = ["qwen3.5:9b", "qwen3.5:4b", "qwen3.5:2b", "qwen3:14b"]
DOCUMENT_FALLBACKS = ["qwen3.5:35b", "qwen3.5:27b", "qwen3.5:9b", "qwen3:32b"]


def ollama_model_exists(model_name: str, settings) -> bool:
    """Return True only if the exact model name is present in Ollama /api/tags."""
    import urllib.request
    import json as _json
    try:
        url = (getattr(settings, "OLLAMA_URL", "http://localhost:11434")
               .rstrip("/") + "/api/tags")
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = _json.loads(resp.read())
        available = [m.get("name", "") for m in data.get("models", [])]
        needle = model_name if ":" in model_name else f"{model_name}:latest"
        return needle in available
    except Exception:
        return True


def resolve_ollama_model(role: str) -> str:
    """
    Return an Ollama model name that exists for the given role.
    Uses configured setting first, then fallback list. Role: 'reason', 'code', 'fast', or 'document'.
    """
    try:
        from settings import settings
    except Exception:
        return "qwen3.5:35b"

    if role == "reason":
        configured = getattr(settings, "OLLAMA_MODEL_REASON", "") or "qwen3.5:35b"
        fallbacks = REASON_FALLBACKS
    elif role == "code":
        configured = getattr(settings, "OLLAMA_MODEL_CODE", "") or "qwen3.5:35b"
        fallbacks = CODE_FALLBACKS
    elif role == "fast":
        configured = getattr(settings, "OLLAMA_MODEL_FAST", "") or "qwen3.5:9b"
        fallbacks = FAST_FALLBACKS
    elif role == "document":
        configured = getattr(settings, "OLLAMA_MODEL_DOCUMENT", "") or "qwen3.5:35b"
        fallbacks = DOCUMENT_FALLBACKS
    else:
        return "qwen3.5:35b"

    if ollama_model_exists(configured, settings):
        return configured
    for fallback in fallbacks:
        if ollama_model_exists(fallback, settings):
            logger.info(
                "Ollama model %s not found; using %s for %s",
                configured, fallback, role,
            )
            return fallback
    return configured
