"""
Opus/Claude 3.5 LLM Client.

Opus has higher capability than Kimi and can:
- Audit Kimi's outputs and improve them
- Teach Grace with deeper reasoning
- Identify holes in Oracle and memory mesh/Magma
- Serve as the primary model for complex tasks
"""

import requests
import logging
from typing import List, Dict, Any, Optional, Union
from .base_client import BaseLLMClient
from settings import settings

logger = logging.getLogger(__name__)

OPUS_BASE_URL = "https://api.anthropic.com/v1"
OPUS_DEFAULT_MODEL = "claude-3-5-sonnet-latest"


class OpusLLMClient(BaseLLMClient):
    """Client for Anthropic's Claude/Opus API."""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or getattr(settings, 'OPUS_API_KEY', '') or settings.LLM_API_KEY
        self.base_url = base_url or getattr(settings, 'OPUS_BASE_URL', OPUS_BASE_URL)
        self.default_model = model or getattr(settings, 'OPUS_MODEL', OPUS_DEFAULT_MODEL)

    def generate(self, prompt: str, model_id: Optional[str] = None,
                 system_prompt: Optional[str] = None, temperature: Optional[float] = None,
                 max_tokens: Optional[int] = None, stream: bool = False, **kwargs) -> Union[str, Dict]:
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages=messages, model=model_id, stream=stream,
                         temperature=temperature, max_tokens=max_tokens,
                         system_prompt=system_prompt, **kwargs)

    def chat(self, messages: List[Dict[str, str]], model: Optional[str] = None,
             stream: bool = False, temperature: Optional[float] = None,
             max_tokens: Optional[int] = None, system_prompt: str = None, **kwargs) -> Union[str, Dict]:
        
        # Anthropic uses a different format — system is separate from messages
        system = ""
        filtered_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                system = msg.get("content", "")
            else:
                filtered_messages.append(msg)
        if system_prompt:
            system = (system + "\n\n" + system_prompt).strip() if system else system_prompt

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        payload = {
            "model": model or self.default_model,
            "messages": filtered_messages or [{"role": "user", "content": "Hello"}],
            "max_tokens": max_tokens or 4096,
            "temperature": temperature if temperature is not None else 0.7,
        }
        if system:
            payload["system"] = system

        try:
            url = f"{self.base_url}/messages"
            response = requests.post(url, headers=headers, json=payload, timeout=120)
            if response.status_code != 200:
                logger.error(f"Opus error ({response.status_code}): {response.text}")
            response.raise_for_status()

            result = response.json()
            # Anthropic returns content as a list of blocks
            content_blocks = result.get("content", [])
            text = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    text += block.get("text", "")
            return text
        except Exception as e:
            logger.error(f"Opus API failed: {e}")
            raise

    def is_running(self) -> bool:
        if not self.api_key:
            return False
        try:
            headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
            r = requests.post(f"{self.base_url}/messages", headers=headers,
                              json={"model": self.default_model, "messages": [{"role": "user", "content": "test"}], "max_tokens": 5},
                              timeout=10)
            return r.status_code in (200, 400)  # 400 means API works but request invalid
        except Exception:
            return False

    def get_all_models(self) -> List[Dict]:
        return [{"id": self.default_model, "name": "Claude 3.5 Sonnet"}]

    def model_exists(self, model_name: str) -> bool:
        return True

    def audit_kimi_output(self, kimi_output: str, original_prompt: str) -> Dict[str, Any]:
        """Opus audits Kimi's output and suggests improvements."""
        response = self.generate(
            prompt=f"Audit this AI output for accuracy, completeness, and quality:\n\n"
                   f"Original prompt: {original_prompt[:500]}\n\n"
                   f"Output to audit:\n{kimi_output[:3000]}\n\n"
                   f"Provide: 1) Accuracy score (1-10) 2) Issues found 3) Improvements 4) Missing information",
            system_prompt="You are auditing another AI's output. Be thorough and critical.",
            temperature=0.2,
        )
        return {"audit": response, "auditor": "opus"}

    def identify_knowledge_gaps(self, knowledge_summary: str) -> Dict[str, Any]:
        """Opus identifies holes in Oracle and memory mesh."""
        response = self.generate(
            prompt=f"Analyse this knowledge base summary and identify gaps:\n\n"
                   f"{knowledge_summary[:5000]}\n\n"
                   f"List: 1) Missing topics 2) Weak areas 3) Contradictions 4) Outdated information 5) Priority learning items",
            system_prompt="You are auditing an AI's knowledge base for completeness and quality.",
            temperature=0.3,
        )
        return {"gaps": response, "auditor": "opus"}
