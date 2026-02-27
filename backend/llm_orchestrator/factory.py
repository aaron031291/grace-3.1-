"""
Factory for creating LLM clients based on settings.

Every client returned is wrapped with GovernanceAwareLLM so that
uploaded governance rules (GDPR, ISO, anti-bribery, code standards,
user rules) and persona context (personal + professional) are
automatically injected into every LLM call system-wide.
"""

from .base_client import BaseLLMClient
from .ollama_adapter import OllamaLLMClient
from .openai_client import OpenAILLMClient
from .kimi_client import KimiLLMClient
from .opus_client import OpusLLMClient
from .governance_wrapper import GovernanceAwareLLM
from settings import settings


def _wrap(client: BaseLLMClient) -> BaseLLMClient:
    """Wrap a client with governance rules + persona injection."""
    return GovernanceAwareLLM(client)


def get_llm_client(provider: str = None) -> BaseLLMClient:
    """
    Get a LLM client instance with governance rules enforced.
    If provider is specified, returns that specific provider's client.
    Otherwise uses the configured default from settings.
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
    else:
        return _wrap(OllamaLLMClient(base_url=settings.OLLAMA_URL))


def get_llm_for_task(task: str = "general") -> BaseLLMClient:
    """
    Get the best model for a specific task type.
    Falls back gracefully if specialised models aren't configured.
    
    Tasks: code, reason, fast, general
    """
    model_override = None
    
    if task == "code" and settings.OLLAMA_MODEL_CODE:
        model_override = settings.OLLAMA_MODEL_CODE
    elif task == "reason" and settings.OLLAMA_MODEL_REASON:
        model_override = settings.OLLAMA_MODEL_REASON
    elif task == "fast" and settings.OLLAMA_MODEL_FAST:
        model_override = settings.OLLAMA_MODEL_FAST

    if model_override:
        client = OllamaLLMClient(base_url=settings.OLLAMA_URL)
        client._default_model = model_override
        return _wrap(client)

    return get_llm_client()


def get_kimi_client() -> KimiLLMClient:
    """Get a Kimi 2.5 client with governance rules enforced."""
    return _wrap(KimiLLMClient(
        api_key=getattr(settings, 'KIMI_API_KEY', '') or settings.LLM_API_KEY,
    ))


def get_opus_client() -> OpusLLMClient:
    """Get an Opus 4.6 client with governance rules enforced."""
    return _wrap(OpusLLMClient(
        api_key=getattr(settings, 'OPUS_API_KEY', '') or settings.LLM_API_KEY,
    ))


def get_raw_client(provider: str = None) -> BaseLLMClient:
    """Get a raw client WITHOUT governance wrapping (for internal use only)."""
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
    else:
        return OllamaLLMClient(base_url=settings.OLLAMA_URL)
