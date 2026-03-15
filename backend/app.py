"""
Grace API - FastAPI application for Ollama-based chat and embeddings.
"""

from fastapi import FastAPI, HTTPException, Depends, Body, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from api.tab_schemas import (
    TabDocsFullResponse, TabChatFullResponse, TabOracleFullResponse,
    TabLearnHealFullResponse, TabHealthFullResponse, TabBIFullResponse,
)
from typing import List, Optional
import re
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
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
# ==================== MINIMAL IMPORTS Ã¢â‚¬â€ Brain-Centric Architecture ====================
# 1. Brain router Ã¢â‚¬â€ contains ALL 93+ actions across 8 domains
from api.brain_api_v2 import router as brain_router
from api.core.brain_controller import router as brain_v2_router

# 2. Health Ã¢â‚¬â€ required by k8s/load balancers (must be separate route)
from api.health import router as health_router

# 3. Auth Ã¢â‚¬â€ middleware requirement
from api.auth import router as auth_router

# 4. Voice Ã¢â‚¬â€ WebSocket (can't route through sync brain)
from api.voice_api import router as voice_router
from api.stream_api import router as stream_router
from api.completion_api import router as completion_router
from api.runtime_triggers_api import router as runtime_triggers_router
from api.qdrant_api import router as qdrant_router
from api.genesis_daily_api import router as genesis_daily_router
from api.autonomous_loop_api import router as autonomous_loop_router
from api.component_health_api import router as component_health_router
from api.unified_problems_api import router as unified_problems_router
from api.ingest import router as ingest_router
from api.retrieve import router as retrieve_router
from api.learning_memory_api import router as learning_memory_router
from api.introspection_api import router as introspection_router
from api.admin_api import router as admin_router
from api.validation_api import router as validation_router
from api.cognitive_events_api import router as cognitive_events_router
from genesis.middleware import GenesisKeyMiddleware
from vector_db.client import get_qdrant_client
from utils.rag_prompt import build_rag_prompt, build_rag_system_prompt
from search.serpapi_service import SerpAPIService
from api.codebase_hub_api import router as codebase_hub_router
from api.whitelist_hub_api import router as whitelist_hub_router
from api.devlab_api import router as devlab_router
from api.sandbox_api import router as sandbox_router
from api.tasks_hub_api import router as tasks_hub_router
from api.grace_mind_api import router as grace_mind_router

try:
    from settings import settings
except ImportError:
    settings = None


# ==================== Foundation: Settings Safety ====================
# Wrap all settings access to survive settings=None
def _setting(attr: str, default=None):
    """Safe settings access — returns default if settings is None or attr missing."""
    if settings is None:
        return default
    return getattr(settings, attr, default)


# ==================== Foundation: Startup Health Emitter ====================
def _emit_warn(msg: str):
    """Print warning AND emit to event bus so Ops Console sees it."""
    print(f"[WARN] {msg}")
    try:
        from cognitive.event_bus import publish
        publish("system.warning", {"message": msg, "source": "startup", "ts": datetime.now(timezone.utc).isoformat()})
    except Exception:
        pass


def _emit_ok(msg: str):
    """Print OK AND emit to event bus."""
    print(f"[OK] {msg}")
    try:
        from cognitive.event_bus import publish
        publish("system.ok", {"message": msg, "source": "startup", "ts": datetime.now(timezone.utc).isoformat()})
    except Exception:
        pass


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


