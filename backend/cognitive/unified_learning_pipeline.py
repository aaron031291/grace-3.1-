"""
Unified Learning Pipeline - Neighbor-by-Neighbor Topic Expansion

Connects Oracle ML predictions, ingestion pipeline, and learning memory
into a continuous 24/7 data pipeline that:

1. Takes training data from Oracle (ingested documents)
2. Performs neighbor-by-neighbor search for related topics
3. Expands knowledge graph through semantic proximity
4. Feeds discoveries back into the learning system
5. Runs perpetually as a background daemon

This is the "push it as far as we can" module for the learning system.
"""

import logging
import asyncio
import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TopicNode:
    """A node in the knowledge graph representing a topic."""
    topic: str
    embedding: Optional[List[float]] = None
    trust_score: float = 0.5
    depth: int = 0
    parent_topic: Optional[str] = None
    discovered_at: str = ""
    neighbor_count: int = 0
    explored: bool = False

    def __post_init__(self):
        if not self.discovered_at:
            self.discovered_at = datetime.now().isoformat()


@dataclass
class ExpansionResult:
    """Result of a neighbor-by-neighbor expansion."""
    seed_topic: str
    neighbors_found: int
    new_topics_discovered: int
    knowledge_items_created: int
    trust_scores: Dict[str, float] = field(default_factory=dict)
    expansion_depth: int = 0
    duration_ms: float = 0.0


class NeighborByNeighborEngine:
    """
    Performs neighbor-by-neighbor search starting from ingested training data.

    Given a seed topic (from Oracle/ingestion), finds semantically related
    topics in the vector store, then recursively explores their neighbors,
    building a connected knowledge graph.
    """

    def __init__(
        self,
        max_depth: int = 3,
        max_neighbors_per_node: int = 8,
        similarity_threshold: float = 0.45,
        max_total_nodes: int = 100,
    ):
        self.max_depth = max_depth
        self.max_neighbors_per_node = max_neighbors_per_node
        self.similarity_threshold = similarity_threshold
        self.max_total_nodes = max_total_nodes

        self._retriever = None
        self._embedding_model = None
        self._knowledge_graph: Dict[str, TopicNode] = {}
        self._edges: Dict[str, Set[str]] = defaultdict(set)

    @property
    def retriever(self):
        if self._retriever is None:
            try:
                from retrieval.retriever import DocumentRetriever
                from embedding import get_embedding_model
                model = get_embedding_model()
                self._retriever = DocumentRetriever(
                    collection_name="documents",
                    embedding_model=model
                )
                self._embedding_model = model
            except Exception as e:
                logger.warning(f"[NEIGHBOR-ENGINE] Could not init retriever: {e}")
        return self._retriever

    def expand_from_seed(self, seed_topic: str, seed_text: str = "") -> ExpansionResult:
        """
        Start neighbor-by-neighbor expansion from a seed topic.

        Args:
            seed_topic: The topic to start expanding from
            seed_text: Optional text content for the seed topic
        """
        start_time = time.time()
        initial_count = len(self._knowledge_graph)

        if not self.retriever:
            return ExpansionResult(
                seed_topic=seed_topic,
                neighbors_found=0,
                new_topics_discovered=0,
                knowledge_items_created=0,
                duration_ms=0.0
            )

        seed_node = TopicNode(
            topic=seed_topic,
            trust_score=0.7,
            depth=0
        )
        self._knowledge_graph[seed_topic] = seed_node

        queue = [(seed_topic, seed_text, 0)]
        visited = {seed_topic}
        total_neighbors = 0
        total_items = 0

        while queue and len(self._knowledge_graph) < self.max_total_nodes:
            current_topic, current_text, depth = queue.pop(0)

            if depth >= self.max_depth:
                continue

            query = current_text if current_text else current_topic
            neighbors = self._find_neighbors(query)
            total_neighbors += len(neighbors)

            for neighbor_text, neighbor_score, neighbor_meta in neighbors:
                neighbor_topic = self._extract_topic(neighbor_text, neighbor_meta)

                if neighbor_topic in visited:
                    self._edges[current_topic].add(neighbor_topic)
                    continue

                visited.add(neighbor_topic)

                neighbor_node = TopicNode(
                    topic=neighbor_topic,
                    trust_score=neighbor_score,
                    depth=depth + 1,
                    parent_topic=current_topic,
                    neighbor_count=0
                )
                self._knowledge_graph[neighbor_topic] = neighbor_node
                self._edges[current_topic].add(neighbor_topic)

                self._store_learning_connection(
                    current_topic, neighbor_topic, neighbor_score
                )
                total_items += 1

                queue.append((neighbor_topic, neighbor_text[:500], depth + 1))

            if current_topic in self._knowledge_graph:
                self._knowledge_graph[current_topic].explored = True

        duration = (time.time() - start_time) * 1000
        new_count = len(self._knowledge_graph) - initial_count

        logger.info(
            f"[NEIGHBOR-ENGINE] Expanded '{seed_topic}': "
            f"depth={self.max_depth}, neighbors={total_neighbors}, "
            f"new_topics={new_count}, items={total_items}, "
            f"duration={duration:.0f}ms"
        )

        return ExpansionResult(
            seed_topic=seed_topic,
            neighbors_found=total_neighbors,
            new_topics_discovered=new_count,
            knowledge_items_created=total_items,
            trust_scores={
                t: n.trust_score for t, n in self._knowledge_graph.items()
            },
            expansion_depth=self.max_depth,
            duration_ms=duration
        )

    def _find_neighbors(self, query: str) -> List[Tuple[str, float, dict]]:
        """Find nearest neighbors in the vector store."""
        try:
            results = self.retriever.retrieve(
                query=query,
                limit=self.max_neighbors_per_node,
                score_threshold=self.similarity_threshold,
                include_metadata=True
            )

            neighbors = []
            for r in results:
                text = r.get("text", r.get("content", ""))
                score = r.get("score", 0.0)
                meta = r.get("metadata", {})
                if text and score >= self.similarity_threshold:
                    neighbors.append((text, score, meta))

            return neighbors
        except Exception as e:
            logger.debug(f"[NEIGHBOR-ENGINE] Neighbor search failed: {e}")
            return []

    def _extract_topic(self, text: str, metadata: dict) -> str:
        """Extract a topic identifier from text and metadata."""
        filename = metadata.get("filename", metadata.get("file_path", ""))
        if filename:
            import os
            name = os.path.splitext(os.path.basename(filename))[0]
            name = name.replace("_", " ").replace("-", " ")
            return name[:80]

        words = text.split()[:10]
        return " ".join(words)[:80]

    def _store_learning_connection(
        self, source_topic: str, target_topic: str, similarity: float
    ):
        """Store a learning connection between topics."""
        try:
            from cognitive.learning_memory import LearningMemoryManager
            from database.session import SessionLocal
            session = SessionLocal()
            if session:
                try:
                    manager = LearningMemoryManager(session)
                    manager.store_pattern(
                        pattern_type="topic_connection",
                        pattern_data={
                            "source": source_topic,
                            "target": target_topic,
                            "similarity": similarity,
                            "discovered_by": "neighbor_expansion"
                        },
                        confidence=similarity,
                        source="neighbor_by_neighbor_engine"
                    )
                except Exception:
                    pass
                finally:
                    session.close()
        except Exception:
            pass

    def get_knowledge_graph(self) -> Dict[str, Any]:
        """Return the current knowledge graph as a dictionary."""
        return {
            "nodes": [
                {
                    "topic": n.topic,
                    "trust_score": n.trust_score,
                    "depth": n.depth,
                    "parent": n.parent_topic,
                    "explored": n.explored,
                    "discovered_at": n.discovered_at
                }
                for n in self._knowledge_graph.values()
            ],
            "edges": {k: list(v) for k, v in self._edges.items()},
            "total_nodes": len(self._knowledge_graph),
            "total_edges": sum(len(v) for v in self._edges.values())
        }


