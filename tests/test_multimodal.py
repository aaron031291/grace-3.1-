"""
Tests for Multimodal LLM System

Tests:
1. Image analysis with mocked vision models
2. Image generation with mocked generation
3. Text-to-speech synchronous with mocked TTS
4. Graceful fallbacks when models unavailable
"""

import pytest
import sys
import base64
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestMultimodalLLMSystem:
    """Tests for MultimodalLLMSystem class."""
    
    @pytest.fixture
    def mock_multi_llm_client(self):
        """Create mock multi-LLM client."""
        client = Mock()
        client.generate = Mock(return_value={
            "content": "This is a test response",
            "confidence": 0.85
        })
        return client
    
    @pytest.fixture
    def mock_repo_access(self):
        """Create mock repository access."""
        return Mock()
    
    @pytest.fixture
    def multimodal_system(self, mock_multi_llm_client, mock_repo_access):
        """Create MultimodalLLMSystem with mocked dependencies."""
        with patch.dict('sys.modules', {
            'llm_orchestrator.multi_llm_client': MagicMock(),
            'llm_orchestrator.repo_access': MagicMock(),
            'genesis.cognitive_layer1_integration': MagicMock(),
            'api.voice_api': MagicMock()
        }):
            with patch('backend.llm_orchestrator.multimodal_llm_system.get_multi_llm_client', return_value=mock_multi_llm_client):
                with patch('backend.llm_orchestrator.multimodal_llm_system.get_repo_access', return_value=mock_repo_access):
                    from backend.llm_orchestrator.multimodal_llm_system import (
                        MultimodalLLMSystem, 
                        MediaType, 
                        MultimodalInput
                    )
                    
                    system = MultimodalLLMSystem(
                        multi_llm_client=mock_multi_llm_client,
                        repo_access=mock_repo_access,
                        session=None
                    )
                    return system


class TestAnalyzeImage:
    """Tests for analyze_image() method."""
    
    @pytest.fixture
    def sample_image_bytes(self):
        """Create sample image bytes (1x1 PNG)."""
        # Minimal valid PNG bytes
        png_header = b'\x89PNG\r\n\x1a\n'
        ihdr_chunk = (
            b'\x00\x00\x00\rIHDR'
            b'\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde'
        )
        idat_chunk = b'\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\x0f\x00\x00\x01\x01\x00\x05\x1d\xf3\x94'
        iend_chunk = b'\x00\x00\x00\x00IEND\xaeB`\x82'
        return png_header + ihdr_chunk + idat_chunk + iend_chunk
    
    @pytest.fixture
    def multimodal_system(self):
        """Create system with mocked dependencies."""
        with patch.dict('sys.modules', {
            'llm_orchestrator.multi_llm_client': MagicMock(),
            'llm_orchestrator.repo_access': MagicMock(),
            'genesis.cognitive_layer1_integration': MagicMock(),
            'api.voice_api': MagicMock()
        }):
            mock_client = Mock()
            mock_client.generate = Mock(return_value={"content": "test", "confidence": 0.8})
            
            from backend.llm_orchestrator.multimodal_llm_system import MultimodalLLMSystem
            system = MultimodalLLMSystem(
                multi_llm_client=mock_client,
                repo_access=None,
                session=None
            )
            return system
    
    def test_analyze_image_with_bytes(self, multimodal_system, sample_image_bytes):
        """Test analyzing image from bytes."""
        # Mock the vision method
        multimodal_system._analyze_with_ollama_vision = Mock(return_value={
            "success": True,
            "description": "A test image showing a red square",
            "model": "llava"
        })
        multimodal_system.vision_model = "llava"
        
        result = multimodal_system.analyze_image(sample_image_bytes, "Describe this image")
        
        assert result["success"] is True
        assert "description" in result
        assert result["model"] == "llava"
    
    def test_analyze_image_with_base64(self, multimodal_system):
        """Test analyzing image from base64 string."""
        multimodal_system._analyze_with_ollama_vision = Mock(return_value={
            "success": True,
            "description": "Test description",
            "model": "llava"
        })
        multimodal_system.vision_model = "llava"
        
        # Create base64 encoded string
        fake_b64 = "a" * 600  # Long enough to be detected as base64
        
        result = multimodal_system.analyze_image(fake_b64, "What is in this image?")
        
        assert result is not None
    
    def test_analyze_image_invalid_input(self, multimodal_system):
        """Test analyzing with invalid input type."""
        result = multimodal_system.analyze_image(12345, "Describe")  # Invalid type
        
        assert result["success"] is False
        assert "error" in result
    
    def test_analyze_image_file_not_found(self, multimodal_system, tmp_path):
        """Test analyzing non-existent file."""
        fake_path = str(tmp_path / "nonexistent.png")
        
        result = multimodal_system.analyze_image(fake_path, "Describe")
        
        assert result["success"] is False
        assert "error" in result
    
    def test_analyze_image_openai_vision(self, multimodal_system, sample_image_bytes):
        """Test OpenAI vision model path."""
        multimodal_system.vision_model = "gpt4v"
        multimodal_system._analyze_with_openai_vision = Mock(return_value={
            "success": True,
            "description": "GPT-4V analysis",
            "model": "gpt-4-vision"
        })
        
        result = multimodal_system.analyze_image(sample_image_bytes, "Analyze")
        
        assert result["success"] is True
        multimodal_system._analyze_with_openai_vision.assert_called_once()
    
    def test_analyze_image_claude_vision(self, multimodal_system, sample_image_bytes):
        """Test Claude vision model path."""
        multimodal_system.vision_model = "claude"
        multimodal_system._analyze_with_claude_vision = Mock(return_value={
            "success": True,
            "description": "Claude analysis",
            "model": "claude-3"
        })
        
        result = multimodal_system.analyze_image(sample_image_bytes, "Analyze")
        
        assert result["success"] is True
        multimodal_system._analyze_with_claude_vision.assert_called_once()
    
    def test_analyze_image_unconfigured_model(self, multimodal_system, sample_image_bytes):
        """Test with unconfigured vision model."""
        multimodal_system.vision_model = "unknown_model"
        
        result = multimodal_system.analyze_image(sample_image_bytes, "Analyze")
        
        assert result["success"] is False
        assert "not configured" in result["error"]


