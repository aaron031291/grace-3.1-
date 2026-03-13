"""
Magma Memory System - Grace's Unified Memory Architecture

Advanced memory architecture that extends Grace's Memory Mesh with:
1. Relation Graphs (Semantic, Temporal, Causal, Entity)
2. Intent-Aware Router with Anchor Identification
3. RRF Fusion (Reciprocal Rank Fusion)
4. Adaptive Topological Retrieval
5. Synaptic Ingestion with Event Segmentation
6. Async Consolidation Pipeline
7. Neighbor Retrieval
8. LLM Causal Inference

Deep Integration with Grace Layers:
- Layer 1: Message Bus connector (event-driven memory)
- Layer 2: Interpreter pattern memory (recurring issues)
- Layer 3: Judgement decision memory (precedents)
- Layer 4: Action Router memory (learned procedures)

Security Integrations:
- Genesis Keys: Full provenance tracking
- Trust Scoring: Neural trust-aware retrieval
- Governance: Constitutional enforcement

RECOMMENDED: Use GraceMagmaSystem for the unified experience:

    from backend.cognitive.magma import get_grace_magma

    magma = get_grace_magma()

    # Ingest content (tracked, validated, linked)
    magma.ingest("Machine learning causes better predictions.")

    # Query with trust-aware retrieval
    results = magma.query("What causes better predictions?")

    # Get context for LLM
    context = magma.get_context("What causes better predictions?")

    # Causal inference
    causes = magma.why("Why did the prediction fail?")

    # Store/find patterns (Layer 2)
    magma.store_pattern("error_cluster", "Database timeout pattern")

    # Store/find decisions (Layer 3)
    magma.store_decision("heal", "database", "Reconnect database")

    # Store/find procedures (Layer 4)
    magma.store_procedure("heal", "Reconnect DB", ["Stop pool", "Restart"])

Alternative: Use MagmaMemory for low-level access:

    from backend.cognitive.magma import MagmaMemory

    magma = MagmaMemory()
    result = magma.ingest("Content here")
    results = magma.query("Query here")
"""

# Core relation graphs
from backend.cognitive.magma.relation_graphs import (
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
from backend.cognitive.magma.intent_router import (
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
from backend.cognitive.magma.rrf_fusion import (
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
from backend.cognitive.magma.topological_retrieval import (
    AdaptiveTopologicalRetriever,
    GraphTraverser,
    TraversalPolicy,
    TraversalConfig,
    TraversalResult
)

# Synaptic ingestion
from backend.cognitive.magma.synaptic_ingestion import (
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
from backend.cognitive.magma.async_consolidation import (
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
from backend.cognitive.magma.causal_inference import (
    LLMCausalInferencer,
    CausalPatternDetector,
    CausalClaim,
    CausalChain,
    CausalExplanation,
    CausalRelationStrength
)

# Unified Grace Magma System (RECOMMENDED)
from backend.cognitive.magma.grace_magma_system import (
    GraceMagmaSystem,
    GraceMagmaConfig,
    get_grace_magma,
    reset_grace_magma,
    ingest,
    query,
    get_context,
    why
)

# Layer integrations
from backend.cognitive.magma.layer_integrations import (
    MagmaMessageBusConnector,
    InterpreterPatternMemory,
    JudgementDecisionMemory,
    ActionRouterMemory,
    MagmaGenesisIntegration,
    MagmaTrustIntegration,
    MagmaGovernanceIntegration,
    create_magma_layer_integrations
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
    # UNIFIED SYSTEM (RECOMMENDED)
    "GraceMagmaSystem",
    "GraceMagmaConfig",
    "get_grace_magma",
    "reset_grace_magma",
    "ingest",
    "query",
    "get_context",
    "why",

    # Layer Integrations
    "MagmaMessageBusConnector",
    "InterpreterPatternMemory",
    "JudgementDecisionMemory",
    "ActionRouterMemory",
    "MagmaGenesisIntegration",
    "MagmaTrustIntegration",
    "MagmaGovernanceIntegration",
    "create_magma_layer_integrations",

    # Low-level interface
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
