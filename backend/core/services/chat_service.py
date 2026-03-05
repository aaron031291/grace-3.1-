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
    """Send prompt through the LLM pipeline directly."""
    from models.repositories import ChatRepository, ChatHistoryRepository
    from llm_orchestrator.factory import get_llm_client
    import time as _time

    factory = get_session_factory()
    session = factory()
    try:
        chat_repo = ChatRepository(session)
        history_repo = ChatHistoryRepository(session)

        chat = chat_repo.get(payload["chat_id"])
        if not chat:
            return {"error": "Chat not found"}

        user_msg = history_repo.add_message(
            chat_id=payload["chat_id"], role="user", content=payload["message"]
        )

        # Track user input as learnable event
        try:
            from api._genesis_tracker import track
            track(
                key_type="user_input",
                what=f"User message: {payload['message'][:100]}",
                who="chat_service",
                input_data={"message": payload["message"][:500], "chat_id": payload["chat_id"]},
                tags=["user_input", "chat"],
            )
        except Exception:
            pass

        client = get_llm_client()
        start = _time.time()
        response = client.chat(
            model=chat.model,
            messages=[
                {"role": "system", "content": "You are Grace, a helpful AI assistant."},
                {"role": "user", "content": payload["message"]},
            ],
            stream=False,
            temperature=chat.temperature or 0.7,
        )
        gen_time = _time.time() - start

        assistant_msg = history_repo.add_message(
            chat_id=payload["chat_id"], role="assistant",
            content=response if isinstance(response, str) else str(response),
        )
        session.commit()

        return {
            "chat_id": payload["chat_id"],
            "message": response if isinstance(response, str) else str(response),
            "model": chat.model,
            "generation_time": round(gen_time, 2),
        }
    except Exception as e:
        session.rollback()
        return {"error": str(e)[:200]}
    finally:
        session.close()


def run_consensus(payload: dict) -> dict:
    from cognitive.consensus_engine import run_consensus as _run
    prompt = payload.get("message", payload.get("prompt", ""))

    # Track user input
    try:
        from api._genesis_tracker import track
        track(key_type="user_input", what=f"Consensus query: {prompt[:100]}",
              who="chat_service.consensus", input_data={"prompt": prompt[:500]},
              tags=["user_input", "consensus"])
    except Exception:
        pass

    result = _run(prompt=prompt, models=payload.get("models"))

    # Track consensus output as learnable event
    try:
        from api._genesis_tracker import track
        track(
            key_type="ai_response",
            what=f"Consensus output: {result.final_output[:100]}",
            who="consensus_engine",
            input_data={"prompt": prompt[:200], "models": result.models_used},
            output_data={
                "output": result.final_output[:500],
                "confidence": result.confidence,
                "agreements": len(result.agreements),
                "disagreements": len(result.disagreements),
            },
            tags=["consensus", "ai_response", "learning_signal"],
        )
    except Exception:
        pass

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
        from cognitive.system_registry import get_system_registry
        registry = get_system_registry()
        return {"state": "active", "components": registry.get_all()}
    except Exception:
        return {"state": "unavailable"}
