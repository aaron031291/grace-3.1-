import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import base64
import tempfile
import os
from llm_orchestrator.multimodal_llm_system import get_multimodal_llm_system, MultimodalLLMSystem, MultimodalInput, MediaType
from llm_orchestrator.multi_llm_client import TaskType
from database.session import get_db

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/multimodal", tags=["Multimodal LLM"])


class MultimodalRequest(BaseModel):
    """Multimodal processing request."""
    prompt: str = Field(..., description="Text prompt/question")
    task_type: str = Field(default="general", description="Task type")
    user_id: Optional[str] = Field(default=None, description="User ID")
    generate_media: bool = Field(default=False, description="Generate media output")
    media_types: List[str] = Field(default=[], description="Types of media in inputs")


class MultimodalResponse(BaseModel):
    """Multimodal processing response."""
    content: str = Field(..., description="Text response")
    genesis_key_id: Optional[str] = Field(None, description="Genesis Key for this interaction")
    trust_score: float = Field(..., description="Trust score (0-1)")
    confidence_score: float = Field(..., description="Confidence score (0-1)")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    media_output: Optional[Dict[str, Any]] = Field(None, description="Generated media if applicable")
    timestamp: str = Field(..., description="Timestamp")


class VoiceTTSRequest(BaseModel):
    """Text-to-Speech request."""
    text: str = Field(..., description="Text to convert to speech")
    voice: str = Field(default="en-US-AriaNeural", description="Voice ID")
    user_id: Optional[str] = Field(default=None, description="User ID")


class VoiceSTTRequest(BaseModel):
    """Speech-to-Text request."""
    language: str = Field(default="en-US", description="Language code")
    user_id: Optional[str] = Field(default=None, description="User ID")


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/process", response_model=MultimodalResponse)
async def process_multimodal(
    prompt: str = Form(...),
    task_type: str = Form("general"),
    user_id: Optional[str] = Form(None),
    generate_media: bool = Form(False),
    files: List[UploadFile] = File(...),
    session: Session = Depends(get_db)
):
    """
    Process multimodal inputs (images, videos, audio, text).
    
    Supports:
    - Images: .jpg, .jpeg, .png, .gif, .webp
    - Videos: .mp4, .avi, .mov, .mkv, .webm
    - Audio: .mp3, .wav, .m4a, .flac, .ogg
    - Text: .txt, .md
    
    All outputs are tracked with Genesis Keys.
    """
    try:
        multimodal_system = get_multimodal_llm_system(session=session)
        
        # Process uploaded files
        inputs = []
        temp_files = []
        
        for file in files:
            # Save to temp file
            ext = os.path.splitext(file.filename)[1].lower()
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            temp_files.append(temp_file.name)
            
            content = await file.read()
            temp_file.write(content)
            temp_file.close()
            
            # Determine media type
            media_type = _determine_media_type(ext)
            
            inputs.append(MultimodalInput(
                media_type=media_type,
                content=content,
                content_path=temp_file.name,
                metadata={"filename": file.filename}
            ))
        
        # Process multimodal inputs
        result = multimodal_system.process_multimodal(
            inputs=inputs,
            prompt=prompt,
            task_type=TaskType[task_type.upper()] if hasattr(TaskType, task_type.upper()) else TaskType.GENERAL,
            user_id=user_id,
            generate_media=generate_media
        )
        
        # Clean up temp files
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except Exception:
                pass
        
        return MultimodalResponse(
            content=result.content,
            genesis_key_id=result.genesis_key_id,
            trust_score=result.trust_score,
            confidence_score=result.confidence_score,
            processing_time_ms=result.processing_time_ms,
            media_output=result.media_output,
            timestamp=result.timestamp.isoformat() if result.timestamp else ""
        )
        
    except Exception as e:
        logger.error(f"Multimodal processing error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts")
async def text_to_speech(
    request: VoiceTTSRequest,
    session: Session = Depends(get_db)
):
    """
    Convert text to speech with Genesis Key tracking.
    
    Returns audio file and Genesis Key ID.
    """
    try:
        multimodal_system = get_multimodal_llm_system(session=session)
        
        audio_data, genesis_key_id = await multimodal_system.text_to_speech(
            text=request.text,
            voice=request.voice,
            user_id=request.user_id
        )
        
        return {
            "audio_base64": base64.b64encode(audio_data).decode('utf-8'),
            "genesis_key_id": genesis_key_id,
            "format": "mp3",
            "text": request.text,
            "voice": request.voice
        }
        
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stt")
async def speech_to_text(
    audio: UploadFile = File(...),
    language: str = Form("en-US"),
    user_id: Optional[str] = Form(None),
    session: Session = Depends(get_db)
):
    """
    Convert speech to text with Genesis Key tracking.
    
    Returns transcribed text and Genesis Key ID.
    """
    try:
        multimodal_system = get_multimodal_llm_system(session=session)
        
        audio_data = await audio.read()
        
        text, genesis_key_id = await multimodal_system.speech_to_text(
            audio_data=audio_data,
            language=language,
            user_id=user_id
        )
        
        return {
            "text": text,
            "genesis_key_id": genesis_key_id,
            "language": language,
            "confidence": 0.95  # Would be calculated by STT engine
        }
        
    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_multimodal_status(session: Session = Depends(get_db)):
    """Get multimodal system status."""
    try:
        multimodal_system = get_multimodal_llm_system(session=session)
        
        return {
            "status": "online",
            "capabilities": {
                "vision": True,
                "audio": True,
                "video": True,
                "voice_tts": multimodal_system.voice_manager is not None,
                "voice_stt": multimodal_system.voice_manager is not None
            },
            "supported_formats": {
                "images": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
                "videos": [".mp4", ".avi", ".mov", ".mkv", ".webm"],
                "audio": [".mp3", ".wav", ".m4a", ".flac", ".ogg"]
            }
        }
        
    except Exception as e:
        logger.error(f"Status check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _determine_media_type(ext: str) -> MediaType:
    """Determine media type from file extension."""
    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}
    video_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"}
    audio_exts = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma"}
    
    ext_lower = ext.lower()
    
    if ext_lower in image_exts:
        return MediaType.IMAGE
    elif ext_lower in video_exts:
        return MediaType.VIDEO
    elif ext_lower in audio_exts:
        return MediaType.AUDIO
    else:
        return MediaType.TEXT
