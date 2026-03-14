import pytest
from datetime import datetime, timezone
from pathlib import Path

from backend.cognitive.active_learning_system import GraceActiveLearningSystem, SkillLevel
from backend.cognitive.adaptive_test_generator import _extract_functions

def test_adaptive_test_generator_extraction():
    """Verify the AST extraction logic in Adaptive Test Generator works on its own source."""
    # Read the generator's own source to test extraction
    generator_path = Path("backend/cognitive/adaptive_test_generator.py")
    source = generator_path.read_text(encoding='utf-8')
    
    functions = _extract_functions(source)
    
    # _extract_functions explicitly ignores functions starting with _
    func_names = [f["name"] for f in functions]
    assert "generate_tests_for_module" in func_names
    assert "generate_tests_for_all_new" in func_names

def test_skill_level_logic():
    """Verify basic SkillLevel logic in ActiveLearningSystem."""
    skill = SkillLevel("python_testing")
    assert skill.current_level == SkillLevel.NOVICE
    assert skill.proficiency_score == 0.0

if __name__ == "__main__":
    pytest.main(['-v', __file__])
