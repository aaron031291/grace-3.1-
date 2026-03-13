import pytest
import time
from backend.cognitive.event_bus import (
    subscribe, publish, publish_async, get_recent_events, get_subscriber_count, Event, _subscribers, _event_log, MAX_LOG
)

@pytest.fixture(autouse=True)
def clear_event_bus():
    """Clear subscribers and event log before each test."""
    _subscribers.clear()
    _event_log.clear()
    yield
    _subscribers.clear()
    _event_log.clear()

def test_subscribe_and_publish_exact():
    received = []
    
    def handler(event: Event):
        received.append(event)
        
    subscribe("test.topic", handler)
    
    publish("test.topic", {"msg": "hello"}, "pytest")
    
    assert len(received) == 1
    assert received[0].topic == "test.topic"
    assert received[0].data["msg"] == "hello"
    assert received[0].source == "pytest"
    
def test_subscribe_wildcards():
    received_specific = []
    received_wildcard = []
    received_global = []
    
    subscribe("user.login", lambda e: received_specific.append(e))
    subscribe("user.*", lambda e: received_wildcard.append(e))
    subscribe("*", lambda e: received_global.append(e))
    
    # Publish to the specific topic
    publish("user.login", {"id": 123})
    
    assert len(received_specific) == 1
    assert len(received_wildcard) == 1
    assert len(received_global) == 1
    
    # Publish to a different sub-topic
    publish("user.logout", {"id": 123})
    
    assert len(received_specific) == 1  # Unchanged
    assert len(received_wildcard) == 2  # Match user.*
    assert len(received_global) == 2    # Match *

def test_publish_async():
    received = []
    
    def handler(event: Event):
        received.append(event)
        
    subscribe("async.test", handler)
    
    publish_async("async.test", {"flag": True})
    
    # Allow small wait for the thread to execute
    time.sleep(0.1)
    
    assert len(received) == 1
    assert received[0].data["flag"] is True

def test_get_recent_events_and_max_log():
    # Publish more than MAX_LOG
    for i in range(MAX_LOG + 10):
        publish("spam.topic", {"seq": i})
        
    recent = get_recent_events(limit=10)
    
    # Should only retain max_log items total in _event_log
    assert len(_event_log) == MAX_LOG
    
    # Recent events are returned in reversed order
    assert len(recent) == 10
    assert recent[0]["topic"] == "spam.topic"
    
    # The most recent one is at index 0 (LIFO from get_recent_events constraint)
    # The last published was seq MAX_LOG + 9
    # Actually wait to verify exact seq if data was stored, but event_log just stores topic, source, ts
    assert recent[0]["source"] == "system"

def test_subscriber_count():
    def dummy(e): pass
    
    subscribe("topic.a", dummy)
    subscribe("topic.a", dummy)
    subscribe("topic.b", dummy)
    
    counts = get_subscriber_count()
    
    assert counts["topic.a"] == 2
    assert counts["topic.b"] == 1
