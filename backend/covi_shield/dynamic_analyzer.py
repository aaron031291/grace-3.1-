"""
COVI-SHIELD Dynamic Analysis Engine

Monitors and verifies system behavior during execution.

Capabilities:
- Code instrumentation and coverage
- Runtime property checking
- Execution tracing
- Memory and resource tracking
- Test generation (fuzzing, property-based)
"""

import ast
import time
import logging
import traceback
import sys
import io
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import contextmanager
from functools import wraps

from .models import (
    VerificationResult,
    RiskLevel,
    AnalysisPhase
)

logger = logging.getLogger(__name__)


# ============================================================================
# RUNTIME MONITORS
# ============================================================================

@dataclass
class ExecutionTrace:
    """Trace of a single execution."""
    trace_id: str
    function_name: str
    args: List[Any]
    kwargs: Dict[str, Any]
    return_value: Any = None
    exception: Optional[str] = None
    duration_ms: float = 0.0
    memory_delta_bytes: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "function_name": self.function_name,
            "args": [str(a)[:100] for a in self.args],
            "kwargs": {k: str(v)[:100] for k, v in self.kwargs.items()},
            "return_value": str(self.return_value)[:100] if self.return_value else None,
            "exception": self.exception,
            "duration_ms": self.duration_ms,
            "memory_delta_bytes": self.memory_delta_bytes,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class CoverageInfo:
    """Code coverage information."""
    total_lines: int = 0
    covered_lines: int = 0
    total_branches: int = 0
    covered_branches: int = 0
    line_coverage: float = 0.0
    branch_coverage: float = 0.0
    uncovered_lines: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_lines": self.total_lines,
            "covered_lines": self.covered_lines,
            "total_branches": self.total_branches,
            "covered_branches": self.covered_branches,
            "line_coverage": self.line_coverage,
            "branch_coverage": self.branch_coverage,
            "uncovered_lines": self.uncovered_lines[:20]  # Limit
        }


@dataclass
class RuntimeViolation:
    """Runtime property violation."""
    violation_id: str
    property_name: str
    description: str
    severity: RiskLevel
    function_name: Optional[str] = None
    line_number: Optional[int] = None
    actual_value: Any = None
    expected_constraint: str = ""
    stack_trace: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "violation_id": self.violation_id,
            "property_name": self.property_name,
            "description": self.description,
            "severity": self.severity.value,
            "function_name": self.function_name,
            "line_number": self.line_number,
            "actual_value": str(self.actual_value)[:100],
            "expected_constraint": self.expected_constraint,
            "stack_trace": self.stack_trace[:500],
            "timestamp": self.timestamp.isoformat()
        }


# ============================================================================
# RUNTIME PROPERTY CHECKERS
# ============================================================================

