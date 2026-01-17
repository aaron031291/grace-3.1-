"""
LLM-Powered Import Healing System

Adaptive import error detection and fixing with LLM reasoning.
Handles:
- Missing imports
- Wrong import paths
- Dependency upgrade issues (renamed modules, deprecated imports)
- Version-specific import changes
- Circular import resolution

Features:
- LLM reasoning for context-aware fixes
- Dependency upgrade adaptation
- Confidence scoring for fixes
- Integration with self-healing system
"""

import logging
import ast
import re
import subprocess
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class ImportError:
    """Represents a detected import error."""
    error_type: str  # "missing_import", "wrong_path", "deprecated", "version_mismatch", "circular"
    severity: str  # "critical", "high", "medium", "low"
    file_path: str
    line_number: int
    missing_symbol: Optional[str] = None  # The symbol that's undefined
    attempted_import: Optional[str] = None  # The import that was attempted
    error_message: Optional[str] = None  # Original error message
    description: str = ""
    code_snippet: str = ""
    reasoning: str = ""  # LLM's reasoning about the fix
    suggested_import: Optional[str] = None  # The correct import statement
    suggested_fix: Optional[str] = None  # Full fix including reasoning
    confidence: float = 0.5  # 0.0-1.0
    dependency_info: Optional[Dict[str, Any]] = None  # Info about dependency versions
    context_lines: List[str] = None  # Surrounding code context


