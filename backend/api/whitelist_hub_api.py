"""
Whitelist Hub API — API Sources, Web Sources, and Domain Learning

Two source tables:
1. API Sources — paste an API endpoint, Grace auto-connects (GitHub, etc.)
2. Web Sources — people, websites, podcasts, YouTube, blogs to learn from

Each source can have document uploads attached for additional context.
Connected to ingestion and learning pipelines. Uses Kimi for reasoning.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import json
import uuid
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/whitelist-hub", tags=["Whitelist Hub"])

DATA_DIR = Path(__file__).parent.parent / "data" / "whitelist_sources"


def _ensure():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for sub in ["api_sources", "web_sources"]:
        (DATA_DIR / sub).mkdir(exist_ok=True)


def _load_sources(kind: str) -> List[Dict[str, Any]]:
    _ensure()
    path = DATA_DIR / f"{kind}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return []


def _save_sources(kind: str, data: List[Dict[str, Any]]):
    _ensure()
    (DATA_DIR / f"{kind}.json").write_text(json.dumps(data, indent=2, default=str))


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class APISourceAdd(BaseModel):
    name: str
    url: str
    api_key: Optional[str] = None
    description: Optional[str] = ""
    headers: Optional[Dict[str, str]] = None


class WebSourceAdd(BaseModel):
    name: str
    url: str
    source_type: str = "website"  # website, youtube, podcast, blog, person, github
    description: Optional[str] = ""
    tags: Optional[List[str]] = None


class SourceRunRequest(BaseModel):
    source_id: str
    query: Optional[str] = None
    use_kimi: bool = True


class SourceDocSave(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# 1. API Sources — paste API endpoints, auto-connect data
# ---------------------------------------------------------------------------

@router.get("/api-sources")
async def list_api_sources():
    """List all whitelisted API sources."""
    return {"sources": _load_sources("api_sources")}


@router.post("/api-sources")
async def add_api_source(request: APISourceAdd):
    """Add a new API source. Paste the endpoint and Grace connects."""
    sources = _load_sources("api_sources")
    source = {
        "id": f"api-{uuid.uuid4().hex[:8]}",
        "name": request.name,
        "url": request.url,
        "api_key": request.api_key or "",
        "description": request.description,
        "headers": request.headers or {},
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "last_run": None,
        "run_count": 0,
        "documents": [],
    }
    sources.append(source)
    _save_sources("api_sources", sources)

    from api._genesis_tracker import track
    track(key_type="system", what=f"API source added: {request.name} ({request.url})",
          how="POST /api/whitelist-hub/api-sources", tags=["whitelist", "api_source"])

    return {"added": True, **source}


@router.delete("/api-sources/{source_id}")
async def delete_api_source(source_id: str):
    """Remove an API source."""
    sources = _load_sources("api_sources")
    sources = [s for s in sources if s["id"] != source_id]
    _save_sources("api_sources", sources)
    return {"deleted": True, "id": source_id}


@router.post("/api-sources/{source_id}/run")
async def run_api_source(source_id: str, request: SourceRunRequest):
    """
    Pull data from an API source. Grace connects, fetches, and
    optionally reasons about the data with Kimi.
    """
    sources = _load_sources("api_sources")
    source = next((s for s in sources if s["id"] == source_id), None)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    import requests as req

    try:
        headers = source.get("headers", {})
        if source.get("api_key"):
            headers["Authorization"] = f"Bearer {source['api_key']}"
        headers.setdefault("Accept", "application/json")

        url = source["url"]
        if request.query:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}q={request.query}"

        resp = req.get(url, headers=headers, timeout=30)
        resp.raise_for_status()

        try:
            data = resp.json()
        except Exception:
            data = resp.text[:5000]

        result = {"status": "success", "data": data if isinstance(data, (str, list)) else json.dumps(data, indent=2)[:5000]}

        if request.use_kimi:
            try:
                from llm_orchestrator.factory import get_kimi_client
                client = get_kimi_client()
                analysis = client.generate(
                    prompt=f"Analyse this API response from {source['name']} ({source['url']}):\n\n{result['data'][:4000]}\n\nProvide key insights and what Grace can learn.",
                    system_prompt="You are Grace's learning intelligence. Extract structured knowledge from API data.",
                    temperature=0.3, max_tokens=2048,
                )
                result["kimi_analysis"] = analysis
            except Exception as e:
                result["kimi_error"] = str(e)

        source["last_run"] = datetime.utcnow().isoformat()
        source["run_count"] = source.get("run_count", 0) + 1
        _save_sources("api_sources", sources)

        from api._genesis_tracker import track
        track(key_type="api_request", what=f"API source run: {source['name']}",
              how="POST /api/whitelist-hub/api-sources/run",
              input_data={"url": source["url"], "query": request.query},
              tags=["whitelist", "api_run"])

        # Store in Oracle (training data) + Magma
        try:
            from cognitive.pipeline import FeedbackLoop
            FeedbackLoop.record_outcome(
                genesis_key="", prompt=f"API source: {source['name']} ({source['url']})",
                output=str(result.get("data", ""))[:3000], outcome="positive",
            )
        except Exception:
            pass
        try:
            from cognitive.magma_bridge import ingest
            ingest(f"API data from {source['name']}: {str(result.get('data', ''))[:1000]}", source="whitelist_api")
        except Exception:
            pass
        try:
            from cognitive.trust_engine import get_trust_engine
            get_trust_engine().score_output(f"whitelist_api_{source['name']}", f"Whitelist: {source['name']}",
                str(result.get("data", ""))[:500], source="internal" if result.get("status") == "success" else "unknown")
        except Exception:
            pass

        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# 2. Web Sources — websites, YouTube, podcasts, blogs, people
# ---------------------------------------------------------------------------

@router.get("/web-sources")
async def list_web_sources():
    """List all whitelisted web sources."""
    return {"sources": _load_sources("web_sources")}


@router.post("/web-sources")
async def add_web_source(request: WebSourceAdd):
    """Add a web source to learn from."""
    sources = _load_sources("web_sources")
    source = {
        "id": f"web-{uuid.uuid4().hex[:8]}",
        "name": request.name,
        "url": request.url,
        "source_type": request.source_type,
        "description": request.description,
        "tags": request.tags or [],
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "last_run": None,
        "run_count": 0,
        "documents": [],
    }
    sources.append(source)
    _save_sources("web_sources", sources)

    from api._genesis_tracker import track
    track(key_type="system", what=f"Web source added: {request.name} ({request.source_type})",
          how="POST /api/whitelist-hub/web-sources", tags=["whitelist", "web_source", request.source_type])

    return {"added": True, **source}


@router.delete("/web-sources/{source_id}")
async def delete_web_source(source_id: str):
    """Remove a web source."""
    sources = _load_sources("web_sources")
    sources = [s for s in sources if s["id"] != source_id]
    _save_sources("web_sources", sources)
    return {"deleted": True, "id": source_id}


@router.post("/web-sources/{source_id}/run")
async def run_web_source(source_id: str, request: SourceRunRequest):
    """
    Pull data from a web source. Grace scrapes, extracts,
    and reasons about it with Kimi for deeper context.
    """
    sources = _load_sources("web_sources")
    source = next((s for s in sources if s["id"] == source_id), None)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    import requests as req

    try:
        resp = req.get(source["url"], timeout=30, headers={"User-Agent": "Grace/1.0"})
        raw = resp.text[:8000]

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(raw, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)[:5000]
            title = soup.title.string if soup.title else source["name"]
        except Exception:
            text = raw[:5000]
            title = source["name"]

        result = {"status": "success", "title": title, "text": text}

        if request.use_kimi:
            try:
                from llm_orchestrator.factory import get_kimi_client
                client = get_kimi_client()
                extra = f"\nUser query: {request.query}" if request.query else ""
                analysis = client.generate(
                    prompt=f"Analyse this content from {source['name']} ({source['source_type']}):\n\nTitle: {title}\n\n{text[:4000]}{extra}\n\nExtract key knowledge, facts, and insights.",
                    system_prompt="You are Grace's learning intelligence. Extract structured knowledge from web content.",
                    temperature=0.3, max_tokens=2048,
                )
                result["kimi_analysis"] = analysis
            except Exception as e:
                result["kimi_error"] = str(e)

        source["last_run"] = datetime.utcnow().isoformat()
        source["run_count"] = source.get("run_count", 0) + 1
        _save_sources("web_sources", sources)

        from api._genesis_tracker import track
        track(key_type="web_fetch", what=f"Web source run: {source['name']}",
              how="POST /api/whitelist-hub/web-sources/run",
              input_data={"url": source["url"], "type": source["source_type"]},
              tags=["whitelist", "web_run", source["source_type"]])

        # Store in Oracle + Magma
        try:
            from cognitive.pipeline import FeedbackLoop
            FeedbackLoop.record_outcome(
                genesis_key="", prompt=f"Web source: {source['name']} ({source['source_type']})",
                output=(result.get("text", "") or "")[:3000], outcome="positive",
            )
        except Exception:
            pass
        try:
            from cognitive.magma_bridge import ingest
            ingest(f"Web data from {source['name']}: {(result.get('text', '') or '')[:1000]}", source="whitelist_web")
        except Exception:
            pass
        try:
            from cognitive.trust_engine import get_trust_engine
            get_trust_engine().score_output(f"whitelist_web_{source['name']}", f"Whitelist: {source['name']}",
                (result.get("text", "") or "")[:500], source="internal" if result.get("status") == "success" else "unknown")
        except Exception:
            pass

        return result
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ---------------------------------------------------------------------------
# 3. Source documents — upload docs to individual sources for context
# ---------------------------------------------------------------------------

@router.post("/sources/{source_id}/upload")
async def upload_source_document(
    source_id: str,
    file: UploadFile = File(...),
    description: str = Form(""),
):
    """Upload a document to a specific source for additional context."""
    _ensure()
    for kind in ["api_sources", "web_sources"]:
        sources = _load_sources(kind)
        source = next((s for s in sources if s["id"] == source_id), None)
        if source:
            docs_dir = DATA_DIR / kind / source_id
            docs_dir.mkdir(parents=True, exist_ok=True)
            file_path = docs_dir / file.filename

            content = await file.read()
            file_path.write_bytes(content)

            doc_entry = {
                "filename": file.filename,
                "path": str(file_path),
                "size": len(content),
                "description": description,
                "uploaded_at": datetime.utcnow().isoformat(),
            }
            if "documents" not in source:
                source["documents"] = []
            source["documents"].append(doc_entry)
            _save_sources(kind, sources)

            try:
                from api.docs_library_api import register_document
                register_document(
                    filename=file.filename, file_path=str(file_path),
                    file_size=len(content), source="whitelist",
                    upload_method="whitelist_source_upload",
                    directory=f"whitelist/{source_id}",
                )
            except Exception:
                pass

            from api._genesis_tracker import track
            track(key_type="upload", what=f"Document uploaded to source {source['name']}: {file.filename}",
                  file_path=str(file_path), tags=["whitelist", "source_upload"])

            return {"uploaded": True, "source_id": source_id, "filename": file.filename, "size": len(content)}

    raise HTTPException(status_code=404, detail="Source not found")


@router.get("/sources/{source_id}/documents")
async def list_source_documents(source_id: str):
    """List documents attached to a source."""
    for kind in ["api_sources", "web_sources"]:
        sources = _load_sources(kind)
        source = next((s for s in sources if s["id"] == source_id), None)
        if source:
            return {"source_id": source_id, "documents": source.get("documents", [])}
    raise HTTPException(status_code=404, detail="Source not found")


@router.get("/sources/{source_id}/documents/{filename}/content")
async def get_source_document_content(source_id: str, filename: str):
    """Read a source document's content for viewing/editing."""
    for kind in ["api_sources", "web_sources"]:
        doc_path = DATA_DIR / kind / source_id / filename
        if doc_path.exists():
            try:
                content = doc_path.read_text(errors="ignore")
            except Exception:
                content = doc_path.read_bytes().decode("utf-8", errors="replace")
            return {"filename": filename, "source_id": source_id, "content": content, "size": doc_path.stat().st_size}
    raise HTTPException(status_code=404, detail="Document not found")


