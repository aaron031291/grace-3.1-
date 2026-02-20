"""
Factory for creating LLM clients based on settings.
"""

from .base_client import BaseLLMClient
from .ollama_adapter import OllamaLLMClient
from .openai_client import OpenAILLMClient
from settings import settings

def get_llm_client() -> BaseLLMClient:
    """
    Get the configured LLM client instance.
    """
    provider = settings.LLM_PROVIDER
    
    if provider == "openai":
        return OpenAILLMClient(
            api_key=settings.LLM_API_KEY,
            # base_url can be added here if needed
        )
    else:
        # Default to Ollama
        return OllamaLLMClient(base_url=settings.OLLAMA_URL)
