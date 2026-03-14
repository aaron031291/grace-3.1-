import pytest
import os
import time

# Avoid starting ZMQ pubsub bridge which binds to a port and causes conflicts
os.environ["IS_SPINDLE_DAEMON"] = "1"

from backend.cognitive.event_bus import (
    subscribe, publish, publish_async, get_recent_events, get_subscriber_count, Event
)

def test_event_bus_pub_sub():
    received = []
    
    def handler(event: Event):
        received.append(event)
        
    subscribe("test.topic", handler)
    publish("test.topic", {"msg": "hello"})
    
    assert len(received) >= 1
    assert received[-1].data["msg"] == "hello"
    assert received[-1].topic == "test.topic"

def test_event_bus_wildcard():
    received = []
    
    def handler(event: Event):
        received.append(event)
        
    subscribe("wildcard.*", handler)
    publish("wildcard.trigger1", {"id": 1})
    publish("wildcard.trigger2", {"id": 2})
    publish("other.topic", {"id": 3})
    
    # We should have received the two wildcard events
    matched = [e for e in received if e.topic.startswith("wildcard.")]
    assert len(matched) == 2
    assert matched[0].data["id"] == 1
    assert matched[1].data["id"] == 2

def test_publish_async():
    received = []
    
    def handler(event: Event):
        if event.topic == "async.topic":
            received.append(event)
        
    subscribe("async.topic", handler)
    publish_async("async.topic", {"data": "async_test"})
    
    # Wait briefly for thread to finish
    time.sleep(0.1)
    
    assert len(received) >= 1
    assert received[-1].data["data"] == "async_test"

def test_get_recent_events():
    publish("recent.topic1", {"a": 1})
    events = get_recent_events(limit=10)
    
    assert len(events) >= 1
    assert any(e["topic"] == "recent.topic1" for e in events)

def test_get_subscriber_count():
    def dummy(e): pass
    subscribe("count.topic", dummy)
    
    counts = get_subscriber_count()
    assert "count.topic" in counts
    assert counts["count.topic"] >= 1

if __name__ == "__main__":
    pytest.main(['-v', __file__])
