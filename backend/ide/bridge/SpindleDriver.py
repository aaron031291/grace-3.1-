"""
Spindle Driver - The Core Compiler for Grace 3.1
Translates raw source code into Grace's internal Braille encoding,
and generates an ExecutableAST that is geometrically verifiable by Z3.
"""
import ast
from cognitive.braille_translator import BrailleTranslator
from cognitive.braille_mapper import mapper as default_mapper

class ExecutableAST:
    def __init__(self, braille_sequence: str, z3_metadata: dict):
        self.braille_sequence = braille_sequence
        self.z3_metadata = z3_metadata
        self.is_compiled = True
        self.type = "GEOMETRIC_NODE"

    def to_dict(self):
        return {
            "type": self.type,
            "braille": self.braille_sequence,
            "z3_metadata": self.z3_metadata,
            "is_compiled": self.is_compiled
        }


def compile_spindle(src: str) -> ExecutableAST:
    """
    SpindleDriver::compile
    Takes raw Python source code from the IDE Bridge.
    Returns: ExecutableAST for Geometric Verification.
    """
    try:
        # Validate syntax first
        tree = ast.parse(src)
        
        # Translate AST into Grace's Deterministic Braille Tokens
        translator = BrailleTranslator()
        braille_sequence = translator.translate_code(src)
        
        # Geometric Meta-graph for Z3
        z3_metadata = {
            "nodes_count": len(translator.output),
            "topology_hash": hash(braille_sequence),
            "entropy": "BOUNDED"
        }
        
        return ExecutableAST(braille_sequence=braille_sequence, z3_metadata=z3_metadata)
    except SyntaxError as e:
        return ExecutableAST("ERROR", {"type": "ERROR_NODE", "msg": str(e)})

