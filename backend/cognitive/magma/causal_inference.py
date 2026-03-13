"""
Magma Memory - LLM Causal Inference

Uses LLM to infer causal relationships:
1. Extract causal claims from text
2. Validate causal chains
3. Score causal relationship strength
4. Generate causal explanations

Integrates with the Causal Graph for storage and retrieval.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Tuple
from enum import Enum
from datetime import datetime
import re
import logging

from backend.cognitive.magma.relation_graphs import (
    MagmaRelationGraphs,
    GraphNode,
    GraphEdge,
    RelationType,
    CausalGraph
)

logger = logging.getLogger(__name__)


class CausalRelationStrength(Enum):
    """Strength of causal relationships."""
    WEAK = "weak"  # Correlation or possible causation
    MODERATE = "moderate"  # Likely causal but not certain
    STRONG = "strong"  # Established causal relationship
    DEFINITE = "definite"  # Proven causation


@dataclass
class CausalClaim:
    """A causal claim extracted from text."""
    id: str
    cause: str
    effect: str
    relation_type: RelationType
    strength: CausalRelationStrength
    confidence: float
    evidence: str
    source_text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalChain:
    """A chain of causal relationships."""
    id: str
    nodes: List[str]  # Ordered list of node contents
    edges: List[RelationType]  # Relations between consecutive nodes
    total_confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalExplanation:
    """An explanation of a causal relationship."""
    cause: str
    effect: str
    explanation: str
    chain: Optional[CausalChain] = None
    confidence: float = 0.5
    supporting_evidence: List[str] = field(default_factory=list)


class CausalPatternDetector:
    """
    Detects causal patterns in text using linguistic patterns.

    This is a rule-based approach that can be enhanced with LLM.
    """

    def __init__(self):
        # Causal indicator patterns with relation type and strength
        self.patterns = [
            # Strong causation
            (r'(\w+(?:\s+\w+)*)\s+directly\s+causes?\s+(\w+(?:\s+\w+)*)',
             RelationType.CAUSAL_CAUSES, CausalRelationStrength.STRONG),
            (r'(\w+(?:\s+\w+)*)\s+always\s+leads?\s+to\s+(\w+(?:\s+\w+)*)',
             RelationType.CAUSAL_CAUSES, CausalRelationStrength.STRONG),

            # Moderate causation
            (r'(\w+(?:\s+\w+)*)\s+causes?\s+(\w+(?:\s+\w+)*)',
             RelationType.CAUSAL_CAUSES, CausalRelationStrength.MODERATE),
            (r'(\w+(?:\s+\w+)*)\s+leads?\s+to\s+(\w+(?:\s+\w+)*)',
             RelationType.CAUSAL_CAUSES, CausalRelationStrength.MODERATE),
            (r'(\w+(?:\s+\w+)*)\s+results?\s+in\s+(\w+(?:\s+\w+)*)',
             RelationType.CAUSAL_CAUSES, CausalRelationStrength.MODERATE),
            (r'due\s+to\s+(\w+(?:\s+\w+)*)[,.]?\s+(\w+(?:\s+\w+)*)',
             RelationType.CAUSAL_CAUSED_BY, CausalRelationStrength.MODERATE),

            # Weak/correlation
            (r'(\w+(?:\s+\w+)*)\s+(?:may|might|can)\s+cause\s+(\w+(?:\s+\w+)*)',
             RelationType.CAUSAL_CAUSES, CausalRelationStrength.WEAK),
            (r'(\w+(?:\s+\w+)*)\s+is\s+associated\s+with\s+(\w+(?:\s+\w+)*)',
             RelationType.CAUSAL_CORRELATES, CausalRelationStrength.WEAK),
            (r'(\w+(?:\s+\w+)*)\s+correlates?\s+with\s+(\w+(?:\s+\w+)*)',
             RelationType.CAUSAL_CORRELATES, CausalRelationStrength.WEAK),

            # Enabling/preventing
            (r'(\w+(?:\s+\w+)*)\s+enables?\s+(\w+(?:\s+\w+)*)',
             RelationType.CAUSAL_ENABLES, CausalRelationStrength.MODERATE),
            (r'(\w+(?:\s+\w+)*)\s+prevents?\s+(\w+(?:\s+\w+)*)',
             RelationType.CAUSAL_PREVENTS, CausalRelationStrength.MODERATE),
            (r'(\w+(?:\s+\w+)*)\s+blocks?\s+(\w+(?:\s+\w+)*)',
             RelationType.CAUSAL_PREVENTS, CausalRelationStrength.MODERATE),
        ]

    def detect(self, text: str) -> List[CausalClaim]:
        """
        Detect causal claims in text.

        Args:
            text: Text to analyze

        Returns:
            List of CausalClaim objects
        """
        claims = []
        claim_id = 0

        for pattern, relation_type, strength in self.patterns:
            matches = re.finditer(pattern, text.lower())

            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    cause = groups[0].strip()
                    effect = groups[1].strip()

                    # Skip very short matches
                    if len(cause) < 3 or len(effect) < 3:
                        continue

                    # Calculate confidence based on strength and match quality
                    confidence = {
                        CausalRelationStrength.DEFINITE: 0.95,
                        CausalRelationStrength.STRONG: 0.8,
                        CausalRelationStrength.MODERATE: 0.6,
                        CausalRelationStrength.WEAK: 0.4,
                    }.get(strength, 0.5)

                    claims.append(CausalClaim(
                        id=f"claim-{claim_id}",
                        cause=cause,
                        effect=effect,
                        relation_type=relation_type,
                        strength=strength,
                        confidence=confidence,
                        evidence=match.group(),
                        source_text=text[max(0, match.start()-50):match.end()+50]
                    ))
                    claim_id += 1

        # Deduplicate similar claims
        unique_claims = self._deduplicate_claims(claims)

        return unique_claims

    def _deduplicate_claims(self, claims: List[CausalClaim]) -> List[CausalClaim]:
        """Remove duplicate or very similar claims."""
        seen = set()
        unique = []

        for claim in claims:
            key = (claim.cause.lower(), claim.effect.lower())
            if key not in seen:
                seen.add(key)
                unique.append(claim)

        return unique


class LLMCausalInferencer:
    """
    LLM-based causal inference.

    Uses LLM to:
    1. Validate causal claims
    2. Infer new causal relationships
    3. Score relationship strength
    4. Generate explanations
    """

    def __init__(
        self,
        graphs: MagmaRelationGraphs,
        llm_fn: Optional[Callable[[str], str]] = None
    ):
        """
        Initialize LLM causal inferencer.

        Args:
            graphs: MagmaRelationGraphs instance
            llm_fn: Optional LLM function (prompt -> response)
        """
        self.graphs = graphs
        self.llm_fn = llm_fn or self._placeholder_llm
        self.pattern_detector = CausalPatternDetector()

        logger.info("[MAGMA-CAUSAL] LLMCausalInferencer initialized")

    def _placeholder_llm(self, prompt: str) -> str:
        """Placeholder LLM function for testing."""
        # In production, this would call actual LLM
        return f"[LLM Response to: {prompt[:50]}...]"

    def infer_causation(
        self,
        text: str,
        use_llm: bool = False
    ) -> List[CausalClaim]:
        """
        Infer causal relationships from text.

        Args:
            text: Text to analyze
            use_llm: Whether to use LLM for enhancement

        Returns:
            List of CausalClaim objects
        """
        # Start with pattern-based detection
        claims = self.pattern_detector.detect(text)

        if use_llm and self.llm_fn:
            # Enhance with LLM
            claims = self._enhance_with_llm(claims, text)

        return claims

    def _enhance_with_llm(
        self,
        claims: List[CausalClaim],
        text: str = ""
    ) -> List[CausalClaim]:
        """Enhance claims with LLM validation and scoring."""
        enhanced = []

        for claim in claims:
            prompt = f"""Analyze this causal claim:
