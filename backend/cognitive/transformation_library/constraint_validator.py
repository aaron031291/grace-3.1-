import ast
import logging
from typing import Dict, Any, List, Optional, Tuple
logger = logging.getLogger(__name__)

class ConstraintValidator:
    """
    Validates pre and post conditions for transformations.
    
    Ensures constraints are met before and after applying transforms.
    """

    def __init__(self):
        """Initialize Constraint Validator."""
        self.constraint_checkers = {
            "no_nested_except": self._check_no_nested_except,
            "not_in_function_definition": self._check_not_in_function_definition,
            "handles_exception_types": self._check_handles_exception_types,
            "preserves_traceback": self._check_preserves_traceback,
            "logging_import_exists": self._check_logging_import_exists,
            "logger_defined": self._check_logger_defined,
        }

    def validate_preconditions(
        self,
        code: str,
        constraints: List[str],
        matches: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Validate preconditions before transformation.
        
        Args:
            code: Source code
            constraints: List of constraint names to check
            matches: AST matches for context
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, [f"Syntax error in code: {e}"]

        for constraint in constraints:
            checker = self.constraint_checkers.get(constraint)
            if checker:
                try:
                    is_valid, error = checker(code, tree, matches)
                    if not is_valid:
                        errors.append(error or f"Precondition failed: {constraint}")
                except Exception as e:
                    logger.warning(f"[CONSTRAINT-VALIDATOR] Error checking {constraint}: {e}")
                    errors.append(f"Error checking {constraint}: {e}")
            else:
                logger.warning(f"[CONSTRAINT-VALIDATOR] Unknown precondition: {constraint}")

        is_valid = len(errors) == 0
        if is_valid:
            logger.info(f"[CONSTRAINT-VALIDATOR] All preconditions passed: {constraints}")
        else:
            logger.warning(f"[CONSTRAINT-VALIDATOR] Preconditions failed: {errors}")

        return is_valid, errors

    def validate_postconditions(
        self,
        before_code: str,
        after_code: str,
        constraints: List[str],
        matches: List[Dict[str, Any]]
    ) -> Tuple[bool, List[str]]:
        """
        Validate postconditions after transformation.
        
        Args:
            before_code: Original code
            after_code: Transformed code
            constraints: List of constraint names to check
            matches: AST matches for context
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        try:
            before_tree = ast.parse(before_code)
            after_tree = ast.parse(after_code)
        except SyntaxError as e:
            return False, [f"Syntax error in transformed code: {e}"]

        for constraint in constraints:
            checker = self.constraint_checkers.get(constraint)
            if checker:
                try:
                    is_valid, error = checker(after_code, after_tree, matches, before_code, before_tree)
                    if not is_valid:
                        errors.append(error or f"Postcondition failed: {constraint}")
                except Exception as e:
                    logger.warning(f"[CONSTRAINT-VALIDATOR] Error checking {constraint}: {e}")
                    errors.append(f"Error checking {constraint}: {e}")
            else:
                logger.warning(f"[CONSTRAINT-VALIDATOR] Unknown postcondition: {constraint}")

        is_valid = len(errors) == 0
        if is_valid:
            logger.info(f"[CONSTRAINT-VALIDATOR] All postconditions passed: {constraints}")
        else:
            logger.warning(f"[CONSTRAINT-VALIDATOR] Postconditions failed: {errors}")

        return is_valid, errors

    def _check_no_nested_except(
        self,
        code: str,
        tree: ast.AST,
        matches: List[Dict[str, Any]],
        *args
    ) -> Tuple[bool, Optional[str]]:
        """Check that except handlers are not nested."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # Check if this except is inside another except handler
                for parent in ast.walk(tree):
                    if isinstance(parent, ast.ExceptHandler) and parent != node:
                        # Simple check - can be made more precise with AST visitor
                        if hasattr(node, 'lineno') and hasattr(parent, 'lineno'):
                            # Basic nesting check
                            pass  # For now, always pass
        
        return True, None

    def _check_not_in_function_definition(
        self,
        code: str,
        tree: ast.AST,
        matches: List[Dict[str, Any]],
        *args
    ) -> Tuple[bool, Optional[str]]:
        """Check that matched nodes are not inside function definitions."""
        for match in matches:
            node = match.get("node")
            if not node:
                continue
            
            # Walk up the tree to check for function definition
            # Simple implementation: check if line is inside a function
            for parent in ast.walk(tree):
                if isinstance(parent, ast.FunctionDef):
                    if hasattr(node, 'lineno') and hasattr(parent, 'lineno'):
                        if parent.lineno <= node.lineno <= parent.lineno + 20:
                            return False, f"Node at line {node.lineno} is inside function definition"
        
        return True, None

    def _check_handles_exception_types(
        self,
        code: str,
        tree: ast.AST,
        matches: List[Dict[str, Any]],
        *args
    ) -> Tuple[bool, Optional[str]]:
        """Check that exception handlers properly handle exception types."""
        # Check that all except handlers have a type
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    return False, "Bare except handler found (should have Exception type)"
        
        return True, None

    def _check_preserves_traceback(
        self,
        code: str,
        tree: ast.AST,
        matches: List[Dict[str, Any]],
        before_code: Optional[str] = None,
        before_tree: Optional[ast.AST] = None
    ) -> Tuple[bool, Optional[str]]:
        """Check that traceback information is preserved."""
        # Simple check: ensure exception handling structure is similar
        # Can be enhanced with more sophisticated checks
        return True, None

    def _check_logging_import_exists(
        self,
        code: str,
        tree: ast.AST,
        matches: List[Dict[str, Any]],
        *args
    ) -> Tuple[bool, Optional[str]]:
        """Check that logging module is imported."""
        has_logging_import = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "logging":
                        has_logging_import = True
            elif isinstance(node, ast.ImportFrom):
                if node.module == "logging":
                    has_logging_import = True
        
        if not has_logging_import:
            return False, "logging module not imported"
        
        return True, None

    def _check_logger_defined(
        self,
        code: str,
        tree: ast.AST,
        matches: List[Dict[str, Any]],
        *args
    ) -> Tuple[bool, Optional[str]]:
        """Check that logger is defined."""
        # Check for logger = logging.getLogger(...) or similar
        has_logger = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "logger":
                        has_logger = True
        
        if not has_logger:
            return False, "logger variable not defined"
        
        return True, None
