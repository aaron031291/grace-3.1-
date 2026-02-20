"""
Base LLM Client Interface for multi-provider support.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union

class BaseLLMClient(ABC):
    """
    Abstract base class for all LLM clients (Ollama, OpenAI, etc.).
    """
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """
        Generate a text response for a given prompt.
        """
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        temperature: Optional[float] = None,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        """
        Chat interaction with a list of messages.
        """
        pass

    @abstractmethod
    def is_running(self) -> bool:
        """
        Check if the LLM service is available.
        """
        pass

    @abstractmethod
    def get_all_models(self) -> List[Dict[str, Any]]:
        """
        List all available models for this provider.
        """
        pass

    @abstractmethod
    def model_exists(self, model_name: str) -> bool:
        """
        Check if a specific model exists.
        """
        pass
