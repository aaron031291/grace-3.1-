"""
Oracle Hub Startup Hooks

Initializes the Unified Oracle Hub at application startup and connects
all intelligence sources for continuous ingestion.

Call `initialize_oracle_hub_on_startup()` from app.py startup event.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def initialize_oracle_hub_on_startup():
    """
    Initialize Oracle Hub with all connections at app startup.
    
    Call this from FastAPI startup event:
    
    @app.on_event("startup")
    async def startup():
        initialize_oracle_hub_on_startup()
    """
    logger.info("[ORACLE-HUB] Initializing at startup...")
    
    try:
        from oracle_intelligence.unified_oracle_hub import (
            get_oracle_hub,
            hook_librarian_to_oracle,
            hook_sandbox_to_oracle,
            hook_learning_memory_to_oracle,
            hook_self_healing_to_oracle
        )
        
        # Get dependencies
        session = None
        genesis_service = None
        oracle_core = None
        librarian = None
        learning_memory = None
        sandbox_lab = None
        self_healer = None
        
        # Database session
        try:
            from database.session import SessionLocal
            session = SessionLocal()
            logger.info("[ORACLE-HUB] ✓ Database session connected")
        except Exception as e:
            logger.warning(f"[ORACLE-HUB] Database session unavailable: {e}")
        
        # Genesis Key Service
        try:
            from models.genesis_key_models import get_genesis_key_service
            genesis_service = get_genesis_key_service()
            logger.info("[ORACLE-HUB] ✓ Genesis Key service connected")
        except Exception as e:
            logger.warning(f"[ORACLE-HUB] Genesis service unavailable: {e}")
        
        # Oracle Core
        try:
            from oracle_intelligence.oracle_core import OracleCore
            oracle_core = OracleCore(
                session=session,
                genesis_service=genesis_service
            )
            logger.info("[ORACLE-HUB] ✓ Oracle Core initialized")
        except Exception as e:
            logger.warning(f"[ORACLE-HUB] Oracle Core unavailable: {e}")
        
        # Librarian Pipeline
        try:
            from genesis.librarian_pipeline import LibrarianPipeline
            librarian = LibrarianPipeline()
            logger.info("[ORACLE-HUB] ✓ Librarian Pipeline connected")
        except Exception as e:
            logger.warning(f"[ORACLE-HUB] Librarian unavailable: {e}")
        
        # Learning Memory
        try:
            from cognitive.learning_memory import get_learning_memory
            learning_memory = get_learning_memory()
            logger.info("[ORACLE-HUB] ✓ Learning Memory connected")
        except Exception as e:
            logger.warning(f"[ORACLE-HUB] Learning Memory unavailable: {e}")
        
        # Sandbox Lab
        try:
            from cognitive.autonomous_sandbox_lab import get_sandbox_lab
            sandbox_lab = get_sandbox_lab()
            logger.info("[ORACLE-HUB] ✓ Sandbox Lab connected")
        except Exception as e:
            logger.warning(f"[ORACLE-HUB] Sandbox Lab unavailable: {e}")
        
        # Self-Healer
        try:
            from cognitive.self_healer import get_self_healer
            self_healer = get_self_healer()
            logger.info("[ORACLE-HUB] ✓ Self-Healer connected")
        except Exception as e:
            logger.warning(f"[ORACLE-HUB] Self-Healer unavailable: {e}")
        
        # Create Oracle Hub
        hub = get_oracle_hub(
            session=session,
            genesis_service=genesis_service,
            oracle_core=oracle_core,
            librarian_pipeline=librarian,
            learning_memory=learning_memory,
            sandbox_lab=sandbox_lab
        )
        
        # Hook all systems
        if librarian:
            hook_librarian_to_oracle(librarian, hub)
        if sandbox_lab:
            hook_sandbox_to_oracle(sandbox_lab, hub)
        if learning_memory:
            hook_learning_memory_to_oracle(learning_memory, hub)
        if self_healer:
            hook_self_healing_to_oracle(self_healer, hub)
        
        # Start background sync (every 5 minutes)
        hub.start_background_sync(interval_seconds=300)
        
        logger.info("[ORACLE-HUB] ✓ Initialization complete - all sources connected")
        
        return hub
        
    except Exception as e:
        logger.error(f"[ORACLE-HUB] Startup initialization failed: {e}")
        return None


def get_hub_status_summary() -> dict:
    """Get a summary of Oracle Hub status for health checks."""
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        hub = get_oracle_hub()
        return hub.get_status()
    except Exception as e:
        return {"status": "error", "error": str(e)}
