"""
Tests for llm_orchestrator logic: factory routing, hallucination guard,
governance wrapper, multi-LLM helpers (RateLimiter, LRUCache, RetryConfig),
ExternalVerifier, and HallucinationGuard layers.
"""

import time
import threading
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Patch heavy imports before any orchestrator module is loaded
# ---------------------------------------------------------------------------
import sys

# Stub modules that pull in DB / cognitive / ML at import time.
# Must be registered BEFORE any llm_orchestrator submodule is imported.
_stub_modules = [
    # cognitive
    "cognitive", "cognitive.trust_engine", "cognitive.event_bus",
    "cognitive.ghost_memory", "cognitive.runpod_client",
    "cognitive.learning_memory",
    # core
    "core.services.govern_service", "core.memory_injector",
    # database / models / ORM (don't stub sqlalchemy — it's installed)
    "database", "database.base", "database.session",
    "models", "models.database_models", "models.genesis_key_models",
    "models.librarian_models",
    # embedding
    "embedding", "embedding.embedder",
    # ollama client
    "ollama_client", "ollama_client.client",
    # genesis
    "genesis", "genesis.cognitive_layer1_integration",
    # ML
    "ml_intelligence", "ml_intelligence.neuro_symbolic_reasoner",
    # API
    "api._genesis_tracker",
]
for mod_name in _stub_modules:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

# Stub settings so factory.py can import
_mock_settings = MagicMock()
_mock_settings.LLM_PROVIDER = "ollama"
_mock_settings.LLM_API_KEY = "test-key"
_mock_settings.LLM_MODEL = "gpt-4o"
_mock_settings.OLLAMA_URL = "http://localhost:11434"
_mock_settings.OLLAMA_LLM_DEFAULT = "qwen3:14b"
_mock_settings.OLLAMA_MODEL_CODE = "qwen2.5-coder:32b"
_mock_settings.OLLAMA_MODEL_REASON = "qwen3:32b"
_mock_settings.OLLAMA_MODEL_FAST = "qwen3:14b"
_mock_settings.OLLAMA_MODEL_DOCUMENT = ""
_mock_settings.KIMI_API_KEY = "kimi-key"
_mock_settings.KIMI_MODEL = "kimi-k2.5"
_mock_settings.OPUS_API_KEY = "opus-key"
_mock_settings.OPUS_MODEL = "opus-4.6"

_settings_mod = MagicMock()
_settings_mod.settings = _mock_settings
sys.modules["settings"] = _settings_mod

