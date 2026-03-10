"""
LLM Factory — Central access point for ALL AI models.

Model hierarchy:
  LOCAL (free, fast, private):
    - Qwen 2.5 Coder (code generation — latest dedicated coder, reasoning for code)
    - Qwen 2.5 (reasoning — latest reasoning model)
    - Qwen 2.5 14B (fast — quick responses)

  CLOUD (paid, powerful, reasoning):
    - Claude 3.5 Sonnet (deep reasoning, architecture, audit)
    - Kimi K2.5 (long context, document analysis, 262K window)

Task routing:
    code     → Qwen 2.5 Coder (local)
    reason   → Qwen 2.5 (local) or Claude 3.5 (cloud)
    fast     → Qwen 2.5 14B (local)
    document → Qwen 2.5 (local, parse/read docs) or Kimi (cloud) if no OLLAMA_MODEL_DOCUMENT
    general  → default model
    audit    → Claude 3.5 (cloud)

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
    Providers: ollama, kimi, opus, openai
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
    elif provider == "runpod":
        from cognitive.runpod_client import get_runpod_client
        return _wrap(get_runpod_client())
    else:
        return _wrap(OllamaLLMClient(base_url=settings.OLLAMA_URL))


def get_llm_for_task(task: str = "general", task_description: str = "", context: dict = None) -> BaseLLMClient:
    """
    Get the best model for a specific task type.
    Routes to the optimal model based on task requirements or dynamic risk arbitration.

    Tasks:
      code         → Qwen 3.5 Coder (local)
      reason       → Qwen 3.5 (local)
      self_healing → Qwen 3.5 (local)
      fast         → Qwen 3.5 14B (local, quick responses)
      audit        → Claude 3.5 (cloud, deep analysis)
      document     → Qwen 3.5 (local) or Kimi (cloud)
      general      → default model (Chat)
    """
    # Dynamic Arbitration based on Risk
    if task_description:
        try:
            from infrastructure.resource_arbitrator import get_resource_arbitrator
            arbitrator = get_resource_arbitrator()
            model_id = arbitrator.route_task(task_description, context)
            if model_id == "opus":
                return get_opus_client()
            elif model_id == "kimi":
                return get_kimi_client()
            else:
                return _ollama_with_model(resolve_ollama_model("reason"))
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to use ResourceArbitrator: {e}")

    if task == "code" and settings.OLLAMA_MODEL_CODE:
        return _ollama_with_model(resolve_ollama_model("code"))

    elif task == "reason" and settings.OLLAMA_MODEL_REASON:
        return _ollama_with_model(resolve_ollama_model("reason"))

    elif task == "self_healing" and settings.OLLAMA_MODEL_REASON:
        return _ollama_with_model(resolve_ollama_model("reason"))

    elif task == "fast" and settings.OLLAMA_MODEL_FAST:
        return _ollama_with_model(resolve_ollama_model("fast"))

    elif task == "audit":
        return get_llm_client()

    elif task == "document":
        # Prefer local Qwen for doc parsing/reading
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
    """Get Claude 3.5 Sonnet / Opus — deep reasoning, architecture, audit."""
    return _wrap(OpusLLMClient(
        api_key=getattr(settings, 'OPUS_API_KEY', '') or settings.LLM_API_KEY,
    ))


def get_qwen_coder() -> BaseLLMClient:
    """Get Qwen 2.5 Coder — code generation (local). Uses resolved model (with fallbacks)."""
    model = resolve_ollama_model("code")
    return _ollama_with_model(model)


def get_qwen_reasoner() -> BaseLLMClient:
    """Get Qwen 2.5 — reasoning model (local). Uses resolved model (with fallbacks)."""
    model = resolve_ollama_model("reason")
    return _ollama_with_model(model)


def get_qwen_document() -> BaseLLMClient:
    """Get Qwen (local) for document parsing/reading. No GPT 4.1 or Kimi required."""
    model = resolve_ollama_model("document")
    return _ollama_with_model(model)


def get_deepseek_reasoner() -> BaseLLMClient:
    """Alias for get_qwen_reasoner(). Qwen 2.5 is the default reasoning model."""
    return get_qwen_reasoner()


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
    elif provider == "runpod":
        from cognitive.runpod_client import get_runpod_client
        return get_runpod_client()
    else:
        return OllamaLLMClient(base_url=settings.OLLAMA_URL)


def get_all_available_models() -> list:
    """List all available models across all providers."""
    models = []

    # Local models
    for task, model_attr, desc in [
        ("code", "OLLAMA_MODEL_CODE", "Code generation (Qwen 2.5 Coder)"),
        ("reason", "OLLAMA_MODEL_REASON", "Reasoning (Qwen 2.5)"),
        ("fast", "OLLAMA_MODEL_FAST", "Fast tasks (Qwen 2.5 14B)"),
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
        "description": "Claude 3.5 Sonnet — deep reasoning, architecture, audit",
        "available": bool(settings.OPUS_API_KEY),
        "cost": "cloud",
        "location": "cloud",
    })

    return models
