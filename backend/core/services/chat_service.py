"""Chat domain service — direct function calls, no HTTP."""

from typing import Dict, Any, Optional
from database.session import session_scope, get_session_factory


def list_chats(limit: int = 50) -> dict:
    from models.repositories import ChatRepository
    factory = get_session_factory()
    session = factory()
    try:
        repo = ChatRepository(session)
        chats = repo.get_all_chats(skip=0, limit=limit)
        total = repo.count()
        return {
            "chats": [
                {"id": c.id, "title": c.title, "model": c.model,
                 "created_at": c.created_at.isoformat() if c.created_at else None}
                for c in chats
            ],
            "total": total,
        }
    finally:
        session.close()


def create_chat(payload: dict) -> dict:
    from models.repositories import ChatRepository
    factory = get_session_factory()
    session = factory()
    try:
        repo = ChatRepository(session)
        chat = repo.create(
            title=payload.get("title"),
            description=payload.get("description"),
            model=payload.get("model", "qwen2.5:7b"),
            temperature=payload.get("temperature", 0.7),
            folder_path=payload.get("folder_path", ""),
        )
        session.commit()
        return {"id": chat.id, "title": chat.title, "model": chat.model}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_chat(payload: dict) -> dict:
    from models.repositories import ChatRepository
    factory = get_session_factory()
    session = factory()
    try:
        repo = ChatRepository(session)
        chat = repo.get(payload["chat_id"])
        if not chat:
            return {"error": "Chat not found"}
        return {"id": chat.id, "title": chat.title, "model": chat.model}
    finally:
        session.close()


def delete_chat(payload: dict) -> dict:
    from models.repositories import ChatRepository
    factory = get_session_factory()
    session = factory()
    try:
        repo = ChatRepository(session)
        repo.delete(payload["chat_id"])
        session.commit()
        return {"deleted": True}
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_history(payload: dict) -> dict:
    from models.repositories import ChatHistoryRepository
    factory = get_session_factory()
    session = factory()
    try:
        repo = ChatHistoryRepository(session)
        messages = repo.get_by_chat(payload["chat_id"], skip=0, limit=100)
        return {
            "messages": [
                {"id": m.id, "role": m.role, "content": m.content,
                 "created_at": m.created_at.isoformat() if m.created_at else None}
                for m in messages
            ]
        }
    finally:
        session.close()


def send_prompt(payload: dict) -> dict:
    """This still needs the LLM — delegate to the app endpoint."""
    import requests as req
    r = req.post("http://127.0.0.1:8000/chats/{}/prompt".format(payload["chat_id"]),
                 json={"content": payload["message"]}, timeout=120)
    return r.json() if r.ok else {"error": f"{r.status_code}"}


def run_consensus(payload: dict) -> dict:
    from cognitive.consensus_engine import run_consensus as _run
    result = _run(
        prompt=payload.get("message", payload.get("prompt", "")),
        models=payload.get("models"),
    )
    return {
        "final_output": result.final_output,
        "confidence": result.confidence,
        "models_used": result.models_used,
        "individual_responses": result.individual_responses,
        "agreements": result.agreements,
        "disagreements": result.disagreements,
        "total_latency_ms": result.total_latency_ms,
    }


def get_world_model(payload: dict) -> dict:
    try:
        from cognitive.world_model import get_system_state
        return get_system_state()
    except Exception:
        return {"state": "unavailable"}
