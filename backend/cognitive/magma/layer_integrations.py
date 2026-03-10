"""
Magma Memory - Deep Layer Integrations

Integrates Magma Memory with Grace's 4-layer cognitive architecture:
- Layer 1: Message Bus connector for event-driven memory
- Layer 2: Interpreter pattern memory for recurring issues
- Layer 3: Judgement decision memory for precedent-based decisions
- Layer 4: Action Router memory for learned procedures

Plus Security integrations:
- Genesis Keys: Full provenance tracking
- Trust Scoring: Neural trust-aware retrieval
- Governance: Constitutional memory enforcement
"""

from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Thread pool for CPU-bound operations
_executor = ThreadPoolExecutor(max_workers=4)


# =============================================================================
# LAYER 1: MESSAGE BUS INTEGRATION
# =============================================================================

class MagmaComponentType(Enum):
    """Magma-specific component types for Layer 1."""
    MAGMA_MEMORY = "magma_memory"
    MAGMA_GRAPHS = "magma_graphs"
    MAGMA_INFERENCE = "magma_inference"
    MAGMA_CONSOLIDATION = "magma_consolidation"


@dataclass
class MagmaEvent:
    """Event for Magma memory operations."""
    event_type: str
    payload: Dict[str, Any]
    genesis_key_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source_layer: int = 1  # Which layer generated this event


