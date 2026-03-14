"""Tests for backend/core/safety.py — all 4 safety subsystems."""

import importlib
import importlib.util
import json
import pathlib
import time
from unittest import mock

import pytest

# ── Direct import to avoid transitive dependency issues ──────────
_spec = importlib.util.spec_from_file_location(
    "safety",
    str(pathlib.Path(__file__).resolve().parents[3] / "backend" / "core" / "safety.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


# ═══════════════════════════════════════════════════════════════════
#  Fixtures
# ═══════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_budget():
    """Reset the module-level _budget dict before every test."""
    _mod._budget["total_calls"] = 0
    _mod._budget["total_tokens_est"] = 0
    _mod._budget["blocked"] = 0
    _mod._budget["window_start"] = time.time()
    _mod._budget["limit_calls_per_hour"] = 500
    _mod._budget["limit_tokens_per_hour"] = 500000


@pytest.fixture(autouse=True)
def reset_rollback_stack():
    """Clear the rollback stack before every test."""
    _mod._rollback_stack.clear()


@pytest.fixture()
def ledger_tmp(tmp_path):
    """Redirect provenance ledger to a temp file."""
    original = _mod.LEDGER_PATH
    _mod.LEDGER_PATH = tmp_path / "test_ledger.jsonl"
    _mod._prev_hash = "0" * 64
    yield
    _mod.LEDGER_PATH = original
    _mod._prev_hash = "0" * 64


# ═══════════════════════════════════════════════════════════════════
#  2. SECURITY SCANNING
# ═══════════════════════════════════════════════════════════════════

class TestSecurityScanning:
    """Most critical — tests for scan_code_security."""

    def test_clean_code_is_safe(self):
        result = _mod.scan_code_security("x = 1 + 2\nprint(x)\n")
        assert result["safe"] is True
        assert result["blocked"] is False
        assert result["findings"] == []
        assert result["total"] == 0

    def test_exec_is_blocked(self):
        code = "exec(user_input)"
        result = _mod.scan_code_security(code, "gen.py")
        assert result["blocked"] is True
        assert result["safe"] is False
        assert any(f["pattern"] == "exec(" for f in result["findings"])
        critical = [f for f in result["findings"] if f["severity"] == "critical"]
        assert len(critical) >= 1

    def test_subprocess_call_not_blocked_but_found(self):
        code = "subprocess.call(['ls'])"
        result = _mod.scan_code_security(code, "script.py")
        assert result["blocked"] is False
        assert result["safe"] is False
        finding = result["findings"][0]
        assert finding["severity"] == "high"
        assert finding["pattern"] == "subprocess.call"

    def test_yaml_load_medium_severity(self):
        code = "data = yaml.load(open('f.yml'))"
        result = _mod.scan_code_security(code)
        assert result["safe"] is False
        assert result["blocked"] is False
        finding = result["findings"][0]
        assert finding["severity"] == "medium"
        assert finding["pattern"] == "yaml.load("

    def test_comment_lines_are_skipped(self):
        code = "# exec(something_bad)\nprint('ok')"
        result = _mod.scan_code_security(code)
        assert result["safe"] is True
        assert result["findings"] == []

    def test_multiple_patterns_multiple_findings(self):
        code = "exec(x)\neval(y)\nos.system('rm -rf /')"
        result = _mod.scan_code_security(code, "bad.py")
        assert result["total"] >= 3
        assert result["blocked"] is True
        patterns_found = {f["pattern"] for f in result["findings"]}
        assert "exec(" in patterns_found
        assert "eval(" in patterns_found
        assert "os.system(" in patterns_found

    def test_finding_structure(self):
        code = "exec('hi')"
        result = _mod.scan_code_security(code, "test.py")
        finding = result["findings"][0]
        expected_keys = {"line", "pattern", "type", "severity", "code", "file"}
        assert expected_keys.issubset(finding.keys())
        assert finding["line"] == 1
        assert finding["file"] == "test.py"

    def test_dangerous_patterns_list_not_empty(self):
        assert len(_mod.DANGEROUS_PATTERNS) > 0
        for pat, vtype, sev in _mod.DANGEROUS_PATTERNS:
            assert isinstance(pat, str)
            assert sev in ("critical", "high", "medium")


# ═══════════════════════════════════════════════════════════════════
#  3. BUDGET CIRCUIT BREAKER
# ═══════════════════════════════════════════════════════════════════

class TestBudgetCircuitBreaker:

    def test_fresh_budget_allows(self):
        assert _mod.check_budget() is True

    def test_record_usage_increments(self):
        _mod.record_usage(tokens=100)
        assert _mod._budget["total_calls"] == 1
        assert _mod._budget["total_tokens_est"] == 100

    def test_exceeding_call_limit_blocks(self):
        _mod._budget["total_calls"] = 500
        assert _mod.check_budget() is False
        assert _mod._budget["blocked"] == 1

    def test_exceeding_token_limit_blocks(self):
        _mod._budget["total_tokens_est"] = 500000
        assert _mod.check_budget() is False

    def test_window_reset_after_3600s(self):
        _mod._budget["total_calls"] = 499
        old_start = time.time() - 3601
        _mod._budget["window_start"] = old_start
        assert _mod.check_budget() is True
        assert _mod._budget["total_calls"] == 0
        assert _mod._budget["total_tokens_est"] == 0

    def test_set_budget_limits_changes_limits(self):
        result = _mod.set_budget_limits(calls_per_hour=100, tokens_per_hour=10000)
        assert _mod._budget["limit_calls_per_hour"] == 100
        assert _mod._budget["limit_tokens_per_hour"] == 10000
        assert "remaining_calls" in result

    def test_get_budget_status_fields(self):
        _mod.record_usage(tokens=50)
        status = _mod.get_budget_status()
        assert status["total_calls"] == 1
        assert status["total_tokens_est"] == 50
        assert "remaining_calls" in status
        assert "remaining_tokens" in status
        assert "window_elapsed_minutes" in status
        assert status["remaining_calls"] == 499
        assert status["remaining_tokens"] == 500000 - 50

    def test_blocked_counter_increments_on_repeated_blocks(self):
        _mod._budget["total_calls"] = 500
        _mod.check_budget()
        _mod.check_budget()
        assert _mod._budget["blocked"] == 2


# ═══════════════════════════════════════════════════════════════════
#  4. PROVENANCE LEDGER
# ═══════════════════════════════════════════════════════════════════

class TestProvenanceLedger:

    def test_record_creates_entry_with_hash(self, ledger_tmp):
        result = _mod.record_provenance(
            action="generate", content_hash="abc123", model="gpt-4",
        )
        assert "hash" in result
        assert "seq" in result
        assert len(result["hash"]) == 64

    def test_sequential_entries_form_chain(self, ledger_tmp):
        r1 = _mod.record_provenance(action="a", content_hash="h1")
        r2 = _mod.record_provenance(action="b", content_hash="h2")
        lines = _mod.LEDGER_PATH.read_text().strip().split("\n")
        e1 = json.loads(lines[0])
        e2 = json.loads(lines[1])
        assert e1["prev_hash"] == "0" * 64
        assert e2["prev_hash"] == r1["hash"]

    def test_verify_ledger_valid(self, ledger_tmp):
        _mod.record_provenance(action="x", content_hash="h1")
        _mod.record_provenance(action="y", content_hash="h2")
        result = _mod.verify_ledger()
        assert result["valid"] is True
        assert result["entries"] == 2

    def test_verify_ledger_empty_file(self, ledger_tmp):
        result = _mod.verify_ledger()
        assert result["valid"] is True
        assert result["entries"] == 0

    def test_get_ledger_entries_returns_list(self, ledger_tmp):
        _mod.record_provenance(action="a", content_hash="h1")
        entries = _mod.get_ledger_entries(limit=10)
        assert isinstance(entries, list)
        assert len(entries) == 1
        assert entries[0]["action"] == "a"

    def test_tampered_ledger_detected(self, ledger_tmp):
        _mod.record_provenance(action="a", content_hash="h1")
        _mod.record_provenance(action="b", content_hash="h2")
        # Tamper with the first entry's hash
        lines = _mod.LEDGER_PATH.read_text().strip().split("\n")
        e1 = json.loads(lines[0])
        e1["hash"] = "bad" * 21 + "x"
        lines[0] = json.dumps(e1)
        _mod.LEDGER_PATH.write_text("\n".join(lines) + "\n")
        result = _mod.verify_ledger()
        assert result["valid"] is False


# ═══════════════════════════════════════════════════════════════════
#  1. MULTI-STEP ROLLBACK
# ═══════════════════════════════════════════════════════════════════

class TestRollback:

    def test_list_snapshots_returns_list(self):
        result = _mod.list_snapshots()
        assert isinstance(result, list)
        assert len(result) == 0

    def test_snapshot_and_list(self):
        sid = _mod.snapshot_state(label="test-snap")
        assert sid.startswith("SNAP-")
        snaps = _mod.list_snapshots()
        assert len(snaps) == 1
        assert snaps[0]["id"] == sid
        assert snaps[0]["label"] == "test-snap"

    def test_rollback_empty_stack_returns_error(self):
        result = _mod.rollback_to()
        assert "error" in result

    def test_rollback_missing_id_returns_error(self):
        _mod.snapshot_state(label="x")
        result = _mod.rollback_to("SNAP-nonexistent")
        assert "error" in result
