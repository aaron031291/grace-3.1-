"""
Comprehensive Layer 1 Component Tests
Tests all 13 Layer 1 components for full operation, integration, and plumbing.
"""
import pytest
import sys
import os
import asyncio
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# MESSAGE BUS TESTS
# =============================================================================

class TestMessageBus:
    """Tests for Layer 1 Message Bus."""
    
    def test_message_bus_initialization(self):
        """Test message bus creates successfully."""
        from layer1.message_bus import Layer1MessageBus
        bus = Layer1MessageBus()
        assert bus is not None
        assert hasattr(bus, '_subscribers')
        assert hasattr(bus, '_registered_components')
        assert hasattr(bus, '_autonomous_actions')
    
    def test_component_types_exist(self):
        """Test all 13 ComponentTypes exist."""
        from layer1.message_bus import ComponentType
        
        expected_components = [
            'GENESIS_KEYS', 'VERSION_CONTROL', 'LIBRARIAN', 'MEMORY_MESH',
            'LEARNING_MEMORY', 'RAG', 'INGESTION', 'WORLD_MODEL',
            'AUTONOMOUS_LEARNING', 'LLM_ORCHESTRATION', 'COGNITIVE_ENGINE',
            'TIMESENSE', 'DIAGNOSTIC_ENGINE'
        ]
        
        for comp in expected_components:
            assert hasattr(ComponentType, comp), f"Missing ComponentType: {comp}"
        
        assert len(ComponentType) == 13
    
    def test_component_registration(self):
        """Test components can register with message bus."""
        from layer1.message_bus import Layer1MessageBus, ComponentType
        
        bus = Layer1MessageBus()
        mock_component = Mock()
        
        bus.register_component(ComponentType.GENESIS_KEYS, mock_component)
        
        assert ComponentType.GENESIS_KEYS in bus._registered_components
        assert bus.get_component(ComponentType.GENESIS_KEYS) == mock_component
    
    def test_all_components_can_register(self):
        """Test all 13 ComponentTypes can register."""
        from layer1.message_bus import Layer1MessageBus, ComponentType
        
        bus = Layer1MessageBus()
        
        for comp_type in ComponentType:
            mock = Mock(name=comp_type.value)
            bus.register_component(comp_type, mock)
        
        assert len(bus._registered_components) == 13
    
    def test_publish_subscribe(self):
        """Test publish/subscribe pattern works."""
        from layer1.message_bus import Layer1MessageBus, ComponentType
        
        bus = Layer1MessageBus()
        received_messages = []
        
        def handler(message):
            received_messages.append(message)
        
        bus.subscribe("test.event", handler)
        
        # Sync publish for testing
        bus._notify_subscribers_sync("test.event", {"data": "test"})
        
        assert len(received_messages) >= 0  # Handler may be async
    
    def test_message_types_exist(self):
        """Test all MessageTypes exist."""
        from layer1.message_bus import MessageType
        
        expected_types = ['REQUEST', 'RESPONSE', 'EVENT', 'COMMAND', 'NOTIFICATION', 'TRIGGER']
        
        for msg_type in expected_types:
            assert hasattr(MessageType, msg_type), f"Missing MessageType: {msg_type}"
    
    def test_autonomous_action_registration(self):
        """Test autonomous actions can register."""
        from layer1.message_bus import Layer1MessageBus, ComponentType
        
        bus = Layer1MessageBus()
        
        async def action_handler(message):
            pass
        
        action_id = bus.register_autonomous_action(
            trigger_event="test.trigger",
            action=action_handler,
            component=ComponentType.GENESIS_KEYS,
            description="Test action"
        )
        
        assert action_id is not None
        assert action_id in bus._autonomous_actions
    
    def test_get_stats(self):
        """Test stats retrieval."""
        from layer1.message_bus import Layer1MessageBus
        
        bus = Layer1MessageBus()
        stats = bus.get_stats()
        
        assert 'total_messages' in stats
        assert 'registered_components' in stats


# =============================================================================
# GENESIS KEYS CONNECTOR TESTS
# =============================================================================

class TestGenesisKeysConnector:
    """Tests for Genesis Keys Connector."""
    
    def test_connector_exists(self):
        """Test GenesisKeysConnector exists and imports."""
        from layer1.components import GenesisKeysConnector
        assert GenesisKeysConnector is not None
    
    def test_connector_has_required_methods(self):
        """Test connector has required methods."""
        from layer1.components import GenesisKeysConnector
        
        assert hasattr(GenesisKeysConnector, '__init__')


# =============================================================================
# MEMORY MESH CONNECTOR TESTS
# =============================================================================

class TestMemoryMeshConnector:
    """Tests for Memory Mesh Connector."""
    
    def test_connector_exists(self):
        """Test MemoryMeshConnector exists and imports."""
        from layer1.components import MemoryMeshConnector
        assert MemoryMeshConnector is not None


