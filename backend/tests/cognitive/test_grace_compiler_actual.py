import pytest
from backend.cognitive.grace_compiler import get_grace_compiler, CompileResult

def test_compiler_success():
    compiler = get_grace_compiler()
    code = "def my_func():\n    return 42"
    
    res = compiler.compile(code)
    assert res.stage == "integrate"
    assert "func:my_func" in res.integration_points

def test_compiler_forbidden_eval():
    compiler = get_grace_compiler()
    code = "eval('1+1')"
    
    res = compiler.compile(code)
    assert res.success is False
    assert any("forbidden" in e for e in res.errors)

def test_compiler_auto_import():
    compiler = get_grace_compiler()
    code = "def x():\n    trust_engine.score()"
    res = compiler._auto_import(code, compiler._parse(code, CompileResult()))
    assert "from cognitive.trust_engine import get_trust_engine" in res

if __name__ == "__main__":
    pytest.main(['-v', __file__])
