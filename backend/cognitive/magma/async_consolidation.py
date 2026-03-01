"""
Magma Memory - Async Consolidation Pipeline

Asynchronous processing for:
1. Async Queue - Buffer for pending operations
2. Neighbor Retrieval - Graph-based neighbor fetching
3. Context Synthesizer - Linearized context generation for LLM
4. Background Consolidation - Periodic graph optimization

This handles the "Asynchronous Consolidation" box in the Magma architecture.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable, Tuple
from enum import Enum
from datetime import datetime
from collections import deque
import threading
import time
import uuid
import logging

from cognitive.magma.relation_graphs import MagmaRelationGraphs, GraphNode
from cognitive.magma.rrf_fusion import RetrievalResult, FusedResult

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of operations in the queue."""
    INGEST = "ingest"
    LINK = "link"
    UPDATE = "update"
    DELETE = "delete"
    CONSOLIDATE = "consolidate"
    INFERENCE = "inference"


class OperationPriority(Enum):
    """Priority levels for operations."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class QueuedOperation:
    """An operation waiting in the queue."""
    id: str
    operation_type: OperationType
    priority: OperationPriority
    payload: Dict[str, Any]
    callback: Optional[Callable] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    retries: int = 0
    max_retries: int = 3
    genesis_key_id: Optional[str] = None


@dataclass
class OperationResult:
    """Result of a processed operation."""
    operation_id: str
    success: bool
    result: Any
    error: Optional[str] = None
    processed_at: datetime = field(default_factory=datetime.utcnow)


class AsyncOperationQueue:
    """
    Async queue for Magma operations.

    Features:
    - Priority-based ordering
    - Retry handling
    - Callback support
    - Thread-safe operations
    """

    def __init__(self, max_size: int = 10000):
        """
        Initialize async queue.

        Args:
            max_size: Maximum queue size
        """
        self.max_size = max_size
        self._queues: Dict[OperationPriority, deque] = {
            priority: deque(maxlen=max_size // 4)
            for priority in OperationPriority
        }
        self._lock = threading.Lock()
        self._results: Dict[str, OperationResult] = {}
        self._results_lock = threading.Lock()

        logger.info(f"[MAGMA-QUEUE] AsyncOperationQueue initialized (max_size={max_size})")

    def enqueue(
        self,
        operation_type: OperationType,
        payload: Dict[str, Any],
        priority: OperationPriority = OperationPriority.MEDIUM,
        callback: Optional[Callable] = None,
        genesis_key_id: Optional[str] = None
    ) -> str:
        """
        Add operation to queue.

        Returns:
            Operation ID
        """
        operation = QueuedOperation(
            id=f"op-{uuid.uuid4().hex[:12]}",
            operation_type=operation_type,
            priority=priority,
            payload=payload,
            callback=callback,
            genesis_key_id=genesis_key_id
        )

        with self._lock:
            self._queues[priority].append(operation)

        logger.debug(f"[MAGMA-QUEUE] Enqueued {operation_type.value} (priority={priority.value})")

        return operation.id

    def dequeue(self) -> Optional[QueuedOperation]:
        """
        Get next operation (highest priority first).

        Returns:
            QueuedOperation or None if queue is empty
        """
        with self._lock:
            # Check queues in priority order (highest first)
            for priority in reversed(list(OperationPriority)):
                if self._queues[priority]:
                    return self._queues[priority].popleft()

        return None

    def peek(self) -> Optional[QueuedOperation]:
        """Peek at next operation without removing."""
        with self._lock:
            for priority in reversed(list(OperationPriority)):
                if self._queues[priority]:
                    return self._queues[priority][0]
        return None

    def store_result(self, result: OperationResult):
        """Store operation result."""
        with self._results_lock:
            self._results[result.operation_id] = result

    def get_result(self, operation_id: str) -> Optional[OperationResult]:
        """Get result for an operation."""
        with self._results_lock:
            return self._results.get(operation_id)

    def get_queue_sizes(self) -> Dict[str, int]:
        """Get current queue sizes by priority."""
        with self._lock:
            return {
                priority.name: len(queue)
                for priority, queue in self._queues.items()
            }

    def total_pending(self) -> int:
        """Get total pending operations."""
        with self._lock:
            return sum(len(q) for q in self._queues.values())


class NeighborRetriever:
    """
    Graph-based neighbor retrieval.

    Retrieves neighbors from relation graphs with configurable strategies.
    """

    def __init__(self, graphs: MagmaRelationGraphs):
        self.graphs = graphs

    def get_neighbors(
        self,
        node_id: str,
        graph_name: str,
        max_neighbors: int = 20,
        min_weight: float = 0.1,
        direction: str = "both"
    ) -> List[Tuple[GraphNode, float]]:
        """
        Get neighbors of a node.

        Args:
            node_id: Source node ID
            graph_name: Target graph
            max_neighbors: Maximum neighbors to return
            min_weight: Minimum edge weight
            direction: outgoing, incoming, or both

        Returns:
            List of (neighbor_node, edge_weight) tuples
        """
        graph_map = {
            "semantic": self.graphs.semantic,
            "temporal": self.graphs.temporal,
            "causal": self.graphs.causal,
            "entity": self.graphs.entity,
        }

        graph = graph_map.get(graph_name)
        if not graph:
            return []

        neighbors = graph.get_neighbors(node_id, direction=direction)

        # Filter by weight and sort
        filtered = [
            (node, edge.weight) for node, edge in neighbors
            if edge.weight >= min_weight
        ]
        filtered.sort(key=lambda x: x[1], reverse=True)

        return filtered[:max_neighbors]

    def get_multi_hop_neighbors(
        self,
        node_id: str,
        graph_name: str,
        hops: int = 2,
        max_per_hop: int = 10
    ) -> Dict[int, List[GraphNode]]:
        """
        Get neighbors at multiple hop distances.

        Returns:
            Dict mapping hop distance to list of nodes
        """
        graph_map = {
            "semantic": self.graphs.semantic,
            "temporal": self.graphs.temporal,
            "causal": self.graphs.causal,
            "entity": self.graphs.entity,
        }

        graph = graph_map.get(graph_name)
        if not graph:
            return {}

        results = {}
        visited = {node_id}
        current_level = [node_id]

        for hop in range(1, hops + 1):
            next_level = []
            for current_id in current_level:
                neighbors = graph.get_neighbors(current_id, direction="both")
                for node, edge in neighbors:
                    if node.id not in visited:
                        visited.add(node.id)
                        next_level.append(node)

            results[hop] = next_level[:max_per_hop]
            current_level = [n.id for n in next_level[:max_per_hop]]

        return results


class ContextSynthesizer:
    """
    Synthesizes context for LLM consumption.

    Converts graph retrieval results into linearized, structured context.
    """

    def __init__(self, max_context_length: int = 4000):
        """
        Initialize context synthesizer.

        Args:
            max_context_length: Maximum context length in characters
        """
        self.max_context_length = max_context_length

    def synthesize(
        self,
        results: List[RetrievalResult],
        query: Optional[str] = None,
        include_metadata: bool = True
    ) -> str:
        """
        Synthesize context from retrieval results.

        Args:
            results: List of retrieval results
            query: Optional original query
            include_metadata: Whether to include metadata

        Returns:
            Linearized context string
        """
        parts = []

        if query:
            parts.append(f"Query: {query}\n")

        parts.append("Retrieved Context:\n")

        remaining_length = self.max_context_length - sum(len(p) for p in parts)

        for i, result in enumerate(results, start=1):
            # Format entry
            entry_parts = [f"\n[{i}] {result.content}"]

            if include_metadata and result.metadata:
                meta_str = self._format_metadata(result.metadata)
                if meta_str:
                    entry_parts.append(f"  ({meta_str})")

            entry = "".join(entry_parts)

            if len(entry) > remaining_length:
                # Truncate if too long
                entry = entry[:remaining_length - 3] + "..."
                parts.append(entry)
                break

            parts.append(entry)
            remaining_length -= len(entry)

        return "".join(parts)

    def synthesize_with_structure(
        self,
        results: List[RetrievalResult],
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesize context with structured output.

        Returns:
            Dict with structured context information
        """
        # Group by source
        by_source: Dict[str, List[RetrievalResult]] = {}
        for result in results:
            source = result.source
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(result)

        structured = {
            "query": query,
            "total_results": len(results),
            "sources": list(by_source.keys()),
            "by_source": {
                source: [
                    {
                        "id": r.id,
                        "content": r.content,
                        "score": r.score,
                        "rank": r.rank
                    }
                    for r in source_results
                ]
                for source, source_results in by_source.items()
            },
            "linearized": self.synthesize(results, query, include_metadata=False)
        }

        return structured

    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata for display."""
        important_keys = ["node_type", "trust_score", "genesis_key_id"]
        parts = []

        for key in important_keys:
            if key in metadata:
                value = metadata[key]
                if isinstance(value, float):
                    parts.append(f"{key}={value:.2f}")
                else:
                    parts.append(f"{key}={value}")

        return ", ".join(parts)


class ConsolidationWorker:
    """
    Background worker for graph consolidation.

    Performs periodic optimization tasks:
    - Prune low-weight edges
    - Merge similar nodes
    - Update importance scores
    - Clean stale data
    """

    def __init__(
        self,
        graphs: MagmaRelationGraphs,
        queue: AsyncOperationQueue,
        interval_seconds: int = 300  # 5 minutes
    ):
        """
        Initialize consolidation worker.

        Args:
            graphs: MagmaRelationGraphs instance
            queue: Operation queue
            interval_seconds: Consolidation interval
        """
        self.graphs = graphs
        self.queue = queue
        self.interval = interval_seconds
        self._running = False
        self._thread: Optional[threading.Thread] = None

        logger.info(f"[MAGMA-CONSOLIDATE] Worker initialized (interval={interval_seconds}s)")

    def start(self):
        """Start background consolidation."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

        logger.info("[MAGMA-CONSOLIDATE] Background worker started")

    def stop(self):
        """Stop background consolidation."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

        logger.info("[MAGMA-CONSOLIDATE] Background worker stopped")

    def _run(self):
        """Main worker loop."""
        while self._running:
            try:
                self._consolidate()
            except Exception as e:
                logger.error(f"[MAGMA-CONSOLIDATE] Error: {e}")

            # Sleep in small increments to allow quick shutdown
            for _ in range(self.interval):
                if not self._running:
                    break
                time.sleep(1)

    def _consolidate(self):
        """Perform consolidation tasks."""
        logger.debug("[MAGMA-CONSOLIDATE] Starting consolidation cycle")

        # Process pending operations from queue
        processed = 0
        while True:
            operation = self.queue.dequeue()
            if not operation:
                break

            try:
                result = self._process_operation(operation)
                self.queue.store_result(result)

                if operation.callback:
                    operation.callback(result)

                processed += 1

            except Exception as e:
                if operation.retries < operation.max_retries:
                    operation.retries += 1
                    self.queue.enqueue(
                        operation.operation_type,
                        operation.payload,
                        operation.priority,
                        operation.callback
                    )
                else:
                    self.queue.store_result(OperationResult(
                        operation_id=operation.id,
                        success=False,
                        result=None,
                        error=str(e)
                    ))

        if processed > 0:
            logger.info(f"[MAGMA-CONSOLIDATE] Processed {processed} operations")

        # Periodic graph maintenance
        self._prune_weak_edges()
        self._update_importance_scores()

    def _process_operation(self, operation: QueuedOperation) -> OperationResult:
        """Process a single operation based on its type."""
        try:
            op_type = operation.operation_type.value if hasattr(operation.operation_type, 'value') else str(operation.operation_type)

            if op_type == "ingest":
                content = operation.data.get("content", "")
                metadata = operation.data.get("metadata", {})
                if content and hasattr(self, 'graphs'):
                    for graph_name, graph in self.graphs.get_all_graphs().items():
                        try:
                            graph.add_node(content[:200], metadata=metadata)
                        except Exception:
                            pass
                return OperationResult(operation_id=operation.id, success=True,
                    result={"processed": True, "type": op_type, "content_length": len(content)})

            elif op_type == "query":
                query = operation.data.get("query", "")
                results = []
                if query and hasattr(self, 'graphs'):
                    for graph_name, graph in self.graphs.get_all_graphs().items():
                        try:
                            neighbors = graph.get_neighbors(query[:100])
                            results.extend(neighbors[:5])
                        except Exception:
                            pass
                return OperationResult(operation_id=operation.id, success=True,
                    result={"processed": True, "type": op_type, "results": len(results)})

            elif op_type == "link":
                source = operation.data.get("source", "")
                target = operation.data.get("target", "")
                relation = operation.data.get("relation", "related")
                if source and target and hasattr(self, 'graphs'):
                    try:
                        semantic = self.graphs.get_all_graphs().get("semantic")
                        if semantic:
                            semantic.add_edge(source, target, relation_type=relation)
                    except Exception:
                        pass
                return OperationResult(operation_id=operation.id, success=True,
                    result={"processed": True, "type": op_type})

            else:
                return OperationResult(operation_id=operation.id, success=True,
                    result={"processed": True, "type": op_type, "note": "passthrough"})

        except Exception as e:
            return OperationResult(operation_id=operation.id, success=False,
                result={"error": str(e)[:200], "type": str(operation.operation_type)})

    def _prune_weak_edges(self, threshold: float = 0.05):
        """Remove edges below weight threshold."""
        for graph_name, graph in self.graphs.get_all_graphs().items():
            weak_edges = [
                edge_id for edge_id, edge in graph.edges.items()
                if edge.weight < threshold
            ]

            for edge_id in weak_edges:
                edge = graph.edges.pop(edge_id, None)
                if edge:
                    graph.adjacency[edge.source_id].discard(edge_id)
                    graph.reverse_adjacency[edge.target_id].discard(edge_id)

            if weak_edges:
                logger.debug(f"[MAGMA-CONSOLIDATE] Pruned {len(weak_edges)} weak edges from {graph_name}")

    def _update_importance_scores(self):
        """Update node importance scores."""
        for graph_name, graph in self.graphs.get_all_graphs().items():
            for node_id in list(graph.nodes.keys()):
                importance = graph.calculate_node_importance(node_id)
                node = graph.nodes.get(node_id)
                if node:
                    node.metadata["importance"] = importance
