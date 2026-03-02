"""
Inline Code Completion API — real-time ghost text as you type.

This is what makes an IDE feel magical. Sub-200ms suggestions
that appear as ghost text while you type.

Strategy:
  1. Local pattern matching (instant, <5ms) — common patterns
  2. Context-aware completion via fast model (<200ms)
  3. Full LLM completion as fallback (<2s)

The frontend sends cursor position + surrounding code.
We return the completion to display as ghost text.
"""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import json
import re
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/complete", tags=["Code Completion"])


# ── Common patterns for instant completion (<5ms) ───────────────

PYTHON_PATTERNS = {
    "def ": "function_name(self):\n    pass",
    "class ": "ClassName:\n    def __init__(self):\n        pass",
    "if __name__": " == \"__main__\":\n    main()",
    "import ": "",
    "from ": " import ",
    "    return ": "",
    "    raise ": "ValueError(\"\")",
    "try:": "\n        pass\n    except Exception as e:\n        pass",
    "with open(": "\"file.txt\", \"r\") as f:\n        content = f.read()",
    "for ": "item in items:\n        pass",
    "while ": "True:\n        break",
    "async def ": "function_name():\n    pass",
    "await ": "",
    "print(f\"": "",
    "logger.": "info(\"\")",
    "self.": "",
    "    assert ": "",
    "except ": "Exception as e:\n        logger.error(f\"Error: {e}\")",
    "@router.": "get(\"/\")\nasync def endpoint():\n    return {}",
    "@app.": "get(\"/\")\nasync def endpoint():\n    return {}",
}

JS_PATTERNS = {
    "const ": "name = ",
    "function ": "name() {\n  \n}",
    "async function ": "name() {\n  \n}",
    "export default ": "function Component() {\n  return <div></div>\n}",
    "import ": "{ } from ''",
    "useState(": "initialValue)",
    "useEffect(": "() => {\n  \n}, [])",
    "console.log(": ")",
    "fetch(": "url, { method: 'GET' })",
    "return (": "\n    <div>\n    </div>\n  )",
    "onClick={": "() => {}}",
    "style={{": "}}",
    "className=\"": "\"",
}


@router.post("/inline")
async def inline_completion(request: Request):
    """
    Fast inline completion.
    Input: { code_before, code_after, language, file_path }
    Output: { completion, source, latency_ms }
    """
    body = await request.json()
    code_before = body.get("code_before", "")
    code_after = body.get("code_after", "")
    language = body.get("language", "python")
    file_path = body.get("file_path", "")

    start = time.time()

    # Level 1: Pattern matching (<5ms)
    completion = _pattern_match(code_before, language)
    if completion:
        return {
            "completion": completion,
            "source": "pattern",
            "latency_ms": round((time.time() - start) * 1000, 1),
        }

    # Level 2: Context-aware via fast endpoint
    last_line = code_before.split("\n")[-1] if code_before else ""
    if len(last_line.strip()) < 3:
        return {"completion": "", "source": "too_short", "latency_ms": 0}

    try:
        from core.independent_models import run_with_failover
        prompt = (
            f"Complete this {language} code. Return ONLY the completion (1-3 lines max), "
            f"no explanation, no markdown:\n\n"
            f"```{language}\n{code_before[-500:]}"
        )
        result = run_with_failover(
            prompt,
            preferred_order=["qwen", "reasoning", "kimi"],
            system_prompt="You are a code completion engine. Return ONLY code. No markdown. No explanation.",
        )
        if result.get("response"):
            completion = result["response"].strip()
            # Clean up — remove markdown fences
            completion = re.sub(r'^```\w*\n?', '', completion)
            completion = re.sub(r'\n?```$', '', completion)
            completion = completion.strip()
            # Limit to 3 lines
            lines = completion.split("\n")[:3]
            completion = "\n".join(lines)

            return {
                "completion": completion,
                "source": f"model:{result.get('model', '?')}",
                "latency_ms": round((time.time() - start) * 1000, 1),
            }
    except Exception as e:
        logger.debug(f"Completion error: {e}")

    return {"completion": "", "source": "none", "latency_ms": round((time.time() - start) * 1000, 1)}


@router.post("/stream")
async def stream_completion(request: Request):
    """Stream completion token by token for longer suggestions."""
    body = await request.json()
    code_before = body.get("code_before", "")
    language = body.get("language", "python")

    async def generate():
        try:
            from settings import settings
            prompt = f"Complete this {language} code:\n```{language}\n{code_before[-500:]}"

            if settings.KIMI_API_KEY:
                import requests
                url = f"{settings.KIMI_BASE_URL}/chat/completions"
                headers = {"Authorization": f"Bearer {settings.KIMI_API_KEY}", "Content-Type": "application/json"}
                payload = {
                    "model": settings.KIMI_MODEL,
                    "messages": [
                        {"role": "system", "content": "Complete the code. Return ONLY code."},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": True, "max_tokens": 200,
                }
                with requests.post(url, headers=headers, json=payload, stream=True, timeout=30) as resp:
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        line = line.decode("utf-8")
                        if line.startswith("data: ") and line[6:] != "[DONE]":
                            try:
                                chunk = json.loads(line[6:])
                                token = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if token:
                                    yield f"data: {json.dumps({'token': token})}\n\n"
                            except Exception:
                                pass
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


def _pattern_match(code_before: str, language: str) -> str:
    """Instant pattern matching for common code patterns."""
    if not code_before:
        return ""

    last_line = code_before.split("\n")[-1].strip()
    patterns = PYTHON_PATTERNS if language == "python" else JS_PATTERNS

    for prefix, completion in patterns.items():
        if last_line.endswith(prefix) or last_line == prefix.strip():
            return completion

    # Bracket/quote auto-close
    if last_line.endswith("("):
        return ")"
    if last_line.endswith("["):
        return "]"
    if last_line.endswith("{"):
        return "}"

    return ""
