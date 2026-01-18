import ast
import logging
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from models.genesis_key_models import GenesisKey, GenesisKeyType
logger = logging.getLogger(__name__)

class ChangeType(str, Enum):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Types of code changes."""
    FUNCTION_ADDED = "function_added"
    FUNCTION_MODIFIED = "function_modified"
    FUNCTION_DELETED = "function_deleted"
    CLASS_ADDED = "class_added"
    CLASS_MODIFIED = "class_modified"
    CLASS_DELETED = "class_deleted"
    IMPORT_ADDED = "import_added"
    IMPORT_REMOVED = "import_removed"
    CONFIG_CHANGE = "config_change"
    TEST_CHANGE = "test_change"
    DOCUMENTATION_CHANGE = "documentation_change"
    UNKNOWN = "unknown"


@dataclass
class CodeEntity:
    """Represents a code entity (function, class, etc.)."""
    name: str
    entity_type: str  # 'function', 'class', 'method'
    line_start: int
    line_end: int
    file_path: str
    parent_class: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)  # Functions/classes it calls
    dependents: List[str] = field(default_factory=list)  # Functions/classes that call it


@dataclass
class CodeChange:
    """Represents a semantic code change."""
    change_type: ChangeType
    entity: Optional[CodeEntity] = None
    file_path: str = ""
    line_numbers: Tuple[int, int] = (0, 0)
    before_code: Optional[str] = None
    after_code: Optional[str] = None
    affected_entities: List[str] = field(default_factory=list)  # Other entities affected
    risk_score: float = 0.0  # 0.0-1.0
    confidence: float = 0.0  # 0.0-1.0


@dataclass
class ChangeAnalysis:
    """Complete analysis of code changes."""
    genesis_key_id: str
    file_path: str
    changes: List[CodeChange] = field(default_factory=list)
    affected_files: List[str] = field(default_factory=list)
    affected_functions: List[str] = field(default_factory=list)
    affected_classes: List[str] = field(default_factory=list)
    affected_tests: List[str] = field(default_factory=list)
    imports_added: List[str] = field(default_factory=list)
    imports_removed: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    confidence: float = 0.0
    estimated_test_time: float = 0.0  # seconds
    suggested_tests: List[str] = field(default_factory=list)


class CodeChangeAnalyzer:
    """
    Analyzes code changes using AST parsing and Genesis Keys.
    
    Goes beyond file diffs to understand:
    - Semantic changes (what functions/classes changed)
    - Impact analysis (what other code is affected)
    - Test selection (which tests should run)
    - Risk assessment (how risky is this change)
    """

    def __init__(self, base_path: Optional[str] = None):
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.test_patterns = [
            r'test_.*\.py$',
            r'.*_test\.py$',
            r'.*test.*\.py$',
        ]

    def analyze_genesis_key(
        self,
        genesis_key: GenesisKey
    ) -> Optional[ChangeAnalysis]:
        """
        Analyze a Genesis Key representing a code change.
        
        Args:
            genesis_key: Genesis Key with CODE_CHANGE or FILE_OPERATION type
            
        Returns:
            ChangeAnalysis with complete semantic understanding
        """
        if genesis_key.key_type not in [
            GenesisKeyType.CODE_CHANGE,
            GenesisKeyType.FILE_OPERATION
        ]:
            logger.debug(f"Genesis Key {genesis_key.key_id} is not a code change")
            return None

        if not genesis_key.file_path:
            logger.warning(f"Genesis Key {genesis_key.key_id} has no file_path")
            return None

        file_path = genesis_key.file_path
        if not Path(file_path).is_absolute():
            file_path = str(self.base_path / file_path)

        try:
            # Parse before and after code
            code_before = genesis_key.code_before or ""
            code_after = genesis_key.code_after or ""

            # Analyze the changes
            changes = self._analyze_code_diff(code_before, code_after, file_path)
            
            # Build complete analysis
            analysis = ChangeAnalysis(
                genesis_key_id=genesis_key.key_id,
                file_path=genesis_key.file_path,
                changes=changes
            )

            # Extract entities from changes
            for change in changes:
                if change.entity:
                    if change.entity.entity_type == 'function':
                        analysis.affected_functions.append(change.entity.name)
                    elif change.entity.entity_type == 'class':
                        analysis.affected_classes.append(change.entity.name)

            # Find affected files and tests
            analysis.affected_files = self._find_affected_files(analysis)
            analysis.affected_tests = self._find_affected_tests(analysis)
            analysis.suggested_tests = self._suggest_tests(analysis)

            # Calculate risk and confidence
            analysis.risk_score = self._calculate_risk_score(analysis)
            analysis.confidence = self._calculate_confidence(analysis)
            analysis.estimated_test_time = self._estimate_test_time(analysis)

            logger.info(
                f"[CodeAnalyzer] Analyzed {genesis_key.key_id}: "
                f"{len(changes)} changes, {len(analysis.affected_tests)} tests, "
                f"risk={analysis.risk_score:.2f}"
            )

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing Genesis Key {genesis_key.key_id}: {e}")
            return None

    def _analyze_code_diff(
        self,
        code_before: str,
        code_after: str,
        file_path: str
    ) -> List[CodeChange]:
        """Analyze semantic differences between code before and after."""
        changes = []

        try:
            # Parse both versions
            tree_before = ast.parse(code_before) if code_before else None
            tree_after = ast.parse(code_after) if code_after else None

            # Extract entities from both versions
            entities_before = self._extract_entities(tree_before, file_path) if tree_before else {}
            entities_after = self._extract_entities(tree_after, file_path) if tree_after else {}

            # Find added entities
            for name, entity in entities_after.items():
                if name not in entities_before:
                    if entity.entity_type == 'function':
                        changes.append(CodeChange(
                            change_type=ChangeType.FUNCTION_ADDED,
                            entity=entity,
                            file_path=file_path,
                            line_numbers=(entity.line_start, entity.line_end),
                            after_code=code_after,
                            risk_score=0.3,  # New code is medium risk
                            confidence=0.8
                        ))
                    elif entity.entity_type == 'class':
                        changes.append(CodeChange(
                            change_type=ChangeType.CLASS_ADDED,
                            entity=entity,
                            file_path=file_path,
                            line_numbers=(entity.line_start, entity.line_end),
                            after_code=code_after,
                            risk_score=0.4,
                            confidence=0.8
                        ))

            # Find deleted entities
            for name, entity in entities_before.items():
                if name not in entities_after:
                    if entity.entity_type == 'function':
                        changes.append(CodeChange(
                            change_type=ChangeType.FUNCTION_DELETED,
                            entity=entity,
                            file_path=file_path,
                            line_numbers=(entity.line_start, entity.line_end),
                            before_code=code_before,
                            risk_score=0.6,  # Deletions are higher risk
                            confidence=0.9
                        ))
                    elif entity.entity_type == 'class':
                        changes.append(CodeChange(
                            change_type=ChangeType.CLASS_DELETED,
                            entity=entity,
                            file_path=file_path,
                            line_numbers=(entity.line_start, entity.line_end),
                            before_code=code_before,
                            risk_score=0.7,
                            confidence=0.9
                        ))

            # Find modified entities (simplified - compare signatures)
            for name, entity_after in entities_after.items():
                if name in entities_before:
                    entity_before = entities_before[name]
                    # Check if signature changed
                    if (entity_before.line_start != entity_after.line_start or
                        entity_before.line_end != entity_after.line_end):
                        if entity_after.entity_type == 'function':
                            changes.append(CodeChange(
                                change_type=ChangeType.FUNCTION_MODIFIED,
                                entity=entity_after,
                                file_path=file_path,
                                line_numbers=(entity_after.line_start, entity_after.line_end),
                                before_code=code_before,
                                after_code=code_after,
                                risk_score=0.5,
                                confidence=0.7
                            ))
                        elif entity_after.entity_type == 'class':
                            changes.append(CodeChange(
                                change_type=ChangeType.CLASS_MODIFIED,
                                entity=entity_after,
                                file_path=file_path,
                                line_numbers=(entity_after.line_start, entity_after.line_end),
                                before_code=code_before,
                                after_code=code_after,
                                risk_score=0.6,
                                confidence=0.7
                            ))

            # Analyze imports
            imports_before = self._extract_imports(tree_before) if tree_before else set()
            imports_after = self._extract_imports(tree_after) if tree_after else set()
            
            for imp in imports_after - imports_before:
                changes.append(CodeChange(
                    change_type=ChangeType.IMPORT_ADDED,
                    file_path=file_path,
                    imports_added=[imp],
                    risk_score=0.2,
                    confidence=0.9
                ))
            
            for imp in imports_before - imports_after:
                changes.append(CodeChange(
                    change_type=ChangeType.IMPORT_REMOVED,
                    file_path=file_path,
                    imports_removed=[imp],
                    risk_score=0.4,
                    confidence=0.9
                ))

        except SyntaxError as e:
            logger.warning(f"Could not parse code for {file_path}: {e}")
            # Fallback: treat as unknown change
            changes.append(CodeChange(
                change_type=ChangeType.UNKNOWN,
                file_path=file_path,
                risk_score=0.5,
                confidence=0.3
            ))
        except Exception as e:
            logger.error(f"Error analyzing code diff: {e}")
            changes.append(CodeChange(
                change_type=ChangeType.UNKNOWN,
                file_path=file_path,
                risk_score=0.5,
                confidence=0.1
            ))

        return changes

    def _extract_entities(
        self,
        tree: ast.AST,
        file_path: str
    ) -> Dict[str, CodeEntity]:
        """Extract functions and classes from AST."""
        entities = {}
        visitor = EntityExtractor(file_path)
        visitor.visit(tree)
        return visitor.entities

    def _extract_imports(self, tree: ast.AST) -> Set[str]:
        """Extract import statements from AST."""
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module)
        return imports

    def _find_affected_files(self, analysis: ChangeAnalysis) -> List[str]:
        """Find files that might be affected by these changes."""
        affected = set()
        
        # Start with the changed file
        affected.add(analysis.file_path)
        
        # Find files that import from the changed file
        # (Simplified - in production, would do proper import analysis)
        changed_module = Path(analysis.file_path).stem
        
        # Search for files that might import this module
        for py_file in self.base_path.rglob("*.py"):
            if py_file == Path(analysis.file_path):
                continue
            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                # Simple check for imports
                if f"from {changed_module}" in content or f"import {changed_module}" in content:
                    affected.add(str(py_file.relative_to(self.base_path)))
            except Exception:
                pass
        
        return sorted(affected)

    def _find_affected_tests(self, analysis: ChangeAnalysis) -> List[str]:
        """Find test files that should run for these changes."""
        tests = []
        
        # Find test files matching the changed file
        changed_file = Path(analysis.file_path)
        test_name_patterns = [
            f"test_{changed_file.stem}.py",
            f"test_{changed_file.name}",
            f"{changed_file.stem}_test.py",
        ]
        
        # Search for test files
        for test_file in self.base_path.rglob("test_*.py"):
            test_path = str(test_file.relative_to(self.base_path))
            
            # Check if test file matches patterns
            matches = any(
                pattern in test_path or test_file.name == pattern
                for pattern in test_name_patterns
            )
            
            # Also check if test file imports the changed module
            if not matches:
                try:
                    content = test_file.read_text(encoding='utf-8', errors='ignore')
                    changed_module = changed_file.stem
                    if f"from {changed_module}" in content or f"import {changed_module}" in content:
                        matches = True
                except Exception:
                    pass
            
            if matches:
                tests.append(test_path)
        
        return tests

    def _suggest_tests(self, analysis: ChangeAnalysis) -> List[str]:
        """Suggest which specific tests should run."""
        suggestions = []
        
        # For each affected function/class, find tests
        for func_name in analysis.affected_functions:
            # Look for test functions matching the function name
            for test_file in self.base_path.rglob("test_*.py"):
                try:
                    content = test_file.read_text(encoding='utf-8', errors='ignore')
                    # Look for test functions that test this function
                    if f"test_{func_name}" in content or f"def test_{func_name}" in content:
                        test_path = str(test_file.relative_to(self.base_path))
                        if test_path not in suggestions:
                            suggestions.append(test_path)
                except Exception:
                    pass
        
        return suggestions

    def _calculate_risk_score(self, analysis: ChangeAnalysis) -> float:
        """Calculate overall risk score for the changes."""
        if not analysis.changes:
            return 0.0
        
        # Average risk scores from individual changes
        total_risk = sum(change.risk_score for change in analysis.changes)
        avg_risk = total_risk / len(analysis.changes)
        
        # Adjust based on number of affected files
        if len(analysis.affected_files) > 5:
            avg_risk = min(1.0, avg_risk * 1.2)
        
        # Adjust based on deletions (higher risk)
        has_deletions = any(
            c.change_type in [ChangeType.FUNCTION_DELETED, ChangeType.CLASS_DELETED]
            for c in analysis.changes
        )
        if has_deletions:
            avg_risk = min(1.0, avg_risk * 1.3)
        
        return min(1.0, avg_risk)

    def _calculate_confidence(self, analysis: ChangeAnalysis) -> float:
        """Calculate confidence in the analysis."""
        if not analysis.changes:
            return 0.0
        
        # Average confidence from individual changes
        total_conf = sum(change.confidence for change in analysis.changes)
        return total_conf / len(analysis.changes)

    def _estimate_test_time(self, analysis: ChangeAnalysis) -> float:
        """Estimate time to run affected tests (in seconds)."""
        # Rough estimate: 2 seconds per test file
        return len(analysis.affected_tests) * 2.0


class EntityExtractor(ast.NodeVisitor):
    """AST visitor to extract functions and classes."""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.entities: Dict[str, CodeEntity] = {}
        self.current_class: Optional[str] = None
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Extract function definition."""
        entity = CodeEntity(
            name=node.name,
            entity_type='method' if self.current_class else 'function',
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            file_path=self.file_path,
            parent_class=self.current_class
        )
        
        # Extract dependencies (function calls)
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    entity.dependencies.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    entity.dependencies.append(child.func.attr)
        
        key = f"{self.current_class}.{node.name}" if self.current_class else node.name
        self.entities[key] = entity
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Extract class definition."""
        old_class = self.current_class
        self.current_class = node.name
        
        entity = CodeEntity(
            name=node.name,
            entity_type='class',
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            file_path=self.file_path
        )
        
        self.entities[node.name] = entity
        self.generic_visit(node)
        
        self.current_class = old_class


# Global instance
_analyzer: Optional[CodeChangeAnalyzer] = None


def get_code_change_analyzer(base_path: Optional[str] = None) -> CodeChangeAnalyzer:
    """Get or create global code change analyzer instance."""
    global _analyzer
    if _analyzer is None or base_path is not None:
        _analyzer = CodeChangeAnalyzer(base_path=base_path)
    return _analyzer
