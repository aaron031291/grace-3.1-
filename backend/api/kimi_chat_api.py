"""
Kimi Chat API - User's Direct Access to Grace

FastAPI endpoints that give the user a chat interface to Kimi.
Kimi has full system access: Oracle, source code, memory, trust,
evolution, world model — everything.

Endpoints:
  POST /kimi/chat          - Send message, get response
  POST /kimi/chat/stream   - SSE streaming response
  GET  /kimi/status        - System status (world model)
  GET  /kimi/history       - Conversation history
  POST /kimi/learn         - Submit whitelist items for learning
  POST /kimi/heal          - Report an issue for self-healing
  POST /kimi/interrogate   - Interrogate a document (6W)
  GET  /kimi/world         - Full world state JSON
  GET  /kimi/world/summary - World state NLP summary
  GET  /kimi/stats         - Comprehensive system stats
"""

import logging
import json
import uuid
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# Try FastAPI imports (may not be installed in test environment)
try:
    from fastapi import APIRouter, HTTPException
    from fastapi.responses import StreamingResponse
    from pydantic import BaseModel, Field
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    # Stubs for testing without FastAPI
    class BaseModel:
        pass
    def Field(*args, **kwargs):
        return None

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from oracle_pipeline.kimi_orchestrator import KimiOrchestrator, KimiMode
from oracle_pipeline.perpetual_learning_loop import PerpetualLearningLoop
from oracle_pipeline.world_model import WorldModel


# =========================================================================
# REQUEST/RESPONSE MODELS
# =========================================================================

class ChatRequest(BaseModel if FASTAPI_AVAILABLE else object):
    """Chat message from user."""
    message: str = ""
    mode: str = "orchestrate"
    chat_id: Optional[str] = None
    include_world_context: bool = True


class ChatResponse(BaseModel if FASTAPI_AVAILABLE else object):
    """Chat response from Kimi."""
    response_id: str = ""
    message: str = ""
    mode: str = ""
    confidence: float = 0.0
    sources: List[str] = []
    oracle_results: int = 0
    reasoning_steps: int = 0
    grounded: bool = True
    world_summary: Optional[str] = None


class LearnRequest(BaseModel if FASTAPI_AVAILABLE else object):
    """Request to learn new topics."""
    items: str = ""  # Newline-separated or bullet-pointed
    domain: Optional[str] = None


class HealRequest(BaseModel if FASTAPI_AVAILABLE else object):
    """Request to heal an issue."""
    issue: str = ""
    severity: str = "medium"


class InterrogateRequest(BaseModel if FASTAPI_AVAILABLE else object):
    """Request to interrogate a document."""
    content: str = ""
    domain: Optional[str] = None


# =========================================================================
# KIMI CHAT SYSTEM (backend, works with or without FastAPI)
# =========================================================================

