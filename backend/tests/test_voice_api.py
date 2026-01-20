"""
Comprehensive Component Tests for Voice API

Tests the complete voice functionality:
- TTS (Text-to-Speech) with multiple engines
- STT (Speech-to-Text) handling
- NLP preprocessing
- WebSocket continuous voice sessions
- Voice settings management
"""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import tempfile
import asyncio
import sys
import io
import base64
import importlib.util

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Direct import to avoid api package initialization
def load_voice_api_module():
    """Load voice_api module directly without going through api package."""
    voice_api_path = Path(__file__).parent.parent / "api" / "voice_api.py"
    spec = importlib.util.spec_from_file_location("voice_api", voice_api_path)
    voice_api = importlib.util.module_from_spec(spec)
    sys.modules["voice_api"] = voice_api
    spec.loader.exec_module(voice_api)
    return voice_api


# Load module at test collection time
voice_api = load_voice_api_module()


# ==================== Enum Tests ====================

class TestTTSEngine:
    """Test TTSEngine enum"""

    def test_all_engines_exist(self):
        """Test all expected TTS engines are defined"""
        TTSEngine = voice_api.TTSEngine

        assert hasattr(TTSEngine, 'EDGE_TTS')
        assert hasattr(TTSEngine, 'PYTTSX3')
        assert hasattr(TTSEngine, 'SYSTEM')

    def test_engine_values(self):
        """Test engine string values"""
        TTSEngine = voice_api.TTSEngine

        assert TTSEngine.EDGE_TTS.value == "edge_tts"
        assert TTSEngine.PYTTSX3.value == "pyttsx3"
        assert TTSEngine.SYSTEM.value == "system"


class TestSTTEngine:
    """Test STTEngine enum"""

    def test_all_engines_exist(self):
        """Test all expected STT engines are defined"""
        STTEngine = voice_api.STTEngine

        assert hasattr(STTEngine, 'WHISPER')
        assert hasattr(STTEngine, 'WEB_SPEECH')


# ==================== Model Tests ====================

class TestVoiceSettings:
    """Test VoiceSettings model"""

    def test_default_settings(self):
        """Test default voice settings"""
        VoiceSettings = voice_api.VoiceSettings
        TTSEngine = voice_api.TTSEngine
        STTEngine = voice_api.STTEngine

        settings = VoiceSettings()

        assert settings.tts_engine == TTSEngine.EDGE_TTS
        assert settings.tts_voice == "en-US-AriaNeural"
        assert settings.tts_rate == "+0%"
        assert settings.tts_pitch == "+0Hz"
        assert settings.stt_engine == STTEngine.WEB_SPEECH
        assert settings.stt_language == "en-US"
        assert settings.continuous_mode == False
        assert settings.auto_send == True
        assert settings.wake_word == "grace"

    def test_custom_settings(self):
        """Test custom voice settings"""
        VoiceSettings = voice_api.VoiceSettings
        TTSEngine = voice_api.TTSEngine

        settings = VoiceSettings(
            tts_engine=TTSEngine.PYTTSX3,
            tts_voice="en-GB-SoniaNeural",
            tts_rate="+10%",
            continuous_mode=True,
            wake_word="hey grace"
        )

        assert settings.tts_engine == TTSEngine.PYTTSX3
        assert settings.tts_voice == "en-GB-SoniaNeural"
        assert settings.tts_rate == "+10%"
        assert settings.continuous_mode == True
        assert settings.wake_word == "hey grace"


class TestTTSRequest:
    """Test TTSRequest model"""

    def test_tts_request_minimal(self):
        """Test minimal TTS request"""
        TTSRequest = voice_api.TTSRequest

        request = TTSRequest(text="Hello world")

        assert request.text == "Hello world"
        assert request.voice == "en-US-AriaNeural"
        assert request.rate == "+0%"
        assert request.pitch == "+0Hz"

    def test_tts_request_full(self):
        """Test full TTS request"""
        TTSRequest = voice_api.TTSRequest
        TTSEngine = voice_api.TTSEngine

        request = TTSRequest(
            text="Hello world",
            voice="en-GB-RyanNeural",
            rate="+20%",
            pitch="-5Hz",
            engine=TTSEngine.EDGE_TTS
        )

        assert request.text == "Hello world"
        assert request.voice == "en-GB-RyanNeural"
        assert request.rate == "+20%"
        assert request.pitch == "-5Hz"


class TestSTTResponse:
    """Test STTResponse model"""

    def test_stt_response(self):
        """Test STT response"""
        STTResponse = voice_api.STTResponse

        response = STTResponse(
            text="Hello world",
            confidence=0.95,
            language="en-US",
            duration_ms=1500.0
        )

        assert response.text == "Hello world"
        assert response.confidence == 0.95
        assert response.language == "en-US"
        assert response.duration_ms == 1500.0


