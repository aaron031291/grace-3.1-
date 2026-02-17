"""
LLM Enrichment Engine

The LLM in this system is NOT the brain -- it's the librarian.
It reads what's in the Oracle, generates additional context/terminology,
and writes enriched data back.

Multiple enrichment modes:
1. Terminology extraction - Pull all terminology from domain
2. Context expansion - Add context to existing knowledge
3. Gap filling - Fill in missing connections
4. Summary generation - Create summaries of ingested content
5. Question generation - Generate practice questions
6. Cross-reference - Link related content across domains
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from .oracle_vector_store import OracleVectorStore, OracleRecord

logger = logging.getLogger(__name__)


class EnrichmentMode(str, Enum):
    """Modes of LLM enrichment."""
    TERMINOLOGY = "terminology"
    CONTEXT_EXPANSION = "context_expansion"
    GAP_FILLING = "gap_filling"
    SUMMARY = "summary"
    QUESTION_GENERATION = "question_generation"
    CROSS_REFERENCE = "cross_reference"


@dataclass
class EnrichmentResult:
    """Result of an LLM enrichment operation."""
    enrichment_id: str
    mode: EnrichmentMode
    source_record_ids: List[str]
    generated_content: str
    domain: Optional[str] = None
    records_created: int = 0
    new_record_ids: List[str] = field(default_factory=list)
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class LLMEnrichmentEngine:
    """
    Uses LLM as a librarian to enrich knowledge in the Oracle.

    The LLM reads existing data, generates additional knowledge,
    and writes it back. This gives Grace multiple enrichment paths:
    1. User search (whitelist) -> direct ingestion
    2. Neighbor search (KNN) -> background discovery
    3. LLM enrichment -> adding context and terminology

    In production, this calls the actual LLM orchestrator. The
    placeholders here show the data flow and return structure.
    """

    def __init__(
        self,
        oracle_store: Optional[OracleVectorStore] = None,
    ):
        self.oracle_store = oracle_store
        self.enrichment_log: List[EnrichmentResult] = []
        self._llm_handler: Optional[Any] = None
        logger.info("[LLM-ENRICH] Enrichment Engine initialized")

    def set_llm_handler(self, handler: Any) -> None:
        """Set the LLM handler for actual generation."""
        self._llm_handler = handler

    def enrich_domain(
        self, domain: str, mode: EnrichmentMode = EnrichmentMode.TERMINOLOGY
    ) -> EnrichmentResult:
        """
        Enrich a domain with LLM-generated content.

        Args:
            domain: Domain to enrich
            mode: Enrichment mode

        Returns:
            EnrichmentResult
        """
        source_records: List[OracleRecord] = []
        if self.oracle_store:
            source_records = self.oracle_store.search_by_domain(domain, limit=10)

        source_content = "\n".join(r.content for r in source_records)
        source_ids = [r.record_id for r in source_records]

        generated = self._generate_enrichment(
            domain, source_content, mode
        )

        new_record_ids: List[str] = []
        if generated and self.oracle_store:
            records = self.oracle_store.ingest(
                content=generated,
                domain=domain,
                trust_score=0.85,
                tags=["llm_enrichment", mode.value],
                metadata={
                    "enrichment_mode": mode.value,
                    "source_records": source_ids,
                },
            )
            new_record_ids = [r.record_id for r in records]

        result = EnrichmentResult(
            enrichment_id=f"enrich-{uuid.uuid4().hex[:12]}",
            mode=mode,
            source_record_ids=source_ids,
            generated_content=generated,
            domain=domain,
            records_created=len(new_record_ids),
            new_record_ids=new_record_ids,
            metadata={"source_count": len(source_records)},
        )

        self.enrichment_log.append(result)

        logger.info(
            f"[LLM-ENRICH] {mode.value} for '{domain}': "
            f"generated {len(generated)} chars, "
            f"created {len(new_record_ids)} records"
        )

        return result

    def enrich_record(
        self,
        record_id: str,
        mode: EnrichmentMode = EnrichmentMode.CONTEXT_EXPANSION,
    ) -> EnrichmentResult:
        """
        Enrich a specific record.

        Args:
            record_id: Record to enrich
            mode: Enrichment mode

        Returns:
            EnrichmentResult
        """
        record = None
        if self.oracle_store:
            record = self.oracle_store.get_record(record_id)

        if not record:
            return EnrichmentResult(
                enrichment_id=f"enrich-{uuid.uuid4().hex[:12]}",
                mode=mode,
                source_record_ids=[record_id],
                generated_content="",
                metadata={"error": "Record not found"},
            )

        generated = self._generate_enrichment(
            record.domain or "general", record.content, mode
        )

        new_record_ids: List[str] = []
        if generated and self.oracle_store:
            records = self.oracle_store.ingest(
                content=generated,
                domain=record.domain,
                source_item_id=record.source_item_id,
                trust_score=0.85,
                tags=["llm_enrichment", mode.value, "record_enrichment"],
                metadata={
                    "enrichment_mode": mode.value,
                    "source_record": record_id,
                },
            )
            new_record_ids = [r.record_id for r in records]

        result = EnrichmentResult(
            enrichment_id=f"enrich-{uuid.uuid4().hex[:12]}",
            mode=mode,
            source_record_ids=[record_id],
            generated_content=generated,
            domain=record.domain,
            records_created=len(new_record_ids),
            new_record_ids=new_record_ids,
        )

        self.enrichment_log.append(result)
        return result

    def generate_practice_questions(
        self, domain: str, count: int = 5
    ) -> EnrichmentResult:
        """Generate practice questions for sandbox training."""
        return self.enrich_domain(domain, EnrichmentMode.QUESTION_GENERATION)

    def _generate_enrichment(
        self,
        domain: str,
        source_content: str,
        mode: EnrichmentMode,
    ) -> str:
        """
        Generate enrichment content using LLM.

        In production, this calls the LLM orchestrator.
        Here we provide the prompt structure and placeholder output.
        """
        if self._llm_handler:
            try:
                prompt = self._build_prompt(domain, source_content, mode)
                return self._llm_handler(prompt)
            except Exception as e:
                logger.warning(f"[LLM-ENRICH] LLM handler failed: {e}")

        # Placeholder enrichment (shows what the LLM would generate)
        return self._placeholder_enrichment(domain, source_content, mode)

    def _build_prompt(
        self, domain: str, source_content: str, mode: EnrichmentMode
    ) -> str:
        """Build LLM prompt for enrichment."""
        prompts = {
            EnrichmentMode.TERMINOLOGY: (
                f"Extract key terminology and definitions from the following "
                f"{domain} content. List each term with a clear definition:\n\n"
                f"{source_content[:2000]}"
            ),
            EnrichmentMode.CONTEXT_EXPANSION: (
                f"Expand the following {domain} content with additional context, "
                f"related concepts, and practical applications:\n\n"
                f"{source_content[:2000]}"
            ),
            EnrichmentMode.GAP_FILLING: (
                f"Identify knowledge gaps in the following {domain} content "
                f"and fill them with important missing information:\n\n"
                f"{source_content[:2000]}"
            ),
            EnrichmentMode.SUMMARY: (
                f"Create a comprehensive summary of the following {domain} "
                f"content, highlighting key concepts and takeaways:\n\n"
                f"{source_content[:2000]}"
            ),
            EnrichmentMode.QUESTION_GENERATION: (
                f"Generate 5 practice questions based on the following "
                f"{domain} content, ranging from basic to advanced:\n\n"
                f"{source_content[:2000]}"
            ),
            EnrichmentMode.CROSS_REFERENCE: (
                f"Identify connections between the following {domain} content "
                f"and other domains. What concepts transfer across fields?\n\n"
                f"{source_content[:2000]}"
            ),
        }
        return prompts.get(mode, f"Analyze the following {domain} content:\n\n{source_content[:2000]}")

    def _placeholder_enrichment(
        self, domain: str, source_content: str, mode: EnrichmentMode
    ) -> str:
        """Placeholder enrichment when LLM is not available."""
        word_count = len(source_content.split())
        content_preview = source_content[:100].replace("\n", " ")

        enrichments = {
            EnrichmentMode.TERMINOLOGY: (
                f"Key {domain} terminology extracted from {word_count} words of source material. "
                f"Domain concepts and definitions pending LLM generation."
            ),
            EnrichmentMode.CONTEXT_EXPANSION: (
                f"Context expansion for {domain}: {content_preview}... "
                f"Additional context and related concepts pending LLM generation."
            ),
            EnrichmentMode.GAP_FILLING: (
                f"Knowledge gaps identified in {domain} content ({word_count} words). "
                f"Gap analysis pending LLM generation."
            ),
            EnrichmentMode.SUMMARY: (
                f"Summary of {domain} content ({word_count} words): {content_preview}... "
                f"Full summary pending LLM generation."
            ),
            EnrichmentMode.QUESTION_GENERATION: (
                f"Practice questions for {domain} based on {word_count} words of content. "
                f"Questions pending LLM generation."
            ),
            EnrichmentMode.CROSS_REFERENCE: (
                f"Cross-references for {domain} content ({word_count} words). "
                f"Cross-domain connections pending LLM generation."
            ),
        }
        return enrichments.get(mode, f"Enrichment for {domain} pending LLM.")

    def get_stats(self) -> Dict[str, Any]:
        """Get enrichment statistics."""
        by_mode = {}
        for m in EnrichmentMode:
            count = sum(1 for r in self.enrichment_log if r.mode == m)
            if count > 0:
                by_mode[m.value] = count
        total_records = sum(r.records_created for r in self.enrichment_log)
        return {
            "total_enrichments": len(self.enrichment_log),
            "total_records_created": total_records,
            "by_mode": by_mode,
        }
