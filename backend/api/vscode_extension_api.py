"""
VSCode Extension API Shim

Maps the extension's expected API paths to the existing backend services.
All routes under /api/* are consumed by the grace-os-vscode extension.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["VSCode Extension"])


# ── Request/Response Models ──

class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None

class MemoryQueryRequest(BaseModel):
    query: str
    limit: int = 20
    memoryTypes: Optional[List[str]] = None
    filters: Optional[Dict[str, Any]] = None

class MemoryStoreRequest(BaseModel):
    content: str
    memory_type: str = "learning"
    metadata: Optional[Dict[str, Any]] = None

class MagmaIngestRequest(BaseModel):
    content: str
    source_type: str = "code"
    metadata: Optional[Dict[str, Any]] = None

class GenesisKeyCreateRequest(BaseModel):
    type: str
    entityId: str
    metadata: Optional[Dict[str, Any]] = None

class CognitiveAnalyzeRequest(BaseModel):
    code: str
    language: str = "python"
    context: Optional[Dict[str, Any]] = None

class CognitiveExplainRequest(BaseModel):
    code: str
    language: str = "python"

class LearningRecordRequest(BaseModel):
    content: str
    category: str = "insight"
    metadata: Optional[Dict[str, Any]] = None

class LibrarianSearchRequest(BaseModel):
    query: str
    filters: Optional[Dict[str, Any]] = None

class LibrarianTagRequest(BaseModel):
    file_path: str
    tags: List[str]


# ── Chat ──

@router.post("/chat")
async def vscode_chat(req: ChatRequest):
    """Chat endpoint for the VSCode extension."""
    try:
        from llm_orchestrator.factory import get_llm_client
        from utils.rag_prompt import build_rag_prompt

        prompt = build_rag_prompt(req.message, req.context.get("surroundingCode", "") if req.context else "")
        client = get_llm_client()
        response = client.generate(prompt=prompt)

        return {
            "role": "assistant",
            "content": response if isinstance(response, str) else str(response),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"[VSCODE-API] Chat error: {e}")
        return {"role": "assistant", "content": f"Error: {e}", "timestamp": datetime.now(timezone.utc).isoformat()}


# ── Streaming Chat (SSE) ──

@router.post("/streaming/chat")
async def vscode_streaming_chat(req: ChatRequest):
    """Streaming chat endpoint (SSE) for the VSCode extension."""
    from fastapi.responses import StreamingResponse
    import json

    async def generate():
        try:
            from llm_orchestrator.factory import get_llm_client
            from utils.rag_prompt import build_rag_prompt

            prompt = build_rag_prompt(req.message, req.context.get("surroundingCode", "") if req.context else "")
            client = get_llm_client()
            response = client.generate(prompt=prompt)
            text = response if isinstance(response, str) else str(response)

            chunk_size = 50
            for i in range(0, len(text), chunk_size):
                yield f"data: {json.dumps({'content': text[i:i+chunk_size], 'done': False})}\n\n"

            yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'content': f'Error: {e}', 'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ── Memory ──

@router.post("/memory/query")
async def vscode_memory_query(req: MemoryQueryRequest):
    """Query memory mesh."""
    try:
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()
        results = mem.search_all(req.query, top_k=req.limit)

        entries = []
        if isinstance(results, dict):
            for sys_name, items in results.items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            entries.append({
                                "id": item.get("id", ""),
                                "content": item.get("content", item.get("expected", item.get("input", str(item)))),
                                "memoryType": sys_name,
                                "timestamp": item.get("created_at", datetime.now(timezone.utc).isoformat()),
                                "score": item.get("trust", 0.5),
                            })
        return entries[:req.limit]
    except Exception as e:
        logger.error(f"[VSCODE-API] Memory query error: {e}")
        return []


@router.post("/memory/store")
async def vscode_memory_store(req: MemoryStoreRequest):
    """Store to unified memory."""
    try:
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()
        mem.store_learning(
            input_ctx=req.content[:500],
            expected=req.content,
            trust=0.7,
            source=f"vscode:{req.memory_type}",
        )
        return {
            "id": f"mem_{int(datetime.now(timezone.utc).timestamp())}",
            "content": req.content[:500],
            "memoryType": req.memory_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


@router.post("/magma/consolidate")
async def vscode_magma_consolidate():
    """Trigger memory consolidation."""
    try:
        from cognitive.memory_reconciler import get_reconciler
        result = get_reconciler().reconcile()
        return {"status": "ok", "changes": result.get("changes", 0)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.post("/magma/ingest")
async def vscode_magma_ingest(req: MagmaIngestRequest):
    """Ingest content to memory."""
    try:
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()
        mem.store_learning(
            input_ctx=f"{req.source_type}:{(req.metadata or {}).get('filePath', 'unknown')}",
            expected=req.content[:5000],
            trust=0.7,
            source=f"vscode_ingest:{req.source_type}",
        )
        return {"status": "ok", "ingested": True}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── Genesis Keys ──

@router.post("/genesis/keys")
async def vscode_genesis_create(req: GenesisKeyCreateRequest):
    """Create a genesis key."""
    try:
        from api._genesis_tracker import track
        key = track(
            key_type="code_change",
            what=f"VSCode genesis key: {req.type} on {req.entityId}",
            how="vscode_extension",
            input_data=req.metadata,
            tags=["vscode", req.type],
        )
        key_id = key if isinstance(key, str) and key else ""
        return {
            "id": key_id or f"gk_{int(datetime.now(timezone.utc).timestamp())}",
            "type": req.type,
            "entityId": req.entityId,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "hash": "",
            "metadata": req.metadata,
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/genesis/lineage")
async def vscode_genesis_lineage(
    filePath: Optional[str] = Query(None),
    lineNumber: Optional[int] = Query(None),
):
    """Get code lineage (genesis keys for a file/line)."""
    try:
        from database.session import session_scope
        from models.genesis_key_models import GenesisKey
        from sqlalchemy import desc

        with session_scope() as session:
            query = session.query(GenesisKey).order_by(desc(GenesisKey.when_timestamp))
            if filePath:
                query = query.filter(GenesisKey.file_path.contains(filePath.split("\\")[-1].split("/")[-1]))
            keys = query.limit(20).all()

            return [
                {
                    "id": str(k.id),
                    "type": str(k.key_type.value) if hasattr(k.key_type, 'value') else str(k.key_type),
                    "entityId": k.file_path or "",
                    "parentKey": None,
                    "timestamp": k.when_timestamp.isoformat() if k.when_timestamp else "",
                    "hash": "",
                    "metadata": {
                        "description": k.what_description,
                        "filePath": k.file_path,
                    },
                }
                for k in keys
            ]
    except Exception as e:
        logger.error(f"[VSCODE-API] Lineage error: {e}")
        return []


# ── Diagnostics ──

@router.post("/diagnostics/run")
async def vscode_diagnostics_run():
    """Run system diagnostics."""
    try:
        from cognitive.autonomous_diagnostics import get_diagnostics
        diag = get_diagnostics()
        result = diag.run_quick_check() if hasattr(diag, 'run_quick_check') else diag.get_status()

        results = []
        if isinstance(result, dict):
            for component, status in result.items():
                if isinstance(status, dict):
                    results.append({
                        "status": status.get("status", "healthy"),
                        "layer": "sensors",
                        "message": f"{component}: {status.get('message', 'OK')}",
                        "details": status,
                    })
                else:
                    results.append({
                        "status": "healthy" if status else "error",
                        "layer": "sensors",
                        "message": f"{component}: {status}",
                    })

        if not results:
            results = [{"status": "healthy", "layer": "sensors", "message": "All systems operational"}]

        return results
    except Exception as e:
        return [{"status": "error", "layer": "sensors", "message": f"Diagnostic error: {e}"}]


@router.get("/diagnostics/health")
async def vscode_diagnostics_health():
    """Get system health summary."""
    try:
        from cognitive.ghost_memory import get_ghost_memory
        ghost = get_ghost_memory()

        return {
            "status": "healthy",
            "uptime": "running",
            "components": {
                "ghost_memory": "active" if ghost._task_id or ghost._cache else "idle",
                "database": "connected",
                "llm": "available",
            },
            "metrics": {
                "ghost_cache_size": len(ghost._cache),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


# ── Cognitive ──

@router.post("/cognitive/analyze")
async def vscode_cognitive_analyze(req: CognitiveAnalyzeRequest):
    """Analyze code using LLM."""
    try:
        from llm_orchestrator.factory import get_llm_for_task
        client = get_llm_for_task("code")

        prompt = f"Analyze this {req.language} code. Identify patterns, potential issues, and suggest improvements:\n\n```{req.language}\n{req.code}\n```"
        response = client.generate(prompt=prompt)

        return {
            "analysis": response if isinstance(response, str) else str(response),
            "patterns": [],
            "suggestions": [],
            "confidence": 0.8,
        }
    except Exception as e:
        return {"analysis": f"Analysis error: {e}", "patterns": [], "suggestions": [], "confidence": 0.0}


@router.post("/cognitive/explain")
async def vscode_cognitive_explain(req: CognitiveExplainRequest):
    """Explain code using LLM."""
    try:
        from llm_orchestrator.factory import get_llm_for_task
        client = get_llm_for_task("reason")

        prompt = f"Explain this {req.language} code clearly and concisely. Cover what it does, how it works, and any notable patterns:\n\n```{req.language}\n{req.code}\n```"
        response = client.generate(prompt=prompt)

        return response if isinstance(response, str) else str(response)
    except Exception as e:
        return f"Explanation error: {e}"


@router.post("/cognitive/refactor")
async def vscode_cognitive_refactor(req: CognitiveExplainRequest):
    """Suggest refactoring for code."""
    try:
        from llm_orchestrator.factory import get_llm_for_task
        client = get_llm_for_task("code")

        prompt = f"Suggest refactoring improvements for this {req.language} code. Provide the refactored version and explain your changes:\n\n```{req.language}\n{req.code}\n```\n\nReturn your response in this format:\nREFACTORED CODE:\n```\n<code>\n```\nSUGGESTIONS:\n- <suggestion 1>\n- <suggestion 2>"
        response = client.generate(prompt=prompt)
        text = response if isinstance(response, str) else str(response)

        return {
            "refactored_code": text,
            "suggestions": [],
        }
    except Exception as e:
        return {"refactored_code": None, "suggestions": [f"Error: {e}"]}


# ── Learning ──

@router.post("/learning/record")
async def vscode_learning_record(req: LearningRecordRequest):
    """Record a learning insight."""
    try:
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()
        mem.store_learning(
            input_ctx=f"insight:{req.category}",
            expected=req.content,
            trust=0.7,
            source="vscode_learning",
        )
        return {
            "id": f"learn_{int(datetime.now(timezone.utc).timestamp())}",
            "content": req.content,
            "category": req.category,
            "trustScore": 0.7,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/learning/history")
async def vscode_learning_history(limit: int = Query(20)):
    """Get learning history."""
    try:
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()
        stats = mem.get_stats()

        entries = []
        learnings = stats.get("learnings", {})
        if isinstance(learnings, dict):
            count = learnings.get("count", 0)
            entries.append({
                "id": "summary",
                "content": f"Total learnings: {count}",
                "category": "summary",
                "trustScore": 0.8,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return entries[:limit]
    except Exception as e:
        return []


# ── Librarian ──

@router.post("/librarian/search")
async def vscode_librarian_search(req: LibrarianSearchRequest):
    """Search knowledge base."""
    try:
        from cognitive.unified_memory import get_unified_memory
        mem = get_unified_memory()
        results = mem.search_all(req.query, top_k=10)

        items = []
        if isinstance(results, dict):
            for sys_name, entries in results.items():
                if isinstance(entries, list):
                    for entry in entries:
                        if isinstance(entry, dict):
                            items.append({
                                "title": entry.get("input", entry.get("content", ""))[:50],
                                "content": entry.get("expected", entry.get("content", str(entry)))[:500],
                                "source": sys_name,
                                "type": "knowledge",
                            })
        return items[:20]
    except Exception as e:
        return []


@router.post("/librarian/tag")
async def vscode_librarian_tag(req: LibrarianTagRequest):
    """Tag a file in the knowledge base."""
    try:
        from api._genesis_tracker import track
        track(
            key_type="user_action",
            what=f"Tagged file: {req.file_path} with {req.tags}",
            how="vscode_librarian",
            tags=["librarian", "tag"] + req.tags,
        )
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ── WebSocket for VSCode extension ──

from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json

@router.websocket("/ws/grace")
async def vscode_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time VSCode extension communication."""
    await websocket.accept()
    logger.info("[VSCODE-WS] Extension connected")

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=35.0)
                message = json.loads(data)
                msg_type = message.get("type", "")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "payload": {}, "timestamp": datetime.now(timezone.utc).isoformat()})

                elif msg_type == "chat":
                    payload = message.get("payload", {})
                    content = payload.get("content", "")

                    try:
                        from llm_orchestrator.factory import get_llm_client
                        from utils.rag_prompt import build_rag_prompt

                        prompt = build_rag_prompt(content)
                        client = get_llm_client()
                        response = client.generate(prompt=prompt)
                        text = response if isinstance(response, str) else str(response)

                        chunk_size = 50
                        for i in range(0, len(text), chunk_size):
                            await websocket.send_json({
                                "type": "stream_chunk",
                                "payload": {"content": text[i:i+chunk_size], "done": False},
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })

                        await websocket.send_json({
                            "type": "stream_end",
                            "payload": {"content": "", "done": True},
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "stream_chunk",
                            "payload": {"content": f"Error: {e}", "done": True},
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        })

                elif msg_type == "subscribe":
                    await websocket.send_json({
                        "type": "notification",
                        "payload": {"level": "info", "title": "Subscribed", "message": "Connected to Grace backend"},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({
                        "type": "health_update",
                        "payload": {"status": "healthy"},
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info("[VSCODE-WS] Extension disconnected")
    except Exception as e:
        logger.error(f"[VSCODE-WS] Error: {e}")
