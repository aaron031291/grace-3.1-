"""
Grace API - FastAPI application for Ollama-based chat and embeddings.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import time
from contextlib import asynccontextmanager
from datetime import datetime

from ollama_client.client import get_ollama_client
from database.session import SessionLocal, get_session, initialize_session_factory
from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType
from database.migration import create_tables
from models.repositories import ChatRepository, ChatHistoryRepository
from models.database_models import Chat
from api.ingest import router as ingest_router
from api.retrieve import router as retrieve_router, get_document_retriever
from vector_db.client import get_qdrant_client
from utils.rag_prompt import build_rag_prompt, build_rag_system_prompt

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


# ==================== Chat Management Models ====================

class ChatCreateRequest(BaseModel):
    """Request model for creating a new chat."""
    title: Optional[str] = Field(None, description="Title of the chat")
    description: Optional[str] = Field(None, description="Description of the chat")
    model: Optional[str] = Field(None, description="Model to use (defaults to settings)")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Temperature for generation")


class ChatResponse(BaseModel):
    """Response model for chat operations."""
    id: int = Field(..., description="Chat ID")
    title: Optional[str] = Field(None, description="Chat title")
    description: Optional[str] = Field(None, description="Chat description")
    model: str = Field(..., description="Model being used")
    temperature: float = Field(..., description="Temperature setting")
    is_active: bool = Field(..., description="Whether chat is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_message_at: Optional[datetime] = Field(None, description="Last message timestamp")


class ChatListResponse(BaseModel):
    """Response model for chat list."""
    chats: List[ChatResponse] = Field(..., description="List of chats")
    total: int = Field(..., description="Total number of chats")
    skip: int = Field(..., description="Skip count")
    limit: int = Field(..., description="Limit count")


class MessageCreateRequest(BaseModel):
    """Request model for adding a message to chat."""
    content: str = Field(..., description="Message content")
    role: Optional[str] = Field("user", description="Message role: 'user', 'assistant', 'system'")


class ChatMessageResponse(BaseModel):
    """Response model for chat message."""
    id: int = Field(..., description="Message ID")
    chat_id: int = Field(..., description="Chat ID")
    role: str = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    tokens: Optional[int] = Field(None, description="Token count")
    is_edited: bool = Field(..., description="Whether message was edited")
    created_at: datetime = Field(..., description="Creation timestamp")
    edited_at: Optional[datetime] = Field(None, description="Edit timestamp")


class ChatHistoryResponse(BaseModel):
    """Response model for chat history."""
    messages: List[ChatMessageResponse] = Field(..., description="List of messages")
    total: int = Field(..., description="Total messages in chat")
    model: str = Field(..., description="Model used in chat")
    created_at: datetime = Field(..., description="Chat creation time")


class PromptRequest(BaseModel):
    """Request model for sending a prompt to a chat."""
    content: str = Field(..., description="The user message/prompt")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Override temperature")
    top_p: Optional[float] = Field(0.9, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    top_k: Optional[int] = Field(40, ge=0, description="Top-k sampling parameter")


class PromptResponse(BaseModel):
    """Response model for prompt generation."""
    chat_id: int = Field(..., description="Chat ID")
    user_message_id: int = Field(..., description="User message ID")
    assistant_message_id: int = Field(..., description="Assistant message ID")
    message: str = Field(..., description="Generated response")
    model: str = Field(..., description="Model used")
    generation_time: float = Field(..., description="Time taken to generate")
    tokens_used: Optional[int] = Field(None, description="Tokens used in response")
    total_tokens_in_chat: int = Field(..., description="Total tokens in chat so far")


# ==================== Lifespan ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown events."""
    # Startup
    print("🚀 Grace API starting up...")
    
    # Initialize database
    try:
        db_type = DatabaseType(settings.DATABASE_TYPE) if settings else DatabaseType.SQLITE
        db_config = DatabaseConfig(
            db_type=db_type,
            host=settings.DATABASE_HOST if settings else None,
            port=settings.DATABASE_PORT if settings else None,
            username=settings.DATABASE_USER if settings else None,
            password=settings.DATABASE_PASSWORD if settings else None,
            database=settings.DATABASE_NAME if settings else "grace",
            database_path=settings.DATABASE_PATH if settings else None,
            echo=settings.DATABASE_ECHO if settings else False,
        )
        DatabaseConnection.initialize(db_config)
        print("✓ Database connection initialized")
        
        # Initialize session factory
        initialize_session_factory()
        print("✓ Database session factory initialized")
        
        # Create tables
        create_tables()
        print("✓ Database tables created/verified")
    except Exception as e:
        print(f"⚠ Database initialization error: {e}")
        raise
    
    # Check Ollama
    try:
        client = get_ollama_client()
        if client.is_running():
            models = client.get_all_models()
            print(f"✓ Ollama is running with {len(models)} model(s)")
        else:
            print("⚠ Ollama is not running - chat endpoint will be unavailable")
    except Exception as e:
        print(f"⚠ Could not connect to Ollama: {e}")
    
    # Check Qdrant
    try:
        qdrant = get_qdrant_client()
        if qdrant.is_connected():
            collections = qdrant.list_collections()
            print(f"✓ Qdrant is running with {len(collections)} collection(s)")
        else:
            print("⚠ Qdrant is not running - document ingestion will be unavailable")
    except Exception as e:
        print(f"⚠ Could not connect to Qdrant: {e}")
    
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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (can be restricted to specific domains)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Register API routers
app.include_router(ingest_router)
app.include_router(retrieve_router)


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


