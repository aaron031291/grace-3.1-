"""
Reverse KNN Neighbor Discovery

After ingesting user-requested data, the Reverse KNN looks at what's
in the Oracle and automatically discovers related domains to fetch.

If the user looked at Python -> auto-discover Rust, Go, AI, quantum.
If the user looked at sales -> auto-discover marketing, advertising.

Runs as a background process so Grace is always learning.
This is the self-learning + self-building loop into the data.
"""

import logging
import uuid
from typing import Dict, Any, Optional, List, Set, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from collections import defaultdict

from .oracle_vector_store import OracleVectorStore

logger = logging.getLogger(__name__)


@dataclass
class NeighborDomain:
    """A discovered neighboring domain."""
    domain: str
    relevance_score: float
    source_domains: List[str]
    suggested_queries: List[str]
    reason: str


@dataclass
class NeighborDiscoveryResult:
    """Result of a reverse KNN neighbor discovery."""
    discovery_id: str
    source_domain: str
    discovered_neighbors: List[NeighborDomain]
    total_discovered: int
    auto_fetch_triggered: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ReverseKNNDiscovery:
    """
    Reverse K-Nearest Neighbor search for auto-discovering related domains.

    Given what's been ingested into the Oracle, finds neighboring
    domains that the user would likely benefit from learning about.

    Domain Neighbor Map (knowledge graph of related domains):
    - python -> [rust, go, javascript, data_science, ai_ml]
    - ai_ml -> [python, mathematics, statistics, neuroscience, quantum]
    - sales_marketing -> [psychology, copywriting, advertising, analytics]
    - security -> [cryptography, networking, devops, compliance]
    - etc.

    The discovery runs as a background process, continuously finding
    new things for Grace to learn based on what she already knows.
    """

    DOMAIN_NEIGHBORS = {
        "python": [
            ("rust", 0.7, "Systems programming complement to Python"),
            ("go", 0.6, "Concurrent programming complement"),
            ("javascript", 0.5, "Full-stack web development"),
            ("ai_ml", 0.9, "Python is the language of AI/ML"),
            ("data_science", 0.85, "Python dominates data science"),
            ("devops", 0.5, "Python for automation"),
        ],
        "rust": [
            ("python", 0.6, "High-level complement to Rust"),
            ("go", 0.7, "Another systems language"),
            ("c_cpp", 0.8, "Systems programming family"),
            ("webassembly", 0.7, "Rust compiles to WASM"),
            ("security", 0.6, "Memory-safe systems programming"),
        ],
        "javascript": [
            ("typescript", 0.9, "Typed JavaScript"),
            ("python", 0.5, "Backend complement"),
            ("react", 0.8, "Most popular JS framework"),
            ("nodejs", 0.85, "Server-side JavaScript"),
            ("web_development", 0.9, "JS is the web language"),
        ],
        "ai_ml": [
            ("python", 0.9, "Primary AI/ML language"),
            ("mathematics", 0.8, "Foundation of ML"),
            ("statistics", 0.8, "Statistical learning"),
            ("deep_learning", 0.9, "Subset of ML"),
            ("nlp", 0.7, "Natural language processing"),
            ("computer_vision", 0.7, "Visual AI"),
            ("quantum", 0.5, "Quantum ML frontier"),
        ],
        "sales_marketing": [
            ("psychology", 0.8, "Understanding buyer behavior"),
            ("copywriting", 0.85, "Writing persuasive content"),
            ("advertising", 0.9, "Paid acquisition"),
            ("analytics", 0.7, "Measuring performance"),
            ("business", 0.7, "Business fundamentals"),
            ("branding", 0.6, "Brand building"),
        ],
        "security": [
            ("cryptography", 0.85, "Encryption and security foundations"),
            ("networking", 0.7, "Network security"),
            ("devops", 0.6, "SecDevOps practices"),
            ("compliance", 0.5, "Regulatory compliance"),
            ("penetration_testing", 0.8, "Offensive security"),
        ],
        "devops": [
            ("kubernetes", 0.9, "Container orchestration"),
            ("docker", 0.9, "Containerization"),
            ("terraform", 0.7, "Infrastructure as code"),
            ("ci_cd", 0.85, "Continuous integration"),
            ("monitoring", 0.7, "Observability"),
            ("security", 0.6, "DevSecOps"),
        ],
        "science": [
            ("mathematics", 0.8, "Scientific foundations"),
            ("physics", 0.7, "Physical sciences"),
            ("biology", 0.5, "Life sciences"),
            ("quantum", 0.6, "Quantum science"),
            ("ai_ml", 0.5, "Scientific computing with AI"),
        ],
        "business": [
            ("sales_marketing", 0.7, "Revenue generation"),
            ("finance", 0.6, "Financial management"),
            ("leadership", 0.5, "Team management"),
            ("analytics", 0.6, "Business intelligence"),
            ("strategy", 0.7, "Business strategy"),
        ],
    }

    MAX_NEIGHBORS = 5
    MIN_RELEVANCE = 0.5

    def __init__(
        self,
        oracle_store: Optional[OracleVectorStore] = None,
        max_neighbors: int = MAX_NEIGHBORS,
        min_relevance: float = MIN_RELEVANCE,
    ):
        self.oracle_store = oracle_store
        self.max_neighbors = max_neighbors
        self.min_relevance = min_relevance
        self.discovery_log: List[NeighborDiscoveryResult] = []
        self._already_discovered: Set[str] = set()
        logger.info("[REVERSE-KNN] Discovery engine initialized")

    def discover_neighbors(
        self, domain: str, exclude_known: bool = True
    ) -> NeighborDiscoveryResult:
        """
        Discover neighboring domains for a given domain.

        Args:
            domain: The source domain to find neighbors for
            exclude_known: Whether to exclude already-known domains

        Returns:
            NeighborDiscoveryResult
        """
        neighbors_raw = self.DOMAIN_NEIGHBORS.get(domain, [])

        # Filter and score
        known_domains: Set[str] = set()
        if exclude_known and self.oracle_store:
            known_domains = set(self.oracle_store.get_all_domains())

        discovered: List[NeighborDomain] = []
        for neighbor_domain, relevance, reason in neighbors_raw:
            if relevance < self.min_relevance:
                continue
            if exclude_known and neighbor_domain in known_domains:
                continue
            if neighbor_domain in self._already_discovered:
                continue

            suggested = self._generate_search_queries(domain, neighbor_domain)
            discovered.append(NeighborDomain(
                domain=neighbor_domain,
                relevance_score=relevance,
                source_domains=[domain],
                suggested_queries=suggested,
                reason=reason,
            ))

        # Sort by relevance and limit
        discovered.sort(key=lambda n: n.relevance_score, reverse=True)
        discovered = discovered[:self.max_neighbors]

        auto_fetch = len(discovered) > 0
        for d in discovered:
            self._already_discovered.add(d.domain)

        result = NeighborDiscoveryResult(
            discovery_id=f"disc-{uuid.uuid4().hex[:12]}",
            source_domain=domain,
            discovered_neighbors=discovered,
            total_discovered=len(discovered),
            auto_fetch_triggered=auto_fetch,
        )

        self.discovery_log.append(result)

        logger.info(
            f"[REVERSE-KNN] Domain '{domain}': discovered "
            f"{len(discovered)} neighbor(s)"
        )

        return result

    def discover_all(self) -> List[NeighborDiscoveryResult]:
        """
        Run neighbor discovery for all domains in the Oracle.

        Returns:
            List of NeighborDiscoveryResult
        """
        if not self.oracle_store:
            return []

        domains = self.oracle_store.get_all_domains()
        results: List[NeighborDiscoveryResult] = []

        for domain in domains:
            result = self.discover_neighbors(domain)
            if result.total_discovered > 0:
                results.append(result)

        return results

    def get_suggested_queries(
        self, domain: str
    ) -> List[Dict[str, Any]]:
        """Get all suggested search queries for a domain."""
        result = self.discover_neighbors(domain, exclude_known=False)
        queries: List[Dict[str, Any]] = []
        for neighbor in result.discovered_neighbors:
            for query in neighbor.suggested_queries:
                queries.append({
                    "query": query,
                    "target_domain": neighbor.domain,
                    "relevance": neighbor.relevance_score,
                    "reason": neighbor.reason,
                })
        return queries

    def _generate_search_queries(
        self, source_domain: str, target_domain: str
    ) -> List[str]:
        """Generate search queries for discovering a target domain."""
        formatted_src = source_domain.replace("_", " ")
        formatted_tgt = target_domain.replace("_", " ")

        queries = [
            f"{formatted_tgt} tutorial for {formatted_src} developers",
            f"best {formatted_tgt} resources",
            f"{formatted_tgt} fundamentals",
        ]
        return queries

    def get_discovery_log(self, limit: int = 20) -> List[NeighborDiscoveryResult]:
        """Get recent discovery log."""
        return self.discovery_log[-limit:]

    def reset_discovered(self) -> None:
        """Reset the already-discovered set."""
        self._already_discovered.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get discovery statistics."""
        total_discovered = sum(r.total_discovered for r in self.discovery_log)
        return {
            "total_discoveries": len(self.discovery_log),
            "total_neighbors_found": total_discovered,
            "domains_explored": len(
                set(r.source_domain for r in self.discovery_log)
            ),
            "already_discovered": len(self._already_discovered),
        }
