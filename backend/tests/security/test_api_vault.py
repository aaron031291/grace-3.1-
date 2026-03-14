import pytest
from unittest.mock import patch, MagicMock
import os
from security.api_vault import _mask_key, get_vault, APIVault

def test_mask_key():
    assert _mask_key("") == "(not set)"
    assert _mask_key(None) == "(not set)"
    assert _mask_key("1234567890") == "1234****"
    assert _mask_key("12345678901234567890") == "12345678...7890"

def test_api_vault_singleton():
    v1 = get_vault()
    v2 = get_vault()
    assert v1 is v2

def test_get_status():
    vault = get_vault()
    with patch.multiple(vault, get_key=MagicMock(return_value="test_key_1234567890"),
                         get_base_url=MagicMock(return_value="http://localhost"),
                         get_model=MagicMock(return_value="model-x")):
        status = vault.get_status()
        assert len(status) == 4
        kimi_status = next(s for s in status if s["id"] == "kimi")
        assert kimi_status["key_configured"] is True

@patch("requests.get")
def test_verify_kimi(mock_get):
    vault = get_vault()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"id": "moonshot-v1-8k"}]}
    mock_get.return_value = mock_response

    with patch.object(vault, 'get_key', return_value="fake_key"):
        with patch.object(vault, 'get_base_url', return_value="fake_url"):
            res = vault._verify_kimi()
            assert res["connected"] is True
            assert "moonshot-v1-8k" in res["models"]

if __name__ == "__main__":
    pytest.main(['-v', __file__])
