"""
Streaming API — Server-Sent Events for token-by-token LLM responses.
Replaces batch consensus with real-time streaming.
"""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import logging
import time

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stream", tags=["Streaming"])


def _stream_rag_and_memory_context(prompt: str) -> str:
    """Unified spine: RAG + episodic recall for stream. Returns prefix string for prompt."""
    try:
        from core.services.chat_service import _get_rag_context, _get_episodic_recall
        rag = _get_rag_context(prompt, limit=5, score_threshold=0.3)
        episode = _get_episodic_recall(prompt, k=3, min_trust=0.5)
        parts = []
        if rag:
            parts.append("Relevant context from the knowledge base:\n" + rag)
        if episode:
            parts.append("Relevant past experience:\n" + episode)
        if parts:
            return "\n\n".join(parts) + "\n\n---\n\nUser: " + prompt
        return prompt
    except Exception:
        return prompt


@router.post("/chat")
async def stream_chat(request: Request):
    """Stream LLM response token-by-token via SSE. Supports use_rag + chat_id for unified RAG+memory context."""
    body = await request.json()
    prompt = body.get("prompt", body.get("message", ""))
    model = body.get("model", "kimi")
    context_files = body.get("context_files", [])
    mentions = body.get("mentions", [])
    use_rag = body.get("use_rag", False)
    chat_id = body.get("chat_id")

    async def generate():
        # Build context from @ mentions
        file_context = ""
        if mentions or context_files:
            file_context = _resolve_mentions(mentions + context_files)

        full_prompt = prompt
        if file_context:
            full_prompt = f"{file_context}\n\n{full_prompt}"
        if use_rag:
            full_prompt = _stream_rag_and_memory_context(full_prompt)

        # Track user input as learnable
        try:
            from api._genesis_tracker import track
            track(key_type="user_input", what=f"Stream chat: {prompt[:100]}",
                  who="stream_api", input_data={"prompt": prompt[:500], "model": model, "mentions": mentions, "use_rag": use_rag, "chat_id": chat_id},
                  tags=["user_input", "stream", "chat"])
        except Exception:
            pass

        try:
            from settings import settings

            if model in ("kimi", "consensus"):
                for chunk in _stream_kimi(full_prompt, settings):
                    yield chunk
            elif model == "opus":
                for chunk in _stream_opus(full_prompt, settings):
                    yield chunk
            else:
                for chunk in _stream_ollama(full_prompt, model, settings):
                    yield chunk

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/complete")
async def stream_completion(request: Request):
    """Inline code completion — fast, single-model, context-aware."""
    body = await request.json()
    code_before = body.get("code_before", "")
    code_after = body.get("code_after", "")
    file_path = body.get("file_path", "")
    language = body.get("language", "python")

    prompt = (
        f"Complete the code. Return ONLY the completion, no explanation.\n"
        f"Language: {language}\nFile: {file_path}\n\n"
        f"```{language}\n{code_before}"
    )

    async def generate():
        try:
            from settings import settings
            # Use fastest available model for completion
            if settings.OLLAMA_MODEL_CODE:
                for chunk in _stream_ollama(prompt, "code", settings):
                    yield chunk
            elif settings.KIMI_API_KEY:
                for chunk in _stream_kimi(prompt, settings):
                    yield chunk
            else:
                yield f"data: {json.dumps({'token': '# No model available'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


def _resolve_mentions(mentions: list) -> str:
    """Resolve @file, @symbol, @folder mentions into context."""
    context_parts = []
    for mention in mentions:
        if not mention:
            continue
        mention = mention.lstrip("@").strip()

        # @file:path — include file content
        if "/" in mention or "." in mention:
            try:
                from core.services.files_service import read
                result = read(mention)
                if isinstance(result, dict) and result.get("content"):
                    context_parts.append(f"--- File: {mention} ---\n{result['content'][:5000]}")
            except Exception:
                try:
                    from core.services.code_service import read_file
                    result = read_file(mention)
                    if isinstance(result, dict) and result.get("content"):
                        context_parts.append(f"--- File: {mention} ---\n{result['content'][:5000]}")
                except Exception:
                    pass
        else:
            # @symbol — search for it
            try:
                from core.services.files_service import search
                result = search(mention, limit=3)
                if result.get("results"):
                    for r in result["results"]:
                        context_parts.append(f"--- Found in: {r.get('path', '?')} ---")
            except Exception:
                pass

    return "\n\n".join(context_parts)