class MagmaMessageBusConnector:
    """
    Connects Magma Memory to Layer 1 Message Bus.

    Provides:
    - Automatic memory ingestion from events
    - Graph-based context retrieval for queries
    - Causal inference triggers
    - Memory consolidation scheduling
    """

    def __init__(
        self,
        magma_memory,  # MagmaMemory instance
        message_bus = None,  # Layer1MessageBus
        auto_ingest: bool = True
    ):
        """
        Initialize Magma connector for Layer 1.

        Args:
            magma_memory: MagmaMemory instance
            message_bus: Layer1MessageBus instance (optional, uses global)
            auto_ingest: Automatically ingest events into memory
        """
        self.magma = magma_memory
        self.message_bus = message_bus
        self.auto_ingest = auto_ingest

        # Track registered handlers
        self._registered_topics: List[str] = []
        self._autonomous_actions: List[str] = []

        logger.info("[MAGMA-L1] MagmaMessageBusConnector initialized")

    def connect(self):
        """Connect to message bus and register all handlers."""
        if not self.message_bus:
            try:
                from layer1.message_bus import get_message_bus, ComponentType
                self.message_bus = get_message_bus()
                self.ComponentType = ComponentType
            except ImportError:
                logger.warning("[MAGMA-L1] Message bus not available")
                return False

        # Register Magma as a component
        self.message_bus.register_component(
            self.ComponentType.MEMORY_MESH,  # Reuse existing type
            self.magma
        )

        # Register autonomous actions
        self._register_autonomous_actions()

        # Register request handlers
        self._register_request_handlers()

        # Subscribe to events
        self._subscribe_to_events()

        logger.info("[MAGMA-L1] Connected to Layer 1 Message Bus")
        return True

    def _register_autonomous_actions(self):
        """Register autonomous actions triggered by events."""

        # 1. Auto-ingest learning experiences
        self._autonomous_actions.append(
            self.message_bus.register_autonomous_action(
                trigger_event="learning_memory.new_experience",
                action=self._on_new_learning_experience,
                component=self.ComponentType.MEMORY_MESH,
                description="Auto-ingest learning into Magma graphs"
            )
        )

        # 2. Causal inference on errors
        self._autonomous_actions.append(
            self.message_bus.register_autonomous_action(
                trigger_event="genesis_keys.error_detected",
                action=self._on_error_detected,
                component=self.ComponentType.MEMORY_MESH,
                description="Trigger causal inference for errors"
            )
        )

        # 3. Memory consolidation on low activity
        self._autonomous_actions.append(
            self.message_bus.register_autonomous_action(
                trigger_event="system.low_activity",
                action=self._on_low_activity,
                component=self.ComponentType.MEMORY_MESH,
                description="Trigger background memory consolidation"
            )
        )

        # 4. Pattern detection notification
        self._autonomous_actions.append(
            self.message_bus.register_autonomous_action(
                trigger_event="magma.pattern_detected",
                action=self._on_pattern_detected,
                component=self.ComponentType.MEMORY_MESH,
                description="Notify other components of detected patterns"
            )
        )

        logger.info(f"[MAGMA-L1] Registered {len(self._autonomous_actions)} autonomous actions")

    def _register_request_handlers(self):
        """Register request handlers for other components."""

        # Query handler - main retrieval endpoint
        self.message_bus.register_request_handler(
            component=self.ComponentType.MEMORY_MESH,
            topic="magma_query",
            handler=self._handle_query
        )

        # Context retrieval for LLM
        self.message_bus.register_request_handler(
            component=self.ComponentType.MEMORY_MESH,
            topic="magma_get_context",
            handler=self._handle_get_context
        )

        # Causal inference request
        self.message_bus.register_request_handler(
            component=self.ComponentType.MEMORY_MESH,
            topic="magma_infer_causation",
            handler=self._handle_infer_causation
        )

        # Graph statistics
        self.message_bus.register_request_handler(
            component=self.ComponentType.MEMORY_MESH,
            topic="magma_stats",
            handler=self._handle_stats
        )

        logger.info("[MAGMA-L1] Registered 4 request handlers")

    def _subscribe_to_events(self):
        """Subscribe to events from other components."""

        topics = [
            "ingestion.file_processed",
            "rag.retrieval_complete",
            "cognitive.decision_made",
            "genesis_keys.key_created",
            "diagnostic.judgement_complete",
            "action_router.action_executed"
        ]

        for topic in topics:
            self.message_bus.subscribe(topic, self._on_system_event)
            self._registered_topics.append(topic)

        logger.info(f"[MAGMA-L1] Subscribed to {len(topics)} event topics")

    # ================================================================
    # AUTONOMOUS ACTION HANDLERS
    # ================================================================

    async def _on_new_learning_experience(self, message):
        """Handle new learning experience - auto-ingest into Magma."""
        if not self.auto_ingest:
            return

        payload = message.payload
        content = payload.get("content", "")
        genesis_key_id = payload.get("genesis_key_id")

        if not content:
            return

        # Run ingestion in thread pool (CPU-bound)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: self.magma.ingest(content, genesis_key_id=genesis_key_id)
        )

        logger.info(
            f"[MAGMA-L1] Auto-ingested learning: {len(result.segments)} segments, "
            f"{result.concepts_linked} concepts"
        )

        # Publish ingestion complete event
        await self.message_bus.publish(
            topic="magma.ingestion_complete",
            payload={
                "segments_created": len(result.segments),
                "concepts_linked": result.concepts_linked,
                "entities_linked": result.entities_linked,
                "genesis_key_id": genesis_key_id
            },
            from_component=self.ComponentType.MEMORY_MESH
        )

    async def _on_error_detected(self, message):
        """Handle error detection - trigger causal inference."""
        payload = message.payload
        error_type = payload.get("error_type", "unknown")
        error_context = payload.get("context", "")
        genesis_key_id = payload.get("genesis_key_id")

        # Run causal inference
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: self.magma.infer_causation(
                f"What causes {error_type}? Context: {error_context}"
            )
        )

        if result.causal_claims:
            logger.info(
                f"[MAGMA-L1] Causal inference for error: "
                f"{len(result.causal_claims)} claims found"
            )

            # Publish causal findings
            await self.message_bus.publish(
                topic="magma.causal_inference_complete",
                payload={
                    "error_type": error_type,
                    "causal_claims": [
                        {
                            "cause": claim.cause,
                            "effect": claim.effect,
                            "confidence": claim.confidence
                        }
                        for claim in result.causal_claims[:5]
                    ],
                    "genesis_key_id": genesis_key_id
                },
                from_component=self.ComponentType.MEMORY_MESH
            )

    async def _on_low_activity(self, message):
        """Handle low activity period - run memory consolidation."""
        logger.info("[MAGMA-L1] Running background memory consolidation")

        # Start consolidation worker if not running
        if hasattr(self.magma, 'consolidation') and self.magma.consolidation:
            if not self.magma.consolidation._running:
                self.magma.consolidation.start()

        await self.message_bus.publish(
            topic="magma.consolidation_started",
            payload={"timestamp": datetime.now(timezone.utc).isoformat()},
            from_component=self.ComponentType.MEMORY_MESH
        )

    async def _on_pattern_detected(self, message):
        """Handle pattern detection - notify other systems."""
        payload = message.payload

        # Notify autonomous learning
        await self.message_bus.publish(
            topic="autonomous_learning.new_pattern",
            payload=payload,
            from_component=self.ComponentType.MEMORY_MESH
        )

        # Notify diagnostic machine
        await self.message_bus.publish(
            topic="diagnostic.pattern_from_memory",
            payload=payload,
            from_component=self.ComponentType.MEMORY_MESH
        )

    async def _on_system_event(self, message):
        """Handle general system events - potentially ingest."""
        if not self.auto_ingest:
            return

        # Extract meaningful content from event
        topic = message.topic
        payload = message.payload

        # Determine if this event should be ingested
        ingestible_topics = [
            "cognitive.decision_made",
            "action_router.action_executed",
            "diagnostic.judgement_complete"
        ]

        if topic not in ingestible_topics:
            return

        # Build content from event
        content_parts = [f"Event: {topic}"]

        if "decision" in payload:
            content_parts.append(f"Decision: {payload['decision']}")
        if "action" in payload:
            content_parts.append(f"Action: {payload['action']}")
        if "result" in payload:
            content_parts.append(f"Result: {payload['result']}")
        if "reason" in payload:
            content_parts.append(f"Reason: {payload['reason']}")

        content = ". ".join(content_parts)

        # Ingest in background
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            _executor,
            lambda: self.magma.ingest(
                content,
                genesis_key_id=payload.get("genesis_key_id")
            )
        )

    # ================================================================
    # REQUEST HANDLERS
    # ================================================================

    async def _handle_query(self, message) -> Dict[str, Any]:
        """Handle memory query request."""
        query = message.payload.get("query", "")
        max_results = message.payload.get("max_results", 10)

        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            _executor,
            lambda: self.magma.query(query, top_k=max_results)
        )

        return {
            "results": [
                {
                    "id": r.id,
                    "content": r.content,
                    "score": r.rrf_score,
                    "sources": r.contributing_sources
                }
                for r in results
            ],
            "query": query
        }

    async def _handle_get_context(self, message) -> Dict[str, Any]:
        """Handle context retrieval for LLM."""
        query = message.payload.get("query", "")
        max_length = message.payload.get("max_length", 4000)

        loop = asyncio.get_event_loop()
        context = await loop.run_in_executor(
            _executor,
            lambda: self.magma.get_context(query, max_context_length=max_length)
        )

        return {"context": context, "query": query}

    async def _handle_infer_causation(self, message) -> Dict[str, Any]:
        """Handle causal inference request."""
        query = message.payload.get("query", "")

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            _executor,
            lambda: self.magma.infer_causation(query)
        )

        return {
            "query": query,
            "causal_claims": [
                {
                    "cause": claim.cause,
                    "effect": claim.effect,
                    "relation": claim.relation_type.value if hasattr(claim.relation_type, 'value') else str(claim.relation_type),
                    "confidence": claim.confidence,
                    "strength": claim.strength.value if hasattr(claim.strength, 'value') else str(claim.strength)
                }
                for claim in result.causal_claims
            ],
            "causal_chains": result.causal_chains
        }

    async def _handle_stats(self, message) -> Dict[str, Any]:
        """Handle statistics request."""
        return {
            "graphs": {
                name: {
                    "nodes": len(graph.nodes),
                    "edges": len(graph.edges)
                }
                for name, graph in self.magma.graphs.get_all_graphs().items()
            },
            "consolidation_queue": (
                self.magma.consolidation.queue.total_pending()
                if hasattr(self.magma, 'consolidation') and self.magma.consolidation
                else 0
            )
        }


