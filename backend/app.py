"""
Grace API - FastAPI application for Ollama-based chat and embeddings.
"""

# Windows multiprocessing setup - MUST be first, before any other imports
# This ensures multiprocessing is properly configured for Windows before
# any code that might use it (including uvicorn's reloader)
import sys
if sys.platform == "win32":
    import multiprocessing
    try:
        multiprocessing.set_start_method('spawn', force=True)
    except RuntimeError:
        # Already set, continue
        pass
    multiprocessing.freeze_support()

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import time
import threading
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
from api.third_party_llm_api import router as third_party_llm_router
from api.chat_llm_integration import get_chat_llm_integration, ChatLLMIntegration
from api.ingestion_integration import router as ingestion_integration_router  # Complete autonomous cycle
from api.ml_intelligence_api import router as ml_intelligence_router  # ML Intelligence features
from api.sandbox_lab import router as sandbox_lab_router  # Autonomous experimentation lab
from api.notion import router as notion_router  # Notion task management system
from api.voice_api import router as voice_router  # Voice API - STT/TTS for GRACE
from api.multimodal_api import router as multimodal_router  # Multimodal API - Vision, Voice, Audio, Video with Genesis Keys
from api.agent_api import router as agent_router  # Full Agent Framework - software engineering agent
from api.governance_api import router as governance_router  # Three-Pillar Governance Framework
from api.codebase_api import router as codebase_router  # Codebase Browser - file browsing, search, analysis
from api.knowledge_base_api import router as knowledge_base_router  # Knowledge Base Connectors
from api.kpi_api import router as kpi_router  # KPI Dashboard tracking
from api.proactive_learning import router as proactive_learning_router  # Proactive Learning system
from api.repositories_api import router as repositories_router  # Enterprise Repository Management
from api.telemetry import router as telemetry_router  # System Telemetry and monitoring
from api.monitoring_api import router as monitoring_router  # System Monitoring - organs, health, metrics
from api.streaming import router as streaming_router  # SSE Streaming chat responses
from api.websocket import router as websocket_router  # WebSocket real-time updates
from api.health import router as health_router  # Comprehensive health checks
from api.metrics import router as metrics_router  # Prometheus metrics endpoint
from api.cicd_api import router as cicd_router  # Genesis CI/CD pipelines
from api.cicd_versioning_api import router as cicd_versioning_router  # CI/CD version control
from api.knowledge_base_cicd import router as kb_cicd_router  # Knowledge base CI/CD integration
from api.adaptive_cicd_api import router as adaptive_cicd_router  # Adaptive CI/CD with trust/KPIs
from api.ingestion_api import router as ingestion_router  # Librarian Ingestion Pipeline
from api.autonomous_api import router as autonomous_router  # Autonomous Action Engine
from api.whitelist_api import router as whitelist_router  # Whitelist Learning Pipeline - human input to learning
from api.testing_api import router as test_router  # Autonomous Testing - self-testing with KPI validation
from diagnostic_machine.api import router as diagnostic_router  # 4-Layer Diagnostic Machine
from api.grace_os_api import router as grace_os_router  # Grace OS - Full IDE integration
from api.timesense import router as timesense_router  # TimeSense - Time & Cost Model with physics-based time awareness
from api.enterprise_genesis_api import router as enterprise_genesis_router  # Enterprise Genesis Key Storage
from api.system_specs_api import router as system_specs_router  # System Specifications - hardware constraints for LLMs
from api.enterprise_api import router as enterprise_router  # Enterprise Analytics - All enterprise system analytics
from api.component_testing_api import router as component_testing_router  # Comprehensive Component Testing with Self-Healing
from api.coding_agent_api import router as coding_agent_router  # Enterprise Coding Agent - Same Quality & Standards as Self-Healing
from api.healing_coding_bridge_api import router as healing_coding_bridge_router  # Bidirectional Communication: Self-Healing ↔ Coding Agent
from api.nlp_file_descriptions_api import router as nlp_descriptions_router  # NLP File Descriptions - Makes filesystem no-code friendly
from api.external_knowledge_api import router as external_knowledge_router  # External Knowledge Extraction - GitHub, AI Research, LLMs
from api.benchmark_api import router as benchmark_router  # Benchmark API - HumanEval, BigCodeBench, etc.
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
    status: str = Field(..., description="Health status: 'healthy', 'degraded', or 'unhealthy'")
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
    
    # Create reminder files for external agents
    try:
        from agent_reminder import create_reminder_files
        create_reminder_files()
        print("[OK] System specs reminder files created")
    except Exception as e:
        print(f"[WARN] Could not create reminder files: {e}")
    
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
        
        # CRITICAL: Import outcome_llm_bridge to register SQLAlchemy event listener
        # This ensures the event listener is registered before any LearningExample is created
        try:
            from cognitive.outcome_llm_bridge import get_outcome_bridge
            # Initialize bridge with session to ensure it's ready
            session = next(get_session())
            bridge = get_outcome_bridge(session=session)
            print("[OK] Outcome → LLM Bridge initialized (event listener registered)")
        except Exception as e:
            print(f"[WARN] Could not initialize Outcome → LLM Bridge: {e}")
    except Exception as e:
        print(f"[WARN] Database initialization error: {e}")
        raise
    
    # ==================== Start Self-Healing in Background ====================
    # Initialize self-healing in background so it doesn't block server startup
    def initialize_self_healing_background():
        """Initialize self-healing system in background thread."""
        try:
            import time
            from pathlib import Path
            from database.session import get_db
            from genesis.autonomous_triggers import get_genesis_trigger_pipeline
            from cognitive.autonomous_healing_system import get_autonomous_healing, TrustLevel
            from cognitive.mirror_self_modeling import get_mirror_system
            
            print("\n[AUTONOMOUS-HEALING] Initializing self-healing system (background)...", flush=True)
            
            # Get session for healing system
            session = next(get_db())
            # Try to resolve knowledge_base path (could be in root or backend/)
            knowledge_base_path = Path("knowledge_base")
            if not knowledge_base_path.exists():
                knowledge_base_path = Path("backend/knowledge_base")
            knowledge_base_path = knowledge_base_path.resolve()
            
            # Initialize healing system FIRST
            healing_system = get_autonomous_healing(
                session=session,
                trust_level=TrustLevel.MEDIUM_RISK_AUTO,
                enable_learning=True
            )
            
            # Initialize trigger pipeline (for error-triggered healing)
            trigger_pipeline = get_genesis_trigger_pipeline(
                session=session,
                knowledge_base_path=knowledge_base_path,
                orchestrator=None
            )
            
            # Initialize mirror system
            mirror_system = get_mirror_system(
                session=session,
                observation_window_hours=24,
                min_pattern_occurrences=3
            )
            
            # Initialize Code Analyzer Self-Healing System
            print("[CODE-ANALYZER-HEALING] Initializing code analyzer self-healing...", flush=True)
            try:
                from cognitive.code_analyzer_self_healing import get_code_analyzer_healing
                from cognitive.autonomous_healing_system import TrustLevel
                
                code_analyzer_healing = get_code_analyzer_healing(
                    healing_system=healing_system,
                    trust_level=TrustLevel.MEDIUM_RISK_AUTO,
                    enable_auto_fix=False,  # Pre-flight mode on boot - analysis only
                    enable_timesense=True
                )
                print("[CODE-ANALYZER-HEALING] Code analyzer self-healing initialized", flush=True)
                print("[CODE-ANALYZER-HEALING] Mode: Pre-flight (analysis on boot, fixes require approval)", flush=True)
            except Exception as e:
                print(f"[CODE-ANALYZER-HEALING] Warning: Could not initialize: {e}", flush=True)
            
            # Run initial code analysis in pre-flight mode (check for issues without auto-fixing)
            print("[CODE-ANALYZER-HEALING] Running initial code analysis (pre-flight)...", flush=True)
            try:
                from cognitive.code_analyzer_self_healing import trigger_code_healing
                from cognitive.autonomous_healing_system import TrustLevel
                
                # Run analysis in pre-flight mode (no auto-fix on boot)
                analysis_results = trigger_code_healing(
                    directory='backend',
                    trust_level=TrustLevel.MEDIUM_RISK_AUTO,
                    auto_fix=False,  # Pre-flight mode - analysis only
                    pre_flight=True,
                    enable_timesense=True
                )
                
                issues_found = analysis_results.get('issues_found', 0)
                fixable = analysis_results.get('fixable_issues', 0)
                health_status = analysis_results.get('health_status', 'healthy')
                timesense_enabled = analysis_results.get('timesense_enabled', False)
                
                print(
                    f"[CODE-ANALYZER-HEALING] Initial analysis complete: "
                    f"Issues={issues_found}, Fixable={fixable}, "
                    f"Health={health_status}, Timesense={timesense_enabled}",
                    flush=True
                )
                
                if fixable > 0:
                    print(
                        f"[CODE-ANALYZER-HEALING] Note: {fixable} issues ready for approval. "
                        f"Use /grace/code-healing/apply to review and apply fixes.",
                        flush=True
                    )
            except Exception as e:
                print(f"[CODE-ANALYZER-HEALING] Warning: Initial analysis failed: {e}", flush=True)
            
            # Run initial health check immediately to catch startup issues
            print("[AUTONOMOUS-HEALING] Running initial health check...", flush=True)
            try:
                initial_check = healing_system.run_monitoring_cycle()
                print(
                    f"[AUTONOMOUS-HEALING] Initial check: Status={initial_check['health_status']}, "
                    f"Anomalies={initial_check['anomalies_detected']}, "
                    f"Actions executed={initial_check['actions_executed']}",
                    flush=True
                )
                if initial_check['actions_executed'] > 0:
                    print("[AUTONOMOUS-HEALING] [OK] Startup issues detected and healed!", flush=True)
            except Exception as check_error:
                # Safely handle Unicode in error messages
                error_msg = str(check_error).encode('ascii', 'replace').decode('ascii')
                print(f"[AUTONOMOUS-HEALING] [WARN] Initial health check error: {error_msg}", flush=True)
            
            # Background health monitoring thread (runs every 5 minutes)
            def health_monitor_background():
                """Run health checks every 5 minutes in background."""
                while True:
                    try:
                        time.sleep(300)  # Check every 5 minutes
                        if healing_system:
                            cycle_result = healing_system.run_monitoring_cycle()
                            print(
                                f"[HEALTH] Status: {cycle_result['health_status']}, "
                                f"Anomalies: {cycle_result['anomalies_detected']}, "
                                f"Actions executed: {cycle_result['actions_executed']}",
                                flush=True
                            )
                    except Exception as e:
                        print(f"[HEALTH-MONITOR] Error: {e}", flush=True)
                        time.sleep(60)
            
            # Background mirror analysis thread (runs every 10 minutes)
            def mirror_analysis_background():
                """Run mirror self-modeling every 10 minutes in background."""
                while True:
                    try:
                        time.sleep(600)  # Analyze every 10 minutes
                        if mirror_system:
                            self_model = mirror_system.build_self_model()
                            print(
                                f"[MIRROR] Patterns: {self_model['behavioral_patterns']['total_detected']}, "
                                f"Suggestions: {len(self_model['improvement_suggestions'])}, "
                                f"Self-awareness: {self_model['self_awareness_score']:.2f}",
                                flush=True
                            )
                    except Exception as e:
                        print(f"[MIRROR-ANALYSIS] Error: {e}", flush=True)
                        time.sleep(60)
            
            # Start background threads
            health_thread = threading.Thread(target=health_monitor_background, daemon=True)
            health_thread.start()
            
            mirror_thread = threading.Thread(target=mirror_analysis_background, daemon=True)
            mirror_thread.start()
            
            print("[AUTONOMOUS-HEALING] [OK] Self-healing system active", flush=True)
            print("[AUTONOMOUS-HEALING] Can now fix runtime/startup issues:", flush=True)
            print("  - Connection issues -> CONNECTION_RESET", flush=True)
            print("  - Process errors -> PROCESS_RESTART", flush=True)
            print("  - Service failures -> SERVICE_RESTART", flush=True)
            print("  - Error spikes -> Automatic healing", flush=True)
            print("  - Performance issues -> CACHE_FLUSH / BUFFER_CLEAR", flush=True)
            print("[AUTONOMOUS-HEALING] Trust Level: MEDIUM_RISK_AUTO\n", flush=True)
            
        except Exception as e:
            print(f"[AUTONOMOUS-HEALING] [WARN] Could not start self-healing: {e}", flush=True)
            import traceback
            traceback.print_exc()
    
    # Start self-healing in background (non-blocking)
    healing_thread = threading.Thread(target=initialize_self_healing_background, daemon=True)
    healing_thread.start()
    print("[AUTONOMOUS-HEALING] Self-healing initialization started in background")
    
    # Pre-initialize embedding model in background (non-blocking)
    # This allows server to start accepting connections faster
    def load_embedding_model_background():
        """Load embedding model in background thread."""
        try:
            from embedding import get_embedding_model
            print("\n[STARTUP] Pre-initializing embedding model (background)...")
            embedding_model = get_embedding_model()
            print("[STARTUP] [OK] Embedding model loaded and ready\n")
        except Exception as e:
            print(f"[STARTUP] [INFO] Embedding model not pre-loaded: {e}")
            print("[STARTUP] [INFO] Model will be loaded on first use\n")
    
    embedding_thread = threading.Thread(target=load_embedding_model_background, daemon=True)
    embedding_thread.start()
    print("[STARTUP] Embedding model loading started in background")

    # ==================== Initialize TimeSense Engine ====================
    # Grace's empirical time calibration - gives her a "clock" grounded in physics
    # Also moved to background to speed up server startup
    def initialize_timesense_background():
        """Initialize TimeSense in background thread."""
        try:
            from timesense.engine import get_timesense_engine
            print("\n[TIMESENSE] Initializing Time & Cost Model (background)...")

            timesense_engine = get_timesense_engine(auto_calibrate=True)

            # Run quick calibration at startup
            initialized = timesense_engine.initialize_sync(quick_calibration=True)

            if initialized:
                print("[TIMESENSE] [OK] TimeSense engine ready")
                print(f"[TIMESENSE] Calibrated profiles: {timesense_engine.stats.stable_profiles}")
                print(f"[TIMESENSE] Average confidence: {timesense_engine.stats.average_confidence:.2f}")
                print("[TIMESENSE] Grace now has empirical time awareness:")
                print("  - Disk I/O throughput calibrated")
                print("  - CPU compute benchmarked")
                print("  - Can predict task durations with uncertainty bounds")
                print("[TIMESENSE] Time predictions: p50/p90/p95/p99 latencies available\n")
            else:
                print("[TIMESENSE] [WARN] Engine initialized but calibration incomplete\n")
        except Exception as e:
            print(f"[TIMESENSE] [WARN] Could not initialize TimeSense: {e}")
            import traceback
            traceback.print_exc()
            print("[TIMESENSE] [WARN] Time predictions will use default estimates\n")
    
    timesense_thread = threading.Thread(target=initialize_timesense_background, daemon=True)
    timesense_thread.start()
    print("[TIMESENSE] TimeSense initialization started in background")

    # CRITICAL: Yield FIRST to let server start listening
    # Move non-critical checks to after server is available
    print("[OK] Database initialized, starting server...")
    yield  # ← SERVER STARTS LISTENING HERE
    
    # Non-critical initialization happens AFTER server is running
    # This way server can accept connections even if these fail
    print("\n[STARTUP] Continuing background initialization...")
    
    # Check Ollama (non-blocking check)
    try:
        client = get_ollama_client()
        if client.is_running():
            models = client.get_all_models()
            print(f"[OK] Ollama is running with {len(models)} model(s)")
        else:
            print("[WARN] Ollama is not running - chat endpoint will be unavailable")
    except Exception as e:
        print(f"[WARN] Could not connect to Ollama: {e}")
    
    # Check Qdrant (non-blocking check)
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
    # Initialize ML Intelligence orchestrator (moved after yield - non-critical)
    def init_ml_intelligence():
        try:
            from api.ml_intelligence_api import get_orchestrator
            orchestrator = get_orchestrator()
            print(f"[OK] ML Intelligence initialized with features: {list(orchestrator.enabled_features.keys())}")
        except Exception as e:
            print(f"[WARN] ML Intelligence not available: {e}")
    
    ml_thread = threading.Thread(target=init_ml_intelligence, daemon=True)
    ml_thread.start()

    # ==================== Initialize Auto-Ingestion ====================
    # Start background task for monitoring knowledge base for new files
    import asyncio
    
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
            
            # Do initial scan on startup (defer to avoid blocking server start)
            print("[AUTO-INGEST] Will run initial scan after server starts...", flush=True)
            time.sleep(5)  # Wait for server to be fully up
            
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
            
            if results:
                print(f"[AUTO-INGEST] Initial scan found {len(results)} changes:", flush=True)
                for result in results[:10]:  # Only show first 10 to avoid spam
                    status = "[OK]" if result.success else "[FAIL]"
                    print(f"  {status} {result.change_type}: {result.filepath}", flush=True)
                if len(results) > 10:
                    print(f"  ... and {len(results) - 10} more changes", flush=True)
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
    # Connect sandbox lab to continuous training data (moved after yield - non-critical)
    def init_continuous_learning():
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
    
    continuous_learning_thread = threading.Thread(target=init_continuous_learning, daemon=True)
    continuous_learning_thread.start()

    # ==================== Start Real-Time Stability Monitor ====================
    def init_stability_monitoring():
        """Initialize real-time stability monitoring."""
        try:
            from cognitive.realtime_stability_monitor import start_stability_monitoring
            print("\n[STABILITY-MONITOR] Starting real-time stability proof system...", flush=True)
            start_stability_monitoring(
                check_interval_seconds=60,  # Check every minute
                alert_on_degradation=True
            )
            print("[STABILITY-MONITOR] [OK] Real-time stability monitoring active", flush=True)
            print("[STABILITY-MONITOR] Grace will continuously:", flush=True)
            print("  - Generate deterministic stability proofs every 60 seconds", flush=True)
            print("  - Detect stability degradation automatically", flush=True)
            print("  - Maintain proof history for analysis", flush=True)
            print("  - Provide mathematical verification of system stability", flush=True)
            print("[STABILITY-MONITOR] Access via: GET /health/stability-proof\n", flush=True)
        except Exception as e:
            print(f"[STABILITY-MONITOR] [WARN] Could not start stability monitoring: {e}", flush=True)
            import traceback
            traceback.print_exc()
    
    stability_monitor_thread = threading.Thread(target=init_stability_monitoring, daemon=True)
    stability_monitor_thread.start()

    # Server is ready to accept connections
    print("\n" + "="*60)
    # Start diagnostic engine
    try:
        from diagnostic_machine.diagnostic_engine import start_diagnostic_engine
        print("\n[STARTUP] Starting diagnostic engine...")
        diagnostic_engine = start_diagnostic_engine(
            heartbeat_interval=300,  # 5 minutes
            enable_healing=True,     # Enable automatic healing
            enable_heartbeat=True    # Enable continuous monitoring
        )
        print("[STARTUP] [OK] Diagnostic engine started - running every 5 minutes")
        print("[STARTUP] Diagnostic engine will continuously:")
        print("  - Scan for code issues proactively")
        print("  - Detect bugs, warnings, and errors")
        print("  - Automatically fix issues when possible")
        print("  - Log all actions with Genesis Keys")
        print("[STARTUP] Diagnostic engine heartbeat: 5 minutes")
    except Exception as e:
        print(f"[STARTUP] [WARN] Failed to start diagnostic engine: {e}")
        import traceback
        traceback.print_exc()
    
    # Start autonomous stress test scheduler
    try:
        from autonomous_stress_testing.scheduler import start_stress_test_scheduler
        print("\n[STARTUP] Starting autonomous stress test scheduler...")
        start_stress_test_scheduler(
            interval_minutes=10,
            base_url="http://localhost:8000",
            enable_genesis_logging=True,
            enable_diagnostic_alerts=True
        )
        print("[STARTUP] [OK] Stress test scheduler started - running every 10 minutes")
    except Exception as e:
        print(f"[STARTUP] [WARN] Failed to start stress test scheduler: {e}")
    
    print("[OK] GRACE API STARTUP COMPLETE")
    print("="*60)
    print("Server is ready to accept connections on http://0.0.0.0:8000")
    print("Health check: http://localhost:8000/health/live")
    print("="*60 + "\n")
    
    # Shutdown
    print("\nGrace API shutting down...")
    
    # Stop diagnostic engine
    try:
        from diagnostic_machine.diagnostic_engine import stop_diagnostic_engine
        print("[SHUTDOWN] Stopping diagnostic engine...")
        stop_diagnostic_engine()
        print("[SHUTDOWN] [OK] Diagnostic engine stopped")
    except Exception as e:
        print(f"[SHUTDOWN] [WARN] Failed to stop diagnostic engine: {e}")
    
    # Stop stress test scheduler
    try:
        from autonomous_stress_testing.scheduler import stop_stress_test_scheduler
        print("[SHUTDOWN] Stopping stress test scheduler...")
        stop_stress_test_scheduler()
        print("[SHUTDOWN] [OK] Stress test scheduler stopped")
    except Exception as e:
        print(f"[SHUTDOWN] [WARN] Failed to stop stress test scheduler: {e}")
    
    # Stop stability monitoring
    try:
        from cognitive.realtime_stability_monitor import stop_stability_monitoring
        print("[SHUTDOWN] Stopping stability monitoring...")
        stop_stability_monitoring()
        print("[SHUTDOWN] [OK] Stability monitoring stopped")
    except Exception as e:
        print(f"[SHUTDOWN] [WARN] Failed to stop stability monitoring: {e}")


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
app.include_router(third_party_llm_router)  # Third-Party LLM Integration - automatic handshake for Gemini, OpenAI, Claude, etc.
from api.chat_orchestrator_endpoint import router as chat_orchestrator_router
app.include_router(chat_orchestrator_router)  # Full LLM orchestrator for chats with world model integration
app.include_router(ingestion_integration_router)  # Complete autonomous cycle with self-healing
app.include_router(ml_intelligence_router)  # ML Intelligence - neural trust, bandits, meta-learning
app.include_router(sandbox_lab_router)  # Autonomous Sandbox Lab - self-improvement experiments
from api.self_healing_training_api import router as self_healing_training_router
app.include_router(self_healing_training_router)  # Self-Healing Training System - continuous learning
from api.training_knowledge_api import router as training_knowledge_router
app.include_router(training_knowledge_router)  # Training Knowledge Tracker - what Grace has learned
app.include_router(notion_router)  # Notion Task Management - Kanban board with Genesis Keys
app.include_router(voice_router)  # Voice API - STT/TTS for continuous voice interaction with GRACE
app.include_router(multimodal_router)  # Multimodal API - Vision, Voice, Audio, Video with Genesis Key tracking
app.include_router(agent_router)  # Full Agent Framework - software engineering agent with execution
app.include_router(governance_router)  # Three-Pillar Governance Framework with human-in-the-loop
app.include_router(codebase_router)  # Codebase Browser - file browsing, code search, commit history, analysis
app.include_router(nlp_descriptions_router)  # NLP File Descriptions - makes every file/folder no-code friendly
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
app.include_router(diagnostic_router)  # 4-Layer Diagnostic Machine - sensors, interpreters, judgement, action
app.include_router(grace_os_router)  # Grace OS - Self-healing IDE, Genesis IDE, autonomous actions
app.include_router(timesense_router)  # TimeSense - Time & Cost Model with physics-based time predictions
app.include_router(enterprise_genesis_router)  # Enterprise Genesis Key Storage - Scalable storage for 100k+ keys
app.include_router(system_specs_router)  # System Specifications - hardware constraints for LLMs and external agents
app.include_router(enterprise_router)  # Enterprise Analytics - All enterprise system analytics and health monitoring
app.include_router(component_testing_router)  # Comprehensive Component Testing - Test all components and send bugs to self-healing
app.include_router(coding_agent_router)  # Enterprise Coding Agent - Same Quality & Standards as Self-Healing System
app.include_router(healing_coding_bridge_router)  # Bidirectional Communication: Self-Healing ↔ Coding Agent
app.include_router(external_knowledge_router)  # External Knowledge Extraction - GitHub, AI Research, LLMs
app.include_router(benchmark_router)  # Benchmark API - HumanEval, BigCodeBench, MBPP, etc.

