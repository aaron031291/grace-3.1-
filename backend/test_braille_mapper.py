import pytest
import os
import sys

# Add backend to path so we can resolve absolute imports like `backend.cognitive.braille_mapper`
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cognitive.braille_mapper import BrailleMapper

def test_braille_mapper_loads():
    mapper = BrailleMapper()
    assert len(mapper.python_to_braille_map) > 0, "Mapper should have loaded entries"
    
def test_valid_keyword():
    mapper = BrailleMapper()
    # Test a keyword
    def_mapping = mapper.python_to_braille("def")
    assert def_mapping is not None
    assert def_mapping["braille"] == "●●●●●● 1mm □"
    assert def_mapping["genesis_key"] == "GRACE-PY-001"
    
def test_braille_to_python():
    mapper = BrailleMapper()
    # Test braille to python
    python_mappings = mapper.braille_to_python("●●●●●● 1mm □")
    assert len(python_mappings) > 0
    # Check if 'def' is in the mapped keywords
    keywords = [m["keyword"] for m in python_mappings]
    assert "def" in keywords
    
def test_genesis_key_lookup():
    mapper = BrailleMapper()
    # Test genesis key lookup
    genesis_mapping = mapper.get_by_genesis_key("GRACE-PY-001")
    assert genesis_mapping is not None
    assert genesis_mapping["keyword"] == "def"

def test_invalid_keyword():
    mapper = BrailleMapper()
    assert mapper.python_to_braille("non_existent_keyword") is None
