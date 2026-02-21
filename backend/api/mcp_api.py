"""
Grace OS — MCP API Endpoints.

Provides REST endpoints for MCP-based tool-calling chat:
- POST /api/mcp/chat — Multi-turn tool-calling conversation
- GET  /api/mcp/tools — List available MCP tools
- GET  /api/mcp/status — MCP system status
- POST /api/mcp/tool — Execute a single MCP tool directly
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.session import get_db
from models.repositories import ChatRepository, ChatHistoryRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["MCP - Model Context Protocol"])


# ==================== Request/Response Models ====================

class MCPChatMessage(BaseModel):
    role: str = Field(..., description="Message role: 'user', 'assistant', 'system'")
    content: str = Field(..., description="Message content")


class MCPChatRequest(BaseModel):
    messages: Optional[List[MCPChatMessage]] = Field(None, description="Conversation messages")
    chat_id: Optional[int] = Field(None, description="Grace Chat ID for database persistence")
    model: Optional[str] = Field(None, description="LLM model to use (default from env)")
    temperature: Optional[float] = Field(0.3, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(4096, description="Max response tokens")
    system_prompt: Optional[str] = Field(None, description="Override system prompt")
    use_rag: Optional[bool] = Field(True, description="Enable RAG knowledge search tool")
    use_web: Optional[bool] = Field(True, description="Enable web search and fetch tools")
    stream: Optional[bool] = Field(False, description="Stream response via Server-Sent Events (SSE)")


class MCPChatResponse(BaseModel):
    content: str = Field(..., description="Final response text")
    tool_calls_made: List[Dict[str, Any]] = Field(default_factory=list)
    sources: List[Dict[str, Any]] = Field(default_factory=list, description="Extracted RAG sources")
    turns: int = Field(0, description="Number of LLM turns used")
    model: Optional[str] = None
    success: bool = True


class MCPToolCallRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the MCP tool to call")
    arguments: Dict[str, Any] = Field(default_factory=dict)


class MCPToolCallResponse(BaseModel):
    content: str = Field("")
    success: bool = True
    error: Optional[str] = None
    duration_ms: Optional[float] = None


# ==================== Global Orchestrator ====================

_orchestrator = None


async def get_orchestrator(enable_rag: bool = True, enable_web: bool = True):
    """Lazy-initialize the MCP orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        from grace_mcp.orchestrator import MCPOrchestrator
        _orchestrator = MCPOrchestrator(
            enable_rag=enable_rag,
            enable_web=enable_web
        )
        success = await _orchestrator.initialize()
        if not success:
            _orchestrator = None
            raise HTTPException(
                status_code=503,
                detail="MCP server is not available. Ensure DesktopCommanderMCP is built."
            )
    return _orchestrator


# ==================== Endpoints ====================