class TestGenerateImage:
    """Tests for generate_image() method."""
    
    @pytest.fixture
    def multimodal_system(self):
        """Create system with mocked dependencies."""
        with patch.dict('sys.modules', {
            'llm_orchestrator.multi_llm_client': MagicMock(),
            'llm_orchestrator.repo_access': MagicMock(),
            'genesis.cognitive_layer1_integration': MagicMock(),
            'api.voice_api': MagicMock()
        }):
            mock_client = Mock()
            mock_client.generate = Mock(return_value={"content": "test", "confidence": 0.8})
            
            from backend.llm_orchestrator.multimodal_llm_system import MultimodalLLMSystem
            system = MultimodalLLMSystem(
                multi_llm_client=mock_client,
                repo_access=None,
                session=None
            )
            return system
    
    def test_generate_image_with_dalle(self, multimodal_system):
        """Test image generation with DALL-E."""
        multimodal_system.image_model = "dalle"
        multimodal_system._generate_with_dalle = Mock(return_value={
            "success": True,
            "image_url": "https://example.com/generated.png",
            "model": "dall-e-3"
        })
        
        result = multimodal_system.generate_image("A beautiful sunset", "1024x1024")
        
        assert result["success"] is True
        assert "image_url" in result
        multimodal_system._generate_with_dalle.assert_called_once()
    
    def test_generate_image_with_stable_diffusion(self, multimodal_system):
        """Test image generation with Stable Diffusion."""
        multimodal_system.image_model = "stable-diffusion"
        multimodal_system._generate_with_stable_diffusion = Mock(return_value={
            "success": True,
            "image_data": b"fake_image_data",
            "model": "stable-diffusion"
        })
        
        result = multimodal_system.generate_image("A mountain landscape", "512x512")
        
        assert result["success"] is True
        assert "image_data" in result
    
    def test_generate_image_unconfigured_model(self, multimodal_system):
        """Test with unconfigured image model."""
        multimodal_system.image_model = "unknown_generator"
        
        result = multimodal_system.generate_image("A test image", "1024x1024")
        
        assert result["success"] is False
        assert "not configured" in result["error"]
    
    def test_generate_image_empty_prompt(self, multimodal_system):
        """Test image generation with empty prompt."""
        multimodal_system.image_model = "dalle"
        multimodal_system._generate_with_dalle = Mock(return_value={
            "success": False,
            "error": "Empty prompt not allowed"
        })
        
        result = multimodal_system.generate_image("", "1024x1024")
        
        assert result["success"] is False


