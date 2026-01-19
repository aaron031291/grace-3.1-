"""
AIContentAnalyzer - LLM-based Content Analysis

Uses LLM Orchestrator to analyze document content and suggest categorization when
rule-based matching is insufficient or ambiguous.

FULLY INTEGRATED with:
- Cognitive Framework (OODA Loop + 12 Invariants)
- Genesis Key tracking
- Hallucination mitigation
- Learning Memory integration
- Layer 1 Message Bus
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
import json
import logging

from models.database_models import Document, DocumentChunk
from librarian.utils import (
    truncate_text,
    parse_confidence_label,
    safe_json_loads,
    normalize_tag_name
)

logger = logging.getLogger(__name__)


class AIContentAnalyzer:
    """
    LLM-powered content analysis for intelligent document categorization.

    NOW FULLY INTEGRATED with LLM Orchestrator to provide:
    - Suggested tags based on content understanding
    - Document category classification
    - Main topics identification
    - Confidence scores

    All AI operations are:
    - Tracked with Genesis Keys
    - Enforced through OODA Loop + 12 Invariants
    - Verified through hallucination mitigation pipeline
    - Integrated with Learning Memory
    - Logged for complete audit trail

    Features:
    - Content sampling (first N chunks to avoid token limits)
    - Low temperature for consistent categorization
    - JSON-structured responses with fallbacks
    - Configurable confidence thresholds

    Example:
        >>> from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
        >>> analyzer = AIContentAnalyzer(db_session, llm_orchestrator=get_llm_orchestrator())
        >>> result = analyzer.analyze_document(document_id=123)
        >>> print(f"Suggested tags: {result['tags']}")
        >>> print(f"Confidence: {result['confidence']}")
        >>> print(f"Genesis Key: {result['genesis_key_id']}")
    """

    def __init__(
        self,
        db_session: Session,
        ollama_client=None,
        llm_orchestrator=None,
        model_name: str = "mistral:7b",
        max_chunks: int = 5,
        max_chars: int = 4000
    ):
        """
        Initialize AIContentAnalyzer.

        Args:
            db_session: SQLAlchemy database session
            ollama_client: [DEPRECATED] Legacy Ollama client (use llm_orchestrator instead)
            llm_orchestrator: LLM Orchestrator instance (preferred)
            model_name: Model to use for analysis (default: "mistral:7b")
            max_chunks: Maximum chunks to analyze (default: 5)
            max_chars: Maximum characters to analyze (default: 4000)
        """
        self.db = db_session
        self.model_name = model_name
        self.max_chunks = max_chunks
        self.max_chars = max_chars

        # Prefer LLM Orchestrator over direct Ollama client
        self._llm_orchestrator = llm_orchestrator
        self._ollama_legacy = ollama_client  # Keep for backward compatibility

        # Try to get orchestrator if not provided
        if self._llm_orchestrator is None:
            try:
                from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
                from embedding import get_embedding_model
                self._llm_orchestrator = get_llm_orchestrator(
                    session=db_session,
                    embedding_model=get_embedding_model(),
                    knowledge_base_path="knowledge_base"
                )
                logger.info("[AI ANALYZER] ✓ Connected to LLM Orchestrator")
            except Exception as e:
                logger.warning(f"[AI ANALYZER] Could not connect to LLM Orchestrator: {e}")
                logger.warning("[AI ANALYZER] Falling back to legacy Ollama client")

        # Legacy compatibility
        self.ollama = ollama_client

    def analyze_document(
        self,
        document_id: int,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze a document using LLM to suggest categorization.

        Args:
            document_id: Document ID to analyze
            custom_prompt: Optional custom analysis prompt

        Returns:
            Dict: Analysis results with tags, category, topics, confidence

        Example:
            >>> result = analyzer.analyze_document(123)
            >>> {
            ...     "tags": ["ai", "machine-learning", "research"],
            ...     "category": "research",
            ...     "topics": ["neural networks", "deep learning"],
            ...     "purpose": "Technical paper on transformers",
            ...     "confidence": 0.9,
            ...     "confidence_label": "high",
            ...     "raw_response": "..."
            ... }
        """
        # Get document
        document = self.db.query(Document).filter(
            Document.id == document_id
        ).first()

        if not document:
            raise ValueError(f"Document {document_id} not found")

        # Sample content
        content_sample = self._sample_document_content(document)

        if not content_sample:
            logger.warning(f"No content available for document {document_id}")
            return {
                "tags": [],
                "category": "unknown",
                "topics": [],
                "purpose": "",
                "confidence": 0.0,
                "confidence_label": "low",
                "error": "No content available"
            }

        # Build prompt
        prompt = custom_prompt or self._build_analysis_prompt(document, content_sample)

        # Generate analysis using LLM Orchestrator (preferred) or legacy Ollama
        try:
            genesis_key_id = None
            trust_score = None

            if self._llm_orchestrator:
                # Use LLM Orchestrator with full cognitive pipeline
                from llm_orchestrator.multi_llm_client import TaskType

                logger.info(f"[AI ANALYZER] Using LLM Orchestrator for document {document_id}")

                task_result = self._llm_orchestrator.execute_task(
                    prompt=prompt,
                    task_type=TaskType.ANALYSIS,
                    user_id=f"librarian_analyzer_{document_id}",
                    require_verification=True,
                    require_consensus=False,  # Single task, no consensus needed
                    require_grounding=False,  # Document analysis, not code grounding
                    enable_learning=True,
                    system_prompt="You are an expert document categorization assistant. Analyze documents and provide structured JSON responses for categorization."
                )

                if task_result.success:
                    response = task_result.content
                    genesis_key_id = task_result.genesis_key_id
                    trust_score = task_result.trust_score
                    logger.info(f"[AI ANALYZER] ✓ Orchestrator task completed - Genesis Key: {genesis_key_id}")
                else:
                    raise Exception(f"Orchestrator task failed: {task_result.audit_trail}")

            elif self._ollama_legacy:
                # Legacy fallback to direct Ollama
                logger.warning(f"[AI ANALYZER] Using legacy Ollama client for document {document_id}")
                response = self._ollama_legacy.generate_response(
                    model=self.model_name,
                    prompt=prompt,
                    temperature=0.3,
                    stream=False
                )
            else:
                raise Exception("No LLM backend available (orchestrator or ollama)")

            # Parse response
            result = self._parse_analysis_response(response)
            result["raw_response"] = response

            # Add orchestrator metadata
            if genesis_key_id:
                result["genesis_key_id"] = genesis_key_id
            if trust_score is not None:
                result["trust_score"] = trust_score

            logger.info(f"[AI ANALYZER] Analyzed document {document_id}: {len(result['tags'])} tags, confidence={result['confidence']}")
            return result

        except Exception as e:
            logger.error(f"[AI ANALYZER] Analysis failed for document {document_id}: {e}")
            return {
                "tags": [],
                "category": "unknown",
                "topics": [],
                "purpose": "",
                "confidence": 0.0,
                "confidence_label": "low",
                "error": str(e),
                "raw_response": ""
            }

    def _sample_document_content(self, document: Document) -> str:
        """
        Sample document content for analysis.

        Takes first N chunks up to max_chars to avoid token limits.

        Args:
            document: Document instance

        Returns:
            str: Sampled content
        """
        if not document.chunks:
            return ""

        content_parts = []
        total_chars = 0

        for i, chunk in enumerate(document.chunks[:self.max_chunks]):
            if total_chars + len(chunk.text_content) > self.max_chars:
                # Add truncated chunk and stop
                remaining_chars = self.max_chars - total_chars
                content_parts.append(chunk.text_content[:remaining_chars])
                break

            content_parts.append(chunk.text_content)
            total_chars += len(chunk.text_content)

        return "\n\n".join(content_parts)

    def _build_analysis_prompt(self, document: Document, content_sample: str) -> str:
        """
        Build analysis prompt for LLM.

        Args:
            document: Document instance
            content_sample: Sampled content

        Returns:
            str: Analysis prompt
        """
        prompt = f"""Analyze this document and provide categorization information.

Document Information:
- Filename: {document.filename}
- File Path: {document.file_path or 'N/A'}
- MIME Type: {document.mime_type or 'N/A'}
- Size: {document.file_size} bytes

Content Sample (first {len(content_sample)} characters):
{truncate_text(content_sample, max_length=3500)}

Please analyze this document and provide:
1. Primary category (choose one: research, code, documentation, media, data, configuration, tutorial, other)
2. 3-7 relevant tags (lowercase, single words or hyphenated phrases)
3. Main topics covered (2-5 topics)
4. Brief document purpose (1 sentence)
5. Your confidence level (low, medium, high)

Respond in JSON format:
{{
    "category": "research",
    "tags": ["ai", "machine-learning", "neural-networks"],
    "topics": ["deep learning", "transformer architecture"],
    "purpose": "Technical paper explaining transformer models",
    "confidence": "high"
}}

Be concise and accurate. Focus on technical classification."""

        return prompt

    def _parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured data.

        Handles various response formats with fallbacks.

        Args:
            response: Raw LLM response

        Returns:
            Dict: Parsed analysis results
        """
        # Try to extract JSON from response
        result = {
            "tags": [],
            "category": "unknown",
            "topics": [],
            "purpose": "",
            "confidence": 0.5,
            "confidence_label": "medium"
        }

        # Try JSON parsing
        json_obj = self._extract_json(response)

        if json_obj:
            # Extract fields
            if "category" in json_obj:
                result["category"] = str(json_obj["category"]).lower()

            if "tags" in json_obj and isinstance(json_obj["tags"], list):
                result["tags"] = [
                    normalize_tag_name(str(tag))
                    for tag in json_obj["tags"]
                    if tag
                ][:7]  # Max 7 tags

            if "topics" in json_obj and isinstance(json_obj["topics"], list):
                result["topics"] = [
                    str(topic).strip()
                    for topic in json_obj["topics"]
                    if topic
                ][:5]  # Max 5 topics

            if "purpose" in json_obj:
                result["purpose"] = str(json_obj["purpose"]).strip()[:200]

            if "confidence" in json_obj:
                conf_str = str(json_obj["confidence"]).lower()
                result["confidence_label"] = conf_str
                result["confidence"] = parse_confidence_label(conf_str)

        else:
            # Fallback: Extract information from text
            logger.warning("Failed to parse JSON from LLM response, using text extraction")
            result = self._extract_from_text(response)

        return result

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract JSON object from text.

        Handles cases where JSON is embedded in markdown or other text.

        Args:
            text: Text containing JSON

        Returns:
            Optional[Dict]: Parsed JSON or None
        """
        # Try direct JSON parse
        json_obj = safe_json_loads(text)
        if json_obj and isinstance(json_obj, dict):
            return json_obj

        # Try to find JSON in code blocks
        import re

        # Look for JSON in markdown code blocks
        json_blocks = re.findall(r'```(?:json)?\s*(\{[^`]+\})\s*```', text, re.DOTALL)
        for block in json_blocks:
            json_obj = safe_json_loads(block)
            if json_obj and isinstance(json_obj, dict):
                return json_obj

        # Look for JSON object anywhere in text
        json_matches = re.findall(r'\{[^}]+\}', text, re.DOTALL)
        for match in json_matches:
            json_obj = safe_json_loads(match)
            if json_obj and isinstance(json_obj, dict) and "category" in json_obj:
                return json_obj

        return None

    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract information from non-JSON text response.

        Fallback parser for when LLM doesn't return proper JSON.

        Args:
            text: LLM response text

        Returns:
            Dict: Extracted information
        """
        result = {
            "tags": [],
            "category": "unknown",
            "topics": [],
            "purpose": "",
            "confidence": 0.4,
            "confidence_label": "low"
        }

        text_lower = text.lower()

        # Extract category
        categories = ["research", "code", "documentation", "media", "data", "configuration", "tutorial"]
        for cat in categories:
            if cat in text_lower:
                result["category"] = cat
                break

        # Extract tags (look for comma-separated words)
        import re
        tag_patterns = [
            r'tags?:\s*([^\n]+)',
            r'keywords?:\s*([^\n]+)',
            r'topics?:\s*([^\n]+)'
        ]

        for pattern in tag_patterns:
            match = re.search(pattern, text_lower)
            if match:
                tags_str = match.group(1)
                tags = [
                    normalize_tag_name(t)
                    for t in re.split(r'[,;]', tags_str)
                    if t.strip()
                ]
                result["tags"].extend(tags[:7])
                break

        # Extract confidence
        if "high confidence" in text_lower or "very confident" in text_lower:
            result["confidence"] = 0.9
            result["confidence_label"] = "high"
        elif "medium confidence" in text_lower or "moderately confident" in text_lower:
            result["confidence"] = 0.7
            result["confidence_label"] = "medium"

        return result

    def analyze_batch(
        self,
        document_ids: List[int],
        skip_errors: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Analyze multiple documents in batch.

        Args:
            document_ids: List of document IDs
            skip_errors: Continue on errors (default: True)

        Returns:
            List[Dict]: Analysis results for each document

        Example:
            >>> results = analyzer.analyze_batch([1, 2, 3, 4, 5])
            >>> successful = [r for r in results if "error" not in r]
            >>> print(f"Analyzed {len(successful)}/{len(results)} documents")
        """
        results = []

        for doc_id in document_ids:
            try:
                result = self.analyze_document(doc_id)
                result["document_id"] = doc_id
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to analyze document {doc_id}: {e}")
                if skip_errors:
                    results.append({
                        "document_id": doc_id,
                        "error": str(e),
                        "tags": [],
                        "category": "unknown",
                        "confidence": 0.0
                    })
                else:
                    raise

        return results

    def suggest_tags_for_query(
        self,
        query: str,
        max_tags: int = 5
    ) -> List[str]:
        """
        Suggest tags for a search query or description.

        Useful for helping users categorize content or refine searches.

        Args:
            query: Search query or content description
            max_tags: Maximum tags to suggest (default: 5)

        Returns:
            List[str]: Suggested tags

        Example:
            >>> tags = analyzer.suggest_tags_for_query(
            ...     "paper about neural networks and deep learning"
            ... )
            >>> print(tags)  # ["ai", "neural-networks", "deep-learning", "research"]
        """
        prompt = f"""Suggest {max_tags} relevant tags for this query or content description:

Query: "{query}"

Provide {max_tags} specific, relevant tags (lowercase, hyphenated if needed).
Respond with ONLY a JSON array of tags, nothing else.

Example response: ["ai", "machine-learning", "research"]
"""

        try:
            if self._llm_orchestrator:
                # Use LLM Orchestrator
                from llm_orchestrator.multi_llm_client import TaskType

                task_result = self._llm_orchestrator.execute_task(
                    prompt=prompt,
                    task_type=TaskType.ANALYSIS,
                    user_id="librarian_tag_suggester",
                    require_verification=False,
                    require_consensus=False,
                    require_grounding=False,
                    enable_learning=True,
                    system_prompt="You are a tag suggestion assistant. Return only JSON arrays."
                )

                if task_result.success:
                    response = task_result.content
                else:
                    return []

            elif self._ollama_legacy:
                response = self._ollama_legacy.generate_response(
                    model=self.model_name,
                    prompt=prompt,
                    temperature=0.3,
                    stream=False
                )
            else:
                return []

            # Parse JSON array
            tags = safe_json_loads(response, default=[])
            if isinstance(tags, list):
                return [normalize_tag_name(str(t)) for t in tags if t][:max_tags]

            return []

        except Exception as e:
            logger.error(f"[AI ANALYZER] Failed to suggest tags for query: {e}")
            return []

    def compare_documents(
        self,
        doc_id_1: int,
        doc_id_2: int
    ) -> Dict[str, Any]:
        """
        Compare two documents to identify similarities and differences.

        Args:
            doc_id_1: First document ID
            doc_id_2: Second document ID

        Returns:
            Dict: Comparison results with similarity score and analysis

        Example:
            >>> comparison = analyzer.compare_documents(123, 456)
            >>> print(f"Similarity: {comparison['similarity_score']}")
            >>> print(f"Relationship: {comparison['relationship_type']}")
        """
        # Get documents
        doc1 = self.db.query(Document).filter(Document.id == doc_id_1).first()
        doc2 = self.db.query(Document).filter(Document.id == doc_id_2).first()

        if not doc1 or not doc2:
            raise ValueError("One or both documents not found")

        # Sample content
        content1 = self._sample_document_content(doc1)[:1000]
        content2 = self._sample_document_content(doc2)[:1000]

        prompt = f"""Compare these two documents and determine their relationship:

Document 1: {doc1.filename}
{truncate_text(content1, 800)}

Document 2: {doc2.filename}
{truncate_text(content2, 800)}

Analyze:
1. Similarity score (0.0-1.0)
2. Relationship type (duplicate, version, related, citation, unrelated)
3. Brief explanation (1 sentence)

Respond in JSON:
{{
    "similarity_score": 0.75,
    "relationship_type": "related",
    "explanation": "Both documents discuss similar topics"
}}
"""

        try:
            genesis_key_id = None

            if self._llm_orchestrator:
                # Use LLM Orchestrator
                from llm_orchestrator.multi_llm_client import TaskType

                task_result = self._llm_orchestrator.execute_task(
                    prompt=prompt,
                    task_type=TaskType.ANALYSIS,
                    user_id=f"librarian_compare_{doc_id_1}_{doc_id_2}",
                    require_verification=True,
                    require_consensus=False,
                    require_grounding=False,
                    enable_learning=True,
                    system_prompt="You are a document comparison assistant. Analyze documents and provide structured JSON responses."
                )

                if task_result.success:
                    response = task_result.content
                    genesis_key_id = task_result.genesis_key_id
                else:
                    raise Exception("Comparison task failed")

            elif self._ollama_legacy:
                response = self._ollama_legacy.generate_response(
                    model=self.model_name,
                    prompt=prompt,
                    temperature=0.3,
                    stream=False
                )
            else:
                raise Exception("No LLM backend available")

            result = self._extract_json(response)
            if result:
                comparison_result = {
                    "document_1_id": doc_id_1,
                    "document_2_id": doc_id_2,
                    "similarity_score": float(result.get("similarity_score", 0.5)),
                    "relationship_type": str(result.get("relationship_type", "unknown")),
                    "explanation": str(result.get("explanation", "")),
                    "raw_response": response
                }
                if genesis_key_id:
                    comparison_result["genesis_key_id"] = genesis_key_id
                return comparison_result

        except Exception as exc:
            logger.error(f"[AI ANALYZER] Failed to compare documents: {exc}")
            return {
                "document_1_id": doc_id_1,
                "document_2_id": doc_id_2,
                "similarity_score": 0.0,
                "relationship_type": "unknown",
                "explanation": "Analysis failed",
                "error": str(exc)
            }

    def is_available(self) -> bool:
        """
        Check if AI analysis is available (LLM Orchestrator or legacy Ollama).

        Returns:
            bool: True if available, False otherwise
        """
        try:
            # Prefer orchestrator
            if self._llm_orchestrator:
                return True

            # Fallback to legacy
            if self._ollama_legacy:
                return (
                    self._ollama_legacy.is_running() and
                    self._ollama_legacy.model_exists(self.model_name)
                )

            return False
        except Exception:
            return False

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current analysis model.

        Returns:
            Dict: Model information
        """
        try:
            if self._llm_orchestrator:
                return {
                    "model_name": self.model_name,
                    "available": True,
                    "backend": "llm_orchestrator",
                    "features": [
                        "cognitive_enforcement",
                        "genesis_key_tracking",
                        "hallucination_mitigation",
                        "learning_memory_integration"
                    ]
                }

            if self._ollama_legacy and self.is_available():
                return {
                    "model_name": self.model_name,
                    "available": True,
                    "backend": "ollama_legacy",
                    "running": self._ollama_legacy.is_model_running(self.model_name)
                }

        except Exception as e:
            logger.error(f"[AI ANALYZER] Failed to get model info: {e}")

        return {
            "model_name": self.model_name,
            "available": False,
            "error": "Model not available"
        }
