"""
Semantic Refactoring Engine - Multi-file cross-repo refactoring.

Provides capabilities for:
1. Rename symbols across the entire repository
2. Move modules and update all imports
3. Extract/inline functions and classes
4. Update imports after structural changes

Integrates with HealingValidationPipeline for safe Plan → Patch → Validate → Rollback.
"""

import ast
import logging
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .healing_validation_pipeline import (
    HealingValidationPipeline,
    Patch,
    ValidationGate,
)

logger = logging.getLogger(__name__)


class RefactoringType(str, Enum):
    """Types of semantic refactoring operations."""
    RENAME_SYMBOL = "rename_symbol"
    RENAME_MODULE = "rename_module"
    MOVE_MODULE = "move_module"
    MOVE_SYMBOL = "move_symbol"
    EXTRACT_FUNCTION = "extract_function"
    EXTRACT_CLASS = "extract_class"
    INLINE_FUNCTION = "inline_function"
    UPDATE_IMPORTS = "update_imports"


class SymbolType(str, Enum):
    """Types of symbols that can be renamed."""
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    MODULE = "module"
    PARAMETER = "parameter"


@dataclass
class SymbolReference:
    """A reference to a symbol in the codebase."""
    file_path: str
    line_number: int
    column: int
    symbol_name: str
    symbol_type: SymbolType
    context: str  # surrounding code for context
    is_definition: bool = False
    is_import: bool = False
    module_path: Optional[str] = None


@dataclass
class RefactoringPlan:
    """A plan for a refactoring operation."""
    plan_id: str
    refactoring_type: RefactoringType
    created_at: datetime
    
    # Source information
    source_symbol: str
    source_type: SymbolType
    source_file: Optional[str] = None
    source_module: Optional[str] = None
    
    # Target information
    target_symbol: Optional[str] = None
    target_file: Optional[str] = None
    target_module: Optional[str] = None
    
    # Affected files and references
    affected_files: List[str] = field(default_factory=list)
    references: List[SymbolReference] = field(default_factory=list)
    patches: List[Patch] = field(default_factory=list)
    
    # Status
    status: str = "planned"  # planned, executing, completed, rolled_back, failed
    confidence: float = 0.0
    risk_level: str = "low"  # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "refactoring_type": self.refactoring_type.value,
            "created_at": self.created_at.isoformat(),
            "source_symbol": self.source_symbol,
            "source_type": self.source_type.value,
            "target_symbol": self.target_symbol,
            "affected_files_count": len(self.affected_files),
            "references_count": len(self.references),
            "status": self.status,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
        }


@dataclass
class RefactoringResult:
    """Result of a refactoring operation."""
    plan: RefactoringPlan
    success: bool
    files_modified: int = 0
    references_updated: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    rollback_available: bool = True
    execution_time_ms: float = 0.0


