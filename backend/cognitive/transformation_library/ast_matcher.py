import ast
import logging
from typing import Dict, Any, Optional, List, Tuple
import hashlib
from genesis.code_analyzer import get_code_analyzer
logger = logging.getLogger(__name__)

class ASTMatcher:
    """
    AST pattern matching engine.
    
    Matches AST patterns defined in Rule DSL against actual code ASTs.
    """

    def __init__(self):
        """Initialize AST Matcher."""
        self.code_analyzer = get_code_analyzer()

    def match_pattern(
        self,
        code: str,
        pattern: Dict[str, Any],
        language: str = "python"
    ) -> List[Dict[str, Any]]:
        """
        Match pattern against code AST.
        
        Args:
            code: Source code to match against
            pattern: Pattern definition from Rule DSL
            language: Programming language (default: python)
        
        Returns:
            List of matches with AST nodes and metadata
        """
        if language != "python":
            logger.warning(f"[AST-MATCHER] Language {language} not fully supported")
            return []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            logger.error(f"[AST-MATCHER] Syntax error in code: {e}")
            return []

        pattern_match = pattern.get("match", "")
        if not pattern_match:
            return []

        # Parse pattern and match against AST
        matches = []
        
        # Simple pattern matching for now
        # Can be extended to support more sophisticated patterns
        if pattern_match == "ExceptHandler(type=None)":
            matches = self._match_bare_except(tree, code)
        elif pattern_match == "Call(func=Name(id='print'))":
            matches = self._match_print_calls(tree, code)
        else:
            # Generic AST walker for custom patterns
            matches = self._generic_pattern_match(tree, pattern_match, code)

        logger.info(f"[AST-MATCHER] Found {len(matches)} matches for pattern: {pattern_match}")
        return matches

    def _match_bare_except(self, tree: ast.AST, code: str) -> List[Dict[str, Any]]:
        """Match bare except handlers."""
        matches = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                matches.append({
                    "node": node,
                    "type": "bare_except",
                    "line_number": node.lineno,
                    "column": node.col_offset,
                    "context": self._get_node_context(code, node),
                    "signature": self._get_ast_signature(node)
                })
        
        return matches

    def _match_print_calls(self, tree: ast.AST, code: str) -> List[Dict[str, Any]]:
        """Match print() function calls."""
        matches = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "print":
                    # Skip if inside function definition
                    in_function = self._is_in_function_definition(node, tree)
                    if not in_function:
                        matches.append({
                            "node": node,
                            "type": "print_call",
                            "line_number": node.lineno,
                            "column": node.col_offset,
                            "context": self._get_node_context(code, node),
                            "signature": self._get_ast_signature(node),
                            "args": [ast.unparse(arg) if hasattr(ast, 'unparse') else str(arg) for arg in node.args]
                        })
        
        return matches

    def _generic_pattern_match(
        self,
        tree: ast.AST,
        pattern_str: str,
        code: str
    ) -> List[Dict[str, Any]]:
        """Generic pattern matching (basic implementation)."""
        # This can be extended with more sophisticated pattern matching
        # For now, return empty list
        logger.debug(f"[AST-MATCHER] Generic pattern matching not fully implemented: {pattern_str}")
        return []

    def _is_in_function_definition(self, node: ast.AST, tree: ast.AST) -> bool:
        """Check if node is inside a function definition."""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.FunctionDef):
                # Simple check - can be made more precise
                if hasattr(node, 'lineno') and hasattr(parent, 'lineno'):
                    if parent.lineno <= node.lineno <= parent.lineno + len(parent.body) * 2:
                        return True
        return False

    def _get_node_context(self, code: str, node: ast.AST) -> str:
        """Get context around a node."""
        lines = code.split('\n')
        line_num = getattr(node, 'lineno', 0)
        
        if line_num <= 0 or line_num > len(lines):
            return ""
        
        start = max(0, line_num - 2)
        end = min(len(lines), line_num + 1)
        
        context = []
        for i in range(start, end):
            prefix = ">>> " if i == line_num - 1 else "    "
            context.append(f"{prefix}{lines[i]}")
        
        return "\n".join(context)

    def _get_ast_signature(self, node: ast.AST) -> str:
        """Get signature/hash of AST node for pattern matching."""
        try:
            # Serialize node structure for hashing
            node_str = ast.dump(node)
            return hashlib.sha256(node_str.encode()).hexdigest()[:16]
        except Exception as e:
            logger.warning(f"[AST-MATCHER] Failed to generate signature: {e}")
            return "unknown"

    def compute_pattern_signature(self, matches: List[Dict[str, Any]]) -> str:
        """Compute signature for a set of matches."""
        if not matches:
            return ""
        
        signatures = [m.get("signature", "") for m in matches]
        combined = "|".join(sorted(signatures))
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