@router.post("/chat", response_model=MCPChatResponse)
async def mcp_chat(request: MCPChatRequest, db: Session = Depends(get_db)):
    """
    Multi-turn tool-calling chat endpoint with database persistence.
    """
    try:
        orchestrator = await get_orchestrator(
            enable_rag=request.use_rag,
            enable_web=request.use_web
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"MCP initialization failed: {str(e)}")

    chat_repo = ChatRepository(db)
    history_repo = ChatHistoryRepository(db)
    
    chat_id = request.chat_id
    messages = []
    
    # 1. Load context if chat_id provided
    if chat_id:
        chat = chat_repo.get(chat_id)
        if not chat:
            raise HTTPException(status_code=404, detail=f"Chat {chat_id} not found")
        
        # If model not in request, use chat default
        if not request.model:
            request.model = chat.model

        # Fetch existing history from DB
        db_history = history_repo.get_by_chat(chat_id, skip=0, limit=50)
        messages = [{"role": m.role, "content": m.content} for m in db_history]
        
        # 2. Append incoming messages from client
        if request.messages:
            incoming_messages = [{"role": m.role, "content": m.content} for m in request.messages]
            
            # Identify which incoming messages are NEW (not in DB yet)
            # Simplest way: if messages is empty, everything is new. 
            # If not empty, we assume the client is only sending the LATEST turn
            # because that's our implementation in ChatWindow.jsx
            for msg in incoming_messages:
                # Save to DB if user message
                if msg["role"] == "user":
                    history_repo.add_message(
                        chat_id=chat_id,
                        role="user",
                        content=msg["content"]
                    )
                messages.append(msg)
        
        if not messages:
            raise HTTPException(status_code=400, detail="No messages provided and no history found.")
    else:
        # Fallback to provided messages (stateless)
        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages or chat_id required.")
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

    # Override system prompt if provided
    if request.system_prompt:
        orchestrator.system_prompt = request.system_prompt

    if request.stream:
        # Create an asyncio.Queue for streaming events
        queue = asyncio.Queue()

        def on_tool_call(name, args):
            # Create a non-blocking task to put into the queue from sync/async boundary
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {"type": "tool_call", "name": name, "args": args}
            )

        def on_tool_result(name, result):
            loop = asyncio.get_event_loop()
            loop.call_soon_threadsafe(
                queue.put_nowait,
                {
                    "type": "tool_result", 
                    "name": name, 
                    "success": result.get("success", False),
                    "duration_ms": result.get("duration_ms", 0),
                    "result_preview": str(result.get("content", ""))[:200]
                }
            )

        async def chat_runner():
            try:
                result = await orchestrator.chat(
                    messages=messages,
                    model=request.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    on_tool_call=on_tool_call,
                    on_tool_result=on_tool_result
                )
                await queue.put({"type": "final_result", "data": result})
            except Exception as e:
                logger.error(f"[MCP API] Streaming error: {e}")
                await queue.put({"type": "error", "error": str(e)})

        # Start the orchestrator in the background
        asyncio.create_task(chat_runner())

        async def sse_generator():
            try:
                while True:
                    item = await queue.get()
                    
                    if item["type"] == "final_result":
                        # Save assistant response to DB
                        result = item["data"]
                        content = result.get("content", "")
                        if chat_id and result.get("success"):
                            history_repo.add_message(
                                chat_id=chat_id,
                                role="assistant",
                                content=content
                            )
                            from datetime import datetime
                            chat_repo.update(chat_id, updated_at=datetime.utcnow(), last_message_at=datetime.utcnow())
                        
                        # Yield final content
                        yield f"data: {json.dumps({'type': 'content', 'content': content, 'sources': result.get('sources', []), 'tool_calls': result.get('tool_calls_made', [])})}\n\n"
                        # We send a special [DONE] event
                        yield "data: [DONE]\n\n"
                        break
                    elif item["type"] == "error":
                        yield f"data: {json.dumps({'type': 'error', 'error': item['error']})}\n\n"
                        yield "data: [DONE]\n\n"
                        break
                    else:
                        # tool_call or tool_result
                        yield f"data: {json.dumps(item)}\n\n"
            except asyncio.CancelledError:
                logger.info("[MCP API] Client disconnected from streaming connection")
                    
        return StreamingResponse(
            sse_generator(), 
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    try:
        # Run the multi-turn orchestrator (non-streaming legacy path)
        result = await orchestrator.chat(
            messages=messages,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        content = result.get("content", "")
        
        # 2. Save assistant response to DB
        if chat_id and result.get("success"):
            history_repo.add_message(
                chat_id=chat_id,
                role="assistant",
                content=content
            )
            # Update chat timestamp
            from datetime import datetime
            chat_repo.update(chat_id, updated_at=datetime.utcnow(), last_message_at=datetime.utcnow())

        return MCPChatResponse(
            content=content,
            tool_calls_made=result.get("tool_calls_made", []),
            sources=result.get("sources", []),
            turns=result.get("turns", 0),
            model=result.get("model"),
            success=result.get("success", True)
        )

    except Exception as e:
        logger.error(f"[MCP API] Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
async def list_mcp_tools():
    """List all available MCP tools."""
    try:
        orchestrator = await get_orchestrator()
        tools = await orchestrator.mcp_client.list_tools()
        return {
            "tools": tools,
            "count": len(tools)
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/status")
async def mcp_status():
    """Get MCP system status."""
    if _orchestrator is None:
        return {
            "initialized": False,
            "message": "MCP orchestrator not yet initialized. Send a /chat request to start."
        }
    return _orchestrator.get_status()


@router.post("/tool", response_model=MCPToolCallResponse)
async def call_mcp_tool(request: MCPToolCallRequest):
    """
    Execute a single MCP tool directly (bypass LLM).
    Useful for direct file operations from the frontend.
    """
    try:
        orchestrator = await get_orchestrator()
    except HTTPException:
        raise

    result = await orchestrator.mcp_client.call_tool(
        tool_name=request.tool_name,
        arguments=request.arguments,
        calling_layer="direct_api"
    )

    return MCPToolCallResponse(
        content=result.get("content", ""),
        success=result.get("success", False),
        error=result.get("error"),
        duration_ms=result.get("duration_ms")
    )


@router.post("/shutdown")
async def mcp_shutdown():
    """Shutdown the MCP orchestrator and disconnect from the server."""
    global _orchestrator
    if _orchestrator:
        await _orchestrator.shutdown()
        _orchestrator = None
    return {"message": "MCP orchestrator shut down"}


@router.get("/resources/templates")
async def list_mcp_resource_templates():
    """List available MCP resource templates."""
    try:
        orchestrator = await get_orchestrator()
        templates = await orchestrator.mcp_client.list_resource_templates()
        return {
            "templates": templates,
            "count": len(templates)
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/resource")
async def read_mcp_resource(uri: str):
    """
    Read a specific MCP resource by URI.
    Useful for direct monitoring of process logs in the UI.
    """
    try:
        orchestrator = await get_orchestrator()
        result = await orchestrator.mcp_client.read_resource(uri)
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to read resource"))
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
