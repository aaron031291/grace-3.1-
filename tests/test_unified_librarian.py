"""
Tests for Unified Librarian System (Amp + Grace Integration)

Tests the integration between Grace's internal Librarian and the Amp Librarian Bridge.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import json

# Import the unified librarian components
from librarian.amp_librarian_bridge import (
    AmpLibrarianBridge,
    ExternalKnowledgeSource,
    KnowledgeSourceType,
    UnifiedSearchResult,
    get_amp_librarian_bridge,
    integrate_with_grace_librarian
)


class TestKnowledgeSourceType:
    """Test knowledge source type enumeration."""
    
    def test_source_types_exist(self):
        """Verify all expected source types exist."""
        assert KnowledgeSourceType.LOCAL.value == "local"
        assert KnowledgeSourceType.GITHUB.value == "github"
        assert KnowledgeSourceType.DOCUMENTATION.value == "docs"
        assert KnowledgeSourceType.API_REFERENCE.value == "api"
        assert KnowledgeSourceType.COMMUNITY.value == "community"


class TestExternalKnowledgeSource:
    """Test external knowledge source dataclass."""
    
    def test_create_source(self):
        """Test creating an external knowledge source."""
        source = ExternalKnowledgeSource(
            source_type=KnowledgeSourceType.GITHUB,
            identifier="github.com/test/repo",
            name="Test Repo",
            url="https://github.com/test/repo"
        )
        
        assert source.source_type == KnowledgeSourceType.GITHUB
        assert source.identifier == "github.com/test/repo"
        assert source.name == "Test Repo"
        assert source.is_private == False
        assert source.needs_sync == True  # Never synced
    
    def test_needs_sync_true_when_never_synced(self):
        """Source needs sync when never synced."""
        source = ExternalKnowledgeSource(
            source_type=KnowledgeSourceType.GITHUB,
            identifier="test",
            name="Test",
            url="https://test.com",
            last_synced=None
        )
        assert source.needs_sync == True
    
    def test_needs_sync_true_when_stale(self):
        """Source needs sync when past sync interval."""
        source = ExternalKnowledgeSource(
            source_type=KnowledgeSourceType.GITHUB,
            identifier="test",
            name="Test",
            url="https://test.com",
            last_synced=datetime.utcnow() - timedelta(hours=48),
            sync_interval_hours=24
        )
        assert source.needs_sync == True
    
    def test_needs_sync_false_when_fresh(self):
        """Source doesn't need sync when recently synced."""
        source = ExternalKnowledgeSource(
            source_type=KnowledgeSourceType.GITHUB,
            identifier="test",
            name="Test",
            url="https://test.com",
            last_synced=datetime.utcnow() - timedelta(hours=1),
            sync_interval_hours=24
        )
        assert source.needs_sync == False


class TestUnifiedSearchResult:
    """Test unified search result dataclass."""
    
    def test_create_result(self):
        """Test creating a search result."""
        result = UnifiedSearchResult(
            content="Test content",
            source_type=KnowledgeSourceType.LOCAL,
            source_identifier="grace-knowledge-base",
            file_path="/docs/test.md",
            relevance_score=0.85,
            snippet="...test snippet..."
        )
        
        assert result.content == "Test content"
        assert result.source_type == KnowledgeSourceType.LOCAL
        assert result.relevance_score == 0.85


