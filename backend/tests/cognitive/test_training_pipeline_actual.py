import pytest
from backend.cognitive.training_pipeline import list_sources, get_recommended_plan

def test_list_sources():
    sources = list_sources()
    assert len(sources) > 0
    names = [s["name"] for s in sources]
    assert any("The Stack" in n for n in names)

def test_recommended_plan():
    plan_small = get_recommended_plan(100)
    assert plan_small["total_estimated_gb"] <= 100
    
    plan_large = get_recommended_plan(2000)
    # the stack + dolma + ...
    assert plan_large["total_estimated_gb"] > 1000
    
if __name__ == "__main__":
    pytest.main(['-v', __file__])
