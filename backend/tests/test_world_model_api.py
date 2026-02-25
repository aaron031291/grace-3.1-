"""Tests for World Model API and Librarian Autonomous FS API."""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestWorldModelHelpers:
    """Test world model internal helpers."""

    def test_get_source_code_stats(self):
        from api.world_model_api import _get_source_code_stats
        stats = _get_source_code_stats()
        assert "total_python_files" in stats
        assert stats["total_python_files"] > 0
        assert "total_lines" in stats
        assert stats["total_lines"] > 0
        assert "modules" in stats
        assert len(stats["modules"]) > 0

    def test_get_knowledge_base_stats(self):
        from api.world_model_api import _get_knowledge_base_stats
        stats = _get_knowledge_base_stats()
        assert "path" in stats
        assert "exists" in stats

    def test_get_system_resources(self):
        from api.world_model_api import _get_system_resources
        resources = _get_system_resources()
        assert "cpu_percent" in resources
        assert "memory_percent" in resources

    def test_read_source_file(self):
        from api.world_model_api import _read_source_file
        content = _read_source_file("settings.py")
        assert "Settings" in content
        assert len(content) > 100

    def test_read_source_file_not_found(self):
        from api.world_model_api import _read_source_file
        content = _read_source_file("nonexistent_file.py")
        assert "[Error" in content

    def test_read_source_file_path_escape(self):
        from api.world_model_api import _read_source_file
        content = _read_source_file("../../etc/passwd")
        assert "[Error" in content

    def test_build_state_context(self):
        from api.world_model_api import _build_state_context
        state = {
            "health": {"overall": "healthy", "llm": "up"},
            "knowledge_base": {"total_files": 42, "total_directories": 5, "total_size_mb": 1.5},
            "source_code": {"total_python_files": 100, "total_lines": 20000, "modules": {"api": 10}},
            "database": {"connected": True, "table_count": 8, "row_counts": {"chats": 50}},
            "chats": {"total_chats": 10, "total_messages": 100},
            "apis": {"total_routes": 200},
            "capabilities": ["chat", "rag_retrieval"],
        }
        ctx = _build_state_context(state)
        assert "healthy" in ctx
        assert "42 files" in ctx
        assert "100 Python files" in ctx
        assert "chats: 50 rows" in ctx
        assert "10 conversations" in ctx
        assert "200 registered endpoints" in ctx


class TestLibrarianFsHelpers:
    """Test librarian filesystem helpers."""

    def test_suggest_directory_python(self):
        from api.librarian_autonomous_api import _suggest_directory
        result = _suggest_directory("main.py", "import os", ".py")
        assert result == "code/python"

    def test_suggest_directory_markdown(self):
        from api.librarian_autonomous_api import _suggest_directory
        result = _suggest_directory("README.md", "# Readme", ".md")
        assert result == "documentation"

    def test_suggest_directory_csv(self):
        from api.librarian_autonomous_api import _suggest_directory
        result = _suggest_directory("data.csv", "col1,col2", ".csv")
        assert result == "data/csv"

    def test_suggest_directory_readme(self):
        from api.librarian_autonomous_api import _suggest_directory
        result = _suggest_directory("README.txt", "About", ".txt")
        assert result == "documentation"

    def test_suggest_directory_unknown(self):
        from api.librarian_autonomous_api import _suggest_directory
        result = _suggest_directory("weird.xyz", "blah", ".xyz")
        assert result is None

    def test_resolve_safe_path_escape(self):
        from api.librarian_autonomous_api import _resolve_safe_path
        with pytest.raises(Exception):
            _resolve_safe_path("../../etc/passwd")

    def test_format_bytes(self):
        from api.librarian_autonomous_api import _read_file_preview
        from pathlib import Path
        result = _read_file_preview(Path("/nonexistent/file.txt"))
        assert "[Unable to read" in result or "[Binary" in result or result == ""


class TestKimiClient:
    """Test Kimi LLM client initialization."""

    def test_kimi_client_init(self):
        from llm_orchestrator.kimi_client import KimiLLMClient
        client = KimiLLMClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert "moonshot" in client.base_url
        assert client.default_model is not None

    def test_kimi_client_no_key(self):
        from llm_orchestrator.kimi_client import KimiLLMClient
        client = KimiLLMClient(api_key="")
        assert client.is_running() is False


class TestLLMFactory:
    """Test LLM factory supports all providers with governance wrapping."""

    def test_factory_default(self):
        from llm_orchestrator.factory import get_llm_client
        client = get_llm_client()
        assert client is not None

    def test_factory_kimi(self):
        from llm_orchestrator.factory import get_llm_client
        from llm_orchestrator.governance_wrapper import GovernanceAwareLLM
        client = get_llm_client(provider="kimi")
        assert isinstance(client, GovernanceAwareLLM)
        assert hasattr(client, '_inner')

    def test_factory_openai(self):
        from llm_orchestrator.factory import get_llm_client
        from llm_orchestrator.governance_wrapper import GovernanceAwareLLM
        client = get_llm_client(provider="openai")
        assert isinstance(client, GovernanceAwareLLM)

    def test_get_kimi_client(self):
        from llm_orchestrator.factory import get_kimi_client
        from llm_orchestrator.governance_wrapper import GovernanceAwareLLM
        client = get_kimi_client()
        assert isinstance(client, GovernanceAwareLLM)

    def test_raw_client_no_wrapper(self):
        from llm_orchestrator.factory import get_raw_client
        from llm_orchestrator.governance_wrapper import GovernanceAwareLLM
        client = get_raw_client()
        assert not isinstance(client, GovernanceAwareLLM)

    def test_governance_prefix_builds(self):
        from llm_orchestrator.governance_wrapper import build_governance_prefix
        prefix = build_governance_prefix()
        assert isinstance(prefix, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