# Now import orchestrator modules
from backend.llm_orchestrator.base_client import BaseLLMClient
from backend.llm_orchestrator.multi_llm_client import (
    RateLimiter, LRUCache, RetryConfig, TaskType, ModelCapability, LLMModel,
)
from backend.llm_orchestrator.hallucination_guard import (
    ExternalVerifier, ConsensusResult, VerificationResult, HallucinationGuard,
)
from backend.llm_orchestrator.governance_wrapper import (
    GovernanceAwareLLM, _track_llm_call, get_llm_usage_stats,
    build_governance_prefix, _usage_stats, _stats_lock,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeClient(BaseLLMClient):
    """Minimal concrete BaseLLMClient for testing."""

    def __init__(self, response="ok", raises=None):
        self._response = response
        self._raises = raises
        self.calls = []

    def generate(self, prompt, model_id=None, system_prompt=None,
                 temperature=None, max_tokens=None, stream=False, **kw):
        self.calls.append(("generate", prompt))
        if self._raises:
            raise self._raises
        return self._response

    def chat(self, messages, model=None, stream=False, temperature=None, **kw):
        self.calls.append(("chat", messages))
        if self._raises:
            raise self._raises
        return self._response

    def is_running(self):
        return True

    def get_all_models(self):
        return [{"name": "fake-model"}]

    def model_exists(self, model_name):
        return model_name == "fake-model"


# ===================================================================
# 1. RateLimiter
# ===================================================================

class TestRateLimiter:
    def test_acquire_succeeds_when_tokens_available(self):
        rl = RateLimiter(requests_per_minute=10, requests_per_hour=100)
        assert rl.acquire(timeout=1) is True

    def test_acquire_depletes_tokens(self):
        rl = RateLimiter(requests_per_minute=2, requests_per_hour=100)
        assert rl.acquire(timeout=0.1) is True
        assert rl.acquire(timeout=0.1) is True
        # Third should fail (minute bucket exhausted, no refill yet)
        assert rl.acquire(timeout=0.2) is False

    def test_get_status_returns_dict(self):
        rl = RateLimiter(requests_per_minute=5, requests_per_hour=50)
        status = rl.get_status()
        assert status["requests_per_minute"] == 5
        assert status["requests_per_hour"] == 50
        assert "minute_tokens_remaining" in status


# ===================================================================
# 2. LRUCache
# ===================================================================

class TestLRUCache:
    def test_set_and_get(self):
        cache = LRUCache(max_size=10, ttl_seconds=60)
        cache.set("hello", "model-a", {"content": "world"})
        hit = cache.get("hello", "model-a")
        assert hit is not None
        assert hit["content"] == "world"

    def test_miss_returns_none(self):
        cache = LRUCache(max_size=10, ttl_seconds=60)
        assert cache.get("nonexistent", "m") is None

    def test_eviction_on_max_size(self):
        cache = LRUCache(max_size=2, ttl_seconds=60)
        cache.set("a", "m", {"v": 1})
        cache.set("b", "m", {"v": 2})
        cache.set("c", "m", {"v": 3})  # should evict "a"
        assert cache.get("a", "m") is None
        assert cache.get("b", "m") is not None

    def test_ttl_expiration(self):
        cache = LRUCache(max_size=10, ttl_seconds=0)  # immediate expiry
        cache.set("x", "m", {"v": 1})
        time.sleep(0.01)
        assert cache.get("x", "m") is None

    def test_stats_tracking(self):
        cache = LRUCache(max_size=10, ttl_seconds=60)
        cache.set("k", "m", {"v": 1})
        cache.get("k", "m")   # hit
        cache.get("z", "m")   # miss
        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1


# ===================================================================
# 3. RetryConfig
# ===================================================================

class TestRetryConfig:
    def test_get_delay_exponential(self):
        rc = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=30.0)
        assert rc.get_delay(0) == 1.0
        assert rc.get_delay(1) == 2.0
        assert rc.get_delay(2) == 4.0

    def test_get_delay_capped(self):
        rc = RetryConfig(base_delay=1.0, exponential_base=2.0, max_delay=5.0)
        assert rc.get_delay(10) == 5.0

    def test_should_retry_connection_error(self):
        rc = RetryConfig()
        assert rc.should_retry(ConnectionError("down")) is True

    def test_should_not_retry_value_error(self):
        rc = RetryConfig()
        assert rc.should_retry(ValueError("bad")) is False


# ===================================================================
# 4. ExternalVerifier
# ===================================================================

class TestExternalVerifier:
    def test_extract_technical_patterns_code_blocks(self):
        ev = ExternalVerifier()
        text = "Use `my_func()` and ```python\nprint('hi')\n```"
        patterns = ev._extract_technical_patterns(text)
        assert "my_func()" in patterns["code_patterns"]
        assert "print('hi')\n" in patterns["code_patterns"]

    def test_extract_function_and_class_names(self):
        ev = ExternalVerifier()
        text = "Call my_function(arg) and use MyClass for it."
        patterns = ev._extract_technical_patterns(text)
        assert "my_function" in patterns["function_names"]
        assert "MyClass" in patterns["class_names"]

    def test_verify_technical_claim_caches(self):
        ev = ExternalVerifier(cache_results=True)
        result1 = ev.verify_technical_claim("test claim", technologies=["python"])
        result2 = ev.verify_technical_claim("test claim", technologies=["python"])
        assert result1 == result2

    def test_verify_factual_claim_conservative(self):
        ev = ExternalVerifier()
        result = ev.verify_factual_claim("The earth is flat")
        assert result["confidence"] == 0.5  # neutral without web search

    def test_validate_js_syntax_balanced(self):
        ev = ExternalVerifier()
        assert ev._validate_js_syntax("function f() { return [1]; }") is True
        assert ev._validate_js_syntax("function f() { return [1; }") is False


# ===================================================================
# 5. GovernanceAwareLLM — wrapper delegation + hallucination check
# ===================================================================

