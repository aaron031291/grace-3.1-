import pytest
from datetime import datetime
from backend.cognitive.spindle_event_store import SpindleEventStore, get_event_store

def test_singleton():
    s1 = get_event_store()
    s2 = get_event_store()
    assert s1 is s2

def test_fallback_append_and_query():
    store = SpindleEventStore()
    store._db_available = False # force fallback
    
    seq1 = store.append("topic1", "sys", payload={"a": 1})
    assert seq1 == 1
    
    seq2 = store.append("topic2", "sys", payload={"b": 2})
    assert seq2 == 2
    
    res = store.query(topic="topic1")
    assert len(res) == 1
    assert res[0]["topic"] == "topic1"
    
    replay = store.replay(after_sequence=1)
    assert len(replay) == 1
    assert replay[0]["topic"] == "topic2"

def test_append_async():
    store = SpindleEventStore()
    store._db_available = False # force fallback
    
    seq = store.append_async("async_topic", "sys")
    assert seq > 0
    
    # check if it is in queue
    assert not store._write_queue.empty()
    item = store._write_queue.get()
    assert item["topic"] == "async_topic"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
