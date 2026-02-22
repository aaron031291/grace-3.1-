"""
Cross-Pattern Analyzer

Analyzes patterns across domains, industries, and customer segments
to find "seed" relationships -- where success in one domain can
feed into another, creating the "be everywhere" effect.

This is the "10X industries that seed each other" concept from
the requirements. The analyzer finds which niches have overlapping
audiences and complementary products.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from business_intelligence.models.data_models import (
    MarketOpportunity,
    PainPoint,
    CustomerArchetype,
    ProductConcept,
    ProductType,
    DataSource,
)

logger = logging.getLogger(__name__)


@dataclass
class DomainConnection:
    """A connection between two market domains."""
    domain_a: str = ""
    domain_b: str = ""
    connection_strength: float = 0.0
    shared_pain_points: List[str] = field(default_factory=list)
    shared_keywords: List[str] = field(default_factory=list)
    shared_audience_percentage: float = 0.0
    seed_direction: str = ""  # "a_to_b", "b_to_a", "bidirectional"
    product_chain: List[str] = field(default_factory=list)


@dataclass
class DomainMap:
    """Map of interconnected market domains."""
    domains: List[str] = field(default_factory=list)
    connections: List[DomainConnection] = field(default_factory=list)
    clusters: List[List[str]] = field(default_factory=list)
    best_entry_point: str = ""
    expansion_path: List[str] = field(default_factory=list)
    total_addressable_market: float = 0.0


class CrossPatternAnalyzer:
    """Analyzes cross-domain patterns for market expansion strategy."""

    async def analyze_domain_connections(
        self,
        opportunities: List[MarketOpportunity],
        archetypes: Optional[List[CustomerArchetype]] = None,
        existing_products: Optional[List[ProductConcept]] = None,
    ) -> DomainMap:
        """Build a map of connected market domains.

        Finds which niches share pain points, audiences, or product
        chain relationships (where one product naturally leads to another).
        """
        domains = list(set(o.niche for o in opportunities if o.niche))
        if not domains:
            return DomainMap()

        connections = []

        for i, opp_a in enumerate(opportunities):
            for j, opp_b in enumerate(opportunities):
                if i >= j or opp_a.niche == opp_b.niche:
                    continue

                connection = self._find_connection(opp_a, opp_b, archetypes)
                if connection and connection.connection_strength > 0.2:
                    connections.append(connection)

        connections.sort(key=lambda c: c.connection_strength, reverse=True)

        clusters = self._find_clusters(domains, connections)
        entry_point = self._find_best_entry(opportunities, connections)
        expansion = self._plan_expansion(entry_point, connections, domains)

        return DomainMap(
            domains=domains,
            connections=connections,
            clusters=clusters,
            best_entry_point=entry_point,
            expansion_path=expansion,
        )

    def _find_connection(
        self,
        opp_a: MarketOpportunity,
        opp_b: MarketOpportunity,
        archetypes: Optional[List[CustomerArchetype]] = None,
    ) -> Optional[DomainConnection]:
        """Find connection between two opportunities."""
        pain_a = {p.description[:50].lower() for p in opp_a.pain_points}
        pain_b = {p.description[:50].lower() for p in opp_b.pain_points}
        shared_pains = pain_a & pain_b

        keywords_a = set()
        for p in opp_a.pain_points:
            keywords_a.update(word.lower() for word in p.description.split() if len(word) > 3)
        keywords_b = set()
        for p in opp_b.pain_points:
            keywords_b.update(word.lower() for word in p.description.split() if len(word) > 3)
        shared_keywords = keywords_a & keywords_b

        pain_overlap = len(shared_pains) / max(len(pain_a | pain_b), 1)
        keyword_overlap = len(shared_keywords) / max(len(keywords_a | keywords_b), 1)

        audience_overlap = 0.0
        if archetypes:
            interests_a = set()
            interests_b = set()
            for arch in archetypes:
                arch_interests = set(arch.pain_points)
                niche_a_words = set(opp_a.niche.lower().split())
                niche_b_words = set(opp_b.niche.lower().split())
                if arch_interests & niche_a_words:
                    interests_a.update(arch.pain_points)
                if arch_interests & niche_b_words:
                    interests_b.update(arch.pain_points)
            if interests_a or interests_b:
                audience_overlap = len(interests_a & interests_b) / max(len(interests_a | interests_b), 1)

        strength = (
            pain_overlap * 0.4 +
            keyword_overlap * 0.3 +
            audience_overlap * 0.3
        )

        if strength < 0.1:
            return None

        if opp_a.opportunity_score > opp_b.opportunity_score:
            seed_dir = "a_to_b"
        elif opp_b.opportunity_score > opp_a.opportunity_score:
            seed_dir = "b_to_a"
        else:
            seed_dir = "bidirectional"

        product_chain = self._identify_product_chain(opp_a, opp_b)

        return DomainConnection(
            domain_a=opp_a.niche,
            domain_b=opp_b.niche,
            connection_strength=round(strength, 3),
            shared_pain_points=list(shared_pains)[:5],
            shared_keywords=list(shared_keywords)[:10],
            shared_audience_percentage=round(audience_overlap, 3),
            seed_direction=seed_dir,
            product_chain=product_chain,
        )

    def _identify_product_chain(
        self,
        opp_a: MarketOpportunity,
        opp_b: MarketOpportunity,
    ) -> List[str]:
        """Identify how products in domain A can seed domain B."""
        chain = []

        type_progression = {
            ProductType.EBOOK_PDF: "Create content in domain A to build authority",
            ProductType.ONLINE_COURSE: "Teach domain A skills, introduce domain B concepts",
            ProductType.TEMPLATE_TOOLKIT: "Provide tools for domain A that cross into domain B",
            ProductType.SAAS: "Build platform that serves both domains",
            ProductType.AI_AUTOMATION: "Automate domain A workflow, extend to domain B",
            ProductType.COMMUNITY_MEMBERSHIP: "Build community around shared interests",
        }

        for pt in opp_a.recommended_product_types:
            if pt in type_progression:
                chain.append(type_progression[pt])

        return chain[:3]

    def _find_clusters(
        self,
        domains: List[str],
        connections: List[DomainConnection],
    ) -> List[List[str]]:
        """Find clusters of tightly connected domains."""
        adjacency: Dict[str, Set[str]] = defaultdict(set)
        for conn in connections:
            if conn.connection_strength > 0.3:
                adjacency[conn.domain_a].add(conn.domain_b)
                adjacency[conn.domain_b].add(conn.domain_a)

        visited: Set[str] = set()
        clusters: List[List[str]] = []

        for domain in domains:
            if domain in visited:
                continue
            cluster = []
            queue = [domain]
            while queue:
                d = queue.pop(0)
                if d in visited:
                    continue
                visited.add(d)
                cluster.append(d)
                for neighbor in adjacency.get(d, set()):
                    if neighbor not in visited:
                        queue.append(neighbor)
            if cluster:
                clusters.append(sorted(cluster))

        clusters.sort(key=len, reverse=True)
        return clusters

    def _find_best_entry(
        self,
        opportunities: List[MarketOpportunity],
        connections: List[DomainConnection],
    ) -> str:
        """Find the best domain to enter first.

        The best entry point has:
        - High opportunity score
        - Many connections to other domains
        - Low entry barriers
        """
        domain_scores: Dict[str, float] = {}

        for opp in opportunities:
            if not opp.niche:
                continue
            conn_count = sum(
                1 for c in connections
                if c.domain_a == opp.niche or c.domain_b == opp.niche
            )
            connectivity_bonus = min(conn_count * 0.1, 0.3)
            barrier_penalty = min(len(opp.entry_barriers) * 0.05, 0.2)

            score = opp.opportunity_score + connectivity_bonus - barrier_penalty
            domain_scores[opp.niche] = score

        if not domain_scores:
            return ""

        return max(domain_scores, key=domain_scores.get)

    def _plan_expansion(
        self,
        entry_point: str,
        connections: List[DomainConnection],
        all_domains: List[str],
    ) -> List[str]:
        """Plan the expansion path from the entry point.

        Order domains by: connection strength to already-entered domains,
        creating a breadth-first expansion from the entry point.
        """
        if not entry_point:
            return []

        visited = {entry_point}
        path = [entry_point]

        remaining_connections = sorted(
            connections, key=lambda c: c.connection_strength, reverse=True
        )

        while len(path) < len(all_domains) and remaining_connections:
            best_next = None
            best_strength = 0

            for conn in remaining_connections:
                if conn.domain_a in visited and conn.domain_b not in visited:
                    if conn.connection_strength > best_strength:
                        best_next = conn.domain_b
                        best_strength = conn.connection_strength
                elif conn.domain_b in visited and conn.domain_a not in visited:
                    if conn.connection_strength > best_strength:
                        best_next = conn.domain_a
                        best_strength = conn.connection_strength

            if best_next:
                visited.add(best_next)
                path.append(best_next)
                remaining_connections = [
                    c for c in remaining_connections
                    if c.domain_a not in visited or c.domain_b not in visited
                ]
            else:
                break

        unvisited = [d for d in all_domains if d not in visited]
        path.extend(unvisited)

        return path

    async def generate_expansion_strategy(
        self,
        domain_map: DomainMap,
        product_concepts: Optional[List[ProductConcept]] = None,
    ) -> Dict[str, Any]:
        """Generate a strategic expansion plan.

        This is the "be everywhere" strategy, broken into
        actionable phases.
        """
        if not domain_map.domains:
            return {"message": "No domains analyzed yet"}

        phases = []
        for idx, domain in enumerate(domain_map.expansion_path[:5]):
            connections_to = [
                c for c in domain_map.connections
                if (c.domain_a == domain or c.domain_b == domain)
                and c.connection_strength > 0.2
            ]

            phase = {
                "phase": idx + 1,
                "domain": domain,
                "strategy": self._phase_strategy(idx),
                "connected_to": [
                    c.domain_b if c.domain_a == domain else c.domain_a
                    for c in connections_to[:3]
                ],
                "product_chain": [
                    step
                    for c in connections_to
                    for step in c.product_chain[:1]
                ][:3],
            }
            phases.append(phase)

        return {
            "total_domains": len(domain_map.domains),
            "entry_point": domain_map.best_entry_point,
            "expansion_path": domain_map.expansion_path,
            "domain_clusters": domain_map.clusters,
            "phases": phases,
            "strategy_summary": (
                f"Enter through '{domain_map.best_entry_point}', "
                f"then expand across {len(domain_map.domains)} connected domains. "
                f"{len(domain_map.connections)} domain connections identified. "
                "Each phase builds on the authority and audience from the previous."
            ),
        }

    def _phase_strategy(self, phase_index: int) -> str:
        strategies = [
            "DOMINATE: Focus 100% on this niche. Build authority, collect data, validate demand.",
            "EXPAND: Leverage domain 1 audience. Cross-promote content. Test new messaging.",
            "BRIDGE: Create products that serve both existing and new domains. Build cross-domain authority.",
            "SCALE: Automation and systems. Replicate proven playbook in new domain.",
            "CONSOLIDATE: Connect all domains. Build platform play. Become the go-to in the ecosystem.",
        ]
        return strategies[min(phase_index, len(strategies) - 1)]
