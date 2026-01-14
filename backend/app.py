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

# Security imports
from security.config import get_security_config
from security.middleware import SecurityHeadersMiddleware, RateLimitMiddleware, RequestValidationMiddleware

from ollama_client.client import get_ollama_client
from database.session import SessionLocal, get_session, initialize_session_factory
from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType
from database.migration import create_tables
from models.repositories import ChatRepository, ChatHistoryRepository
from models.database_models import Chat
from api.ingest import router as ingest_router
from api.retrieve import router as retrieve_router, get_document_retriever
from api.version_control import router as version_control_router
from api.file_management import router as file_management_router
from api.file_ingestion import router as file_ingestion_router
from api.genesis_keys import router as genesis_keys_router
from api.auth import router as auth_router
from api.directory_hierarchy import router as directory_hierarchy_router
from api.repo_genesis import router as repo_genesis_router
from api.layer1 import router as layer1_router
from api.learning_memory_api import router as learning_memory_router
from api.librarian_api import router as librarian_router
from api.cognitive import router as cognitive_router
from api.training import router as training_router
from api.autonomous_learning import router as autonomous_learning_router
from api.master_integration import router as master_router
from api.llm_orchestration import router as llm_orchestration_router
from api.ingestion_integration import router as ingestion_integration_router  # Complete autonomous cycle
from api.ml_intelligence_api import router as ml_intelligence_router  # ML Intelligence features
from api.sandbox_lab import router as sandbox_lab_router  # Autonomous experimentation lab
from api.notion import router as notion_router  # Notion task management system
from api.voice_api import router as voice_router  # Voice API - STT/TTS for GRACE
from api.agent_api import router as agent_router  # Full Agent Framework - software engineering agent
from api.governance_api import router as governance_router  # Three-Pillar Governance Framework
from api.knowledge_base_api import router as knowledge_base_router  # Knowledge Base Connectors
from api.kpi_api import router as kpi_router  # KPI Dashboard tracking
from api.proactive_learning import router as proactive_learning_router  # Proactive Learning system
from api.repositories_api import router as repositories_router  # Enterprise Repository Management
from api.telemetry import router as telemetry_router  # System Telemetry and monitoring
from genesis.middleware import GenesisKeyMiddleware
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
    sources: Optional[List[dict]] = Field(None, description="Source chunks used for RAG context")


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
    folder_path: Optional[str] = Field(None, description="Path to folder context for this chat")


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
    folder_path: Optional[str] = Field(None, description="Path to folder context for this chat")


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
    sources: Optional[List[dict]] = Field(None, description="Source chunks used for RAG context")


