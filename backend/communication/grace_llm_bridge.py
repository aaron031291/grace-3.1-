"""
Grace-LLM Bidirectional Communication Bridge

Enables async bidirectional communication between Grace and LLMs:
- Grace can ask LLMs questions
- LLMs can respond to Grace
- Async communication with callbacks
- Governance and verification enforced
- Anti-hallucination measures
- DeepSeek direct support
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable
from datetime import datetime, UTC
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session

from llm_orchestrator.llm_orchestrator import LLMOrchestrator, LLMTaskRequest, TaskType
from llm_orchestrator.hallucination_guard import VerificationResult
from genesis.genesis_key_service import get_genesis_service
from models.genesis_key_models import GenesisKeyType

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of messages in Grace-LLM communication."""
    GRACE_TO_LLM = "grace_to_llm"  # Grace asking LLM
    LLM_TO_GRACE = "llm_to_grace"  # LLM responding to Grace
    KNOWLEDGE_REQUEST = "knowledge_request"
    KNOWLEDGE_RESPONSE = "knowledge_response"
    VERIFICATION_REQUEST = "verification_request"
    VERIFICATION_RESPONSE = "verification_response"


@dataclass
class GraceLLMMessage:
    """Message in Grace-LLM bidirectional communication."""
    message_id: str
    message_type: MessageType
    sender: str  # "grace" or "llm"
    recipient: str  # "grace" or "llm"
    content: str
    context: Dict[str, Any]
    requires_response: bool = True
    callback: Optional[Callable[[Any], Awaitable[None]]] = None
    timestamp: datetime = None
    verified: bool = False
    trust_score: float = 0.0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(UTC)


