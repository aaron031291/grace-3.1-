import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from llm_orchestrator.multi_llm_client import MultiLLMClient, TaskType
from llm_orchestrator.repo_access import RepositoryAccessLayer
from cognitive.learning_memory import LearningMemoryManager, LearningExample
from genesis.cognitive_layer1_integration import CognitiveLayer1Integration
class LearningIntegration:
    logger = logging.getLogger(__name__)
    """
    Integrates LLM orchestration with Learning Memory.

    Enables:
    - Proactive learning from new data
    - Autonomous knowledge updates
    - Trust-scored training data generation
    - Continuous LLM improvement
    """

    def __init__(
        self,
        multi_llm_client: Optional[MultiLLMClient] = None,
        repo_access: Optional[RepositoryAccessLayer] = None,
        learning_memory: Optional[LearningMemoryManager] = None,
        cognitive_layer1: Optional[CognitiveLayer1Integration] = None,
        session: Optional[Session] = None
    ):
        """
        Initialize learning integration.

        Args:
            multi_llm_client: Multi-LLM client
            repo_access: Repository access
            learning_memory: Learning memory manager
            cognitive_layer1: Cognitive Layer 1 integration
            session: Database session
        """
        self.multi_llm = multi_llm_client
        self.repo_access = repo_access
        self.learning_memory = learning_memory
        self.cognitive_layer1 = cognitive_layer1
        self.session = session

        # Learning statistics
        self.stats = {
            "documents_processed": 0,
            "learning_examples_created": 0,
            "knowledge_updates": 0,
            "autonomous_triggers": 0
        }

    # =======================================================================
    # PROACTIVE LEARNING FROM NEW DOCUMENTS
    # =======================================================================

    def process_new_document(
        self,
        document_id: int,
        document_content: str,
        document_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process new document for learning.

        LLMs analyze the document and extract learning examples.

        Args:
            document_id: Document ID
            document_content: Document content
            document_metadata: Document metadata

        Returns:
            Learning results
        """
        logger.info(f"[LEARNING] Processing new document {document_id} for learning")

        # Use LLM to extract key concepts and patterns
        extraction_prompt = f"""Analyze this document and extract key learnings.

Document: {document_content[:2000]}...

Extract:
1. Key concepts and definitions
2. Important procedures or patterns
3. Critical facts or data points
4. Relationships between concepts

Format as structured learning examples."""

        response = self.multi_llm.generate(
            prompt=extraction_prompt,
            task_type=TaskType.GENERAL,
            system_prompt="You are an expert at extracting structured knowledge from documents."
        )

        if not response["success"]:
            return {"error": "Failed to extract learning examples"}

        # Create learning examples from extraction
        learning_examples = self._parse_learning_examples(
            response["content"],
            document_id,
            document_metadata
        )

        # Store in learning memory
        created_examples = []
        if self.learning_memory:
            for example_data in learning_examples:
                try:
                    example = self.learning_memory.ingest_learning_data(
                        learning_type=example_data["type"],
                        learning_data=example_data["data"],
                        source="document_extraction",
                        genesis_key_id=document_metadata.get("genesis_key_id")
                    )
                    if example:
                        created_examples.append(str(example.id))
                except Exception as e:
                    logger.error(f"Error creating learning example: {e}")

        self.stats["documents_processed"] += 1
        self.stats["learning_examples_created"] += len(created_examples)

        return {
            "document_id": document_id,
            "learning_examples_created": len(created_examples),
            "example_ids": created_examples,
            "extraction_content": response["content"]
        }

    def _parse_learning_examples(
        self,
        extraction_content: str,
        document_id: int,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Parse extracted learning examples."""
        # Simplified parsing - in production, use structured output
        examples = []

        # Create a general learning example
        examples.append({
            "type": "document_knowledge",
            "data": {
                "context": {
                    "document_id": document_id,
                    "filename": metadata.get("filename", "unknown"),
                    "extraction": extraction_content
                },
                "expected": {
                    "knowledge_extracted": True
                },
                "actual": {
                    "content": extraction_content
                }
            }
        })

        return examples

    # =======================================================================
    # AUTONOMOUS KNOWLEDGE UPDATES
    # =======================================================================

    def update_llm_knowledge(
        self,
        min_trust_score: float = 0.8,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Update LLM knowledge base with high-trust learning examples.

        This creates a knowledge context that LLMs can reference.

        Args:
            min_trust_score: Minimum trust score for examples
            limit: Maximum examples to include

        Returns:
            Knowledge update results
        """
        logger.info(f"[LEARNING] Updating LLM knowledge base (trust >= {min_trust_score})")

        if not self.repo_access:
            return {"error": "Repository access not available"}

        # Get high-trust learning examples
        examples = self.repo_access.get_learning_examples(
            min_trust_score=min_trust_score,
            limit=limit
        )

        # Get learning patterns
        patterns = self.repo_access.get_learning_patterns(
            min_trust_score=min_trust_score
        )

        # Build knowledge context
        knowledge_context = self._build_knowledge_context(examples, patterns)

        # ✅ CRITICAL FIX: Actually persist knowledge context to file for LLM access
        knowledge_persisted = self._persist_knowledge_context(knowledge_context)

        self.stats["knowledge_updates"] += 1

        return {
            "examples_included": len(examples),
            "patterns_included": len(patterns),
            "knowledge_context_length": len(knowledge_context),
            "knowledge_persisted": knowledge_persisted,
            "min_trust_score": min_trust_score,
            "timestamp": datetime.now().isoformat()
        }

    def _build_knowledge_context(
        self,
        examples: List[Dict[str, Any]],
        patterns: List[Dict[str, Any]]
    ) -> str:
        """Build knowledge context from examples and patterns."""
        context_lines = ["# GRACE Knowledge Base\n"]

        # Add patterns
        if patterns:
            context_lines.append("## Learned Patterns\n")
            for pattern in patterns[:10]:  # Top 10 patterns
                context_lines.append(f"### {pattern['pattern_name']}")
                context_lines.append(f"Trust: {pattern['trust_score']:.2f}")
                context_lines.append(f"Success Rate: {pattern['success_rate']:.2%}")
                context_lines.append("")

        # Add examples
        if examples:
            context_lines.append("## Verified Knowledge\n")
            for example in examples[:20]:  # Top 20 examples
                context_lines.append(f"**{example['example_type']}** (Trust: {example['trust_score']:.2f})")
                context_lines.append(f"Context: {str(example['input_context'])[:200]}...")
                context_lines.append("")

        return "\n".join(context_lines)

    def _persist_knowledge_context(self, knowledge_context: str) -> bool:
        """
        Persist knowledge context to a file in knowledge base for LLM access.
        
        This file can be retrieved via RAG and injected into LLM context.
        
        Args:
            knowledge_context: The knowledge context string to persist
            
        Returns:
            True if successfully persisted, False otherwise
        """
        try:
            from pathlib import Path
            from settings import KNOWLEDGE_BASE_PATH
            
            # Determine knowledge base path
            kb_path = Path(KNOWLEDGE_BASE_PATH)
            if not kb_path.exists():
                # Try alternative location
                kb_path = Path("backend/knowledge_base")
            if not kb_path.exists():
                kb_path = Path("knowledge_base")
            
            # Create directory for learned knowledge
            learned_knowledge_dir = kb_path / "layer_1" / "learning_memory"
            learned_knowledge_dir.mkdir(parents=True, exist_ok=True)
            
            # Save to file (overwrites previous version)
            knowledge_file = learned_knowledge_dir / "learned_knowledge.md"
            
            # Add metadata header
            metadata_header = f"""<!-- 
This file is automatically generated from high-trust LearningExamples.
Last updated: {datetime.now().isoformat()}
Source: LearningIntegration.update_llm_knowledge()
-->

"""
            
            full_content = metadata_header + knowledge_context
            
            with open(knowledge_file, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            logger.info(
                f"[LEARNING] ✅ Knowledge context persisted to: {knowledge_file} "
                f"({len(knowledge_context)} chars)"
            )
            
            # ✅ CRITICAL FIX: Trigger ingestion to make available to RAG
            try:
                from ingestion.file_manager import get_file_manager
                file_manager = get_file_manager()
                
                # ✅ FIX: Check if file manager is available
                if not file_manager:
                    logger.warning(
                        f"[LEARNING] File manager not available, skipping ingestion. "
                        f"File saved, will be picked up by auto-ingestion."
                    )
                else:
                    # Trigger ingestion to embed and store in Qdrant (file exists, so process as modified)
                    result = file_manager.process_modified_file(knowledge_file)
                    if result and result.success:
                        logger.info(
                            f"[LEARNING] ✅ Knowledge file ingested to Qdrant: {result.document_id}"
                        )
                    else:
                        error_msg = result.message if result else "Unknown error"
                        logger.warning(
                            f"[LEARNING] ⚠️ Knowledge file ingestion failed: {error_msg}. "
                            f"File saved, will be picked up by auto-ingestion."
                        )
            except Exception as ingest_error:
                # Don't fail persistence if ingestion fails - file is still saved
                # Auto-ingestion will pick it up on next scan
                logger.warning(
                    f"[LEARNING] Could not trigger ingestion for {knowledge_file}: {ingest_error}. "
                    f"File saved, will be picked up by auto-ingestion.",
                    exc_info=True
                )
            
            return True
            
        except Exception as e:
            logger.error(
                f"[LEARNING] Error persisting knowledge context: {e}",
                exc_info=True
            )
            return False

    # =======================================================================
    # AUTONOMOUS LEARNING TRIGGERS
    # =======================================================================

    def trigger_autonomous_learning(
        self,
        trigger_type: str,
        trigger_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Trigger autonomous learning based on events.

        LLMs can autonomously decide to learn from events.

        Args:
            trigger_type: Type of trigger (e.g., "new_document", "error", "pattern_detected")
            trigger_data: Trigger data

        Returns:
            Learning trigger results
        """
        logger.info(f"[LEARNING] Autonomous learning triggered: {trigger_type}")

        # Use LLM to analyze if learning is needed
        analysis_prompt = f"""Analyze this event and determine if learning should occur.

Trigger Type: {trigger_type}
Trigger Data: {str(trigger_data)[:500]}

Questions:
1. Is this event significant enough to learn from?
2. What should be learned?
3. How should this knowledge be stored?

Analysis:"""

        response = self.multi_llm.generate(
            prompt=analysis_prompt,
            task_type=TaskType.REASONING,
            system_prompt="You decide whether events warrant learning and what should be learned."
        )

        should_learn = "yes" in response.get("content", "").lower() or "significant" in response.get("content", "").lower()

        if should_learn and self.learning_memory:
            # Create learning example
            learning_data = {
                "context": {
                    "trigger_type": trigger_type,
                    "trigger_data": trigger_data,
                    "analysis": response.get("content", "")
                },
                "expected": {
                    "learning_triggered": True
                },
                "actual": {
                    "should_learn": should_learn
                }
            }

            try:
                example = self.learning_memory.ingest_learning_data(
                    learning_type="autonomous_trigger",
                    learning_data=learning_data,
                    source="autonomous_system"
                )
                learning_id = str(example.id) if example else None
            except Exception as e:
                logger.error(f"Error creating autonomous learning example: {e}")
                learning_id = None

            self.stats["autonomous_triggers"] += 1

            return {
                "triggered": True,
                "should_learn": should_learn,
                "learning_example_id": learning_id,
                "analysis": response.get("content", "")
            }

        return {
            "triggered": True,
            "should_learn": False,
            "analysis": response.get("content", "")
        }

    # =======================================================================
    # FINE-TUNING DATA GENERATION
    # =======================================================================

    def generate_fine_tuning_data(
        self,
        task_type: str,
        num_examples: int = 100,
        min_trust_score: float = 0.8
    ) -> Dict[str, Any]:
        """
        Generate fine-tuning dataset from high-trust examples.

        Args:
            task_type: Type of task to generate data for
            num_examples: Number of examples to generate
            min_trust_score: Minimum trust score

        Returns:
            Fine-tuning dataset
        """
        logger.info(f"[LEARNING] Generating fine-tuning data for {task_type}")

        if not self.repo_access:
            return {"error": "Repository access not available"}

        # Get high-trust examples
        examples = self.repo_access.get_learning_examples(
            min_trust_score=min_trust_score,
            example_type=task_type,
            limit=num_examples
        )

        # Format for fine-tuning
        fine_tuning_examples = []
        for example in examples:
            fine_tuning_examples.append({
                "input": str(example.get("input_context", "")),
                "output": str(example.get("expected_output", "")),
                "trust_score": example.get("trust_score", 0.0),
                "validated": example.get("times_validated", 0) > 0
            })

        return {
            "task_type": task_type,
            "num_examples": len(fine_tuning_examples),
            "examples": fine_tuning_examples,
            "min_trust_score": min_trust_score,
            "timestamp": datetime.now().isoformat()
        }

    # =======================================================================
    # VERIFICATION AGAINST LEARNING MEMORY
    # =======================================================================

    def verify_against_learning_memory(
        self,
        content: str,
        context: Dict[str, Any],
        min_trust_score: float = 0.7
    ) -> Dict[str, Any]:
        """
        Verify content against learning memory.

        Args:
            content: Content to verify
            context: Context information
            min_trust_score: Minimum trust score

        Returns:
            Verification result
        """
        logger.info("[LEARNING] Verifying content against learning memory")

        if not self.repo_access:
            return {"verified": False, "reason": "Repository access not available"}

        # Get relevant learning examples
        examples = self.repo_access.get_learning_examples(
            min_trust_score=min_trust_score,
            limit=10
        )

        if not examples:
            return {
                "verified": False,
                "reason": "No high-trust examples available",
                "trust_score": 0.5
            }

        # Use LLM to check consistency with learning examples
        verification_prompt = f"""Verify if this content is consistent with learned knowledge.

Content to verify:
{content}

Learned Knowledge (high-trust examples):
{chr(10).join(f"- {ex.get('example_type', 'unknown')}: Trust {ex.get('trust_score', 0):.2f}" for ex in examples[:5])}

Is the content consistent with learned knowledge? (Yes/No and why)"""

        response = self.multi_llm.generate(
            prompt=verification_prompt,
            task_type=TaskType.VALIDATION,
            system_prompt="You verify content against established knowledge."
        )

        is_consistent = "yes" in response.get("content", "").lower()

        # Calculate verification trust score
        avg_trust = sum(ex.get("trust_score", 0) for ex in examples) / len(examples)

        return {
            "verified": is_consistent,
            "trust_score": avg_trust if is_consistent else avg_trust * 0.5,
            "examples_checked": len(examples),
            "verification_reasoning": response.get("content", ""),
            "timestamp": datetime.now().isoformat()
        }

    # =======================================================================
    # STATISTICS
    # =======================================================================

    def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning integration statistics."""
        return {
            **self.stats,
            "timestamp": datetime.now().isoformat()
        }


# Global instance
_learning_integration: Optional[LearningIntegration] = None


def get_learning_integration(
    multi_llm_client: Optional[MultiLLMClient] = None,
    repo_access: Optional[RepositoryAccessLayer] = None,
    learning_memory: Optional[LearningMemoryManager] = None,
    cognitive_layer1: Optional[CognitiveLayer1Integration] = None,
    session: Optional[Session] = None
) -> LearningIntegration:
    """Get or create global learning integration instance."""
    global _learning_integration
    if _learning_integration is None:
        _learning_integration = LearningIntegration(
            multi_llm_client=multi_llm_client,
            repo_access=repo_access,
            learning_memory=learning_memory,
            cognitive_layer1=cognitive_layer1,
            session=session
        )
    return _learning_integration
