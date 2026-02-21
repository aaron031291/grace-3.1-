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
from api.codebase_api import router as codebase_router  # Codebase Browser - file browsing, search, analysis
from api.knowledge_base_api import router as knowledge_base_router  # Knowledge Base Connectors
from api.kpi_api import router as kpi_router  # KPI Dashboard tracking
from api.proactive_learning import router as proactive_learning_router  # Proactive Learning system
from api.repositories_api import router as repositories_router  # Enterprise Repository Management
from api.context_api import router as context_router  # Context submission for multi-tier queries
from api.telemetry import router as telemetry_router  # System Telemetry and monitoring
from api.monitoring_api import router as monitoring_router  # System Monitoring - organs, health, metrics
from api.streaming import router as streaming_router  # SSE Streaming chat responses
from api.websocket import router as websocket_router  # WebSocket real-time updates
from api.health import router as health_router  # Comprehensive health checks
from api.metrics import router as metrics_router  # Prometheus metrics endpoint
from api.learning_efficiency_api import router as learning_efficiency_router  # Learning Efficiency - Data-to-Insight tracking
from api.cicd_api import router as cicd_router  # Genesis CI/CD pipelines
from api.cicd_versioning_api import router as cicd_versioning_router  # CI/CD version control
from api.knowledge_base_cicd import router as kb_cicd_router  # Knowledge base CI/CD integration
from api.adaptive_cicd_api import router as adaptive_cicd_router  # Adaptive CI/CD with trust/KPIs
from api.ingestion_api import router as ingestion_router  # Librarian Ingestion Pipeline
from api.autonomous_api import router as autonomous_router  # Autonomous Action Engine
from api.whitelist_api import router as whitelist_router  # Whitelist Learning Pipeline - human input to learning
from api.testing_api import router as test_router  # Autonomous Testing - self-testing with KPI validation
from api.scraping import router as scraping_router  # Web Scraping - URL scraping and crawling
from diagnostic_machine.api import router as diagnostic_router  # 4-Layer Diagnostic Machine
from api.ide_bridge_api import router as ide_bridge_router  # Grace OS VSCode Extension IDE Bridge
from api.grace_todos_api import router as grace_todos_router  # Grace Autonomous Todos - task management with sub-agents
from api.grace_planning_api import router as grace_planning_router  # Grace Planning - concept-to-execution workflow
from api.mcp_api import router as mcp_router  # MCP - Model Context Protocol file/terminal/git tools
from api.bi_api import router as bi_router  # Business Intelligence - market research, campaigns, customer intelligence
from mobile.mobile_api import router as mobile_router  # Mobile companion app - push notifications, quick actions, voice commands
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
    
    # Check Ollama
    if not settings.SKIP_OLLAMA_CHECK:
        try:
            client = get_ollama_client()
            if client.is_running():
                models = client.get_all_models()
                print(f"[OK] Ollama is running with {len(models)} model(s)")
            else:
                print("[WARN] Ollama is not running - chat endpoint will be unavailable")
        except Exception as e:
            print(f"[WARN] Could not connect to Ollama: {e}")
    else:
        print("[SKIP] Ollama check skipped (SKIP_OLLAMA_CHECK=true)")
    
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

    # ==================== Initialize Unified Learning Pipeline ====================
    try:
        from cognitive.unified_learning_pipeline import get_unified_pipeline
        unified_pipeline = get_unified_pipeline()
        unified_pipeline.start()
        print("[OK] Unified Learning Pipeline started - 24/7 neighbor-by-neighbor expansion active")
    except Exception as e:
        print(f"[WARN] Unified Learning Pipeline not available: {e}")

    # ==================== Genesis# Component Registry ====================
    try:
        from genesis.component_registry import auto_register_all_components
        from database.session import SessionLocal
        reg_session = SessionLocal()
        if reg_session:
            count = auto_register_all_components(reg_session)
            reg_session.close()
            print(f"[OK] Genesis# Component Registry: {count} components auto-registered")
    except Exception as e:
        print(f"[WARN] Component Registry not available: {e}")

    # ==================== Genesis Handshake Protocol ====================
    try:
        from genesis.handshake_protocol import get_handshake_protocol
        handshake = get_handshake_protocol()
        handshake.start()
        print("[OK] Genesis Handshake Protocol started - heartbeat monitoring active")
    except Exception as e:
        print(f"[WARN] Handshake Protocol not available: {e}")

    # ==================== Unified Intelligence Daemon ====================
    try:
        from genesis.unified_intelligence import get_intelligence_daemon
        intel_daemon = get_intelligence_daemon()
        intel_daemon.start()
        print("[OK] Unified Intelligence Daemon started - collecting from all subsystems")
    except Exception as e:
        print(f"[WARN] Unified Intelligence Daemon not available: {e}")

    # ==================== Self-* Closed-Loop Ecosystem ====================
    try:
        from cognitive.self_agent_ecosystem import get_closed_loop
        from database.session import SessionLocal
        cl_session = SessionLocal()
        if cl_session:
            closed_loop = get_closed_loop(cl_session)
            closed_loop.start(interval=300)
            print("[OK] Self-* Closed-Loop Ecosystem started - 6 agents, autonomous improvement")
    except Exception as e:
        print(f"[WARN] Closed-Loop Ecosystem not available: {e}")

    # ==================== TimeSense Governance ====================
    try:
        from cognitive.timesense_governance import get_timesense_governance
        ts_gov = get_timesense_governance()
        print(f"[OK] TimeSense Governance active - {len(ts_gov.slas)} SLAs across 12 components")
    except Exception as e:
        print(f"[WARN] TimeSense Governance not available: {e}")

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
    # Connect sandbox lab to continuous training data
    if not settings.DISABLE_CONTINUOUS_LEARNING:
        try:
            from cognitive.continuous_learning_orchestrator import start_continuous_learning
            # print("\n[CONTINUOUS_LEARNING] Starting continuous autonomous learning orchestration...", flush=True)
            orchestrator = start_continuous_learning()
            print("[OK] Continuous learning activated", flush=True)
            # Suppress verbose startup messages
            # print("[CONTINUOUS_LEARNING] Grace will now continuously:", flush=True)
            # print("  - Ingest new data from knowledge_base", flush=True)
            # print("  - Learn autonomously from content", flush=True)
            # print("  - Mirror observes and proposes experiments", flush=True)
            # print("  - Run sandbox experiments and trials", flush=True)
            # print("  - Request approval for validated improvements", flush=True)
            # print("[CONTINUOUS_LEARNING] Grace's continuous self-improvement loop is active!\n", flush=True)
        except Exception as e:
            print(f"[WARN] Could not start continuous learning: {e}", flush=True)
    else:
        print("[SKIP] Continuous learning disabled (DISABLE_CONTINUOUS_LEARNING=true)")

    # ==================== UNIFIED SUBSYSTEM ACTIVATION ====================
    # Wire ALL disconnected Claude subsystems: Layer 1 Message Bus, Component Registry,
    # Cognitive Engine, Magma Memory, Diagnostic Engine, Systems Integration, Autonomous Engine
    try:
        from startup import initialize_all_subsystems, get_subsystems
        
        db_session = None
        try:
            db_session = SessionLocal()
        except Exception:
            pass
        
        subsystems = initialize_all_subsystems(session=db_session, settings=settings)
        
    except Exception as e:
        print(f"[WARN] Subsystem activation error (non-fatal): {e}")
        import traceback
        traceback.print_exc()

    yield
    
    # Shutdown
    print("Grace API shutting down...")
    
    # Graceful subsystem shutdown
    try:
        from startup import get_subsystems
        subs = get_subsystems()
        
        # Save TimeSense state
        if subs.timesense:
            try:
                subs.timesense.save_state()
                print("[SHUTDOWN] TimeSense state saved")
            except Exception:
                pass
        
        # Save Self-Mirror state
        if subs.self_mirror:
            try:
                subs.self_mirror.save_state()
                subs.self_mirror.stop_heartbeat()
                print("[SHUTDOWN] Self-Mirror state saved")
            except Exception:
                pass
        
        # Save Magma state
        if subs.magma:
            try:
                if hasattr(subs, '_magma_persistence') and subs._magma_persistence:
                    subs._magma_persistence.save(subs.magma)
                    print("[SHUTDOWN] Magma Memory state saved")
                if hasattr(subs.magma, 'stop_background_processing'):
                    subs.magma.stop_background_processing()
            except Exception:
                pass
        
        # Stop Diagnostic Engine
        if subs.diagnostic_engine:
            try:
                subs.diagnostic_engine.stop()
                print("[SHUTDOWN] Diagnostic Engine stopped")
            except Exception:
                pass
        
        print("[SHUTDOWN] All subsystems stopped gracefully")
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

