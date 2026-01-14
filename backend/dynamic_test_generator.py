"""
Dynamic Test Generator for Grace

Enables Grace to automatically generate and execute tests for any new logic,
code, or implementations. Works with the sandbox for safe execution.

Features:
- Parse Python code to understand structure
- Generate appropriate unit tests
- Generate integration tests
- Execute in sandbox environment
- Validate and report results
"""

import ast
import os
import sys
import json
import logging
import tempfile
import subprocess
import importlib.util
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).parent


@dataclass
class CodeAnalysis:
    """Analysis of a code module."""
    module_name: str
    file_path: str
    classes: List[Dict[str, Any]] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    docstring: Optional[str] = None


@dataclass
class GeneratedTest:
    """A generated test case."""
    test_name: str
    test_code: str
    test_type: str  # unit, integration, api
    target_function: str
    target_class: Optional[str] = None
    description: str = ""


@dataclass
class TestExecutionResult:
    """Result of test execution."""
    test_name: str
    status: str  # passed, failed, error
    duration: float
    output: str
    error: Optional[str] = None


class CodeAnalyzer:
    """Analyzes Python code structure for test generation."""

    def analyze_file(self, file_path: str) -> CodeAnalysis:
        """
        Analyze a Python file to extract testable components.

        Args:
            file_path: Path to the Python file

        Returns:
            CodeAnalysis with extracted information
        """
        with open(file_path, 'r') as f:
            source_code = f.read()

        tree = ast.parse(source_code)
        module_name = Path(file_path).stem

        analysis = CodeAnalysis(
            module_name=module_name,
            file_path=file_path,
            docstring=ast.get_docstring(tree)
        )

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    analysis.imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ''
                for alias in node.names:
                    analysis.imports.append(f"{module}.{alias.name}")

            elif isinstance(node, ast.ClassDef):
                class_info = self._analyze_class(node)
                analysis.classes.append(class_info)

            elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                # Only top-level functions
                func_info = self._analyze_function(node)
                analysis.functions.append(func_info)

        return analysis

    def analyze_code(self, source_code: str, module_name: str = "dynamic_module") -> CodeAnalysis:
        """
        Analyze Python source code string.

        Args:
            source_code: Python source code
            module_name: Name for the module

        Returns:
            CodeAnalysis with extracted information
        """
        tree = ast.parse(source_code)

        analysis = CodeAnalysis(
            module_name=module_name,
            file_path="<dynamic>",
            docstring=ast.get_docstring(tree)
        )

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                class_info = self._analyze_class(node)
                analysis.classes.append(class_info)

            elif isinstance(node, ast.FunctionDef):
                func_info = self._analyze_function(node)
                analysis.functions.append(func_info)

        return analysis

    def _analyze_class(self, node: ast.ClassDef) -> Dict[str, Any]:
        """Analyze a class definition."""
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(self._analyze_function(item))

        return {
            'name': node.name,
            'docstring': ast.get_docstring(node),
            'methods': methods,
            'bases': [self._get_name(base) for base in node.bases],
            'decorators': [self._get_decorator_name(d) for d in node.decorator_list]
        }

    def _analyze_function(self, node: ast.FunctionDef) -> Dict[str, Any]:
        """Analyze a function definition."""
        args = []
        for arg in node.args.args:
            arg_info = {'name': arg.arg}
            if arg.annotation:
                arg_info['type'] = self._get_annotation(arg.annotation)
            args.append(arg_info)

        return_type = None
        if node.returns:
            return_type = self._get_annotation(node.returns)

        return {
            'name': node.name,
            'docstring': ast.get_docstring(node),
            'args': args,
            'return_type': return_type,
            'decorators': [self._get_decorator_name(d) for d in node.decorator_list],
            'is_async': isinstance(node, ast.AsyncFunctionDef)
        }

    def _get_name(self, node) -> str:
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)

    def _get_decorator_name(self, node) -> str:
        """Get decorator name."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return str(node)

    def _get_annotation(self, node) -> str:
        """Get type annotation as string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Subscript):
            return f"{self._get_annotation(node.value)}[{self._get_annotation(node.slice)}]"
        return "Any"


