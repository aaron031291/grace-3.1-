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


@router.post("/chat")
async def stream_chat(request: Request):
    """Stream LLM response token-by-token via SSE."""
    body = await request.json()
    prompt = body.get("prompt", body.get("message", ""))
    model = body.get("model", "kimi")
    context_files = body.get("context_files", [])
    mentions = body.get("mentions", [])

    async def generate():
        # Build context from @ mentions
        file_context = ""
        if mentions or context_files:
            file_context = _resolve_mentions(mentions + context_files)

        full_prompt = f"{file_context}\n\n{prompt}" if file_context else prompt

        # Track user input as learnable
        try:
            from api._genesis_tracker import track
            track(key_type="user_input", what=f"Stream chat: {prompt[:100]}",
                  who="stream_api", input_data={"prompt": prompt[:500], "model": model, "mentions": mentions},
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
