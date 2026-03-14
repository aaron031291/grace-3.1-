"""
Tests for backend.coding_agent modules — real logic tests with mocked externals.
"""
import ast
import asyncio
import threading
from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest


# ═══════════════════════════════════════════════════════════════════════════
# deterministic_gate.py
# ═══════════════════════════════════════════════════════════════════════════

class TestGateReport:
    def test_as_prompt_context_clean(self):
        from backend.coding_agent.deterministic_gate import GateReport
        r = GateReport()
        ctx = r.as_prompt_context()
        assert "DETERMINISTIC PRE-ANALYSIS" in ctx
        assert "Risk score: 0.00" in ctx

    def test_as_prompt_context_with_findings(self):
        from backend.coding_agent.deterministic_gate import GateReport
        r = GateReport(
            syntax_valid=False,
            syntax_errors=["Line 5: invalid syntax"],
            imports_found=["os", "sys"],
            high_risk_patterns=["os.remove"],
            risk_score=0.5,
        )
        ctx = r.as_prompt_context()
        assert "SYNTAX ERRORS" in ctx
        assert "os, sys" in ctx
        assert "HIGH RISK" in ctx
        assert "os.remove" in ctx


class TestDeterministicGate:
    def test_analyze_clean_code(self):
        from backend.coding_agent.deterministic_gate import DeterministicGate
        gate = DeterministicGate()
        report = gate.analyze(task="Add logging", existing_code="def hello():\n    return 1\n")
        assert report.syntax_valid is True
        assert report.risk_score == 0.0
        assert report.gate_passed is True
        assert "hello()" in report.functions_found[0]

    def test_analyze_syntax_error(self):
        from backend.coding_agent.deterministic_gate import DeterministicGate
        gate = DeterministicGate()
        report = gate.analyze(task="Fix bug", existing_code="def broken(\n")
        assert report.syntax_valid is False
        assert len(report.syntax_errors) >= 1
        assert report.risk_score >= 0.2  # syntax-invalid penalty

    def test_analyze_high_risk_patterns(self):
        from backend.coding_agent.deterministic_gate import DeterministicGate
        gate = DeterministicGate()
        code = "import os, subprocess\nos.remove('/tmp/x')\nshutil.rmtree('/var')\neval('1+1')\nos.system('rm -rf /')\n"
        report = gate.analyze(task="cleanup", existing_code=code)
        assert "os.remove" in report.high_risk_patterns
        assert "shutil.rmtree" in report.high_risk_patterns
        assert "eval(" in report.high_risk_patterns
        assert "os.system" in report.high_risk_patterns
        assert report.risk_score >= 0.9  # 4 * 0.3 = 1.2 capped to 1.0
        assert report.gate_passed is False

    def test_analyze_medium_risk_patterns(self):
        from backend.coding_agent.deterministic_gate import DeterministicGate
        gate = DeterministicGate()
        report = gate.analyze(task="save data", existing_code="f = open('x.txt')\nf.write('hi')\n")
        assert "open(" in report.medium_risk_patterns
        assert "write(" in report.medium_risk_patterns
        assert report.risk_score == pytest.approx(0.2, abs=0.01)

    def test_analyze_extracts_classes_and_imports(self):
        from backend.coding_agent.deterministic_gate import DeterministicGate
        gate = DeterministicGate()
        code = "import json\nfrom pathlib import Path\nclass Foo:\n    pass\n"
        report = gate.analyze(task="refactor", existing_code=code)
        assert "json" in report.imports_found
        assert "pathlib" in report.imports_found
        assert "Foo" in report.classes_found

    def test_recommendations_for_destructive_ops(self):
        from backend.coding_agent.deterministic_gate import DeterministicGate
        gate = DeterministicGate()
        report = gate.analyze(task="delete files", existing_code="os.remove('x')")
        assert any("dry_run" in r for r in report.recommendations)

    def test_recommendations_session_usage(self):
        from backend.coding_agent.deterministic_gate import DeterministicGate
        gate = DeterministicGate()
        report = gate.analyze(task="update db", existing_code="session.commit()")
        assert any("session_scope" in r for r in report.recommendations)

    @patch("backend.coding_agent.deterministic_gate.DeterministicGate._search_kb", return_value=[])
    def test_kb_search_called(self, mock_kb):
        from backend.coding_agent.deterministic_gate import DeterministicGate
        gate = DeterministicGate()
        gate.analyze(task="test task")
        mock_kb.assert_called_once()


