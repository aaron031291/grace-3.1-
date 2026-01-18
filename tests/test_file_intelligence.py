"""
Tests for File Intelligence Agent

Tests:
1. _analyze_file_relationships()
2. Import extraction
3. Export extraction
4. Call relationship detection
5. Inheritance detection
"""

import pytest
import sys
import ast
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent))


# Sample Python code for testing
SAMPLE_CODE_SIMPLE = '''
import os
import json
from pathlib import Path
from typing import Dict, List, Optional

def hello_world():
    """Say hello."""
    return "Hello, World!"

def add_numbers(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

class Calculator:
    """A simple calculator."""
    
    def __init__(self):
        self.result = 0
    
    def add(self, x, y):
        return x + y
'''

SAMPLE_CODE_WITH_INHERITANCE = '''
from abc import ABC, abstractmethod
from base_module import BaseClass

class Animal(ABC):
    """Abstract base animal."""
    
    @abstractmethod
    def speak(self):
        pass

class Dog(Animal):
    """A dog that barks."""
    
    def speak(self):
        return "Woof!"

class Cat(Animal):
    """A cat that meows."""
    
    def speak(self):
        return "Meow!"

class Labrador(Dog):
    """A Labrador retriever."""
    
    def fetch(self):
        return "Fetching!"
'''

SAMPLE_CODE_WITH_CALLS = '''
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def process_data(data):
    """Process some data."""
    logger.info("Processing data")
    result = transform(data)
    save_to_db(result)
    return result

def transform(data):
    """Transform data."""
    return data.upper()

def save_to_db(data):
    """Save to database."""
    timestamp = datetime.now()
    print(f"Saved at {timestamp}")
'''

SAMPLE_CODE_WITH_COMPLEX_IMPORTS = '''
import os
import sys
from typing import Dict, List, Optional, Any
from collections import defaultdict
from pathlib import Path

from mypackage.module1 import func1, func2
from mypackage.module2 import ClassA
from ..relative_module import relative_func
from . import local_module

def main():
    os.getcwd()
    sys.exit(0)
'''


class TestFileIntelligenceAgent:
    """Tests for FileIntelligenceAgent class."""
    
    @pytest.fixture
    def agent(self):
        """Create FileIntelligenceAgent with mocked dependencies."""
        from backend.file_manager.file_intelligence_agent import FileIntelligenceAgent
        
        mock_file_handler = Mock()
        mock_ollama_client = Mock()
        
        agent = FileIntelligenceAgent(
            file_handler=mock_file_handler,
            ollama_client=mock_ollama_client
        )
        return agent
    
    def test_init(self, agent):
        """Test agent initialization."""
        assert agent is not None
        assert agent.file_handler is not None
        assert agent.ollama_client is not None
    
    def test_init_without_dependencies(self):
        """Test agent initialization without dependencies."""
        from backend.file_manager.file_intelligence_agent import FileIntelligenceAgent
        
        agent = FileIntelligenceAgent()
        assert agent.file_handler is None
        assert agent.ollama_client is None