# ==================== Lifespan ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app startup and shutdown events."""
    # Startup
    print("Grace API starting up...")
    
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
        print("[OK] Database connection initialized")
        
        # Initialize session factory
        initialize_session_factory()
        print("[OK] Database session factory initialized")
        
        # Create tables
        create_tables()
        print("[OK] Database tables created/verified")
    except Exception as e:
        print(f"[WARN] Database initialization error: {e}")
        raise
    
    # Pre-initialize embedding model at startup (ONCE) to avoid loading twice
    try:
        from embedding.embedder import get_embedding_model
        print("\n[STARTUP] Pre-initializing embedding model...")
        embedding_model = get_embedding_model()
        print("[STARTUP] [OK] Embedding model loaded and ready\n")
    except Exception as e:
        print(f"[STARTUP] [WARN] Warning: Could not pre-load embedding model: {e}")
        print("[STARTUP] [WARN] Model will be loaded on first use\n")
    
    # Check Ollama
    try:
        client = get_ollama_client()
        if client.is_running():
            models = client.get_all_models()
            print(f"[OK] Ollama is running with {len(models)} model(s)")
        else:
            print("[WARN] Ollama is not running - chat endpoint will be unavailable")
    except Exception as e:
        print(f"[WARN] Could not connect to Ollama: {e}")
    
    # Check Qdrant
    try:
        qdrant = get_qdrant_client()
        if qdrant.is_connected():
            collections = qdrant.list_collections()
            print(f"[OK] Qdrant is running with {len(collections)} collection(s)")
        else:
            print("[WARN] Qdrant is not running - document ingestion will be unavailable")
    except Exception as e:
        print(f"[WARN] Could not connect to Qdrant: {e}")

    # ==================== Initialize File Watcher ====================
    # Start file system watcher for automatic version control
    try:
        from genesis.file_watcher import start_watching_workspace
        import threading

        def run_file_watcher():
            """Run file watcher in background thread"""
            try:
                print("[FILE-WATCHER] Starting file system monitoring...")
                start_watching_workspace()
            except Exception as e:
                print(f"[FILE-WATCHER] [WARN] Error: {e}")

        watcher_thread = threading.Thread(target=run_file_watcher, daemon=True)
        watcher_thread.start()
        print("[OK] File watcher started - automatic version tracking enabled")
    except Exception as e:
        print(f"[WARN] Could not start file watcher: {e}")

    # ==================== Initialize ML Intelligence ====================
    # Initialize ML Intelligence orchestrator
    try:
        from api.ml_intelligence_api import get_orchestrator
        orchestrator = get_orchestrator()
        print(f"[OK] ML Intelligence initialized with features: {list(orchestrator.enabled_features.keys())}")
    except Exception as e:
        print(f"[WARN] ML Intelligence not available: {e}")

    # ==================== Initialize Auto-Ingestion ====================
    # Start background task for monitoring knowledge base for new files
    import asyncio
    import threading
    
    auto_ingest_task = None
    
    def run_auto_ingestion():
        """Run auto-ingestion in a background thread."""
        try:
            import time
            import sys
            from api.file_ingestion import get_file_manager
            from database.connection import DatabaseConnection
            from database.session import initialize_session_factory
            
            # Ensure database is initialized in this thread context
            print("\n[AUTO-INGEST] Verifying database connection...", flush=True)
            try:
                engine = DatabaseConnection.get_engine()
                if engine:
                    print("[AUTO-INGEST] [OK] Database engine verified", flush=True)
            except RuntimeError as e:
                print(f"[AUTO-INGEST] [WARN] Database not initialized yet: {e}", flush=True)
                print("[AUTO-INGEST] Waiting 2 seconds...", flush=True)
                time.sleep(2)
            
            # Initialize session factory in this thread if needed
            print("[AUTO-INGEST] Initializing session factory...", flush=True)
            session_factory = initialize_session_factory()
            if session_factory:
                print("[AUTO-INGEST] [OK] Session factory initialized", flush=True)
            else:
                print("[AUTO-INGEST] [FAIL] Failed to initialize session factory", flush=True)
            
            print("[AUTO-INGEST] Starting auto-ingestion monitor...", flush=True)
            
            # Get the file manager instance
            file_manager = get_file_manager()
            
            # Initialize git if needed
            file_manager.git_tracker.initialize_git()
            
            # Do initial scan on startup
            print("[AUTO-INGEST] Running initial scan of knowledge base...", flush=True)
            max_retries = 3
            retry_count = 0
            results = []
            
            while retry_count < max_retries:
                try:
                    results = file_manager.scan_directory()
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        print(f"[AUTO-INGEST] Scan attempt {retry_count} failed, retrying in 2 seconds: {e}", flush=True)
                        time.sleep(2)
                    else:
                        print(f"[AUTO-INGEST] [FAIL] Initial scan failed after {max_retries} attempts: {e}", flush=True)
                        raise
            
            if results:
                print(f"[AUTO-INGEST] Initial scan found {len(results)} changes:", flush=True)
                for result in results:
                    status = "[OK]" if result.success else "[FAIL]"
                    print(f"  {status} {result.change_type}: {result.filepath}", flush=True)
            else:
                print("[AUTO-INGEST] No changes detected in initial scan", flush=True)
            
            # Continue monitoring in background
            print("[AUTO-INGEST] Auto-ingestion monitor started (will check every 30 seconds)\n", flush=True)
            file_manager.watch_and_process(continuous=True)
        except Exception as e:
            print(f"[AUTO-INGEST] [FAIL] Error in auto-ingestion: {e}", flush=True)
            import traceback
            traceback.print_exc()
    
    # Start auto-ingestion in a daemon thread
    try:
        auto_ingest_thread = threading.Thread(target=run_auto_ingestion, daemon=True)
        auto_ingest_thread.start()
    except Exception as e:
        print(f"[AUTO-INGEST] [FAIL] Failed to start auto-ingestion: {e}")

    # ==================== Start Continuous Learning Orchestrator ====================
    # Connect sandbox lab to continuous training data
    try:
        from cognitive.continuous_learning_orchestrator import start_continuous_learning
        print("\n[CONTINUOUS_LEARNING] Starting continuous autonomous learning orchestration...", flush=True)
        orchestrator = start_continuous_learning()
        print("[CONTINUOUS_LEARNING] [OK] Continuous learning activated", flush=True)
        print("[CONTINUOUS_LEARNING] Grace will now continuously:", flush=True)
        print("  - Ingest new data from knowledge_base", flush=True)
        print("  - Learn autonomously from content", flush=True)
        print("  - Mirror observes and proposes experiments", flush=True)
        print("  - Run sandbox experiments and trials", flush=True)
        print("  - Request approval for validated improvements", flush=True)
        print("[CONTINUOUS_LEARNING] Grace's continuous self-improvement loop is active!\n", flush=True)
    except Exception as e:
        print(f"[CONTINUOUS_LEARNING] [WARN] Could not start continuous learning: {e}", flush=True)

    yield
    
    # Shutdown
    print("Grace API shutting down...")


