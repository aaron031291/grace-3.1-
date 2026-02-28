"""
Kimi 2.5 (Moonshot AI) LLM Client implementation.

Uses the OpenAI-compatible API at https://api.moonshot.cn/v1
Kimi 2.5 supports long-context reasoning and is well-suited for
document analysis and system-level reasoning tasks.
"""

import requests
import logging
from typing import List, Dict, Any, Optional, Union
from .base_client import BaseLLMClient
from settings import settings

logger = logging.getLogger(__name__)

KIMI_BASE_URL = "https://api.moonshot.ai/v1"
KIMI_DEFAULT_MODEL = "kimi-k2.5"


class KimiLLMClient(BaseLLMClient):
    """
    Client for Moonshot AI's Kimi 2.5 API.
    OpenAI-compatible interface with extended context and reasoning.
    """

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or getattr(settings, 'KIMI_API_KEY', '') or settings.LLM_API_KEY
        self.base_url = base_url or getattr(settings, 'KIMI_BASE_URL', KIMI_BASE_URL)
        self.default_model = model or getattr(settings, 'KIMI_MODEL', KIMI_DEFAULT_MODEL)
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

        model_name = model or self.default_model

        # Kimi K2.5 reasoning models only support temperature=1
        if "k2" in model_name or "thinking" in model_name:
            temp = 1.0
        else:
            temp = temperature if temperature is not None else 0.7

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": temp,
            "stream": stream
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        try:
            logger.info(f"Kimi request to {url} with model {payload['model']}")
            response = requests.post(
                url, headers=self.headers, json=payload, timeout=120
            )
            if response.status_code != 200:
                logger.error(f"Kimi error ({response.status_code}): {response.text}")
            response.raise_for_status()

            if stream:
                return response

            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Kimi API request failed: {e}")
            raise

    def is_running(self) -> bool:
        if not self.api_key:
            return False
        try:
            self.get_all_models()
            return True
        except Exception:
            return False

    def get_all_models(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/models"
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.json().get('data', [])
        except Exception as e:
            logger.error(f"Error fetching Kimi models: {e}")
            return []

    def model_exists(self, model_name: str) -> bool:
        models = self.get_all_models()
        return any(m.get('id') == model_name for m in models)

    def reason_about_document(
        self,
        document_content: str,
        instruction: str,
        context: Optional[str] = None
    ) -> str:
        """
        Use Kimi's long-context capability to reason about a document.
        Ideal for librarian document classification and organization.
        """
        system = (
            "You are Grace's Librarian intelligence. You analyze documents to determine "
            "their category, topic, relationships, and optimal organization within a "
            "knowledge base directory structure. Be precise and structured in your analysis."
        )
        if context:
            system += f"\n\nCurrent knowledge base context:\n{context}"

        user_message = f"{instruction}\n\n---\nDocument content:\n{document_content}"

        return self.generate(
            prompt=user_message,
            system_prompt=system,
            temperature=0.3,
            max_tokens=2048
        )

    def system_analysis(
        self,
        system_state: Dict[str, Any],
        query: str
    ) -> str:
        """
        Analyze the entire system state and provide bird's eye perspective.
        Used by the Chat tab's world model view.
        """
        system = (
            "You are Grace, an autonomous AI system. You have full awareness of your "
            "own architecture, subsystems, and current state. When asked about your "
            "system, provide insightful analysis from a bird's eye perspective. "
            "Reference specific subsystems, their health, and how they interact."
        )

        state_summary = _format_system_state(system_state)
        user_message = f"Current system state:\n{state_summary}\n\nQuery: {query}"

        return self.generate(
            prompt=user_message,
            system_prompt=system,
            temperature=0.5,
            max_tokens=4096
        )


def _format_system_state(state: Dict[str, Any]) -> str:
    """Format system state dict into a readable summary for the LLM."""
    lines = []
    for section, data in state.items():
        lines.append(f"\n## {section}")
        if isinstance(data, dict):
            for k, v in data.items():
                lines.append(f"  - {k}: {v}")
        elif isinstance(data, list):
            for item in data[:20]:
                lines.append(f"  - {item}")
        else:
            lines.append(f"  {data}")
    return "\n".join(lines)