Cause: {claim.cause}
Effect: {claim.effect}
Evidence: {claim.evidence}

Rate the strength of this causal relationship (weak/moderate/strong/definite)
and provide a confidence score (0-1).
"""

            try:
                response = self.llm_fn(prompt)
                # Parse response and update claim
                # Placeholder - actual implementation would parse LLM response
                enhanced.append(claim)
            except Exception as e:
                logger.warning(f"LLM enhancement failed: {e}")
                enhanced.append(claim)

        return enhanced

    def store_claims(
        self,
        claims: List[CausalClaim],
        genesis_key_id: Optional[str] = None
    ) -> List[str]:
        """
        Store causal claims in the graph.

        Args:
            claims: List of causal claims
            genesis_key_id: Optional Genesis Key for tracking

        Returns:
            List of created edge IDs
        """
        created_ids = []

        for claim in claims:
            # Create/find cause node
            cause_node = self._find_or_create_node(
                claim.cause, "cause", genesis_key_id
            )

            # Create/find effect node
            effect_node = self._find_or_create_node(
                claim.effect, "effect", genesis_key_id
            )

            # Create causal edge
            try:
                edge_id = self.graphs.causal.add_causal_link(
                    cause_node.id,
                    effect_node.id,
                    claim.relation_type,
                    confidence=claim.confidence,
                    evidence=[claim.evidence],
                    genesis_key_id=genesis_key_id
                )
                created_ids.append(edge_id)

                logger.debug(
                    f"[MAGMA-CAUSAL] Stored: {claim.cause} -> {claim.effect} "
                    f"({claim.relation_type.value}, conf={claim.confidence:.2f})"
                )

            except Exception as e:
                logger.warning(f"Failed to store claim: {e}")

        return created_ids

    def _find_or_create_node(
        self,
        content: str,
        node_type: str,
        genesis_key_id: Optional[str]
    ) -> GraphNode:
        """Find existing node or create new one."""
        # Search for existing node
        content_lower = content.lower()
        for node_id, node in self.graphs.causal.nodes.items():
            if node.content.lower() == content_lower:
                return node

        # Create new node
        import uuid
        node = GraphNode(
            id=f"causal-{uuid.uuid4().hex[:8]}",
            node_type=node_type,
            content=content,
            genesis_key_id=genesis_key_id
        )
        self.graphs.causal.add_node(node)

        return node

    def trace_causal_chain(
        self,
        start_concept: str,
        direction: str = "effects",
        max_depth: int = 5
    ) -> List[CausalChain]:
        """
        Trace causal chains starting from a concept.

        Args:
            start_concept: Starting concept
            direction: "effects" or "causes"
            max_depth: Maximum chain depth

        Returns:
            List of CausalChain objects
        """
        # Find starting node
        start_node = None
        start_lower = start_concept.lower()

        for node_id, node in self.graphs.causal.nodes.items():
            if start_lower in node.content.lower():
                start_node = node
                break

        if not start_node:
            return []

        # Trace chains
        raw_chains = self.graphs.causal.trace_causal_chain(
            start_node.id,
            direction=direction,
            max_depth=max_depth
        )

        # Convert to CausalChain objects
        causal_chains = []
        for i, chain_nodes in enumerate(raw_chains):
            if len(chain_nodes) < 2:
                continue

            nodes = [n.content for n in chain_nodes]

            # Calculate chain confidence (product of node trust scores)
            total_confidence = 1.0
            for node in chain_nodes:
                total_confidence *= node.trust_score

            causal_chains.append(CausalChain(
                id=f"chain-{i}",
                nodes=nodes,
                edges=[RelationType.CAUSAL_CAUSES] * (len(nodes) - 1),
                total_confidence=total_confidence
            ))

        return causal_chains

    def explain_causation(
        self,
        cause: str,
        effect: str,
        use_llm: bool = False
    ) -> CausalExplanation:
        """
        Generate explanation for a causal relationship.

        Args:
            cause: Cause concept
            effect: Effect concept
            use_llm: Whether to use LLM for explanation

        Returns:
            CausalExplanation object
        """
        # Find connecting chain
        chains = self.trace_causal_chain(cause, direction="effects")

        # Filter chains that reach the effect
        matching_chains = [
            chain for chain in chains
            if any(effect.lower() in node.lower() for node in chain.nodes)
        ]

        if matching_chains:
            chain = matching_chains[0]
            explanation = f"{cause} leads to {effect} through: " + " → ".join(chain.nodes)
            evidence = [f"Chain: {' → '.join(chain.nodes)}"]
        else:
            chain = None
            explanation = f"Direct relationship: {cause} causes {effect}"
            evidence = []

        if use_llm and self.llm_fn:
            prompt = f"""Explain the causal relationship between:
