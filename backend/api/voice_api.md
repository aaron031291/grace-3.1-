# Voice Api

**File:** `api/voice_api.py`

## Overview

Voice API - Speech-to-Text (STT) and Text-to-Speech (TTS) endpoints

Provides voice capabilities for GRACE:
- Speech-to-Text using Whisper (via Ollama or local)
- Text-to-Speech using edge-tts, pyttsx3, or system TTS
- Continuous conversation mode
- NLP preprocessing for natural language understanding

## Classes

- `TTSEngine`
- `STTEngine`
- `VoiceSettings`
- `TTSRequest`
- `STTResponse`
- `NLPProcessedText`
- `VoiceManager`
- `VoiceSession`

## Key Methods

- `preprocess_text_nlp()`

---
*Grace 3.1*