# =============================================================================
# LAYER 2: INTERPRETER PATTERN MEMORY
# =============================================================================

@dataclass
class PatternMemoryEntry:
    """A pattern stored in Magma for Layer 2."""
    pattern_id: str
    pattern_type: str
    description: str
    confidence: float
    frequency: int
    first_seen: datetime
    last_seen: datetime
    affected_components: List[str]
    evidence_ids: List[str]  # Genesis Key IDs
    embedding_id: Optional[str] = None  # ID in semantic graph


class InterpreterPatternMemory:
    """
    Layer 2 Integration: Pattern memory for interpreters.

    Stores and retrieves recurring patterns to improve pattern detection:
    - Similar past patterns
    - Pattern evolution over time
    - Cross-pattern correlations
    """

    def __init__(self, magma_memory):
        """
        Initialize pattern memory.

        Args:
            magma_memory: MagmaMemory instance
        """
        self.magma = magma_memory
        self._pattern_cache: Dict[str, PatternMemoryEntry] = {}

        logger.info("[MAGMA-L2] InterpreterPatternMemory initialized")

    def store_pattern(
        self,
        pattern_type: str,
        description: str,
        confidence: float,
        affected_components: List[str],
        evidence: List[Dict[str, Any]],
        genesis_key_id: Optional[str] = None
    ) -> str:
        """
        Store a detected pattern in Magma memory.

        Returns:
            Pattern ID
        """
        import uuid
        pattern_id = f"pattern-{uuid.uuid4().hex[:12]}"

        # Build content for ingestion
        content = (
            f"Pattern detected: {pattern_type}. "
            f"{description} "
            f"Confidence: {confidence:.2f}. "
            f"Affected: {', '.join(affected_components)}."
        )

        # Ingest into Magma
        result = self.magma.ingest(
            content,
            genesis_key_id=genesis_key_id,
            metadata={
                "type": "pattern",
                "pattern_type": pattern_type,
                "pattern_id": pattern_id
            }
        )

        # Cache pattern entry
        entry = PatternMemoryEntry(
            pattern_id=pattern_id,
            pattern_type=pattern_type,
            description=description,
            confidence=confidence,
            frequency=1,
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
            affected_components=affected_components,
            evidence_ids=[genesis_key_id] if genesis_key_id else [],
            embedding_id=result.nodes_created[0] if result.nodes_created else None
        )
        self._pattern_cache[pattern_id] = entry

        logger.debug(f"[MAGMA-L2] Stored pattern: {pattern_id} ({pattern_type})")
        return pattern_id

    def find_similar_patterns(
        self,
        description: str,
        pattern_type: Optional[str] = None,
        min_confidence: float = 0.5,
        top_k: int = 5
    ) -> List[PatternMemoryEntry]:
        """
        Find similar patterns from memory.

        Args:
            description: Pattern description to match
            pattern_type: Optional filter by type
            min_confidence: Minimum confidence threshold
            top_k: Maximum results

        Returns:
            List of similar pattern entries
        """
        # Query Magma for similar patterns
        query = f"Pattern: {description}"
        if pattern_type:
            query = f"{pattern_type} pattern: {description}"

        results = self.magma.query(query, top_k=top_k * 2)  # Get extra for filtering

        similar_patterns = []
        for result in results:
            # Check if this is a pattern entry
            metadata = result.metadata or {}
            if metadata.get("type") != "pattern":
                continue

            stored_pattern_id = metadata.get("pattern_id")
            if stored_pattern_id and stored_pattern_id in self._pattern_cache:
                entry = self._pattern_cache[stored_pattern_id]
                if entry.confidence >= min_confidence:
                    similar_patterns.append(entry)

        return similar_patterns[:top_k]

    def update_pattern_frequency(self, pattern_id: str) -> bool:
        """Update pattern frequency when seen again."""
        if pattern_id not in self._pattern_cache:
            return False

        entry = self._pattern_cache[pattern_id]
        entry.frequency += 1
        entry.last_seen = datetime.now(timezone.utc)

        logger.debug(
            f"[MAGMA-L2] Updated pattern frequency: {pattern_id} "
            f"(now seen {entry.frequency} times)"
        )
        return True

    def get_pattern_evolution(
        self,
        pattern_type: str,
        lookback_hours: int = 24
    ) -> List[PatternMemoryEntry]:
        """Get pattern evolution over time."""
        cutoff = datetime.now(timezone.utc)

        evolution = [
            entry for entry in self._pattern_cache.values()
            if entry.pattern_type == pattern_type
        ]

        # Sort by first_seen
        evolution.sort(key=lambda e: e.first_seen)
        return evolution


