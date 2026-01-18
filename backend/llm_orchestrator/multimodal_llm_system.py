import logging
import os
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

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    from diffusers import StableDiffusionPipeline
    import torch
    DIFFUSERS_AVAILABLE = True
except ImportError:
    DIFFUSERS_AVAILABLE = False

class MediaType(Enum):
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
        
        self.vision_model = os.environ.get("GRACE_VISION_MODEL", "llava")
        self.image_model = os.environ.get("GRACE_IMAGE_MODEL", "dalle")
        self.tts_model = os.environ.get("GRACE_TTS_MODEL", "local")
        
        self._sd_pipeline = None
        self._tts_engine = None
        
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
            try:
                with open(input_item.content_path, 'rb') as f:
                    image_data = f.read()
            except Exception as e:
                logger.error(f"Error reading image: {e}")
                return f"[Image file: {input_item.content_path}]"
        else:
            image_data = input_item.content
        
        result = self.analyze_image(image_data, "Describe this image in detail.")
        if result.get("success"):
            return f"[Image Analysis: {result.get('description', '')}]"
        return f"[Image: {len(image_data) if image_data else 0} bytes]"
    
    def analyze_image(self, image_path: str, prompt: str) -> Dict[str, Any]:
        """
        Analyze image using vision model.
        
        Args:
            image_path: Path to image file or base64 encoded image bytes
            prompt: Question/prompt about the image
            
        Returns:
            Dict with 'success', 'description', 'model', 'error'
        """
        if isinstance(image_path, bytes):
            image_data = image_path
            image_b64 = base64.b64encode(image_data).decode('utf-8')
        elif isinstance(image_path, str):
            if image_path.startswith("data:") or len(image_path) > 500:
                image_b64 = image_path.split(",")[-1] if "," in image_path else image_path
            else:
                try:
                    with open(image_path, 'rb') as f:
                        image_data = f.read()
                    image_b64 = base64.b64encode(image_data).decode('utf-8')
                except Exception as e:
                    return {"success": False, "error": f"Failed to read image: {e}"}
        else:
            return {"success": False, "error": "Invalid image input type"}
        
        if self.vision_model in ("gpt4v", "gpt-4-vision", "gpt-4o"):
            return self._analyze_with_openai_vision(image_b64, prompt)
        elif self.vision_model == "claude":
            return self._analyze_with_claude_vision(image_b64, prompt)
        elif self.vision_model in ("llava", "bakllava", "minicpm-v"):
            return self._analyze_with_ollama_vision(image_b64, prompt)
        else:
            return {"success": False, "error": f"Vision model '{self.vision_model}' not configured"}
    
    def _analyze_with_openai_vision(self, image_b64: str, prompt: str) -> Dict[str, Any]:
        """Analyze image using OpenAI GPT-4 Vision."""
        if not OPENAI_AVAILABLE:
            return {"success": False, "error": "OpenAI library not installed"}
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return {"success": False, "error": "OPENAI_API_KEY not set"}
        
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                    ]
                }],
                max_tokens=1000
            )
            description = response.choices[0].message.content
            return {"success": True, "description": description, "model": "gpt-4o"}
        except Exception as e:
            logger.error(f"OpenAI vision error: {e}")
            return {"success": False, "error": str(e)}
    
    def _analyze_with_claude_vision(self, image_b64: str, prompt: str) -> Dict[str, Any]:
        """Analyze image using Claude Vision."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return {"success": False, "error": "ANTHROPIC_API_KEY not set"}
        
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            )
            description = response.content[0].text
            return {"success": True, "description": description, "model": "claude-3-5-sonnet"}
        except ImportError:
            return {"success": False, "error": "anthropic library not installed"}
        except Exception as e:
            logger.error(f"Claude vision error: {e}")
            return {"success": False, "error": str(e)}
    
    def _analyze_with_ollama_vision(self, image_b64: str, prompt: str) -> Dict[str, Any]:
        """Analyze image using local Ollama vision model (LLaVA, etc.)."""
        import requests
        
        ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
        model = self.vision_model if self.vision_model != "llava" else "llava:latest"
        
        try:
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "images": [image_b64], "stream": False},
                timeout=120
            )
            if response.status_code == 200:
                result = response.json()
                return {"success": True, "description": result.get("response", ""), "model": model}
            else:
                return {"success": False, "error": f"Ollama returned {response.status_code}"}
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": "Ollama not running at " + ollama_url}
        except Exception as e:
            logger.error(f"Ollama vision error: {e}")
            return {"success": False, "error": str(e)}
    
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
        has_voice_input = any(inp.media_type == MediaType.VOICE for inp in inputs)
        if has_voice_input:
            tts_result = self.text_to_speech_sync(content)
            if tts_result.get("success"):
                return {"type": "audio", "data": tts_result.get("audio_data")}
        return None
    
    def generate_image(self, prompt: str, size: str = "1024x1024") -> Dict[str, Any]:
        """
        Generate image from text prompt.
        
        Args:
            prompt: Text description for image generation
            size: Image size (e.g., "1024x1024", "512x512")
            
        Returns:
            Dict with 'success', 'image_data' or 'image_url', 'model', 'error'
        """
        if self.image_model in ("dalle", "dall-e", "dall-e-3"):
            return self._generate_with_dalle(prompt, size)
        elif self.image_model in ("sd", "stable-diffusion", "sdxl"):
            return self._generate_with_stable_diffusion(prompt, size)
        else:
            return {"success": False, "error": f"Image model '{self.image_model}' not configured"}
    
    def _generate_with_dalle(self, prompt: str, size: str) -> Dict[str, Any]:
        """Generate image using OpenAI DALL-E."""
        if not OPENAI_AVAILABLE:
            return {"success": False, "error": "OpenAI library not installed"}
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return {"success": False, "error": "OPENAI_API_KEY not set"}
        
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size if size in ("1024x1024", "1024x1792", "1792x1024") else "1024x1024",
                quality="standard",
                n=1
            )
            image_url = response.data[0].url
            return {"success": True, "image_url": image_url, "model": "dall-e-3"}
        except Exception as e:
            logger.error(f"DALL-E generation error: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_with_stable_diffusion(self, prompt: str, size: str) -> Dict[str, Any]:
        """Generate image using local Stable Diffusion."""
        if not DIFFUSERS_AVAILABLE:
            return {"success": False, "error": "diffusers library not installed"}
        
        try:
            if self._sd_pipeline is None:
                model_id = os.environ.get("SD_MODEL_ID", "stabilityai/stable-diffusion-xl-base-1.0")
                self._sd_pipeline = StableDiffusionPipeline.from_pretrained(
                    model_id,
                    torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32
                )
                if torch.cuda.is_available():
                    self._sd_pipeline = self._sd_pipeline.to("cuda")
            
            width, height = 1024, 1024
            if "x" in size:
                parts = size.split("x")
                width, height = int(parts[0]), int(parts[1])
            
            image = self._sd_pipeline(prompt, width=width, height=height).images[0]
            
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            image_data = buffer.getvalue()
            
            return {"success": True, "image_data": image_data, "model": "stable-diffusion"}
        except Exception as e:
            logger.error(f"Stable Diffusion error: {e}")
            return {"success": False, "error": str(e)}
    
    def text_to_speech_sync(self, text: str, voice: str = "default") -> Dict[str, Any]:
        """
        Convert text to speech (synchronous version).
        
        Args:
            text: Text to convert to speech
            voice: Voice identifier
            
        Returns:
            Dict with 'success', 'audio_data', 'model', 'error'
        """
        if self.tts_model in ("openai", "openai-tts"):
            return self._tts_with_openai(text, voice)
        elif self.tts_model in ("local", "pyttsx3"):
            return self._tts_with_pyttsx3(text, voice)
        else:
            return {"success": False, "error": f"TTS model '{self.tts_model}' not configured"}
    
    def _tts_with_openai(self, text: str, voice: str) -> Dict[str, Any]:
        """Convert text to speech using OpenAI TTS."""
        if not OPENAI_AVAILABLE:
            return {"success": False, "error": "OpenAI library not installed"}
        
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return {"success": False, "error": "OPENAI_API_KEY not set"}
        
        try:
            client = openai.OpenAI(api_key=api_key)
            voice_id = voice if voice in ("alloy", "echo", "fable", "onyx", "nova", "shimmer") else "alloy"
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice_id,
                input=text
            )
            audio_data = response.content
            return {"success": True, "audio_data": audio_data, "model": "openai-tts"}
        except Exception as e:
            logger.error(f"OpenAI TTS error: {e}")
            return {"success": False, "error": str(e)}
    
    def _tts_with_pyttsx3(self, text: str, voice: str) -> Dict[str, Any]:
        """Convert text to speech using local pyttsx3."""
        if not PYTTSX3_AVAILABLE:
            return {"success": False, "error": "pyttsx3 library not installed"}
        
        try:
            if self._tts_engine is None:
                self._tts_engine = pyttsx3.init()
            
            if voice != "default":
                voices = self._tts_engine.getProperty('voices')
                for v in voices:
                    if voice.lower() in v.name.lower():
                        self._tts_engine.setProperty('voice', v.id)
                        break
            
            buffer = io.BytesIO()
            temp_file = Path(os.environ.get("TEMP", "/tmp")) / f"tts_{datetime.now().timestamp()}.wav"
            
            self._tts_engine.save_to_file(text, str(temp_file))
            self._tts_engine.runAndWait()
            
            if temp_file.exists():
                audio_data = temp_file.read_bytes()
                temp_file.unlink()
                return {"success": True, "audio_data": audio_data, "model": "pyttsx3"}
            else:
                return {"success": False, "error": "Failed to generate audio file"}
        except Exception as e:
            logger.error(f"pyttsx3 TTS error: {e}")
            return {"success": False, "error": str(e)}
    
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
        voice: str = "default",
        user_id: Optional[str] = None
    ) -> Tuple[bytes, Optional[str]]:
        """
        Convert text to speech with Genesis Key tracking (async version).
        
        Returns:
            (audio_data, genesis_key_id)
        """
        if self.voice_manager:
            audio_data = await self.voice_manager.text_to_speech(text=text, voice=voice)
        else:
            result = self.text_to_speech_sync(text, voice)
            if not result.get("success"):
                raise ValueError(result.get("error", "TTS not available"))
            audio_data = result.get("audio_data", b"")
        
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
