import pytest
from backend.cognitive.communication_layer import format_for_target, CommunicationTarget

def test_communication_layer_human():
    data = {
        "health_score": 95,
        "status": "online",
        "improvements": ["Faster processing"],
        "problems": ["High memory"],
        "metrics": {"latency_ms": 10}
    }
    
    output = format_for_target(data, target=CommunicationTarget.HUMAN)
    
    assert "System health is at 95%." in output
    assert "Current status: online" in output
    assert "What's going well" in output
    assert "+ Faster processing" in output
    assert "needing attention" in output
    assert "- High memory" in output
    assert "Key numbers" in output
    assert "Latency Ms: 10" in output

def test_communication_layer_system():
    data = "hello world"
    output = format_for_target(data, target=CommunicationTarget.SYSTEM)
    # Should wrap string in dict
    assert isinstance(output, dict)
    assert output["message"] == "hello world"
    
    data_list = [1, 2, 3]
    output_list = format_for_target(data_list, target=CommunicationTarget.SYSTEM)
    assert output_list["count"] == 3
    assert output_list["items"] == [1, 2, 3]

def test_communication_layer_llm():
    data = {"task": "fix"}
    context = "High priority"
    output = format_for_target(data, target=CommunicationTarget.LLM, context=context)
    
    assert "Context: High priority" in output
    assert "task" in output
    assert "fix" in output

if __name__ == "__main__":
    pytest.main(['-v', __file__])