class TestGetGateSingleton:
    def test_returns_same_instance(self):
        import backend.coding_agent.deterministic_gate as mod
        mod._gate = None
        g1 = mod.get_gate()
        g2 = mod.get_gate()
        assert g1 is g2
        mod._gate = None  # cleanup


# ═══════════════════════════════════════════════════════════════════════════
# verification_pass.py
# ═══════════════════════════════════════════════════════════════════════════

class TestVerificationPass:
    def test_empty_code_rejected(self):
        from backend.coding_agent.verification_pass import VerificationPass
        vp = VerificationPass()
        r = vp.verify(code="", task="fix bug")
        assert r.accepted is False
        assert r.trust_score == 0.0
        assert "empty_or_trivial_output" in r.flags

    def test_trivial_code_rejected(self):
        from backend.coding_agent.verification_pass import VerificationPass
        vp = VerificationPass()
        r = vp.verify(code="   x   ", task="fix bug")
        assert r.accepted is False

    @patch("backend.coding_agent.verification_pass.VerificationPass._record_verification")
    @patch("backend.coding_agent.verification_pass.VerificationPass._rag_check")
    def test_clean_code_accepted(self, mock_rag, mock_rec):
        from backend.coding_agent.verification_pass import VerificationPass
        vp = VerificationPass()
        code = "def greet(name):\n    return f'Hello {name}'\n"
        r = vp.verify(code=code, task="add greet function")
        assert r.accepted is True
        # base 0.75 + 0.10 clean bonus = 0.85
        assert r.trust_score == pytest.approx(0.85, abs=0.01)

    @patch("backend.coding_agent.verification_pass.VerificationPass._record_verification")
    @patch("backend.coding_agent.verification_pass.VerificationPass._rag_check")
    def test_syntax_error_drops_trust(self, mock_rag, mock_rec):
        from backend.coding_agent.verification_pass import VerificationPass
        vp = VerificationPass()
        r = vp.verify(code="def broken(:\n    pass\n", task="fix")
        assert r.accepted is False
        assert r.trust_score < 0.65  # below TRUST_THRESHOLD

    @patch("backend.coding_agent.verification_pass.VerificationPass._record_verification")
    @patch("backend.coding_agent.verification_pass.VerificationPass._rag_check")
    def test_dangerous_pattern_reduces_trust(self, mock_rag, mock_rec):
        from backend.coding_agent.verification_pass import VerificationPass
        vp = VerificationPass()
        code = "result = eval(user_input)\nprint(result)\n"
        r = vp.verify(code=code, task="process input")
        assert any("dangerous_pattern" in f for f in r.flags)
        # 0.75 - 0.25 = 0.50, below threshold
        assert r.trust_score < 0.65

    @patch("backend.coding_agent.verification_pass.VerificationPass._record_verification")
    @patch("backend.coding_agent.verification_pass.VerificationPass._rag_check")
    def test_hallucination_signal_detected(self, mock_rag, mock_rec):
        from backend.coding_agent.verification_pass import VerificationPass
        vp = VerificationPass()
        code = "from nonexistent import magic\nresult = magic.run()\n"
        r = vp.verify(code=code, task="generate code")
        assert any("hallucination_signal" in f for f in r.flags)

    @patch("backend.coding_agent.verification_pass.VerificationPass._record_verification")
    @patch("backend.coding_agent.verification_pass.VerificationPass._rag_check")
    def test_ghost_contradiction_flagged(self, mock_rag, mock_rec):
        from backend.coding_agent.verification_pass import VerificationPass
        vp = VerificationPass()
        code = "def critical_handler():\n    return 'overridden'\n"
        ghost = "Session notes: DO_NOT_MODIFY_DEF_critical_handler is protected."
        r = vp.verify(code=code, task="update handler", ghost_context=ghost)
        assert len(r.contradictions) == 1
        assert "critical_handler" in r.contradictions[0]

    @patch("backend.coding_agent.verification_pass.VerificationPass._record_verification")
    @patch("backend.coding_agent.verification_pass.VerificationPass._rag_check")
    def test_stub_only_flagged(self, mock_rag, mock_rec):
        from backend.coding_agent.verification_pass import VerificationPass
        vp = VerificationPass()
        code = "def stub():\n    pass\n"
        r = vp.verify(code=code, task="implement feature")
        assert "stub_only_no_implementation" in r.flags
        assert r.trust_score < 0.65