class LLMImportHealer:
    """
    Uses LLM reasoning to detect and fix import errors adaptively.
    
    Features:
    - Detects missing imports, wrong paths, deprecated modules
    - Handles dependency upgrade issues
    - Uses LLM to reason about correct imports
    - Searches codebase for symbol definitions
    - Adapts to version changes in dependencies
    """
    
    def __init__(self, llm_service=None, repo_path: Optional[Path] = None):
        """
        Initialize LLM Import Healer.
        
        Args:
            llm_service: Optional LLM service instance
            repo_path: Optional repository path for codebase searches
        """
        self.llm_service = llm_service
        if not self.llm_service:
            try:
                from llm_orchestrator.llm_service import get_llm_service
                self.llm_service = get_llm_service()
            except Exception as e:
                logger.warning(f"Could not initialize LLM service: {e}")
        
        self.repo_path = repo_path or Path.cwd()
        self._dependency_cache = {}  # Cache for dependency info
    
    def detect_import_errors(
        self,
        file_path: str,
        code: Optional[str] = None,
        error_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[ImportError]:
        """
        Detect import errors in a file using static analysis and LLM reasoning.
        
        Args:
            file_path: Path to file to analyze
            code: Optional code content (if not provided, reads from file)
            error_message: Optional error message from runtime (ImportError, ModuleNotFoundError)
            context: Optional context (dependency versions, recent changes, etc.)
            
        Returns:
            List of detected ImportError objects
        """
        if not code:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    code = f.read()
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                return []
        
        if not code:
            return []
        
        errors = []
        
        # 1. Static analysis: Find undefined names that look like imports
        static_errors = self._detect_static_import_errors(code, file_path)
        errors.extend(static_errors)
        
        # 2. Parse error messages for import errors
        if error_message:
            parsed_errors = self._parse_error_message(error_message, file_path, code)
            errors.extend(parsed_errors)
        
        # 3. Use LLM to analyze and suggest fixes for each error
        if self.llm_service:
            for error in errors:
                llm_fix = self._llm_analyze_import_error(error, code, context)
                if llm_fix:
                    # Update error with LLM reasoning and fix
                    error.reasoning = llm_fix.get("reasoning", "")
                    error.suggested_import = llm_fix.get("suggested_import")
                    error.suggested_fix = llm_fix.get("suggested_fix")
                    error.confidence = llm_fix.get("confidence", error.confidence)
                    error.dependency_info = llm_fix.get("dependency_info")
        
        # 4. Validate suggested imports against codebase
        for error in errors:
            if error.suggested_import:
                validation = self._validate_import_in_codebase(
                    error.suggested_import,
                    file_path,
                    error.missing_symbol
                )
                if not validation["valid"]:
                    error.confidence *= 0.7  # Reduce confidence if validation fails
                    if validation.get("alternative"):
                        error.suggested_import = validation["alternative"]
        
        return errors
    
    def _detect_static_import_errors(self, code: str, file_path: str) -> List[ImportError]:
        """Detect import errors using static analysis (AST)."""
        errors = []
        
        try:
            tree = ast.parse(code)
            
            # Find all names that are used but not imported/defined
            imports = set()
            defined_names = set()
            used_names = set()
            
            for node in ast.walk(tree):
                # Collect imports
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        if alias.asname:
                            imports.add(alias.asname)
                        else:
                            imports.add(alias.name.split('.')[0])  # First part of module
                
                # Collect defined names (functions, classes, variables)
                if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                    defined_names.add(node.name)
                elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    defined_names.add(node.id)
                
                # Collect used names
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
            
            # Find undefined names (used but not imported/defined, excluding builtins)
            builtins = set(dir(__builtins__))
            undefined = (used_names - defined_names - imports - builtins)
            
            # Filter to likely import errors (names that look like they should be imported)
            for name in undefined:
                # Skip obvious non-imports (lowercase with underscores, single letters)
                if not (name[0].isupper() or '_' not in name or len(name) > 3):
                    continue
                
                error = ImportError(
                    error_type="missing_import",
                    severity="high",
                    file_path=file_path,
                    line_number=0,  # Will be set by LLM analysis
                    missing_symbol=name,
                    description=f"Symbol '{name}' is used but not imported or defined",
                    code_snippet=code,
                    confidence=0.6  # Moderate confidence - needs LLM validation
                )
                errors.append(error)
                
        except SyntaxError:
            # File has syntax errors - skip static analysis
            pass
        
        return errors
    
    def _parse_error_message(
        self,
        error_message: str,
        file_path: str,
        code: str
    ) -> List[ImportError]:
        """Parse error messages for import-related errors."""
        errors = []
        
        # ModuleNotFoundError: No module named 'X'
        module_not_found = re.search(r"No module named ['\"](\w+(?:\.\w+)*)['\"]", error_message)
        if module_not_found:
            module_name = module_not_found.group(1)
            errors.append(ImportError(
                error_type="missing_import",
                severity="critical",
                file_path=file_path,
                line_number=0,
                attempted_import=module_name,
                error_message=error_message,
                description=f"Module '{module_name}' not found",
                code_snippet=code,
                confidence=0.9
            ))
        
        # ImportError: cannot import name 'X' from 'Y'
        import_error = re.search(
            r"cannot import name ['\"](\w+)['\"] from ['\"](\w+(?:\.\w+)*)['\"]",
            error_message
        )
        if import_error:
            symbol = import_error.group(1)
            module = import_error.group(2)
            errors.append(ImportError(
                error_type="wrong_path",
                severity="critical",
                file_path=file_path,
                line_number=0,
                missing_symbol=symbol,
                attempted_import=f"{module}.{symbol}",
                error_message=error_message,
                description=f"Cannot import '{symbol}' from '{module}'",
                code_snippet=code,
                confidence=0.9
            ))
        
        # NameError: name 'X' is not defined
        name_error = re.search(r"name ['\"](\w+)['\"] is not defined", error_message)
        if name_error:
            symbol = name_error.group(1)
            # This could be an import error or a different issue
            errors.append(ImportError(
                error_type="missing_import",
                severity="medium",
                file_path=file_path,
                line_number=0,
                missing_symbol=symbol,
                error_message=error_message,
                description=f"Name '{symbol}' is not defined (possible missing import)",
                code_snippet=code,
                confidence=0.5  # Lower confidence - might not be an import issue
            ))
        
        return errors
    
    def _llm_analyze_import_error(
        self,
        error: ImportError,
        code: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Use LLM to analyze import error and suggest fix.
        
        This is where the adaptive reasoning happens:
        - Handles dependency upgrades
        - Finds correct import paths
        - Understands version-specific changes
        """
        if not self.llm_service:
            return None
        
        # Get dependency information
        dependency_info = self._get_dependency_info(context)
        
        # Build prompt for LLM
        prompt = self._build_import_healing_prompt(error, code, dependency_info, context)
        
        try:
            response = self.llm_service.generate(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.2,  # Low temperature for deterministic fixes
                system_prompt=self._get_system_prompt()
            )
            
            # Parse LLM response
            fix = self._parse_llm_response(response, error)
            return fix
            
        except Exception as e:
            logger.error(f"[IMPORT-HEALER] LLM analysis failed: {e}")
            return None
    
    def _build_import_healing_prompt(
        self,
        error: ImportError,
        code: str,
        dependency_info: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for LLM import healing."""
        
        dependency_str = ""
        if dependency_info:
            dep_list = [f"{name}=={version}" for name, version in dependency_info.items()]
            dependency_str = f"\nInstalled Dependencies:\n" + "\n".join(dep_list)
        
        context_str = ""
        if context:
            if "recent_changes" in context:
                context_str += f"\nRecent Changes: {context['recent_changes']}\n"
            if "dependency_upgrade" in context:
                context_str += f"\nDependency Upgrade Detected: {context['dependency_upgrade']}\n"
        
        prompt = f"""Analyze this import error and suggest the correct fix:

Error Type: {error.error_type}
File: {error.file_path}
{dependency_str}
{context_str}

Error Details:
- Missing Symbol: {error.missing_symbol or 'N/A'}
- Attempted Import: {error.attempted_import or 'N/A'}
- Error Message: {error.error_message or 'N/A'}
- Description: {error.description}

File Code:
```python
{code[:3000]}  # First 3000 chars
```

Consider:
1. **Missing Import**: Add the correct import statement at the top
2. **Wrong Path**: Fix the import path (relative vs absolute, package structure)
3. **Dependency Upgrade**: Check if module was renamed, moved, or deprecated in newer versions
4. **Version Mismatch**: Import path may have changed between dependency versions
5. **Circular Import**: May need to restructure imports

For dependency upgrades, consider:
- Module renaming (e.g., `distutils` → `setuptools`)
- Package restructuring (e.g., `urllib2` → `urllib.request`)
- Deprecated modules moved to different packages
- API changes requiring different imports

Provide your analysis in this JSON format:
{{
  "reasoning": "Your step-by-step reasoning about why this import error occurred and how to fix it",
  "suggested_import": "from module import Symbol  or  import module",
  "suggested_fix": "Full fix explanation including import statement and where to place it",
  "confidence": 0.0-1.0,
  "dependency_info": {{
    "package_name": "package that provides this import",
    "version_requirement": "version where this import is available",
    "alternative_if_deprecated": "alternative import if deprecated"
  }},
  "line_number": <suggested line number for import (usually near top)>
}}

Focus on being specific and accurate. For dependency upgrades, explain what changed and why.
"""
        
        return prompt
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for import healing."""
        return """You are an expert Python developer specializing in import error resolution and 
dependency management. You understand:
- Python import system (absolute vs relative imports, packages, modules)
- Common dependency upgrade issues (module renames, API changes)
- How to find correct import paths in codebases
- Version-specific import changes in popular packages

You provide clear, accurate import fixes with reasoning, especially for dependency upgrade scenarios.
You adapt your suggestions based on installed dependency versions."""
    
    def _parse_llm_response(
        self,
        response: str,
        error: ImportError
    ) -> Optional[Dict[str, Any]]:
        """Parse LLM response into fix dictionary."""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                return {
                    "reasoning": data.get("reasoning", ""),
                    "suggested_import": data.get("suggested_import"),
                    "suggested_fix": data.get("suggested_fix", ""),
                    "confidence": data.get("confidence", 0.7),
                    "dependency_info": data.get("dependency_info"),
                    "line_number": data.get("line_number", 1)
                }
        except Exception as e:
            logger.warning(f"[IMPORT-HEALER] Failed to parse LLM JSON response: {e}")
        
        # Fallback: Extract import statement from text
        import_match = re.search(
            r"(?:from\s+\S+\s+)?import\s+\S+",
            response,
            re.IGNORECASE
        )
        if import_match:
            return {
                "reasoning": response[:500],
                "suggested_import": import_match.group(0),
                "suggested_fix": response,
                "confidence": 0.6,
                "dependency_info": None,
                "line_number": 1
            }
        
        return None
    
    def _get_dependency_info(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Get information about installed dependencies."""
        if self._dependency_cache:
            return self._dependency_cache
        
        try:
            # Try to read requirements.txt or similar
            req_file = self.repo_path / "requirements.txt"
            if req_file.exists():
                with open(req_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if '==' in line:
                            parts = line.split('==')
                            if len(parts) == 2:
                                self._dependency_cache[parts[0].strip()] = parts[1].strip()
            
            # Also try pip list
            try:
                result = subprocess.run(
                    ["pip", "list", "--format=freeze"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if '==' in line:
                            parts = line.split('==')
                            if len(parts) == 2:
                                self._dependency_cache[parts[0].strip()] = parts[1].strip()
            except Exception:
                pass  # pip not available or command failed
            
        except Exception as e:
            logger.debug(f"[IMPORT-HEALER] Could not read dependency info: {e}")
        
        return self._dependency_cache
    
    def _validate_import_in_codebase(
        self,
        import_statement: str,
        file_path: str,
        symbol: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate that an import statement makes sense in the codebase context.
        
        Returns:
            Dict with 'valid' bool and optional 'alternative' import
        """
        # Extract module path from import statement
        # Simple validation - could be enhanced with actual file system checks
        if "from" in import_statement:
            # from X import Y
            match = re.search(r"from\s+([\w.]+)\s+import", import_statement)
            if match:
                module_path = match.group(1)
                # Check if it's a relative import
                if module_path.startswith('.'):
                    return {"valid": True}  # Relative imports are hard to validate statically
                # Check if module file exists (rough check)
                module_file = self.repo_path / module_path.replace('.', '/') / "__init__.py"
                module_file_alt = self.repo_path / module_path.replace('.', '/') / (module_path.split('.')[-1] + ".py")
                if module_file.exists() or module_file_alt.exists():
                    return {"valid": True}
        
        # For now, trust the LLM suggestion
        return {"valid": True}
    
    def apply_fix(
        self,
        error: ImportError,
        code: str,
        auto_apply: bool = False
    ) -> Tuple[str, str]:
        """
        Apply import fix to code.
        
        Args:
            error: ImportError with suggested fix
            code: Original code
            auto_apply: Whether to automatically apply the fix
            
        Returns:
            Tuple of (fixed_code, explanation)
        """
        if not error.suggested_import:
            return code, "No suggested import available"
        
        lines = code.split('\n')
        
        # Find insertion point (after existing imports, before code)
        insert_line = error.line_number if error.line_number > 0 else self._find_import_insertion_point(lines)
        
        # Check if import already exists
        import_statement = error.suggested_import
        if any(import_statement.strip() in line for line in lines):
            return code, "Import already exists in file"
        
        # Insert import
        lines.insert(insert_line, import_statement)
        fixed_code = '\n'.join(lines)
        
        explanation = f"Added import: {import_statement}\nReasoning: {error.reasoning}"
        
        return fixed_code, explanation
    
    def _find_import_insertion_point(self, lines: List[str]) -> int:
        """Find the best line to insert a new import."""
        # Find the last import statement
        last_import = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')) and not stripped.startswith('#'):
                last_import = i
        
        if last_import >= 0:
            return last_import + 1
        
        # Find first non-comment, non-blank line
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                return i
        
        return 0


def get_import_healer(llm_service=None, repo_path: Optional[Path] = None) -> LLMImportHealer:
    """Get or create LLM Import Healer instance."""
    global _import_healer_instance
    
    if '_import_healer_instance' not in globals():
        _import_healer_instance = None
        
    if _import_healer_instance is None:
        _import_healer_instance = LLMImportHealer(llm_service=llm_service, repo_path=repo_path)
        
    return _import_healer_instance
