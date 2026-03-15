"""
RAG prompt utilities for injecting retrieved context into chat prompts.
"""

from typing import List, Optional

from cognitive.event_bus import subscribe

_latest_ghost_reflection = None


def _on_ghost_reflection(event):
    global _latest_ghost_reflection
    _latest_ghost_reflection = event.data if hasattr(event, 'data') else event


subscribe("ghost.reflection_captured", _on_ghost_reflection)


def build_rag_prompt(user_query: str, context: Optional[str] = None) -> str:
    """
    Build a RAG-augmented prompt by injecting retrieved context
    and ghost memory continuity context.
    
    Args:
        user_query: The original user message/query
        context: Retrieved context from the RAG system (optional)
        
    Returns:
        str: Formatted prompt with context injected
    """
    # ── Wire: Ghost Memory → Prompt (continuity across sessions) ──
    ghost_context = ""
    try:
        from cognitive.ghost_memory import get_ghost_memory, PLAYBOOK_DIR
        ghost = get_ghost_memory()
        # 1. Live RAM cache (current task)
        ghost_ctx = ghost.get_context(max_tokens=400)
        if ghost_ctx:
            ghost_context = ghost_ctx
        # 2. GM-Query: targeted retrieval by user query subject
        gm_results = ghost.gm_query(user_query, time_window_hours=48, epsilon=0.4)
        if gm_results:
            gm_lines = []
            for entry in gm_results[:5]:
                gm_lines.append(f"[ghost:{entry.get('type','?')}] {entry.get('content','')[:150]}")
            ghost_context += ("\n" if ghost_context else "") + "\n".join(gm_lines)
        # 3. Playbook patterns (cross-session continuity from .json reflections)
        if PLAYBOOK_DIR.exists():
            import json
            playbook_lines = []
            for f in sorted(PLAYBOOK_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]:
                try:
                    data = json.loads(f.read_text())
                    playbook_lines.append(
                        f"[playbook:{data.get('pattern_name','?')}] {data.get('task','')[:120]} "
                        f"(confidence={data.get('confidence',0):.1f})"
                    )
                except Exception:
                    pass
            if playbook_lines:
                ghost_context += ("\n" if ghost_context else "") + "\n".join(playbook_lines)
    except Exception:
        pass

    # Inject latest ghost reflection from event bus (real-time wire)
    if _latest_ghost_reflection:
        try:
            summary = _latest_ghost_reflection.get("summary", "")
            if summary:
                ghost_context += ("\n" if ghost_context else "") + f"[ghost:latest_reflection] {summary[:300]}"
        except Exception:
            pass

    if (not context or not context.strip()) and not ghost_context:
        return user_query

    parts = []
    if context and context.strip():
        parts.append(f"<context>\n{context}\n</context>")
    if ghost_context:
        parts.append(f"<ghost_memory>\n{ghost_context}\n</ghost_memory>")

    if not parts:
        return user_query

    combined = "\n\n".join(parts)
    prompt = f"""Based on the following context, answer the user's question:

{combined}

User Question: {user_query}"""
    
    return prompt


def build_rag_system_prompt() -> str:
    """
    Build the system prompt for RAG-augmented responses.
    Strict mode: Only use information from the provided context.
    
    Returns:
        str: System prompt instructing the model to ONLY use provided context
    """
    return """You are a knowledge assistant that ONLY answers questions using the provided context.

CRITICAL RULES:
1. You MUST answer ONLY based on the information provided in the context below
2. You MUST NOT add any information from your training data
3. You MUST NOT make assumptions or inferences beyond what is explicitly stated in the context
4. You MUST NOT provide general knowledge unless it appears in the context
5. If the user's question cannot be directly answered from the context, you MUST say: "I cannot answer this question based on the available knowledge base."
6. Be precise, factual, and cite the context when possible
7. Do not add opinions, interpretations, or information not in the context

Remember: Your role is to convey the knowledge base faithfully, not to generate information."""