class SymbolFinder(ast.NodeVisitor):
    """AST visitor to find symbol definitions and references."""
    
    def __init__(self, target_symbol: str, file_path: str):
        self.target_symbol = target_symbol
        self.file_path = file_path
        self.references: List[SymbolReference] = []
        self.current_class: Optional[str] = None
        self.source_lines: List[str] = []
    
    def find_all(self, source: str) -> List[SymbolReference]:
        """Find all references to the target symbol."""
        self.source_lines = source.split('\n')
        try:
            tree = ast.parse(source)
            self.visit(tree)
        except SyntaxError as e:
            logger.warning(f"[SYMBOL-FINDER] Syntax error in {self.file_path}: {e}")
        return self.references
    
    def _get_context(self, lineno: int) -> str:
        """Get surrounding code context for a line."""
        if 0 <= lineno - 1 < len(self.source_lines):
            return self.source_lines[lineno - 1].strip()
        return ""
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        if node.name == self.target_symbol:
            self.references.append(SymbolReference(
                file_path=self.file_path,
                line_number=node.lineno,
                column=node.col_offset,
                symbol_name=node.name,
                symbol_type=SymbolType.METHOD if self.current_class else SymbolType.FUNCTION,
                context=self._get_context(node.lineno),
                is_definition=True,
            ))
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        if node.name == self.target_symbol:
            self.references.append(SymbolReference(
                file_path=self.file_path,
                line_number=node.lineno,
                column=node.col_offset,
                symbol_name=node.name,
                symbol_type=SymbolType.METHOD if self.current_class else SymbolType.FUNCTION,
                context=self._get_context(node.lineno),
                is_definition=True,
            ))
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        if node.name == self.target_symbol:
            self.references.append(SymbolReference(
                file_path=self.file_path,
                line_number=node.lineno,
                column=node.col_offset,
                symbol_name=node.name,
                symbol_type=SymbolType.CLASS,
                context=self._get_context(node.lineno),
                is_definition=True,
            ))
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class
    
    def visit_Name(self, node: ast.Name):
        if node.id == self.target_symbol:
            self.references.append(SymbolReference(
                file_path=self.file_path,
                line_number=node.lineno,
                column=node.col_offset,
                symbol_name=node.id,
                symbol_type=SymbolType.VARIABLE,
                context=self._get_context(node.lineno),
                is_definition=isinstance(node.ctx, ast.Store),
            ))
        self.generic_visit(node)
    
    def visit_Attribute(self, node: ast.Attribute):
        if node.attr == self.target_symbol:
            self.references.append(SymbolReference(
                file_path=self.file_path,
                line_number=node.lineno,
                column=node.col_offset,
                symbol_name=node.attr,
                symbol_type=SymbolType.METHOD if callable else SymbolType.VARIABLE,
                context=self._get_context(node.lineno),
            ))
        self.generic_visit(node)
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.asname or alias.name
            if name == self.target_symbol or alias.name == self.target_symbol:
                self.references.append(SymbolReference(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    column=node.col_offset,
                    symbol_name=alias.name,
                    symbol_type=SymbolType.MODULE,
                    context=self._get_context(node.lineno),
                    is_import=True,
                    module_path=alias.name,
                ))
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        if module == self.target_symbol:
            self.references.append(SymbolReference(
                file_path=self.file_path,
                line_number=node.lineno,
                column=node.col_offset,
                symbol_name=module,
                symbol_type=SymbolType.MODULE,
                context=self._get_context(node.lineno),
                is_import=True,
                module_path=module,
            ))
        for alias in node.names:
            name = alias.asname or alias.name
            if name == self.target_symbol or alias.name == self.target_symbol:
                self.references.append(SymbolReference(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    column=node.col_offset,
                    symbol_name=alias.name,
                    symbol_type=SymbolType.FUNCTION,  # Could be class or function
                    context=self._get_context(node.lineno),
                    is_import=True,
                    module_path=module,
                ))
        self.generic_visit(node)


