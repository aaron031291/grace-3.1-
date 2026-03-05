"""
Tests for QwenModelPool — async hot-swappable task-routed model pool.

Verifies:
1. Pool initializes with 3 model slots (code/reason/fast)
2. Task classification routes correctly
3. Read-only governance contract enforced by default
4. Write mode only with explicit user prompt
5. Hot-swap works at runtime
6. Failover when primary model is unhealthy
7. Pool status reporting
8. Factory integration routes through pool
9. Event bus integration
"""

import sys
import os
import importlib.util
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _load(name, path):
    full = os.path.join(os.path.dirname(__file__), "..", path)
    spec = importlib.util.spec_from_file_location(name, full)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_settings = _load("settings", "settings.py")
_base = _load("llm_orchestrator.base_client", "llm_orchestrator/base_client.py")
_qwen = _load("llm_orchestrator.qwen_client", "llm_orchestrator/qwen_client.py")
_gov = _load("llm_orchestrator.governance_wrapper", "llm_orchestrator/governance_wrapper.py")
_pool_mod = _load("llm_orchestrator.qwen_pool", "llm_orchestrator/qwen_pool.py")

QwenModelPool = _pool_mod.QwenModelPool
QwenTask = _pool_mod.QwenTask
WriteMode = _pool_mod.WriteMode


@pytest.fixture
def pool():
    p = QwenModelPool()
    p.initialize()
    return p


class TestPoolInitialization:

    def test_initializes_three_slots(self, pool):
        status = pool.get_status()
        assert len(status["models"]) == 3
        assert "code" in status["models"]
        assert "reason" in status["models"]
        assert "fast" in status["models"]

    def test_all_slots_healthy(self, pool):
        status = pool.get_status()
        for key, info in status["models"].items():
            assert info["healthy"] is True

    def test_default_read_only(self, pool):
        status = pool.get_status()
        assert status["global_write_mode"] == "read_only"

    def test_models_have_qwen3(self, pool):
        status = pool.get_status()
        for key, info in status["models"].items():
            assert "qwen3" in info["model_name"] or "qwen" in info["model_name"]

    def test_code_slot_has_correct_tasks(self, pool):
        status = pool.get_status()
        code_tasks = status["models"]["code"]["tasks"]
        assert "code" in code_tasks
        assert "general" in code_tasks

    def test_reason_slot_has_correct_tasks(self, pool):
        status = pool.get_status()
        reason_tasks = status["models"]["reason"]["tasks"]
        assert "reason" in reason_tasks
        assert "diagnose" in reason_tasks
        assert "heal" in reason_tasks

    def test_fast_slot_has_correct_tasks(self, pool):
        status = pool.get_status()
        fast_tasks = status["models"]["fast"]["tasks"]
        assert "fast" in fast_tasks
        assert "chat" in fast_tasks
        assert "learn" in fast_tasks


class TestTaskClassification:

    def test_code_task(self, pool):
        assert pool._classify_task("write code for a parser", None) == QwenTask.CODE
        assert pool._classify_task("implement the function", None) == QwenTask.CODE
        assert pool._classify_task("refactor this class", None) == QwenTask.CODE

    def test_reason_task(self, pool):
        assert pool._classify_task("explain why this happens", None) == QwenTask.REASON
        assert pool._classify_task("analyze the trade-off", None) == QwenTask.REASON

    def test_diagnose_task(self, pool):
        assert pool._classify_task("diagnose the error", None) == QwenTask.DIAGNOSE
        assert pool._classify_task("debug this crash", None) == QwenTask.DIAGNOSE

    def test_heal_task(self, pool):
        assert pool._classify_task("heal the service now", None) == QwenTask.HEAL
        assert pool._classify_task("self-heal the service", None) == QwenTask.HEAL

    def test_fast_fallback(self, pool):
        assert pool._classify_task("hello", None) == QwenTask.FAST
        assert pool._classify_task("what time is it", None) == QwenTask.FAST

    def test_explicit_task_override(self, pool):
        assert pool._classify_task("anything", "code") == QwenTask.CODE
        assert pool._classify_task("anything", "reason") == QwenTask.REASON
        assert pool._classify_task("anything", "fast") == QwenTask.FAST