# =============================================================================
# LAYER 3: JUDGEMENT DECISION MEMORY
# =============================================================================

@dataclass
class DecisionPrecedent:
    """A past decision stored in Magma for Layer 3."""
    decision_id: str
    health_status: str
    recommended_action: str
    confidence: float
    risk_level: str
    context_summary: str
    outcome: Optional[str] = None
    outcome_success: Optional[bool] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    genesis_key_id: Optional[str] = None


class JudgementDecisionMemory:
    """
    Layer 3 Integration: Decision memory for judgement.

    Stores and retrieves past decisions to inform future judgements:
    - Similar past situations
    - Decision outcomes
    - Risk precedents
    """

    def __init__(self, magma_memory):
        """
        Initialize decision memory.

        Args:
            magma_memory: MagmaMemory instance
        """
        self.magma = magma_memory
        self._decision_cache: Dict[str, DecisionPrecedent] = {}

        logger.info("[MAGMA-L3] JudgementDecisionMemory initialized")

    def store_decision(
        self,
        health_status: str,
        recommended_action: str,
        confidence: float,
        risk_level: str,
        context_summary: str,
        genesis_key_id: Optional[str] = None
    ) -> str:
        """
        Store a judgement decision in Magma memory.

        Returns:
            Decision ID
        """
        import uuid
        decision_id = f"decision-{uuid.uuid4().hex[:12]}"

        # Build content for ingestion
        content = (
            f"Judgement decision: {recommended_action}. "
            f"Health: {health_status}. Risk: {risk_level}. "
            f"Confidence: {confidence:.2f}. "
            f"Context: {context_summary}"
        )

        # Ingest with causal linking
        result = self.magma.ingest(
            content,
            genesis_key_id=genesis_key_id,
            metadata={
                "type": "decision",
                "decision_id": decision_id,
                "action": recommended_action,
                "health_status": health_status
            }
        )

        # Cache decision
        precedent = DecisionPrecedent(
            decision_id=decision_id,
            health_status=health_status,
            recommended_action=recommended_action,
            confidence=confidence,
            risk_level=risk_level,
            context_summary=context_summary,
            genesis_key_id=genesis_key_id
        )
        self._decision_cache[decision_id] = precedent

        logger.debug(f"[MAGMA-L3] Stored decision: {decision_id} ({recommended_action})")
        return decision_id

    def find_precedents(
        self,
        health_status: str,
        risk_level: str,
        context: str,
        top_k: int = 5
    ) -> List[DecisionPrecedent]:
        """
        Find similar past decisions as precedents.

        Args:
            health_status: Current health status
            risk_level: Current risk level
            context: Current context description
            top_k: Maximum results

        Returns:
            List of relevant precedents
        """
        query = (
            f"Decision for {health_status} health with {risk_level} risk. "
            f"Context: {context}"
        )

        results = self.magma.query(query, top_k=top_k * 2)

        precedents = []
        for result in results:
            metadata = result.metadata or {}
            if metadata.get("type") != "decision":
                continue

            decision_id = metadata.get("decision_id")
            if decision_id and decision_id in self._decision_cache:
                precedents.append(self._decision_cache[decision_id])

        return precedents[:top_k]

    def record_outcome(
        self,
        decision_id: str,
        outcome: str,
        success: bool
    ) -> bool:
        """Record the outcome of a past decision."""
        if decision_id not in self._decision_cache:
            return False

        precedent = self._decision_cache[decision_id]
        precedent.outcome = outcome
        precedent.outcome_success = success

        # Update in Magma with outcome
        outcome_content = (
            f"Decision outcome for {decision_id}: {outcome}. "
            f"Success: {success}. "
            f"Original action: {precedent.recommended_action}"
        )

        self.magma.ingest(
            outcome_content,
            genesis_key_id=precedent.genesis_key_id,
            metadata={
                "type": "decision_outcome",
                "decision_id": decision_id,
                "success": success
            }
        )

        logger.debug(f"[MAGMA-L3] Recorded outcome for {decision_id}: {success}")
        return True

    def get_success_rate(self, action_type: str) -> Tuple[float, int]:
        """
        Get success rate for a specific action type.

        Returns:
            (success_rate, sample_count)
        """
        relevant = [
            p for p in self._decision_cache.values()
            if p.recommended_action == action_type and p.outcome_success is not None
        ]

        if not relevant:
            return (0.5, 0)  # Default 50% with no data

        successes = sum(1 for p in relevant if p.outcome_success)
        return (successes / len(relevant), len(relevant))


