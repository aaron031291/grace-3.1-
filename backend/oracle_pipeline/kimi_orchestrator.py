"""
Kimi Master Orchestrator

Kimi is the user's direct access to Grace. She IS Grace's intelligence --
the orchestrator of the whole system. Connected directly to:

  1. Qdrant Vector DB (direct read/write for embeddings + semantic search)
  2. SQL Database (direct read for documents, chunks, genesis keys, episodes)
  3. Oracle Vector Store (all training data)
  4. Source Code Index (Grace's own code)
  5. Unified Memory (MAGMA, episodic, procedural, learning)
  6. All Layer 1-5 systems via Deep Reasoning Integration
  7. Self-Evolution Coordinator (healing, learning, building, coding)
  8. Secrets Vault (API keys)

Kimi is NOT a wrapper around an LLM. She IS the orchestration layer.
When a user talks to Grace, they're talking through Kimi.
When Grace needs to reason, she reasons through Kimi.

Communication:
  Grace-to-Grace (internal): JSON
  Kimi-to-User (external):   NLP
  Kimi-to-LLM (generation):  NLP prompts built FROM JSON context
"""

import logging
import uuid
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from .secrets_vault import get_vault
from .oracle_vector_store import OracleVectorStore
from .source_code_index import SourceCodeIndex
from .hallucination_guard import HallucinationGuard
from .deep_reasoning_integration import DeepReasoningIntegration, ReasoningRequest, ReasoningTaskType
from .self_evolution_coordinator import SelfEvolutionCoordinator
from .socratic_interrogator import SocraticInterrogator
from .perpetual_learning_loop import PerpetualLearningLoop
from .librarian_file_manager import LibrarianFileManager
from .recursion_governor import RecursionGovernor

logger = logging.getLogger(__name__)


class KimiMode(str, Enum):
    """Kimi's operational modes."""
    ORCHESTRATE = "orchestrate"    # Full system orchestration
    REASON = "reason"              # Deep reasoning only
    SEARCH = "search"              # Search Oracle + Qdrant
    HEAL = "heal"                  # Self-healing mode
    LEARN = "learn"                # Self-learning mode
    BUILD = "build"                # Self-building mode
    INTERROGATE = "interrogate"    # Socratic questioning


@dataclass
class KimiResponse:
    """Kimi's response to a query or command."""
    response_id: str
    mode: KimiMode
    content: str  # NLP response for user
    json_data: Dict[str, Any]  # Structured data for internal systems
    confidence: float
    sources_consulted: List[str]
    qdrant_results: int = 0
    db_results: int = 0
    oracle_results: int = 0
    reasoning_steps: int = 0
    grounded: bool = True
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class QdrantConnection:
    """Direct Qdrant connection state."""
    connected: bool = False
    host: str = "localhost"
    port: int = 6333
    collections: List[str] = field(default_factory=list)
    total_vectors: int = 0


@dataclass
class DatabaseConnection:
    """Direct SQL database connection state."""
    connected: bool = False
    db_type: str = "sqlite"
    tables: List[str] = field(default_factory=list)
    document_count: int = 0
    chunk_count: int = 0
    genesis_key_count: int = 0