class TestVerificationResult:
    def test_summary_accepted(self):
        from backend.coding_agent.verification_pass import VerificationResult
        r = VerificationResult(accepted=True, trust_score=0.9)
        assert "ACCEPTED" in r.summary()

    def test_summary_rejected(self):
        from backend.coding_agent.verification_pass import VerificationResult
        r = VerificationResult(accepted=False, trust_score=0.3, flags=["syntax_error"])
        assert "REJECTED" in r.summary()


# ═══════════════════════════════════════════════════════════════════════════
# task_queue.py
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _reset_task_queue():
    """Reset module-level state between tests."""
    import backend.coding_agent.task_queue as tq
    original_queue = tq._queue[:]
    original_handlers = tq._handlers.copy()
    tq._queue.clear()
    tq._handlers.clear()
    yield
    tq._queue[:] = original_queue
    tq._handlers.clear()
    tq._handlers.update(original_handlers)


class TestTaskQueueSubmit:
    @patch("backend.coding_agent.task_queue._record_submission")
    @patch("backend.coding_agent.task_queue._persist_task")
    def test_submit_returns_task_id(self, mock_persist, mock_rec):
        from backend.coding_agent.task_queue import submit
        tid = submit("fix_error", "Fix the import bug", priority=3)
        assert tid.startswith("task_")
        assert "fix_erro" in tid

    @patch("backend.coding_agent.task_queue._record_submission")
    @patch("backend.coding_agent.task_queue._persist_task")
    def test_submit_adds_to_queue_sorted(self, mock_persist, mock_rec):
        import backend.coding_agent.task_queue as tq
        from backend.coding_agent.task_queue import submit
        submit("a", "low priority", priority=9)
        submit("b", "high priority", priority=1)
        assert tq._queue[0]["priority"] == 1
        assert tq._queue[1]["priority"] == 9


class TestTaskQueuePoll:
    @patch("backend.coding_agent.task_queue._record_submission")
    @patch("backend.coding_agent.task_queue._persist_task")
    def test_poll_returns_pending_task(self, mock_persist, mock_rec):
        from backend.coding_agent.task_queue import submit, poll
        submit("test", "do something", priority=5)
        task = poll()
        assert task is not None
        assert task["status"] == "running"
        assert task["attempts"] == 1

    def test_poll_empty_queue(self):
        from backend.coding_agent.task_queue import poll
        assert poll() is None

    @patch("backend.coding_agent.task_queue._record_submission")
    @patch("backend.coding_agent.task_queue._persist_task")
    def test_poll_skips_completed(self, mock_persist, mock_rec):
        import backend.coding_agent.task_queue as tq
        from backend.coding_agent.task_queue import submit, poll
        submit("test", "done task", priority=5)
        tq._queue[0]["status"] = "completed"
        assert poll() is None


