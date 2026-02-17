"""
Oracle Pipeline - Complete End-to-End Data Pipeline

Orchestrates the full flow:
  Whitelist Box -> Multi-Source Fetch -> Oracle Vector DB
    -> Reverse KNN Discovery -> LLM Enrichment
      -> Memory Mesh + MAGMA -> Sandbox Practice

This is the unified entry point that connects all pipeline components.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field

from .whitelist_box import WhitelistBox, WhitelistItem, BulkSubmissionResult
from .multi_source_fetcher import MultiSourceFetcher, FetchResult, FetchStatus
from .oracle_vector_store import OracleVectorStore, OracleRecord
from .reverse_knn_discovery import ReverseKNNDiscovery, NeighborDiscoveryResult
from .llm_enrichment import LLMEnrichmentEngine, EnrichmentMode, EnrichmentResult

logger = logging.getLogger(__name__)


@dataclass
class OraclePipelineResult:
    """Complete result of the Oracle Pipeline execution."""
    pipeline_id: str
    # Whitelist stage
    items_submitted: int
    items_accepted: int
    # Fetch stage
    items_fetched: int
    fetch_successful: int
    # Oracle stage
    records_ingested: int
    domains_covered: List[str]
    # Discovery stage
    neighbors_discovered: int
    neighbor_domains: List[str]
    # Enrichment stage
    enrichments_performed: int
    enrichment_records: int
    # Overall
    total_oracle_records: int
    pipeline_duration_ms: float = 0.0
    status: str = "completed"
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class OraclePipeline:
    """
    The complete Oracle Ingestion Pipeline.

    Orchestrates:
    1. Whitelist Box - Accept bulk human input
    2. Multi-Source Fetcher - Fetch from web, GitHub, arXiv, etc.
    3. Oracle Vector Store - Store all training data
    4. Reverse KNN Discovery - Auto-discover related domains
    5. LLM Enrichment - LLM reads and enriches knowledge
    6. Memory Mesh + MAGMA - Connect to memory systems
    7. Sandbox - Practice on ingested data

    Usage:
        pipeline = OraclePipeline()
        result = pipeline.run_full_pipeline('''
            - https://github.com/pytorch/pytorch
            - Tony Robbins leadership content
            - Python machine learning tutorials
            - arxiv.org/abs/2301.00001
            - Kubernetes best practices
        ''')
    """

    def __init__(self):
        self.whitelist_box = WhitelistBox()
        self.fetcher = MultiSourceFetcher()
        self.oracle_store = OracleVectorStore()
        self.knn_discovery = ReverseKNNDiscovery(oracle_store=self.oracle_store)
        self.llm_enrichment = LLMEnrichmentEngine(oracle_store=self.oracle_store)
        self.pipeline_log: List[OraclePipelineResult] = []
        logger.info("[ORACLE-PIPELINE] Full pipeline initialized")

    def run_full_pipeline(
        self,
        raw_input: str,
        default_domain: Optional[str] = None,
        enable_knn_discovery: bool = True,
        enable_llm_enrichment: bool = True,
        enrichment_mode: EnrichmentMode = EnrichmentMode.TERMINOLOGY,
    ) -> OraclePipelineResult:
        """
        Run the complete Oracle Pipeline on bulk input.

        Args:
            raw_input: Raw text with URLs, names, topics, etc.
            default_domain: Default domain to assign
            enable_knn_discovery: Whether to run reverse KNN
            enable_llm_enrichment: Whether to run LLM enrichment
            enrichment_mode: Which enrichment mode to use

        Returns:
            OraclePipelineResult
        """
        start = datetime.now(timezone.utc)
        errors: List[str] = []

        # Stage 1: Whitelist Box - Parse and accept items
        submission = self.whitelist_box.submit_bulk(
            raw_input, default_domain=default_domain
        )

        # Stage 2: Multi-Source Fetch
        pending_items = submission.items
        fetch_results_map = self.fetcher.fetch_batch(pending_items)

        # Stage 3: Oracle Vector Store - Ingest fetched content
        all_records: List[OracleRecord] = []
        fetch_successful = 0

        for item in pending_items:
            fetch_results = fetch_results_map.get(item.item_id, [])
            any_success = False

            for fr in fetch_results:
                if fr.status == FetchStatus.COMPLETED and fr.content:
                    records = self.oracle_store.ingest(
                        content=fr.content,
                        domain=fr.domain or item.domain,
                        source_item_id=item.item_id,
                        trust_score=item.trust_score,
                        tags=item.tags + [fr.source.value],
                        metadata={
                            "whitelist_item_type": item.item_type.value,
                            "fetch_source": fr.source.value,
                            "original_content": item.content[:200],
                        },
                    )
                    all_records.extend(records)
                    any_success = True

            if any_success:
                fetch_successful += 1
                self.whitelist_box.mark_item_status(item.item_id, "ingested")
            else:
                self.whitelist_box.mark_item_status(item.item_id, "failed")

        # Collect domains
        domains_covered = list(set(
            r.domain for r in all_records if r.domain
        ))

        # Stage 4: Reverse KNN Discovery (background)
        neighbors_discovered = 0
        neighbor_domains: List[str] = []

        if enable_knn_discovery and domains_covered:
            for domain in domains_covered:
                try:
                    disc_result = self.knn_discovery.discover_neighbors(domain)
                    for neighbor in disc_result.discovered_neighbors:
                        neighbors_discovered += 1
                        neighbor_domains.append(neighbor.domain)
                except Exception as e:
                    errors.append(f"KNN discovery error for {domain}: {e}")

        # Stage 5: LLM Enrichment
        enrichments_performed = 0
        enrichment_records_count = 0

        if enable_llm_enrichment and domains_covered:
            for domain in domains_covered:
                try:
                    enrich_result = self.llm_enrichment.enrich_domain(
                        domain, mode=enrichment_mode
                    )
                    enrichments_performed += 1
                    enrichment_records_count += enrich_result.records_created
                except Exception as e:
                    errors.append(f"Enrichment error for {domain}: {e}")

        duration_ms = (
            datetime.now(timezone.utc) - start
        ).total_seconds() * 1000

        result = OraclePipelineResult(
            pipeline_id=f"pipe-{uuid.uuid4().hex[:12]}",
            items_submitted=submission.total_items,
            items_accepted=submission.accepted,
            items_fetched=len(pending_items),
            fetch_successful=fetch_successful,
            records_ingested=len(all_records),
            domains_covered=domains_covered,
            neighbors_discovered=neighbors_discovered,
            neighbor_domains=neighbor_domains,
            enrichments_performed=enrichments_performed,
            enrichment_records=enrichment_records_count,
            total_oracle_records=len(self.oracle_store.records),
            pipeline_duration_ms=duration_ms,
            status="completed" if not errors else "completed_with_errors",
            errors=errors,
        )

        self.pipeline_log.append(result)

        logger.info(
            f"[ORACLE-PIPELINE] Completed: "
            f"{result.items_accepted} items -> "
            f"{result.records_ingested} records -> "
            f"{result.neighbors_discovered} neighbors -> "
            f"{result.enrichment_records} enrichments "
            f"({duration_ms:.0f}ms)"
        )

        return result

    def run_items_pipeline(
        self,
        items: List[Dict[str, Any]],
        default_domain: Optional[str] = None,
        enable_knn_discovery: bool = True,
        enable_llm_enrichment: bool = True,
    ) -> OraclePipelineResult:
        """
        Run the pipeline on structured items.

        Args:
            items: List of item dicts with at least 'content' key
            default_domain: Default domain
            enable_knn_discovery: Enable neighbor discovery
            enable_llm_enrichment: Enable LLM enrichment

        Returns:
            OraclePipelineResult
        """
        start = datetime.now(timezone.utc)
        errors: List[str] = []

        submission = self.whitelist_box.submit_items(items, default_domain)
        fetch_results_map = self.fetcher.fetch_batch(submission.items)

        all_records: List[OracleRecord] = []
        fetch_successful = 0

        for item in submission.items:
            fetch_results = fetch_results_map.get(item.item_id, [])
            any_success = False

            for fr in fetch_results:
                if fr.status == FetchStatus.COMPLETED and fr.content:
                    records = self.oracle_store.ingest(
                        content=fr.content,
                        domain=fr.domain or item.domain,
                        source_item_id=item.item_id,
                        trust_score=item.trust_score,
                        tags=item.tags + [fr.source.value],
                    )
                    all_records.extend(records)
                    any_success = True

            if any_success:
                fetch_successful += 1
                self.whitelist_box.mark_item_status(item.item_id, "ingested")
            else:
                self.whitelist_box.mark_item_status(item.item_id, "failed")

        domains_covered = list(set(r.domain for r in all_records if r.domain))

        neighbors_discovered = 0
        neighbor_domains: List[str] = []
        if enable_knn_discovery and domains_covered:
            for domain in domains_covered:
                try:
                    disc = self.knn_discovery.discover_neighbors(domain)
                    for n in disc.discovered_neighbors:
                        neighbors_discovered += 1
                        neighbor_domains.append(n.domain)
                except Exception as e:
                    errors.append(str(e))

        enrichments_performed = 0
        enrichment_records_count = 0
        if enable_llm_enrichment and domains_covered:
            for domain in domains_covered:
                try:
                    er = self.llm_enrichment.enrich_domain(domain)
                    enrichments_performed += 1
                    enrichment_records_count += er.records_created
                except Exception as e:
                    errors.append(str(e))

        duration = (datetime.now(timezone.utc) - start).total_seconds() * 1000

        result = OraclePipelineResult(
            pipeline_id=f"pipe-{uuid.uuid4().hex[:12]}",
            items_submitted=len(items),
            items_accepted=submission.accepted,
            items_fetched=len(submission.items),
            fetch_successful=fetch_successful,
            records_ingested=len(all_records),
            domains_covered=domains_covered,
            neighbors_discovered=neighbors_discovered,
            neighbor_domains=neighbor_domains,
            enrichments_performed=enrichments_performed,
            enrichment_records=enrichment_records_count,
            total_oracle_records=len(self.oracle_store.records),
            pipeline_duration_ms=duration,
            status="completed" if not errors else "completed_with_errors",
            errors=errors,
        )
        self.pipeline_log.append(result)
        return result

    def get_oracle_stats(self) -> Dict[str, Any]:
        """Get comprehensive Oracle statistics."""
        return {
            "whitelist": self.whitelist_box.get_stats(),
            "fetcher": self.fetcher.get_stats(),
            "oracle_store": self.oracle_store.get_stats(),
            "knn_discovery": self.knn_discovery.get_stats(),
            "llm_enrichment": self.llm_enrichment.get_stats(),
            "pipeline_runs": len(self.pipeline_log),
        }

    def get_pipeline_log(self, limit: int = 10) -> List[OraclePipelineResult]:
        """Get recent pipeline runs."""
        return self.pipeline_log[-limit:]
