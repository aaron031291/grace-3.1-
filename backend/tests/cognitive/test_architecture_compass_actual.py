import pytest
from backend.cognitive.architecture_compass import ArchitectureCompass, COMPONENT_KNOWLEDGE

def test_compass_explain():
    compass = ArchitectureCompass()
    
    # Just seed the map manually without building from file system
    compass.component_map = COMPONENT_KNOWLEDGE.copy()
    
    explanation = compass.explain("cognitive/pipeline.py")
    assert "9-stage cognitive processing chain" in explanation
    
    explanation3 = compass.explain("does_not_exist")
    assert "Unknown component" in explanation3

def test_compass_find_for():
    compass = ArchitectureCompass()
    compass.component_map = COMPONENT_KNOWLEDGE.copy()
    
    # find components containing "consensus" capability
    res = compass.find_for("multi_model_consensus")
    assert "cognitive/consensus_engine.py" in res
    assert "api/brain_api_v2.py" in res

if __name__ == "__main__":
    pytest.main(['-v', __file__])
