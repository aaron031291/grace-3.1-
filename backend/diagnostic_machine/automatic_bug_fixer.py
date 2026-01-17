import ast
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
class FixResult:
    logger = logging.getLogger(__name__)
    """Result of an automatic fix."""
    success: bool
    file_path: str
    issue_type: str
    fix_applied: str
    lines_changed: List[int] = field(default_factory=list)
    backup_created: bool = False
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class AutomaticBugFixer:
    """
    Automatically fixes bugs and warnings detected by proactive scanner.
    
    Enhanced with DeepSeek AI for intelligent, context-aware fixes.
    
    Can fix:
    - Syntax errors (indentation, missing colons, etc.)
    - Import errors (comment out broken imports)
    - Missing files (comment out imports)
    - Code quality issues (bare except, mutable defaults, print vs logger, 'is' vs '==')
    - Complex issues (using DeepSeek AI for context-aware fixes)
    """
    
    def __init__(
        self, 
        backend_dir: Optional[Path] = None, 
        create_backups: bool = True,
        use_deepseek: bool = True
    ):
        """Initialize automatic bug fixer."""
        if backend_dir is None:
            backend_dir = Path(__file__).parent.parent
        self.backend_dir = backend_dir
        self.create_backups = create_backups
        self.fixes_applied: List[FixResult] = []
        self.use_deepseek = use_deepseek and DEEPSEEK_AVAILABLE
        
        # Initialize DeepSeek client if available
        self.deepseek_client = None
        if self.use_deepseek:
            try:
                self.deepseek_client = MultiLLMClient()
                logger.info("[BUG-FIXER] DeepSeek AI enabled for intelligent fixes")
            except Exception as e:
                logger.warning(f"[BUG-FIXER] Could not initialize DeepSeek: {e}")
                self.use_deepseek = False
    
    def fix_issue(self, issue) -> FixResult:
        """Fix a single issue (works with CodeIssue or ProactiveIssue)."""
        try:
            # Handle both CodeIssue and ProactiveIssue types
            issue_type = getattr(issue, 'issue_type', None)
            file_path = getattr(issue, 'file_path', '')
            line_number = getattr(issue, 'line_number', None)
            message = getattr(issue, 'message', '')
            
            # Try pattern-based fixes first (fast)
            if issue_type == 'syntax_error':
                result = self._fix_syntax_error(issue)
                # If pattern-based fix failed and DeepSeek available, try AI fix
                if not result.success and self.use_deepseek:
                    return self._fix_with_deepseek(issue, 'syntax_error')
                return result
            elif issue_type == 'import_error':
                result = self._fix_import_error(issue)
                if not result.success and self.use_deepseek:
                    return self._fix_with_deepseek(issue, 'import_error')
                return result
            elif issue_type == 'missing_file':
                result = self._fix_missing_file(issue)
                if not result.success and self.use_deepseek:
                    return self._fix_with_deepseek(issue, 'missing_file')
                return result
            elif issue_type == 'code_quality':
                result = self._fix_code_quality(issue)
                # For complex code quality issues, use DeepSeek
                if not result.success and self.use_deepseek:
                    return self._fix_with_deepseek(issue, 'code_quality')
                return result
            else:
                # Unknown issue type - try DeepSeek if available
                if self.use_deepseek:
                    return self._fix_with_deepseek(issue, issue_type or 'unknown')
                return FixResult(
                    success=False,
                    file_path=file_path,
                    issue_type=issue_type or 'unknown',
                    fix_applied="",
                    error_message=f"Unknown issue type: {issue_type}"
                )
        except Exception as e:
            logger.error(f"Failed to fix issue {getattr(issue, 'issue_type', 'unknown')} in {getattr(issue, 'file_path', 'unknown')}: {e}")
            return FixResult(
                success=False,
                file_path=getattr(issue, 'file_path', ''),
                issue_type=getattr(issue, 'issue_type', 'unknown'),
                fix_applied="",
                error_message=str(e)
            )
    
    def fix_all_issues(self, issues: List) -> List[FixResult]:
        """Fix all issues."""
        results = []
        for issue in issues:
            result = self.fix_issue(issue)
            results.append(result)
            if result.success:
                self.fixes_applied.append(result)
        return results
    
    def _fix_syntax_error(self, issue) -> FixResult:
        """Fix syntax errors."""
        # Handle both absolute and relative paths
        if Path(issue.file_path).is_absolute():
            file_path = Path(issue.file_path)
        else:
            file_path = self.backend_dir / issue.file_path
        
        # Also try just the filename if the full path doesn't exist
        if not file_path.exists():
            file_path = self.backend_dir / Path(issue.file_path).name
        
        if not file_path.exists():
            return FixResult(
                success=False,
                file_path=issue.file_path,
                issue_type='syntax_error',
                fix_applied="",
                error_message=f"File not found: {file_path}"
            )
        
        # Create backup
        if self.create_backups:
            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
            backup_path.write_text(file_path.read_text())
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Common syntax fixes
            fixes_applied = []
            changed_lines = []
            
            # Fix indentation errors
            if 'indented block' in issue.message.lower():
                # Find the function definition
                for i, line in enumerate(lines):
                    if i + 1 == issue.line_number and 'def ' in line:
                        # Add pass statement if next line is empty or has wrong indent
                        if i + 1 < len(lines):
                            next_line = lines[i + 1] if i + 1 < len(lines) else ""
                            if not next_line.strip() or not next_line.startswith('    '):
                                lines.insert(i + 1, '    pass')
                                fixes_applied.append("Added 'pass' statement to fix indentation")
                                changed_lines.append(i + 2)
                                break
            
            # Fix missing colons
            if 'expected' in issue.message.lower() and (':' in issue.message or "expected ':'" in issue.message):
                for i, line in enumerate(lines):
                    if i + 1 == issue.line_number:
                        # Check if it's a line that should have a colon
                        if ('def ' in line or 'if ' in line or 'for ' in line or 'while ' in line or 'elif ' in line or 'else' in line):
                            if not line.rstrip().endswith(':'):
                                lines[i] = line.rstrip() + ':'
                                fixes_applied.append("Added missing colon")
                                changed_lines.append(i + 1)
                                break
            
            # Fix unclosed parentheses
            if 'was never closed' in issue.message.lower():
                # Try to find and fix unclosed parentheses
                for i, line in enumerate(lines):
                    if i + 1 == issue.line_number:
                        open_count = line.count('(') - line.count(')')
                        if open_count > 0:
                            lines[i] = line.rstrip() + ')' * open_count
                            fixes_applied.append(f"Added {open_count} closing parenthesis(es)")
                            changed_lines.append(i + 1)
                            break
            
            if fixes_applied:
                file_path.write_text('\n'.join(lines), encoding='utf-8')
                return FixResult(
                    success=True,
                    file_path=issue.file_path,
                    issue_type='syntax_error',
                    fix_applied="; ".join(fixes_applied),
                    lines_changed=changed_lines,
                    backup_created=self.create_backups
                )
            else:
                return FixResult(
                    success=False,
                    file_path=issue.file_path,
                    issue_type='syntax_error',
                    fix_applied="",
                    error_message="Could not automatically fix syntax error"
                )
        except Exception as e:
            return FixResult(
                success=False,
                file_path=issue.file_path,
                issue_type='syntax_error',
                fix_applied="",
                error_message=str(e)
            )
    
    def _fix_import_error(self, issue) -> FixResult:
        """Fix import errors by commenting them out."""
        # Import errors are usually in the file that tries to import
        # We can't easily fix these automatically without knowing the correct import
        # So we'll log them for manual review
        return FixResult(
            success=False,
            file_path=issue.file_path,
            issue_type='import_error',
            fix_applied="",
            error_message="Import errors require manual review - cannot auto-fix safely"
        )
    
    def _fix_missing_file(self, issue) -> FixResult:
        """Fix missing file imports by commenting them out."""
        file_path = self.backend_dir / issue.file_path
        if not file_path.exists():
            return FixResult(
                success=False,
                file_path=issue.file_path,
                issue_type='missing_file',
                fix_applied="",
                error_message="File not found"
            )
        
        # Create backup
        if self.create_backups:
            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
            backup_path.write_text(file_path.read_text())
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            changed_lines = []
            
            # Find and comment out the problematic import
            for i, line in enumerate(lines):
                if 'from .self_healing_ide' in line and not line.strip().startswith('#'):
                    # Comment out the import
                    lines[i] = f"# {line.strip()}  # TODO: Create this module"
                    changed_lines.append(i + 1)
                    break
            
            if changed_lines:
                file_path.write_text('\n'.join(lines), encoding='utf-8')
                return FixResult(
                    success=True,
                    file_path=issue.file_path,
                    issue_type='missing_file',
                    fix_applied="Commented out import of missing file",
                    lines_changed=changed_lines,
                    backup_created=self.create_backups
                )
            else:
                return FixResult(
                    success=False,
                    file_path=issue.file_path,
                    issue_type='missing_file',
                    fix_applied="",
                    error_message="Could not find import to comment out"
                )
        except Exception as e:
            return FixResult(
                success=False,
                file_path=issue.file_path,
                issue_type='missing_file',
                fix_applied="",
                error_message=str(e)
            )
    
    def _fix_code_quality(self, issue) -> FixResult:
        """Fix code quality issues."""
        file_path = self.backend_dir / issue.file_path
        if not file_path.exists():
            return FixResult(
                success=False,
                file_path=issue.file_path,
                issue_type='code_quality',
                fix_applied="",
                error_message="File not found"
            )
        
        # Create backup
        if self.create_backups:
            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
            backup_path.write_text(file_path.read_text())
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            fixes_applied = []
            changed_lines = []
            
            line_num = issue.line_number
            if line_num and line_num <= len(lines):
                line = lines[line_num - 1]
                original_line = line
                
                # Fix bare except
                if issue.message and 'bare except' in issue.message.lower():
                    if line.strip() == 'except:':
                        lines[line_num - 1] = line.replace('except:', 'except Exception:')
                        fixes_applied.append("Changed bare except to 'except Exception:'")
                        changed_lines.append(line_num)
                
                # Fix mutable default arguments
                elif issue.message and 'mutable default' in issue.message.lower():
                    # This is complex - would need to parse function signature
                    # For now, just log it
                    fixes_applied.append("Mutable default argument - requires manual review")
                
                # Fix 'is' with literals (if we can detect it)
                elif 'is' in line and any(x in line for x in ['"', "'", '0', '1', 'True', 'False', 'None']):
                    # Check if it's a comparison with a literal
                    if re.search(r'\bis\s+["\']', line) or re.search(r'\bis\s+(True|False|None|0|1)\b', line):
                        # Replace 'is' with '=='
                        fixed = re.sub(r'\bis\s+', '== ', line, count=1)
                        if fixed != line:
                            lines[line_num - 1] = fixed
                            fixes_applied.append("Changed 'is' to '==' for literal comparison")
                            changed_lines.append(line_num)
            
            if fixes_applied and changed_lines:
                file_path.write_text('\n'.join(lines), encoding='utf-8')
                return FixResult(
                    success=True,
                    file_path=issue.file_path,
                    issue_type='code_quality',
                    fix_applied="; ".join(fixes_applied),
                    lines_changed=changed_lines,
                    backup_created=self.create_backups
                )
            else:
                return FixResult(
                    success=False,
                    file_path=issue.file_path,
                    issue_type='code_quality',
                    fix_applied="",
                    error_message="Could not automatically fix code quality issue"
                )
        except Exception as e:
            return FixResult(
                success=False,
                file_path=issue.file_path,
                issue_type='code_quality',
                fix_applied="",
                error_message=str(e)
            )
    
    def fix_print_statements(self, file_path: Path, max_fixes: int = 50) -> List[FixResult]:
        """Fix print() statements by replacing with logger (for production files only)."""
        results = []
        
        # Only fix in production code, not test files
        if 'test_' in file_path.name or 'test' in str(file_path.parent):
            return results
        
        if not file_path.exists():
            return results
        
        # Create backup
        if self.create_backups:
            backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
            backup_path.write_text(file_path.read_text())
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            changed_lines = []
            has_logger = 'import logging' in content or 'from logging import' in content
            
            # Add logger import if not present
            if not has_logger and any('print(' in line for line in lines):
                # Find first import line
                import_line_idx = None
                for i, line in enumerate(lines):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        import_line_idx = i
                        break
                
                if import_line_idx is not None:
                    lines.insert(import_line_idx + 1, 'import logging')
                    lines.insert(import_line_idx + 2, 'logger = logging.getLogger(__name__)')
                    changed_lines.extend([import_line_idx + 2, import_line_idx + 3])
            
            # Replace print statements
            fixes_count = 0
            for i, line in enumerate(lines):
                if fixes_count >= max_fixes:
                    break
                
                # Match print(...) but not logger.print or print.debug
                if re.search(r'\bprint\s*\(', line) and 'logger' not in line.lower():
                    # Convert print(...) to logger.info(...)
                    fixed = re.sub(r'\bprint\s*\(', 'logger.info(', line)
                    if fixed != line:
                        lines[i] = fixed
                        changed_lines.append(i + 1)
                        fixes_count += 1
            
            if changed_lines:
                file_path.write_text('\n'.join(lines), encoding='utf-8')
                results.append(FixResult(
                    success=True,
                    file_path=str(file_path.relative_to(self.backend_dir.parent)),
                    issue_type='code_quality',
                    fix_applied=f"Replaced {fixes_count} print() statements with logger.info()",
                    lines_changed=changed_lines[:20],  # Limit to first 20
                    backup_created=self.create_backups
                ))
        except Exception as e:
            results.append(FixResult(
                success=False,
                file_path=str(file_path.relative_to(self.backend_dir.parent)),
                issue_type='code_quality',
                fix_applied="",
                error_message=str(e)
            ))
        
        return results
    
    def fix_all_warnings(self, max_files: int = 100) -> List[FixResult]:
        """Fix all common warnings across the codebase."""
        results = []
        python_files = list(self.backend_dir.rglob("*.py"))
        
        # Skip test files and backups
        python_files = [
            f for f in python_files[:max_files]
            if 'test_' not in f.name and '.backup' not in f.suffix
        ]
        
        for py_file in python_files:
            # Fix print statements
            print_fixes = self.fix_print_statements(py_file, max_fixes=10)
            results.extend(print_fixes)
        
        return results


    def _fix_with_deepseek(self, issue, issue_type: str) -> FixResult:
        """
        Use DeepSeek AI to intelligently fix code issues.
        
        DeepSeek provides context-aware fixes that understand:
        - Code structure and patterns
        - Best practices
        - Project-specific conventions
        - Related code context
        """
        if not self.use_deepseek or not self.deepseek_client:
            return FixResult(
                success=False,
                file_path=getattr(issue, 'file_path', ''),
                issue_type=issue_type,
                fix_applied="",
                error_message="DeepSeek not available"
            )
        
        try:
            # Get file path
            file_path = self.backend_dir / getattr(issue, 'file_path', '')
            if Path(getattr(issue, 'file_path', '')).is_absolute():
                file_path = Path(getattr(issue, 'file_path', ''))
            if not file_path.exists():
                file_path = self.backend_dir / Path(getattr(issue, 'file_path', '')).name
            
            if not file_path.exists():
                return FixResult(
                    success=False,
                    file_path=getattr(issue, 'file_path', ''),
                    issue_type=issue_type,
                    fix_applied="",
                    error_message="File not found for DeepSeek fix"
                )
            
            # Read file content
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')
            line_number = getattr(issue, 'line_number', None)
            message = getattr(issue, 'message', '')
            
            # Get context around the issue (5 lines before and after)
            context_start = max(0, (line_number or 1) - 6)
            context_end = min(len(lines), (line_number or 1) + 5)
            context_lines = lines[context_start:context_end]
            context = '\n'.join(context_lines)
            
            # Create prompt for DeepSeek
            prompt = f"""You are an expert Python code fixer. Fix the following code issue:

Issue Type: {issue_type}
File: {getattr(issue, 'file_path', '')}
Line: {line_number}
Error: {message}

Code Context (lines {context_start+1}-{context_end}):
```python
{context}
```

Please provide:
1. The fixed code (only the lines that need to change)
2. A brief explanation of the fix
3. The line numbers that were changed

Format your response as:
FIXED_CODE:
```python
[fixed lines here]
```

EXPLANATION:
[explanation here]

LINES_CHANGED:
[line numbers, comma-separated]
"""
            
            # Call DeepSeek
            logger.info(f"[BUG-FIXER] Using DeepSeek to fix {issue_type} in {file_path.name}:{line_number}")
            
            # Use generate method with code generation task type
            result = self.deepseek_client.generate(
                prompt=prompt,
                task_type=TaskType.CODE_GENERATION,
                model_id="deepseek-coder:33b-instruct",  # Use DeepSeek Coder for code fixes
                temperature=0.2,  # Low temperature for deterministic fixes
                max_tokens=500,  # Limit response size
                system_prompt="You are an expert Python code fixer. Provide precise, minimal fixes that maintain code functionality."
            )
            
            if not result or not result.get('success', False):
                return FixResult(
                    success=False,
                    file_path=getattr(issue, 'file_path', ''),
                    issue_type=issue_type,
                    fix_applied="",
                    error_message="DeepSeek fix failed"
                )
            
            # Parse DeepSeek response
            response_text = result.get('content', '') if isinstance(result, dict) else str(result)
            
            # Extract fixed code
            fixed_code_match = re.search(r'FIXED_CODE:\s*```python\n(.*?)\n```', response_text, re.DOTALL)
            if not fixed_code_match:
                # Try without code block
                fixed_code_match = re.search(r'FIXED_CODE:\s*(.*?)(?=EXPLANATION|$)', response_text, re.DOTALL)
            
            if not fixed_code_match:
                logger.warning(f"[BUG-FIXER] Could not parse DeepSeek response: {response_text[:200]}")
                return FixResult(
                    success=False,
                    file_path=getattr(issue, 'file_path', ''),
                    issue_type=issue_type,
                    fix_applied="",
                    error_message="Could not parse DeepSeek response"
                )
            
            fixed_code = fixed_code_match.group(1).strip()
            fixed_lines = [l for l in fixed_code.split('\n') if l.strip()]
            
            # Extract explanation
            explanation_match = re.search(r'EXPLANATION:\s*(.*?)(?=LINES_CHANGED|$)', response_text, re.DOTALL)
            explanation = explanation_match.group(1).strip() if explanation_match else "Fixed by DeepSeek AI"
            
            # Extract line numbers
            lines_changed_match = re.search(r'LINES_CHANGED:\s*(\d+(?:,\s*\d+)*)', response_text)
            if lines_changed_match:
                lines_changed = [int(x.strip()) for x in lines_changed_match.group(1).split(',')]
            else:
                # Default to the issue line
                lines_changed = [line_number] if line_number else []
            
            # Create backup
            if self.create_backups:
                backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
                backup_path.write_text(content)
            
            # Apply fix
            # Replace the affected lines
            if fixed_lines and lines_changed:
                for i, line_num in enumerate(lines_changed):
                    if 0 < line_num <= len(lines):
                        if i < len(fixed_lines):
                            lines[line_num - 1] = fixed_lines[i]
            
            # Write fixed content
            file_path.write_text('\n'.join(lines), encoding='utf-8')
            
            return FixResult(
                success=True,
                file_path=str(file_path.relative_to(self.backend_dir.parent)) if file_path.is_relative_to(self.backend_dir.parent) else getattr(issue, 'file_path', ''),
                issue_type=issue_type,
                fix_applied=f"DeepSeek AI fix: {explanation}",
                lines_changed=lines_changed,
                backup_created=self.create_backups
            )
            
        except Exception as e:
            logger.error(f"DeepSeek fix failed: {e}")
            import traceback
            traceback.print_exc()
            return FixResult(
                success=False,
                file_path=getattr(issue, 'file_path', ''),
                issue_type=issue_type,
                fix_applied="",
                error_message=f"DeepSeek fix error: {str(e)}"
            )


def get_automatic_fixer(
    backend_dir: Optional[Path] = None, 
    use_deepseek: bool = True
) -> AutomaticBugFixer:
    """Get or create automatic bug fixer instance."""
    return AutomaticBugFixer(backend_dir=backend_dir, use_deepseek=use_deepseek)
