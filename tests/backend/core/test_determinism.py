"""
Comprehensive tests for backend.core.determinism — real-logic tests, no mocking of internals.
"""

import importlib
import importlib.util
import os
import pathlib
import re

import pytest

# ── Direct import to avoid transitive issues ──────────────────────────────────
_spec = importlib.util.spec_from_file_location(
    "determinism",
    str(pathlib.Path(__file__).resolve().parents[3] / "backend" / "core" / "determinism.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

_hash_payload = _mod._hash_payload
_config_float = _mod._config_float
deterministic_choice = _mod.deterministic_choice
deterministic_run_id = _mod.deterministic_run_id
deterministic_trace_id = _mod.deterministic_trace_id
should_use_llm = _mod.should_use_llm
deterministic_temperature = _mod.deterministic_temperature
llm_kwargs_for_determinism = _mod.llm_kwargs_for_determinism
deterministic_model_choice = _mod.deterministic_model_choice
get_determinism_info = _mod.get_determinism_info


# ══════════════════════════════════════════════════════════════════════════════
# 1. _hash_payload
# ══════════════════════════════════════════════════════════════════════════════

class TestHashPayload:
    def test_same_input_same_output(self):
        assert _hash_payload("hello") == _hash_payload("hello")

    def test_different_inputs_different_outputs(self):
        assert _hash_payload("hello") != _hash_payload("world")

    def test_respects_hex_len(self):
        h8 = _hash_payload("test", hex_len=8)
        h16 = _hash_payload("test", hex_len=16)
        h32 = _hash_payload("test", hex_len=32)
        assert len(h8) == 8
        assert len(h16) == 16
        assert len(h32) == 32
        # shorter is a prefix of longer
        assert h32.startswith(h16)
        assert h16.startswith(h8)

    def test_output_is_hex(self):
        h = _hash_payload("anything", hex_len=32)
        assert re.fullmatch(r"[0-9a-f]+", h)

    def test_empty_string(self):
        h = _hash_payload("")
        assert isinstance(h, str) and len(h) == 32

    def test_unicode_input(self):
        h = _hash_payload("日本語テスト")
        assert len(h) == 32

    def test_default_hex_len_is_32(self):
        assert len(_hash_payload("x")) == 32


# ══════════════════════════════════════════════════════════════════════════════
# 2. _config_float
# ══════════════════════════════════════════════════════════════════════════════

class TestConfigFloat:
    def test_returns_default_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("DETERMINISM_TEST_FLOAT", raising=False)
        assert _config_float("DETERMINISM_TEST_FLOAT", 1.5) == 1.5

    def test_reads_env_var(self, monkeypatch):
        monkeypatch.setenv("DETERMINISM_TEST_FLOAT", "2.7")
        assert _config_float("DETERMINISM_TEST_FLOAT", 1.0) == 2.7

    def test_handles_invalid_value_falls_back(self, monkeypatch):
        monkeypatch.setenv("DETERMINISM_TEST_FLOAT", "not_a_number")
        assert _config_float("DETERMINISM_TEST_FLOAT", 9.9) == 9.9

    def test_handles_empty_string(self, monkeypatch):
        monkeypatch.setenv("DETERMINISM_TEST_FLOAT", "")
        assert _config_float("DETERMINISM_TEST_FLOAT", 3.3) == 3.3

    def test_handles_negative(self, monkeypatch):
        monkeypatch.setenv("DETERMINISM_TEST_FLOAT", "-0.5")
        assert _config_float("DETERMINISM_TEST_FLOAT", 1.0) == -0.5

    def test_handles_integer_string(self, monkeypatch):
        monkeypatch.setenv("DETERMINISM_TEST_FLOAT", "7")
        assert _config_float("DETERMINISM_TEST_FLOAT", 0.0) == 7.0


# ══════════════════════════════════════════════════════════════════════════════
# 3. deterministic_choice
# ══════════════════════════════════════════════════════════════════════════════

class TestDeterministicChoice:
    def test_empty_list_returns_none(self):
        assert deterministic_choice([], "seed") is None

    def test_same_seed_same_element(self):
        opts = ["a", "b", "c", "d", "e"]
        r1 = deterministic_choice(opts, "fixed-seed")
        r2 = deterministic_choice(opts, "fixed-seed")
        assert r1 == r2

    def test_different_seeds_can_pick_different_elements(self):
        opts = list(range(100))
        results = {deterministic_choice(opts, f"seed-{i}") for i in range(50)}
        # With 100 options and 50 different seeds, we expect more than 1 unique result
        assert len(results) > 1

    def test_single_element_always_returns_it(self):
        assert deterministic_choice(["only"], "any-seed") == "only"

    def test_result_is_from_options(self):
        opts = ["x", "y", "z"]
        result = deterministic_choice(opts, "test")
        assert result in opts

    def test_none_seed_treated_as_empty(self):
        opts = ["a", "b", "c"]
        r1 = deterministic_choice(opts, None)
        r2 = deterministic_choice(opts, "")
        assert r1 == r2


# ══════════════════════════════════════════════════════════════════════════════
# 4. deterministic_run_id
# ══════════════════════════════════════════════════════════════════════════════

class TestDeterministicRunId:
    def test_prefix(self):
        rid = deterministic_run_id("some-task")
        assert rid.startswith("PIPE-")

    def test_hex_length(self):
        rid = deterministic_run_id("some-task")
        hex_part = rid[len("PIPE-"):]
        assert len(hex_part) == 8
        assert re.fullmatch(r"[0-9a-f]+", hex_part)

    def test_same_task_same_minute_same_id(self):
        # Two calls within the same minute should match
        r1 = deterministic_run_id("task-a", bucket_minutes=True)
        r2 = deterministic_run_id("task-a", bucket_minutes=True)
        assert r1 == r2

    def test_different_tasks_different_ids(self):
        r1 = deterministic_run_id("task-alpha")
        r2 = deterministic_run_id("task-beta")
        assert r1 != r2

    def test_empty_task(self):
        rid = deterministic_run_id("")
        assert rid.startswith("PIPE-")
        assert len(rid) == len("PIPE-") + 8

    def test_none_task(self):
        rid = deterministic_run_id(None)
        assert rid.startswith("PIPE-")


# ══════════════════════════════════════════════════════════════════════════════
# 5. deterministic_trace_id
# ══════════════════════════════════════════════════════════════════════════════

class TestDeterministicTraceId:
    def test_length(self):
        tid = deterministic_trace_id("path", "name")
        assert len(tid) == 16

    def test_hex_format(self):
        tid = deterministic_trace_id("/api", "op")
        assert re.fullmatch(r"[0-9a-f]+", tid)

    def test_same_inputs_same_bucket_same_id(self):
        t1 = deterministic_trace_id("/p", "n", bucket_minutes=True)
        t2 = deterministic_trace_id("/p", "n", bucket_minutes=True)
        assert t1 == t2

    def test_different_path_different_id(self):
        t1 = deterministic_trace_id("/a", "op")
        t2 = deterministic_trace_id("/b", "op")
        assert t1 != t2

    def test_different_name_different_id(self):
        t1 = deterministic_trace_id("/p", "op1")
        t2 = deterministic_trace_id("/p", "op2")
        assert t1 != t2

    def test_defaults_to_empty(self):
        tid = deterministic_trace_id()
        assert len(tid) == 16


# ══════════════════════════════════════════════════════════════════════════════
# 6. should_use_llm
# ══════════════════════════════════════════════════════════════════════════════

class TestShouldUseLlm:
    def test_force_deterministic_returns_false(self):
        assert should_use_llm(force_deterministic=True) is False

    def test_phase0_no_handoff_returns_false(self):
        result = should_use_llm(phase0_result={"handoff_to_llm": False})
        assert result is False

    def test_phase0_handoff_true_returns_true(self):
        result = should_use_llm(phase0_result={"handoff_to_llm": True})
        assert result is True

    def test_default_returns_true(self):
        assert should_use_llm() is True

    def test_phase0_none_returns_true(self):
        assert should_use_llm(phase0_result=None) is True

    def test_phase0_no_key_defaults_to_true(self):
        # dict without handoff_to_llm key → .get defaults to True
        assert should_use_llm(phase0_result={"other_key": 42}) is True

    def test_force_deterministic_overrides_phase0(self):
        result = should_use_llm(
            phase0_result={"handoff_to_llm": True},
            force_deterministic=True,
        )
        assert result is False


# ══════════════════════════════════════════════════════════════════════════════
# 7. deterministic_temperature
# ══════════════════════════════════════════════════════════════════════════════

class TestDeterministicTemperature:
    def test_deterministic_returns_zero(self):
        assert deterministic_temperature(for_deterministic=True) == 0.0

    def test_non_deterministic_returns_cap(self, monkeypatch):
        monkeypatch.delenv("DETERMINISM_TEMPERATURE_CAPPED", raising=False)
        assert deterministic_temperature(for_deterministic=False) == 0.3

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("DETERMINISM_TEMPERATURE_CAPPED", "0.7")
        assert deterministic_temperature(for_deterministic=False) == 0.7

    def test_default_param_is_deterministic(self):
        assert deterministic_temperature() == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# 8. llm_kwargs_for_determinism
# ══════════════════════════════════════════════════════════════════════════════

class TestLlmKwargsForDeterminism:
    def test_deterministic_sets_temp_zero(self):
        result = llm_kwargs_for_determinism(True)
        assert result["temperature"] == 0.0

    def test_non_deterministic_sets_cap(self, monkeypatch):
        monkeypatch.delenv("DETERMINISM_TEMPERATURE_CAPPED", raising=False)
        result = llm_kwargs_for_determinism(False)
        assert result["temperature"] == 0.3

    def test_preserves_other_kwargs(self):
        result = llm_kwargs_for_determinism(True, model="gpt-4", max_tokens=100)
        assert result["model"] == "gpt-4"
        assert result["max_tokens"] == 100
        assert result["temperature"] == 0.0

    def test_overrides_existing_temperature(self):
        result = llm_kwargs_for_determinism(True, temperature=0.9)
        assert result["temperature"] == 0.0

    def test_empty_kwargs(self):
        result = llm_kwargs_for_determinism(True)
        assert result == {"temperature": 0.0}


# ══════════════════════════════════════════════════════════════════════════════
# 9. deterministic_model_choice
# ══════════════════════════════════════════════════════════════════════════════

class TestDeterministicModelChoice:
    def test_empty_list_returns_empty_string(self):
        assert deterministic_model_choice([]) == ""

    def test_deterministic_pick(self):
        models = ["gpt-4", "gpt-3.5", "claude"]
        r1 = deterministic_model_choice(models, "seed-x")
        r2 = deterministic_model_choice(models, "seed-x")
        assert r1 == r2
        assert r1 in models

    def test_different_seeds_can_differ(self):
        models = list(f"model-{i}" for i in range(100))
        results = {deterministic_model_choice(models, f"s{i}") for i in range(50)}
        assert len(results) > 1

    def test_single_model(self):
        assert deterministic_model_choice(["only-model"], "any") == "only-model"

    def test_default_seed(self):
        models = ["a", "b"]
        r1 = deterministic_model_choice(models)
        r2 = deterministic_model_choice(models)
        assert r1 == r2


# ══════════════════════════════════════════════════════════════════════════════
# 10. get_determinism_info
# ══════════════════════════════════════════════════════════════════════════════

class TestGetDeterminismInfo:
    def test_returns_dict(self):
        info = get_determinism_info()
        assert isinstance(info, dict)

    def test_expected_keys(self):
        info = get_determinism_info()
        expected = {
            "api_version",
            "hash_algorithm",
            "encoding",
            "temperature_deterministic",
            "temperature_capped",
        }
        assert expected == set(info.keys())

    def test_api_version(self):
        assert get_determinism_info()["api_version"] == "1.0"

    def test_hash_algorithm(self):
        assert get_determinism_info()["hash_algorithm"] == "sha256"

    def test_encoding(self):
        assert get_determinism_info()["encoding"] == "utf-8"

    def test_temperature_deterministic_value(self):
        assert get_determinism_info()["temperature_deterministic"] == 0.0

    def test_temperature_capped_default(self, monkeypatch):
        monkeypatch.delenv("DETERMINISM_TEMPERATURE_CAPPED", raising=False)
        assert get_determinism_info()["temperature_capped"] == 0.3

    def test_temperature_capped_env_override(self, monkeypatch):
        monkeypatch.setenv("DETERMINISM_TEMPERATURE_CAPPED", "0.5")
        assert get_determinism_info()["temperature_capped"] == 0.5
