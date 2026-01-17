import ast
import sys
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import importlib.util

# Module-level logger
logger = logging.getLogger(__name__)


class Severity(Enum):
    """Issue severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Confidence(Enum):
    """Confidence level in issue detection"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class CodeIssue:
    """Represents a code issue (from Bandit + Semgrep pattern)"""
    rule_id: str
    severity: Severity
    confidence: Confidence
    message: str
    file_path: str
    line_number: int
    column: Optional[int] = None
    context: Optional[str] = None
    suggested_fix: Optional[str] = None
    fix_confidence: float = 0.0  # 0-1
    pattern_match: Optional[Dict[str, Any]] = None  # Metavariable bindings


@dataclass
class PatternRule:
    """Rule definition (from Semgrep pattern system)"""
    rule_id: str
    description: str
    severity: Severity
    patterns: List[ast.AST]  # Pattern ASTs to match
    message: str
    suggested_fix: Optional[str] = None
    check_node_types: Set[type] = field(default_factory=set)  # Which node types to check


@dataclass
class AnalysisContext:
    """Context tracking during AST traversal (from Bandit)"""
    file_path: str = ''
    node: Optional[ast.AST] = None
    function: Optional[str] = None
    class_: Optional[str] = None
    scope_stack: List[str] = field(default_factory=list)
    call_stack: List[str] = field(default_factory=list)
    assignments: Dict[str, ast.AST] = field(default_factory=dict)
    imports: Set[str] = field(default_factory=set)
    # Context-aware tracking
    in_try_block: bool = False
    in_async_function: bool = False
    has_logging: bool = False
    current_function_has_docstring: bool = False
    current_class_has_logger: bool = False


# ============================================================================
# Pattern Matching Engine (from Semgrep)
# ============================================================================

class PatternMatcher:
    """Structural pattern matching engine (inspired by Semgrep)"""
    
    def __init__(self):
        self.bindings: Dict[str, ast.AST] = {}
    
    def match_pattern(self, pattern: ast.AST, target: ast.AST) -> Optional[Dict[str, Any]]:
        """
        Match a pattern AST against a target AST.
        Returns metavariable bindings if match, None otherwise.
        """
        self.bindings.clear()
        
        if self._match(pattern, target):
            return dict(self.bindings)
        return None
    
    def _match(self, pattern: ast.AST, target: ast.AST) -> bool:
        """Internal matching logic"""
        # Metavariable matching (e.g., $X matches anything)
        if isinstance(pattern, Metavariable):
            var_name = pattern.name
            if var_name in self.bindings:
                # Consistency check: must match previously bound value
                return self._same_ast(self.bindings[var_name], target)
            else:
                # New binding
                self.bindings[var_name] = target
                return True
        
        # Ellipsis: matches any sequence
        if isinstance(pattern, Ellipsis):
            return True
        
        # Type must match
        if type(pattern) != type(target):
            return False
        
        # Node-specific matching
        if isinstance(pattern, ast.Name) and isinstance(target, ast.Name):
            return pattern.id == target.id
        
        elif isinstance(pattern, ast.Call) and isinstance(target, ast.Call):
            return (self._match(pattern.func, target.func) and
                    self._match_list(pattern.args, target.args))
        
        elif isinstance(pattern, ast.Attribute) and isinstance(target, ast.Attribute):
            return (self._match(pattern.value, target.value) and
                    pattern.attr == target.attr)
        
        elif isinstance(pattern, ast.ImportFrom) and isinstance(target, ast.ImportFrom):
            return pattern.module == target.module
        
        # For other nodes, recursively check children
        return self._match_children(pattern, target)
    
    def _match_list(self, pattern_list: List, target_list: List) -> bool:
        """Match lists with ellipsis support"""
        # Handle ellipsis in pattern
        # This is simplified - full ellipsis matching is more complex
        if len(pattern_list) != len(target_list):
            return False
        
        return all(self._match(p, t) for p, t in zip(pattern_list, target_list))
    
    def _match_children(self, pattern: ast.AST, target: ast.AST) -> bool:
        """Match children recursively"""
        pattern_children = list(ast.iter_child_nodes(pattern))
        target_children = list(ast.iter_child_nodes(target))
        
        if len(pattern_children) != len(target_children):
            return False
        
        return all(self._match(p, t) for p, t in zip(pattern_children, target_children))
    
    def _same_ast(self, node1: ast.AST, node2: ast.AST) -> bool:
        """Check if two AST nodes are structurally identical"""
        return ast.dump(node1) == ast.dump(node2)


