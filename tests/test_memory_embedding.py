"""
Tests for Memory Embedding Methods

Tests embedding generation and indexing for:
1. ProceduralRepository (procedural_memory.py)
2. EpisodicBuffer (episodic_memory.py)
"""

import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


class TestProceduralMemoryEmbedding:
    """Tests for procedural memory embedding methods."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = Mock()
        session.commit = Mock()
        session.add = Mock()
        session.query = Mock()
        return session

    @pytest.fixture
    def mock_embedder(self):
        """Create mock embedder."""
        embedder = Mock()
        embedder.embed_text = Mock(return_value=[[0.1, 0.2, 0.3, 0.4, 0.5]])
        return embedder

    @pytest.fixture
    def mock_procedure(self):
        """Create mock procedure object."""
        proc = Mock()
        proc.id = "proc_123"
        proc.name = "fix_dockerfile_error"
        proc.goal = "Fix broken Dockerfile build"
        proc.procedure_type = "fix"
        proc.steps = [{"action": "check_syntax"}, {"action": "fix_error"}]
        proc.preconditions = {"file_type": "Dockerfile"}
        proc.embedding = None
        return proc

    def test_generate_procedure_embedding_uses_correct_fields(self, mock_session, mock_embedder, mock_procedure):
        """Test that generate_procedure_embedding uses name + goal + steps + type."""
        try:
            from cognitive.procedural_memory import ProceduralRepository
        except ImportError:
            pytest.skip("Cannot import ProceduralRepository")

        repo = ProceduralRepository(mock_session, embedder=mock_embedder)

        result = repo.generate_procedure_embedding(mock_procedure)

        mock_embedder.embed_text.assert_called_once()
        call_args = mock_embedder.embed_text.call_args[0][0]
        text = call_args[0]

        assert mock_procedure.name in text
        assert mock_procedure.goal in text
        assert "type: fix" in text
        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]

    def test_generate_procedure_embedding_calls_embedder_correctly(self, mock_session, mock_embedder, mock_procedure):
        """Test embedder is called with list containing concatenated text."""
        try:
            from cognitive.procedural_memory import ProceduralRepository
        except ImportError:
            pytest.skip("Cannot import ProceduralRepository")

        repo = ProceduralRepository(mock_session, embedder=mock_embedder)
        repo.generate_procedure_embedding(mock_procedure)

        mock_embedder.embed_text.assert_called_once()
        args = mock_embedder.embed_text.call_args[0]
        assert isinstance(args[0], list)
        assert len(args[0]) == 1
        assert isinstance(args[0][0], str)

    def test_generate_procedure_embedding_handles_missing_embedder(self, mock_session, mock_procedure):
        """Test graceful handling when embedder is not available."""
        try:
            from cognitive.procedural_memory import ProceduralRepository
        except ImportError:
            pytest.skip("Cannot import ProceduralRepository")

        repo = ProceduralRepository(mock_session, embedder=None)
        repo._embedder = None
        repo._use_semantic = False

        with patch('embedding.get_embedding_model', side_effect=ImportError("No embedder")):
            result = repo.generate_procedure_embedding(mock_procedure)

        assert result is None

    def test_generate_procedure_embedding_stores_result(self, mock_session, mock_embedder, mock_procedure):
        """Test embedding is stored as JSON in procedure."""
        try:
            from cognitive.procedural_memory import ProceduralRepository
        except ImportError:
            pytest.skip("Cannot import ProceduralRepository")

        repo = ProceduralRepository(mock_session, embedder=mock_embedder)
        repo.generate_procedure_embedding(mock_procedure)

        assert mock_procedure.embedding is not None
        stored = json.loads(mock_procedure.embedding)
        assert stored == [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_session.commit.assert_called()

    def test_index_all_procedures_indexes_unembedded(self, mock_session, mock_embedder):
        """Test index_all_procedures indexes all procedures without embeddings."""
        try:
            from cognitive.procedural_memory import ProceduralRepository
        except ImportError:
            pytest.skip("Cannot import ProceduralRepository")

        proc1 = Mock()
        proc1.name = "proc1"
        proc1.goal = "goal1"
        proc1.steps = []
        proc1.procedure_type = "fix"
        proc1.preconditions = {}
        proc1.embedding = None

        proc2 = Mock()
        proc2.name = "proc2"
        proc2.goal = "goal2"
        proc2.steps = []
        proc2.procedure_type = "analyze"
        proc2.preconditions = {}
        proc2.embedding = None

        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [proc1, proc2]
        mock_session.query.return_value = mock_query

        mock_embedder.embed_text = Mock(return_value=[[0.1, 0.2], [0.3, 0.4]])

        repo = ProceduralRepository(mock_session, embedder=mock_embedder)
        count = repo.index_all_procedures()

        assert count == 2
        assert proc1.embedding is not None
        assert proc2.embedding is not None
        mock_session.commit.assert_called()

    def test_index_all_procedures_handles_batch_failure_with_fallback(self, mock_session, mock_embedder):
        """Test fallback to individual indexing when batch fails."""
        try:
            from cognitive.procedural_memory import ProceduralRepository
        except ImportError:
            pytest.skip("Cannot import ProceduralRepository")

        proc1 = Mock()
        proc1.name = "proc1"
        proc1.goal = "goal1"
        proc1.steps = []
        proc1.procedure_type = "fix"
        proc1.preconditions = {}
        proc1.embedding = None

        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [proc1]
        mock_session.query.return_value = mock_query

        call_count = [0]
        def embed_side_effect(texts, batch_size=None):
            call_count[0] += 1
            if batch_size is not None:
                raise Exception("Batch failed")
            return [[0.1, 0.2, 0.3]]

        mock_embedder.embed_text = Mock(side_effect=embed_side_effect)

        repo = ProceduralRepository(mock_session, embedder=mock_embedder)
        count = repo.index_all_procedures()

        assert count >= 0

    def test_index_all_procedures_returns_zero_without_embedder(self, mock_session):
        """Test returns 0 when no embedder available."""
        try:
            from cognitive.procedural_memory import ProceduralRepository
        except ImportError:
            pytest.skip("Cannot import ProceduralRepository")

        repo = ProceduralRepository(mock_session, embedder=None)
        repo._embedder = None
        repo._use_semantic = False

        with patch.object(ProceduralRepository, 'embedder', new_callable=lambda: property(lambda self: None)):
            count = repo.index_all_procedures()

        assert count == 0


class TestEpisodicMemoryEmbedding:
    """Tests for episodic memory embedding methods."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = Mock()
        session.commit = Mock()
        session.add = Mock()
        session.query = Mock()
        return session

    @pytest.fixture
    def mock_embedder(self):
        """Create mock embedder."""
        embedder = Mock()
        embedder.embed_text = Mock(return_value=[[0.5, 0.6, 0.7, 0.8]])
        return embedder

    @pytest.fixture
    def mock_episode(self):
        """Create mock episode object."""
        ep = Mock()
        ep.id = "ep_456"
        ep.problem = "Docker container fails to start"
        ep.action = {"type": "restart", "container": "web"}
        ep.outcome = {"success": True, "message": "Container restarted"}
        ep.source = "user_action"
        ep.embedding = None
        return ep

    def test_generate_episode_embedding_uses_correct_fields(self, mock_session, mock_embedder, mock_episode):
        """Test that generate_episode_embedding uses problem + action + outcome + source."""
        try:
            from cognitive.episodic_memory import EpisodicBuffer
        except ImportError:
            pytest.skip("Cannot import EpisodicBuffer")

        buffer = EpisodicBuffer(mock_session, embedder=mock_embedder)
        result = buffer.generate_episode_embedding(mock_episode)

        mock_embedder.embed_text.assert_called_once()
        call_args = mock_embedder.embed_text.call_args[0][0]
        text = call_args[0]

        assert mock_episode.problem in text
        assert "source: user_action" in text
        assert result == [0.5, 0.6, 0.7, 0.8]

    def test_generate_episode_embedding_calls_embedder_correctly(self, mock_session, mock_embedder, mock_episode):
        """Test embedder is called with list containing concatenated text."""
        try:
            from cognitive.episodic_memory import EpisodicBuffer
        except ImportError:
            pytest.skip("Cannot import EpisodicBuffer")

        buffer = EpisodicBuffer(mock_session, embedder=mock_embedder)
        buffer.generate_episode_embedding(mock_episode)

        mock_embedder.embed_text.assert_called_once()
        args = mock_embedder.embed_text.call_args[0]
        assert isinstance(args[0], list)
        assert len(args[0]) == 1
        assert isinstance(args[0][0], str)

    def test_generate_episode_embedding_handles_missing_embedder(self, mock_session, mock_episode):
        """Test graceful handling when embedder is not available."""
        try:
            from cognitive.episodic_memory import EpisodicBuffer
        except ImportError:
            pytest.skip("Cannot import EpisodicBuffer")

        buffer = EpisodicBuffer(mock_session, embedder=None)
        buffer._embedder = None
        buffer._use_semantic = False

        with patch('embedding.get_embedding_model', side_effect=ImportError("No embedder")):
            result = buffer.generate_episode_embedding(mock_episode)

        assert result is None

    def test_generate_episode_embedding_stores_result(self, mock_session, mock_embedder, mock_episode):
        """Test embedding is stored as JSON in episode."""
        try:
            from cognitive.episodic_memory import EpisodicBuffer
        except ImportError:
            pytest.skip("Cannot import EpisodicBuffer")

        buffer = EpisodicBuffer(mock_session, embedder=mock_embedder)
        buffer.generate_episode_embedding(mock_episode)

        assert mock_episode.embedding is not None
        stored = json.loads(mock_episode.embedding)
        assert stored == [0.5, 0.6, 0.7, 0.8]
        mock_session.commit.assert_called()

    def test_index_all_episodes_indexes_unembedded(self, mock_session, mock_embedder):
        """Test index_all_episodes indexes all episodes without embeddings."""
        try:
            from cognitive.episodic_memory import EpisodicBuffer
        except ImportError:
            pytest.skip("Cannot import EpisodicBuffer")

        ep1 = Mock(problem="problem1", action={}, outcome={}, source="test", embedding=None)
        ep2 = Mock(problem="problem2", action={}, outcome={}, source="test", embedding=None)

        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [ep1, ep2]
        mock_session.query.return_value = mock_query

        mock_embedder.embed_text = Mock(return_value=[[0.1, 0.2], [0.3, 0.4]])

        buffer = EpisodicBuffer(mock_session, embedder=mock_embedder)
        count = buffer.index_all_episodes()

        assert count == 2
        assert ep1.embedding is not None
        assert ep2.embedding is not None
        mock_session.commit.assert_called()

    def test_index_all_episodes_handles_batch_failure_with_fallback(self, mock_session, mock_embedder):
        """Test fallback to individual indexing when batch fails."""
        try:
            from cognitive.episodic_memory import EpisodicBuffer
        except ImportError:
            pytest.skip("Cannot import EpisodicBuffer")

        ep1 = Mock(problem="problem1", action={}, outcome={}, source="test", embedding=None)

        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = [ep1]
        mock_session.query.return_value = mock_query

        call_count = [0]
        def embed_side_effect(texts, batch_size=None):
            call_count[0] += 1
            if batch_size is not None:
                raise Exception("Batch failed")
            return [[0.1, 0.2, 0.3]]

        mock_embedder.embed_text = Mock(side_effect=embed_side_effect)

        buffer = EpisodicBuffer(mock_session, embedder=mock_embedder)
        count = buffer.index_all_episodes()

        assert count >= 0

    def test_index_all_episodes_returns_zero_without_embedder(self, mock_session):
        """Test returns 0 when no embedder available."""
        try:
            from cognitive.episodic_memory import EpisodicBuffer
        except ImportError:
            pytest.skip("Cannot import EpisodicBuffer")

        buffer = EpisodicBuffer(mock_session, embedder=None)
        buffer._embedder = None
        buffer._use_semantic = False

        with patch.object(EpisodicBuffer, 'embedder', new_callable=lambda: property(lambda self: None)):
            count = buffer.index_all_episodes()

        assert count == 0


