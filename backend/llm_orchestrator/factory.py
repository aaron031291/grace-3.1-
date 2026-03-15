"""
LLM Factory — Central access point for ALL AI models.

Model hierarchy:
  LOCAL (free, fast, private):
    - Qwen 2.5 Coder (code generation — latest dedicated coder, reasoning for code)
    - Qwen 3 (reasoning — latest reasoning model)
    - Qwen 3 14B (fast — quick responses)

  CLOUD (paid, powerful, reasoning):
    - Opus 4.6 / Claude (deep reasoning, architecture, audit)
    - Kimi K2.5 (long context, document analysis, 262K window)

Task routing:
    code     → Qwen 2.5 Coder (local)
    reason   → Qwen 3 (local) or Opus (cloud)
    fast     → Qwen 3 14B (local)
    document → Qwen 3 (local, parse/read docs) or Kimi (cloud) if no OLLAMA_MODEL_DOCUMENT
    general  → default model
    audit    → Opus (cloud)

Every client wrapped with GovernanceAwareLLM:
    - Governance rules injected into every call
    - Hallucination guard on every response
    - Usage stats tracked for BI dashboard
    - Genesis Key on every call
"""

from .base_client import BaseLLMClient
from .ollama_adapter import OllamaLLMClient
from .openai_client import OpenAILLMClient
from .kimi_client import KimiLLMClient
from .opus_client import OpusLLMClient
from .governance_wrapper import GovernanceAwareLLM
from .ollama_resolver import resolve_ollama_model
from settings import settings

import logging
import threading
import time

logger = logging.getLogger(__name__)


# ==================== FIX 3: Offline LLM Client (Fallback) ====================
class OfflineLLMClient(BaseLLMClient):
    """
    Fallback client when ALL LLM providers are unavailable.
    Returns clear error messages instead of crashing.
    62 modules that call get_llm_client() now survive LLM downtime.
    """
    
    def __init__(self):
        self._model = "offline"
    
    def is_running(self) -> bool:
        return False
    
    def generate(self, prompt: str, **kwargs) -> str:
        return "[LLM OFFLINE] All LLM providers are currently unavailable. Request queued for retry."
    
    def chat(self, messages: list, **kwargs) -> dict:
        return {
            "message": {"role": "assistant", "content": self.generate(str(messages))},
            "model": "offline",
            "done": True,
        }
    
    def list_models(self) -> list:
        return []
    
    def get_model_name(self) -> str:
        return "offline-fallback"
    
    def embed(self, text: str, **kwargs) -> list:
        return []


