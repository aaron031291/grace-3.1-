import pytest
from backend.cognitive.system_registry import get_system_registry

def test_registry_singleton():
    reg1 = get_system_registry()
    reg2 = get_system_registry()
    assert reg1 is reg2

def test_registry_health_check():
    reg = get_system_registry()
    health = reg.check_health()
    assert "total" in health
    assert health["total"] > 0
    
    all_comps = reg.get_all()
    assert len(all_comps) == health["total"]

def test_registry_get_by_category():
    reg = get_system_registry()
    cats = reg.get_by_category()
    assert "cognitive" in cats
    assert len(cats["cognitive"]) > 0

if __name__ == "__main__":
    pytest.main(['-v', __file__])
