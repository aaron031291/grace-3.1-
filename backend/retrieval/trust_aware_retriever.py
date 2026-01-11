"""
Trust-Aware Document Retriever - Neuro-Symbolic Integration

Extends DocumentRetriever with trust-aware embeddings and trust-weighted similarity.
This creates a neuro-symbolic retrieval system where neural embeddings respect
symbolic trust scores from the knowledge base.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from retrieval.retriever import DocumentRetriever
from ml_intelligence.trust_aware_embedding import TrustAwareEmbeddingModel, TrustContext, get_trust_aware_embedding_model
from embedding.embedder import EmbeddingModel, get_embedding_model

logger = logging.getLogger(__name__)


class TrustAwareDocumentRetriever:
    """
    Trust-aware document retriever that incorporates symbolic trust scores.
    
    This creates neuro-symbolic retrieval where:
    - Neural component: Semantic similarity (from embeddings)
    - Symbolic component: Trust scores (from confidence_score fields)
    - Integrated: Trust-weighted retrieval that respects knowledge confidence
    """
    
    def __init__(
        self,
        base_retriever: Optional[DocumentRetriever] = None,
        trust_weight: float = 0.3,
        min_trust_threshold: float = 0.3,
        embedding_model: Optional[EmbeddingModel] = None,
    ):
        """
        Initialize trust-aware document retriever.
        
        Args:
            base_retriever: Base DocumentRetriever instance (creates new if None)
            trust_weight: Weight of trust in similarity (0-1)
            min_trust_threshold: Minimum trust to include in results
            embedding_model: Base EmbeddingModel (uses singleton if None)
        """
        # Create base retriever if not provided
        if base_retriever is None:
            base_embedding_model = embedding_model or get_embedding_model()
            base_retriever = DocumentRetriever(embedding_model=base_embedding_model)
        
        self.base_retriever = base_retriever
        self.trust_weight = trust_weight
        self.min_trust_threshold = min_trust_threshold
        
        # Create trust-aware embedding model
        self.trust_aware_model = get_trust_aware_embedding_model(
            base_model=base_retriever.embedding_model,
            trust_weight=trust_weight,
            min_trust_threshold=min_trust_threshold,
        )
        
        logger.info(f"[TRUST-AWARE RETRIEVER] Initialized with trust_weight={trust_weight}, min_trust={min_trust_threshold}")
    
    def retrieve(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.3,
        include_metadata: bool = True,
        use_trust_weighting: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents with trust-aware weighting.
        
        Args:
            query: Query text
            limit: Maximum results
            score_threshold: Minimum similarity score
            include_metadata: Include metadata
            use_trust_weighting: Apply trust weighting (if False, uses base retriever)
            
        Returns:
            List of chunks with trust-weighted scores
        """
        # If trust weighting disabled, use base retriever
        if not use_trust_weighting:
            return self.base_retriever.retrieve(
                query=query,
                limit=limit,
                score_threshold=score_threshold,
                include_metadata=include_metadata,
            )
        
        # Get base results
        base_results = self.base_retriever.retrieve(
            query=query,
            limit=limit * 2,  # Get more for trust filtering
            score_threshold=0.0,  # No threshold yet, we'll filter by trust
            include_metadata=include_metadata,
        )
        
        if not base_results:
            return []
        
        # Apply trust weighting
        trust_weighted_results = self._apply_trust_weighting(query, base_results)
        
        # Filter by trust threshold and original score threshold
        filtered_results = [
            r for r in trust_weighted_results
            if r.get("trust_score", 0.0) >= self.min_trust_threshold
            and r.get("score", 0.0) >= score_threshold
        ]
        
        # Sort by trust-weighted score and limit
        filtered_results.sort(key=lambda x: x.get("trust_weighted_score", 0.0), reverse=True)
        
        return filtered_results[:limit]
    
    def _apply_trust_weighting(
        self,
        query: str,
        results: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Apply trust weighting to retrieval results.
        
        Combines neural similarity with symbolic trust scores.
        """
        weighted_results = []
        
        for result in results:
            # Get confidence score from result
            confidence_score = result.get("confidence_score", 0.5) or 0.5
            
            # Create trust context
            trust_context = TrustContext(
                trust_score=confidence_score,
                confidence_score=confidence_score,
                source_reliability=confidence_score,  # Use confidence as proxy
                validation_count=0,  # Could be extracted from metadata if available
                invalidation_count=0,
            )
            
            # Get original similarity score
            original_score = result.get("score", 0.0)
            
            # Calculate trust-weighted score
            # Formula: (1 - trust_weight) * similarity + trust_weight * trust_score
            trust_weighted_score = (
                (1 - self.trust_weight) * original_score +
                self.trust_weight * trust_context.get_effective_trust()
            )
            
            # Update result
            result_copy = result.copy()
            result_copy["trust_score"] = trust_context.get_effective_trust()
            result_copy["trust_weighted_score"] = trust_weighted_score
            result_copy["original_score"] = original_score
            
            # Add trust metadata
            if "metadata" in result_copy:
                result_copy["metadata"]["trust_score"] = trust_context.get_effective_trust()
                result_copy["metadata"]["trust_weighted_score"] = trust_weighted_score
            
            weighted_results.append(result_copy)
        
        return weighted_results
    
    def retrieve_hybrid(
        self,
        query: str,
        limit: int = 5,
        score_threshold: float = 0.3,
        include_metadata: bool = True,
        keyword_weight: float = 0.3,
        use_trust_weighting: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval with trust-aware weighting.
        
        Combines semantic search + keyword matching + trust weighting.
        """
        # Get hybrid results from base retriever
        hybrid_results = self.base_retriever.retrieve_hybrid(
            query=query,
            limit=limit * 2,
            score_threshold=0.0,
            include_metadata=include_metadata,
            keyword_weight=keyword_weight,
        )
        
        if not hybrid_results:
            return []
        
        # Apply trust weighting
        if use_trust_weighting:
            trust_weighted_results = self._apply_trust_weighting(query, hybrid_results)
        else:
            trust_weighted_results = hybrid_results
            for r in trust_weighted_results:
                r["trust_score"] = r.get("confidence_score", 0.5) or 0.5
                r["trust_weighted_score"] = r.get("score", 0.0)
        
        # Filter and sort
        filtered_results = [
            r for r in trust_weighted_results
            if r.get("trust_score", 0.0) >= self.min_trust_threshold
            and r.get("score", 0.0) >= score_threshold
        ]
        
        filtered_results.sort(key=lambda x: x.get("trust_weighted_score", 0.0), reverse=True)
        
        return filtered_results[:limit]
    
    def retrieve_by_document(
        self,
        document_id: int,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Delegate to base retriever."""
        return self.base_retriever.retrieve_by_document(document_id, limit)
    
    def retrieve_by_source(
        self,
        source: str,
        limit: int = 20,
        include_text: bool = True,
    ) -> List[Dict[str, Any]]:
        """Delegate to base retriever."""
        return self.base_retriever.retrieve_by_source(source, limit, include_text)
    
    def build_context(
        self,
        chunks: List[Dict[str, Any]],
        max_length: Optional[int] = None,
        include_sources: bool = True,
    ) -> str:
        """Delegate to base retriever."""
        return self.base_retriever.build_context(chunks, max_length, include_sources)
    
    @property
    def collection_name(self) -> str:
        """Get collection name from base retriever."""
        return self.base_retriever.collection_name
    
    @property
    def embedding_model(self):
        """Get embedding model (trust-aware version)."""
        return self.trust_aware_model
    
    def close(self):
        """Clean up resources."""
        if hasattr(self.base_retriever, 'close'):
            self.base_retriever.close()


def get_trust_aware_retriever(
    base_retriever: Optional[DocumentRetriever] = None,
    trust_weight: float = 0.3,
    min_trust_threshold: float = 0.3,
    embedding_model: Optional[EmbeddingModel] = None,
) -> TrustAwareDocumentRetriever:
    """
    Get trust-aware document retriever instance.
    
    Args:
        base_retriever: Base DocumentRetriever (creates new if None)
        trust_weight: Weight of trust in similarity (0-1)
        min_trust_threshold: Minimum trust to include
        embedding_model: Base EmbeddingModel (uses singleton if None)
        
    Returns:
        TrustAwareDocumentRetriever instance
    """
    return TrustAwareDocumentRetriever(
        base_retriever=base_retriever,
        trust_weight=trust_weight,
        min_trust_threshold=min_trust_threshold,
        embedding_model=embedding_model,
    )