class TestGovernanceAwareLLM:
    @patch("backend.llm_orchestrator.governance_wrapper.build_governance_prefix", return_value="")
    @patch("backend.llm_orchestrator.governance_wrapper._track_llm_call")
    def test_generate_delegates_to_inner(self, mock_track, mock_gov):
        inner = FakeClient(response="hello world response text")
        wrapped = GovernanceAwareLLM(inner)
        result = wrapped.generate("say hello")
        assert result == "hello world response text"
        assert inner.calls[0] == ("generate", "say hello")

    @patch("backend.llm_orchestrator.governance_wrapper.build_governance_prefix", return_value="")
    @patch("backend.llm_orchestrator.governance_wrapper._track_llm_call")
    def test_generate_detects_self_referential(self, mock_track, mock_gov):
        inner = FakeClient(response="As an AI language model, I cannot do that thing for you ever.")
        wrapped = GovernanceAwareLLM(inner)
        # Should still return but log a warning (we just check it doesn't crash)
        result = wrapped.generate("tell me something")
        assert "AI language model" in result

    @patch("backend.llm_orchestrator.governance_wrapper.build_governance_prefix", return_value="")
    @patch("backend.llm_orchestrator.governance_wrapper._track_llm_call")
    def test_generate_detects_overconfidence(self, mock_track, mock_gov):
        inner = FakeClient(response="This method is 100% guaranteed to work every time forever.")
        wrapped = GovernanceAwareLLM(inner)
        result = wrapped.generate("will this work?")
        assert "100% guaranteed" in result

    @patch("backend.llm_orchestrator.governance_wrapper.build_governance_prefix", return_value="")
    @patch("backend.llm_orchestrator.governance_wrapper._track_llm_call")
    def test_chat_injects_governance_system_message(self, mock_track, mock_gov):
        mock_gov.return_value = "\n\nRULES HERE\n\n"
        inner = FakeClient(response="chat reply")
        wrapped = GovernanceAwareLLM(inner)
        msgs = [{"role": "user", "content": "hi"}]
        result = wrapped.chat(msgs)
        assert result == "chat reply"
        # The wrapper should have inserted a system message
        sent_msgs = inner.calls[0][1]
        assert sent_msgs[0]["role"] == "system"

    @patch("backend.llm_orchestrator.governance_wrapper.build_governance_prefix", return_value="")
    @patch("backend.llm_orchestrator.governance_wrapper._track_llm_call")
    def test_is_running_delegates(self, mock_track, mock_gov):
        inner = FakeClient()
        wrapped = GovernanceAwareLLM(inner)
        assert wrapped.is_running() is True

    @patch("backend.llm_orchestrator.governance_wrapper.build_governance_prefix", return_value="")
    @patch("backend.llm_orchestrator.governance_wrapper._track_llm_call")
    def test_model_exists_delegates(self, mock_track, mock_gov):
        inner = FakeClient()
        wrapped = GovernanceAwareLLM(inner)
        assert wrapped.model_exists("fake-model") is True
        assert wrapped.model_exists("nope") is False


# ===================================================================
# 6. _track_llm_call & get_llm_usage_stats
# ===================================================================

class TestUsageStats:
    def setup_method(self):
        # Reset global stats before each test
        with _stats_lock:
            _usage_stats["total_calls"] = 0
            _usage_stats["total_errors"] = 0
            _usage_stats["by_provider"] = {}
            _usage_stats["total_latency_ms"] = 0

    def test_track_increments_calls(self):
        _track_llm_call("prompt", "response", "TestProvider", latency_ms=50)
        stats = get_llm_usage_stats()
        assert stats["total_calls"] == 1
        assert stats["by_provider"]["TestProvider"]["calls"] == 1

    def test_track_records_errors(self):
        _track_llm_call("p", "r", "P", latency_ms=10, error="boom")
        stats = get_llm_usage_stats()
        assert stats["total_errors"] == 1
        assert stats["by_provider"]["P"]["errors"] == 1

    def test_avg_latency_computed(self):
        _track_llm_call("a", "b", "X", latency_ms=100)
        _track_llm_call("a", "b", "X", latency_ms=200)
        stats = get_llm_usage_stats()
        assert stats["avg_latency_ms"] == 150.0

    def test_error_rate_computed(self):
        _track_llm_call("a", "b", "X", latency_ms=10)
        _track_llm_call("a", "b", "X", latency_ms=10, error="e")
        stats = get_llm_usage_stats()
        assert stats["error_rate"] == 0.5


# ===================================================================
# 7. HallucinationGuard — layer methods
# ===================================================================