class TestTaskQueueComplete:
    @patch("backend.coding_agent.task_queue._record_completion")
    @patch("backend.coding_agent.task_queue._record_submission")
    @patch("backend.coding_agent.task_queue._persist_task")
    def test_complete_success(self, mock_persist, mock_rec_s, mock_rec_c):
        import backend.coding_agent.task_queue as tq
        from backend.coding_agent.task_queue import submit, poll, complete
        tid = submit("test", "task", priority=5)
        poll()
        complete(tid, success=True, result={"code": "ok"})
        assert tq._queue[0]["status"] == "completed"

    @patch("backend.coding_agent.task_queue._record_completion")
    @patch("backend.coding_agent.task_queue._record_submission")
    @patch("backend.coding_agent.task_queue._persist_task")
    def test_complete_failure_retries(self, mock_persist, mock_rec_s, mock_rec_c):
        import backend.coding_agent.task_queue as tq
        from backend.coding_agent.task_queue import submit, poll, complete
        tid = submit("test", "retry me", priority=5)
        poll()  # attempt 1
        complete(tid, success=False, error="boom")
        # Should be re-queued as pending since attempts (1) < MAX_RETRIES (3)
        assert tq._queue[0]["status"] == "pending"


class TestTaskQueueStatus:
    @patch("backend.coding_agent.task_queue._record_submission")
    @patch("backend.coding_agent.task_queue._persist_task")
    def test_get_status(self, mock_persist, mock_rec):
        from backend.coding_agent.task_queue import submit, get_status
        submit("a", "t1")
        submit("b", "t2")
        status = get_status()
        assert status["queue_depth"] == 2
        assert status["by_status"]["pending"] == 2

    @patch("backend.coding_agent.task_queue._record_submission")
    @patch("backend.coding_agent.task_queue._persist_task")
    def test_get_swarm_status(self, mock_persist, mock_rec):
        from backend.coding_agent.task_queue import submit, get_swarm_status
        submit("fix", "fix the bug")
        active = get_swarm_status()
        assert len(active) == 1
        assert active[0]["status"] == "pending"
        assert active[0]["progress"] == 0


class TestRegisterHandler:
    def test_register_and_lookup(self):
        import backend.coding_agent.task_queue as tq
        from backend.coding_agent.task_queue import register_handler
        handler = lambda t: {"ok": True}
        register_handler("custom", handler)
        assert tq._handlers["custom"] is handler


# ═══════════════════════════════════════════════════════════════════════════
# fix_applier.py
# ═══════════════════════════════════════════════════════════════════════════

class TestFixApplier:
    @patch("backend.coding_agent.fix_applier.FixApplier._record")
    def test_rejects_syntax_invalid_code(self, mock_rec, tmp_path):
        from backend.coding_agent.fix_applier import FixApplier
        fa = FixApplier()
        target = tmp_path / "target.py"
        target.write_text("original = 1\n")
        with patch.object(fa, "_resolve_safe_path", return_value=target):
            r = fa.apply(file_path=str(target), generated_code="def broken(:\n    pass\n")
        assert r.success is False
        assert "Syntax error" in r.error

    @patch("backend.coding_agent.fix_applier.FixApplier._record")
    def test_rejects_non_python_file(self, mock_rec):
        from backend.coding_agent.fix_applier import FixApplier, _SAFE_BASE_DIR
        fa = FixApplier()
        target = str(_SAFE_BASE_DIR / "readme.md")
        r = fa.apply(file_path=target, generated_code="print('hi')\n")
        assert r.success is False
        assert r.error  # path validation fails

    @patch("backend.coding_agent.fix_applier.FixApplier._record")
    def test_rejects_nonexistent_without_allow_create(self, mock_rec):
        from backend.coding_agent.fix_applier import FixApplier, _SAFE_BASE_DIR
        fa = FixApplier()
        target = str(_SAFE_BASE_DIR / "does_not_exist_xyz.py")
        r = fa.apply(file_path=target, generated_code="x = 1\n", allow_create=False)
        assert r.success is False

    @patch("backend.coding_agent.fix_applier.FixApplier._hot_reload", return_value=True)
    @patch("backend.coding_agent.fix_applier.FixApplier._record")
    def test_apply_creates_new_file(self, mock_rec, mock_reload, tmp_path):
        from backend.coding_agent.fix_applier import FixApplier
        fa = FixApplier()
        target = tmp_path / "new_module.py"
        # Patch _resolve_safe_path to allow our tmp_path
        with patch.object(fa, "_resolve_safe_path", return_value=target):
            r = fa.apply(
                file_path=str(target),
                generated_code="x = 42\n",
                allow_create=True,
            )
        assert r.success is True
        assert r.lines_written == 1
        assert target.read_text() == "x = 42\n"

    @patch("backend.coding_agent.fix_applier.FixApplier._hot_reload", return_value=True)
    @patch("backend.coding_agent.fix_applier.FixApplier._record")
    def test_apply_backs_up_existing(self, mock_rec, mock_reload, tmp_path):
        from backend.coding_agent.fix_applier import FixApplier
        fa = FixApplier()
        target = tmp_path / "existing.py"
        target.write_text("old = 1\n")
        backup_file = tmp_path / "existing.py.bak"
        with patch.object(fa, "_resolve_safe_path", return_value=target), \
             patch.object(fa, "_backup", return_value=backup_file):
            r = fa.apply(file_path=str(target), generated_code="new = 2\n")
        assert r.success is True
        assert target.read_text() == "new = 2\n"
        assert r.backup_path == str(backup_file)


