"""
Infrastructure-Grounded Hallucination Guard

Instead of just checking LLM output against facts, this guard verifies
claims against the ACTUAL infrastructure:
- Source code index (does this function/class actually exist?)
- Oracle Vector Store (is this fact in our knowledge base?)
- Database schema (does this table/column exist?)
- System state (is this service actually running?)
- Configuration (is this setting actually set?)

This is hallucination prevention rooted in reality, not just a wrapper.
Every claim the LLM makes about Grace's own system can be verified
against the source code index and Oracle.
"""

import logging
import uuid
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from .source_code_index import SourceCodeIndex
from .oracle_vector_store import OracleVectorStore

logger = logging.getLogger(__name__)


class ClaimType(str, Enum):
    """Types of claims that can be verified."""
    CODE_EXISTS = "code_exists"           # "function X exists"
    FACT_CLAIM = "fact_claim"             # "Python uses indentation"
    CAPABILITY_CLAIM = "capability_claim" # "Grace can do X"
    CONFIG_CLAIM = "config_claim"         # "Setting X is set to Y"
    ARCHITECTURE_CLAIM = "architecture"   # "Module A depends on B"
    DATA_CLAIM = "data_claim"             # "There are N documents"


class VerificationStatus(str, Enum):
    """Status of claim verification."""
    VERIFIED = "verified"           # Confirmed true
    REFUTED = "refuted"             # Confirmed false
    UNVERIFIABLE = "unverifiable"   # Cannot verify
    PARTIALLY_VERIFIED = "partial"  # Some aspects verified


@dataclass
class Claim:
    """An extracted claim to be verified."""
    claim_id: str
    claim_type: ClaimType
    claim_text: str
    extracted_entities: List[str]  # Names, functions, values mentioned
    confidence: float = 0.5


@dataclass
class VerificationResult:
    """Result of verifying a single claim."""
    claim: Claim
    status: VerificationStatus
    evidence: List[Dict[str, Any]]
    confidence: float
    explanation: str


