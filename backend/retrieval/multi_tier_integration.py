"""
Multi-tier chat integration helper.

Provides a simplified wrapper to integrate MultiTierQueryHandler
with the existing chat endpoint without major refactoring.
"""

from typing import Dict, Any, Optional, List
import logging
from retrieval.query_intelligence import MultiTierQueryHandler, QueryTier
from database.session import get_session
from datetime import datetime
import contextlib

logger = logging.getLogger(__name__)


def create_multi_tier_handler(llm_client):
    """
    Create a MultiTierQueryHandler instance.
    
    Args:
        llm_client: Ollama client for LLM operations
        
    Returns:
        Configured MultiTierQueryHandler
    """
    # Import here to avoid circular dependency
    from retrieval.retriever import DocumentRetriever
    from embedding import get_embedding_model
    from settings import settings as get_settings
    
    # Get the singleton embedding model
    embedding_model = get_embedding_model()
    
    # Create retriever
    retriever = DocumentRetriever(
        collection_name="documents",
        embedding_model=embedding_model
    )
    
    # Get SerpAPI service if enabled
    serpapi_service = None
    if get_settings and get_settings.SERPAPI_ENABLED and get_settings.SERPAPI_KEY:
        from search.serpapi_service import SerpAPIService
        serpapi_service = SerpAPIService(api_key=get_settings.SERPAPI_KEY)
        logger.info("SerpAPI enabled for internet search (Tier 3)")
    else:
        logger.info("SerpAPI not configured - internet search (Tier 3) disabled")
    
    return MultiTierQueryHandler(
        retriever=retriever,
        llm_client=llm_client,
        serpapi_service=serpapi_service,
        vectordb_quality_threshold=0.6,
        model_confidence_threshold=0.7,
        enable_tier2=True,  # Model knowledge
        enable_tier3=True,  # Internet search
        enable_tier4=True   # Context request
    )


def log_query_handling(
    query_id: str,
    query_text: str,
    tier_result,
    response_time_ms: int,
    user_id: Optional[str] = None,
    genesis_key_id: Optional[str] = None
):
    """
    Log query handling to database for tracking and learning.
    
    Args:
        query_id: Query identifier
        query_text: Original query text
        tier_result: QueryResult from MultiTierQueryHandler
        response_time_ms: Response time in milliseconds
        user_id: Optional user identifier
        genesis_key_id: Optional Genesis Key
    """
    session = None
    try:
        from database.session import SessionLocal
        session = SessionLocal()
        
        # Create query log
        query_log = QueryHandlingLog(
            query_id=query_id,
            query_text=query_text,
            tier_used=tier_result.tier.value,
            confidence_score=tier_result.confidence.overall_score,
            vectordb_attempted=tier_result.tier in [QueryTier.VECTORDB, QueryTier.MODEL_KNOWLEDGE, QueryTier.USER_CONTEXT],
            vectordb_quality=tier_result.confidence.overall_score if tier_result.tier == QueryTier.VECTORDB else None,
            vectordb_result_count=tier_result.confidence.result_count if tier_result.tier == QueryTier.VECTORDB else None,
            model_attempted=tier_result.tier in [QueryTier.MODEL_KNOWLEDGE, QueryTier.USER_CONTEXT],
            model_confidence=tier_result.confidence.overall_score if tier_result.tier == QueryTier.MODEL_KNOWLEDGE else None,
            uncertainty_detected=tier_result.confidence.uncertainty_detected,
            context_requested=tier_result.tier == QueryTier.USER_CONTEXT,
            context_provided=False,
            final_success=tier_result.success,
            response_time_ms=response_time_ms,
            user_id=user_id,
            genesis_key_id=genesis_key_id
        )
        session.add(query_log)
        
        # Create knowledge gap records
        for gap in tier_result.knowledge_gaps:
            knowledge_gap = KnowledgeGap(
                query_id=query_id,
                gap_id=gap.gap_id,
                gap_topic=gap.topic,
                specific_question=gap.specific_question,
                required=gap.required
            )
            session.add(knowledge_gap)
        
        session.commit()
        logger.info(f"Logged query handling for {query_id}: tier={tier_result.tier.value}, confidence={tier_result.confidence.overall_score:.2f}")
        
    except Exception as e:
        logger.error(f"Error logging query handling: {e}")
        if session:
            session.rollback()
    finally:
        if session:
            session.close()


def format_chat_response(tier_result, model_name: str, generation_time: float) -> Dict[str, Any]:
    """
    Format QueryResult into ChatResponse format.
    
    Args:
        tier_result: QueryResult from MultiTierQueryHandler
        model_name: Model name used
        generation_time: Generation time in seconds
        
    Returns:
        Dictionary matching ChatResponse schema
    """
    return {
        "message": tier_result.response,
        "model": model_name,
        "generation_time": generation_time,
        "sources": tier_result.sources,
        "tier": tier_result.tier.value,
        "confidence": tier_result.confidence.overall_score,
        "knowledge_gaps": [gap.to_dict() for gap in tier_result.knowledge_gaps],
        "warnings": tier_result.warnings,
        "prompt_tokens": None,
        "response_tokens": None
    }
