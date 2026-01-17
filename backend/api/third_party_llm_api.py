import logging
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from llm_orchestrator.third_party_llm_client import get_third_party_llm_client
from llm_orchestrator.third_party_llm_integration import LLMProvider
class RegisterGeminiRequest(BaseModel):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Request to register Google Gemini."""
    api_key: str = Field(..., description="Gemini API key")
    model_name: str = Field(default="gemini-pro", description="Model name")
    base_url: Optional[str] = Field(None, description="Custom base URL")


class RegisterOpenAIRequest(BaseModel):
    """Request to register OpenAI."""
    api_key: str = Field(..., description="OpenAI API key")
    model_name: str = Field(default="gpt-4", description="Model name")
    base_url: Optional[str] = Field(None, description="Custom base URL")


class RegisterAnthropicRequest(BaseModel):
    """Request to register Anthropic Claude."""
    api_key: str = Field(..., description="Anthropic API key")
    model_name: str = Field(default="claude-3-opus-20240229", description="Model name")
    base_url: Optional[str] = Field(None, description="Custom base URL")


class GenerateRequest(BaseModel):
    """Request to generate response from registered LLM."""
    llm_id: str = Field(..., description="Registered LLM ID")
    prompt: str = Field(..., description="User prompt")
    system_prompt: Optional[str] = Field(None, description="System prompt (optional, uses system context if not provided)")
    temperature: Optional[float] = Field(None, description="Temperature")
    max_tokens: Optional[int] = Field(None, description="Max tokens")


class RegisterResponse(BaseModel):
    """Response from LLM registration."""
    success: bool
    llm_id: Optional[str] = None
    handshake_passed: bool
    capabilities: Dict[str, Any]
    errors: list[str] = []


class GenerateResponse(BaseModel):
    """Response from LLM generation."""
    success: bool
    content: Optional[str] = None
    llm_id: str
    error: Optional[str] = None


# ========================================================================
# API ENDPOINTS
# ========================================================================

@router.post("/register/gemini", response_model=RegisterResponse)
async def register_gemini(request: RegisterGeminiRequest):
    """
    Register Google Gemini LLM with automatic handshake.
    
    The LLM will immediately receive:
    - Complete system architecture
    - All rules and governance policies
    - Available APIs and scripts
    - Integration protocols
    """
    try:
        client = get_third_party_llm_client()
        llm_id = client.register_gemini(
            api_key=request.api_key,
            model_name=request.model_name,
            base_url=request.base_url
        )
        
        # Get handshake result
        integration = client.integration
        handshake_result = integration.get_handshake_result(llm_id)
        
        return RegisterResponse(
            success=True,
            llm_id=llm_id,
            handshake_passed=handshake_result.integration_test_passed if handshake_result else False,
            capabilities=handshake_result.capabilities if handshake_result else {},
            errors=handshake_result.errors if handshake_result else []
        )
    except Exception as e:
        logger.error(f"Failed to register Gemini: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register/openai", response_model=RegisterResponse)
async def register_openai(request: RegisterOpenAIRequest):
    """
    Register OpenAI LLM with automatic handshake.
    
    The LLM will immediately receive:
    - Complete system architecture
    - All rules and governance policies
    - Available APIs and scripts
    - Integration protocols
    """
    try:
        client = get_third_party_llm_client()
        llm_id = client.register_openai(
            api_key=request.api_key,
            model_name=request.model_name,
            base_url=request.base_url
        )
        
        # Get handshake result
        integration = client.integration
        handshake_result = integration.get_handshake_result(llm_id)
        
        return RegisterResponse(
            success=True,
            llm_id=llm_id,
            handshake_passed=handshake_result.integration_test_passed if handshake_result else False,
            capabilities=handshake_result.capabilities if handshake_result else {},
            errors=handshake_result.errors if handshake_result else []
        )
    except Exception as e:
        logger.error(f"Failed to register OpenAI: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register/anthropic", response_model=RegisterResponse)
async def register_anthropic(request: RegisterAnthropicRequest):
    """
    Register Anthropic Claude LLM with automatic handshake.
    
    The LLM will immediately receive:
    - Complete system architecture
    - All rules and governance policies
    - Available APIs and scripts
    - Integration protocols
    """
    try:
        client = get_third_party_llm_client()
        llm_id = client.register_anthropic(
            api_key=request.api_key,
            model_name=request.model_name,
            base_url=request.base_url
        )
        
        # Get handshake result
        integration = client.integration
        handshake_result = integration.get_handshake_result(llm_id)
        
        return RegisterResponse(
            success=True,
            llm_id=llm_id,
            handshake_passed=handshake_result.integration_test_passed if handshake_result else False,
            capabilities=handshake_result.capabilities if handshake_result else {},
            errors=handshake_result.errors if handshake_result else []
        )
    except Exception as e:
        logger.error(f"Failed to register Anthropic: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Generate response from registered third-party LLM.
    
    The LLM will automatically:
    - Use system context if no system prompt provided
    - Follow all GRACE rules
    - Be validated through hallucination prevention
    - Be tracked with Genesis Keys
    """
    try:
        client = get_third_party_llm_client()
        
        kwargs = {}
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature
        if request.max_tokens is not None:
            kwargs["max_tokens"] = request.max_tokens
        
        content = client.generate(
            llm_id=request.llm_id,
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            **kwargs
        )
        
        return GenerateResponse(
            success=True,
            content=content,
            llm_id=request.llm_id
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_integrated_llms():
    """List all integrated third-party LLMs."""
    try:
        client = get_third_party_llm_client()
        integration = client.integration
        
        llm_ids = integration.get_integrated_llms()
        
        results = []
        for llm_id in llm_ids:
            handshake_result = integration.get_handshake_result(llm_id)
            if handshake_result:
                results.append({
                    "llm_id": llm_id,
                    "provider": handshake_result.provider.value,
                    "model_name": handshake_result.model_name,
                    "handshake_passed": handshake_result.integration_test_passed,
                    "capabilities": handshake_result.capabilities,
                    "handshake_timestamp": handshake_result.handshake_timestamp.isoformat()
                })
        
        return {"integrated_llms": results}
    except Exception as e:
        logger.error(f"Failed to list LLMs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
