import pytest
from unittest.mock import patch, MagicMock

import sys
sys.modules['backend.api'] = MagicMock()
sys.modules['backend.api._genesis_tracker'] = MagicMock()
sys.modules['api._genesis_tracker'] = MagicMock()

from backend.cognitive.grace_compiler import get_grace_compiler, CompileResult

@pytest.fixture
def compiler():
    return get_grace_compiler()

@patch('cognitive.architecture_compass.get_compass')
@patch('cognitive.code_sandbox.execute_sandboxed')
@patch('cognitive.trust_engine.get_trust_engine')
def test_compile_safe_code(mock_trust, mock_sandbox, mock_compass, compiler):
    code = """
def hello_world(name: str):
    return f"Hello {name}"

class Greeter:
    pass
"""
    # Mocking successful execution and testing
    mock_sandbox_result = MagicMock()
    mock_sandbox_result.success = True
    mock_sandbox_result.compiled = True
    mock_sandbox_result.stdout = "TEST PASS"
    mock_sandbox_result.runtime_error = None
    mock_sandbox_result.to_dict.return_value = {"compiled": True}
    mock_sandbox.return_value = mock_sandbox_result

    # Mock trust engine
    mock_te_instance = MagicMock()
    mock_te_instance.score_output.return_value = 0.9
    mock_trust.return_value = mock_te_instance

    result = compiler.compile(code)

    assert result.success is True
    assert len(result.errors) == 0
    assert "func:hello_world" in result.integration_points
    assert "class:Greeter" in result.integration_points
    assert result.generated_tests == 1
    assert result.tests_passed == 1
    assert result.citizenship_level in ["resident", "citizen"]

def test_compile_dangerous_code_rejected(compiler):
    code = """
import os

def delete_everything():
    os.system("rm -rf /")
    eval("print('Dangerous')")
"""
    result = compiler.compile(code)

    assert result.success is False
    assert len(result.errors) > 0
    
    error_str = " ".join(result.errors)
    assert "os.system()" in error_str
    assert "eval()" in error_str

@patch('cognitive.architecture_compass.get_compass')
@patch('cognitive.code_sandbox.execute_sandboxed')
def test_compile_auto_import(mock_sandbox, mock_compass, compiler):
    code = """
def check_trust():
    engine = get_trust_engine()
    return engine.score()
"""
    # Mock
    mock_sandbox_result = MagicMock()
    mock_sandbox_result.compiled = True
    mock_sandbox_result.runtime_error = None
    mock_sandbox_result.to_dict.return_value = {"compiled": True}
    mock_sandbox.return_value = mock_sandbox_result

    result = compiler.compile(code)

    assert len(result.warnings) > 0
    warn_str = " ".join(result.warnings)
    assert "auto-imported" in warn_str
    
@patch('cognitive.architecture_compass.get_compass')
@patch('cognitive.code_sandbox.execute_sandboxed')
def test_compiler_forecast_warning(mock_sandbox, mock_compass, compiler):
    code = """
class ExistingComponent:
    pass
"""
    mock_compass_instance = MagicMock()
    mock_compass_instance.find_for.return_value = ["ExistingComponent"]
    mock_compass_instance.predict_dependency_issues.return_value = [{"severity": "high"}]
    mock_compass.return_value = mock_compass_instance

    mock_sandbox_result = MagicMock()
    mock_sandbox_result.compiled = True
    mock_sandbox_result.runtime_error = None
    mock_sandbox_result.to_dict.return_value = {"compiled": True}
    mock_sandbox.return_value = mock_sandbox_result
    
    result = compiler.compile(code)
    
    # We expect warnings about class resolution and high severity dependency issues
    warn_str = " ".join(result.warnings)
    assert "ExistingComponent" in warn_str
    assert "high-severity dependency issues" in warn_str
