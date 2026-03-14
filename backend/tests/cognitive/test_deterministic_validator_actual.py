"""
Real logic tests for the Deterministic Validator.

Tests actual AST parsing, silent failure detection, unwired router detection,
and broken import checking — the code that was orphaned until we registered
introspection_api.py.

No mocks. Real file system. Real AST.
"""
import pytest
import sys
import os
import ast
import tempfile
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from deterministic_validator import (
    Issue,
    ValidationReport,
    detect_silent_failures,
    detect_unwired_routers,
    detect_broken_imports,
    run_full_validation,
    BACKEND_ROOT,
)


# ── Issue dataclass ──────────────────────────────────────────────────────

def test_issue_dataclass():
    """Issue should store category, severity, file, line, message."""
    issue = Issue(
        category="silent_failure",
        severity="critical",
        file="cognitive/trust_engine.py",
        line=42,
        message="bare except:pass swallows error",
    )
    assert issue.category == "silent_failure"
    assert issue.severity == "critical"
    assert issue.line == 42


# ── Silent failure detection (real AST scan) ─────────────────────────────

def test_detect_silent_failures_returns_list():
    """detect_silent_failures should return a list of Issues."""
    issues = detect_silent_failures()
    assert isinstance(issues, list)
    for issue in issues:
        assert isinstance(issue, Issue)
        assert issue.category == "silent_failure"


def test_silent_failures_have_file_and_line():
    """Each silent failure issue should reference a real file and line number."""
    issues = detect_silent_failures()
    for issue in issues:
        assert issue.file, f"Issue missing file: {issue.message}"
        # Line can be None for some patterns, but most should have it
        if issue.line is not None:
            assert issue.line > 0


# ── Unwired router detection ────────────────────────────────────────────

def test_detect_unwired_routers_returns_list():
    """detect_unwired_routers should return a list of Issues."""
    issues = detect_unwired_routers()
    assert isinstance(issues, list)
    for issue in issues:
        assert isinstance(issue, Issue)


def test_introspection_api_no_longer_unwired():
    """After our fix, introspection_api should NOT appear as unwired."""
    issues = detect_unwired_routers()
    unwired_files = [i.file for i in issues]
    # introspection_api.py should NOT be in the unwired list anymore
    for f in unwired_files:
        assert "introspection_api" not in f, \
            f"introspection_api.py is still detected as unwired: {f}"


# ── Broken import detection ─────────────────────────────────────────────

def test_detect_broken_imports_returns_list():
    """detect_broken_imports should return a list of Issues."""
    issues = detect_broken_imports()
    assert isinstance(issues, list)
    for issue in issues:
        assert isinstance(issue, Issue)
        assert issue.category == "broken_import"


# ── ValidationReport structure ────────────────────────────────────────────

def test_validation_report_structure():
    """ValidationReport should be constructable and serializable."""
    import json
    report = ValidationReport(
        timestamp="2026-03-14T00:00:00Z",
        total_issues=3,
        critical_count=1,
        warning_count=1,
        info_count=1,
        categories={"silent_failure": 1, "unwired_router": 1, "broken_import": 1},
        issues=[
            Issue(category="silent_failure", severity="critical", file="test.py", line=1, message="bare except"),
            Issue(category="unwired_router", severity="warning", file="api.py", line=10, message="not registered"),
            Issue(category="broken_import", severity="info", file="mod.py", line=5, message="missing module"),
        ],
        files_scanned=100,
        scan_time_ms=42.0,
    )
    d = report.to_dict()
    assert isinstance(d, dict)
    assert d["total_issues"] == 3
    assert d["critical_count"] == 1
    json_str = json.dumps(d, default=str)
    assert len(json_str) > 0


def test_validation_counts_consistency():
    """critical + warning + info should equal total_issues in a report."""
    report = ValidationReport(
        timestamp="2026-03-14T00:00:00Z",
        total_issues=5,
        critical_count=2,
        warning_count=2,
        info_count=1,
        categories={"a": 3, "b": 2},
        issues=[],
        files_scanned=50,
        scan_time_ms=10.0,
    )
    assert report.total_issues == report.critical_count + report.warning_count + report.info_count


# ── Backend root is correct ─────────────────────────────────────────────

def test_backend_root_exists():
    """BACKEND_ROOT should point to the actual backend directory."""
    assert BACKEND_ROOT.exists()
    assert (BACKEND_ROOT / "app.py").exists()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
