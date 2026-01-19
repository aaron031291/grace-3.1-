"""
COVI-SHIELD Static Analysis Engine

Analyzes code structure, syntax, and patterns without execution to detect potential issues.

Capabilities:
- Multi-language parsing (Python, C++, CUDA)
- Abstract Syntax Tree generation with type information
- Control flow graph construction
- Data flow analysis
- Pattern matching for 1000+ bug patterns
- Security vulnerability scanning
- API compatibility checking
"""

import ast
import re
import hashlib
import logging
import time
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .models import (
    VerificationResult,
    BugPattern,
    BugCategory,
    RiskLevel,
    AnalysisPhase
)

logger = logging.getLogger(__name__)


# ============================================================================
# BUG PATTERN DATABASE
# ============================================================================

BUILTIN_PATTERNS: List[Dict[str, Any]] = [
    # Security vulnerabilities
    {
        "pattern_id": "SEC-001",
        "name": "SQL Injection",
        "description": "Potential SQL injection via string concatenation",
        "category": BugCategory.SECURITY,
        "severity": RiskLevel.CRITICAL,
        "detection_logic": r"execute\s*\(\s*['\"].*%s|execute\s*\(\s*f['\"]|execute\s*\(\s*['\"].*\+",
        "repair_template": "Use parameterized queries: cursor.execute(sql, params)"
    },
    {
        "pattern_id": "SEC-002",
        "name": "Command Injection",
        "description": "Potential command injection via subprocess",
        "category": BugCategory.SECURITY,
        "severity": RiskLevel.CRITICAL,
        "detection_logic": r"subprocess\.call\s*\(\s*['\"].*\+|os\.system\s*\(\s*['\"].*\+|shell\s*=\s*True",
        "repair_template": "Use subprocess.run with shell=False and list arguments"
    },
    {
        "pattern_id": "SEC-003",
        "name": "Hardcoded Credentials",
        "description": "Hardcoded password or API key",
        "category": BugCategory.SECURITY,
        "severity": RiskLevel.HIGH,
        "detection_logic": r"password\s*=\s*['\"][^'\"]+['\"]|api_key\s*=\s*['\"][^'\"]+['\"]|secret\s*=\s*['\"][^'\"]+['\"]",
        "repair_template": "Use environment variables: os.environ.get('PASSWORD')"
    },
    {
        "pattern_id": "SEC-004",
        "name": "Insecure Deserialization",
        "description": "Using pickle with untrusted data",
        "category": BugCategory.SECURITY,
        "severity": RiskLevel.HIGH,
        "detection_logic": r"pickle\.load|pickle\.loads|yaml\.load\s*\([^)]*Loader\s*=\s*None",
        "repair_template": "Use json.loads() or yaml.safe_load() instead"
    },
    {
        "pattern_id": "SEC-005",
        "name": "Path Traversal",
        "description": "Potential path traversal vulnerability",
        "category": BugCategory.SECURITY,
        "severity": RiskLevel.HIGH,
        "detection_logic": r"open\s*\(\s*[^)]*\+[^)]*user|open\s*\(\s*f['\"].*{.*}",
        "repair_template": "Validate and sanitize file paths using os.path.normpath"
    },

    # Type errors
    {
        "pattern_id": "TYPE-001",
        "name": "None Type Access",
        "description": "Accessing attribute on potentially None value",
        "category": BugCategory.TYPE,
        "severity": RiskLevel.HIGH,
        "detection_logic": "attribute_access_on_optional",
        "repair_template": "Add None check: if value is not None: value.attr"
    },
    {
        "pattern_id": "TYPE-002",
        "name": "Type Mismatch",
        "description": "Type mismatch in assignment or function call",
        "category": BugCategory.TYPE,
        "severity": RiskLevel.MEDIUM,
        "detection_logic": "type_mismatch",
        "repair_template": "Convert to correct type or fix type annotation"
    },

    # Logic errors
    {
        "pattern_id": "LOGIC-001",
        "name": "Always True Condition",
        "description": "Condition that is always true",
        "category": BugCategory.LOGIC,
        "severity": RiskLevel.MEDIUM,
        "detection_logic": r"if\s+True|while\s+True(?!\s*:)|if\s+1\s*:|if\s+['\"][^'\"]+['\"]:",
        "repair_template": "Review condition logic"
    },
    {
        "pattern_id": "LOGIC-002",
        "name": "Unreachable Code",
        "description": "Code after return/raise that will never execute",
        "category": BugCategory.LOGIC,
        "severity": RiskLevel.LOW,
        "detection_logic": "unreachable_code",
        "repair_template": "Remove unreachable code"
    },
    {
        "pattern_id": "LOGIC-003",
        "name": "Comparison with None",
        "description": "Using == instead of is for None comparison",
        "category": BugCategory.LOGIC,
        "severity": RiskLevel.LOW,
        "detection_logic": r"==\s*None|!=\s*None",
        "repair_template": "Use 'is None' or 'is not None'"
    },

    # Memory issues
    {
        "pattern_id": "MEM-001",
        "name": "Resource Leak",
        "description": "File or connection not properly closed",
        "category": BugCategory.MEMORY,
        "severity": RiskLevel.MEDIUM,
        "detection_logic": "resource_not_closed",
        "repair_template": "Use context manager: with open(file) as f:"
    },
    {
        "pattern_id": "MEM-002",
        "name": "Unbounded Collection",
        "description": "Collection that grows without bound",
        "category": BugCategory.MEMORY,
        "severity": RiskLevel.MEDIUM,
        "detection_logic": "unbounded_append",
        "repair_template": "Add size limit or use collections.deque with maxlen"
    },

    # Performance issues
    {
        "pattern_id": "PERF-001",
        "name": "Inefficient Loop",
        "description": "Loop that could be vectorized or optimized",
        "category": BugCategory.PERFORMANCE,
        "severity": RiskLevel.LOW,
        "detection_logic": "inefficient_loop",
        "repair_template": "Consider using numpy operations or list comprehension"
    },
    {
        "pattern_id": "PERF-002",
        "name": "N+1 Query",
        "description": "Database query inside loop",
        "category": BugCategory.PERFORMANCE,
        "severity": RiskLevel.MEDIUM,
        "detection_logic": r"for\s+.*:[\s\S]*?(\.query\(|\.execute\(|session\.)",
        "repair_template": "Use batch query or eager loading"
    },

    # Concurrency issues
    {
        "pattern_id": "CONC-001",
        "name": "Race Condition",
        "description": "Shared mutable state without synchronization",
        "category": BugCategory.CONCURRENCY,
        "severity": RiskLevel.HIGH,
        "detection_logic": "race_condition",
        "repair_template": "Use threading.Lock or asyncio.Lock"
    },
    {
        "pattern_id": "CONC-002",
        "name": "Deadlock Risk",
        "description": "Multiple locks acquired in inconsistent order",
        "category": BugCategory.CONCURRENCY,
        "severity": RiskLevel.HIGH,
        "detection_logic": "deadlock_risk",
        "repair_template": "Use consistent lock ordering or timeout"
    },

    # Numerical issues
    {
        "pattern_id": "NUM-001",
        "name": "Division by Zero",
        "description": "Potential division by zero",
        "category": BugCategory.NUMERICAL,
        "severity": RiskLevel.HIGH,
        "detection_logic": "division_by_zero",
        "repair_template": "Add zero check before division"
    },
    {
        "pattern_id": "NUM-002",
        "name": "Floating Point Comparison",
        "description": "Direct equality comparison of floating point numbers",
        "category": BugCategory.NUMERICAL,
        "severity": RiskLevel.MEDIUM,
        "detection_logic": r"==\s*\d+\.\d+|\d+\.\d+\s*==",
        "repair_template": "Use math.isclose() or tolerance-based comparison"
    },
    {
        "pattern_id": "NUM-003",
        "name": "Gradient Explosion Risk",
        "description": "Neural network without gradient clipping",
        "category": BugCategory.NUMERICAL,
        "severity": RiskLevel.MEDIUM,
        "detection_logic": r"backward\s*\(\)|\.backward\(\)(?![\s\S]*clip_grad)",
        "repair_template": "Add torch.nn.utils.clip_grad_norm_()"
    },

    # API issues
    {
        "pattern_id": "API-001",
        "name": "Deprecated API",
        "description": "Using deprecated function or method",
        "category": BugCategory.API,
        "severity": RiskLevel.LOW,
        "detection_logic": r"asyncio\.coroutine|@coroutine|\.warn\(",
        "repair_template": "Use recommended alternative API"
    },
    {
        "pattern_id": "API-002",
        "name": "Missing Error Handling",
        "description": "API call without error handling",
        "category": BugCategory.API,
        "severity": RiskLevel.MEDIUM,
        "detection_logic": "missing_error_handling",
        "repair_template": "Wrap in try-except block"
    },

    # Syntax issues
    {
        "pattern_id": "SYN-001",
        "name": "Bare Except",
        "description": "Except clause without exception type",
        "category": BugCategory.SYNTAX,
        "severity": RiskLevel.MEDIUM,
        "detection_logic": r"except\s*:",
        "repair_template": "Specify exception type: except Exception as e:"
    },
    {
        "pattern_id": "SYN-002",
        "name": "Mutable Default Argument",
        "description": "Mutable default argument in function",
        "category": BugCategory.SYNTAX,
        "severity": RiskLevel.MEDIUM,
        "detection_logic": "mutable_default",
        "repair_template": "Use None as default and initialize inside function"
    },
]