class TestHallucinationGuard:
    def test_verify_repository_grounding_no_repo(self):
        guard = HallucinationGuard(enable_external_verification=False)
        is_grounded, files, details = guard.verify_repository_grounding(
            "Check `main.py` for details", require_file_references=True
        )
        # No repo_access → no files verified → not grounded
        assert is_grounded is False
        assert "main.py" in details["referenced_files"]

    def test_verify_repository_grounding_with_repo(self):
        repo = MagicMock()
        repo.read_file.return_value = {"content": "x = 1"}
        guard = HallucinationGuard(repo_access=repo, enable_external_verification=False)
        is_grounded, files, details = guard.verify_repository_grounding(
            'Look at `utils.py` and "config.json"', require_file_references=True
        )
        assert is_grounded is True
        assert len(files) > 0

    def test_consensus_without_multi_llm(self):
        guard = HallucinationGuard(enable_external_verification=False)
        result = guard.check_cross_model_consensus("test", TaskType.GENERAL)
        assert result.agreed is False
        assert result.confidence == 0.0

    def test_consensus_with_agreeing_models(self):
        multi = MagicMock()
        multi.generate_multiple.return_value = [
            {"success": True, "content": "Python is a programming language.", "model_name": "A"},
            {"success": True, "content": "Python is a programming language.", "model_name": "B"},
            {"success": True, "content": "Python is a programming language.", "model_name": "C"},
        ]
        guard = HallucinationGuard(multi_llm_client=multi, enable_external_verification=False)
        result = guard.check_cross_model_consensus("What is Python?", TaskType.GENERAL)
        assert result.agreed is True
        assert result.confidence >= 0.7

    def test_consensus_with_disagreeing_models(self):
        multi = MagicMock()
        multi.generate_multiple.return_value = [
            {"success": True, "content": "Python is a snake.", "model_name": "A"},
            {"success": True, "content": "Completely different unrelated text about weather.", "model_name": "B"},
        ]
        guard = HallucinationGuard(multi_llm_client=multi, enable_external_verification=False)
        result = guard.check_cross_model_consensus("What is Python?", TaskType.GENERAL, similarity_threshold=0.9)
        assert result.agreed is False
        assert len(result.disagreements) > 0

    def test_calculate_similarity(self):
        guard = HallucinationGuard(enable_external_verification=False)
        assert guard._calculate_similarity("hello world", "hello world") == 1.0
        assert guard._calculate_similarity("", "text") == 0.0
        sim = guard._calculate_similarity("abc", "abx")
        assert 0.0 < sim < 1.0

    def test_check_contradictions_no_detector(self):
        guard = HallucinationGuard(enable_external_verification=False)
        has, items = guard.check_contradictions("some text")
        assert has is False
        assert items == []

    def test_calculate_confidence_no_scorer(self):
        guard = HallucinationGuard(enable_external_verification=False)
        result = guard.calculate_confidence_score("text here")
        assert result["confidence_score"] == 0.5

    def test_verify_trust_no_repo(self):
        guard = HallucinationGuard(enable_external_verification=False)
        verified, score, examples = guard.verify_against_trust_system("content")
        assert verified is False
        assert score == 0.5

    def test_detect_technologies(self):
        guard = HallucinationGuard(enable_external_verification=False)
        techs = guard._detect_technologies("Use fastapi and pytorch with numpy arrays")
        assert "fastapi" in techs
        assert "pytorch" in techs

    def test_detect_technologies_empty(self):
        guard = HallucinationGuard(enable_external_verification=False)
        techs = guard._detect_technologies("no tech keywords here at all")
        assert techs == []

    def test_verification_stats_empty(self):
        guard = HallucinationGuard(enable_external_verification=False)
        stats = guard.get_verification_stats()
        assert stats["total_verifications"] == 0
        assert stats["avg_confidence"] == 0.0

    def test_verification_log_and_stats(self):
        guard = HallucinationGuard(enable_external_verification=False)
        guard.verification_log.append({
            "timestamp": "2025-01-01", "prompt": "test",
            "is_verified": True, "confidence": 0.9,
            "layers": {"grounding": True}
        })
        guard.verification_log.append({
            "timestamp": "2025-01-02", "prompt": "test2",
            "is_verified": False, "confidence": 0.4,
            "layers": {"grounding": False}
        })
        stats = guard.get_verification_stats()
        assert stats["total_verifications"] == 2
        assert stats["verification_rate"] == 0.5
        assert 0.6 < stats["avg_confidence"] < 0.7
        assert "grounding" in stats["layer_success_rates"]

    def test_verify_external_no_verifier(self):
        guard = HallucinationGuard(enable_external_verification=False)
        result = guard.verify_external("code here", TaskType.CODE_GENERATION)
        assert result["verified"] is False
        assert result["enabled"] is False


