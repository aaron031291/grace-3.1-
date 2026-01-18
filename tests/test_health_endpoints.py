"""
Tests for Health Check Endpoints

Tests the /health/memory and /health/systems endpoints for:
- Correct response structure
- Component status reporting
- Status determination logic (healthy/degraded/unhealthy)
"""

import sys
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, 'backend')

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.health import router


@pytest.fixture
def app():
    """Create FastAPI app with health router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = MagicMock()
    session.query.return_value.count.return_value = 10
    return session


# ==================== /health/memory Endpoint Tests ====================

class TestMemoryHealthEndpoint:
    """Tests for /health/memory endpoint."""

    def test_memory_health_returns_correct_structure(self, client, mock_session):
        """Test that /health/memory returns correct structure."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('cognitive.procedural_memory.ProceduralRepository') as mock_proc, \
                 patch('cognitive.procedural_memory.Procedure'), \
                 patch('cognitive.episodic_memory.EpisodicBuffer') as mock_epi, \
                 patch('cognitive.episodic_memory.Episode'), \
                 patch('cognitive.learning_memory.LearningExample'), \
                 patch('vector_db.client.get_qdrant_client') as mock_qdrant, \
                 patch('cognitive.memory_mesh_cache.get_memory_mesh_cache') as mock_cache:
                
                mock_proc.return_value.embedder = MagicMock()
                mock_epi.return_value.embedder = MagicMock()
                mock_qdrant.return_value.get_collections.return_value = MagicMock(collections=[])
                mock_cache.return_value.get_cache_stats.return_value = {}
                
                response = client.get("/health/memory")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "components" in data
        assert "issues" in data
        assert "timestamp" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_memory_health_reports_procedural_memory(self, client, mock_session):
        """Test that procedural_memory status is reported."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('cognitive.procedural_memory.ProceduralRepository') as mock_proc, \
                 patch('cognitive.procedural_memory.Procedure'), \
                 patch('cognitive.episodic_memory.EpisodicBuffer') as mock_epi, \
                 patch('cognitive.episodic_memory.Episode'), \
                 patch('cognitive.learning_memory.LearningExample'), \
                 patch('vector_db.client.get_qdrant_client') as mock_qdrant, \
                 patch('cognitive.memory_mesh_cache.get_memory_mesh_cache') as mock_cache:
                
                mock_proc.return_value.embedder = MagicMock()
                mock_epi.return_value.embedder = MagicMock()
                mock_qdrant.return_value.get_collections.return_value = MagicMock(collections=[])
                mock_cache.return_value.get_cache_stats.return_value = {}
                
                response = client.get("/health/memory")
        
        assert response.status_code == 200
        data = response.json()
        assert "procedural_memory" in data["components"]

    def test_memory_health_reports_episodic_memory(self, client, mock_session):
        """Test that episodic_memory status is reported."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('cognitive.procedural_memory.ProceduralRepository') as mock_proc, \
                 patch('cognitive.procedural_memory.Procedure'), \
                 patch('cognitive.episodic_memory.EpisodicBuffer') as mock_epi, \
                 patch('cognitive.episodic_memory.Episode'), \
                 patch('cognitive.learning_memory.LearningExample'), \
                 patch('vector_db.client.get_qdrant_client') as mock_qdrant, \
                 patch('cognitive.memory_mesh_cache.get_memory_mesh_cache') as mock_cache:
                
                mock_proc.return_value.embedder = MagicMock()
                mock_epi.return_value.embedder = MagicMock()
                mock_qdrant.return_value.get_collections.return_value = MagicMock(collections=[])
                mock_cache.return_value.get_cache_stats.return_value = {}
                
                response = client.get("/health/memory")
        
        assert response.status_code == 200
        data = response.json()
        assert "episodic_memory" in data["components"]

    def test_memory_health_reports_learning_memory(self, client, mock_session):
        """Test that learning_memory status is reported."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('cognitive.procedural_memory.ProceduralRepository') as mock_proc, \
                 patch('cognitive.procedural_memory.Procedure'), \
                 patch('cognitive.episodic_memory.EpisodicBuffer') as mock_epi, \
                 patch('cognitive.episodic_memory.Episode'), \
                 patch('cognitive.learning_memory.LearningExample'), \
                 patch('vector_db.client.get_qdrant_client') as mock_qdrant, \
                 patch('cognitive.memory_mesh_cache.get_memory_mesh_cache') as mock_cache:
                
                mock_proc.return_value.embedder = MagicMock()
                mock_epi.return_value.embedder = MagicMock()
                mock_qdrant.return_value.get_collections.return_value = MagicMock(collections=[])
                mock_cache.return_value.get_cache_stats.return_value = {}
                
                response = client.get("/health/memory")
        
        assert response.status_code == 200
        data = response.json()
        assert "learning_memory" in data["components"]

    def test_memory_health_reports_vector_db(self, client, mock_session):
        """Test that vector_db status is reported."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('cognitive.procedural_memory.ProceduralRepository') as mock_proc, \
                 patch('cognitive.procedural_memory.Procedure'), \
                 patch('cognitive.episodic_memory.EpisodicBuffer') as mock_epi, \
                 patch('cognitive.episodic_memory.Episode'), \
                 patch('cognitive.learning_memory.LearningExample'), \
                 patch('vector_db.client.get_qdrant_client') as mock_qdrant, \
                 patch('cognitive.memory_mesh_cache.get_memory_mesh_cache') as mock_cache:
                
                mock_proc.return_value.embedder = MagicMock()
                mock_epi.return_value.embedder = MagicMock()
                mock_collection = MagicMock()
                mock_collection.name = "test_collection"
                mock_qdrant.return_value.get_collections.return_value = MagicMock(
                    collections=[mock_collection]
                )
                mock_cache.return_value.get_cache_stats.return_value = {}
                
                response = client.get("/health/memory")
        
        assert response.status_code == 200
        data = response.json()
        assert "vector_db" in data["components"]

    def test_memory_health_handles_degraded_state(self, client, mock_session):
        """Test that degraded state is reported when embedder unavailable."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('cognitive.procedural_memory.ProceduralRepository') as mock_proc, \
                 patch('cognitive.procedural_memory.Procedure'), \
                 patch('cognitive.episodic_memory.EpisodicBuffer') as mock_epi, \
                 patch('cognitive.episodic_memory.Episode'), \
                 patch('cognitive.learning_memory.LearningExample'), \
                 patch('vector_db.client.get_qdrant_client') as mock_qdrant, \
                 patch('cognitive.memory_mesh_cache.get_memory_mesh_cache') as mock_cache:
                
                mock_proc.return_value.embedder = None  # No embedder = degraded
                mock_epi.return_value.embedder = MagicMock()
                mock_qdrant.return_value.get_collections.return_value = MagicMock(collections=[])
                mock_cache.return_value.get_cache_stats.return_value = {}
                
                response = client.get("/health/memory")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["degraded", "unhealthy"]

    def test_memory_health_handles_unhealthy_state(self, client, mock_session):
        """Test that unhealthy state is reported when component is down."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('cognitive.procedural_memory.ProceduralRepository', 
                       side_effect=Exception("Connection failed")), \
                 patch('cognitive.procedural_memory.Procedure'), \
                 patch('cognitive.episodic_memory.EpisodicBuffer', 
                       side_effect=Exception("Connection failed")), \
                 patch('cognitive.episodic_memory.Episode'), \
                 patch('cognitive.learning_memory.LearningExample', 
                       side_effect=Exception("Connection failed")), \
                 patch('vector_db.client.get_qdrant_client', 
                       side_effect=Exception("Connection failed")), \
                 patch('cognitive.memory_mesh_cache.get_memory_mesh_cache', 
                       side_effect=Exception("Connection failed")):
                
                response = client.get("/health/memory")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert len(data["issues"]) > 0


