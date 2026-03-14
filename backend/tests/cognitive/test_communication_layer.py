import pytest
from backend.cognitive.communication_layer import (
    CommunicationTarget,
    format_for_target,
    detect_best_target,
    smart_format
)

def test_detect_best_target():
    assert detect_best_target("To a human user") == CommunicationTarget.HUMAN
    assert detect_best_target("Hey Aaron, what's up") == CommunicationTarget.HUMAN
    assert detect_best_target("Send to REST API endpoint") == CommunicationTarget.API
    assert detect_best_target("Feed this to the LLM prompt") == CommunicationTarget.LLM
    assert detect_best_target("Route to cognitive module") == CommunicationTarget.COMPONENT
    assert detect_best_target("Unknown random string") == CommunicationTarget.SYSTEM

def test_format_human_string():
    result = format_for_target("Just a string", target=CommunicationTarget.HUMAN)
    assert result == "Just a string"

def test_format_human_dict():
    data = {"status": "Online", "health_score": 95, "improvements": ["Speed", "Memory"], "error": "None"}
    result = format_for_target(data, target=CommunicationTarget.HUMAN)
    assert "System health is at 95%." in result
    assert "Current status: Online." in result
    assert "What's going well:" in result
    assert "+ Speed" in result
    assert "There was an issue: None" in result

def test_format_system():
    data = ["item1", "item2"]
    result = format_for_target(data, target=CommunicationTarget.SYSTEM)
    assert isinstance(result, dict)
    assert result["count"] == 2
    assert "items" in result

def test_format_component():
    data = {"key1": "val1", "key2": None}
    result = format_for_target(data, target=CommunicationTarget.COMPONENT)
    assert "key1" in result
    assert "key2" not in result

def test_format_llm():
    data = {"fact": "Sky is blue"}
    result = format_for_target(data, target=CommunicationTarget.LLM, context="General Info")
    assert "Context: General Info" in result
    assert "Data:" in result
    assert "fact: Sky is blue" in result

def test_format_api():
    data = {"user": "Aaron"}
    result = format_for_target(data, target=CommunicationTarget.API)
    assert result["success"] is True
    assert result["data"]["user"] == "Aaron"

def test_smart_format():
    data = {"health_score": 88, "status": "Degraded"}
    # Target "user" -> HUMAN
    human_result = smart_format(data, recipient="user")
    assert isinstance(human_result, str)
    assert "System health is at 88%." in human_result

    # Target "api" -> API
    api_result = smart_format(data, recipient="api")
    assert isinstance(api_result, dict)
    assert api_result["success"] is True
    assert api_result["data"]["health_score"] == 88

if __name__ == "__main__":
    pytest.main(["-v", __file__])
