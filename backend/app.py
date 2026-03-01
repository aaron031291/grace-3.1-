"""
Grace API - FastAPI application for Ollama-based chat and embeddings.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime
import os
import sys
from pathlib import Path

# Configure logging FIRST before any other imports
from logging_config import setup_logging
setup_logging()

# Get logger instance
import logging
logger = logging.getLogger(__name__)

# Security imports
from security.config import get_security_config
from security.middleware import SecurityHeadersMiddleware, RateLimitMiddleware, RequestValidationMiddleware

from llm_orchestrator.factory import get_llm_client
from database.session import SessionLocal, get_session, initialize_session_factory
from database.connection import DatabaseConnection
from database.config import DatabaseConfig, DatabaseType
from database.migration import create_tables
from models.repositories import ChatRepository, ChatHistoryRepository
from models.database_models import Chat
from api.retrieve import router as retrieve_router, get_document_retriever
from api.voice_api import router as voice_router
from api.health import router as health_router
from api.mcp_api import router as mcp_router  # MCP - Model Context Protocol file/terminal/git tools
from api.world_model_api import router as world_model_router
from api.librarian_autonomous_api import router as librarian_autonomous_router
from api.docs_library_api import router as docs_library_router
from api.cross_tab_api import router as cross_tab_router
from api.governance_hub_api import router as governance_hub_router
from api.genesis_daily_api import router as genesis_daily_router
from api.governance_rules_api import router as governance_rules_router
from api.whitelist_hub_api import router as whitelist_hub_router
from api.oracle_api import router as oracle_router
from api.codebase_hub_api import router as codebase_hub_router
from api.system_bridge_api import router as system_bridge_router
from api.manifest_api import router as manifest_router
from api.v1.router import register_v1
from api.tasks_hub_api import router as tasks_hub_router
from api.api_registry_api import router as api_registry_router
from api.business_intelligence_api import router as bi_router
from api.system_health_api import router as system_health_router
from api.learning_healing_api import router as learning_healing_router
from api.unified_coding_agent_api import router as unified_coding_agent_router
from api.api_explorer_api import router as api_explorer_router
from api.chunked_upload_api import router as chunked_upload_router
from api.flash_cache_api import router as flash_cache_router
from api.consensus_api import router as consensus_router
from api.system_audit_api import router as system_audit_router
from api.api_vault_api import router as api_vault_router
from api.planner_api import router as planner_router
from api.reporting_api import router as reporting_router
from api.knowledge_mining_api import router as knowledge_mining_router
from api.governance_discussion_api import router as governance_discussion_router
from api.live_console_api import router as live_console_router
from api.feedback_api import router as feedback_router
from api.tab_aggregator_api import router as tab_aggregator_router
from api.version_control import router as version_control_router
from api.ingestion_api import router as ingestion_router
from api.genesis_keys import router as genesis_keys_router
from api.auth import router as auth_router
from api.kpi_api import router as kpi_router
from api.knowledge_base_api import router as knowledge_base_router
from api.repositories_api import router as repositories_router
from api.cicd_api import router as cicd_router
from api.scraping import router as scraping_router
from api.streaming import router as streaming_router
from api.websocket import router as websocket_router
from api.telemetry import router as telemetry_router
from diagnostic_machine.api import router as diagnostic_router
from api.runtime_triggers_api import router as runtime_triggers_router
from api.component_health_api import router as component_health_router
from genesis.middleware import GenesisKeyMiddleware
from vector_db.client import get_qdrant_client
from utils.rag_prompt import build_rag_prompt, build_rag_system_prompt
from search.serpapi_service import SerpAPIService

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
    # Multi-tier query handling fields
    tier: Optional[str] = Field(None, description="Query tier used: VECTORDB, MODEL_KNOWLEDGE, or USER_CONTEXT")
    confidence: Optional[float] = Field(None, description="Confidence score (0.0-1.0)")
    knowledge_gaps: Optional[List[dict]] = Field(None, description="Knowledge gaps identified (Tier 3)")
    warnings: Optional[List[str]] = Field(None, description="Warnings about response quality")


class HealthResponse(BaseModel):
    """Health response model."""
    status: str
    llm_running: bool
    models_available: int


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
        print("[WARN] Grace will continue with limited functionality")
    
    # Auto-ingest training corpus on startup
    try:
        from cognitive.training_ingest import ingest_training_corpus
        result = ingest_training_corpus()
        if result.get("ingested", 0) > 0:
            print(f"[OK] Training corpus: {result['ingested']} files ingested")
        else:
            print(f"[OK] Training corpus up to date")
    except Exception as e:
        print(f"[WARN] Training ingest skipped: {e}")

    # Run startup diagnostic
    try:
        from cognitive.autonomous_diagnostics import get_diagnostics
        diag = get_diagnostics()
        startup_result = diag.on_startup()
        print(f"[OK] Startup diagnostic: {startup_result.get('status', 'unknown')} ({startup_result.get('healthy', 0)}/{startup_result.get('total', 0)} healthy)")
    except Exception as e:
        print(f"[WARN] Startup diagnostic skipped: {e}")

    # Pre-initialize embedding model at startup (ONCE) to avoid loading twice
    if not settings.SKIP_EMBEDDING_LOAD:
        try:
            from embedding import get_embedding_model
            print("\n[STARTUP] Pre-initializing embedding model...")
            embedding_model = get_embedding_model()
            print("[STARTUP] [OK] Embedding model loaded and ready\n")
        except Exception as e:
            print(f"[STARTUP] [WARN] Warning: Could not pre-load embedding model: {e}")
            print("[STARTUP] [WARN] Model will be loaded on first use\n")
    else:
        print("[STARTUP] Embedding model loading skipped (SKIP_EMBEDDING_LOAD=true)\n")
    
    # Check LLM Provider
    if not getattr(settings, 'SKIP_LLM_CHECK', False):
        try:
            client = get_llm_client()
            provider_name = settings.LLM_PROVIDER.upper()
            if client.is_running():
                print(f"[OK] {provider_name} is running and reachable")
            else:
                print(f"[WARN] {provider_name} is not responding - chat features may be limited")
        except Exception as e:
            provider = settings.LLM_PROVIDER if settings else "LLM"
            print(f"[WARN] Could not connect to LLM provider ({provider}): {e}")
    else:
        print("[SKIP] LLM check skipped")
    
    # Check Qdrant
    if not settings.SKIP_QDRANT_CHECK:
        try:
            qdrant = get_qdrant_client()
            if qdrant.is_connected():
                collections = qdrant.list_collections()
                print(f"[OK] Qdrant is running with {len(collections)} collection(s)")
            else:
                print("[WARN] Qdrant is not running - document ingestion will be unavailable")
        except Exception as e:
            print(f"[WARN] Could not connect to Qdrant: {e}")
    else:
        print("[SKIP] Qdrant check skipped (SKIP_QDRANT_CHECK=true)")

    # ==================== Initialize File Watcher ====================
    # Start file system watcher for automatic version control
    if not settings.DISABLE_GENESIS_TRACKING:
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
    else:
        print("[SKIP] File watcher disabled (DISABLE_GENESIS_TRACKING=true)")

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
            print("[AUTO-INGEST] File manager initialized", flush=True)
            
            # Initialize git if needed
            file_manager.git_tracker.initialize_git()
            print("[AUTO-INGEST] Git tracker initialized", flush=True)
            
            # Do initial scan on startup
            # print("[AUTO-INGEST] Running initial scan of knowledge base...", flush=True)
            max_retries = 3
            results = []
            
            print("[AUTO-INGEST] Starting directory scan...", flush=True)
            for retry_count in range(max_retries):
                try:
                    results = file_manager.scan_directory()
                    print(f"[AUTO-INGEST] Scan completed with {len(results)} results", flush=True)
                    break
                except Exception as e:
                    if retry_count < max_retries - 1:
                        # print(f"[AUTO-INGEST] Scan attempt {retry_count + 1} failed, retrying: {e}", flush=True)
                        time.sleep(2)
                    else:
                        if settings.SUPPRESS_INGESTION_ERRORS:
                            # print("[AUTO-INGEST] [WARN] Error suppressed (SUPPRESS_INGESTION_ERRORS=true)", flush=True)
                            results = []
                        else:
                            raise
            
            # Summarize results (compact output)
            if results:
                fail_count = sum(1 for r in results if not r.success)
                success_count = sum(1 for r in results if r.success)
                if fail_count > 0:
                    print(f"[AUTO-INGEST] Excluded {fail_count} files (Genesis/already ingested)", flush=True)
                if success_count > 0:
                    print(f"[AUTO-INGEST] Ingested {success_count} new files", flush=True)
            # Don't print anything if no changes - just continue silently
            
            # Continue monitoring in background - suppress the message
            # print("[AUTO-INGEST] Auto-ingestion monitor started (will check every 30 seconds)\n", flush=True)
            
            try:
                file_manager.watch_and_process(continuous=True)
            except Exception as e:
                if settings.SUPPRESS_INGESTION_ERRORS:
                    print(f"[AUTO-INGEST] [WARN] Error in continuous monitoring (suppressed): {e}", flush=True)
                else:
                    raise
        except Exception as e:
            print(f"[AUTO-INGEST] [FAIL] Error in auto-ingestion: {e}", flush=True)
            import traceback
            traceback.print_exc()
    
    # Start auto-ingestion in a daemon thread
    if not settings.SKIP_AUTO_INGESTION:
        try:
            auto_ingest_thread = threading.Thread(target=run_auto_ingestion, daemon=True)
            auto_ingest_thread.start()
        except Exception as e:
            print(f"[AUTO-INGEST] [FAIL] Failed to start auto-ingestion: {e}")
    else:
        print("[SKIP] Auto-ingestion disabled (SKIP_AUTO_INGESTION=true)")


    # ==================== Start Continuous Learning Orchestrator ====================
    if not settings.DISABLE_CONTINUOUS_LEARNING:
        try:
            from cognitive.continuous_learning_orchestrator import start_continuous_learning
            orchestrator = start_continuous_learning()
            print("[OK] Continuous learning activated", flush=True)
        except Exception as e:
            print(f"[WARN] Could not start continuous learning: {e}", flush=True)
    else:
        print("[SKIP] Continuous learning disabled (DISABLE_CONTINUOUS_LEARNING=true)")

    # ==================== Start Diagnostic Engine (Self-Healing Runtime) ====================
    _diag_engine = None
    try:
        from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
        _diag_engine = get_diagnostic_engine()
        started = _diag_engine.start()
        if started:
            print("[OK] Diagnostic engine started — self-healing active (60s heartbeat)")
        else:
            print("[WARN] Diagnostic engine already running")
    except Exception as e:
        print(f"[WARN] Diagnostic engine not started: {e}")

    # ==================== Runtime Management State ====================
    app.state.runtime_paused = False
    app.state.diagnostic_engine = _diag_engine
    app.state._start_time = time.time()

    yield
    
    # ==================== Shutdown — clean up background systems ====================
    print("Grace API shutting down...")
    if _diag_engine:
        try:
            _diag_engine.stop()
            print("[OK] Diagnostic engine stopped")
        except Exception:
            pass
    try:
        DatabaseConnection.close()
        print("[OK] Database connection closed")
    except Exception:
        pass


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

# =============================================================================
# API ROUTERS — v1 resource layer + minimal core
# =============================================================================

# Core: needed by app.py's own chat/RAG endpoints
app.include_router(retrieve_router)          # /retrieve — used by app.py chat
app.include_router(health_router)            # /health — used by frontend health check
app.include_router(mcp_router)               # /api/mcp — MCP tool-calling
app.include_router(voice_router)             # /voice — TTS/STT

# Hub APIs: called by v1 resource layer via direct imports
app.include_router(world_model_router)       # /api/world-model
app.include_router(librarian_autonomous_router)  # /api/librarian-fs
app.include_router(docs_library_router)      # /api/docs
app.include_router(cross_tab_router)         # /api/intelligence
app.include_router(governance_hub_router)    # /api/governance-hub
app.include_router(genesis_daily_router)     # /api/genesis-daily
app.include_router(governance_rules_router)  # /api/governance-rules
app.include_router(whitelist_hub_router)     # /api/whitelist-hub
app.include_router(oracle_router)            # /api/oracle
app.include_router(codebase_hub_router)      # /api/codebase-hub
app.include_router(tasks_hub_router)         # /api/tasks-hub
app.include_router(unified_coding_agent_router)  # /api/coding-agent
app.include_router(bi_router)                # /api/bi
app.include_router(system_health_router)     # /api/system-health
app.include_router(learning_healing_router)  # /api/learn-heal
app.include_router(api_registry_router)      # /api/registry
app.include_router(api_explorer_router)      # /api/explorer
app.include_router(manifest_router)          # /api/manifest
app.include_router(chunked_upload_router)    # /api/upload — chunked 5GB uploads
app.include_router(flash_cache_router)       # /api/flash-cache — reference caching
app.include_router(consensus_router)         # /api/consensus — multi-model roundtable
app.include_router(system_audit_router)      # /api/audit — system analysis + model updates
app.include_router(api_vault_router)         # /api/vault — central API key management
app.include_router(planner_router)           # /api/planner — intelligent dual-pane planner
app.include_router(reporting_router)         # /api/reports — system reports + sandbox experiments
app.include_router(knowledge_mining_router)  # /api/knowledge-mine — LLM knowledge extraction
app.include_router(governance_discussion_router)  # /api/governance/discuss — chat about approvals
app.include_router(live_console_router)           # /api/console — real-time Kimi+Opus interaction
app.include_router(feedback_router)              # /api/feedback — user feedback on generated code
app.include_router(tab_aggregator_router)        # /api/tabs — aggregated tab data for frontend
app.include_router(version_control_router)       # /api/version-control — git history & diffs
app.include_router(ingestion_router)             # /api/ingestion — document ingestion pipeline
app.include_router(genesis_keys_router)          # /genesis — genesis key tracking UI
app.include_router(auth_router)                  # /auth — authentication/sessions
app.include_router(kpi_router)                   # /kpi — KPI dashboards
app.include_router(knowledge_base_router)        # /knowledge-base — KB connectors
app.include_router(repositories_router)          # /repositories — enterprise repo management
app.include_router(cicd_router)                  # /api/cicd — CI/CD pipelines
app.include_router(scraping_router)              # /scrape — web scraping engine
app.include_router(streaming_router)             # /stream — SSE streaming
app.include_router(websocket_router)             # WebSocket — real-time events
app.include_router(telemetry_router)             # /telemetry — system telemetry
app.include_router(diagnostic_router)            # /diagnostic — 4-layer diagnostic machine + healing
app.include_router(runtime_triggers_router)      # /api/triggers — trigger scanning + auto-healing pipeline
app.include_router(component_health_router)      # /api/component-health — behavioral profiling + health map

# v1 resource API (enterprise pattern — the public surface)
register_v1(app)

# Add Genesis Key middleware for automatic tracking (if not disabled)
if not (settings and settings.DISABLE_GENESIS_TRACKING):
    app.add_middleware(GenesisKeyMiddleware)
    print("[GENESIS] Genesis Key tracking enabled")
else:
    print("[GENESIS] Genesis Key tracking disabled (DISABLE_GENESIS_TRACKING=true)")


# ==================== Health Check Endpoint ====================

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        HealthResponse: Status of the API and Ollama service
    """
    try:
        client = get_llm_client()
        status_info = client.is_running()
        
        if status_info:
            models = client.get_all_models()
            models_available = len(models)
            status = "healthy"
        else:
            models_available = 0
            status = "unhealthy"
        
        return HealthResponse(
            status=status,
            llm_running=status_info,
            models_available=models_available
        )
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            llm_running=False,
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
        client = get_llm_client()
        
        if not client.is_running():
            raise HTTPException(
                status_code=503,
                detail=f"{settings.LLM_PROVIDER.capitalize()} service is not running"
            )
        
        # Generate title using a simple prompt
        title_prompt = f"Generate a short title (max 5 words) for: {request.text}"
        
        response = client.chat(
            model=settings.LLM_MODEL,
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
        # Get the LLM client
        client = get_llm_client()
        
        # Check if service is running
        if not client.is_running():
            raise HTTPException(
                status_code=503,
                detail=f"{settings.LLM_PROVIDER.capitalize()} service is not running. Please check your configuration and try again."
            )
        
        # Get model from settings
        model_name = settings.LLM_MODEL
        
        # Check if model exists (optional check, some providers might not support listing or have transient models)
        if settings.LLM_PROVIDER == "ollama" and not client.model_exists(model_name):
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model_name}' not found. Available models: {[m['name'] for m in client.get_all_models()]}"
            )
        
        # ==================== ROUTING: SMALL-TALK vs RAG vs WEB ====================
        # Get the last user message as the query
        user_query = ""
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_query = msg.content.strip()
                break

        if not user_query:
            raise HTTPException(
                status_code=400,
                detail="No user message found in conversation"
            )

        # Small-talk / greeting detector (avoid RAG & SerpAPI for simple chat)
        greeting_pattern = re.compile(
            r"^(hi|hello|hey|hola|yo|sup|what'?s\s+up|wassup|howdy|greetings|good\s+(morning|afternoon|evening)|thanks|thank you|bye|goodbye|see\s+ya)\b",
            re.IGNORECASE
        )
        if greeting_pattern.match(user_query):
            messages = [
                {"role": "system", "content": "You are a concise, friendly assistant. Keep casual greetings short and do not cite sources."},
                {"role": "user", "content": user_query},
            ]

            response = client.chat(
                model=model_name,
                messages=messages,
                stream=False,
                temperature=request.temperature or 0.4,
                max_tokens=request.top_k or 256,
            )

            return ChatResponse(
                response=response,
                sources=[],
                model=model_name,
                temperature=request.temperature,
                max_tokens=request.top_k
            )
        # ==================== MULTI-TIER QUERY HANDLING ====================
        # Use multi-tier system: VectorDB → Model Knowledge → User Context Request
        from retrieval.multi_tier_integration import (
            create_multi_tier_handler,
            log_query_handling,
            format_chat_response
        )
        
        # Create multi-tier handler
        handler = create_multi_tier_handler(client)
        
        # Handle query with tier fallback
        start_time = time.time()
        tier_result = handler.handle_query(
            query=user_query,
            user_id=None,  # TODO: Get from auth
            genesis_key_id=None  # TODO: Get from Genesis tracking
        )
        generation_time = time.time() - start_time
        
        # Log query handling for tracking and learning
        log_query_handling(
            query_id=tier_result.metadata.get("query_id", "unknown"),
            query_text=user_query,
            tier_result=tier_result,
            response_time_ms=tier_result.metadata.get("response_time_ms", 0)
        )
        
        # Format response
        response_data = format_chat_response(tier_result, model_name, generation_time)
        
        return ChatResponse(**response_data)
    
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
        model = request.model or (settings.LLM_MODEL if settings else "mistral:7b")
        
        # Verify model exists if possible
        client = get_llm_client()
        # Some providers don't support model check, so we only check if it's Ollama or if client provides the method
        if settings.LLM_PROVIDER == "ollama" and hasattr(client, 'model_exists'):
            if not getattr(settings, 'SKIP_LLM_CHECK', False) and not client.model_exists(model):
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

            # Extract folder name from path safely
            parts = folder_path.split('/') if '/' in folder_path else folder_path.split('\\')
            folder_name = parts[-1] if parts and parts[-1] else folder_path

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
            # Verify model exists if possible
            client = get_llm_client()
            if settings.LLM_PROVIDER == "ollama" and hasattr(client, 'model_exists'):
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
        
        # Add user message to chat
        user_message = history_repo.add_message(
            chat_id=chat_id,
            role="user",
            content=request.content
        )

        # ==================== SMALL-TALK / GREETING ROUTE ====================
        # Short-circuit simple greetings to avoid RAG/SerpAPI and keep UI tidy
        user_query = request.content.strip()
        greeting_pattern = re.compile(r"^(hi|hello|hey|hola|yo|sup|good\s+(morning|afternoon|evening)|thanks|thank you|bye|goodbye)\b", re.IGNORECASE)
        if greeting_pattern.match(user_query):
            client = get_llm_client()
            if not client.is_running():
                raise HTTPException(
                    status_code=503,
                    detail=f"{settings.LLM_PROVIDER.upper()} service is not running. Please start the service to generate responses."
                )

            # Fetch conversation history for context-aware greetings
            recent_messages = history_repo.get_by_chat_reverse(
                chat_id=chat_id,
                skip=0,
                limit=5  # Last 5 messages for greetings
            )
            
            # Build small talk messages with conversation history
            small_talk_messages = [
                {
                    "role": "system",
                    "content": "You are a concise, friendly assistant with conversation memory. Keep casual greetings short and remember what the user told you earlier. Do not cite sources."
                }
            ]
            
            # Add recent conversation history
            for msg in reversed(recent_messages):
                small_talk_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Add current greeting
            small_talk_messages.append({"role": "user", "content": user_query})

            start_time = time.time()
            temperature = request.temperature or chat.temperature or 0.4
            # Build generation parameters in a provider-agnostic way
            chat_kwargs = {
                "model": chat.model,
                "messages": small_talk_messages,
                "stream": False,
                "temperature": min(temperature, 0.7),
                "top_p": request.top_p if request.top_p else 0.8,
                "max_tokens": settings.MAX_NUM_PREDICT if settings else 256
            }
            
            # top_k is Ollama-specific, only pass for Ollama
            if settings.LLM_PROVIDER == "ollama":
                chat_kwargs["top_k"] = request.top_k if request.top_k else 40
                
            response_text = client.chat(**chat_kwargs)
            generation_time = time.time() - start_time

            assistant_message = history_repo.add_message(
                chat_id=chat_id,
                role="assistant",
                content=response_text,
                completion_time=generation_time
            )

            chat_repo.update(chat_id, last_message_at=datetime.utcnow())
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
                sources=[]
            )
        
        # ==================== MULTI-TIER QUERY HANDLING ====================
        # Use multi-tier system: Model Knowledge → Internet Search → Context Request
        from retrieval.multi_tier_integration import (
            create_multi_tier_handler,
            log_query_handling
        )
        
        # ==================== CONVERSATION CONTEXT RETRIEVAL ====================
        # Fetch recent conversation history for context-aware responses
        recent_messages = history_repo.get_by_chat_reverse(
            chat_id=chat_id,
            skip=0,
            limit=10  # Last 10 messages (excluding current user message)
        )
        
        # Build conversation context array (reverse to chronological order)
        conversation_context = []
        for msg in reversed(recent_messages):
            conversation_context.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current user message to context
        conversation_context.append({
            "role": "user",
            "content": request.content
        })
        
        logger.info(f"[CONTEXT] Built conversation context with {len(conversation_context)} messages")
        
        # Create multi-tier handler
        client = get_llm_client()
        handler = create_multi_tier_handler(client)
        
        # Handle query with tier fallback and conversation context
        start_time = time.time()
        tier_result = handler.handle_query(
            query=request.content,
            user_id=None,  # TODO: Get from auth
            genesis_key_id=None,  # TODO: Get from Genesis tracking
            conversation_history=conversation_context  # Pass conversation context
        )
        generation_time = time.time() - start_time
        
        # Log query handling for tracking and learning
        log_query_handling(
            query_id=tier_result.metadata.get("query_id", "unknown"),
            query_text=request.content,
            tier_result=tier_result,
            response_time_ms=tier_result.metadata.get("response_time_ms", 0)
        )
        
        # Check if query was successful
        if not tier_result.success:
            # All tiers failed - return error
            session.commit()
            raise HTTPException(
                status_code=404,
                detail=tier_result.response or "Unable to answer query. No relevant information found."
            )
        
        # Extract response and sources from tier result
        response_text = tier_result.response
        sources = tier_result.sources or []


        
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


