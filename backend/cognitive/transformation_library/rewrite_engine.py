import ast
import logging
from typing import Dict, Any, List, Optional
logger = logging.getLogger(__name__)

class RewriteEngine:
    """
    Template-based code rewriting engine.
    
    Applies rewrite templates from Rule DSL to transform code.
    """

    def __init__(self):
        """Initialize Rewrite Engine."""
        pass

    def apply_rewrite(
        self,
        code: str,
        matches: List[Dict[str, Any]],
        rewrite: Dict[str, Any],
        preserve: Optional[List[str]] = None
    ) -> str:
        """
        Apply rewrite template to code based on matches.
        
        Args:
            code: Original source code
            matches: AST matches from ASTMatcher
            rewrite: Rewrite definition from Rule DSL
            preserve: List of attributes to preserve from original
        
        Returns:
            Transformed code
        """
        if not matches:
            return code

        template = rewrite.get("template", "")
        preserve_list = preserve or rewrite.get("preserve", [])
        
        if not template:
            logger.warning("[REWRITE-ENGINE] No rewrite template provided")
            return code

        lines = code.split('\n')
        transformed_lines = lines.copy()
        
        # Apply rewrites in reverse line order to preserve line numbers
        for match in sorted(matches, key=lambda m: m.get("line_number", 0), reverse=True):
            node = match.get("node")
            line_num = match.get("line_number", 0)
            
            if not node or line_num <= 0 or line_num > len(transformed_lines):
                continue
            
            # Generate replacement code from template
            replacement = self._expand_template(template, node, match, preserve_list)
            
            if replacement:
                # Replace the line(s) containing the matched node
                original_line = transformed_lines[line_num - 1]
                transformed_lines[line_num - 1] = self._replace_in_line(original_line, node, replacement)
        
        result = '\n'.join(transformed_lines)
        logger.info(f"[REWRITE-ENGINE] Applied rewrite to {len(matches)} matches")
        
        return result

    def _expand_template(
        self,
        template: str,
        node: ast.AST,
        match: Dict[str, Any],
        preserve: List[str]
    ) -> Optional[str]:
        """Expand rewrite template with values from node."""
        try:
            # Extract values from node based on preserve list
            context = {}
            
            for attr in preserve:
                if attr == "body" and hasattr(node, 'body'):
                    # Preserve body content
                    if hasattr(ast, 'unparse'):
                        context[attr] = ast.unparse(node.body) if node.body else ""
                    else:
                        context[attr] = str(node.body)
                elif attr == "name" and hasattr(node, 'name'):
                    context[attr] = node.name
                elif attr == "args" and "args" in match:
                    context[attr] = ", ".join(match["args"])
                else:
                    # Try to get attribute from node
                    if hasattr(node, attr):
                        context[attr] = getattr(node, attr)
            
            # Expand template
            try:
                result = template.format(**context)
            except KeyError as e:
                logger.warning(f"[REWRITE-ENGINE] Missing template variable: {e}")
                # Fallback: use template as-is if formatting fails
                result = template
            
            return result
        
        except Exception as e:
            logger.error(f"[REWRITE-ENGINE] Error expanding template: {e}")
            return None

    def _replace_in_line(self, line: str, node: ast.AST, replacement: str) -> str:
        """Replace node in line with replacement."""
        # Simple implementation: replace the entire line
        # More sophisticated: preserve indentation and context
        
        # Preserve indentation
        indent = len(line) - len(line.lstrip())
        indented_replacement = " " * indent + replacement.lstrip()
        
        # If node is an except handler, we need to preserve the body
        if isinstance(node, ast.ExceptHandler) and hasattr(node, 'body'):
            # Keep the rest of the line structure if possible
            # For now, simple replacement
            return indented_replacement
        
        return indented_replacement

    def generate_diff_summary(
        self,
        before_code: str,
        after_code: str
    ) -> str:
        """Generate a summary of changes between before and after code."""
        before_lines = before_code.split('\n')
        after_lines = after_code.split('\n')
        
        changes = []
        
        # Simple diff summary
        if len(before_lines) != len(after_lines):
            changes.append(f"Line count changed: {len(before_lines)} -> {len(after_lines)}")
        
        # Count changed lines
        changed_count = 0
        for i, (before, after) in enumerate(zip(before_lines, after_lines)):
            if before != after:
                changed_count += 1
                if len(changes) < 5:  # Limit to first 5 changes
                    changes.append(f"Line {i+1}: {before.strip()[:50]} -> {after.strip()[:50]}")
        
        if changed_count > 0:
            changes.insert(0, f"{changed_count} line(s) modified")
        
        return "; ".join(changes) if changes else "No changes"
