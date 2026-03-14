import pytest
import sys
import json
from unittest.mock import MagicMock, patch
from backend.cognitive.model_updater import (
    check_kimi_models,
    check_opus_models,
    check_all_models,
    update_model,
    _load_version_history
)

def test_check_kimi_models():
    sys.modules["settings"] = MagicMock()
    sys.modules["settings"].settings.KIMI_API_KEY = "dummy"
    sys.modules["settings"].settings.KIMI_MODEL = "kimi-old"
    
    mock_client = MagicMock()
    mock_client.get_all_models.return_value = [
        {"id": "kimi-old", "created": 1},
        {"id": "kimi-new", "created": 2}
    ]
    
    mock_client_class = MagicMock(return_value=mock_client)
    sys.modules["llm_orchestrator.kimi_client"] = MagicMock()
    sys.modules["llm_orchestrator.kimi_client"].KimiLLMClient = mock_client_class
    
    res = check_kimi_models()
    
    assert res["provider"] == "kimi"
    assert res["current_model"] == "kimi-old"
    assert len(res["available"]) == 2
    assert "kimi-new" in res["new_found"]
    assert "kimi-old" not in res["new_found"]

def test_check_opus_models():
    sys.modules["settings"] = MagicMock()
    sys.modules["settings"].settings.OPUS_API_KEY = "dummy"
    sys.modules["settings"].settings.OPUS_MODEL = "opus-old"
    sys.modules["settings"].settings.OPUS_BASE_URL = "http://anthropic"
    
    sys.modules["requests"] = MagicMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"data": [{"id": "opus-old"}, {"id": "opus-new"}]}
    sys.modules["requests"].get.return_value = mock_resp
    
    res = check_opus_models()
    
    assert res["provider"] == "opus"
    assert res["current_model"] == "opus-old"
    assert len(res["available"]) == 2
    assert "opus-new" in res["new_found"]

def test_update_model(tmp_path):
    sys.modules["settings"] = MagicMock()
    sys.modules["settings"].settings.KIMI_MODEL = "kimi-old"
    sys.modules["api._genesis_tracker"] = MagicMock()
    
    # We patch Path to use tmp_path
    with patch("backend.cognitive.model_updater.Path") as mock_path_cls:
        # Mock the env file
        mock_env_file = MagicMock()
        mock_env_file.exists.return_value = True
        mock_env_file.read_text.return_value = "KIMI_MODEL=kimi-old\nOTHER=foo"
        
        # Mock the versions file
        mock_versions_file = MagicMock()
        mock_versions_file.exists.return_value = True
        mock_versions_file.read_text.return_value = json.dumps({"checks": [], "current": {}, "history": []})
        
        def path_side_effect(arg):
            if str(arg).endswith(".env"):
                return mock_env_file
            if str(arg).endswith("model_versions.json"):
                return mock_versions_file
            # fallback
            mock_p = MagicMock()
            mock_p.parent = mock_p
            mock_p.__truediv__.return_value = mock_p
            return mock_p

        mock_path_cls.return_value.__truediv__.side_effect = path_side_effect
        
        # We need to mock _load_version_history because it uses the module level VERSIONS_FILE
        # Let's just patch _load_version_history and _save_version_history directly
        with patch("backend.cognitive.model_updater._load_version_history", return_value={"checks": [], "current": {}, "history": []}):
            with patch("backend.cognitive.model_updater._save_version_history"):
                res = update_model("kimi", "kimi-new")
                
                assert res["updated"] is True
                assert res["old_model"] == "kimi-old"
                assert res["new_model"] == "kimi-new"
                assert sys.modules["settings"].settings.KIMI_MODEL == "kimi-new"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