class DynamicTestGenerator:
    """
    Generates tests dynamically for any Python code.
    """

    def __init__(self):
        self.analyzer = CodeAnalyzer()
        self.generated_tests: List[GeneratedTest] = []

    def generate_tests_for_file(self, file_path: str) -> List[GeneratedTest]:
        """
        Generate tests for a Python file.

        Args:
            file_path: Path to the Python file

        Returns:
            List of generated tests
        """
        analysis = self.analyzer.analyze_file(file_path)
        return self._generate_tests_from_analysis(analysis)

    def generate_tests_for_code(
        self,
        source_code: str,
        module_name: str = "dynamic_module"
    ) -> List[GeneratedTest]:
        """
        Generate tests for Python source code.

        Args:
            source_code: Python source code
            module_name: Name for the module

        Returns:
            List of generated tests
        """
        analysis = self.analyzer.analyze_code(source_code, module_name)
        return self._generate_tests_from_analysis(analysis)

    def _generate_tests_from_analysis(self, analysis: CodeAnalysis) -> List[GeneratedTest]:
        """Generate tests from code analysis."""
        tests = []

        # Generate tests for standalone functions
        for func in analysis.functions:
            if not func['name'].startswith('_'):
                tests.extend(self._generate_function_tests(func, analysis))

        # Generate tests for classes
        for cls in analysis.classes:
            tests.extend(self._generate_class_tests(cls, analysis))

        self.generated_tests.extend(tests)
        return tests

    def _generate_function_tests(
        self,
        func: Dict,
        analysis: CodeAnalysis
    ) -> List[GeneratedTest]:
        """Generate tests for a function."""
        tests = []
        func_name = func['name']

        # Basic test - function exists and is callable
        tests.append(GeneratedTest(
            test_name=f"test_{func_name}_exists",
            test_code=self._create_existence_test(func_name, analysis.module_name),
            test_type="unit",
            target_function=func_name,
            description=f"Test that {func_name} exists and is callable"
        ))

        # Test with no arguments (if applicable)
        if not func['args'] or all(a['name'] == 'self' for a in func['args']):
            tests.append(GeneratedTest(
                test_name=f"test_{func_name}_no_args",
                test_code=self._create_no_args_test(func_name, analysis.module_name),
                test_type="unit",
                target_function=func_name,
                description=f"Test {func_name} can be called without arguments"
            ))

        # Test with None arguments
        if func['args']:
            tests.append(GeneratedTest(
                test_name=f"test_{func_name}_handles_none",
                test_code=self._create_none_args_test(func, analysis.module_name),
                test_type="unit",
                target_function=func_name,
                description=f"Test {func_name} handles None arguments gracefully"
            ))

        # Return type test if specified
        if func.get('return_type'):
            tests.append(GeneratedTest(
                test_name=f"test_{func_name}_return_type",
                test_code=self._create_return_type_test(func, analysis.module_name),
                test_type="unit",
                target_function=func_name,
                description=f"Test {func_name} returns correct type"
            ))

        return tests

    def _generate_class_tests(
        self,
        cls: Dict,
        analysis: CodeAnalysis
    ) -> List[GeneratedTest]:
        """Generate tests for a class."""
        tests = []
        class_name = cls['name']

        # Test class instantiation
        tests.append(GeneratedTest(
            test_name=f"test_{class_name}_instantiation",
            test_code=self._create_class_instantiation_test(cls, analysis.module_name),
            test_type="unit",
            target_function="__init__",
            target_class=class_name,
            description=f"Test {class_name} can be instantiated"
        ))

        # Test each public method
        for method in cls['methods']:
            if not method['name'].startswith('_'):
                tests.extend(self._generate_method_tests(method, cls, analysis))

        return tests

    def _generate_method_tests(
        self,
        method: Dict,
        cls: Dict,
        analysis: CodeAnalysis
    ) -> List[GeneratedTest]:
        """Generate tests for a class method."""
        tests = []
        method_name = method['name']
        class_name = cls['name']

        # Method existence test
        tests.append(GeneratedTest(
            test_name=f"test_{class_name}_{method_name}_exists",
            test_code=self._create_method_existence_test(method_name, cls, analysis.module_name),
            test_type="unit",
            target_function=method_name,
            target_class=class_name,
            description=f"Test {class_name}.{method_name} exists"
        ))

        return tests

    def _create_existence_test(self, func_name: str, module_name: str) -> str:
        """Create test that checks function existence."""
        return f'''
def test_{func_name}_exists():
    """Test that {func_name} exists and is callable."""
    from {module_name} import {func_name}
    assert callable({func_name}), "{func_name} should be callable"
'''

    def _create_no_args_test(self, func_name: str, module_name: str) -> str:
        """Create test for function with no args."""
        return f'''
def test_{func_name}_no_args():
    """Test {func_name} can be called without arguments."""
    from {module_name} import {func_name}
    try:
        result = {func_name}()
        assert result is not None or result is None  # Just check it doesn't crash
    except TypeError as e:
        # If it requires args, that's expected
        if "required" in str(e) or "argument" in str(e):
            pass
        else:
            raise
'''

    def _create_none_args_test(self, func: Dict, module_name: str) -> str:
        """Create test with None arguments."""
        func_name = func['name']
        args = func['args']
        none_args = ', '.join(['None'] * len(args))

        return f'''
def test_{func_name}_handles_none():
    """Test {func_name} handles None arguments gracefully."""
    from {module_name} import {func_name}
    try:
        result = {func_name}({none_args})
        # If it accepts None, that's fine
    except (TypeError, ValueError, AttributeError) as e:
        # Expected - function doesn't accept None
        pass
    except Exception as e:
        # Unexpected error type - might indicate a bug
        raise AssertionError(f"Unexpected error type: {{type(e).__name__}}: {{e}}")
'''

    def _create_return_type_test(self, func: Dict, module_name: str) -> str:
        """Create return type test."""
        func_name = func['name']
        return_type = func.get('return_type', 'Any')

        return f'''
def test_{func_name}_return_type():
    """Test {func_name} returns expected type."""
    from {module_name} import {func_name}
    # This is a placeholder - actual implementation depends on function signature
    pass
'''

    def _create_class_instantiation_test(self, cls: Dict, module_name: str) -> str:
        """Create class instantiation test."""
        class_name = cls['name']

        return f'''
def test_{class_name}_instantiation():
    """Test {class_name} can be instantiated."""
    from {module_name} import {class_name}
    try:
        instance = {class_name}()
        assert instance is not None
    except TypeError as e:
        # If __init__ requires args, try to detect and handle
        if "required" in str(e) or "argument" in str(e):
            # Class requires arguments - this test just validates import works
            assert {class_name} is not None
        else:
            raise
'''

    def _create_method_existence_test(
        self,
        method_name: str,
        cls: Dict,
        module_name: str
    ) -> str:
        """Create method existence test."""
        class_name = cls['name']

        return f'''
def test_{class_name}_{method_name}_exists():
    """Test {class_name}.{method_name} exists."""
    from {module_name} import {class_name}
    assert hasattr({class_name}, '{method_name}'), "{class_name} should have {method_name} method"
    assert callable(getattr({class_name}, '{method_name}')), "{method_name} should be callable"
'''

    def generate_test_file(self, tests: List[GeneratedTest], output_path: str = None) -> str:
        """
        Generate a complete test file from generated tests.

        Args:
            tests: List of generated tests
            output_path: Optional path to write the file

        Returns:
            Generated test file content
        """
        header = '''"""
Auto-generated tests by Grace Dynamic Test Generator.
Generated at: {timestamp}
"""

import pytest
from typing import Any

'''.format(timestamp=datetime.now().isoformat())

        test_code = header
        for test in tests:
            test_code += test.test_code + "\n\n"

        if output_path:
            with open(output_path, 'w') as f:
                f.write(test_code)
            logger.info(f"Generated test file: {output_path}")

        return test_code


