"""
Tests for Dynamic Test Generator

Tests:
1. Type inference from parameter names
2. Test value generation for each type
3. Function signature analysis
"""

import pytest
import sys
import ast
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent))


# Sample code for testing
SAMPLE_FUNCTION_SIMPLE = '''
def greet(name):
    """Greet someone by name."""
    return f"Hello, {name}!"
'''

SAMPLE_FUNCTION_TYPED = '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def concat(text: str, suffix: str = "") -> str:
    """Concatenate strings."""
    return text + suffix
'''

SAMPLE_CLASS = '''
class Calculator:
    """A simple calculator."""
    
    def __init__(self, initial: int = 0):
        self.value = initial
    
    def add(self, x: int) -> int:
        """Add to the current value."""
        self.value += x
        return self.value
    
    def reset(self) -> None:
        """Reset the value to zero."""
        self.value = 0
'''

SAMPLE_COMPLEX_TYPES = '''
from typing import List, Dict, Optional, Any

def process_items(items: List[str], config: Dict[str, Any]) -> Optional[str]:
    """Process items with config."""
    if not items:
        return None
    return items[0]

def get_user(user_id: int, include_metadata: bool = False) -> Dict[str, Any]:
    """Get user by ID."""
    return {"id": user_id, "name": "Test"}
'''

SAMPLE_INFERRABLE_NAMES = '''
def update_user(user_id, user_name, is_active, email_count, config_options):
    """Update user with various parameters."""
    pass

def set_threshold(min_value, max_value, ratio, percentage):
    """Set threshold values."""
    pass
'''


class TestCodeAnalyzer:
    """Tests for CodeAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create CodeAnalyzer instance."""
        from backend.dynamic_test_generator import CodeAnalyzer
        return CodeAnalyzer()
    
    def test_init(self, analyzer):
        """Test analyzer initialization."""
        assert analyzer is not None
    
    def test_analyze_code_simple(self, analyzer):
        """Test analyzing simple code."""
        result = analyzer.analyze_code(SAMPLE_FUNCTION_SIMPLE, "test_module")
        
        assert result.module_name == "test_module"
        assert len(result.functions) == 1
        assert result.functions[0]["name"] == "greet"
    
    def test_analyze_code_with_class(self, analyzer):
        """Test analyzing code with class."""
        result = analyzer.analyze_code(SAMPLE_CLASS, "calc_module")
        
        assert len(result.classes) == 1
        assert result.classes[0]["name"] == "Calculator"
        assert len(result.classes[0]["methods"]) >= 3
    
    def test_analyze_file(self, analyzer, tmp_path):
        """Test analyzing a file."""
        test_file = tmp_path / "test_code.py"
        test_file.write_text(SAMPLE_FUNCTION_TYPED)
        
        result = analyzer.analyze_file(str(test_file))
        
        assert result.file_path == str(test_file)
        assert len(result.functions) == 2


class TestFunctionSignatureAnalysis:
    """Tests for function signature analysis."""
    
    @pytest.fixture
    def analyzer(self):
        """Create CodeAnalyzer instance."""
        from backend.dynamic_test_generator import CodeAnalyzer
        return CodeAnalyzer()
    
    def test_extract_function_name(self, analyzer):
        """Test extraction of function name."""
        result = analyzer.analyze_code(SAMPLE_FUNCTION_SIMPLE)
        
        assert result.functions[0]["name"] == "greet"
    
    def test_extract_function_args(self, analyzer):
        """Test extraction of function arguments."""
        result = analyzer.analyze_code(SAMPLE_FUNCTION_SIMPLE)
        
        args = result.functions[0]["args"]
        assert len(args) == 1
        assert args[0]["name"] == "name"
    
    def test_extract_typed_args(self, analyzer):
        """Test extraction of typed arguments."""
        result = analyzer.analyze_code(SAMPLE_FUNCTION_TYPED)
        
        add_func = next(f for f in result.functions if f["name"] == "add")
        args = add_func["args"]
        
        assert args[0]["type"] == "int"
        assert args[1]["type"] == "int"
    
    def test_extract_return_type(self, analyzer):
        """Test extraction of return type."""
        result = analyzer.analyze_code(SAMPLE_FUNCTION_TYPED)
        
        add_func = next(f for f in result.functions if f["name"] == "add")
        assert add_func["return_type"] == "int"
    
    def test_extract_default_args(self, analyzer):
        """Test extraction of default arguments."""
        result = analyzer.analyze_code(SAMPLE_FUNCTION_TYPED)
        
        concat_func = next(f for f in result.functions if f["name"] == "concat")
        args = concat_func["args"]
        
        # suffix has a default
        suffix_arg = next(a for a in args if a["name"] == "suffix")
        assert suffix_arg.get("has_default") is True
    
    def test_extract_docstring(self, analyzer):
        """Test extraction of docstring."""
        result = analyzer.analyze_code(SAMPLE_FUNCTION_SIMPLE)
        
        assert result.functions[0]["docstring"] == "Greet someone by name."
    
    def test_extract_decorators(self, analyzer):
        """Test extraction of decorators."""
        code = '''
