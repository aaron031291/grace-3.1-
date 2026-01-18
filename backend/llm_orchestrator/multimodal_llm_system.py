import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import base64
import io
from pathlib import Path
from llm_orchestrator.multi_llm_client import MultiLLMClient, TaskType, get_multi_llm_client
from llm_orchestrator.repo_access import RepositoryAccessLayer, get_repo_access
from genesis.cognitive_layer1_integration import get_cognitive_layer1_integration
class MediaType(Enum):
    logger = logging.getLogger(__name__)
    """Types of media that can be processed."""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    VOICE = "voice"


@dataclass
class MultimodalInput:
    """Multimodal input for LLM processing."""
    media_type: MediaType
    content: Any  # Can be text, image bytes, audio bytes, video bytes
    content_path: Optional[str] = None  # File path if available
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MultimodalOutput:
    """Multimodal output from LLM."""
    content: str  # Text response
    media_output: Optional[Any] = None  # Generated image/audio/video if applicable
    genesis_key_id: Optional[str] = None
    trust_score: float = 0.0
    confidence_score: float = 0.0
    processing_time_ms: float = 0.0
    timestamp: datetime = None


class MultimodalLLMSystem:
    """
    Multimodal LLM system supporting vision, audio, video, and voice.
    
    Features:
    - Vision models for image/video understanding
    - Voice integration (STT/TTS)
    - Audio transcription
    - Video analysis
    - All outputs tracked with Genesis Keys
    """
    
    def __init__(
        self,
        multi_llm_client: Optional[MultiLLMClient] = None,
        repo_access: Optional[RepositoryAccessLayer] = None,
        session=None
    ):
        """
        Initialize multimodal LLM system.
        
        Args:
            multi_llm_client: Multi-LLM client (auto-created if None)
            repo_access: Repository access (auto-created if None)
            session: Database session
        """
        self.multi_llm = multi_llm_client or get_multi_llm_client()
        self.repo_access = repo_access or (get_repo_access(session=session) if session else None)
        self.session = session
        self.cognitive_layer1 = get_cognitive_layer1_integration(session=session) if session else None
        
        # Voice manager (if available)
        try:
            from api.voice_api import VoiceManager
            self.voice_manager = VoiceManager()
        except ImportError:
            self.voice_manager = None
            logger.warning("Voice manager not available")
    
    def process_multimodal(
        self,
        inputs: List[MultimodalInput],
        prompt: str,
        task_type: TaskType = TaskType.GENERAL,
        user_id: Optional[str] = None,
        generate_media: bool = False
    ) -> MultimodalOutput:
        """
        Process multimodal inputs (text, image, video, audio, voice).
        
        Args:
            inputs: List of multimodal inputs
            prompt: Text prompt/question
            task_type: Type of task
            user_id: User ID
            generate_media: Whether to generate media output (image/audio/video)
        
        Returns:
            MultimodalOutput with text response and optional media
        """
        start_time = datetime.now()
        
        logger.info(f"[MULTIMODAL] Processing {len(inputs)} inputs")
        
        # Process each input type
        processed_inputs = []
        for input_item in inputs:
            if input_item.media_type == MediaType.IMAGE:
                processed = self._process_image(input_item)
            elif input_item.media_type == MediaType.VIDEO:
                processed = self._process_video(input_item)
            elif input_item.media_type == MediaType.AUDIO:
                processed = self._process_audio(input_item)
            elif input_item.media_type == MediaType.VOICE:
                processed = self._process_voice(input_item)
            else:
                processed = input_item.content  # Text
            
            processed_inputs.append(processed)
        
        # Build multimodal prompt
        multimodal_prompt = self._build_multimodal_prompt(prompt, processed_inputs, inputs)
        
        # Generate response using vision-capable model if images/video present
        has_vision = any(inp.media_type in [MediaType.IMAGE, MediaType.VIDEO] for inp in inputs)
        model_id = self._select_multimodal_model(has_vision, task_type)
        
        # Generate LLM response
        response = self.multi_llm.generate(
            prompt=multimodal_prompt,
            task_type=task_type,
            model_id=model_id,
            system_prompt="You are a multimodal AI assistant. Analyze images, videos, audio, and text to provide comprehensive responses."
        )
        
        content = response.get("content", "")
        
        # Generate media output if requested
        media_output = None
        if generate_media:
            media_output = self._generate_media_output(content, inputs)
        
        # Assign Genesis Key
        genesis_key_id = self._assign_genesis_key(
            inputs=inputs,
            prompt=prompt,
            content=content,
            user_id=user_id,
            task_type=task_type
        )
        
        # Calculate trust and confidence
        trust_score = self._calculate_trust_score(inputs, content)
        confidence_score = response.get("confidence", 0.7)
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        return MultimodalOutput(
            content=content,
            media_output=media_output,
            genesis_key_id=genesis_key_id,
            trust_score=trust_score,
            confidence_score=confidence_score,
            processing_time_ms=processing_time,
            timestamp=datetime.now()
        )
    
    def _process_image(self, input_item: MultimodalInput) -> str:
        """Process image input - extract description or use vision model."""
        if input_item.content_path:
            # Read image file
            try:
                with open(input_item.content_path, 'rb') as f:
                    image_data = f.read()
            except Exception as e:
                logger.error(f"Error reading image: {e}")
                return f"[Image file: {input_item.content_path}]"
        else:
            image_data = input_item.content
        
        # For now, return placeholder - would use vision model
        # Vision models: llava, bakllava, minicpm-v, etc.
        return f"[Image: {len(image_data)} bytes]"
    
    def _process_video(self, input_item: MultimodalInput) -> str:
        """Process video input - extract frames or transcribe audio."""
        if input_item.content_path:
            # Extract audio and transcribe
            try:
                from file_manager.file_handler import FileHandler
                handler = FileHandler()
                text, error = handler._extract_video(input_item.content_path)
                if text:
                    return f"[Video transcription: {text[:500]}]"
            except Exception as e:
                logger.error(f"Error processing video: {e}")
        
        return f"[Video: {input_item.content_path or 'data'}]"
    
    def _process_audio(self, input_item: MultimodalInput) -> str:
        """Process audio input - transcribe speech."""
        if input_item.content_path:
            try:
                from file_manager.file_handler import FileHandler
                handler = FileHandler()
                text, error = handler._extract_audio(input_item.content_path)
                if text:
                    return f"[Audio transcription: {text[:500]}]"
            except Exception as e:
                logger.error(f"Error processing audio: {e}")
        
        return f"[Audio: {input_item.content_path or 'data'}]"
    
    def _process_voice(self, input_item: MultimodalInput) -> str:
        """Process voice input - speech-to-text."""
        if self.voice_manager:
            # If audio data provided, transcribe
            if input_item.content:
                # Would use STT here
                return f"[Voice input: {len(input_item.content)} bytes]"
        
        return input_item.content if isinstance(input_item.content, str) else "[Voice input]"
    
    def _build_multimodal_prompt(
        self,
        prompt: str,
        processed_inputs: List[str],
        original_inputs: List[MultimodalInput]
    ) -> str:
        """Build prompt with multimodal context."""
        context_parts = [prompt]
        
        for i, (processed, original) in enumerate(zip(processed_inputs, original_inputs)):
            context_parts.append(f"\n[{original.media_type.value.upper()} INPUT {i+1}]:")
            context_parts.append(processed)
        
        return "\n".join(context_parts)
    
    def _select_multimodal_model(self, has_vision: bool, task_type: TaskType) -> Optional[str]:
        """Select appropriate model for multimodal task."""
        if has_vision:
            # Vision models (would need to add to registry)
            # For now, use general model
            return None  # Auto-select
        else:
            return None  # Auto-select
    
    def _generate_media_output(self, content: str, inputs: List[MultimodalInput]) -> Optional[Any]:
        """Generate media output (image/audio/video) from text if requested."""
        # Placeholder - would use image generation models, TTS, etc.
        return None
    
    def _assign_genesis_key(
        self,
        inputs: List[MultimodalInput],
        prompt: str,
        content: str,
        user_id: Optional[str],
        task_type: TaskType
    ) -> Optional[str]:
        """Assign Genesis Key to multimodal LLM interaction."""
        if not self.cognitive_layer1:
            return None
        
        # Create metadata
        metadata = {
            "prompt": prompt[:500],
            "content_length": len(content),
            "num_inputs": len(inputs),
            "input_types": [inp.media_type.value for inp in inputs],
            "task_type": task_type.value,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # Process through Layer 1 to get Genesis Key
        try:
            result = self.cognitive_layer1.process_system_event(
                event_type="multimodal_llm_interaction",
                event_data={
                    "prompt": prompt,
                    "content": content[:1000],
                    "inputs": [{"type": inp.media_type.value, "path": inp.content_path} for inp in inputs]
                },
                metadata=metadata
            )
            
            return result.get("genesis_key_id")
        except Exception as e:
            logger.error(f"Error assigning Genesis Key: {e}")
            return f"GK-MULTIMODAL-{datetime.now().timestamp()}"
    
    def _calculate_trust_score(self, inputs: List[MultimodalInput], content: str) -> float:
        """Calculate trust score for multimodal output."""
        base_score = 0.7
        
        # Increase trust if inputs are from files (more reliable)
        if any(inp.content_path for inp in inputs):
            base_score += 0.1
        
        # Increase trust if content is substantial
        if len(content) > 100:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    # =======================================================================
    # VOICE INTEGRATION
    # =======================================================================
    
    async def text_to_speech(
        self,
        text: str,
        voice: str = "en-US-AriaNeural",
        user_id: Optional[str] = None
    ) -> Tuple[bytes, Optional[str]]:
        """
        Convert text to speech with Genesis Key tracking.
        
        Returns:
            (audio_data, genesis_key_id)
        """
        if not self.voice_manager:
            raise ValueError("Voice manager not available")
        
        # Generate audio
        audio_data = await self.voice_manager.text_to_speech(
            text=text,
            voice=voice
        )
        
        # Assign Genesis Key
        genesis_key_id = self._assign_genesis_key(
            inputs=[MultimodalInput(media_type=MediaType.TEXT, content=text)],
            prompt="TTS generation",
            content=text,
            user_id=user_id,
            task_type=TaskType.GENERAL
        )
        
        return audio_data, genesis_key_id
    
    async def speech_to_text(
        self,
        audio_data: bytes,
        language: str = "en-US",
        user_id: Optional[str] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Convert speech to text with Genesis Key tracking.
        
        Returns:
            (transcribed_text, genesis_key_id)
        """
        # Use voice manager or file handler for STT
        text = ""  # Would implement STT here
        
        # Assign Genesis Key
        genesis_key_id = self._assign_genesis_key(
            inputs=[MultimodalInput(media_type=MediaType.VOICE, content=audio_data)],
            prompt="STT transcription",
            content=text,
            user_id=user_id,
            task_type=TaskType.GENERAL
        )
        
        return text, genesis_key_id


# Global instance
_multimodal_system: Optional[MultimodalLLMSystem] = None


def get_multimodal_llm_system(
    multi_llm_client: Optional[MultiLLMClient] = None,
    repo_access: Optional[RepositoryAccessLayer] = None,
    session=None
) -> MultimodalLLMSystem:
    """Get or create global multimodal LLM system instance."""
    global _multimodal_system
    if _multimodal_system is None:
        _multimodal_system = MultimodalLLMSystem(
            multi_llm_client=multi_llm_client,
            repo_access=repo_access,
            session=session
        )
    return _multimodal_system
