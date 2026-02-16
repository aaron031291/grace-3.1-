"""
Magma Chat Integration

Wires Magma's intent-aware retrieval into Grace's chat endpoints.
Instead of using the basic retriever, chat queries go through:
1. Magma's intent classifier (what type of question is this?)
2. Graph-based retrieval (semantic + temporal + causal + entity)
3. RRF fusion (combine results from multiple graphs)
4. Context synthesis (generate LLM-ready context)

This replaces the basic retriever in the multi-tier integration.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def get_magma_enhanced_context(query: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """
    Get enhanced context for a chat query using Magma memory.
    
    Falls back gracefully to None if Magma is not available,
    allowing the existing retriever to handle the query.
    
    Args:
        query: The user's question
        limit: Max number of context chunks
        
    Returns:
        Dict with 'context' string and 'sources' list, or None
    """
    try:
        from cognitive.magma import get_grace_magma
        magma = get_grace_magma()
        
        results = magma.query(query=query, limit=limit)
        
        if not results:
            return None
        
        context = magma.get_context(results, query=query)
        
        if not context or len(context.strip()) < 10:
            return None
        
        sources = []
        for r in results:
            sources.append({
                "text": getattr(r, 'content', str(r))[:200],
                "score": getattr(r, 'score', 0.0),
                "graph": getattr(r, 'graph', 'unknown'),
                "source": "magma_memory",
            })
        
        logger.info(
            f"[MAGMA-CHAT] Enhanced context for query: "
            f"{len(results)} results, {len(context)} chars"
        )
        
        return {
            "context": context,
            "sources": sources,
            "result_count": len(results),
        }
        
    except Exception as e:
        logger.debug(f"[MAGMA-CHAT] Magma context not available: {e}")
        return None


def enrich_rag_context(existing_context: str, query: str) -> str:
    """
    Enrich existing RAG context with Magma graph memory.
    
    Combines standard vector retrieval with Magma's graph-based
    retrieval for deeper context.
    
    Args:
        existing_context: Context from standard RAG retriever
        query: The user's question
        
    Returns:
        Enriched context string
    """
    magma_result = get_magma_enhanced_context(query, limit=3)
    
    if not magma_result:
        return existing_context
    
    magma_context = magma_result["context"]
    
    enriched = existing_context
    if magma_context:
        enriched += "\n\n[Graph Memory Context]\n" + magma_context
    
    return enriched


def ingest_chat_interaction(user_query: str, assistant_response: str, sources: List = None):
    """
    Feed a chat interaction back into Magma memory for learning.
    
    Every chat interaction makes Grace smarter by building
    her relation graphs.
    """
    try:
        from cognitive.magma import get_grace_magma
        magma = get_grace_magma()
        
        content = f"Q: {user_query}\nA: {assistant_response[:500]}"
        magma.ingest(content, source="chat_interaction")
        
        logger.debug(f"[MAGMA-CHAT] Ingested chat interaction ({len(content)} chars)")
    except Exception as e:
        logger.debug(f"[MAGMA-CHAT] Chat ingestion failed: {e}")
