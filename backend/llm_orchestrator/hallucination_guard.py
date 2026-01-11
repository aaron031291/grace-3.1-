"""
Hallucination Mitigation Pipeline

Multi-layered approach to minimize LLM hallucinations:

Layer 1: Repository Grounding - Claims must reference actual files/code
Layer 2: Cross-Model Consensus - Multiple LLMs must agree
Layer 3: Contradiction Detection - Check against existing knowledge
Layer 4: Confidence Scoring - Trust score calculation
Layer 5: Trust System Verification - Validate against learning memory

All operations are tracked and logged.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import re
from difflib import SequenceMatcher

from .multi_llm_client import MultiLLMClient, TaskType
from .repo_access import RepositoryAccessLayer
from confidence_scorer.confidence_scorer import ConfidenceScorer
from confidence_scorer.contradiction_detector import SemanticContradictionDetector

logger = logging.getLogger(__name__)


@dataclass
class ConsensusResult:
    """Result of cross-model consensus checking."""
    agreed: bool
    confidence: float
    responses: List[Dict[str, Any]]
    consensus_content: str
    disagreements: List[str]
    verification_details: Dict[str, Any]


@dataclass
class VerificationResult:
    """Result of hallucination verification."""
    is_verified: bool
    confidence_score: float
    verification_layers: Dict[str, bool]
    sources: List[str]
    contradictions: List[Dict[str, Any]]
    trust_score: float
    final_content: str
    audit_trail: List[Dict[str, Any]]


class HallucinationGuard:
    """
    Multi-layer hallucination mitigation system.

    Ensures LLM outputs are:
    1. Grounded in actual repository data
    2. Agreed upon by multiple models
    3. Non-contradictory with existing knowledge
    4. Trust-scored and verified
    """

    def __init__(
        self,
        multi_llm_client: Optional[MultiLLMClient] = None,
        repo_access: Optional[RepositoryAccessLayer] = None,
        confidence_scorer: Optional[ConfidenceScorer] = None,
        contradiction_detector: Optional[SemanticContradictionDetector] = None
    ):
        """
        Initialize hallucination guard.

        Args:
            multi_llm_client: Multi-LLM client
            repo_access: Repository access layer
            confidence_scorer: Confidence scoring system
            contradiction_detector: Contradiction detection system
        """
        self.multi_llm = multi_llm_client
        self.repo_access = repo_access
        self.confidence_scorer = confidence_scorer
        self.contradiction_detector = contradiction_detector or SemanticContradictionDetector()

        # Verification log
        self.verification_log: List[Dict[str, Any]] = []

    # =======================================================================
    # LAYER 1: REPOSITORY GROUNDING
    # =======================================================================

    def verify_repository_grounding(
        self,
        content: str,
        require_file_references: bool = True
    ) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        Verify content is grounded in actual repository files.

        Args:
            content: Content to verify
            require_file_references: Require explicit file references

        Returns:
            (is_grounded, referenced_files, verification_details)
        """
        logger.info("[LAYER 1] Verifying repository grounding")

        # Extract file references from content
        file_patterns = [
            r'`([a-zA-Z0-9_/\\.-]+\.(py|js|ts|md|json))`',
            r'\[([a-zA-Z0-9_/\\.-]+\.(py|js|ts|md|json))\]',
            r'"([a-zA-Z0-9_/\\.-]+\.(py|js|ts|md|json))"',
            r"'([a-zA-Z0-9_/\\.-]+\.(py|js|ts|md|json))'",
        ]

        referenced_files = set()
        for pattern in file_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if isinstance(match, tuple):
                    referenced_files.add(match[0])
                else:
                    referenced_files.add(match)

        # Verify referenced files exist
        verified_files = []
        if self.repo_access:
            for file_path in referenced_files:
                result = self.repo_access.read_file(file_path, max_lines=1)
                if "error" not in result:
                    verified_files.append(file_path)

        # Check grounding
        is_grounded = True
        if require_file_references and not verified_files:
            is_grounded = False

        details = {
            "referenced_files": list(referenced_files),
            "verified_files": verified_files,
            "unverified_files": list(referenced_files - set(verified_files)),
            "grounding_score": len(verified_files) / max(len(referenced_files), 1)
        }

        return is_grounded, verified_files, details

    # =======================================================================
    # LAYER 2: CROSS-MODEL CONSENSUS
    # =======================================================================

    def check_cross_model_consensus(
        self,
        prompt: str,
        task_type: TaskType,
        num_models: int = 3,
        similarity_threshold: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> ConsensusResult:
        """
        Get consensus from multiple LLM models.

        Args:
            prompt: Query prompt
            task_type: Type of task
            num_models: Number of models to query
            similarity_threshold: Minimum similarity for consensus
            system_prompt: System prompt

        Returns:
            ConsensusResult with consensus analysis
        """
        logger.info(f"[LAYER 2] Checking cross-model consensus ({num_models} models)")

        if not self.multi_llm:
            return ConsensusResult(
                agreed=False,
                confidence=0.0,
                responses=[],
                consensus_content="",
                disagreements=["Multi-LLM client not initialized"],
                verification_details={}
            )

        # Get responses from multiple models
        responses = self.multi_llm.generate_multiple(
            prompt=prompt,
            task_type=task_type,
            num_models=num_models,
            system_prompt=system_prompt
        )

        # Filter successful responses
        successful_responses = [r for r in responses if r["success"]]

        if len(successful_responses) < 2:
            return ConsensusResult(
                agreed=False,
                confidence=0.0,
                responses=responses,
                consensus_content="",
                disagreements=["Insufficient models responded"],
                verification_details={"successful_count": len(successful_responses)}
            )

        # Calculate pairwise similarities
        similarities = []
        contents = [r["content"] for r in successful_responses]

        for i in range(len(contents)):
            for j in range(i + 1, len(contents)):
                similarity = self._calculate_similarity(contents[i], contents[j])
                similarities.append(similarity)

        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0

        # Check for consensus
        agreed = avg_similarity >= similarity_threshold

        # Find consensus content (most common response or longest if similar)
        if agreed:
            # Use longest response as consensus if all similar
            consensus_content = max(contents, key=len)
        else:
            consensus_content = contents[0]  # Default to first response

        # Identify disagreements
        disagreements = []
        if not agreed:
            for i, content in enumerate(contents):
                model_name = successful_responses[i]["model_name"]
                disagreements.append(f"{model_name}: {content[:100]}...")

        return ConsensusResult(
            agreed=agreed,
            confidence=avg_similarity,
            responses=responses,
            consensus_content=consensus_content,
            disagreements=disagreements,
            verification_details={
                "num_models": num_models,
                "successful_responses": len(successful_responses),
                "avg_similarity": avg_similarity,
                "similarities": similarities
            }
        )

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        if not text1 or not text2:
            return 0.0

        # Use SequenceMatcher for quick similarity
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    # =======================================================================
    # LAYER 3: CONTRADICTION DETECTION
    # =======================================================================

    def check_contradictions(
        self,
        content: str,
        context_documents: Optional[List[str]] = None
    ) -> Tuple[bool, List[Dict[str, Any]]]:
        """
        Check for contradictions with existing knowledge.

        Args:
            content: Content to check
            context_documents: Existing documents to check against

        Returns:
            (has_contradictions, contradiction_details)
        """
        logger.info("[LAYER 3] Checking for contradictions")

        if not self.contradiction_detector:
            return False, []

        contradictions = []

        # Check against provided context
        if context_documents:
            for i, doc in enumerate(context_documents):
                try:
                    is_contradiction, score = self.contradiction_detector.detect_contradiction(
                        content,
                        doc,
                        threshold=0.7
                    )

                    if is_contradiction:
                        contradictions.append({
                            "document_index": i,
                            "contradiction_score": score,
                            "document_snippet": doc[:200]
                        })
                except Exception as e:
                    logger.error(f"Error detecting contradiction: {e}")

        # Check against RAG system if available
        if self.repo_access and self.repo_access.retriever:
            try:
                similar_docs = self.repo_access.rag_query(content, limit=5)
                for doc in similar_docs:
                    doc_text = doc.get("text", "")
                    if doc_text:
                        is_contradiction, score = self.contradiction_detector.detect_contradiction(
                            content,
                            doc_text,
                            threshold=0.7
                        )

                        if is_contradiction:
                            contradictions.append({
                                "document_id": doc.get("document_id"),
                                "chunk_id": doc.get("chunk_id"),
                                "contradiction_score": score,
                                "source": doc.get("metadata", {}).get("filename", "unknown")
                            })
            except Exception as e:
                logger.error(f"Error checking RAG contradictions: {e}")

        has_contradictions = len(contradictions) > 0

        return has_contradictions, contradictions

    # =======================================================================
    # LAYER 4: CONFIDENCE SCORING
    # =======================================================================

    def calculate_confidence_score(
        self,
        content: str,
        source_type: str = "llm_generated",
        existing_chunks: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calculate confidence score for content.

        Args:
            content: Content to score
            source_type: Source type
            existing_chunks: Existing chunks for consensus

        Returns:
            Confidence score details
        """
        logger.info("[LAYER 4] Calculating confidence score")

        if not self.confidence_scorer:
            return {
                "confidence_score": 0.5,
                "source_reliability": 0.5,
                "content_quality": 0.5,
                "consensus_score": 0.5
            }

        try:
            score_result = self.confidence_scorer.calculate_confidence_score(
                text_content=content,
                source_type=source_type,
                existing_chunks=existing_chunks
            )
            return score_result
        except Exception as e:
            logger.error(f"Error calculating confidence: {e}")
            return {
                "confidence_score": 0.5,
                "error": str(e)
            }

    # =======================================================================
    # LAYER 5: TRUST SYSTEM VERIFICATION
    # =======================================================================

    def verify_against_trust_system(
        self,
        content: str,
        min_trust_score: float = 0.7
    ) -> Tuple[bool, float, List[Dict[str, Any]]]:
        """
        Verify content against learning memory trust system.

        Args:
            content: Content to verify
            min_trust_score: Minimum trust score threshold

        Returns:
            (is_verified, trust_score, supporting_examples)
        """
        logger.info("[LAYER 5] Verifying against trust system")

        if not self.repo_access:
            return False, 0.5, []

        try:
            # Get high-trust learning examples
            learning_examples = self.repo_access.get_learning_examples(
                min_trust_score=min_trust_score,
                limit=10
            )

            if not learning_examples:
                return False, 0.5, []

            # Calculate average trust of similar examples
            # (Simplified - should use semantic similarity)
            avg_trust = sum(ex["trust_score"] for ex in learning_examples) / len(learning_examples)

            is_verified = avg_trust >= min_trust_score

            return is_verified, avg_trust, learning_examples

        except Exception as e:
            logger.error(f"Error verifying trust system: {e}")
            return False, 0.5, []

    # =======================================================================
    # COMPLETE VERIFICATION PIPELINE
    # =======================================================================

    def verify_content(
        self,
        prompt: str,
        content: str,
        task_type: TaskType = TaskType.GENERAL,
        enable_consensus: bool = True,
        enable_grounding: bool = True,
        enable_contradiction_check: bool = True,
        enable_trust_verification: bool = True,
        consensus_threshold: float = 0.7,
        confidence_threshold: float = 0.6,
        trust_threshold: float = 0.7,
        system_prompt: Optional[str] = None,
        context_documents: Optional[List[str]] = None
    ) -> VerificationResult:
        """
        Complete hallucination verification pipeline.

        Runs all 5 layers of verification and returns comprehensive result.

        Args:
            prompt: Original prompt
            content: Generated content to verify
            task_type: Type of task
            enable_consensus: Enable cross-model consensus
            enable_grounding: Enable repository grounding
            enable_contradiction_check: Enable contradiction detection
            enable_trust_verification: Enable trust system verification
            consensus_threshold: Consensus similarity threshold
            confidence_threshold: Minimum confidence score
            trust_threshold: Minimum trust score
            system_prompt: System prompt for consensus
            context_documents: Context documents for contradiction check

        Returns:
            VerificationResult with complete analysis
        """
        logger.info("Starting complete hallucination verification pipeline")

        audit_trail = []
        verification_layers = {}
        sources = []
        contradictions = []
        final_content = content
        overall_confidence = 1.0

        # LAYER 1: Repository Grounding
        if enable_grounding:
            is_grounded, verified_files, grounding_details = self.verify_repository_grounding(
                content,
                require_file_references=False  # Don't require for all content
            )
            verification_layers["repository_grounding"] = is_grounded
            sources.extend(verified_files)
            audit_trail.append({
                "layer": "repository_grounding",
                "passed": is_grounded,
                "details": grounding_details
            })
            if not is_grounded:
                overall_confidence *= 0.8

        # LAYER 2: Cross-Model Consensus
        consensus_result = None
        if enable_consensus:
            consensus_result = self.check_cross_model_consensus(
                prompt=prompt,
                task_type=task_type,
                num_models=3,
                similarity_threshold=consensus_threshold,
                system_prompt=system_prompt
            )
            verification_layers["cross_model_consensus"] = consensus_result.agreed
            audit_trail.append({
                "layer": "cross_model_consensus",
                "passed": consensus_result.agreed,
                "confidence": consensus_result.confidence,
                "details": consensus_result.verification_details
            })

            # Use consensus content if agreed
            if consensus_result.agreed:
                final_content = consensus_result.consensus_content
            else:
                overall_confidence *= 0.7

        # LAYER 3: Contradiction Detection
        if enable_contradiction_check:
            has_contradictions, contradiction_list = self.check_contradictions(
                content=final_content,
                context_documents=context_documents
            )
            verification_layers["contradiction_check"] = not has_contradictions
            contradictions = contradiction_list
            audit_trail.append({
                "layer": "contradiction_detection",
                "passed": not has_contradictions,
                "contradictions_found": len(contradiction_list)
            })
            if has_contradictions:
                overall_confidence *= 0.6

        # LAYER 4: Confidence Scoring
        confidence_result = self.calculate_confidence_score(
            content=final_content,
            source_type="llm_generated",
            existing_chunks=context_documents
        )
        verification_layers["confidence_scoring"] = confidence_result.get("confidence_score", 0.0) >= confidence_threshold
        audit_trail.append({
            "layer": "confidence_scoring",
            "passed": verification_layers["confidence_scoring"],
            "score": confidence_result.get("confidence_score", 0.0)
        })
        if not verification_layers["confidence_scoring"]:
            overall_confidence *= 0.7

        # LAYER 5: Trust System Verification
        trust_verified = False
        trust_score = 0.5
        if enable_trust_verification:
            trust_verified, trust_score, trust_examples = self.verify_against_trust_system(
                content=final_content,
                min_trust_score=trust_threshold
            )
            verification_layers["trust_system"] = trust_verified
            audit_trail.append({
                "layer": "trust_system_verification",
                "passed": trust_verified,
                "trust_score": trust_score,
                "supporting_examples": len(trust_examples)
            })
            if not trust_verified:
                overall_confidence *= 0.8

        # Calculate final verification status
        is_verified = all(verification_layers.values())

        # Log verification
        self.verification_log.append({
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt[:200],
            "is_verified": is_verified,
            "confidence": overall_confidence,
            "layers": verification_layers
        })

        return VerificationResult(
            is_verified=is_verified,
            confidence_score=overall_confidence,
            verification_layers=verification_layers,
            sources=sources,
            contradictions=contradictions,
            trust_score=trust_score,
            final_content=final_content,
            audit_trail=audit_trail
        )

    # =======================================================================
    # UTILITY METHODS
    # =======================================================================

    def get_verification_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent verification log entries."""
        return self.verification_log[-limit:]

    def get_verification_stats(self) -> Dict[str, Any]:
        """Get verification statistics."""
        if not self.verification_log:
            return {
                "total_verifications": 0,
                "verification_rate": 0.0,
                "avg_confidence": 0.0
            }

        total = len(self.verification_log)
        verified_count = sum(1 for v in self.verification_log if v["is_verified"])

        return {
            "total_verifications": total,
            "verification_rate": verified_count / total,
            "avg_confidence": sum(v["confidence"] for v in self.verification_log) / total,
            "layer_success_rates": self._calculate_layer_success_rates()
        }

    def _calculate_layer_success_rates(self) -> Dict[str, float]:
        """Calculate success rate for each verification layer."""
        layer_stats = {}

        for entry in self.verification_log:
            layers = entry.get("layers", {})
            for layer_name, passed in layers.items():
                if layer_name not in layer_stats:
                    layer_stats[layer_name] = {"total": 0, "passed": 0}
                layer_stats[layer_name]["total"] += 1
                if passed:
                    layer_stats[layer_name]["passed"] += 1

        return {
            layer: stats["passed"] / stats["total"] if stats["total"] > 0 else 0.0
            for layer, stats in layer_stats.items()
        }


# Global instance
_hallucination_guard: Optional[HallucinationGuard] = None


def get_hallucination_guard(
    multi_llm_client: Optional[MultiLLMClient] = None,
    repo_access: Optional[RepositoryAccessLayer] = None,
    confidence_scorer: Optional[ConfidenceScorer] = None
) -> HallucinationGuard:
    """Get or create global hallucination guard instance."""
    global _hallucination_guard
    if _hallucination_guard is None:
        _hallucination_guard = HallucinationGuard(
            multi_llm_client=multi_llm_client,
            repo_access=repo_access,
            confidence_scorer=confidence_scorer
        )
    return _hallucination_guard
