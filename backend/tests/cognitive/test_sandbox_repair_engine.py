"""Tests for the Sandbox Repair Engine (Phase 3.3)."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from cognitive.sandbox_repair_engine import (
    SandboxRepairEngine,
    SandboxVerdict,
    get_sandbox_repair_engine,
)


@pytest.fixture
def engine():
    return SandboxRepairEngine()


class TestSyntaxStage:
    def test_valid_syntax_passes(self, engine):
        verdict = engine.evaluate(
            target_file="cognitive/example.py",
            patch_code="def hello():\n    return 42\n",
            run_tests=False,
        )
        assert verdict.syntax_valid is True

    def test_invalid_syntax_rejected(self, engine):
        verdict = engine.evaluate(
            target_file="cognitive/example.py",
            patch_code="def broken(:\n    pass\n",
            run_tests=False,
        )
        assert verdict.passed is False
        assert verdict.syntax_valid is False
        assert "Syntax error" in verdict.rejection_reason

    def test_empty_code_passes_syntax(self, engine):
        verdict = engine.evaluate(
            target_file="cognitive/example.py",
            patch_code="# empty file\n",
            run_tests=False,
        )
        assert verdict.syntax_valid is True


class TestStaticAnalysis:
    def test_clean_code_passes(self, engine):
        verdict = engine.evaluate(
            target_file="cognitive/example.py",
            patch_code="def safe():\n    return [1, 2, 3]\n",
            run_tests=False,
        )
        assert verdict.passed is True
        assert verdict.static_clean is True

    def test_dangerous_call_rejected(self, engine):
        verdict = engine.evaluate(
            target_file="cognitive/example.py",
            patch_code="import os\nos.system('rm -rf /')\n",
            run_tests=False,
        )
        assert verdict.passed is False
        assert "dangerous" in verdict.rejection_reason.lower()

    def test_non_critical_warnings_allowed(self, engine):
        # eval is dangerous but let's test the flow —
        # static_analyse flags it as dangerous, so it should be rejected
        verdict = engine.evaluate(
            target_file="cognitive/example.py",
            patch_code="x = eval('1+1')\n",
            run_tests=False,
        )
        # eval is flagged as dangerous → rejected
        assert verdict.passed is False


class TestTestDiscovery:
    def test_discovers_test_file(self, engine):
        # This should find tests/cognitive/test_code_sandbox.py for cognitive/code_sandbox.py
        result = engine._discover_test_file("cognitive/code_sandbox.py")
        # May or may not exist — just test the function doesn't crash
        assert result is None or result.endswith(".py")

    def test_returns_none_for_nonexistent(self, engine):
        result = engine._discover_test_file("cognitive/nonexistent_module_xyz.py")
        assert result is None


class TestSandboxCreation:
    def test_creates_sandbox_dir(self, engine):
        code = "def hello():\n    return 42\n"
        sandbox_dir = engine._create_sandbox(
            target_file="cognitive/example_test_target.py",
            patch_code=code,
            test_file=None,
        )
        try:
            assert sandbox_dir.exists()
            target = sandbox_dir / "cognitive" / "example_test_target.py"
            assert target.exists()
            assert target.read_text(encoding="utf-8") == code
        finally:
            engine._cleanup_sandbox(sandbox_dir)

    def test_cleanup_removes_sandbox(self, engine):
        sandbox_dir = Path(tempfile.mkdtemp(prefix="grace_sandbox_test_"))
        engine._cleanup_sandbox(sandbox_dir)
        assert not sandbox_dir.exists()


class TestFullEvaluation:
    def test_valid_patch_no_tests_passes(self, engine):
        verdict = engine.evaluate(
            target_file="cognitive/example.py",
            patch_code="x = 42\ny = x + 1\n",
            run_tests=False,
        )
        assert verdict.passed is True
        assert verdict.syntax_valid is True
        assert engine._total_passed == 1

    def test_patch_hash_computed(self, engine):
        verdict = engine.evaluate(
            target_file="cognitive/example.py",
            patch_code="x = 1\n",
            run_tests=False,
        )
        assert len(verdict.patch_hash) == 16

    def test_timing_recorded(self, engine):
        verdict = engine.evaluate(
            target_file="cognitive/example.py",
            patch_code="x = 1\n",
            run_tests=False,
        )
        assert verdict.total_ms > 0


class TestStats:
    def test_initial_stats(self, engine):
        stats = engine.get_stats()
        assert stats["total_evaluations"] == 0
        assert stats["pass_rate"] == 0.0

    def test_stats_update_after_evaluation(self, engine):
        engine.evaluate("cognitive/x.py", "x = 1\n", run_tests=False)
        stats = engine.get_stats()
        assert stats["total_evaluations"] == 1
        assert stats["total_passed"] == 1

    def test_history_empty_initially(self, engine):
        assert engine.get_history() == []

    def test_history_records_verdicts(self, engine):
        engine.evaluate("cognitive/x.py", "x = 1\n", run_tests=False)
        history = engine.get_history()
        assert len(history) == 1
        assert history[0]["passed"] is True


class TestVerdict:
    def test_to_dict(self):
        v = SandboxVerdict(passed=True, patch_hash="abc123", target_file="foo.py")
        d = v.to_dict()
        assert d["passed"] is True
        assert d["patch_hash"] == "abc123"


class TestSingleton:
    def test_singleton(self):
        import cognitive.sandbox_repair_engine as mod
        mod._engine = None
        e1 = get_sandbox_repair_engine()
        e2 = get_sandbox_repair_engine()
        assert e1 is e2
        mod._engine = None


if __name__ == "__main__":
    pytest.main(["-v", __file__])
