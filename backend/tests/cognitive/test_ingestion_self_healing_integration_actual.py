import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.ingestion_self_healing_integration import IngestionSelfHealingIntegration

def test_init_and_infer_topic():
    from pathlib import Path
    mock_session = MagicMock()
    mock_kb_path = Path("test_kb")
    
    with patch("backend.cognitive.ingestion_self_healing_integration.get_genesis_service"), \
         patch("backend.cognitive.ingestion_self_healing_integration.get_genesis_trigger_pipeline"), \
         patch("backend.cognitive.ingestion_self_healing_integration.get_autonomous_healing"), \
         patch("backend.cognitive.ingestion_self_healing_integration.get_mirror_system"):
        
        integration = IngestionSelfHealingIntegration(
            session=mock_session,
            knowledge_base_path=mock_kb_path,
            enable_healing=True,
            enable_mirror=True
        )
        
        topic = integration._infer_topic_from_path(Path("test_dir/my_file.txt"))
        assert topic == "test_dir"
        
        topic2 = integration._infer_topic_from_path(Path("my_file_two.txt"))
        assert topic2 == "my file two"

if __name__ == "__main__":
    pytest.main(['-v', __file__])