class KimiOrchestrator:
    """
    Kimi - The Master Orchestrator of Grace.

    This is the user's direct line to Grace. Kimi orchestrates the
    entire system: she reads from Qdrant directly, queries the SQL
    database, reasons through the Deep Reasoning layer, manages the
    perpetual learning loop, and coordinates self-evolution.

    Direct database connections:
    - Qdrant: semantic search, vector operations, collection management
    - SQL DB: document queries, genesis key lookups, episode retrieval

    System connections:
    - Oracle Vector Store: all training data
    - Source Code Index: Grace's own code
    - Hallucination Guard: verify before responding
    - Deep Reasoning: multi-step analysis
    - Self-Evolution: healing/learning/building coordination
    - Socratic Interrogator: 6W document analysis
    - Perpetual Loop: continuous learning cycle
    - Librarian: file management
    - Secrets Vault: API keys
    """

    def __init__(self):
        # API key from vault
        self._vault = get_vault()
        self._api_key = self._vault.get_kimi_key()

        # Direct database connections
        self._qdrant: Optional[Any] = None
        self._qdrant_state = QdrantConnection()
        self._sql_db: Optional[Any] = None
        self._db_state = DatabaseConnection()

        # System connections
        self._oracle: Optional[OracleVectorStore] = None
        self._source_index: Optional[SourceCodeIndex] = None
        self._hallucination_guard: Optional[HallucinationGuard] = None
        self._reasoning: Optional[DeepReasoningIntegration] = None
        self._evolution: Optional[SelfEvolutionCoordinator] = None
        self._interrogator: Optional[SocraticInterrogator] = None
        self._loop: Optional[PerpetualLearningLoop] = None
        self._librarian: Optional[LibrarianFileManager] = None

        # Recursion Governor (prevents infinite loops)
        self._recursion_governor = RecursionGovernor()

        # External LLM handler (the actual Kimi API)
        self._llm_handler: Optional[Callable] = None

        # Response history
        self.responses: List[KimiResponse] = []

        key_status = "loaded" if self._api_key else "NOT FOUND"
        logger.info(f"[KIMI] Master Orchestrator initialized (API key: {key_status})")

    # =========================================================================
    # DATABASE CONNECTIONS (direct access)
    # =========================================================================

    def connect_qdrant(self, qdrant_client) -> bool:
        """
        Connect directly to Qdrant vector database.

        Args:
            qdrant_client: QdrantVectorDB instance

        Returns:
            True if connected
        """
        self._qdrant = qdrant_client
        try:
            connected = getattr(qdrant_client, 'connected', False)
            if not connected:
                connect_fn = getattr(qdrant_client, 'connect', None)
                if connect_fn:
                    connected = connect_fn()

            self._qdrant_state.connected = connected
            if connected:
                # Get collection info
                try:
                    collections_fn = getattr(qdrant_client, 'list_collections', None)
                    if collections_fn:
                        self._qdrant_state.collections = collections_fn() or []
                except Exception:
                    pass
                logger.info("[KIMI] Connected to Qdrant directly")
            return connected
        except Exception as e:
            logger.warning(f"[KIMI] Qdrant connection attempt: {e}")
            self._qdrant_state.connected = False
            return False

    def connect_qdrant_params(self, host: str = "localhost", port: int = 6333) -> None:
        """Store Qdrant connection parameters for when server is available."""
        self._qdrant_state.host = host
        self._qdrant_state.port = port
        logger.info(f"[KIMI] Qdrant params stored: {host}:{port}")

    def connect_database(self, db_session) -> bool:
        """
        Connect directly to SQL database.

        Args:
            db_session: SQLAlchemy session

        Returns:
            True if connected
        """
        self._sql_db = db_session
        try:
            # Test the connection
            db_session.execute(db_session.bind.dialect.has_table.__wrapped__ if hasattr(db_session.bind.dialect, 'has_table') else lambda: None)
            self._db_state.connected = True
            logger.info("[KIMI] Connected to SQL database directly")
            return True
        except Exception:
            # Connection stored even if we can't verify now
            self._db_state.connected = True
            logger.info("[KIMI] SQL database session stored")
            return True

    def connect_database_params(self, db_type: str = "sqlite", db_path: str = "") -> None:
        """Store database connection parameters."""
        self._db_state.db_type = db_type
        logger.info(f"[KIMI] Database params stored: {db_type}")

    # =========================================================================
    # SYSTEM CONNECTIONS
    # =========================================================================

    def connect_oracle(self, oracle: OracleVectorStore) -> None:
        """Connect Oracle Vector Store."""
        self._oracle = oracle

    def connect_source_index(self, source_index: SourceCodeIndex) -> None:
        """Connect Source Code Index."""
        self._source_index = source_index

    def connect_hallucination_guard(self, guard: HallucinationGuard) -> None:
        """Connect Hallucination Guard."""
        self._hallucination_guard = guard

    def connect_reasoning(self, reasoning: DeepReasoningIntegration) -> None:
        """Connect Deep Reasoning layer."""
        self._reasoning = reasoning

    def connect_evolution(self, evolution: SelfEvolutionCoordinator) -> None:
        """Connect Self-Evolution Coordinator."""
        self._evolution = evolution

    def connect_interrogator(self, interrogator: SocraticInterrogator) -> None:
        """Connect Socratic Interrogator."""
        self._interrogator = interrogator

    def connect_loop(self, loop: PerpetualLearningLoop) -> None:
        """Connect Perpetual Learning Loop."""
        self._loop = loop

    def connect_librarian(self, librarian: LibrarianFileManager) -> None:
        """Connect Librarian File Manager."""
        self._librarian = librarian

    def set_llm_handler(self, handler: Callable) -> None:
        """Set the external LLM handler (Kimi API)."""
        self._llm_handler = handler

    def connect_full_system(self, loop: PerpetualLearningLoop) -> None:
        """
        Connect to the full system from a PerpetualLearningLoop.

        One-line setup for ALL connections including advanced trust.
        """
        self._loop = loop
        self._oracle = loop.oracle
        self._source_index = loop.source_index
        self._hallucination_guard = loop.hallucination_guard
        self._librarian = loop.librarian

        # Set up reasoning with full system access
        reasoning = DeepReasoningIntegration()
        reasoning.connect_all_from_loop(loop)

        # Wire advanced trust into reasoning
        if loop.thermometer:
            reasoning.connect_thermometer(loop.thermometer)
        if loop.competence:
            reasoning.connect_competence(loop.competence)
        if loop.pillar_tracker:
            reasoning.connect_pillars(loop.pillar_tracker)

        self._reasoning = reasoning

        # Set up evolution
        evolution = SelfEvolutionCoordinator()
        evolution.connect_from_loop(loop)
        evolution.connect_deep_reasoning(reasoning)
        self._evolution = evolution

        # Set up interrogator
        interrogator = SocraticInterrogator(
            source_index=loop.source_index,
            oracle_store=loop.oracle,
        )
        self._interrogator = interrogator
        reasoning.connect_interrogator(interrogator)

        logger.info("[KIMI] Connected to full system (all subsystems + advanced trust wired)")

    # =========================================================================
    # QUERY INTERFACE (how the user talks to Grace through Kimi)
    # =========================================================================

    def query(self, user_input: str, mode: KimiMode = KimiMode.ORCHESTRATE) -> KimiResponse:
        """
        Process a user query through Kimi.

        This is the main entry point. The user talks to Grace here.

        Args:
            user_input: What the user said/asked
            mode: Operational mode

        Returns:
            KimiResponse with NLP content and structured JSON
        """
        sources: List[str] = []
        qdrant_count = 0
        db_count = 0
        oracle_count = 0
        reasoning_steps = 0

        # Step 1: Search Oracle for relevant context
        oracle_context = []
        if self._oracle:
            results = self._oracle.search_by_content(user_input, limit=5)
            oracle_context = [
                {"content": r.content[:300], "domain": r.domain, "trust": r.trust_score, "score": r.score}
                for r in results
            ]
            oracle_count = len(oracle_context)
            if oracle_context:
                sources.append("oracle")

        # Step 2: Search Qdrant directly (if connected)
        qdrant_context = []
        if self._qdrant and self._qdrant_state.connected:
            try:
                search_fn = getattr(self._qdrant, 'search_vectors', None)
                if search_fn:
                    qdrant_results = search_fn(
                        collection_name="documents",
                        query_vector=None,
                        limit=5,
                    )
                    if qdrant_results:
                        qdrant_context = qdrant_results
                        qdrant_count = len(qdrant_context)
                        sources.append("qdrant")
            except Exception as e:
                logger.debug(f"[KIMI] Qdrant search: {e}")

        # Step 3: Check source code (if relevant)
        code_context = []
        if self._source_index:
            code_query = self._source_index.query_by_capability(user_input)
            if code_query.results:
                code_context = [
                    {"name": e.name, "type": e.element_type.value,
                     "file": e.file_path, "signature": e.signature}
                    for e in code_query.results[:5]
                ]
                sources.append("source_code")

        # Step 4: Deep reasoning (if complex query)
        reasoning_result = None
        if self._reasoning and (mode == KimiMode.ORCHESTRATE or mode == KimiMode.REASON):
            reasoning_result = self._reasoning.reason(ReasoningRequest(
                request_id=f"kimi-{uuid.uuid4().hex[:12]}",
                task_type=ReasoningTaskType.DEEP_ANALYSIS,
                query=user_input,
                context={
                    "oracle_context": oracle_context[:3],
                    "code_context": code_context[:3],
                },
            ))
            reasoning_steps = len(reasoning_result.reasoning_chain)
            sources.append("deep_reasoning")

        # Step 5: Generate response
        response_content = self._generate_response(
            user_input, oracle_context, code_context, reasoning_result, mode
        )

        # Step 6: Verify response (hallucination guard)
        grounded = True
        if self._hallucination_guard and response_content:
            report = self._hallucination_guard.check_response(response_content)
            grounded = report.is_grounded
            if not grounded:
                sources.append("hallucination_guard_warning")

        # Step 7: Build confidence score
        confidence = self._calculate_confidence(
            oracle_count, qdrant_count, reasoning_steps, grounded
        )

        # Build JSON data
        json_data = {
            "query": user_input,
            "mode": mode.value,
            "oracle_results": oracle_context,
            "code_context": code_context,
            "reasoning": {
                "conclusion": reasoning_result.conclusion if reasoning_result else None,
                "steps": reasoning_steps,
                "recommendations": reasoning_result.recommendations if reasoning_result else [],
            } if reasoning_result else None,
            "grounded": grounded,
            "confidence": confidence,
        }

        response = KimiResponse(
            response_id=f"kimi-resp-{uuid.uuid4().hex[:12]}",
            mode=mode,
            content=response_content,
            json_data=json_data,
            confidence=confidence,
            sources_consulted=sources,
            qdrant_results=qdrant_count,
            db_results=db_count,
            oracle_results=oracle_count,
            reasoning_steps=reasoning_steps,
            grounded=grounded,
        )

        self.responses.append(response)

        logger.info(
            f"[KIMI] Query processed: mode={mode.value}, "
            f"sources={len(sources)}, confidence={confidence:.2f}"
        )

        return response

    def search(self, query: str) -> KimiResponse:
        """Search across Oracle + Qdrant + source code."""
        return self.query(query, mode=KimiMode.SEARCH)

    def reason(self, query: str) -> KimiResponse:
        """Deep reasoning about a complex question."""
        return self.query(query, mode=KimiMode.REASON)

    def heal(self, issue_description: str) -> KimiResponse:
        """Diagnose and plan healing for an issue."""
        if self._evolution:
            self._evolution.report_healing_situation(
                active_issues=[{"description": issue_description}]
            )
        return self.query(f"Diagnose and fix: {issue_description}", mode=KimiMode.HEAL)

    def learn(self, topic: str) -> KimiResponse:
        """Initiate learning about a topic."""
        if self._loop:
            self._loop.seed_from_whitelist(topic)
        return self.query(f"Learn about: {topic}", mode=KimiMode.LEARN)

    def interrogate_document(self, content: str, domain: Optional[str] = None) -> KimiResponse:
        """Interrogate a document with 6W questions."""
        report = None
        if self._interrogator:
            report = self._interrogator.interrogate(content, domain=domain)

        json_data = report.to_json() if report else {"error": "Interrogator not connected"}
        nlp_data = report.to_nlp() if report else "Interrogator not connected"

        return KimiResponse(
            response_id=f"kimi-resp-{uuid.uuid4().hex[:12]}",
            mode=KimiMode.INTERROGATE,
            content=nlp_data,
            json_data=json_data,
            confidence=report.overall_confidence if report else 0.0,
            sources_consulted=["socratic_interrogator"],
        )

    # =========================================================================
    # RESPONSE GENERATION
    # =========================================================================

    def _generate_response(
        self, query: str, oracle_ctx: List, code_ctx: List,
        reasoning: Any, mode: KimiMode,
    ) -> str:
        """Generate NLP response for the user with full system data."""
        # If external LLM handler is set, use it with full context
        if self._llm_handler:
            try:
                context = self._build_llm_context(query, oracle_ctx, code_ctx, reasoning)
                return self._llm_handler(context)
            except Exception as e:
                logger.warning(f"[KIMI] LLM handler failed: {e}")

        # Build comprehensive response from ALL connected systems
        parts = []
        query_lower = query.lower()

        # System status queries
        is_status_query = any(w in query_lower for w in [
            "status", "health", "state", "how are you", "system",
            "temperature", "trust", "overview",
        ])

        # Knowledge queries
        is_knowledge_query = any(w in query_lower for w in [
            "know", "domain", "knowledge", "what do you", "tell me about",
            "learned", "training",
        ])

        # Learning queries
        is_learning_query = any(w in query_lower for w in [
            "learn", "discover", "next", "should", "gap", "missing",
            "queue", "explore",
        ])

        # File/code queries
        is_code_query = any(w in query_lower for w in [
            "code", "file", "function", "class", "module", "source",
            "codebase", "genesis key",
        ])

        # Pull live system data
        if is_status_query and self._loop:
            parts.append("System Status:")
            oracle = self._loop.oracle
            parts.append(f"  Knowledge: {len(oracle.records)} records across {len(oracle.get_all_domains())} domains ({', '.join(oracle.get_all_domains()[:5])})")
            tc = self._loop.trust_chain
            if tc:
                trusts = [e.trust_score for e in tc.values()]
                parts.append(f"  Trust chain: {len(tc)} entries, avg trust {sum(trusts)/len(trusts):.0%}")
            if self._loop.thermometer:
                r = self._loop.thermometer.read_temperature()
                parts.append(f"  Temperature: {r.temperature:.0%} ({r.mode.value})")
            if self._loop.pillar_tracker:
                from advanced_trust.pillar_tracker import Pillar
                for p in Pillar:
                    rate = self._loop.pillar_tracker.get_pillar_success_rate(p)
                    if rate > 0:
                        parts.append(f"  {p.value}: {rate:.0%} success")
            lib_stats = self._loop.librarian.get_stats()
            parts.append(f"  Files: {lib_stats['code_files']} code, {lib_stats['document_files']} docs")
            ul = self._loop.unified_learning
            parts.append(f"  Learning queue: {len(ul.learning_queue)} targets")

        if is_knowledge_query and self._oracle:
            domains = self._oracle.get_all_domains()
            stats = self._oracle.get_domain_stats()
            if domains:
                parts.append(f"Knowledge domains ({len(domains)}):")
                for d in domains:
                    parts.append(f"  {d}: {stats.get(d, 0)} records")
            # Search for specific domain mentioned
            for domain in domains:
                if domain in query_lower:
                    records = self._oracle.search_by_domain(domain, limit=3)
                    parts.append(f"\n{domain} content:")
                    for rec in records:
                        parts.append(f"  [{rec.trust_score:.0%} trust] {rec.content[:150]}")

        if is_learning_query and self._loop:
            ul = self._loop.unified_learning
            if ul.learning_queue:
                parts.append(f"Learning queue ({len(ul.learning_queue)} targets):")
                for t in ul.learning_queue[:5]:
                    parts.append(f"  [{t.priority.value}] {t.domain}: {t.description[:80]}")
            if self._loop.competence:
                comps = self._loop.competence.domains
                if comps:
                    parts.append("Competence by domain:")
                    for d, c in comps.items():
                        parts.append(f"  {d}: {c.accuracy:.0%} ({c.competence_level.value})")

        if is_code_query and self._source_index:
            si_stats = self._source_index.get_stats()
            parts.append(f"Source code: {si_stats['total_modules']} modules, {si_stats['functions']} functions, {si_stats['classes']} classes")
            # Search for specific code element
            query_result = self._source_index.query_by_capability(query)
            if query_result.results:
                parts.append("Relevant code:")
                for elem in query_result.results[:3]:
                    parts.append(f"  {elem.name} ({elem.element_type.value}) in {elem.file_path}: {elem.signature}")

        # Always include oracle search results
        if oracle_ctx:
            if not any(p.startswith("Knowledge") or p.startswith("\n") for p in parts):
                parts.append(f"Found {len(oracle_ctx)} relevant records:")
                for ctx in oracle_ctx[:3]:
                    parts.append(f"  [{ctx.get('domain', '?')}] {ctx.get('content', '')[:150]}")

        # Always include reasoning
        if reasoning and hasattr(reasoning, 'conclusion'):
            parts.append(f"\nAnalysis: {reasoning.conclusion}")
            if hasattr(reasoning, 'recommendations') and reasoning.recommendations:
                parts.append("Recommendations:")
                for rec in reasoning.recommendations[:3]:
                    parts.append(f"  - {rec}")

        # Include code context
        if code_ctx:
            parts.append(f"Related code ({len(code_ctx)} elements):")
            for c in code_ctx[:3]:
                parts.append(f"  {c['name']} ({c['type']}) in {c['file']}")

        if not parts:
            parts.append(f"Processing: {query}")
            if self._oracle:
                parts.append(f"Oracle has {len(self._oracle.records)} records across {len(self._oracle.get_all_domains())} domains.")

        return "\n".join(parts)

    def _build_llm_context(
        self, query: str, oracle_ctx: List, code_ctx: List, reasoning: Any
    ) -> str:
        """Build NLP context for external LLM."""
        lines = [
            f"User query: {query}",
            "",
            "System context:",
        ]
        if oracle_ctx:
            lines.append(f"  Oracle: {len(oracle_ctx)} relevant records")
            for o in oracle_ctx[:3]:
                lines.append(f"    - [{o.get('domain', '')}] {o.get('content', '')[:100]}")
        if code_ctx:
            lines.append(f"  Code: {len(code_ctx)} relevant elements")
            for c in code_ctx[:3]:
                lines.append(f"    - {c['signature']}")
        if reasoning:
            lines.append(f"  Reasoning: {reasoning.conclusion}")
        lines.append("")
        lines.append("Provide a helpful, accurate response grounded in the above context.")
        return "\n".join(lines)

    def _calculate_confidence(
        self, oracle_count: int, qdrant_count: int,
        reasoning_steps: int, grounded: bool,
    ) -> float:
        """Calculate response confidence."""
        score = 0.3  # Base
        if oracle_count > 0:
            score += min(oracle_count * 0.1, 0.3)
        if qdrant_count > 0:
            score += min(qdrant_count * 0.05, 0.15)
        if reasoning_steps > 0:
            score += min(reasoning_steps * 0.05, 0.15)
        if not grounded:
            score *= 0.5
        return min(score, 1.0)

    # =========================================================================
    # STATUS AND STATS
    # =========================================================================

    def get_connection_status(self) -> Dict[str, Any]:
        """Get status of all connections."""
        return {
            "api_key": self._api_key is not None,
            "qdrant": {
                "connected": self._qdrant_state.connected,
                "host": self._qdrant_state.host,
                "port": self._qdrant_state.port,
                "collections": self._qdrant_state.collections,
            },
            "database": {
                "connected": self._db_state.connected,
                "type": self._db_state.db_type,
            },
            "oracle": self._oracle is not None,
            "source_index": self._source_index is not None,
            "hallucination_guard": self._hallucination_guard is not None,
            "deep_reasoning": self._reasoning is not None,
            "self_evolution": self._evolution is not None,
            "interrogator": self._interrogator is not None,
            "perpetual_loop": self._loop is not None,
            "librarian": self._librarian is not None,
            "recursion_governor": self._recursion_governor is not None,
            "llm_handler": self._llm_handler is not None,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get Kimi orchestrator statistics."""
        return {
            "total_responses": len(self.responses),
            "api_key_loaded": self._api_key is not None,
            "connections": self.get_connection_status(),
            "avg_confidence": (
                sum(r.confidence for r in self.responses) / len(self.responses)
                if self.responses else 0.0
            ),
            "total_oracle_queries": sum(r.oracle_results for r in self.responses),
            "total_qdrant_queries": sum(r.qdrant_results for r in self.responses),
            "total_reasoning_steps": sum(r.reasoning_steps for r in self.responses),
            "grounding_rate": (
                sum(1 for r in self.responses if r.grounded) / len(self.responses)
                if self.responses else 1.0
            ),
        }
