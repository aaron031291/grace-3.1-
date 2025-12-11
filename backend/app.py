"""
Grace API - FastAPI application for Ollama-based chat and embeddings.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import time
from contextlib import asynccontextmanager

from ollama_client.client import get_ollama_client

try:
    from settings import settings
except ImportError:
    settings = None


# ==================== Pydantic Models ====================

class Message(BaseModel):
    """Represents a single message in a conversation."""
    role: str = Field(..., description="Role of the message sender: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="The content of the message")


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    messages: List[Message] = Field(..., description="List of messages in conversation history")
    model: Optional[str] = Field(
        None,
        description="Model to use. If not provided, uses OLLAMA_LLM_DEFAULT from settings"
    )
    temperature: Optional[float] = Field(
        0.7,
        ge=0.0,
        le=2.0,
        description="Controls randomness of responses (0.0-2.0). Higher = more random"
    )
    top_p: Optional[float] = Field(
        0.9,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter (0.0-1.0)"
    )
    top_k: Optional[int] = Field(
        40,
        ge=0,
        description="Top-k sampling parameter"
    )
    num_predict: Optional[int] = Field(
        None,
        ge=1,
        description="Maximum number of tokens to generate"
    )


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    message: str = Field(..., description="The generated response from the model")
    model: str = Field(..., description="The model that generated the response")
    generation_time: float = Field(..., description="Time taken to generate response in seconds")
    prompt_tokens: Optional[int] = Field(None, description="Number of tokens in the prompt")
    response_tokens: Optional[int] = Field(None, description="Number of tokens in the response")


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    status: str = Field(..., description="Health status: 'healthy' or 'unhealthy'")
    ollama_running: bool = Field(..., description="Whether Ollama service is running")
    models_available: int = Field(..., description="Number of available models")


# ==================== Lifespan ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown events."""
    # Startup
    print("🚀 Grace API starting up...")
    try:
        client = get_ollama_client()
        if client.is_running():
            models = client.get_all_models()
            print(f"✓ Ollama is running with {len(models)} model(s)")
        else:
            print("⚠ Ollama is not running - chat endpoint will be unavailable")
    except Exception as e:
        print(f"⚠ Could not connect to Ollama: {e}")
    
    yield
    
    # Shutdown
    print("👋 Grace API shutting down...")


# ==================== FastAPI App ====================

app = FastAPI(
    title="Grace API",
    description="API for Ollama-based chat and embeddings",
    version="0.1.0",
    lifespan=lifespan
)


# ==================== Health Check Endpoint ====================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        HealthResponse: Status of the API and Ollama service
    """
    try:
        client = get_ollama_client()
        ollama_running = client.is_running()
        
        if ollama_running:
            models = client.get_all_models()
            models_available = len(models)
            status = "healthy"
        else:
            models_available = 0
            status = "unhealthy"
        
        return HealthResponse(
            status=status,
            ollama_running=ollama_running,
            models_available=models_available
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            ollama_running=False,
            models_available=0
        )


# ==================== Chat Endpoint ====================

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Chat endpoint using Ollama models.
    
    Accepts a list of messages and generates a response using the specified model.
    
    Args:
        request: ChatRequest containing messages and generation parameters
        
    Returns:
        ChatResponse: The generated response with metadata
        
    Raises:
        HTTPException: If Ollama is not running or model is not available
    """
    try:
        # Get the Ollama client
        client = get_ollama_client()
        
        # Check if Ollama is running
        if not client.is_running():
            raise HTTPException(
                status_code=503,
                detail="Ollama service is not running. Please start Ollama and try again."
            )
        
        # Determine which model to use
        model_name = request.model
        if not model_name:
            if settings:
                model_name = settings.OLLAMA_LLM_DEFAULT
            else:
                model_name = "mistral:7b"
        
        # Check if model exists
        if not client.model_exists(model_name):
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_name}' not found. Available models: {[m.name for m in client.get_all_models()]}"
            )
        
        # Convert Pydantic models to dicts for Ollama client
        messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]
        
        # Generate response
        start_time = time.time()
        response = client.chat(
            model=model_name,
            messages=messages,
            stream=False,
            temperature=request.temperature,
            top_p=request.top_p,
            top_k=request.top_k,
            num_predict=request.num_predict
        )
        generation_time = time.time() - start_time
        
        return ChatResponse(
            message=response,
            model=model_name,
            generation_time=generation_time,
            prompt_tokens=None,
            response_tokens=None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating response: {str(e)}"
        )


# ==================== Root Endpoint ====================

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.
    
    Returns:
        dict: API name and version
    """
    return {
        "name": "Grace API",
        "version": "0.1.0",
        "description": "API for Ollama-based chat and embeddings",
        "docs": "/docs",
        "health": "/health"
    }




# ==================== Run ====================

if __name__ == "__main__":
    import uvicorn
    
    # Run the app
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
