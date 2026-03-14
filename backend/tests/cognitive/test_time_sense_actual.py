import pytest
from datetime import datetime, timezone, timedelta
from backend.cognitive.time_sense import TimeSense, _fmt_duration

def test_now_context():
    context = TimeSense.now_context()
    assert "timestamp" in context
    assert "period" in context
    assert "day_of_week" in context
    assert isinstance(context["is_weekend"], bool)

def test_urgency_score():
    now = datetime.now(timezone.utc)
    
    # Critical (within 1 hour)
    deadline_critical = (now + timedelta(minutes=30)).isoformat()
    res = TimeSense.urgency_score(deadline_critical)
    assert res["urgency"] == 0.95
    assert res["label"] == "critical"
    
    # Overdue
    deadline_overdue = (now - timedelta(hours=2)).isoformat()
    res = TimeSense.urgency_score(deadline_overdue)
    assert res["urgency"] == 1.0
    assert res["label"] == "overdue"
    assert "hours_overdue" in res
    
    # Invalid
    res = TimeSense.urgency_score("not a date")
    assert res["urgency"] == 0
    assert res["label"] == "no_deadline"

def test_time_until():
    now = datetime.now(timezone.utc)
    target = (now + timedelta(hours=2)).isoformat()
    
    res = TimeSense.time_until(target)
    assert not res["is_past"]
    assert "text" in res
    assert "seconds" in res

def test_activity_patterns():
    now = datetime.now(timezone.utc)
    timestamps = [
        now.isoformat(),
        (now + timedelta(hours=1)).isoformat(),
        (now + timedelta(hours=2)).isoformat(),
        (now - timedelta(days=1)).isoformat()
    ]
    
    res = TimeSense.activity_patterns(timestamps)
    assert res["total"] == 4
    assert "peak_hour" in res
    assert "busiest_period" in res

def test_prioritise_by_time():
    now = datetime.now(timezone.utc)
    tasks = [
        {"id": 1, "deadline": (now + timedelta(days=5)).isoformat(), "priority": "low"},
        {"id": 2, "deadline": (now + timedelta(hours=1)).isoformat(), "priority": "high"},
        {"id": 3, "deadline": (now - timedelta(hours=1)).isoformat(), "priority": "critical"}
    ]
    
    scored = TimeSense.prioritise_by_time(tasks)
    
    assert len(scored) == 3
    assert scored[0]["id"] == 3  # Overdue + critical
    assert scored[1]["id"] == 2  # High + 1 hr
    assert scored[2]["id"] == 1  # Low + 5 days

if __name__ == "__main__":
    pytest.main(['-v', __file__])
