"""
Multi-Tier Query Intelligence System

Orchestrates intelligent query handling with three-tier fallback:
1. Tier 1 - VectorDB Search: Query Qdrant for relevant information
2. Tier 2 - Model Knowledge: Use model's built-in knowledge if VectorDB fails
3. Tier 3 - User Context Request: Request specific context from user

Each tier has quality/confidence thresholds that trigger fallback to next tier.

Classes:
- `QueryTier`
- `ConfidenceMetrics`
- `KnowledgeGap`
- `QueryResult`
- `MultiTierQueryHandler`

Key Methods:
- `is_high_quality()`
- `to_dict()`
- `to_dict()`
- `handle_query()`

Connects To:
- `embedding`
- `ingestion.service`
- `retrieval.reranker`
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
import uuid
import time

try:
    from settings import settings
except ImportError:
    settings = None

logger = logging.getLogger(__name__)


class QueryTier(Enum):
    """Query handling tiers."""
    VECTORDB = "VECTORDB"
    MODEL_KNOWLEDGE = "MODEL_KNOWLEDGE"
    INTERNET_SEARCH = "INTERNET_SEARCH"
    USER_CONTEXT = "USER_CONTEXT"


@dataclass
class ConfidenceMetrics:
    """
    Confidence and quality metrics for query results.
    
    Attributes:
        overall_score: Overall confidence score (0.0-1.0)
        result_count: Number of results returned
        avg_similarity: Average similarity score
        score_variance: Variance in similarity scores
        coverage_score: How well results cover the query
        uncertainty_detected: Whether uncertainty signals were found
    """
    overall_score: float = 0.0
    result_count: int = 0
    avg_similarity: float = 0.0
    score_variance: float = 0.0
    coverage_score: float = 0.0
    uncertainty_detected: bool = False
    
    def is_high_quality(self, threshold: float = 0.7) -> bool:
        """Check if metrics indicate high quality results."""
        return self.overall_score >= threshold


@dataclass
class KnowledgeGap:
    """
    Represents a specific piece of missing information.
    
    Attributes:
        gap_id: Unique identifier for this gap
        topic: General topic area of the gap
        specific_question: Specific question to ask user
        required: Whether this gap must be filled
        suggestions: Optional suggestions for user
    """
    gap_id: str
    topic: str
    specific_question: str
    required: bool = True
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "gap_id": self.gap_id,
            "topic": self.topic,
            "specific_question": self.specific_question,
            "required": self.required,
            "suggestions": self.suggestions
        }


@dataclass
class QueryResult:
    """
    Unified result structure for all query tiers.
    
    Attributes:
        tier: Which tier was used
        success: Whether query was successfully answered
        response: The generated response text
        confidence: Confidence metrics
        sources: Source chunks (for Tier 1)
        knowledge_gaps: Identified gaps (for Tier 3)
        warnings: Any warnings to display to user
        metadata: Additional metadata
    """
    tier: QueryTier
    success: bool
    response: str
    confidence: ConfidenceMetrics
    sources: List[Dict[str, Any]] = field(default_factory=list)
    knowledge_gaps: List[KnowledgeGap] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "tier": self.tier.value,
            "success": self.success,
            "response": self.response,
            "confidence": self.confidence.overall_score,
            "sources": self.sources,
            "knowledge_gaps": [gap.to_dict() for gap in self.knowledge_gaps],
            "warnings": self.warnings,
            "metadata": self.metadata
        }


class MultiTierQueryHandler:
    """
    Central orchestrator for multi-tier query handling.
    
    Implements intelligent fallback logic:
    - Try VectorDB first (Tier 1)
    - Fall back to model knowledge if VectorDB quality is low (Tier 2)
    - Request user context if model confidence is low (Tier 3)
    
    Each tier has configurable quality/confidence thresholds.
    """
    
    def __init__(
        self,
        retriever,
        llm_client,
        serpapi_service=None,
        vectordb_quality_threshold: float = 0.6,
        model_confidence_threshold: float = 0.7,
        enable_tier2: bool = True,
        enable_tier3: bool = True,
        enable_tier4: bool = True
    ):
        """
        Initialize multi-tier query handler.
        
        Args:
            retriever: DocumentRetriever instance for Tier 1
            llm_client: LLM client for Tier 2 & 3
            serpapi_service: SerpAPI service for Tier 3 (internet search)
            vectordb_quality_threshold: Minimum quality for Tier 1 success
            model_confidence_threshold: Minimum confidence for Tier 2 success
            enable_tier2: Enable Tier 2 (model knowledge)
            enable_tier3: Enable Tier 3 (internet search)
            enable_tier4: Enable Tier 4 (context requests)
        """
        self.retriever = retriever
        self.llm_client = llm_client
        self.serpapi_service = serpapi_service
        self.vectordb_quality_threshold = vectordb_quality_threshold
        self.model_confidence_threshold = model_confidence_threshold
        self.enable_tier2 = enable_tier2
        self.enable_tier3 = enable_tier3
        self.enable_tier4 = enable_tier4
        
        logger.info(
            f"MultiTierQueryHandler initialized: "
            f"T1_threshold={vectordb_quality_threshold}, "
            f"T2_threshold={model_confidence_threshold}, "
            f"T2_enabled={enable_tier2}, T3_enabled={enable_tier3}, T4_enabled={enable_tier4}"
        )
    
    def handle_query(
        self,
        query: str,
        user_id: Optional[str] = None,
        genesis_key_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None  # NEW: Conversation context
    ) -> QueryResult:
        """
        Main entry point for query handling.
        
        Executes tier fallback logic:
        1. Try VectorDB (Tier 1)
        2. If quality low, try model knowledge (Tier 2)
        3. If confidence low, request user context (Tier 3)
        
        Args:
            query: User query text
            user_id: Optional user identifier
            genesis_key_id: Optional Genesis Key for tracking
            context: Optional user-provided context from previous Tier 3 request
            conversation_history: Optional conversation history for context-aware responses
            
        Returns:
            QueryResult with response and metadata
        """
        query_id = f"q_{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        
        logger.info(f"[{query_id}] Handling query: {query[:100]}...")
        
        # Log conversation context if available
        if conversation_history:
            logger.info(f"[{query_id}] Using conversation context with {len(conversation_history)} messages")
        
        # If context provided, integrate it
        if context:
            logger.info(f"[{query_id}] User context provided, integrating...")
            # TODO: Implement context integration
            # For now, just add to query
            query = f"{query}\n\nContext: {context.get('text', '')}"
        
        # ==================== MODEL-FIRST STRATEGY ====================
        # Try Model Knowledge FIRST (Tier 2)
        tier2_result = None
        if self.enable_tier2:
            logger.info(f"[{query_id}] Trying Model Knowledge first...")
            tier2_result = self._try_model_knowledge(query, query_id, None, conversation_history)
            
            # Check if model is confident and certain
            if tier2_result.success and tier2_result.confidence.is_high_quality(self.model_confidence_threshold):
                # Model is confident - use its response
                logger.info(f"[{query_id}] ✅ Model Knowledge succeeded with confidence {tier2_result.confidence.overall_score:.2f}")
                tier2_result.metadata["query_id"] = query_id
                tier2_result.metadata["response_time_ms"] = int((time.time() - start_time) * 1000)
                return tier2_result
            
            logger.info(
                f"[{query_id}] Model uncertain (confidence {tier2_result.confidence.overall_score:.2f}), "
                f"trying internet search..."
            )
        
        # Model uncertain or disabled - Try Internet Search (Tier 3)
        if self.enable_tier3 and self.serpapi_service:
            if self._should_use_internet_search(query, tier2_result):
                logger.info(f"[{query_id}] Attempting internet search for current/factual info...")
                tier3_result = self._try_internet_search(query, query_id)
                
                if tier3_result.success and len(tier3_result.sources) > 0:
                    logger.info(f"[{query_id}] ✅ Internet Search succeeded with {len(tier3_result.sources)} results")
                    tier3_result.metadata["query_id"] = query_id
                    tier3_result.metadata["response_time_ms"] = int((time.time() - start_time) * 1000)
                    return tier3_result
                
                logger.info(f"[{query_id}] Internet search found no results, requesting user context...")
            else:
                logger.info(f"[{query_id}] Query doesn't need internet search, requesting user context...")
        
        # Internet search failed or disabled - Request User Context (Tier 4)
        if self.enable_tier4:
            logger.info(f"[{query_id}] Requesting user to provide context...")
            # Try VectorDB to see what we have (for context)
            tier1_result = self._try_vectordb(query, query_id)
            tier4_result = self._request_user_context(query, query_id, tier1_result)
            tier4_result.metadata["query_id"] = query_id
            tier4_result.metadata["response_time_ms"] = int((time.time() - start_time) * 1000)
            return tier4_result
        
        # All tiers failed or disabled
        logger.warning(f"[{query_id}] All tiers failed or disabled")
        return QueryResult(
            tier=QueryTier.MODEL_KNOWLEDGE,
            success=False,
            response="I cannot answer this question with the available information.",
            confidence=ConfidenceMetrics(overall_score=0.0),
            warnings=["No relevant information found"],
            metadata={"query_id": query_id, "response_time_ms": int((time.time() - start_time) * 1000)}
        )
    
    def _try_vectordb(self, query: str, query_id: str) -> QueryResult:
        """
        Tier 1: Try VectorDB retrieval.
        
        Args:
            query: User query
            query_id: Query identifier
            
        Returns:
            QueryResult with VectorDB results and quality metrics
        """
        try:
            # Retrieve from VectorDB
            chunks = self.retriever.retrieve(
                query=query,
                limit=10,  # Retrieve more candidates for reranking
                include_metadata=True
            )

            # Rerank results using cross-encoder for better relevance
            try:
                from retrieval.reranker import get_reranker
                reranker = get_reranker()
                if reranker and chunks:
                    chunks = reranker.rerank(query, chunks, top_k=5)
                    logger.debug(f"[TIER1] Reranked {len(chunks)} chunks")
            except Exception as _rr_err:
                logger.debug(f"[TIER1] Reranker not available: {_rr_err}")
                chunks = chunks[:5]  # Fallback: take top 5 by raw similarity
            
            # Assess quality
            quality_metrics = self._assess_vectordb_quality(chunks, query)
            
            if not chunks or quality_metrics.overall_score < 0.3:
                return QueryResult(
                    tier=QueryTier.VECTORDB,
                    success=False,
                    response="",
                    confidence=quality_metrics,
                    sources=[]
                )
            
            # Build context from chunks
            context = self.retriever.build_context(chunks, include_sources=True)
            
            # Prepare sources for response
            sources = [
                {
                    "text": chunk["text"],
                    "score": chunk.get("score", 0),
                    "chunk_id": chunk.get("chunk_id"),
                    "document_id": chunk.get("document_id"),
                    "filename": chunk.get("metadata", {}).get("filename", "Unknown"),
                    "source": chunk.get("metadata", {}).get("source", "Unknown"),
                }
                for chunk in chunks
            ]
            
            # Generate response with RAG context
            response = self._generate_rag_response(query, context)
            
            return QueryResult(
                tier=QueryTier.VECTORDB,
                success=True,
                response=response,
                confidence=quality_metrics,
                sources=sources
            )
            
        except Exception as e:
            logger.error(f"[{query_id}] Tier 1 error: {e}")
            return QueryResult(
                tier=QueryTier.VECTORDB,
                success=False,
                response="",
                confidence=ConfidenceMetrics(overall_score=0.0),
                warnings=[f"VectorDB error: {str(e)}"]
            )
    
    def _try_model_knowledge(
        self,
        query: str,
        query_id: str,
        tier1_result: QueryResult,
        conversation_history: Optional[List[Dict[str, str]]] = None  # NEW
    ) -> QueryResult:
        """
        Tier 2: Try model's built-in knowledge.
        
        Args:
            query: User query
            query_id: Query identifier
            tier1_result: Result from Tier 1 (may have partial info)
            conversation_history: Optional conversation history for context
            
        Returns:
            QueryResult with model-generated response and confidence
        """
        try:
            # Generate response using model knowledge (with conversation context)
            response = self._generate_model_response(query, conversation_history)
            
            # Assess confidence
            confidence_metrics = self._assess_model_confidence(response, query)
            
            # Add warning about non-KB source
            warnings = [
                "This answer is based on the AI model's general knowledge, not your knowledge base. "
                "It may not be specific to your context."
            ]
            
            return QueryResult(
                tier=QueryTier.MODEL_KNOWLEDGE,
                success=True,
                response=response,
                confidence=confidence_metrics,
                warnings=warnings,
                sources=[]
            )
            
        except Exception as e:
            logger.error(f"[{query_id}] Tier 2 error: {e}")
            return QueryResult(
                tier=QueryTier.MODEL_KNOWLEDGE,
                success=False,
                response="",
                confidence=ConfidenceMetrics(overall_score=0.0),
                warnings=[f"Model error: {str(e)}"]
            )
    
    
    def _should_use_internet_search(
        self,
        query: str,
        tier2_result: Optional[QueryResult]
    ) -> bool:
        """
        Determine if internet search is appropriate for this query.
        
        Internet search is useful for:
        - Current events, news, recent information
        - Factual lookups (people, places, companies, products)
        - Technical documentation, APIs, libraries
        - Questions the model explicitly says it doesn't know
        
        NOT useful for:
        - Personal/contextual questions
        - Opinion-based questions
        - Questions about user's specific setup/environment
        
        Args:
            query: User query
            tier2_result: Result from Tier 2 (model knowledge)
            
        Returns:
            True if internet search should be attempted
        """
        query_lower = query.lower()
        
        # Check if model explicitly said it doesn't know
        if tier2_result and tier2_result.response:
            response_lower = tier2_result.response.lower()
            dont_know_phrases = [
                "i don't know", "i'm not sure", "i don't have information",
                "i cannot provide", "i don't have access", "i'm not aware",
                "no information available", "cannot find", "don't have data"
            ]
            if any(phrase in response_lower for phrase in dont_know_phrases):
                logger.info("Model explicitly indicated lack of knowledge - internet search appropriate")
                return True
        
        # Indicators that internet search would be useful
        current_info_keywords = [
            "latest", "recent", "current", "today", "now", "2024", "2025", "2026",
            "news", "update", "new version", "release"
        ]
        
        factual_keywords = [
            "who is", "what is", "where is", "when did", "how to",
            "documentation", "api", "library", "framework", "tutorial",
            "company", "product", "service", "website"
        ]
        
        # Check for current information needs
        if any(keyword in query_lower for keyword in current_info_keywords):
            logger.info(f"Query contains current info keywords - internet search appropriate")
            return True
        
        # Check for factual lookups
        if any(keyword in query_lower for keyword in factual_keywords):
            logger.info(f"Query appears to be factual lookup - internet search appropriate")
            return True
        
        # Indicators that internet search is NOT appropriate
        personal_keywords = [
            "my", "our", "this project", "this code", "this system",
            "how do i", "should i", "can i", "configure", "setup my"
        ]
        
        if any(keyword in query_lower for keyword in personal_keywords):
            logger.info(f"Query appears personal/contextual - internet search NOT appropriate")
            return False
        
        # Default: if model had low confidence and no personal context, try internet
        if tier2_result and tier2_result.confidence.overall_score < 0.5:
            logger.info(f"Model confidence very low ({tier2_result.confidence.overall_score:.2f}) - trying internet search")
            return True
        
        return False
    
    def _try_internet_search(
        self,
        query: str,
        query_id: str
    ) -> QueryResult:
        """
        Tier 3: Try internet search via SerpAPI.
        
        Args:
            query: User query
            query_id: Query identifier
            
        Returns:
            QueryResult with internet search results
        """
        try:
            if not self.serpapi_service:
                return QueryResult(
                    tier=QueryTier.INTERNET_SEARCH,
                    success=False,
                    response="",
                    confidence=ConfidenceMetrics(overall_score=0.0),
                    warnings=["Internet search not configured"]
                )
            
            # Search the internet
            search_results = self.serpapi_service.search(query=query, num_results=5)
            
            if not search_results:
                return QueryResult(
                    tier=QueryTier.INTERNET_SEARCH,
                    success=False,
                    response="",
                    confidence=ConfidenceMetrics(overall_score=0.0),
                    sources=[]
                )
            
            # Build context from search results
            context_parts = []
            sources = []
            
            for idx, result in enumerate(search_results, 1):
                title = result.get("title", "")
                snippet = result.get("snippet", "")
                link = result.get("link", "")
                
                if snippet:
                    context_parts.append(f"[Source {idx}: {title}]\n{snippet}")
                    sources.append({
                        "text": snippet,
                        "score": 1.0 - (idx * 0.1),  # Decreasing score by position
                        "chunk_id": None,
                        "document_id": None,
                        "filename": title,
                        "source": link,
                        "upload_method": "internet_search"
                    })
            
            if not context_parts:
                return QueryResult(
                    tier=QueryTier.INTERNET_SEARCH,
                    success=False,
                    response="",
                    confidence=ConfidenceMetrics(overall_score=0.0),
                    sources=[]
                )
            
            context = "\n\n".join(context_parts)
            
            # Generate response using internet search context
            response = self._generate_rag_response(query, context)
            
            # ==================== AUTO-INGEST SEARCH RESULTS ====================
            # Save search results to knowledge base so they're available for future queries
            try:
                logger.info(f"[{query_id}] Auto-ingesting {len(search_results)} internet search results...")
                self._ingest_search_results(query, search_results, query_id)
                logger.info(f"[{query_id}] [OK] Search results ingested successfully")
            except Exception as ingest_error:
                logger.warning(f"[{query_id}] Failed to ingest search results: {ingest_error}")
                # Don't fail the query if ingestion fails, just log it
            
            # Add warning about internet source
            warnings = [
                "This answer is based on current internet search results. "
                "Information may not be verified or specific to your context.",
                "✓ Search results have been saved to your knowledge base for future reference."
            ]
            
            return QueryResult(
                tier=QueryTier.INTERNET_SEARCH,
                success=True,
                response=response,
                confidence=ConfidenceMetrics(overall_score=0.8, result_count=len(sources)),
                sources=sources,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"[{query_id}] Tier 3 (Internet Search) error: {e}")
            return QueryResult(
                tier=QueryTier.INTERNET_SEARCH,
                success=False,
                response="",
                confidence=ConfidenceMetrics(overall_score=0.0),
                warnings=[f"Internet search error: {str(e)}"]
            )
    
    def _ingest_search_results(
        self,
        query: str,
        search_results: List[Dict[str, Any]],
        query_id: str
    ) -> None:
        """
        Ingest internet search results into the knowledge base.
        
        This saves the search results so they're available for future queries,
        preventing repeated internet searches for the same information.
        
        Args:
            query: Original search query
            search_results: List of search results from SerpAPI
            query_id: Query identifier for logging
        """
        try:
            # Import ingestion service
            from ingestion.service import TextIngestionService
            from embedding import get_embedding_model  # Get global singleton
            import datetime
            
            # CRITICAL: Use global singleton embedding model to prevent unload
            # The singleton is kept alive for the entire application lifecycle
            embedding_model = get_embedding_model()
            
            # Create ingestion service with singleton model
            ingestion_service = TextIngestionService(
                collection_name="documents",
                embedding_model=embedding_model
            )
            
            # Ingest each search result directly (no file creation needed)
            for idx, result in enumerate(search_results, 1):
                title = result.get("title", f"Result_{idx}")
                snippet = result.get("snippet", "")
                link = result.get("link", "")
                
                if not snippet:
                    continue
                
                # Create content with metadata
                content = f"""# {title}