class TestAnalyzeFileRelationships:
    """Tests for _analyze_file_relationships() method."""
    
    @pytest.fixture
    def agent(self):
        """Create FileIntelligenceAgent."""
        from backend.file_manager.file_intelligence_agent import FileIntelligenceAgent
        return FileIntelligenceAgent()
    
    def test_analyze_relationships_simple_code(self, agent):
        """Test relationship analysis with simple code."""
        relationships = agent._analyze_file_relationships(
            "test_file.py",
            SAMPLE_CODE_SIMPLE
        )
        
        assert isinstance(relationships, list)
        
        # Should have imports, exports, calls
        rel_types = {r["type"] for r in relationships}
        assert "imports" in rel_types or "exports" in rel_types
    
    def test_analyze_relationships_with_inheritance(self, agent):
        """Test relationship analysis with inheritance."""
        relationships = agent._analyze_file_relationships(
            "animals.py",
            SAMPLE_CODE_WITH_INHERITANCE
        )
        
        # Find inheritance relationships
        inheritance_rels = [r for r in relationships if r["type"] == "inheritance"]
        
        assert len(inheritance_rels) > 0
        
        # Check that Dog inherits from Animal
        dog_inheritance = next(
            (r for r in inheritance_rels if r["target"] == "Dog"),
            None
        )
        if dog_inheritance:
            assert "Animal" in dog_inheritance["details"]["parent_classes"]
    
    def test_analyze_relationships_with_calls(self, agent):
        """Test relationship analysis with function calls."""
        relationships = agent._analyze_file_relationships(
            "processor.py",
            SAMPLE_CODE_WITH_CALLS
        )
        
        # Find call relationships
        call_rels = [r for r in relationships if r["type"] == "calls"]
        
        # Should detect calls to logger.info, transform, save_to_db
        call_targets = {r["target"] for r in call_rels}
        
        # At least some calls should be detected
        assert len(call_rels) > 0
    
    def test_analyze_relationships_invalid_syntax(self, agent):
        """Test with invalid Python syntax."""
        invalid_code = "def broken(:\n    pass"
        
        relationships = agent._analyze_file_relationships(
            "broken.py",
            invalid_code
        )
        
        # Should return empty list on parse error
        assert relationships == []
    
    def test_analyze_relationships_empty_file(self, agent):
        """Test with empty file content."""
        relationships = agent._analyze_file_relationships(
            "empty.py",
            ""
        )
        
        assert relationships == []
    
    def test_analyze_relationships_non_python(self, agent):
        """Test with non-Python file extension."""
        relationships = agent._analyze_file_relationships(
            "readme.txt",
            "This is just text, not Python code."
        )
        
        # Should return empty list for non-.py files
        assert relationships == []


class TestImportExtraction:
    """Tests for _extract_imports() method."""
    
    @pytest.fixture
    def agent(self):
        """Create FileIntelligenceAgent."""
        from backend.file_manager.file_intelligence_agent import FileIntelligenceAgent
        return FileIntelligenceAgent()
    
    def test_extract_simple_imports(self, agent):
        """Test extraction of simple imports."""
        tree = ast.parse(SAMPLE_CODE_SIMPLE)
        
        imports = agent._extract_imports("test.py", tree)
        
        # Should have import os, import json
        import_targets = {r["target"] for r in imports}
        assert "os" in import_targets
        assert "json" in import_targets
    
    def test_extract_from_imports(self, agent):
        """Test extraction of 'from X import Y' statements."""
        tree = ast.parse(SAMPLE_CODE_SIMPLE)
        
        imports = agent._extract_imports("test.py", tree)
        
        # Should have from pathlib import Path
        pathlib_import = next(
            (r for r in imports if r["target"] == "pathlib"),
            None
        )
        assert pathlib_import is not None
        assert "Path" in pathlib_import["details"]["imported_names"]
    
    def test_extract_complex_imports(self, agent):
        """Test extraction of complex import patterns."""
        tree = ast.parse(SAMPLE_CODE_WITH_COMPLEX_IMPORTS)
        
        imports = agent._extract_imports("complex.py", tree)
        
        # Check for various import types
        import_targets = {r["target"] for r in imports}
        
        assert "os" in import_targets
        assert "sys" in import_targets
        assert "typing" in import_targets
    
    def test_extract_relative_imports(self, agent):
        """Test extraction of relative imports."""
        tree = ast.parse(SAMPLE_CODE_WITH_COMPLEX_IMPORTS)
        
        imports = agent._extract_imports("complex.py", tree)
        
        # Find relative imports (level > 0)
        relative_imports = [
            r for r in imports 
            if r["details"].get("level", 0) > 0
        ]
        
        # Should have at least one relative import
        assert len(relative_imports) >= 1
    
    def test_extract_import_line_numbers(self, agent):
        """Test that line numbers are captured."""
        tree = ast.parse(SAMPLE_CODE_SIMPLE)
        
        imports = agent._extract_imports("test.py", tree)
        
        for imp in imports:
            assert "line" in imp["details"]
            assert imp["details"]["line"] > 0


