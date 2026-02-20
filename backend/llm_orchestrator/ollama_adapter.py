"""
Ollama LLM Client Adapter.
"""

from typing import List, Dict, Any, Optional, Union
from .base_client import BaseLLMClient
from ollama_client.client import OllamaClient
from settings import settings

class OllamaLLMClient(BaseLLMClient):
    """
    Adapter for OllamaClient to implement BaseLLMClient interface.
    """
    
    def __init__(self, base_url: str = None):
        self.client = OllamaClient(base_url or settings.OLLAMA_URL)

    def generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        # Map parameters to Ollama format
        options = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        
        # Merge other options from kwargs
        options.update(kwargs.get("options", {}))
        
        return self.client.generate(
            model=model_id or settings.LLM_MODEL or "mistral:7b",
            prompt=prompt,
            system=system_prompt,
            stream=stream,
            options=options
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        # Map parameters for OllamaClient.chat
        chat_kwargs = {
            "model": model or settings.LLM_MODEL or "mistral:7b",
            "messages": messages,
            "stream": stream,
        }
        
        if temperature is not None:
            chat_kwargs["temperature"] = temperature
        if max_tokens is not None:
            chat_kwargs["num_predict"] = max_tokens
            
        # Add other supported parameters from kwargs if they exist in OllamaClient.chat
        # OllamaClient.chat doesn't take **kwargs, so we only pass known ones
        if "top_p" in kwargs:
            chat_kwargs["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            chat_kwargs["top_k"] = kwargs["top_k"]

        return self.client.chat(**chat_kwargs)

    def is_running(self) -> bool:
        return self.client.is_running()

    def get_all_models(self) -> List[Dict[str, Any]]:
        models = self.client.get_all_models()
        return [
            {
                "name": m.name,
                "id": m.name,
                "status": m.status.value,
                "size": m.size
            }
            for m in models
        ]

    def model_exists(self, model_name: str) -> bool:
        return self.client.model_exists(model_name)