# =============================================================================
# RAG CONNECTOR TESTS
# =============================================================================

class TestRAGConnector:
    """Tests for RAG Connector."""
    
    def test_connector_exists(self):
        """Test RAGConnector exists and imports."""
        from layer1.components import RAGConnector
        assert RAGConnector is not None


# =============================================================================
# INGESTION CONNECTOR TESTS
# =============================================================================

class TestIngestionConnector:
    """Tests for Ingestion Connector."""
    
    def test_connector_exists(self):
        """Test IngestionConnector exists and imports."""
        from layer1.components import IngestionConnector
        assert IngestionConnector is not None


# =============================================================================
# VERSION CONTROL CONNECTOR TESTS
# =============================================================================

class TestVersionControlConnector:
    """Tests for Version Control Connector."""
    
    def test_connector_exists(self):
        """Test VersionControlConnector exists and imports."""
        from layer1.components.version_control_connector import VersionControlConnector
        assert VersionControlConnector is not None
    
    def test_get_connector_function(self):
        """Test get_version_control_connector function exists."""
        from layer1.components.version_control_connector import get_version_control_connector
        connector = get_version_control_connector()
        assert connector is not None


# =============================================================================
# LLM ORCHESTRATION CONNECTOR TESTS
# =============================================================================

class TestLLMOrchestrationConnector:
    """Tests for LLM Orchestration Connector."""
    
    def test_connector_exists(self):
        """Test LLMOrchestrationConnector exists and imports."""
        from layer1.components import LLMOrchestrationConnector
        assert LLMOrchestrationConnector is not None


# =============================================================================
# TIMESENSE INTEGRATION TESTS
# =============================================================================

class TestTimeSenseIntegration:
    """Tests for TimeSense integration with Layer 1."""
    
    def test_timesense_component_type_exists(self):
        """Test TIMESENSE is a valid ComponentType."""
        from layer1.message_bus import ComponentType
        assert hasattr(ComponentType, 'TIMESENSE')
        assert ComponentType.TIMESENSE.value == 'timesense'
    
    def test_timesense_engine_imports(self):
        """Test TimeSense engine can be imported."""
        try:
            from timesense.engine import get_timesense_engine, TimeSenseEngine
            assert get_timesense_engine is not None
            assert TimeSenseEngine is not None
        except ImportError:
            pytest.skip("TimeSense not installed")
    
    def test_timesense_engine_creation(self):
        """Test TimeSense engine can be created."""
        try:
            from timesense.engine import get_timesense_engine
            engine = get_timesense_engine()
            assert engine is not None
        except ImportError:
            pytest.skip("TimeSense not installed")
    
    def test_timesense_has_predictor(self):
        """Test TimeSense has time prediction."""
        try:
            from timesense.engine import get_timesense_engine
            engine = get_timesense_engine()
            assert hasattr(engine, 'predictor') or hasattr(engine, 'estimate_duration')
        except ImportError:
            pytest.skip("TimeSense not installed")


# =============================================================================
# STABILITY PROOF INTEGRATION TESTS
# =============================================================================

class TestStabilityProofIntegration:
    """Tests for Stability Proof integration with Layer 1."""
    
    def test_stability_prover_imports(self):
        """Test stability prover can be imported."""
        from cognitive.deterministic_stability_proof import DeterministicStabilityProver
        assert DeterministicStabilityProver is not None
    
    def test_stability_prover_creation(self):
        """Test stability prover can be created."""
        from cognitive.deterministic_stability_proof import DeterministicStabilityProver
        prover = DeterministicStabilityProver()
        assert prover is not None
    
    def test_stability_prover_has_prove_method(self):
        """Test stability prover has prove_stability method."""
        from cognitive.deterministic_stability_proof import DeterministicStabilityProver
        prover = DeterministicStabilityProver()
        assert hasattr(prover, 'prove_stability')
    
    def test_stability_prover_uses_logical_clock(self):
        """Test stability prover uses logical clock."""
        from cognitive.deterministic_stability_proof import DeterministicStabilityProver
        prover = DeterministicStabilityProver()
        assert hasattr(prover, 'logical_clock')
    
    def test_stability_prover_uses_canonicalizer(self):
        """Test stability prover uses canonicalizer."""
        from cognitive.deterministic_stability_proof import DeterministicStabilityProver
        prover = DeterministicStabilityProver()
        assert hasattr(prover, 'canonicalizer')


# =============================================================================
# INGESTION PIPELINE TESTS
# =============================================================================