# ==================== FastAPI App ====================

app = FastAPI(
    title="Grace API",
    description="API for Ollama-based chat and embeddings",
    version="0.1.0",
    lifespan=lifespan
)

# ==================== Security Middleware ====================
# Load security configuration
security_config = get_security_config()

# Add security headers middleware (runs last, so added first)
app.add_middleware(SecurityHeadersMiddleware)

# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware, default_limit=security_config.RATE_LIMIT_DEFAULT)

# Add request validation middleware
app.add_middleware(RequestValidationMiddleware)

# Add CORS middleware with secure configuration
# IMPORTANT: In production, set CORS_ALLOWED_ORIGINS env var to your specific domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=security_config.CORS_ALLOWED_ORIGINS,
    allow_credentials=security_config.CORS_ALLOW_CREDENTIALS,
    allow_methods=security_config.CORS_ALLOWED_METHODS,
    allow_headers=security_config.CORS_ALLOWED_HEADERS,
    max_age=security_config.CORS_MAX_AGE,
)

# Register API routers
app.include_router(ingest_router)
app.include_router(retrieve_router)
app.include_router(version_control_router)
app.include_router(file_management_router)
app.include_router(file_ingestion_router)
app.include_router(genesis_keys_router)
app.include_router(auth_router)
app.include_router(directory_hierarchy_router)
app.include_router(repo_genesis_router)
app.include_router(layer1_router)
app.include_router(learning_memory_router)
app.include_router(librarian_router)
app.include_router(cognitive_router)
app.include_router(training_router)
app.include_router(master_router)  # Master integration - unified access to ALL systems
app.include_router(autonomous_learning_router)
app.include_router(llm_orchestration_router)
app.include_router(ingestion_integration_router)  # Complete autonomous cycle with self-healing
app.include_router(ml_intelligence_router)  # ML Intelligence - neural trust, bandits, meta-learning
app.include_router(sandbox_lab_router)  # Autonomous Sandbox Lab - self-improvement experiments
app.include_router(notion_router)  # Notion Task Management - Kanban board with Genesis Keys
app.include_router(voice_router)  # Voice API - STT/TTS for continuous voice interaction with GRACE
app.include_router(agent_router)  # Full Agent Framework - software engineering agent with execution
app.include_router(governance_router)  # Three-Pillar Governance Framework with human-in-the-loop
app.include_router(knowledge_base_router)  # Knowledge Base Connectors for external sources
app.include_router(kpi_router)  # KPI Dashboard - system health and performance metrics
app.include_router(proactive_learning_router)  # Proactive Learning - task queue and autonomous learning
app.include_router(repositories_router)  # Enterprise Repository Management - multi-repo support
app.include_router(telemetry_router)  # System Telemetry - drift detection, baselines, alerts