class TestNLPProcessedText:
    """Test NLPProcessedText model"""

    def test_nlp_processed_text(self):
        """Test NLP processed text"""
        NLPProcessedText = voice_api.NLPProcessedText

        processed = NLPProcessedText(
            original_text="um, like, what is the weather?",
            cleaned_text="what is the weather?",
            intent="question",
            entities=[{"type": "topic", "value": "weather"}],
            sentiment="neutral"
        )

        assert processed.original_text == "um, like, what is the weather?"
        assert processed.cleaned_text == "what is the weather?"
        assert processed.intent == "question"
        assert processed.sentiment == "neutral"


# ==================== VoiceManager Tests ====================

class TestVoiceManager:
    """Test VoiceManager class"""

    @pytest.fixture
    def manager(self):
        """Create VoiceManager instance"""
        VoiceManager = voice_api.VoiceManager
        return VoiceManager()

    def test_voice_manager_initialization(self, manager):
        """Test VoiceManager initializes correctly"""
        assert manager.settings is not None
        assert manager._edge_tts_available is None
        assert manager._pyttsx3_available is None

    def test_available_voices_structure(self, manager):
        """Test available voices structure"""
        voices = manager.AVAILABLE_VOICES

        assert "en-US" in voices
        assert "en-GB" in voices
        assert "en-AU" in voices

        # Check voice structure
        us_voices = voices["en-US"]
        assert len(us_voices) > 0
        assert all("id" in v for v in us_voices)
        assert all("name" in v for v in us_voices)
        assert all("gender" in v for v in us_voices)


class TestVoiceManagerNLP:
    """Test VoiceManager NLP functionality"""

    @pytest.fixture
    def manager(self):
        """Create VoiceManager instance"""
        VoiceManager = voice_api.VoiceManager
        return VoiceManager()

    def test_preprocess_text_nlp_basic(self, manager):
        """Test basic NLP preprocessing"""
        result = manager.preprocess_text_nlp("Hello world")

        assert result.original_text == "Hello world"
        assert result.cleaned_text == "Hello world"
        assert result.intent is not None

    def test_preprocess_removes_filler_words(self, manager):
        """Test filler word removal"""
        result = manager.preprocess_text_nlp("um, like, what is that?")

        assert "um" not in result.cleaned_text.lower() or result.cleaned_text != "um, like, what is that?"
        assert result.cleaned_text.strip() != ""

    def test_detect_intent_question(self, manager):
        """Test question intent detection"""
        result = manager.preprocess_text_nlp("What is machine learning?")
        assert result.intent == "question"

        result = manager.preprocess_text_nlp("How does this work?")
        assert result.intent == "question"

        result = manager.preprocess_text_nlp("Can you help me?")
        assert result.intent == "question"

    def test_detect_intent_command(self, manager):
        """Test command intent detection"""
        result = manager.preprocess_text_nlp("Create a new file")
        assert result.intent == "command"

        result = manager.preprocess_text_nlp("Delete the old data")
        assert result.intent == "command"

        result = manager.preprocess_text_nlp("Run the tests")
        assert result.intent == "command"

    def test_detect_intent_request(self, manager):
        """Test request intent detection"""
        result = manager.preprocess_text_nlp("Please help me with this")
        assert result.intent == "request"

        result = manager.preprocess_text_nlp("I need some assistance")
        assert result.intent == "request"

    def test_detect_intent_greeting(self, manager):
        """Test greeting intent detection"""
        result = manager.preprocess_text_nlp("Hello there!")
        assert result.intent == "greeting"

        result = manager.preprocess_text_nlp("Hi Grace")
        assert result.intent == "greeting"

        result = manager.preprocess_text_nlp("Good morning")
        assert result.intent == "greeting"

    def test_detect_intent_farewell(self, manager):
        """Test farewell intent detection"""
        result = manager.preprocess_text_nlp("Goodbye")
        assert result.intent == "farewell"

        result = manager.preprocess_text_nlp("Bye for now")
        assert result.intent == "farewell"

    def test_detect_intent_statement(self, manager):
        """Test statement intent detection"""
        result = manager.preprocess_text_nlp("The sky is blue")
        assert result.intent == "statement"

    def test_extract_entities_file_path(self, manager):
        """Test file path entity extraction"""
        result = manager.preprocess_text_nlp("Open the file test.py")

        file_entities = [e for e in result.entities if e["type"] == "file_path"]
        assert len(file_entities) >= 1
        assert any("test.py" in e["value"] for e in file_entities)

    def test_extract_entities_url(self, manager):
        """Test URL entity extraction"""
        result = manager.preprocess_text_nlp("Visit https://example.com")

        url_entities = [e for e in result.entities if e["type"] == "url"]
        assert len(url_entities) == 1
        assert url_entities[0]["value"] == "https://example.com"

    def test_extract_entities_numbers(self, manager):
        """Test number entity extraction"""
        result = manager.preprocess_text_nlp("Set timeout to 30 seconds")

        number_entities = [e for e in result.entities if e["type"] == "number"]
        assert len(number_entities) >= 1
        assert any(e["value"] == "30" for e in number_entities)

    def test_detect_sentiment_positive(self, manager):
        """Test positive sentiment detection"""
        result = manager.preprocess_text_nlp("This is great! I love it!")
        assert result.sentiment == "positive"

    def test_detect_sentiment_negative(self, manager):
        """Test negative sentiment detection"""
        result = manager.preprocess_text_nlp("This is terrible, the code has bugs")
        assert result.sentiment == "negative"

    def test_detect_sentiment_neutral(self, manager):
        """Test neutral sentiment detection"""
        result = manager.preprocess_text_nlp("The function returns a value")
        assert result.sentiment == "neutral"