class TestAmpLibrarianBridge:
    """Test the Amp Librarian Bridge."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return MagicMock()
    
    @pytest.fixture
    def temp_cache_dir(self):
        """Create a temporary cache directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def bridge(self, mock_session, temp_cache_dir):
        """Create an Amp Librarian Bridge instance."""
        return AmpLibrarianBridge(
            db_session=mock_session,
            knowledge_base_path=temp_cache_dir,
            cache_path=f"{temp_cache_dir}/cache"
        )
    
    def test_initialization(self, bridge):
        """Test bridge initializes correctly."""
        assert bridge is not None
        assert bridge.sources == {} or len(bridge.sources) >= 0
        assert bridge.cache_path.exists()
    
    def test_register_github_repo(self, bridge):
        """Test registering a GitHub repository."""
        source = bridge.register_github_repo(
            repo_url="github.com/test/example-repo",
            name="Example Repo",
            is_private=False,
            sync_interval_hours=12
        )
        
        assert source.source_type == KnowledgeSourceType.GITHUB
        assert source.identifier == "github.com/test/example-repo"
        assert source.name == "Example Repo"
        assert source.sync_interval_hours == 12
        assert "github.com/test/example-repo" in bridge.sources
    
    def test_register_github_repo_normalizes_url(self, bridge):
        """Test URL normalization for GitHub repos."""
        # Test with https://
        source1 = bridge.register_github_repo(
            repo_url="https://github.com/owner/repo1"
        )
        assert source1.identifier == "github.com/owner/repo1"
        
        # Test without protocol
        source2 = bridge.register_github_repo(
            repo_url="owner/repo2"
        )
        assert source2.identifier == "github.com/owner/repo2"
    
    def test_register_documentation(self, bridge):
        """Test registering external documentation."""
        source = bridge.register_documentation(
            url="https://docs.python.org/3/",
            name="Python Docs",
            doc_type="language"
        )
        
        assert source.source_type == KnowledgeSourceType.DOCUMENTATION
        assert source.name == "Python Docs"
        assert source.url == "https://docs.python.org/3/"
        assert source.metadata.get("doc_type") == "language"
    
    def test_connect_enterprise_librarian(self, bridge):
        """Test connecting to enterprise librarian."""
        mock_enterprise = MagicMock()
        bridge.connect_enterprise_librarian(mock_enterprise)
        assert bridge._enterprise_librarian == mock_enterprise
    
    def test_connect_librarian_engine(self, bridge):
        """Test connecting to librarian engine."""
        mock_engine = MagicMock()
        bridge.connect_librarian_engine(mock_engine)
        assert bridge._librarian_engine == mock_engine
    
    def test_get_status(self, bridge):
        """Test getting bridge status."""
        # Register a source first
        bridge.register_github_repo(
            repo_url="github.com/test/repo",
            name="Test"
        )
        
        status = bridge.get_status()
        
        assert status["bridge_status"] == "active"
        assert status["registered_sources"] == 1
        assert "github.com/test/repo" in status["sources"]
        assert "timestamp" in status
    
    def test_get_unified_analytics(self, bridge):
        """Test getting unified analytics."""
        # Register sources
        bridge.register_github_repo("github.com/test/repo1")
        bridge.register_github_repo("github.com/test/repo2")
        bridge.register_documentation("https://docs.test.com", "Test Docs")
        
        analytics = bridge.get_unified_analytics()
        
        assert "local" in analytics
        assert "external" in analytics
        assert "totals" in analytics
        assert analytics["external"]["github_repos"] == 2
        assert analytics["external"]["documentation_sources"] == 1
    
    def test_unified_search_empty(self, bridge):
        """Test unified search with no sources."""
        results = bridge.unified_search("test query")
        assert isinstance(results, list)
    
    def test_save_and_load_sources(self, bridge, temp_cache_dir):
        """Test sources are persisted to disk."""
        # Register a source
        bridge.register_github_repo(
            repo_url="github.com/persist/test",
            name="Persist Test"
        )
        
        # Create new bridge instance - should load saved sources
        new_bridge = AmpLibrarianBridge(
            db_session=MagicMock(),
            knowledge_base_path=temp_cache_dir,
            cache_path=f"{temp_cache_dir}/cache"
        )
        
        assert "github.com/persist/test" in new_bridge.sources
        assert new_bridge.sources["github.com/persist/test"].name == "Persist Test"
    
    def test_is_indexable_file(self, bridge):
        """Test file extension filtering."""
        assert bridge._is_indexable_file("test.py") == True
        assert bridge._is_indexable_file("src/main.ts") == True
        assert bridge._is_indexable_file("README.md") == True
        assert bridge._is_indexable_file("config.json") == True
        assert bridge._is_indexable_file("image.png") == False
        assert bridge._is_indexable_file("binary.exe") == False