class GraceLLMBridge:
    """
    Bidirectional communication bridge between Grace and LLMs.
    
    Features:
    - Async message passing
    - Callback-based responses
    - Governance enforcement
    - Verification pipeline
    - Anti-hallucination checks
    - DeepSeek direct support
    """
    
    def __init__(
        self,
        session: Session,
        llm_orchestrator: Optional[LLMOrchestrator] = None
    ):
        self.session = session
        self.llm_orchestrator = llm_orchestrator
        self.genesis_service = get_genesis_service()
        
        # Message queues
        self.grace_to_llm_queue: asyncio.Queue = asyncio.Queue()
        self.llm_to_grace_queue: asyncio.Queue = asyncio.Queue()
        
        # Active conversations
        self.active_conversations: Dict[str, List[GraceLLMMessage]] = {}
        
        # Message handlers
        self.message_handlers: Dict[MessageType, Callable] = {}
        
        # Running state
        self.running = False
        self.message_processor_task: Optional[asyncio.Task] = None
        
        logger.info("[GRACE-LLM-BRIDGE] Initialized")
    
    async def start(self):
        """Start the bidirectional communication bridge."""
        if self.running:
            return
        
        self.running = True
        self.message_processor_task = asyncio.create_task(self._process_messages())
        logger.info("[GRACE-LLM-BRIDGE] Started")
    
    async def stop(self):
        """Stop the bridge."""
        self.running = False
        if self.message_processor_task:
            self.message_processor_task.cancel()
            try:
                await self.message_processor_task
            except asyncio.CancelledError:
                pass
        logger.info("[GRACE-LLM-BRIDGE] Stopped")
    
    async def grace_asks_llm(
        self,
        question: str,
        context: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable[[Any], Awaitable[None]]] = None,
        use_deepseek: bool = True
    ) -> str:
        """
        Grace asks LLM a question (async bidirectional).
        
        Args:
            question: Grace's question
            context: Additional context
            callback: Async callback for response
            use_deepseek: Use DeepSeek directly
        
        Returns:
            Message ID for tracking
        """
        import uuid
        message_id = str(uuid.uuid4())
        
        message = GraceLLMMessage(
            message_id=message_id,
            message_type=MessageType.GRACE_TO_LLM,
            sender="grace",
            recipient="llm",
            content=question,
            context=context or {},
            callback=callback,
            requires_response=True
        )
        
        # Create Genesis Key
        self.genesis_service.create_key(
            key_type=GenesisKeyType.SYSTEM_EVENT,
            what_description=f"Grace asking LLM: {question[:100]}",
            who_actor="grace",
            why_reason="Knowledge request",
            how_method="llm_bidirectional_communication",
            context_data={
                "message_id": message_id,
                "question": question,
                "use_deepseek": use_deepseek
            },
            session=self.session
        )
        
        await self.grace_to_llm_queue.put(message)
        logger.info(f"[GRACE-LLM-BRIDGE] Grace asked LLM: {question[:50]}...")
        
        return message_id
    
    async def _process_messages(self):
        """Process messages in the queue (async)."""
        while self.running:
            try:
                # Process Grace -> LLM messages
                try:
                    message = await asyncio.wait_for(
                        self.grace_to_llm_queue.get(),
                        timeout=1.0
                    )
                    await self._handle_grace_to_llm(message)
                except asyncio.TimeoutError:
                    pass
                
                # Process LLM -> Grace messages
                try:
                    message = await asyncio.wait_for(
                        self.llm_to_grace_queue.get(),
                        timeout=1.0
                    )
                    await self._handle_llm_to_grace(message)
                except asyncio.TimeoutError:
                    pass
                
            except Exception as e:
                logger.error(f"[GRACE-LLM-BRIDGE] Error processing messages: {e}")
                await asyncio.sleep(1)
    
    async def _handle_grace_to_llm(self, message: GraceLLMMessage):
        """Handle Grace -> LLM message."""
        logger.info(f"[GRACE-LLM-BRIDGE] Processing Grace->LLM: {message.message_id}")
        
        try:
            # Create LLM task request
            task_request = LLMTaskRequest(
                task_id=message.message_id,
                prompt=message.content,
                task_type=TaskType.KNOWLEDGE_ACQUISITION,
                require_verification=True,  # Governance: Always verify
                require_consensus=True,  # Anti-hallucination: Consensus
                require_grounding=True,  # Anti-hallucination: Grounding
                enable_learning=True,
                context_documents=message.context.get("documents", [])
            )
            
            # Execute with governance (synchronous method)
            # Note: execute_task is synchronous, so we run it in thread
            def execute_sync():
                return self.llm_orchestrator.execute_task(
                    prompt=task_request.prompt,
                    task_type=task_request.task_type,
                    user_id=task_request.user_id,
                    require_verification=task_request.require_verification,
                    require_consensus=task_request.require_consensus,
                    require_grounding=task_request.require_grounding,
                    enable_learning=task_request.enable_learning,
                    system_prompt=task_request.system_prompt,
                    context_documents=task_request.context_documents,
                    cognitive_constraints=task_request.cognitive_constraints
                )
            
            result = await asyncio.to_thread(execute_sync)
            
            # Create response message
            response = GraceLLMMessage(
                message_id=f"{message.message_id}_response",
                message_type=MessageType.LLM_TO_GRACE,
                sender="llm",
                recipient="grace",
                content=result.content if result.success else f"Error: {result.content}",
                context={
                    "original_message_id": message.message_id,
                    "trust_score": result.trust_score,
                    "confidence_score": result.confidence_score,
                    "verified": result.verification_result.passed if result.verification_result else False,
                    "model_used": result.model_used
                },
                verified=result.verification_result.passed if result.verification_result else False,
                trust_score=result.trust_score,
                requires_response=False
            )
            
            # Put response in queue
            await self.llm_to_grace_queue.put(response)
            
            # Call callback if provided
            if message.callback:
                await message.callback(response)
            
            # Create Genesis Key for response
            self.genesis_service.create_key(
                key_type=GenesisKeyType.SYSTEM_EVENT,
                what_description=f"LLM responded to Grace: {message.content[:100]}",
                who_actor="llm",
                why_reason="Response to Grace's question",
                how_method="llm_bidirectional_communication",
                context_data={
                    "message_id": message.message_id,
                    "response_id": response.message_id,
                    "trust_score": result.trust_score,
                    "verified": response.verified
                },
                session=self.session
            )
            
        except Exception as e:
            logger.error(f"[GRACE-LLM-BRIDGE] Error handling Grace->LLM: {e}")
            # Send error response
            error_response = GraceLLMMessage(
                message_id=f"{message.message_id}_error",
                message_type=MessageType.LLM_TO_GRACE,
                sender="llm",
                recipient="grace",
                content=f"Error: {str(e)}",
                context={"error": True},
                verified=False,
                trust_score=0.0,
                requires_response=False
            )
            await self.llm_to_grace_queue.put(error_response)
    
    async def _handle_llm_to_grace(self, message: GraceLLMMessage):
        """Handle LLM -> Grace message."""
        logger.info(f"[GRACE-LLM-BRIDGE] Processing LLM->Grace: {message.message_id}")
        
        # Store in conversation history
        conv_id = message.context.get("original_message_id", message.message_id)
        if conv_id not in self.active_conversations:
            self.active_conversations[conv_id] = []
        self.active_conversations[conv_id].append(message)
        
        # Grace can process the response
        # This would trigger Grace's learning/action systems
        logger.info(f"[GRACE-LLM-BRIDGE] LLM response received: {message.content[:100]}...")
    
    async def wait_for_response(
        self,
        message_id: str,
        timeout: float = 30.0
    ) -> Optional[GraceLLMMessage]:
        """Wait for response to a message."""
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            # Check conversation history
            if message_id in self.active_conversations:
                messages = self.active_conversations[message_id]
                for msg in messages:
                    if msg.message_type == MessageType.LLM_TO_GRACE:
                        return msg
            
            await asyncio.sleep(0.1)
        
        return None


def get_grace_llm_bridge(
    session: Session,
    llm_orchestrator: Optional[LLMOrchestrator] = None
) -> GraceLLMBridge:
    """Get or create Grace-LLM bridge."""
    return GraceLLMBridge(session=session, llm_orchestrator=llm_orchestrator)
