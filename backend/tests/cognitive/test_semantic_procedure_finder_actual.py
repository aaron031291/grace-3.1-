import pytest
from unittest.mock import MagicMock, patch
from backend.cognitive.semantic_procedure_finder import SemanticProcedureFinder, get_semantic_procedure_finder
from models.database_models import Procedure

@patch("backend.cognitive.semantic_procedure_finder.get_embedding_model")
@patch("backend.cognitive.semantic_procedure_finder.get_qdrant_client")
def test_find_procedure_semantic(mock_qdrant, mock_embedder):
    session = MagicMock()
    
    # Mock embedder
    mock_embed = MagicMock()
    mock_embed.embed_text.return_value = [[0.1, 0.2, 0.3]]
    mock_embedder.return_value = mock_embed
    
    # Mock Qdrant
    mock_db = MagicMock()
    mock_db.search_vectors.return_value = [{"id": 1, "score": 0.9}]
    mock_qdrant.return_value = mock_db
    
    # Mock Session
    mock_proc = Procedure(id=1, goal="test goal", success_rate=0.9)
    session.query.return_value.filter.return_value.all.return_value = [mock_proc]
    
    finder = SemanticProcedureFinder(session)
    res = finder.find_procedure_semantic("test goal")
    
    assert len(res) == 1
    assert res[0].id == 1

@patch("backend.cognitive.semantic_procedure_finder.get_embedding_model")
@patch("backend.cognitive.semantic_procedure_finder.get_qdrant_client")
def test_fallback(mock_qdrant, mock_embedder):
    session = MagicMock()
    
    # Mock error in semantic search
    mock_embed = MagicMock()
    mock_embed.embed_text.side_effect = Exception("Embedder error")
    mock_embedder.return_value = mock_embed
    
    # Mock Session fallback
    mock_proc = Procedure(id=1, goal="test goal", success_rate=0.9)
    session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_proc]
    
    finder = SemanticProcedureFinder(session)
    res = finder.find_procedure_semantic("test goal")
    
    assert len(res) == 1
    assert res[0].id == 1

if __name__ == "__main__":
    pytest.main(['-v', __file__])
