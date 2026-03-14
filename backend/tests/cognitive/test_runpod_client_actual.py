import pytest
import os
from unittest.mock import patch, MagicMock
from backend.cognitive.runpod_client import RunPodvLLMClient, get_runpod_client

def test_init():
    with patch.dict(os.environ, {"RUNPOD_API_KEY": "test_key", "RUNPOD_ENDPOINT_ID": "test_id"}):
        client = get_runpod_client()
        assert client.api_key == "test_key"
        assert client.endpoint_id == "test_id"
        assert "test_id" in client.base_url

@patch("backend.cognitive.runpod_client.requests.post")
def test_chat(mock_post):
    client = RunPodvLLMClient(api_key="key", endpoint_id="id")
    
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": "hello"}}]}
    mock_post.return_value = mock_response
    
    res = client.chat([{"role": "user", "content": "hi"}])
    assert res == "hello"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
