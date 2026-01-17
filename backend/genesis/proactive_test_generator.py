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
            "return_type": None,
            "has_exceptions": False,
            "complexity": 0
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func_name:
                info["parameters"] = [arg.arg for arg in node.args.args]
                
                # Check for exceptions
                for child in ast.walk(node):
                    if isinstance(child, (ast.Raise, ast.Try)):
                        info["has_exceptions"] = True
                
                break
        
        return info
    
    def _create_basic_test(
        self,
        entity: CodeEntity,
        func_info: Dict[str, Any],
        genesis_key: GenesisKey
    ) -> GeneratedTest:
        """Create a basic test case."""
        params = func_info.get("parameters", [])
        param_values = ", ".join([f"{p}=mock_{p}" for p in params])
        
        test_code = f"""
def test_{entity.name}_basic():
    \"\"\"Basic test for {entity.name}.\"\"\"
    # TODO: Implement test
    # Expected: Function should work with valid inputs
    result = {entity.name}({param_values})
    assert result is not None
"""
        
        return GeneratedTest(
            test_name=f"test_{entity.name}_basic",
            test_code=test_code.strip(),
            test_type="unit",
            target_function=entity.name,
            confidence=0.6,
            reasoning="Basic functionality test"
        )
    
    def _generate_edge_case_tests(
        self,
        entity: CodeEntity,
        func_info: Dict[str, Any],
        genesis_key: GenesisKey
    ) -> List[GeneratedTest]:
        """Generate edge case tests."""
        tests = []
        
        params = func_info.get("parameters", [])
        
        # Generate edge cases
        edge_cases = [
            ("empty", "Empty input"),
            ("none", "None input"),
            ("negative", "Negative values"),
            ("large", "Very large values"),
        ]
        
        for case_name, description in edge_cases:
            test = GeneratedTest(
                test_name=f"test_{entity.name}_{case_name}",
                test_code=f"""
def test_{entity.name}_{case_name}():
    \"\"\"Test {entity.name} with {description.lower()}.\"\"\"
    # TODO: Implement edge case test
    # Expected: Function should handle {description.lower()} gracefully
    pass
""".strip(),
                test_type="edge_case",
                target_function=entity.name,
                confidence=0.5,
                reasoning=f"Edge case: {description}"
            )
            tests.append(test)
        
        return tests
    
    def _generate_error_tests(
        self,
        entity: CodeEntity,
        func_info: Dict[str, Any],
        genesis_key: GenesisKey
    ) -> List[GeneratedTest]:
        """Generate error handling tests."""
        tests = []
        
        if func_info.get("has_exceptions"):
            test = GeneratedTest(
                test_name=f"test_{entity.name}_error_handling",
                test_code=f"""
def test_{entity.name}_error_handling():
    \"\"\"Test {entity.name} error handling.\"\"\"
    # TODO: Test that function raises appropriate exceptions
    # Expected: Function should raise specific exceptions for invalid inputs
    pass
""".strip(),
                test_type="error_handling",
                target_function=entity.name,
                confidence=0.5,
                reasoning="Error handling test"
            )
            tests.append(test)
        
        return tests
    
    def _create_simple_test_template(
        self,
        entity: CodeEntity,
        genesis_key: GenesisKey
    ) -> GeneratedTest:
        """Create a simple test template when analysis fails."""
        return GeneratedTest(
            test_name=f"test_{entity.name}",
            test_code=f"""
def test_{entity.name}():
    \"\"\"Test for {entity.name}.\"\"\"
    # TODO: Implement test
    pass
""".strip(),
            test_type="unit",
            target_function=entity.name,
            confidence=0.3,
            reasoning="Basic test template"
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
        """Generate regression test code."""
        return f"""
def test_{entity.name}_regression():
    \"\"\"Regression test for {entity.name}.\"\"\"
    # TODO: Test that modified function maintains backward compatibility
    # Expected: Function should still work with existing use cases
    pass
""".strip()
    
    def _generate_integration_test_code(
        self,
        change_analysis: ChangeAnalysis
    ) -> str:
        """Generate integration test code."""
        funcs = change_analysis.affected_functions[:2]
        return f"""
def test_integration_{'_'.join(funcs)}():
    \"\"\"Integration test for {', '.join(funcs)}.\"\"\"
    # TODO: Test interaction between {', '.join(funcs)}
    # Expected: Functions should work together correctly
    pass
""".strip()
    
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
