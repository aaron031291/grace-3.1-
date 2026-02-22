"""
Backward compatibility wrapper.
Real code moved to cognitive/grace_brain.py
"""
from cognitive.grace_brain import *

# Backward compatibility aliases
from cognitive.grace_brain import GraceBrain as KimiBrain
from cognitive.grace_brain import GraceBrain
from cognitive.grace_brain import get_kimi_brain, GraceDiagnosis as KimiDiagnosis
from cognitive.grace_brain import GraceInstructionSet as KimiInstructionSet
from cognitive.grace_brain import GraceInstruction as KimiInstruction

