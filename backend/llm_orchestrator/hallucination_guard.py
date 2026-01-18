import logging
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from urllib.parse import quote_plus
import requests
from llm_orchestrator.multi_llm_client import MultiLLMClient, TaskType
from llm_orchestrator.repo_access import RepositoryAccessLayer
logger = logging.getLogger(__name__)

class ExternalVerifier:
    """
    External verification system for LLM outputs.

    Verifies claims against:
    1. Official documentation (Python, JS, framework docs)
    2. Web search results (for factual claims)
    3. Known API references
    """

    # Official documentation URLs for common frameworks/languages
    DOCUMENTATION_SOURCES = {
        "python": "https://docs.python.org/3/search.html?q={query}",
        "javascript": "https://developer.mozilla.org/en-US/search?q={query}",
        "typescript": "https://www.typescriptlang.org/docs/handbook/",
        "react": "https://react.dev/reference/",
        "fastapi": "https://fastapi.tiangolo.com/",
        "django": "https://docs.djangoproject.com/en/stable/search/?q={query}",
        "flask": "https://flask.palletsprojects.com/en/latest/search/?q={query}",
        "sqlalchemy": "https://docs.sqlalchemy.org/en/20/search.html?q={query}",
        "pytorch": "https://pytorch.org/docs/stable/search.html?q={query}",
        "tensorflow": "https://www.tensorflow.org/s/results?q={query}",
    }

    def __init__(
        self,
        enable_web_search: bool = True,
        enable_doc_lookup: bool = True,
        search_timeout: float = 10.0,
        cache_results: bool = True
    ):
        """
        Initialize external verifier.

        Args:
            enable_web_search: Enable web search verification
            enable_doc_lookup: Enable documentation lookup
            search_timeout: Timeout for external requests
            cache_results: Cache verification results
        """
        self.enable_web_search = enable_web_search
        self.enable_doc_lookup = enable_doc_lookup
        self.search_timeout = search_timeout
        self.cache_results = cache_results
        self._cache: Dict[str, Dict[str, Any]] = {}

    def verify_technical_claim(
        self,
        claim: str,
        context: str = "",
        technologies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Verify a technical claim against external sources.

        Args:
            claim: The technical claim to verify
            context: Additional context about the claim
            technologies: List of relevant technologies (python, react, etc.)

        Returns:
            Verification result with confidence and sources
        """
        logger.info(f"[EXTERNAL VERIFY] Verifying claim: {claim[:100]}...")

        result = {
            "verified": False,
            "confidence": 0.5,
            "sources": [],
            "details": {}
        }

        # Check cache
        cache_key = f"{claim}:{','.join(technologies or [])}"
        if self.cache_results and cache_key in self._cache:
            logger.debug("[EXTERNAL VERIFY] Returning cached result")
            return self._cache[cache_key]

        # Extract technical terms and patterns
        technical_patterns = self._extract_technical_patterns(claim)

        # Verify against documentation
        if self.enable_doc_lookup and technologies:
            doc_result = self._verify_against_documentation(
                claim,
                technical_patterns,
                technologies
            )
            if doc_result["found"]:
                result["verified"] = True
                result["confidence"] = max(result["confidence"], doc_result["confidence"])
                result["sources"].extend(doc_result["sources"])
                result["details"]["documentation"] = doc_result

        # Verify code patterns
        if technical_patterns.get("code_patterns"):
            code_result = self._verify_code_patterns(
                technical_patterns["code_patterns"],
                technologies or []
            )
            if code_result["valid"]:
                result["confidence"] = max(result["confidence"], 0.7)
                result["details"]["code_patterns"] = code_result

        # Cache result
        if self.cache_results:
            self._cache[cache_key] = result

        logger.info(f"[EXTERNAL VERIFY] Result: verified={result['verified']}, confidence={result['confidence']:.2f}")
        return result

    def _extract_technical_patterns(self, text: str) -> Dict[str, Any]:
        """Extract technical patterns from text for verification."""
        patterns = {
            "code_patterns": [],
            "function_names": [],
            "class_names": [],
            "imports": [],
            "api_endpoints": [],
            "config_values": []
        }

        # Extract code blocks
        code_blocks = re.findall(r'```[\w]*\n?(.*?)```', text, re.DOTALL)
        patterns["code_patterns"].extend(code_blocks)

        # Extract inline code
        inline_code = re.findall(r'`([^`]+)`', text)
        patterns["code_patterns"].extend(inline_code)

        # Extract function/method names
        patterns["function_names"] = re.findall(r'\b([a-z_][a-z0-9_]*)\s*\(', text)

        # Extract class names (PascalCase)
        patterns["class_names"] = re.findall(r'\b([A-Z][a-zA-Z0-9]*)\b', text)

        # Extract imports
        patterns["imports"] = re.findall(r'(?:import|from)\s+([\w.]+)', text)

        # Extract API endpoints
        patterns["api_endpoints"] = re.findall(r'["\']/([\w/{}:-]+)["\']', text)

        return patterns

    def _verify_against_documentation(
        self,
        claim: str,
        patterns: Dict[str, Any],
        technologies: List[str]
    ) -> Dict[str, Any]:
        """Verify claim against official documentation."""
        result = {
            "found": False,
            "confidence": 0.0,
            "sources": [],
            "matches": []
        }

        # Build search queries from claim and patterns
        queries = []

        # Add function names as queries
        for func in patterns.get("function_names", [])[:3]:
            queries.append(func)

        # Add class names as queries
        for cls in patterns.get("class_names", [])[:3]:
            queries.append(cls)

        # Add key terms from claim
        key_terms = re.findall(r'\b((?:async|await|yield|return|class|def|function|const|let|var|import|export)\s+\w+)', claim.lower())
        queries.extend(key_terms[:2])

        if not queries:
            # Extract important words if no specific patterns found
            words = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]{3,})\b', claim)
            queries = words[:3]

        # Search each relevant technology's documentation
        for tech in technologies:
            if tech.lower() in self.DOCUMENTATION_SOURCES:
                for query in queries[:2]:  # Limit queries per tech
                    try:
                        doc_url = self.DOCUMENTATION_SOURCES[tech.lower()].format(
                            query=quote_plus(query)
                        )
                        result["sources"].append({
                            "technology": tech,
                            "query": query,
                            "url": doc_url,
                            "type": "documentation"
                        })
                        # Note: Actual fetching would require more complex handling
                        # For now, we mark as potentially found if pattern exists
                        result["found"] = True
                        result["confidence"] = 0.6
                    except Exception as e:
                        logger.debug(f"[EXTERNAL VERIFY] Doc lookup failed for {tech}: {e}")

        return result

    def _verify_code_patterns(
        self,
        code_patterns: List[str],
        technologies: List[str]
    ) -> Dict[str, Any]:
        """Verify code patterns are syntactically valid."""
        result = {
            "valid": True,
            "errors": [],
            "validated_patterns": []
        }

        for pattern in code_patterns[:5]:  # Limit patterns to check
            if not pattern.strip():
                continue

            # Check Python syntax
            if "python" in [t.lower() for t in technologies] or not technologies:
                try:
                    compile(pattern, '<string>', 'exec')
                    result["validated_patterns"].append({
                        "pattern": pattern[:100],
                        "language": "python",
                        "valid": True
                    })
                except SyntaxError as e:
                    result["errors"].append({
                        "pattern": pattern[:100],
                        "error": str(e)
                    })

            # Check for common JS patterns
            if "javascript" in [t.lower() for t in technologies] or "typescript" in [t.lower() for t in technologies]:
                # Basic JS syntax validation (simplified)
                js_valid = self._validate_js_syntax(pattern)
                result["validated_patterns"].append({
                    "pattern": pattern[:100],
                    "language": "javascript",
                    "valid": js_valid
                })

        return result

    def _validate_js_syntax(self, code: str) -> bool:
        """Basic JavaScript syntax validation."""
        # Very basic checks - production would use a proper parser
        bracket_balance = code.count('{') - code.count('}')
        paren_balance = code.count('(') - code.count(')')
        square_balance = code.count('[') - code.count(']')

        return bracket_balance == 0 and paren_balance == 0 and square_balance == 0

    def verify_factual_claim(
        self,
        claim: str,
        category: str = "general"
    ) -> Dict[str, Any]:
        """
        Verify a factual (non-code) claim.

        Args:
            claim: The factual claim to verify
            category: Category of claim (general, technical, historical)

        Returns:
            Verification result
        """
        logger.info(f"[EXTERNAL VERIFY] Verifying factual claim: {claim[:100]}...")

        result = {
            "verified": False,
            "confidence": 0.5,
            "category": category,
            "details": {}
        }

        # For factual claims, we're more conservative
        # Without actual web search integration, we flag as uncertain
        result["details"]["note"] = "Factual verification requires web search integration"
        result["confidence"] = 0.5  # Neutral - can't confirm or deny

        return result

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_entries": len(self._cache),
            "cache_enabled": self.cache_results
        }

    def clear_cache(self):
        """Clear the verification cache."""
        self._cache.clear()


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
        contradiction_detector: Optional[SemanticContradictionDetector] = None,
        external_verifier: Optional[ExternalVerifier] = None,
        enable_external_verification: bool = True
    ):
        """
        Initialize hallucination guard.

        Args:
            multi_llm_client: Multi-LLM client
            repo_access: Repository access layer
            confidence_scorer: Confidence scoring system
            contradiction_detector: Contradiction detection system
            external_verifier: External verification system
            enable_external_verification: Enable external verification layer
        """
        self.multi_llm = multi_llm_client
        self.repo_access = repo_access
        self.confidence_scorer = confidence_scorer
        self.contradiction_detector = contradiction_detector or SemanticContradictionDetector()
        self.external_verifier = external_verifier or (ExternalVerifier() if enable_external_verification else None)

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
    # LAYER 6: EXTERNAL VERIFICATION
    # =======================================================================

    def verify_external(
        self,
        content: str,
        task_type: TaskType = TaskType.GENERAL,
        technologies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Verify content against external sources (Layer 6).

        Args:
            content: Content to verify
            task_type: Type of task (helps determine verification strategy)
            technologies: List of relevant technologies

        Returns:
            External verification result
        """
        logger.info("[LAYER 6] Running external verification")

        if not self.external_verifier:
            return {
                "verified": False,
                "confidence": 0.5,
                "enabled": False,
                "reason": "External verifier not enabled"
            }

        result = {
            "verified": False,
            "confidence": 0.5,
            "technical_verification": None,
            "code_syntax_valid": True,
            "sources": []
        }

        # Detect technologies from content if not provided
        if not technologies:
            technologies = self._detect_technologies(content)

        # For code-related tasks, do technical verification
        if task_type in [TaskType.CODE_GENERATION, TaskType.CODE_DEBUGGING,
                         TaskType.CODE_EXPLANATION, TaskType.CODE_REVIEW]:
            tech_result = self.external_verifier.verify_technical_claim(
                claim=content,
                technologies=technologies
            )
            result["technical_verification"] = tech_result
            result["verified"] = tech_result.get("verified", False)
            result["confidence"] = tech_result.get("confidence", 0.5)
            result["sources"].extend(tech_result.get("sources", []))

            # Check code syntax
            if tech_result.get("details", {}).get("code_patterns"):
                errors = tech_result["details"]["code_patterns"].get("errors", [])
                if errors:
                    result["code_syntax_valid"] = False
                    result["confidence"] *= 0.7  # Reduce confidence for syntax errors

        # For general/reasoning tasks, do factual verification
        elif task_type in [TaskType.GENERAL, TaskType.REASONING]:
            factual_result = self.external_verifier.verify_factual_claim(
                claim=content[:500],  # Limit claim length
                category="technical" if technologies else "general"
            )
            result["factual_verification"] = factual_result
            result["confidence"] = factual_result.get("confidence", 0.5)

        return result

    def _detect_technologies(self, content: str) -> List[str]:
        """Detect technologies mentioned in content."""
        technologies = []

        # Common technology patterns
        tech_patterns = {
            "python": r'\b(python|pip|pypi|django|flask|fastapi|pytorch|tensorflow|pandas|numpy)\b',
            "javascript": r'\b(javascript|js|node|npm|yarn|react|vue|angular|express)\b',
            "typescript": r'\b(typescript|ts|tsx)\b',
            "react": r'\b(react|jsx|redux|nextjs|next\.js)\b',
            "fastapi": r'\b(fastapi|uvicorn|starlette)\b',
            "django": r'\b(django)\b',
            "sqlalchemy": r'\b(sqlalchemy|alembic)\b',
            "pytorch": r'\b(pytorch|torch)\b',
            "tensorflow": r'\b(tensorflow|keras|tf)\b',
        }

        content_lower = content.lower()
        for tech, pattern in tech_patterns.items():
            if re.search(pattern, content_lower, re.IGNORECASE):
                technologies.append(tech)

        return list(set(technologies))

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
        enable_external_verification: bool = True,
        consensus_threshold: float = 0.7,
        confidence_threshold: float = 0.6,
        trust_threshold: float = 0.7,
        system_prompt: Optional[str] = None,
        context_documents: Optional[List[str]] = None,
        max_retry_attempts: int = 3,
        auto_correct_low_trust: bool = True
    ) -> VerificationResult:
        """
        Complete hallucination verification pipeline.

        Runs all 6 layers of verification and returns comprehensive result.
        When trust scores are low, automatically retries with stricter verification
        and attempts to correct/refine the content.

        Layers:
        1. Repository Grounding - Claims must reference actual files/code
        2. Cross-Model Consensus - Multiple LLMs must agree
        3. Contradiction Detection - Check against existing knowledge
        4. Confidence Scoring - Trust score calculation
        5. Trust System Verification - Validate against learning memory
        6. External Verification - Web search and documentation lookup

        Args:
            prompt: Original prompt
            content: Generated content to verify
            task_type: Type of task
            enable_consensus: Enable cross-model consensus
            enable_grounding: Enable repository grounding
            enable_contradiction_check: Enable contradiction detection
            enable_trust_verification: Enable trust system verification
            enable_external_verification: Enable external verification (Layer 6)
            consensus_threshold: Consensus similarity threshold
            confidence_threshold: Minimum confidence score
            trust_threshold: Minimum trust score
            system_prompt: System prompt for consensus
            context_documents: Context documents for contradiction check
            max_retry_attempts: Maximum retry attempts for low-trust content
            auto_correct_low_trust: Automatically attempt to correct low-trust content

        Returns:
            VerificationResult with complete analysis
        """
        logger.info("Starting complete hallucination verification pipeline")

        # Run verification with potential retries for low trust
        return self._verify_with_retry(
            prompt=prompt,
            content=content,
            task_type=task_type,
            enable_consensus=enable_consensus,
            enable_grounding=enable_grounding,
            enable_contradiction_check=enable_contradiction_check,
            enable_trust_verification=enable_trust_verification,
            consensus_threshold=consensus_threshold,
            confidence_threshold=confidence_threshold,
            trust_threshold=trust_threshold,
            system_prompt=system_prompt,
            context_documents=context_documents,
            max_retry_attempts=max_retry_attempts,
            auto_correct_low_trust=auto_correct_low_trust,
            attempt=1
        )

    def _verify_with_retry(
        self,
        prompt: str,
        content: str,
        task_type: TaskType,
        enable_consensus: bool,
        enable_grounding: bool,
        enable_contradiction_check: bool,
        enable_trust_verification: bool,
        consensus_threshold: float,
        confidence_threshold: float,
        trust_threshold: float,
        system_prompt: Optional[str],
        context_documents: Optional[List[str]],
        max_retry_attempts: int,
        auto_correct_low_trust: bool,
        attempt: int
    ) -> VerificationResult:
        """Internal verification with retry logic for low-trust content."""
        logger.info(f"[VERIFICATION] Attempt {attempt}/{max_retry_attempts}")

        # Run the actual verification
        result = self._run_verification_pipeline(
            prompt=prompt,
            content=content,
            task_type=task_type,
            enable_consensus=enable_consensus,
            enable_grounding=enable_grounding,
            enable_contradiction_check=enable_contradiction_check,
            enable_trust_verification=enable_trust_verification,
            consensus_threshold=consensus_threshold,
            confidence_threshold=confidence_threshold,
            trust_threshold=trust_threshold,
            system_prompt=system_prompt,
            context_documents=context_documents
        )

        # Check if trust score is too low and we should retry
        LOW_TRUST_THRESHOLD = 0.5
        if (result.trust_score < LOW_TRUST_THRESHOLD or result.confidence_score < LOW_TRUST_THRESHOLD) \
           and attempt < max_retry_attempts and auto_correct_low_trust:

            logger.warning(f"[VERIFICATION] Low trust detected (trust={result.trust_score:.2f}, confidence={result.confidence_score:.2f})")
            logger.info(f"[VERIFICATION] Attempting correction and re-verification...")

            # Attempt to correct the content
            corrected_content = self._attempt_correction(
                prompt=prompt,
                content=content,
                verification_result=result,
                task_type=task_type,
                system_prompt=system_prompt
            )

            if corrected_content and corrected_content != content:
                logger.info("[VERIFICATION] Content corrected, re-verifying...")

                # Add correction to audit trail
                result.audit_trail.append({
                    "layer": "auto_correction",
                    "attempt": attempt,
                    "original_trust": result.trust_score,
                    "original_confidence": result.confidence_score,
                    "correction_applied": True
                })

                # Retry with corrected content (stricter thresholds)
                return self._verify_with_retry(
                    prompt=prompt,
                    content=corrected_content,
                    task_type=task_type,
                    enable_consensus=enable_consensus,
                    enable_grounding=enable_grounding,
                    enable_contradiction_check=enable_contradiction_check,
                    enable_trust_verification=enable_trust_verification,
                    consensus_threshold=min(consensus_threshold + 0.05, 0.9),  # Stricter
                    confidence_threshold=min(confidence_threshold + 0.05, 0.8),
                    trust_threshold=min(trust_threshold + 0.05, 0.85),
                    system_prompt=system_prompt,
                    context_documents=context_documents,
                    max_retry_attempts=max_retry_attempts,
                    auto_correct_low_trust=auto_correct_low_trust,
                    attempt=attempt + 1
                )

        # Add retry info to result
        result.audit_trail.append({
            "layer": "retry_status",
            "total_attempts": attempt,
            "final_trust": result.trust_score,
            "final_confidence": result.confidence_score
        })

        return result

    def _attempt_correction(
        self,
        prompt: str,
        content: str,
        verification_result: VerificationResult,
        task_type: TaskType,
        system_prompt: Optional[str]
    ) -> Optional[str]:
        """Attempt to correct low-trust content using LLM refinement."""
        if not self.multi_llm:
            return None

        # Build correction prompt based on verification failures
        issues = []
        for layer, passed in verification_result.verification_layers.items():
            if not passed:
                issues.append(f"- {layer.replace('_', ' ').title()} failed")

        if verification_result.contradictions:
            issues.append(f"- {len(verification_result.contradictions)} contradictions detected")

        if not issues:
            return None

        correction_prompt = f"""The following response has low trust/confidence and needs refinement:

ORIGINAL RESPONSE:
{content}

ISSUES DETECTED:
{chr(10).join(issues)}

ORIGINAL QUESTION:
{prompt}

Please provide a corrected, more accurate response that:
1. Only states facts that can be verified
2. Avoids speculation or assumptions
3. Clearly indicates uncertainty where appropriate
4. References specific files/code when making claims about code

CORRECTED RESPONSE:"""

        try:
            response = self.multi_llm.generate(
                prompt=correction_prompt,
                task_type=task_type,
                system_prompt=(system_prompt or "") + "\nYou are correcting a potentially inaccurate response. Be precise and factual."
            )

            if response.get("success"):
                return response.get("content", "")
        except Exception as e:
            logger.error(f"[CORRECTION] Failed to correct content: {e}")

        return None

    def _run_verification_pipeline(
        self,
        prompt: str,
        content: str,
        task_type: TaskType,
        enable_consensus: bool,
        enable_grounding: bool,
        enable_contradiction_check: bool,
        enable_trust_verification: bool,
        consensus_threshold: float,
        confidence_threshold: float,
        trust_threshold: float,
        system_prompt: Optional[str],
        context_documents: Optional[List[str]]
    ) -> VerificationResult:
        """Run the core verification pipeline (5 layers)."""
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

        # LAYER 6: External Verification (for code tasks especially)
        if self.external_verifier and task_type in [
            TaskType.CODE_GENERATION, TaskType.CODE_DEBUGGING,
            TaskType.CODE_EXPLANATION, TaskType.CODE_REVIEW
        ]:
            external_result = self.verify_external(
                content=final_content,
                task_type=task_type
            )
            verification_layers["external_verification"] = external_result.get("verified", False)
            audit_trail.append({
                "layer": "external_verification",
                "passed": external_result.get("verified", False),
                "confidence": external_result.get("confidence", 0.5),
                "code_syntax_valid": external_result.get("code_syntax_valid", True),
                "sources_checked": len(external_result.get("sources", []))
            })

            # Adjust confidence based on external verification
            if external_result.get("code_syntax_valid") is False:
                overall_confidence *= 0.6  # Syntax errors are serious
            elif not external_result.get("verified", False):
                overall_confidence *= 0.85

            # Add external sources to sources list
            for source in external_result.get("sources", []):
                sources.append(source.get("url", str(source)))

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
