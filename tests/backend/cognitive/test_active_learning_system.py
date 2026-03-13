import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

import sys
# Pre-mock dependencies so the runner doesn't blow up on missing imports
sys.modules['embedding.embedder'] = MagicMock()
sys.modules['backend.embedding.embedder'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['llm_orchestrator'] = MagicMock()
sys.modules['huggingface_hub'] = MagicMock()

from backend.cognitive.active_learning_system import GraceActiveLearningSystem, SkillLevel

@pytest.fixture
def mock_session():
    session = MagicMock()
    # Mock query.filter.order_by.limit.all() chain for getting examples
    session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    # Mock query.filter.all() chain for related knowledge update
    session.query.return_value.filter.return_value.all.return_value = []
    # Mock query.filter.limit.all() for assess_consistency
    session.query.return_value.filter.return_value.limit.return_value.all.return_value = []
    return session

@pytest.fixture
def mock_retriever():
    retriever = MagicMock()
    # Return mocked chunks from AI research documents
    retriever.retrieve.return_value = [
        {
            "document_id": "doc_123",
            "metadata": {"source": "python_guide.pdf"},
            "text": "A python function is defined using def.",
            "score": 0.95
        },
        {
            "document_id": "doc_123",
            "metadata": {"source": "python_guide.pdf"},
            "text": "Functions can take arguments.",
            "score": 0.85
        }
    ]
    return retriever

def test_active_learning_system_study_topic(mock_session, mock_retriever):
    with patch('backend.cognitive.active_learning_system.PredictiveContextLoader') as mock_loader_cls:
        # Mock predictive loader
        mock_loader = MagicMock()
        mock_loader.process_query.return_value = {
            "ready_topics": ["decorators", "classes"],
            "statistics": {}
        }
        mock_loader_cls.return_value = mock_loader
        
        system = GraceActiveLearningSystem(
            session=mock_session,
            retriever=mock_retriever,
            knowledge_base_path=MagicMock()
        )
        
        # Test Study Phase
        result = system.study_topic(
            topic="Python Functions",
            learning_objectives=["Understand syntax", "Learn arguments"]
        )
        
        assert result["topic"] == "Python Functions"
        assert result["materials_studied"] == 1  # Consolidated from the 2 chunks
        assert result["concepts_learned"] == 2
        assert len(result["prefetched_topics"]) == 2
        
        # Verify it attempted to save the learning examples to the DB
        assert mock_session.add.call_count == 2
        assert mock_session.commit.call_count == 2

def test_active_learning_system_practice_skill(mock_session, mock_retriever):
    with patch('backend.cognitive.active_learning_system.PredictiveContextLoader'):
        system = GraceActiveLearningSystem(
            session=mock_session,
            retriever=mock_retriever,
            knowledge_base_path=MagicMock()
        )
        
        # Ensure fresh state
        system.skill_levels = {}
        
        # Initial skill level should be novice/empty
        assert "Python" not in system.skill_levels
        
        # Act: Practice the skill
        result = system.practice_skill(
            skill_name="Python",
            task={"description": "Write a function", "complexity": 0.5},
            sandbox_context={"files": []}
        )
        
        assert result["skill"] == "Python"
        assert result["outcome"] is not None
        
        # The practice simulator is hardcoded to return success if estimated > 0.5 
        # (decide approach returns 0.6)
        assert result["success"] is True
        
        # Validate that the skill level was initialized and incremented
        assert "Python" in system.skill_levels
        skill = system.skill_levels["Python"]
        
        # In active_learning_system, proficiency_score = success_rate * (1 + (tasks_completed / 100))
        # 1.0 * (1 + (1 / 100)) = 1.01. Since 1.01 > 0.8, it jumps Novice -> Beginner immediately.
        assert skill.current_level == SkillLevel.BEGINNER
        assert skill.tasks_completed == 1
        assert skill.success_rate == 1.0
        
        # Verify it committed the practice outcome and updated related knowledge
        assert mock_session.commit.call_count >= 1

def test_active_learning_skill_progression(mock_session, mock_retriever):
    with patch('backend.cognitive.active_learning_system.PredictiveContextLoader'):
        system = GraceActiveLearningSystem(
            session=mock_session,
            retriever=mock_retriever,
            knowledge_base_path=MagicMock()
        )
        
        # Force 100 successful practices to trigger leveling up
        for _ in range(100):
            system.practice_skill(
                skill_name="Python",
                task={"description": "Write a function"},
                sandbox_context={}
            )
            
        skill = system.skill_levels["Python"]
        assert skill.tasks_completed == 100
        # Proficiency score calculation: success_rate * (1 + (tasks / 100))
        # 1.0 * (1 + (100/100)) = 2.0
        assert skill.proficiency_score == 2.0
        
        # 2.0 is > 1.5, so it should have skipped right through Novice/Beginner to Intermediate
        assert skill.current_level == SkillLevel.INTERMEDIATE
