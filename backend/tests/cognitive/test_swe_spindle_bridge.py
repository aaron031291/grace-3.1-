"""Tests for the SWE → Spindle Bridge (Phase 4 wiring)."""

import pytest
from unittest.mock import MagicMock, patch

from cognitive.swe_spindle_bridge import (
    SWESpindleBridge,
    TranslationResult,
    get_swe_spindle_bridge,
)


@pytest.fixture
def bridge():
    return SWESpindleBridge()


def _make_example(code: str, trust: float = 0.85, times_validated: int = 2, ex_id: int = 1):
    """Create a mock LearningExample with Python code in expected_output."""
    import json
    ex = MagicMock()
    ex.id = ex_id
    ex.trust_score = trust
    ex.times_validated = times_validated
    ex.times_referenced = 0
    ex.last_used = None
    ex.input_context = json.dumps({"raw": "SWE pattern"})
    ex.expected_output = json.dumps({"raw": code})
    ex.actual_output = None
    return ex


class TestCodeExtraction:
    def test_extracts_python_from_raw_field(self, bridge):
        code = "def hello():\n    return 42"
        ex = _make_example(code)
        result = bridge._extract_code_from_example(ex)
        assert result is not None
        assert "def hello" in result

    def test_extracts_from_markdown_fenced_block(self, bridge):
        import json
        md = 'Some explanation\n\n```python\ndef foo():\n    pass\n```\n\nMore text'
        ex = _make_example("not code here")
        ex.expected_output = json.dumps({"raw": md})
        result = bridge._extract_code_from_example(ex)
        assert result is not None
        assert "def foo" in result

    def test_returns_none_for_non_code(self, bridge):
        ex = _make_example("This is just plain English text with no code.")
        result = bridge._extract_code_from_example(ex)
        assert result is None

    def test_returns_none_for_invalid_syntax(self, bridge):
        ex = _make_example("def broken(:\n    not valid python ===")
        result = bridge._extract_code_from_example(ex)
        assert result is None


class TestTranslation:
    @patch("cognitive.braille_translator.BrailleTranslator")
    def test_successful_translation(self, MockTranslator, bridge):
        """Valid code + deterministic translation → is_valid=True."""
        mock_instance = MagicMock()
        mock_instance.translate_code.return_value = "●●●●●● 1mm □\nhello\n●●●●●● 3mm ○\n42"
        MockTranslator.return_value = mock_instance

        code = "def hello():\n    return 42"
        ex = _make_example(code)

        result = bridge._translate_and_validate(ex, code)

        assert result.is_valid
        assert result.token_count > 0
        assert bridge._stats.total_translations_succeeded == 1

    @patch("cognitive.braille_translator.BrailleTranslator")
    def test_nondeterministic_translation_rejected(self, MockTranslator, bridge):
        """If two translations differ → rejected."""
        call_count = [0]
        def side_effect(code):
            call_count[0] += 1
            return f"output_{call_count[0]}"

        mock_instance = MagicMock()
        mock_instance.translate_code.side_effect = side_effect
        MockTranslator.return_value = mock_instance

        code = "def hello():\n    return 42"
        ex = _make_example(code)

        result = bridge._translate_and_validate(ex, code)
        assert not result.is_valid
        assert "Non-deterministic" in result.validation_error

    def test_empty_code_rejected(self, bridge):
        ex = _make_example("")
        result = bridge._translate_and_validate(ex, "")
        assert not result.is_valid


class TestExampleHash:
    def test_same_example_same_hash(self, bridge):
        ex = _make_example("def foo(): pass", ex_id=42)
        h1 = bridge._example_hash(ex)
        h2 = bridge._example_hash(ex)
        assert h1 == h2

    def test_different_examples_different_hash(self, bridge):
        ex1 = _make_example("def foo(): pass", ex_id=1)
        ex2 = _make_example("def bar(): pass", ex_id=2)
        h1 = bridge._example_hash(ex1)
        h2 = bridge._example_hash(ex2)
        assert h1 != h2


class TestStats:
    def test_initial_stats(self, bridge):
        stats = bridge.get_stats()
        assert stats["running"] is False
        assert stats["deterministic_paths"] == 0
        assert stats["llm_bypass_ratio"] == 0.0

    def test_translation_history_empty(self, bridge):
        assert bridge.get_translation_history() == []


class TestSingleton:
    def test_singleton_returns_same_instance(self):
        import cognitive.swe_spindle_bridge as mod
        mod._bridge = None  # reset
        b1 = get_swe_spindle_bridge()
        b2 = get_swe_spindle_bridge()
        assert b1 is b2
        mod._bridge = None  # cleanup


if __name__ == "__main__":
    pytest.main(["-v", __file__])
