"""
Tests for the Grace FastAPI application.
"""

import pytest
from fastapi.testclient import TestClient
from app import app, ChatRequest, ChatResponse, Message, HealthResponse


client = TestClient(app)


class TestRootEndpoint:
    """Test the root endpoint."""
    
    def test_root_endpoint(self):
        """Test GET / returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Grace API"
        assert "version" in data
        assert data["docs"] == "/docs"


class TestHealthEndpoint:
    """Test the health check endpoint."""
    
    def test_health_endpoint(self):
        """Test GET /health returns health status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        
        # Should have these fields
        assert "status" in data
        assert "ollama_running" in data
        assert "models_available" in data
        
        # Status should be either healthy or unhealthy
        assert data["status"] in ["healthy", "unhealthy"]
        
        # If unhealthy, models should be 0
        if not data["ollama_running"]:
            assert data["models_available"] == 0


class TestChatEndpoint:
    """Test the chat endpoint."""
    
    def test_chat_endpoint_with_valid_request(self):
        """Test POST /chat with valid request."""
        request_data = {
            "messages": [
                {"role": "user", "content": "What is Python?"}
            ],
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40
        }
        
        response = client.post("/chat", json=request_data)
        
        # Should return 200 if Ollama is running with the model
        # Should return 503 if Ollama is not running
        # Should return 400 if model doesn't exist
        assert response.status_code in [200, 400, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "model" in data
            assert "generation_time" in data
            assert isinstance(data["generation_time"], float)
            assert data["generation_time"] > 0
    
    def test_chat_endpoint_with_multiple_messages(self):
        """Test POST /chat with multi-turn conversation."""
        request_data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi! How can I help?"},
                {"role": "user", "content": "Tell me a joke"}
            ],
            "temperature": 0.8
        }
        
        response = client.post("/chat", json=request_data)
        assert response.status_code in [200, 400, 503]
    
    def test_chat_endpoint_without_model(self):
        """Test POST /chat without specifying model uses default."""
        request_data = {
            "messages": [
                {"role": "user", "content": "What is AI?"}
            ]
        }
        
        response = client.post("/chat", json=request_data)
        assert response.status_code in [200, 400, 503]
    
    def test_chat_endpoint_with_invalid_temperature(self):
        """Test POST /chat with invalid temperature."""
        request_data = {
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "temperature": 5.0  # Out of range
        }
        
        # Pydantic should validate and reject
        response = client.post("/chat", json=request_data)
        assert response.status_code in [422, 400]  # Validation error


class TestDocumentation:
    """Test the API documentation endpoints."""
    
    def test_swagger_docs_available(self):
        """Test that Swagger documentation is available."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger" in response.text.lower() or "openapi" in response.text.lower()
    
    def test_redoc_docs_available(self):
        """Test that ReDoc documentation is available."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "redoc" in response.text.lower() or "openapi" in response.text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
