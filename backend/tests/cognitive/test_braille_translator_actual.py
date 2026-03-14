import pytest
import ast
from backend.cognitive.braille_mapper import BrailleMapper
from backend.cognitive.braille_translator import BrailleTranslator

def test_braille_mapper_loading():
    """Ensure the mapper can load correctly from the configuration file."""
    mapper = BrailleMapper()
    assert len(mapper.python_to_braille_map) > 0, "Failed to load braille mappings"
    
    # Test specific lookup
    def_entry = mapper.python_to_braille("def")
    assert def_entry is not None
    assert def_entry["keyword"] == "def"
    assert "●●●●●●" in def_entry["braille"]
    assert "GRACE-PY" in def_entry["genesis_key"]

def test_braille_translator():
    """Ensure the translator correctly converts raw python ASTs into Braille Encoded streams."""
    mapper = BrailleMapper()
    translator = BrailleTranslator(mapper=mapper)
    
    python_code = """
def compile_target(target_id):
    if target_id == 5:
        return True
    return False
"""
    braille_stream = translator.translate_code(python_code)
    
    # Check that core logic mappings were injected
    assert "●●●●●●" in braille_stream  # Verify some braille representation was output
    assert "compile_target" in braille_stream  # Verify identifiers passed through
    assert "target_id" in braille_stream  # Verify arguments passed through

if __name__ == "__main__":
    pytest.main(['-v', __file__])