class TestExportExtraction:
    """Tests for _extract_exports() method."""
    
    @pytest.fixture
    def agent(self):
        """Create FileIntelligenceAgent."""
        from backend.file_manager.file_intelligence_agent import FileIntelligenceAgent
        return FileIntelligenceAgent()
    
    def test_extract_function_exports(self, agent):
        """Test extraction of exported functions."""
        tree = ast.parse(SAMPLE_CODE_SIMPLE)
        
        exports = agent._extract_exports("test.py", tree)
        
        # Should have hello_world and add_numbers
        export_names = {r["target"] for r in exports}
        assert "hello_world" in export_names
        assert "add_numbers" in export_names
    
    def test_extract_class_exports(self, agent):
        """Test extraction of exported classes."""
        tree = ast.parse(SAMPLE_CODE_SIMPLE)
        
        exports = agent._extract_exports("test.py", tree)
        
        # Should have Calculator class
        class_exports = [e for e in exports if e["details"]["kind"] == "class"]
        class_names = {e["target"] for e in class_exports}
        assert "Calculator" in class_names
    
    def test_extract_class_methods(self, agent):
        """Test that class methods are captured in export details."""
        tree = ast.parse(SAMPLE_CODE_SIMPLE)
        
        exports = agent._extract_exports("test.py", tree)
        
        # Find Calculator export
        calc_export = next(
            (e for e in exports if e["target"] == "Calculator"),
            None
        )
        
        assert calc_export is not None
        assert "methods" in calc_export["details"]
        assert "__init__" in calc_export["details"]["methods"]
        assert "add" in calc_export["details"]["methods"]
    
    def test_extract_private_functions(self, agent):
        """Test that private functions are marked."""
        code = '''
def public_func():
    pass

def _private_func():
    pass

def __dunder_func__():
    pass
'''
        tree = ast.parse(code)
        exports = agent._extract_exports("test.py", tree)
        
        # Find private function
        private_export = next(
            (e for e in exports if e["target"] == "_private_func"),
            None
        )
        
        if private_export:
            assert private_export["details"]["is_private"] is True
    
    def test_extract_async_functions(self, agent):
        """Test extraction of async functions."""
        code = '''
async def async_handler():
    return await some_operation()

def sync_handler():
    return result
'''
        tree = ast.parse(code)
        exports = agent._extract_exports("test.py", tree)
        
        # Find async function
        async_export = next(
            (e for e in exports if e["target"] == "async_handler"),
            None
        )
        
        if async_export:
            assert async_export["details"]["is_async"] is True
    
    def test_extract_function_args(self, agent):
        """Test that function arguments are captured."""
        tree = ast.parse(SAMPLE_CODE_SIMPLE)
        
        exports = agent._extract_exports("test.py", tree)
        
        # Find add_numbers function
        add_export = next(
            (e for e in exports if e["target"] == "add_numbers"),
            None
        )
        
        assert add_export is not None
        assert "args" in add_export["details"]
        assert "a" in add_export["details"]["args"]
        assert "b" in add_export["details"]["args"]


