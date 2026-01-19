"""
Tests for Layer 1 Integration (End-to-End Tests)

Tests the complete Layer 1 system including:
- User input processing with governance
- File upload with trust verification
- External API ingestion with enforcement
- Web scraping with verification
- Cognitive integration
- Genesis Key tracking
- Full pipeline flow
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock


# ==================== Layer 1 User Input Integration Tests ====================

@pytest.mark.integration
class TestLayer1UserInputIntegration:
    """Integration tests for Layer 1 user input processing."""

    def test_user_input_with_governance_enabled(self, client):
        """Test user input flows through governance enforcement."""
        response = client.post("/layer1/user-input", json={
            "user_input": "Hello Grace, can you help me?",
            "user_id": "integration-test-user",
            "input_type": "chat",
            "metadata": {"source": "integration_test"}
        })

        # Should succeed for valid input
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify response structure
        assert "success" in data or "status" in data or "genesis_key_id" in data

        # Should include governance info if enabled
        if "governance" in data:
            assert "action" in data["governance"], "Governance must include action"
            assert "trust_score" in data["governance"], "Governance must include trust_score"
            # Human input should be trusted
            assert data["governance"]["trust_score"] >= 0.7

    def test_user_input_different_types(self, client):
        """Test different input types are processed correctly."""
        input_types = ["chat", "command", "ui_interaction"]

        for input_type in input_types:
            response = client.post("/layer1/user-input", json={
                "user_input": f"Test {input_type} input",
                "user_id": "test-user",
                "input_type": input_type
            })
            assert response.status_code == 200, f"Input type '{input_type}' failed: {response.text}"
            data = response.json()
            # Each type should be processed successfully
            assert data is not None

    def test_user_input_with_metadata(self, client):
        """Test user input with rich metadata."""
        response = client.post("/layer1/user-input", json={
            "user_input": "Analyze this code snippet",
            "user_id": "test-user",
            "input_type": "command",
            "metadata": {
                "file_context": "main.py",
                "cursor_position": 42,
                "selection": "def hello():"
            }
        })
        assert response.status_code == 200, f"Metadata input failed: {response.text}"
        data = response.json()
        assert data is not None

    def test_user_input_empty_rejected(self, client):
        """Test empty user input is properly rejected."""
        response = client.post("/layer1/user-input", json={
            "user_input": "",
            "user_id": "test-user",
            "input_type": "chat"
        })
        # Empty input should be rejected with 422 or handled gracefully
        assert response.status_code in [200, 422], f"Unexpected status: {response.status_code}"
        if response.status_code == 422:
            data = response.json()
            assert "detail" in data or "error" in data


# ==================== Layer 1 File Upload Integration Tests ====================

@pytest.mark.integration
class TestLayer1FileUploadIntegration:
    """Integration tests for Layer 1 file upload processing."""

    def test_file_upload_basic(self, client):
        """Test basic file upload through Layer 1."""
        # Create a simple test file content
        file_content = b"# Test Python File\nprint('hello')"

        response = client.post(
            "/layer1/upload",
            files={"file": ("test.py", file_content, "text/x-python")},
            data={"user_id": "test-user"}
        )

        assert response.status_code == 200, f"File upload failed: {response.text}"
        data = response.json()
        assert data is not None

        # Verify governance is applied
        if "governance" in data:
            assert data["governance"]["trust_score"] >= 0
            assert data["governance"]["trust_score"] <= 1.0

    def test_file_upload_markdown(self, client):
        """Test markdown file upload."""
        file_content = b"# README\n\nThis is a test document."

        response = client.post(
            "/layer1/upload",
            files={"file": ("README.md", file_content, "text/markdown")},
            data={"user_id": "test-user"}
        )

        assert response.status_code == 200, f"Markdown upload failed: {response.text}"
        data = response.json()
        assert data is not None

    def test_file_upload_json(self, client):
        """Test JSON file upload."""
        file_content = b'{"name": "test", "value": 42}'

        response = client.post(
            "/layer1/upload",
            files={"file": ("config.json", file_content, "application/json")},
            data={"user_id": "test-user"}
        )

        assert response.status_code == 200, f"JSON upload failed: {response.text}"
        data = response.json()
        assert data is not None


# ==================== Layer 1 External API Integration Tests ====================

@pytest.mark.integration
class TestLayer1ExternalAPIIntegration:
    """Integration tests for Layer 1 external API ingestion."""

    def test_external_api_ingestion(self, client):
        """Test external API data ingestion with governance."""
        response = client.post("/layer1/external-api", json={
            "api_name": "GitHub",
            "api_endpoint": "/repos/test/commits",
            "api_data": {
                "commits": [
                    {"sha": "abc123", "message": "Test commit"}
                ]
            },
            "user_id": "test-user"
        })

        assert response.status_code == 200, f"External API ingestion failed: {response.text}"
        data = response.json()
        assert data is not None

        # External API should have governance enforcement
        if "governance" in data:
            # External sources should not be 100% trusted
            assert data["governance"]["trust_score"] < 1.0 or \
                   data["governance"]["source_classification"] == "human_triggered"

    def test_external_api_without_user(self, client):
        """Test external API ingestion without user (autonomous)."""
        response = client.post("/layer1/external-api", json={
            "api_name": "Monitoring",
            "api_endpoint": "/metrics",
            "api_data": {
                "cpu": 45.2,
                "memory": 78.5
            }
            # No user_id - autonomous
        })

        assert response.status_code == 200, f"Autonomous API ingestion failed: {response.text}"
        data = response.json()
        assert data is not None

    def test_external_api_different_sources(self, client):
        """Test various external API sources."""
        apis = [
            ("OpenAI", "/v1/chat/completions", {"response": "AI text"}),
            ("GitHub", "/repos/owner/repo", {"stars": 100}),
            ("Monitoring", "/health", {"status": "ok"})
        ]

        for api_name, endpoint, api_data in apis:
            response = client.post("/layer1/external-api", json={
                "api_name": api_name,
                "api_endpoint": endpoint,
                "api_data": api_data,
                "user_id": "test-user"
            })
            assert response.status_code == 200, f"API {api_name} ingestion failed: {response.text}"
            data = response.json()
            assert data is not None


# ==================== Layer 1 Web Scraping Integration Tests ====================

@pytest.mark.integration
class TestLayer1WebScrapingIntegration:
    """Integration tests for Layer 1 web scraping ingestion."""

    def test_web_scraping_ingestion(self, client):
        """Test web scraping data ingestion."""
        response = client.post("/layer1/web-scraping", json={
            "url": "https://example.com/docs",
            "html_content": "<html><body><h1>Documentation</h1></body></html>",
            "parsed_data": {
                "title": "Documentation",
                "headings": ["Documentation"]
            },
            "user_id": "test-user"
        })

        assert response.status_code == 200, f"Web scraping failed: {response.text}"
        data = response.json()
        assert data is not None

    def test_web_scraping_without_user(self, client):
        """Test autonomous web scraping."""
        response = client.post("/layer1/web-scraping", json={
            "url": "https://docs.python.org",
            "html_content": "<html><body>Python docs</body></html>",
            "parsed_data": {"content": "Python documentation"}
            # No user_id
        })

        assert response.status_code == 200, f"Autonomous web scraping failed: {response.text}"
        data = response.json()
        assert data is not None


# ==================== Layer 1 Memory/Learning Integration Tests ====================

@pytest.mark.integration
class TestLayer1MemoryIntegration:
    """Integration tests for Layer 1 memory and learning ingestion."""

    def test_memory_mesh_ingestion(self, client):
        """Test memory mesh data ingestion."""
        response = client.post("/layer1/memory-mesh", json={
            "memory_type": "knowledge_graph",
            "memory_data": {
                "entity": "Python",
                "relations": ["is_language", "has_library"]
            },
            "user_id": "test-user"
        })

        assert response.status_code == 200, f"Memory mesh ingestion failed: {response.text}"
        data = response.json()
        assert data is not None

    def test_learning_memory_ingestion(self, client):
        """Test learning memory data ingestion."""
        response = client.post("/layer1/learning-memory", json={
            "learning_type": "pattern",
            "learning_data": {
                "pattern": "error_fix",
                "success_rate": 0.95
            },
            "user_id": "test-user"
        })

        assert response.status_code == 200, f"Learning memory ingestion failed: {response.text}"
        data = response.json()
        assert data is not None


# ==================== Layer 1 Whitelist Integration Tests ====================

@pytest.mark.integration
class TestLayer1WhitelistIntegration:
    """Integration tests for Layer 1 whitelist management."""

    def test_whitelist_ingestion(self, client):
        """Test whitelist data ingestion."""
        response = client.post("/layer1/whitelist", json={
            "whitelist_type": "api",
            "whitelist_data": {
                "source": "trusted_api",
                "reason": "Verified partner"
            },
            "user_id": "admin-user"
        })

        assert response.status_code == 200, f"Whitelist ingestion failed: {response.text}"
        data = response.json()
        assert data is not None


# ==================== Layer 1 System Events Integration Tests ====================

@pytest.mark.integration
class TestLayer1SystemEventsIntegration:
    """Integration tests for Layer 1 system event processing."""

    def test_system_event_error(self, client):
        """Test error event ingestion."""
        response = client.post("/layer1/system-event", json={
            "event_type": "error",
            "event_data": {
                "error_type": "ImportError",
                "message": "Module not found",
                "traceback": "..."
            }
        })

        assert response.status_code == 200, f"Error event ingestion failed: {response.text}"
        data = response.json()
        assert data is not None

    def test_system_event_telemetry(self, client):
        """Test telemetry event ingestion."""
        response = client.post("/layer1/system-event", json={
            "event_type": "telemetry",
            "event_data": {
                "metric": "response_time",
                "value": 0.042,
                "unit": "seconds"
            }
        })

        assert response.status_code == 200, f"Telemetry event ingestion failed: {response.text}"
        data = response.json()
        assert data is not None

    def test_system_event_log(self, client):
        """Test log event ingestion."""
        response = client.post("/layer1/system-event", json={
            "event_type": "log",
            "event_data": {
                "level": "INFO",
                "message": "System started successfully"
            }
        })

        assert response.status_code == 200, f"Log event ingestion failed: {response.text}"
        data = response.json()
        assert data is not None


# ==================== Layer 1 Stats/Status Integration Tests ====================

@pytest.mark.integration
class TestLayer1StatusIntegration:
    """Integration tests for Layer 1 status and statistics."""

    def test_get_layer1_stats(self, client):
        """Test getting Layer 1 statistics."""
        response = client.get("/layer1/stats")

        assert response.status_code == 200, f"Stats endpoint failed: {response.text}"
        data = response.json()
        assert isinstance(data, dict)
        # Verify stats structure
        assert data is not None

    def test_verify_layer1_structure(self, client):
        """Test Layer 1 structure verification."""
        response = client.get("/layer1/verify")

        assert response.status_code == 200, f"Verify endpoint failed: {response.text}"
        data = response.json()
        assert data is not None


# ==================== Layer 1 Cognitive Integration Tests ====================

@pytest.mark.integration
class TestLayer1CognitiveIntegration:
    """Integration tests for Layer 1 cognitive engine integration."""

    def test_cognitive_status(self, client):
        """Test cognitive integration status."""
        response = client.get("/layer1/cognitive/status")

        assert response.status_code == 200, f"Cognitive status failed: {response.text}"
        data = response.json()
        assert isinstance(data, dict)

    def test_cognitive_decisions(self, client):
        """Test getting cognitive decisions."""
        response = client.get("/layer1/cognitive/decisions")

        assert response.status_code == 200, f"Cognitive decisions failed: {response.text}"
        data = response.json()
        assert data is not None

    def test_cognitive_active(self, client):
        """Test getting active cognitive processes."""
        response = client.get("/layer1/cognitive/active")

        assert response.status_code == 200, f"Cognitive active failed: {response.text}"
        data = response.json()
        assert data is not None


# ==================== Layer 1 Full Pipeline Tests ====================

@pytest.mark.integration
class TestLayer1FullPipeline:
    """Test complete Layer 1 pipeline from input to storage."""

    def test_full_pipeline_user_input(self, client):
        """Test complete pipeline for user input."""
        # 1. Submit user input
        response = client.post("/layer1/user-input", json={
            "user_input": "Create a function that calculates fibonacci",
            "user_id": "pipeline-test-user",
            "input_type": "command",
            "metadata": {"test": "full_pipeline"}
        })

        assert response.status_code == 200, f"Full pipeline failed: {response.text}"
        data = response.json()
        assert data is not None

        # 2. Check governance was applied
        if "governance" in data:
            assert "action" in data["governance"], "Governance must have action"
            assert "trust_score" in data["governance"], "Governance must have trust_score"
            # User input should be trusted
            assert data["governance"]["trust_score"] == 1.0 or \
                   data["governance"]["action"] == "allow"

        # 3. Check for Genesis Key (if tracking is enabled)
        # Genesis tracking should work for user input
        if "genesis_key_id" in data:
            assert data["genesis_key_id"] is not None

    def test_full_pipeline_with_governance_block(self, client):
        """Test pipeline handles governance blocks."""
        response = client.post("/layer1/user-input", json={
            "user_input": "Normal user message",
            "user_id": "test-user",
            "input_type": "chat"
        })

        assert response.status_code == 200, f"Normal input should not fail: {response.text}"
        data = response.json()
        assert data is not None

        # Should not be blocked for normal input
        if "blocked" in data:
            assert data.get("blocked") is not True, "Normal input should not be blocked"


# ==================== Layer 1 + Layer 3 Integration Tests ====================

@pytest.mark.integration
class TestLayer1Layer3Integration:
    """Test Layer 1 and Layer 3 governance integration."""

    @pytest.mark.asyncio
    async def test_governance_enforcement_on_layer1(self):
        """Test governance enforcement is called for Layer 1."""
        from governance.layer_enforcement import enforce_layer1, EnforcementAction
        
        # Test human input
        decision = await enforce_layer1(
            data="User question",
            origin="user_input",
            input_type="chat",
            user_id="test-user"
        )
        
        assert decision.action == EnforcementAction.ALLOW
        assert decision.trust_score == 1.0

    @pytest.mark.asyncio
    async def test_governance_blocks_untrusted_source(self):
        """Test governance can block untrusted sources."""
        from governance.layer_enforcement import enforce_layer1, EnforcementAction
        
        # Test completely unknown source
        decision = await enforce_layer1(
            data={"suspicious": "data"},
            origin="unknown_source_xyz",
            input_type="unknown",
            user_id=None
        )
        
        # Should have low trust and potentially block
        assert decision.trust_score < 0.7
        # Action depends on thresholds

    @pytest.mark.asyncio
    async def test_governance_tracks_kpis(self):
        """Test governance updates KPIs for Layer 1 operations."""
        from governance.layer_enforcement import LayerEnforcement
        
        enforcement = LayerEnforcement()
        initial_layer1 = enforcement.stats["layer1_enforced"]
        
        await enforcement.enforce_layer1_ingestion(
            data="test",
            origin="human",
            input_type="chat",
            user_id="user-1"
        )
        
        assert enforcement.stats["layer1_enforced"] == initial_layer1 + 1


# ==================== Layer 1 Error Handling Tests ====================

@pytest.mark.integration
class TestLayer1ErrorHandling:
    """Test error handling in Layer 1."""

    def test_invalid_input_type(self, client):
        """Test handling of invalid input type."""
        response = client.post("/layer1/user-input", json={
            "user_input": "Test message",
            "user_id": "test-user",
            "input_type": "invalid_type_xyz"
        })

        # Should handle gracefully - either accept with default type or reject
        assert response.status_code in [200, 422], f"Invalid input type handling: {response.status_code}"

    def test_missing_required_fields(self, client):
        """Test handling of missing required fields."""
        response = client.post("/layer1/user-input", json={
            # Missing user_input and user_id
        })

        # Should reject with 422 Unprocessable Entity
        assert response.status_code == 422, f"Missing fields should return 422: {response.status_code}"
        data = response.json()
        assert "detail" in data or "error" in data

    def test_empty_api_data(self, client):
        """Test handling of empty API data."""
        response = client.post("/layer1/external-api", json={
            "api_name": "TestAPI",
            "api_endpoint": "/test",
            "api_data": {}  # Empty
        })

        # Should handle empty data gracefully
        assert response.status_code in [200, 422], f"Empty API data handling: {response.status_code}"

    def test_malformed_json(self, client):
        """Test handling of malformed data."""
        response = client.post(
            "/layer1/user-input",
            content="not json at all",
            headers={"Content-Type": "application/json"}
        )

        # Should reject malformed JSON
        assert response.status_code == 422, f"Malformed JSON should return 422: {response.status_code}"


# ==================== Layer 1 Performance Tests ====================

@pytest.mark.integration
class TestLayer1Performance:
    """Performance tests for Layer 1."""

    def test_multiple_user_inputs(self, client):
        """Test processing multiple user inputs."""
        success_count = 0
        for i in range(5):
            response = client.post("/layer1/user-input", json={
                "user_input": f"Test message {i}",
                "user_id": "perf-test-user",
                "input_type": "chat"
            })
            if response.status_code == 200:
                success_count += 1

        # All inputs should succeed
        assert success_count == 5, f"Only {success_count}/5 requests succeeded"

    def test_concurrent_inputs(self, client):
        """Test handling concurrent inputs (sequential for now)."""
        responses = []
        for i in range(3):
            response = client.post("/layer1/user-input", json={
                "user_input": f"Concurrent test {i}",
                "user_id": f"user-{i}",
                "input_type": "chat"
            })
            responses.append(response.status_code)

        # All should complete successfully
        assert all(code == 200 for code in responses), f"Not all requests succeeded: {responses}"