class TestApplyResult:
    def test_summary_success(self):
        from backend.coding_agent.fix_applier import ApplyResult
        r = ApplyResult(success=True, file_path="x.py", lines_written=10, module_reloaded=True)
        assert "Applied" in r.summary()

    def test_summary_rollback(self):
        from backend.coding_agent.fix_applier import ApplyResult
        r = ApplyResult(success=False, file_path="x.py", rolled_back=True, error="bad")
        assert "Rolled back" in r.summary()

    def test_summary_failure(self):
        from backend.coding_agent.fix_applier import ApplyResult
        r = ApplyResult(success=False, file_path="x.py", error="write failed")
        assert "Failed" in r.summary()


# ═══════════════════════════════════════════════════════════════════════════
# validation_pipeline.py
# ═══════════════════════════════════════════════════════════════════════════

class TestRunStage:
    @pytest.mark.asyncio
    async def test_run_stage_success(self):
        from backend.coding_agent.validation_pipeline import run_stage
        result = await run_stage("unit", 60, "backend/")
        assert result["stage"] == "unit"
        assert result["status"] == "success"
        assert result["score"] == 100

    @pytest.mark.asyncio
    async def test_run_stage_different_names(self):
        from backend.coding_agent.validation_pipeline import run_stage
        result = await run_stage("integration", 180, "frontend/")
        assert result["stage"] == "integration"


class TestRunPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_completes_all_stages(self):
        from backend.coding_agent.validation_pipeline import run_pipeline
        # get_db import inside run_pipeline is wrapped in try/except, so it
        # gracefully falls back to collection=None when mongo isn't available
        summary = await run_pipeline("task_123", "backend/app.py")
        assert summary["task_id"] == "task_123"
        assert summary["status"] == "success"
        assert len(summary["stages"]) == 4

    @pytest.mark.asyncio
    async def test_pipeline_stops_on_failure(self):
        from backend.coding_agent.validation_pipeline import run_pipeline

        async def fail_second(name, timeout, target):
            if name == "integration":
                return {"stage": name, "status": "failed", "error": "boom"}
            return {"stage": name, "status": "success", "score": 100}

        with patch("backend.coding_agent.validation_pipeline.run_stage", side_effect=fail_second):
            summary = await run_pipeline("task_fail", "x.py")
        assert summary["status"] == "failed"
        # Should have unit (success) + integration (failed), then stop
        assert len(summary["stages"]) == 2
