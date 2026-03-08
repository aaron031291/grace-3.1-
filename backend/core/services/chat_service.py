"""Chat domain service — direct function calls, no HTTP.

Unified conversational spine: RAG + unified memory (episodic recall) + LLM.
"""

from typing import Dict, Any, Optional, List
from database.session import session_scope, get_session_factory


def _get_rag_context(query: str, limit: int = 5, score_threshold: float = 0.3) -> str:
    """Retrieve relevant chunks and build context string. Returns '' on failure."""
    try:
        from embedding import get_embedding_model
        from retrieval.retriever import DocumentRetriever
        model = get_embedding_model()
        retriever = DocumentRetriever(collection_name="documents", embedding_model=model)
        chunks = retriever.retrieve(
            query=query,
            limit=limit,
            score_threshold=score_threshold,
            include_metadata=True,
        )
        if not chunks:
            return ""
        return retriever.build_context(chunks, max_length=6000, include_sources=True)
    except Exception:
        return ""


def _get_episodic_recall(problem: str, k: int = 3, min_trust: float = 0.5) -> str:
    """Recall similar past episodes from unified memory. Returns '' on failure."""
    try:
        with session_scope() as sess:
            from core.memory.unified_memory import UnifiedMemory
            mem = UnifiedMemory(sess)
            episodes = mem.recall_similar(problem, k=k, min_trust=min_trust)
            if not episodes:
                return ""
            parts = []
            for i, ep in enumerate(episodes[:k], 1):
                if hasattr(ep, "problem") and hasattr(ep, "outcome"):
                    parts.append(f"[Past {i}] Problem: {str(ep.problem)[:200]}\nOutcome: {str(ep.outcome)[:200]}")
                elif isinstance(ep, dict):
                    parts.append(f"[Past {i}] {str(ep)[:300]}")
            return "\n".join(parts) if parts else ""
    except Exception:
        return ""


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
            model=payload.get("model", "qwen3:14b"),
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


def send_prompt_with_rag(payload: dict) -> dict:
    """Send prompt with RAG context and unified memory (episodic recall). Single conversational spine."""
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

        message = payload.get("message", "")
        history_repo.add_message(chat_id=payload["chat_id"], role="user", content=message)

        try:
            from api._genesis_tracker import track
            track(
                key_type="user_input",
                what=f"User message: {message[:100]}",
                who="chat_service",
                input_data={"message": message[:500], "chat_id": payload["chat_id"]},
                tags=["user_input", "chat", "rag"],
            )
        except Exception:
            pass

        rag_ctx = _get_rag_context(message, limit=5, score_threshold=0.3)
        episode_ctx = _get_episodic_recall(message, k=3, min_trust=0.5)
        system_parts = ["You are Grace, a helpful AI assistant."]
        if rag_ctx:
            system_parts.append("Relevant context from the knowledge base:\n" + rag_ctx)
        if episode_ctx:
            system_parts.append("Relevant past experience (use when helpful):\n" + episode_ctx)
        system_content = "\n\n".join(system_parts)

        recent = history_repo.get_by_chat_reverse(payload["chat_id"], skip=0, limit=10)
        messages = [{"role": "system", "content": system_content}]
        for m in reversed(recent):
            messages.append({"role": m.role, "content": m.content or ""})

        client = get_llm_client()
        start = _time.time()
        response = client.chat(
            model=chat.model,
            messages=messages,
            stream=False,
            temperature=chat.temperature or 0.7,
        )
        gen_time = _time.time() - start

        assistant_msg = history_repo.add_message(
            chat_id=payload["chat_id"], role="assistant",
            content=response if isinstance(response, str) else str(response),
        )
        session.commit()

        try:
            from core.kpi_recorder import record_component_kpi
            record_component_kpi("rag", "requests", 1.0, success=True)
        except Exception:
            pass
        return {
            "chat_id": payload["chat_id"],
            "message": response if isinstance(response, str) else str(response),
            "model": chat.model,
            "generation_time": round(gen_time, 2),
            "used_rag": bool(rag_ctx),
            "used_memory": bool(episode_ctx),
        }
    except Exception as e:
        session.rollback()
        try:
            from core.kpi_recorder import record_component_kpi
            record_component_kpi("rag", "requests", 1.0, success=False)
        except Exception:
            pass
        return {"error": str(e)[:200]}
    finally:
        session.close()


def send_prompt(payload: dict) -> dict:
    """Send prompt through the LLM pipeline. Uses RAG + unified memory when use_rag is True (default)."""
    use_rag = payload.get("use_rag", True)
    if use_rag:
        return send_prompt_with_rag(payload)
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
        history_repo.add_message(chat_id=payload["chat_id"], role="user", content=payload["message"])
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
        history_repo.add_message(
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
        from cognitive.world_model import get_system_state
        return get_system_state()
    except Exception:
        return {"state": "unavailable"}