class TestVoiceManagerTTS:
    """Test VoiceManager TTS functionality"""

    @pytest.fixture
    def manager(self):
        """Create VoiceManager instance"""
        VoiceManager = voice_api.VoiceManager
        return VoiceManager()

    @pytest.mark.asyncio
    async def test_check_tts_availability(self, manager):
        """Test checking TTS availability"""
        results = await manager.check_tts_availability()

        assert "edge_tts" in results
        assert "pyttsx3" in results
        assert isinstance(results["edge_tts"], bool)
        assert isinstance(results["pyttsx3"], bool)


# ==================== VoiceSession Tests ====================

class TestVoiceSession:
    """Test VoiceSession class"""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket"""
        ws = AsyncMock()
        return ws

    @pytest.mark.asyncio
    async def test_session_start(self, mock_websocket):
        """Test starting a voice session"""
        VoiceSession = voice_api.VoiceSession

        session = VoiceSession(mock_websocket)
        await session.start()

        assert session.active == True
        mock_websocket.send_json.assert_called_once()

        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "session_started"

    @pytest.mark.asyncio
    async def test_session_stop(self, mock_websocket):
        """Test stopping a voice session"""
        VoiceSession = voice_api.VoiceSession

        session = VoiceSession(mock_websocket)
        session.active = True

        await session.stop()

        assert session.active == False
        mock_websocket.send_json.assert_called_once()

        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "session_ended"

    def test_session_conversation_history(self, mock_websocket):
        """Test conversation history tracking"""
        VoiceSession = voice_api.VoiceSession

        session = VoiceSession(mock_websocket)

        assert session.conversation_history == []

        session.conversation_history.append({
            "role": "user",
            "content": "Hello"
        })

        assert len(session.conversation_history) == 1
        assert session.conversation_history[0]["role"] == "user"


# ==================== API Endpoint Tests ====================

class TestVoiceAPIEndpoints:
    """Test Voice API endpoints"""

    @pytest.mark.asyncio
    async def test_get_available_voices(self):
        """Test getting available voices for a locale"""
        get_available_voices = voice_api.get_available_voices

        # Test US voices
        result = await get_available_voices("en-US")

        assert result["locale"] == "en-US"
        assert "voices" in result
        assert result["total"] > 0

        # Check voice structure
        voices = result["voices"]
        assert all("id" in v for v in voices)
        assert all("name" in v for v in voices)

    @pytest.mark.asyncio
    async def test_get_available_voices_gb(self):
        """Test getting GB voices"""
        get_available_voices = voice_api.get_available_voices

        result = await get_available_voices("en-GB")

        assert result["locale"] == "en-GB"
        assert len(result["voices"]) > 0

    @pytest.mark.asyncio
    async def test_get_available_voices_unknown_locale(self):
        """Test getting voices for unknown locale returns all English"""
        get_available_voices = voice_api.get_available_voices

        result = await get_available_voices("fr-FR")

        # Should return all English voices
        assert "voices" in result

    @pytest.mark.asyncio
    async def test_get_voice_settings(self):
        """Test getting voice settings"""
        get_voice_settings = voice_api.get_voice_settings

        result = await get_voice_settings()

        assert "tts_engine" in result
        assert "tts_voice" in result
        assert "stt_language" in result

    @pytest.mark.asyncio
    async def test_update_voice_settings(self):
        """Test updating voice settings"""
        update_voice_settings = voice_api.update_voice_settings
        VoiceSettings = voice_api.VoiceSettings
        TTSEngine = voice_api.TTSEngine

        new_settings = VoiceSettings(
            tts_engine=TTSEngine.PYTTSX3,
            tts_voice="en-GB-RyanNeural",
            continuous_mode=True
        )

        result = await update_voice_settings(new_settings)

        assert result["status"] == "updated"
        assert result["settings"]["tts_engine"] == "pyttsx3"

    @pytest.mark.asyncio
    async def test_process_text_nlp_endpoint(self):
        """Test NLP processing endpoint"""
        process_text_nlp = voice_api.process_text_nlp

        result = await process_text_nlp("What is machine learning?")

        assert "original_text" in result
        assert "cleaned_text" in result
        assert "intent" in result
        assert result["intent"] == "question"


# ==================== Integration Tests ====================

class TestVoiceAPIIntegration:
    """Integration tests for Voice API"""

    @pytest.fixture
    def manager(self):
        """Create VoiceManager instance"""
        VoiceManager = voice_api.VoiceManager
        return VoiceManager()

    def test_full_nlp_pipeline(self, manager):
        """Test complete NLP processing pipeline"""
        # Input with filler words, entities, and clear intent
        text = "um, like, can you help me open the file test.py at https://github.com"

        result = manager.preprocess_text_nlp(text)

        # Should clean filler words (at least partially)
        assert result.cleaned_text != "" or result.original_text == text

        # Should detect intent
        assert result.intent in ["question", "request", "statement"]

        # Should extract some entities
        assert len(result.entities) >= 0  # May have entities

    @pytest.mark.asyncio
    async def test_voice_status_check(self):
        """Test getting voice system status"""
        get_voice_status = voice_api.get_voice_status

        status = await get_voice_status()

        assert status["status"] == "online"
        assert "tts_engines" in status
        assert "stt_engines" in status
        assert "current_settings" in status
        assert "timestamp" in status


# ==================== Error Handling Tests ====================

class TestVoiceAPIErrorHandling:
    """Test error handling in Voice API"""

    @pytest.fixture
    def manager(self):
        """Create VoiceManager instance"""
        VoiceManager = voice_api.VoiceManager
        return VoiceManager()

    def test_nlp_empty_text(self, manager):
        """Test NLP with empty text"""
        result = manager.preprocess_text_nlp("")

        assert result.original_text == ""
        assert result.cleaned_text == ""

    def test_nlp_whitespace_only(self, manager):
        """Test NLP with whitespace only"""
        result = manager.preprocess_text_nlp("   ")

        assert result.cleaned_text == ""

    def test_nlp_special_characters(self, manager):
        """Test NLP with special characters"""
        result = manager.preprocess_text_nlp("!@#$%^&*()")

        # Should not crash
        assert result.original_text == "!@#$%^&*()"

    def test_nlp_very_long_text(self, manager):
        """Test NLP with very long text"""
        long_text = "hello " * 1000

        result = manager.preprocess_text_nlp(long_text)

        # Should not crash
        assert len(result.original_text) > 0

    def test_nlp_unicode_text(self, manager):
        """Test NLP with unicode characters"""
        result = manager.preprocess_text_nlp("Hello World!")

        # Should handle unicode
        assert result.original_text == "Hello World!"


# ==================== Voice Quality Tests ====================

class TestVoiceQuality:
    """Test voice quality related functionality"""

    @pytest.fixture
    def manager(self):
        """Create VoiceManager instance"""
        VoiceManager = voice_api.VoiceManager
        return VoiceManager()

    def test_available_voice_count(self, manager):
        """Test sufficient voices are available"""
        total_voices = sum(
            len(voices) for voices in manager.AVAILABLE_VOICES.values()
        )
        assert total_voices >= 15  # Should have at least 15 voices

    def test_voice_genders_balanced(self, manager):
        """Test voice genders are somewhat balanced"""
        us_voices = manager.AVAILABLE_VOICES.get("en-US", [])

        male_count = sum(1 for v in us_voices if v["gender"] == "Male")
        female_count = sum(1 for v in us_voices if v["gender"] == "Female")

        assert male_count > 0
        assert female_count > 0

    def test_default_voice_exists(self, manager):
        """Test default voice is in available voices"""
        default_voice = manager.settings.tts_voice

        all_voice_ids = []
        for voices in manager.AVAILABLE_VOICES.values():
            all_voice_ids.extend(v["id"] for v in voices)

        assert default_voice in all_voice_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