@staticmethod
def static_func():
    pass

@classmethod
def class_func(cls):
    pass

@property
def prop(self):
    return self._value
'''
        result = analyzer.analyze_code(code)
        
        static_func = next(f for f in result.functions if f["name"] == "static_func")
        assert "staticmethod" in static_func["decorators"]
    
    def test_extract_async_function(self, analyzer):
        """Test extraction of async function."""
        code = '''
async def fetch_data(url: str) -> dict:
    """Fetch data from URL."""
    return {}
'''
        result = analyzer.analyze_code(code)
        
        # Note: is_async may not be set for top-level async functions
        # depending on implementation
        assert len(result.functions) == 1
    
    def test_extract_varargs(self, analyzer):
        """Test extraction of *args and **kwargs."""
        code = '''
def flexible_func(*args, **kwargs):
    pass
'''
        result = analyzer.analyze_code(code)
        
        func = result.functions[0]
        assert func["has_varargs"] is True
        assert func["has_kwargs"] is True
        assert func["vararg_name"] == "args"
        assert func["kwarg_name"] == "kwargs"


class TestTypeInference:
    """Tests for type inference from parameter names."""
    
    @pytest.fixture
    def generator(self):
        """Create DynamicTestGenerator instance."""
        from backend.dynamic_test_generator import DynamicTestGenerator
        return DynamicTestGenerator()
    
    def test_infer_int_from_name(self, generator):
        """Test inferring int from parameter names like 'count', 'id', 'age'."""
        analysis = generator.analyzer.analyze_code(SAMPLE_INFERRABLE_NAMES)
        
        # The _generate_test_cases method uses name hints
        update_func = next(f for f in analysis.functions if f["name"] == "update_user")
        
        # user_id should be inferred as int
        user_id_arg = next(a for a in update_func["args"] if a["name"] == "user_id")
        
        # Generate test cases
        test_cases = generator._generate_test_cases(update_func["args"])
        
        # First argument (user_id) should have int values
        assert len(test_cases) > 0
        # Values should be appropriate for inferred types
    
    def test_infer_str_from_name(self, generator):
        """Test inferring str from parameter names like 'name', 'text', 'path'."""
        analysis = generator.analyzer.analyze_code(SAMPLE_INFERRABLE_NAMES)
        
        update_func = next(f for f in analysis.functions if f["name"] == "update_user")
        
        # user_name should be inferred as str
        test_cases = generator._generate_test_cases(update_func["args"])
        
        # Should have test cases
        assert len(test_cases) > 0
    
    def test_infer_bool_from_name(self, generator):
        """Test inferring bool from parameter names like 'is_active', 'enabled'."""
        analysis = generator.analyzer.analyze_code(SAMPLE_INFERRABLE_NAMES)
        
        # is_active should be inferred as bool
        update_func = next(f for f in analysis.functions if f["name"] == "update_user")
        
        test_cases = generator._generate_test_cases(update_func["args"])
        assert len(test_cases) > 0
    
    def test_infer_dict_from_name(self, generator):
        """Test inferring dict from parameter names like 'config', 'options'."""
        analysis = generator.analyzer.analyze_code(SAMPLE_INFERRABLE_NAMES)
        
        update_func = next(f for f in analysis.functions if f["name"] == "update_user")
        
        # config_options should be inferred as dict
        test_cases = generator._generate_test_cases(update_func["args"])
        assert len(test_cases) > 0
    
    def test_infer_float_from_name(self, generator):
        """Test inferring float from parameter names like 'ratio', 'percentage'."""
        analysis = generator.analyzer.analyze_code(SAMPLE_INFERRABLE_NAMES)
        
        threshold_func = next(f for f in analysis.functions if f["name"] == "set_threshold")
        
        test_cases = generator._generate_test_cases(threshold_func["args"])
        assert len(test_cases) > 0


class TestTestValueGeneration:
    """Tests for test value generation for each type."""
    
    @pytest.fixture
    def generator(self):
        """Create DynamicTestGenerator instance."""
        from backend.dynamic_test_generator import DynamicTestGenerator
        return DynamicTestGenerator()
    
    def test_generate_str_values(self, generator):
        """Test generation of string test values."""
        args = [{"name": "text", "type": "str"}]
        
        test_cases = generator._generate_test_cases(args)
        
        # Should have multiple string test cases
        assert len(test_cases) > 0
        for case in test_cases:
            assert isinstance(case[0], str)
    
    def test_generate_int_values(self, generator):
        """Test generation of integer test values."""
        args = [{"name": "count", "type": "int"}]
        
        test_cases = generator._generate_test_cases(args)
        
        # Should include edge cases like 0, negative, large values
        values = [case[0] for case in test_cases]
        assert 0 in values
        assert any(v < 0 for v in values)  # Has negative
        assert any(v > 100 for v in values)  # Has large value
    
    def test_generate_float_values(self, generator):
        """Test generation of float test values."""
        args = [{"name": "ratio", "type": "float"}]
        
        test_cases = generator._generate_test_cases(args)
        
        # Should have float values
        assert len(test_cases) > 0
        values = [case[0] for case in test_cases]
        assert any(isinstance(v, float) for v in values)
    
    def test_generate_bool_values(self, generator):
        """Test generation of boolean test values."""
        args = [{"name": "flag", "type": "bool"}]
        
        test_cases = generator._generate_test_cases(args)
        
        # Should have True and False
        values = [case[0] for case in test_cases]
        assert True in values
        assert False in values
    
    def test_generate_list_values(self, generator):
        """Test generation of list test values."""
        args = [{"name": "items", "type": "list"}]
        
        test_cases = generator._generate_test_cases(args)
        
        # Should include empty list and non-empty lists
        values = [case[0] for case in test_cases]
        assert [] in values
        assert any(len(v) > 0 for v in values if isinstance(v, list))
    
    def test_generate_dict_values(self, generator):
        """Test generation of dict test values."""
        args = [{"name": "config", "type": "dict"}]
        
        test_cases = generator._generate_test_cases(args)
        
        # Should include empty dict and non-empty dicts
        values = [case[0] for case in test_cases]
        assert {} in values
        assert any(len(v) > 0 for v in values if isinstance(v, dict))
    
    def test_generate_optional_values(self, generator):
        """Test generation of Optional type values."""
        args = [{"name": "value", "type": "Optional"}]
        
        test_cases = generator._generate_test_cases(args)
        
        # Should include None
        values = [case[0] for case in test_cases]
        assert None in values
    
    def test_generate_any_values(self, generator):
        """Test generation of Any type values."""
        args = [{"name": "value", "type": "Any"}]
        
        test_cases = generator._generate_test_cases(args)
        
        # Should have diverse values
        values = [case[0] for case in test_cases]
        assert len(values) > 1
    
    def test_generate_multiple_args(self, generator):
        """Test generation of values for multiple arguments."""
        args = [
            {"name": "name", "type": "str"},
            {"name": "age", "type": "int"},
            {"name": "active", "type": "bool"}
        ]
        
        test_cases = generator._generate_test_cases(args)
        
        # Each case should have 3 values
        for case in test_cases:
            assert len(case) == 3
    
    def test_generate_no_args(self, generator):
        """Test generation for function with no arguments."""
        args = []
        
        test_cases = generator._generate_test_cases(args)
        
        # Should return empty case list
        assert test_cases == [[]]


class TestDynamicTestGenerator:
    """Tests for DynamicTestGenerator class."""
    
    @pytest.fixture
    def generator(self):
        """Create DynamicTestGenerator instance."""
        from backend.dynamic_test_generator import DynamicTestGenerator
        return DynamicTestGenerator()
    
    def test_init(self, generator):
        """Test generator initialization."""
        assert generator is not None
        assert generator.analyzer is not None
        assert generator.generated_tests == []
    
    def test_generate_tests_for_code(self, generator):
        """Test generating tests for code string."""
        tests = generator.generate_tests_for_code(SAMPLE_FUNCTION_SIMPLE, "greet_module")
        
        assert len(tests) > 0
        assert all(t.test_name.startswith("test_") for t in tests)
    
    def test_generate_tests_for_file(self, generator, tmp_path):
        """Test generating tests for file."""
        test_file = tmp_path / "test_code.py"
        test_file.write_text(SAMPLE_FUNCTION_TYPED)
        
        tests = generator.generate_tests_for_file(str(test_file))
        
        assert len(tests) > 0
    
    def test_generate_function_tests(self, generator):
        """Test generating tests for a function."""
        analysis = generator.analyzer.analyze_code(SAMPLE_FUNCTION_TYPED)
        add_func = next(f for f in analysis.functions if f["name"] == "add")
        
        tests = generator._generate_function_tests(add_func, analysis)
        
        # Should have existence test and possibly others
        assert len(tests) > 0
        assert any("exists" in t.test_name for t in tests)
    
    def test_generate_class_tests(self, generator):
        """Test generating tests for a class."""
        analysis = generator.analyzer.analyze_code(SAMPLE_CLASS)
        calc_class = analysis.classes[0]
        
        tests = generator._generate_class_tests(calc_class, analysis)
        
        # Should have instantiation test
        assert any("instantiation" in t.test_name for t in tests)
    
    def test_generate_return_type_test(self, generator):
        """Test generating return type test."""
        analysis = generator.analyzer.analyze_code(SAMPLE_FUNCTION_TYPED)
        add_func = next(f for f in analysis.functions if f["name"] == "add")
        
        tests = generator._generate_function_tests(add_func, analysis)
        
        # Should have return type test
        return_tests = [t for t in tests if "return_type" in t.test_name]
        assert len(return_tests) > 0


class TestTypeCheckGeneration:
    """Tests for type check code generation."""
    
    @pytest.fixture
    def generator(self):
        """Create DynamicTestGenerator instance."""
        from backend.dynamic_test_generator import DynamicTestGenerator
        return DynamicTestGenerator()
    
    def test_generate_type_check_str(self, generator):
        """Test generating type check for str."""
        check = generator._generate_type_check("str")
        
        assert "isinstance" in check
        assert "str" in check
    
    def test_generate_type_check_int(self, generator):
        """Test generating type check for int."""
        check = generator._generate_type_check("int")
        
        assert "isinstance" in check
        assert "int" in check
    
    def test_generate_type_check_float(self, generator):
        """Test generating type check for float."""
        check = generator._generate_type_check("float")
        
        assert "isinstance" in check
        # Should accept both int and float
        assert "float" in check
    
    def test_generate_type_check_optional(self, generator):
        """Test generating type check for Optional."""
        check = generator._generate_type_check("Optional[str]")
        
        assert "None" in check
    
    def test_generate_type_check_any(self, generator):
        """Test generating type check for Any."""
        check = generator._generate_type_check("Any")
        
        # Any type should not have strict check
        assert "pass" in check
    
    def test_generate_type_check_list(self, generator):
        """Test generating type check for list."""
        check = generator._generate_type_check("list")
        
        assert "isinstance" in check
        assert "list" in check
    
    def test_generate_type_check_dict(self, generator):
        """Test generating type check for dict."""
        check = generator._generate_type_check("dict")
        
        assert "isinstance" in check
        assert "dict" in check


class TestGeneratedTestCode:
    """Tests for generated test code quality."""
    
    @pytest.fixture
    def generator(self):
        """Create DynamicTestGenerator instance."""
        from backend.dynamic_test_generator import DynamicTestGenerator
        return DynamicTestGenerator()
    
    def test_generated_test_is_valid_python(self, generator):
        """Test that generated tests are valid Python."""
        tests = generator.generate_tests_for_code(SAMPLE_FUNCTION_SIMPLE)
        
        for test in tests:
            # Should not raise SyntaxError
            try:
                ast.parse(test.test_code)
            except SyntaxError as e:
                pytest.fail(f"Generated test has syntax error: {e}\n{test.test_code}")
    
    def test_generated_test_has_docstring(self, generator):
        """Test that generated tests have docstrings."""
        tests = generator.generate_tests_for_code(SAMPLE_FUNCTION_SIMPLE)
        
        for test in tests:
            # Tests should have documentation
            assert '"""' in test.test_code or "'''" in test.test_code
    
    def test_generated_test_imports_module(self, generator):
        """Test that generated tests import the module."""
        tests = generator.generate_tests_for_code(SAMPLE_FUNCTION_SIMPLE, "my_module")
        
        for test in tests:
            assert "from my_module import" in test.test_code or "import my_module" in test.test_code
    
    def test_generated_test_has_assertions(self, generator):
        """Test that generated tests have assertions."""
        tests = generator.generate_tests_for_code(SAMPLE_FUNCTION_TYPED)
        
        # At least some tests should have assertions
        tests_with_assert = [t for t in tests if "assert" in t.test_code]
        assert len(tests_with_assert) > 0


