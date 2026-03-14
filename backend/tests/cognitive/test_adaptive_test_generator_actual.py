import pytest
import os
import json
from pathlib import Path
from unittest.mock import MagicMock

def test_extract_functions():
    from backend.cognitive.adaptive_test_generator import _extract_functions
    
    source_code = """
def my_func(a: int, b: str) -> bool:
    '''This is a test function.'''
    return True
    
def _private_func():
    pass

class MyClass:
    def method(self):
        pass
"""
    functions = _extract_functions(source_code)
    
    assert len(functions) == 2 # my_func and method (class methods without 'self' might show up if not filtered properly, actually 'self' is filtered out from args, but method is parsed as FunctionDef)
    
    names = [f["name"] for f in functions]
    assert "my_func" in names
    assert "method" in names
    assert "_private_func" not in names
    
    # Check args parsing
    my_func_dict = next(f for f in functions if f["name"] == "my_func")
    assert len(my_func_dict["args"]) == 2
    assert my_func_dict["args"][0]["name"] == "a"
    assert my_func_dict["args"][0]["type"] == "int"
    assert "This is a test function." in my_func_dict["docstring"]

def test_generate_tests_for_module_success(monkeypatch, tmp_path):
    import backend.cognitive.adaptive_test_generator as atg
    
    # Mock backend dir
    mock_backend_dir = tmp_path
    monkeypatch.setattr(atg, "BACKEND_DIR", mock_backend_dir)
    monkeypatch.setattr(atg, "GENERATED_TESTS_DIR", tmp_path / "data" / "generated_tests")
    
    # Create fake module
    module_path = mock_backend_dir / "cognitive" / "fake_module.py"
    module_path.parent.mkdir(parents=True, exist_ok=True)
    module_path.write_text("def add(a, b): return a + b")
    
    # Mock LLM and consensus
    monkeypatch.setattr(atg, "_consensus_reason_about_module", lambda s, p: "Adds numbers.")
    monkeypatch.setattr(atg, "_generate_test_for_function", lambda f, s, p, m: "def test_add(): assert add(1, 1) == 2")
    
    # Mock Sandbox execution
    class MockSandboxResult:
        def __init__(self):
            self.stdout = "TEST_PASSED"
            self.stderr = ""
            self.runtime_error = ""
            
    monkeypatch.setattr(atg, "_run_generated_test", lambda t, s: {"passed": True, "output": "TEST_PASSED", "error": ""})
    
    # Mock track and publish
    import backend.cognitive.event_bus as eb
    monkeypatch.setattr(eb, "publish", lambda *args, **kwargs: None)
    
    import sys
    sys.modules["api._genesis_tracker"] = MagicMock()
    
    res = atg.generate_tests_for_module("cognitive/fake_module.py")
    
    assert res["functions_found"] == 1
    assert res["tests_generated"] == 1
    assert res["tests_passed"] == 1
    assert res["pass_rate"] == 100.0
    assert len(res["tests"]) == 1
    
    # Check saved output
    saved_file = atg.GENERATED_TESTS_DIR / f"{str(module_path).replace('/', '_').replace('.py', '')}.json"
    
    # On windows paths have backward slashes, so replace handles differ slightly in practice. 
    # Just check that it created a file in GENERATED_TESTS_DIR.
    files = list(atg.GENERATED_TESTS_DIR.glob("*.json"))
    assert len(files) == 1
    
    saved_data = json.loads(files[0].read_text())
    assert saved_data["tests_generated"] == 1

if __name__ == "__main__":
    pytest.main(['-v', __file__])