# Add Genesis Key middleware for automatic tracking
app.add_middleware(GenesisKeyMiddleware)


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
        sources = []  # Track source chunks
        try:
            retriever = get_document_retriever()
            retrieval_result = retriever.retrieve(
                query=user_query,
                limit=5,
                include_metadata=True  # Include metadata for source attribution
            )
            
            if retrieval_result:
                rag_context = "\n\n".join([chunk["text"] for chunk in retrieval_result])
                rag_context = rag_context.strip()
                
                # Prepare sources for response
                sources = [
                    {
                        "text": chunk["text"],
                        "score": chunk.get("score", 0),
                        "chunk_id": chunk.get("chunk_id"),
                        "document_id": chunk.get("document_id"),
                        "filename": chunk.get("metadata", {}).get("filename", "Unknown"),
                        "source": chunk.get("metadata", {}).get("source", "Unknown"),
                        "upload_method": chunk.get("metadata", {}).get("upload_method", "Unknown"),
                        "chunk_index": chunk.get("metadata", {}).get("chunk_index", 0),
                        "trust_score": chunk.get("metadata", {}).get("trust_score", 0.0),
                        "created_at": chunk.get("metadata", {}).get("created_at"),
                        "description": chunk.get("metadata", {}).get("description"),
                    }
                    for chunk in retrieval_result
                ]
        except Exception as e:
            print(f"[WARN] RAG retrieval error: {str(e)}")
        
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
        max_num_predict = settings.MAX_NUM_PREDICT if settings else 512
        
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
            response_tokens=None,
            sources=sources  # Include source chunks
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
        request: ChatCreateRequest with optional title, description, model, temperature, and folder_path
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
        
        # Create chat with folder_path
        chat = repo.create(
            title=request.title,
            description=request.description,
            model=model,
            temperature=request.temperature or 0.7,
            folder_path=request.folder_path or ""
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
            last_message_at=chat.last_message_at,
            folder_path=getattr(chat, 'folder_path', None)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating chat: {str(e)}"
        )


@app.get("/chats/folders", tags=["Chat Management"])
async def list_chat_folders(session = Depends(get_session)):
    """
    List all unique folder paths from chats.
    Returns folder names with chat counts for the folder selector UI.
    """
    try:
        from sqlalchemy import func, distinct

        # Get all unique folder paths and their chat counts
        results = session.query(
            Chat.folder_path,
            func.count(Chat.id).label('chat_count'),
            func.max(Chat.updated_at).label('last_updated')
        ).filter(
            Chat.folder_path != None,
            Chat.folder_path != ''
        ).group_by(Chat.folder_path).order_by(func.max(Chat.updated_at).desc()).all()

        folders = []
        for row in results:
            folder_path = row.folder_path or row[0]
            chat_count = row.chat_count if hasattr(row, 'chat_count') else row[1]
            last_updated = row.last_updated if hasattr(row, 'last_updated') else row[2]

            # Extract folder name from path
            folder_name = folder_path.split('/')[-1] or folder_path.split('\\')[-1] or folder_path

            folders.append({
                "path": folder_path,
                "name": folder_name,
                "chat_count": chat_count,
                "last_updated": last_updated.isoformat() if last_updated else None
            })

        # Also get count of chats with no folder (general chats)
        general_count = session.query(func.count(Chat.id)).filter(
            (Chat.folder_path == None) | (Chat.folder_path == '')
        ).scalar() or 0

        return {
            "folders": folders,
            "general_chat_count": general_count,
            "total_folders": len(folders)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing folders: {str(e)}"
        )


