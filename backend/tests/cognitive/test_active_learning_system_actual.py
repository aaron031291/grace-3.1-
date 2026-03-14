import pytest
from backend.cognitive.active_learning_system import GraceActiveLearningSystem, SkillLevel
from pathlib import Path

class DummySession:
    pass

class DummyRetriever:
    pass

def test_active_learning_system_curriculum():
    sys = GraceActiveLearningSystem(session=DummySession(), retriever=DummyRetriever(), knowledge_base_path=Path("/tmp"))
    
    curr = sys.create_training_curriculum("Python programming")
    assert curr["skill_name"] == "Python programming"
    assert curr["target_proficiency"] == SkillLevel.INTERMEDIATE
    assert len(curr["study_phases"]) > 0
    assert len(curr["practice_tasks"]) > 0

def test_active_learning_system_assessment():
    sys = GraceActiveLearningSystem(session=DummySession(), retriever=DummyRetriever(), knowledge_base_path=Path("/tmp"))
    
    # Not started
    res1 = sys.get_skill_assessment("Rust programming")
    assert res1["level"] == SkillLevel.NOVICE
    assert res1["status"] == "not_started"
    
    # Started
    # Wait, the method checks `if skill_name not in self.skill_levels:`
    sys.skill_levels["Rust programming"] = SkillLevel(
        skill_name="Rust programming",
        current_level=SkillLevel.BEGINNER,
        proficiency_score=1.2,
        practice_hours=10.0,
        success_rate=0.8,
        tasks_completed=5
    )
    
    res2 = sys.get_skill_assessment("Rust programming")
    assert res2["level"] == SkillLevel.BEGINNER
    assert res2["proficiency_score"] == 1.2
    assert "status" not in res2 or res2.get("status") == "in_progress"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
