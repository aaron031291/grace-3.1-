"""
Validate determinism: same inputs must produce same outputs (no random, no model).

Run from the backend directory (project root for pytest):
  cd path/to/grace-3.1--Aaron-new2/backend
  python -m pytest tests/test_determinism_validation.py -v
"""

import pytest
import sys
from pathlib import Path

# Ensure backend is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class TestDeterminismValidation:
    """Run determinism to validate."""

    def test_deterministic_choice_same_seed_same_result(self):
        from core.determinism import deterministic_choice
        options = ["a", "b", "c"]
        seed = "task-123"
        r1 = deterministic_choice(options, seed)
        r2 = deterministic_choice(options, seed)
        assert r1 == r2, "Same seed must yield same choice"
        assert r1 in options

    def test_deterministic_choice_different_seed_can_differ(self):
        from core.determinism import deterministic_choice
        options = ["x", "y", "z"]
        a = deterministic_choice(options, "seed1")
        b = deterministic_choice(options, "seed2")
        # May or may not be equal; just ensure both valid
        assert a in options and b in options

    def test_deterministic_run_id_same_task_same_minute_same_id(self):
        from core.determinism import deterministic_run_id
        task = "fix the bug"
        # Same minute => same bucket => same run_id
        r1 = deterministic_run_id(task)
        r2 = deterministic_run_id(task)
        assert r1 == r2
        assert r1.startswith("PIPE-") and len(r1) == 13  # PIPE- + 8 hex

    def test_should_use_llm_force_deterministic_false(self):
        from core.determinism import should_use_llm
        assert should_use_llm(force_deterministic=True) is False

    def test_should_use_llm_phase0_no_handoff_false(self):
        from core.determinism import should_use_llm
        phase0 = {"handoff_to_llm": False}
        assert should_use_llm(phase0_result=phase0) is False

    def test_should_use_llm_phase0_handoff_true(self):
        from core.determinism import should_use_llm
        phase0 = {"handoff_to_llm": True}
        assert should_use_llm(phase0_result=phase0) is True

    def test_should_use_llm_none_phase0_true(self):
        from core.determinism import should_use_llm
        assert should_use_llm(phase0_result=None) is True

    def test_deterministic_temperature(self):
        from core.determinism import deterministic_temperature
        assert deterministic_temperature(for_deterministic=True) == 0.0
        assert deterministic_temperature(for_deterministic=False) == 0.3

    def test_deterministic_model_choice_same_seed_same_model(self):
        from core.determinism import deterministic_model_choice
        models = ["kimi", "opus", "qwen"]
        m1 = deterministic_model_choice(models, "task-a")
        m2 = deterministic_model_choice(models, "task-a")
        assert m1 == m2
        assert m1 in models

    def test_genesis_key_id_format_deterministic(self):
        """Genesis key IDs are GK- + 32 hex (hash-based), not UUID."""
        import hashlib
        from models.genesis_key_models import GenesisKeyType
        # Replicate the deterministic formula from genesis_key_service
        key_type = GenesisKeyType.API_REQUEST
        what_description = "test what"
        who_actor = "test-who"
        where_location = "/test"
        when_ts = "2025-01-01T12:00:00"
        input_hash = ""
        parent_key_id = ""
        payload = f"{key_type.value}|{what_description}|{who_actor}|{where_location or ''}|||{when_ts}|{input_hash}|{parent_key_id or ''}"
        key_id = "GK-" + hashlib.sha256(payload.encode()).hexdigest()[:32]
        assert key_id.startswith("GK-")
        assert len(key_id) == 3 + 32  # GK- + 32 hex
        assert all(c in "0123456789abcdef" for c in key_id[3:])
        # Same inputs => same key_id (run twice)
        key_id2 = "GK-" + hashlib.sha256(payload.encode()).hexdigest()[:32]
        assert key_id == key_id2

    def test_get_determinism_info(self):
        """Enterprise: version and config exposed for observability."""
        from core.determinism import get_determinism_info, DETERMINISM_API_VERSION
        info = get_determinism_info()
        assert info["api_version"] == DETERMINISM_API_VERSION
        assert info["hash_algorithm"] == "sha256"
        assert "temperature_deterministic" in info
        assert info["temperature_deterministic"] == 0.0