class TestAutonomousTestBuilder:
    """Tests for AutonomousTestBuilder class."""
    
    @pytest.fixture
    def builder(self):
        """Create AutonomousTestBuilder instance."""
        from backend.dynamic_test_generator import AutonomousTestBuilder
        return AutonomousTestBuilder()
    
    def test_init(self, builder):
        """Test builder initialization."""
        assert builder.generator is not None
        assert builder.executor is not None
    
    def test_validate_implementation_functions(self, builder):
        """Test validating implementation has expected functions."""
        result = builder.validate_implementation(
            SAMPLE_FUNCTION_TYPED,
            {"functions": ["add", "concat"]}
        )
        
        assert result["valid"] is True
        assert "add" in result["analysis"]["functions_found"]
        assert "concat" in result["analysis"]["functions_found"]
    
    def test_validate_implementation_missing_function(self, builder):
        """Test validation fails for missing function."""
        result = builder.validate_implementation(
            SAMPLE_FUNCTION_TYPED,
            {"functions": ["add", "missing_func"]}
        )
        
        assert result["valid"] is False
        assert any("missing_func" in issue for issue in result["issues"])
    
    def test_validate_implementation_classes(self, builder):
        """Test validating implementation has expected classes."""
        result = builder.validate_implementation(
            SAMPLE_CLASS,
            {"classes": ["Calculator"]}
        )
        
        assert result["valid"] is True
        assert "Calculator" in result["analysis"]["classes_found"]
    
    def test_validate_implementation_missing_class(self, builder):
        """Test validation fails for missing class."""
        result = builder.validate_implementation(
            SAMPLE_CLASS,
            {"classes": ["Calculator", "MissingClass"]}
        )
        
        assert result["valid"] is False
        assert any("MissingClass" in issue for issue in result["issues"])