class TestCallRelationshipDetection:
    """Tests for _extract_calls() method."""
    
    @pytest.fixture
    def agent(self):
        """Create FileIntelligenceAgent."""
        from backend.file_manager.file_intelligence_agent import FileIntelligenceAgent
        return FileIntelligenceAgent()
    
    def test_extract_simple_calls(self, agent):
        """Test extraction of simple function calls."""
        tree = ast.parse(SAMPLE_CODE_WITH_CALLS)
        
        calls = agent._extract_calls("processor.py", tree)
        
        # Should detect transform() and save_to_db() calls
        call_targets = {r["target"] for r in calls}
        assert "transform" in call_targets or any("transform" in str(c) for c in calls)
    
    def test_extract_method_calls(self, agent):
        """Test extraction of method calls."""
        tree = ast.parse(SAMPLE_CODE_WITH_CALLS)
        
        calls = agent._extract_calls("processor.py", tree)
        
        # Should detect logger.info call
        method_calls = [c for c in calls if c["details"].get("is_method")]
        assert len(method_calls) > 0
    
    def test_extract_chained_calls(self, agent):
        """Test extraction of chained method calls."""
        code = '''
def process():
    result = data.strip().lower().split()
    obj.method1().method2().method3()
'''
        tree = ast.parse(code)
        calls = agent._extract_calls("chained.py", tree)
        
        # Should detect some calls
        assert len(calls) > 0
    
    def test_extract_builtin_calls(self, agent):
        """Test extraction of builtin function calls."""
        code = '''
def example():
    items = list(range(10))
    length = len(items)
    text = str(123)
    print(text)
'''
        tree = ast.parse(code)
        calls = agent._extract_calls("builtins.py", tree)
        
        call_targets = {c["target"] for c in calls}
        
        # Should detect builtin calls
        assert "list" in call_targets or "len" in call_targets or "print" in call_targets
    
    def test_extract_call_line_numbers(self, agent):
        """Test that call line numbers are captured."""
        tree = ast.parse(SAMPLE_CODE_WITH_CALLS)
        
        calls = agent._extract_calls("processor.py", tree)
        
        for call in calls:
            assert "line" in call["details"]
            assert call["details"]["line"] > 0
    
    def test_no_duplicate_calls(self, agent):
        """Test that duplicate calls are not recorded multiple times."""
        code = '''
def example():
    print("hello")
    print("world")
    print("test")
'''
        tree = ast.parse(code)
        calls = agent._extract_calls("example.py", tree)
        
        # print should appear only once (deduplication)
        print_calls = [c for c in calls if c["target"] == "print"]
        assert len(print_calls) <= 1


class TestInheritanceDetection:
    """Tests for _extract_inheritance() method."""
    
    @pytest.fixture
    def agent(self):
        """Create FileIntelligenceAgent."""
        from backend.file_manager.file_intelligence_agent import FileIntelligenceAgent
        return FileIntelligenceAgent()
    
    def test_extract_single_inheritance(self, agent):
        """Test extraction of single inheritance."""
        tree = ast.parse(SAMPLE_CODE_WITH_INHERITANCE)
        
        inheritance = agent._extract_inheritance("animals.py", tree)
        
        # Should detect Dog(Animal)
        dog_inheritance = next(
            (i for i in inheritance if i["target"] == "Dog"),
            None
        )
        
        assert dog_inheritance is not None
        assert "Animal" in dog_inheritance["details"]["parent_classes"]
    
    def test_extract_multiple_inheritance(self, agent):
        """Test extraction of multiple inheritance."""
        code = '''
class A:
    pass

class B:
    pass

class C(A, B):
    pass
'''
        tree = ast.parse(code)
        inheritance = agent._extract_inheritance("multi.py", tree)
        
        # Find C's inheritance
        c_inheritance = next(
            (i for i in inheritance if i["target"] == "C"),
            None
        )
        
        assert c_inheritance is not None
        assert "A" in c_inheritance["details"]["parent_classes"]
        assert "B" in c_inheritance["details"]["parent_classes"]
    
    def test_extract_module_inheritance(self, agent):
        """Test extraction of inheritance from module classes."""
        code = '''
from abc import ABC
import base_module

class MyClass(ABC):
    pass

class OtherClass(base_module.BaseClass):
    pass
'''
        tree = ast.parse(code)
        inheritance = agent._extract_inheritance("module_inherit.py", tree)
        
        # Should detect both inheritances
        assert len(inheritance) >= 2
        
        # Find ABC inheritance
        abc_inheritance = next(
            (i for i in inheritance if i["target"] == "MyClass"),
            None
        )
        assert abc_inheritance is not None
        assert "ABC" in abc_inheritance["details"]["parent_classes"]
    
    def test_extract_chained_inheritance(self, agent):
        """Test extraction with inheritance chains."""
        tree = ast.parse(SAMPLE_CODE_WITH_INHERITANCE)
        
        inheritance = agent._extract_inheritance("animals.py", tree)
        
        # Should detect Labrador(Dog)
        labrador_inheritance = next(
            (i for i in inheritance if i["target"] == "Labrador"),
            None
        )
        
        assert labrador_inheritance is not None
        assert "Dog" in labrador_inheritance["details"]["parent_classes"]
    
    def test_no_inheritance_for_plain_classes(self, agent):
        """Test that classes without bases are not in inheritance list."""
        code = '''
class PlainClass:
    def method(self):
        pass
'''
        tree = ast.parse(code)
        inheritance = agent._extract_inheritance("plain.py", tree)
        
        # Should be empty - no inheritance
        assert len(inheritance) == 0
    
    def test_inheritance_line_numbers(self, agent):
        """Test that inheritance line numbers are captured."""
        tree = ast.parse(SAMPLE_CODE_WITH_INHERITANCE)
        
        inheritance = agent._extract_inheritance("animals.py", tree)
        
        for inh in inheritance:
            assert "line" in inh["details"]
            assert inh["details"]["line"] > 0


