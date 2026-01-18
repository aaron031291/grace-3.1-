"""
Reverse KNN Proactive Learning System

Instead of just finding similar items, this system:
1. Analyzes what exists in the Oracle
2. Uses KNN in reverse to find knowledge GAPS
3. Proactively fetches more relevant knowledge from original sources
4. Uses LLM orchestration to optimize queries and insights

The Oracle doesn't just receive - it actively seeks to expand.
"""

import logging
import asyncio
import json
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
import uuid
import threading

logger = logging.getLogger(__name__)


class KnowledgeClusterType(str, Enum):
    """Types of knowledge clusters identified."""
    DENSE = "dense"           # Well-covered topic
    SPARSE = "sparse"         # Needs more knowledge
    FRONTIER = "frontier"     # Edge of known knowledge
    ISOLATED = "isolated"     # Disconnected knowledge
    TRENDING = "trending"     # Recently active topic


class ExpansionStrategy(str, Enum):
    """Strategies for knowledge expansion."""
    DEPTH_FIRST = "depth"     # Go deeper on existing topics
    BREADTH_FIRST = "breadth" # Explore related topics
    GAP_FILL = "gap_fill"     # Fill sparse areas
    FRONTIER_PUSH = "frontier" # Expand boundaries
    REINFORCE = "reinforce"   # Strengthen weak connections


@dataclass
class KnowledgeCluster:
    """A cluster of related knowledge in the Oracle."""
    cluster_id: str
    cluster_type: KnowledgeClusterType
    centroid_topic: str
    member_count: int
    avg_confidence: float
    topics: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)  # Original ingestion sources
    gap_score: float = 0.0  # 0 = complete, 1 = major gaps
    expansion_priority: float = 0.0
    last_expanded: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "type": self.cluster_type.value,
            "centroid": self.centroid_topic,
            "members": self.member_count,
            "confidence": self.avg_confidence,
            "gap_score": self.gap_score,
            "priority": self.expansion_priority,
            "sources": self.sources
        }


@dataclass
class ExpansionQuery:
    """A query to expand knowledge from a source."""
    query_id: str
    source: str  # github, stackoverflow, arxiv, etc.
    query_text: str
    cluster_id: str
    strategy: ExpansionStrategy
    priority: float
    expected_relevance: float
    llm_optimized: bool = False
    executed: bool = False
    results_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass  
class LLMInsight:
    """Insight from LLM orchestration."""
    insight_id: str
    insight_type: str  # gap_analysis, query_optimization, connection_discovery
    content: str
    confidence: float
    actionable_queries: List[str] = field(default_factory=list)
    source_recommendations: List[str] = field(default_factory=list)


