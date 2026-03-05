"""
Qwen 3.5 LLM Client — open-source model running locally via Ollama.

Default mode: LOCAL via Ollama (no API key, no cloud, fully private).
  ollama pull qwen3.5:9b       — 9B model (fast, efficient)
  ollama pull qwen3.5:27b      — 27B dense model (recommended default)
  ollama pull qwen3.5:122b-a10b — 122B MoE, 10B active (high quality, 262K context)
  ollama pull qwen3.5:397b-a17b — 397B flagship MoE

Qwen 3.5 features: 201 languages, hybrid Gated DeltaNet architecture,
native 262K context window, unified multimodal (text, images, video).

Optional cloud mode: set QWEN_API_KEY for DashScope API if needed.
"""

import requests
import logging
from typing import List, Dict, Any, Optional, Union
from .base_client import BaseLLMClient
from settings import settings

logger = logging.getLogger(__name__)

QWEN_DEFAULT_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
QWEN_DEFAULT_MODEL = "qwen3.5:27b"


class QwenLLMClient(BaseLLMClient):
    """
    Client for Qwen 3.5 open-source model running locally via Ollama.

    Default: Ollama local mode (free, private, no API key).
    Optional: DashScope cloud mode when QWEN_API_KEY is set.
    """

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or getattr(settings, "QWEN_API_KEY", "")
        self.base_url = (
            base_url
            or getattr(settings, "QWEN_BASE_URL", "")
            or QWEN_DEFAULT_BASE_URL
        )
        self.default_model = (
            model
            or getattr(settings, "QWEN_MODEL", "")
            or QWEN_DEFAULT_MODEL
        )
        self._use_cloud = bool(self.api_key)
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        mode = "cloud (DashScope)" if self._use_cloud else "local (Ollama)"
        logger.info(f"[QWEN] Initialized in {mode} mode, model={self.default_model}")

    def generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
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
            **kwargs,
        )

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Union[str, Dict[str, Any]]:
        if self._use_cloud:
            return self._chat_cloud(messages, model, stream, temperature, max_tokens, **kwargs)
        else:
            return self._chat_ollama(messages, model, stream, temperature, max_tokens, **kwargs)

    def _chat_cloud(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        model_name = model or self.default_model

        payload = {
            "model": model_name,
            "messages": messages,
            "stream": stream,
        }

        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        enable_thinking = kwargs.pop("enable_thinking", None)
        if enable_thinking is not None:
            payload["extra_body"] = {"enable_thinking": enable_thinking}

        payload.update(kwargs)

        try:
            logger.info(f"[QWEN] Cloud request to {url} model={model_name}")
            response = requests.post(
                url, headers=self.headers, json=payload, timeout=180
            )
            if response.status_code != 200:
                logger.error(f"[QWEN] Error ({response.status_code}): {response.text[:500]}")
            response.raise_for_status()

            if stream:
                return response

            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"[QWEN] Cloud API failed: {e}")
            raise

    def _chat_ollama(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        ollama_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
        model_name = model or getattr(settings, "QWEN_MODEL", "") or getattr(settings, "OLLAMA_MODEL_FAST", "") or "qwen3.5:27b"

        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False,
        }
        options = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options

        try:
            logger.info(f"[QWEN] Ollama fallback model={model_name}")
            response = requests.post(
                f"{ollama_url}/api/chat",
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()
            return result.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"[QWEN] Ollama fallback failed: {e}")
            raise

    def is_running(self) -> bool:
        if self._use_cloud:
            try:
                url = f"{self.base_url.rstrip('/')}/models"
                response = requests.get(url, headers=self.headers, timeout=10)
                return response.status_code == 200
            except Exception:
                return False
        else:
            try:
                ollama_url = getattr(settings, "OLLAMA_URL", "http://localhost:11434")
                r = requests.get(f"{ollama_url}/api/tags", timeout=3)
                return r.status_code == 200
            except Exception:
                return False

    def get_all_models(self) -> List[Dict[str, Any]]:
        if self._use_cloud:
            try:
                url = f"{self.base_url.rstrip('/')}/models"
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                return response.json().get("data", [])
            except Exception as e:
                logger.error(f"[QWEN] Error fetching models: {e}")
                return [{"id": self.default_model, "name": f"Qwen ({self.default_model})"}]
        else:
            return [{"id": "qwen-local", "name": "Qwen via Ollama (local)"}]

    def model_exists(self, model_name: str) -> bool:
        models = self.get_all_models()
        return any(
            m.get("id") == model_name or model_name in m.get("id", "")
            for m in models
        )

    def code_generate(self, prompt: str, language: str = "python", context: str = "") -> str:
        """Code generation using Qwen's coding capabilities."""
        system = (
            f"You are an expert {language} programmer. Generate clean, well-structured, "
            f"production-quality code. Include type hints and handle edge cases. "
            f"Only output the code, no explanations unless asked."
        )
        full_prompt = prompt
        if context:
            full_prompt = f"Existing code context:\n```\n{context}\n```\n\n{prompt}"

        if self._use_cloud:
            code_model = getattr(settings, "QWEN_CODE_MODEL", "") or "qwen-coder-plus"
        else:
            code_model = getattr(settings, "QWEN_CODE_MODEL", "") or getattr(settings, "OLLAMA_MODEL_CODE", "") or "qwen3.5:27b"

        return self.generate(
            prompt=full_prompt,
            model_id=code_model,
            system_prompt=system,
            temperature=0.2,
            max_tokens=4096,
        )

    def reason(self, problem: str, context: str = "") -> str:
        """Deep reasoning using Qwen 3.5's thinking mode."""
        system = (
            "You are a deep reasoning engine. Think step by step through the problem. "
            "Consider multiple angles, identify assumptions, and verify your conclusions."
        )
        full_prompt = problem
        if context:
            full_prompt = f"Context:\n{context}\n\nProblem:\n{problem}"

        if self._use_cloud:
            reason_model = getattr(settings, "QWEN_REASON_MODEL", "") or "qwq-plus"
        else:
            reason_model = getattr(settings, "QWEN_REASON_MODEL", "") or getattr(settings, "OLLAMA_MODEL_REASON", "") or "qwen3.5:27b"

        return self.generate(
            prompt=full_prompt,
            model_id=reason_model,
            system_prompt=system,
            temperature=0.3,
            max_tokens=8192,
            enable_thinking=True if self._use_cloud else None,
        )
