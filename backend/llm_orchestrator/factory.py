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
        return _wrap(QwenLLMClient(
            api_key=getattr(settings, 'QWEN_API_KEY', ''),
        ))
    else:
        return _wrap(OllamaLLMClient(base_url=settings.OLLAMA_URL))


def get_llm_for_task(task: str = "general") -> BaseLLMClient:
    """
    Get the best model for a specific task type.
    Routes to the optimal model based on task requirements.

    Tasks:
      code     → Qwen 2.5 Coder (local, specialised for code)
      reason   → DeepSeek R1 (local, specialised for reasoning)
      fast     → Qwen 2.5 (local, quick responses)
      audit    → Opus (cloud, deep analysis)
      document → Kimi (cloud, 262K context)
      general  → default model
    """
    if task == "code" and settings.OLLAMA_MODEL_CODE:
        return _ollama_with_model(settings.OLLAMA_MODEL_CODE)

    elif task == "reason" and settings.OLLAMA_MODEL_REASON:
        return _ollama_with_model(settings.OLLAMA_MODEL_REASON)

    elif task == "fast" and settings.OLLAMA_MODEL_FAST:
        return _ollama_with_model(settings.OLLAMA_MODEL_FAST)

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
    """Get Qwen 3 — cloud (DashScope) or local (Ollama) depending on config."""
    return _wrap(QwenLLMClient(
        api_key=getattr(settings, 'QWEN_API_KEY', ''),
    ))


def get_qwen_coder() -> BaseLLMClient:
    """Get Qwen Coder — code generation. Cloud if QWEN_API_KEY set, else Ollama."""
    if getattr(settings, 'QWEN_API_KEY', ''):
        code_model = getattr(settings, 'QWEN_CODE_MODEL', '') or 'qwen3-coder'
        return _wrap(QwenLLMClient(
            api_key=settings.QWEN_API_KEY,
            model=code_model,
        ))
    model = settings.OLLAMA_MODEL_CODE or "qwen2.5-coder:7b"
    return _ollama_with_model(model)


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
        return QwenLLMClient(
            api_key=getattr(settings, 'QWEN_API_KEY', ''),
        )
    else:
        return OllamaLLMClient(base_url=settings.OLLAMA_URL)


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
    models.append({
        "id": "qwen",
        "provider": "qwen",
        "model": getattr(settings, 'QWEN_MODEL', 'qwen-plus'),
        "description": "Qwen 3 — 256K context, multilingual, code, reasoning (cloud or local)",
        "available": bool(getattr(settings, 'QWEN_API_KEY', '')) or bool(getattr(settings, 'OLLAMA_MODEL_FAST', '')),
        "cost": "cloud" if getattr(settings, 'QWEN_API_KEY', '') else "free",
        "location": "cloud" if getattr(settings, 'QWEN_API_KEY', '') else "local",
        "strengths": ["code generation", "reasoning", "multilingual", "256K context", "tool calling"],
    })

    return models
