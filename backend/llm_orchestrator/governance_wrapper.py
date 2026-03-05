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
        from core.services.govern_service import get_persona as get_active_persona, list_rules, RULES_DIR
        _list_rule_files = lambda: list_rules().get("documents", [])
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
    Includes governance rules + unified memory context.
    """
    ctx = _load_governance_context()

    parts = []

    # Inject unified memory context (lazy, catches import loops)
    try:
        import importlib
        mi = importlib.import_module("core.memory_injector")
        memory_context = mi.build_llm_context()
        if memory_context:
            parts.append(f"SYSTEM CONTEXT (from Grace's memory):\n{memory_context}")
    except Exception:
        pass

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
        from core.services.govern_service import get_rule_content
        return get_rule_content(folder_path).get("content", "")
    except Exception:
        return ""


_usage_stats = {
    "total_calls": 0,
    "total_errors": 0,
    "by_provider": {},
    "total_latency_ms": 0,
}
_stats_lock = __import__("threading").Lock()


def _track_llm_call(prompt: str, response: str, provider: str, latency_ms: float = 0, error: str = None):
    """Track every LLM call — genesis key + in-memory stats + DB stats."""
    # In-memory stats for BI dashboard
    with _stats_lock:
        _usage_stats["total_calls"] += 1
        _usage_stats["total_latency_ms"] += latency_ms
        if error:
            _usage_stats["total_errors"] += 1
        if provider not in _usage_stats["by_provider"]:
            _usage_stats["by_provider"][provider] = {"calls": 0, "errors": 0, "latency_ms": 0}
        _usage_stats["by_provider"][provider]["calls"] += 1
        _usage_stats["by_provider"][provider]["latency_ms"] += latency_ms
        if error:
            _usage_stats["by_provider"][provider]["errors"] += 1

    # DB stats (fire-and-forget)
    try:
        from database.session import SessionLocal
        if SessionLocal:
            db = SessionLocal()
            try:
                from sqlalchemy import text
                db.execute(text(
                    "INSERT INTO llm_usage_stats (provider, model, call_type, prompt_tokens, "
                    "completion_tokens, latency_ms, success, error_message, caller, created_at, updated_at) "
                    "VALUES (:prov, :model, 'generate', :pt, :ct, :lat, :suc, :err, :caller, :now, :now)"
                ), {
                    "prov": provider, "model": "", "pt": len(prompt.split()),
                    "ct": len(response.split()) if isinstance(response, str) else 0,
                    "lat": latency_ms, "suc": error is None,
                    "err": error, "caller": "governance_wrapper",
                    "now": __import__("datetime").datetime.utcnow(),
                })
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()
    except Exception:
        pass

    # Genesis key
    try:
        from api._genesis_tracker import track
        track(
            key_type="ai_response",
            what=f"LLM call ({provider}): {prompt[:80]}",
            who="system",
            how=f"GovernanceAwareLLM → {provider}",
            input_data={"prompt": prompt},
            output_data={"response": response, "latency_ms": latency_ms},
            tags=["llm_call", provider.lower()],
        )
    except Exception:
        pass

    # Event bus notification
    try:
        from cognitive.event_bus import publish_async
        publish_async("llm.called", {
            "provider": provider, "latency_ms": latency_ms,
            "success": error is None,
        })
    except Exception:
        pass


def get_llm_usage_stats() -> dict:
    """Get aggregated LLM usage statistics for BI dashboard."""
    with _stats_lock:
        stats = dict(_usage_stats)
        stats["by_provider"] = dict(stats["by_provider"])
        if stats["total_calls"] > 0:
            stats["avg_latency_ms"] = round(stats["total_latency_ms"] / stats["total_calls"], 1)
            stats["error_rate"] = round(stats["total_errors"] / stats["total_calls"], 4)
        else:
            stats["avg_latency_ms"] = 0
            stats["error_rate"] = 0
    return stats


class GovernanceAwareLLM(BaseLLMClient):
    """
    Wraps any LLM client to inject governance rules and persona
    into every call automatically. Tracks usage stats for BI.
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
        import time as _time
        gov_prefix = build_governance_prefix()
        if gov_prefix:
            system_prompt = (system_prompt or "") + gov_prefix

        provider_name = type(self._inner).__name__
        start = _time.time()
        error_msg = None
        try:
            result = self._inner.generate(
                prompt=prompt, model_id=model_id, system_prompt=system_prompt,
                temperature=temperature, max_tokens=max_tokens, stream=stream, **kwargs
            )
        except Exception as e:
            error_msg = str(e)
            latency = (_time.time() - start) * 1000
            _track_llm_call(prompt[:200], "", provider_name, latency, error_msg)
            raise

        latency = (_time.time() - start) * 1000
        _track_llm_call(prompt[:200], result if isinstance(result, str) else str(result)[:200], provider_name, latency)

        # Hallucination guard on EVERY call (TIEBREAK-001: quality over quantity)
        result = self._hallucination_check(result, prompt)

        return result

    def _hallucination_check(self, result, prompt: str):
        """Quick hallucination check on every LLM response."""
        if not isinstance(result, str) or len(result) < 20:
            return result
        try:
            flags = []
            lower = result.lower()
            if "as an ai language model" in lower:
                flags.append("self_referential")
            if any(p in lower for p in ["100% guaranteed", "absolutely impossible", "never fails"]):
                flags.append("overconfident")
            if len(result) < 30 and "?" not in prompt:
                flags.append("suspiciously_short")

            if flags:
                try:
                    from cognitive.event_bus import publish_async
                    publish_async("hallucination.detected", {
                        "flags": flags, "provider": type(self._inner).__name__,
                        "prompt_preview": prompt[:100],
                    }, source="governance_wrapper")
                except Exception:
                    pass
        except Exception:
            pass
        return result

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        import time as _time
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

        provider_name = type(self._inner).__name__
        start = _time.time()
        error_msg = None
        try:
            result = self._inner.chat(
                messages=messages, model=model, stream=stream,
                temperature=temperature, **kwargs
            )
        except Exception as e:
            error_msg = str(e)
            latency = (_time.time() - start) * 1000
            _track_llm_call(prompt_preview, "", provider_name, latency, error_msg)
            raise

        latency = (_time.time() - start) * 1000
        _track_llm_call(prompt_preview, result if isinstance(result, str) else str(result)[:200], provider_name, latency)
        return result

    def is_running(self) -> bool:
        return self._inner.is_running()

    def get_all_models(self) -> List[Dict[str, Any]]:
        return self._inner.get_all_models()

    def model_exists(self, model_name: str) -> bool:
        return self._inner.model_exists(model_name)
