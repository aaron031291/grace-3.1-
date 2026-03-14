import pytest
from backend.cognitive.ambiguity import AmbiguityLedger, AmbiguityLevel

def test_ledger_add_known():
    ledger = AmbiguityLedger()
    ledger.add_known("database_url", "postgres://localhost", "Found in config")
    
    assert "database_url" in ledger._entries
    entry = ledger.get("database_url")
    assert entry.level == AmbiguityLevel.KNOWN
    assert entry.confidence == 1.0
    assert not entry.blocking
    
def test_ledger_add_inferred():
    ledger = AmbiguityLedger()
    # High confidence inference
    ledger.add_inferred("user_intent", "query_data", 0.9, "Based on keywords")
    entry_high = ledger.get("user_intent")
    assert entry_high.level == AmbiguityLevel.INFERRED
    assert not entry_high.blocking
    
    # Low confidence inference (blocking)
    ledger.add_inferred("system_state", "stable", 0.6, "Inferred from logs")
    entry_low = ledger.get("system_state")
    assert entry_low.level == AmbiguityLevel.INFERRED
    assert entry_low.blocking

def test_ledger_add_assumed():
    ledger = AmbiguityLedger()
    ledger.add_assumed("api_available", True, must_validate=True)
    entry = ledger.get("api_available")
    assert entry.level == AmbiguityLevel.ASSUMED
    assert entry.blocking
    
def test_ledger_add_unknown():
    ledger = AmbiguityLedger()
    ledger.add_unknown("db_password", blocking=True)
    entry = ledger.get("db_password")
    assert entry.level == AmbiguityLevel.UNKNOWN
    assert entry.value is None
    assert entry.blocking

def test_ledger_filters_and_queries():
    ledger = AmbiguityLedger()
    ledger.add_known("k1", "v1")
    ledger.add_inferred("k2", "v2", 0.8)
    ledger.add_assumed("k3", "v3", must_validate=False)
    ledger.add_unknown("k4", blocking=True)
    
    all_entries = ledger.get_all()
    assert len(all_entries) == 4
    
    knowns = ledger.get_by_level(AmbiguityLevel.KNOWN)
    assert len(knowns) == 1
    assert knowns[0].key == "k1"
    
    blocking_unknowns = ledger.get_blocking_unknowns()
    assert len(blocking_unknowns) == 1
    assert blocking_unknowns[0].key == "k4"
    assert ledger.has_blocking_unknowns()
    
    blocking_all = ledger.get_blocking_items()
    assert len(blocking_all) == 1
    
def test_ledger_promote_to_known():
    ledger = AmbiguityLedger()
    ledger.add_unknown("secret_key", blocking=True)
    assert ledger.get("secret_key").level == AmbiguityLevel.UNKNOWN
    
    ledger.promote_to_known("secret_key", "my-secret")
    entry = ledger.get("secret_key")
    assert entry.level == AmbiguityLevel.KNOWN
    assert entry.value == "my-secret"
    assert "Promoted from" in entry.notes
    
def test_ledger_to_dict_and_summary():
    ledger = AmbiguityLedger()
    ledger.add_known("k1", "v1")
    ledger.add_unknown("k2", blocking=True)
    
    d = ledger.to_dict()
    assert "known" in d
    assert d["known"]["k1"] == "v1"
    assert len(d["unknown"]) == 1
    
    summary = ledger.summary()
    assert "1 known" in summary
    assert "1 unknown" in summary
    assert "1 blocking" in summary

if __name__ == "__main__":
    pytest.main(['-v', __file__])