# Add TimeSense auto-instrumentation (times every API request automatically)
try:
    from cognitive.timesense_enhanced import TimeSenseMiddleware
    app.add_middleware(TimeSenseMiddleware)
    print("[TIMESENSE] Auto-instrumentation middleware active (timing all API requests)")
except Exception as e:
    print(f"[TIMESENSE] Auto-instrumentation not available: {e}")

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
app.include_router(learning_efficiency_router)  # Learning Efficiency - Data-to-Insight tracking
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
app.include_router(codebase_router)  # Codebase Browser - file browsing, code search, commit history, analysis
app.include_router(knowledge_base_router)  # Knowledge Base Connectors - external knowledge sources
app.include_router(kpi_router)  # KPI Dashboard - system health and performance metrics
app.include_router(proactive_learning_router)  # Proactive Learning - task queue and autonomous learning
app.include_router(repositories_router)  # Enterprise Repository Management - multi-repo support
app.include_router(telemetry_router)  # System Telemetry - drift detection, baselines, alerts
app.include_router(monitoring_router)  # System Monitoring - organs of grace, health, metrics
app.include_router(streaming_router)  # SSE Streaming - real-time chat response streaming
app.include_router(websocket_router)  # WebSocket - real-time bidirectional updates
app.include_router(health_router)  # Comprehensive health checks for all services
app.include_router(metrics_router)  # Prometheus metrics - /metrics endpoint
app.include_router(cicd_router)  # Genesis CI/CD - self-hosted pipelines
app.include_router(cicd_versioning_router)  # CI/CD Version Control - audit trail
app.include_router(kb_cicd_router)  # Knowledge Base CI/CD - autonomous triggers
app.include_router(adaptive_cicd_router)  # Adaptive CI/CD - trust, KPIs, LLM, governance
app.include_router(ingestion_router)  # Librarian Ingestion Pipeline - Genesis-tracked data flow
app.include_router(autonomous_router)  # Autonomous Action Engine - self-triggered actions
app.include_router(whitelist_router)  # Whitelist Learning Pipeline - human input to GRACE learning
app.include_router(test_router)  # Autonomous Testing - self-testing with KPI validation
app.include_router(scraping_router)  # Web Scraping - URL scraping and crawling
app.include_router(diagnostic_router)  # 4-Layer Diagnostic Machine - sensors, interpreters, judgement, action
app.include_router(ide_bridge_router)  # Grace OS VSCode Extension - IDE Bridge for cognitive IDE
app.include_router(grace_todos_router)  # Grace Autonomous Todos - drag-drop task management with sub-agents
app.include_router(grace_planning_router)  # Grace Planning - concept→questions→tech→decisions→execute→IDE workflow
app.include_router(unified_pipeline_router)  # Unified Learning Pipeline - 24/7 neighbor-by-neighbor knowledge expansion
app.include_router(knowledge_browser_router)  # Knowledge Browser - domain-organized Oracle file system
app.include_router(llm_learning_router)  # LLM Learning & Tracking - learn from Kimi, track reasoning, reduce LLM dependency
app.include_router(context_router)  # Context API - user context submission for multi-tier queries
app.include_router(mcp_router)  # MCP - Model Context Protocol file/terminal/git tools for Grace OS
app.include_router(bi_router)  # Business Intelligence - market research, campaigns, customer intelligence, product discovery
app.include_router(mobile_router)  # Mobile companion app - push notifications, quick actions, voice commands, camera-to-knowledge

