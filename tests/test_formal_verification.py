"""Tests for executable invariants system."""

import pytest
from backend.cognitive.executable_invariants import (
    global_registry,
    InvariantRegistry,
    ExecutableInvariant,
    InvariantType,
    not_none,
    not_null,
    non_empty,
    is_string,
    is_dict,
    is_list,
    is_positive,
    is_non_negative,
    has_keys,
    type_is,
    length_at_least,
)


class TestNotNoneInvariant:
    """Tests for not_none and not_null invariants."""

    def test_passes_when_result_is_not_none(self):
        passed, error = not_none.check({"result": "value"})
        assert passed is True
        assert error is None

    def test_fails_when_result_is_none(self):
        passed, error = not_none.check({"result": None})
        assert passed is False
        assert error is not None

    def test_fails_when_result_key_missing(self):
        passed, error = not_none.check({})
        assert passed is False

    def test_not_null_alias_passes(self):
        passed, error = not_null.check({"result": 42})
        assert passed is True
        assert error is None

    def test_not_null_alias_fails(self):
        passed, error = not_null.check({"result": None})
        assert passed is False

    def test_uses_output_key_as_fallback(self):
        passed, error = not_none.check({"output": "value"})
        assert passed is True


class TestNonEmptyInvariant:
    """Tests for non_empty invariant."""

    def test_passes_for_non_empty_string(self):
        passed, error = non_empty.check({"result": "hello"})
        assert passed is True
        assert error is None

    def test_fails_for_empty_string(self):
        passed, error = non_empty.check({"result": ""})
        assert passed is False

    def test_passes_for_non_empty_list(self):
        passed, error = non_empty.check({"result": [1, 2, 3]})
        assert passed is True

    def test_fails_for_empty_list(self):
        passed, error = non_empty.check({"result": []})
        assert passed is False

    def test_passes_for_non_empty_dict(self):
        passed, error = non_empty.check({"result": {"key": "value"}})
        assert passed is True

    def test_fails_for_empty_dict(self):
        passed, error = non_empty.check({"result": {}})
        assert passed is False

    def test_fails_for_none(self):
        passed, error = non_empty.check({"result": None})
        assert passed is False


class TestTypeInvariants:
    """Tests for is_string, is_dict, is_list invariants."""

    def test_is_string_passes_for_string(self):
        passed, error = is_string.check({"result": "hello"})
        assert passed is True
        assert error is None

    def test_is_string_fails_for_int(self):
        passed, error = is_string.check({"result": 42})
        assert passed is False

    def test_is_string_fails_for_list(self):
        passed, error = is_string.check({"result": [1, 2]})
        assert passed is False

    def test_is_dict_passes_for_dict(self):
        passed, error = is_dict.check({"result": {"a": 1}})
        assert passed is True
        assert error is None

    def test_is_dict_fails_for_string(self):
        passed, error = is_dict.check({"result": "not a dict"})
        assert passed is False

    def test_is_dict_fails_for_list(self):
        passed, error = is_dict.check({"result": [1, 2, 3]})
        assert passed is False

    def test_is_list_passes_for_list(self):
        passed, error = is_list.check({"result": [1, 2, 3]})
        assert passed is True
        assert error is None

    def test_is_list_fails_for_string(self):
        passed, error = is_list.check({"result": "not a list"})
        assert passed is False

    def test_is_list_fails_for_dict(self):
        passed, error = is_list.check({"result": {"a": 1}})
        assert passed is False


class TestIsPositiveInvariant:
    """Tests for is_positive invariant."""

    def test_passes_for_positive_int(self):
        passed, error = is_positive.check({"result": 5})
        assert passed is True
        assert error is None

    def test_passes_for_positive_float(self):
        passed, error = is_positive.check({"result": 3.14})
        assert passed is True

    def test_fails_for_zero(self):
        passed, error = is_positive.check({"result": 0})
        assert passed is False

    def test_fails_for_negative(self):
        passed, error = is_positive.check({"result": -5})
        assert passed is False

    def test_fails_for_none(self):
        passed, error = is_positive.check({"result": None})
        assert passed is False

    def test_fails_for_non_numeric(self):
        passed, error = is_positive.check({"result": "5"})
        assert passed is False


class TestIsNonNegativeInvariant:
    """Tests for is_non_negative invariant."""

    def test_passes_for_zero(self):
        passed, error = is_non_negative.check({"result": 0})
        assert passed is True
        assert error is None

    def test_passes_for_positive(self):
        passed, error = is_non_negative.check({"result": 10})
        assert passed is True

    def test_passes_for_positive_float(self):
        passed, error = is_non_negative.check({"result": 0.5})
        assert passed is True

    def test_fails_for_negative(self):
        passed, error = is_non_negative.check({"result": -1})
        assert passed is False

    def test_fails_for_negative_float(self):
        passed, error = is_non_negative.check({"result": -0.001})
        assert passed is False

    def test_fails_for_none(self):
        passed, error = is_non_negative.check({"result": None})
        assert passed is False


