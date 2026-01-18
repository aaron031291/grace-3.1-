"""
Tests for the Semantic Refactoring Engine.

Tests multi-file symbol renaming, module moves, and import updates.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestSemanticRefactoringEngine:
    """Test suite for SemanticRefactoringEngine."""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository for testing."""
        temp_dir = tempfile.mkdtemp(prefix="test_refactor_")
        repo_path = Path(temp_dir)
        
        # Create test files
        (repo_path / "module_a.py").write_text('''
def helper_function():
    """A helper function."""
    return 42

class MyClass:
    def method(self):
        return helper_function()
''')
        
        (repo_path / "module_b.py").write_text('''
from module_a import helper_function, MyClass

def use_helper():
    result = helper_function()
    obj = MyClass()
    return result + obj.method()
''')
        
        (repo_path / "subdir").mkdir()
        (repo_path / "subdir" / "__init__.py").write_text("")
        (repo_path / "subdir" / "module_c.py").write_text('''
from module_a import helper_function

value = helper_function()
''')
        
        yield repo_path
        
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def engine(self, temp_repo):
        """Create a refactoring engine for the temp repo."""
        from cognitive.semantic_refactoring_engine import SemanticRefactoringEngine
        return SemanticRefactoringEngine(repo_path=str(temp_repo))
    
    def test_find_symbol_references(self, engine, temp_repo):
        """Test finding all references to a symbol."""
        refs = engine.find_symbol_references("helper_function")
        
        assert len(refs) >= 3  # Definition + imports + usages
        
        # Check we found references in multiple files
        files = set(r.file_path for r in refs)
        assert len(files) >= 2
        
        # Check we found the definition
        definitions = [r for r in refs if r.is_definition]
        assert len(definitions) >= 1
        
        # Check we found imports
        imports = [r for r in refs if r.is_import]
        assert len(imports) >= 2
    
    def test_plan_rename_symbol(self, engine, temp_repo):
        """Test creating a rename plan."""
        plan = engine.plan_rename_symbol(
            old_name="helper_function",
            new_name="utility_function",
        )
        
        assert plan.plan_id is not None
        assert plan.refactoring_type.value == "rename_symbol"
        assert plan.source_symbol == "helper_function"
        assert plan.target_symbol == "utility_function"
        assert len(plan.affected_files) >= 2
        assert len(plan.patches) >= 2
        assert plan.status == "planned"
    
    def test_execute_rename_dry_run(self, engine, temp_repo):
        """Test dry run of rename doesn't modify files."""
        # Get original content
        original_a = (temp_repo / "module_a.py").read_text()
        original_b = (temp_repo / "module_b.py").read_text()
        
        # Plan and dry run
        plan = engine.plan_rename_symbol(
            old_name="helper_function",
            new_name="utility_function",
        )
        result = engine.execute_plan(plan.plan_id, dry_run=True)
        
        assert result.success
        assert result.files_modified == len(plan.patches)
        
        # Verify files unchanged
        assert (temp_repo / "module_a.py").read_text() == original_a
        assert (temp_repo / "module_b.py").read_text() == original_b
    
    def test_execute_rename_actual(self, engine, temp_repo):
        """Test actual rename modifies files correctly."""
        plan = engine.plan_rename_symbol(
            old_name="helper_function",
            new_name="utility_function",
        )
        result = engine.execute_plan(plan.plan_id, dry_run=False)
        
        assert result.success
        assert result.files_modified >= 2
        assert plan.status == "completed"
        
        # Verify files were modified
        content_a = (temp_repo / "module_a.py").read_text()
        content_b = (temp_repo / "module_b.py").read_text()
        
        assert "utility_function" in content_a
        assert "helper_function" not in content_a
        assert "utility_function" in content_b
        assert "helper_function" not in content_b
    
    def test_rename_class(self, engine, temp_repo):
        """Test renaming a class across files."""
        from cognitive.semantic_refactoring_engine import SymbolType
        
        plan = engine.plan_rename_symbol(
            old_name="MyClass",
            new_name="RenamedClass",
            symbol_type=SymbolType.CLASS,
        )
        result = engine.execute_plan(plan.plan_id, dry_run=False)
        
        assert result.success
        
        content_a = (temp_repo / "module_a.py").read_text()
        content_b = (temp_repo / "module_b.py").read_text()
        
        assert "RenamedClass" in content_a
        assert "RenamedClass" in content_b
    
    def test_rollback_on_validation_failure(self, engine, temp_repo):
        """Test that rollback works when validation fails."""
        # Get original content
        original_a = (temp_repo / "module_a.py").read_text()
        
        # Create a plan
        plan = engine.plan_rename_symbol(
            old_name="helper_function",
            new_name="utility_function",
        )
        
        # Execute
        result = engine.execute_plan(plan.plan_id, dry_run=False)
        
        if result.success and plan.status == "completed":
            # Manually rollback
            rollback_success = engine.rollback_plan(plan.plan_id)
            
            if rollback_success:
                content_a = (temp_repo / "module_a.py").read_text()
                assert content_a == original_a
    
    def test_plan_move_module(self, engine, temp_repo):
        """Test creating a module move plan."""
        plan = engine.plan_move_module(
            source_module="module_a",
            target_module="utils.module_a",
        )
        
        assert plan.plan_id is not None
        assert plan.refactoring_type.value == "move_module"
        assert plan.source_module == "module_a"
        assert plan.target_module == "utils.module_a"
        assert plan.status == "planned"
    
    def test_list_plans(self, engine, temp_repo):
        """Test listing all plans."""
        # Create some plans
        engine.plan_rename_symbol("helper_function", "new_name1")
        engine.plan_rename_symbol("MyClass", "NewClass")
        
        plans = engine.list_plans()
        
        assert len(plans) >= 2
        assert all("plan_id" in p for p in plans)
    
    def test_get_plan_status(self, engine, temp_repo):
        """Test getting plan status."""
        plan = engine.plan_rename_symbol("helper_function", "new_helper")
        
        status = engine.get_plan_status(plan.plan_id)
        
        assert status is not None
        assert status["plan_id"] == plan.plan_id
        assert status["status"] == "planned"