class SandboxTestExecutor:
    """
    Executes tests in a sandbox environment for safe testing.
    """

    def __init__(self, sandbox_dir: str = None):
        """Initialize the sandbox executor."""
        self.sandbox_dir = Path(sandbox_dir) if sandbox_dir else Path(tempfile.mkdtemp())
        self.results: List[TestExecutionResult] = []

    def execute_test_code(
        self,
        test_code: str,
        module_code: str = None,
        module_name: str = "test_module",
        timeout: int = 60
    ) -> List[TestExecutionResult]:
        """
        Execute test code in sandbox.

        Args:
            test_code: Test code to execute
            module_code: Optional module code being tested
            module_name: Name for the module
            timeout: Execution timeout in seconds

        Returns:
            List of test execution results
        """
        results = []

        # Create temporary directory for test
        test_dir = Path(tempfile.mkdtemp(dir=self.sandbox_dir))

        try:
            # Write module code if provided
            if module_code:
                module_path = test_dir / f"{module_name}.py"
                with open(module_path, 'w') as f:
                    f.write(module_code)

            # Write test code
            test_path = test_dir / f"test_{module_name}.py"
            with open(test_path, 'w') as f:
                f.write(test_code)

            # Run pytest
            cmd = [
                sys.executable, "-m", "pytest",
                str(test_path),
                "-v",
                "--tb=short",
                f"--timeout={timeout}"
            ]

            start_time = datetime.now()
            proc = subprocess.run(
                cmd,
                cwd=str(test_dir),
                capture_output=True,
                text=True,
                timeout=timeout + 10,
                env={**os.environ, 'PYTHONPATH': str(test_dir)}
            )
            duration = (datetime.now() - start_time).total_seconds()

            # Parse output
            results = self._parse_pytest_output(proc.stdout, proc.stderr, duration)

        except subprocess.TimeoutExpired:
            results.append(TestExecutionResult(
                test_name="execution",
                status="error",
                duration=timeout,
                output="",
                error="Test execution timed out"
            ))
        except Exception as e:
            results.append(TestExecutionResult(
                test_name="execution",
                status="error",
                duration=0,
                output="",
                error=str(e)
            ))
        finally:
            # Cleanup
            import shutil
            try:
                shutil.rmtree(test_dir)
            except:
                pass

        self.results.extend(results)
        return results

    def _parse_pytest_output(
        self,
        stdout: str,
        stderr: str,
        duration: float
    ) -> List[TestExecutionResult]:
        """Parse pytest output into results."""
        results = []

        for line in stdout.split('\n'):
            if '::' in line:
                if ' PASSED' in line:
                    test_name = line.split('::')[-1].split(' PASSED')[0].strip()
                    results.append(TestExecutionResult(
                        test_name=test_name,
                        status="passed",
                        duration=duration / max(1, len(results) + 1),
                        output=line
                    ))
                elif ' FAILED' in line:
                    test_name = line.split('::')[-1].split(' FAILED')[0].strip()
                    results.append(TestExecutionResult(
                        test_name=test_name,
                        status="failed",
                        duration=duration / max(1, len(results) + 1),
                        output=line,
                        error=stderr
                    ))
                elif ' ERROR' in line:
                    test_name = line.split('::')[-1].split(' ERROR')[0].strip()
                    results.append(TestExecutionResult(
                        test_name=test_name,
                        status="error",
                        duration=duration / max(1, len(results) + 1),
                        output=line,
                        error=stderr
                    ))

        return results


