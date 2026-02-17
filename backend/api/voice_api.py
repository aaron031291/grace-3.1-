"""
Voice API - Speech-to-Text (STT) and Text-to-Speech (TTS) endpoints

Provides voice capabilities for GRACE:
- Speech-to-Text using Whisper (via Ollama or local)
- Text-to-Speech using edge-tts, pyttsx3, or system TTS
- Continuous conversation mode
- NLP preprocessing for natural language understanding
"""

import logging
import asyncio
import tempfile
import os
import io
import base64
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

def _track_voice(desc, **kwargs):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event("voice_api", desc, **kwargs)
    except Exception:
        pass

router = APIRouter(prefix="/voice", tags=["voice"])


# =============================================================================
# MODELS
# =============================================================================

class TTSEngine(str, Enum):
    """Available TTS engines."""
    EDGE_TTS = "edge_tts"       # Microsoft Edge TTS (best quality, requires internet)
    PYTTSX3 = "pyttsx3"         # Offline TTS (cross-platform)
    SYSTEM = "system"           # System default TTS


class STTEngine(str, Enum):
    """Available STT engines."""
    WHISPER = "whisper"         # OpenAI Whisper (via Ollama or local)
    WEB_SPEECH = "web_speech"   # Browser Web Speech API (handled client-side)


class VoiceSettings(BaseModel):
    """Voice configuration settings."""
    tts_engine: TTSEngine = TTSEngine.EDGE_TTS
    tts_voice: str = "en-US-AriaNeural"  # Default voice
    tts_rate: str = "+0%"                 # Speech rate adjustment
    tts_pitch: str = "+0Hz"               # Pitch adjustment
    stt_engine: STTEngine = STTEngine.WEB_SPEECH
    stt_language: str = "en-US"
    continuous_mode: bool = False
    auto_send: bool = True                # Auto-send after speech recognition
    wake_word: Optional[str] = "grace"    # Optional wake word


class TTSRequest(BaseModel):
    """Text-to-Speech request."""
    text: str
    voice: Optional[str] = "en-US-AriaNeural"
    rate: Optional[str] = "+0%"
    pitch: Optional[str] = "+0Hz"
    engine: Optional[TTSEngine] = TTSEngine.EDGE_TTS


class STTResponse(BaseModel):
    """Speech-to-Text response."""
    text: str
    confidence: float
    language: str
    duration_ms: float


class NLPProcessedText(BaseModel):
    """NLP processed text with intent and entities."""
    original_text: str
    cleaned_text: str
    intent: Optional[str] = None
    entities: List[Dict[str, Any]] = []
    sentiment: Optional[str] = None


# =============================================================================
# VOICE MANAGER
# =============================================================================