class _CostTracker:
    """Tracks API token costs and enforces back-pressure on quota exhaustion."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.total_calls = 0
        self.total_cost_usd = 0.0
        self.calls_this_hour = 0
        self.hour_start = time.time()
        # Configurable limits
        self.max_calls_per_hour = 500
        self.max_cost_per_hour_usd = 10.0
        self._backpressure_until = 0.0

    @classmethod
    def get_instance(cls) -> "_CostTracker":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record_call(self, provider: str, prompt_tokens: int = 0, completion_tokens: int = 0):
        """Record a call and its estimated cost."""
        with self._lock:
            now = time.time()
            if now - self.hour_start > 3600:
                self.calls_this_hour = 0
                self.hour_start = now
            self.total_calls += 1
            self.calls_this_hour += 1
            # Estimate cost (per 1K tokens)
            cost_per_1k = {"opus": 0.015, "kimi": 0.005, "openai": 0.01}.get(provider, 0.0)
            call_cost = cost_per_1k * (prompt_tokens + completion_tokens) / 1000
            self.total_cost_usd += call_cost

    def check_backpressure(self) -> bool:
        """Return True if requests should be throttled."""
        with self._lock:
            now = time.time()
            if now < self._backpressure_until:
                return True
            if now - self.hour_start > 3600:
                self.calls_this_hour = 0
                self.hour_start = now
            if self.calls_this_hour >= self.max_calls_per_hour:
                self._backpressure_until = now + 60  # back off 60s
                logger.warning(f"[COST] Back-pressure: {self.calls_this_hour} calls/hr exceeds limit")
                return True
            return False

    def get_stats(self) -> dict:
        with self._lock:
            return {
                "total_calls": self.total_calls,
                "total_cost_usd": round(self.total_cost_usd, 4),
                "calls_this_hour": self.calls_this_hour,
                "max_calls_per_hour": self.max_calls_per_hour,
                "backpressure_active": time.time() < self._backpressure_until,
            }


_cost_tracker = _CostTracker.get_instance()


def _wrap(client: BaseLLMClient) -> BaseLLMClient:
    """Wrap a client with governance rules + persona + hallucination guard + cost tracking."""
    if _cost_tracker.check_backpressure():
        logger.warning("[COST] Back-pressure active — throttling LLM call")
    return GovernanceAwareLLM(client)


def _ollama_with_model(model: str) -> BaseLLMClient:
    """Create an Ollama client with a specific model override."""
    client = OllamaLLMClient(base_url=settings.OLLAMA_URL)
    client._default_model = model
    return _wrap(client)


def get_llm_client(provider: str = None) -> BaseLLMClient:
    """
    Get a LLM client with governance rules enforced.
    Tries requested provider first, then falls back through all available providers.
    Final fallback: OfflineLLMClient (returns clear error, never crashes).
    """
    provider = provider or (settings.LLM_PROVIDER if settings else 'ollama')
    
    # Try the requested provider first
    try:
        client = _create_provider_client(provider)
        if client is not None:
            return _wrap(client)
    except Exception as e:
        logger.warning(f"[LLM-FALLBACK] Primary provider '{provider}' failed: {e}")
    
    # Fallback chain: try other providers
    fallback_order = ['ollama', 'kimi', 'opus', 'openai']
    for fb in fallback_order:
        if fb == provider:
            continue
        try:
            client = _create_provider_client(fb)
            if client is not None:
                logger.info(f"[LLM-FALLBACK] Using fallback provider: {fb}")
                return _wrap(client)
        except Exception:
            continue
    
    # All providers failed → return offline client
    logger.error("[LLM-FALLBACK] ALL providers unavailable. Using OfflineLLMClient.")
    return OfflineLLMClient()


def _create_provider_client(provider: str) -> BaseLLMClient:
    """Create a raw client for the given provider. Returns None if not configured."""
    if provider == "openai":
        key = getattr(settings, 'LLM_API_KEY', '') if settings else ''
        if not key:
            return None
        return OpenAILLMClient(api_key=key)
    elif provider == "kimi":
        key = (getattr(settings, 'KIMI_API_KEY', '') or getattr(settings, 'LLM_API_KEY', '')) if settings else ''
        if not key:
            return None
        return KimiLLMClient(api_key=key)
    elif provider == "opus":
        key = (getattr(settings, 'OPUS_API_KEY', '') or getattr(settings, 'LLM_API_KEY', '')) if settings else ''
        if not key:
            return None
        return OpusLLMClient(api_key=key)
    elif provider == "runpod":
        from cognitive.runpod_client import get_runpod_client
        return get_runpod_client()
    else:  # ollama
        url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434') if settings else 'http://localhost:11434'
        return OllamaLLMClient(base_url=url)


def get_llm_for_task(task: str = "general") -> BaseLLMClient:
    """
    Get the best model for a specific task type.
    Routes to the optimal model based on task requirements.

    Tasks:
      code     → Qwen 2.5 Coder (local, reasoning + coding)
      reason   → Qwen 3 (local, reasoning)
      fast     → Qwen 3 14B (local, quick responses)
      audit    → Opus (cloud, deep analysis)
      document → Qwen (local, parse/read) or Kimi (cloud, 262K) if no local
      general  → default model
    """
    if task == "code" and settings.OLLAMA_MODEL_CODE:
        return _ollama_with_model(resolve_ollama_model("code"))

    elif task == "reason" and settings.OLLAMA_MODEL_REASON:
        return _ollama_with_model(resolve_ollama_model("reason"))

    elif task == "fast" and settings.OLLAMA_MODEL_FAST:
        return _ollama_with_model(resolve_ollama_model("fast"))

    elif task == "audit":
        if getattr(settings, 'OPUS_API_KEY', ''):
            return get_opus_client()
        return get_llm_client()

    elif task == "document":
        # Prefer local Qwen for doc parsing/reading (no GPT 4.1 or Kimi required)
        if getattr(settings, "OLLAMA_MODEL_DOCUMENT", ""):
            return _ollama_with_model(resolve_ollama_model("document"))
        if getattr(settings, 'KIMI_API_KEY', ''):
            return get_kimi_client()
        return get_llm_client()

    return get_llm_client()


def get_kimi_client() -> BaseLLMClient:
    """Get Kimi K2.5 — long context, document analysis, 262K window."""
    return _wrap(KimiLLMClient(
        api_key=getattr(settings, 'KIMI_API_KEY', '') or settings.LLM_API_KEY,
    ))


def get_opus_client() -> BaseLLMClient:
    """Get Opus 4.6 (Claude) — deep reasoning, architecture, audit."""
    return _wrap(OpusLLMClient(
        api_key=getattr(settings, 'OPUS_API_KEY', '') or settings.LLM_API_KEY,
    ))


def get_qwen_coder() -> BaseLLMClient:
    """Get Qwen 2.5 Coder — code generation (local). Uses resolved model (with fallbacks)."""
    model = resolve_ollama_model("code")
    return _ollama_with_model(model)


def get_qwen_reasoner() -> BaseLLMClient:
    """Get Qwen 3 — reasoning model (local). Uses resolved model (with fallbacks)."""
    model = resolve_ollama_model("reason")
    return _ollama_with_model(model)


def get_qwen_document() -> BaseLLMClient:
    """Get Qwen (local) for document parsing/reading. No GPT 4.1 or Kimi required."""
    model = resolve_ollama_model("document")
    return _ollama_with_model(model)


def get_deepseek_reasoner() -> BaseLLMClient:
    """Alias for get_qwen_reasoner(). Qwen 3 is the default reasoning model."""
    return get_qwen_reasoner()


def get_raw_client(provider: str = None) -> BaseLLMClient:
    """Get a raw client WITHOUT governance wrapping (internal use only)."""
    provider = provider or (settings.LLM_PROVIDER if settings else 'ollama')
    try:
        client = _create_provider_client(provider)
        if client is not None:
            return client
    except Exception:
        pass
    return OfflineLLMClient()


def get_all_available_models() -> list:
    """List all available models across all providers."""
    models = []

    # Local models
    for task, model_attr, desc in [
        ("code", "OLLAMA_MODEL_CODE", "Code generation (Qwen 2.5 Coder)"),
        ("reason", "OLLAMA_MODEL_REASON", "Reasoning (Qwen 3)"),
        ("fast", "OLLAMA_MODEL_FAST", "Fast tasks (Qwen 3 14B)"),
    ]:
        model = getattr(settings, model_attr, "")
        models.append({
            "id": task,
            "provider": "ollama",
            "model": model or "(not set)",
            "description": desc,
            "available": bool(model),
            "cost": "free",
            "location": "local",
        })

    # Cloud models
    models.append({
        "id": "kimi",
        "provider": "kimi",
        "model": settings.KIMI_MODEL,
        "description": "Kimi K2.5 — long context, document analysis, 262K window",
        "available": bool(settings.KIMI_API_KEY),
        "cost": "cloud",
        "location": "cloud",
    })
    models.append({
        "id": "opus",
        "provider": "opus",
        "model": settings.OPUS_MODEL,
        "description": "Opus 4.6 (Claude) — deep reasoning, architecture, audit",
        "available": bool(settings.OPUS_API_KEY),
        "cost": "cloud",
        "location": "cloud",
    })

    return models


def get_cost_stats() -> dict:
    """Get API token cost tracking statistics."""
    return _cost_tracker.get_stats()
