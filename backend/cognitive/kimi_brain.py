"""
Backward compatibility wrapper.
Real code moved to cognitive/grace_brain.py

Classes:
- `InstructionType`
- `InstructionPriority`
- `KimiDiagnosis`
- `KimiInstruction`
- `KimiInstructionSet`
- `KimiBrain`

Key Methods:
- `connect_mirror()`
- `connect_diagnostics()`
- `connect_learning()`
- `connect_pattern_learner()`
- `read_system_state()`
- `diagnose()`
- `produce_instructions()`
- `get_status()`
- `get_kimi_brain()`
"""
from cognitive.grace_brain import *

# Backward compatibility aliases
from cognitive.grace_brain import GraceBrain as KimiBrain
from cognitive.grace_brain import GraceBrain
from cognitive.grace_brain import get_kimi_brain, GraceDiagnosis as KimiDiagnosis
from cognitive.grace_brain import GraceInstructionSet as KimiInstructionSet
from cognitive.grace_brain import GraceInstruction as KimiInstruction

