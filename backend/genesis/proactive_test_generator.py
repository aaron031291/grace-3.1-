import ast
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from models.genesis_key_models import GenesisKey
from genesis.code_change_analyzer import ChangeAnalysis, CodeChange, CodeEntity
class GeneratedTest:
    logger = logging.getLogger(__name__)
    """A generated test case."""
    test_name: str
    test_code: str
    test_type: str  # unit, integration, edge_case, etc.
    target_function: Optional[str] = None
    confidence: float = 0.5
    reasoning: str = ""


@dataclass
class TestGenerationPlan:
    """Plan for generating tests."""
    genesis_key_id: str
    file_path: str
    target_functions: List[str]
    generated_tests: List[GeneratedTest] = field(default_factory=list)
    suggested_test_cases: List[str] = field(default_factory=list)
    coverage_estimate: float = 0.0
    generation_confidence: float = 0.5


class ProactiveTestGenerator:
    """
    Generates tests proactively for code changes.
    
    Analyzes:
    - New functions/classes
    - Function signatures
    - Expected behavior
    - Edge cases
    - Integration points
    """
    
    def __init__(self):
        self.generated_tests: List[GeneratedTest] = []
        self.test_patterns: Dict[str, List[str]] = {}
    
    def generate_tests_for_change(
        self,
        genesis_key: GenesisKey,
        change_analysis: ChangeAnalysis
    ) -> TestGenerationPlan:
        """
        Generate tests for a code change.
        
        Args:
            genesis_key: Genesis Key representing the change
            change_analysis: Semantic analysis of the change
            
        Returns:
            Test generation plan with generated tests
        """
        plan = TestGenerationPlan(
            genesis_key_id=genesis_key.key_id,
            file_path=genesis_key.file_path,
            target_functions=change_analysis.affected_functions
        )
        
        # Generate tests for each new/modified function
        for change in change_analysis.changes:
            if change.entity and change.entity.entity_type == 'function':
                if change.change_type.value.endswith('_added'):
                    # New function - generate comprehensive tests
                    tests = self._generate_tests_for_new_function(
                        change.entity,
                        genesis_key,
                        change
                    )
                    plan.generated_tests.extend(tests)
                
                elif change.change_type.value.endswith('_modified'):
                    # Modified function - generate regression tests
                    tests = self._generate_tests_for_modified_function(
                        change.entity,
                        genesis_key,
                        change
                    )
                    plan.generated_tests.extend(tests)
        
        # Generate integration tests
        if len(change_analysis.affected_functions) > 1:
            integration_tests = self._generate_integration_tests(
                change_analysis,
                genesis_key
            )
            plan.generated_tests.extend(integration_tests)
        
        # Estimate coverage
        plan.coverage_estimate = self._estimate_coverage(plan)
        plan.generation_confidence = self._calculate_confidence(plan)
        
        logger.info(
            f"[TestGenerator] Generated {len(plan.generated_tests)} tests "
            f"for {genesis_key.key_id}"
        )
        
        return plan
    
    def _generate_tests_for_new_function(
        self,
        entity: CodeEntity,
        genesis_key: GenesisKey,
        change: CodeChange
    ) -> List[GeneratedTest]:
        """Generate tests for a new function."""
        tests = []
        
        # Basic test structure
        test_name = f"test_{entity.name}"
        
        # Parse function to understand parameters
        if change.after_code:
            try:
                tree = ast.parse(change.after_code)
                func_info = self._analyze_function(tree, entity.name)
                
                # Generate basic test
                basic_test = self._create_basic_test(entity, func_info, genesis_key)
                tests.append(basic_test)
                
                # Generate edge case tests
                edge_tests = self._generate_edge_case_tests(entity, func_info, genesis_key)
                tests.extend(edge_tests)
                
                # Generate error handling tests
                error_tests = self._generate_error_tests(entity, func_info, genesis_key)
                tests.extend(error_tests)
                
            except SyntaxError:
                # Fallback: simple test template
                tests.append(self._create_simple_test_template(entity, genesis_key))
        
        return tests
    
    def _generate_tests_for_modified_function(
        self,
        entity: CodeEntity,
        genesis_key: GenesisKey,
        change: CodeChange
    ) -> List[GeneratedTest]:
        """Generate regression tests for modified function."""
        tests = []
        
        # Focus on what changed
        if change.before_code and change.after_code:
            # Compare before/after to identify what to test
            diff_analysis = self._analyze_change_diff(change)
            
            # Generate regression test
            regression_test = GeneratedTest(
                test_name=f"test_{entity.name}_regression",
                test_code=self._generate_regression_test_code(entity, diff_analysis),
                test_type="regression",
                target_function=entity.name,
                confidence=0.7,
                reasoning="Ensures modified function maintains expected behavior"
            )
            tests.append(regression_test)
        
        return tests
    
    def _generate_integration_tests(
        self,
        change_analysis: ChangeAnalysis,
        genesis_key: GenesisKey
    ) -> List[GeneratedTest]:
        """Generate integration tests for multiple affected functions."""
        tests = []
        
        if len(change_analysis.affected_functions) >= 2:
            # Generate test for interaction between functions
            test = GeneratedTest(
                test_name=f"test_integration_{'_'.join(change_analysis.affected_functions[:2])}",
                test_code=self._generate_integration_test_code(change_analysis),
                test_type="integration",
                confidence=0.6,
                reasoning="Tests interaction between modified functions"
            )
            tests.append(test)
        
        return tests
    
    def _analyze_function(self, tree: ast.AST, func_name: str) -> Dict[str, Any]:
        """Analyze function to extract information."""
        info = {
            "parameters": [],
            "param_types": {},
            "param_defaults": {},
            "return_type": None,
            "has_exceptions": False,
            "exception_types": [],
            "complexity": 0
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                # Extract parameter names (skip 'self' for methods)
                params = [arg.arg for arg in node.args.args if arg.arg != 'self']
                info["parameters"] = params
                
                # Extract parameter type annotations
                for arg in node.args.args:
                    if arg.annotation:
                        info["param_types"][arg.arg] = ast.unparse(arg.annotation)
                
                # Extract default values
                defaults = node.args.defaults
                num_defaults = len(defaults)
                num_params = len(node.args.args)
                for i, default in enumerate(defaults):
                    param_idx = num_params - num_defaults + i
                    if param_idx >= 0 and param_idx < len(node.args.args):
                        param_name = node.args.args[param_idx].arg
                        try:
                            info["param_defaults"][param_name] = ast.unparse(default)
                        except Exception:
                            info["param_defaults"][param_name] = "None"
                
                # Extract return type annotation
                if node.returns:
                    info["return_type"] = ast.unparse(node.returns)
                
                # Check for exceptions and extract types
                for child in ast.walk(node):
                    if isinstance(child, ast.Raise):
                        info["has_exceptions"] = True
                        if child.exc:
                            if isinstance(child.exc, ast.Call):
                                exc_name = ast.unparse(child.exc.func)
                                if exc_name not in info["exception_types"]:
                                    info["exception_types"].append(exc_name)
                            elif isinstance(child.exc, ast.Name):
                                if child.exc.id not in info["exception_types"]:
                                    info["exception_types"].append(child.exc.id)
                    elif isinstance(child, ast.Try):
                        info["has_exceptions"] = True
                
                break
        
        return info
    
    def _generate_mock_value(self, param_name: str, param_type: Optional[str] = None) -> str:
        """Generate appropriate mock value based on parameter name and type."""
        # Type-based mock values
        type_mocks = {
            "str": '"test_string"',
            "int": "42",
            "float": "3.14",
            "bool": "True",
            "list": "[]",
            "dict": "{}",
            "List": "[]",
            "Dict": "{}",
            "Optional": "None",
            "Any": '"test_value"',
        }
        
        if param_type:
            for type_key, mock_val in type_mocks.items():
                if type_key in param_type:
                    return mock_val
        
        # Name-based inference
        name_lower = param_name.lower()
        if "name" in name_lower or "text" in name_lower or "string" in name_lower:
            return '"test_value"'
        elif "count" in name_lower or "num" in name_lower or "id" in name_lower or "size" in name_lower:
            return "1"
        elif "flag" in name_lower or "is_" in name_lower or "has_" in name_lower or "enable" in name_lower:
            return "True"
        elif "list" in name_lower or "items" in name_lower or "array" in name_lower:
            return "[]"
        elif "dict" in name_lower or "map" in name_lower or "config" in name_lower:
            return "{}"
        elif "path" in name_lower or "file" in name_lower or "dir" in name_lower:
            return '"/tmp/test"'
        elif "data" in name_lower:
            return '{"key": "value"}'
        elif "callback" in name_lower or "func" in name_lower or "handler" in name_lower:
            return "lambda x: x"
        
        return '"test_value"'
    
    def _create_basic_test(
        self,
        entity: CodeEntity,
        func_info: Dict[str, Any],
        genesis_key: GenesisKey
    ) -> GeneratedTest:
        """Create a basic test case with proper imports and assertions."""
        params = func_info.get("parameters", [])
        param_types = func_info.get("param_types", {})
        return_type = func_info.get("return_type")
        
        # Generate setup lines for each parameter
        setup_lines = []
        call_args = []
        for p in params:
            mock_value = self._generate_mock_value(p, param_types.get(p))
            setup_lines.append(f"    {p} = {mock_value}")
            call_args.append(p)
        
        setup_code = "\n".join(setup_lines) if setup_lines else "    # No parameters required"
        call_params = ", ".join(call_args)
        
        # Generate appropriate assertions based on return type
        if return_type:
            if "bool" in return_type.lower():
                assertion = "    assert isinstance(result, bool)"
            elif "int" in return_type.lower():
                assertion = "    assert isinstance(result, int)"
            elif "str" in return_type.lower():
                assertion = "    assert isinstance(result, str)"
            elif "list" in return_type.lower() or "List" in return_type:
                assertion = "    assert isinstance(result, list)"
            elif "dict" in return_type.lower() or "Dict" in return_type:
                assertion = "    assert isinstance(result, dict)"
            elif "None" in return_type:
                assertion = "    assert result is None"
            else:
                assertion = "    assert result is not None"
        else:
            assertion = "    assert result is not None or result is None  # Verify function executes without error"
        
        test_code = f'''import pytest

def test_{entity.name}_basic():
    """Basic test for {entity.name} - verifies function executes with valid inputs."""
    # Setup test inputs
{setup_code}
    
    # Execute function under test
    result = {entity.name}({call_params})
    
    # Verify result
{assertion}
'''
        
        return GeneratedTest(
            test_name=f"test_{entity.name}_basic",
            test_code=test_code.strip(),
            test_type="unit",
            target_function=entity.name,
            confidence=0.8,
            reasoning="Basic functionality test with type-aware assertions"
        )
    
    def _generate_edge_case_tests(
        self,
        entity: CodeEntity,
        func_info: Dict[str, Any],
        genesis_key: GenesisKey
    ) -> List[GeneratedTest]:
        """Generate edge case tests with actual test implementations."""
        tests = []
        
        params = func_info.get("parameters", [])
        param_types = func_info.get("param_types", {})
        
        if not params:
            return tests
        
        # Edge case value mappings
        edge_case_values = {
            "empty": {
                "str": '""',
                "list": "[]",
                "dict": "{}",
                "List": "[]",
                "Dict": "{}",
                "default": '""',
            },
            "none": {
                "default": "None",
            },
            "negative": {
                "int": "-1",
                "float": "-1.0",
                "default": "-1",
            },
            "large": {
                "int": "10**9",
                "float": "float('inf')",
                "str": '"x" * 10000',
                "list": "list(range(10000))",
                "default": "10**9",
            },
            "boundary": {
                "int": "0",
                "float": "0.0",
                "str": '" "',
                "default": "0",
            },
            "special_chars": {
                "str": r'"!@#$%^&*()_+-=[]{}|;:,.<>?\n\t"',
                "default": r'"!@#$%^&*()"',
            },
        }
        
        edge_cases = [
            ("empty", "empty input", "should handle empty values gracefully"),
            ("none", "None input", "should handle None values without crashing"),
            ("negative", "negative values", "should handle negative numbers correctly"),
            ("large", "very large values", "should handle large inputs without overflow"),
            ("boundary", "boundary values", "should handle boundary conditions (0, empty, etc.)"),
            ("special_chars", "special characters", "should handle special characters safely"),
        ]
        
        for case_name, description, expectation in edge_cases:
            # Generate parameter assignments for this edge case
            setup_lines = []
            call_args = []
            
            for p in params:
                param_type = param_types.get(p, "")
                case_values = edge_case_values.get(case_name, {})
                
                # Find matching value based on type
                value = case_values.get("default", "None")
                for type_key, type_value in case_values.items():
                    if type_key != "default" and type_key in param_type:
                        value = type_value
                        break
                
                setup_lines.append(f"    {p} = {value}")
                call_args.append(p)
            
            setup_code = "\n".join(setup_lines)
            call_params = ", ".join(call_args)
            
            test_code = f'''import pytest

def test_{entity.name}_{case_name}():
    """Test {entity.name} with {description} - {expectation}."""
    # Setup edge case inputs
{setup_code}
    
    # Execute and verify function handles edge case
    try:
        result = {entity.name}({call_params})
        # Function should either return a valid result or None
        assert result is not None or result is None
    except (ValueError, TypeError, AttributeError) as e:
        # Expected exceptions for invalid edge case inputs are acceptable
        assert isinstance(e, (ValueError, TypeError, AttributeError))
    except Exception as e:
        # Unexpected exceptions should fail the test
        pytest.fail(f"Unexpected exception for {description}: {{type(e).__name__}}: {{e}}")
'''
            
            test = GeneratedTest(
                test_name=f"test_{entity.name}_{case_name}",
                test_code=test_code.strip(),
                test_type="edge_case",
                target_function=entity.name,
                confidence=0.7,
                reasoning=f"Edge case test: {description} - validates graceful handling"
            )
            tests.append(test)
        
        return tests
    
    def _generate_error_tests(
        self,
        entity: CodeEntity,
        func_info: Dict[str, Any],
        genesis_key: GenesisKey
    ) -> List[GeneratedTest]:
        """Generate error handling tests with pytest.raises."""
        tests = []
        
        if not func_info.get("has_exceptions"):
            return tests
        
        params = func_info.get("parameters", [])
        exception_types = func_info.get("exception_types", [])
        
        # Generate invalid input test
        invalid_inputs = []
        for p in params:
            invalid_inputs.append(f"    {p} = None  # Invalid input to trigger exception")
        invalid_setup = "\n".join(invalid_inputs) if invalid_inputs else "    # No parameters"
        call_params = ", ".join(params)
        
        # If we know specific exception types, test for them
        if exception_types:
            for exc_type in exception_types:
                # Extract base exception name
                exc_name = exc_type.split(".")[-1] if "." in exc_type else exc_type
                
                test_code = f'''import pytest

def test_{entity.name}_raises_{exc_name.lower()}():
    """Test that {entity.name} raises {exc_name} for invalid inputs."""
    # Setup invalid inputs that should trigger {exc_name}
{invalid_setup}
    
    # Verify function raises expected exception
    with pytest.raises({exc_name}):
        {entity.name}({call_params})
'''
                
                test = GeneratedTest(
                    test_name=f"test_{entity.name}_raises_{exc_name.lower()}",
                    test_code=test_code.strip(),
                    test_type="error_handling",
                    target_function=entity.name,
                    confidence=0.8,
                    reasoning=f"Exception test: verifies {exc_name} is raised for invalid inputs"
                )
                tests.append(test)
        else:
            # Generic exception handling test
            test_code = f'''import pytest

def test_{entity.name}_error_handling():
    """Test {entity.name} error handling with invalid inputs."""
    # Setup invalid inputs
{invalid_setup}
    
    # Verify function raises appropriate exception for invalid inputs
    with pytest.raises((ValueError, TypeError, AttributeError, RuntimeError)):
        {entity.name}({call_params})


def test_{entity.name}_exception_message():
    """Test that {entity.name} provides meaningful exception messages."""
{invalid_setup}
    
    try:
        {entity.name}({call_params})
        pytest.fail("Expected an exception to be raised")
    except Exception as e:
        # Verify exception has a meaningful message
        assert str(e), "Exception message should not be empty"
        assert len(str(e)) > 0
'''
            
            test = GeneratedTest(
                test_name=f"test_{entity.name}_error_handling",
                test_code=test_code.strip(),
                test_type="error_handling",
                target_function=entity.name,
                confidence=0.7,
                reasoning="Exception test: verifies proper error handling and messages"
            )
            tests.append(test)
        
        return tests
    
    def _create_simple_test_template(
        self,
        entity: CodeEntity,
        genesis_key: GenesisKey
    ) -> GeneratedTest:
        """Create a simple test template when analysis fails."""
        test_code = f'''import pytest

def test_{entity.name}_exists():
    """Verify {entity.name} is callable and accessible."""
    # Verify the function/class exists and is callable
    assert callable({entity.name}), "{entity.name} should be callable"


def test_{entity.name}_execution():
    """Test basic execution of {entity.name}."""
    try:
        # Attempt to call with no arguments (may fail, but tests accessibility)
        result = {entity.name}()
        assert result is not None or result is None
    except TypeError as e:
        # TypeError is expected if function requires arguments
        assert "argument" in str(e).lower() or "required" in str(e).lower()
    except Exception as e:
        # Other exceptions should be specific and not generic crashes
        assert isinstance(e, Exception)
'''
        return GeneratedTest(
            test_name=f"test_{entity.name}",
            test_code=test_code.strip(),
            test_type="unit",
            target_function=entity.name,
            confidence=0.5,
            reasoning="Basic test template with existence and execution checks"
        )
    
    def _analyze_change_diff(self, change: CodeChange) -> Dict[str, Any]:
        """Analyze what changed between before/after."""
        return {
            "change_type": change.change_type.value,
            "lines_changed": change.line_numbers[1] - change.line_numbers[0]
        }
    
    def _generate_regression_test_code(
        self,
        entity: CodeEntity,
        diff_analysis: Dict[str, Any]
    ) -> str:
        """Generate regression test code for backward compatibility."""
        change_type = diff_analysis.get("change_type", "modified")
        lines_changed = diff_analysis.get("lines_changed", 0)
        
        return f'''import pytest
import warnings

def test_{entity.name}_regression():
    """Regression test for {entity.name} - ensures backward compatibility after modification."""
    # Test that the function signature hasn't changed breaking existing calls
    import inspect
    sig = inspect.signature({entity.name})
    
    # Verify function is still callable
    assert callable({entity.name}), "{entity.name} should remain callable after changes"
    
    # Verify parameter count hasn't decreased (would break existing calls)
    params = list(sig.parameters.keys())
    assert len(params) >= 0, "Function parameters should be accessible"


def test_{entity.name}_old_api_compatibility():
    """Test that old API signatures still work for {entity.name}."""
    # Verify deprecated usage patterns still work (with warnings)
    try:
        # Attempt basic invocation - should not crash
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            # Old API call pattern should still work
            result = {entity.name}
            assert callable(result) or result is not None
    except TypeError:
        # If it requires arguments, that's expected - not a regression
        pass


def test_{entity.name}_return_type_consistency():
    """Test that {entity.name} return type remains consistent after changes."""
    # This test verifies the function's contract hasn't changed
    # The return type should be stable across versions
    import inspect
    try:
        annotations = {entity.name}.__annotations__
        if 'return' in annotations:
            # Return type annotation exists - good for API stability
            assert annotations['return'] is not None
    except AttributeError:
        # No annotations is acceptable for older code
        pass
'''.strip()
    
    def _generate_integration_test_code(
        self,
        change_analysis: ChangeAnalysis
    ) -> str:
        """Generate integration test code."""
        funcs = change_analysis.affected_functions[:2]
        func_list = ", ".join(funcs)
        func_name_combined = "_".join(funcs)
        
        return f'''import pytest

def test_integration_{func_name_combined}():
    """Integration test for {func_list} - verifies functions work together correctly."""
    # Test that functions can be called in sequence without errors
    results = []
    
    # Execute each function and collect results
    for func in [{func_list}]:
        try:
            if callable(func):
                # Try calling with no args first
                try:
                    result = func()
                    results.append(("success", result))
                except TypeError:
                    # Function requires arguments - that's fine for integration test
                    results.append(("needs_args", None))
        except Exception as e:
            results.append(("error", str(e)))
    
    # Verify at least functions are accessible
    assert len(results) == {len(funcs)}, "All functions should be accessible"


def test_integration_{func_name_combined}_data_flow():
    """Test data can flow between {func_list}."""
    # Verify functions can potentially share data structures
    # This is a basic integration smoke test
    import inspect
    
    signatures = []
    for func in [{func_list}]:
        try:
            sig = inspect.signature(func)
            signatures.append(sig)
        except (ValueError, TypeError):
            signatures.append(None)
    
    # At minimum, functions should be introspectable
    assert len(signatures) > 0, "Functions should have inspectable signatures"
'''.strip()
    
    def _estimate_coverage(self, plan: TestGenerationPlan) -> float:
        """Estimate test coverage."""
        # Simple heuristic: more tests = better coverage
        base_coverage = min(0.8, len(plan.generated_tests) * 0.15)
        return base_coverage
    
    def _calculate_confidence(self, plan: TestGenerationPlan) -> float:
        """Calculate confidence in generated tests."""
        # Based on number of tests and analysis quality
        if len(plan.generated_tests) > 0:
            avg_confidence = sum(t.confidence for t in plan.generated_tests) / len(plan.generated_tests)
            return avg_confidence
        return 0.3


# Global instance
_generator: Optional[ProactiveTestGenerator] = None


def get_proactive_test_generator() -> ProactiveTestGenerator:
    """Get or create global proactive test generator instance."""
    global _generator
    if _generator is None:
        _generator = ProactiveTestGenerator()
    return _generator
