"""
OpenAI LLM Client implementation.
"""

import requests
import logging
from typing import List, Dict, Any, Optional, Union
from .base_client import BaseLLMClient
from settings import settings

logger = logging.getLogger(__name__)

class OpenAILLMClient(BaseLLMClient):
    """
    Client for interacting with OpenAI API.
    """
    
    def __init__(self, api_key: str = None, base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key or settings.LLM_API_KEY
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

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
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        return self.chat(
            messages=messages,
            model=model_id,
            stream=stream,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
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
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": model or settings.LLM_MODEL or "gpt-4o",
            "messages": messages,
            "temperature": temperature if temperature is not None else 0.7,
            "stream": stream
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
            
        # Add any extra kwargs that OpenAI supports
        payload.update(kwargs)

        try:
            logger.info(f"Making OpenAI request to: {url} with model: {payload.get('model')}")
            response = requests.post(url, headers=self.headers, json=payload, timeout=60)
            if response.status_code != 200:
                logger.error(f"OpenAI error response ({response.status_code}): {response.text}")
            response.raise_for_status()
            
            if stream:
                return response # Return raw response for streaming handle
            
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"OpenAI API request failed: {e}")
            raise

    def is_running(self) -> bool:
        """
        For online providers, we just check if the API key is present and we can reach the API.
        """
        if not self.api_key:
            return False
        try:
            # Simple list models call to verify connectivity
            self.get_all_models()
            return True
        except Exception:
            return False

    def get_all_models(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/models"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json()['data']
        except Exception as e:
            logger.error(f"Error fetching OpenAI models: {e}")
            return []

    def model_exists(self, model_name: str) -> bool:
        models = self.get_all_models()
        return any(m['id'] == model_name for m in models)
