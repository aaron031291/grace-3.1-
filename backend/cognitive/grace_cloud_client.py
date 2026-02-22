"""
Kimi Cloud Client - External LLM for Edge Cases

GraceBrain governs ALL calls to this client.
Grace decides WHEN to call, WHAT to ask, and WHETHER to trust the response.

Used for:
- Complex composition that local Llama can't handle well
- Novel reasoning outside Grace's compiled knowledge
- Knowledge mining at higher quality than 1B model

NOT used for:
- Anything Grace can answer from her own knowledge store
- Anything the 9-layer unified intelligence chain handles
- Anything that doesn't pass Grace's governance check

Rate limited: max N calls per hour (configurable).
Every call tracked with Genesis Keys.
Every response verified by hallucination guard.
Every answer stored in distilled knowledge for future deterministic serving.
"""

import logging
import time
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from collections import deque

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class KimiCloudClient:
    """
    Governed external LLM client with read-only source code access.

    GraceBrain decides when to call this.
    Rate limited. Tracked. Verified. Distilled.

    COST OPTIMIZATION:
    - max_tokens capped (shorter responses = fewer tokens)
    - Temperature 0 (deterministic = cacheable)
    - Every response stored in distilled KB (never ask same question twice)
    - Source code context sent only when needed (reduces prompt tokens)
    - System prompt reused (cached on server side)
    """

    def __init__(
        self,
        api_key: str,
        api_url: str = "https://api.moonshot.ai/v1",
        model: str = "moonshot-v1-8k",
        max_calls_per_hour: int = 20,
        temperature: float = 0.0,
        max_tokens: int = 1000,
    ):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.max_calls_per_hour = max_calls_per_hour
        self.temperature = temperature
        self.max_tokens = max_tokens

        self._call_timestamps: deque = deque(maxlen=max_calls_per_hour)
        self._total_calls = 0
        self._total_tokens = 0
        self._source_code_cache: Dict[str, str] = {}  # Cache file reads

    def is_available(self) -> bool:
        """Check if client is configured and not rate limited."""
        if not REQUESTS_AVAILABLE or not self.api_key:
            return False
        return not self._is_rate_limited()

    def _is_rate_limited(self) -> bool:
        """Check if we've exceeded hourly rate limit."""
        now = time.time()
        # Remove timestamps older than 1 hour
        while self._call_timestamps and now - self._call_timestamps[0] > 3600:
            self._call_timestamps.popleft()
        return len(self._call_timestamps) >= self.max_calls_per_hour

    def read_source_file(self, file_path: str, max_lines: int = 100) -> Optional[str]:
        """
        Read-only source code access. Cached to minimize re-reads.

        Used to give Kimi Cloud context about Grace's code when needed.
        Only reads, never modifies.
        """
        if file_path in self._source_code_cache:
            return self._source_code_cache[file_path]

        import os
        # Resolve relative to backend directory
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base, file_path)

        if not os.path.exists(full_path):
            return None

        try:
            with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()[:max_lines]
            content = ''.join(lines)
            self._source_code_cache[file_path] = content
            return content
        except Exception:
            return None

    def generate_with_code_context(
        self,
        prompt: str,
        code_files: List[str],
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate with source code context. Cost-optimized:
        - Only includes relevant file snippets (first 50 lines each)
        - Caps total context to 3000 chars
        - Cached file reads (no re-reading same file)
        """
        context_parts = []
        total_chars = 0
        for file_path in code_files[:5]:  # Max 5 files
            code = self.read_source_file(file_path, max_lines=50)
            if code and total_chars + len(code) < 3000:
                context_parts.append(f"--- {file_path} ---\n{code[:600]}")
                total_chars += len(code[:600])

        if context_parts:
            code_context = "\n\n".join(context_parts)
            full_prompt = f"Source code context:\n{code_context}\n\nQuestion: {prompt}"
        else:
            full_prompt = prompt

        return self.generate(full_prompt, system_prompt=system_prompt, max_tokens=max_tokens)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        task_type: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Call Kimi cloud API. GraceBrain must approve this call first.

        Returns:
            {"success": bool, "content": str, "model_name": str, "tokens": int}
        """
        if not self.api_key:
            return {"success": False, "content": "", "error": "No API key configured"}

        if self._is_rate_limited():
            return {"success": False, "content": "", "error": f"Rate limited ({self.max_calls_per_hour}/hour)"}

        effective_max_tokens = max_tokens or self.max_tokens

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt[:4000]})  # Cap prompt length for cost

        try:
            resp = requests.post(
                f"{self.api_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": self.temperature,
                    "max_tokens": effective_max_tokens,
                },
                timeout=60,
            )

            self._call_timestamps.append(time.time())
            self._total_calls += 1

            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                tokens = data.get("usage", {}).get("total_tokens", 0)
                self._total_tokens += tokens

                return {
                    "success": True,
                    "content": content,
                    "model_name": f"kimi_cloud:{self.model}",
                    "tokens": tokens,
                }
            else:
                return {
                    "success": False,
                    "content": "",
                    "error": f"API error {resp.status_code}: {resp.text[:200]}",
                }

        except Exception as e:
            return {"success": False, "content": "", "error": str(e)}

    def chat(self, model, messages, stream=False, temperature=None, **kwargs):
        """OpenAI-compatible chat interface."""
        prompt = messages[-1].get("content", "") if messages else ""
        system = messages[0].get("content") if messages and messages[0].get("role") == "system" else None
        result = self.generate(prompt, system_prompt=system)
        return result.get("content", "")

    @property
    def default_model(self):
        return self.model

    def is_running(self):
        return bool(self.api_key)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_calls": self._total_calls,
            "total_tokens": self._total_tokens,
            "calls_this_hour": len(self._call_timestamps),
            "rate_limit": self.max_calls_per_hour,
            "available": self.is_available(),
        }


_kimi_cloud: Optional[KimiCloudClient] = None


def get_kimi_cloud_client() -> Optional[KimiCloudClient]:
    """Get the Kimi cloud client if configured."""
    global _kimi_cloud
    if _kimi_cloud is None:
        try:
            from settings import settings
            if settings.KIMI_CLOUD_API_KEY and settings.KIMI_CLOUD_ENABLED:
                _kimi_cloud = KimiCloudClient(
                    api_key=settings.KIMI_CLOUD_API_KEY,
                    api_url=settings.KIMI_CLOUD_API_URL,
                    model=settings.KIMI_CLOUD_MODEL,
                    max_calls_per_hour=settings.KIMI_CLOUD_MAX_CALLS_PER_HOUR,
                    temperature=settings.KIMI_CLOUD_TEMPERATURE,
                )
        except Exception:
            pass
    return _kimi_cloud