class VoiceManager:
    """Manages voice operations for STT and TTS."""

    # Available Edge TTS voices for English
    AVAILABLE_VOICES = {
        "en-US": [
            {"id": "en-US-AriaNeural", "name": "Aria (Female)", "gender": "Female"},
            {"id": "en-US-GuyNeural", "name": "Guy (Male)", "gender": "Male"},
            {"id": "en-US-JennyNeural", "name": "Jenny (Female)", "gender": "Female"},
            {"id": "en-US-DavisNeural", "name": "Davis (Male)", "gender": "Male"},
            {"id": "en-US-AmberNeural", "name": "Amber (Female)", "gender": "Female"},
            {"id": "en-US-AnaNeural", "name": "Ana (Female, Child)", "gender": "Female"},
            {"id": "en-US-BrandonNeural", "name": "Brandon (Male)", "gender": "Male"},
            {"id": "en-US-ChristopherNeural", "name": "Christopher (Male)", "gender": "Male"},
            {"id": "en-US-CoraNeural", "name": "Cora (Female)", "gender": "Female"},
            {"id": "en-US-ElizabethNeural", "name": "Elizabeth (Female)", "gender": "Female"},
            {"id": "en-US-EricNeural", "name": "Eric (Male)", "gender": "Male"},
            {"id": "en-US-JacobNeural", "name": "Jacob (Male)", "gender": "Male"},
            {"id": "en-US-MichelleNeural", "name": "Michelle (Female)", "gender": "Female"},
            {"id": "en-US-MonicaNeural", "name": "Monica (Female)", "gender": "Female"},
            {"id": "en-US-SaraNeural", "name": "Sara (Female)", "gender": "Female"},
        ],
        "en-GB": [
            {"id": "en-GB-SoniaNeural", "name": "Sonia (Female, British)", "gender": "Female"},
            {"id": "en-GB-RyanNeural", "name": "Ryan (Male, British)", "gender": "Male"},
            {"id": "en-GB-LibbyNeural", "name": "Libby (Female, British)", "gender": "Female"},
        ],
        "en-AU": [
            {"id": "en-AU-NatashaNeural", "name": "Natasha (Female, Australian)", "gender": "Female"},
            {"id": "en-AU-WilliamNeural", "name": "William (Male, Australian)", "gender": "Male"},
        ],
    }

    def __init__(self):
        self.settings = VoiceSettings()
        self._edge_tts_available = None
        self._pyttsx3_available = None

    async def check_tts_availability(self) -> Dict[str, bool]:
        """Check which TTS engines are available."""
        results = {}

        # Check edge-tts
        try:
            import edge_tts
            self._edge_tts_available = True
            results["edge_tts"] = True
        except ImportError:
            self._edge_tts_available = False
            results["edge_tts"] = False

        # Check pyttsx3
        try:
            import pyttsx3
            self._pyttsx3_available = True
            results["pyttsx3"] = True
        except ImportError:
            self._pyttsx3_available = False
            results["pyttsx3"] = False

        return results

    async def text_to_speech(
        self,
        text: str,
        voice: str = "en-US-AriaNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        engine: TTSEngine = TTSEngine.EDGE_TTS
    ) -> bytes:
        """Convert text to speech audio."""

        if engine == TTSEngine.EDGE_TTS:
            return await self._edge_tts(text, voice, rate, pitch)
        elif engine == TTSEngine.PYTTSX3:
            return await self._pyttsx3_tts(text, rate)
        else:
            # Fallback to edge-tts
            return await self._edge_tts(text, voice, rate, pitch)

    async def _edge_tts(
        self,
        text: str,
        voice: str,
        rate: str,
        pitch: str
    ) -> bytes:
        """Generate speech using Microsoft Edge TTS."""
        try:
            import edge_tts

            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch
            )

            # Collect audio data
            audio_data = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data.write(chunk["data"])

            audio_data.seek(0)
            return audio_data.read()

        except ImportError:
            logger.error("edge-tts not installed. Install with: pip install edge-tts")
            raise HTTPException(
                status_code=500,
                detail="edge-tts not installed. Install with: pip install edge-tts"
            )
        except Exception as e:
            logger.error(f"Edge TTS error: {e}")
            raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

    async def _pyttsx3_tts(self, text: str, rate: str) -> bytes:
        """Generate speech using pyttsx3 (offline)."""
        try:
            import pyttsx3

            # Run in executor since pyttsx3 is synchronous
            loop = asyncio.get_event_loop()

            def generate():
                engine = pyttsx3.init()

                # Parse rate adjustment
                rate_adj = int(rate.replace("%", "").replace("+", ""))
                current_rate = engine.getProperty('rate')
                engine.setProperty('rate', current_rate + rate_adj)

                # Save to temp file
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    temp_path = f.name

                engine.save_to_file(text, temp_path)
                engine.runAndWait()

                with open(temp_path, 'rb') as f:
                    audio_data = f.read()

                os.unlink(temp_path)
                return audio_data

            return await loop.run_in_executor(None, generate)

        except ImportError:
            logger.error("pyttsx3 not installed. Install with: pip install pyttsx3")
            raise HTTPException(
                status_code=500,
                detail="pyttsx3 not installed. Install with: pip install pyttsx3"
            )
        except Exception as e:
            logger.error(f"pyttsx3 TTS error: {e}")
            raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

    def preprocess_text_nlp(self, text: str) -> NLPProcessedText:
        """
        Preprocess text using NLP for better understanding.

        Handles:
        - Filler word removal
        - Command extraction
        - Intent detection
        - Entity extraction
        """
        import re

        original = text
        cleaned = text.strip()

        # Remove common filler words
        filler_words = [
            r'\bum+\b', r'\buh+\b', r'\blike\b', r'\byou know\b',
            r'\bbasically\b', r'\bactually\b', r'\bliterally\b',
            r'\bi mean\b', r'\bso+\b(?=\s|$)', r'\bwell\b(?=\s|,)'
        ]

        for filler in filler_words:
            cleaned = re.sub(filler, '', cleaned, flags=re.IGNORECASE)

        # Clean up multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # Detect intent
        intent = self._detect_intent(cleaned)

        # Extract entities
        entities = self._extract_entities(cleaned)

        # Simple sentiment detection
        sentiment = self._detect_sentiment(cleaned)

        return NLPProcessedText(
            original_text=original,
            cleaned_text=cleaned,
            intent=intent,
            entities=entities,
            sentiment=sentiment
        )

    def _detect_intent(self, text: str) -> Optional[str]:
        """Detect the intent of the text."""
        text_lower = text.lower()

        # Question intents
        if any(text_lower.startswith(q) for q in ['what', 'who', 'where', 'when', 'why', 'how', 'can', 'could', 'would', 'is', 'are', 'do', 'does']):
            return "question"

        # Command intents
        command_words = ['create', 'make', 'build', 'generate', 'write', 'delete', 'remove', 'update', 'change', 'modify', 'add', 'show', 'display', 'list', 'find', 'search', 'open', 'close', 'start', 'stop', 'run', 'execute']
        if any(text_lower.startswith(cmd) for cmd in command_words):
            return "command"

        # Request intents
        if any(phrase in text_lower for phrase in ['please', 'can you', 'could you', 'would you', 'i need', 'i want', 'help me']):
            return "request"

        # Greeting
        if any(text_lower.startswith(g) for g in ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening']):
            return "greeting"

        # Farewell
        if any(text_lower.startswith(f) for f in ['bye', 'goodbye', 'see you', 'talk to you later']):
            return "farewell"

        return "statement"

    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from text."""
        import re
        entities = []

        # File paths
        file_patterns = re.findall(r'[\w/\\]+\.\w+', text)
        for fp in file_patterns:
            entities.append({"type": "file_path", "value": fp})

        # URLs
        url_pattern = re.findall(r'https?://\S+', text)
        for url in url_pattern:
            entities.append({"type": "url", "value": url})

        # Numbers
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        for num in numbers:
            entities.append({"type": "number", "value": num})

        # Code references (function names, class names)
        code_refs = re.findall(r'\b[a-z_][a-z0-9_]*(?:\(\))?', text, re.IGNORECASE)
        for ref in code_refs[:5]:  # Limit to first 5
            if len(ref) > 2 and ref not in ['the', 'and', 'for', 'with']:
                entities.append({"type": "code_reference", "value": ref})

        return entities

    def _detect_sentiment(self, text: str) -> Optional[str]:
        """Simple sentiment detection."""
        text_lower = text.lower()

        positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'love', 'like', 'happy', 'thanks', 'thank you', 'perfect', 'awesome']
        negative_words = ['bad', 'terrible', 'awful', 'horrible', 'hate', 'dislike', 'wrong', 'error', 'bug', 'broken', 'failed', 'issue', 'problem']

        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)

        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"


# Global voice manager instance
voice_manager = VoiceManager()


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.get("/status")
async def get_voice_status():
    """Get voice system status and available engines."""
    tts_availability = await voice_manager.check_tts_availability()

    return {
        "status": "online",
        "tts_engines": tts_availability,
        "stt_engines": {
            "web_speech": True,  # Always available (browser-based)
            "whisper": False,    # Would need to check Ollama
        },
        "current_settings": voice_manager.settings.model_dump(),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/voices")
async def get_available_voices(locale: str = "en-US"):
    """Get available TTS voices for a locale."""
    voices = voice_manager.AVAILABLE_VOICES.get(locale, [])

    # If specific locale not found, return all English voices
    if not voices:
        all_voices = []
        for loc, voice_list in voice_manager.AVAILABLE_VOICES.items():
            if loc.startswith("en"):
                all_voices.extend(voice_list)
        voices = all_voices

    return {
        "locale": locale,
        "voices": voices,
        "total": len(voices)
    }


@router.post("/tts")
async def text_to_speech(request: TTSRequest):
    """Convert text to speech and return audio."""
    try:
        audio_data = await voice_manager.text_to_speech(
            text=request.text,
            voice=request.voice or "en-US-AriaNeural",
            rate=request.rate or "+0%",
            pitch=request.pitch or "+0Hz",
            engine=request.engine or TTSEngine.EDGE_TTS
        )

        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=speech.mp3"
            }
        )

    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts/base64")
async def text_to_speech_base64(request: TTSRequest):
    """Convert text to speech and return base64 encoded audio."""
    try:
        audio_data = await voice_manager.text_to_speech(
            text=request.text,
            voice=request.voice or "en-US-AriaNeural",
            rate=request.rate or "+0%",
            pitch=request.pitch or "+0Hz",
            engine=request.engine or TTSEngine.EDGE_TTS
        )

        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

        return {
            "audio": audio_base64,
            "format": "mp3",
            "text": request.text,
            "voice": request.voice,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    language: str = Form("en-US")
):
    """
    Convert speech audio to text using Whisper.

    Note: Primary STT is handled client-side using Web Speech API.
    This endpoint is for file-based transcription.
    """
    try:
        # Read audio file
        audio_data = await audio.read()

        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            # Try using whisper via transformers
            import torch
            from transformers import pipeline

            transcriber = pipeline(
                "automatic-speech-recognition",
                model="openai/whisper-base",
                device="cuda" if torch.cuda.is_available() else "cpu"
            )

            result = transcriber(temp_path)
            text = result["text"]

            return STTResponse(
                text=text,
                confidence=0.95,  # Whisper doesn't provide confidence
                language=language,
                duration_ms=0
            )

        except ImportError:
            # Fall back to returning error - client should use Web Speech API
            raise HTTPException(
                status_code=501,
                detail="Server-side STT not available. Use client-side Web Speech API."
            )
        finally:
            os.unlink(temp_path)

    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/nlp/process")
async def process_text_nlp(text: str = Form(...)):
    """Process text with NLP for intent and entity extraction."""
    result = voice_manager.preprocess_text_nlp(text)
    return result.model_dump()


@router.post("/settings")
async def update_voice_settings(settings: VoiceSettings):
    """Update voice settings."""
    voice_manager.settings = settings
    return {
        "status": "updated",
        "settings": settings.model_dump()
    }


@router.get("/settings")
async def get_voice_settings():
    """Get current voice settings."""
    return voice_manager.settings.model_dump()


# =============================================================================
# WEBSOCKET FOR CONTINUOUS VOICE
# =============================================================================

class VoiceSession:
    """Manages a continuous voice conversation session."""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.active = False
        self.conversation_history: List[Dict[str, str]] = []

    async def start(self):
        self.active = True
        await self.websocket.send_json({
            "type": "session_started",
            "message": "Voice session started. I'm listening...",
            "timestamp": datetime.now().isoformat()
        })

    async def stop(self):
        self.active = False
        await self.websocket.send_json({
            "type": "session_ended",
            "message": "Voice session ended.",
            "timestamp": datetime.now().isoformat()
        })


@router.websocket("/ws/continuous")
async def websocket_continuous_voice(websocket: WebSocket):
    """
    WebSocket endpoint for continuous voice conversation.

    Client sends:
    - {"type": "start"} - Start listening
    - {"type": "stop"} - Stop listening
    - {"type": "transcript", "text": "..."} - Speech transcript from client
    - {"type": "audio", "data": "base64..."} - Audio data for server-side STT

    Server sends:
    - {"type": "session_started"} - Session started confirmation
    - {"type": "session_ended"} - Session ended confirmation
    - {"type": "response", "text": "...", "audio": "base64..."} - Response with TTS
    - {"type": "error", "message": "..."} - Error message
    """
    await websocket.accept()
    session = VoiceSession(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "start":
                await session.start()

            elif msg_type == "stop":
                await session.stop()

            elif msg_type == "transcript":
                # Process the transcript
                text = data.get("text", "")
                if not text.strip():
                    continue

                # NLP preprocessing
                processed = voice_manager.preprocess_text_nlp(text)

                # Send acknowledgment
                await websocket.send_json({
                    "type": "transcript_received",
                    "original": text,
                    "processed": processed.cleaned_text,
                    "intent": processed.intent,
                    "timestamp": datetime.now().isoformat()
                })

                # Store in history
                session.conversation_history.append({
                    "role": "user",
                    "content": processed.cleaned_text
                })

                # Note: The actual LLM response would be handled by the chat system
                # This WebSocket just manages the voice I/O

            elif msg_type == "speak":
                # Generate TTS for text
                text = data.get("text", "")
                voice = data.get("voice", voice_manager.settings.tts_voice)

                if text:
                    try:
                        audio_data = await voice_manager.text_to_speech(
                            text=text,
                            voice=voice,
                            rate=voice_manager.settings.tts_rate,
                            pitch=voice_manager.settings.tts_pitch
                        )

                        audio_base64 = base64.b64encode(audio_data).decode('utf-8')

                        await websocket.send_json({
                            "type": "audio_response",
                            "text": text,
                            "audio": audio_base64,
                            "format": "mp3",
                            "timestamp": datetime.now().isoformat()
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"TTS error: {str(e)}"
                        })

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info("Voice WebSocket disconnected")
    except Exception as e:
        logger.error(f"Voice WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass  # Client may have disconnected