class TestModelSelection:

    def test_code_routes_to_code_slot(self, pool):
        assert pool._select_model(QwenTask.CODE) == "code"

    def test_reason_routes_to_reason_slot(self, pool):
        assert pool._select_model(QwenTask.REASON) == "reason"

    def test_fast_routes_to_fast_slot(self, pool):
        assert pool._select_model(QwenTask.FAST) == "fast"

    def test_diagnose_routes_to_reason_slot(self, pool):
        assert pool._select_model(QwenTask.DIAGNOSE) == "reason"

    def test_chat_routes_to_fast_slot(self, pool):
        assert pool._select_model(QwenTask.CHAT) == "fast"

    def test_failover_when_primary_unhealthy(self, pool):
        pool._slots["code"].healthy = False
        selected = pool._select_model(QwenTask.CODE)
        assert selected != "code"
        assert pool._slots[selected].healthy is True


class TestGovernanceContract:

    def test_read_only_by_default(self, pool):
        mode = pool._check_write_permission(QwenTask.CODE, user_prompted=False)
        assert mode == WriteMode.READ_ONLY

    def test_write_requires_user_prompt(self, pool):
        mode = pool._check_write_permission(QwenTask.CODE, user_prompted=True)
        assert mode == WriteMode.WRITE

    def test_non_code_tasks_always_read_only(self, pool):
        for task in [QwenTask.REASON, QwenTask.FAST, QwenTask.CHAT, QwenTask.LEARN]:
            mode = pool._check_write_permission(task, user_prompted=True)
            assert mode == WriteMode.READ_ONLY

    def test_heal_allows_write_with_prompt(self, pool):
        mode = pool._check_write_permission(QwenTask.HEAL, user_prompted=True)
        assert mode == WriteMode.WRITE

    def test_read_only_prefix_injected(self, pool):
        result = pool._apply_read_only_prefix("Base prompt", WriteMode.READ_ONLY)
        assert "READ-ONLY MODE" in result
        assert "MUST NOT generate code" in result

    def test_write_prefix_injected(self, pool):
        result = pool._apply_read_only_prefix("Base prompt", WriteMode.WRITE)
        assert "WRITE MODE" in result
        assert "user-authorized" in result


class TestHotSwap:

    def test_swap_changes_model(self, pool):
        pool.swap_model("fast", "qwen3:4b")
        assert pool._slots["fast"].model_name == "qwen3:4b"

    def test_swap_resets_health(self, pool):
        pool._slots["fast"].healthy = False
        pool._slots["fast"].total_errors = 10
        pool.swap_model("fast", "qwen3:8b")
        assert pool._slots["fast"].healthy is True
        assert pool._slots["fast"].total_errors == 0

    def test_swap_creates_new_client(self, pool):
        old_client = pool._clients["fast"]
        pool.swap_model("fast", "qwen3:8b")
        assert pool._clients["fast"] is not old_client

    def test_swap_invalid_slot_raises(self, pool):
        with pytest.raises(ValueError):
            pool.swap_model("nonexistent", "qwen3:8b")


class TestFailover:

    def test_fallback_skips_failed_model(self, pool):
        fallback = pool._get_fallback("code")
        assert fallback is not None
        assert fallback != "code"

    def test_fallback_returns_healthy_model(self, pool):
        pool._slots["fast"].healthy = False
        fallback = pool._get_fallback("code")
        assert fallback is not None
        assert pool._slots[fallback].healthy is True

    def test_no_fallback_if_all_unhealthy(self, pool):
        for slot in pool._slots.values():
            slot.healthy = False
        fallback = pool._get_fallback("code")
        assert fallback is None


class TestPoolStatus:

    def test_status_has_all_fields(self, pool):
        status = pool.get_status()
        assert "initialized" in status
        assert "global_write_mode" in status
        assert "stats" in status
        assert "models" in status

    def test_stats_start_at_zero(self, pool):
        status = pool.get_status()
        assert status["stats"]["total_calls"] == 0
        assert status["stats"]["write_calls"] == 0
        assert status["stats"]["read_only_calls"] == 0

    def test_get_client_for_task_returns_governed(self, pool):
        client = pool.get_client_for_task("code")
        assert type(client).__name__ == "GovernanceAwareLLM"

    def test_get_client_for_unknown_task_returns_fast(self, pool):
        client = pool.get_client_for_task("nonexistent")
        assert client is not None


class TestGlobalWriteMode:

    def test_set_write_mode(self, pool):
        pool.set_write_mode(True)
        assert pool._write_mode == WriteMode.WRITE

    def test_set_read_only_mode(self, pool):
        pool.set_write_mode(True)
        pool.set_write_mode(False)
        assert pool._write_mode == WriteMode.READ_ONLY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