class ChatDetailResponse(BaseModel):
    """Response model for chat operations (detail view)."""
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
    chats: List[ChatDetailResponse] = Field(..., description="List of chats")
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
        db_type = DatabaseType(_setting('DATABASE_TYPE', 'sqlite'))
        db_config = DatabaseConfig(
            db_type=db_type,
            host=_setting('DATABASE_HOST'),
            port=_setting('DATABASE_PORT'),
            username=_setting('DATABASE_USER'),
            password=_setting('DATABASE_PASSWORD'),
            database=_setting('DATABASE_NAME', 'grace'),
            database_path=_setting('DATABASE_PATH'),
            echo=_setting('DATABASE_ECHO', False),
            sslmode=(_setting('DATABASE_SSLMODE', '') or '').strip() or None,
        )
        DatabaseConnection.initialize(db_config)
        print("[OK] Database connection initialized")
        
        # Initialize session factory
        initialize_session_factory()
        print("[OK] Database session factory initialized")
        
        # Create tables
        create_tables()
        print("[OK] Database tables created/verified")

        # Ã¢â€â‚¬Ã¢â€â‚¬ Auto-migrate: detect and fix schema drift on every startup Ã¢â€â‚¬Ã¢â€â‚¬
        # Grace learns from past errors: if any ORM model has columns the
        # live DB doesn't have yet, they are added automatically here.
        try:
            from database.auto_migrate import run_auto_migrate
            engine = DatabaseConnection.get_engine()
            changes = run_auto_migrate(engine)
            if changes:
                print(f"[OK] Schema auto-migrate: applied {len(changes)} fix(es) -> {changes}")
            else:
                print("[OK] Schema auto-migrate: schema is up to date")
        except Exception as e:
            print(f"[WARN] Schema auto-migrate: {e}")

        # ── Run all pending standalone migration scripts ──
        try:
            from database.startup_migrations import run_pending_migrations
            engine = DatabaseConnection.get_engine()
            applied = run_pending_migrations(engine)
            if applied:
                print(f"[OK] Startup migrations: applied {len(applied)} -> {applied}")
            else:
                print("[OK] Startup migrations: all up to date")
        except Exception as e:
            print(f"[WARN] Startup migrations: {e}")

    except Exception as e:
        _emit_warn(f"Database initialization error: {e}")
        _emit_warn("Grace will continue with limited functionality (DB features may be unavailable). Fix: check backend/.env DATABASE_PATH and run backend/database/migration if needed.")

    # ==================== Lifecycle Cortex — dependency-aware boot ====================
    try:
        from core.lifecycle_cortex import get_lifecycle_cortex, SubsystemSpec, StartPolicy

        cortex = get_lifecycle_cortex()

        # ── Register core subsystems with dependency graph ──
        cortex.register(SubsystemSpec(
            name="event_bus",
            factory=lambda: __import__("cognitive.event_bus", fromlist=["publish"]),
            start_policy=StartPolicy.BLOCKING,
            critical=True,
        ))

        cortex.register(SubsystemSpec(
            name="central_orchestrator",
            factory=lambda: (lambda o: (o.initialize(), o))(__import__("cognitive.central_orchestrator", fromlist=["get_orchestrator"]).get_orchestrator())[1],
            dependencies={"event_bus"},
            start_policy=StartPolicy.BLOCKING,
            critical=True,
        ))

        cortex.register(SubsystemSpec(
            name="error_pipeline",
            factory=lambda: __import__("self_healing.error_pipeline", fromlist=["get_error_pipeline"]).get_error_pipeline(),
            dependencies={"event_bus"},
            start_policy=StartPolicy.BLOCKING,
            critical=False,
        ))

        cortex.register(SubsystemSpec(
            name="ghost_memory",
            factory=lambda: __import__("cognitive.ghost_memory", fromlist=["get_ghost_memory"]).get_ghost_memory(),
            start_policy=StartPolicy.BACKGROUND,
            critical=False,
        ))

        cortex.register(SubsystemSpec(
            name="trust_engine",
            factory=lambda: __import__("cognitive.trust_engine", fromlist=["get_trust_engine"]).get_trust_engine(),
            dependencies={"event_bus"},
            start_policy=StartPolicy.BACKGROUND,
            critical=False,
        ))

        cortex.register(SubsystemSpec(
            name="unified_memory",
            factory=lambda: __import__("cognitive.unified_memory", fromlist=["get_unified_memory"]).get_unified_memory(),
            start_policy=StartPolicy.BACKGROUND,
            critical=False,
        ))

        cortex.register(SubsystemSpec(
            name="consensus_engine",
            factory=lambda: __import__("cognitive.consensus_engine", fromlist=["run_consensus"]),
            dependencies={"event_bus", "trust_engine"},
            start_policy=StartPolicy.BACKGROUND,
            critical=False,
        ))

        # ── Register memory consolidation jobs ──
        def _ghost_to_unified():
            """Consolidate ghost memory reflections into unified memory."""
            try:
                from cognitive.ghost_memory import get_ghost_memory, PLAYBOOK_DIR
                from cognitive.unified_memory import get_unified_memory
                import json
                mem = get_unified_memory()
                if not PLAYBOOK_DIR.exists():
                    return
                for f in sorted(PLAYBOOK_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
                    try:
                        data = json.loads(f.read_text())
                        mem.store_episode({
                            "type": "ghost_reflection",
                            "pattern": data.get("pattern_name", "unknown"),
                            "task": data.get("task", "")[:300],
                            "confidence": data.get("confidence", 0),
                            "source": "ghost_memory_consolidation",
                        })
                    except Exception:
                        pass
            except Exception as e:
                logging.getLogger(__name__).warning(f"[CORTEX-JOB] ghost_to_unified: {e}")

        def _learning_to_mesh():
            """Sync learning examples into the memory mesh."""
            try:
                from cognitive.memory_mesh_integration import MemoryMeshIntegration
                from database import session as db_session
                session_factory = db_session.SessionLocal
                if not session_factory:
                    return
                session = session_factory()
                try:
                    kb_path = Path(__file__).parent / "knowledge_base"
                    mesh = MemoryMeshIntegration(session, kb_path)
                    mesh.sync_learning_folders()
                finally:
                    session.close()
            except Exception as e:
                logging.getLogger(__name__).warning(f"[CORTEX-JOB] learning_to_mesh: {e}")

        cortex.register_job(
            name="ghost_to_unified",
            handler=_ghost_to_unified,
            requires={"unified_memory", "ghost_memory"},
            interval_s=900,  # Every 15 minutes
        )

        cortex.register_job(
            name="learning_to_mesh",
            handler=_learning_to_mesh,
            requires={"unified_memory"},
            interval_s=1800,  # Every 30 minutes
        )

        # ── Boot blocking subsystems ──
        blocking_results = cortex.start_blocking()
        for name, status in blocking_results.items():
            print(f"[CORTEX] {name}: {status}")

        # ── Store cortex on app for shutdown access ──
        app.state.lifecycle_cortex = cortex

        print(f"[OK] Lifecycle Cortex: {len(cortex._subsystems)} subsystems, {len(cortex._jobs)} jobs registered")

    except Exception as e:
        _emit_warn(f"Lifecycle Cortex: {e}")

    # ==================== Lazy Background Init (non-blocking) ====================
    import threading

    def _init_spindle_services():
        """Initialize all Spindle parallel runtime services."""
        _logger = logging.getLogger("spindle_init")
        try:
            # 1. Bridge cognitive event bus to persistent store
            from cognitive.spindle_event_store import get_event_store, bridge_to_event_bus
            store = get_event_store()
            store.start_background_flush()
            bridge_to_event_bus()
            _logger.info("[SPINDLE-INIT] Event store + bridge started")

            # 2. Start CQRS projection background updates
            from cognitive.spindle_projection import get_spindle_projection
            get_spindle_projection(auto_start=True)
            _logger.info("[SPINDLE-INIT] Projection background updates started")

            # 3. Initialize deterministic event bus bridges
            from core.deterministic_event_bus import initialize_bridges
            initialize_bridges()
            _logger.info("[SPINDLE-INIT] Deterministic event bus bridges initialized")

            # 4. Start ZMQ event bridge (inter-process pub/sub for Spindle)
            from cognitive.event_bus import start_zmq_bridge
            start_zmq_bridge()
            _logger.info("[SPINDLE-INIT] ZMQ event bridge started")

            # 5. Pre-warm executor singleton
            from cognitive.spindle_executor import get_spindle_executor
            get_spindle_executor()
            _logger.info("[SPINDLE-INIT] Executor ready")

        except Exception as e:
            _logger.warning(f"[SPINDLE-INIT] Non-fatal init error: {e}")

    def _background_init():
        """Heavy init tasks run in background so server starts fast."""

        # Ã¢â€â‚¬Ã¢â€â‚¬ 0. Start error pipeline FIRST Ã¢â‚¬â€ catches all subsequent errors Ã¢â€â‚¬
        try:
            from self_healing.error_pipeline import get_error_pipeline
            pipe = get_error_pipeline()
            _emit_ok("Self-healing error pipeline started")
        except Exception as e:
            _emit_warn(f"Error pipeline: {e}")

        # ── 0.1 Central Orchestrator — Grace's nervous system ──
        try:
            from cognitive.central_orchestrator import get_orchestrator
            orchestrator = get_orchestrator()
            orchestrator.initialize()
            _emit_ok("Central Orchestrator initialized (event bus subscriptions active)")
        except Exception as e:
            _emit_warn(f"Central Orchestrator: {e}")

        # ── 0.2 Feedback Bridge — decision chain correlation ──
        try:
            from core.feedback_bridge import start_feedback_bridge
            start_feedback_bridge()
            _emit_ok("Feedback bridge started")
        except Exception as e:
            _emit_warn(f"Feedback bridge: {e}")

        # ── Gap 5.2: Ghost Memory reboot replay (restore continuity) ──
        try:
            from cognitive.ghost_memory import get_ghost_memory
            replayed = get_ghost_memory().replay_reboot_deltas()
            if replayed:
                print(f"[OK] Ghost memory: replayed {replayed} reboot deltas for continuity")
        except Exception as e:
            print(f"[WARN] Ghost memory replay: {e}")

        # ── Gap 5.3: ULH Meta-Rule Injector (runtime CTL/LTL constraints) ──
        try:
            from self_healing.ulh_meta_rule_injector import get_meta_rule_injector
            injector = get_meta_rule_injector()
            rules = injector.get_active_rules()
            print(f"[OK] ULH meta-rule injector ready ({len(rules)} active rules)")
        except Exception as e:
            print(f"[WARN] ULH meta-rule injector: {e}")

        # Ã¢â€â‚¬Ã¢â€â‚¬ 0a. Start coding agent worker Ã¢â‚¬â€ processes fix tasks from error pipeline Ã¢â€â‚¬
        try:
            from coding_agent.task_queue import start_worker
            start_worker()
            print("[OK] Coding agent worker started")
        except Exception as e:
            print(f"[WARN] Coding agent worker: {e}")

        # Ã¢â€â‚¬Ã¢â€â‚¬ 0b. Start trigger fabric Ã¢â‚¬â€ multi-source event nervous system Ã¢â€â‚¬Ã¢â€â‚¬
        try:
            from self_healing.trigger_fabric import start as start_fabric
            start_fabric(app=app)
            print("[OK] Multi-trigger fabric started (12 trigger sources)")
        except Exception as e:
            print(f"[WARN] Trigger fabric: {e}")

        # Ã¢â€â‚¬Ã¢â€â‚¬ 0b. Startup health check Ã¢â‚¬â€ validate key tables are queryable Ã¢â€â‚¬Ã¢â€â‚¬
        try:
            from database.session import session_scope
            from sqlalchemy import text
            with session_scope() as session:
                session.execute(text("SELECT COUNT(*) FROM episodes LIMIT 1"))
                session.execute(text("SELECT COUNT(*) FROM genesis_key LIMIT 1"))
            print("[OK] Startup health: core tables queryable")
        except Exception as e:
            print(f"[WARN] Startup health check failed: {e}")

        # Ã¢â€â‚¬Ã¢â€â‚¬ 0c. Autonomous Diagnostics Ã¢â‚¬â€ boot scan then maintenance pulse Ã¢â€â‚¬
        try:
            from cognitive.autonomous_diagnostics import AutonomousDiagnostics
            diag = AutonomousDiagnostics.get_instance()
            # Boot scan (runs on_startup in a background thread Ã¢â‚¬â€ non-blocking)
            import threading
            threading.Thread(
                target=diag.on_startup,
                daemon=True,
                name="grace-boot-diag",
            ).start()
            print("[OK] Autonomous diagnostics boot scan started")
        except Exception as e:
            print(f"[WARN] Autonomous diagnostics: {e}")

        # Ã¢â€â‚¬Ã¢â€â‚¬ 0d. Probe agent Ã¢â‚¬â€ periodic light + deep API sweeps Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬
        try:
            import threading, time

            def _probe_pulse():
                time.sleep(30)   # wait for server fully ready
                while True:
                    try:
                        # Light sweep every 10 minutes (internal, non-blocking)
                        from api.probe_agent_api import _probe_endpoint, _track_probe, _ROUTES, _check_component_vitals
                        sample = list(_ROUTES)[:5]  # quick sample
                        results = [_probe_endpoint(r["path"], r["method"]) for r in sample]
                        _track_probe(results)
                        # Component vitals: throughput, latency, degradation
                        try:
                            _check_component_vitals()
                        except Exception:
                            pass
                        # Feed broken probes into healing swarm
                        broken = [r for r in results if r.get("status") == "broken"]
                        if broken:
                            try:
                                from cognitive.healing_swarm import get_healing_swarm
                                swarm = get_healing_swarm()
                                for b in broken:
                                    swarm.submit({
                                        "component": b.get("path", "unknown"),
                                        "description": f"Probe failed: {b.get('error', '')}",
                                        "error": b.get("error", ""),
                                        "severity": "medium",
                                    })
                            except Exception:
                                pass
                    except Exception:
                        pass
                    time.sleep(600)  # 10 minutes

            threading.Thread(target=_probe_pulse, daemon=True, name="grace-probe-pulse").start()
            print("[OK] Probe agent maintenance pulse started (light every 10min)")
        except Exception as e:
            print(f"[WARN] Probe pulse: {e}")


        try:
            from core.execution_registry import init_registry
            init_registry()
            print("[OK] Execution registry initialized")
        except Exception as e:
            print(f"[WARN] Registry init: {e}")

        try:
            from cognitive.training_ingest import ingest_training_corpus
            result = ingest_training_corpus()
            if result.get("ingested", 0) > 0:
                print(f"[OK] Training corpus: {result['ingested']} files ingested")
        except Exception as e:
            print(f"[WARN] Training ingest: {e}")

        try:
            from cognitive.autonomous_diagnostics import get_diagnostics
            diag = get_diagnostics()
            startup_result = diag.on_startup()
            print(f"[OK] Startup diagnostic: {startup_result.get('status', 'unknown')}")
        except Exception as e:
            print(f"[WARN] Diagnostic: {e}")

        if not _setting('SKIP_EMBEDDING_LOAD', False):
            try:
                from embedding import get_embedding_model
                get_embedding_model()
                print("[OK] Embedding model loaded")
            except Exception as e:
                print(f"[WARN] Embedding: {e}")

        # Warm NLP (voice + intent/entity pipeline) so it's ready at runtime

        try:
            from api.voice_api import voice_manager
            voice_manager.preprocess_text_nlp("hello")
            print("[OK] NLP pipeline ready (voice/intent)")
        except Exception as e:
            print(f"[WARN] NLP warm: {e}")

        # Ã¢â€â‚¬Ã¢â€â‚¬ Phase 3.1: Governance â†' Self-Healing Bridge Ã¢â€â‚¬Ã¢â€â‚¬
        try:
            from cognitive.governance_healing_bridge import get_governance_healing_bridge
            bridge = get_governance_healing_bridge()
            bridge.start()
            print("[OK] Governance healing bridge started (trust < 90 + high confidence â†' auto-heal)")
        except Exception as e:
            print(f"[WARN] Governance healing bridge: {e}")

        # Ã¢â€â‚¬Ã¢â€â‚¬ Phase 3.2: External Knowledge Pull Pipeline Ã¢â€â‚¬Ã¢â€â‚¬
        try:
            from cognitive.external_knowledge_pipeline import get_external_knowledge_pipeline
            ext_pipeline = get_external_knowledge_pipeline()
            ext_pipeline.start()
            print("[OK] External knowledge pipeline started (gap-detect â†' fetch â†' ingest every 30min)")
        except Exception as e:
            print(f"[WARN] External knowledge pipeline: {e}")

        # ── Phase 3.4: Self-Mirroring Telemetry ──
        try:
            from telemetry.self_mirror import get_self_mirror
            mirror = get_self_mirror()
            mirror.start()
            print("[OK] Self-mirroring telemetry started (CPU/memory/latency/governance every 60s)")
        except Exception as e:
            print(f"[WARN] Self-mirroring telemetry: {e}")

        # ── Phase 4: SWE → Spindle Bridge ──
        try:
            from cognitive.swe_spindle_bridge import get_swe_spindle_bridge
            swe_bridge = get_swe_spindle_bridge()
            swe_bridge.start()
            print("[OK] SWE->Spindle bridge started (LearningExample -> Braille -> deterministic paths)")
        except Exception as e:
            print(f"[WARN] SWE->Spindle bridge: {e}")

        # ── Proactive Healing (background loop) ──
        if not _setting('DISABLE_PROACTIVE_HEALING', False):
            try:
                from cognitive.proactive_healing_engine import start_proactive_healing
                start_proactive_healing()
                print("[OK] Proactive healing started (background health monitor)")
            except Exception as e:
                print(f"[WARN] Proactive healing: {e}")
        else:
            print("[SKIP] Proactive healing disabled (DISABLE_PROACTIVE_HEALING=true)")

        # ── Intelligent CICD orchestrator (warm singleton for webhook/API use) ──
        try:
            from genesis.intelligent_cicd_orchestrator import get_intelligent_cicd_orchestrator
            get_intelligent_cicd_orchestrator()
            print("[OK] Intelligent CICD orchestrator ready (ML-assisted test selection, webhooks)")
        except Exception as e:
            print(f"[WARN] Intelligent CICD: {e}")

        # ── Governance Projection (operational → domain folders) ──
        try:
            from services.governance_projection import get_governance_projection
            gov_projection = get_governance_projection()
            gov_projection.start()
            print("[OK] Governance projection service started (event bus -> .grace/ folders)")
        except Exception as e:
            print(f"[WARN] Governance projection: {e}")

        # ── Memory Mesh reconciliation (periodic sync) ──
        try:
            from cognitive.memory_reconciler import MemoryReconciler
            import threading as _mesh_threading

            def _mesh_reconcile_loop():
                import time as _t
                _t.sleep(120)
                reconciler = MemoryReconciler.get_instance()
                while True:
                    try:
                        result = reconciler.reconcile()
                        if result.get("changes", 0) > 0:
                            logger.info(f"[MESH-SYNC] Reconciled {result['changes']} entries")
                    except Exception as _e:
                        logger.warning(f"[MESH-SYNC] Reconciliation error: {_e}")
                    _t.sleep(1800)

            _mesh_threading.Thread(target=_mesh_reconcile_loop, daemon=True, name="grace-mesh-sync").start()
            print("[OK] Memory mesh reconciliation cron started (every 30min)")
        except Exception as e:
            print(f"[WARN] Memory mesh reconciliation: {e}")

        # ── Gap 5.4: Consensus → RL Reward Bridge (closes reinforcement loop) ──
        try:
            from ml_intelligence.consensus_reward_bridge import get_consensus_reward_bridge
            get_consensus_reward_bridge().start()
            print("[OK] Consensus→RL reward bridge started (online weight updates)")
        except Exception as e:
            print(f"[WARN] Consensus reward bridge: {e}")

        # ── Gap 5.6: Executive Watchdog (SAFE_MODE failover) ──
        try:
            from cognitive.exec_watchdog import get_exec_watchdog
            watchdog = get_exec_watchdog()
            watchdog.start()
            print("[OK] Executive watchdog started (SAFE_MODE failover on hang)")
        except Exception as e:
            print(f"[WARN] Executive watchdog: {e}")

        # ── Watchdog auto-heartbeat (proves event loop is responsive) ──
        def _watchdog_heartbeat():
            import urllib.request
            while True:
                try:
                    time.sleep(60)
                    r = urllib.request.urlopen("http://localhost:8000/kpi/health", timeout=5)
                    if r.status == 200:
                        watchdog.heartbeat()
                except Exception:
                    pass  # If health check fails, no heartbeat → watchdog triggers correctly
        try:
            threading.Thread(target=_watchdog_heartbeat, daemon=True, name="grace-watchdog-hb").start()
        except Exception:
            pass

        # ── Spindle parallel runtime services ──
        _init_spindle_services()

    threading.Thread(target=_background_init, daemon=True, name="grace-init").start()
    print("[OK] Background init started (training, diagnostics, embedding)")

    # Start cortex background subsystems + job scheduler after background init thread
    try:
        cortex = app.state.lifecycle_cortex
        cortex.start_background()
        print("[OK] Lifecycle Cortex: background subsystems + job scheduler started")
    except Exception as e:
        print(f"[WARN] Cortex background start: {e}")

    # Optional: auto hot-reload when .py files are saved (HOT_RELOAD_WATCH=1)
    try:
        from core.hot_reload import start_reload_watcher
        start_reload_watcher()
    except Exception:
        pass

    # Check LLM Provider
    if not _setting('SKIP_LLM_CHECK', False):
        try:
            client = get_llm_client()
            provider_name = _setting('LLM_PROVIDER', 'ollama').upper()
            if client.is_running():
                _emit_ok(f"{provider_name} is running and reachable")
            else:
                _emit_warn(f"{provider_name} is not responding - chat features may be limited")
        except Exception as e:
            provider = _setting('LLM_PROVIDER', 'LLM')
            _emit_warn(f"Could not connect to LLM provider ({provider}): {e}")
    else:
        print("[SKIP] LLM check skipped")
    
    # Check Qdrant
    if not _setting('SKIP_QDRANT_CHECK', False):
        qdrant_target = _setting('QDRANT_URL', '') or f"{_setting('QDRANT_HOST', 'localhost')}:{_setting('QDRANT_PORT', 6333)}"
        try:
            qdrant = get_qdrant_client()
            if qdrant.is_connected():
                collections = qdrant.list_collections()
                print(f"[OK] Qdrant ({qdrant_target}) is running with {len(collections)} collection(s)")
            else:
                print(f"[WARN] Qdrant ({qdrant_target}) is not running - document ingestion will be unavailable")
        except Exception as e:
            print(f"[WARN] Could not connect to Qdrant ({qdrant_target}): {e}")
    else:
        print("[SKIP] Qdrant check skipped (SKIP_QDRANT_CHECK=true)")

    # ==================== Initialize File Watcher ====================
    # Start file system watcher for automatic version control
    if not _setting('DISABLE_GENESIS_TRACKING', False):
        try:
            from genesis.file_watcher import start_watching_workspace
            import threading

            def run_file_watcher():
                """Run file watcher in background thread"""
                try:
                    logger.info("[FILE-WATCHER] Starting file system monitoring...")
                    start_watching_workspace()
                except Exception as e:
                    logger.exception(f"[FILE-WATCHER] Crashed: {e}")
                    print(f"[FILE-WATCHER] [WARN] Error: {e}")

            watcher_thread = threading.Thread(target=run_file_watcher, daemon=True, name="grace-file-watcher")
            watcher_thread.start()
            print("[OK] File watcher started - automatic version tracking enabled")
        except Exception as e:
            logger.exception(f"[FILE-WATCHER] Failed to initialize: {e}")
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
                        if _setting('SUPPRESS_INGESTION_ERRORS', True):
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
                if _setting('SUPPRESS_INGESTION_ERRORS', True):
                    print(f"[AUTO-INGEST] [WARN] Error in continuous monitoring (suppressed): {e}", flush=True)
                else:
                    raise
        except Exception as e:
            print(f"[AUTO-INGEST] [FAIL] Error in auto-ingestion: {e}", flush=True)
            import traceback
            traceback.print_exc()
    
    # Start auto-ingestion in a daemon thread
    if not _setting('SKIP_AUTO_INGESTION', False):
        try:
            auto_ingest_thread = threading.Thread(target=run_auto_ingestion, daemon=True)
            auto_ingest_thread.start()
        except Exception as e:
            print(f"[AUTO-INGEST] [FAIL] Failed to start auto-ingestion: {e}")
    else:
        print("[SKIP] Auto-ingestion disabled (SKIP_AUTO_INGESTION=true)")


    # ==================== Start Continuous Learning Orchestrator ====================
    if not _setting('DISABLE_CONTINUOUS_LEARNING', False):
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
    _diag_session = None
    try:
        from diagnostic_machine.diagnostic_engine import get_diagnostic_engine
        # Use module-level SessionLocal/initialize_session_factory (do not re-import here or lifespan sees a local and fails at first use)
        if SessionLocal is None:
            initialize_session_factory()
        from database import session as db_session
        session_factory = db_session.SessionLocal
        _diag_session = session_factory() if session_factory else None
        _kb_path = str(Path(__file__).parent / "knowledge_base")
        _diag_engine = get_diagnostic_engine(session=_diag_session, kb_path=_kb_path)
        started = _diag_engine.start()
        if started:
            print("[OK] Diagnostic engine started Ã¢â‚¬â€ self-healing active (60s heartbeat)")
        else:
            print("[WARN] Diagnostic engine already running")
    except Exception as e:
        print(f"[WARN] Diagnostic engine not started: {e}")

    # ==================== Start Autonomous Loop ====================
    try:
        from api.autonomous_loop_api import _background_loop, _stop_event, _loop_state, _run_cycle
        import threading
        _stop_event.clear()
        _loop_state["running"] = True
        # Run first cycle in background (5s delay) so uvicorn can bind the port first
        def _delayed_start_loop():
            import time as _time
            _time.sleep(5)  # Let uvicorn bind and start serving first
            try:
                _run_cycle()
            except Exception as _e:
                print(f"[WARN] Autonomous first cycle: {_e}")
            _background_loop(30)
        _auto_thread = threading.Thread(target=_delayed_start_loop, daemon=True, name="grace-autonomous")
        _auto_thread.start()
        print("[OK] Autonomous loop started (first cycle in 5s, then 30s: heal->learn->verify->composite)")
    except Exception as e:
        print(f"[WARN] Autonomous loop not started: {e}")

    # ==================== Start Meta Loop Orchestrator ====================
    try:
        from cognitive.meta_loop_orchestrator import start_meta_loop
        start_meta_loop()
        print("[OK] Meta loop coordinator started (60s heartbeat, system_maintenance every 3 cycles)")
    except Exception as e:
        print(f"[WARN] Meta loop not started: {e}")

    # ==================== Start Spindle Daemon (autonomous, always-on) ====================
    _spindle_proc = None
    if not _setting('DISABLE_SPINDLE_DAEMON', False):
        try:
            import subprocess
            backend_dir = str(Path(__file__).parent)
            _spindle_proc = subprocess.Popen(
                [sys.executable, "spindle_daemon.py"],
                cwd=backend_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )
            app.state.spindle_daemon_process = _spindle_proc
            from cognitive.event_bus import ZMQ_PUB_ENDPOINT
            print(f"[OK] Spindle daemon started (autonomous, {ZMQ_PUB_ENDPOINT})")
        except Exception as e:
            print(f"[WARN] Spindle daemon not started: {e}")
            app.state.spindle_daemon_process = None
    else:
        app.state.spindle_daemon_process = None
        print("[SKIP] Spindle daemon disabled (DISABLE_SPINDLE_DAEMON=true)")

    # ==================== Start Autonomous CICD Engine ====================
    try:
        from genesis.autonomous_cicd_engine import start_autonomous_cicd
        await start_autonomous_cicd()
        print("[OK] Autonomous CICD engine started (file-change -> auto tests, high-risk -> manual)")
    except Exception as e:
        print(f"[WARN] Autonomous CICD engine not started: {e}")

    # ==================== Register Auto-Probe ====================
    try:
        from core.tracing import register_auto_probe
        register_auto_probe()
        print("[OK] Auto-probe registered (triggers on code changes)")
    except Exception as e:
        print(f"[WARN] Auto-probe: {e}")

    # ==================== Startup Component Tracker ====================
    _startup_components = {}

    def _start_component(name: str, fn, *args, **kwargs):
        """Start an optional component with status tracking and visible logging."""
        try:
            result = fn(*args, **kwargs)
            _startup_components[name] = {"ok": True}
            print(f"[OK] {name} started")
            return result
        except Exception as e:
            _startup_components[name] = {"ok": False, "error": str(e)[:200]}
            logger.exception(f"[STARTUP] {name} failed: {e}")
            print(f"[WARN] {name} not started: {e}")
            return None

    # ==================== Start Grace Systems Integration ====================
    def _init_systems_integration():
        from services.grace_systems_integration import GraceSystemsIntegration
        hub = GraceSystemsIntegration()
        app.state.systems_integration = hub
        return hub
    _start_component("GraceSystemsIntegration", _init_systems_integration)

    # ==================== Start Grace Autonomous Engine ====================
    def _init_autonomous_engine():
        from services.grace_autonomous_engine import GraceAutonomousEngine
        engine = GraceAutonomousEngine()
        engine.start()
        app.state.autonomous_engine = engine
        return engine
    _start_component("GraceAutonomousEngine", _init_autonomous_engine)

    # ==================== Start Grace Team Management ====================
    def _init_team_management():
        from services.grace_team_management import get_team_management
        team_mgmt = get_team_management()
        app.state.team_management = team_mgmt
        return team_mgmt
    _start_component("GraceTeamManagement", _init_team_management)

    # ==================== Start Governance Healing Bridge ====================
    def _init_gov_healing_bridge():
        from cognitive.governance_healing_bridge import get_governance_healing_bridge
        bridge = get_governance_healing_bridge()
        bridge.start()
        return bridge
    _start_component("GovernanceHealingBridge", _init_gov_healing_bridge)

    # ==================== Runtime Management State ====================
    app.state.runtime_paused = False
    app.state.diagnostic_engine = _diag_engine
    app.state._diag_session = _diag_session
    app.state._start_time = time.time()
    app.state.startup_components = _startup_components

    # ==================== Startup Summary ====================
    ok_count = sum(1 for v in _startup_components.values() if v.get("ok"))
    fail_count = sum(1 for v in _startup_components.values() if not v.get("ok"))
    failed_names = [k for k, v in _startup_components.items() if not v.get("ok")]
    print(f"\n{'='*60}")
    print(f"  Grace Startup Summary: {ok_count} OK, {fail_count} degraded")
    if failed_names:
        print(f"  Degraded: {', '.join(failed_names)}")
    print(f"{'='*60}\n")

    yield

    # ==================== Shutdown Ã¢â‚¬â€ clean up background systems ====================
    print("Grace API shutting down...")

    # Lifecycle Cortex graceful shutdown (reverse dependency order)
    try:
        if hasattr(app.state, 'lifecycle_cortex'):
            app.state.lifecycle_cortex.shutdown()
            print("[OK] Lifecycle Cortex shutdown complete")
    except Exception as e:
        print(f"[WARN] Cortex shutdown: {e}")

    try:
        from api.autonomous_loop_api import _stop_event
        _stop_event.set()
        print("[OK] Autonomous loop stop signaled")
    except Exception:
        pass

    try:
        from cognitive.meta_loop_orchestrator import stop_meta_loop
        stop_meta_loop()
        print("[OK] Meta loop coordinator stopped")
    except Exception:
        pass

    try:
        from genesis.autonomous_cicd_engine import stop_autonomous_cicd
        await stop_autonomous_cicd()
        print("[OK] Autonomous CICD engine stopped")
    except Exception:
        pass

    if not getattr(settings, "DISABLE_CONTINUOUS_LEARNING", False):
        try:
            from cognitive.continuous_learning_orchestrator import stop_continuous_learning
            stop_continuous_learning()
            print("[OK] Continuous learning stopped")
        except Exception:
            pass

    if not getattr(settings, "DISABLE_GENESIS_TRACKING", False):
        try:
            from genesis.file_watcher import get_file_watcher_service
            get_file_watcher_service().stop_all()
            print("[OK] File watcher stopped")
        except Exception:
            pass

    try:
        from core.hot_reload import stop_reload_watcher
        stop_reload_watcher()
        print("[OK] Hot-reload watcher stopped")
    except Exception:
        pass

    if _diag_engine:
        try:
            _diag_engine.stop()
            print("[OK] Diagnostic engine stopped")
        except Exception:
            pass
    if getattr(app.state, "_diag_session", None) is not None:
        try:
            app.state._diag_session.close()
            print("[OK] Diagnostic engine session closed")
        except Exception:
            pass
    # Governance healing bridge shutdown
    try:
        from cognitive.governance_healing_bridge import get_governance_healing_bridge
        get_governance_healing_bridge().stop()
        print("[OK] Governance healing bridge stopped")
    except Exception:
        pass

    # External knowledge pipeline shutdown
    try:
        from cognitive.external_knowledge_pipeline import get_external_knowledge_pipeline
        get_external_knowledge_pipeline().stop()
        print("[OK] External knowledge pipeline stopped")
    except Exception:
        pass

    # Self-mirroring telemetry shutdown
    try:
        from telemetry.self_mirror import get_self_mirror
        get_self_mirror().stop()
        print("[OK] Self-mirroring telemetry stopped")
    except Exception:
        pass

    # Spindle daemon shutdown
    _proc = getattr(app.state, "spindle_daemon_process", None)
    if _proc is not None and _proc.poll() is None:
        try:
            _proc.terminate()
            _proc.wait(timeout=5)
            print("[OK] Spindle daemon stopped")
        except Exception:
            try:
                _proc.kill()
            except Exception:
                pass

    # SWE->Spindle bridge shutdown
    try:
        from cognitive.swe_spindle_bridge import get_swe_spindle_bridge
        get_swe_spindle_bridge().stop()
        print("[OK] SWE->Spindle bridge stopped")
    except Exception:
        pass

    # Proactive healing shutdown
    if not getattr(settings, "DISABLE_PROACTIVE_HEALING", False):
        try:
            from cognitive.proactive_healing_engine import stop_proactive_healing
            stop_proactive_healing()
            print("[OK] Proactive healing stopped")
        except Exception:
            pass

    # ── Spindle shutdown ──
    try:
        from cognitive.spindle_event_store import get_event_store
        get_event_store().stop_background_flush()
        from cognitive.spindle_projection import get_spindle_projection
        get_spindle_projection(auto_start=False).stop_background_update()
        print("[OK] Spindle services stopped")
    except Exception:
        pass

    try:
        DatabaseConnection.close()
        print("[OK] Database connection closed")
    except Exception:
        pass


# ==================== FastAPI App ====================

# Start internal bus bridging (cognitive ↔ layer1) so components can interoperate.
try:
    from infrastructure.bus_bridge import start_bus_bridge

    start_bus_bridge()
except Exception:
    # Best-effort only; never block app startup.
    pass

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

@app.middleware("http")
async def connection_cleanup_middleware(request, call_next):
    response = await call_next(request)
    # Force connection close on API responses to prevent CLOSE_WAIT buildup
    # WebSocket upgrades are excluded automatically (they don't hit http middleware)
    if "upgrade" not in (request.headers.get("connection", "").lower()):
        response.headers["Connection"] = "close"
    return response


# ==================== FIX 1: Global Exception Handler ====================
# Catches ALL unhandled exceptions across 525 endpoints.
# Prevents raw 500s, logs errors, emits to event bus for Ops Console visibility.
from fastapi.responses import JSONResponse
from starlette.requests import Request
import traceback as _tb

@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions. Logs, emits, returns clean JSON."""
    path = request.url.path
    method = request.method
    err_msg = str(exc)[:500]
    tb_str = ''.join(_tb.format_exception(type(exc), exc, exc.__traceback__))[-1000:]
    
    logger.error(f"Unhandled {method} {path}: {err_msg}\n{tb_str}")
    
    # Emit to event bus → visible in Ops Console Tail Logs + Live Feed
    try:
        from cognitive.event_bus import publish
        publish("system.error", {
            "path": path,
            "method": method,
            "error": err_msg,
            "traceback": tb_str[-500:],
            "ts": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass
    
    # Track as Genesis key for self-healing
    try:
        from api._genesis_tracker import track
        track(
            key_type="error",
            what=f"Unhandled API error: {method} {path} → {err_msg[:100]}",
            who="global_exception_handler",
            is_error=True,
            error_type=type(exc).__name__,
            error_message=err_msg[:300],
            tags=["api", "unhandled", "500"],
        )
    except Exception:
        pass
    
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": err_msg[:200],
            "type": type(exc).__name__,
            "path": path,
        }
    )

# =============================================================================
# API ROUTERS Ã¢â‚¬â€ v1 resource layer + minimal core
# =============================================================================

# Core: needed by app.py's own chat/RAG endpoints
# =============================================================================
# BRAIN-CENTRIC ARCHITECTURE Ã¢â‚¬â€ 4 routers only
# =============================================================================

# THE BRAIN Ã¢â‚¬â€ 95+ actions, 9 domains (chat, files, govern, ai, system, data, tasks, code, deterministic)
app.include_router(brain_router)                 # /brain/{domain}
app.include_router(brain_v2_router)              # /api/v2/{domain}/{action}

# Infrastructure (can't live inside brain)
app.include_router(health_router)                # /health (k8s probes)
app.include_router(auth_router)                  # /auth (middleware)
app.include_router(voice_router)                 # /voice (WebSocket)
app.include_router(stream_router)                # /api/stream (SSE streaming)
app.include_router(completion_router)            # /api/complete (inline code completion)
app.include_router(runtime_triggers_router)        # /api/triggers (scan, scan-and-heal, log)
app.include_router(qdrant_router)                  # /api/qdrant/status (simple Qdrant check)
app.include_router(genesis_daily_router)            # /api/genesis-daily/* (Governance tab Genesis Keys)
app.include_router(autonomous_loop_router)           # /api/autonomous/* (loop status, start/stop; used by loop for mirror-feed)
app.include_router(component_health_router)         # /api/component-health/* (mirror-feed for autonomous loop + health UI)
app.include_router(unified_problems_router)              # /api/problems/* (unified single-source-of-truth problems)
app.include_router(ingest_router)                    # /ingest/* (document ingestion; frontend + docs)
app.include_router(retrieve_router)                  # /retrieve/* (RAG search; frontend FoldersTab, SearchInternetButton)
app.include_router(learning_memory_router)           # /api/learning-memory/* (neighbour search, fill gaps, expand)
app.include_router(admin_router)                     # /api/admin/* (registry, state, reload-config, trigger-diagnostics; requires ADMIN_TOKEN)
app.include_router(validation_router)                # /api/validation/* (trust scores, KPIs, verification history Ã¢â‚¬â€ frontend dashboard)
app.include_router(cognitive_events_router)          # /api/cognitive-events/* (WebSocket stream of self-healing logs)
app.include_router(introspection_router)             # /api/system/* (System Introspection & Validation)

from api.layer1_api import router as layer1_router
app.include_router(layer1_router)

from api.cognitive_api import router as cognitive_router
app.include_router(cognitive_router)

from api.codebase_api import router as codebase_router
app.include_router(codebase_router)

from api.genesis_api import router as genesis_router
app.include_router(genesis_router)

from api.governance_api import router as governance_router
app.include_router(governance_router)

from api.librarian_api import router as librarian_router
app.include_router(librarian_router)

from api.ml_intelligence_api import router as ml_intelligence_router, intelligence_router as doc_intelligence_router
app.include_router(ml_intelligence_router)
app.include_router(doc_intelligence_router)

from api.monitoring_api import router as monitoring_router
app.include_router(monitoring_router)

from api.codebase_hub_api import router as codebase_hub_router
app.include_router(codebase_hub_router, prefix="/api")

@app.get("/api/cicd/genesis-keys")
async def cicd_genesis_keys():
    return {"status": "ok", "keys": []}

from api.tasks_hub_api import router as tasks_hub_router
from api.schema_evolution_api import router as schema_evolution_router
from api.oracle_api import router as oracle_router
from api.learn_heal_api import router as learn_heal_router
from api.system_health_api import router as system_health_router, immune_router, diagnostic_router, proactive_router
from api.system_audit_api import router as system_audit_router
from api.bi_api import router as bi_router
from api.kpi_api import router as kpi_router
from api.planner_api import router as planner_router
from api.scrape_api import router as scrape_router
from api.version_control_api import router as version_control_router
from api.hitl_dashboard import router as hitl_dashboard_router
from api.consensus_fixer_api import router as consensus_fixer_router
from api.agent_api import router as agent_router
from api.governance_healing_api import router as governance_healing_router
from api.external_knowledge_api import router as external_knowledge_router

app.include_router(codebase_hub_router, prefix="/api")
app.include_router(whitelist_hub_router, prefix="/api")
app.include_router(devlab_router, prefix="/api")
app.include_router(sandbox_router, prefix="/api")
app.include_router(tasks_hub_router, prefix="/api")
app.include_router(grace_mind_router, prefix="/api")
app.include_router(schema_evolution_router, prefix="/api")
app.include_router(oracle_router)
app.include_router(learn_heal_router)
app.include_router(system_health_router)
app.include_router(system_audit_router)
app.include_router(immune_router)
app.include_router(diagnostic_router)
app.include_router(proactive_router)
app.include_router(bi_router)
app.include_router(kpi_router)
app.include_router(planner_router)
app.include_router(scrape_router)
app.include_router(version_control_router)
app.include_router(hitl_dashboard_router)
app.include_router(consensus_fixer_router)
app.include_router(agent_router, prefix="/api/agents")
app.include_router(governance_healing_router)
app.include_router(external_knowledge_router)

from api.swe_spindle_api import router as swe_spindle_router
app.include_router(swe_spindle_router)

from api.intelligent_cicd_api import router as intelligent_cicd_router
app.include_router(intelligent_cicd_router)

from api.sandbox_repair_api import router as sandbox_repair_router
app.include_router(sandbox_repair_router)

from api.self_mirror_api import router as self_mirror_router
app.include_router(self_mirror_router)

from api.orchestrator_ws_api import router as orchestrator_ws_router
app.include_router(orchestrator_ws_router)

from api.cortex_api import router as cortex_router
app.include_router(cortex_router)

from api.docs_library_api import router as docs_library_router
app.include_router(docs_library_router)

from api.librarian_fs_api import router as librarian_fs_router
app.include_router(librarian_fs_router)

try:
    from api.federated_api import router as federated_router
    app.include_router(federated_router)              # /api/federated/* (federated learning)
except Exception as _e:
    print(f"[WARN] Federated API router not loaded: {_e}")

from api.chunked_upload_api import router as chunked_upload_router
app.include_router(chunked_upload_router)

# ── Orphan wiring: previously defined but never mounted ──
from api.ask_grace_api import router as ask_grace_router
app.include_router(ask_grace_router)                 # /api/ask-grace (natural language query)

from api.vscode_extension_api import router as vscode_extension_router
app.include_router(vscode_extension_router)          # /api/* (VSCode extension shim)

from api.connection_api import router as connection_router
app.include_router(connection_router)                # /api/connections (connection validation)

from api.workspace_api import router as workspace_router
app.include_router(workspace_router)                 # /api/workspaces (workspace management)

from api.world_model_api import router as world_model_router
app.include_router(world_model_router)               # /api/world-model (world model queries)

from api.live_console_api import router as live_console_router
app.include_router(live_console_router)              # /api/console (live console)

from api.probe_agent_api import router as probe_agent_router
app.include_router(probe_agent_router)                    # /api/probe/* (sweep, sweep-and-heal, endpoint)

from api.spindle_dashboard_api import router as spindle_dashboard_router
app.include_router(spindle_dashboard_router)              # /api/spindle/* (dashboard, events, gate, WS)

# Spindle Formal Verification & Autonomous Execution
try:
    from api.spindle_api import router as spindle_router
    app.include_router(spindle_router)
except Exception as _e:
    print(f"[WARN] Spindle API router not loaded: {_e}")

# DevLab VVT (Validation, Verification, Test)
try:
    from api.test_verify_api import router as test_verify_router
    app.include_router(test_verify_router)               # /api/test-verify/* (smoke, pytest, stress, deterministic pipeline)
except Exception as _e:
    print(f"[WARN] Test-Verify API router not loaded: {_e}")

# Testing & Quality (unified test execution, scheduling, chaos engineering)
try:
    from api.testing_api import router as testing_router
    app.include_router(testing_router)
    print("[ROUTER] ✓ Testing & Quality API")
except Exception as _e:
    print(f"[WARN] Testing API router not loaded: {_e}")

# Healing Swarm (concurrent multi-agent self-healing)
try:
    from api.healing_swarm_api import router as swarm_router
    app.include_router(swarm_router)
    print("[ROUTER] ✓ Healing Swarm API")
except Exception as _e:
    print(f"[WARN] Healing Swarm API router not loaded: {_e}")

# System Introspection & Deterministic Validation
try:
    from api.introspection_api import router as introspection_router
    app.include_router(introspection_router)
except Exception as _e:
    print(f"[WARN] Introspection API router not loaded: {_e}")

# Add Genesis Key middleware for automatic tracking (if not disabled)
if not (settings and settings.DISABLE_GENESIS_TRACKING):
    app.add_middleware(GenesisKeyMiddleware)
    print("[GENESIS] Genesis Key tracking enabled")
else:
    print("[GENESIS] Genesis Key tracking disabled (DISABLE_GENESIS_TRACKING=true)")


# ==================== Startup Status Endpoint ====================
@app.get("/api/startup-status", tags=["System"])
async def startup_status():
    """Returns the status of all optional startup components."""
    components = getattr(app.state, "startup_components", {})
    ok = sum(1 for v in components.values() if v.get("ok"))
    degraded = sum(1 for v in components.values() if not v.get("ok"))
    return {
        "ok_count": ok,
        "degraded_count": degraded,
        "components": components,
        "uptime_seconds": round(time.time() - getattr(app.state, "_start_time", time.time()), 1),
    }

# ==================== Tab Aggregation Endpoints ====================
# Frontend tabs call /api/tabs/{tab}/full for aggregated data on mount.

@app.get("/api/tabs/docs/full", tags=["Tab Aggregation"], response_model=TabDocsFullResponse)
async def tabs_docs_full():
    """Aggregated data for the Docs tab."""
    return TabDocsFullResponse()

@app.get("/api/tabs/chat/full", tags=["Tab Aggregation"], response_model=TabChatFullResponse)
async def tabs_chat_full():
    """Aggregated data for the Chat tab."""
    return TabChatFullResponse()

@app.get("/api/tabs/oracle/full", tags=["Tab Aggregation"], response_model=TabOracleFullResponse)
async def tabs_oracle_full():
    """Aggregated data for the Oracle tab."""
    return TabOracleFullResponse()

@app.get("/api/tabs/learn-heal/full", tags=["Tab Aggregation"], response_model=TabLearnHealFullResponse)
async def tabs_learn_heal_full():
    """Aggregated data for the Learning & Healing tab."""
    return TabLearnHealFullResponse()

@app.get("/api/tabs/health/full", tags=["Tab Aggregation"], response_model=TabHealthFullResponse)
async def tabs_health_full():
    """Aggregated data for the System Health tab."""
    return TabHealthFullResponse()

@app.get("/api/tabs/bi/full", tags=["Tab Aggregation"], response_model=TabBIFullResponse)
async def tabs_bi_full():
    """Aggregated data for the Business Intelligence tab."""
    return TabBIFullResponse()


# ==================== Ingestion Dashboard Compatibility Endpoints ====================
# IngestionDashboard.jsx uses /api/ingestion/* — proxy to the real /ingest/* router

@app.get("/api/ingestion/list", tags=["Ingestion Dashboard"])
async def api_ingestion_list(status: Optional[str] = None, source: Optional[str] = None, limit: int = 100, offset: int = 0):
    """List ingested documents (proxy for IngestionDashboard)."""
    try:
        from api.ingest import get_ingestion_service
        svc = get_ingestion_service()
        if svc is None:
            return {"documents": [], "total": 0}
        docs = svc.list_documents(status=status, source=source, limit=limit, offset=offset)
        return {"documents": docs, "total": len(docs)}
    except Exception as e:
        return {"documents": [], "total": 0, "error": str(e)}

@app.get("/api/ingestion/statistics", tags=["Ingestion Dashboard"])
async def api_ingestion_statistics():
    """Get ingestion stats (proxy for IngestionDashboard)."""
    try:
        from api.ingest import get_ingestion_service
        from vector_db.client import get_qdrant_client
        svc = get_ingestion_service()
        qdrant = get_qdrant_client()
        docs = svc.list_documents(limit=10000) if svc else []
        collection_info = qdrant.get_collection_info("documents") if qdrant.is_connected() else None
        return {
            "total_documents": len(docs),
            "completed": len([d for d in docs if d.get("status") == "completed"]),
            "pending": len([d for d in docs if d.get("status") == "pending"]),
            "failed": len([d for d in docs if d.get("status") == "failed"]),
            "total_chunks": sum(d.get("total_chunks", 0) for d in docs),
            "vector_count": collection_info.get("vectors_count", 0) if collection_info else 0,
            "qdrant_connected": qdrant.is_connected(),
        }
    except Exception as e:
        return {"total_documents": 0, "error": str(e)}

@app.get("/api/ingestion/{ingestion_id}", tags=["Ingestion Dashboard"])
async def api_ingestion_detail(ingestion_id: int):
    """Get single document details (proxy for IngestionDashboard)."""
    try:
        from api.ingest import get_ingestion_service
        svc = get_ingestion_service()
        if svc is None:
            raise HTTPException(status_code=503, detail="Ingestion service unavailable")
        info = svc.get_document_info(ingestion_id)
        if not info:
            raise HTTPException(status_code=404, detail="Document not found")
        return info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ingestion/upload", tags=["Ingestion Dashboard"])
async def api_ingestion_upload(file: UploadFile = File(...), source: str = Form("upload")):
    """Upload file for ingestion (proxy for IngestionDashboard)."""
    from api.ingest import ingest_file
    return await ingest_file(file=file, source=source)


# ==================== Knowledge Base Manager Endpoints ====================
# KnowledgeBaseManager.jsx uses /knowledge-base/*

@app.get("/knowledge-base/stats", tags=["Knowledge Base"])
async def kb_stats():
    """Knowledge base statistics for KnowledgeBaseManager."""
    try:
        from vector_db.client import get_qdrant_client
        qdrant = get_qdrant_client()
        collections = qdrant.list_collections() if qdrant.is_connected() else []
        info = qdrant.get_collection_info("documents") if qdrant.is_connected() else None
        return {
            "collections": collections,
            "documents_collection": info or {},
            "qdrant_connected": qdrant.is_connected(),
            "total_vectors": info.get("vectors_count", 0) if info else 0,
        }
    except Exception as e:
        return {"collections": [], "qdrant_connected": False, "error": str(e)}

@app.get("/knowledge-base/connectors", tags=["Knowledge Base"])
async def kb_connectors():
    """List knowledge base connectors (file sources)."""
    return {"connectors": [], "total": 0}

@app.post("/knowledge-base/connectors", tags=["Knowledge Base"])
async def kb_create_connector(payload: dict = Body({})):
    """Create a knowledge base connector."""
    return {"id": 1, "status": "created", **payload}

@app.post("/knowledge-base/connectors/{connector_id}/sync", tags=["Knowledge Base"])
async def kb_sync_connector(connector_id: int):
    """Sync a knowledge base connector."""
    return {"status": "synced", "connector_id": connector_id}


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
        # Use multi-tier system: VectorDB Ã¢â€ â€™ Model Knowledge Ã¢â€ â€™ User Context Request
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

            chat_repo.update(chat_id, last_message_at=datetime.now(timezone.utc))
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
        # Use multi-tier system: Model Knowledge Ã¢â€ â€™ Internet Search Ã¢â€ â€™ Context Request
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
        chat_repo.update(chat_id, last_message_at=datetime.now(timezone.utc))
        
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
    """Pause the runtime Ã¢â‚¬â€ stops diagnostic heartbeat and self-healing without killing the process."""
    app.state.runtime_paused = True
    diag = getattr(app.state, "diagnostic_engine", None)
    if diag:
        try:
            diag.pause()
        except Exception:
            pass
    return {"status": "paused", "message": "Runtime paused Ã¢â‚¬â€ heartbeat and self-healing suspended"}


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
    return {"status": "resumed", "message": "Runtime resumed Ã¢â‚¬â€ heartbeat and self-healing active"}


@app.post("/api/runtime/hot-reload", tags=["Runtime"])
async def runtime_hot_reload():
    """
    Full hot-reload: apply updates immediately without restart.
    Re-reads .env, refreshes model registry, reconnects DB, reloads all
    hot-reloadable modules (brain, pipeline, triggers, etc.).
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

    # 4. Hot-reload all service modules (code changes apply immediately)
    try:
        from core.hot_reload import hot_reload_all_services
        code_reload = hot_reload_all_services()
        results["code_reload"] = code_reload
    except Exception as e:
        results["code_reload"] = f"error: {e}"

    # 5. Run a quick diagnostic
    try:
        from cognitive.autonomous_diagnostics import get_diagnostics
        diag = get_diagnostics()
        diag_result = diag.on_startup()
        results["diagnostic"] = diag_result.get("status", "unknown")
    except Exception as e:
        results["diagnostic"] = f"error: {e}"

    return {"status": "hot-reload complete", "results": results}


@app.get("/api/runtime/security", tags=["Runtime"])
async def runtime_security():
    """Rate limit status and security configuration."""
    from core.security import get_rate_limit_status, MAX_REQUEST_SIZE
    return {
        "rate_limits": get_rate_limit_status(),
        "max_request_size_mb": round(MAX_REQUEST_SIZE / 1048576, 1),
    }


@app.post("/api/runtime/backup", tags=["Runtime"])
async def runtime_backup():
    """Create a database backup."""
    from core.security import backup_database
    path = backup_database()
    return {"backup_path": path}


@app.get("/api/runtime/resilience", tags=["Runtime"])
async def runtime_resilience():
    """Circuit breaker and degradation status."""
    from core.resilience import all_breaker_statuses, GracefulDegradation
    return {
        "degradation_level": GracefulDegradation.get_level(),
        "circuit_breakers": all_breaker_statuses(),
    }


@app.get("/api/runtime/connectivity", tags=["Runtime"])
async def runtime_connectivity():
    """Check connectivity of all external dependencies Ã¢â‚¬â€ Ollama, Qdrant, Kimi, Opus."""
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
        qdrant_loc = settings.QDRANT_URL if settings.QDRANT_URL else f"{settings.QDRANT_HOST}:{settings.QDRANT_PORT}"
        checks["qdrant"] = {"connected": connected, "url": qdrant_loc}
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

    # Embedding / GPU (setup_gpu.py sets EMBEDDING_DEVICE; only "using_gpu" true when CUDA actually available)
    try:
        import torch
        device = getattr(settings, "EMBEDDING_DEVICE", "cpu")
        cuda_available = getattr(torch, "cuda", None) and torch.cuda.is_available()
        checks["embedding"] = {
            "connected": True,
            "device": device,
            "cuda_available": cuda_available,
            "using_gpu": (device == "cuda" and cuda_available),
        }
    except Exception as e:
        checks["embedding"] = {"connected": False, "device": None, "cuda_available": False, "using_gpu": False, "error": str(e)}

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
        reload=True,
        timeout_keep_alive=30,
        limit_concurrency=50,
        timeout_graceful_shutdown=10,
    )