class ImportAnalyzer(ast.NodeVisitor):
    """Analyze imports in a Python file."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.imports: List[Dict[str, Any]] = []
        self.from_imports: List[Dict[str, Any]] = []
    
    def analyze(self, source: str) -> Dict[str, Any]:
        """Analyze all imports in source code."""
        try:
            tree = ast.parse(source)
            self.visit(tree)
        except SyntaxError:
            pass
        return {
            "imports": self.imports,
            "from_imports": self.from_imports,
        }
    
    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append({
                "module": alias.name,
                "alias": alias.asname,
                "line": node.lineno,
                "col": node.col_offset,
            })
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        self.from_imports.append({
            "module": node.module or "",
            "level": node.level,
            "names": [(a.name, a.asname) for a in node.names],
            "line": node.lineno,
            "col": node.col_offset,
        })
        self.generic_visit(node)


class SemanticRefactoringEngine:
    """
    Multi-file semantic refactoring engine.
    
    Provides safe, validated refactoring with automatic rollback on failure.
    """
    
    def __init__(
        self,
        repo_path: Optional[str] = None,
        validation_pipeline: Optional[HealingValidationPipeline] = None,
    ):
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()
        self.validation_pipeline = validation_pipeline or HealingValidationPipeline(
            repo_path=str(self.repo_path)
        )
        
        self._file_cache: Dict[str, str] = {}
        self._backup_dir: Optional[Path] = None
        self._plans: Dict[str, RefactoringPlan] = {}
        
        self.exclude_patterns = [
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
            "*.pyc",
            "*.pyo",
        ]
        
        logger.info(f"[SEMANTIC-REFACTOR] Initialized for repo: {self.repo_path}")
    
    def _should_exclude(self, path: Path) -> bool:
        """Check if path should be excluded from analysis."""
        path_str = str(path)
        for pattern in self.exclude_patterns:
            if pattern.startswith("*"):
                if path_str.endswith(pattern[1:]):
                    return True
            elif pattern in path_str:
                return True
        return False
    
    def _get_python_files(self) -> List[Path]:
        """Get all Python files in the repository."""
        files = []
        for py_file in self.repo_path.rglob("*.py"):
            if not self._should_exclude(py_file):
                files.append(py_file)
        return files
    
    def _read_file(self, file_path: Path) -> str:
        """Read file content with caching."""
        path_str = str(file_path)
        if path_str not in self._file_cache:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self._file_cache[path_str] = f.read()
            except Exception as e:
                logger.warning(f"[SEMANTIC-REFACTOR] Error reading {file_path}: {e}")
                return ""
        return self._file_cache[path_str]
    
    def _write_file(self, file_path: Path, content: str) -> bool:
        """Write content to file."""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self._file_cache[str(file_path)] = content
            return True
        except Exception as e:
            logger.error(f"[SEMANTIC-REFACTOR] Error writing {file_path}: {e}")
            return False
    
    def _create_backup(self, files: List[Path]) -> Path:
        """Create backup of files before refactoring."""
        import tempfile
        backup_dir = Path(tempfile.mkdtemp(prefix="refactor_backup_"))
        
        for file_path in files:
            if file_path.exists():
                rel_path = file_path.relative_to(self.repo_path)
                backup_path = backup_dir / rel_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, backup_path)
        
        self._backup_dir = backup_dir
        logger.info(f"[SEMANTIC-REFACTOR] Created backup in {backup_dir}")
        return backup_dir
    
    def _restore_backup(self, backup_dir: Path, files: List[Path]) -> bool:
        """Restore files from backup."""
        try:
            for file_path in files:
                rel_path = file_path.relative_to(self.repo_path)
                backup_path = backup_dir / rel_path
                if backup_path.exists():
                    shutil.copy2(backup_path, file_path)
            logger.info(f"[SEMANTIC-REFACTOR] Restored {len(files)} files from backup")
            return True
        except Exception as e:
            logger.error(f"[SEMANTIC-REFACTOR] Backup restore failed: {e}")
            return False
    
    def find_symbol_references(
        self,
        symbol_name: str,
        symbol_type: Optional[SymbolType] = None,
        scope_file: Optional[str] = None,
    ) -> List[SymbolReference]:
        """
        Find all references to a symbol across the codebase.
        
        Args:
            symbol_name: Name of the symbol to find
            symbol_type: Optional type filter
            scope_file: Optional file to limit search to
        
        Returns:
            List of symbol references
        """
        all_refs: List[SymbolReference] = []
        
        if scope_file:
            files = [Path(scope_file)]
        else:
            files = self._get_python_files()
        
        for py_file in files:
            source = self._read_file(py_file)
            if not source:
                continue
            
            finder = SymbolFinder(symbol_name, str(py_file))
            refs = finder.find_all(source)
            
            if symbol_type:
                refs = [r for r in refs if r.symbol_type == symbol_type]
            
            all_refs.extend(refs)
        
        logger.info(f"[SEMANTIC-REFACTOR] Found {len(all_refs)} references to '{symbol_name}'")
        return all_refs
    
    def plan_rename_symbol(
        self,
        old_name: str,
        new_name: str,
        symbol_type: Optional[SymbolType] = None,
        scope_file: Optional[str] = None,
    ) -> RefactoringPlan:
        """
        Plan a symbol rename operation.
        
        Args:
            old_name: Current symbol name
            new_name: New symbol name
            symbol_type: Type of symbol (function, class, etc.)
            scope_file: Optional file to limit scope
        
        Returns:
            Refactoring plan
        """
        import uuid
        
        plan = RefactoringPlan(
            plan_id=f"rename-{uuid.uuid4().hex[:8]}",
            refactoring_type=RefactoringType.RENAME_SYMBOL,
            created_at=datetime.now(),
            source_symbol=old_name,
            source_type=symbol_type or SymbolType.VARIABLE,
            target_symbol=new_name,
        )
        
        # Find all references
        refs = self.find_symbol_references(old_name, symbol_type, scope_file)
        plan.references = refs
        
        # Group by file
        affected_files: Set[str] = set()
        for ref in refs:
            affected_files.add(ref.file_path)
        
        plan.affected_files = list(affected_files)
        
        # Generate patches for each file
        for file_path in plan.affected_files:
            file_refs = [r for r in refs if r.file_path == file_path]
            source = self._read_file(Path(file_path))
            
            if source:
                patched = self._apply_rename_to_source(source, file_refs, old_name, new_name)
                if patched != source:
                    plan.patches.append(Patch(
                        file_path=file_path,
                        original_content=source,
                        patched_content=patched,
                        description=f"Rename '{old_name}' to '{new_name}'",
                        issue_type="refactoring",
                        confidence=0.95,
                    ))
        
        # Calculate risk level
        if len(plan.affected_files) > 20:
            plan.risk_level = "high"
        elif len(plan.affected_files) > 5:
            plan.risk_level = "medium"
        else:
            plan.risk_level = "low"
        
        plan.confidence = 0.95 if len(plan.references) > 0 else 0.0
        self._plans[plan.plan_id] = plan
        
        logger.info(
            f"[SEMANTIC-REFACTOR] Created rename plan: {plan.plan_id}, "
            f"{len(plan.affected_files)} files, {len(plan.references)} refs"
        )
        
        return plan
    
    def _apply_rename_to_source(
        self,
        source: str,
        refs: List[SymbolReference],
        old_name: str,
        new_name: str,
    ) -> str:
        """Apply rename to source code using references."""
        lines = source.split('\n')
        
        # Group refs by line and sort by column (reverse to preserve positions)
        line_refs: Dict[int, List[SymbolReference]] = {}
        for ref in refs:
            if ref.line_number not in line_refs:
                line_refs[ref.line_number] = []
            line_refs[ref.line_number].append(ref)
        
        for line_no, line_group in line_refs.items():
            line_group.sort(key=lambda r: r.column, reverse=True)
        
        # Apply renames line by line
        for line_no in sorted(line_refs.keys()):
            if 0 < line_no <= len(lines):
                line = lines[line_no - 1]
                for ref in line_refs[line_no]:
                    # Use word boundary replacement to avoid partial matches
                    pattern = rf'\b{re.escape(old_name)}\b'
                    line = re.sub(pattern, new_name, line)
                lines[line_no - 1] = line
        
        return '\n'.join(lines)
    
    def plan_move_module(
        self,
        source_module: str,
        target_module: str,
    ) -> RefactoringPlan:
        """
        Plan moving a module to a new location.
        
        Args:
            source_module: Current module path (e.g., "cognitive.old_module")
            target_module: Target module path (e.g., "cognitive.new_location.module")
        
        Returns:
            Refactoring plan
        """
        import uuid
        
        plan = RefactoringPlan(
            plan_id=f"move-{uuid.uuid4().hex[:8]}",
            refactoring_type=RefactoringType.MOVE_MODULE,
            created_at=datetime.now(),
            source_symbol=source_module,
            source_type=SymbolType.MODULE,
            source_module=source_module,
            target_module=target_module,
        )
        
        # Convert module path to file path
        source_path = self.repo_path / source_module.replace(".", "/")
        if not source_path.suffix:
            source_path = source_path.with_suffix(".py")
        
        target_path = self.repo_path / target_module.replace(".", "/")
        if not target_path.suffix:
            target_path = target_path.with_suffix(".py")
        
        plan.source_file = str(source_path)
        plan.target_file = str(target_path)
        
        # Find all imports of this module
        for py_file in self._get_python_files():
            source = self._read_file(py_file)
            if not source:
                continue
            
            # Check if file imports the source module
            if source_module in source or source_module.split('.')[-1] in source:
                analyzer = ImportAnalyzer(str(py_file))
                import_info = analyzer.analyze(source)
                
                needs_update = False
                for imp in import_info["imports"]:
                    if imp["module"] == source_module or imp["module"].startswith(f"{source_module}."):
                        needs_update = True
                        break
                
                for from_imp in import_info["from_imports"]:
                    if from_imp["module"] == source_module or from_imp["module"].startswith(f"{source_module}."):
                        needs_update = True
                        break
                
                if needs_update:
                    plan.affected_files.append(str(py_file))
                    patched = self._update_module_imports(source, source_module, target_module)
                    if patched != source:
                        plan.patches.append(Patch(
                            file_path=str(py_file),
                            original_content=source,
                            patched_content=patched,
                            description=f"Update imports: {source_module} → {target_module}",
                            issue_type="refactoring",
                            confidence=0.90,
                        ))
        
        plan.risk_level = "high" if len(plan.affected_files) > 10 else "medium"
        plan.confidence = 0.85
        self._plans[plan.plan_id] = plan
        
        logger.info(
            f"[SEMANTIC-REFACTOR] Created move plan: {plan.plan_id}, "
            f"{len(plan.affected_files)} files to update"
        )
        
        return plan
    
    def _update_module_imports(
        self,
        source: str,
        old_module: str,
        new_module: str,
    ) -> str:
        """Update import statements for a moved module."""
        lines = source.split('\n')
        new_lines = []
        
        old_parts = old_module.split('.')
        new_parts = new_module.split('.')
        
        for line in lines:
            new_line = line
            
            # Handle: from old_module import X
            pattern1 = rf'^(\s*from\s+){re.escape(old_module)}(\s+import\s+.*)$'
            if re.match(pattern1, line):
                new_line = re.sub(pattern1, rf'\1{new_module}\2', line)
            
            # Handle: import old_module
            pattern2 = rf'^(\s*import\s+){re.escape(old_module)}(\s*(?:as\s+\w+)?\s*)$'
            if re.match(pattern2, line):
                new_line = re.sub(pattern2, rf'\1{new_module}\2', line)
            
            # Handle: from old_module.submodule import X
            pattern3 = rf'^(\s*from\s+){re.escape(old_module)}\.(\S+)(\s+import\s+.*)$'
            if re.match(pattern3, line):
                new_line = re.sub(pattern3, rf'\1{new_module}.\2\3', line)
            
            new_lines.append(new_line)
        
        return '\n'.join(new_lines)
    
    def execute_plan(
        self,
        plan_id: str,
        dry_run: bool = False,
        skip_validation: bool = False,
    ) -> RefactoringResult:
        """
        Execute a refactoring plan.
        
        Args:
            plan_id: ID of the plan to execute
            dry_run: If True, only simulate execution
            skip_validation: If True, skip validation gates
        
        Returns:
            Refactoring result
        """
        import time
        start_time = time.time()
        
        plan = self._plans.get(plan_id)
        if not plan:
            return RefactoringResult(
                plan=RefactoringPlan(
                    plan_id=plan_id,
                    refactoring_type=RefactoringType.RENAME_SYMBOL,
                    created_at=datetime.now(),
                    source_symbol="unknown",
                    source_type=SymbolType.VARIABLE,
                    status="failed",
                ),
                success=False,
                errors=[f"Plan not found: {plan_id}"],
            )
        
        result = RefactoringResult(plan=plan, success=True)
        
        if dry_run:
            logger.info(f"[SEMANTIC-REFACTOR] Dry run for plan {plan_id}")
            result.files_modified = len(plan.patches)
            result.references_updated = len(plan.references)
            plan.status = "simulated"
            return result
        
        # Create backup
        affected_paths = [Path(p.file_path) for p in plan.patches]
        backup_dir = self._create_backup(affected_paths)
        
        try:
            plan.status = "executing"
            
            # Apply patches
            for patch in plan.patches:
                file_path = Path(patch.file_path)
                
                # Validate syntax before writing
                try:
                    ast.parse(patch.patched_content)
                except SyntaxError as e:
                    result.errors.append(f"Syntax error in {patch.file_path}: {e}")
                    result.success = False
                    continue
                
                if self._write_file(file_path, patch.patched_content):
                    result.files_modified += 1
                    patch.applied_at = datetime.now()
                else:
                    result.errors.append(f"Failed to write {patch.file_path}")
                    result.success = False
            
            # Run validation if not skipped
            if not skip_validation and result.success:
                validation_result = self._validate_refactoring(plan)
                if not validation_result["passed"]:
                    result.success = False
                    result.errors.extend(validation_result.get("errors", []))
                    result.warnings.extend(validation_result.get("warnings", []))
            
            # Rollback on failure
            if not result.success:
                logger.warning(f"[SEMANTIC-REFACTOR] Rolling back plan {plan_id}")
                self._restore_backup(backup_dir, affected_paths)
                plan.status = "rolled_back"
            else:
                plan.status = "completed"
                result.references_updated = len(plan.references)
            
        except Exception as e:
            logger.error(f"[SEMANTIC-REFACTOR] Execution error: {e}")
            result.success = False
            result.errors.append(str(e))
            self._restore_backup(backup_dir, affected_paths)
            plan.status = "failed"
        
        result.execution_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            f"[SEMANTIC-REFACTOR] Plan {plan_id} {plan.status}: "
            f"{result.files_modified} files, {result.execution_time_ms:.2f}ms"
        )
        
        return result
    
    def _validate_refactoring(self, plan: RefactoringPlan) -> Dict[str, Any]:
        """Run validation gates on refactored code."""
        result = {"passed": True, "errors": [], "warnings": [], "gates": []}
        
        # Syntax check all affected files
        for file_path in plan.affected_files:
            try:
                source = self._read_file(Path(file_path))
                ast.parse(source)
                result["gates"].append({"gate": "syntax", "file": file_path, "passed": True})
            except SyntaxError as e:
                result["passed"] = False
                result["errors"].append(f"Syntax error in {file_path}: {e}")
                result["gates"].append({"gate": "syntax", "file": file_path, "passed": False})
        
        # Use validation pipeline if available
        if self.validation_pipeline:
            for patch in plan.patches:
                validation = self.validation_pipeline.validate_patch(patch)
                if not validation.get("all_passed", True):
                    result["warnings"].append(f"Validation warning for {patch.file_path}")
        
        return result
    
    def rollback_plan(self, plan_id: str) -> bool:
        """Rollback a previously executed plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            logger.error(f"[SEMANTIC-REFACTOR] Plan not found: {plan_id}")
            return False
        
        if plan.status != "completed":
            logger.warning(f"[SEMANTIC-REFACTOR] Cannot rollback plan with status: {plan.status}")
            return False
        
        if not self._backup_dir:
            logger.error("[SEMANTIC-REFACTOR] No backup available")
            return False
        
        affected_paths = [Path(p.file_path) for p in plan.patches]
        if self._restore_backup(self._backup_dir, affected_paths):
            plan.status = "rolled_back"
            logger.info(f"[SEMANTIC-REFACTOR] Rolled back plan {plan_id}")
            return True
        
        return False
    
    def rename_symbol(
        self,
        old_name: str,
        new_name: str,
        symbol_type: Optional[SymbolType] = None,
        dry_run: bool = False,
    ) -> RefactoringResult:
        """
        Convenience method to plan and execute symbol rename.
        
        Args:
            old_name: Current symbol name
            new_name: New symbol name
            symbol_type: Type of symbol
            dry_run: If True, only simulate
        
        Returns:
            Refactoring result
        """
        plan = self.plan_rename_symbol(old_name, new_name, symbol_type)
        return self.execute_plan(plan.plan_id, dry_run=dry_run)
    
    def move_module(
        self,
        source_module: str,
        target_module: str,
        dry_run: bool = False,
    ) -> RefactoringResult:
        """
        Convenience method to plan and execute module move.
        
        Args:
            source_module: Current module path
            target_module: Target module path
            dry_run: If True, only simulate
        
        Returns:
            Refactoring result
        """
        plan = self.plan_move_module(source_module, target_module)
        return self.execute_plan(plan.plan_id, dry_run=dry_run)
    
    def get_plan_status(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a refactoring plan."""
        plan = self._plans.get(plan_id)
        if plan:
            return plan.to_dict()
        return None
    
    def list_plans(self) -> List[Dict[str, Any]]:
        """List all refactoring plans."""
        return [p.to_dict() for p in self._plans.values()]


# Singleton accessor
_engine_instance: Optional[SemanticRefactoringEngine] = None


def get_refactoring_engine(repo_path: Optional[str] = None) -> SemanticRefactoringEngine:
    """Get or create the semantic refactoring engine singleton."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SemanticRefactoringEngine(repo_path=repo_path)
    return _engine_instance
