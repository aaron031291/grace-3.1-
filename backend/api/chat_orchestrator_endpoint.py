import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from chat_llm_integration import get_chat_llm_integration
from database.session import get_session
from models.repositories import ChatRepository, ChatHistoryRepository
class ChatOrchestratorRequest(BaseModel):
    logger = logging.getLogger(__name__)
    """Request for LLM orchestrator chat."""
    message: str = Field(..., description="User message")
    chat_id: Optional[int] = Field(None, description="Chat ID (if existing chat)")
    folder_path: Optional[str] = Field(None, description="Folder path (for folder chats)")
    user_id: Optional[str] = Field(None, description="User ID")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="Previous messages")


class ChatOrchestratorResponse(BaseModel):
    """Response from LLM orchestrator chat."""
    content: str = Field(..., description="LLM response")
    genesis_key_id: Optional[str] = Field(None, description="Genesis Key for this interaction")
    trust_score: float = Field(..., description="Trust score (0-1)")
    confidence_score: float = Field(..., description="Confidence score (0-1)")
    model_used: str = Field(..., description="Model used")
    world_model_integrated: bool = Field(..., description="Whether integrated into world model")
    verification: Optional[Dict[str, Any]] = Field(None, description="Verification details")
    timestamp: str = Field(..., description="Timestamp")


@router.post("/orchestrator", response_model=ChatOrchestratorResponse)
async def chat_with_orchestrator(
    request: ChatOrchestratorRequest,
    session: Session = Depends(get_session)
):
    """
    Chat using full LLM orchestrator with world model integration.
    
    Features:
    - Full LLM orchestrator pipeline
    - Genesis Key assignment
    - World model integration
    - Trust scoring
    - Verification
    - Folder context support
    """
    try:
        chat_llm = get_chat_llm_integration(session=session)
        
        # Get conversation history if chat_id provided
        conversation_history = request.conversation_history
        if request.chat_id and not conversation_history:
            try:
                history_repo = ChatHistoryRepository(session)
                messages = history_repo.get_by_chat(request.chat_id, limit=20)
                conversation_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in messages
                ]
            except Exception as e:
                logger.warning(f"Could not load conversation history: {e}")
                conversation_history = []
        
        # Process through LLM orchestrator
        result = chat_llm.process_chat_message(
            message=request.message,
            chat_id=request.chat_id or 0,
            folder_path=request.folder_path,
            user_id=request.user_id,
            conversation_history=conversation_history
        )
        
        # Save to chat history if chat_id provided
        if request.chat_id:
            try:
                history_repo = ChatHistoryRepository(session)
                
                # Save user message
                history_repo.add_message(
                    chat_id=request.chat_id,
                    role="user",
                    content=request.message
                )
                
                # Save assistant message
                history_repo.add_message(
                    chat_id=request.chat_id,
                    role="assistant",
                    content=result["content"]
                )
            except Exception as e:
                logger.warning(f"Could not save to chat history: {e}")
        
        return ChatOrchestratorResponse(
            content=result["content"],
            genesis_key_id=result.get("genesis_key_id"),
            trust_score=result.get("trust_score", 0.7),
            confidence_score=result.get("confidence_score", 0.7),
            model_used=result.get("model_used", "unknown"),
            world_model_integrated=result.get("world_model_integrated", False),
            verification=result.get("verification"),
            timestamp=result.get("timestamp", "")
        )
        
    except Exception as e:
        logger.error(f"Chat orchestrator error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/directory-prompt-orchestrator")
async def directory_chat_with_orchestrator(
    query: str = Body(...),
    directory_path: str = Body(...),
    chat_id: Optional[int] = Body(None),
    session: Session = Depends(get_session)
):
    """
    Directory/folder chat using full LLM orchestrator.
    
    This endpoint is specifically for folder chats in the Documents tab.
    """
    try:
        chat_llm = get_chat_llm_integration(session=session)
        
        # Get conversation history if chat_id provided
        conversation_history = []
        if chat_id:
            try:
                history_repo = ChatHistoryRepository(session)
                messages = history_repo.get_by_chat(chat_id, limit=20)
                conversation_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in messages
                ]
            except Exception as e:
                logger.warning(f"Could not load conversation history: {e}")
        
        # Process with folder context
        result = chat_llm.process_chat_message(
            message=query,
            chat_id=chat_id or 0,
            folder_path=directory_path,
            user_id=None,
            conversation_history=conversation_history
        )
        
        # Save to chat history if chat_id provided
        if chat_id:
            try:
                history_repo = ChatHistoryRepository(session)
                history_repo.add_message(chat_id=chat_id, role="user", content=query)
                history_repo.add_message(chat_id=chat_id, role="assistant", content=result["content"])
            except Exception as e:
                logger.warning(f"Could not save to chat history: {e}")
        
        return {
            "response": result["content"],
            "genesis_key_id": result.get("genesis_key_id"),
            "trust_score": result.get("trust_score", 0.7),
            "confidence_score": result.get("confidence_score", 0.7),
            "model_used": result.get("model_used", "unknown"),
            "world_model_integrated": result.get("world_model_integrated", False),
            "sources": []  # Would include RAG sources if available
        }
        
    except Exception as e:
        logger.error(f"Directory chat orchestrator error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