class UnifiedLearningPipeline:
    """
    24/7 continuous data pipeline that:
    1. Monitors Oracle for new training data
    2. Runs neighbor-by-neighbor expansion on ingested content
    3. Feeds discoveries into the learning system
    4. Tracks performance and adapts expansion parameters
    5. Never stops - perpetual knowledge growth
    """

    def __init__(self):
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._neighbor_engine = NeighborByNeighborEngine(
            max_depth=3,
            max_neighbors_per_node=8,
            similarity_threshold=0.40,
            max_total_nodes=150
        )

        self.config = {
            "scan_interval_seconds": 120,
            "expansion_interval_seconds": 300,
            "min_trust_for_expansion": 0.3,
            "auto_expand_on_ingest": True,
            "max_expansions_per_cycle": 5,
            "enable_predictive_prefetch": True,
        }

        self.stats = {
            "total_expansions": 0,
            "total_topics_discovered": 0,
            "total_connections_made": 0,
            "total_cycles": 0,
            "last_cycle_time": None,
            "uptime_seconds": 0,
            "start_time": None,
        }

        self._pending_seeds: List[Dict[str, str]] = []
        self._processed_seeds: Set[str] = set()

    def start(self):
        """Start the continuous learning pipeline as a daemon thread."""
        if self.running:
            logger.info("[UNIFIED-PIPELINE] Already running")
            return

        self.running = True
        self.stats["start_time"] = datetime.now().isoformat()
        self._thread = threading.Thread(
            target=self._pipeline_loop,
            daemon=True,
            name="unified-learning-pipeline"
        )
        self._thread.start()
        logger.info("[UNIFIED-PIPELINE] Started 24/7 continuous learning pipeline")

    def stop(self):
        """Stop the pipeline."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("[UNIFIED-PIPELINE] Stopped")

    def add_seed(self, topic: str, text: str = ""):
        """Add a seed topic for expansion (called by ingestion pipeline)."""
        if topic not in self._processed_seeds:
            self._pending_seeds.append({"topic": topic, "text": text})
            logger.info(f"[UNIFIED-PIPELINE] Seed queued: {topic[:60]}")

    def _pipeline_loop(self):
        """Main pipeline loop - runs perpetually."""
        logger.info("[UNIFIED-PIPELINE] Pipeline loop started")
        cycle_count = 0

        while self.running:
            try:
                cycle_count += 1
                self.stats["total_cycles"] = cycle_count
                self.stats["last_cycle_time"] = datetime.now().isoformat()

                # Phase 1: Process pending seeds from ingestion
                seeds_processed = self._process_pending_seeds()

                # Phase 2: Discover new seeds from recent ingestions
                if cycle_count % 3 == 0:
                    self._discover_new_seeds()

                # Phase 3: Run predictive prefetch for active topics
                if self.config["enable_predictive_prefetch"] and cycle_count % 5 == 0:
                    self._run_predictive_prefetch()

                # Phase 4: Update stats
                self.stats["uptime_seconds"] = (
                    (datetime.now() - datetime.fromisoformat(
                        self.stats["start_time"]
                    )).total_seconds()
                    if self.stats["start_time"] else 0
                )

                interval = self.config["scan_interval_seconds"]
                time.sleep(interval)

            except Exception as e:
                logger.error(f"[UNIFIED-PIPELINE] Cycle error: {e}")
                time.sleep(30)

    def _process_pending_seeds(self) -> int:
        """Process all pending seed topics."""
        processed = 0
        max_per_cycle = self.config["max_expansions_per_cycle"]

        while self._pending_seeds and processed < max_per_cycle:
            seed = self._pending_seeds.pop(0)
            topic = seed["topic"]
            text = seed.get("text", "")

            if topic in self._processed_seeds:
                continue

            try:
                result = self._neighbor_engine.expand_from_seed(topic, text)
                self._processed_seeds.add(topic)
                processed += 1

                self.stats["total_expansions"] += 1
                self.stats["total_topics_discovered"] += result.new_topics_discovered
                self.stats["total_connections_made"] += result.neighbors_found

                logger.info(
                    f"[UNIFIED-PIPELINE] Expanded '{topic[:40]}': "
                    f"+{result.new_topics_discovered} topics, "
                    f"+{result.neighbors_found} connections"
                )
            except Exception as e:
                logger.warning(f"[UNIFIED-PIPELINE] Expansion failed for '{topic[:40]}': {e}")

        return processed

    def _discover_new_seeds(self):
        """Discover new seed topics from recently ingested documents."""
        try:
            from database.session import SessionLocal
            from models.database_models import Document
            session = SessionLocal()
            if not session:
                return

            try:
                cutoff = datetime.now() - timedelta(hours=1)
                recent_docs = session.query(Document).filter(
                    Document.status == "completed",
                    Document.created_at >= cutoff
                ).limit(10).all()

                for doc in recent_docs:
                    topic = doc.filename or "unknown"
                    if topic not in self._processed_seeds:
                        self._pending_seeds.append({
                            "topic": topic,
                            "text": f"Document: {topic}"
                        })
            finally:
                session.close()
        except Exception as e:
            logger.debug(f"[UNIFIED-PIPELINE] Seed discovery error: {e}")

    def _run_predictive_prefetch(self):
        """Run predictive context loading for high-value topics."""
        try:
            from cognitive.predictive_context_loader import PredictiveContextLoader
            from database.session import SessionLocal
            session = SessionLocal()
            if not session:
                return

            try:
                loader = PredictiveContextLoader(session=session)
                graph = self._neighbor_engine.get_knowledge_graph()

                high_trust_topics = [
                    n["topic"] for n in graph.get("nodes", [])
                    if n.get("trust_score", 0) > 0.6
                ][:5]

                for topic in high_trust_topics:
                    try:
                        loader.prefetch_context(topic)
                    except Exception:
                        pass
            finally:
                session.close()
        except Exception as e:
            logger.debug(f"[UNIFIED-PIPELINE] Prefetch error: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get pipeline status."""
        return {
            "running": self.running,
            "stats": self.stats,
            "config": self.config,
            "pending_seeds": len(self._pending_seeds),
            "processed_seeds": len(self._processed_seeds),
            "knowledge_graph": self._neighbor_engine.get_knowledge_graph()
        }


# Singleton
_pipeline_instance: Optional[UnifiedLearningPipeline] = None


def get_unified_pipeline() -> UnifiedLearningPipeline:
    """Get or create the unified learning pipeline singleton."""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = UnifiedLearningPipeline()
    return _pipeline_instance
