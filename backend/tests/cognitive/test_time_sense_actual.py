import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from backend.cognitive.time_sense import TimeSense, _fmt_duration

@patch("backend.cognitive.time_sense.datetime")
def test_now_context(mock_datetime):
    # Set mock to return our specific UTC datetime for .now()
    dt = datetime(2024, 5, 10, 14, 30, 0, tzinfo=timezone.utc)
    mock_datetime.now.return_value = dt
    
    ctx = TimeSense.now_context()
    assert ctx["hour"] == 14
    assert ctx["period"] == "afternoon"
    assert ctx["is_business_hours"] is True
    assert ctx["day_of_week"] == "Friday"

@patch("backend.cognitive.time_sense.datetime")
def test_urgency_score(mock_datetime):
    # Base mock time
    dt = datetime(2024, 5, 10, 14, 30, 0, tzinfo=timezone.utc)
    mock_datetime.now.return_value = dt
    mock_datetime.fromisoformat.side_effect = datetime.fromisoformat
    
    # 30 mins left
    deadline = (dt + timedelta(minutes=30)).isoformat()
    score = TimeSense.urgency_score(deadline)
    assert score["label"] == "critical"
    
    # overdue
    overdue = (dt - timedelta(hours=2)).isoformat()
    score2 = TimeSense.urgency_score(overdue)
    assert score2["label"] == "overdue"
    assert score2["urgency"] == 1.0

def test_fmt_duration():
    assert _fmt_duration(30) == "30s"
    assert "m" in _fmt_duration(90)
    assert "h" in _fmt_duration(3600)
    assert "d" in _fmt_duration(90000)

if __name__ == "__main__":
    pytest.main(['-v', __file__])