Source: {link}
Query: {query}
Retrieved: {datetime.datetime.now().isoformat()}

---

{snippet}
"""
                
                # Create safe filename
                safe_title = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in title)
                safe_title = safe_title[:100]
                filename = f"internet_search_{safe_title}.txt"
                
                # Ingest directly into VectorDB (bypasses file watcher)
                doc_id, status = ingestion_service.ingest_text_fast(
                    text_content=content,
                    filename=filename,
                    source=link,
                    upload_method="internet_search",
                    source_type="internet_search",
                    description=f"Internet search result for query: {query}",
                    tags=["internet_search", "auto_ingested"],
                    metadata={
                        "query": query,
                        "search_position": idx,
                        "link": link,
                        "title": title
                    }
                )
                
                if doc_id:
                    logger.info(f"[{query_id}] Ingested search result {idx}: {title} (doc_id={doc_id})")
                else:
                    logger.warning(f"[{query_id}] Failed to ingest search result {idx}: {status}")
            
            logger.info(f"[{query_id}] Successfully ingested {len(search_results)} search results directly into VectorDB")
            
        except Exception as e:
            logger.error(f"[{query_id}] Error ingesting search results: {e}", exc_info=True)
            raise
    
    def _request_user_context(
        self,
        query: str,
        query_id: str,
        tier1_result: QueryResult
    ) -> QueryResult:
        """
        Tier 3: Request specific context from user.
        
        Args:
            query: User query
            query_id: Query identifier
            tier1_result: Result from Tier 1 (may have partial info)
            
        Returns:
            QueryResult with context request
        """
        # Identify knowledge gaps
        gaps = self._identify_knowledge_gaps(query, tier1_result)
        
        # Generate context request message
        message = self._generate_context_request_message(query, gaps)
        
        return QueryResult(
            tier=QueryTier.USER_CONTEXT,
            success=False,  # Not answered yet, waiting for context
            response=message,
            confidence=ConfidenceMetrics(overall_score=0.0),
            knowledge_gaps=gaps,
            metadata={
                "context_submission_endpoint": "/api/submit-context",
                "query_id": query_id
            }
        )
    
    def _assess_vectordb_quality(
        self,
        chunks: List[Dict[str, Any]],
        query: str
    ) -> ConfidenceMetrics:
        """
        Assess quality of VectorDB retrieval results.
        
        Factors:
        - Number of chunks returned
        - Average similarity scores
        - Score variance (consistency)
        - Coverage (do results address the query)
        
        Args:
            chunks: Retrieved chunks
            query: Original query
            
        Returns:
            ConfidenceMetrics with quality assessment
        """
        if not chunks:
            return ConfidenceMetrics(overall_score=0.0, result_count=0)
        
        # Extract scores
        scores = [chunk.get("score", 0.0) for chunk in chunks]
        
        # Calculate metrics
        result_count = len(chunks)
        avg_similarity = sum(scores) / len(scores) if scores else 0.0
        
        # Calculate variance
        if len(scores) > 1:
            mean = avg_similarity
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            score_variance = variance
        else:
            score_variance = 0.0
        
        # Coverage score (simple heuristic: more results = better coverage)
        coverage_score = min(result_count / 5.0, 1.0)
        
        # Overall score (weighted combination)
        overall_score = (
            avg_similarity * 0.5 +  # Similarity is most important
            coverage_score * 0.3 +  # Coverage matters
            (1.0 - score_variance) * 0.2  # Consistency is good
        )
        
        return ConfidenceMetrics(
            overall_score=overall_score,
            result_count=result_count,
            avg_similarity=avg_similarity,
            score_variance=score_variance,
            coverage_score=coverage_score
        )
    
    def _assess_model_confidence(
        self,
        response: str,
        query: str
    ) -> ConfidenceMetrics:
        """
        Assess confidence in model-generated response.
        
        Looks for uncertainty signals like:
        - "I'm not sure", "might be", "possibly"
        - Very short responses
        - Hedging language
        - Explicit lack of knowledge statements
        
        Args:
            response: Model-generated response
            query: Original query
            
        Returns:
            ConfidenceMetrics with confidence assessment
        """
        # Enhanced uncertainty phrases for model-first strategy
        uncertainty_phrases = [
            # Explicit lack of knowledge
            "i don't know", "i'm not sure", "i don't have information",
            "i cannot provide", "i don't have access", "i'm not aware",
            "no information available", "cannot find", "don't have data",
            "i would need more", "i don't have enough", "i lack",
            
            # Hedging language
            "might be", "possibly", "perhaps", "maybe", "could be",
            "i think", "i believe", "probably", "likely", "seems like",
            "appears to be", "may be", "uncertain", "unclear",
            
            # Requesting more info
            "need more context", "need more information", "can you provide",
            "please clarify", "could you specify", "more details"
        ]
        
        response_lower = response.lower()
        uncertainty_detected = any(phrase in response_lower for phrase in uncertainty_phrases)
        
        # If uncertainty detected, confidence is very low
        if uncertainty_detected:
            return ConfidenceMetrics(
                overall_score=0.2,  # Low confidence when uncertain
                uncertainty_detected=True
            )
        
        # Length check (very short = low confidence)
        response_length = len(response.split())
        
        # Very short responses (< 10 words) are suspicious
        if response_length < 10:
            length_score = 0.3
        # Short responses (10-30 words) are medium confidence
        elif response_length < 30:
            length_score = 0.6
        # Normal responses (30+ words) are high confidence
        else:
            length_score = 1.0
        
        return ConfidenceMetrics(
            overall_score=length_score,
            uncertainty_detected=False
        )
    
    def _identify_knowledge_gaps(
        self,
        query: str,
        tier1_result: QueryResult
    ) -> List[KnowledgeGap]:
        """
        Identify specific knowledge gaps preventing a complete answer.
        
        Args:
            query: User query
            tier1_result: Tier 1 result (may have partial info)
            
        Returns:
            List of KnowledgeGap objects
        """
        gaps = []
        
        # Simple heuristic: identify question type and create relevant gaps
        query_lower = query.lower()
        
        if "how" in query_lower and ("deploy" in query_lower or "install" in query_lower):
            gaps.append(KnowledgeGap(
                gap_id=f"gap_{uuid.uuid4().hex[:8]}",
                topic="deployment_environment",
                specific_question="What is your target deployment environment?",
                required=True,
                suggestions=["AWS", "Azure", "GCP", "On-premise", "Docker", "Kubernetes"]
            ))
        
        if "configure" in query_lower or "setup" in query_lower or "config" in query_lower:
            gaps.append(KnowledgeGap(
                gap_id=f"gap_{uuid.uuid4().hex[:8]}",
                topic="configuration_details",
                specific_question="What specific configuration are you trying to set up?",
                required=True
            ))
        
        # If no specific gaps identified, create a general one
        if not gaps:
            gaps.append(KnowledgeGap(
                gap_id=f"gap_{uuid.uuid4().hex[:8]}",
                topic="general_context",
                specific_question="Can you provide more context about your specific use case or environment?",
                required=False
            ))
        
        return gaps
    
    def _generate_rag_response(self, query: str, context: str) -> str:
        """Generate response using RAG context."""
        prompt = f"""Based on the following context, answer the question.

