import pytest
import sys
from unittest.mock import MagicMock, patch
from backend.cognitive.notification_system import NotificationSystem

@pytest.fixture(autouse=True)
def isolated_notif():
    NotificationSystem._instance = None
    yield
    NotificationSystem._instance = None

def test_alert_console_and_history():
    notif_sys = NotificationSystem()
    
    with patch("backend.cognitive.notification_system.logger.warning") as mock_logger:
        res = notif_sys.alert("Test", "msg", severity="high", channel="console")
        
        assert "console" in res["channels_sent"]
        assert "Test" in res["title"]
        assert len(notif_sys._history) == 1
        mock_logger.assert_called_once()

def test_alert_ui_event_bus():
    notif_sys = NotificationSystem()
    
    sys.modules["cognitive.event_bus"] = MagicMock()
    
    res = notif_sys.alert("UI Test", "msg", channel="ui")
    
    assert "ui" in res["channels_sent"]
    sys.modules["cognitive.event_bus"].publish.assert_called_once()
    
def test_history_limits():
    notif_sys = NotificationSystem()
    for i in range(250):
        notif_sys._history.append({"id": str(i), "timestamp": "2024-01-01"})
        
    # Trigger limit
    notif_sys.alert("Lim", "msg", channel="console")
    
    assert len(notif_sys._history) <= 100

def test_get_recent():
    notif_sys = NotificationSystem()
    notif_sys.alert("1", "msg", channel="console")
    notif_sys.alert("2", "msg", channel="console")
    
    recent = notif_sys.get_recent(1)
    assert len(recent) == 1
    assert recent[0]["title"] == "2"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
