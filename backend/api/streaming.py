"""
Streaming Chat API
==================
Server-Sent Events (SSE) streaming for real-time chat responses.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, AsyncGenerator
import json
import asyncio

from database.session import get_session
from models.repositories import ChatRepository, ChatHistoryRepository

try:
    from settings import settings
except ImportError:
    settings = None

router = APIRouter(prefix="/stream", tags=["Streaming"])


class StreamChatRequest(BaseModel):
    """Request model for streaming chat."""
    message: str = Field(..., description="User message")
    chat_id: Optional[int] = Field(None, description="Chat ID for context")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0)
    include_sources: Optional[bool] = Field(True, description="Include RAG sources")


class StreamEvent(BaseModel):
    """SSE event structure."""
    event: str  # "token", "sources", "done", "error"
    data: str


async def generate_stream(
    message: str,
    chat_id: Optional[int] = None,
    temperature: float = 0.7,
    include_sources: bool = True,
    session=None
) -> AsyncGenerator[str, None]:
    """
    Generate streaming response using SSE format.

    Yields:
        SSE formatted strings: "event: <type>\ndata: <json>\n\n"
    """
    try:
        from llm_orchestrator.factory import get_llm_client
        client = get_llm_client()

        if not client.is_running():
            provider_name = settings.LLM_PROVIDER.upper() if settings else "LLM"
            yield f"event: error\ndata: {json.dumps({'error': f'{provider_name} service not responding'})}\n\n"
            return

        model_name = settings.LLM_MODEL if settings else "gpt-4o"

        # HIA honesty check — send disclaimer event if no sources found
        # Governance check on final output happens post-stream

        # RAG retrieval for context (trust-aware when available)
        rag_context = ""
        sources = []

        try:
            from retrieval.trust_aware_retriever import TrustAwareDocumentRetriever
            from api.retrieve import get_document_retriever
            base_retriever = get_document_retriever()
            try:
                retriever = TrustAwareDocumentRetriever(base_retriever=base_retriever)
            except Exception:
                retriever = base_retriever

            retrieval_result = retriever.retrieve(
                query=message,
                limit=5,
                score_threshold=0.3,
                include_metadata=True
            )

            if retrieval_result:
                context_parts = []
                for i, chunk in enumerate(retrieval_result[:5]):
                    text = chunk.get("text", chunk.get("content", ""))
                    score = chunk.get("score", 0)
                    metadata = chunk.get("metadata", {})

                    context_parts.append(f"[Source {i+1}]: {text[:500]}")
                    sources.append({
                        "index": i + 1,
                        "text": text[:200] + "..." if len(text) > 200 else text,
                        "score": round(score, 3),
                        "file": metadata.get("file_path", "unknown")
                    })

                rag_context = "\n\n".join(context_parts)
        except Exception as e:
            print(f"[STREAM] RAG retrieval error: {e}")

        # Send sources first if available
        if include_sources and sources:
            yield f"event: sources\ndata: {json.dumps({'sources': sources})}\n\n"

        # Build prompt with RAG context
        if rag_context:
            system_prompt = """You are GRACE, an AI assistant. Answer based ONLY on the provided context.
If the context doesn't contain relevant information, say so clearly.
Always cite your sources by number [Source N]."""

            full_prompt = f"""Context from knowledge base:
{rag_context}

User question: {message}

Provide a helpful answer based on the context above:"""
        else:
            system_prompt = "You are GRACE, an AI assistant."
            full_prompt = message

            # Notify no sources found
            yield f"event: sources\ndata: {json.dumps({'sources': [], 'note': 'No relevant sources found'})}\n\n"

        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt}
        ]

        # Use unified streaming interface
        response_text = ""
        try:
            stream_gen = client.chat(
                messages=messages,
                model=model_name,
                stream=True,
                temperature=temperature
            )

            # Handle different stream response types (Requests vs native generator)
            if hasattr(stream_gen, "iter_lines"):
                # OpenAI/Requests style streaming
                for line in stream_gen.iter_lines():
                    if line:
                        line_text = line.decode('utf-8')
                        if line_text.startswith("data: "):
                            data_str = line_text[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk_json = json.loads(data_str)
                                if "choices" in chunk_json and len(chunk_json["choices"]) > 0:
                                    token = chunk_json["choices"][0].get("delta", {}).get("content", "")
                                    if token:
                                        response_text += token
                                        yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
                            except Exception:
                                continue
            else:
                # Ollama/Native generator style
                for chunk in stream_gen:
                    # Native Ollama adapter handles format, returns chunk dict
                    if isinstance(chunk, dict) and "message" in chunk:
                        token = chunk["message"].get("content", "")
                        if token:
                            response_text += token
                            yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"
                    elif isinstance(chunk, str):
                        # Raw string chunk fallback
                        response_text += chunk
                        yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"
                    
                    await asyncio.sleep(0)

        except Exception as stream_error:
            # Fallback to non-streaming
            print(f"[STREAM] Streaming failed, using fallback: {stream_error}")
            response = client.generate(
                prompt=full_prompt,
                model_id=model_name,
                temperature=temperature,
                stream=False
            )
            response_text = response if isinstance(response, str) else str(response)
            # Send as single token
            yield f"event: token\ndata: {json.dumps({'token': response_text})}\n\n"

        # Save to chat history if chat_id provided
        if chat_id and session:
            try:
                history_repo = ChatHistoryRepository(session)
                history_repo.add_message(chat_id=chat_id, role="user", content=message)
                history_repo.add_message(chat_id=chat_id, role="assistant", content=response_text)
            except Exception as save_error:
                print(f"[STREAM] Failed to save history: {save_error}")

        # Feed to Kimi knowledge feedback loop
        try:
            from cognitive.kimi_knowledge_feedback import get_kimi_feedback
            if len(response_text) >= 200:
                get_kimi_feedback().feed_answer(
                    question=message, answer=response_text,
                    confidence=0.6, tier_used="streaming",
                )
        except Exception:
            pass

        # Send completion event
        yield f"event: done\ndata: {json.dumps({'status': 'complete', 'total_length': len(response_text)})}\n\n"

    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"


@router.post("/chat")
async def stream_chat(request: StreamChatRequest, session=Depends(get_session)):
    """
    Stream chat response using Server-Sent Events (SSE).

    Events:
    - sources: RAG sources used for context
    - token: Individual response tokens
    - done: Stream complete
    - error: Error occurred

    Example client usage:
    ```javascript
    const eventSource = new EventSource('/stream/chat', {
        method: 'POST',
        body: JSON.stringify({ message: 'Hello' })
    });

    eventSource.addEventListener('token', (e) => {
        const data = JSON.parse(e.data);
        appendToResponse(data.token);
    });
    ```
    """
    return StreamingResponse(
        generate_stream(
            message=request.message,
            chat_id=request.chat_id,
            temperature=request.temperature,
            include_sources=request.include_sources,
            session=session
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.get("/health")
async def stream_health():
    """Health check for streaming endpoint."""
    return {"status": "ok", "streaming": True}
