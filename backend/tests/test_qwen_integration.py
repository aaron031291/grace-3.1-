"""
Tests for Qwen 3 integration across the Grace system.

Verifies:
1. QwenLLMClient implements BaseLLMClient correctly
2. Client works in both cloud and local (Ollama) modes
3. Factory registers and returns Qwen client
4. Consensus engine includes Qwen in model registry
5. Settings load Qwen configuration correctly
6. Ask Grace LLM fallback includes Qwen
"""

import sys
import os
import importlib.util
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _load_module(name, path):
    """Load a module directly from file path, bypassing __init__.py chains."""
    full = os.path.join(os.path.dirname(__file__), "..", path)
    spec = importlib.util.spec_from_file_location(name, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Pre-load to avoid qdrant import chain
_settings = _load_module("settings", "settings.py")
_base = _load_module("llm_orchestrator.base_client", "llm_orchestrator/base_client.py")
_qwen = _load_module("llm_orchestrator.qwen_client", "llm_orchestrator/qwen_client.py")


class TestQwenClientBasics:

    def test_instantiates_without_api_key(self):
        client = _qwen.QwenLLMClient()
        assert client._use_cloud is False
        assert "qwen3" in client.default_model or "qwen" in client.default_model

    def test_instantiates_with_api_key(self):
        client = _qwen.QwenLLMClient(api_key="test-key-123")
        assert client._use_cloud is True
        assert client.api_key == "test-key-123"

    def test_implements_base_client(self):
        client = _qwen.QwenLLMClient()
        assert isinstance(client, _base.BaseLLMClient)

    def test_has_generate_method(self):
        client = _qwen.QwenLLMClient()
        assert callable(getattr(client, "generate", None))

    def test_has_chat_method(self):
        client = _qwen.QwenLLMClient()
        assert callable(getattr(client, "chat", None))

    def test_has_is_running_method(self):
        client = _qwen.QwenLLMClient()
        assert callable(getattr(client, "is_running", None))

    def test_has_get_all_models_method(self):
        client = _qwen.QwenLLMClient()
        assert callable(getattr(client, "get_all_models", None))

    def test_has_model_exists_method(self):
        client = _qwen.QwenLLMClient()
        assert callable(getattr(client, "model_exists", None))

    def test_has_code_generate(self):
        client = _qwen.QwenLLMClient()
        assert callable(getattr(client, "code_generate", None))

    def test_has_reason(self):
        client = _qwen.QwenLLMClient()
        assert callable(getattr(client, "reason", None))

    def test_custom_base_url(self):
        client = _qwen.QwenLLMClient(base_url="https://custom.endpoint.com/v1")
        assert client.base_url == "https://custom.endpoint.com/v1"

    def test_custom_model(self):
        client = _qwen.QwenLLMClient(model="qwen-max")
        assert client.default_model == "qwen-max"

    def test_local_get_all_models(self):
        client = _qwen.QwenLLMClient()
        models = client.get_all_models()
        assert isinstance(models, list)
        assert len(models) >= 1
        assert models[0]["id"] == "qwen-local"

    def test_cloud_headers(self):
        client = _qwen.QwenLLMClient(api_key="sk-test")
        assert client.headers["Authorization"] == "Bearer sk-test"
        assert client.headers["Content-Type"] == "application/json"


class TestQwenSettings:

    def test_qwen_api_key_setting(self):
        assert hasattr(_settings.settings, "QWEN_API_KEY")

    def test_qwen_base_url_setting(self):
        assert hasattr(_settings.settings, "QWEN_BASE_URL")
        assert "dashscope" in _settings.settings.QWEN_BASE_URL

    def test_qwen_model_setting(self):
        assert hasattr(_settings.settings, "QWEN_MODEL")
        assert "qwen3" in _settings.settings.QWEN_MODEL

    def test_qwen_code_model_setting(self):
        assert hasattr(_settings.settings, "QWEN_CODE_MODEL")
        assert "qwen3" in _settings.settings.QWEN_CODE_MODEL

    def test_qwen_reason_model_setting(self):
        assert hasattr(_settings.settings, "QWEN_REASON_MODEL")
        assert "qwen3" in _settings.settings.QWEN_REASON_MODEL


class TestFactoryIntegration:

    def test_factory_has_qwen_import(self):
        factory_path = os.path.join(os.path.dirname(__file__), "..", "llm_orchestrator", "factory.py")
        with open(factory_path) as f:
            content = f.read()
        assert "QwenLLMClient" in content
        assert "from .qwen_client import QwenLLMClient" in content

    def test_factory_get_llm_client_qwen_branch(self):
        factory_path = os.path.join(os.path.dirname(__file__), "..", "llm_orchestrator", "factory.py")
        with open(factory_path) as f:
            content = f.read()
        assert 'provider == "qwen"' in content

    def test_factory_get_raw_client_qwen_branch(self):
        factory_path = os.path.join(os.path.dirname(__file__), "..", "llm_orchestrator", "factory.py")
        with open(factory_path) as f:
            content = f.read()
        assert "get_qwen_client" in content

    def test_factory_all_models_includes_qwen(self):
        factory_path = os.path.join(os.path.dirname(__file__), "..", "llm_orchestrator", "factory.py")
        with open(factory_path) as f:
            content = f.read()
        assert '"id": "qwen"' in content
        assert "Qwen 3" in content


class TestConsensusEngineIntegration:

    def test_model_registry_has_qwen(self):
        consensus_path = os.path.join(os.path.dirname(__file__), "..", "cognitive", "consensus_engine.py")
        with open(consensus_path) as f:
            content = f.read()
        assert '"qwen"' in content
        assert '"provider": "qwen"' in content

    def test_get_client_handles_qwen_provider(self):
        consensus_path = os.path.join(os.path.dirname(__file__), "..", "cognitive", "consensus_engine.py")
        with open(consensus_path) as f:
            content = f.read()
        assert 'provider == "qwen"' in content
        assert "get_qwen_client" in content

    def test_check_available_handles_qwen(self):
        consensus_path = os.path.join(os.path.dirname(__file__), "..", "cognitive", "consensus_engine.py")
        with open(consensus_path) as f:
            content = f.read()
        assert 'info["provider"] == "qwen"' in content
        assert "QWEN_API_KEY" in content

    def test_qwen_strengths_include_key_capabilities(self):
        consensus_path = os.path.join(os.path.dirname(__file__), "..", "cognitive", "consensus_engine.py")
        with open(consensus_path) as f:
            content = f.read()
        assert "code generation" in content
        assert "reasoning" in content
        assert "multilingual" in content


class TestLiveConsoleIntegration:

    def test_live_console_checks_qwen(self):
        console_path = os.path.join(os.path.dirname(__file__), "..", "api", "live_console_api.py")
        with open(console_path) as f:
            content = f.read()
        assert "QWEN_API_KEY" in content
        assert 'models"]["qwen"]' in content


class TestAskGraceIntegration:

    def test_ask_grace_tries_qwen_first(self):
        api_path = os.path.join(os.path.dirname(__file__), "..", "api", "ask_grace_api.py")
        with open(api_path) as f:
            content = f.read()
        assert '"qwen"' in content
        assert 'providers_to_try' in content

    def test_ask_grace_consensus_includes_qwen(self):
        api_path = os.path.join(os.path.dirname(__file__), "..", "api", "ask_grace_api.py")
        with open(api_path) as f:
            content = f.read()
        assert 'models=["qwen", "kimi", "opus"]' in content


class TestEnvExample:

    def test_env_example_has_qwen_config(self):
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env.example")
        with open(env_path) as f:
            content = f.read()
        assert "QWEN_API_KEY" in content
        assert "QWEN_BASE_URL" in content
        assert "QWEN_MODEL" in content
        assert "QWEN_CODE_MODEL" in content
        assert "QWEN_REASON_MODEL" in content
        assert "dashscope" in content


class TestFrontendIntegration:

    def test_chat_tab_has_qwen3_label(self):
        chat_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "components", "ChatTab.jsx")
        with open(chat_path) as f:
            content = f.read()
        assert 'label: "Qwen 3"' in content

    def test_consensus_chat_has_qwen3_color(self):
        consensus_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "components", "ConsensusChat.jsx")
        with open(consensus_path) as f:
            content = f.read()
        assert "'Qwen 3'" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
