"""
Tests for Unified Memory facade.
"""
import pytest
import json


class TestUnifiedMemoryImport:
    def test_import_unified_memory(self):
        from core.memory.unified_memory import UnifiedMemory
        assert UnifiedMemory is not None

    def test_import_learning_example(self):
        from core.memory.unified_memory import LearningExample
        assert LearningExample is not None

    def test_import_episode(self):
        from core.memory.unified_memory import Episode
        assert Episode is not None


class TestJsonSerialization:
    def test_to_json_str_with_dict(self):
        from cognitive.learning_memory import _to_json_str
        result = _to_json_str({"key": "value"})
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed["key"] == "value"

    def test_to_json_str_with_none(self):
        from cognitive.learning_memory import _to_json_str
        result = _to_json_str(None)
        assert result == "{}"

    def test_to_json_str_with_string(self):
        from cognitive.learning_memory import _to_json_str
        result = _to_json_str("already a string")
        assert result == "already a string"

    def test_to_json_str_with_nested_dict(self):
        from cognitive.learning_memory import _to_json_str
        result = _to_json_str({"a": {"b": [1, 2, 3]}})
        parsed = json.loads(result)
        assert parsed["a"]["b"] == [1, 2, 3]

    def test_from_json_str_with_dict(self):
        from cognitive.learning_memory import _from_json_str
        result = _from_json_str('{"key": "value"}')
        assert result["key"] == "value"

    def test_from_json_str_with_none(self):
        from cognitive.learning_memory import _from_json_str
        result = _from_json_str(None)
        assert result == {}

    def test_from_json_str_with_dict_passthrough(self):
        from cognitive.learning_memory import _from_json_str
        result = _from_json_str({"key": "value"})
        assert result["key"] == "value"