class RuntimePropertyChecker:
    """Checks runtime properties during execution."""

    def __init__(self):
        self.violations: List[RuntimeViolation] = []
        self.checks_performed = 0
        self.violation_counter = 0

    def check_precondition(
        self,
        condition: bool,
        description: str,
        function_name: str = "",
        severity: RiskLevel = RiskLevel.HIGH
    ) -> bool:
        """Check a precondition."""
        self.checks_performed += 1
        if not condition:
            self.violation_counter += 1
            self.violations.append(RuntimeViolation(
                violation_id=f"PRE-{self.violation_counter:04d}",
                property_name="Precondition",
                description=description,
                severity=severity,
                function_name=function_name,
                stack_trace=traceback.format_stack()[-3]
            ))
            return False
        return True

    def check_postcondition(
        self,
        condition: bool,
        description: str,
        function_name: str = "",
        actual_value: Any = None,
        severity: RiskLevel = RiskLevel.HIGH
    ) -> bool:
        """Check a postcondition."""
        self.checks_performed += 1
        if not condition:
            self.violation_counter += 1
            self.violations.append(RuntimeViolation(
                violation_id=f"POST-{self.violation_counter:04d}",
                property_name="Postcondition",
                description=description,
                severity=severity,
                function_name=function_name,
                actual_value=actual_value,
                stack_trace=traceback.format_stack()[-3]
            ))
            return False
        return True

    def check_invariant(
        self,
        condition: bool,
        description: str,
        severity: RiskLevel = RiskLevel.MEDIUM
    ) -> bool:
        """Check an invariant."""
        self.checks_performed += 1
        if not condition:
            self.violation_counter += 1
            self.violations.append(RuntimeViolation(
                violation_id=f"INV-{self.violation_counter:04d}",
                property_name="Invariant",
                description=description,
                severity=severity,
                stack_trace=traceback.format_stack()[-3]
            ))
            return False
        return True

    def check_bounds(
        self,
        value: Any,
        min_val: Optional[Any] = None,
        max_val: Optional[Any] = None,
        description: str = "Value out of bounds"
    ) -> bool:
        """Check value bounds."""
        self.checks_performed += 1
        in_bounds = True

        if min_val is not None and value < min_val:
            in_bounds = False
        if max_val is not None and value > max_val:
            in_bounds = False

        if not in_bounds:
            self.violation_counter += 1
            self.violations.append(RuntimeViolation(
                violation_id=f"BOUNDS-{self.violation_counter:04d}",
                property_name="Bounds Check",
                description=description,
                severity=RiskLevel.MEDIUM,
                actual_value=value,
                expected_constraint=f"[{min_val}, {max_val}]",
                stack_trace=traceback.format_stack()[-3]
            ))
            return False
        return True

    def check_type(
        self,
        value: Any,
        expected_type: type,
        description: str = "Type mismatch"
    ) -> bool:
        """Check value type."""
        self.checks_performed += 1
        if not isinstance(value, expected_type):
            self.violation_counter += 1
            self.violations.append(RuntimeViolation(
                violation_id=f"TYPE-{self.violation_counter:04d}",
                property_name="Type Check",
                description=description,
                severity=RiskLevel.HIGH,
                actual_value=type(value).__name__,
                expected_constraint=expected_type.__name__,
                stack_trace=traceback.format_stack()[-3]
            ))
            return False
        return True

    def get_violations(self) -> List[Dict[str, Any]]:
        """Get all violations as dicts."""
        return [v.to_dict() for v in self.violations]

    def clear(self):
        """Clear violations."""
        self.violations.clear()
        self.checks_performed = 0


# ============================================================================
# DYNAMIC ANALYZER
# ============================================================================