# Placeholder classes for pattern syntax
class Metavariable(ast.AST):
    """Represents a metavariable in pattern (e.g., $X)"""
    def __init__(self, name: str):
        self.name = name


class Ellipsis(ast.AST):
    """Represents ellipsis in pattern (matches any sequence)"""
    pass


# ============================================================================
# AST Visitor (from Bandit)
# ============================================================================

class GraceCodeVisitor(ast.NodeVisitor):
    """
    AST Visitor for GRACE code analysis.
    Combines visitor pattern from Bandit with pattern matching from Semgrep.
    """
    
    def __init__(self, rules: List[PatternRule], context: AnalysisContext):
        self.rules = rules
        self.context = context
        self.issues: List[CodeIssue] = []
        self.pattern_matcher = PatternMatcher()
    
    def visit(self, node: ast.AST):
        """Visit a node and all its children"""
        # Update context
        old_node = self.context.node
        self.context.node = node
        
        # Call node-specific visitor
        method = 'visit_' + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        result = visitor(node)
        
        # Visit children
        self.generic_visit(node)
        
        # Restore context
        self.context.node = old_node
        
        return result
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track function context"""
        old_function = self.context.function
        old_async = self.context.in_async_function
        old_has_docstring = self.context.current_function_has_docstring
        
        self.context.function = node.name
        self.context.scope_stack.append('function')
        self.context.in_async_function = False  # Will check in AsyncFunctionDef
        self.context.current_function_has_docstring = (
            ast.get_docstring(node) is not None
        )
        
        # Check for docstring
        self._check_rules(node)
        
        self.generic_visit(node)
        
        # Restore context
        self.context.function = old_function
        self.context.in_async_function = old_async
        self.context.current_function_has_docstring = old_has_docstring
        if self.context.scope_stack:
            self.context.scope_stack.pop()
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Track async function context"""
        old_function = self.context.function
        old_async = self.context.in_async_function
        old_has_docstring = self.context.current_function_has_docstring
        
        self.context.function = node.name
        self.context.scope_stack.append('async_function')
        self.context.in_async_function = True
        self.context.current_function_has_docstring = (
            ast.get_docstring(node) is not None
        )
        
        # Check for docstring and async patterns
        self._check_rules(node)
        
        self.generic_visit(node)
        
        # Restore context
        self.context.function = old_function
        self.context.in_async_function = old_async
        self.context.current_function_has_docstring = old_has_docstring
        if self.context.scope_stack:
            self.context.scope_stack.pop()
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Track class context"""
        old_class = self.context.class_
        old_has_logger = self.context.current_class_has_logger
        
        self.context.class_ = node.name
        self.context.scope_stack.append('class')
        self.context.current_class_has_logger = False  # Will check in body
        
        # Check for logger in class body
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == 'logger':
                        self.context.current_class_has_logger = True
                        break
        
        # Check class-related rules
        self._check_rules(node)
        
        self.generic_visit(node)
        
        # Restore context
        self.context.class_ = old_class
        self.context.current_class_has_logger = old_has_logger
        if self.context.scope_stack:
            self.context.scope_stack.pop()
    
    def visit_Try(self, node: ast.Try):
        """Track try/except context"""
        old_in_try = self.context.in_try_block
        self.context.in_try_block = True
        
        self.generic_visit(node)
        
        # Restore context
        self.context.in_try_block = old_in_try
    
    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """Check except handlers"""
        self._check_rules(node)
        self.generic_visit(node)
    
    def visit_Import(self, node: ast.Import):
        """Check imports"""
        for alias in node.names:
            self.context.imports.add(alias.name)
        
        # Check import-related rules
        self._check_rules(node)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Check import from"""
        if node.module:
            self.context.imports.add(node.module)
        
        self._check_rules(node)
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        """Check function calls (most common place for issues)"""
        # Check for logging
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == 'logger':
                self.context.has_logging = True
        
        self._check_rules(node)
        self.generic_visit(node)
    
    def visit_Assign(self, node: ast.Assign):
        """Track assignments"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.context.assignments[target.id] = node.value
        
        self._check_rules(node)
        self.generic_visit(node)
    
    def visit_Assert(self, node: ast.Assert):
        """Check assertions (can be enhanced with pytest-style transformation)"""
        self._check_rules(node)
        self.generic_visit(node)
    
    def _check_rules(self, node: ast.AST):
        """Check all applicable rules against current node"""
        node_type = type(node)
        
        for rule in self.rules:
            # Only check rules that apply to this node type
            if rule.check_node_types and node_type not in rule.check_node_types:
                continue
            
            # Context-aware filtering
            if self._should_skip_rule(rule, node):
                continue
            
            # Custom context-aware checks for specific rules
            if rule.rule_id in ['G002', 'G005', 'G010', 'G017']:
                # Skip if in try block (error handling exists)
                if self.context.in_try_block:
                    continue
            
            # Try to match pattern (if patterns exist)
            if rule.patterns:
                for pattern in rule.patterns:
                    bindings = self.pattern_matcher.match_pattern(pattern, node)
                    if bindings:
                        # Pattern matched - create issue
                        issue = self._create_issue(rule, node, bindings)
                        if issue:
                            self.issues.append(issue)
            else:
                # Rules without patterns use direct node checking
                if self._check_rule_directly(rule, node):
                    issue = self._create_issue(rule, node, {})
                    if issue:
                        self.issues.append(issue)
    
    def _check_rule_directly(self, rule: PatternRule, node: ast.AST) -> bool:
        """Direct checking for rules without patterns"""
        rule_id = rule.rule_id
        
        # G006: Print statement check
        if rule_id == 'G006' and isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'print':
                # Only flag if not in __main__ or test files
                if '__main__' not in self.context.file_path and 'test' not in self.context.file_path.lower():
                    return True
        
        # G007: Bare except
        if rule_id == 'G007' and isinstance(node, ast.ExceptHandler):
            if node.type is None:  # Bare except
                return True
        
        # G008: Mutable default argument
        if rule_id == 'G008' and isinstance(node, ast.FunctionDef):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    return True
        
        # G009: Missing type hints
        if rule_id == 'G009' and isinstance(node, ast.FunctionDef):
            # Check if function has type hints
            has_return_annotation = node.returns is not None
            has_param_annotations = any(arg.annotation is not None for arg in node.args.args)
            if not (has_return_annotation or has_param_annotations):
                return True
        
        # G010: Qdrant query check (more specific)
        if rule_id == 'G010' and isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                # Check for client.query or qdrant_client.query patterns
                if node.func.attr == 'query':
                    if isinstance(node.func.value, (ast.Name, ast.Attribute)):
                        # More specific - check variable names
                        var_name = self._get_variable_name(node.func.value)
                        if var_name and ('client' in var_name.lower() or 'qdrant' in var_name.lower()):
                            # Check if query has user input (simplified check)
                            # In practice, this would need data flow analysis
                            return True
        
        # G012: Missing logger in class
        if rule_id == 'G012' and isinstance(node, ast.ClassDef):
            if not self.context.current_class_has_logger:
                return True
        
        # G014: Missing docstring
        if rule_id == 'G014':
            if isinstance(node, ast.FunctionDef) and not self.context.current_function_has_docstring:
                return True
            elif isinstance(node, ast.ClassDef) and ast.get_docstring(node) is None:
                return True
        
        # G015: Import star
        if rule_id == 'G015' and isinstance(node, ast.ImportFrom):
            if any(alias.name == '*' for alias in node.names):
                return True
        
        return False
    
    def _get_variable_name(self, node: ast.AST) -> Optional[str]:
        """Get variable name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name):
                return node.value.id
        return None
    
    def _should_skip_rule(self, rule: PatternRule, node: ast.AST) -> bool:
        """Context-aware rule filtering"""
        rule_id = rule.rule_id
        
        # Skip error handling rules if we're in a try block
        if rule_id in ['G002', 'G005', 'G017'] and self.context.in_try_block:
            return True
        
        # Skip logging rules if logging is present (checked per-call)
        if rule_id == 'G003' and self.context.has_logging:
            return True
        
        # Skip docstring rules if docstring exists
        if rule_id == 'G014':
            if isinstance(node, ast.FunctionDef) and self.context.current_function_has_docstring:
                return True
            elif isinstance(node, ast.ClassDef) and ast.get_docstring(node):
                return True
        
        # Skip logger rules if logger exists
        if rule_id == 'G012' and self.context.current_class_has_logger:
            return True
        
        return False
    
    def _create_issue(self, rule: PatternRule, node: ast.AST, bindings: Dict[str, Any]) -> Optional[CodeIssue]:
        """Create an issue from a matched rule"""
        # Get location information
        line_number = getattr(node, 'lineno', 0)
        column = getattr(node, 'col_offset', None)
        
        # Format message with bindings
        message = rule.message
        for var_name, value in bindings.items():
            # Replace $VAR in message with actual value
            message = message.replace(f'${var_name}', self._format_ast_value(value))
        
        return CodeIssue(
            rule_id=rule.rule_id,
            severity=rule.severity,
            confidence=Confidence.MEDIUM,  # Could be computed from context
            message=message,
            file_path=getattr(self.context, 'file_path', ''),
            line_number=line_number,
            column=column,
            context=self._get_context(node),
            suggested_fix=rule.suggested_fix,
            pattern_match=bindings
        )
    
    def _format_ast_value(self, node: ast.AST) -> str:
        """Format AST node for display"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Str):
            return f'"{node.s}"'
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        else:
            return ast.dump(node)
    
    def _get_context(self, node: ast.AST) -> str:
        """Get context string for node"""
        parts = []
        if self.context.class_:
            parts.append(f"class {self.context.class_}")
        if self.context.function:
            parts.append(f"function {self.context.function}")
        return " in ".join(parts) if parts else ""


# ============================================================================
# GRACE-Specific Rules (Combining all three patterns)
# ============================================================================

class GraceRuleBuilder:
    """Build GRACE-specific rules using pattern matching"""
    
    @staticmethod
    def unsafe_vector_query() -> PatternRule:
        """Check for unsafe vector database queries"""
        # Pattern: qdrant_client.query($USER_INPUT)
        pattern = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='qdrant_client', ctx=ast.Load()),
                attr='query',
                ctx=ast.Load()
            ),
            args=[Metavariable('USER_INPUT')],
            keywords=[]
        )
        
        return PatternRule(
            rule_id='G001',
            description='Unsanitized vector database query',
            severity=Severity.HIGH,
            patterns=[pattern],
            message='Unsanitized user input in vector database query: $USER_INPUT',
            suggested_fix='Sanitize input or use parameterized queries',
            check_node_types={ast.Call}
        )
    
    @staticmethod
    def missing_error_handling() -> PatternRule:
        """Check for missing error handling"""
        # Pattern: function_call() without try/except
        # This is simplified - real implementation would check context
        return PatternRule(
            rule_id='G002',
            description='Missing error handling',
            severity=Severity.MEDIUM,
            patterns=[],  # Would need context-aware checking
            message='Function call without error handling',
            check_node_types={ast.Call}
        )
    
    @staticmethod
    def cognitive_layer_call_without_logging() -> PatternRule:
        """Check for cognitive layer calls without logging"""
        pattern = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='cognitive_engine', ctx=ast.Load()),
                attr=Metavariable('METHOD'),
                ctx=ast.Load()
            ),
            args=[Ellipsis()],
            keywords=[]
        )
        
        return PatternRule(
            rule_id='G003',
            description='Cognitive layer call without logging',
            severity=Severity.MEDIUM,
            patterns=[pattern],
            message='Cognitive layer call $METHOD without logging',
            suggested_fix='Add logging around cognitive layer calls',
            check_node_types={ast.Call}
        )
    
    @staticmethod
    def hardcoded_credentials() -> PatternRule:
        """Check for hardcoded credentials"""
        # Pattern: password = "hardcoded_value"
        pattern = ast.Assign(
            targets=[ast.Name(id=Metavariable('VAR_NAME'), ctx=ast.Store())],
            value=ast.Constant(value=Metavariable('VALUE'))
        )
        
        return PatternRule(
            rule_id='G004',
            description='Possible hardcoded credentials',
            severity=Severity.HIGH,
            patterns=[pattern],
            message='Possible hardcoded credential: $VAR_NAME',
            suggested_fix='Use environment variables or secure storage',
            check_node_types={ast.Assign}
        )
    
    @staticmethod
    def async_function_without_error_handling() -> PatternRule:
        """Check for async functions without error handling"""
        return PatternRule(
            rule_id='G005',
            description='Async function without error handling',
            severity=Severity.MEDIUM,
            patterns=[],  # Context-aware - checks for try/except in async def
            message='Async function without proper error handling',
            suggested_fix='Wrap async operations in try/except blocks',
            check_node_types={ast.FunctionDef}
        )
    
    @staticmethod
    def print_statement_usage() -> PatternRule:
        """Check for print statements (should use logging)"""
        pattern = ast.Call(
            func=ast.Name(id='print', ctx=ast.Load()),
            args=[Ellipsis()],
            keywords=[]
        )
        
        return PatternRule(
            rule_id='G006',
            description='Use of print instead of logging',
            severity=Severity.LOW,
            patterns=[pattern],
            message='print() statement found - use logger instead',
            suggested_fix='Replace print() with logger.info() or logger.debug()',
            check_node_types={ast.Call}
        )
    
    @staticmethod
    def bare_except_clause() -> PatternRule:
        """Check for bare except clauses"""
        pattern = ast.ExceptHandler(
            type=None,  # Bare except
            name=None,
            body=[Ellipsis()]
        )
        
        return PatternRule(
            rule_id='G007',
            description='Bare except clause',
            severity=Severity.MEDIUM,
            patterns=[pattern],
            message='Bare except clause catches all exceptions including SystemExit',
            suggested_fix='Use "except Exception:" instead',
            check_node_types={ast.ExceptHandler}
        )
    
    @staticmethod
    def mutable_default_argument() -> PatternRule:
        """Check for mutable default arguments"""
        # This would need to check function definitions
        return PatternRule(
            rule_id='G008',
            description='Mutable default argument',
            severity=Severity.HIGH,
            patterns=[],  # Context-aware - checks function defaults
            message='Mutable default argument can cause unexpected behavior',
            suggested_fix='Use None as default and initialize inside function',
            check_node_types={ast.FunctionDef}
        )
    
    @staticmethod
    def missing_type_hints() -> PatternRule:
        """Check for missing type hints in function definitions"""
        return PatternRule(
            rule_id='G009',
            description='Missing type hints',
            severity=Severity.LOW,
            patterns=[],
            message='Function missing type hints',
            suggested_fix='Add type hints to function parameters and return type',
            check_node_types={ast.FunctionDef}
        )
    
    @staticmethod
    def qdrant_query_without_sanitization() -> PatternRule:
        """Check for Qdrant queries without sanitization"""
        # Pattern: client.query(...) or qdrant_client.query(...)
        # More specific - only match actual Qdrant client patterns
        # This is a simplified pattern - full implementation would check more precisely
        return PatternRule(
            rule_id='G010',
            description='Potential unsanitized Qdrant query',
            severity=Severity.HIGH,
            patterns=[],  # Context-aware - checked in visitor
            message='Qdrant query may contain unsanitized user input',
            suggested_fix='Sanitize query parameters before passing to Qdrant',
            check_node_types={ast.Call}
        )
    
    @staticmethod
    def database_query_with_string_formatting() -> PatternRule:
        """Check for database queries with string formatting (SQL injection risk)"""
        # Pattern: query = f"SELECT * FROM ... WHERE id = {user_input}"
        # This is simplified - full check would look at f-strings or .format()
        return PatternRule(
            rule_id='G011',
            description='Database query with string formatting',
            severity=Severity.CRITICAL,
            patterns=[],
            message='Database query uses string formatting - SQL injection risk',
            suggested_fix='Use parameterized queries or ORM methods',
            check_node_types={ast.Assign, ast.Call}
        )
    
    @staticmethod
    def missing_logger_in_class() -> PatternRule:
        """Check for classes without logger initialization"""
        return PatternRule(
            rule_id='G012',
            description='Class missing logger initialization',
            severity=Severity.LOW,
            patterns=[],
            message='Class should have logger = logging.getLogger(__name__)',
            suggested_fix='Add logger initialization in class __init__ or module level',
            check_node_types={ast.ClassDef}
        )
    
    @staticmethod
    def hardcoded_url() -> PatternRule:
        """Check for hardcoded URLs"""
        # Pattern: url = "http://..."
        pattern = ast.Assign(
            targets=[ast.Name(id=Metavariable('VAR'), ctx=ast.Store())],
            value=ast.Constant(value=Metavariable('URL'))
        )
        
        return PatternRule(
            rule_id='G013',
            description='Hardcoded URL',
            severity=Severity.MEDIUM,
            patterns=[pattern],
            message='Hardcoded URL found: $VAR',
            suggested_fix='Move URL to configuration file or environment variable',
            check_node_types={ast.Assign}
        )
    
    @staticmethod
    def missing_docstring() -> PatternRule:
        """Check for missing docstrings in functions/classes"""
        return PatternRule(
            rule_id='G014',
            description='Missing docstring',
            severity=Severity.LOW,
            patterns=[],
            message='Function or class missing docstring',
            suggested_fix='Add docstring describing the function/class purpose',
            check_node_types={ast.FunctionDef, ast.ClassDef}
        )
    
    @staticmethod
    def import_star() -> PatternRule:
        """Check for import * statements"""
        pattern = ast.ImportFrom(
            module=Metavariable('MODULE'),
            names=[ast.alias(name='*', asname=None)],
            level=0
        )
        
        return PatternRule(
            rule_id='G015',
            description='Import * statement',
            severity=Severity.MEDIUM,
            patterns=[pattern],
            message='Import * from $MODULE - pollutes namespace',
            suggested_fix='Import specific names instead of using import *',
            check_node_types={ast.ImportFrom}
        )
    
    @staticmethod
    def deprecated_import() -> PatternRule:
        """Check for deprecated imports"""
        deprecated_modules = {
            'distutils',  # Deprecated in Python 3.12
        }
        
        # This would need context checking
        return PatternRule(
            rule_id='G016',
            description='Deprecated module import',
            severity=Severity.MEDIUM,
            patterns=[],
            message='Importing deprecated module',
            suggested_fix='Use alternative module or upgrade code',
            check_node_types={ast.Import, ast.ImportFrom}
        )
    
    @staticmethod
    def memory_mesh_call_without_error_handling() -> PatternRule:
        """Check for memory mesh calls without error handling"""
        pattern = ast.Call(
            func=ast.Attribute(
                value=ast.Name(id='memory_mesh', ctx=ast.Load()),
                attr=Metavariable('METHOD'),
                ctx=ast.Load()
            ),
            args=[Ellipsis()],
            keywords=[]
        )
        
        return PatternRule(
            rule_id='G017',
            description='Memory mesh call without error handling',
            severity=Severity.MEDIUM,
            patterns=[pattern],
            message='Memory mesh call $METHOD without error handling',
            suggested_fix='Wrap memory mesh calls in try/except blocks',
            check_node_types={ast.Call}
        )
    
    @staticmethod
    def api_endpoint_without_validation() -> PatternRule:
        """Check for API endpoints without input validation"""
        # Pattern: @app.post(...) or @router.post(...) without validation
        return PatternRule(
            rule_id='G018',
            description='API endpoint without input validation',
            severity=Severity.MEDIUM,
            patterns=[],
            message='API endpoint missing input validation',
            suggested_fix='Add Pydantic models or input validation',
            check_node_types={ast.FunctionDef}
        )
    
    @staticmethod
    def unused_import() -> PatternRule:
        """Check for unused imports"""
        return PatternRule(
            rule_id='G019',
            description='Potentially unused import',
            severity=Severity.LOW,
            patterns=[],
            message='Import may be unused',
            suggested_fix='Remove if not used, or check if needed for side effects',
            check_node_types={ast.Import, ast.ImportFrom}
        )
    
    @staticmethod
    def missing_await_in_async_context() -> PatternRule:
        """Check for missing await in async context"""
        # Pattern: async def function() calling awaitable without await
        return PatternRule(
            rule_id='G020',
            description='Missing await in async function',
            severity=Severity.HIGH,
            patterns=[],
            message='Async function calls awaitable without await',
            suggested_fix='Add await keyword before async function call',
            check_node_types={ast.Call}
        )
    
    @staticmethod
    def get_all_rules() -> List[PatternRule]:
        """Get all GRACE-specific rules"""
        return [
            GraceRuleBuilder.unsafe_vector_query(),
            GraceRuleBuilder.missing_error_handling(),
            GraceRuleBuilder.cognitive_layer_call_without_logging(),
            GraceRuleBuilder.hardcoded_credentials(),
            GraceRuleBuilder.async_function_without_error_handling(),
            GraceRuleBuilder.print_statement_usage(),
            GraceRuleBuilder.bare_except_clause(),
            GraceRuleBuilder.mutable_default_argument(),
            GraceRuleBuilder.missing_type_hints(),
            GraceRuleBuilder.qdrant_query_without_sanitization(),
            GraceRuleBuilder.database_query_with_string_formatting(),
            GraceRuleBuilder.missing_logger_in_class(),
            GraceRuleBuilder.hardcoded_url(),
            GraceRuleBuilder.missing_docstring(),
            GraceRuleBuilder.import_star(),
            GraceRuleBuilder.deprecated_import(),
            GraceRuleBuilder.memory_mesh_call_without_error_handling(),
            GraceRuleBuilder.api_endpoint_without_validation(),
            GraceRuleBuilder.unused_import(),
            GraceRuleBuilder.missing_await_in_async_context(),
        ]


# ============================================================================
# Main Analyzer (Combining all three tools)
# ============================================================================

class GraceCodeAnalyzer:
    """
    Unified GRACE Code Analyzer
    
    Combines:
    - AST Visitor Pattern (Bandit)
    - Pattern Matching (Semgrep)
    - AST Transformation capabilities (pytest - for future use)
    """
    
    def __init__(self, custom_rules: Optional[List[PatternRule]] = None):
        self.rules = custom_rules or GraceRuleBuilder.get_all_rules()
        self.context = AnalysisContext()
    
    def analyze_file(self, file_path: str) -> List[CodeIssue]:
        """Analyze a single file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            return self.analyze_source(source, file_path)
        
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")
            return []
    
    def analyze_source(self, source: str, file_path: str = '') -> List[CodeIssue]:
        """Analyze source code"""
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError as e:
            # Return syntax error as issue
            return [CodeIssue(
                rule_id='SYNTAX_ERROR',
                severity=Severity.CRITICAL,
                confidence=Confidence.HIGH,
                message=f"Syntax error: {e.msg}",
                file_path=file_path,
                line_number=e.lineno or 0,
                column=e.offset
            )]
        
        # Create visitor with context
        context = AnalysisContext(file_path=file_path)
        visitor = GraceCodeVisitor(self.rules, context)
        
        # Visit AST
        visitor.visit(tree)
        
        return visitor.issues
    
    def analyze_directory(self, directory: str, exclude_patterns: Optional[List[str]] = None) -> Dict[str, List[CodeIssue]]:
        """Analyze all Python files in directory"""
        results = {}
        exclude_patterns = exclude_patterns or ['__pycache__', '.git', 'venv', 'node_modules']
        
        for file_path in Path(directory).rglob('*.py'):
            # Skip excluded paths
            if any(pattern in str(file_path) for pattern in exclude_patterns):
                continue
            
            issues = self.analyze_file(str(file_path))
            if issues:
                results[str(file_path)] = issues
        
        return results


