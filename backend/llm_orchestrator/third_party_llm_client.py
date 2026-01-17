import logging
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

# Try to import third_party_llm_integration with fallback
try:
    from llm_orchestrator.third_party_llm_integration import (
        ThirdPartyLLMIntegration, 
        ThirdPartyLLMConfig, 
        LLMProvider, 
        SystemContextProvider, 
        get_third_party_llm_integration
    )
except ImportError:
    try:
        from third_party_llm_integration import (
            ThirdPartyLLMIntegration, 
            ThirdPartyLLMConfig, 
            LLMProvider, 
            SystemContextProvider, 
            get_third_party_llm_integration
        )
    except ImportError:
        # Make these optional - third party LLM is not required
        ThirdPartyLLMIntegration = None
        ThirdPartyLLMConfig = None
        LLMProvider = None
        SystemContextProvider = None
        get_third_party_llm_integration = None
        logger.warning("[THIRD-PARTY-LLM] third_party_llm_integration not available")


class ThirdPartyLLMClient:
    """
    Client for third-party LLM APIs.
    
    Supports:
    - Google Gemini
    - OpenAI GPT-4/3.5
    - Anthropic Claude
    - Custom APIs
    """
    
    def __init__(self):
        if get_third_party_llm_integration:
            try:
                self.integration = get_third_party_llm_integration()
            except Exception as e:
                logger.warning(f"[THIRD-PARTY-LLM] Failed to initialize integration: {e}")
                self.integration = None
        else:
            self.integration = None
        
        if SystemContextProvider:
            try:
                self.context_provider = SystemContextProvider()
            except Exception as e:
                logger.warning(f"[THIRD-PARTY-LLM] Failed to initialize context provider: {e}")
                self.context_provider = None
        else:
            self.context_provider = None
        
        self.llm_handlers: Dict[str, Callable] = {}
    
    def register_gemini(
        self,
        api_key: str,
        model_name: str = "gemini-pro",
        base_url: Optional[str] = None
    ) -> str:
        """
        Register Google Gemini LLM.
        
        Args:
            api_key: Gemini API key
            model_name: Model name (default: gemini-pro)
            base_url: Custom base URL (optional)
        
        Returns:
            LLM ID if successful
        """
        config = ThirdPartyLLMConfig(
            provider=LLMProvider.GEMINI,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or "https://generativelanguage.googleapis.com/v1beta"
        )
        
        def generate_fn(prompt: str, system_prompt: Optional[str] = None, kwargs: Optional[Dict] = None) -> str:
            return self._call_gemini(config, prompt, system_prompt, kwargs or {})
        
        result = self.integration.register_llm(config, generate_fn)
        
        if result.success:
            self.llm_handlers[result.llm_id] = generate_fn
            return result.llm_id
        else:
            raise Exception(f"Failed to register Gemini: {result.errors}")
    
    def register_openai(
        self,
        api_key: str,
        model_name: str = "gpt-4",
        base_url: Optional[str] = None
    ) -> str:
        """
        Register OpenAI LLM.
        
        Args:
            api_key: OpenAI API key
            model_name: Model name (default: gpt-4)
            base_url: Custom base URL (optional)
        
        Returns:
            LLM ID if successful
        """
        config = ThirdPartyLLMConfig(
            provider=LLMProvider.OPENAI,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or "https://api.openai.com/v1"
        )
        
        def generate_fn(prompt: str, system_prompt: Optional[str] = None, kwargs: Optional[Dict] = None) -> str:
            return self._call_openai(config, prompt, system_prompt, kwargs or {})
        
        result = self.integration.register_llm(config, generate_fn)
        
        if result.success:
            self.llm_handlers[result.llm_id] = generate_fn
            return result.llm_id
        else:
            raise Exception(f"Failed to register OpenAI: {result.errors}")
    
    def register_anthropic(
        self,
        api_key: str,
        model_name: str = "claude-3-opus-20240229",
        base_url: Optional[str] = None
    ) -> str:
        """
        Register Anthropic Claude LLM.
        
        Args:
            api_key: Anthropic API key
            model_name: Model name
            base_url: Custom base URL (optional)
        
        Returns:
            LLM ID if successful
        """
        config = ThirdPartyLLMConfig(
            provider=LLMProvider.ANTHROPIC,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url or "https://api.anthropic.com/v1"
        )
        
        def generate_fn(prompt: str, system_prompt: Optional[str] = None, kwargs: Optional[Dict] = None) -> str:
            return self._call_anthropic(config, prompt, system_prompt, kwargs or {})
        
        result = self.integration.register_llm(config, generate_fn)
        
        if result.success:
            self.llm_handlers[result.llm_id] = generate_fn
            return result.llm_id
        else:
            raise Exception(f"Failed to register Anthropic: {result.errors}")
    
    def register_custom(
        self,
        model_name: str,
        generate_fn: Callable[[str, Optional[str], Optional[Dict]], str],
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ) -> str:
        """
        Register custom LLM.
        
        Args:
            model_name: Model name
            generate_fn: Function to call LLM
            api_key: API key (optional)
            base_url: Base URL (optional)
        
        Returns:
            LLM ID if successful
        """
        config = ThirdPartyLLMConfig(
            provider=LLMProvider.CUSTOM,
            model_name=model_name,
            api_key=api_key,
            base_url=base_url
        )
        
        result = self.integration.register_llm(config, generate_fn)
        
        if result.success:
            self.llm_handlers[result.llm_id] = generate_fn
            return result.llm_id
        else:
            raise Exception(f"Failed to register custom LLM: {result.errors}")
    
    def generate(
        self,
        llm_id: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate response from registered LLM.
        
        Args:
            llm_id: Registered LLM ID
            prompt: User prompt
            system_prompt: System prompt (optional, will use system context if not provided)
            **kwargs: Additional parameters
        
        Returns:
            LLM response
        """
        if llm_id not in self.llm_handlers:
            raise ValueError(f"LLM {llm_id} not registered")
        
        if not self.integration.is_integrated(llm_id):
            raise ValueError(f"LLM {llm_id} not integrated (handshake failed)")
        
        # Use system context if no system prompt provided
        if system_prompt is None:
            system_prompt = self.context_provider.get_complete_system_context()
        
        handler = self.llm_handlers[llm_id]
        return handler(prompt, system_prompt, kwargs)
    
    def _call_gemini(
        self,
        config: ThirdPartyLLMConfig,
        prompt: str,
        system_prompt: Optional[str] = None,
        kwargs: Dict[str, Any] = None
    ) -> str:
        """Call Gemini API."""
        kwargs = kwargs or {}
        
        url = f"{config.base_url}/models/{config.model_name}:generateContent"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        if config.api_key:
            headers["x-goog-api-key"] = config.api_key
        
        # Combine system prompt and user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\nUser Query: {prompt}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": full_prompt
                }]
            }],
            "generationConfig": {
                "temperature": kwargs.get("temperature", config.temperature),
                "maxOutputTokens": kwargs.get("max_tokens", config.max_tokens)
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=config.timeout_seconds)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract text from Gemini response
            if "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        return parts[0]["text"]
            
            raise Exception("Unexpected Gemini response format")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[GEMINI] API error: {e}")
            raise Exception(f"Gemini API error: {e}")
    
    def _call_openai(
        self,
        config: ThirdPartyLLMConfig,
        prompt: str,
        system_prompt: Optional[str] = None,
        kwargs: Dict[str, Any] = None
    ) -> str:
        """Call OpenAI API."""
        kwargs = kwargs or {}
        
        url = f"{config.base_url}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": config.model_name,
            "messages": messages,
            "temperature": kwargs.get("temperature", config.temperature),
            "max_tokens": kwargs.get("max_tokens", config.max_tokens)
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=config.timeout_seconds)
            response.raise_for_status()
            
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                choice = data["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]
            
            raise Exception("Unexpected OpenAI response format")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[OPENAI] API error: {e}")
            raise Exception(f"OpenAI API error: {e}")
    
    def _call_anthropic(
        self,
        config: ThirdPartyLLMConfig,
        prompt: str,
        system_prompt: Optional[str] = None,
        kwargs: Dict[str, Any] = None
    ) -> str:
        """Call Anthropic API."""
        kwargs = kwargs or {}
        
        url = f"{config.base_url}/messages"
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": config.model_name,
            "max_tokens": kwargs.get("max_tokens", config.max_tokens),
            "temperature": kwargs.get("temperature", config.temperature),
            "messages": [{
                "role": "user",
                "content": prompt
            }]
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=config.timeout_seconds)
            response.raise_for_status()
            
            data = response.json()
            
            if "content" in data and len(data["content"]) > 0:
                content_block = data["content"][0]
                if "text" in content_block:
                    return content_block["text"]
            
            raise Exception("Unexpected Anthropic response format")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[ANTHROPIC] API error: {e}")
            raise Exception(f"Anthropic API error: {e}")


# Singleton instance
_third_party_client: Optional[ThirdPartyLLMClient] = None


def get_third_party_llm_client() -> ThirdPartyLLMClient:
    """Get singleton third-party LLM client instance."""
    global _third_party_client
    if _third_party_client is None:
        _third_party_client = ThirdPartyLLMClient()
    return _third_party_client