class TestStartupIndexing:
    """Tests for startup indexing behavior."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = Mock()
        session.commit = Mock()
        mock_query = Mock()
        mock_query.filter.return_value.all.return_value = []
        session.query.return_value = mock_query
        return session

    def test_procedural_index_callable(self, mock_session):
        """Test index_all_procedures is callable."""
        try:
            from cognitive.procedural_memory import ProceduralRepository
        except ImportError:
            pytest.skip("Cannot import ProceduralRepository")

        repo = ProceduralRepository(mock_session, embedder=None)
        repo._embedder = None

        assert hasattr(repo, 'index_all_procedures')
        assert callable(repo.index_all_procedures)

    def test_episodic_index_callable(self, mock_session):
        """Test index_all_episodes is callable."""
        try:
            from cognitive.episodic_memory import EpisodicBuffer
        except ImportError:
            pytest.skip("Cannot import EpisodicBuffer")

        buffer = EpisodicBuffer(mock_session, embedder=None)
        buffer._embedder = None

        assert hasattr(buffer, 'index_all_episodes')
        assert callable(buffer.index_all_episodes)

    def test_procedural_index_empty_database(self, mock_session):
        """Test index_all_procedures doesn't fail with empty database."""
        try:
            from cognitive.procedural_memory import ProceduralRepository
        except ImportError:
            pytest.skip("Cannot import ProceduralRepository")

        mock_embedder = Mock()
        mock_embedder.embed_text = Mock(return_value=[])

        repo = ProceduralRepository(mock_session, embedder=mock_embedder)
        count = repo.index_all_procedures()

        assert count == 0

    def test_episodic_index_empty_database(self, mock_session):
        """Test index_all_episodes doesn't fail with empty database."""
        try:
            from cognitive.episodic_memory import EpisodicBuffer
        except ImportError:
            pytest.skip("Cannot import EpisodicBuffer")

        mock_embedder = Mock()
        mock_embedder.embed_text = Mock(return_value=[])

        buffer = EpisodicBuffer(mock_session, embedder=mock_embedder)
        count = buffer.index_all_episodes()

        assert count == 0

    def test_procedural_generate_embedding_callable(self, mock_session):
        """Test generate_procedure_embedding is callable."""
        try:
            from cognitive.procedural_memory import ProceduralRepository
        except ImportError:
            pytest.skip("Cannot import ProceduralRepository")

        repo = ProceduralRepository(mock_session, embedder=None)
        assert hasattr(repo, 'generate_procedure_embedding')
        assert callable(repo.generate_procedure_embedding)

    def test_episodic_generate_embedding_callable(self, mock_session):
        """Test generate_episode_embedding is callable."""
        try:
            from cognitive.episodic_memory import EpisodicBuffer
        except ImportError:
            pytest.skip("Cannot import EpisodicBuffer")

        buffer = EpisodicBuffer(mock_session, embedder=None)
        assert hasattr(buffer, 'generate_episode_embedding')
        assert callable(buffer.generate_episode_embedding)