@app.get("/chats", response_model=ChatListResponse, tags=["Chat Management"])
async def list_chats(skip: int = 0, limit: int = 50, active_only: bool = False, folder_path: Optional[str] = None, session = Depends(get_session)):
    """
    List all chats with optional filtering.
    
    Args:
        skip: Number of chats to skip
        limit: Maximum number of chats to return
        active_only: If True, only return active chats
        folder_path: If specified, only return chats for this folder
        session: Database session
        
    Returns:
        ChatListResponse: List of chats with metadata
    """
    try:
        repo = ChatRepository(session)
        
        # Build filter criteria
        filter_kwargs = {}
        if folder_path is not None:
            filter_kwargs['folder_path'] = folder_path
        if active_only:
            filter_kwargs['is_active'] = True
        
        # Get chats with filters
        if filter_kwargs:
            # Use filtered query
            from sqlalchemy import and_, inspect
            query = session.query(Chat)
            
            # Check if columns exist before filtering
            mapper = inspect(Chat)
            columns = {column.name for column in mapper.columns}
            
            for key, value in filter_kwargs.items():
                if key in columns:
                    query = query.filter(getattr(Chat, key) == value)
            
            chats = query.order_by(Chat.updated_at.desc()).offset(skip).limit(limit).all()
            total = query.count()
        else:
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
                    last_message_at=chat.last_message_at,
                    folder_path=getattr(chat, 'folder_path', None)
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
            last_message_at=chat.last_message_at,
            folder_path=getattr(chat, 'folder_path', None)
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
        if request.folder_path is not None:
            update_data['folder_path'] = request.folder_path
        
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
            last_message_at=updated_chat.last_message_at,
            folder_path=getattr(updated_chat, 'folder_path', None)
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
        # CONTEXT SCOPING:
        #   - General chats (no folder_path): Full access to world model + all knowledge
        #   - Folder chats (has folder_path): Scoped to folder's learning memory only
        rag_context = ""
        sources = []  # Track source chunks
        is_folder_scoped = bool(chat.folder_path and chat.folder_path.strip())

        try:
            retriever = get_document_retriever()
            retrieval_result = retriever.retrieve(
                query=request.content,
                limit=10 if is_folder_scoped else 5,  # Get more for folder filtering
                include_metadata=True  # Include metadata for source attribution
            )

            # Apply folder scoping if this is a folder chat
            if is_folder_scoped and retrieval_result:
                folder_path = chat.folder_path.replace("\\", "/").strip("/")
                filtered_chunks = []
                for chunk in retrieval_result:
                    file_path = chunk.get("metadata", {}).get("file_path", "")
                    file_path = file_path.replace("\\", "/") if file_path else ""
                    # Check if file is within the folder scope
                    if file_path.startswith(folder_path + "/") or file_path.startswith(folder_path):
                        filtered_chunks.append(chunk)
                retrieval_result = filtered_chunks[:5]  # Limit to 5 after filtering

            # Check if any relevant data was found
            if retrieval_result:
                # Build context with metadata enrichment for each chunk
                context_parts = []
                for chunk in retrieval_result:
                    filename = chunk.get("metadata", {}).get("filename", "Unknown")
                    created_at = chunk.get("metadata", {}).get("created_at", "Unknown")
                    confidence = chunk.get("confidence_score", 0.0)
                    chunk_text = chunk["text"]
                    chunk_index = chunk.get("chunk_index", 0)

                    # Format chunk with metadata for LLM context
                    enriched_chunk = f"""[Source: {filename} | Date: {created_at} | Confidence: {confidence:.1%} | Chunk {chunk_index}]
{chunk_text}"""
                    context_parts.append(enriched_chunk)

                rag_context = "\n\n".join(context_parts)
                rag_context = rag_context.strip()

                # Prepare sources for response
                sources = [
                    {
                        "text": chunk["text"],
                        "score": chunk.get("score", 0),
                        "chunk_id": chunk.get("chunk_id"),
                        "document_id": chunk.get("document_id"),
                        "filename": chunk.get("metadata", {}).get("filename", "Unknown"),
                        "source": chunk.get("metadata", {}).get("source", "Unknown"),
                        "upload_method": chunk.get("metadata", {}).get("upload_method", "Unknown"),
                        "chunk_index": chunk.get("metadata", {}).get("chunk_index", 0),
                        "trust_score": chunk.get("confidence_score", 0.0),  # Get confidence_score from chunk, not metadata
                        "created_at": chunk.get("metadata", {}).get("created_at"),
                        "description": chunk.get("metadata", {}).get("description"),
                    }
                    for chunk in retrieval_result
                ]
        except Exception as e:
            print(f"[WARN] RAG retrieval error: {str(e)}")
        
        # ==================== REJECT IF NO KNOWLEDGE FOUND ====================
        # Core enforcement: No knowledge in database = reject response
        if not rag_context:
            # Delete the user message since we're rejecting the query
            session.delete(user_message)
            session.commit()

            # Context-aware rejection message
            if is_folder_scoped:
                detail_msg = f"No relevant information found in folder '{chat.folder_path}'. This chat is scoped to that folder's learning memory. Please upload documents to this folder or use a General Chat for broader queries."
            else:
                detail_msg = "I cannot answer this question. No relevant information found in the knowledge base. Please upload documents related to your query."

            raise HTTPException(
                status_code=404,
                detail=detail_msg
            )

        # Get chat history for context
        chat_history = history_repo.get_by_chat(chat_id, skip=0, limit=100)

        # Prepare messages for Ollama
        messages = []

        # Build context-aware system prompt
        if is_folder_scoped:
            # Folder-scoped: Focus on folder-specific knowledge
            folder_system_prompt = f"""You are Grace, an intelligent assistant with access to the learning memory for the folder: {chat.folder_path}

Your knowledge is SCOPED to this specific folder's documents and learning memory only.
You can apply your intelligence and reasoning within this context, but you cannot access or reference information from other folders or the general knowledge base.

IMPORTANT CONSTRAINTS:
- Only use information from the provided context (from folder: {chat.folder_path})
- If asked about topics outside this folder's scope, acknowledge the limitation
- Be precise and reference the source documents when possible
- Apply your full reasoning capabilities within this folder's context"""
            messages.append({
                "role": "system",
                "content": folder_system_prompt
            })
        else:
            # General chat: Full world model access
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
        max_num_predict = settings.MAX_NUM_PREDICT if settings else 512
        
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
            total_tokens_in_chat=total_tokens,
            sources=sources  # Include source chunks for attribution
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


