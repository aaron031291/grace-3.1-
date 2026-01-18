"""
Tests for LLM API integrations in AI Comparison Benchmark.

Tests each LLM provider's API integration:
- Claude (Anthropic)
- ChatGPT (OpenAI)
- Gemini (Google)
- DeepSeek
- Cursor (IDE-only)

Uses mocked requests to avoid actual API calls.
"""

import pytest
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, 'backend')

from benchmarking.ai_comparison_benchmark import (
    AIComparisonBenchmark,
    AIProvider,
    BenchmarkTask,
    AIResponse
)


@pytest.fixture
def benchmark():
    """Create benchmark instance with all providers enabled."""
    return AIComparisonBenchmark(
        enable_claude=True,
        enable_gemini=True,
        enable_cursor=True,
        enable_chatgpt=True,
        enable_deepseek=True
    )


@pytest.fixture
def sample_task():
    """Create a sample benchmark task."""
    return BenchmarkTask(
        task_id="test_task_001",
        task_type="code_generation",
        prompt="Write a Python function that adds two numbers.",
        context={}
    )


class TestClaudeAPI:
    """Tests for Claude (Anthropic) API integration."""

    @pytest.mark.asyncio
    async def test_claude_sends_correct_request_format(self, benchmark, sample_task):
        """Test that Claude API receives correctly formatted request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": "def add(a, b): return a + b"}],
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 10, "output_tokens": 20}
        }

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("requests.post", return_value=mock_response) as mock_post:
                result = await benchmark._run_claude(sample_task)

                mock_post.assert_called_once()
                call_args = mock_post.call_args

                assert call_args[0][0] == "https://api.anthropic.com/v1/messages"
                assert call_args[1]["headers"]["x-api-key"] == "test-key"
                assert call_args[1]["headers"]["anthropic-version"] == "2023-06-01"
                assert call_args[1]["headers"]["content-type"] == "application/json"

                payload = call_args[1]["json"]
                assert payload["model"] == "claude-3-5-sonnet-20241022"
                assert payload["max_tokens"] == 4096
                assert payload["messages"][0]["role"] == "user"
                assert payload["messages"][0]["content"] == sample_task.prompt
                assert call_args[1]["timeout"] == 120

    @pytest.mark.asyncio
    async def test_claude_parses_response_correctly(self, benchmark, sample_task):
        """Test that Claude API response is parsed correctly."""
        expected_text = "def add(a, b):\n    return a + b"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"text": expected_text}],
            "model": "claude-3-5-sonnet-20241022",
            "usage": {"input_tokens": 10, "output_tokens": 20}
        }

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("requests.post", return_value=mock_response):
                result = await benchmark._run_claude(sample_task)

                assert result is not None
                assert result.provider == AIProvider.CLAUDE
                assert result.task_id == sample_task.task_id
                assert result.response == expected_text
                assert result.error is None
                assert result.metadata["model"] == "claude-3-5-sonnet-20241022"
                assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_claude_handles_missing_api_key(self, benchmark, sample_task):
        """Test that Claude returns appropriate error when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            result = await benchmark._run_claude(sample_task)

            assert result is not None
            assert result.provider == AIProvider.CLAUDE
            assert result.error == "ANTHROPIC_API_KEY not configured"
            assert result.response == ""
            assert result.metadata.get("api_integration") == "missing_key"

    @pytest.mark.asyncio
    async def test_claude_handles_api_error(self, benchmark, sample_task):
        """Test that Claude handles API errors gracefully."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "invalid-key"}):
            with patch("requests.post", return_value=mock_response):
                result = await benchmark._run_claude(sample_task)

                assert result is not None
                assert result.provider == AIProvider.CLAUDE
                assert "API error 401" in result.error
                assert result.response == ""


class TestChatGPTAPI:
    """Tests for ChatGPT (OpenAI) API integration."""

    @pytest.mark.asyncio
    async def test_chatgpt_sends_correct_request_format(self, benchmark, sample_task):
        """Test that ChatGPT API receives correctly formatted request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "def add(a, b): return a + b"}}],
            "model": "gpt-4o",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20}
        }

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("requests.post", return_value=mock_response) as mock_post:
                result = await benchmark._run_chatgpt(sample_task)

                mock_post.assert_called_once()
                call_args = mock_post.call_args

                assert call_args[0][0] == "https://api.openai.com/v1/chat/completions"
                assert call_args[1]["headers"]["Authorization"] == "Bearer test-key"
                assert call_args[1]["headers"]["Content-Type"] == "application/json"

                payload = call_args[1]["json"]
                assert payload["model"] == "gpt-4o"
                assert payload["max_tokens"] == 4096
                assert payload["messages"][0]["role"] == "user"
                assert payload["messages"][0]["content"] == sample_task.prompt
                assert call_args[1]["timeout"] == 120

    @pytest.mark.asyncio
    async def test_chatgpt_parses_response_correctly(self, benchmark, sample_task):
        """Test that ChatGPT API response is parsed correctly."""
        expected_text = "def add(a, b):\n    return a + b"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": expected_text}}],
            "model": "gpt-4o",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20}
        }

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("requests.post", return_value=mock_response):
                result = await benchmark._run_chatgpt(sample_task)

                assert result is not None
                assert result.provider == AIProvider.CHATGPT
                assert result.task_id == sample_task.task_id
                assert result.response == expected_text
                assert result.error is None
                assert result.metadata["model"] == "gpt-4o"
                assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_chatgpt_handles_missing_api_key(self, benchmark, sample_task):
        """Test that ChatGPT returns appropriate error when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPENAI_API_KEY", None)
            result = await benchmark._run_chatgpt(sample_task)

            assert result is not None
            assert result.provider == AIProvider.CHATGPT
            assert result.error == "OPENAI_API_KEY not configured"
            assert result.response == ""
            assert result.metadata.get("api_integration") == "missing_key"


class TestGeminiAPI:
    """Tests for Gemini (Google) API integration."""

    @pytest.mark.asyncio
    async def test_gemini_sends_correct_request_format(self, benchmark, sample_task):
        """Test that Gemini API receives correctly formatted request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "def add(a, b): return a + b"}]}}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20}
        }

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            with patch("requests.post", return_value=mock_response) as mock_post:
                result = await benchmark._run_gemini(sample_task)

                mock_post.assert_called_once()
                call_args = mock_post.call_args

                expected_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=test-key"
                assert call_args[0][0] == expected_url

                payload = call_args[1]["json"]
                assert payload["contents"][0]["parts"][0]["text"] == sample_task.prompt
                assert payload["generationConfig"]["maxOutputTokens"] == 4096
                assert call_args[1]["timeout"] == 120

    @pytest.mark.asyncio
    async def test_gemini_parses_response_correctly(self, benchmark, sample_task):
        """Test that Gemini API response is parsed correctly."""
        expected_text = "def add(a, b):\n    return a + b"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": expected_text}]}}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20}
        }

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            with patch("requests.post", return_value=mock_response):
                result = await benchmark._run_gemini(sample_task)

                assert result is not None
                assert result.provider == AIProvider.GEMINI
                assert result.task_id == sample_task.task_id
                assert result.response == expected_text
                assert result.error is None
                assert result.metadata["model"] == "gemini-pro"
                assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_gemini_handles_missing_api_key(self, benchmark, sample_task):
        """Test that Gemini returns appropriate error when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("GOOGLE_API_KEY", None)
            result = await benchmark._run_gemini(sample_task)

            assert result is not None
            assert result.provider == AIProvider.GEMINI
            assert result.error == "GOOGLE_API_KEY not configured"
            assert result.response == ""
            assert result.metadata.get("api_integration") == "missing_key"


class TestDeepSeekAPI:
    """Tests for DeepSeek API integration."""

    @pytest.mark.asyncio
    async def test_deepseek_sends_correct_request_format(self, benchmark, sample_task):
        """Test that DeepSeek API receives correctly formatted request."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "def add(a, b): return a + b"}}],
            "model": "deepseek-coder",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20}
        }

        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
            with patch("requests.post", return_value=mock_response) as mock_post:
                result = await benchmark._run_deepseek(sample_task)

                mock_post.assert_called_once()
                call_args = mock_post.call_args

                assert call_args[0][0] == "https://api.deepseek.com/v1/chat/completions"
                assert call_args[1]["headers"]["Authorization"] == "Bearer test-key"
                assert call_args[1]["headers"]["Content-Type"] == "application/json"

                payload = call_args[1]["json"]
                assert payload["model"] == "deepseek-coder"
                assert payload["max_tokens"] == 4096
                assert payload["messages"][0]["role"] == "user"
                assert payload["messages"][0]["content"] == sample_task.prompt
                assert call_args[1]["timeout"] == 120

    @pytest.mark.asyncio
    async def test_deepseek_parses_response_correctly(self, benchmark, sample_task):
        """Test that DeepSeek API response is parsed correctly."""
        expected_text = "def add(a, b):\n    return a + b"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": expected_text}}],
            "model": "deepseek-coder",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20}
        }

        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
            with patch("requests.post", return_value=mock_response):
                result = await benchmark._run_deepseek(sample_task)

                assert result is not None
                assert result.provider == AIProvider.DEEPSEEK
                assert result.task_id == sample_task.task_id
                assert result.response == expected_text
                assert result.error is None
                assert result.metadata["model"] == "deepseek-coder"
                assert result.duration_ms > 0

    @pytest.mark.asyncio
    async def test_deepseek_handles_missing_api_key(self, benchmark, sample_task):
        """Test that DeepSeek returns appropriate error when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DEEPSEEK_API_KEY", None)
            result = await benchmark._run_deepseek(sample_task)

            assert result is not None
            assert result.provider == AIProvider.DEEPSEEK
            assert result.error == "DEEPSEEK_API_KEY not configured"
            assert result.response == ""
            assert result.metadata.get("api_integration") == "missing_key"


class TestTimeoutHandling:
    """Tests for timeout handling across all LLM APIs."""

    @pytest.mark.asyncio
    async def test_claude_handles_timeout(self, benchmark, sample_task):
        """Test that Claude handles timeouts gracefully."""
        import requests as req
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("requests.post", side_effect=req.Timeout("Connection timed out")):
                result = await benchmark._run_claude(sample_task)

                assert result is not None
                assert result.provider == AIProvider.CLAUDE
                assert result.error == "Request timeout"
                assert result.response == ""

    @pytest.mark.asyncio
    async def test_chatgpt_handles_timeout(self, benchmark, sample_task):
        """Test that ChatGPT handles timeouts gracefully."""
        import requests as req
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("requests.post", side_effect=req.Timeout("Connection timed out")):
                result = await benchmark._run_chatgpt(sample_task)

                assert result is not None
                assert result.provider == AIProvider.CHATGPT
                assert result.error == "Request timeout"
                assert result.response == ""

    @pytest.mark.asyncio
    async def test_gemini_handles_timeout(self, benchmark, sample_task):
        """Test that Gemini handles timeouts gracefully."""
        import requests as req
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            with patch("requests.post", side_effect=req.Timeout("Connection timed out")):
                result = await benchmark._run_gemini(sample_task)

                assert result is not None
                assert result.provider == AIProvider.GEMINI
                assert result.error == "Request timeout"
                assert result.response == ""

    @pytest.mark.asyncio
    async def test_deepseek_handles_timeout(self, benchmark, sample_task):
        """Test that DeepSeek handles timeouts gracefully."""
        import requests as req
        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
            with patch("requests.post", side_effect=req.Timeout("Connection timed out")):
                result = await benchmark._run_deepseek(sample_task)

                assert result is not None
                assert result.provider == AIProvider.DEEPSEEK
                assert result.error == "Request timeout"
                assert result.response == ""


class TestCursorIDE:
    """Tests for Cursor (IDE-only) integration."""

    @pytest.mark.asyncio
    async def test_cursor_returns_not_available_message(self, benchmark, sample_task):
        """Test that Cursor returns appropriate 'not available' message."""
        result = await benchmark._run_cursor(sample_task)

        assert result is not None
        assert result.provider == AIProvider.CURSOR
        assert result.task_id == sample_task.task_id
        assert result.response == ""
        assert result.duration_ms == 0
        assert "IDE-only" in result.error
        assert "no public api" in result.error.lower()
        assert result.metadata.get("api_integration") == "not_available"
        assert "Cursor IDE" in result.metadata.get("reason", "")
        assert "workaround" in result.metadata


class TestEmptyResponses:
    """Tests for handling empty or malformed API responses."""

    @pytest.mark.asyncio
    async def test_claude_handles_empty_content(self, benchmark, sample_task):
        """Test Claude handles empty content array."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [],
            "model": "claude-3-5-sonnet-20241022"
        }

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            with patch("requests.post", return_value=mock_response):
                result = await benchmark._run_claude(sample_task)

                assert result is not None
                assert result.response == ""
                assert result.error is None

    @pytest.mark.asyncio
    async def test_chatgpt_handles_empty_choices(self, benchmark, sample_task):
        """Test ChatGPT handles empty choices array."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [],
            "model": "gpt-4o"
        }

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("requests.post", return_value=mock_response):
                result = await benchmark._run_chatgpt(sample_task)

                assert result is not None
                assert result.response == ""
                assert result.error is None

    @pytest.mark.asyncio
    async def test_gemini_handles_empty_candidates(self, benchmark, sample_task):
        """Test Gemini handles empty candidates array."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": []
        }

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}):
            with patch("requests.post", return_value=mock_response):
                result = await benchmark._run_gemini(sample_task)

                assert result is not None
                assert result.response == ""
                assert result.error is None

    @pytest.mark.asyncio
    async def test_deepseek_handles_empty_choices(self, benchmark, sample_task):
        """Test DeepSeek handles empty choices array."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [],
            "model": "deepseek-coder"
        }

        with patch.dict(os.environ, {"DEEPSEEK_API_KEY": "test-key"}):
            with patch("requests.post", return_value=mock_response):
                result = await benchmark._run_deepseek(sample_task)

                assert result is not None
                assert result.response == ""
                assert result.error is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
