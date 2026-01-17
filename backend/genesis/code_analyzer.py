import ast
import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CodeIssue:
    """Represents a code issue detected by the analyzer."""
    issue_type: str
    severity: str  # "low", "medium", "high", "critical"
    line_number: int
    column: Optional[int]
    message: str
    suggested_fix: Optional[str]
    fix_confidence: float  # 0-1
    context: Optional[str]


class CodeAnalyzer:
    """
    Analyzes code for errors and suggests fixes.

    Like spell-check for code - highlights problems and suggests solutions.
    """

    def __init__(self):
        self.python_keywords = {
            'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
            'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
            'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
            'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
            'try', 'while', 'with', 'yield'
        }

    def analyze_python_code(self, code: str, file_path: Optional[str] = None) -> List[CodeIssue]:
        """
        Analyze Python code for errors and issues.

        Args:
            code: Python code to analyze
            file_path: Optional file path for context

        Returns:
            List of detected code issues
        """
        issues = []

        # Try to parse as AST
        try:
            tree = ast.parse(code)
            issues.extend(self._analyze_ast(tree, code))
        except SyntaxError as e:
            # Syntax error detected
            issues.append(CodeIssue(
                issue_type="syntax_error",
                severity="critical",
                line_number=e.lineno or 0,
                column=e.offset,
                message=f"Syntax Error: {e.msg}",
                suggested_fix=self._suggest_syntax_fix(code, e),
                fix_confidence=0.7,
                context=self._get_line_context(code, e.lineno or 0)
            ))

        # Check for common patterns
        issues.extend(self._check_common_patterns(code))

        # Check for style issues
        issues.extend(self._check_style_issues(code))

        return issues

    def analyze_javascript_code(self, code: str, file_path: Optional[str] = None) -> List[CodeIssue]:
        """
        Analyze JavaScript code for errors and issues.

        Args:
            code: JavaScript code to analyze
            file_path: Optional file path for context

        Returns:
            List of detected code issues
        """
        issues = []

        # Check for common JavaScript patterns
        issues.extend(self._check_js_patterns(code))

        return issues

    def _analyze_ast(self, tree: ast.AST, code: str) -> List[CodeIssue]:
        """Analyze Python AST for issues."""
        issues = []

        for node in ast.walk(tree):
            # Check for unused variables
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                # Variable assignment - could check if it's used later
                pass

            # Check for bare except clauses
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append(CodeIssue(
                        issue_type="bare_except",
                        severity="medium",
                        line_number=node.lineno,
                        column=node.col_offset,
                        message="Bare 'except:' catches all exceptions, including SystemExit and KeyboardInterrupt",
                        suggested_fix="except Exception:",
                        fix_confidence=0.9,
                        context=self._get_line_context(code, node.lineno)
                    ))

            # Check for mutable default arguments
            if isinstance(node, ast.FunctionDef):
                for arg_idx, default in enumerate(node.args.defaults):
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        issues.append(CodeIssue(
                            issue_type="mutable_default",
                            severity="high",
                            line_number=node.lineno,
                            column=node.col_offset,
                            message="Mutable default argument can cause unexpected behavior",
                            suggested_fix="Use None as default and initialize inside function",
                            fix_confidence=0.8,
                            context=self._get_line_context(code, node.lineno)
                        ))

        return issues

    def _check_common_patterns(self, code: str) -> List[CodeIssue]:
        """Check for common anti-patterns."""
        issues = []
        lines = code.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Check for print statements (should use logging)
            if re.search(r'\bprint\s*\(', line) and 'def ' not in line:
                issues.append(CodeIssue(
                    issue_type="print_statement",
                    severity="low",
                    line_number=line_num,
                    column=line.find('print'),
                    message="Consider using logging instead of print for production code",
                    suggested_fix="logger.info(...)",
                    fix_confidence=0.6,
                    context=line.strip()
                ))

            # Check for TODO comments
            if 'TODO' in line or 'FIXME' in line:
                issues.append(CodeIssue(
                    issue_type="todo_comment",
                    severity="low",
                    line_number=line_num,
                    column=line.find('TODO') if 'TODO' in line else line.find('FIXME'),
                    message="TODO/FIXME comment found - consider creating a task",
                    suggested_fix=None,
                    fix_confidence=0.0,
                    context=line.strip()
                ))

            # Check for long lines
            if len(line) > 120:
                issues.append(CodeIssue(
                    issue_type="line_too_long",
                    severity="low",
                    line_number=line_num,
                    column=120,
                    message=f"Line too long ({len(line)} > 120 characters)",
                    suggested_fix="Break line into multiple lines",
                    fix_confidence=0.3,
                    context=line[:80] + "..."
                ))

        return issues

    def _check_style_issues(self, code: str) -> List[CodeIssue]:
        """Check for style issues."""
        issues = []
        lines = code.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Check for trailing whitespace
            if line != line.rstrip():
                issues.append(CodeIssue(
                    issue_type="trailing_whitespace",
                    severity="low",
                    line_number=line_num,
                    column=len(line.rstrip()),
                    message="Trailing whitespace",
                    suggested_fix=line.rstrip(),
                    fix_confidence=1.0,
                    context=line
                ))

            # Check for inconsistent indentation
            if line and not line[0].isspace() and line_num > 1:
                prev_line = lines[line_num - 2] if line_num > 1 else ""
                if prev_line.rstrip().endswith(':'):
                    if not line.startswith(('    ', '\t')):
                        issues.append(CodeIssue(
                            issue_type="indentation",
                            severity="medium",
                            line_number=line_num,
                            column=0,
                            message="Expected indentation after colon",
                            suggested_fix="    " + line,
                            fix_confidence=0.8,
                            context=line
                        ))

        return issues

    def _check_js_patterns(self, code: str) -> List[CodeIssue]:
        """Check for JavaScript patterns and issues."""
        issues = []
        lines = code.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Check for console.log
            if re.search(r'\bconsole\.log\s*\(', line):
                issues.append(CodeIssue(
                    issue_type="console_log",
                    severity="low",
                    line_number=line_num,
                    column=line.find('console.log'),
                    message="console.log found - remove before production",
                    suggested_fix="// " + line.strip(),
                    fix_confidence=0.9,
                    context=line.strip()
                ))

            # Check for var (should use let/const)
            if re.search(r'\bvar\s+', line):
                issues.append(CodeIssue(
                    issue_type="var_usage",
                    severity="medium",
                    line_number=line_num,
                    column=line.find('var'),
                    message="Use 'let' or 'const' instead of 'var'",
                    suggested_fix=line.replace('var ', 'const '),
                    fix_confidence=0.7,
                    context=line.strip()
                ))

            # Check for == (should use ===)
            if '==' in line and '===' not in line and '!=' in line or '==' in line and '===' not in line:
                if re.search(r'[^=!<>]==[^=]', line):
                    issues.append(CodeIssue(
                        issue_type="loose_equality",
                        severity="medium",
                        line_number=line_num,
                        column=line.find('=='),
                        message="Use '===' for strict equality comparison",
                        suggested_fix=line.replace('==', '==='),
                        fix_confidence=0.8,
                        context=line.strip()
                    ))

        return issues

    def _suggest_syntax_fix(self, code: str, error: SyntaxError) -> Optional[str]:
        """Suggest a fix for syntax errors."""
        if not error.lineno:
            return None

        lines = code.split('\n')
        if error.lineno > len(lines):
            return None

        line = lines[error.lineno - 1]

        # Common syntax fixes
        if "invalid syntax" in error.msg.lower():
            # Missing colon
            if not line.rstrip().endswith(':') and any(keyword in line for keyword in ['if', 'else', 'elif', 'for', 'while', 'def', 'class', 'try', 'except', 'finally']):
                return line.rstrip() + ':'

            # Missing parenthesis
            if line.count('(') > line.count(')'):
                return line + ')'
            if line.count('(') < line.count(')'):
                return line.replace(')', '', 1)

        return None

    def _get_line_context(self, code: str, line_num: int, context_lines: int = 2) -> str:
        """Get context around a line number."""
        lines = code.split('\n')
        if line_num <= 0 or line_num > len(lines):
            return ""

        start = max(0, line_num - context_lines - 1)
        end = min(len(lines), line_num + context_lines)

        context = []
        for i in range(start, end):
            prefix = ">>> " if i == line_num - 1 else "    "
            context.append(f"{prefix}{lines[i]}")

        return "\n".join(context)

    def generate_fix_code(self, issue: CodeIssue, original_code: str) -> Optional[str]:
        """Generate the fixed code for an issue."""
        if not issue.suggested_fix:
            return None

        lines = original_code.split('\n')
        if issue.line_number <= 0 or issue.line_number > len(lines):
            return None

        # Replace the problematic line
        fixed_lines = lines.copy()
        fixed_lines[issue.line_number - 1] = issue.suggested_fix

        return '\n'.join(fixed_lines)


# Global code analyzer instance
_code_analyzer: Optional[CodeAnalyzer] = None


def get_code_analyzer() -> CodeAnalyzer:
    """Get or create the global code analyzer instance."""
    global _code_analyzer
    if _code_analyzer is None:
        _code_analyzer = CodeAnalyzer()
    return _code_analyzer
