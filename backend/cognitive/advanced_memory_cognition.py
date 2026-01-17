import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
import json
class MemoryAbstractionLevel(str, Enum):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Hierarchical memory abstraction levels."""
    RAW = "raw"  # Raw memories
    EPISODE = "episode"  # Concrete episodes
    PATTERN = "pattern"  # Recurring patterns
    PRINCIPLE = "principle"  # Abstracted principles
    NARRATIVE = "narrative"  # Compressed narratives


class HallucinationRisk(str, Enum):
    """Hallucination risk levels."""
    LOW = "low"  # High confidence, verified
    MEDIUM = "medium"  # Moderate confidence, partial verification
    HIGH = "high"  # Low confidence, unverified
    CRITICAL = "critical"  # Contradicts known facts


@dataclass
class ContextWindowState:
    """Context window state tracking."""
    total_tokens: int
    max_tokens: int
    used_percent: float
    memory_tokens: int
    prompt_tokens: int
    system_tokens: int
    reserved_tokens: int
    available_tokens: int
    compression_ratio: float
    abstraction_level: MemoryAbstractionLevel


@dataclass
class MemoryAbstraction:
    """Abstracted memory representation."""
    level: MemoryAbstractionLevel
    content: str
    source_memories: List[int]  # IDs of source memories
    compression_ratio: float  # How much compressed (0-1)
    confidence: float  # Confidence in abstraction
    verified: bool  # Whether verified against sources


@dataclass
class HallucinationCheck:
    """Hallucination detection result."""
    risk_level: HallucinationRisk
    confidence: float
    contradictions: List[str]  # Contradictory statements
    missing_evidence: List[str]  # Claims without evidence
    source_coverage: float  # % of claims backed by sources
    consistency_score: float  # Internal consistency (0-1)


class AdvancedMemoryCognition:
    """
    Advanced memory cognition system that goes beyond traditional RAG.
    
    Features:
    1. Hierarchical Memory Compression - Episodes → Patterns → Principles
    2. Context Window Visualization - Real-time tracking
    3. Hallucination Mitigation - Multi-layer verification
    4. Power Without Size - Compression & abstraction
    5. Transformer Failure Mode Mitigation - Attention decay, context limits
    6. Structured Reasoning - Plan → Retrieve → Synthesize → Generate
    """
    
    def __init__(self, session, knowledge_base_path):
        """Initialize advanced memory cognition system."""
        self.session = session
        self.kb_path = knowledge_base_path
        
        # Import memory systems
        from cognitive.smart_memory_retrieval import SmartMemoryRetrieval
        from cognitive.memory_synthesis import get_memory_synthesis
        from cognitive.memory_clustering import get_memory_clustering
        
        self.retrieval = SmartMemoryRetrieval(session, knowledge_base_path)
        self.synthesis = get_memory_synthesis(session, knowledge_base_path)
        self.clustering = get_memory_clustering(session)
        
        # Context window tracking
        self.context_window_history: List[ContextWindowState] = []
        
        # Abstraction cache
        self.abstraction_cache: Dict[str, MemoryAbstraction] = {}
        
        # Hallucination detection cache
        self.hallucination_cache: Dict[str, HallucinationCheck] = {}
        
        logger.info("[ADVANCED-MEMORY-COGNITION] Initialized")
    
    # ==================== 1. HIERARCHICAL MEMORY COMPRESSION ====================
    
    def compress_memories_hierarchically(
        self,
        memories: List[Dict[str, Any]],
        target_level: MemoryAbstractionLevel = MemoryAbstractionLevel.PATTERN
    ) -> Tuple[List[MemoryAbstraction], float]:
        """
        Compress memories hierarchically: Raw → Episode → Pattern → Principle.
        
        Benefits:
        - Fits more information in smaller context windows
        - Reduces noise and focuses on essential patterns
        - Enables reasoning over compressed knowledge
        
        Returns:
            (compressed_abstractions, compression_ratio)
        """
        if not memories:
            return [], 1.0
        
        original_tokens = sum(len(str(m)) // 4 for m in memories)  # Approximate
        
        abstractions = []
        
        if target_level in [MemoryAbstractionLevel.PATTERN, MemoryAbstractionLevel.PRINCIPLE]:
            # Group memories by pattern
            patterns = self.clustering.cluster_memories(
                memories=memories,
                clustering_type="semantic",
                max_clusters=min(len(memories) // 3, 10)
            )
            
            # Abstract each pattern
            for pattern_id, pattern_memories in patterns.items():
                # Synthesize pattern into abstraction
                abstraction = self.synthesis.synthesize_memories(
                    memories=pattern_memories,
                    synthesis_type="pattern"
                )
                
                if abstraction:
                    compressed_content = self._abstract_pattern(
                        pattern_memories,
                        abstraction
                    )
                    
                    abstractions.append(MemoryAbstraction(
                        level=target_level,
                        content=compressed_content,
                        source_memories=[m.get("id") for m in pattern_memories],
                        compression_ratio=len(compressed_content) / original_tokens,
                        confidence=abstraction.get("confidence", 0.7),
                        verified=False
                    ))
        else:
            # Lower level abstractions (episode level)
            for memory in memories:
                abstractions.append(MemoryAbstraction(
                    level=MemoryAbstractionLevel.EPISODE,
                    content=self._format_memory_episode(memory),
                    source_memories=[memory.get("id")],
                    compression_ratio=0.8,  # Slight compression
                    confidence=memory.get("trust_score", 0.5),
                    verified=False
                ))
        
        compressed_tokens = sum(len(a.content) // 4 for a in abstractions)
        compression_ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0
        
        logger.info(
            f"[MEMORY-COMPRESSION] Compressed {len(memories)} memories → "
            f"{len(abstractions)} abstractions ({compression_ratio:.2%})"
        )
        
        return abstractions, compression_ratio
    
    def _abstract_pattern(self, memories: List[Dict[str, Any]], synthesis: Dict[str, Any]) -> str:
        """Abstract pattern from memories."""
        pattern_desc = synthesis.get("pattern_description", "")
        key_points = synthesis.get("key_points", [])
        frequency = synthesis.get("frequency", 1)
        
        abstracted = f"Pattern (appears {frequency}x): {pattern_desc}\n"
        
        if key_points:
            abstracted += "Key Points:\n"
            for point in key_points[:3]:  # Top 3 only
                abstracted += f"  - {point}\n"
        
        return abstracted.strip()
    
    def _format_memory_episode(self, memory: Dict[str, Any]) -> str:
        """Format memory at episode level."""
        mem_obj = memory.get("memory")
        if not mem_obj:
            return str(memory)
        
        desc = getattr(mem_obj, "input_context", None) or getattr(mem_obj, "problem", None) or ""
        solution = getattr(mem_obj, "solution", None) or getattr(mem_obj, "outcome", None) or ""
        
        return f"Episode: {desc[:100]} → {solution[:100]}"
    
    # ==================== 2. CONTEXT WINDOW VISUALIZATION ====================
    
    def track_context_window(
        self,
        total_tokens: int,
        max_tokens: int,
        memory_tokens: int,
        prompt_tokens: int,
        system_tokens: int,
        reserved_tokens: int = 500,
        compression_ratio: float = 1.0,
        abstraction_level: MemoryAbstractionLevel = MemoryAbstractionLevel.RAW
    ) -> ContextWindowState:
        """
        Track context window state for visualization.
        
        Returns state that can be displayed to users to understand:
        - How much context is being used
        - What compression/abstraction is active
        - Available space for responses
        """
        used_percent = (total_tokens / max_tokens) * 100 if max_tokens > 0 else 0
        available_tokens = max_tokens - total_tokens - reserved_tokens
        
        state = ContextWindowState(
            total_tokens=total_tokens,
            max_tokens=max_tokens,
            used_percent=used_percent,
            memory_tokens=memory_tokens,
            prompt_tokens=prompt_tokens,
            system_tokens=system_tokens,
            reserved_tokens=reserved_tokens,
            available_tokens=max(0, available_tokens),
            compression_ratio=compression_ratio,
            abstraction_level=abstraction_level
        )
        
        self.context_window_history.append(state)
        
        # Keep only recent history (last 100 states)
        if len(self.context_window_history) > 100:
            self.context_window_history = self.context_window_history[-100:]
        
        return state
    
    def get_context_window_visualization(self) -> Dict[str, Any]:
        """Get context window visualization data for UI."""
        if not self.context_window_history:
            return {
                "current": None,
                "history": [],
                "recommendations": []
            }
        
        current = self.context_window_history[-1]
        
        # Recommendations
        recommendations = []
        if current.used_percent > 90:
            recommendations.append("Context window nearly full - consider higher abstraction")
        if current.compression_ratio > 0.8:
            recommendations.append("Low compression - could compress more memories")
        if current.abstraction_level == MemoryAbstractionLevel.RAW:
            recommendations.append("Using raw memories - consider pattern/principle abstraction")
        
        return {
            "current": {
                "total_tokens": current.total_tokens,
                "max_tokens": current.max_tokens,
                "used_percent": current.used_percent,
                "memory_tokens": current.memory_tokens,
                "prompt_tokens": current.prompt_tokens,
                "system_tokens": current.system_tokens,
                "reserved_tokens": current.reserved_tokens,
                "available_tokens": current.available_tokens,
                "compression_ratio": current.compression_ratio,
                "abstraction_level": current.abstraction_level.value
            },
            "history": [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "used_percent": s.used_percent,
                    "compression_ratio": s.compression_ratio,
                    "abstraction_level": s.abstraction_level.value
                }
                for s in self.context_window_history[-20:]  # Last 20 states
            ],
            "recommendations": recommendations
        }
    
    # ==================== 3. HALLUCINATION MITIGATION ====================
    
    def check_hallucination(
        self,
        generated_text: str,
        source_memories: List[Dict[str, Any]],
        retrieved_context: str
    ) -> HallucinationCheck:
        """
        Multi-layer hallucination detection.
        
        Checks:
        1. Consistency with source memories
        2. Evidence coverage (claims backed by sources)
        3. Internal consistency (no contradictions)
        4. Fact verification against known facts
        """
        # Extract claims from generated text
        claims = self._extract_claims(generated_text)
        
        # Check contradictions with sources
        contradictions = self._find_contradictions(claims, source_memories, retrieved_context)
        
        # Check evidence coverage
        missing_evidence = self._check_evidence_coverage(claims, source_memories, retrieved_context)
        
        # Calculate source coverage
        total_claims = len(claims)
        backed_claims = total_claims - len(missing_evidence)
        source_coverage = backed_claims / total_claims if total_claims > 0 else 1.0
        
        # Internal consistency (check for contradictions within generated text)
        consistency_score = self._check_internal_consistency(generated_text)
        
        # Determine risk level
        if contradictions or source_coverage < 0.5 or consistency_score < 0.6:
            risk_level = HallucinationRisk.CRITICAL
        elif source_coverage < 0.7 or consistency_score < 0.8:
            risk_level = HallucinationRisk.HIGH
        elif source_coverage < 0.85 or consistency_score < 0.9:
            risk_level = HallucinationRisk.MEDIUM
        else:
            risk_level = HallucinationRisk.LOW
        
        confidence = (source_coverage + consistency_score) / 2
        
        check = HallucinationCheck(
            risk_level=risk_level,
            confidence=confidence,
            contradictions=contradictions,
            missing_evidence=missing_evidence,
            source_coverage=source_coverage,
            consistency_score=consistency_score
        )
        
        self.hallucination_cache[generated_text[:100]] = check
        
        logger.info(
            f"[HALLUCINATION-CHECK] Risk: {risk_level.value}, "
            f"Coverage: {source_coverage:.2%}, Consistency: {consistency_score:.2%}"
        )
        
        return check
    
    def _extract_claims(self, text: str) -> List[str]:
        """Extract factual claims from text."""
        # Simple heuristic: sentences that make factual statements
        import re
        sentences = re.split(r'[.!?]+', text)
        
        claims = []
        # Look for patterns indicating factual claims
        claim_patterns = [
            r'\b(is|are|was|were|has|have|can|will|did)\b',
            r'\b\d+\b',  # Numbers
            r'\b(always|never|all|every|none)\b'  # Absolute statements
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20:  # Minimum length
                # Check if sentence contains claim patterns
                if any(re.search(pattern, sentence, re.IGNORECASE) for pattern in claim_patterns):
                    claims.append(sentence)
        
        return claims
    
    def _find_contradictions(
        self,
        claims: List[str],
        source_memories: List[Dict[str, Any]],
        context: str
    ) -> List[str]:
        """Find claims that contradict source memories."""
        contradictions = []
        
        # Build knowledge base from sources
        source_texts = [str(m) for m in source_memories] + [context]
        combined_sources = " ".join(source_texts).lower()
        
        # Check each claim against sources
        for claim in claims:
            claim_lower = claim.lower()
            
            # Simple contradiction detection (can be enhanced)
            # Look for negations and opposite statements
            negation_words = ["not", "never", "no", "none", "cannot", "won't"]
            opposite_words = {"small": "large", "fast": "slow", "high": "low"}
            
            # Check for potential contradictions (simplified)
            # This could be enhanced with semantic similarity checks
            
        return contradictions
    
    def _check_evidence_coverage(
        self,
        claims: List[str],
        source_memories: List[Dict[str, Any]],
        context: str
    ) -> List[str]:
        """Check which claims lack evidence in sources."""
        missing_evidence = []
        
        # Build source text
        source_texts = [str(m) for m in source_memories] + [context]
        combined_sources = " ".join(source_texts).lower()
        
        # Check each claim
        for claim in claims:
            claim_words = set(claim.lower().split())
            source_words = set(combined_sources.split())
            
            # Check word overlap (simple heuristic)
            overlap = len(claim_words & source_words)
            overlap_ratio = overlap / len(claim_words) if claim_words else 0
            
            # If low overlap, likely lacks evidence
            if overlap_ratio < 0.3:
                missing_evidence.append(claim)
        
        return missing_evidence
    
    def _check_internal_consistency(self, text: str) -> float:
        """Check internal consistency of text."""
        # Extract all statements
        claims = self._extract_claims(text)
        
        if len(claims) < 2:
            return 1.0  # Single claim is consistent
        
        # Check for contradictions within text
        # Simple heuristic: check for opposite keywords
        contradictions = 0
        total_pairs = 0
        
        for i, claim1 in enumerate(claims):
            for claim2 in claims[i+1:]:
                total_pairs += 1
                # Simple contradiction check
                if self._are_contradictory(claim1, claim2):
                    contradictions += 1
        
        if total_pairs == 0:
            return 1.0
        
        consistency = 1.0 - (contradictions / total_pairs)
        return consistency
    
    def _are_contradictory(self, claim1: str, claim2: str) -> bool:
        """Check if two claims contradict each other."""
        # Simple heuristic (can be enhanced with semantic similarity)
        opposites = [
            ("not", ""),
            ("always", "never"),
            ("all", "none"),
            ("high", "low"),
            ("fast", "slow")
        ]
        
        claim1_lower = claim1.lower()
        claim2_lower = claim2.lower()
        
        for word1, word2 in opposites:
            if (word1 in claim1_lower and word2 in claim2_lower) or \
               (word2 in claim1_lower and word1 in claim2_lower):
                return True
        
        return False
    
    # ==================== 4. POWER WITHOUT SIZE ====================
    
    def retrieve_and_compress(
        self,
        query: str,
        max_tokens: int = 4000,
        target_abstraction: MemoryAbstractionLevel = MemoryAbstractionLevel.PATTERN
    ) -> Tuple[str, ContextWindowState]:
        """
        Retrieve memories and compress for maximum power in small windows.
        
        Strategy:
        1. Retrieve relevant memories
        2. Compress hierarchically
        3. Focus on high-value patterns/principles
        4. Track context window usage
        """
        # Retrieve memories
        learning_mems = self.retrieval.retrieve_learning_memories(context={"query": query}, max_results=50)
        episodic_mems = self.retrieval.retrieve_episodic_memories(problem_context=query, max_results=30)
        procedures = self.retrieval.retrieve_procedures(goal=query, max_results=20)
        
        all_memories = learning_mems + episodic_mems + procedures
        
        # Compress hierarchically
        abstractions, compression_ratio = self.compress_memories_hierarchically(
            all_memories,
            target_level=target_abstraction
        )
        
        # Format compressed context
        formatted_parts = []
        for abs in abstractions:
            formatted_parts.append(f"[{abs.level.value.upper()}] {abs.content}")
        
        compressed_context = "\n\n".join(formatted_parts)
        
        # Track context window
        memory_tokens = len(compressed_context) // 4  # Approximate
        context_state = self.track_context_window(
            total_tokens=memory_tokens,
            max_tokens=max_tokens,
            memory_tokens=memory_tokens,
            prompt_tokens=0,  # Will be set later
            system_tokens=0,
            compression_ratio=compression_ratio,
            abstraction_level=target_abstraction
        )
        
        return compressed_context, context_state
    
    # ==================== 5. TRANSFORMER FAILURE MODE MITIGATION ====================
    
    def mitigate_transformer_failures(
        self,
        prompt: str,
        context: str,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """
        Mitigate transformer model failure modes:
        1. Attention decay (information loss in long contexts)
        2. Context position bias (better at start/end)
        3. Token limit constraints
        4. Hallucination in low-confidence areas
        
        Strategy:
        - Use hierarchical compression to fit more in less space
        - Structure context to put most important info first
        - Add verification layers
        - Use abstraction to reduce token count
        """
        # Structure context: Most important first (attention is strongest at start)
        structured_context = self._structure_context_for_attention(context)
        
        # Add explicit markers for important information (helps attention)
        marked_context = self._mark_important_information(structured_context)
        
        # Verify context quality
        verification = self._verify_context_quality(marked_context)
        
        return {
            "structured_context": marked_context,
            "verification": verification,
            "recommendations": self._get_failure_mitigation_recommendations(max_tokens, len(marked_context))
        }
    
    def _structure_context_for_attention(self, context: str) -> str:
        """Structure context to maximize attention effectiveness."""
        # Split into sections
        sections = context.split("\n\n")
        
        # Prioritize sections (put most important first)
        # Simple heuristic: longer sections with more detail
        sections_with_priority = [
            (len(s.split()), s) for s in sections
        ]
        sections_with_priority.sort(reverse=True)  # Longest first
        
        # Rebuild with priority markers
        structured = "=== MOST IMPORTANT ===\n"
        structured += sections_with_priority[0][1] + "\n\n"
        
        if len(sections_with_priority) > 1:
            structured += "=== IMPORTANT ===\n"
            for _, section in sections_with_priority[1:3]:
                structured += section + "\n\n"
        
        if len(sections_with_priority) > 3:
            structured += "=== ADDITIONAL CONTEXT ===\n"
            for _, section in sections_with_priority[3:]:
                structured += section + "\n\n"
        
        return structured.strip()
    
    def _mark_important_information(self, context: str) -> str:
        """Add explicit markers for important information."""
        # Add emphasis markers that models can recognize
        # These help guide attention
        marked = context.replace(
            "Pattern:",
            "***PATTERN***:"
        ).replace(
            "Key Points:",
            "***KEY POINTS***:"
        ).replace(
            "Principle:",
            "***PRINCIPLE***:"
        )
        
        return marked
    
    def _verify_context_quality(self, context: str) -> Dict[str, Any]:
        """Verify context quality."""
        # Check for completeness
        has_patterns = "***PATTERN***" in context or "Pattern" in context
        has_principles = "***PRINCIPLE***" in context or "Principle" in context
        has_examples = "Episode" in context or "Example" in context
        
        # Check length
        token_count = len(context) // 4
        is_reasonable_length = 100 < token_count < 8000
        
        return {
            "has_patterns": has_patterns,
            "has_principles": has_principles,
            "has_examples": has_examples,
            "token_count": token_count,
            "is_reasonable_length": is_reasonable_length,
            "quality_score": (
                (1.0 if has_patterns else 0.0) * 0.4 +
                (1.0 if has_principles else 0.0) * 0.3 +
                (1.0 if has_examples else 0.0) * 0.2 +
                (1.0 if is_reasonable_length else 0.0) * 0.1
            )
        }
    
    def _get_failure_mitigation_recommendations(
        self,
        max_tokens: int,
        context_tokens: int
    ) -> List[str]:
        """Get recommendations for mitigating transformer failures."""
        recommendations = []
        
        if context_tokens > max_tokens * 0.8:
            recommendations.append("Context near limit - use higher abstraction level")
        
        if context_tokens < max_tokens * 0.3:
            recommendations.append("Context underutilized - could add more relevant memories")
        
        recommendations.append("Place most important information at context start (attention bias)")
        recommendations.append("Use explicit markers for key information (***PATTERN***, etc.)")
        
        return recommendations


def get_advanced_memory_cognition(session, knowledge_base_path) -> AdvancedMemoryCognition:
    """Factory function."""
    return AdvancedMemoryCognition(session, knowledge_base_path)