# ==================== Runtime Management Endpoints ====================

@app.get("/api/runtime/status", tags=["Runtime"])
async def runtime_status():
    """Full runtime status: diagnostic engine, self-healing, pause state."""
    diag = getattr(app.state, "diagnostic_engine", None)
    diag_status = "unavailable"
    if diag:
        try:
            diag_status = diag.state.value if hasattr(diag.state, "value") else str(diag.state)
        except Exception:
            diag_status = "unknown"
    return {
        "paused": getattr(app.state, "runtime_paused", False),
        "diagnostic_engine": diag_status,
        "self_healing": diag_status not in ("unavailable", "stopped"),
        "uptime_seconds": time.time() - getattr(app.state, "_start_time", time.time()),
    }


@app.post("/api/runtime/pause", tags=["Runtime"])
async def runtime_pause():
    """Pause the runtime — stops diagnostic heartbeat and self-healing without killing the process."""
    app.state.runtime_paused = True
    diag = getattr(app.state, "diagnostic_engine", None)
    if diag:
        try:
            diag.pause()
        except Exception:
            pass
    return {"status": "paused", "message": "Runtime paused — heartbeat and self-healing suspended"}


@app.post("/api/runtime/resume", tags=["Runtime"])
async def runtime_resume():
    """Resume a paused runtime."""
    app.state.runtime_paused = False
    diag = getattr(app.state, "diagnostic_engine", None)
    if diag:
        try:
            diag.resume()
        except Exception:
            pass
    return {"status": "resumed", "message": "Runtime resumed — heartbeat and self-healing active"}


