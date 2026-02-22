"""
Ollama client module for detecting running models and generating responses.

Classes:
- `ModelStatus`
- `Model`
- `OllamaClient`

Key Methods:
- `is_running()`
- `get_all_models()`
- `get_running_models()`
- `model_exists()`
- `is_model_running()`
- `get_model_info()`
- `generate_response()`
- `generate_response_with_context()`
- `pull_model()`
- `delete_model()`
- `chat()`
- `get_model_info_detailed()`
- `get_ollama_client()`
"""

import json
import subprocess
import requests
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Import settings
try:
    from settings import settings
    USE_SETTINGS = True
except ImportError:
    USE_SETTINGS = False


class ModelStatus(Enum):
    """Status of a model."""
    RUNNING = "running"
    AVAILABLE = "available"
    NOT_INSTALLED = "not_installed"


@dataclass
class Model:
    """Represents an Ollama model."""
    name: str
    digest: str
    size: int
    modified_at: str
    status: ModelStatus = ModelStatus.AVAILABLE
    
    def __str__(self) -> str:
        return f"{self.name} ({self._format_size()})"
    
    def _format_size(self) -> str:
        """Format size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if self.size < 512:
                return f"{self.size:.2f}{unit}"
            self.size /= 512
        return f"{self.size:.2f}TB"


class OllamaClient:
    """Client for interacting with Ollama service."""
    
    def __init__(self, base_url: str = None):
        """
        Initialize Ollama client.
        
        Args:
            base_url: The base URL of the Ollama service. If None, uses settings or default
        """
        if base_url is None:
            if USE_SETTINGS:
                base_url = settings.OLLAMA_URL
            else:
                base_url = "http://localhost:11434"
        
        self.base_url = base_url
        self.api_list_url = f"{base_url}/api/tags"
        self.api_generate_url = f"{base_url}/api/generate"
        self.api_show_url = f"{base_url}/api/show"
        self.api_ps_url = f"{base_url}/api/ps"
    
    def is_running(self) -> bool:
        """
        Check if Ollama service is running.
        
        Returns:
            bool: True if service is accessible, False otherwise
        """
        try:
            response = requests.get(self.base_url, timeout=5)
            return response.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False
        except Exception:
            return False
    
    def get_all_models(self) -> List[Model]:
        """
        Get all available models from Ollama.
        
        Returns:
            List[Model]: List of all installed models
            
        Raises:
            ConnectionError: If unable to connect to Ollama service
            requests.RequestException: If API request fails
        """
        try:
            response = requests.get(self.api_list_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            models = []
            if "models" in data:
                for model_data in data["models"]:
                    model = Model(
                        name=model_data.get("name", ""),
                        digest=model_data.get("digest", ""),
                        size=model_data.get("size", 0),
                        modified_at=model_data.get("modified_at", ""),
                        status=ModelStatus.AVAILABLE
                    )
                    models.append(model)
            
            return models
        except requests.ConnectionError:
            raise ConnectionError(f"Failed to connect to Ollama service at {self.base_url}")
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch models: {e}")
    
    def get_running_models(self) -> List[str]:
        """
        Get list of models currently running in memory.
        
        Returns:
            List[str]: List of model names that are currently running
            
        Raises:
            ConnectionError: If unable to connect to Ollama service
            requests.RequestException: If API request fails
        """
        try:
            response = requests.get(self.api_ps_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            running_models = []
            if "models" in data:
                running_models = [model.get("name", "") for model in data["models"]]
            
            return running_models
        except requests.ConnectionError:
            raise ConnectionError(f"Failed to connect to Ollama service at {self.base_url}")
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to fetch running models: {e}")
    
    def model_exists(self, model_name: str) -> bool:
        """
        Check if a model is installed.
        
        Args:
            model_name: The name of the model to check
            
        Returns:
            bool: True if model exists, False otherwise
        """
        try:
            models = self.get_all_models()
            return any(m.name == model_name for m in models)
        except Exception:
            return False
    
    def is_model_running(self, model_name: str) -> bool:
        """
        Check if a specific model is currently running.
        
        Args:
            model_name: The name of the model to check
            
        Returns:
            bool: True if model is running, False otherwise
        """
        try:
            running_models = self.get_running_models()
            return model_name in running_models
        except Exception:
            return False
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific model.
        
        Args:
            model_name: The name of the model
            
        Returns:
            Dict: Model information including parameters, template, etc.
            
        Raises:
            ConnectionError: If unable to connect to Ollama service
            ValueError: If model doesn't exist
            requests.RequestException: If API request fails
        """
        try:
            params = {"name": model_name}
            response = requests.post(self.api_show_url, json=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.ConnectionError:
            raise ConnectionError(f"Failed to connect to Ollama service at {self.base_url}")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Model '{model_name}' not found")
            raise requests.RequestException(f"Failed to fetch model info: {e}")
    
    def generate_response(
        self,
        model: str,
        prompt: str,
        stream: bool = False,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        num_predict: Optional[int] = None,
        context: Optional[List[int]] = None,
    ) -> str:
        """
        Generate a response from a model.
        
        Args:
            model: The model name to use
            prompt: The prompt/question to send
            stream: Whether to stream the response
            temperature: Controls randomness (0-1, higher = more random)
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            num_predict: Maximum tokens to generate
            context: Context tokens from previous interactions
            
        Returns:
            str: The generated response
            
        Raises:
            ValueError: If model doesn't exist
            ConnectionError: If unable to connect to Ollama service
            requests.RequestException: If API request fails
        """
        if not self.model_exists(model):
            raise ValueError(f"Model '{model}' not found. Available models: {self.get_all_models()}")
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
            }
        }
        
        if num_predict is not None:
            payload["options"]["num_predict"] = num_predict
        
        if context is not None:
            payload["context"] = context
        
        try:
            response = requests.post(
                self.api_generate_url,
                json=payload,
                timeout=300,  # Long timeout for model inference
                stream=stream
            )
            response.raise_for_status()
            
            if stream:
                return self._process_streamed_response(response)
            else:
                return response.json().get("response", "")
        
        except requests.ConnectionError:
            raise ConnectionError(f"Failed to connect to Ollama service at {self.base_url}")
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to generate response: {e}")
    
    def _process_streamed_response(self, response: requests.Response) -> str:
        """
        Process a streamed response from Ollama.
        
        Args:
            response: The response object with streaming enabled
            
        Returns:
            str: The complete response text
        """
        full_response = ""
        try:
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        full_response += chunk.get("response", "")
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            raise requests.RequestException(f"Error processing streamed response: {e}")
        
        return full_response
    
    def generate_response_with_context(
        self,
        model: str,
        prompt: str,
        context: Optional[List[int]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a response and return both response and context for follow-up.
        
        Args:
            model: The model name to use
            prompt: The prompt/question to send
            context: Previous context tokens
            **kwargs: Additional arguments to pass to generate_response
            
        Returns:
            Dict with 'response' and 'context' keys for multi-turn conversations
            
        Raises:
            ValueError: If model doesn't exist
            ConnectionError: If unable to connect to Ollama service
            requests.RequestException: If API request fails
        """
        if not self.model_exists(model):
            raise ValueError(f"Model '{model}' not found")
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        
        if context is not None:
            payload["context"] = context
        
        # Merge additional options
        payload["options"] = kwargs.get("options", {})
        for key in ["temperature", "top_p", "top_k", "num_predict"]:
            if key in kwargs:
                payload["options"][key] = kwargs[key]
        
        try:
            response = requests.post(
                self.api_generate_url,
                json=payload,
                timeout=300
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "response": data.get("response", ""),
                "context": data.get("context", [])
            }
        except requests.ConnectionError:
            raise ConnectionError(f"Failed to connect to Ollama service at {self.base_url}")
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to generate response with context: {e}")
    
    def pull_model(self, model_name: str) -> bool:
        """
        Pull/download a model from registry.
        
        Args:
            model_name: The model to pull
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = subprocess.run(
                ["ollama", "pull", model_name],
                capture_output=True,
                timeout=600,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            raise ConnectionError("Ollama CLI not found")
        except subprocess.TimeoutExpired:
            return False
        except Exception as e:
            raise Exception(f"Failed to pull model: {e}")
    
    def delete_model(self, model_name: str) -> bool:
        """
        Delete a model.
        
        Args:
            model_name: The model to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            result = subprocess.run(
                ["ollama", "rm", model_name],
                capture_output=True,
                timeout=30,
                text=True
            )
            return result.returncode == 0
        except FileNotFoundError:
            raise ConnectionError("Ollama CLI not found")
        except Exception as e:
            raise Exception(f"Failed to delete model: {e}")
    
    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = False,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        num_predict: Optional[int] = None,
    ) -> str:
        """
        Generate a response using Ollama's chat endpoint.
        
        Args:
            model: The model name to use
            messages: List of message dicts with 'role' and 'content' keys.
                     Roles can be 'user', 'assistant', or 'system'
                     Example: [
                         {"role": "system", "content": "You are a helpful assistant"},
                         {"role": "user", "content": "Hello"},
                         {"role": "assistant", "content": "Hi! How can I help?"},
                         {"role": "user", "content": "Tell me a joke"}
                     ]
            stream: Whether to stream the response
            temperature: Controls randomness (0-1, higher = more random)
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            num_predict: Maximum tokens to generate
            
        Returns:
            str: The generated response
            
        Raises:
            ValueError: If model doesn't exist
            ConnectionError: If unable to connect to Ollama service
            requests.RequestException: If API request fails
        """
        if not self.model_exists(model):
            raise ValueError(f"Model '{model}' not found. Available models: {self.get_all_models()}")
        
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
            }
        }
        
        if num_predict is not None:
            payload["options"]["num_predict"] = num_predict
        
        api_chat_url = f"{self.base_url}/api/chat"
        
        try:
            response = requests.post(
                api_chat_url,
                json=payload,
                timeout=300,  # Long timeout for model inference
                stream=stream
            )
            response.raise_for_status()
            
            if stream:
                return self._process_streamed_response(response)
            else:
                return response.json().get("message", {}).get("content", "")
        
        except requests.ConnectionError:
            raise ConnectionError(f"Failed to connect to Ollama service at {self.base_url}")
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to generate chat response: {e}")
    
    def get_model_info_detailed(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed model information in a user-friendly format.
        
        Args:
            model_name: The name of the model
            
        Returns:
            Dict with formatted model info or None if not found
        """
        try:
            info = self.get_model_info(model_name)
            models = self.get_all_models()
            model = next((m for m in models if m.name == model_name), None)
            
            if model:
                info["size_formatted"] = str(model)
                info["status"] = "running" if self.is_model_running(model_name) else "available"
            
            return info
        except Exception:
            return None


# Convenience functions
def get_ollama_client(base_url: str = None) -> OllamaClient:
    """
    Factory function to create an Ollama client.
    
    Args:
        base_url: The base URL of the Ollama service. If None, uses settings or default
    """
    if base_url is None and USE_SETTINGS:
        base_url = settings.OLLAMA_URL
    return OllamaClient(base_url)