class TestHasKeysInvariant:
    """Tests for has_keys parameterized invariant."""

    def test_passes_with_all_keys(self):
        inv = has_keys("a", "b")
        passed, error = inv.check({"result": {"a": 1, "b": 2}})
        assert passed is True
        assert error is None

    def test_passes_with_extra_keys(self):
        inv = has_keys("a", "b")
        passed, error = inv.check({"result": {"a": 1, "b": 2, "c": 3}})
        assert passed is True

    def test_fails_without_required_keys(self):
        inv = has_keys("a", "b")
        passed, error = inv.check({"result": {"a": 1}})
        assert passed is False

    def test_fails_for_empty_dict(self):
        inv = has_keys("a", "b")
        passed, error = inv.check({"result": {}})
        assert passed is False

    def test_fails_for_non_dict(self):
        inv = has_keys("a", "b")
        passed, error = inv.check({"result": "not a dict"})
        assert passed is False

    def test_invariant_name_includes_keys(self):
        inv = has_keys("x", "y", "z")
        assert "x" in inv.name
        assert "y" in inv.name
        assert "z" in inv.name


class TestTypeIsInvariant:
    """Tests for type_is parameterized invariant."""

    def test_passes_for_correct_type(self):
        inv = type_is(int)
        passed, error = inv.check({"result": 42})
        assert passed is True
        assert error is None

    def test_fails_for_wrong_type(self):
        inv = type_is(int)
        passed, error = inv.check({"result": "42"})
        assert passed is False

    def test_works_with_str(self):
        inv = type_is(str)
        passed, _ = inv.check({"result": "hello"})
        assert passed is True
        passed, _ = inv.check({"result": 123})
        assert passed is False

    def test_works_with_list(self):
        inv = type_is(list)
        passed, _ = inv.check({"result": [1, 2, 3]})
        assert passed is True
        passed, _ = inv.check({"result": (1, 2, 3)})
        assert passed is False

    def test_invariant_name_includes_type(self):
        inv = type_is(dict)
        assert "dict" in inv.name


class TestLengthAtLeastInvariant:
    """Tests for length_at_least parameterized invariant."""

    def test_passes_for_exact_length(self):
        inv = length_at_least(3)
        passed, error = inv.check({"result": "abc"})
        assert passed is True
        assert error is None

    def test_passes_for_greater_length(self):
        inv = length_at_least(3)
        passed, _ = inv.check({"result": "abcdef"})
        assert passed is True

    def test_fails_for_less_length(self):
        inv = length_at_least(3)
        passed, _ = inv.check({"result": "ab"})
        assert passed is False

    def test_works_with_list(self):
        inv = length_at_least(2)
        passed, _ = inv.check({"result": [1, 2, 3]})
        assert passed is True
        passed, _ = inv.check({"result": [1]})
        assert passed is False

    def test_works_with_dict(self):
        inv = length_at_least(2)
        passed, _ = inv.check({"result": {"a": 1, "b": 2}})
        assert passed is True
        passed, _ = inv.check({"result": {"a": 1}})
        assert passed is False

    def test_fails_for_none(self):
        inv = length_at_least(1)
        passed, _ = inv.check({"result": None})
        assert passed is False

    def test_fails_for_non_sized(self):
        inv = length_at_least(1)
        passed, _ = inv.check({"result": 42})
        assert passed is False

    def test_invariant_name_includes_length(self):
        inv = length_at_least(5)
        assert "5" in inv.name


class TestInvariantRegistry:
    """Tests for the InvariantRegistry."""

    def test_invariants_registered_at_module_load(self):
        assert global_registry.get("not_none") is not None
        assert global_registry.get("not_null") is not None
        assert global_registry.get("non_empty") is not None
        assert global_registry.get("is_string") is not None
        assert global_registry.get("is_dict") is not None
        assert global_registry.get("is_list") is not None
        assert global_registry.get("is_positive") is not None
        assert global_registry.get("is_non_negative") is not None

    def test_can_look_up_by_name(self):
        inv = global_registry.get("not_none")
        assert inv is not None
        assert isinstance(inv, ExecutableInvariant)
        assert inv.name == "not_none"

    def test_check_via_registry_by_name(self):
        passed, error = global_registry.check("not_none", {"result": "value"})
        assert passed is True

        passed, error = global_registry.check("not_none", {"result": None})
        assert passed is False

    def test_returns_error_for_unknown_invariant(self):
        passed, error = global_registry.check("unknown_invariant", {})
        assert passed is False
        assert "not found" in error

    def test_register_and_unregister(self):
        registry = InvariantRegistry()
        inv = has_keys("test_key")
        
        registry.register(inv)
        assert registry.get(inv.name) is not None
        
        result = registry.unregister(inv.name)
        assert result is True
        assert registry.get(inv.name) is None

    def test_list_invariants(self):
        invariant_names = global_registry.list_invariants()
        assert "not_none" in invariant_names
        assert "is_string" in invariant_names
        assert "is_positive" in invariant_names

    def test_list_invariants_by_type(self):
        postconditions = global_registry.list_invariants(InvariantType.POSTCONDITION)
        assert "not_none" in postconditions
        assert "is_string" in postconditions

    def test_check_multiple(self):
        results = global_registry.check_multiple(
            ["not_none", "is_string"],
            {"result": "hello"}
        )
        assert len(results) == 2
        assert all(passed for _, passed, _ in results)

        results = global_registry.check_multiple(
            ["not_none", "is_string"],
            {"result": 42}
        )
        not_none_result = next(r for r in results if r[0] == "not_none")
        is_string_result = next(r for r in results if r[0] == "is_string")
        assert not_none_result[1] is True
        assert is_string_result[1] is False