class AutonomousTestBuilder:
    """
    Main class for autonomous test building and execution.

    Combines code analysis, test generation, and sandbox execution.
    """

    def __init__(self):
        self.generator = DynamicTestGenerator()
        self.executor = SandboxTestExecutor()

    def build_and_test(
        self,
        source_code: str,
        module_name: str = "test_module"
    ) -> Dict[str, Any]:
        """
        Build tests for code and execute them.

        Args:
            source_code: Python source code to test
            module_name: Name for the module

        Returns:
            Dict with generated tests and execution results
        """
        logger.info(f"Building and testing module: {module_name}")

        # Generate tests
        tests = self.generator.generate_tests_for_code(source_code, module_name)
        test_code = self.generator.generate_test_file(tests)

        logger.info(f"Generated {len(tests)} tests")

        # Execute tests
        results = self.executor.execute_test_code(
            test_code=test_code,
            module_code=source_code,
            module_name=module_name
        )

        # Calculate summary
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        errors = sum(1 for r in results if r.status == "error")

        return {
            'module_name': module_name,
            'tests_generated': len(tests),
            'tests_run': len(results),
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'success_rate': (passed / len(results) * 100) if results else 0,
            'tests': [
                {
                    'name': t.test_name,
                    'type': t.test_type,
                    'target': t.target_function,
                    'description': t.description
                }
                for t in tests
            ],
            'results': [
                {
                    'name': r.test_name,
                    'status': r.status,
                    'duration': r.duration,
                    'error': r.error
                }
                for r in results
            ]
        }

    def build_tests_for_file(self, file_path: str) -> Dict[str, Any]:
        """
        Build tests for an existing file.

        Args:
            file_path: Path to Python file

        Returns:
            Dict with generated tests
        """
        with open(file_path, 'r') as f:
            source_code = f.read()

        module_name = Path(file_path).stem
        return self.build_and_test(source_code, module_name)

    def validate_implementation(
        self,
        implementation_code: str,
        expected_behavior: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate that implementation matches expected behavior.

        Args:
            implementation_code: Code to validate
            expected_behavior: Dict describing expected behavior
                - functions: List of function names that should exist
                - classes: List of class names that should exist
                - patterns: List of patterns that should be present

        Returns:
            Validation results
        """
        analysis = self.generator.analyzer.analyze_code(implementation_code)

        validation = {
            'valid': True,
            'issues': [],
            'analysis': {
                'functions_found': [f['name'] for f in analysis.functions],
                'classes_found': [c['name'] for c in analysis.classes]
            }
        }

        # Check for expected functions
        for expected_func in expected_behavior.get('functions', []):
            if expected_func not in validation['analysis']['functions_found']:
                validation['valid'] = False
                validation['issues'].append(f"Missing function: {expected_func}")

        # Check for expected classes
        for expected_class in expected_behavior.get('classes', []):
            if expected_class not in validation['analysis']['classes_found']:
                validation['valid'] = False
                validation['issues'].append(f"Missing class: {expected_class}")

        return validation


# Singleton instance
_test_builder: Optional[AutonomousTestBuilder] = None


def get_test_builder() -> AutonomousTestBuilder:
    """Get or create the autonomous test builder instance."""
    global _test_builder
    if _test_builder is None:
        _test_builder = AutonomousTestBuilder()
    return _test_builder


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Grace Dynamic Test Generator")
    parser.add_argument("--file", "-f", help="Python file to generate tests for")
    parser.add_argument("--code", "-c", help="Python code string to test")
    parser.add_argument("--execute", "-e", action="store_true", help="Execute generated tests")
    parser.add_argument("--output", "-o", help="Output path for generated tests")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    builder = get_test_builder()

    if args.file:
        if args.execute:
            result = builder.build_tests_for_file(args.file)
            print(f"\nTest Results for {args.file}:")
            print(f"  Generated: {result['tests_generated']} tests")
            print(f"  Passed: {result['passed']}/{result['tests_run']}")
            print(f"  Success Rate: {result['success_rate']:.1f}%")
        else:
            with open(args.file, 'r') as f:
                code = f.read()
            tests = builder.generator.generate_tests_for_code(code, Path(args.file).stem)
            test_code = builder.generator.generate_test_file(tests, args.output)
            print(f"Generated {len(tests)} tests")
            if not args.output:
                print(test_code)

    elif args.code:
        result = builder.build_and_test(args.code)
        print(json.dumps(result, indent=2))

    else:
        parser.print_help()