# ==================== Directory-Scoped Chat ====================

class DirectoryPromptRequest(BaseModel):
    """Request for directory-scoped chat."""
    query: str = Field(..., description="User query/prompt")
    directory_path: str = Field("", description="Directory path relative to knowledge_base root")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Temperature for generation")
    top_p: Optional[float] = Field(0.9, ge=0.0, le=1.0, description="Nucleus sampling parameter")
    top_k: Optional[int] = Field(40, ge=0, description="Top-k sampling parameter")


class DirectoryPromptResponse(BaseModel):
    """Response for directory-scoped chat."""
    message: str = Field(..., description="The generated response")
    message_id: Optional[int] = Field(None, description="Message ID if saved")
    directory_path: str = Field(..., description="Directory path that was queried")
    generation_time: float = Field(..., description="Time taken to generate response")
    sources: Optional[List[dict]] = Field(None, description="Source chunks used")


@app.post("/chat/directory-prompt", response_model=DirectoryPromptResponse, tags=["Directory Chat"])
async def directory_chat_prompt(request: DirectoryPromptRequest, session = Depends(get_session)):
    """
    Send a prompt/message and get a response using only context from files in a specific directory.
    This is a stateless chat endpoint that doesn't save to chat history.
    
    Args:
        request: DirectoryPromptRequest with query and directory path
        session: Database session
        
    Returns:
        DirectoryPromptResponse: The generated response with source attribution
        
    Raises:
        HTTPException: 404 if no documents found in directory, 503 if services unavailable
    """
    try:
        # Verify Ollama is running
        client = get_ollama_client()
        if not client.is_running():
            raise HTTPException(
                status_code=503,
                detail="Ollama service is not running"
            )
        
        # ==================== DIRECTORY-SCOPED RAG RETRIEVAL ====================
        # Retrieve context only from specified directory
        rag_context = ""
        sources = []
        try:
            from api.retrieve import get_document_retriever
            
            retriever = get_document_retriever()
            
            # Use directory-scoped retrieval endpoint
            retrieval_result = retriever.retrieve(
                query=request.query,
                limit=10,
                score_threshold=0.2,
                include_metadata=True
            )
            
            # Filter by directory if specified
            if retrieval_result:
                filtered_chunks = []
                # Normalize directory path to forward slashes for cross-platform compatibility
                target_dir = request.directory_path.rstrip("/").rstrip("\\").replace("\\", "/") if request.directory_path else ""
                
                for chunk in retrieval_result:
                    file_path = chunk.get("metadata", {}).get("file_path", "")
                    # Normalize file_path to forward slashes as well
                    file_path = file_path.replace("\\", "/") if file_path else ""
                    
                    # Check if file is in the directory
                    if target_dir == "":
                        # Root directory - include files with no subdirectory
                        if file_path and "/" not in file_path:
                            filtered_chunks.append(chunk)
                    else:
                        # Check if file_path starts with directory
                        if file_path and (file_path.startswith(target_dir + "/") or file_path == target_dir):
                            filtered_chunks.append(chunk)
                
                # Limit to top chunks
                filtered_chunks = filtered_chunks[:5]
                
                if filtered_chunks:
                    # Build context with metadata enrichment
                    context_parts = []
                    for chunk in filtered_chunks:
                        filename = chunk.get("metadata", {}).get("filename", "Unknown")
                        created_at = chunk.get("metadata", {}).get("created_at", "Unknown")
                        confidence = chunk.get("confidence_score", 0.0)
                        chunk_text = chunk["text"]
                        chunk_index = chunk.get("chunk_index", 0)
                        
                        enriched_chunk = f"""[Source: {filename} | Date: {created_at} | Confidence: {confidence:.1%} | Chunk {chunk_index}]
{chunk_text}"""
                        context_parts.append(enriched_chunk)
                    
                    rag_context = "\n\n".join(context_parts)
                    rag_context = rag_context.strip()
                    
                    # Prepare sources for response
                    sources = [
                        {
                            "text": chunk["text"],
                            "score": chunk.get("score", 0),
                            "chunk_id": chunk.get("chunk_id"),
                            "document_id": chunk.get("document_id"),
                            "filename": chunk.get("metadata", {}).get("filename", "Unknown"),
                            "source": chunk.get("metadata", {}).get("source", "Unknown"),
                            "chunk_index": chunk.get("metadata", {}).get("chunk_index", 0),
                            "confidence_score": chunk.get("confidence_score", 0.0),
                            "created_at": chunk.get("metadata", {}).get("created_at"),
                        }
                        for chunk in filtered_chunks
                    ]
        
        except Exception as e:
            print(f"[WARN] Directory RAG retrieval error: {str(e)}")
        
        # ==================== REJECT IF NO KNOWLEDGE FOUND ====================
        if not rag_context:
            raise HTTPException(
                status_code=404,
                detail=f"No documents found in directory: {request.directory_path or 'root'}"
            )
        
        # ==================== PREPARE MESSAGES FOR OLLAMA ====================
        messages = []
        
        # Add system prompt
        messages.append({
            "role": "system",
            "content": build_rag_system_prompt()
        })
        
        # Inject RAG context into the user message
        augmented_content = build_rag_prompt(request.query, rag_context)
        messages.append({"role": "user", "content": augmented_content})
        
        # ==================== GENERATE RESPONSE ====================
        start_time = time.time()
        temperature = min(request.temperature or 0.7, 0.3)  # Cap temperature for deterministic responses
        max_num_predict = settings.MAX_NUM_PREDICT if settings else 512
        
        response_text = client.chat(
            model=settings.OLLAMA_LLM_DEFAULT if settings else "llama2",
            messages=messages,
            stream=False,
            temperature=temperature,
            top_p=request.top_p or 0.5,
            top_k=request.top_k or 10,
            num_predict=max_num_predict
        )
        generation_time = time.time() - start_time
        
        response_text = response_text.strip()
        
        return DirectoryPromptResponse(
            message=response_text,
            directory_path=request.directory_path or "root",
            generation_time=generation_time,
            sources=sources
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in directory chat: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing directory chat: {str(e)}"
        )


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