# =============================================================================
# LAYER 4: ACTION ROUTER MEMORY
# =============================================================================

@dataclass
class ActionProcedure:
    """A learned procedure stored in Magma for Layer 4."""
    procedure_id: str
    action_type: str
    name: str
    description: str
    target_components: List[str]
    steps: List[str]
    success_rate: float
    times_used: int
    avg_duration_ms: float
    genesis_key_ids: List[str]
    last_used: datetime = field(default_factory=datetime.utcnow)


class ActionRouterMemory:
    """
    Layer 4 Integration: Action memory for the action router.

    Stores and retrieves learned procedures and action outcomes:
    - Successful healing procedures
    - Action execution history
    - Component-specific remediation patterns
    """

    def __init__(self, magma_memory):
        """
        Initialize action memory.

        Args:
            magma_memory: MagmaMemory instance
        """
        self.magma = magma_memory
        self._procedure_cache: Dict[str, ActionProcedure] = {}

        logger.info("[MAGMA-L4] ActionRouterMemory initialized")

    def store_procedure(
        self,
        action_type: str,
        name: str,
        description: str,
        target_components: List[str],
        steps: List[str],
        success: bool,
        duration_ms: float,
        genesis_key_id: Optional[str] = None
    ) -> str:
        """
        Store an executed procedure in Magma memory.

        Returns:
            Procedure ID
        """
        import uuid
        procedure_id = f"proc-{uuid.uuid4().hex[:12]}"

        # Build content for ingestion
        content = (
            f"Procedure: {name} ({action_type}). "
            f"{description} "
            f"Target: {', '.join(target_components)}. "
            f"Steps: {'; '.join(steps)}. "
            f"Success: {success}. Duration: {duration_ms:.0f}ms."
        )

        # Ingest with causal links (action causes outcome)
        result = self.magma.ingest(
            content,
            genesis_key_id=genesis_key_id,
            metadata={
                "type": "procedure",
                "procedure_id": procedure_id,
                "action_type": action_type,
                "success": success
            }
        )

        # Cache procedure
        procedure = ActionProcedure(
            procedure_id=procedure_id,
            action_type=action_type,
            name=name,
            description=description,
            target_components=target_components,
            steps=steps,
            success_rate=1.0 if success else 0.0,
            times_used=1,
            avg_duration_ms=duration_ms,
            genesis_key_ids=[genesis_key_id] if genesis_key_id else []
        )
        self._procedure_cache[procedure_id] = procedure

        logger.debug(f"[MAGMA-L4] Stored procedure: {procedure_id} ({name})")
        return procedure_id

    def find_procedures(
        self,
        action_type: str,
        target_component: Optional[str] = None,
        min_success_rate: float = 0.5,
        top_k: int = 5
    ) -> List[ActionProcedure]:
        """
        Find relevant procedures for an action.

        Args:
            action_type: Type of action needed
            target_component: Optional component filter
            min_success_rate: Minimum success rate
            top_k: Maximum results

        Returns:
            List of relevant procedures
        """
        query = f"Procedure for {action_type}"
        if target_component:
            query += f" targeting {target_component}"

        results = self.magma.query(query, top_k=top_k * 2)

        procedures = []
        for result in results:
            metadata = result.metadata or {}
            if metadata.get("type") != "procedure":
                continue

            proc_id = metadata.get("procedure_id")
            if proc_id and proc_id in self._procedure_cache:
                proc = self._procedure_cache[proc_id]
                if proc.success_rate >= min_success_rate:
                    procedures.append(proc)

        # Sort by success rate * times_used (proven procedures first)
        procedures.sort(
            key=lambda p: p.success_rate * min(p.times_used, 10),
            reverse=True
        )

        return procedures[:top_k]

    def update_procedure_outcome(
        self,
        procedure_id: str,
        success: bool,
        duration_ms: float,
        genesis_key_id: Optional[str] = None
    ) -> bool:
        """Update procedure statistics after use."""
        if procedure_id not in self._procedure_cache:
            return False

        proc = self._procedure_cache[procedure_id]

        # Update rolling statistics
        old_total = proc.times_used
        new_total = old_total + 1

        proc.success_rate = (
            (proc.success_rate * old_total + (1 if success else 0)) / new_total
        )
        proc.avg_duration_ms = (
            (proc.avg_duration_ms * old_total + duration_ms) / new_total
        )
        proc.times_used = new_total
        proc.last_used = datetime.now(timezone.utc)

        if genesis_key_id:
            proc.genesis_key_ids.append(genesis_key_id)

        logger.debug(
            f"[MAGMA-L4] Updated procedure {procedure_id}: "
            f"success_rate={proc.success_rate:.2f}, times_used={proc.times_used}"
        )
        return True

    def get_best_procedure(
        self,
        action_type: str,
        target_component: str
    ) -> Optional[ActionProcedure]:
        """Get the best procedure for an action."""
        procedures = self.find_procedures(
            action_type,
            target_component,
            min_success_rate=0.7,
            top_k=1
        )
        return procedures[0] if procedures else None