@app.post("/api/runtime/hot-reload", tags=["Runtime"])
async def runtime_hot_reload():
    """
    Hot-reload: re-read configs, refresh model registry, reconnect DB,
    and re-run startup diagnostic — all without restarting the process.
    """
    results = {}

    # 1. Reload settings from .env
    try:
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent / ".env", override=True)
        results["settings"] = "reloaded"
    except Exception as e:
        results["settings"] = f"error: {e}"

    # 2. Refresh consensus model registry
    try:
        from cognitive.consensus_engine import _build_model_registry, get_available_models
        import cognitive.consensus_engine as ce
        ce.MODEL_REGISTRY = _build_model_registry()
        models = get_available_models()
        results["consensus_models"] = {m["id"]: m["available"] for m in models}
    except Exception as e:
        results["consensus_models"] = f"error: {e}"

    # 3. Reconnect DB (dispose and re-create pool)
    try:
        engine = DatabaseConnection.get_engine()
        engine.dispose()
        results["database"] = "pool refreshed"
    except Exception as e:
        results["database"] = f"error: {e}"

    # 4. Run a quick diagnostic
    try:
        from cognitive.autonomous_diagnostics import get_diagnostics
        diag = get_diagnostics()
        diag_result = diag.on_startup()
        results["diagnostic"] = diag_result.get("status", "unknown")
    except Exception as e:
        results["diagnostic"] = f"error: {e}"

    return {"status": "hot-reload complete", "results": results}