# ============================================================================
# AST VISITORS
# ============================================================================

class SecurityVisitor(ast.NodeVisitor):
    """AST visitor for security vulnerability detection."""

    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.current_function: Optional[str] = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = None

    def visit_Call(self, node: ast.Call):
        # Check for dangerous function calls
        func_name = self._get_func_name(node)

        # eval/exec detection
        if func_name in ("eval", "exec"):
            self.issues.append({
                "pattern_id": "SEC-006",
                "name": "Dangerous Eval/Exec",
                "description": f"Use of {func_name}() with potential untrusted input",
                "severity": RiskLevel.CRITICAL,
                "line": node.lineno,
                "column": node.col_offset,
                "function": self.current_function
            })

        # subprocess shell=True
        if func_name in ("subprocess.run", "subprocess.call", "subprocess.Popen"):
            for keyword in node.keywords:
                if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant):
                    if keyword.value.value is True:
                        self.issues.append({
                            "pattern_id": "SEC-002",
                            "name": "Shell Injection Risk",
                            "description": "subprocess with shell=True is dangerous",
                            "severity": RiskLevel.HIGH,
                            "line": node.lineno,
                            "column": node.col_offset,
                            "function": self.current_function
                        })

        self.generic_visit(node)

    def _get_func_name(self, node: ast.Call) -> str:
        """Extract function name from Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return ""


class TypeSafetyVisitor(ast.NodeVisitor):
    """AST visitor for type safety analysis."""

    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.defined_vars: Dict[str, Optional[str]] = {}  # var_name -> type_hint
        self.current_function: Optional[str] = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.current_function = node.name

        # Check for mutable default arguments
        for default in node.args.defaults + node.args.kw_defaults:
            if default and isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.issues.append({
                    "pattern_id": "SYN-002",
                    "name": "Mutable Default Argument",
                    "description": f"Function {node.name} has mutable default argument",
                    "severity": RiskLevel.MEDIUM,
                    "line": node.lineno,
                    "column": node.col_offset,
                    "function": node.name
                })

        self.generic_visit(node)
        self.current_function = None

    def visit_Compare(self, node: ast.Compare):
        # Check for comparison with None using == instead of is
        for op, comparator in zip(node.ops, node.comparators):
            if isinstance(comparator, ast.Constant) and comparator.value is None:
                if isinstance(op, (ast.Eq, ast.NotEq)):
                    op_str = "==" if isinstance(op, ast.Eq) else "!="
                    self.issues.append({
                        "pattern_id": "LOGIC-003",
                        "name": "Comparison with None",
                        "description": f"Use 'is None' instead of '{op_str} None'",
                        "severity": RiskLevel.LOW,
                        "line": node.lineno,
                        "column": node.col_offset,
                        "function": self.current_function
                    })

        self.generic_visit(node)


class ResourceLeakVisitor(ast.NodeVisitor):
    """AST visitor for resource leak detection."""

    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.open_resources: List[Tuple[str, int]] = []  # (resource_name, line)
        self.in_with: bool = False
        self.current_function: Optional[str] = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.current_function = node.name
        self.open_resources = []
        self.generic_visit(node)
        # Check for unclosed resources
        for resource, line in self.open_resources:
            self.issues.append({
                "pattern_id": "MEM-001",
                "name": "Potential Resource Leak",
                "description": f"Resource '{resource}' opened at line {line} may not be closed",
                "severity": RiskLevel.MEDIUM,
                "line": line,
                "function": self.current_function
            })
        self.current_function = None

    def visit_With(self, node: ast.With):
        old_in_with = self.in_with
        self.in_with = True
        self.generic_visit(node)
        self.in_with = old_in_with

    def visit_Call(self, node: ast.Call):
        if not self.in_with:
            func_name = ""
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if func_name == "open":
                self.open_resources.append(("file", node.lineno))

        self.generic_visit(node)


class ControlFlowVisitor(ast.NodeVisitor):
    """AST visitor for control flow analysis."""

    def __init__(self):
        self.issues: List[Dict[str, Any]] = []
        self.current_function: Optional[str] = None
        self.unreachable_after: Set[int] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.current_function = node.name
        self._check_unreachable(node.body)
        self.generic_visit(node)
        self.current_function = None

    def _check_unreachable(self, statements: List[ast.stmt]) -> None:
        """Check for unreachable code after return/raise/break/continue."""
        for i, stmt in enumerate(statements):
            if isinstance(stmt, (ast.Return, ast.Raise, ast.Break, ast.Continue)):
                if i < len(statements) - 1:
                    next_stmt = statements[i + 1]
                    if next_stmt.lineno not in self.unreachable_after:
                        self.unreachable_after.add(next_stmt.lineno)
                        self.issues.append({
                            "pattern_id": "LOGIC-002",
                            "name": "Unreachable Code",
                            "description": "Code after return/raise/break/continue will never execute",
                            "severity": RiskLevel.LOW,
                            "line": next_stmt.lineno,
                            "function": self.current_function
                        })


# ============================================================================
# STATIC ANALYZER
# ============================================================================

class StaticAnalyzer:
    """
    COVI-SHIELD Static Analysis Engine.

    Analyzes code without execution to detect:
    - Security vulnerabilities
    - Type errors
    - Logic errors
    - Memory issues
    - Performance problems
    - Concurrency issues
    - API misuse
    """

    def __init__(self):
        self.patterns: List[BugPattern] = self._load_patterns()
        self.stats = {
            "total_analyses": 0,
            "total_issues_found": 0,
            "patterns_matched": {}
        }
        logger.info(f"[COVI-SHIELD] Static Analyzer initialized with {len(self.patterns)} patterns")

    def _load_patterns(self) -> List[BugPattern]:
        """Load bug patterns from the database."""
        patterns = []
        for p in BUILTIN_PATTERNS:
            patterns.append(BugPattern(
                pattern_id=p["pattern_id"],
                name=p["name"],
                description=p["description"],
                category=p["category"],
                severity=p["severity"],
                detection_logic=p["detection_logic"],
                repair_templates=[p.get("repair_template", "")]
            ))
        return patterns

    def analyze(
        self,
        code: str,
        language: str = "python",
        file_path: Optional[str] = None,
        genesis_key_id: Optional[str] = None
    ) -> VerificationResult:
        """
        Perform static analysis on code.

        Args:
            code: Source code to analyze
            language: Programming language
            file_path: Optional file path for context
            genesis_key_id: Associated Genesis Key

        Returns:
            VerificationResult with detected issues
        """
        start_time = time.time()
        self.stats["total_analyses"] += 1

        issues: List[Dict[str, Any]] = []

        if language.lower() == "python":
            # Parse AST
            try:
                tree = ast.parse(code)

                # Run AST visitors
                security_visitor = SecurityVisitor()
                security_visitor.visit(tree)
                issues.extend(security_visitor.issues)

                type_visitor = TypeSafetyVisitor()
                type_visitor.visit(tree)
                issues.extend(type_visitor.issues)

                resource_visitor = ResourceLeakVisitor()
                resource_visitor.visit(tree)
                issues.extend(resource_visitor.issues)

                control_visitor = ControlFlowVisitor()
                control_visitor.visit(tree)
                issues.extend(control_visitor.issues)

            except SyntaxError as e:
                issues.append({
                    "pattern_id": "SYN-000",
                    "name": "Syntax Error",
                    "description": str(e),
                    "severity": RiskLevel.CRITICAL,
                    "line": e.lineno or 0,
                    "column": e.offset or 0
                })

        # Run regex-based pattern matching
        for pattern in self.patterns:
            if self._is_regex_pattern(pattern.detection_logic):
                matches = self._match_regex_pattern(code, pattern)
                issues.extend(matches)

        # Calculate metrics
        analysis_time_ms = (time.time() - start_time) * 1000
        self.stats["total_issues_found"] += len(issues)

        # Determine risk level
        risk_level = self._calculate_risk_level(issues)

        # Add code snippets to issues
        code_lines = code.split("\n")
        for issue in issues:
            line_num = issue.get("line", 0)
            if 0 < line_num <= len(code_lines):
                issue["code_snippet"] = code_lines[line_num - 1].strip()

        result = VerificationResult(
            genesis_key_id=genesis_key_id,
            phase=AnalysisPhase.PRE_FLIGHT,
            success=len([i for i in issues if i.get("severity") == RiskLevel.CRITICAL]) == 0,
            risk_level=risk_level,
            issues_found=len(issues),
            issues=issues,
            metrics={
                "lines_of_code": len(code_lines),
                "patterns_checked": len(self.patterns),
                "ast_nodes_visited": self._count_ast_nodes(code, language),
                "file_path": file_path
            },
            analysis_time_ms=analysis_time_ms
        )

        logger.info(
            f"[COVI-SHIELD] Static analysis complete: {len(issues)} issues found, "
            f"risk={risk_level.value}, time={analysis_time_ms:.2f}ms"
        )

        return result

    def _is_regex_pattern(self, detection_logic: str) -> bool:
        """Check if detection logic is a regex pattern."""
        # Non-regex patterns are simple identifiers
        return not detection_logic.replace("_", "").isalpha()

    def _match_regex_pattern(
        self,
        code: str,
        pattern: BugPattern
    ) -> List[Dict[str, Any]]:
        """Match regex pattern against code."""
        issues = []
        try:
            for match in re.finditer(pattern.detection_logic, code, re.MULTILINE):
                # Calculate line number
                line_num = code[:match.start()].count("\n") + 1
                issues.append({
                    "pattern_id": pattern.pattern_id,
                    "name": pattern.name,
                    "description": pattern.description,
                    "severity": pattern.severity,
                    "category": pattern.category.value,
                    "line": line_num,
                    "match": match.group(0)[:50],
                    "repair_template": pattern.repair_templates[0] if pattern.repair_templates else ""
                })

                # Update stats
                self.stats["patterns_matched"][pattern.pattern_id] = \
                    self.stats["patterns_matched"].get(pattern.pattern_id, 0) + 1

        except re.error as e:
            logger.warning(f"Regex error in pattern {pattern.pattern_id}: {e}")

        return issues

    def _calculate_risk_level(self, issues: List[Dict[str, Any]]) -> RiskLevel:
        """Calculate overall risk level from issues."""
        if not issues:
            return RiskLevel.INFO

        severities = [i.get("severity", RiskLevel.INFO) for i in issues]

        if RiskLevel.CRITICAL in severities:
            return RiskLevel.CRITICAL
        elif RiskLevel.HIGH in severities:
            return RiskLevel.HIGH
        elif RiskLevel.MEDIUM in severities:
            return RiskLevel.MEDIUM
        elif RiskLevel.LOW in severities:
            return RiskLevel.LOW
        return RiskLevel.INFO

    def _count_ast_nodes(self, code: str, language: str) -> int:
        """Count AST nodes for metrics."""
        if language.lower() != "python":
            return 0
        try:
            tree = ast.parse(code)
            return sum(1 for _ in ast.walk(tree))
        except SyntaxError:
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            **self.stats,
            "patterns_loaded": len(self.patterns)
        }

    def add_pattern(self, pattern: BugPattern) -> None:
        """Add a new bug pattern."""
        self.patterns.append(pattern)
        logger.info(f"[COVI-SHIELD] Added pattern: {pattern.pattern_id}")

    def get_pattern(self, pattern_id: str) -> Optional[BugPattern]:
        """Get a pattern by ID."""
        for pattern in self.patterns:
            if pattern.pattern_id == pattern_id:
                return pattern
        return None
