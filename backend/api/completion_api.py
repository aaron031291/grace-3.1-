"""
Inline Code Completion API — real-time ghost text as you type.

This is what makes an IDE feel magical. Sub-200ms suggestions
that appear as ghost text while you type.

Strategy (4 levels):
  1. Bracket/quote auto-close (instant, <1ms)
  2. Pattern matching (instant, <5ms) — 80+ patterns across 8 languages
  3. Context-aware completion via cached + fast model (<200ms)
  4. Full LLM streaming completion as fallback (<2s)

The frontend sends cursor position + surrounding code.
We return the completion to display as ghost text.
"""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import json
import re
import time
import hashlib
import logging
import threading
from typing import Optional, Dict, List
from collections import OrderedDict

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/complete", tags=["Code Completion"])


# ── Completion cache (avoid re-calling LLM for same prefix) ─────

class CompletionCache:
    """LRU cache for recent completions — keyed by (language, last_lines_hash)."""

    def __init__(self, max_size: int = 256):
        self._max = max_size
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def _key(self, code_before: str, language: str) -> str:
        last_lines = "\n".join(code_before.split("\n")[-5:])
        raw = f"{language}:{last_lines}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, code_before: str, language: str) -> Optional[str]:
        k = self._key(code_before, language)
        with self._lock:
            if k in self._cache:
                self._cache.move_to_end(k)
                self.hits += 1
                return self._cache[k]
            self.misses += 1
            return None

    def put(self, code_before: str, language: str, completion: str):
        k = self._key(code_before, language)
        with self._lock:
            self._cache[k] = completion
            self._cache.move_to_end(k)
            if len(self._cache) > self._max:
                self._cache.popitem(last=False)

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {
            "size": len(self._cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": round(self.hits / max(total, 1), 3),
        }


_cache = CompletionCache()


# ── Language-specific patterns ──────────────────────────────────

PYTHON_PATTERNS = {
    "def ": "function_name(self):\n    pass",
    "class ": "ClassName:\n    def __init__(self):\n        pass",
    "if __name__": ' == "__main__":\n    main()',
    "from ": " import ",
    "    raise ": 'ValueError("")',
    "try:": "\n        pass\n    except Exception as e:\n        pass",
    'with open(': '"file.txt", "r") as f:\n        content = f.read()',
    "for ": "item in items:\n        pass",
    "while ": "True:\n        break",
    "async def ": "function_name():\n    pass",
    "print(f\"": "",
    "logger.": 'info("")',
    "except ": 'Exception as e:\n        logger.error(f"Error: {e}")',
    "@router.": 'get("/")\nasync def endpoint():\n    return {}',
    "@app.": 'get("/")\nasync def endpoint():\n    return {}',
    "@property": "\ndef name(self):\n    return self._name",
    "@staticmethod": "\ndef method():\n    pass",
    "@classmethod": "\ndef method(cls):\n    pass",
    "if not ": "",
    "elif ": "",
    "else:": "\n    pass",
    "yield ": "",
    "lambda ": "x: x",
    "assert ": "",
    "global ": "",
    "nonlocal ": "",
    "del ": "",
    "with ": "",
    "__init__": "(self):\n        pass",
    "super().__init__": "()",
    "self._": "",
    "isinstance(": "",
    "enumerate(": "",
    "zip(": "",
    "map(": "",
    "filter(": "",
    "sorted(": ", key=lambda x: x)",
    "defaultdict(": "list)",
    "dataclass": "\nclass DataClass:\n    name: str = \"\"\n    value: int = 0",
    "typing import": " List, Dict, Optional, Tuple, Any",
    "pathlib import": " Path",
    "datetime import": " datetime, timedelta",
    "collections import": " defaultdict, OrderedDict, deque",
    "json.dumps(": "data, indent=2)",
    "json.loads(": "text)",
    "os.path.": "join()",
    "os.environ.get(": '"KEY", "")',
}

JS_PATTERNS = {
    "const ": "name = ",
    "let ": "name = ",
    "function ": "name() {\n  \n}",
    "async function ": "name() {\n  \n}",
    "export default ": "function Component() {\n  return <div></div>\n}",
    "export const ": "Component = () => {\n  return <div></div>\n}",
    "import ": "{ } from ''",
    "useState(": "initialValue)",
    "useEffect(": "() => {\n  \n}, [])",
    "useCallback(": "() => {\n  \n}, [])",
    "useMemo(": "() => {\n  \n}, [])",
    "useRef(": "null)",
    "useContext(": ")",
    "console.log(": ")",
    "fetch(": "url, { method: 'GET' })",
    "return (": "\n    <div>\n    </div>\n  )",
    "onClick={": "() => {}}",
    "onChange={": "(e) => {}}",
    "style={{": "}}",
    'className="': '"',
    "try {": "\n  \n} catch (error) {\n  console.error(error)\n}",
    "async ": "() => {\n  \n}",
    "await ": "",
    "new Promise(": "(resolve, reject) => {\n  resolve()\n})",
    "Array.from(": ")",
    "Object.keys(": ")",
    "Object.entries(": ")",
    ".map(": "(item) => item)",
    ".filter(": "(item) => item)",
    ".reduce(": "(acc, item) => acc, initialValue)",
    ".forEach(": "(item) => {\n  \n})",
    "addEventListener(": "'click', (e) => {\n  \n})",
    "document.querySelector(": "'selector')",
    "JSON.stringify(": "data, null, 2)",
    "JSON.parse(": "text)",
    "setTimeout(": "() => {\n  \n}, 1000)",
    "setInterval(": "() => {\n  \n}, 1000)",
}

TS_PATTERNS = {
    **JS_PATTERNS,
    "interface ": "Props {\n  \n}",
    "type ": "Name = {\n  \n}",
    "enum ": "Name {\n  \n}",
    ": React.FC": "<Props> = () => {\n  return <div></div>\n}",
    "as const": "",
    "Record<": "string, any>",
    "Partial<": ">",
    "Required<": ">",
    "Omit<": ", ''>",
    "Pick<": ", ''>",
    "keyof ": "",
    "typeof ": "",
    "readonly ": "",
    "generic<T>": "",
}

CSS_PATTERNS = {
    "display: ": "flex;",
    "justify-content: ": "center;",
    "align-items: ": "center;",
    "flex-direction: ": "column;",
    "position: ": "relative;",
    "background-color: ": "#ffffff;",
    "color: ": "#333333;",
    "font-size: ": "16px;",
    "font-weight: ": "600;",
    "margin: ": "0 auto;",
    "padding: ": "16px;",
    "border-radius: ": "8px;",
    "box-shadow: ": "0 2px 8px rgba(0, 0, 0, 0.1);",
    "transition: ": "all 0.3s ease;",
    "grid-template-columns: ": "repeat(auto-fit, minmax(250px, 1fr));",
    "gap: ": "16px;",
    "overflow: ": "hidden;",
    "z-index: ": "10;",
    "opacity: ": "1;",
    "transform: ": "translateX(0);",
    "@media (": "max-width: 768px) {\n  \n}",
    ":hover": " {\n  \n}",
    "::before": " {\n  content: '';\n}",
    "::after": " {\n  content: '';\n}",
    "@keyframes ": "name {\n  from { }\n  to { }\n}",
    "var(--": ")",
}

HTML_PATTERNS = {
    "<div": ' className="">\n  \n</div>',
    "<span": ">\n</span>",
    "<button": ' onClick={}>\n  Click\n</button>',
    "<input": ' type="text" value="" onChange={} />',
    "<form": ' onSubmit={}>\n  \n</form>',
    "<a ": 'href="">\n</a>',
    "<img ": 'src="" alt="" />',
    "<ul": ">\n  <li></li>\n</ul>",
    "<table": ">\n  <thead>\n    <tr><th></th></tr>\n  </thead>\n  <tbody>\n  </tbody>\n</table>",
    "<section": ">\n  \n</section>",
    "<header": ">\n  \n</header>",
    "<footer": ">\n  \n</footer>",
    "<nav": ">\n  \n</nav>",
}

SQL_PATTERNS = {
    "SELECT ": "* FROM table_name WHERE condition",
    "INSERT INTO ": "table_name (col1, col2) VALUES (?, ?)",
    "UPDATE ": "table_name SET col1 = ? WHERE id = ?",
    "DELETE FROM ": "table_name WHERE id = ?",
    "CREATE TABLE ": "table_name (\n  id SERIAL PRIMARY KEY,\n  name VARCHAR(255)\n);",
    "ALTER TABLE ": "table_name ADD COLUMN col_name VARCHAR(255);",
    "DROP TABLE ": "IF EXISTS table_name;",
    "CREATE INDEX ": "idx_name ON table_name (col_name);",
    "JOIN ": "table_name ON t1.id = t2.foreign_id",
    "LEFT JOIN ": "table_name ON t1.id = t2.foreign_id",
    "GROUP BY ": "col_name HAVING COUNT(*) > 1",
    "ORDER BY ": "col_name DESC",
    "LIMIT ": "100 OFFSET 0",
    "WHERE ": "col_name = ?",
    "HAVING ": "COUNT(*) > 1",
    "CASE WHEN ": "condition THEN value ELSE other END",
    "COALESCE(": "col_name, 'default')",
    "COUNT(": "*)",
    "SUM(": "col_name)",
    "AVG(": "col_name)",
    "WITH ": "cte AS (\n  SELECT * FROM table_name\n)\nSELECT * FROM cte",
}

RUST_PATTERNS = {
    "fn ": "name() -> Result<(), Box<dyn Error>> {\n    Ok(())\n}",
    "pub fn ": "name() -> Result<(), Box<dyn Error>> {\n    Ok(())\n}",
    "struct ": "Name {\n    field: String,\n}",
    "impl ": "Name {\n    fn new() -> Self {\n        Self {}\n    }\n}",
    "enum ": "Name {\n    Variant,\n}",
    "trait ": "Name {\n    fn method(&self);\n}",
    "match ": "value {\n    _ => {},\n}",
    "if let Some(": "val) = option {",
    "let mut ": "name = ",
    "let ": "name = ",
    "use std::": "",
    "println!(\"": '{}",)',
    "vec![": "]",
    "HashMap::new(": ")",
    "#[derive(": "Debug, Clone)]",
    "async fn ": "name() -> Result<()> {\n    Ok(())\n}",
    "pub struct ": "Name {\n    pub field: String,\n}",
    ".unwrap()": "",
    "Result<": ", Box<dyn Error>>",
    "Option<": ">",
}

GO_PATTERNS = {
    "func ": "name() error {\n\treturn nil\n}",
    "func (": "s *Struct) Method() error {\n\treturn nil\n}",
    "type ": "Name struct {\n\tField string\n}",
    "interface ": "{\n\tMethod() error\n}",
    "if err != nil": " {\n\treturn err\n}",
    "for ": "i, v := range items {\n\t\n}",
    "switch ": "v {\ncase :\n\t\ndefault:\n\t\n}",
    "go func()": " {\n\t\n}()",
    "select {": "\ncase <-ch:\n\t\ndefault:\n\t\n}",
    "make(": "[]string, 0)",
    "fmt.Println(": ")",
    'fmt.Sprintf("': '%v",)',
    "json.Marshal(": "v)",
    "json.Unmarshal(": "data, &v)",
    "http.HandleFunc(": '"/", handler)',
    "defer ": "",
    "chan ": "struct{}",
    "map[string]": "interface{}",
    "context.": "Background()",
    ":= range ": "",
}

LANGUAGE_PATTERNS = {
    "python": PYTHON_PATTERNS,
    "javascript": JS_PATTERNS,
    "typescript": TS_PATTERNS,
    "typescriptreact": TS_PATTERNS,
    "javascriptreact": JS_PATTERNS,
    "css": CSS_PATTERNS,
    "scss": CSS_PATTERNS,
    "html": HTML_PATTERNS,
    "jsx": JS_PATTERNS,
    "tsx": TS_PATTERNS,
    "sql": SQL_PATTERNS,
    "rust": RUST_PATTERNS,
    "go": GO_PATTERNS,
}


# ── Context-aware variable extraction ───────────────────────────

def _extract_context(code_before: str, language: str) -> Dict:
    """Extract variables, imports, and function names from surrounding code."""
    lines = code_before.split("\n")[-30:]
    context = {
        "variables": [],
        "imports": [],
        "functions": [],
        "classes": [],
    }

    for line in lines:
        stripped = line.strip()
        if language in ("python",):
            if stripped.startswith("import ") or stripped.startswith("from "):
                context["imports"].append(stripped)
            elif stripped.startswith("def "):
                match = re.match(r"def\s+(\w+)", stripped)
                if match:
                    context["functions"].append(match.group(1))
            elif stripped.startswith("class "):
                match = re.match(r"class\s+(\w+)", stripped)
                if match:
                    context["classes"].append(match.group(1))
            elif "=" in stripped and not stripped.startswith("#"):
                match = re.match(r"(\w+)\s*=", stripped)
                if match:
                    context["variables"].append(match.group(1))
        elif language in ("javascript", "typescript", "jsx", "tsx"):
            if stripped.startswith("import "):
                context["imports"].append(stripped)
            elif re.match(r"(const|let|var)\s+\w+", stripped):
                match = re.match(r"(?:const|let|var)\s+(\w+)", stripped)
                if match:
                    context["variables"].append(match.group(1))
            elif re.match(r"(function|async\s+function)\s+\w+", stripped):
                match = re.match(r"(?:async\s+)?function\s+(\w+)", stripped)
                if match:
                    context["functions"].append(match.group(1))

    return context


# ── Multi-line block completion ─────────────────────────────────

def _block_completion(code_before: str, language: str) -> str:
    """Detect if we're inside an unfinished block and suggest closure."""
    lines = code_before.split("\n")
    if not lines:
        return ""

    if language in ("python",):
        open_count = sum(1 for l in lines if l.strip().endswith(":") and not l.strip().startswith("#"))
        indent_level = 0
        for l in reversed(lines):
            if l.strip():
                indent_level = len(l) - len(l.lstrip())
                break
        if open_count > 0 and lines[-1].strip() == "":
            return " " * (indent_level + 4) + "pass"

    elif language in ("javascript", "typescript", "jsx", "tsx"):
        opens = sum(l.count("{") for l in lines)
        closes = sum(l.count("}") for l in lines)
        if opens > closes:
            return "}"

    return ""


# ── API Endpoints ───────────────────────────────────────────────

@router.post("/inline")
async def inline_completion(request: Request):
    """
    Fast inline completion.
    Input: { code_before, code_after, language, file_path }
    Output: { completion, source, latency_ms, context }
    """
    body = await request.json()
    code_before = body.get("code_before", "")
    code_after = body.get("code_after", "")
    language = body.get("language", "python")
    file_path = body.get("file_path", "")

    start = time.time()

    # Level 0: Bracket/quote auto-close (<1ms)
    completion = _auto_close(code_before)
    if completion:
        return {
            "completion": completion,
            "source": "auto_close",
            "latency_ms": round((time.time() - start) * 1000, 1),
        }

    # Level 1: Pattern matching (<5ms)
    completion = _pattern_match(code_before, language)
    if completion:
        _cache.put(code_before, language, completion)
        return {
            "completion": completion,
            "source": "pattern",
            "latency_ms": round((time.time() - start) * 1000, 1),
        }

    # Level 1.5: Block completion
    completion = _block_completion(code_before, language)
    if completion:
        return {
            "completion": completion,
            "source": "block",
            "latency_ms": round((time.time() - start) * 1000, 1),
        }

    # Level 2: Check cache
    cached = _cache.get(code_before, language)
    if cached:
        return {
            "completion": cached,
            "source": "cache",
            "latency_ms": round((time.time() - start) * 1000, 1),
        }

    # Level 3: Context-aware LLM completion
    last_line = code_before.split("\n")[-1] if code_before else ""
    if len(last_line.strip()) < 3:
        return {"completion": "", "source": "too_short", "latency_ms": 0}

    try:
        context = _extract_context(code_before, language)
        context_hint = ""
        if context["variables"]:
            context_hint += f"\nAvailable variables: {', '.join(context['variables'][-10:])}"
        if context["functions"]:
            context_hint += f"\nDefined functions: {', '.join(context['functions'][-5:])}"
        if context["imports"]:
            context_hint += f"\nImported: {'; '.join(context['imports'][-5:])}"

        from core.independent_models import run_with_failover
        prompt = (
            f"Complete this {language} code. Return ONLY the completion (1-3 lines max), "
            f"no explanation, no markdown, no code fences:\n"
            f"{context_hint}\n\n"
            f"```{language}\n{code_before[-800:]}"
        )
        result = run_with_failover(
            prompt,
            preferred_order=["qwen", "reasoning", "kimi"],
            system_prompt=(
                "You are a code completion engine. Return ONLY the raw code that completes "
                "the current line and optionally 1-2 following lines. No markdown fences. "
                "No explanation. No comments about the code."
            ),
        )
        if result.get("response"):
            completion = _clean_completion(result["response"], language)
            if completion:
                _cache.put(code_before, language, completion)
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
    max_tokens = body.get("max_tokens", 200)

    async def generate():
        try:
            from settings import settings
            context = _extract_context(code_before, language)
            context_hint = ""
            if context["variables"]:
                context_hint = f"\nVariables in scope: {', '.join(context['variables'][-10:])}"

            prompt = (
                f"Complete this {language} code:{context_hint}\n"
                f"```{language}\n{code_before[-800:]}"
            )

            if settings.KIMI_API_KEY:
                import requests
                url = f"{settings.KIMI_BASE_URL}/chat/completions"
                headers = {"Authorization": f"Bearer {settings.KIMI_API_KEY}", "Content-Type": "application/json"}
                payload = {
                    "model": settings.KIMI_MODEL,
                    "messages": [
                        {"role": "system", "content": "Complete the code. Return ONLY code. No markdown."},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": True,
                    "max_tokens": min(max_tokens, 500),
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


@router.get("/stats")
async def completion_stats():
    """Get completion cache statistics."""
    return _cache.stats()


# ── Helper functions ────────────────────────────────────────────

def _auto_close(code_before: str) -> str:
    """Instant bracket/quote auto-close."""
    if not code_before:
        return ""
    last_char = code_before[-1] if code_before else ""

    pairs = {"(": ")", "[": "]", "{": "}", "'": "'", '"': '"', "`": "`"}
    if last_char in pairs:
        closing = pairs[last_char]
        opens = code_before.count(last_char)
        closes = code_before.count(closing)
        if last_char == closing:
            if opens % 2 != 0:
                return closing
        elif opens > closes:
            return closing
    return ""


def _pattern_match(code_before: str, language: str) -> str:
    """Multi-language pattern matching for common code patterns."""
    if not code_before:
        return ""

    last_line = code_before.split("\n")[-1]
    stripped = last_line.strip()

    patterns = LANGUAGE_PATTERNS.get(language, PYTHON_PATTERNS)

    for prefix, completion in patterns.items():
        if stripped.endswith(prefix) or stripped == prefix.strip():
            return completion

    return ""


def _clean_completion(raw: str, language: str) -> str:
    """Clean LLM output to extract just the code completion."""
    completion = raw.strip()

    completion = re.sub(r'^```\w*\n?', '', completion)
    completion = re.sub(r'\n?```$', '', completion)
    completion = completion.strip()

    if completion.startswith("Here") or completion.startswith("The ") or completion.startswith("This "):
        lines = completion.split("\n")
        code_lines = [l for l in lines if not l.startswith(("Here", "The ", "This ", "I ", "Note"))]
        completion = "\n".join(code_lines).strip()

    lines = completion.split("\n")[:5]
    completion = "\n".join(lines)

    return completion