Context:
{context}

Question: {query}

Answer:"""
        
        model_name = settings.LLM_MODEL
        
        response = self.llm_client.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
            temperature=0.3
        )
        
        return response
    
    def _generate_model_response(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Generate response using model knowledge (with optional conversation context)."""
        
        # Build messages array
        messages = []
        
        # Add system prompt with conversation memory instructions
        system_prompt = """You are a helpful AI assistant with conversation memory. Follow these guidelines:

**IMPORTANT: Use Conversation History**
- You can see the previous messages in this conversation
- ALWAYS check if the answer is in the conversation history before saying you don't know
- Reference previous messages when relevant
- Remember what the user told you earlier

**Response Guidelines:**

1. **If the question is about something mentioned earlier**: Use the conversation history to answer. Don't say you don't know if it was already discussed.

2. **If the question is CLEAR and you know the answer**: Provide a direct, concise, and accurate answer.

3. **If the question is AMBIGUOUS or lacks context**: Ask 2-3 specific clarifying questions to understand what the user needs.

4. **If you genuinely don't have the information AND it wasn't mentioned earlier**: Say "I don't know" or "I don't have information about this" clearly.

**Examples:**
- Previous: "I love red" → Later: "What's my favorite color?" → Answer: "Red! You mentioned earlier that you love the color red."
- "What is Python?" → Answer directly with definition
- "How do I fix it?" → Ask: "What are you trying to fix? What error are you seeing?"
- "Tell me about the project" → Ask: "Which project? What aspect interests you?"

**Remember**: Always check the conversation history first!
"""
        
        messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history if available
        if conversation_history and len(conversation_history) > 0:
            # Use conversation history (already includes current query)
            messages.extend(conversation_history)
            logger.info(f"[CONVERSATION-MEMORY] Passing {len(conversation_history)} messages to model")
            logger.debug(f"[CONVERSATION-MEMORY] Messages: {conversation_history}")
        else:
            # No history, just add current query
            messages.append({"role": "user", "content": f"Question: {query}\n\nAnswer:"})
            logger.info("[CONVERSATION-MEMORY] No conversation history available")
        
        model_name = settings.LLM_MODEL
        
        response = self.llm_client.chat(
            model=model_name,
            messages=messages,  # Full conversation with history
            stream=False,
            temperature=0.5
        )
        
        return response
    
    def _generate_context_request_message(
        self,
        query: str,
        gaps: List[KnowledgeGap]
    ) -> str:
        """Generate user-friendly context request message."""
        message = "I need more information to answer your question accurately.\n\n"
        
        for i, gap in enumerate(gaps, 1):
            message += f"{i}. {gap.specific_question}\n"
            if gap.suggestions:
                message += f"   Suggestions: {', '.join(gap.suggestions)}\n"
        
        message += "\nPlease provide this information so I can give you a better answer."
        
        return message
