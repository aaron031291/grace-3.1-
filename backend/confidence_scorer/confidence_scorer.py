"""
Confidence scoring system for knowledge quality assessment.

Calculates confidence scores based on multiple factors:
- source_reliability: Type and trustworthiness of the source
- content_quality: Quality indicators of the content itself
- consensus_score: Agreement with existing knowledge base (with contradiction detection)
- recency: How recent the information is

Formula:
confidence_score = (
    source_reliability * 0.35 +
    content_quality * 0.25 +
    consensus_score * 0.25 +
    recency * 0.10
)

Now includes semantic contradiction detection to prevent contradictory chunks
from artificially boosting consensus scores.

Classes:
- `ConfidenceScorer`

Key Methods:
- `calculate_source_reliability()`
- `calculate_content_quality()`
- `calculate_consensus_score()`
- `calculate_recency()`
- `calculate_confidence_score()`
"""

import logging
import numpy as np
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from embedding import EmbeddingModel
from vector_db.client import get_qdrant_client
from .contradiction_detector import SemanticContradictionDetector

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    Calculates confidence scores for ingested knowledge based on multiple factors.
    """
    
    # Source reliability mapping
    SOURCE_RELIABILITY_SCORES = {
        "official_docs": 0.95,
        "academic_paper": 0.90,
        "verified_tutorial": 0.85,
        "trusted_blog": 0.75,
        "community_qa": 0.65,
        "user_generated": 0.50,
        "unverified": 0.30,
    }
    
    # Weights for each component
    WEIGHTS = {
        "source_reliability": 0.35,
        "content_quality": 0.25,
        "consensus_score": 0.25,
        "recency": 0.10,
    }
    
    def __init__(
        self,
        embedding_model: Optional[EmbeddingModel] = None,
        qdrant_client=None,
        collection_name: str = "documents",
    ):
        """
        Initialize confidence scorer.
        
        Args:
            embedding_model: EmbeddingModel instance for consensus calculation
            qdrant_client: Qdrant client for vector search
            collection_name: Name of the vector collection
        """
        self.embedding_model = embedding_model
        self.qdrant_client = qdrant_client or get_qdrant_client()
        self.collection_name = collection_name
        
        # Initialize semantic contradiction detector
        logger.info("Initializing semantic contradiction detector...")
        self.contradiction_detector = SemanticContradictionDetector(use_gpu=True)
    
    def calculate_source_reliability(self, source_type: str) -> float:
        """
        Calculate source reliability score.
        
        Args:
            source_type: Type of source (official_docs, academic_paper, etc.)
            
        Returns:
            Reliability score between 0.0 and 1.0
        """
        # Normalize source type to match mapping
        normalized_source = source_type.lower().replace(" ", "_").replace("-", "_")
        
        # Return mapped score or default to user_generated
        return self.SOURCE_RELIABILITY_SCORES.get(normalized_source, 0.50)
    
    def calculate_content_quality(self, text_content: str) -> float:
        """
        Calculate content quality score based on various factors.
        
        Factors:
        - Length > 1000 chars: +0.2
        - Has structure (headers, sections): +0.1
        - Contains code/technical content: +0.1
        - Has citations/references: +0.1
        
        Args:
            text_content: The text content to analyze
            
        Returns:
            Quality score between 0.0 and 1.0
        """
        quality_score = 0.0
        
        # Check length (base score)
        if len(text_content) > 1000:
            quality_score += 0.2
        elif len(text_content) > 500:
            quality_score += 0.1
        
        # Check for structure (headers, lists, sections)
        structure_indicators = [
            '#',  # Markdown headers
            '##',
            '###',
            '- ',  # Lists
            '* ',
            '1. ',  # Numbered lists
            'Abstract:',
            'Introduction:',
            'Conclusion:',
            'Summary:',
        ]
        
        has_structure = any(indicator in text_content for indicator in structure_indicators)
        if has_structure:
            quality_score += 0.1
        
        # Check for code/technical content
        code_indicators = [
            '```',
            '`',
            '<?php',
            '<script>',
            'def ',
            'class ',
            'function ',
            'import ',
            'from ',
        ]
        
        has_code = any(indicator in text_content for indicator in code_indicators)
        if has_code:
            quality_score += 0.1
        
        # Check for citations/references
        citation_indicators = [
            '[',  # Markdown links
            '](',
            'http',
            'https',
            'www.',
            'See:',
            'Reference:',
            'Source:',
            'Citation:',
            'et al.',
        ]
        
        has_citations = any(indicator in text_content for indicator in citation_indicators)
        if has_citations:
            quality_score += 0.1
        
        # Cap at 1.0
        return min(quality_score, 1.0)
    
    def calculate_consensus_score(
        self,
        chunk_text: str,
        existing_chunks: Optional[List[str]] = None,
    ) -> Tuple[float, List[float]]:
        """
        Calculate consensus score by comparing with existing knowledge.
        
        Uses cosine similarity to find related chunks in the knowledge base.
        Consensus score is calculated as the mean similarity with related content.
        
        Now includes semantic contradiction detection - if similar chunks contradict,
        the consensus score is reduced instead of boosted.
        
        Args:
            chunk_text: The text chunk to compare
            existing_chunks: Optional list of existing chunks for offline comparison
            
        Returns:
            Tuple of (consensus_score, similarity_scores, contradiction_details)
        """
        if not self.embedding_model:
            logger.warning("Embedding model not available for consensus calculation")
            return 0.5, [], None
        
        try:
            # Generate embedding for the chunk
            chunk_embedding = self.embedding_model.embed_text([chunk_text])[0]
            
            # Search for similar chunks in the vector database
            similarity_results = []
            similarity_scores = []
            trust_scores = []
            
            try:
                # Search with a low threshold to get related content
                results = self.qdrant_client.search_vectors(
                    collection_name=self.collection_name,
                    query_vector=chunk_embedding,
                    limit=5,
                    score_threshold=0.3,  # Low threshold to capture related content
                )
                
                if results:
                    for result in results:
                        score = result.get("score", 0.0)
                        similarity_scores.append(score)
                        # Try to get chunk text and trust score from payload
                        payload = result.get("payload", {})
                        chunk_str = payload.get("text", "")
                        # Get confidence_score from payload (trust score of existing chunk)
                        chunk_trust_score = payload.get("confidence_score", 0.5)
                        trust_scores.append(chunk_trust_score)
                        similarity_results.append((chunk_str, score))
            except Exception as e:
                logger.debug(f"Could not search vector DB for consensus: {e}")
                similarity_scores = []
                trust_scores = []
            
            # If we have existing chunks for offline comparison
            if existing_chunks and len(existing_chunks) > 0:
                try:
                    existing_embeddings = self.embedding_model.embed_text(existing_chunks)
                    
                    for i, emb in enumerate(existing_embeddings):
                        sim = self._cosine_similarity(chunk_embedding, emb)
                        if sim > 0.3:  # Only consider meaningful similarities
                            similarity_scores.append(sim)
                            # For existing chunks, default trust to 0.5 (medium trust)
                            trust_scores.append(0.5)
                            similarity_results.append((existing_chunks[i], sim))
                except Exception as e:
                    logger.debug(f"Error calculating similarity with existing chunks: {e}")
            
            # Use contradiction detector to adjust consensus with trust scores
            if similarity_results:
                consensus_score, contradiction_details = \
                    self.contradiction_detector.adjust_consensus_for_contradictions(
                        chunk_text,
                        similarity_results,
                        trust_scores,
                        threshold=0.7
                    )
                
                if contradiction_details:
                    logger.warning(
                        f"Found {len(contradiction_details)} semantic contradictions "
                        f"while calculating consensus. Adjusted score accordingly."
                    )
                
                return consensus_score, similarity_scores, contradiction_details
            else:
                # No related content found - neutral consensus
                consensus_score = 0.5
                return consensus_score, similarity_scores, None
        
        except Exception as e:
            logger.error(f"Error calculating consensus score: {e}")
            return 0.5, [], None
    
    def calculate_recency(self, created_at: Optional[datetime] = None) -> float:
        """
        Calculate recency score based on when the content was created.
        
        Recent content (< 3 months): 1.0
        Medium age (3-12 months): 0.7
        Old (1-3 years): 0.4
        Very old (> 3 years): 0.2
        
        Args:
            created_at: Datetime when the content was created
            
        Returns:
            Recency score between 0.0 and 1.0
        """
        if created_at is None:
            created_at = datetime.now()
        
        # Ensure we're working with timezone-naive datetimes
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)
        
        now = datetime.now()
        age_days = (now - created_at).days
        
        if age_days <= 90:  # 3 months
            return 1.0
        elif age_days <= 365:  # 1 year
            return 0.7
        elif age_days <= 1095:  # 3 years
            return 0.4
        else:
            return 0.2
    
    def calculate_confidence_score(
        self,
        text_content: str,
        source_type: str = "user_generated",
        created_at: Optional[datetime] = None,
        existing_chunks: Optional[List[str]] = None,
    ) -> Dict[str, any]:
        """
        Calculate overall confidence score for a chunk or document.
        
        Includes semantic contradiction detection - if contradictory content is found,
        the consensus score and overall confidence are reduced accordingly.
        
        Args:
            text_content: The text content
            source_type: Type of source (e.g., "user_generated", "official_docs")
            created_at: When the content was created
            existing_chunks: Optional list of existing chunks for consensus calculation
            
        Returns:
            Dictionary with all component scores, final confidence_score, and contradiction details
        """
        # Calculate individual components
        source_reliability = self.calculate_source_reliability(source_type)
        content_quality = self.calculate_content_quality(text_content)
        
        # New: calculate_consensus_score now returns 3 values including contradiction_details
        consensus_score, similarities, contradiction_details = self.calculate_consensus_score(
            text_content, 
            existing_chunks
        )
        recency = self.calculate_recency(created_at)
        
        # Calculate weighted confidence score
        confidence_score = (
            source_reliability * self.WEIGHTS["source_reliability"] +
            content_quality * self.WEIGHTS["content_quality"] +
            consensus_score * self.WEIGHTS["consensus_score"] +
            recency * self.WEIGHTS["recency"]
        )
        
        # Ensure it's between 0 and 1
        confidence_score = max(0.0, min(1.0, confidence_score))
        
        # Build result dictionary
        result = {
            "confidence_score": confidence_score,
            "source_reliability": source_reliability,
            "content_quality": content_quality,
            "consensus_score": consensus_score,
            "recency": recency,
            "similarity_scores": similarities,
        }
        
        # Add contradiction information if found
        if contradiction_details:
            result["contradictions_detected"] = True
            result["contradiction_count"] = len(contradiction_details)
            result["contradiction_details"] = contradiction_details
            logger.warning(
                f"Contradiction detected during confidence scoring: "
                f"{len(contradiction_details)} contradiction(s) found. "
                f"Confidence score reduced from potential maximum."
            )
        else:
            result["contradictions_detected"] = False
            result["contradiction_count"] = 0

        # Feed confidence scoring results to LLM learning tracker
        try:
            from cognitive.llm_interaction_tracker import get_llm_interaction_tracker
            from database.session import SessionLocal
            _cs_session = SessionLocal()
            _cs_tracker = get_llm_interaction_tracker(_cs_session)
            _cs_tracker.record_interaction(
                prompt=f"[CONFIDENCE_SCORE] source={source_type}, len={len(text_content)}",
                response=f"score={confidence_score:.3f}, quality={content_quality:.3f}, consensus={consensus_score:.3f}",
                model_used="confidence_scorer",
                interaction_type="reasoning",
                outcome="success" if confidence_score >= 0.5 else "failure",
                confidence_score=confidence_score,
                metadata={
                    "source_type": source_type,
                    "content_quality": content_quality,
                    "consensus_score": consensus_score,
                    "contradictions": result.get("contradiction_count", 0),
                },
            )
            _cs_session.commit()
            _cs_session.close()
        except Exception:
            pass  # Non-blocking
        
        return result
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            a: First vector
            b: Second vector
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        try:
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = float(dot_product / (norm_a * norm_b))
            # Clamp to [0, 1] in case of numerical issues
            return max(0.0, min(1.0, similarity))
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {e}")
            return 0.0
