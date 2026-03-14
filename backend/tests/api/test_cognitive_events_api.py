import pytest
from fastapi.testclient import TestClient
from backend.app import app
import json

client = TestClient(app)

def test_cognitive_events_recent():
    response = client.get("/api/cognitive-events/recent")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert data["ok"] is True

def test_cognitive_events_websocket():
    # Make sure we can connect to the websocket and disconnect without crashing
    with client.websocket_connect("/api/cognitive-events/ws") as websocket:
        # We can publish an event directly to the bus and see if it comes across
        from backend.cognitive.event_bus import publish
        
        publish("test.event", data={"connected": True}, source="pytest")
        
        # Test client WebSocket blocks and waits for message
        data = websocket.receive_json()
        assert "topic" in data
        assert "test.event" in data["topic"]
        assert data["data"]["connected"] is True
        assert data["source"] == "pytest"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