# ===================================================================
# 8. Factory routing (get_llm_for_task, get_llm_client)
# ===================================================================

class TestFactory:
    @patch("backend.llm_orchestrator.factory.OllamaLLMClient")
    @patch("backend.llm_orchestrator.factory.resolve_ollama_model", return_value="qwen2.5-coder:32b")
    def test_get_llm_for_task_code(self, mock_resolve, mock_ollama_cls):
        mock_ollama_cls.return_value = FakeClient()
        from backend.llm_orchestrator.factory import get_llm_for_task
        client = get_llm_for_task("code")
        assert isinstance(client, GovernanceAwareLLM)
        mock_resolve.assert_called_with("code")

    @patch("backend.llm_orchestrator.factory.OllamaLLMClient")
    @patch("backend.llm_orchestrator.factory.resolve_ollama_model", return_value="qwen3:32b")
    def test_get_llm_for_task_reason(self, mock_resolve, mock_ollama_cls):
        mock_ollama_cls.return_value = FakeClient()
        from backend.llm_orchestrator.factory import get_llm_for_task
        client = get_llm_for_task("reason")
        assert isinstance(client, GovernanceAwareLLM)

    @patch("backend.llm_orchestrator.factory.OpusLLMClient")
    def test_get_llm_for_task_audit_uses_opus(self, mock_opus_cls):
        mock_opus_cls.return_value = FakeClient()
        from backend.llm_orchestrator.factory import get_llm_for_task
        client = get_llm_for_task("audit")
        assert isinstance(client, GovernanceAwareLLM)

    @patch("backend.llm_orchestrator.factory.OllamaLLMClient")
    def test_get_llm_for_task_general_fallback(self, mock_ollama_cls):
        mock_ollama_cls.return_value = FakeClient()
        from backend.llm_orchestrator.factory import get_llm_for_task
        client = get_llm_for_task("general")
        assert isinstance(client, GovernanceAwareLLM)

    @patch("backend.llm_orchestrator.factory.OpenAILLMClient")
    def test_get_llm_client_openai(self, mock_openai_cls):
        mock_openai_cls.return_value = FakeClient()
        from backend.llm_orchestrator.factory import get_llm_client
        client = get_llm_client("openai")
        assert isinstance(client, GovernanceAwareLLM)

    @patch("backend.llm_orchestrator.factory.OllamaLLMClient")
    def test_get_llm_client_default_ollama(self, mock_ollama_cls):
        mock_ollama_cls.return_value = FakeClient()
        from backend.llm_orchestrator.factory import get_llm_client
        client = get_llm_client("ollama")
        assert isinstance(client, GovernanceAwareLLM)

    def test_get_all_available_models(self):
        from backend.llm_orchestrator.factory import get_all_available_models
        models = get_all_available_models()
        assert isinstance(models, list)
        assert len(models) >= 5  # 3 local + 2 cloud
        ids = [m["id"] for m in models]
        assert "code" in ids
        assert "kimi" in ids
        assert "opus" in ids


# ===================================================================
# 9. LLMModel dataclass
# ===================================================================

class TestLLMModel:
    def test_model_creation(self):
        m = LLMModel(
            name="Test", model_id="test:7b",
            capabilities=[ModelCapability.CODE],
            context_window=8192,
            recommended_tasks=[TaskType.CODE_GENERATION],
            priority=5
        )
        assert m.name == "Test"
        assert m.priority == 5
        assert m.temperature == 0.7  # default

    def test_model_custom_defaults(self):
        m = LLMModel(
            name="Fast", model_id="fast:3b",
            capabilities=[ModelCapability.SPEED],
            context_window=4096,
            recommended_tasks=[TaskType.QUICK_QUERY],
            priority=3, max_tokens=1024, temperature=0.3
        )
        assert m.max_tokens == 1024
        assert m.temperature == 0.3