# Add Genesis Key middleware for automatic tracking
app.add_middleware(GenesisKeyMiddleware)


# ==================== Health Check Endpoints ====================

@app.get("/health/live", tags=["Health"])
async def health_live():
    """
    Liveness check endpoint - indicates the process is running.
    
    This is a lightweight check used by the launcher to verify the backend
    process has started and is accepting connections. It does not check
    service health - use /health for that.
    
    Returns:
        dict: Simple status indicating the process is alive
    """
    return {"status": "alive"}


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Optimized health check endpoint with parallel checks and caching.
    
    Returns:
        HealthResponse: Status of the API and Ollama service
        
    Status values:
    - "healthy": All services running
    - "degraded": Backend functional but optional services (Ollama, Qdrant) unavailable
    - "unhealthy": NEVER RETURNED - if this endpoint responds, backend is functional
    """
    # CRITICAL: Backend is ALWAYS functional if this endpoint responds
    # NEVER return "unhealthy" - if we can respond, backend works
    
    try:
        # Use optimized parallel health checker
        from cognitive.optimized_health_checker import get_optimized_health_checker
        
        checker = get_optimized_health_checker(cache_ttl=30)
        service_health = await checker.check_all_services_parallel()
        
        # Extract service statuses
        ollama_status = service_health.get("ollama", {}).get("status", "unknown")
        qdrant_status = service_health.get("qdrant", {}).get("status", "unknown")
        database_status = service_health.get("database", {}).get("status", "unknown")
        
        # Determine overall status
        ollama_running = ollama_status == "healthy"
        
        # Backend is always functional - Ollama is optional
        # Return "healthy" if Ollama is running, "degraded" if not
        # ABSOLUTELY NEVER return "unhealthy" - if this endpoint responds, backend works
        status = "healthy" if ollama_running else "degraded"
        
        # Triple-check: ensure we NEVER return "unhealthy"
        if status == "unhealthy" or status not in ["healthy", "degraded"]:
            status = "degraded"
        
        response = HealthResponse(
            status=status,
            ollama_running=ollama_running,
            models_available=0  # Don't enumerate - too slow
        )
        
        # Final safety check on the response object itself
        if response.status == "unhealthy":
            response.status = "degraded"
        
        return response
        
    except Exception as e:
        # Fallback to simple check if optimized checker fails
        logger.warning(f"[HEALTH] Optimized check failed, using fallback: {e}")
        
        # Simple fallback
        try:
            import requests
            from settings import settings
            ollama_url = getattr(settings, 'OLLAMA_URL', 'http://localhost:11434')
            response = requests.get(ollama_url, timeout=0.5)
            ollama_running = response.status_code == 200
        except Exception:
            ollama_running = False
        
        status = "healthy" if ollama_running else "degraded"
        return HealthResponse(
            status=status,
            ollama_running=ollama_running,
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
        try:
            client = get_ollama_client()
        except Exception as e:
            raise HTTPException(
                status_code=503,
                detail=f"Failed to initialize Ollama client: {str(e)}"
            )
        
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
        # Include context in error message for better debugging
        error_msg = f"Error adding message to chat {chat_id}"
        if hasattr(request, 'role') and hasattr(request, 'content'):
            error_msg += f" (role: {request.role}, content_length: {len(request.content) if request.content else 0})"
        raise HTTPException(
            status_code=500,
            detail=f"{error_msg}: {str(e)}"
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
        
        # TimeSense: Estimate LLM generation time before starting
        time_estimate = None
        try:
            from timesense.integration import TimeEstimator
            if TimeEstimator:
                # Estimate tokens (rough: 4 chars per token)
                prompt_tokens = len(augmented_content.split())
                max_output_tokens = settings.MAX_NUM_PREDICT if settings else 512
                
                llm_estimate = TimeEstimator.estimate_llm_response(
                    prompt_tokens=prompt_tokens,
                    max_output_tokens=max_output_tokens,
                    model_name=chat.model
                )
                
                if llm_estimate:
                    time_estimate = {
                        'estimated_ms': llm_estimate.p50_ms,
                        'estimated_range': f"{llm_estimate.p50_seconds:.1f}-{llm_estimate.p95_seconds:.1f}s",
                        'human_readable': llm_estimate.human_readable(),
                        'confidence': llm_estimate.confidence,
                        'confidence_level': llm_estimate.confidence_level.value
                    }
        except Exception as e:
            # TimeSense not available or error - continue without estimate
            pass
        
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


@app.get("/version", tags=["System"])
async def get_version():
    """
    Version endpoint for launcher handshake.
    
    Returns version information for compatibility checking.
    This endpoint is used by the launcher to verify protocol compatibility.
    
    Returns:
        dict: Version information including backend, embeddings, and protocol versions
    """
    # Get embedding model version if available
    embeddings_version = None
    try:
        from embedding import get_embedding_model
        embedding_model = get_embedding_model()
        if embedding_model and hasattr(embedding_model, 'get_model_info'):
            model_info = embedding_model.get_model_info()
            embeddings_version = model_info.get("version", "1.0.0")
    except Exception:
        # Embeddings not loaded yet, that's ok
        pass
    
    return {
        "version": "1.0.0",  # Backend API version
        "protocol_version": "1.0",  # API protocol version
        "embeddings_version": embeddings_version,  # Embeddings service version
        "name": "Grace API"
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
    import asyncio
    
    # On Windows, handle event loop manually to avoid asyncio conflicts
    # On other platforms, use standard uvicorn.run
    if sys.platform == "win32":
        # Use Config and Server with manual event loop handling
        # Pass app object directly (we're already in this module)
        config = uvicorn.Config(
            app=app,  # Pass app object directly instead of string
            host="0.0.0.0",
            port=8000,
            reload=False,  # Disabled on Windows
            log_level="info"
        )
        server = uvicorn.Server(config)
        
        # Manually handle the event loop to avoid asyncio.run() issues on Windows
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(server.serve())
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()
    else:
        # Standard uvicorn.run on non-Windows platforms
        uvicorn.run(
            "app:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            workers=1
        )
