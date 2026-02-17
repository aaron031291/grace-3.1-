"""
Oracle Ingestion Pipeline for Grace.

The complete data pipeline from human whitelist through to Oracle Vector DB,
with reverse KNN neighbor discovery, LLM enrichment, and sandbox practice.

Flow:
  Human Whitelist Box (bulk 50+)
    -> Multi-Source Fetcher (web, API, GitHub, arXiv, file upload)
      -> Ingestion Pipeline (chunk, embed, score)
        -> Oracle Vector DB (all training data + dependencies)
          -> Reverse KNN Neighbor Search (auto-discover related domains)
            -> LLM Enrichment (librarian mode: read, generate, write back)
              -> Memory Mesh + MAGMA Integration
                -> Sandbox Practice Environment
"""

from .whitelist_box import WhitelistBox, WhitelistItem, WhitelistItemType, BulkSubmissionResult
from .multi_source_fetcher import MultiSourceFetcher, FetchSource, FetchResult
from .oracle_vector_store import OracleVectorStore, OracleRecord
from .reverse_knn_discovery import ReverseKNNDiscovery, NeighborDiscoveryResult
from .llm_enrichment import LLMEnrichmentEngine, EnrichmentResult
from .oracle_pipeline import OraclePipeline, OraclePipelineResult
from .librarian_file_manager import LibrarianFileManager, FileNode, FileCategory, FileType
from .proactive_discovery_engine import ProactiveDiscoveryEngine, DiscoveryTask, DiscoveryAlgorithm
from .source_code_index import SourceCodeIndex, CodeElement, CodeElementType
from .hallucination_guard import HallucinationGuard, HallucinationReport
from .perpetual_learning_loop import PerpetualLearningLoop, LoopState, TrustChainEntry
from .socratic_interrogator import SocraticInterrogator, InterrogationReport, QuestionCategory

__all__ = [
    "WhitelistBox",
    "WhitelistItem",
    "WhitelistItemType",
    "BulkSubmissionResult",
    "MultiSourceFetcher",
    "FetchSource",
    "FetchResult",
    "OracleVectorStore",
    "OracleRecord",
    "ReverseKNNDiscovery",
    "NeighborDiscoveryResult",
    "LLMEnrichmentEngine",
    "EnrichmentResult",
    "OraclePipeline",
    "OraclePipelineResult",
    "LibrarianFileManager",
    "FileNode",
    "FileCategory",
    "FileType",
    "ProactiveDiscoveryEngine",
    "DiscoveryTask",
    "DiscoveryAlgorithm",
    "SourceCodeIndex",
    "CodeElement",
    "CodeElementType",
    "HallucinationGuard",
    "HallucinationReport",
    "PerpetualLearningLoop",
    "LoopState",
    "TrustChainEntry",
    "SocraticInterrogator",
    "InterrogationReport",
    "QuestionCategory",
]