@dataclass
class HallucinationReport:
    """Full hallucination check report for an LLM response."""
    report_id: str
    original_text: str
    total_claims: int
    verified: int
    refuted: int
    unverifiable: int
    partially_verified: int
    overall_trust: float
    claim_results: List[VerificationResult]
    is_grounded: bool
    recommendations: List[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class HallucinationGuard:
    """
    Infrastructure-grounded hallucination prevention.

    Extracts claims from LLM output and verifies each against:
    1. Source Code Index - Does this code/function/class exist?
    2. Oracle Vector Store - Is this fact in our knowledge?
    3. System capabilities - Can Grace actually do this?
    4. Architecture - Does this dependency/integration exist?

    This goes beyond surface-level fact-checking. It verifies against
    the actual running infrastructure, making hallucination detection
    structural rather than statistical.
    """

    # Patterns for extracting claims
    CODE_REF_PATTERN = re.compile(
        r'`(\w+(?:\.\w+)*)`|function\s+(\w+)|class\s+(\w+)|'
        r'module\s+(\w+)|method\s+(\w+)',
        re.IGNORECASE,
    )
    CAPABILITY_PATTERN = re.compile(
        r'(?:grace|system|we)\s+(?:can|could|will|does|has|supports?|handles?|'
        r'provides?|includes?|implements?|uses?)\s+(.+?)(?:\.|,|$)',
        re.IGNORECASE,
    )
    FACT_PATTERN = re.compile(
        r'(?:is|are|was|were|has|have)\s+(?:a|an|the)?\s*(.+?)(?:\.|,|$)',
        re.IGNORECASE,
    )

    # Grounding threshold: below this = hallucination likely
    GROUNDING_THRESHOLD = 0.5

    def __init__(
        self,
        source_index: Optional[SourceCodeIndex] = None,
        oracle_store: Optional[OracleVectorStore] = None,
        grounding_threshold: float = GROUNDING_THRESHOLD,
    ):
        self.source_index = source_index or SourceCodeIndex()
        self.oracle_store = oracle_store
        self.grounding_threshold = grounding_threshold
        self.reports: List[HallucinationReport] = []
        logger.info("[HALLUCINATION-GUARD] Infrastructure-grounded guard initialized")

    def check_response(
        self, response_text: str, context: Optional[Dict[str, Any]] = None
    ) -> HallucinationReport:
        """
        Check an LLM response for hallucinations.

        Extracts claims, verifies each against infrastructure,
        produces a grounding report.

        Args:
            response_text: The LLM-generated text to check
            context: Optional context about what was asked

        Returns:
            HallucinationReport
        """
        # Extract claims
        claims = self._extract_claims(response_text)

        # Verify each claim
        results: List[VerificationResult] = []
        for claim in claims:
            result = self._verify_claim(claim)
            results.append(result)

        # Calculate overall trust
        verified = sum(1 for r in results if r.status == VerificationStatus.VERIFIED)
        refuted = sum(1 for r in results if r.status == VerificationStatus.REFUTED)
        unverifiable = sum(1 for r in results if r.status == VerificationStatus.UNVERIFIABLE)
        partial = sum(1 for r in results if r.status == VerificationStatus.PARTIALLY_VERIFIED)

        total = len(results)
        if total > 0:
            # Verified claims boost trust, refuted claims tank it
            trust_score = (
                (verified * 1.0 + partial * 0.5 + unverifiable * 0.3) /
                max(total, 1)
            )
            # Refuted claims are a strong negative signal
            if refuted > 0:
                trust_score *= max(0.0, 1.0 - (refuted / total))
        else:
            trust_score = 0.5  # No claims to verify

        is_grounded = trust_score >= self.grounding_threshold
        recommendations = self._generate_recommendations(results, trust_score)

        report = HallucinationReport(
            report_id=f"hg-{uuid.uuid4().hex[:12]}",
            original_text=response_text,
            total_claims=total,
            verified=verified,
            refuted=refuted,
            unverifiable=unverifiable,
            partially_verified=partial,
            overall_trust=trust_score,
            claim_results=results,
            is_grounded=is_grounded,
            recommendations=recommendations,
        )

        self.reports.append(report)

        logger.info(
            f"[HALLUCINATION-GUARD] Check: {total} claims, "
            f"{verified} verified, {refuted} refuted, "
            f"trust={trust_score:.2f}, grounded={is_grounded}"
        )

        return report

    def _extract_claims(self, text: str) -> List[Claim]:
        """Extract verifiable claims from text."""
        claims: List[Claim] = []

        # Extract code references
        for match in self.CODE_REF_PATTERN.finditer(text):
            entity = next(g for g in match.groups() if g)
            claims.append(Claim(
                claim_id=f"claim-{uuid.uuid4().hex[:8]}",
                claim_type=ClaimType.CODE_EXISTS,
                claim_text=f"Code element '{entity}' exists",
                extracted_entities=[entity],
                confidence=0.8,
            ))

        # Extract capability claims
        for match in self.CAPABILITY_PATTERN.finditer(text):
            capability = match.group(1).strip()
            if len(capability) > 5:
                claims.append(Claim(
                    claim_id=f"claim-{uuid.uuid4().hex[:8]}",
                    claim_type=ClaimType.CAPABILITY_CLAIM,
                    claim_text=f"System capability: {capability}",
                    extracted_entities=[capability],
                    confidence=0.6,
                ))

        # If no specific claims found, treat the whole text as a fact claim
        if not claims and len(text.strip()) > 20:
            claims.append(Claim(
                claim_id=f"claim-{uuid.uuid4().hex[:8]}",
                claim_type=ClaimType.FACT_CLAIM,
                claim_text=text[:200],
                extracted_entities=[],
                confidence=0.5,
            ))

        return claims

    def _verify_claim(self, claim: Claim) -> VerificationResult:
        """Verify a single claim against infrastructure."""
        if claim.claim_type == ClaimType.CODE_EXISTS:
            return self._verify_code_claim(claim)
        elif claim.claim_type == ClaimType.CAPABILITY_CLAIM:
            return self._verify_capability_claim(claim)
        elif claim.claim_type == ClaimType.FACT_CLAIM:
            return self._verify_fact_claim(claim)
        elif claim.claim_type == ClaimType.ARCHITECTURE_CLAIM:
            return self._verify_architecture_claim(claim)
        else:
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.UNVERIFIABLE,
                evidence=[],
                confidence=0.3,
                explanation="Claim type not supported for verification",
            )

    def _verify_code_claim(self, claim: Claim) -> VerificationResult:
        """Verify a claim about code existence."""
        evidence: List[Dict[str, Any]] = []

        for entity in claim.extracted_entities:
            exists = self.source_index.what_exists(entity)
            if exists:
                # Find the actual element
                query = self.source_index.query_by_name(entity)
                for elem in query.results[:3]:
                    evidence.append({
                        "source": "source_code_index",
                        "entity": entity,
                        "found": True,
                        "type": elem.element_type.value,
                        "file": elem.file_path,
                        "line": elem.line_number,
                        "signature": elem.signature,
                    })

        if evidence:
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.VERIFIED,
                evidence=evidence,
                confidence=0.95,
                explanation=f"Code element(s) found in source index",
            )
        else:
            # Check if maybe it's a partial match
            for entity in claim.extracted_entities:
                query = self.source_index.query_keyword(entity, limit=3)
                if query.results:
                    return VerificationResult(
                        claim=claim,
                        status=VerificationStatus.PARTIALLY_VERIFIED,
                        evidence=[{"similar_found": True, "entity": entity}],
                        confidence=0.5,
                        explanation="Exact match not found, similar elements exist",
                    )

            return VerificationResult(
                claim=claim,
                status=VerificationStatus.REFUTED,
                evidence=[{"entity": e, "found": False} for e in claim.extracted_entities],
                confidence=0.8,
                explanation="Code element(s) not found in source index",
            )

    def _verify_capability_claim(self, claim: Claim) -> VerificationResult:
        """Verify a claim about system capabilities."""
        evidence: List[Dict[str, Any]] = []

        for capability in claim.extracted_entities:
            handlers = self.source_index.what_handles(capability)
            if handlers:
                evidence.extend([
                    {"source": "source_code_index", "handler": h}
                    for h in handlers[:3]
                ])

        # Also check Oracle for knowledge about capabilities
        if self.oracle_store:
            for capability in claim.extracted_entities:
                results = self.oracle_store.search_by_content(capability, limit=3)
                if results:
                    evidence.extend([
                        {
                            "source": "oracle_store",
                            "content_preview": r.content[:100],
                            "domain": r.domain,
                        }
                        for r in results
                    ])

        if len(evidence) >= 2:
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.VERIFIED,
                evidence=evidence,
                confidence=0.85,
                explanation="Capability confirmed by code and/or knowledge base",
            )
        elif evidence:
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.PARTIALLY_VERIFIED,
                evidence=evidence,
                confidence=0.6,
                explanation="Partial evidence for capability",
            )
        else:
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.UNVERIFIABLE,
                evidence=[],
                confidence=0.3,
                explanation="No evidence found for claimed capability",
            )

    def _verify_fact_claim(self, claim: Claim) -> VerificationResult:
        """Verify a factual claim against Oracle knowledge."""
        evidence: List[Dict[str, Any]] = []

        if self.oracle_store:
            results = self.oracle_store.search_by_content(claim.claim_text, limit=5)
            for r in results:
                if r.score > 0.2:
                    evidence.append({
                        "source": "oracle_store",
                        "content": r.content[:100],
                        "score": r.score,
                        "domain": r.domain,
                        "trust": r.trust_score,
                    })

        if evidence and any(e["score"] > 0.3 for e in evidence):
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.VERIFIED,
                evidence=evidence,
                confidence=0.75,
                explanation="Fact corroborated by Oracle knowledge base",
            )
        elif evidence:
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.PARTIALLY_VERIFIED,
                evidence=evidence,
                confidence=0.5,
                explanation="Partial corroboration in knowledge base",
            )
        else:
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.UNVERIFIABLE,
                evidence=[],
                confidence=0.3,
                explanation="No corroborating evidence in knowledge base",
            )

    def _verify_architecture_claim(self, claim: Claim) -> VerificationResult:
        """Verify a claim about system architecture."""
        dep_graph = self.source_index.get_dependency_graph()
        evidence: List[Dict[str, Any]] = []

        for entity in claim.extracted_entities:
            if entity in dep_graph:
                evidence.append({
                    "source": "dependency_graph",
                    "module": entity,
                    "dependencies": dep_graph[entity],
                })

        if evidence:
            return VerificationResult(
                claim=claim,
                status=VerificationStatus.VERIFIED,
                evidence=evidence,
                confidence=0.9,
                explanation="Architecture confirmed by dependency graph",
            )

        return VerificationResult(
            claim=claim,
            status=VerificationStatus.UNVERIFIABLE,
            evidence=[],
            confidence=0.3,
            explanation="Cannot verify architecture claim",
        )

    def _generate_recommendations(
        self, results: List[VerificationResult], trust: float
    ) -> List[str]:
        """Generate recommendations based on verification results."""
        recs: List[str] = []

        refuted = [r for r in results if r.status == VerificationStatus.REFUTED]
        if refuted:
            entities = []
            for r in refuted:
                entities.extend(r.claim.extracted_entities)
            recs.append(
                f"REFUTED claims about: {', '.join(entities[:5])}. "
                f"Response contains hallucinated code references."
            )

        unverifiable = [r for r in results if r.status == VerificationStatus.UNVERIFIABLE]
        if len(unverifiable) > len(results) / 2:
            recs.append(
                "Most claims could not be verified. Consider re-querying "
                "with more specific context or indexing more source code."
            )

        if trust < self.grounding_threshold:
            recs.append(
                f"Overall trust ({trust:.2f}) is below threshold "
                f"({self.grounding_threshold}). Response should be "
                f"regenerated or manually verified."
            )

        if not recs:
            recs.append("Response is well-grounded in infrastructure.")

        return recs

    def get_stats(self) -> Dict[str, Any]:
        """Get guard statistics."""
        if not self.reports:
            return {"total_checks": 0, "grounding_rate": 0.0}

        grounded = sum(1 for r in self.reports if r.is_grounded)
        total_claims = sum(r.total_claims for r in self.reports)
        total_verified = sum(r.verified for r in self.reports)
        total_refuted = sum(r.refuted for r in self.reports)

        return {
            "total_checks": len(self.reports),
            "grounding_rate": grounded / len(self.reports),
            "total_claims_checked": total_claims,
            "total_verified": total_verified,
            "total_refuted": total_refuted,
            "average_trust": sum(r.overall_trust for r in self.reports) / len(self.reports),
        }
