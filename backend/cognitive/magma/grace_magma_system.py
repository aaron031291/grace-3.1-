"""
Grace Magma System - Unified Memory Architecture

This is the single unified entry point that integrates Magma Memory
with ALL Grace systems:

Core Memory:
- MagmaMemory: Graph-based memory with 4 relation types
- RRF Fusion: Multi-source retrieval fusion
- Causal Inference: LLM-powered cause-effect reasoning

Layer Integration:
- Layer 1: Message Bus connector (event-driven memory)
- Layer 2: Interpreter pattern memory (recurring issues)
- Layer 3: Judgement decision memory (precedents)
- Layer 4: Action Router memory (learned procedures)

Security Integration:
- Genesis Keys: Full provenance tracking
- Trust Scoring: Neural trust-aware retrieval
- Governance: Constitutional enforcement

Usage:
    from backend.cognitive.magma.grace_magma_system import GraceMagmaSystem, get_grace_magma

    # Get singleton instance
    magma = get_grace_magma()

    # Ingest content
    magma.ingest("Learning experience about Python error handling")

    # Query memory
    results = magma.query("How do I handle errors?")

    # Get context for LLM
    context = magma.get_context("What causes timeout errors?")

    # Causal inference
    causes = magma.why("What causes database connection failures?")

    # Store a pattern from Layer 2
    magma.store_pattern("error_cluster", "Database timeout pattern")

    # Store a decision from Layer 3
    magma.store_decision("heal", "database", "Reconnect database")

    # Store a procedure from Layer 4
    magma.store_procedure("heal", "Reconnect DB", ["Stop pool", "Restart"])
"""

from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import logging
import threading

logger = logging.getLogger(__name__)


@dataclass
class GraceMagmaConfig:
    """Configuration for Grace Magma System."""
    # Core memory settings
    embedding_dimension: int = 384
    max_context_length: int = 4000
    consolidation_interval_seconds: int = 300

    # Layer integration settings
    auto_connect_layers: bool = True
    auto_ingest_events: bool = True

    # Security settings
    enable_genesis_tracking: bool = True
    enable_trust_scoring: bool = True
    enable_governance: bool = True
    min_trust_threshold: float = 0.5

    # Performance settings
    max_workers: int = 4
    cache_size: int = 1000