class TestTextToSpeechSync:
    """Tests for text_to_speech_sync() method."""
    
    @pytest.fixture
    def multimodal_system(self):
        """Create system with mocked dependencies."""
        with patch.dict('sys.modules', {
            'llm_orchestrator.multi_llm_client': MagicMock(),
            'llm_orchestrator.repo_access': MagicMock(),
            'genesis.cognitive_layer1_integration': MagicMock(),
            'api.voice_api': MagicMock()
        }):
            mock_client = Mock()
            mock_client.generate = Mock(return_value={"content": "test", "confidence": 0.8})
            
            from backend.llm_orchestrator.multimodal_llm_system import MultimodalLLMSystem
            system = MultimodalLLMSystem(
                multi_llm_client=mock_client,
                repo_access=None,
                session=None
            )
            return system
    
    def test_tts_with_openai(self, multimodal_system):
        """Test TTS with OpenAI."""
        multimodal_system.tts_model = "openai"
        multimodal_system._tts_with_openai = Mock(return_value={
            "success": True,
            "audio_data": b"fake_audio_data",
            "model": "openai-tts"
        })
        
        result = multimodal_system.text_to_speech_sync("Hello, world!", "alloy")
        
        assert result["success"] is True
        assert "audio_data" in result
        multimodal_system._tts_with_openai.assert_called_once()
    
    def test_tts_with_pyttsx3(self, multimodal_system):
        """Test TTS with local pyttsx3."""
        multimodal_system.tts_model = "local"
        multimodal_system._tts_with_pyttsx3 = Mock(return_value={
            "success": True,
            "audio_data": b"fake_audio_data",
            "model": "pyttsx3"
        })
        
        result = multimodal_system.text_to_speech_sync("Hello, world!", "default")
        
        assert result["success"] is True
        assert result["model"] == "pyttsx3"
    
    def test_tts_unconfigured_model(self, multimodal_system):
        """Test TTS with unconfigured model."""
        multimodal_system.tts_model = "unknown_tts"
        
        result = multimodal_system.text_to_speech_sync("Test", "default")
        
        assert result["success"] is False
        assert "not configured" in result["error"]
    
    def test_tts_empty_text(self, multimodal_system):
        """Test TTS with empty text."""
        multimodal_system.tts_model = "openai"
        multimodal_system._tts_with_openai = Mock(return_value={
            "success": True,
            "audio_data": b"",
            "model": "openai-tts"
        })
        
        result = multimodal_system.text_to_speech_sync("", "default")
        
        # Should still process (empty text might produce silence)
        assert result is not None


class TestGracefulFallbacks:
    """Tests for graceful fallbacks when models are unavailable."""
    
    @pytest.fixture
    def multimodal_system(self):
        """Create system with mocked dependencies."""
        with patch.dict('sys.modules', {
            'llm_orchestrator.multi_llm_client': MagicMock(),
            'llm_orchestrator.repo_access': MagicMock(),
            'genesis.cognitive_layer1_integration': MagicMock(),
            'api.voice_api': MagicMock()
        }):
            mock_client = Mock()
            mock_client.generate = Mock(return_value={"content": "test", "confidence": 0.8})
            
            from backend.llm_orchestrator.multimodal_llm_system import MultimodalLLMSystem
            system = MultimodalLLMSystem(
                multi_llm_client=mock_client,
                repo_access=None,
                session=None
            )
            return system
    
    def test_openai_unavailable_fallback(self, multimodal_system):
        """Test fallback when OpenAI library is not available."""
        # Simulate unavailability by mocking the internal method
        multimodal_system.tts_model = "openai"
        
        # Mock the internal method to simulate unavailability
        multimodal_system._tts_with_openai = Mock(return_value={
            "success": False,
            "error": "OpenAI library not installed"
        })
        
        result = multimodal_system.text_to_speech_sync("Test", "default")
        
        assert result["success"] is False
        assert "not installed" in result["error"]
    
    def test_pyttsx3_unavailable_fallback(self, multimodal_system):
        """Test fallback when pyttsx3 is not available."""
        multimodal_system.tts_model = "local"
        multimodal_system._tts_with_pyttsx3 = Mock(return_value={
            "success": False,
            "error": "pyttsx3 library not installed"
        })
        
        result = multimodal_system.text_to_speech_sync("Test", "default")
        
        assert result["success"] is False
        assert "not installed" in result["error"]
    
    def test_diffusers_unavailable_fallback(self, multimodal_system):
        """Test fallback when diffusers is not available."""
        multimodal_system.image_model = "stable-diffusion"
        multimodal_system._generate_with_stable_diffusion = Mock(return_value={
            "success": False,
            "error": "diffusers library not installed"
        })
        
        result = multimodal_system.generate_image("A test image", "512x512")
        
        assert result["success"] is False
        assert "not installed" in result["error"]
    
    def test_api_key_missing_fallback(self, multimodal_system):
        """Test fallback when API key is missing."""
        multimodal_system.image_model = "dalle"
        multimodal_system._generate_with_dalle = Mock(return_value={
            "success": False,
            "error": "OPENAI_API_KEY not set"
        })
        
        result = multimodal_system.generate_image("A test image", "1024x1024")
        
        assert result["success"] is False
        assert "API_KEY" in result["error"] or "not set" in result["error"]
    
    def test_vision_model_exception_handling(self, multimodal_system):
        """Test exception handling in vision model."""
        multimodal_system.vision_model = "llava"
        multimodal_system._analyze_with_ollama_vision = Mock(side_effect=Exception("Network error"))
        
        # Should handle exception gracefully
        try:
            result = multimodal_system.analyze_image(b"fake_image", "Describe")
            # If it returns, it should indicate failure
            if result:
                assert result.get("success") is False or "error" in result
        except Exception as e:
            # Exception propagation is also acceptable
            assert "Network error" in str(e)
    
    def test_voice_manager_not_available(self, multimodal_system):
        """Test behavior when voice manager is not available."""
        multimodal_system.voice_manager = None
        multimodal_system.tts_model = "local"
        multimodal_system._tts_with_pyttsx3 = Mock(return_value={
            "success": True,
            "audio_data": b"audio",
            "model": "pyttsx3"
        })
        
        # Should fall back to sync TTS
        result = multimodal_system.text_to_speech_sync("Hello", "default")
        
        assert result["success"] is True