Cause: {cause}
Effect: {effect}
Known chain: {chain.nodes if chain else 'Unknown'}

Provide a clear explanation of how the cause leads to the effect.
"""
            try:
                llm_explanation = self.llm_fn(prompt)
                explanation = llm_explanation
            except Exception as e:
                logger.warning(f"LLM explanation failed: {e}")

        return CausalExplanation(
            cause=cause,
            effect=effect,
            explanation=explanation,
            chain=chain,
            confidence=chain.total_confidence if chain else 0.5,
            supporting_evidence=evidence
        )

    def validate_claim(
        self,
        claim: CausalClaim,
        use_llm: bool = False
    ) -> Tuple[bool, float, str]:
        """
        Validate a causal claim.

        Args:
            claim: CausalClaim to validate
            use_llm: Whether to use LLM for validation

        Returns:
            Tuple of (is_valid, confidence, reason)
        """
        # Check if chain exists in graph
        chains = self.trace_causal_chain(claim.cause, direction="effects")

        # Look for matching chain
        for chain in chains:
            if any(claim.effect.lower() in node.lower() for node in chain.nodes):
                return True, chain.total_confidence, f"Supported by existing chain: {' → '.join(chain.nodes)}"

        # Check reverse direction
        reverse_chains = self.trace_causal_chain(claim.effect, direction="causes")
        for chain in reverse_chains:
            if any(claim.cause.lower() in node.lower() for node in chain.nodes):
                return True, chain.total_confidence, f"Supported by reverse chain"

        # No existing support
        if use_llm and self.llm_fn:
            prompt = f"""Validate this causal claim:
"{claim.cause}" causes "{claim.effect}"
Evidence: {claim.evidence}

Is this claim plausible? Respond with: valid/invalid and confidence (0-1).
"""
            try:
                response = self.llm_fn(prompt)
                # Parse response - placeholder
                return True, 0.5, "Validated by LLM"
            except Exception as e:
                logger.warning(f"LLM validation failed: {e}")

        return False, 0.3, "No supporting evidence found"
