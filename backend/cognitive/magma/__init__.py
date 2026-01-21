"""
Magma Memory System

Advanced memory architecture that extends Grace's Memory Mesh with:
1. Relation Graphs (Semantic, Temporal, Causal, Entity)
2. Intent-Aware Router with Anchor Identification
3. RRF Fusion (Reciprocal Rank Fusion)
4. Adaptive Topological Retrieval
5. Synaptic Ingestion with Event Segmentation
6. Async Consolidation Pipeline
7. Neighbor Retrieval
8. LLM Causal Inference

Hybrid of existing Memory Mesh + Graph-based memory architecture.

Usage:
    from cognitive.magma import MagmaMemory

    magma = MagmaMemory()

    # Ingest content
    result = magma.ingest("Machine learning causes better predictions.")

    # Query
    results = magma.query("What causes better predictions?")

    # Get context for LLM
    context = magma.get_context(results)
"""

# Core relation graphs
from cognitive.magma.relation_graphs import (
    MagmaRelationGraphs,
    SemanticGraph,
    TemporalGraph,
    CausalGraph,
    EntityGraph,
    GraphNode,
    GraphEdge,
    RelationType,
    BaseRelationGraph
)

# Intent-aware routing
from cognitive.magma.intent_router import (
    IntentAwareRouter,
    QueryIntent,
    AnchorType,
    Anchor,
    QueryAnalysis,
    IntentClassifier,
    AnchorIdentifier,
    GraphSelector,
    RetrievalPolicySelector
)

# RRF Fusion
from cognitive.magma.rrf_fusion import (
    MagmaFusion,
    RRFFusion,
    WeightedRRFFusion,
    CombSUMFusion,
    CombMNZFusion,
    InterleavingFusion,
    RetrievalResult,
    FusedResult,
    FusionMethod
)

# Topological retrieval
from cognitive.magma.topological_retrieval import (
    AdaptiveTopologicalRetriever,
    GraphTraverser,
    TraversalPolicy,
    TraversalConfig,
    TraversalResult
)

# Synaptic ingestion
from cognitive.magma.synaptic_ingestion import (
    SynapticIngestionPipeline,
    EventSegmenter,
    SemanticLinker,
    TemporalLinker,
    EntityLinker,
    CausalLinker,
    Segment,
    SegmentType,
    IngestionResult
)

# Async consolidation
from cognitive.magma.async_consolidation import (
    AsyncOperationQueue,
    NeighborRetriever,
    ContextSynthesizer,
    ConsolidationWorker,
    QueuedOperation,
    OperationType,
    OperationPriority,
    OperationResult
)

# Causal inference
from cognitive.magma.causal_inference import (
    LLMCausalInferencer,
    CausalPatternDetector,
    CausalClaim,
    CausalChain,
    CausalExplanation,
    CausalRelationStrength
)


class MagmaMemory:
    """
    Unified Magma Memory interface.

    Combines all Magma components into a single, easy-to-use API.
    """

    def __init__(self, embedding_fn=None, llm_fn=None):
        """
        Initialize Magma Memory.

        Args:
            embedding_fn: Optional embedding function (text -> vector)
            llm_fn: Optional LLM function (prompt -> response)
        """
        # Initialize core graphs
        self.graphs = MagmaRelationGraphs()

        # Initialize components
        self.router = IntentAwareRouter()
        self.fusion = MagmaFusion()
        self.retriever = AdaptiveTopologicalRetriever(self.graphs)
        self.ingestion = SynapticIngestionPipeline(self.graphs, embedding_fn=embedding_fn)
        self.queue = AsyncOperationQueue()
        self.neighbor_retriever = NeighborRetriever(self.graphs)
        self.context_synthesizer = ContextSynthesizer()
        self.causal_inferencer = LLMCausalInferencer(self.graphs, llm_fn=llm_fn)

        # Background worker (not started by default)
        self.consolidation_worker = ConsolidationWorker(self.graphs, self.queue)

    def ingest(self, content: str, genesis_key_id: str = None, **kwargs):
        """
        Ingest content into Magma memory.

        Args:
            content: Content to ingest
            genesis_key_id: Optional Genesis Key for tracking
            **kwargs: Additional metadata

        Returns:
            IngestionResult
        """
        return self.ingestion.ingest(content, genesis_key_id=genesis_key_id, metadata=kwargs)

    def query(self, query: str, limit: int = 10):
        """
        Query Magma memory.

        Args:
            query: Query string
            limit: Maximum results

        Returns:
            List of RetrievalResult
        """
        # Analyze query
        analysis = self.router.analyze_query(query)

        # Retrieve from graphs
        results = self.retriever.retrieve(analysis)

        return results[:limit]

    def get_context(self, results, query: str = None):
        """
        Generate context for LLM consumption.

        Args:
            results: List of RetrievalResult
            query: Optional original query

        Returns:
            Linearized context string
        """
        return self.context_synthesizer.synthesize(results, query)

    def infer_causation(self, text: str):
        """
        Infer causal relationships from text.

        Args:
            text: Text to analyze

        Returns:
            List of CausalClaim
        """
        return self.causal_inferencer.infer_causation(text)

    def explain(self, cause: str, effect: str):
        """
        Explain causal relationship.

        Args:
            cause: Cause concept
            effect: Effect concept

        Returns:
            CausalExplanation
        """
        return self.causal_inferencer.explain_causation(cause, effect)

    def get_stats(self):
        """Get Magma memory statistics."""
        return {
            "graphs": self.graphs.get_unified_stats(),
            "queue": self.queue.get_queue_sizes()
        }

    def start_background_processing(self):
        """Start background consolidation worker."""
        self.consolidation_worker.start()

    def stop_background_processing(self):
        """Stop background consolidation worker."""
        self.consolidation_worker.stop()


__all__ = [
    # Main interface
    "MagmaMemory",

    # Relation Graphs
    "MagmaRelationGraphs",
    "SemanticGraph",
    "TemporalGraph",
    "CausalGraph",
    "EntityGraph",
    "GraphNode",
    "GraphEdge",
    "RelationType",
    "BaseRelationGraph",

    # Intent Router
    "IntentAwareRouter",
    "QueryIntent",
    "AnchorType",
    "Anchor",
    "QueryAnalysis",
    "IntentClassifier",
    "AnchorIdentifier",
    "GraphSelector",
    "RetrievalPolicySelector",

    # RRF Fusion
    "MagmaFusion",
    "RRFFusion",
    "WeightedRRFFusion",
    "CombSUMFusion",
    "CombMNZFusion",
    "InterleavingFusion",
    "RetrievalResult",
    "FusedResult",
    "FusionMethod",

    # Topological Retrieval
    "AdaptiveTopologicalRetriever",
    "GraphTraverser",
    "TraversalPolicy",
    "TraversalConfig",
    "TraversalResult",

    # Synaptic Ingestion
    "SynapticIngestionPipeline",
    "EventSegmenter",
    "SemanticLinker",
    "TemporalLinker",
    "EntityLinker",
    "CausalLinker",
    "Segment",
    "SegmentType",
    "IngestionResult",

    # Async Consolidation
    "AsyncOperationQueue",
    "NeighborRetriever",
    "ContextSynthesizer",
    "ConsolidationWorker",
    "QueuedOperation",
    "OperationType",
    "OperationPriority",
    "OperationResult",

    # Causal Inference
    "LLMCausalInferencer",
    "CausalPatternDetector",
    "CausalClaim",
    "CausalChain",
    "CausalExplanation",
    "CausalRelationStrength",
]
