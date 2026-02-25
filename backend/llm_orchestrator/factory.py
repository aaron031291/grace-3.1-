"""
Factory for creating LLM clients based on settings.
"""

from .base_client import BaseLLMClient
from .ollama_adapter import OllamaLLMClient
from .openai_client import OpenAILLMClient
from .kimi_client import KimiLLMClient
from settings import settings


def get_llm_client(provider: str = None) -> BaseLLMClient:
    """
    Get a LLM client instance.
    If provider is specified, returns that specific provider's client.
    Otherwise uses the configured default from settings.
    """
    provider = provider or settings.LLM_PROVIDER

    if provider == "openai":
        return OpenAILLMClient(api_key=settings.LLM_API_KEY)
    elif provider == "kimi":
        return KimiLLMClient(
            api_key=getattr(settings, 'KIMI_API_KEY', '') or settings.LLM_API_KEY,
        )
    else:
        return OllamaLLMClient(base_url=settings.OLLAMA_URL)


def get_kimi_client() -> KimiLLMClient:
    """Get a Kimi 2.5 client specifically, regardless of the default provider."""
    return KimiLLMClient(
        api_key=getattr(settings, 'KIMI_API_KEY', '') or settings.LLM_API_KEY,
    )