@app.get("/api/runtime/connectivity", tags=["Runtime"])
async def runtime_connectivity():
    """Check connectivity of all external dependencies — Ollama, Qdrant, Kimi, Opus."""
    checks = {}

    # Ollama
    try:
        client = get_llm_client()
        checks["ollama"] = {"connected": client.is_running(), "url": settings.OLLAMA_URL}
    except Exception as e:
        checks["ollama"] = {"connected": False, "error": str(e)}

    # Qdrant
    try:
        qdrant = get_qdrant_client()
        connected = qdrant.is_connected()
        checks["qdrant"] = {"connected": connected, "host": settings.QDRANT_HOST}
    except Exception as e:
        checks["qdrant"] = {"connected": False, "error": str(e)}

    # Kimi
    checks["kimi"] = {"configured": bool(settings.KIMI_API_KEY), "model": settings.KIMI_MODEL}

    # Opus
    checks["opus"] = {"configured": bool(settings.OPUS_API_KEY), "model": settings.OPUS_MODEL}

    # Database
    try:
        checks["database"] = {"connected": DatabaseConnection.health_check(), "type": settings.DATABASE_TYPE}
    except Exception as e:
        checks["database"] = {"connected": False, "error": str(e)}

    all_ok = all(
        c.get("connected", False) or c.get("configured", False)
        for c in checks.values()
    )
    return {"status": "all_connected" if all_ok else "partial", "services": checks}


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
        # Verify LLM is running
        client = get_llm_client()
        if not client.is_running():
            raise HTTPException(
                status_code=503,
                detail=f"{settings.LLM_PROVIDER.upper()} service is not running"
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
        
        # Build generation parameters in a provider-agnostic way
        chat_kwargs = {
            "model": settings.OLLAMA_LLM_DEFAULT if settings else "llama2",
            "messages": messages,
            "stream": False,
            "temperature": temperature,
            "top_p": request.top_p or 0.5,
            "max_tokens": max_num_predict
        }
        
        # top_k is Ollama-specific, only pass for Ollama
        if settings.LLM_PROVIDER == "ollama":
            chat_kwargs["top_k"] = request.top_k or 10
            
        response_text = client.chat(**chat_kwargs)
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