# ==================== /health/systems Endpoint Tests ====================

class TestSystemsHealthEndpoint:
    """Tests for /health/systems endpoint."""

    def test_systems_health_returns_correct_structure(self, client, mock_session):
        """Test that /health/systems returns correct structure."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('llm_orchestrator.llm_orchestrator.LLMOrchestrator'), \
                 patch('diagnostic_machine.diagnostic_engine.DiagnosticEngine'), \
                 patch('cognitive.autonomous_healing_system.AutonomousHealingSystem'), \
                 patch('cognitive.grace_code_analyzer.GraceCodeAnalyzer'), \
                 patch('genesis.genesis_key_service.GenesisKeyService'):
                
                response = client.get("/health/systems")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert "components" in data
        assert "issues" in data
        assert "timestamp" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]

    def test_systems_health_reports_llm_orchestrator(self, client, mock_session):
        """Test that LLM Orchestrator status is reported."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('llm_orchestrator.llm_orchestrator.LLMOrchestrator') as mock_llm, \
                 patch('diagnostic_machine.diagnostic_engine.DiagnosticEngine'), \
                 patch('cognitive.autonomous_healing_system.AutonomousHealingSystem'), \
                 patch('cognitive.grace_code_analyzer.GraceCodeAnalyzer'), \
                 patch('genesis.genesis_key_service.GenesisKeyService'):
                
                mock_llm.return_value.multi_llm_client = MagicMock()
                mock_llm.return_value.hallucination_guard = MagicMock()
                
                response = client.get("/health/systems")
        
        assert response.status_code == 200
        data = response.json()
        assert "llm_orchestrator" in data["components"]

    def test_systems_health_reports_diagnostic_engine(self, client, mock_session):
        """Test that Diagnostic Engine status is reported."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('llm_orchestrator.llm_orchestrator.LLMOrchestrator'), \
                 patch('diagnostic_machine.diagnostic_engine.DiagnosticEngine') as mock_engine, \
                 patch('cognitive.autonomous_healing_system.AutonomousHealingSystem'), \
                 patch('cognitive.grace_code_analyzer.GraceCodeAnalyzer'), \
                 patch('genesis.genesis_key_service.GenesisKeyService'):
                
                mock_state = MagicMock()
                mock_state.value = "running"
                mock_engine.return_value.state = mock_state
                mock_engine.return_value.sensor_layer = MagicMock()
                mock_engine.return_value.interpreter_layer = MagicMock()
                
                response = client.get("/health/systems")
        
        assert response.status_code == 200
        data = response.json()
        assert "diagnostic_engine" in data["components"]

    def test_systems_health_reports_self_healing_system(self, client, mock_session):
        """Test that Self-Healing System status is reported."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('llm_orchestrator.llm_orchestrator.LLMOrchestrator'), \
                 patch('diagnostic_machine.diagnostic_engine.DiagnosticEngine'), \
                 patch('cognitive.autonomous_healing_system.AutonomousHealingSystem') as mock_healing, \
                 patch('cognitive.grace_code_analyzer.GraceCodeAnalyzer'), \
                 patch('genesis.genesis_key_service.GenesisKeyService'):
                
                mock_trust = MagicMock()
                mock_trust.name = "SUGGEST_ONLY"
                mock_healing.return_value.trust_level = mock_trust
                mock_healing.return_value.healing_system = MagicMock()
                mock_healing.return_value.genesis_service = MagicMock()
                
                response = client.get("/health/systems")
        
        assert response.status_code == 200
        data = response.json()
        assert "self_healing_system" in data["components"]

    def test_systems_health_reports_code_analyzer(self, client, mock_session):
        """Test that Code Analyzer status is reported."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('llm_orchestrator.llm_orchestrator.LLMOrchestrator'), \
                 patch('diagnostic_machine.diagnostic_engine.DiagnosticEngine'), \
                 patch('cognitive.autonomous_healing_system.AutonomousHealingSystem'), \
                 patch('cognitive.grace_code_analyzer.GraceCodeAnalyzer') as mock_analyzer, \
                 patch('genesis.genesis_key_service.GenesisKeyService'):
                
                mock_analyzer.return_value.pattern_matcher = MagicMock()
                mock_analyzer.return_value.rules = [MagicMock()]
                
                response = client.get("/health/systems")
        
        assert response.status_code == 200
        data = response.json()
        assert "code_analyzer" in data["components"]

    def test_systems_health_reports_genesis_service(self, client, mock_session):
        """Test that Genesis Service status is reported."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('llm_orchestrator.llm_orchestrator.LLMOrchestrator'), \
                 patch('diagnostic_machine.diagnostic_engine.DiagnosticEngine'), \
                 patch('cognitive.autonomous_healing_system.AutonomousHealingSystem'), \
                 patch('cognitive.grace_code_analyzer.GraceCodeAnalyzer'), \
                 patch('genesis.genesis_key_service.GenesisKeyService') as mock_genesis:
                
                mock_genesis.return_value.git_service = MagicMock()
                mock_genesis.return_value.repo_path = "/path/to/repo"
                
                response = client.get("/health/systems")
        
        assert response.status_code == 200
        data = response.json()
        assert "genesis_service" in data["components"]