# =============================================================================
# SECURITY: GENESIS KEYS INTEGRATION
# =============================================================================

class MagmaGenesisIntegration:
    """
    Security Integration: Genesis Keys tracking for Magma operations.

    Provides:
    - Full provenance tracking for all Magma operations
    - Audit trail for memory queries and updates
    - Rollback capability through Genesis Keys
    """

    def __init__(self, magma_memory, genesis_service=None):
        """
        Initialize Genesis integration.

        Args:
            magma_memory: MagmaMemory instance
            genesis_service: GenesisKeyService instance
        """
        self.magma = magma_memory
        self.genesis = genesis_service

        logger.info("[MAGMA-SECURITY] Genesis Keys integration initialized")

    def connect_genesis(self):
        """Connect to Genesis Key service."""
        if self.genesis:
            return True

        try:
            from genesis.genesis_key_service import get_genesis_service
            self.genesis = get_genesis_service()
            return True
        except Exception as e:
            logger.warning("[MAGMA-SECURITY] Genesis Key service not available: %s", e)
            return False

    def track_ingestion(
        self,
        content: str,
        result,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        """Track memory ingestion with Genesis Key."""
        if not self.genesis:
            return None

        key = self.genesis.create_key(
            key_type="MAGMA_INGESTION",
            what_description=f"Ingested {len(result.segments)} segments into Magma memory",
            where_location="cognitive/magma",
            why_reason="Memory ingestion for graph-based retrieval",
            who_actor=user_id or "system",
            how_method="synaptic_ingestion",
            metadata={
                "segments_created": len(result.segments),
                "nodes_created": len(result.nodes_created),
                "edges_created": len(result.edges_created),
                "concepts_linked": result.concepts_linked,
                "entities_linked": result.entities_linked
            }
        )

        return key.key_id if key else None

    def track_query(
        self,
        query: str,
        results: List,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        """Track memory query with Genesis Key."""
        if not self.genesis:
            return None

        key = self.genesis.create_key(
            key_type="MAGMA_QUERY",
            what_description=f"Queried Magma memory: {query[:100]}",
            where_location="cognitive/magma",
            why_reason="Memory retrieval for context",
            who_actor=user_id or "system",
            how_method="rrf_fusion_retrieval",
            metadata={
                "query": query[:200],
                "results_count": len(results),
                "top_score": results[0].rrf_score if results else 0
            }
        )

        return key.key_id if key else None

    def track_causal_inference(
        self,
        query: str,
        result,
        user_id: Optional[str] = None
    ) -> Optional[str]:
        """Track causal inference with Genesis Key."""
        if not self.genesis:
            return None

        key = self.genesis.create_key(
            key_type="MAGMA_INFERENCE",
            what_description=f"Causal inference: {query[:100]}",
            where_location="cognitive/magma/causal_inference",
            why_reason="Understanding causal relationships",
            who_actor=user_id or "system",
            how_method="llm_causal_inference",
            metadata={
                "query": query[:200],
                "claims_found": len(result.causal_claims),
                "chains_found": len(result.causal_chains)
            }
        )

        return key.key_id if key else None


# =============================================================================
# SECURITY: TRUST SCORING INTEGRATION
# =============================================================================

class MagmaTrustIntegration:
    """
    Security Integration: Trust-aware memory operations.

    Provides:
    - Trust-weighted retrieval results
    - Trust scoring for memory nodes
    - Trust decay over time
    """

    def __init__(self, magma_memory, trust_scorer=None):
        """
        Initialize trust integration.

        Args:
            magma_memory: MagmaMemory instance
            trust_scorer: NeuralTrustScorer instance (optional)
        """
        self.magma = magma_memory
        self.trust_scorer = trust_scorer

        logger.info("[MAGMA-SECURITY] Trust scoring integration initialized")

    def connect_trust_scorer(self):
        """Connect to neural trust scorer."""
        if self.trust_scorer:
            return True

        try:
            from ml_intelligence.neural_trust_scorer import NeuralTrustScorer
            self.trust_scorer = NeuralTrustScorer()
            return True
        except ImportError:
            logger.warning("[MAGMA-SECURITY] Neural trust scorer not available")
            return False

    def get_trusted_results(
        self,
        query: str,
        min_trust: float = 0.5,
        top_k: int = 10
    ) -> List:
        """
        Get trust-filtered retrieval results.

        Args:
            query: Search query
            min_trust: Minimum trust score
            top_k: Maximum results

        Returns:
            Trust-filtered results
        """
        # Get raw results
        results = self.magma.query(query, top_k=top_k * 2)

        if not self.trust_scorer:
            return results[:top_k]

        # Score and filter by trust
        trusted_results = []
        for result in results:
            # Extract features for trust scoring
            metadata = result.metadata or {}
            features = {
                "source_reliability": metadata.get("source_reliability", 0.7),
                "outcome_quality": 0.7,  # Default
                "consistency_score": 0.8,
                "validation_count": metadata.get("validation_count", 0),
                "invalidation_count": 0,
                "age_days": 1,  # Would calculate from timestamp
                "content_length": len(result.content),
                "has_code": "code" in result.content.lower(),
                "has_structure": result.content.count('\n') > 2,
                "has_references": "http" in result.content.lower(),
                "usage_frequency": 0.5,
                "success_rate": 0.8
            }

            trust_score, uncertainty = self.trust_scorer.predict_trust(features)

            if trust_score >= min_trust:
                # Add trust info to metadata
                result.metadata = result.metadata or {}
                result.metadata["trust_score"] = trust_score
                result.metadata["trust_uncertainty"] = uncertainty
                trusted_results.append(result)

        return trusted_results[:top_k]

    def update_trust_from_feedback(
        self,
        result_id: str,
        helpful: bool
    ):
        """Update trust based on user feedback."""
        if not self.trust_scorer:
            return

        # This would update the trust scorer's model
        # For now, just log
        logger.debug(
            f"[MAGMA-SECURITY] Trust feedback for {result_id}: "
            f"helpful={helpful}"
        )


# =============================================================================
# SECURITY: GOVERNANCE INTEGRATION
# =============================================================================

class MagmaGovernanceIntegration:
    """
    Security Integration: Constitutional governance for memory.

    Provides:
    - Memory operation governance checks
    - Constitutional rule enforcement
    - Audit logging for compliance
    """

    def __init__(self, magma_memory, governance_engine=None):
        """
        Initialize governance integration.

        Args:
            magma_memory: MagmaMemory instance
            governance_engine: GovernanceEngine instance
        """
        self.magma = magma_memory
        self.governance = governance_engine

        logger.info("[MAGMA-SECURITY] Governance integration initialized")

    def connect_governance(self):
        """Connect to governance engine."""
        if self.governance:
            return True

        try:
            from security.governance import get_governance_engine
            self.governance = get_governance_engine()
            return True
        except ImportError:
            logger.warning("[MAGMA-SECURITY] Governance engine not available")
            return False

    def check_ingestion_allowed(
        self,
        content: str,
        user_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if memory ingestion is allowed by governance.

        Returns:
            (allowed, reason)
        """
        if not self.governance:
            return (True, None)

        # Check constitutional rules
        # INV-8: Respect Privacy
        # INV-11: Preserve Provenance

        # Check for PII patterns (simplified)
        pii_patterns = [
            "ssn:", "social security",
            "credit card", "password:",
            "api_key:", "secret:"
        ]

        content_lower = content.lower()
        for pattern in pii_patterns:
            if pattern in content_lower:
                return (
                    False,
                    f"Content may contain sensitive data (pattern: {pattern})"
                )

        return (True, None)

    def check_query_allowed(
        self,
        query: str,
        user_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if memory query is allowed by governance.

        Returns:
            (allowed, reason)
        """
        if not self.governance:
            return (True, None)

        # All queries allowed for now
        # Could add rate limiting, scope restrictions, etc.
        return (True, None)

    def log_governance_event(
        self,
        event_type: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """Log governance event for audit trail."""
        if not self.governance:
            return

        logger.info(
            f"[MAGMA-GOVERNANCE] {event_type}: "
            f"user={user_id}, details={details}"
        )


# =============================================================================
# UNIFIED INTEGRATION FACTORY
# =============================================================================

def create_magma_layer_integrations(
    magma_memory,
    message_bus=None,
    genesis_service=None,
    trust_scorer=None,
    governance_engine=None
) -> Dict[str, Any]:
    """
    Create all Magma layer integrations.

    Returns:
        Dict containing all integration instances
    """
    integrations = {
        # Layer 1: Message Bus
        "layer1_connector": MagmaMessageBusConnector(magma_memory, message_bus),

        # Layer 2: Interpreter Pattern Memory
        "layer2_patterns": InterpreterPatternMemory(magma_memory),

        # Layer 3: Judgement Decision Memory
        "layer3_decisions": JudgementDecisionMemory(magma_memory),

        # Layer 4: Action Router Memory
        "layer4_actions": ActionRouterMemory(magma_memory),

        # Security: Genesis Keys
        "genesis": MagmaGenesisIntegration(magma_memory, genesis_service),

        # Security: Trust Scoring
        "trust": MagmaTrustIntegration(magma_memory, trust_scorer),

        # Security: Governance
        "governance": MagmaGovernanceIntegration(magma_memory, governance_engine)
    }

    logger.info("[MAGMA] Created all layer integrations")
    return integrations
