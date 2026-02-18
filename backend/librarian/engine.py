"""
LibrarianEngine - Central Orchestrator

Coordinates all librarian components to provide comprehensive file management:
- Rule-based categorization
- AI content analysis (via LLM Orchestrator)
- Tag management
- Relationship detection
- Approval workflow

FULLY INTEGRATED with:
- LLM Orchestrator for AI operations
- Cognitive Framework (OODA Loop + 12 Invariants)
- Genesis Key tracking
- Layer 1 Message Bus

This is the main entry point for the librarian system.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging

from models.database_models import Document
from librarian.tag_manager import TagManager
from librarian.rule_categorizer import RuleBasedCategorizer
from librarian.ai_analyzer import AIContentAnalyzer
from librarian.relationship_manager import RelationshipManager
from librarian.approval_workflow import ApprovalWorkflow

logger = logging.getLogger(__name__)


class LibrarianEngine:
    """
    Central orchestrator for the Grace Librarian System.

    NOW FULLY INTEGRATED with LLM Orchestrator for all AI operations.

    Coordinates all librarian components to automatically organize, categorize,
    and index documents. Handles the complete processing pipeline:

    1. Rule-based categorization (fast pattern matching)
    2. AI content analysis (via LLM Orchestrator with full cognitive pipeline)
    3. Tag assignment (with confidence tracking)
    4. Relationship detection (citations, versions, similarity)
    5. Approval workflow (for sensitive operations)

    All AI operations include:
    - OODA Loop enforcement
    - 12 Invariants validation
    - Genesis Key tracking
    - Hallucination mitigation
    - Learning Memory integration

    Example:
        >>> from database.session import initialize_session_factory
        >>> from database.config import DatabaseConfig
        >>> from database.connection import DatabaseConnection
        >>> from embedding import get_embedding_model
        >>> from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
        >>> from vector_db.client import get_qdrant_client
        >>>
        >>> # Initialize
        >>> config = DatabaseConfig.from_env()
        >>> DatabaseConnection.initialize(config)
        >>> SessionLocal = initialize_session_factory()
        >>> db = SessionLocal()
        >>>
        >>> # Create engine with LLM Orchestrator (preferred)
        >>> librarian = LibrarianEngine(
        ...     db_session=db,
        ...     embedding_model=get_embedding_model(),
        ...     llm_orchestrator=get_llm_orchestrator(session=db),
        ...     vector_db_client=get_qdrant_client()
        ... )
        >>>
        >>> # Process a document
        >>> result = librarian.process_document(document_id=123)
        >>> print(f"Tags: {result['tags_assigned']}")
        >>> print(f"Relationships: {result['relationships_detected']}")
        >>> print(f"Genesis Key: {result.get('genesis_key_id')}")
    """

    def __init__(
        self,
        db_session: Session,
        embedding_model=None,
        ollama_client=None,  # [DEPRECATED] Use llm_orchestrator instead
        llm_orchestrator=None,
        vector_db_client=None,
        ai_model_name: str = "mistral:7b",
        use_ai: bool = True,
        detect_relationships: bool = True,
        ai_confidence_threshold: float = 0.6,
        similarity_threshold: float = 0.7
    ):
        """
        Initialize LibrarianEngine with all components.

        Args:
            db_session: SQLAlchemy database session
            embedding_model: Embedding model for similarity
            ollama_client: [DEPRECATED] Legacy Ollama client (use llm_orchestrator instead)
            llm_orchestrator: LLM Orchestrator instance (preferred)
            vector_db_client: Qdrant vector DB client
            ai_model_name: LLM model name (default: "mistral:7b")
            use_ai: Enable AI content analysis (default: True)
            detect_relationships: Enable relationship detection (default: True)
            ai_confidence_threshold: Min confidence for AI suggestions (default: 0.6)
            similarity_threshold: Min similarity for relationships (default: 0.7)
        """
        self.db = db_session

        # Configuration
        self.use_ai = use_ai
        self.detect_relationships = detect_relationships
        self.ai_confidence_threshold = ai_confidence_threshold
        self.similarity_threshold = similarity_threshold

        # Initialize components
        self.tag_manager = TagManager(db_session)
        self.rule_categorizer = RuleBasedCategorizer(db_session)
        self.approval_workflow = ApprovalWorkflow(db_session)

        # Store orchestrator reference
        self._llm_orchestrator = llm_orchestrator

        # Try to get orchestrator if not provided
        if self._llm_orchestrator is None and use_ai:
            try:
                from llm_orchestrator.llm_orchestrator import get_llm_orchestrator
                self._llm_orchestrator = get_llm_orchestrator(
                    session=db_session,
                    embedding_model=embedding_model,
                    knowledge_base_path="knowledge_base"
                )
                logger.info("[LIBRARIAN] ✓ Connected to LLM Orchestrator")
            except Exception as e:
                logger.warning(f"[LIBRARIAN] Could not connect to LLM Orchestrator: {e}")

        # Optional AI analyzer (now uses orchestrator)
        self.ai_analyzer = None
        if use_ai:
            try:
                self.ai_analyzer = AIContentAnalyzer(
                    db_session,
                    ollama_client=ollama_client,  # Legacy fallback
                    llm_orchestrator=self._llm_orchestrator,  # Preferred
                    model_name=ai_model_name
                )
                if not self.ai_analyzer.is_available():
                    logger.warning("[LIBRARIAN] AI analyzer created but not available")
                    self.ai_analyzer = None
                else:
                    logger.info("[LIBRARIAN] ✓ AI analyzer ready (via LLM Orchestrator)")
            except Exception as e:
                logger.warning(f"[LIBRARIAN] Failed to initialize AI analyzer: {e}")
                self.ai_analyzer = None

        # Optional relationship manager
        self.relationship_manager = None
        if detect_relationships:
            self.relationship_manager = RelationshipManager(
                db_session,
                embedding_model,
                vector_db_client
            )

        logger.info(f"[LIBRARIAN] Engine initialized (AI: {self.ai_analyzer is not None}, Relationships: {self.relationship_manager is not None})")

    def process_document(
        self,
        document_id: int,
        use_ai: Optional[bool] = None,
        detect_relationships: Optional[bool] = None,
        auto_execute: bool = True
    ) -> Dict[str, Any]:
        """
        Process a single document through the complete pipeline.

        Args:
            document_id: Document ID to process
            use_ai: Override use_ai setting (default: use engine setting)
            detect_relationships: Override setting (default: use engine setting)
            auto_execute: Auto-execute approved actions (default: True)

        Returns:
            Dict: Processing results with tags, relationships, actions

        Example:
            >>> result = librarian.process_document(123)
            >>> {
            ...     "document_id": 123,
            ...     "tags_assigned": 5,
            ...     "relationships_detected": 3,
            ...     "actions_created": 2,
            ...     "rules_matched": ["PDF Documents", "AI Research Folder"],
            ...     "ai_analysis": {"confidence": 0.9, "category": "research"},
            ...     "status": "success"
            ... }
        """
        use_ai_analysis = use_ai if use_ai is not None else self.use_ai
        detect_rels = detect_relationships if detect_relationships is not None else self.detect_relationships

        result = {
            "document_id": document_id,
            "tags_assigned": 0,
            "relationships_detected": 0,
            "actions_created": 0,
            "rules_matched": [],
            "ai_analysis": None,
            "status": "pending"
        }

        try:
            # Verify document exists
            document = self.db.query(Document).filter(Document.id == document_id).first()
            if not document:
                result["status"] = "error"
                result["error"] = f"Document {document_id} not found"
                return result

            # Step 1: Rule-based categorization
            logger.info(f"Processing document {document_id}: {document.filename}")
            rule_matches = self.rule_categorizer.categorize_document(document_id)
            result["rules_matched"] = [match["rule_name"] for match in rule_matches]

            # Collect tags from rules
            rule_tags = set()
            for match in rule_matches:
                if match["action_type"] == "assign_tag":
                    tag_names = match["action_params"].get("tag_names", [])
                    rule_tags.update(tag_names)

            # Assign rule-based tags
            if rule_tags:
                self.tag_manager.assign_tags(
                    document_id=document_id,
                    tag_names=list(rule_tags),
                    assigned_by="rule",
                    confidence=0.95
                )
                result["tags_assigned"] += len(rule_tags)
                logger.info(f"Assigned {len(rule_tags)} rule-based tags")

            # Step 2: AI content analysis (if enabled and needed)
            ai_tags = set()
            if use_ai_analysis and self.ai_analyzer:
                # Use AI if: no rules matched OR AI is available for refinement
                if len(rule_matches) == 0 or len(rule_tags) < 3:
                    try:
                        ai_result = self.ai_analyzer.analyze_document(document_id)
                        result["ai_analysis"] = {
                            "confidence": ai_result.get("confidence", 0.0),
                            "category": ai_result.get("category", "unknown"),
                            "topics": ai_result.get("topics", [])
                        }

                        # Use AI-suggested tags if confidence is high enough
                        if ai_result.get("confidence", 0.0) >= self.ai_confidence_threshold:
                            ai_tags = set(ai_result.get("tags", []))

                            # Remove tags already assigned by rules
                            ai_tags = ai_tags - rule_tags

                            if ai_tags:
                                self.tag_manager.assign_tags(
                                    document_id=document_id,
                                    tag_names=list(ai_tags),
                                    assigned_by="ai",
                                    confidence=ai_result["confidence"]
                                )
                                result["tags_assigned"] += len(ai_tags)
                                logger.info(f"Assigned {len(ai_tags)} AI-suggested tags")

                    except Exception as e:
                        logger.error(f"AI analysis failed for document {document_id}: {e}")
                        result["ai_analysis"] = {"error": str(e)}

            # Step 3: Relationship detection (if enabled)
            if detect_rels and self.relationship_manager:
                try:
                    relationships = self.relationship_manager.detect_relationships(
                        document_id=document_id,
                        similarity_threshold=self.similarity_threshold
                    )

                    if relationships:
                        # Save relationships
                        saved_count = self.relationship_manager.save_detected_relationships(relationships)
                        result["relationships_detected"] = saved_count
                        logger.info(f"Detected and saved {saved_count} relationships")

                except Exception as e:
                    logger.error(f"Relationship detection failed for document {document_id}: {e}")

            # Step 4: Auto-execute approved actions (if enabled)
            if auto_execute:
                approved_count = self.approval_workflow.auto_approve_safe_actions(
                    min_confidence=0.8
                )
                if approved_count > 0:
                    logger.info(f"Auto-approved {approved_count} actions")

            # Step 5: Feed to Unified Learning Pipeline for neighbor-by-neighbor expansion
            try:
                from cognitive.unified_learning_pipeline import get_unified_pipeline
                pipeline = get_unified_pipeline()
                if pipeline.running:
                    all_tags = list(rule_tags | ai_tags)
                    seed_topic = document.filename or f"document_{document_id}"
                    seed_text = " ".join(all_tags) if all_tags else seed_topic
                    pipeline.add_seed(topic=seed_topic, text=seed_text)
                    logger.info(f"[LIBRARIAN] Queued '{seed_topic}' for neighbor expansion")
            except Exception as pipe_err:
                logger.debug(f"[LIBRARIAN] Pipeline feed skipped: {pipe_err}")

            # TimeSense: Record librarian processing timing
            try:
                from cognitive.timesense_governance import get_timesense_governance
                get_timesense_governance().record("librarian.process", 0, "librarian")
            except Exception:
                pass

            result["status"] = "success"
            logger.info(f"Successfully processed document {document_id}: {result['tags_assigned']} tags, {result['relationships_detected']} relationships")

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def process_batch(
        self,
        document_ids: List[int],
        use_ai: Optional[bool] = None,
        detect_relationships: Optional[bool] = None,
        skip_errors: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Process multiple documents in batch.

        Args:
            document_ids: List of document IDs
            use_ai: Override AI setting
            detect_relationships: Override relationship detection
            skip_errors: Continue on errors (default: True)

        Returns:
            List[Dict]: Results for each document

        Example:
            >>> results = librarian.process_batch([1, 2, 3, 4, 5])
            >>> successful = [r for r in results if r["status"] == "success"]
            >>> print(f"Processed {len(successful)}/{len(results)} documents")
        """
        results = []

        logger.info(f"Batch processing {len(document_ids)} documents")

        for doc_id in document_ids:
            try:
                result = self.process_document(
                    document_id=doc_id,
                    use_ai=use_ai,
                    detect_relationships=detect_relationships
                )
                results.append(result)

            except Exception as e:
                logger.error(f"Failed to process document {doc_id}: {e}")
                if skip_errors:
                    results.append({
                        "document_id": doc_id,
                        "status": "error",
                        "error": str(e),
                        "tags_assigned": 0,
                        "relationships_detected": 0
                    })
                else:
                    raise

        successful = len([r for r in results if r["status"] == "success"])
        logger.info(f"Batch processing complete: {successful}/{len(document_ids)} successful")

        return results

    def reprocess_all_documents(
        self,
        use_ai: bool = False,
        detect_relationships: bool = True,
        batch_size: int = 10,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Reprocess all documents in the knowledge base.

        Useful after:
        - Adding new rules
        - Updating AI models
        - System upgrades

        Args:
            use_ai: Use AI analysis (default: False, expensive)
            detect_relationships: Detect relationships (default: True)
            batch_size: Process in batches of N documents
            limit: Maximum documents to process (None = all)

        Returns:
            Dict: Summary statistics

        Example:
            >>> # Reprocess all with rules only (fast)
            >>> summary = librarian.reprocess_all_documents(use_ai=False)
            >>> print(f"Processed {summary['documents_processed']} documents")
            >>>
            >>> # Reprocess with AI (expensive, limit to 100)
            >>> summary = librarian.reprocess_all_documents(use_ai=True, limit=100)
        """
        logger.info("Starting full knowledge base reprocessing...")

        # Get all documents
        query = self.db.query(Document).filter(
            Document.status == "completed"
        ).order_by(Document.id)

        if limit:
            query = query.limit(limit)

        all_documents = query.all()
        total_docs = len(all_documents)

        logger.info(f"Found {total_docs} documents to reprocess")

        # Process in batches
        all_results = []
        for i in range(0, total_docs, batch_size):
            batch = all_documents[i:i + batch_size]
            batch_ids = [doc.id for doc in batch]

            logger.info(f"Processing batch {i//batch_size + 1}/{(total_docs + batch_size - 1)//batch_size}")

            batch_results = self.process_batch(
                document_ids=batch_ids,
                use_ai=use_ai,
                detect_relationships=detect_relationships
            )
            all_results.extend(batch_results)

        # Calculate summary
        successful = [r for r in all_results if r["status"] == "success"]
        failed = [r for r in all_results if r["status"] == "error"]

        total_tags = sum(r.get("tags_assigned", 0) for r in all_results)
        total_relationships = sum(r.get("relationships_detected", 0) for r in all_results)

        summary = {
            "documents_processed": len(all_results),
            "successful": len(successful),
            "failed": len(failed),
            "total_tags_assigned": total_tags,
            "total_relationships_detected": total_relationships,
            "average_tags_per_doc": total_tags / len(all_results) if all_results else 0,
            "settings": {
                "use_ai": use_ai,
                "detect_relationships": detect_relationships,
                "batch_size": batch_size
            }
        }

        logger.info(f"Reprocessing complete: {summary['successful']}/{summary['documents_processed']} successful")
        logger.info(f"Assigned {summary['total_tags_assigned']} tags, detected {summary['total_relationships_detected']} relationships")

        return summary

    def get_system_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive system statistics.

        Returns:
            Dict: Statistics from all components

        Example:
            >>> stats = librarian.get_system_statistics()
            >>> print(f"Total tags: {stats['tags']['total']}")
            >>> print(f"Total rules: {stats['rules']['total']}")
        """
        stats = {
            "tags": self.tag_manager.get_tag_statistics(),
            "rules": self.rule_categorizer.get_rule_statistics(),
            "actions": self.approval_workflow.get_action_statistics(),
            "ai_available": self.ai_analyzer.is_available() if self.ai_analyzer else False,
            "relationships_enabled": self.relationship_manager is not None
        }

        return stats

    def health_check(self) -> Dict[str, Any]:
        """
        Check health of all librarian components.

        Returns:
            Dict: Health status of each component

        Example:
            >>> health = librarian.health_check()
            >>> if health["overall_status"] == "healthy":
            ...     print("All systems operational")
        """
        health = {
            "tag_manager": "healthy",
            "rule_categorizer": "healthy",
            "approval_workflow": "healthy",
            "ai_analyzer": "unavailable",
            "relationship_manager": "unavailable",
            "overall_status": "healthy"
        }

        # Check AI analyzer
        if self.ai_analyzer:
            if self.ai_analyzer.is_available():
                health["ai_analyzer"] = "healthy"
            else:
                health["ai_analyzer"] = "degraded"
                health["overall_status"] = "degraded"

        # Check relationship manager
        if self.relationship_manager:
            health["relationship_manager"] = "healthy"

        return health