# Add Genesis Key middleware for automatic tracking (if not disabled)
if not (settings and settings.DISABLE_GENESIS_TRACKING):
    app.add_middleware(GenesisKeyMiddleware)
    print("[GENESIS] Genesis Key tracking enabled")
else:
    print("[GENESIS] Genesis Key tracking disabled (DISABLE_GENESIS_TRACKING=true)")

# Add Governance Enforcement middleware for AI output safety
try:
    from security.governance_middleware import GovernanceEnforcementMiddleware
    app.add_middleware(GovernanceEnforcementMiddleware, enable_enforcement=True)
    print("[GOVERNANCE] Governance enforcement middleware active")
except Exception as e:
    print(f"[WARN] Governance middleware not loaded: {e}")


# ==================== Auth + CSRF Enforcement ====================
# Sensitive endpoints require authentication via Genesis ID
# CSRF protection on state-changing operations

from security.auth import get_current_user, get_optional_user, require_auth, generate_csrf_token, validate_csrf_token

# CSRF middleware for state-changing requests
class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """Enforce CSRF tokens on POST/PUT/DELETE to sensitive endpoints."""

    PROTECTED_PREFIXES = [
        "/agent/", "/llm-learning/grace/", "/llm-learning/tools/call",
        "/api/autonomous/", "/governance/", "/api/cicd/",
    ]
    EXEMPT_PREFIXES = [
        "/chat", "/chats", "/health", "/docs", "/openapi.json",
        "/ingest", "/retrieve", "/llm-learning/track",
    ]

    async def dispatch(self, request, call_next):
        if request.method in ("POST", "PUT", "DELETE"):
            path = request.url.path
            is_protected = any(path.startswith(p) for p in self.PROTECTED_PREFIXES)
            is_exempt = any(path.startswith(p) for p in self.EXEMPT_PREFIXES)

            if is_protected and not is_exempt:
                csrf_token = request.headers.get("X-CSRF-Token")
                session_csrf = request.cookies.get("csrf_token")
                if csrf_token and session_csrf:
                    import secrets
                    if not secrets.compare_digest(csrf_token, session_csrf):
                        return JSONResponse(status_code=403, content={"detail": "CSRF token mismatch"})

        return await call_next(request)

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse as StarletteJSONResponse

# Only enable CSRF in production mode
_sec_config = get_security_config()
if _sec_config.PRODUCTION_MODE:
    app.add_middleware(CSRFProtectionMiddleware)
    print("[SECURITY] CSRF protection enabled (production mode)")
