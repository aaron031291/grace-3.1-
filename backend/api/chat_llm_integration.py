import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from llm_orchestrator.llm_orchestrator import get_llm_orchestrator, LLMOrchestrator
from llm_orchestrator.multi_llm_client import TaskType
from genesis.pipeline_integration import DataPipeline
from genesis.genesis_key_service import get_genesis_service

# Import emoji sanitization
try:
    from utils.emoji_sanitizer import sanitize_llm_output
except ImportError:
    def sanitize_llm_output(output, replace=True):
        return output

logger = logging.getLogger(__name__)


class ChatLLMIntegration:
    """
    Integrates full LLM orchestrator into chat system.
    
    Features:
    - All chat messages use LLM orchestrator
    - Genesis Keys for all interactions
    - Layer 1 integration
    - World model integration
    - Learning memory integration
    - Trust scoring
    """
    
    def __init__(self, session: Optional[Session] = None):
        """Initialize chat LLM integration."""
        self.session = session
        self.orchestrator = get_llm_orchestrator(session=session)
        self.pipeline = DataPipeline(session=session) if session else None
        self.genesis_service = get_genesis_service(session=session) if session else None
    
    def process_chat_message(
        self,
        message: str,
        chat_id: int,
        folder_path: Optional[str] = None,
        user_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process chat message through full LLM orchestrator.
        
        Args:
            message: User message
            chat_id: Chat ID
            folder_path: Folder path (for folder chats)
            user_id: User ID
            conversation_history: Previous messages in conversation
        
        Returns:
            Complete response with LLM output, Genesis Key, trust scores, etc.
        """
        logger.info(f"[CHAT-LLM] Processing message for chat {chat_id}")
        
        # Build prompt with conversation history
        prompt = self._build_prompt_with_history(message, conversation_history)
        
        # Determine task type based on message content
        task_type = self._determine_task_type(message, folder_path)
        
        # Execute through LLM orchestrator
        result = self.orchestrator.execute_task(
            prompt=prompt,
            task_type=task_type,
            user_id=user_id or f"chat_user_{chat_id}",
            require_verification=True,
            require_consensus=False,  # Faster for chat
            require_grounding=bool(folder_path),  # Ground in folder if folder chat
            enable_learning=True,
            context_documents=[folder_path] if folder_path else None
        )
        
        # Integrate with world model
        world_model_result = None
        if self.pipeline and result.genesis_key_id:
            try:
                world_model_result = self.pipeline._integrate_world_model(
                    genesis_key=self.genesis_service.get_by_key_id(result.genesis_key_id) if self.genesis_service else None,
                    input_data={
                        "message": message,
                        "response": result.content,
                        "chat_id": chat_id,
                        "folder_path": folder_path
                    },
                    rag_result={"indexed": True}
                )
            except Exception as e:
                logger.warning(f"World model integration failed: {e}")
        
        # Sanitize LLM output to remove emojis
        sanitized_content = sanitize_llm_output(result.content, replace=True)
        
        # Build response
        response = {
            "content": sanitized_content,  # Emojis removed/replaced
            "genesis_key_id": result.genesis_key_id,
            "trust_score": result.trust_score,
            "confidence_score": result.confidence_score,
            "model_used": result.model_used,
            "task_id": result.task_id,
            "world_model_integrated": world_model_result is not None if world_model_result else False,
            "timestamp": result.timestamp.isoformat() if result.timestamp else datetime.now().isoformat()
        }
        
        # Add verification details if available
        if result.verification_result:
            response["verification"] = {
                "is_verified": result.verification_result.is_verified,
                "confidence": result.verification_result.confidence_score,
                "trust_score": result.verification_result.trust_score
            }
        
        return response
    
    def _build_prompt_with_history(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> str:
        """Build prompt with conversation history."""
        if not conversation_history:
            return message
        
        # Build context from history
        context_parts = []
        for msg in conversation_history[-10:]:  # Last 10 messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                context_parts.append(f"User: {content}")
            elif role == "assistant":
                context_parts.append(f"Assistant: {content}")
        
        # Add current message
        context_parts.append(f"User: {message}")
        
        return "\n".join(context_parts)
    
    def _determine_task_type(
        self,
        message: str,
        folder_path: Optional[str]
    ) -> TaskType:
        """Determine task type from message and context."""
        message_lower = message.lower()
        
        # Code-related
        if any(keyword in message_lower for keyword in [
            "code", "function", "class", "import", "def ", "create a script",
            "write code", "implement", "debug", "fix error"
        ]):
            if "debug" in message_lower or "fix" in message_lower or "error" in message_lower:
                return TaskType.CODE_DEBUGGING
            elif "explain" in message_lower or "how does" in message_lower:
                return TaskType.CODE_EXPLANATION
            elif "review" in message_lower:
                return TaskType.CODE_REVIEW
            else:
                return TaskType.CODE_GENERATION
        
        # Reasoning
        if any(keyword in message_lower for keyword in [
            "why", "how should", "what is the best", "analyze", "compare",
            "reason", "think about"
        ]):
            return TaskType.REASONING
        
        # Planning
        if any(keyword in message_lower for keyword in [
            "plan", "strategy", "steps", "roadmap", "design"
        ]):
            return TaskType.PLANNING
        
        # Folder chat defaults to general with grounding
        if folder_path:
            return TaskType.GENERAL
        
        # Default
        return TaskType.GENERAL


# Global instance
_chat_llm_integration: Optional[ChatLLMIntegration] = None


def get_chat_llm_integration(session: Optional[Session] = None) -> ChatLLMIntegration:
    """Get or create global chat LLM integration instance."""
    global _chat_llm_integration
    if _chat_llm_integration is None or session is not None:
        _chat_llm_integration = ChatLLMIntegration(session=session)
    return _chat_llm_integration