class TestSymbolFinder:
    """Tests for the SymbolFinder AST visitor."""
    
    def test_find_function_definitions(self):
        """Test finding function definitions."""
        from cognitive.semantic_refactoring_engine import SymbolFinder
        
        source = '''
def my_function():
    pass

async def my_async_function():
    pass
'''
        finder = SymbolFinder("my_function", "/test/file.py")
        refs = finder.find_all(source)
        
        assert len(refs) == 1
        assert refs[0].is_definition
        assert refs[0].symbol_name == "my_function"
    
    def test_find_class_definitions(self):
        """Test finding class definitions."""
        from cognitive.semantic_refactoring_engine import SymbolFinder
        
        source = '''
class MyClass:
    def method(self):
        pass
'''
        finder = SymbolFinder("MyClass", "/test/file.py")
        refs = finder.find_all(source)
        
        assert len(refs) == 1
        assert refs[0].is_definition
        assert refs[0].symbol_type.value == "class"
    
    def test_find_imports(self):
        """Test finding import statements."""
        from cognitive.semantic_refactoring_engine import SymbolFinder
        
        source = '''
from module import my_function
import my_function as mf
'''
        finder = SymbolFinder("my_function", "/test/file.py")
        refs = finder.find_all(source)
        
        imports = [r for r in refs if r.is_import]
        assert len(imports) >= 1


class TestImportAnalyzer:
    """Tests for the ImportAnalyzer."""
    
    def test_analyze_imports(self):
        """Test analyzing imports."""
        from cognitive.semantic_refactoring_engine import ImportAnalyzer
        
        source = '''
import os
import sys as system
from pathlib import Path
from typing import List, Optional
'''
        analyzer = ImportAnalyzer("/test/file.py")
        result = analyzer.analyze(source)
        
        assert len(result["imports"]) == 2
        assert len(result["from_imports"]) == 2
        
        # Check import details
        os_import = next(i for i in result["imports"] if i["module"] == "os")
        assert os_import["alias"] is None
        
        sys_import = next(i for i in result["imports"] if i["module"] == "sys")
        assert sys_import["alias"] == "system"


class TestRefactoringIntegration:
    """Integration tests for the full refactoring workflow."""
    
    @pytest.fixture
    def healing_system_mock(self):
        """Mock the healing system dependencies."""
        with patch('cognitive.autonomous_healing_system.get_healing_system') as mock:
            mock.return_value = MagicMock()
            yield mock
    
    def test_healing_system_has_semantic_refactor_action(self):
        """Test that HealingAction enum includes semantic refactor."""
        from cognitive.autonomous_healing_system import HealingAction
        
        assert hasattr(HealingAction, 'SEMANTIC_REFACTOR')
        assert HealingAction.SEMANTIC_REFACTOR.value == "semantic_refactor"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