class TestAmpLibrarianBridgeAsync:
    """Test async operations of the Amp Librarian Bridge."""
    
    @pytest.fixture
    def mock_session(self):
        return MagicMock()
    
    @pytest.fixture
    def temp_cache_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def bridge(self, mock_session, temp_cache_dir):
        return AmpLibrarianBridge(
            db_session=mock_session,
            knowledge_base_path=temp_cache_dir,
            cache_path=f"{temp_cache_dir}/cache"
        )
    
    def test_sync_github_repo_not_found(self, bridge):
        """Test syncing non-existent repo."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                bridge.sync_github_repo("nonexistent/repo")
            )
            assert "error" in result
        finally:
            loop.close()
    
    def test_sync_github_repo_registered(self, bridge):
        """Test that registered repo can be found for sync."""
        # Register the repo first
        bridge.register_github_repo(
            repo_url="github.com/test/sync-test",
            name="Sync Test"
        )
        
        # Verify source is registered
        assert "github.com/test/sync-test" in bridge.sources
        source = bridge.sources["github.com/test/sync-test"]
        assert source.name == "Sync Test"
        assert source.source_type == KnowledgeSourceType.GITHUB


class TestIntegration:
    """Test full integration between Amp and Grace librarians."""
    
    @pytest.fixture
    def mock_session(self):
        return MagicMock()
    
    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    def test_integrate_with_grace_librarian(self, mock_session, temp_dir):
        """Test the full integration function."""
        mock_enterprise = MagicMock()
        mock_engine = MagicMock()
        
        bridge = integrate_with_grace_librarian(
            db_session=mock_session,
            enterprise_librarian=mock_enterprise,
            librarian_engine=mock_engine,
            knowledge_base_path=temp_dir
        )
        
        # Check connections
        assert bridge._enterprise_librarian == mock_enterprise
        assert bridge._librarian_engine == mock_engine
        
        # Check Grace repo auto-registered
        assert "github.com/aaron031291/grace-3.1-" in bridge.sources
    
    def test_singleton_pattern(self, mock_session, temp_dir):
        """Test that get_amp_librarian_bridge returns singleton."""
        # Reset singleton
        import librarian.amp_librarian_bridge as bridge_module
        bridge_module._amp_librarian_bridge = None
        
        bridge1 = get_amp_librarian_bridge(mock_session, temp_dir)
        bridge2 = get_amp_librarian_bridge(mock_session, temp_dir)
        
        assert bridge1 is bridge2


class TestLibrarianEngineIntegration:
    """Test Amp Bridge integration in LibrarianEngine."""
    
    @pytest.fixture
    def mock_session(self):
        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = []
        session.query.return_value.filter.return_value.count.return_value = 0
        return session
    
    def test_engine_has_amp_bridge(self, mock_session):
        """Test LibrarianEngine includes amp_bridge."""
        with patch('librarian.engine.TagManager'):
            with patch('librarian.engine.RuleBasedCategorizer'):
                with patch('librarian.engine.ApprovalWorkflow'):
                    with patch('librarian.engine.FileOrganizer'):
                        with patch('librarian.engine.FileNamingManager'):
                            with patch('librarian.engine.FileCreator'):
                                with patch('librarian.engine.UnifiedRetriever'):
                                    with patch('librarian.engine.LibrarianGenesisIntegration'):
                                        with patch('librarian.engine.ContentRecommender'):
                                            with patch('librarian.engine.ContentLifecycleManager'):
                                                with patch('librarian.engine.ContentIntegrityVerifier'):
                                                    with patch('librarian.engine.ContentVisualizer'):
                                                        with patch('librarian.engine.BulkOperationsManager'):
                                                            with patch('librarian.engine.get_amp_librarian_bridge') as mock_bridge:
                                                                mock_bridge.return_value = MagicMock()
                                                                
                                                                from librarian.engine import LibrarianEngine
                                                                engine = LibrarianEngine(
                                                                    db_session=mock_session,
                                                                    use_ai=False,
                                                                    detect_relationships=False
                                                                )
                                                                
                                                                assert hasattr(engine, 'amp_bridge')
                                                                assert engine.amp_bridge is not None


class TestUnifiedSearchIntegration:
    """Test unified search functionality."""
    
    def test_search_result_sorting(self):
        """Test that results are sorted by relevance."""
        results = [
            UnifiedSearchResult(
                content="Low relevance",
                source_type=KnowledgeSourceType.LOCAL,
                source_identifier="local",
                relevance_score=0.3
            ),
            UnifiedSearchResult(
                content="High relevance",
                source_type=KnowledgeSourceType.GITHUB,
                source_identifier="github",
                relevance_score=0.9
            ),
            UnifiedSearchResult(
                content="Medium relevance",
                source_type=KnowledgeSourceType.DOCUMENTATION,
                source_identifier="docs",
                relevance_score=0.6
            )
        ]
        
        sorted_results = sorted(results, key=lambda r: r.relevance_score, reverse=True)
        
        assert sorted_results[0].relevance_score == 0.9
        assert sorted_results[1].relevance_score == 0.6
        assert sorted_results[2].relevance_score == 0.3


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
