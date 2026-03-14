import pytest
from backend.cognitive.code_sandbox import compile_check, static_analyse, execute_sandboxed, verify_code_quality

def test_compile_check_logic():
    result = compile_check("print('hello')")
    assert result.compiled is True

    result_bad = compile_check("print('hello'")
    assert result_bad.compiled is False
    assert len(result_bad.syntax_errors) > 0

def test_static_analyse_logic():
    code = "import os; os.system('ls')"
    warnings = static_analyse(code)
    # Check that dangerous calls and imports are found
    assert any("dangerous module 'os'" in w for w in warnings)
    assert any("dangerous call" in w for w in warnings)

def test_execute_sandboxed_logic():
    code = "print('sandboxed hello')"
    result = execute_sandboxed(code)
    assert result.compiled is True
    assert result.executed is True
    assert result.success is True
    assert "sandboxed hello\n" == result.stdout

def test_execute_sandbox_timeout():
    # infinite loop must hit timeout
    code = "while True: pass"
    result = execute_sandboxed(code, timeout=1) # Need to set short timeout
    assert result.compiled is True
    assert result.executed is True
    assert result.success is False
    assert "Execution timed out" in result.runtime_error

def test_verify_code_quality_logic():
    code = "print(1 + 1)"
    quality = verify_code_quality(code)
    assert quality["score"] == 100
    assert quality["compiled"] is True
    assert quality["runs_successfully"] is True

if __name__ == "__main__":
    pytest.main(['-v', __file__])