@router.put("/sources/{source_id}/documents/{filename}/content")
async def save_source_document(source_id: str, filename: str, request: SourceDocSave):
    """Save (edit) a source document."""
    for kind in ["api_sources", "web_sources"]:
        doc_path = DATA_DIR / kind / source_id / filename
        if doc_path.exists():
            doc_path.write_text(request.content, encoding="utf-8")
            from api._genesis_tracker import track
            track(key_type="file_op", what=f"Whitelist source doc edited: {filename}",
                  file_path=str(doc_path), tags=["whitelist", "edit"])
            return {"saved": True, "filename": filename, "size": doc_path.stat().st_size}
    raise HTTPException(status_code=404, detail="Document not found")


@router.delete("/sources/{source_id}/documents/{filename}")
async def delete_source_document(source_id: str, filename: str):
    """Delete a source document."""
    for kind in ["api_sources", "web_sources"]:
        doc_path = DATA_DIR / kind / source_id / filename
        if doc_path.exists():
            doc_path.unlink()
            sources = _load_sources(kind)
            source = next((s for s in sources if s["id"] == source_id), None)
            if source and "documents" in source:
                source["documents"] = [d for d in source["documents"] if d["filename"] != filename]
                _save_sources(kind, sources)
            return {"deleted": True}
    raise HTTPException(status_code=404, detail="Document not found")


# ---------------------------------------------------------------------------
# 4. Stats
# ---------------------------------------------------------------------------

@router.get("/stats")
async def whitelist_stats():
    """Get whitelist hub statistics."""
    api = _load_sources("api_sources")
    web = _load_sources("web_sources")
    return {
        "api_source_count": len(api),
        "web_source_count": len(web),
        "total_api_runs": sum(s.get("run_count", 0) for s in api),
        "total_web_runs": sum(s.get("run_count", 0) for s in web),
        "total_documents": sum(len(s.get("documents", [])) for s in api + web),
        "web_types": {t: sum(1 for s in web if s.get("source_type") == t) for t in set(s.get("source_type", "website") for s in web)},
    }