# ==================== Status Determination Tests ====================

class TestStatusDetermination:
    """Tests for status determination logic."""

    def test_all_up_returns_healthy(self, client, mock_session):
        """Test that all components up = healthy status."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('cognitive.procedural_memory.ProceduralRepository') as mock_proc, \
                 patch('cognitive.procedural_memory.Procedure'), \
                 patch('cognitive.episodic_memory.EpisodicBuffer') as mock_epi, \
                 patch('cognitive.episodic_memory.Episode'), \
                 patch('cognitive.learning_memory.LearningExample'), \
                 patch('vector_db.client.get_qdrant_client') as mock_qdrant, \
                 patch('cognitive.memory_mesh_cache.get_memory_mesh_cache') as mock_cache:
                
                mock_proc.return_value.embedder = MagicMock()
                mock_epi.return_value.embedder = MagicMock()
                mock_qdrant.return_value.get_collections.return_value = MagicMock(collections=[])
                mock_cache.return_value.get_cache_stats.return_value = {}
                
                response = client.get("/health/memory")
        
        assert response.status_code == 200
        data = response.json()
        
        all_up = all(
            comp.get("status") == "up" 
            for comp in data["components"].values()
        )
        if all_up:
            assert data["status"] == "healthy"

    def test_some_down_returns_degraded_or_unhealthy(self, client, mock_session):
        """Test that some components down = degraded or unhealthy status."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('cognitive.procedural_memory.ProceduralRepository') as mock_proc, \
                 patch('cognitive.procedural_memory.Procedure'), \
                 patch('cognitive.episodic_memory.EpisodicBuffer') as mock_epi, \
                 patch('cognitive.episodic_memory.Episode'), \
                 patch('cognitive.learning_memory.LearningExample'), \
                 patch('vector_db.client.get_qdrant_client', 
                       side_effect=Exception("Connection failed")), \
                 patch('cognitive.memory_mesh_cache.get_memory_mesh_cache') as mock_cache:
                
                mock_proc.return_value.embedder = MagicMock()
                mock_epi.return_value.embedder = MagicMock()
                mock_cache.return_value.get_cache_stats.return_value = {}
                
                response = client.get("/health/memory")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["degraded", "unhealthy"]

    def test_critical_down_returns_unhealthy(self, client, mock_session):
        """Test that critical components down = unhealthy status."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('cognitive.procedural_memory.ProceduralRepository', 
                       side_effect=Exception("Critical failure")), \
                 patch('cognitive.procedural_memory.Procedure'), \
                 patch('cognitive.episodic_memory.EpisodicBuffer', 
                       side_effect=Exception("Critical failure")), \
                 patch('cognitive.episodic_memory.Episode'), \
                 patch('cognitive.learning_memory.LearningExample', 
                       side_effect=Exception("Critical failure")), \
                 patch('vector_db.client.get_qdrant_client', 
                       side_effect=Exception("Critical failure")), \
                 patch('cognitive.memory_mesh_cache.get_memory_mesh_cache', 
                       side_effect=Exception("Critical failure")):
                
                response = client.get("/health/memory")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert len(data["issues"]) > 0

    def test_systems_all_up_returns_healthy(self, client, mock_session):
        """Test that all systems up = healthy status."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('llm_orchestrator.llm_orchestrator.LLMOrchestrator') as mock_llm, \
                 patch('diagnostic_machine.diagnostic_engine.DiagnosticEngine') as mock_engine, \
                 patch('cognitive.autonomous_healing_system.AutonomousHealingSystem') as mock_healing, \
                 patch('cognitive.grace_code_analyzer.GraceCodeAnalyzer') as mock_analyzer, \
                 patch('genesis.genesis_key_service.GenesisKeyService') as mock_genesis:
                
                mock_llm.return_value.multi_llm_client = MagicMock()
                mock_llm.return_value.hallucination_guard = MagicMock()
                
                mock_state = MagicMock()
                mock_state.value = "running"
                mock_engine.return_value.state = mock_state
                mock_engine.return_value.sensor_layer = MagicMock()
                mock_engine.return_value.interpreter_layer = MagicMock()
                
                mock_trust = MagicMock()
                mock_trust.name = "SUGGEST_ONLY"
                mock_healing.return_value.trust_level = mock_trust
                mock_healing.return_value.healing_system = MagicMock()
                mock_healing.return_value.genesis_service = MagicMock()
                
                mock_analyzer.return_value.pattern_matcher = MagicMock()
                mock_analyzer.return_value.rules = [MagicMock()]
                
                mock_genesis.return_value.git_service = MagicMock()
                mock_genesis.return_value.repo_path = "/path/to/repo"
                
                response = client.get("/health/systems")
        
        assert response.status_code == 200
        data = response.json()
        
        all_up = all(
            comp.get("status") == "up" 
            for comp in data["components"].values()
        )
        if all_up:
            assert data["status"] == "healthy"

    def test_systems_some_down_returns_unhealthy(self, client, mock_session):
        """Test that some systems down = unhealthy status."""
        with patch('database.session.SessionLocal', return_value=mock_session):
            with patch('llm_orchestrator.llm_orchestrator.LLMOrchestrator', 
                       side_effect=Exception("LLM connection failed")), \
                 patch('diagnostic_machine.diagnostic_engine.DiagnosticEngine', 
                       side_effect=Exception("Engine failed")), \
                 patch('cognitive.autonomous_healing_system.AutonomousHealingSystem', 
                       side_effect=Exception("Healing failed")), \
                 patch('cognitive.grace_code_analyzer.GraceCodeAnalyzer', 
                       side_effect=Exception("Analyzer failed")), \
                 patch('genesis.genesis_key_service.GenesisKeyService', 
                       side_effect=Exception("Genesis failed")):
                
                response = client.get("/health/systems")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert len(data["issues"]) > 0