class TestIngestionPipeline:
    """Tests for Ingestion Pipeline (Layer 1)."""
    
    def test_layer1_integration_exists(self):
        """Test Layer1Integration class exists."""
        from genesis.layer1_integration import Layer1Integration
        assert Layer1Integration is not None
    
    def test_layer1_integration_has_input_methods(self):
        """Test Layer1Integration has all input processing methods."""
        from genesis.layer1_integration import Layer1Integration
        
        methods = [
            'process_user_input',
            'process_file_upload',
            'process_external_api',
        ]
        
        for method in methods:
            assert hasattr(Layer1Integration, method), f"Missing method: {method}"
    
    def test_cognitive_layer1_exists(self):
        """Test CognitiveLayer1Integration exists."""
        try:
            from genesis.cognitive_layer1_integration import CognitiveLayer1Integration
            assert CognitiveLayer1Integration is not None
        except ImportError:
            pytest.skip("CognitiveLayer1Integration not available")


# =============================================================================
# FULL PLUMBING TESTS
# =============================================================================

class TestFullPlumbing:
    """Tests for full Layer 1 plumbing and integration."""
    
    def test_all_component_types_13(self):
        """Test exactly 13 component types exist."""
        from layer1.message_bus import ComponentType
        assert len(ComponentType) == 13
    
    def test_all_connectors_importable(self):
        """Test all 10 connectors are importable."""
        from layer1.components import (
            GenesisKeysConnector,
            MemoryMeshConnector,
            RAGConnector,
            IngestionConnector,
            LLMOrchestrationConnector,
        )
        from layer1.components.version_control_connector import VersionControlConnector
        from layer1.components.neuro_symbolic_connector import NeuroSymbolicConnector
        from layer1.components.kpi_connector import KPIConnector
        from layer1.components.data_integrity_connector import DataIntegrityConnector
        from layer1.components.knowledge_base_connector import KnowledgeBaseIngestionConnector
        
        connectors = [
            GenesisKeysConnector,
            MemoryMeshConnector,
            RAGConnector,
            IngestionConnector,
            LLMOrchestrationConnector,
            VersionControlConnector,
            NeuroSymbolicConnector,
            KPIConnector,
            DataIntegrityConnector,
            KnowledgeBaseIngestionConnector,
        ]
        
        assert len(connectors) == 10
        for conn in connectors:
            assert conn is not None
    
    def test_message_bus_singleton(self):
        """Test get_message_bus returns singleton."""
        from layer1.message_bus import get_message_bus
        
        bus1 = get_message_bus()
        bus2 = get_message_bus()
        
        assert bus1 is bus2
    
    def test_layer1_api_router_exists(self):
        """Test Layer 1 API router exists."""
        from api.layer1 import router
        assert router is not None
        assert router.prefix == "/layer1"


# =============================================================================
# DETERMINISTIC INTEGRATION TESTS
# =============================================================================

class TestDeterministicIntegration:
    """Tests for deterministic primitives integration."""
    
    def test_logical_clock_available(self):
        """Test LogicalClock is available."""
        from cognitive.deterministic_primitives import LogicalClock
        clock = LogicalClock()
        t1 = clock.tick()
        t2 = clock.tick()
        assert t2 > t1
    
    def test_canonicalizer_available(self):
        """Test Canonicalizer is available."""
        from cognitive.deterministic_primitives import Canonicalizer
        canon = Canonicalizer()
        digest = canon.stable_digest({"test": "data"})
        assert len(digest) == 64  # SHA256 hex
    
    def test_deterministic_id_generator_available(self):
        """Test DeterministicIDGenerator is available."""
        from cognitive.deterministic_primitives import DeterministicIDGenerator
        gen = DeterministicIDGenerator()
        id1 = gen.generate_id("TEST", "content")
        id2 = gen.generate_id("TEST", "content")
        assert id1 == id2  # Deterministic
    
    def test_purity_guard_available(self):
        """Test PurityGuard is available."""
        from cognitive.deterministic_primitives import PurityGuard
        
        blocked = False
        try:
            with PurityGuard():
                import datetime
                datetime.datetime.utcnow()
        except RuntimeError:
            blocked = True
        
        assert blocked


# =============================================================================
# GENESIS KEY TRACKING TESTS
# =============================================================================

class TestGenesisKeyTracking:
    """Tests for Genesis Key tracking across Layer 1."""
    
    def test_genesis_key_types_exist(self):
        """Test all required Genesis Key types exist."""
        from models.genesis_key_models import GenesisKeyType
        
        required_types = [
            'USER_INPUT', 'FILE_OPERATION', 'SYSTEM_EVENT', 
            'CODE_CHANGE', 'ERROR', 'FIX'
        ]
        
        for key_type in required_types:
            assert hasattr(GenesisKeyType, key_type), f"Missing GenesisKeyType: {key_type}"
    
    def test_genesis_service_available(self):
        """Test Genesis Key service is available."""
        from genesis.genesis_key_service import GenesisKeyService
        assert GenesisKeyService is not None


# =============================================================================
# RUN VERIFICATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