else:
    print("[SECURITY] CSRF protection available (enable with PRODUCTION_MODE=true)")


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
        
        # ==================== INPUT SANITIZATION ====================
        # Validate user input before processing to prevent injection attacks
        try:
            from security.validators import get_validator
            _validator = get_validator()
            for msg in request.messages:
                _valid, _sanitized, _err = _validator.validate_string(
                    msg.content, max_length=50000, allow_html=False, field_name="message"
                )
                if not _valid:
                    raise HTTPException(status_code=400, detail=f"Invalid input: {_err}")
        except HTTPException:
            raise
        except Exception:
            pass  # Validator not available, continue without

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

        # ==================== UNIFIED INTELLIGENCE CHAIN ====================
        # Query ALL 9 intelligence layers in order before falling through to LLM.
        # Layers 1-6 are 100% deterministic (no LLM needed).
        # Layer 7 is RAG (high confidence vector search).
        # Layer 8 is Oracle ML (prediction).
        # Layer 9 signals "needs LLM" -- falls through to existing Ollama call below.
        try:
            from cognitive.unified_intelligence import get_unified_intelligence
            from database.session import SessionLocal

            _ui_session = SessionLocal()
            _ui = get_unified_intelligence(_ui_session)

            _ui_result = _ui.query(
                question=user_query,
                min_confidence=0.7,
                max_layer=8,  # Don't call LLM here -- existing code below handles that
            )

            if _ui_result.answered and _ui_result.confidence >= 0.7:
                logger.info(
                    f"[UNIFIED] Answered by Layer {_ui_result.layer_number} "
                    f"({_ui_result.layer_used}), confidence={_ui_result.confidence:.2f}, "
                    f"deterministic={_ui_result.deterministic}, {_ui_result.duration_ms:.1f}ms"
                )

                _ui_session.close()
                return ChatResponse(
                    response=_ui_result.response,
                    sources=[{
                        "text": f"Answered by Grace's {_ui_result.layer_used} (Layer {_ui_result.layer_number})",
                        "score": _ui_result.confidence,
                    }],
                    model=f"grace:{_ui_result.layer_used}",
                    temperature=request.temperature,
                )

            _ui_session.close()
        except Exception as _ui_err:
            logger.debug(f"[UNIFIED] Chain error (non-fatal): {_ui_err}")

        # ==================== KIMI CONSULTATION ====================
        # If unified intelligence couldn't answer, consult Kimi Brain
        # before falling through to raw LLM. Kimi can compose from
        # facts, reason about the system, and produce a smarter answer.
        try:
            from cognitive.kimi_brain import get_kimi_brain
            from database.session import SessionLocal

            _kimi_session = SessionLocal()
            _kimi = get_kimi_brain(_kimi_session)

            _kimi_result = _kimi.consult(user_query, requester="chat_endpoint")

            if _kimi_result.get("answered") and _kimi_result.get("response"):
                response_text = _kimi_result["response"]
                if len(response_text) > 20:
                    logger.info(f"[KIMI-CONSULT] Kimi answered from {_kimi_result.get('source', 'analysis')}")
                    _kimi_session.close()
                    return ChatResponse(
                        response=response_text,
                        sources=[{
                            "text": f"Answered by Kimi ({_kimi_result.get('source', 'analysis')})",
                            "score": 0.7,
                        }],
                        model="kimi:brain",
                        temperature=request.temperature,
                    )

            _kimi_session.close()
        except Exception as _kimi_err:
            logger.debug(f"[KIMI-CONSULT] Error (non-fatal): {_kimi_err}")

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
                num_predict=request.top_k or 256,
            )

            # Track greeting in learning pipeline
            try:
                from cognitive.llm_interaction_tracker import get_llm_interaction_tracker
                from database.session import SessionLocal
                _gs = SessionLocal()
                get_llm_interaction_tracker(_gs).record_interaction(
                    prompt=user_query, response=response[:500],
                    model_used=model_name, interaction_type="question_answer",
                    outcome="success", confidence_score=0.95, duration_ms=0,
                )
                _gs.commit()
                _gs.close()
            except Exception:
                pass

            return ChatResponse(
                response=response,
                sources=[],
                model=model_name,
                temperature=request.temperature,
                max_tokens=request.top_k
            )
        # ==================== MAGMA-ENHANCED MULTI-TIER QUERY HANDLING ====================
        # Magma graph memory enriches the retrieval before multi-tier handles it
        from retrieval.multi_tier_integration import (
            create_multi_tier_handler,
            log_query_handling,
            format_chat_response
        )
        
        # Try Magma-enhanced context first
        try:
            from cognitive.magma.chat_integration import get_magma_enhanced_context
            magma_result = get_magma_enhanced_context(user_query, limit=3)
        except Exception:
            magma_result = None
        
        # Create multi-tier handler
        handler = create_multi_tier_handler(client)
        
        # Handle query with tier fallback
        start_time = time.time()
        tier_result = handler.handle_query(
            query=user_query,
            user_id=None,
            genesis_key_id=None
        )
        generation_time = time.time() - start_time
        
        # Log query handling for tracking and learning
        log_query_handling(
            query_id=tier_result.metadata.get("query_id", "unknown"),
            query_text=user_query,
            tier_result=tier_result,
            response_time_ms=tier_result.metadata.get("response_time_ms", 0)
        )
        
        # Track in TimeSense
        try:
            from cognitive.timesense import get_timesense
            get_timesense().record_operation(
                "chat.query", generation_time * 1000, "chat",
                data_bytes=float(len(user_query)),
            )
        except Exception:
            pass
        
        # Feed interaction back to Magma for learning
        try:
            from cognitive.magma.chat_integration import ingest_chat_interaction
            response_data = format_chat_response(tier_result, model_name, generation_time)
            ingest_chat_interaction(user_query, response_data.get("message", ""))
        except Exception:
            response_data = format_chat_response(tier_result, model_name, generation_time)
        
        # Add Magma sources if available
        if magma_result and "sources" in magma_result:
            existing_sources = response_data.get("sources") or []
            response_data["sources"] = existing_sources + magma_result["sources"]

        # ==================== RETRIEVAL QUALITY TRACKING ====================
        # Track which retrieved chunks were useful in the final response
        try:
            from cognitive.knowledge_indexer import get_retrieval_quality_tracker
            from database.session import SessionLocal
            _rq_session = SessionLocal()
            _rq_tracker = get_retrieval_quality_tracker(_rq_session)

            sources = response_data.get("sources") or []
            if sources and isinstance(sources, list):
                _rq_tracker.record_retrieval_usage(
                    retrieved_chunks=sources,
                    final_response=response_data.get("message", ""),
                )
                _rq_session.commit()
            _rq_session.close()
        except Exception:
            pass

        # ==================== DISTILL LLM RESPONSE ====================
        # Store this LLM response in distilled knowledge for future use.
        # Next time someone asks the same/similar question, Grace can
        # answer from the store without calling the LLM.
        try:
            from cognitive.knowledge_compiler import get_llm_knowledge_miner
            from database.session import SessionLocal

            _dist_session = SessionLocal()
            _dist_miner = get_llm_knowledge_miner(_dist_session)
            _dist_miner.store_interaction(
                query=user_query,
                response=response_data.get("message", "")[:10000],
                model_used=model_name,
                confidence=tier_result.confidence if hasattr(tier_result, 'confidence') else 0.6,
                domain=None,
            )
            _dist_session.commit()
            _dist_session.close()
        except Exception as _dist_err:
            logger.debug(f"[DISTILL] Storage error (non-fatal): {_dist_err}")

        # ==================== KIMI LEARNING PIPELINE ====================
        # Track every chat interaction for learning. Run hallucination check.
        # This activates the entire Kimi+Grace learning system for ALL traffic.
        try:
            from cognitive.llm_interaction_tracker import get_llm_interaction_tracker
            from database.session import SessionLocal

            _track_session = SessionLocal()
            tracker = get_llm_interaction_tracker(_track_session)

            response_text = response_data.get("message", "")

            tracker.record_interaction(
                prompt=user_query,
                response=response_text[:5000],
                model_used=model_name,
                interaction_type="question_answer",
                outcome="success",
                confidence_score=tier_result.confidence if hasattr(tier_result, 'confidence') else 0.7,
                duration_ms=generation_time * 1000,
                context_used={"tier": tier_result.tier_used if hasattr(tier_result, 'tier_used') else "unknown"},
                reasoning_chain=[
                    {"action": "observe", "thought": f"User query: {user_query[:100]}"},
                    {"action": "retrieve", "thought": f"Retrieved from knowledge base"},
                    {"action": "generate", "thought": f"Generated response via {model_name}"},
                ],
            )
            _track_session.commit()
            _track_session.close()
        except Exception as _track_err:
            logger.debug(f"[CHAT-TRACK] Tracking error (non-fatal): {_track_err}")

        # Run near-zero hallucination check WITH RAG context for contradiction detection
        try:
            from startup import get_subsystems
            _subs = get_subsystems()
            if _subs.near_zero_guard:
                # Extract RAG source texts to pass as context_documents
                _context_docs = []
                try:
                    _sources = response_data.get("sources") or []
                    for _src in _sources[:10]:
                        _src_text = _src.get("text", "") if isinstance(_src, dict) else str(_src)
                        if _src_text:
                            _context_docs.append(_src_text[:1000])
                except Exception:
                    pass

                _verify_result = _subs.near_zero_guard.verify(
                    prompt=user_query,
                    content=response_data.get("message", ""),
                    task_type="general",
                    context_documents=_context_docs if _context_docs else None,
                    max_retries=0,
                )
                response_data["hallucination_check"] = {
                    "verified": _verify_result.is_verified,
                    "probability": _verify_result.hallucination_probability,
                    "claims_verified": _verify_result.verified_claims,
                    "claims_total": _verify_result.total_claims,
                }

                # Feed hallucination results back to learning tracker
                try:
                    if _track_session and not _track_session.is_active:
                        _track_session = SessionLocal()
                    _ltracker = get_llm_interaction_tracker(_track_session)
                    _ltracker.record_interaction(
                        prompt=f"[HALLUCINATION_CHECK] {user_query[:200]}",
                        response=f"verified={_verify_result.is_verified}, prob={_verify_result.hallucination_probability:.3f}",
                        model_used="near_zero_guard",
                        interaction_type="reasoning",
                        outcome="success" if _verify_result.is_verified else "failure",
                        confidence_score=1.0 - _verify_result.hallucination_probability,
                        metadata={"claims_total": _verify_result.total_claims, "claims_verified": _verify_result.verified_claims},
                    )
                    _track_session.commit()
                    _track_session.close()
                except Exception:
                    pass
        except Exception as _guard_err:
            logger.debug(f"[CHAT-GUARD] Guard error (non-fatal): {_guard_err}")

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
        model = request.model or (settings.OLLAMA_LLM_DEFAULT if settings else "mistral:7b")
        
        # Verify model exists
        client = get_ollama_client()
        if not getattr(settings, 'SKIP_OLLAMA_CHECK', False) and not client.model_exists(model):
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
            client = get_ollama_client()
            if not client.is_running():
                raise HTTPException(
                    status_code=503,
                    detail="Ollama service is not running. Please start Ollama to generate responses."
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
            response_text = client.chat(
                model=chat.model,
                messages=small_talk_messages,  # Now includes conversation history
                stream=False,
                temperature=min(temperature, 0.7),
                top_p=request.top_p if request.top_p else 0.8,
                top_k=request.top_k if request.top_k else 40,
                num_predict=settings.MAX_NUM_PREDICT if settings else 256
            )
            generation_time = time.time() - start_time

            assistant_message = history_repo.add_message(
                chat_id=chat_id,
                role="assistant",
                content=response_text,
                completion_time=generation_time
            )

            chat_repo.update(chat_id, last_message_at=datetime.now())
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
        
        # ==================== GENESIS# ROUTING ====================
        # If user prompt contains Genesis#<component>, route through Genesis system
        genesis_route_result = None
        try:
            from genesis.genesis_hash_router import get_genesis_hash_router
            genesis_router = get_genesis_hash_router()
            if genesis_router.has_genesis_ref(user_query):
                genesis_route_result = genesis_router.route(user_query)
                if genesis_route_result:
                    logger.info(
                        f"[GENESIS#] Routed {genesis_route_result['genesis_refs_found']} reference(s)"
                    )
        except Exception as e:
            logger.debug(f"[GENESIS#] Routing skipped: {e}")

        # ==================== CHAT INTELLIGENCE ====================
        # Wire in ambiguity detection, governance, episodic memory, Oracle routing
        from cognitive.chat_intelligence import get_chat_intelligence
        chat_intel = get_chat_intelligence()

        # Phase 1: Detect ambiguity in user query
        ambiguity_result = None
        try:
            ambiguity_result = chat_intel.detect_ambiguity(
                user_query,
                conversation_history=[]
            )
            if ambiguity_result and ambiguity_result.get("is_ambiguous"):
                logger.info(
                    f"[CHAT-INTEL] Ambiguity detected: level={ambiguity_result['ambiguity_level']}, "
                    f"signals={ambiguity_result['ambiguity_signals']}"
                )
        except Exception as e:
            logger.debug(f"[CHAT-INTEL] Ambiguity detection skipped: {e}")

        # Phase 2: Reasoning Router — classify into Tier 0/1/2/3
        reasoning_tier = 1  # Default: standard
        try:
            from llm_orchestrator.reasoning_router import get_reasoning_router
            rr = get_reasoning_router()
            ambiguity_score = ambiguity_result.get("ambiguity_score", 0) if ambiguity_result else 0
            routing_decision = rr.classify(
                query=user_query,
                ambiguity_score=ambiguity_score,
            )
            reasoning_tier = routing_decision.tier
            logger.info(
                f"[REASONING-ROUTER] Tier {routing_decision.tier_name}: {routing_decision.reason} "
                f"(est. {routing_decision.estimated_time_ms:.0f}ms)"
            )
        except Exception as e:
            logger.debug(f"[REASONING-ROUTER] Classification skipped: {e}")

        # Phase 2b: Oracle query routing prediction
        try:
            routing_prediction = chat_intel.predict_query_routing(user_query)
            logger.info(
                f"[CHAT-INTEL] Oracle routing: tier={routing_prediction.get('predicted_tier')}, "
                f"confidence={routing_prediction.get('confidence')}"
            )
        except Exception as e:
            logger.debug(f"[CHAT-INTEL] Oracle routing skipped: {e}")

        # ==================== TIERED REASONING EXECUTION ====================
        # reasoning_tier from the router determines HOW we process this query
        # Tier 0: handled by greeting detector above
        # Tier 2: parallel consensus (Layer 1 only)
        # Tier 3: full 3-layer reasoning (L1 + L2 + L3)
        # Tier 1: standard multi-tier (default path below)

        if reasoning_tier >= 2:
            try:
                from llm_orchestrator.three_layer_reasoning import get_three_layer_reasoning
                deep_pipeline = get_three_layer_reasoning()
                start_time = time.time()

                if reasoning_tier == 2:
                    # Tier 2: Layer 1 only (parallel consensus)
                    l1_result = deep_pipeline.layer1_parallel_reasoning(user_query)
                    generation_time = time.time() - start_time
                    if l1_result.outputs:
                        best = max(l1_result.outputs, key=lambda o: len(o.reasoning))
                        response_text = best.reasoning
                        sources = []
                        logger.info(f"[TIER-2] Consensus from {len(l1_result.outputs)} models, agreement={l1_result.agreement_score:.2f}")

                        # Governance + HIA check on T2 output
                        try:
                            gov = chat_intel.check_governance(response_text, has_sources=False)
                            if not gov.get("passed"):
                                logger.warning(f"[TIER-2] Governance issue: {gov.get('violations')}")
                        except Exception:
                            pass

                        # Episodic memory for T2
                        try:
                            chat_intel.record_episode(user_query, response_text, [], "consensus", l1_result.agreement_score, generation_time, chat_id)
                        except Exception:
                            pass

                        assistant_message = history_repo.add_message(
                            chat_id=chat_id, role="assistant",
                            content=response_text, completion_time=generation_time
                        )
                        chat_repo.update(chat_id, last_message_at=datetime.now())
                        total_tokens = history_repo.count_tokens_in_chat(chat_id)
                        return PromptResponse(
                            chat_id=chat_id, user_message_id=user_message.id,
                            assistant_message_id=assistant_message.id,
                            message=response_text, model=chat.model,
                            generation_time=generation_time, tokens_used=None,
                            total_tokens_in_chat=total_tokens, sources=sources
                        )
                else:
                    # Tier 3: Full 3-layer reasoning
                    verified = deep_pipeline.reason(user_query)
                    generation_time = time.time() - start_time
                    response_text = verified.answer
                    sources = []
                    logger.info(
                        f"[TIER-3] 3-layer complete: confidence={verified.confidence:.1%}, "
                        f"grounded={verified.training_data_grounded}"
                    )

                    # Governance + HIA on T3 output
                    try:
                        gov = chat_intel.check_governance(response_text, has_sources=verified.training_data_grounded)
                    except Exception:
                        pass

                    # Episodic memory for T3
                    try:
                        chat_intel.record_episode(user_query, response_text, [], "deep_reasoning", verified.confidence, generation_time, chat_id)
                    except Exception:
                        pass

                    assistant_message = history_repo.add_message(
                        chat_id=chat_id, role="assistant",
                        content=response_text, completion_time=generation_time
                    )
                    chat_repo.update(chat_id, last_message_at=datetime.now())
                    total_tokens = history_repo.count_tokens_in_chat(chat_id)
                    return PromptResponse(
                        chat_id=chat_id, user_message_id=user_message.id,
                        assistant_message_id=assistant_message.id,
                        message=response_text, model=chat.model,
                        generation_time=generation_time, tokens_used=None,
                        total_tokens_in_chat=total_tokens, sources=sources
                    )
            except Exception as e:
                logger.warning(f"[TIER-{reasoning_tier}] Deep reasoning failed, falling back to standard: {e}")

        # ==================== STANDARD MULTI-TIER QUERY HANDLING (Tier 1) ====================
        from retrieval.multi_tier_integration import (
            create_multi_tier_handler,
            log_query_handling
        )
        
        # ==================== CONVERSATION CONTEXT RETRIEVAL ====================
        recent_messages = history_repo.get_by_chat_reverse(
            chat_id=chat_id, skip=0, limit=10
        )
        
        conversation_context = []
        for msg in reversed(recent_messages):
            conversation_context.append({"role": msg.role, "content": msg.content})
        conversation_context.append({"role": "user", "content": request.content})
        
        logger.info(f"[CONTEXT] Built conversation context with {len(conversation_context)} messages")
        
        # Create multi-tier handler with trust-aware retrieval
        client = get_ollama_client()
        handler = create_multi_tier_handler(client)
        
        start_time = time.time()
        tier_result = handler.handle_query(
            query=request.content,
            user_id=None,
            genesis_key_id=None,
            conversation_history=conversation_context
        )
        generation_time = time.time() - start_time
        
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

        # Phase 3: Governance check on response
        governance_result = None
        try:
            governance_result = chat_intel.check_governance(response_text)
            if not governance_result.get("passed"):
                logger.warning(
                    f"[CHAT-INTEL] Governance violation: {governance_result.get('violations')}"
                )
        except Exception as e:
            logger.debug(f"[CHAT-INTEL] Governance check skipped: {e}")

        # Phase 4: Enrich response with ambiguity questions / governance notes
        try:
            response_text = chat_intel.enrich_response(
                response_text, ambiguity_result, governance_result
            )
        except Exception as e:
            logger.debug(f"[CHAT-INTEL] Response enrichment skipped: {e}")

        # Phase 4b: Inject Genesis# confirmation if present
        if genesis_route_result and genesis_route_result.get("components"):
            genesis_msg = genesis_route_result.get("system_message", "")
            if genesis_msg:
                response_text = f"**[Genesis#]** {genesis_msg}\n\n{response_text}"

        # Phase 4c: Magma Memory context enrichment
        try:
            from cognitive.magma.grace_magma_system import get_grace_magma
            magma = get_grace_magma()
            if magma:
                magma.ingest(f"Q: {request.content[:200]} A: {response_text[:200]}")
        except Exception:
            pass

        # Phase 4d: User preference observation + personalization
        try:
            from cognitive.user_preference_model import UserPreferenceEngine
            from database.session import SessionLocal
            _up_session = SessionLocal()
            if _up_session:
                try:
                    genesis_id = request.headers.get("X-Genesis-ID", "") if hasattr(request, 'headers') else ""
                    if not genesis_id:
                        genesis_id = str(chat_id)
                    up_engine = UserPreferenceEngine(_up_session)
                    up_engine.observe_interaction(genesis_id, user_query, len(response_text))
                finally:
                    _up_session.close()
        except Exception:
            pass

        # Verify response is not a rejection/failure message from the model
        response_text = response_text.strip()
        
        # Add assistant message to chat
        assistant_message = history_repo.add_message(
            chat_id=chat_id,
            role="assistant",
            content=response_text,
            completion_time=generation_time
        )

        # Phase 5: Record episode for learning (non-blocking)
        try:
            import asyncio
            asyncio.create_task(asyncio.to_thread(
                chat_intel.record_episode,
                user_query=request.content,
                response=response_text,
                sources_used=sources,
                tier_used=tier_result.tier.value if hasattr(tier_result, 'tier') else "unknown",
                confidence=tier_result.confidence.overall_score if hasattr(tier_result, 'confidence') and hasattr(tier_result.confidence, 'overall_score') else 0.5,
                generation_time=generation_time,
                chat_id=chat_id
            ))
        except Exception as e:
            logger.debug(f"[CHAT-INTEL] Episode recording skipped: {e}")

        # Phase 6: Feed topic to unified learning pipeline for neighbor expansion
        try:
            from cognitive.unified_learning_pipeline import get_unified_pipeline
            pipeline = get_unified_pipeline()
            if pipeline.running:
                pipeline.add_seed(
                    topic=request.content[:100],
                    text=request.content
                )
        except Exception as e:
            logger.debug(f"[CHAT-INTEL] Pipeline seed skipped: {e}")

        # Phase 7: Kimi Knowledge Feedback — embed high-quality answers into vector DB
        try:
            from cognitive.kimi_knowledge_feedback import get_kimi_feedback
            kimi_fb = get_kimi_feedback()
            confidence = tier_result.confidence.overall_score if hasattr(tier_result, 'confidence') and hasattr(tier_result.confidence, 'overall_score') else 0.5
            kimi_fb.feed_answer(
                question=request.content,
                answer=response_text,
                confidence=confidence,
                tier_used=tier_result.tier.value if hasattr(tier_result, 'tier') else "unknown",
                sources_count=len(sources) if sources else 0,
                chat_id=chat_id,
            )
        except Exception as e:
            logger.debug(f"[KIMI-FEEDBACK] Skipped: {e}")
        
        # Update chat's last_message_at
        chat_repo.update(chat_id, last_message_at=datetime.now())
        
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


# ==================== User Feedback on Chat ====================

class ChatFeedbackRequest(BaseModel):
    """User feedback on a chat response (upvote/downvote)."""
    message_content: str = Field(..., description="The response the user is rating")
    query: str = Field("", description="The original query")
    feedback: str = Field(..., description="positive, negative, or neutral")
    note: Optional[str] = Field(None, description="Optional feedback text")

@app.post("/chat/feedback", tags=["Chat"])
async def submit_chat_feedback(request: ChatFeedbackRequest):
    """
    Submit user feedback on a chat response.

    This is the highest-value learning signal -- direct human preference data.
    Feeds into the LLM interaction tracker and pattern learner.
    """
    try:
        from cognitive.llm_interaction_tracker import get_llm_interaction_tracker
        from database.session import SessionLocal

        _fb_session = SessionLocal()
        tracker = get_llm_interaction_tracker(_fb_session)

        tracker.record_interaction(
            prompt=request.query[:2000],
            response=request.message_content[:2000],
            model_used="user_feedback",
            interaction_type="question_answer",
            outcome="success" if request.feedback == "positive" else "failure",
            confidence_score=1.0 if request.feedback == "positive" else 0.0,
            user_feedback=request.feedback,
            user_feedback_text=request.note,
            metadata={"source": "chat_feedback", "feedback_type": request.feedback},
        )
        _fb_session.commit()
        _fb_session.close()

        # Also update distilled knowledge quality
        try:
            from cognitive.knowledge_compiler import get_llm_knowledge_miner
            _fk_session = SessionLocal()
            _fk_miner = get_llm_knowledge_miner(_fk_session)
            _fk_miner.update_quality(
                query=request.query,
                feedback=request.feedback,
            )
            _fk_session.commit()
            _fk_session.close()
        except Exception:
            pass

        # BACKPROPAGATION: Propagate feedback through Grace's weight system
        try:
            from cognitive.grace_weight_system import get_grace_weight_system
            import hashlib
            _ws_session = SessionLocal()
            _ws = get_grace_weight_system(_ws_session)

            outcome = "user_positive" if request.feedback == "positive" else "user_negative"
            query_hash = hashlib.sha256(request.query.strip().lower().encode()).hexdigest()[:16]

            _ws.propagate_outcome(
                outcome=outcome,
                knowledge_ids=[query_hash],
                source_type="llm_generated",
            )
            _ws_session.commit()
            _ws_session.close()
        except Exception:
            pass

        return {"status": "recorded", "feedback": request.feedback}

    except Exception as e:
        logger.error(f"[FEEDBACK] Error recording feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
