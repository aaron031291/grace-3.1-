import pytest
import os
import json
from unittest.mock import MagicMock, patch
from backend.genesis.healing_system import HealingSystem

@pytest.fixture
def temp_healing(tmp_path):
    with patch('backend.genesis.healing_system.get_repo_scanner') as mock_scanner, \
         patch('backend.genesis.healing_system.get_code_analyzer') as mock_analyzer, \
         patch('backend.genesis.healing_system.get_genesis_service') as mock_genesis:
             
        # Create dummy immutable memory
        immutable_mem_path = tmp_path / ".genesis_immutable_memory.json"
        with open(immutable_mem_path, "w") as f:
            json.dump({
                "files": {
                    "src/main.py": {
                        "extension": ".py",
                        "genesis_key": "gk-main-1"
                    }
                }
            }, f)
        
        # Setup mock dependencies
        scanner_inst = MagicMock()
        mock_scanner.return_value = scanner_inst
        
        analyzer_inst = MagicMock()
        mock_analyzer.return_value = analyzer_inst
        
        mock_genesis.return_value = MagicMock()
        
        system = HealingSystem(repo_path=str(tmp_path))
        yield system, tmp_path, scanner_inst, analyzer_inst

def test_scan_for_issues(temp_healing):
    system, tmp_path, scanner, analyzer = temp_healing
    
    # Create a dummy python file
    test_file = tmp_path / "src" / "main.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test(): pass")
    
    # Set up scanner behavior
    scanner.find_by_genesis_key.return_value = {
        "type": "file",
        "info": {
            "absolute_path": str(test_file),
            "extension": ".py",
            "path": "src/main.py",
            "name": "main.py",
            "directory_genesis_key": "gk-dir-1"
        }
    }
    
    # Set up analyzer behavior
    mock_issue = MagicMock()
    mock_issue.issue_type = "syntax"
    mock_issue.severity = "high"
    mock_issue.line_number = 1
    mock_issue.column = 1
    mock_issue.message = "dummy message"
    mock_issue.suggested_fix = "def test(): return True"
    mock_issue.fix_confidence = 0.9
    mock_issue.context = "def test(): pass"
    analyzer.analyze_python_code.return_value = [mock_issue]
    
    issues = system.scan_for_issues()
    
    assert len(issues) == 1
    assert issues[0]["issue_type"] == "syntax"
    assert issues[0]["file_genesis_key"] == "gk-main-1"

def test_heal_file_auto_apply(temp_healing):
    system, tmp_path, scanner, analyzer = temp_healing
    
    test_file = tmp_path / "fixme.py"
    test_file.write_text("def bad(): pass")
    
    scanner.find_by_genesis_key.return_value = {
        "type": "file",
        "info": {
            "absolute_path": str(test_file),
            "extension": ".py",
            "path": "fixme.py",
            "name": "fixme.py",
            "directory_genesis_key": "gk-dir-1"
        }
    }
    
    mock_issue = MagicMock()
    mock_issue.issue_type = "syntax"
    mock_issue.severity = "high"
    mock_issue.line_number = 1
    mock_issue.column = 0
    mock_issue.message = ""
    mock_issue.suggested_fix = "def bad(): return False"
    mock_issue.fix_confidence = 0.9
    mock_issue.context = ""
    analyzer.analyze_python_code.return_value = [mock_issue]
    
    result = system.heal_file("gk-fixme-1", auto_apply=True)
    
    assert result["status"] == "healed"
    assert result["fixes_applied"] == 1
    
    # Verify file was modified
    mod_code = test_file.read_text()
    assert "return False" in mod_code

if __name__ == "__main__":
    pytest.main(['-v', __file__])