class GraceMagmaSystem:
    """
    Unified Grace Magma Memory System.

    This is THE single entry point for all memory operations in Grace.
    It unifies:
    - Graph-based memory (semantic, temporal, causal, entity)
    - Layer 1-4 integrations
    - Security integrations (Genesis, Trust, Governance)
    """

    def __init__(
        self,
        config: Optional[GraceMagmaConfig] = None,
        embedding_fn: Optional[Callable[[str], List[float]]] = None,
        session = None  # Database session for persistence
    ):
        """
        Initialize the unified Grace Magma System.

        Args:
            config: Configuration options
            embedding_fn: Optional embedding function
            session: Database session
        """
        self.config = config or GraceMagmaConfig()
        self._session = session
        self._initialized = False
        self._lock = threading.Lock()

        # Core memory (lazy initialization)
        self._magma = None

        # Layer integrations
        self._layer1 = None  # Message Bus connector
        self._layer2 = None  # Pattern memory
        self._layer3 = None  # Decision memory
        self._layer4 = None  # Action memory

        # Security integrations
        self._genesis = None
        self._trust = None
        self._governance = None

        # Embedding function
        self._embedding_fn = embedding_fn

        logger.info("[GRACE-MAGMA] GraceMagmaSystem created (lazy initialization)")

    def initialize(self) -> bool:
        """
        Initialize all components.

        Call this explicitly or let it auto-initialize on first use.
        """
        with self._lock:
            if self._initialized:
                return True

            try:
                # 1. Initialize core Magma memory
                from backend.cognitive.magma import MagmaMemory
                self._magma = MagmaMemory(embedding_fn=self._embedding_fn)
                logger.info("[GRACE-MAGMA] Core MagmaMemory initialized")

                # 2. Initialize layer integrations
                from backend.cognitive.magma.layer_integrations import (
                    MagmaMessageBusConnector,
                    InterpreterPatternMemory,
                    JudgementDecisionMemory,
                    ActionRouterMemory,
                    MagmaGenesisIntegration,
                    MagmaTrustIntegration,
                    MagmaGovernanceIntegration
                )

                self._layer2 = InterpreterPatternMemory(self._magma)
                self._layer3 = JudgementDecisionMemory(self._magma)
                self._layer4 = ActionRouterMemory(self._magma)
                logger.info("[GRACE-MAGMA] Layer 2-4 integrations initialized")

                # 3. Initialize Layer 1 connector (connects to message bus)
                self._layer1 = MagmaMessageBusConnector(
                    self._magma,
                    auto_ingest=self.config.auto_ingest_events
                )
                if self.config.auto_connect_layers:
                    self._layer1.connect()
                logger.info("[GRACE-MAGMA] Layer 1 Message Bus connected")

                # 4. Initialize security integrations
                if self.config.enable_genesis_tracking:
                    self._genesis = MagmaGenesisIntegration(self._magma)
                    self._genesis.connect_genesis()

                if self.config.enable_trust_scoring:
                    self._trust = MagmaTrustIntegration(self._magma)
                    self._trust.connect_trust_scorer()

                if self.config.enable_governance:
                    self._governance = MagmaGovernanceIntegration(self._magma)
                    self._governance.connect_governance()

                logger.info("[GRACE-MAGMA] Security integrations initialized")

                self._initialized = True
                logger.info("[GRACE-MAGMA] ✓ System fully initialized")
                return True

            except Exception as e:
                logger.error(f"[GRACE-MAGMA] Initialization failed: {e}")
                return False

    def _ensure_initialized(self):
        """Ensure system is initialized before use."""
        if not self._initialized:
            self.initialize()

    # =========================================================================
    # CORE MEMORY OPERATIONS
    # =========================================================================

    def ingest(
        self,
        content: str,
        genesis_key_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ):
        """
        Ingest content into Magma memory.

        This is the primary write operation. Content is:
        - Segmented into meaningful units
        - Embedded into semantic space
        - Linked across all 4 graphs (semantic, temporal, causal, entity)
        - Tracked with Genesis Key
        - Validated by governance

        Args:
            content: Text content to ingest
            genesis_key_id: Optional existing Genesis Key
            metadata: Optional metadata
            user_id: Optional user ID for tracking

        Returns:
            IngestionResult with details
        """
        self._ensure_initialized()

        # Governance check
        if self._governance:
            allowed, reason = self._governance.check_ingestion_allowed(content, user_id)
            if not allowed:
                logger.warning(f"[GRACE-MAGMA] Ingestion blocked: {reason}")
                raise ValueError(f"Ingestion blocked by governance: {reason}")

        # Ingest into Magma
        result = self._magma.ingest(
            content,
            genesis_key_id=genesis_key_id,
            metadata=metadata
        )

        # Track with Genesis Key
        if self._genesis and not genesis_key_id:
            self._genesis.track_ingestion(content, result, user_id)

        return result

    def query(
        self,
        query: str,
        top_k: int = 10,
        min_trust: Optional[float] = None,
        user_id: Optional[str] = None
    ) -> List:
        """
        Query Magma memory.

        This is the primary read operation. Uses:
        - Intent-aware routing to select graphs
        - Multi-hop graph traversal
        - RRF fusion of results from all sources
        - Trust-based filtering (if enabled)

        Args:
            query: Search query
            top_k: Maximum results
            min_trust: Minimum trust score (uses config default if None)
            user_id: Optional user ID for tracking

        Returns:
            List of FusedResult objects
        """
        self._ensure_initialized()

        # Governance check
        if self._governance:
            allowed, reason = self._governance.check_query_allowed(query, user_id)
            if not allowed:
                logger.warning(f"[GRACE-MAGMA] Query blocked: {reason}")
                raise ValueError(f"Query blocked by governance: {reason}")

        # Use trust-aware retrieval if available
        if self._trust and self.config.enable_trust_scoring:
            trust_threshold = min_trust or self.config.min_trust_threshold
            results = self._trust.get_trusted_results(query, trust_threshold, top_k)
        else:
            results = self._magma.query(query, top_k=top_k)

        # Track with Genesis Key
        if self._genesis:
            self._genesis.track_query(query, results, user_id)

        return results

    def get_context(
        self,
        query: str,
        max_length: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Get linearized context for LLM consumption.

        Synthesizes retrieval results into a formatted context string
        suitable for adding to LLM prompts.

        Args:
            query: Query to retrieve context for
            max_length: Maximum context length in characters
            user_id: Optional user ID

        Returns:
            Formatted context string
        """
        self._ensure_initialized()

        max_len = max_length or self.config.max_context_length
        return self._magma.get_context(query, max_context_length=max_len)

    def why(
        self,
        query: str,
        user_id: Optional[str] = None
    ):
        """
        Answer "why" questions using causal inference.

        Combines:
        - Pattern-based causal detection
        - Causal graph traversal
        - LLM-powered causal reasoning

        Args:
            query: Causal question (e.g., "Why did X happen?")
            user_id: Optional user ID

        Returns:
            CausalInferenceResult with claims and chains
        """
        self._ensure_initialized()

        result = self._magma.infer_causation(query)

        # Track with Genesis Key
        if self._genesis:
            self._genesis.track_causal_inference(query, result, user_id)

        return result

    def explain(
        self,
        query: str,
        user_id: Optional[str] = None
    ) -> str:
        """
        Get human-readable explanation of causal relationships.

        Args:
            query: What to explain
            user_id: Optional user ID

        Returns:
            Natural language explanation
        """
        self._ensure_initialized()
        return self._magma.explain(query)

    # =========================================================================
    # LAYER 2: PATTERN MEMORY
    # =========================================================================

    def store_pattern(
        self,
        pattern_type: str,
        description: str,
        confidence: float = 0.7,
        affected_components: Optional[List[str]] = None,
        genesis_key_id: Optional[str] = None
    ) -> str:
        """
        Store a detected pattern (Layer 2 integration).

        Called by the Interpreter layer when patterns are detected.

        Args:
            pattern_type: Type of pattern
            description: Pattern description
            confidence: Detection confidence
            affected_components: List of affected components
            genesis_key_id: Optional Genesis Key

        Returns:
            Pattern ID
        """
        self._ensure_initialized()

        return self._layer2.store_pattern(
            pattern_type=pattern_type,
            description=description,
            confidence=confidence,
            affected_components=affected_components or [],
            evidence=[],
            genesis_key_id=genesis_key_id
        )

    def find_similar_patterns(
        self,
        description: str,
        pattern_type: Optional[str] = None,
        top_k: int = 5
    ) -> List:
        """
        Find similar patterns from memory.

        Args:
            description: Pattern to match
            pattern_type: Optional type filter
            top_k: Maximum results

        Returns:
            List of similar PatternMemoryEntry objects
        """
        self._ensure_initialized()

        return self._layer2.find_similar_patterns(
            description=description,
            pattern_type=pattern_type,
            top_k=top_k
        )

    # =========================================================================
    # LAYER 3: DECISION MEMORY
    # =========================================================================

    def store_decision(
        self,
        action: str,
        health_status: str,
        context: str,
        confidence: float = 0.7,
        risk_level: str = "medium",
        genesis_key_id: Optional[str] = None
    ) -> str:
        """
        Store a judgement decision (Layer 3 integration).

        Called by the Judgement layer when decisions are made.

        Args:
            action: Recommended action
            health_status: System health at time of decision
            context: Decision context
            confidence: Decision confidence
            risk_level: Risk level (low/medium/high/critical)
            genesis_key_id: Optional Genesis Key

        Returns:
            Decision ID
        """
        self._ensure_initialized()

        return self._layer3.store_decision(
            health_status=health_status,
            recommended_action=action,
            confidence=confidence,
            risk_level=risk_level,
            context_summary=context,
            genesis_key_id=genesis_key_id
        )

    def find_precedents(
        self,
        health_status: str,
        risk_level: str,
        context: str,
        top_k: int = 5
    ) -> List:
        """
        Find similar past decisions as precedents.

        Args:
            health_status: Current health
            risk_level: Current risk
            context: Current context
            top_k: Maximum results

        Returns:
            List of DecisionPrecedent objects
        """
        self._ensure_initialized()

        return self._layer3.find_precedents(
            health_status=health_status,
            risk_level=risk_level,
            context=context,
            top_k=top_k
        )

    def record_decision_outcome(
        self,
        decision_id: str,
        outcome: str,
        success: bool
    ) -> bool:
        """
        Record outcome of a past decision.

        Args:
            decision_id: Decision to update
            outcome: What happened
            success: Whether decision was successful

        Returns:
            True if updated
        """
        self._ensure_initialized()

        return self._layer3.record_outcome(decision_id, outcome, success)

    # =========================================================================
    # LAYER 4: ACTION MEMORY
    # =========================================================================

    def store_procedure(
        self,
        action_type: str,
        name: str,
        steps: List[str],
        target_components: Optional[List[str]] = None,
        success: bool = True,
        duration_ms: float = 0,
        genesis_key_id: Optional[str] = None
    ) -> str:
        """
        Store an executed procedure (Layer 4 integration).

        Called by the Action Router when procedures complete.

        Args:
            action_type: Type of action (heal, alert, etc.)
            name: Procedure name
            steps: List of steps taken
            target_components: Components affected
            success: Whether procedure succeeded
            duration_ms: Execution duration
            genesis_key_id: Optional Genesis Key

        Returns:
            Procedure ID
        """
        self._ensure_initialized()

        return self._layer4.store_procedure(
            action_type=action_type,
            name=name,
            description=f"Procedure: {name}",
            target_components=target_components or [],
            steps=steps,
            success=success,
            duration_ms=duration_ms,
            genesis_key_id=genesis_key_id
        )

    def find_procedures(
        self,
        action_type: str,
        target_component: Optional[str] = None,
        min_success_rate: float = 0.5,
        top_k: int = 5
    ) -> List:
        """
        Find relevant procedures for an action.

        Args:
            action_type: Type of action needed
            target_component: Optional component filter
            min_success_rate: Minimum success rate
            top_k: Maximum results

        Returns:
            List of ActionProcedure objects
        """
        self._ensure_initialized()

        return self._layer4.find_procedures(
            action_type=action_type,
            target_component=target_component,
            min_success_rate=min_success_rate,
            top_k=top_k
        )

    def get_best_procedure(
        self,
        action_type: str,
        target_component: str
    ):
        """
        Get the best procedure for an action.

        Returns the highest-success-rate procedure for the given
        action type and target component.

        Args:
            action_type: Action type
            target_component: Target component

        Returns:
            ActionProcedure or None
        """
        self._ensure_initialized()

        return self._layer4.get_best_procedure(action_type, target_component)

    # =========================================================================
    # GRAPH ACCESS
    # =========================================================================

    @property
    def graphs(self):
        """Access underlying graph structures."""
        self._ensure_initialized()
        return self._magma.graphs

    @property
    def semantic_graph(self):
        """Access semantic relation graph."""
        self._ensure_initialized()
        return self._magma.graphs.semantic

    @property
    def temporal_graph(self):
        """Access temporal relation graph."""
        self._ensure_initialized()
        return self._magma.graphs.temporal

    @property
    def causal_graph(self):
        """Access causal relation graph."""
        self._ensure_initialized()
        return self._magma.graphs.causal

    @property
    def entity_graph(self):
        """Access entity relation graph."""
        self._ensure_initialized()
        return self._magma.graphs.entity

    # =========================================================================
    # STATISTICS & HEALTH
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive system statistics.

        Returns:
            Dict with stats from all components
        """
        self._ensure_initialized()

        graph_stats = {}
        for name, graph in self._magma.graphs.get_all_graphs().items():
            graph_stats[name] = {
                "nodes": len(graph.nodes),
                "edges": len(graph.edges)
            }

        return {
            "initialized": self._initialized,
            "graphs": graph_stats,
            "patterns_stored": len(self._layer2._pattern_cache) if self._layer2 else 0,
            "decisions_stored": len(self._layer3._decision_cache) if self._layer3 else 0,
            "procedures_stored": len(self._layer4._procedure_cache) if self._layer4 else 0,
            "security": {
                "genesis_enabled": self._genesis is not None,
                "trust_enabled": self._trust is not None,
                "governance_enabled": self._governance is not None
            }
        }

    def health_check(self) -> Tuple[bool, str]:
        """
        Check system health.

        Returns:
            (healthy, message)
        """
        if not self._initialized:
            return (False, "System not initialized")

        try:
            # Test basic query
            self._magma.query("health check", top_k=1)
            return (True, "System healthy")
        except Exception as e:
            return (False, f"Health check failed: {e}")

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    def shutdown(self):
        """Gracefully shut down the system."""
        logger.info("[GRACE-MAGMA] Shutting down...")

        # Stop consolidation worker
        if self._magma and hasattr(self._magma, 'consolidation'):
            if self._magma.consolidation:
                self._magma.consolidation.stop()

        self._initialized = False
        logger.info("[GRACE-MAGMA] Shutdown complete")


# =============================================================================
# SINGLETON ACCESS
# =============================================================================

_grace_magma_instance: Optional[GraceMagmaSystem] = None
_instance_lock = threading.Lock()


def get_grace_magma(
    config: Optional[GraceMagmaConfig] = None,
    force_new: bool = False
) -> GraceMagmaSystem:
    """
    Get the singleton GraceMagmaSystem instance.

    Args:
        config: Optional configuration (only used for new instance)
        force_new: Force create a new instance

    Returns:
        GraceMagmaSystem instance
    """
    global _grace_magma_instance

    with _instance_lock:
        if force_new or _grace_magma_instance is None:
            _grace_magma_instance = GraceMagmaSystem(config)

        return _grace_magma_instance


def reset_grace_magma():
    """Reset the singleton (mainly for testing)."""
    global _grace_magma_instance

    with _instance_lock:
        if _grace_magma_instance:
            _grace_magma_instance.shutdown()
        _grace_magma_instance = None


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def ingest(content: str, **kwargs):
    """Quick ingest into Grace Magma."""
    return get_grace_magma().ingest(content, **kwargs)


def query(query_text: str, **kwargs) -> List:
    """Quick query from Grace Magma."""
    return get_grace_magma().query(query_text, **kwargs)


def get_context(query_text: str, **kwargs) -> str:
    """Quick context retrieval from Grace Magma."""
    return get_grace_magma().get_context(query_text, **kwargs)


def why(question: str, **kwargs):
    """Quick causal inference from Grace Magma."""
    return get_grace_magma().why(question, **kwargs)