class KimiChatSystem:
    """
    The backend system for Kimi chat.

    Works independently of FastAPI — can be used from any interface.
    The FastAPI router below is just one way to expose it.
    """

    def __init__(self):
        self.loop = PerpetualLearningLoop()
        self.kimi = KimiOrchestrator()
        self.kimi.connect_full_system(self.loop)
        self.world_model = WorldModel()
        self.world_model.connect_all(self.kimi)
        logger.info("[KIMI-CHAT] System initialized with full connections")

    def chat(
        self, message: str, mode: str = "orchestrate",
        include_world_context: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a chat message from the user.

        1. Record in world model
        2. Get world context (if enabled)
        3. Query Kimi with full system access
        4. Record response in world model
        5. Return structured response
        """
        # Record user message
        self.world_model.record_user_message(message)

        # Get world context for Kimi
        world_summary = None
        if include_world_context:
            world_summary = self.world_model.get_world_summary_nlp()

        # Map mode string to enum
        try:
            kimi_mode = KimiMode(mode)
        except ValueError:
            kimi_mode = KimiMode.ORCHESTRATE

        # Query Kimi
        response = self.kimi.query(message, mode=kimi_mode)

        # Record Kimi's response
        self.world_model.record_kimi_response(
            content=response.content,
            mode=response.mode.value,
            confidence=response.confidence,
            sources=response.sources_consulted,
        )

        return {
            "response_id": response.response_id,
            "message": response.content,
            "mode": response.mode.value,
            "confidence": response.confidence,
            "sources": response.sources_consulted,
            "oracle_results": response.oracle_results,
            "reasoning_steps": response.reasoning_steps,
            "grounded": response.grounded,
            "world_summary": world_summary,
        }

    def learn(self, items: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """Submit items for learning through the perpetual loop."""
        iteration = self.loop.seed_from_whitelist(items, domain=domain)
        return {
            "items_ingested": iteration.items_ingested,
            "records_created": iteration.records_created,
            "domains": iteration.domains_active,
        }

    def heal(self, issue: str) -> Dict[str, Any]:
        """Report an issue for self-healing."""
        response = self.kimi.heal(issue)
        return {
            "response_id": response.response_id,
            "message": response.content,
            "confidence": response.confidence,
        }

    def interrogate(self, content: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """Interrogate a document with 6W questions."""
        response = self.kimi.interrogate_document(content, domain=domain)
        return {
            "response_id": response.response_id,
            "message": response.content,
            "confidence": response.confidence,
            "json_data": response.json_data,
        }

    def get_world_state(self) -> Dict[str, Any]:
        """Get full world state as JSON."""
        return self.world_model.get_world_summary_json()

    def get_world_summary(self) -> str:
        """Get world state as human-readable summary."""
        return self.world_model.get_world_summary_nlp()

    def get_history(self, last_n: int = 20) -> List[Dict[str, Any]]:
        """Get conversation history."""
        return self.world_model.get_conversation_context(last_n)

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive system stats."""
        return {
            "kimi": self.kimi.get_stats(),
            "loop": self.loop.get_stats(),
            "world_model": self.world_model.get_stats(),
        }


# =========================================================================
# FASTAPI ROUTER (optional — only created if FastAPI is installed)
# =========================================================================

# Global chat system instance
_chat_system: Optional[KimiChatSystem] = None


def get_chat_system() -> KimiChatSystem:
    """Get or create the global chat system."""
    global _chat_system
    if _chat_system is None:
        _chat_system = KimiChatSystem()
    return _chat_system


if FASTAPI_AVAILABLE:
    router = APIRouter(prefix="/kimi", tags=["Kimi Chat"])

    @router.post("/chat", summary="Chat with Kimi")
    async def chat_with_kimi(request: ChatRequest) -> Dict[str, Any]:
        """Send a message to Kimi and get a response."""
        system = get_chat_system()
        return system.chat(
            message=request.message,
            mode=request.mode,
            include_world_context=request.include_world_context,
        )

    @router.post("/learn", summary="Submit items for learning")
    async def learn_topics(request: LearnRequest) -> Dict[str, Any]:
        """Submit whitelist items for Grace to learn."""
        system = get_chat_system()
        return system.learn(items=request.items, domain=request.domain)

    @router.post("/heal", summary="Report issue for self-healing")
    async def report_issue(request: HealRequest) -> Dict[str, Any]:
        """Report an issue for Grace's self-healing system."""
        system = get_chat_system()
        return system.heal(issue=request.issue)

    @router.post("/interrogate", summary="Interrogate a document")
    async def interrogate_document(request: InterrogateRequest) -> Dict[str, Any]:
        """Interrogate a document with 6W Socratic questions."""
        system = get_chat_system()
        return system.interrogate(content=request.content, domain=request.domain)

    @router.get("/world", summary="Get world state")
    async def get_world() -> Dict[str, Any]:
        """Get Grace's full world state as JSON."""
        system = get_chat_system()
        return system.get_world_state()

    @router.get("/world/summary", summary="Get world summary")
    async def get_world_summary() -> Dict[str, str]:
        """Get Grace's world state as human-readable summary."""
        system = get_chat_system()
        return {"summary": system.get_world_summary()}

    @router.get("/history", summary="Get conversation history")
    async def get_history(last_n: int = 20) -> List[Dict[str, Any]]:
        """Get recent conversation history."""
        system = get_chat_system()
        return system.get_history(last_n)

    @router.get("/status", summary="Get system status")
    async def get_status() -> Dict[str, Any]:
        """Get comprehensive system status."""
        system = get_chat_system()
        return system.get_stats()
