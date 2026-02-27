"""
Governance-Aware LLM Wrapper

Wraps any BaseLLMClient to automatically inject governance rules and
persona context into every LLM call system-wide.

All uploaded rule documents (GDPR, ISO, anti-bribery, code standards,
user rules) become law — injected into the system prompt so Grace and
Kimi always follow them.

Persona context (personal + professional) shapes how Grace communicates.
"""

import logging
from typing import List, Dict, Any, Optional, Union
from .base_client import BaseLLMClient

logger = logging.getLogger(__name__)

_rules_cache = None
_rules_cache_ts = 0


def _load_governance_context() -> Dict[str, str]:
    """
    Load all active governance rules and persona from the governance rules API.
    Cached for 60 seconds to avoid reading files on every LLM call.
    """
    import time
    global _rules_cache, _rules_cache_ts

    now = time.time()
    if _rules_cache is not None and (now - _rules_cache_ts) < 60:
        return _rules_cache

    try:
        from api.governance_rules_api import get_active_persona, _list_rule_files, RULES_DIR
        import json

        persona = get_active_persona()

        rule_texts = []
        docs = _list_rule_files()
        for d in docs:
            if not d.get("enforced", True):
                continue
            file_path = RULES_DIR / d["id"]
            if file_path.exists():
                try:
                    text = file_path.read_text(errors="ignore")[:3000]
                    rule_texts.append(f"[RULE: {d['filename']} ({d['category']})]\n{text}")
                except Exception:
                    pass

        result = {
            "rules": "\n\n---\n\n".join(rule_texts) if rule_texts else "",
            "rules_count": len(rule_texts),
            "personal": persona.get("personal", ""),
            "professional": persona.get("professional", ""),
        }

        _rules_cache = result
        _rules_cache_ts = now
        return result
    except Exception as e:
        logger.debug(f"Governance context load skipped: {e}")
        return {"rules": "", "rules_count": 0, "personal": "", "professional": ""}


def build_governance_prefix() -> str:
    """
    Build the governance prefix that gets prepended to every system prompt.
    Returns empty string if no rules or persona are configured.
    """
    ctx = _load_governance_context()

    parts = []

    if ctx["rules"]:
        parts.append(
            f"MANDATORY GOVERNANCE RULES ({ctx['rules_count']} documents enforced):\n"
            f"You MUST comply with all of the following rules. They are LAW.\n\n"
            f"{ctx['rules']}"
        )

    if ctx["personal"]:
        parts.append(f"PERSONAL INTERACTION STYLE:\n{ctx['personal']}")

    if ctx["professional"]:
        parts.append(f"PROFESSIONAL PRESENTATION STYLE (for external communications, documents, emails):\n{ctx['professional']}")

    if not parts:
        return ""

    return "\n\n" + "\n\n---\n\n".join(parts) + "\n\n---\n\n"


def build_domain_prefix(folder_path: str) -> str:
    """Build governance prefix specific to a domain folder."""
    try:
        from api.domain_api import _get_domain_rules
        return _get_domain_rules(folder_path)
    except Exception:
        return ""


def _track_llm_call(prompt: str, response: str, provider: str):
    """Track every LLM input/output via genesis key."""
    try:
        from api._genesis_tracker import track
        track(
            key_type="ai_response",
            what=f"LLM call ({provider}): {prompt[:80]}",
            who="system",
            how=f"GovernanceAwareLLM → {provider}",
            input_data={"prompt": prompt},
            output_data={"response": response},
            tags=["llm_call", provider.lower()],
        )
    except Exception:
        pass


class GovernanceAwareLLM(BaseLLMClient):
    """
    Wraps any LLM client to inject governance rules and persona
    into every call automatically.
    """

    def __init__(self, inner: BaseLLMClient):
        self._inner = inner

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
        gov_prefix = build_governance_prefix()
        if gov_prefix:
            system_prompt = (system_prompt or "") + gov_prefix
        result = self._inner.generate(
            prompt=prompt, model_id=model_id, system_prompt=system_prompt,
            temperature=temperature, max_tokens=max_tokens, stream=stream, **kwargs
        )
        _track_llm_call(prompt[:200], result if isinstance(result, str) else str(result)[:200], type(self._inner).__name__)
        return result

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        gov_prefix = build_governance_prefix()
        prompt_preview = messages[-1].get("content", "")[:200] if messages else ""
        if gov_prefix:
            messages = list(messages)
            if messages and messages[0].get("role") == "system":
                messages[0] = {
                    "role": "system",
                    "content": messages[0]["content"] + gov_prefix,
                }
            else:
                messages.insert(0, {"role": "system", "content": gov_prefix.strip()})
        result = self._inner.chat(
            messages=messages, model=model, stream=stream,
            temperature=temperature, **kwargs
        )
        _track_llm_call(prompt_preview, result if isinstance(result, str) else str(result)[:200], type(self._inner).__name__)
        return result

    def is_running(self) -> bool:
        return self._inner.is_running()

    def get_all_models(self) -> List[Dict[str, Any]]:
        return self._inner.get_all_models()

    def model_exists(self, model_name: str) -> bool:
        return self._inner.model_exists(model_name)