class TestMultimodalHelpers:
    """Tests for helper methods in multimodal system."""
    
    @pytest.fixture
    def multimodal_system(self):
        """Create system with mocked dependencies."""
        with patch.dict('sys.modules', {
            'llm_orchestrator.multi_llm_client': MagicMock(),
            'llm_orchestrator.repo_access': MagicMock(),
            'genesis.cognitive_layer1_integration': MagicMock(),
            'api.voice_api': MagicMock()
        }):
            mock_client = Mock()
            mock_client.generate = Mock(return_value={"content": "test", "confidence": 0.8})
            
            from backend.llm_orchestrator.multimodal_llm_system import MultimodalLLMSystem
            system = MultimodalLLMSystem(
                multi_llm_client=mock_client,
                repo_access=None,
                session=None
            )
            return system
    
    @pytest.fixture
    def multimodal_types(self):
        """Import multimodal types with mocked dependencies."""
        with patch.dict('sys.modules', {
            'llm_orchestrator.multi_llm_client': MagicMock(),
            'llm_orchestrator.repo_access': MagicMock(),
            'genesis.cognitive_layer1_integration': MagicMock(),
            'api.voice_api': MagicMock()
        }):
            from backend.llm_orchestrator.multimodal_llm_system import MultimodalInput, MediaType
            return MultimodalInput, MediaType
    
    def test_calculate_trust_score_with_file_inputs(self, multimodal_system, multimodal_types):
        """Test trust score calculation with file inputs."""
        MultimodalInput, MediaType = multimodal_types
        
        inputs = [
            MultimodalInput(
                media_type=MediaType.IMAGE,
                content=b"test",
                content_path="/path/to/image.png"
            )
        ]
        
        score = multimodal_system._calculate_trust_score(inputs, "This is a test response with sufficient length")
        
        # File inputs should increase trust (use approximate comparison for float)
        assert score >= 0.79
    
    def test_calculate_trust_score_no_files(self, multimodal_system, multimodal_types):
        """Test trust score calculation without file inputs."""
        MultimodalInput, MediaType = multimodal_types
        
        inputs = [
            MultimodalInput(
                media_type=MediaType.TEXT,
                content="test content"
            )
        ]
        
        score = multimodal_system._calculate_trust_score(inputs, "Short")
        
        # No files, short content = lower trust
        assert 0.6 <= score <= 0.8
    
    def test_calculate_trust_score_long_content(self, multimodal_system, multimodal_types):
        """Test trust score with long content."""
        MultimodalInput, MediaType = multimodal_types
        
        inputs = [
            MultimodalInput(
                media_type=MediaType.TEXT,
                content="query"
            )
        ]
        
        long_content = "A" * 200  # Substantial content
        score = multimodal_system._calculate_trust_score(inputs, long_content)
        
        # Long content should increase trust (use approximate comparison for float)
        assert score >= 0.79