# ============================================================================
# AST Transformation (from pytest - for future use)
# ============================================================================

class GraceASTTransformer(ast.NodeTransformer):
    """
    AST Transformer for GRACE code enhancement.
    Inspired by pytest's assertion rewriting, can be used for:
    - Enhanced error messages
    - Automatic logging injection
    - Monitoring code insertion
    """
    
    def visit_Assert(self, node: ast.Assert):
        """Transform assert statements for better error messages"""
        # Similar to pytest's assertion rewriting
        # Can enhance GRACE assertions with detailed context
        return self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call):
        """Transform calls for monitoring"""
        # Could wrap cognitive layer calls with monitoring
        return self.generic_visit(node)


# ============================================================================
# Main Entry Point
# ============================================================================

def analyze_grace_codebase(
    directory: str = 'backend',
    custom_rules: Optional[List[PatternRule]] = None,
    exclude_patterns: Optional[List[str]] = None
) -> Dict[str, List[CodeIssue]]:
    """
    Analyze GRACE codebase using unified analyzer.
    
    Args:
        directory: Directory to analyze
        custom_rules: Custom rules to add
        exclude_patterns: Patterns to exclude
    
    Returns:
        Dictionary mapping file paths to list of issues
    """
    analyzer = GraceCodeAnalyzer(custom_rules=custom_rules)
    return analyzer.analyze_directory(directory, exclude_patterns)


if __name__ == '__main__':
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Analyze GRACE codebase
    results = analyze_grace_codebase('backend')
    
    # Print results
    for file_path, issues in results.items():
        print(f"\n{file_path}: {len(issues)} issues")
        for issue in issues:
            print(f"  [{issue.severity.value}] {issue.rule_id}: {issue.message}")
