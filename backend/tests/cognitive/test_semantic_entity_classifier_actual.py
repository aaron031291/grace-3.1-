import pytest
from backend.cognitive.semantic_entity_classifier import SemanticEntityClassifier, get_classifier, classify_entity

def test_classifier_singleton():
    c1 = get_classifier()
    c2 = get_classifier()
    assert c1 is c2

def test_classify_customer():
    clf = SemanticEntityClassifier()
    res = clf.classify("User Aaron placed an order for $99")
    
    assert res.entity_type in ("CUSTOMER", "TRANSACTION")
    assert res.confidence > 0.0

def test_classify_code():
    clf = SemanticEntityClassifier()
    res = clf.classify("def my_function(): pass", filename="test.py")
    
    assert res.entity_type == "CODE"
    assert res.db_table == "code_entities"

def test_classify_entity_module():
    res = classify_entity("System alert: CPU is 99%", source_type="system_generated")
    assert res["entity_type"] == "SYSTEM"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
