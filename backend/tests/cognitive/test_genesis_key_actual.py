import pytest
from backend.cognitive.genesis_key import genesis_key, GenesisKeyGenerator

def test_genesis_key_mint():
    # Test singleton instance
    key1 = genesis_key.mint("test_component")
    
    assert key1.startswith("genesis_test_component_")
    
    # Check length: 'genesis_' + 'test_component' + '_' + 12 chars hash
    assert len(key1) == len("genesis_test_component_") + 12
    
def test_genesis_key_generator_unique():
    gen = GenesisKeyGenerator()
    key1 = gen.mint("foo")
    key2 = gen.mint("foo")
    
    assert key1 != key2

if __name__ == "__main__":
    pytest.main(['-v', __file__])
