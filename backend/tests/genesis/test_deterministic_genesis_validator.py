import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from backend.genesis.deterministic_genesis_validator import (
    run_genesis_validation,
    check_genesis_schema_integrity,
    check_genesis_import_chain,
    GenesisValidationReport
)

# Using MagicMock to simulate AST parsing behavior where needed
# but mostly we focus on the high-level run and basic checks

def test_run_genesis_validation_structure():
    # If the DB doesn't exist or is empty, this should still run deterministically without crashing
    report = run_genesis_validation()
    
    # Check the return type is correct
    assert isinstance(report, GenesisValidationReport)
    assert hasattr(report, "total_issues")
    assert hasattr(report, "critical_count")
    assert hasattr(report, "warning_count")
    
    # Ensure checks_run contains the expected module steps
    assert "schema_integrity" in report.checks_run
    assert "chain_integrity" in report.checks_run
    assert "kb_sync" in report.checks_run

def test_check_genesis_import_chain_missing():
    # Patch Path.exists to force a missing file scenario
    with patch('pathlib.Path.exists', return_value=False):
        issues = check_genesis_import_chain()
        
        assert len(issues) > 0
        assert any(i.check == "import_chain" for i in issues)
        assert any(i.severity == "critical" for i in issues)
        assert "missing" in issues[0].message

def test_check_genesis_schema_integrity_missing_file():
    # Patch Path.exists to force a missing model file scenario
    with patch('pathlib.Path.exists', return_value=False):
        issues = check_genesis_schema_integrity()
        
        assert len(issues) > 0
        assert issues[0].check == "schema_integrity"
        assert issues[0].severity == "critical"
        assert "not found" in issues[0].message

@patch('backend.genesis.deterministic_genesis_validator._gather_genesis_stats')
def test_validation_report_to_dict(mock_gather):
    mock_gather.return_value = {"total_keys": 5}
    
    report = run_genesis_validation()
    report_dict = report.to_dict()
    
    assert "timestamp" in report_dict
    assert "total_issues" in report_dict
    assert report_dict["stats"] == {"total_keys": 5}

if __name__ == "__main__":
    pytest.main(['-v', __file__])
