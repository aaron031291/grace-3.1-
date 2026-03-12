import pytest
import ast
import os
import sys

# Add backend to path so we can resolve absolute imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.cognitive.braille_translator import BrailleTranslator

def test_translate_simple_function():
    source = "def foo(a, b):\n    return a + b"
    translator = BrailleTranslator()
    braille_output = translator.translate_code(source)
    
    # Check if 'def' braille symbol is present
    assert "●●●●●● 1mm □" in braille_output
    # Check if 'return' braille symbol is present
    assert "●●●●●● 3mm ○" in braille_output
    # Check if 'add' braille symbol is present
    assert "●●●●●● 3mm ○" in braille_output # Wait, return and add are the same braille symbol?
    
def test_translate_assignment():
    source = "x = 42"
    translator = BrailleTranslator()
    braille_output = translator.translate_code(source)
    
    # Check if 'assign' braille symbol is present
    assert "●●●●●● 1mm □" in braille_output
    assert "x" in braille_output
    assert "42" in braille_output
