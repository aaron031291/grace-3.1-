import pytest
import time
from backend.cognitive.event_bus import (
    subscribe,
    publish,
    publish_async,
    get_recent_events,
    get_subscriber_count,
    Event
)

def test_publish_subscribe_exact():
    test_data = {"param": "value"}
    received = []
    
    def handler(evt: Event):
        received.append(evt)

    subscribe("test.topic.exact", handler)
    publish("test.topic.exact", data=test_data, source="pytest")

    assert len(received) == 1
    assert received[0].topic == "test.topic.exact"
    assert received[0].data["param"] == "value"
    assert received[0].source == "pytest"

def test_publish_subscribe_wildcard():
    received = []
    
    def handler(evt: Event):
        received.append(evt)

    subscribe("llm.*", handler)
    publish("llm.called", data={"status": "working"})
    publish("llm.failed", data={"status": "error"})
    publish("other.topic", data={})

    assert len(received) == 2
    assert received[0].topic == "llm.called"
    assert received[1].topic == "llm.failed"

def test_get_recent_events():
    publish("test.log.1", source="log_test")
    publish("test.log.2", source="log_test")
    events = get_recent_events()
    topics = [e["topic"] for e in events]
    assert "test.log.1" in topics
    assert "test.log.2" in topics

def test_publish_async():
    received = []
    def handler(evt: Event):
        received.append(evt)
        
    subscribe("async.test", handler)
    publish_async("async.test", data={"async": True})
    
    # Wait for the background thread to execute
    time.sleep(0.5)
    
    assert len(received) >= 1
    assert received[0].data["async"] is True

def test_subscriber_count():
    subscribe("count.topic", lambda e: None)
    subscribe("count.topic", lambda e: None)
    
    counts = get_subscriber_count()
    assert counts.get("count.topic", 0) >= 2

if __name__ == "__main__":
    pytest.main(["-v", __file__])