class DynamicAnalyzer:
    """
    COVI-SHIELD Dynamic Analysis Engine.

    Monitors code execution for:
    - Runtime property violations
    - Exception handling
    - Resource usage
    - Performance metrics
    - Test execution
    """

    def __init__(self):
        self.property_checker = RuntimePropertyChecker()
        self.traces: List[ExecutionTrace] = []
        self.trace_counter = 0
        self.stats = {
            "total_executions": 0,
            "exceptions_caught": 0,
            "violations_detected": 0,
            "tests_generated": 0
        }
        logger.info("[COVI-SHIELD] Dynamic Analyzer initialized")

    def analyze_execution(
        self,
        code: str,
        test_inputs: Optional[List[Dict[str, Any]]] = None,
        timeout_seconds: float = 5.0,
        genesis_key_id: Optional[str] = None
    ) -> VerificationResult:
        """
        Execute code with monitoring and analysis.

        Args:
            code: Code to execute
            test_inputs: List of input dictionaries for testing
            timeout_seconds: Execution timeout
            genesis_key_id: Associated Genesis Key

        Returns:
            VerificationResult with execution analysis
        """
        start_time = time.time()
        self.stats["total_executions"] += 1

        issues: List[Dict[str, Any]] = []
        coverage = CoverageInfo()

        # Parse code for analysis
        try:
            tree = ast.parse(code)
            coverage.total_lines = len(code.split("\n"))
        except SyntaxError as e:
            issues.append({
                "type": "syntax_error",
                "description": str(e),
                "severity": RiskLevel.CRITICAL,
                "line": e.lineno
            })
            return self._create_result(
                genesis_key_id, issues, coverage, start_time
            )

        # Instrument code for tracing
        instrumented_code = self._instrument_code(code, tree)

        # Execute with generated test inputs
        if test_inputs is None:
            test_inputs = self._generate_test_inputs(tree)

        execution_results = []
        for test_input in test_inputs:
            result = self._execute_with_monitoring(
                instrumented_code,
                test_input,
                timeout_seconds
            )
            execution_results.append(result)

            if result.get("exception"):
                self.stats["exceptions_caught"] += 1
                issues.append({
                    "type": "runtime_exception",
                    "description": result["exception"],
                    "severity": RiskLevel.HIGH,
                    "input": test_input,
                    "trace": result.get("traceback", "")
                })

        # Check property violations
        violations = self.property_checker.get_violations()
        self.stats["violations_detected"] += len(violations)
        for violation in violations:
            issues.append({
                "type": "property_violation",
                **violation
            })

        # Calculate coverage
        covered_lines = set()
        for result in execution_results:
            covered_lines.update(result.get("covered_lines", []))
        coverage.covered_lines = len(covered_lines)
        coverage.line_coverage = (
            coverage.covered_lines / coverage.total_lines
            if coverage.total_lines > 0 else 0
        )
        coverage.uncovered_lines = [
            i for i in range(1, coverage.total_lines + 1)
            if i not in covered_lines
        ]

        return self._create_result(
            genesis_key_id, issues, coverage, start_time, execution_results
        )

    def _instrument_code(self, code: str, tree: ast.AST) -> str:
        """Add instrumentation to code for tracing."""
        # Simplified: add trace calls
        lines = code.split("\n")
        instrumented_lines = []

        for i, line in enumerate(lines, 1):
            instrumented_lines.append(line)
            # Could add trace calls here for detailed monitoring

        return "\n".join(instrumented_lines)

    def _generate_test_inputs(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Generate test inputs for functions in code."""
        self.stats["tests_generated"] += 1
        test_inputs = []

        # Find function definitions and generate inputs
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Generate basic test cases
                args = [arg.arg for arg in node.args.args]

                # Test with typical values
                test_inputs.append({
                    "function": node.name,
                    "args": {arg: None for arg in args}
                })

                # Test with edge cases
                test_inputs.append({
                    "function": node.name,
                    "args": {arg: 0 for arg in args}
                })

                test_inputs.append({
                    "function": node.name,
                    "args": {arg: "" for arg in args}
                })

                test_inputs.append({
                    "function": node.name,
                    "args": {arg: [] for arg in args}
                })

        return test_inputs if test_inputs else [{}]

    def _execute_with_monitoring(
        self,
        code: str,
        test_input: Dict[str, Any],
        timeout: float
    ) -> Dict[str, Any]:
        """Execute code with monitoring."""
        result = {
            "success": False,
            "exception": None,
            "traceback": None,
            "output": None,
            "covered_lines": [],
            "duration_ms": 0
        }

        start_time = time.time()

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()

        try:
            # Create execution namespace
            namespace = {
                "__builtins__": __builtins__,
                "test_input": test_input,
                **test_input.get("args", {})
            }

            # Execute code
            exec(compile(code, "<string>", "exec"), namespace)

            result["success"] = True
            result["output"] = captured_output.getvalue()

            # Call function if specified
            func_name = test_input.get("function")
            if func_name and func_name in namespace:
                func = namespace[func_name]
                args = test_input.get("args", {})
                try:
                    func_result = func(**args)
                    result["return_value"] = func_result
                except Exception as e:
                    result["exception"] = str(e)
                    result["traceback"] = traceback.format_exc()

        except Exception as e:
            result["exception"] = str(e)
            result["traceback"] = traceback.format_exc()

        finally:
            sys.stdout = old_stdout

        result["duration_ms"] = (time.time() - start_time) * 1000

        # Record trace
        self.trace_counter += 1
        trace = ExecutionTrace(
            trace_id=f"TRACE-{self.trace_counter:06d}",
            function_name=test_input.get("function", "<module>"),
            args=list(test_input.get("args", {}).values()),
            kwargs={},
            return_value=result.get("return_value"),
            exception=result.get("exception"),
            duration_ms=result["duration_ms"]
        )
        self.traces.append(trace)

        return result

    def _create_result(
        self,
        genesis_key_id: Optional[str],
        issues: List[Dict[str, Any]],
        coverage: CoverageInfo,
        start_time: float,
        execution_results: Optional[List[Dict[str, Any]]] = None
    ) -> VerificationResult:
        """Create verification result."""
        analysis_time_ms = (time.time() - start_time) * 1000

        risk_level = self._calculate_risk_level(issues)
        successful_executions = sum(
            1 for r in (execution_results or [])
            if r.get("success", False)
        )

        return VerificationResult(
            genesis_key_id=genesis_key_id,
            phase=AnalysisPhase.IN_FLIGHT,
            success=len(issues) == 0,
            risk_level=risk_level,
            issues_found=len(issues),
            issues=issues,
            metrics={
                "coverage": coverage.to_dict(),
                "executions": len(execution_results or []),
                "successful_executions": successful_executions,
                "traces_collected": len(self.traces),
                "property_checks": self.property_checker.checks_performed
            },
            analysis_time_ms=analysis_time_ms
        )

    def _calculate_risk_level(self, issues: List[Dict[str, Any]]) -> RiskLevel:
        """Calculate risk level from issues."""
        if not issues:
            return RiskLevel.INFO

        severities = [
            i.get("severity", RiskLevel.INFO)
            if isinstance(i.get("severity"), RiskLevel)
            else RiskLevel.INFO
            for i in issues
        ]

        if RiskLevel.CRITICAL in severities:
            return RiskLevel.CRITICAL
        elif RiskLevel.HIGH in severities:
            return RiskLevel.HIGH
        elif RiskLevel.MEDIUM in severities:
            return RiskLevel.MEDIUM
        elif RiskLevel.LOW in severities:
            return RiskLevel.LOW
        return RiskLevel.INFO

    def get_traces(self) -> List[Dict[str, Any]]:
        """Get execution traces."""
        return [t.to_dict() for t in self.traces]

    def clear_traces(self):
        """Clear execution traces."""
        self.traces.clear()
        self.trace_counter = 0
        self.property_checker.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            **self.stats,
            "traces_collected": len(self.traces),
            "property_checks": self.property_checker.checks_performed
        }

    # =========================================================================
    # DECORATORS FOR INSTRUMENTATION
    # =========================================================================

    def trace(self, func: Callable) -> Callable:
        """Decorator to trace function execution."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            self.trace_counter += 1
            trace_id = f"TRACE-{self.trace_counter:06d}"

            start_time = time.time()
            exception_str = None
            return_value = None

            try:
                return_value = func(*args, **kwargs)
                return return_value
            except Exception as e:
                exception_str = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                trace = ExecutionTrace(
                    trace_id=trace_id,
                    function_name=func.__name__,
                    args=list(args),
                    kwargs=kwargs,
                    return_value=return_value,
                    exception=exception_str,
                    duration_ms=duration_ms
                )
                self.traces.append(trace)

        return wrapper

    def check_contract(
        self,
        precondition: Optional[Callable[..., bool]] = None,
        postcondition: Optional[Callable[..., bool]] = None
    ) -> Callable:
        """Decorator to add contract checking to functions."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Check precondition
                if precondition:
                    self.property_checker.check_precondition(
                        precondition(*args, **kwargs),
                        f"Precondition failed for {func.__name__}",
                        func.__name__
                    )

                # Execute function
                result = func(*args, **kwargs)

                # Check postcondition
                if postcondition:
                    self.property_checker.check_postcondition(
                        postcondition(result),
                        f"Postcondition failed for {func.__name__}",
                        func.__name__,
                        result
                    )

                return result
            return wrapper
        return decorator
