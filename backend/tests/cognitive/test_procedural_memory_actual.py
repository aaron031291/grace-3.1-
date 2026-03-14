import pytest
import sys
import numpy as np
import json
from unittest.mock import MagicMock
from backend.cognitive.procedural_memory import Procedure, ProceduralRepository

def test_create_procedure():
    session = MagicMock()
    repo = ProceduralRepository(session)
    
    proc = repo.create_procedure(
        goal="Build docker",
        action_sequence=[{"step": "1"}],
        preconditions={"os": "linux"}
    )
    
    session.add.assert_called_once()
    assert proc.goal == "Build docker"
    assert proc.success_rate == 1.0

def test_find_procedure_text_fallback():
    session = MagicMock()
    proc = Procedure(name="test", goal="Build docker", preconditions={"os": "linux"})
    
    mq = MagicMock()
    mq.filter.return_value.all.return_value = [proc]
    session.query.return_value = mq
    
    repo = ProceduralRepository(session)
    repo._match_preconditions = MagicMock(return_value=1.0) # exact match
    
    found = repo._find_procedure_text("Build docker", {"os": "linux"})
    assert found == proc

def test_update_success_rate():
    session = MagicMock()
    proc = Procedure(id="1", usage_count=10, success_count=8, success_rate=0.8)
    
    mq = MagicMock()
    mq.filter.return_value.first.return_value = proc
    session.query.return_value = mq
    
    repo = ProceduralRepository(session)
    repo.update_success_rate("1", succeeded=True)
    
    assert proc.usage_count == 11
    assert proc.success_count == 9
    assert proc.success_rate == 9 / 11

def test_cosine_similarity():
    repo = ProceduralRepository(MagicMock())
    a = np.array([1, 0, 0])
    b = np.array([1, 0, 0])
    sim = repo._cosine_similarity(a, b)
    assert sim == pytest.approx(1.0)
    
    c = np.array([0, 1, 0])
    sim2 = repo._cosine_similarity(a, c)
    assert sim2 == pytest.approx(0.0)

if __name__ == "__main__":
    pytest.main(['-v', __file__])