class TestFileIntelligenceDeepAnalysis:
    """Tests for analyze_file_deeply() method."""
    
    @pytest.fixture
    def agent(self):
        """Create FileIntelligenceAgent with mocked LLM."""
        from backend.file_manager.file_intelligence_agent import FileIntelligenceAgent
        
        mock_ollama = Mock()
        mock_ollama.generate = Mock(return_value={
            "response": "This is a test summary of the content."
        })
        
        return FileIntelligenceAgent(ollama_client=mock_ollama)
    
    def test_analyze_file_deeply_returns_intelligence(self, agent, tmp_path):
        """Test that deep analysis returns FileIntelligence."""
        # Create temp file
        test_file = tmp_path / "test_module.py"
        test_file.write_text(SAMPLE_CODE_SIMPLE)
        
        result = agent.analyze_file_deeply(str(test_file))
        
        from backend.file_manager.file_intelligence_agent import FileIntelligence
        assert isinstance(result, FileIntelligence)
    
    def test_analyze_file_deeply_with_content(self, agent):
        """Test deep analysis with pre-provided content."""
        result = agent.analyze_file_deeply(
            "virtual_file.py",
            content=SAMPLE_CODE_SIMPLE
        )
        
        assert result.content_summary is not None
        assert result.metadata is not None
    
    def test_analyze_file_deeply_metadata(self, agent):
        """Test that metadata is populated."""
        result = agent.analyze_file_deeply(
            "test.py",
            content=SAMPLE_CODE_SIMPLE
        )
        
        assert "file_size" in result.metadata
        assert "line_count" in result.metadata
        assert "word_count" in result.metadata
        assert "analyzed_at" in result.metadata
    
    def test_analyze_file_deeply_relationships(self, agent):
        """Test that relationships are extracted."""
        result = agent.analyze_file_deeply(
            "test.py",
            content=SAMPLE_CODE_SIMPLE
        )
        
        assert isinstance(result.relationships, list)
    
    def test_analyze_file_deeply_error_handling(self, agent):
        """Test error handling for non-existent file."""
        result = agent.analyze_file_deeply("/nonexistent/path/file.py")
        
        # Should return minimal intelligence with error
        assert result.content_summary == "Analysis failed" or "error" in result.metadata
