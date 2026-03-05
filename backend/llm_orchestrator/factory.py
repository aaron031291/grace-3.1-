"""
LLM Factory — Central access point for ALL AI models.

Model hierarchy:
  LOCAL (free, fast, private):
    - Qwen 2.5 Coder (code generation — best open-source coder)
    - DeepSeek R1 (reasoning — best open-source reasoning)
    - Qwen 2.5 (general — fast default)

  CLOUD (paid, powerful, reasoning):
    - Opus 4.6 / Claude (deep reasoning, architecture, audit)
    - Kimi K2.5 (long context, document analysis, 262K window)

Task routing:
    code    → Qwen 2.5 Coder (local)
    reason  → DeepSeek R1 (local) or Opus (cloud)
    fast    → Qwen 2.5 (local)
    general → default model
    audit   → Opus (cloud)
    document→ Kimi (cloud, 262K context)

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
from .qwen_client import QwenLLMClient
from .qwen_pool import get_qwen_pool, QwenModelPool
from .governance_wrapper import GovernanceAwareLLM
from settings import settings


def _wrap(client: BaseLLMClient) -> BaseLLMClient:
    """Wrap a client with governance rules + persona + hallucination guard."""
    return GovernanceAwareLLM(client)


def _ollama_with_model(model: str) -> BaseLLMClient:
    """Create an Ollama client with a specific model override."""
    client = OllamaLLMClient(base_url=settings.OLLAMA_URL)
    client._default_model = model
    return _wrap(client)


def get_llm_client(provider: str = None) -> BaseLLMClient:
    """
    Get a LLM client with governance rules enforced.
    Providers: ollama, kimi, opus, openai, qwen
    """
    provider = provider or settings.LLM_PROVIDER

    if provider == "openai":
        return _wrap(OpenAILLMClient(api_key=settings.LLM_API_KEY))
    elif provider == "kimi":
        return _wrap(KimiLLMClient(
            api_key=getattr(settings, 'KIMI_API_KEY', '') or settings.LLM_API_KEY,
        ))
    elif provider == "opus":
        return _wrap(OpusLLMClient(
            api_key=getattr(settings, 'OPUS_API_KEY', '') or settings.LLM_API_KEY,
        ))
    elif provider == "qwen":
        pool = get_qwen_pool()
        return pool.get_client_for_task("general")
    else:
        return _wrap(OllamaLLMClient(base_url=settings.OLLAMA_URL))


def get_llm_for_task(task: str = "general") -> BaseLLMClient:
    """
    Get the best model for a specific task type.
    Routes through the Qwen pool for code/reason/fast tasks.

    Tasks:
      code     → Qwen pool (32b)
      reason   → Qwen pool (30b MoE)
      fast     → Qwen pool (14b)
      audit    → Opus (cloud, deep analysis)
      document → Kimi (cloud, 262K context)
      general  → Qwen pool (default)
    """
    if task in ("code", "reason", "fast", "general"):
        pool = get_qwen_pool()
        return pool.get_client_for_task(task)

    elif task == "audit":
        if getattr(settings, 'OPUS_API_KEY', ''):
            return get_opus_client()
        return get_llm_client()

    elif task == "document":
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


def get_qwen_client() -> BaseLLMClient:
    """Get Qwen 3 via the pool — auto-routes to the best model for general tasks."""
    pool = get_qwen_pool()
    return pool.get_client_for_task("general")


def get_qwen_coder() -> BaseLLMClient:
    """Get Qwen Coder via the pool — routes to the code-optimized model."""
    pool = get_qwen_pool()
    return pool.get_client_for_task("code")


def get_deepseek_reasoner() -> BaseLLMClient:
    """Get DeepSeek R1 — best open-source reasoning model."""
    model = settings.OLLAMA_MODEL_REASON or "deepseek-r1:7b"
    return _ollama_with_model(model)


def get_raw_client(provider: str = None) -> BaseLLMClient:
    """Get a raw client WITHOUT governance wrapping (internal use only)."""
    provider = provider or settings.LLM_PROVIDER
    if provider == "openai":
        return OpenAILLMClient(api_key=settings.LLM_API_KEY)
    elif provider == "kimi":
        return KimiLLMClient(
            api_key=getattr(settings, 'KIMI_API_KEY', '') or settings.LLM_API_KEY,
        )
    elif provider == "opus":
        return OpusLLMClient(
            api_key=getattr(settings, 'OPUS_API_KEY', '') or settings.LLM_API_KEY,
        )
    elif provider == "qwen":
        return QwenLLMClient(api_key=getattr(settings, 'QWEN_API_KEY', ''))
    else:
        return OllamaLLMClient(base_url=settings.OLLAMA_URL)


def get_ai_mode_client(task: str = "code") -> BaseLLMClient:
    """
    Get a LLM client in AI-to-AI mode.
    Skips NLP governance prefix (persona, rules prose).
    Uses structured constraints instead of natural language rules.
    For internal component-to-component calls only.
    """
    client = get_llm_for_task(task)
    if hasattr(client, 'ai_mode'):
        client.ai_mode = True
    return client


def get_all_available_models() -> list:
    """List all available models across all providers."""
    models = []

    # Local models
    for task, model_attr, desc in [
        ("code", "OLLAMA_MODEL_CODE", "Code generation (Qwen 2.5 Coder)"),
        ("reason", "OLLAMA_MODEL_REASON", "Reasoning (DeepSeek R1)"),
        ("fast", "OLLAMA_MODEL_FAST", "Fast tasks (Qwen 2.5)"),
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
    try:
        pool = get_qwen_pool()
        pool_status = pool.get_status()
        for key, info in pool_status.get("models", {}).items():
            models.append({
                "id": f"qwen-{key}",
                "provider": "qwen",
                "model": info["model_name"],
                "description": f"Qwen 3 {key} — {', '.join(info['tasks'])}",
                "available": info["healthy"],
                "cost": "free",
                "location": "local",
                "strengths": info["tasks"],
                "pool_stats": {
                    "calls": info["total_calls"],
                    "avg_latency": info["avg_latency_ms"],
                },
            })
    except Exception:
        models.append({
            "id": "qwen",
            "provider": "qwen",
            "model": getattr(settings, 'QWEN_MODEL', 'qwen3:32b'),
            "description": "Qwen 3 (pool not initialized)",
            "available": True,
            "cost": "free",
            "location": "local",
        })

    return models