class TitleGenerationRequest(BaseModel):
    """Request model for title generation."""
    text: str = Field(..., description="Text to generate title from")


class TitleGenerationResponse(BaseModel):
    """Response model for title generation."""
    title: str = Field(..., description="Generated title")


# ==================== Title Generation Endpoint ====================

@app.post("/generate-title", response_model=TitleGenerationResponse, tags=["Utilities"])
async def generate_title(request: TitleGenerationRequest):
    """
    Generate a concise title from text without storing it in chat history.
    
    Args:
        request: TitleGenerationRequest with text to generate title from
        
    Returns:
        TitleGenerationResponse: The generated title
    """
    try:
        client = get_ollama_client()
        
        if not client.is_running():
            raise HTTPException(
                status_code=503,
                detail="Ollama service is not running"
            )
        
        # Generate title using a simple prompt
        title_prompt = f"Generate a short title (max 5 words) for: {request.text}"
        
        response = client.chat(
            model=settings.OLLAMA_LLM_DEFAULT if settings else "mistral:7b",
            messages=[{"role": "user", "content": title_prompt}],
            stream=False,
            temperature=0.3,
        )
        
        return TitleGenerationResponse(title=response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating title: {str(e)}"
        )


# ==================== Chat Endpoint ====================

@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
    """
    Chat endpoint using Ollama models with RAG enforcement.
    ENFORCES RAG-FIRST: Only responds if relevant knowledge is found in the knowledge base.
    
    Accepts a list of messages and generates a response using the specified model.
    Uses RAG retrieval to augment responses with knowledge base content.
    
    Args:
        request: ChatRequest containing messages and generation parameters
        
    Returns:
        ChatResponse: The generated response with metadata
        
    Raises:
        HTTPException: 404 if no relevant knowledge found, 503 if services unavailable
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
        
        # Get model from settings
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
        
        # ==================== RAG-FIRST RETRIEVAL ====================
        # Get the last user message as the query
        user_query = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_query = msg.content
                break
        
        if not user_query:
            raise HTTPException(
                status_code=400,
                detail="No user message found in conversation"
            )
        
        # Retrieve RAG context
        rag_context = ""
        try:
            retriever = get_document_retriever()
            retrieval_result = retriever.retrieve(
                query=user_query,
                limit=5,
                include_metadata=False
            )
            
            if retrieval_result:
                rag_context = "\n\n".join([chunk["text"] for chunk in retrieval_result])
                rag_context = rag_context.strip()
        except Exception as e:
            print(f"⚠ RAG retrieval error: {str(e)}")
        
        # ==================== REJECT IF NO KNOWLEDGE FOUND ====================
        # Core enforcement: No knowledge = reject response
        if not rag_context:
            raise HTTPException(
                status_code=404,
                detail="I cannot answer this question. No relevant information found in the knowledge base. Please upload documents related to your query."
            )
        
        # Prepare messages with RAG context
        messages = []
        
        # Add strict system prompt
        messages.append({
            "role": "system",
            "content": build_rag_system_prompt()
        })
        
        # Add conversation history, injecting RAG context into the last user message
        for i, msg in enumerate(request.messages):
            if i == len(request.messages) - 1 and msg.role == "user":
                # Last message is user query - inject RAG context
                augmented_content = build_rag_prompt(msg.content, rag_context)
                messages.append({
                    "role": msg.role,
                    "content": augmented_content
                })
            else:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Generate response with strict constraints
        start_time = time.time()
        temperature = request.temperature if request.temperature is not None else 0.7
        # Use lower temperature to enforce deterministic, knowledge-based responses
        temperature = min(temperature, 0.3)  # Cap temperature at 0.3 for strict RAG
        max_num_predict = settings.MAX_NUM_PREDICT if settings else 2048
        
        response = client.chat(
            model=model_name,
            messages=messages,
            stream=False,
            temperature=temperature,
            top_p=request.top_p if request.top_p else 0.5,  # Lower top_p
            top_k=request.top_k if request.top_k else 10,   # Lower top_k
            num_predict=max_num_predict
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


# ==================== Chat Management Endpoints ====================

@app.post("/chats", response_model=ChatResponse, tags=["Chat Management"])
async def create_chat(request: ChatCreateRequest, session = Depends(get_session)):
    """
    Create a new chat session.
    
    Args:
        request: ChatCreateRequest with optional title, description, model, and temperature
        session: Database session
        
    Returns:
        ChatResponse: The created chat
    """
    try:
        repo = ChatRepository(session)
        
        # Use default model if not specified
        model = request.model or (settings.OLLAMA_LLM_DEFAULT if settings else "mistral:7b")
        
        # Verify model exists
        client = get_ollama_client()
        if not client.model_exists(model):
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model}' not found"
            )
        
        # Create chat
        chat = repo.create(
            title=request.title,
            description=request.description,
            model=model,
            temperature=request.temperature or 0.7
        )
        
        return ChatResponse(
            id=chat.id,
            title=chat.title,
            description=chat.description,
            model=chat.model,
            temperature=chat.temperature,
            is_active=chat.is_active,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            last_message_at=chat.last_message_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating chat: {str(e)}"
        )


@app.get("/chats", response_model=ChatListResponse, tags=["Chat Management"])
async def list_chats(skip: int = 0, limit: int = 50, active_only: bool = False, session = Depends(get_session)):
    """
    List all chats with optional filtering.
    
    Args:
        skip: Number of chats to skip
        limit: Maximum number of chats to return
        active_only: If True, only return active chats
        session: Database session
        
    Returns:
        ChatListResponse: List of chats with metadata
    """
    try:
        repo = ChatRepository(session)
        
        if active_only:
            chats = repo.get_active_chats(skip=skip, limit=limit)
            total = repo.count_active()
        else:
            chats = repo.get_all_chats(skip=skip, limit=limit)
            total = repo.count()
        
        return ChatListResponse(
            chats=[
                ChatResponse(
                    id=chat.id,
                    title=chat.title,
                    description=chat.description,
                    model=chat.model,
                    temperature=chat.temperature,
                    is_active=chat.is_active,
                    created_at=chat.created_at,
                    updated_at=chat.updated_at,
                    last_message_at=chat.last_message_at
                )
                for chat in chats
            ],
            total=total,
            skip=skip,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing chats: {str(e)}"
        )


@app.get("/chats/{chat_id}", response_model=ChatResponse, tags=["Chat Management"])
async def get_chat(chat_id: int, session = Depends(get_session)):
    """
    Get a specific chat by ID.
    
    Args:
        chat_id: ID of the chat
        session: Database session
        
    Returns:
        ChatResponse: The chat details
    """
    try:
        repo = ChatRepository(session)
        chat = repo.get(chat_id)
        
        if not chat:
            raise HTTPException(
                status_code=404,
                detail=f"Chat {chat_id} not found"
            )
        
        return ChatResponse(
            id=chat.id,
            title=chat.title,
            description=chat.description,
            model=chat.model,
            temperature=chat.temperature,
            is_active=chat.is_active,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            last_message_at=chat.last_message_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving chat: {str(e)}"
        )


@app.put("/chats/{chat_id}", response_model=ChatResponse, tags=["Chat Management"])
async def update_chat(chat_id: int, request: ChatCreateRequest, session = Depends(get_session)):
    """
    Update a chat's settings.
    
    Args:
        chat_id: ID of the chat
        request: Updated chat settings
        session: Database session
        
    Returns:
        ChatResponse: The updated chat
    """
    try:
        repo = ChatRepository(session)
        
        # Verify chat exists
        chat = repo.get(chat_id)
        if not chat:
            raise HTTPException(
                status_code=404,
                detail=f"Chat {chat_id} not found"
            )
        
        # Prepare update data
        update_data = {}
        if request.title is not None:
            update_data['title'] = request.title
        if request.description is not None:
            update_data['description'] = request.description
        if request.model is not None:
            # Verify model exists
            client = get_ollama_client()
            if not client.model_exists(request.model):
                raise HTTPException(
                    status_code=400,
                    detail=f"Model '{request.model}' not found"
                )
            update_data['model'] = request.model
        if request.temperature is not None:
            update_data['temperature'] = request.temperature
        
        # Update chat
        updated_chat = repo.update(chat_id, **update_data)
        
        return ChatResponse(
            id=updated_chat.id,
            title=updated_chat.title,
            description=updated_chat.description,
            model=updated_chat.model,
            temperature=updated_chat.temperature,
            is_active=updated_chat.is_active,
            created_at=updated_chat.created_at,
            updated_at=updated_chat.updated_at,
            last_message_at=updated_chat.last_message_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating chat: {str(e)}"
        )


@app.delete("/chats/{chat_id}", tags=["Chat Management"])
async def delete_chat(chat_id: int, session = Depends(get_session)):
    """
    Delete a chat and all its messages.
    
    Args:
        chat_id: ID of the chat
        session: Database session
        
    Returns:
        dict: Confirmation message
    """
    try:
        repo = ChatRepository(session)
        
        # Verify chat exists
        chat = repo.get(chat_id)
        if not chat:
            raise HTTPException(
                status_code=404,
                detail=f"Chat {chat_id} not found"
            )
        
        # Delete chat (cascades to messages)
        repo.delete(chat_id)
        
        return {"message": f"Chat {chat_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting chat: {str(e)}"
        )


@app.post("/chats/{chat_id}/messages", response_model=ChatMessageResponse, tags=["Chat Messages"])
async def add_message_to_chat(chat_id: int, request: MessageCreateRequest, session = Depends(get_session)):
    """
    Add a message to a chat (typically for manual message storage).
    
    Args:
        chat_id: ID of the chat
        request: Message content and role
        session: Database session
        
    Returns:
        ChatMessageResponse: The created message
    """
    try:
        chat_repo = ChatRepository(session)
        history_repo = ChatHistoryRepository(session)
        
        # Verify chat exists
        chat = chat_repo.get(chat_id)
        if not chat:
            raise HTTPException(
                status_code=404,
                detail=f"Chat {chat_id} not found"
            )
        
        # Add message
        message = history_repo.add_message(
            chat_id=chat_id,
            role=request.role,
            content=request.content
        )
        
        return ChatMessageResponse(
            id=message.id,
            chat_id=message.chat_id,
            role=message.role,
            content=message.content,
            tokens=message.tokens,
            is_edited=message.is_edited,
            created_at=message.created_at,
            edited_at=message.edited_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error adding message: {str(e)}"
        )


@app.get("/chats/{chat_id}/messages", response_model=ChatHistoryResponse, tags=["Chat Messages"])
async def get_chat_history(chat_id: int, skip: int = 0, limit: int = 100, session = Depends(get_session)):
    """
    Get message history for a chat.
    
    Args:
        chat_id: ID of the chat
        skip: Number of messages to skip
        limit: Maximum number of messages to return
        session: Database session
        
    Returns:
        ChatHistoryResponse: Chat messages and metadata
    """
    try:
        chat_repo = ChatRepository(session)
        history_repo = ChatHistoryRepository(session)
        
        # Verify chat exists
        chat = chat_repo.get(chat_id)
        if not chat:
            raise HTTPException(
                status_code=404,
                detail=f"Chat {chat_id} not found"
            )
        
        # Get messages
        messages = history_repo.get_by_chat(chat_id, skip=skip, limit=limit)
        total = history_repo.count_by_chat(chat_id)
        
        return ChatHistoryResponse(
            messages=[
                ChatMessageResponse(
                    id=msg.id,
                    chat_id=msg.chat_id,
                    role=msg.role,
                    content=msg.content,
                    tokens=msg.tokens,
                    is_edited=msg.is_edited,
                    created_at=msg.created_at,
                    edited_at=msg.edited_at
                )
                for msg in messages
            ],
            total=total,
            model=chat.model,
            created_at=chat.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving chat history: {str(e)}"
        )


@app.post("/chats/{chat_id}/prompt", response_model=PromptResponse, tags=["Chat Prompts"])
async def send_prompt(chat_id: int, request: PromptRequest, session = Depends(get_session)):
    """
    Send a prompt/message to a chat and get an AI-generated response.
    ENFORCES RAG-FIRST RETRIEVAL: Rejects queries if no relevant knowledge is found.
    Only uses information from the knowledge base, does not add external knowledge.
    
    Args:
        chat_id: ID of the chat
        request: PromptRequest with message content and generation parameters
        session: Database session
        
    Returns:
        PromptResponse: The generated response with metadata
        
    Raises:
        HTTPException: 404 if no relevant knowledge found, 503 if services unavailable
    """
    try:
        chat_repo = ChatRepository(session)
        history_repo = ChatHistoryRepository(session)
        
        # Verify chat exists
        chat = chat_repo.get(chat_id)
        if not chat:
            raise HTTPException(
                status_code=404,
                detail=f"Chat {chat_id} not found"
            )
        
        # Verify Ollama is running
        client = get_ollama_client()
        if not client.is_running():
            raise HTTPException(
                status_code=503,
                detail="Ollama service is not running"
            )
        
        # Add user message to chat
        user_message = history_repo.add_message(
            chat_id=chat_id,
            role="user",
            content=request.content
        )
        
        # ==================== RAG-FIRST RETRIEVAL ====================
        # Retrieve RAG context for the user query - MANDATORY
        rag_context = ""
        try:
            retriever = get_document_retriever()
            retrieval_result = retriever.retrieve(
                query=request.content,
                limit=5,
                include_metadata=False
            )
            
            # Check if any relevant data was found
            if retrieval_result:
                rag_context = "\n\n".join([chunk["text"] for chunk in retrieval_result])
                rag_context = rag_context.strip()
        except Exception as e:
            print(f"⚠ RAG retrieval error: {str(e)}")
        
        # ==================== REJECT IF NO KNOWLEDGE FOUND ====================
        # Core enforcement: No knowledge in database = reject response
        if not rag_context:
            # Delete the user message since we're rejecting the query
            session.delete(user_message)
            session.commit()
            
            raise HTTPException(
                status_code=404,
                detail="I cannot answer this question. No relevant information found in the knowledge base. Please upload documents related to your query."
            )
        
        # Get chat history for context
        chat_history = history_repo.get_by_chat(chat_id, skip=0, limit=100)
        
        # Prepare messages for Ollama
        messages = []
        
        # Add strict system prompt that enforces knowledge-only responses
        messages.append({
            "role": "system",
            "content": build_rag_system_prompt()
        })
        
        # Add chat history (excluding the latest user message for now)
        for msg in chat_history[:-1]:  # All messages except the last user message
            messages.append({"role": msg.role, "content": msg.content})
        
        # Inject RAG context into the user message
        augmented_content = build_rag_prompt(request.content, rag_context)
        messages.append({"role": "user", "content": augmented_content})
        
        # Generate response with strict constraints
        start_time = time.time()
        temperature = request.temperature or chat.temperature
        # Use lower temperature to enforce deterministic, knowledge-based responses
        temperature = min(temperature, 0.3) if temperature else 0.1  # Cap temperature at 0.3 for strict RAG
        max_num_predict = settings.MAX_NUM_PREDICT if settings else 2048
        
        response_text = client.chat(
            model=chat.model,
            messages=messages,
            stream=False,
            temperature=temperature,
            top_p=request.top_p if request.top_p else 0.5,  # Lower top_p for deterministic output
            top_k=request.top_k if request.top_k else 10,   # Lower top_k for stricter sampling
            num_predict=max_num_predict
        )
        generation_time = time.time() - start_time
        
        # Verify response is not a rejection/failure message from the model
        response_text = response_text.strip()
        
        # Add assistant message to chat
        assistant_message = history_repo.add_message(
            chat_id=chat_id,
            role="assistant",
            content=response_text,
            completion_time=generation_time
        )
        
        # Update chat's last_message_at
        chat_repo.update(chat_id, last_message_at=datetime.utcnow())
        
        # Get total tokens in chat
        total_tokens = history_repo.count_tokens_in_chat(chat_id)
        
        return PromptResponse(
            chat_id=chat_id,
            user_message_id=user_message.id,
            assistant_message_id=assistant_message.id,
            message=response_text,
            model=chat.model,
            generation_time=generation_time,
            tokens_used=None,
            total_tokens_in_chat=total_tokens
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing prompt: {str(e)}"
        )


@app.put("/chats/{chat_id}/messages/{message_id}", response_model=ChatMessageResponse, tags=["Chat Messages"])
async def edit_message(chat_id: int, message_id: int, request: MessageCreateRequest, session = Depends(get_session)):
    """
    Edit a message in a chat.
    
    Args:
        chat_id: ID of the chat
        message_id: ID of the message to edit
        request: New message content
        session: Database session
        
    Returns:
        ChatMessageResponse: The edited message
    """
    try:
        chat_repo = ChatRepository(session)
        history_repo = ChatHistoryRepository(session)
        
        # Verify chat exists
        chat = chat_repo.get(chat_id)
        if not chat:
            raise HTTPException(
                status_code=404,
                detail=f"Chat {chat_id} not found"
            )
        
        # Edit message
        edited_message = history_repo.edit_message(message_id, request.content)
        
        if not edited_message:
            raise HTTPException(
                status_code=404,
                detail=f"Message {message_id} not found"
            )
        
        return ChatMessageResponse(
            id=edited_message.id,
            chat_id=edited_message.chat_id,
            role=edited_message.role,
            content=edited_message.content,
            tokens=edited_message.tokens,
            is_edited=edited_message.is_edited,
            created_at=edited_message.created_at,
            edited_at=edited_message.edited_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error editing message: {str(e)}"
        )


@app.delete("/chats/{chat_id}/messages/{message_id}", tags=["Chat Messages"])
async def delete_message(chat_id: int, message_id: int, session = Depends(get_session)):
    """
    Delete a message from a chat.
    
    Args:
        chat_id: ID of the chat
        message_id: ID of the message to delete
        session: Database session
        
    Returns:
        dict: Confirmation message
    """
    try:
        chat_repo = ChatRepository(session)
        history_repo = ChatHistoryRepository(session)
        
        # Verify chat exists
        chat = chat_repo.get(chat_id)
        if not chat:
            raise HTTPException(
                status_code=404,
                detail=f"Chat {chat_id} not found"
            )
        
        # Delete message
        deleted = history_repo.delete(message_id)
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Message {message_id} not found"
            )
        
        return {"message": f"Message {message_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting message: {str(e)}"
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
