"""
Cross-Tab Intelligence API

Closes the loop between Chat, Folders, and Docs by exposing:
- Folder-scoped RAG retrieval for chat context
- Document tags and relationships for any file
- Activity feed across all subsystems
- Related documents discovery
- Tag-based navigation across folders
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intelligence", tags=["Cross-Tab Intelligence"])


class FolderChatRequest(BaseModel):
    query: str
    folder_path: str
    limit: int = 8
    threshold: float = 0.3
    provider: Optional[str] = None


class FolderChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    folder_path: str
    provider_used: str


def _get_db():
    from database.session import SessionLocal
    if SessionLocal is None:
        from database.session import initialize_session_factory
        initialize_session_factory()
        from database.session import SessionLocal as SL
        return SL()
    return SessionLocal()


def _safe_json(text, default=None):
    if not text:
        return default
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


# ---------------------------------------------------------------------------
# 1. Folder-scoped chat — Chat with context from a specific folder
# ---------------------------------------------------------------------------

@router.post("/folder-chat", response_model=FolderChatResponse)
async def folder_scoped_chat(request: FolderChatRequest):
    """
    Chat with AI using only documents from a specific folder as context.
    Bridges Chat ↔ Folders: select a folder, ask questions scoped to it.
    """
    from settings import settings

    sources = []
    context_text = ""

    try:
        from retrieval.retriever import DocumentRetriever
        from embedding.embedder import get_embedding_model
        from vector_db.client import get_qdrant_client

        retriever = DocumentRetriever(
            embedding_model=get_embedding_model(),
            qdrant_client=get_qdrant_client(),
        )
        chunks = retriever.retrieve(
            query=request.query,
            limit=request.limit,
            score_threshold=request.threshold,
            filter_path=request.folder_path,
        )
        for chunk in chunks:
            sources.append({
                "text": chunk.get("text", "")[:300],
                "score": chunk.get("score", 0),
                "source": chunk.get("metadata", {}).get("filename", ""),
                "file_path": chunk.get("metadata", {}).get("file_path", ""),
            })
            context_text += chunk.get("text", "") + "\n\n"
    except Exception as e:
        logger.warning(f"Folder-scoped retrieval failed: {e}")

    provider = request.provider or ("kimi" if settings.KIMI_API_KEY else settings.LLM_PROVIDER)

    system_prompt = (
        f"You are Grace, answering questions using ONLY documents from the folder '{request.folder_path}'. "
        f"Base your answer on the provided context. If the context doesn't contain relevant information, say so."
    )
    if context_text:
        system_prompt += f"\n\nContext from folder '{request.folder_path}':\n{context_text[:6000]}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.query},
    ]

    try:
        if provider == "kimi":
            from llm_orchestrator.factory import get_kimi_client
            client = get_kimi_client()
        else:
            from llm_orchestrator.factory import get_llm_client
            client = get_llm_client()

        response_text = client.chat(messages=messages, temperature=0.5)

        from api._genesis_tracker import track
        track(
            key_type="ai_response",
            what=f"Folder-scoped chat: {request.query[:80]}",
            where=request.folder_path,
            how="POST /api/intelligence/folder-chat",
            input_data={"query": request.query, "folder": request.folder_path},
            output_data={"source_count": len(sources), "provider": provider},
            tags=["folder_chat", "intelligence"],
        )

        return FolderChatResponse(
            response=response_text,
            sources=sources,
            folder_path=request.folder_path,
            provider_used=provider,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# 2. Document intelligence — tags, relationships, for any document
# ---------------------------------------------------------------------------

@router.get("/document/{doc_id}/tags")
async def get_document_tags(doc_id: int):
    """Get auto-generated tags for a document. Bridges Docs ↔ Folders."""
    db = _get_db()
    try:
        from models.database_models import Document
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        tags = _safe_json(doc.tags, [])

        librarian_tags = []
        try:
            from sqlalchemy import text
            result = db.execute(text(
                "SELECT tag_name, tag_type, confidence FROM document_tags WHERE document_id = :did"
            ), {"did": doc_id})
            for row in result:
                librarian_tags.append({
                    "name": row[0], "type": row[1], "confidence": row[2]
                })
        except Exception:
            pass

        return {
            "document_id": doc_id,
            "filename": doc.filename,
            "tags": tags,
            "librarian_tags": librarian_tags,
        }
    finally:
        db.close()


@router.get("/document/{doc_id}/related")
async def get_related_documents(doc_id: int, limit: int = 10):
    """Get related documents via the librarian relationship graph."""
    db = _get_db()
    try:
        from models.database_models import Document

        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        related = []
        try:
            from sqlalchemy import text
            result = db.execute(text("""
                SELECT dr.target_document_id, dr.relationship_type, dr.confidence,
                       d.filename, d.file_path, d.source
                FROM document_relationships dr
                JOIN documents d ON d.id = dr.target_document_id
                WHERE dr.source_document_id = :did
                ORDER BY dr.confidence DESC
                LIMIT :lim
            """), {"did": doc_id, "lim": limit})
            for row in result:
                related.append({
                    "document_id": row[0],
                    "relationship_type": row[1],
                    "confidence": row[2],
                    "filename": row[3],
                    "file_path": row[4],
                    "source": row[5],
                })
        except Exception:
            pass

        if not related:
            try:
                from retrieval.retriever import DocumentRetriever
                from embedding.embedder import get_embedding_model
                from vector_db.client import get_qdrant_client

                sample_text = ""
                for chunk in doc.chunks[:3]:
                    sample_text += (chunk.text_content or "") + " "
                if sample_text.strip():
                    retriever = DocumentRetriever(
                        embedding_model=get_embedding_model(),
                        qdrant_client=get_qdrant_client(),
                    )
                    similar = retriever.retrieve(
                        query=sample_text[:500], limit=limit + 1, score_threshold=0.3
                    )
                    seen = set()
                    for s in similar:
                        sid = s.get("document_id")
                        if sid and sid != doc_id and sid not in seen:
                            seen.add(sid)
                            related.append({
                                "document_id": sid,
                                "relationship_type": "semantically_similar",
                                "confidence": s.get("score", 0),
                                "filename": s.get("metadata", {}).get("filename", ""),
                                "file_path": s.get("metadata", {}).get("file_path", ""),
                                "source": "vector_similarity",
                            })
            except Exception:
                pass

        return {
            "document_id": doc_id,
            "filename": doc.filename,
            "related_count": len(related),
            "related": related[:limit],
        }
    finally:
        db.close()


@router.post("/document/{doc_id}/reprocess")
async def reprocess_document(doc_id: int, background_tasks: BackgroundTasks):
    """Re-run librarian processing on a document (auto-tag, detect relationships)."""
    db = _get_db()
    try:
        from models.database_models import Document
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        try:
            from api.file_management import _process_with_librarian
            background_tasks.add_task(_process_with_librarian, doc_id)
            from api._genesis_tracker import track
            track(key_type="librarian", what=f"Reprocess queued: {doc.filename}", how="POST /api/intelligence/document/reprocess", output_data={"doc_id": doc_id}, tags=["reprocess", "librarian"])
            return {"queued": True, "document_id": doc_id, "message": "Librarian reprocessing queued"}
        except ImportError:
            raise HTTPException(status_code=503, detail="Librarian processing not available")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 3. Tag-based navigation — unified across all folders
# ---------------------------------------------------------------------------

@router.get("/tags")
async def get_all_tags():
    """Get all tags with document counts. Bridges Docs ↔ Folders."""
    db = _get_db()
    try:
        from models.database_models import Document
        docs = db.query(Document).all()

        tag_counts: Dict[str, int] = {}
        for doc in docs:
            tags = _safe_json(doc.tags, [])
            for tag in tags:
                if isinstance(tag, str) and tag.strip():
                    tag_counts[tag.strip()] = tag_counts.get(tag.strip(), 0) + 1

        try:
            from sqlalchemy import text
            result = db.execute(text(
                "SELECT tag_name, COUNT(*) as cnt FROM document_tags GROUP BY tag_name ORDER BY cnt DESC"
            ))
            for row in result:
                tag_counts[row[0]] = tag_counts.get(row[0], 0) + row[1]
        except Exception:
            pass

        tag_list = [{"tag": t, "count": c} for t, c in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)]

        return {"total_tags": len(tag_list), "tags": tag_list}
    finally:
        db.close()


@router.get("/tags/{tag_name}/documents")
async def get_documents_by_tag(tag_name: str):
    """Get all documents with a specific tag, across all folders."""
    db = _get_db()
    try:
        from models.database_models import Document
        docs = db.query(Document).all()

        results = []
        for doc in docs:
            tags = _safe_json(doc.tags, [])
            if tag_name in tags:
                from api.docs_library_api import _doc_to_dict
                results.append(_doc_to_dict(doc))

        return {"tag": tag_name, "total": len(results), "documents": results}
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 4. Folder intelligence — what the librarian knows about a folder
# ---------------------------------------------------------------------------

@router.get("/folder/{folder_path:path}/summary")
async def get_folder_summary(folder_path: str):
    """
    Librarian's intelligence summary for a folder.
    Shows: document count, tags, relationships, types.
    Bridges all three tabs with folder-level intelligence.
    """
    db = _get_db()
    try:
        from models.database_models import Document
        from pathlib import Path

        docs = db.query(Document).all()
        kb_path = None
        try:
            from settings import settings
            kb_path = Path(settings.KNOWLEDGE_BASE_PATH)
        except Exception:
            pass

        folder_docs = []
        for doc in docs:
            fp = doc.file_path or ""
            try:
                if kb_path and fp:
                    rel = str(Path(fp).relative_to(kb_path))
                    if rel.startswith(folder_path):
                        folder_docs.append(doc)
                elif folder_path in fp:
                    folder_docs.append(doc)
            except (ValueError, TypeError):
                if folder_path in fp:
                    folder_docs.append(doc)

        tag_counts: Dict[str, int] = {}
        mime_types: Dict[str, int] = {}
        total_size = 0

        for doc in folder_docs:
            total_size += doc.file_size or 0
            mime = doc.mime_type or "unknown"
            mime_types[mime] = mime_types.get(mime, 0) + 1
            for tag in _safe_json(doc.tags, []):
                if isinstance(tag, str):
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return {
            "folder": folder_path,
            "document_count": len(folder_docs),
            "total_size": total_size,
            "top_tags": sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:15],
            "file_types": mime_types,
            "documents": [
                {"id": d.id, "filename": d.filename, "status": d.status, "file_size": d.file_size}
                for d in folder_docs
            ],
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 5. Activity feed — recent events across all tabs
# ---------------------------------------------------------------------------

@router.get("/activity")
async def get_activity_feed(limit: int = 30):
    """
    Recent activity across Chat, Folders, and Docs.
    Gives a unified timeline of what happened in the system.
    """
    db = _get_db()
    try:
        from models.database_models import Document
        from sqlalchemy import text

        events = []

        recent_docs = db.query(Document).order_by(Document.created_at.desc()).limit(limit).all()
        for doc in recent_docs:
            events.append({
                "type": "document_added",
                "timestamp": doc.created_at.isoformat() if doc.created_at else None,
                "title": f"Document uploaded: {doc.filename}",
                "detail": f"Source: {doc.source}, Method: {doc.upload_method}",
                "entity_id": doc.id,
                "entity_type": "document",
            })

        try:
            result = db.execute(text("""
                SELECT id, title, created_at FROM chats
                ORDER BY created_at DESC LIMIT :lim
            """), {"lim": limit})
            for row in result:
                events.append({
                    "type": "chat_created",
                    "timestamp": row[2].isoformat() if row[2] else None,
                    "title": f"Chat: {row[1] or 'Untitled'}",
                    "detail": "",
                    "entity_id": row[0],
                    "entity_type": "chat",
                })
        except Exception:
            pass

        events.sort(key=lambda x: x.get("timestamp") or "", reverse=True)

        return {"total": len(events), "events": events[:limit]}
    finally:
        db.close()