@router.post("/chat/send")
async def stream_chat_send(request: Request):
    """
    Stream a full chat turn via SSE: saves user msg, streams LLM response token-by-token,
    saves assistant msg. Uses Ollama /api/chat for multi-turn with RAG + memory context.

    Body: { chat_id: int, message: str, use_rag?: bool }
    SSE events: data: {"token":"..."} ... data: {"done":true,"chat_id":...,"message":"..."} ... data: [DONE]
    """
    body = await request.json()
    chat_id = body.get("chat_id")
    message = body.get("message", "")
    use_rag = body.get("use_rag", True)

    if not chat_id or not message.strip():
        return StreamingResponse(
            iter([f'data: {json.dumps({"error": "chat_id and message required"})}\n\n', "data: [DONE]\n\n"]),
            media_type="text/event-stream",
        )

    async def generate():
        import requests as _requests
        from database.session import get_session_factory
        from models.repositories import ChatRepository, ChatHistoryRepository
        from settings import settings

        factory = get_session_factory()
        session = factory()
        try:
            chat_repo = ChatRepository(session)
            history_repo = ChatHistoryRepository(session)
            chat = chat_repo.get(chat_id)
            if not chat:
                yield f'data: {json.dumps({"error": "Chat not found"})}\n\n'
                yield "data: [DONE]\n\n"
                return

            # Save user message
            history_repo.add_message(chat_id=chat_id, role="user", content=message)
            session.commit()

            # Build messages array with RAG + memory context
            rag_ctx = ""
            episode_ctx = ""
            if use_rag:
                from core.services.chat_service import _get_rag_context, _get_episodic_recall
                rag_ctx = _get_rag_context(message, limit=5, score_threshold=0.3)
                episode_ctx = _get_episodic_recall(message, k=3, min_trust=0.5)

            system_parts = ["You are Grace, a helpful AI assistant."]
            if rag_ctx:
                system_parts.append("Relevant context from the knowledge base:\n" + rag_ctx)
            if episode_ctx:
                system_parts.append("Relevant past experience (use when helpful):\n" + episode_ctx)

            # Governance prefix
            try:
                from llm_orchestrator.governance_wrapper import build_governance_prefix
                gov = build_governance_prefix()
                if gov:
                    system_parts.append(gov)
            except Exception:
                pass

            system_content = "\n\n".join(system_parts)

            # Recent history for multi-turn
            recent = history_repo.get_by_chat_reverse(chat_id, skip=0, limit=10)
            messages_list = [{"role": "system", "content": system_content}]
            for m in reversed(recent):
                messages_list.append({"role": m.role, "content": m.content or ""})

            model = chat.model or settings.OLLAMA_LLM_DEFAULT or "qwen3:14b"
            temperature = chat.temperature or 0.7

            # Stream from Ollama /api/chat
            url = f"{settings.OLLAMA_URL}/api/chat"
            payload = {
                "model": model,
                "messages": messages_list,
                "stream": True,
                "options": {"temperature": temperature},
            }

            full_response = ""
            start = time.time()
            try:
                with _requests.post(url, json=payload, stream=True, timeout=300) as resp:
                    if resp.status_code != 200:
                        yield f'data: {json.dumps({"error": f"Ollama returned {resp.status_code}"})}\n\n'
                        yield "data: [DONE]\n\n"
                        return
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                full_response += token
                                yield f"data: {json.dumps({'token': token})}\n\n"
                            if chunk.get("done"):
                                break
                        except Exception:
                            pass
            except _requests.ConnectionError:
                yield f'data: {json.dumps({"error": "Cannot connect to Ollama. Is it running?"})}\n\n'
                yield "data: [DONE]\n\n"
                return

            gen_time = round(time.time() - start, 2)

            # Save assistant message
            history_repo.add_message(chat_id=chat_id, role="assistant", content=full_response)
            session.commit()

            # Final metadata event
            yield f'data: {json.dumps({"done": True, "chat_id": chat_id, "message": full_response, "model": model, "generation_time": gen_time, "used_rag": bool(rag_ctx), "used_memory": bool(episode_ctx)})}\n\n'
            yield "data: [DONE]\n\n"

        except Exception as e:
            session.rollback()
            logger.exception("stream_chat_send error")
            yield f'data: {json.dumps({"error": str(e)[:300]})}\n\n'
            yield "data: [DONE]\n\n"
        finally:
            session.close()

    return StreamingResponse(generate(), media_type="text/event-stream")


def _stream_kimi(prompt: str, settings):
    """Stream from Kimi API."""
    import requests
    url = f"{settings.KIMI_BASE_URL}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.KIMI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": settings.KIMI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "max_tokens": 4096,
    }

    with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as resp:
        for line in resp.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield f"data: {json.dumps({'token': token})}\n\n"
                except Exception:
                    pass


def _stream_opus(prompt: str, settings):
    """Stream from Anthropic/Opus API."""
    import requests
    url = f"{settings.OPUS_BASE_URL}/messages"
    headers = {
        "x-api-key": settings.OPUS_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": settings.OPUS_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4096,
        "stream": True,
    }

    with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as resp:
        for line in resp.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data = line[6:]
                try:
                    chunk = json.loads(data)
                    if chunk.get("type") == "content_block_delta":
                        token = chunk.get("delta", {}).get("text", "")
                        if token:
                            yield f"data: {json.dumps({'token': token})}\n\n"
                except Exception:
                    pass


def _stream_ollama(prompt: str, task: str, settings):
    """Stream from Ollama."""
    import requests
    model = settings.OLLAMA_MODEL_CODE if task == "code" else settings.OLLAMA_MODEL_REASON
    url = f"{settings.OLLAMA_URL}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": True}

    with requests.post(url, json=payload, stream=True, timeout=120) as resp:
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
                token = chunk.get("response", "")
                if token:
                    yield f"data: {json.dumps({'token': token})}\n\n"
                if chunk.get("done"):
                    break
            except Exception:
                pass