class ReverseKNNLearning:
    """
    Reverse KNN Proactive Learning System.
    
    Uses KNN in reverse:
    - Instead of "find similar to query" 
    - Does "find what's missing around existing knowledge"
    
    Workflow:
    1. Embed all Oracle knowledge
    2. Cluster to find dense/sparse areas
    3. Identify gaps (sparse regions, frontier edges)
    4. Generate expansion queries for original sources
    5. Use LLM to optimize queries and discover connections
    6. Fetch and ingest new knowledge
    7. Repeat continuously
    """
    
    def __init__(
        self,
        oracle_hub=None,
        oracle_core=None,
        vector_db=None,
        llm_client=None,
        k_neighbors: int = 10,
        gap_threshold: float = 0.3,
        expansion_interval_seconds: int = 600
    ):
        self._oracle_hub = oracle_hub
        self._oracle_core = oracle_core
        self._vector_db = vector_db
        self._llm_client = llm_client
        
        self.k_neighbors = k_neighbors
        self.gap_threshold = gap_threshold
        self.expansion_interval = expansion_interval_seconds
        
        # Knowledge state
        self._clusters: Dict[str, KnowledgeCluster] = {}
        self._embeddings_cache: Dict[str, np.ndarray] = {}
        self._expansion_queue: List[ExpansionQuery] = []
        
        # Source connectors (same routes as ingestion)
        self._source_connectors: Dict[str, callable] = {}
        
        # Learning thread
        self._learning_thread: Optional[threading.Thread] = None
        self._running = False
        
        # Statistics
        self._stats = {
            "clusters_analyzed": 0,
            "gaps_identified": 0,
            "expansions_executed": 0,
            "knowledge_added": 0,
            "llm_optimizations": 0,
            "last_cycle": None
        }
        
        logger.info("[REVERSE-KNN] Proactive learning system initialized")
    
    # =========================================================================
    # CORE KNN REVERSE ALGORITHM
    # =========================================================================
    
    async def analyze_knowledge_landscape(self) -> Dict[str, Any]:
        """
        Analyze the Oracle's knowledge landscape using reverse KNN.
        
        Returns cluster analysis with gaps and expansion opportunities.
        """
        logger.info("[REVERSE-KNN] Analyzing knowledge landscape...")
        
        # Step 1: Get all knowledge embeddings
        embeddings = await self._get_all_embeddings()
        if len(embeddings) < self.k_neighbors:
            return {"status": "insufficient_data", "count": len(embeddings)}
        
        # Step 2: Compute KNN graph
        knn_graph = self._compute_knn_graph(embeddings)
        
        # Step 3: Identify clusters
        clusters = self._identify_clusters(embeddings, knn_graph)
        
        # Step 4: Compute gap scores (reverse KNN insight)
        for cluster in clusters:
            cluster.gap_score = self._compute_gap_score(cluster, embeddings, knn_graph)
            cluster.expansion_priority = self._compute_expansion_priority(cluster)
        
        # Step 5: Store clusters
        self._clusters = {c.cluster_id: c for c in clusters}
        
        self._stats["clusters_analyzed"] = len(clusters)
        
        return {
            "total_knowledge_items": len(embeddings),
            "clusters": len(clusters),
            "sparse_clusters": len([c for c in clusters if c.cluster_type == KnowledgeClusterType.SPARSE]),
            "frontier_clusters": len([c for c in clusters if c.cluster_type == KnowledgeClusterType.FRONTIER]),
            "clusters_data": [c.to_dict() for c in sorted(clusters, key=lambda x: x.expansion_priority, reverse=True)[:10]]
        }
    
    async def _get_all_embeddings(self) -> Dict[str, np.ndarray]:
        """Get embeddings for all Oracle knowledge."""
        embeddings = {}
        
        if self._oracle_core and hasattr(self._oracle_core, '_research'):
            try:
                from embedding.embedder import get_embedder
                embedder = get_embedder()
                
                for research_id, entry in self._oracle_core._research.items():
                    if research_id in self._embeddings_cache:
                        embeddings[research_id] = self._embeddings_cache[research_id]
                    else:
                        text = f"{entry.topic} {entry.findings[:500]}"
                        embedding = await embedder.embed(text)
                        embeddings[research_id] = np.array(embedding)
                        self._embeddings_cache[research_id] = embeddings[research_id]
                        
            except Exception as e:
                logger.warning(f"[REVERSE-KNN] Embedding error: {e}")
        
        # Also check vector DB
        if self._vector_db:
            try:
                # Get all vectors from oracle_research collection
                results = await self._vector_db.scroll(
                    collection_name="oracle_research",
                    limit=1000
                )
                for point in results:
                    if point.id not in embeddings:
                        embeddings[point.id] = np.array(point.vector)
            except Exception as e:
                logger.debug(f"[REVERSE-KNN] Vector DB scroll: {e}")
        
        return embeddings
    
    def _compute_knn_graph(self, embeddings: Dict[str, np.ndarray]) -> Dict[str, List[Tuple[str, float]]]:
        """Compute K-nearest neighbors graph."""
        ids = list(embeddings.keys())
        vectors = [embeddings[id] for id in ids]
        
        if not vectors:
            return {}
        
        vectors_array = np.array(vectors)
        
        # Compute pairwise distances
        knn_graph = {}
        
        for i, id in enumerate(ids):
            distances = []
            for j, other_id in enumerate(ids):
                if i != j:
                    dist = np.linalg.norm(vectors_array[i] - vectors_array[j])
                    distances.append((other_id, dist))
            
            # Sort by distance and take k nearest
            distances.sort(key=lambda x: x[1])
            knn_graph[id] = distances[:self.k_neighbors]
        
        return knn_graph
    
    def _identify_clusters(
        self,
        embeddings: Dict[str, np.ndarray],
        knn_graph: Dict[str, List[Tuple[str, float]]]
    ) -> List[KnowledgeCluster]:
        """Identify knowledge clusters using KNN connectivity."""
        clusters = []
        visited = set()
        
        for start_id in embeddings.keys():
            if start_id in visited:
                continue
            
            # BFS to find connected component
            cluster_members = []
            queue = [start_id]
            
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                cluster_members.append(current)
                
                # Add neighbors within distance threshold
                if current in knn_graph:
                    for neighbor_id, distance in knn_graph[current]:
                        if neighbor_id not in visited and distance < self.gap_threshold:
                            queue.append(neighbor_id)
            
            if cluster_members:
                # Determine cluster type based on density
                avg_neighbor_distance = self._compute_avg_neighbor_distance(
                    cluster_members, knn_graph
                )
                
                if avg_neighbor_distance < 0.1:
                    cluster_type = KnowledgeClusterType.DENSE
                elif avg_neighbor_distance < 0.2:
                    cluster_type = KnowledgeClusterType.SPARSE
                elif len(cluster_members) == 1:
                    cluster_type = KnowledgeClusterType.ISOLATED
                else:
                    cluster_type = KnowledgeClusterType.FRONTIER
                
                # Get topics and sources from cluster members
                topics, sources = self._extract_cluster_metadata(cluster_members)
                
                cluster = KnowledgeCluster(
                    cluster_id=f"CLUSTER-{uuid.uuid4().hex[:8]}",
                    cluster_type=cluster_type,
                    centroid_topic=topics[0] if topics else "Unknown",
                    member_count=len(cluster_members),
                    avg_confidence=0.7,
                    topics=topics[:5],
                    sources=sources
                )
                clusters.append(cluster)
        
        return clusters
    
    def _compute_avg_neighbor_distance(
        self,
        members: List[str],
        knn_graph: Dict[str, List[Tuple[str, float]]]
    ) -> float:
        """Compute average distance to neighbors for cluster density."""
        distances = []
        for member in members:
            if member in knn_graph:
                for _, dist in knn_graph[member]:
                    distances.append(dist)
        return np.mean(distances) if distances else 1.0
    
    def _extract_cluster_metadata(self, members: List[str]) -> Tuple[List[str], List[str]]:
        """Extract topics and sources from cluster members."""
        topics = []
        sources = set()
        
        if self._oracle_core and hasattr(self._oracle_core, '_research'):
            for member_id in members:
                if member_id in self._oracle_core._research:
                    entry = self._oracle_core._research[member_id]
                    topics.append(entry.topic)
        
        # Determine sources based on ID prefixes
        for member_id in members:
            if member_id.startswith("GITHUB"):
                sources.add("github")
            elif member_id.startswith("SANDBOX"):
                sources.add("sandbox")
            elif member_id.startswith("TEMPLATE"):
                sources.add("templates")
            elif member_id.startswith("RESEARCH"):
                sources.add("ai_research")
            elif member_id.startswith("HEAL"):
                sources.add("self_healing")
            elif member_id.startswith("LEARNING"):
                sources.add("learning_memory")
            else:
                sources.add("web_knowledge")
        
        return topics, list(sources)
    
    def _compute_gap_score(
        self,
        cluster: KnowledgeCluster,
        embeddings: Dict[str, np.ndarray],
        knn_graph: Dict[str, List[Tuple[str, float]]]
    ) -> float:
        """
        Compute gap score using REVERSE KNN logic.
        
        High gap score means:
        - Few neighbors point TO this cluster (reverse KNN)
        - Large distances between members
        - Frontier edges with unexplored space
        """
        # Count how many OTHER points have this cluster in their KNN
        reverse_knn_count = 0
        cluster_member_ids = set()
        
        # Get cluster member IDs by matching topics
        for id, entry_data in embeddings.items():
            if self._oracle_core and hasattr(self._oracle_core, '_research'):
                if id in self._oracle_core._research:
                    entry = self._oracle_core._research[id]
                    if entry.topic in cluster.topics:
                        cluster_member_ids.add(id)
        
        # Count reverse KNN references
        for id, neighbors in knn_graph.items():
            if id not in cluster_member_ids:
                for neighbor_id, _ in neighbors:
                    if neighbor_id in cluster_member_ids:
                        reverse_knn_count += 1
        
        # Normalize by cluster size
        expected_references = cluster.member_count * self.k_neighbors
        if expected_references > 0:
            reverse_knn_ratio = reverse_knn_count / expected_references
        else:
            reverse_knn_ratio = 0
        
        # Gap score = inverse of connectivity
        # Low reverse KNN = high gap (isolated knowledge)
        gap_score = 1.0 - min(1.0, reverse_knn_ratio)
        
        # Boost gap score for sparse/frontier clusters
        if cluster.cluster_type == KnowledgeClusterType.SPARSE:
            gap_score = min(1.0, gap_score * 1.3)
        elif cluster.cluster_type == KnowledgeClusterType.FRONTIER:
            gap_score = min(1.0, gap_score * 1.5)
        elif cluster.cluster_type == KnowledgeClusterType.ISOLATED:
            gap_score = min(1.0, gap_score * 1.8)
        
        return gap_score
    
    def _compute_expansion_priority(self, cluster: KnowledgeCluster) -> float:
        """Compute priority for expanding this cluster."""
        priority = cluster.gap_score
        
        # Boost recently active topics
        if cluster.last_expanded:
            hours_since = (datetime.utcnow() - cluster.last_expanded).total_seconds() / 3600
            if hours_since < 24:
                priority *= 0.5  # Recently expanded, lower priority
            elif hours_since > 168:  # > 1 week
                priority *= 1.2  # Stale, boost priority
        
        # Boost multi-source clusters (more valuable)
        if len(cluster.sources) > 2:
            priority *= 1.1
        
        # Boost by inverse confidence (less confident = more important to expand)
        priority *= (1.5 - cluster.avg_confidence)
        
        return min(1.0, priority)
    
    # =========================================================================
    # EXPANSION QUERY GENERATION
    # =========================================================================
    
    async def generate_expansion_queries(
        self,
        max_queries: int = 10
    ) -> List[ExpansionQuery]:
        """Generate queries to expand knowledge from original sources."""
        queries = []
        
        # Sort clusters by expansion priority
        sorted_clusters = sorted(
            self._clusters.values(),
            key=lambda c: c.expansion_priority,
            reverse=True
        )
        
        for cluster in sorted_clusters[:max_queries]:
            # Determine strategy based on cluster type
            if cluster.cluster_type == KnowledgeClusterType.SPARSE:
                strategy = ExpansionStrategy.GAP_FILL
            elif cluster.cluster_type == KnowledgeClusterType.FRONTIER:
                strategy = ExpansionStrategy.FRONTIER_PUSH
            elif cluster.cluster_type == KnowledgeClusterType.ISOLATED:
                strategy = ExpansionStrategy.BREADTH_FIRST
            else:
                strategy = ExpansionStrategy.DEPTH_FIRST
            
            # Generate query for each source that contributed to this cluster
            for source in cluster.sources:
                query_text = self._generate_query_for_source(cluster, source, strategy)
                
                query = ExpansionQuery(
                    query_id=f"EXPAND-{uuid.uuid4().hex[:8]}",
                    source=source,
                    query_text=query_text,
                    cluster_id=cluster.cluster_id,
                    strategy=strategy,
                    priority=cluster.expansion_priority,
                    expected_relevance=0.7
                )
                queries.append(query)
        
        self._expansion_queue.extend(queries)
        self._stats["gaps_identified"] += len(queries)
        
        return queries
    
    def _generate_query_for_source(
        self,
        cluster: KnowledgeCluster,
        source: str,
        strategy: ExpansionStrategy
    ) -> str:
        """Generate source-specific expansion query."""
        base_topics = " ".join(cluster.topics[:3])
        
        if source == "github":
            if strategy == ExpansionStrategy.DEPTH_FIRST:
                return f"{base_topics} implementation example code"
            elif strategy == ExpansionStrategy.GAP_FILL:
                return f"{base_topics} edge cases error handling"
            else:
                return f"{base_topics} related patterns best practices"
                
        elif source == "stackoverflow":
            if strategy == ExpansionStrategy.GAP_FILL:
                return f"{base_topics} common issues solutions"
            else:
                return f"{base_topics} how to tutorial"
                
        elif source == "ai_research":
            if strategy == ExpansionStrategy.FRONTIER_PUSH:
                return f"{base_topics} latest advances state of the art"
            else:
                return f"{base_topics} technique algorithm"
                
        elif source == "templates":
            return f"{base_topics} template pattern boilerplate"
            
        elif source == "self_healing":
            return f"{base_topics} fix solution error resolution"
            
        else:
            return base_topics
    
    # =========================================================================
    # LLM ORCHESTRATION
    # =========================================================================
    
    async def llm_optimize_expansion(
        self,
        queries: List[ExpansionQuery]
    ) -> List[ExpansionQuery]:
        """Use LLM to optimize expansion queries and discover connections."""
        if not self._llm_client:
            return queries
        
        optimized = []
        
        for query in queries:
            try:
                # Build LLM prompt
                prompt = self._build_optimization_prompt(query)
                
                # Call LLM
                response = await self._call_llm(prompt)
                
                if response:
                    # Parse optimized query
                    optimized_query = self._parse_llm_optimization(query, response)
                    optimized_query.llm_optimized = True
                    optimized.append(optimized_query)
                    self._stats["llm_optimizations"] += 1
                else:
                    optimized.append(query)
                    
            except Exception as e:
                logger.warning(f"[REVERSE-KNN] LLM optimization failed: {e}")
                optimized.append(query)
        
        return optimized
    
    def _build_optimization_prompt(self, query: ExpansionQuery) -> str:
        """Build prompt for LLM query optimization."""
        cluster = self._clusters.get(query.cluster_id)
        
        return f"""You are optimizing a knowledge expansion query for an AI system.

Current Query: {query.query_text}
Source: {query.source}
Strategy: {query.strategy.value}
Cluster Topics: {cluster.topics if cluster else []}
Gap Score: {cluster.gap_score if cluster else 0}

Your task:
1. Improve the search query to find MORE RELEVANT knowledge
2. Suggest RELATED topics that might fill gaps
3. Recommend specific search terms for this source

Output format (JSON):
{{
    "optimized_query": "improved search query",
    "related_queries": ["query1", "query2"],
    "key_terms": ["term1", "term2"],
    "reasoning": "why this optimization helps"
}}"""
    
    async def _call_llm(self, prompt: str) -> Optional[str]:
        """Call LLM for optimization."""
        if self._llm_client:
            try:
                response = await self._llm_client.generate(prompt)
                return response
            except Exception as e:
                logger.warning(f"[REVERSE-KNN] LLM call failed: {e}")
        
        # Fallback: Try DeepSeek or other configured LLM
        try:
            from llm.deepseek_client import get_deepseek_client
            client = get_deepseek_client()
            response = await client.chat(prompt)
            return response
        except Exception as e:
            logger.debug(f"[REVERSE-KNN] No LLM available: {e}")
        
        return None
    
    def _parse_llm_optimization(
        self,
        original: ExpansionQuery,
        llm_response: str
    ) -> ExpansionQuery:
        """Parse LLM response and create optimized query."""
        try:
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\{[^{}]+\}', llm_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                optimized_text = data.get("optimized_query", original.query_text)
                return ExpansionQuery(
                    query_id=original.query_id,
                    source=original.source,
                    query_text=optimized_text,
                    cluster_id=original.cluster_id,
                    strategy=original.strategy,
                    priority=original.priority,
                    expected_relevance=original.expected_relevance + 0.1,
                    llm_optimized=True
                )
        except Exception as e:
            logger.debug(f"[REVERSE-KNN] Parse error: {e}")
        
        return original
    
    async def llm_discover_connections(self) -> List[LLMInsight]:
        """Use LLM to discover hidden connections between clusters."""
        insights = []
        
        if not self._llm_client and not self._clusters:
            return insights
        
        # Build cluster summary for LLM
        cluster_summary = "\n".join([
            f"- {c.centroid_topic}: {c.member_count} items, gap={c.gap_score:.2f}, sources={c.sources}"
            for c in list(self._clusters.values())[:20]
        ])
        
        prompt = f"""Analyze these knowledge clusters and find:
1. Hidden connections between clusters
2. Knowledge gaps that span multiple clusters  
3. Opportunities to cross-pollinate knowledge

Clusters:
{cluster_summary}

Output insights as JSON array:
[{{"type": "connection|gap|opportunity", "description": "...", "clusters": ["id1", "id2"], "suggested_queries": ["..."]}}]"""
        
        response = await self._call_llm(prompt)
        
        if response:
            try:
                import re
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    for item in data:
                        insight = LLMInsight(
                            insight_id=f"INSIGHT-{uuid.uuid4().hex[:8]}",
                            insight_type=item.get("type", "connection"),
                            content=item.get("description", ""),
                            confidence=0.7,
                            actionable_queries=item.get("suggested_queries", [])
                        )
                        insights.append(insight)
            except Exception as e:
                logger.debug(f"[REVERSE-KNN] Insight parse error: {e}")
        
        return insights
    
    # =========================================================================
    # EXECUTE EXPANSION
    # =========================================================================
    
    async def execute_expansions(self, max_per_source: int = 5) -> Dict[str, Any]:
        """Execute expansion queries and ingest results."""
        results = {
            "executed": 0,
            "knowledge_added": 0,
            "by_source": {}
        }
        
        if not self._oracle_hub:
            logger.warning("[REVERSE-KNN] Oracle Hub not connected")
            return results
        
        # Group queries by source
        queries_by_source = defaultdict(list)
        for query in self._expansion_queue:
            if not query.executed:
                queries_by_source[query.source].append(query)
        
        # Execute for each source
        for source, queries in queries_by_source.items():
            source_results = await self._execute_source_expansion(
                source, queries[:max_per_source]
            )
            results["by_source"][source] = source_results
            results["executed"] += source_results.get("executed", 0)
            results["knowledge_added"] += source_results.get("ingested", 0)
        
        self._stats["expansions_executed"] += results["executed"]
        self._stats["knowledge_added"] += results["knowledge_added"]
        
        return results
    
    async def _execute_source_expansion(
        self,
        source: str,
        queries: List[ExpansionQuery]
    ) -> Dict[str, Any]:
        """Execute expansion for a specific source."""
        results = {"executed": 0, "ingested": 0}
        
        for query in queries:
            try:
                if source == "github":
                    items = await self._fetch_from_github(query.query_text)
                elif source == "stackoverflow":
                    items = await self._fetch_from_stackoverflow(query.query_text)
                elif source == "ai_research":
                    items = await self._fetch_from_research(query.query_text)
                elif source == "web_knowledge":
                    items = await self._fetch_from_web(query.query_text)
                else:
                    items = []
                
                # Ingest results through Oracle Hub
                for item in items:
                    await self._oracle_hub.ingest(item)
                    results["ingested"] += 1
                
                query.executed = True
                query.results_count = len(items)
                results["executed"] += 1
                
            except Exception as e:
                logger.warning(f"[REVERSE-KNN] Expansion error for {source}: {e}")
        
        return results
    
    async def _fetch_from_github(self, query: str) -> List:
        """Fetch from GitHub using web knowledge integration."""
        items = []
        try:
            from oracle_intelligence.web_knowledge import WebKnowledgeIntegration
            web_knowledge = WebKnowledgeIntegration()
            results = await web_knowledge.search_github_code(query, limit=5)
            
            from oracle_intelligence.unified_oracle_hub import IntelligenceSource, IntelligenceItem
            
            for result in results:
                item = IntelligenceItem(
                    item_id=f"EXPAND-GH-{uuid.uuid4().hex[:8]}",
                    source=IntelligenceSource.GITHUB_PULLS,
                    title=result.title if hasattr(result, 'title') else query,
                    content=result.content if hasattr(result, 'content') else str(result),
                    code_examples=[result.content[:500]] if hasattr(result, 'content') else [],
                    confidence=0.75,
                    tags=["expansion", "github", "proactive"]
                )
                items.append(item)
                
        except Exception as e:
            logger.debug(f"[REVERSE-KNN] GitHub fetch: {e}")
        
        return items
    
    async def _fetch_from_stackoverflow(self, query: str) -> List:
        """Fetch from Stack Overflow."""
        items = []
        try:
            from oracle_intelligence.web_knowledge import WebKnowledgeIntegration
            web_knowledge = WebKnowledgeIntegration()
            results = await web_knowledge.search_stackoverflow(query, limit=5)
            
            from oracle_intelligence.unified_oracle_hub import IntelligenceSource, IntelligenceItem
            
            for result in results:
                item = IntelligenceItem(
                    item_id=f"EXPAND-SO-{uuid.uuid4().hex[:8]}",
                    source=IntelligenceSource.STACKOVERFLOW,
                    title=result.title if hasattr(result, 'title') else query,
                    content=result.content if hasattr(result, 'content') else str(result),
                    confidence=0.8,
                    tags=["expansion", "stackoverflow", "proactive"]
                )
                items.append(item)
                
        except Exception as e:
            logger.debug(f"[REVERSE-KNN] StackOverflow fetch: {e}")
        
        return items
    
    async def _fetch_from_research(self, query: str) -> List:
        """Fetch from AI research sources."""
        items = []
        try:
            from oracle_intelligence.web_knowledge import WebKnowledgeIntegration
            web_knowledge = WebKnowledgeIntegration()
            results = await web_knowledge.search_documentation(query, limit=3)
            
            from oracle_intelligence.unified_oracle_hub import IntelligenceSource, IntelligenceItem
            
            for result in results:
                item = IntelligenceItem(
                    item_id=f"EXPAND-RES-{uuid.uuid4().hex[:8]}",
                    source=IntelligenceSource.AI_RESEARCH,
                    title=result.title if hasattr(result, 'title') else query,
                    content=result.content if hasattr(result, 'content') else str(result),
                    confidence=0.85,
                    tags=["expansion", "research", "proactive"]
                )
                items.append(item)
                
        except Exception as e:
            logger.debug(f"[REVERSE-KNN] Research fetch: {e}")
        
        return items
    
    async def _fetch_from_web(self, query: str) -> List:
        """Fetch from general web search."""
        items = []
        try:
            from oracle_intelligence.web_knowledge import WebKnowledgeIntegration
            web_knowledge = WebKnowledgeIntegration()
            results = await web_knowledge.search_web(query, limit=3)
            
            from oracle_intelligence.unified_oracle_hub import IntelligenceSource, IntelligenceItem
            
            for result in results:
                item = IntelligenceItem(
                    item_id=f"EXPAND-WEB-{uuid.uuid4().hex[:8]}",
                    source=IntelligenceSource.WEB_KNOWLEDGE,
                    title=result.title if hasattr(result, 'title') else query,
                    content=result.content if hasattr(result, 'content') else str(result),
                    confidence=0.7,
                    tags=["expansion", "web", "proactive"]
                )
                items.append(item)
                
        except Exception as e:
            logger.debug(f"[REVERSE-KNN] Web fetch: {e}")
        
        return items
    
    # =========================================================================
    # CONTINUOUS LEARNING LOOP
    # =========================================================================
    
    def start_proactive_learning(self):
        """Start continuous proactive learning loop."""
        if self._running:
            return {"status": "already_running"}
        
        self._running = True
        
        def learning_loop():
            while self._running:
                try:
                    asyncio.run(self._run_learning_cycle())
                except Exception as e:
                    logger.error(f"[REVERSE-KNN] Learning cycle error: {e}")
                
                # Wait for next cycle
                for _ in range(self.expansion_interval):
                    if not self._running:
                        break
                    import time
                    time.sleep(1)
        
        self._learning_thread = threading.Thread(target=learning_loop, daemon=True)
        self._learning_thread.start()
        
        logger.info("[REVERSE-KNN] Proactive learning started")
        return {"status": "started", "interval": self.expansion_interval}
    
    def stop_proactive_learning(self):
        """Stop continuous proactive learning."""
        self._running = False
        logger.info("[REVERSE-KNN] Proactive learning stopped")
        return {"status": "stopped"}
    
    async def _run_learning_cycle(self):
        """Run one complete learning cycle."""
        logger.info("[REVERSE-KNN] Running proactive learning cycle...")
        
        # Step 1: Analyze knowledge landscape
        landscape = await self.analyze_knowledge_landscape()
        logger.info(f"[REVERSE-KNN] Landscape: {landscape.get('clusters', 0)} clusters, {landscape.get('sparse_clusters', 0)} sparse")
        
        # Step 2: Generate expansion queries
        queries = await self.generate_expansion_queries(max_queries=10)
        logger.info(f"[REVERSE-KNN] Generated {len(queries)} expansion queries")
        
        # Step 3: LLM optimize queries
        optimized = await self.llm_optimize_expansion(queries)
        logger.info(f"[REVERSE-KNN] Optimized {len([q for q in optimized if q.llm_optimized])} queries with LLM")
        
        # Step 4: Discover connections
        insights = await self.llm_discover_connections()
        if insights:
            logger.info(f"[REVERSE-KNN] Discovered {len(insights)} insights")
        
        # Step 5: Execute expansions
        results = await self.execute_expansions(max_per_source=3)
        logger.info(f"[REVERSE-KNN] Executed {results['executed']} expansions, added {results['knowledge_added']} items")
        
        self._stats["last_cycle"] = datetime.utcnow().isoformat()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get learning statistics."""
        return {
            **self._stats,
            "clusters": len(self._clusters),
            "pending_queries": len([q for q in self._expansion_queue if not q.executed]),
            "running": self._running
        }


# =============================================================================
# SINGLETON
# =============================================================================

_reverse_knn_instance: Optional[ReverseKNNLearning] = None


def get_reverse_knn_learning(
    oracle_hub=None,
    oracle_core=None,
    vector_db=None,
    llm_client=None
) -> ReverseKNNLearning:
    """Get singleton Reverse KNN Learning instance."""
    global _reverse_knn_instance
    
    if _reverse_knn_instance is None:
        _reverse_knn_instance = ReverseKNNLearning(
            oracle_hub=oracle_hub,
            oracle_core=oracle_core,
            vector_db=vector_db,
            llm_client=llm_client
        )
    
    return _reverse_knn_instance


async def initialize_reverse_knn_with_oracle():
    """Initialize Reverse KNN with Oracle Hub connection."""
    try:
        from oracle_intelligence.unified_oracle_hub import get_oracle_hub
        from oracle_intelligence.oracle_core import OracleCore
        
        hub = get_oracle_hub()
        oracle = OracleCore()
        
        rknn = get_reverse_knn_learning(
            oracle_hub=hub,
            oracle_core=oracle
        )
        
        # Start proactive learning
        rknn.start_proactive_learning()
        
        logger.info("[REVERSE-KNN] Initialized with Oracle Hub")
        return rknn
        
    except Exception as e:
        logger.error(f"[REVERSE-KNN] Initialization failed: {e}")
        return None
