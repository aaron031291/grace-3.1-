import os
import logging
from typing import Optional, Dict, Any, List
import requests

logger = logging.getLogger(__name__)

from llm_orchestrator.base_client import BaseLLMClient

class RunPodvLLMClient(BaseLLMClient):
    """
    OpenAI-compatible client for communicating with RunPod Serverless vLLM endpoints.
    """
    def __init__(self, api_key: Optional[str] = None, endpoint_id: Optional[str] = None):
        # Prefer provided args, fallback to environment
        self.api_key = api_key or os.environ.get("RUNPOD_API_KEY")
        self.endpoint_id = endpoint_id or os.environ.get("RUNPOD_ENDPOINT_ID")
        
        if not self.api_key or not self.endpoint_id:
            logger.warning("[RunPod] RUNPOD_API_KEY or RUNPOD_ENDPOINT_ID is not set. RunPod client may fail.")
            
        # Standard RunPod vLLM OpenAI-compatible endpoint URL
        self.base_url = f"https://api.runpod.ai/v2/{self.endpoint_id}/openai/v1"

    def generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> str:
        """
        Generates a text response using the completions endpoint.
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return self.chat(
            messages=messages,
            model=model_id,
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
    ) -> str:
        """
        Chat interaction matching the OpenAI-compatible vLLM endpoint.
        """
        if not self.api_key or not self.endpoint_id:
            raise ValueError("RunPod API Key and Endpoint ID must be configured.")

        # Default model from environment or fallback
        model = model or os.environ.get("RUNPOD_MODEL") or "Mistral-7B-Instruct"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature or 0.5,
            "max_tokens": max_tokens or 4096,
            "stream": stream
        }
        payload.update(kwargs)

        try:
            logger.info(f"[RunPod] Sending chat request to {self.base_url}/chat/completions")
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"[RunPod] Unexpected response structure: {data}")
                return "Error: Unexpected response from RunPod."
                
        except requests.exceptions.RequestException as e:
            logger.error(f"[RunPod] API request failed: {e}")
            raise

    def is_running(self) -> bool:
        """
        Check if the RunPod endpoint is reachable by calling the models endpoint.
        """
        if not self.api_key or not self.endpoint_id:
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.base_url}/models", headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

    def get_all_models(self) -> List[Dict[str, Any]]:
        """
        List available models from the RunPod vLLM endpoint.
        """
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.get(f"{self.base_url}/models", headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [])
            return []
        except Exception as e:
            logger.error(f"[RunPod] Failed to list models: {e}")
            return []

    def model_exists(self, model_name: str) -> bool:
        """
        Check if the specific model ID exists on the endpoint.
        """
        models = self.get_all_models()
        return any(m.get("id") == model_name for m in models)

def get_runpod_client() -> RunPodvLLMClient:
    return RunPodvLLMClient()
