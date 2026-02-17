"""
World Model - Grace's Understanding of Her Own State and Environment

The World Model is Grace's internal representation of:
  - What she knows (Oracle domains, record counts, trust levels)
  - What she can do (source code capabilities, connected systems)
  - What she's learning (discovery queue, active domains)
  - What she's good/bad at (competence boundaries)
  - How healthy she is (pillar health, trust temperature)
  - What's happening (recent actions, active contracts, pending tasks)
  - What the user cares about (conversation history, whitelist patterns)

Kimi reads the World Model before every response to ground herself
in reality. The model updates after every action.

The World Model is NOT the Oracle (that's knowledge storage).
The World Model is self-awareness: "who am I, what can I do, what's
happening right now, and what should I do next?"
"""

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """A single turn in conversation history."""
    turn_id: str
    role: str  # "user" or "kimi"
    content: str
    mode: str = "orchestrate"
    confidence: float = 0.0
    sources_used: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorldState:
    """Complete snapshot of Grace's world at a point in time."""
    # Identity
    system_name: str = "Grace"
    version: str = "3.1"

    # Knowledge
    total_knowledge_records: int = 0
    knowledge_domains: List[str] = field(default_factory=list)
    domain_coverage: Dict[str, int] = field(default_factory=dict)
    total_training_bytes: int = 0

    # Capabilities
    source_code_modules: int = 0
    source_code_functions: int = 0
    source_code_classes: int = 0
    connected_systems: List[str] = field(default_factory=list)

    # Learning
    discovery_queue_size: int = 0
    active_learning_domains: List[str] = field(default_factory=list)
    evolution_score: float = 0.0
    learning_velocity: float = 0.0  # Records per hour

    # Competence
    competence_by_domain: Dict[str, float] = field(default_factory=dict)
    strongest_domains: List[str] = field(default_factory=list)
    weakest_domains: List[str] = field(default_factory=list)

    # Health
    trust_temperature: float = 0.5
    system_mode: str = "cautious"
    pillar_health: Dict[str, float] = field(default_factory=dict)
    overall_health: float = 0.5
    hallucination_rate: float = 0.0

    # Activity
    total_conversations: int = 0
    total_queries_processed: int = 0
    active_contracts: int = 0
    pending_actions: int = 0
    recent_actions: List[str] = field(default_factory=list)

    # Trust
    trust_chain_size: int = 0
    trust_chain_generations: Dict[int, int] = field(default_factory=dict)
    average_trust: float = 0.5

    # Files
    total_files: int = 0
    code_files: int = 0
    doc_files: int = 0
    genesis_key_blocks: int = 0

    # Timestamp
    snapshot_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WorldModel:
    """
    Grace's self-awareness model.

    Updated after every action. Read by Kimi before every response.
    This is how Grace knows who she is, what's happening, and
    what she should do next.

    Connected to:
    - PerpetualLearningLoop (knowledge + learning state)
    - KimiOrchestrator (conversation + query state)
    - SelfEvolutionCoordinator (evolution + action state)
    - RecursionGovernor (contract + bound state)
    - Advanced Trust (trust + competence + pillar state)
    """

    def __init__(self):
        self._loop = None
        self._kimi = None
        self._evolution = None
        self._governor = None

        # Conversation history
        self.conversations: List[ConversationTurn] = []
        self._world_states: List[WorldState] = []

        # User patterns
        self._user_topics: Dict[str, int] = defaultdict(int)
        self._user_domains: Dict[str, int] = defaultdict(int)

        logger.info("[WORLD-MODEL] Initialized")

    # =========================================================================
    # CONNECTIONS
    # =========================================================================

    def connect_loop(self, loop) -> None:
        """Connect to PerpetualLearningLoop."""
        self._loop = loop

    def connect_kimi(self, kimi) -> None:
        """Connect to KimiOrchestrator."""
        self._kimi = kimi

    def connect_evolution(self, evolution) -> None:
        """Connect to SelfEvolutionCoordinator."""
        self._evolution = evolution

    def connect_governor(self, governor) -> None:
        """Connect to RecursionGovernor."""
        self._governor = governor

    def connect_all(self, kimi) -> None:
        """Connect to everything from a KimiOrchestrator."""
        self._kimi = kimi
        if hasattr(kimi, '_loop') and kimi._loop:
            self._loop = kimi._loop
        if hasattr(kimi, '_evolution') and kimi._evolution:
            self._evolution = kimi._evolution
        if hasattr(kimi, '_recursion_governor') and kimi._recursion_governor:
            self._governor = kimi._recursion_governor

    # =========================================================================
    # CONVERSATION TRACKING
    # =========================================================================

    def record_user_message(self, content: str) -> ConversationTurn:
        """Record a user message."""
        turn = ConversationTurn(
            turn_id=f"turn-{uuid.uuid4().hex[:12]}",
            role="user",
            content=content,
        )
        self.conversations.append(turn)

        # Track user patterns
        words = content.lower().split()
        for word in words:
            if len(word) > 4:
                self._user_topics[word] = self._user_topics.get(word, 0) + 1

        return turn

    def record_kimi_response(
        self, content: str, mode: str = "orchestrate",
        confidence: float = 0.0, sources: Optional[List[str]] = None,
    ) -> ConversationTurn:
        """Record Kimi's response."""
        turn = ConversationTurn(
            turn_id=f"turn-{uuid.uuid4().hex[:12]}",
            role="kimi",
            content=content,
            mode=mode,
            confidence=confidence,
            sources_used=sources or [],
        )
        self.conversations.append(turn)
        return turn

    def get_conversation_context(self, last_n: int = 10) -> List[Dict[str, Any]]:
        """Get recent conversation for context injection."""
        recent = self.conversations[-last_n:]
        return [
            {"role": t.role, "content": t.content, "mode": t.mode}
            for t in recent
        ]

    # =========================================================================
    # WORLD STATE SNAPSHOT
    # =========================================================================

    def get_world_state(self) -> WorldState:
        """Take a complete snapshot of Grace's current world."""
        state = WorldState()

        # Knowledge (from loop's oracle)
        if self._loop:
            oracle = self._loop.oracle
            state.total_knowledge_records = len(oracle.records)
            state.knowledge_domains = oracle.get_all_domains()
            state.domain_coverage = oracle.get_domain_stats()
            state.total_training_bytes = sum(
                len(r.content.encode()) for r in oracle.records.values()
            )

            # Source code
            si = self._loop.source_index
            si_stats = si.get_stats()
            state.source_code_modules = si_stats.get("total_modules", 0)
            state.source_code_functions = si_stats.get("functions", 0)
            state.source_code_classes = si_stats.get("classes", 0)

            # Learning
            state.discovery_queue_size = len(self._loop.unified_learning.learning_queue)
            state.active_learning_domains = list(
                self._loop.discovery._domain_activity.keys()
            )

            # Trust
            state.trust_chain_size = len(self._loop.trust_chain)
            for entry in self._loop.trust_chain.values():
                gen = entry.generation
                state.trust_chain_generations[gen] = state.trust_chain_generations.get(gen, 0) + 1
            trusts = [e.trust_score for e in self._loop.trust_chain.values()]
            state.average_trust = sum(trusts) / len(trusts) if trusts else 0.5

            # Temperature
            if self._loop.thermometer:
                reading = self._loop.thermometer.read_temperature()
                state.trust_temperature = reading.temperature
                state.system_mode = reading.mode.value

            # Competence
            if self._loop.competence:
                for domain, comp in self._loop.competence.domains.items():
                    state.competence_by_domain[domain] = comp.accuracy
                sorted_comp = sorted(
                    state.competence_by_domain.items(),
                    key=lambda x: x[1], reverse=True,
                )
                state.strongest_domains = [d for d, _ in sorted_comp[:3]]
                state.weakest_domains = [d for d, _ in sorted_comp[-3:]]

            # Pillar health
            if self._loop.pillar_tracker:
                from advanced_trust.pillar_tracker import Pillar
                for p in Pillar:
                    state.pillar_health[p.value] = (
                        self._loop.pillar_tracker.get_pillar_success_rate(p)
                    )
                rates = list(state.pillar_health.values())
                state.overall_health = sum(rates) / len(rates) if rates else 0.5

            # Hallucination
            hg_stats = self._loop.hallucination_guard.get_stats()
            state.hallucination_rate = 1.0 - hg_stats.get("grounding_rate", 1.0)

            # Files
            lib_stats = self._loop.librarian.get_stats()
            state.total_files = lib_stats.get("total_files", 0)
            state.code_files = lib_stats.get("code_files", 0)
            state.doc_files = lib_stats.get("document_files", 0)
            state.genesis_key_blocks = lib_stats.get("genesis_key_blocks", 0)

        # Kimi state
        if self._kimi:
            state.total_queries_processed = len(self._kimi.responses)
            state.connected_systems = list(self._kimi.get_connection_status().keys())

        # Evolution
        if self._evolution:
            state.evolution_score = self._evolution._evolution_score
            state.pending_actions = len(self._evolution.get_pending_actions())

        # Governor
        if self._governor:
            gov_stats = self._governor.get_stats()
            state.active_contracts = gov_stats.get("active", 0)

        # Conversations
        state.total_conversations = len(self.conversations)

        self._world_states.append(state)
        return state

    def get_world_summary_json(self) -> Dict[str, Any]:
        """Get world state as JSON for Kimi's context."""
        state = self.get_world_state()
        return {
            "identity": {"name": state.system_name, "version": state.version},
            "knowledge": {
                "records": state.total_knowledge_records,
                "domains": state.knowledge_domains,
                "coverage": state.domain_coverage,
                "bytes": state.total_training_bytes,
            },
            "capabilities": {
                "modules": state.source_code_modules,
                "functions": state.source_code_functions,
                "classes": state.source_code_classes,
                "connected": state.connected_systems,
            },
            "learning": {
                "queue": state.discovery_queue_size,
                "active_domains": state.active_learning_domains,
                "evolution_score": state.evolution_score,
            },
            "competence": {
                "by_domain": state.competence_by_domain,
                "strongest": state.strongest_domains,
                "weakest": state.weakest_domains,
            },
            "health": {
                "temperature": state.trust_temperature,
                "mode": state.system_mode,
                "pillars": state.pillar_health,
                "overall": state.overall_health,
                "hallucination_rate": state.hallucination_rate,
            },
            "activity": {
                "conversations": state.total_conversations,
                "queries": state.total_queries_processed,
                "contracts": state.active_contracts,
                "pending_actions": state.pending_actions,
            },
            "trust": {
                "chain_size": state.trust_chain_size,
                "average": state.average_trust,
            },
            "files": {
                "total": state.total_files,
                "code": state.code_files,
                "docs": state.doc_files,
                "genesis_blocks": state.genesis_key_blocks,
            },
        }

    def get_world_summary_nlp(self) -> str:
        """Get world state as NLP for user display."""
        state = self.get_world_state()
        lines = [
            f"Grace {state.version} — System Status",
            f"",
            f"Knowledge: {state.total_knowledge_records} records across {len(state.knowledge_domains)} domains",
            f"Trust: {state.trust_temperature:.0%} ({state.system_mode})",
            f"Health: {state.overall_health:.0%}",
            f"Evolution: {state.evolution_score:.0%}",
        ]
        if state.strongest_domains:
            lines.append(f"Best at: {', '.join(state.strongest_domains)}")
        if state.discovery_queue_size:
            lines.append(f"Learning queue: {state.discovery_queue_size} targets")
        if state.active_contracts:
            lines.append(f"Active contracts: {state.active_contracts}")
        lines.append(f"Files: {state.code_files} code, {state.doc_files} docs")
        return "\n".join(lines)

    def get_user_interests(self) -> List[str]:
        """Get user's top topics from conversation history."""
        sorted_topics = sorted(
            self._user_topics.items(), key=lambda x: x[1], reverse=True
        )
        return [t for t, _ in sorted_topics[:10]]

    def get_stats(self) -> Dict[str, Any]:
        """Get world model statistics."""
        return {
            "total_conversations": len(self.conversations),
            "total_snapshots": len(self._world_states),
            "user_topics_tracked": len(self._user_topics),
            "loop_connected": self._loop is not None,
            "kimi_connected": self._kimi is not None,
            "evolution_connected": self._evolution is not None,
            "governor_connected": self._governor is not None,
        }
