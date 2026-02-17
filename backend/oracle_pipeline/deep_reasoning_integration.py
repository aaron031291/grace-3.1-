"""
Deep Reasoning Integration Layer (Kimi / Advanced Model Connector)

Connects a deep reasoning model (Kimi 2.5, or any advanced reasoning LLM)
directly into the Oracle system in READ-ONLY capacity, with full access
to every subsystem through the Protocol Bus.

Architecture decision: Kimi operates as a REASONING LAYER, not a data
mutator. It reads everything, reasons about everything, but all writes
go through the normal pipeline (Oracle ingest, librarian, etc.).

What Kimi connects to (read-only):
  - Oracle Vector Store (all training data)
  - Source Code Index (Grace's own code)
  - Trust Chain (provenance of every fact)
  - Pillar Tracker (system health)
  - Competence Boundaries (what Grace is good/bad at)
  - Trust Thermometer (system confidence)
  - Genesis Keys (full audit trail)
  - Hallucination Guard (verification results)
  - Discovery Engine (what's being learned)
  - Librarian (file structure)

What Kimi does:
  1. Deep reasoning about complex queries (multi-step chains)
  2. Cross-system analysis ("what's the relationship between X and Y?")
  3. Strategic planning ("what should Grace learn next and why?")
  4. Verification reasoning ("is this claim consistent across all data?")
  5. Architecture review ("is the system well-structured?")
  6. Knowledge synthesis ("combine these 5 domains into one insight")

Communication Protocol:
  All internal: JSON (structured, typed, validated)
  User-facing:  NLP (natural language, human readable)
  LLM boundary: NLP prompts constructed FROM JSON context
"""

import logging
import uuid
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ReasoningTaskType(str, Enum):
    """Types of reasoning tasks."""
    DEEP_ANALYSIS = "deep_analysis"
    CROSS_SYSTEM = "cross_system"
    STRATEGIC_PLANNING = "strategic_planning"
    VERIFICATION = "verification"
    ARCHITECTURE_REVIEW = "architecture_review"
    KNOWLEDGE_SYNTHESIS = "knowledge_synthesis"
    GAP_ANALYSIS = "gap_analysis"
    ANOMALY_DETECTION = "anomaly_detection"


class AccessMode(str, Enum):
    """Access modes for system connections."""
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"  # Only for specific outputs like reports


@dataclass
class SystemSnapshot:
    """Read-only snapshot of all connected systems for reasoning."""
    oracle_domains: List[str]
    oracle_record_count: int
    oracle_domain_stats: Dict[str, int]
    source_code_modules: int
    source_code_functions: int
    source_code_classes: int
    trust_temperature: float
    competence_domains: Dict[str, float]  # domain -> accuracy
    pillar_health: Dict[str, float]  # pillar -> success_rate
    trust_chain_size: int
    trust_chain_generations: Dict[int, int]  # generation -> count
    pending_discoveries: int
    active_learning_domains: List[str]
    recent_verifications: int
    hallucination_rate: float
    librarian_file_count: int
    librarian_code_files: int
    librarian_doc_files: int
    # Unified Memory System
    memory_mesh_connected: bool = False
    magma_connected: bool = False
    episodic_memory_count: int = 0
    procedural_memory_count: int = 0
    learning_example_count: int = 0
    learning_pattern_count: int = 0
    memory_mesh_links: int = 0
    magma_nodes: int = 0
    magma_relations: int = 0
    causal_chains: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ReasoningRequest:
    """A request for deep reasoning."""
    request_id: str
    task_type: ReasoningTaskType
    query: str
    context: Dict[str, Any] = field(default_factory=dict)
    require_evidence: bool = True
    max_reasoning_depth: int = 5


@dataclass
class ReasoningStep:
    """A single step in a reasoning chain."""
    step_number: int
    thought: str
    evidence: List[Dict[str, Any]]
    confidence: float
    sources_consulted: List[str]


@dataclass
class ReasoningResult:
    """Result of a deep reasoning task."""
    request_id: str
    task_type: ReasoningTaskType
    conclusion: str
    reasoning_chain: List[ReasoningStep]
    confidence: float
    evidence_count: int
    systems_consulted: List[str]
    recommendations: List[str]
    # Dual format outputs
    json_output: Dict[str, Any] = field(default_factory=dict)
    nlp_output: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DeepReasoningIntegration:
    """
    Deep Reasoning Integration Layer.

    Connects an advanced reasoning model (Kimi 2.5 or equivalent) to the
    entire Grace system in read-only capacity. The model can read from
    every subsystem, reason across all data, and produce insights.

    All internal communication is JSON. NLP is only generated at the
    boundary where a human or external LLM needs to read it.

    The reasoning engine doesn't hallucinate about Grace's internals
    because it reads actual system state, not assumptions.
    """

    def __init__(self):
        # Connected subsystems (read-only references)
        self._oracle = None
        self._source_index = None
        self._trust_chain = None
        self._discovery_engine = None
        self._competence_tracker = None
        self._pillar_tracker = None
        self._thermometer = None
        self._hallucination_guard = None
        self._librarian = None
        self._interrogator = None
        # Unified Memory System
        self._memory_mesh = None
        self._magma = None
        self._episodic_memory = None
        self._procedural_memory = None
        self._learning_memory = None

        # The reasoning handler (Kimi, or any advanced model)
        self._reasoning_handler: Optional[Callable] = None

        # Results log
        self.results: List[ReasoningResult] = []

        # Access permissions (enforce read-only)
        self._access_modes: Dict[str, AccessMode] = {}

        logger.info("[DEEP-REASONING] Integration layer initialized")

    # =========================================================================
    # CONNECTION MANAGEMENT (read-only)
    # =========================================================================

    def connect_oracle(self, oracle) -> None:
        """Connect Oracle Vector Store (read-only)."""
        self._oracle = oracle
        self._access_modes["oracle"] = AccessMode.READ_ONLY

    def connect_source_index(self, source_index) -> None:
        """Connect Source Code Index (read-only)."""
        self._source_index = source_index
        self._access_modes["source_index"] = AccessMode.READ_ONLY

    def connect_trust_chain(self, trust_chain: Dict) -> None:
        """Connect Trust Chain (read-only)."""
        self._trust_chain = trust_chain
        self._access_modes["trust_chain"] = AccessMode.READ_ONLY

    def connect_discovery(self, discovery) -> None:
        """Connect Discovery Engine (read-only)."""
        self._discovery_engine = discovery
        self._access_modes["discovery"] = AccessMode.READ_ONLY

    def connect_competence(self, competence) -> None:
        """Connect Competence Tracker (read-only)."""
        self._competence_tracker = competence
        self._access_modes["competence"] = AccessMode.READ_ONLY

    def connect_pillars(self, pillars) -> None:
        """Connect Pillar Tracker (read-only)."""
        self._pillar_tracker = pillars
        self._access_modes["pillars"] = AccessMode.READ_ONLY

    def connect_thermometer(self, thermometer) -> None:
        """Connect Trust Thermometer (read-only)."""
        self._thermometer = thermometer
        self._access_modes["thermometer"] = AccessMode.READ_ONLY

    def connect_hallucination_guard(self, guard) -> None:
        """Connect Hallucination Guard (read-only)."""
        self._hallucination_guard = guard
        self._access_modes["hallucination_guard"] = AccessMode.READ_ONLY

    def connect_librarian(self, librarian) -> None:
        """Connect Librarian (read-only)."""
        self._librarian = librarian
        self._access_modes["librarian"] = AccessMode.READ_ONLY

    def connect_interrogator(self, interrogator) -> None:
        """Connect Socratic Interrogator (read-only)."""
        self._interrogator = interrogator
        self._access_modes["interrogator"] = AccessMode.READ_ONLY

    # --- Unified Memory System connections ---

    def connect_memory_mesh(self, memory_mesh) -> None:
        """Connect Memory Mesh Integration (read-only)."""
        self._memory_mesh = memory_mesh
        self._access_modes["memory_mesh"] = AccessMode.READ_ONLY

    def connect_magma(self, magma) -> None:
        """Connect MAGMA unified memory (read-only)."""
        self._magma = magma
        self._access_modes["magma"] = AccessMode.READ_ONLY

    def connect_episodic_memory(self, episodic) -> None:
        """Connect Episodic Memory buffer (read-only)."""
        self._episodic_memory = episodic
        self._access_modes["episodic_memory"] = AccessMode.READ_ONLY

    def connect_procedural_memory(self, procedural) -> None:
        """Connect Procedural Memory repository (read-only)."""
        self._procedural_memory = procedural
        self._access_modes["procedural_memory"] = AccessMode.READ_ONLY

    def connect_learning_memory(self, learning) -> None:
        """Connect Learning Memory manager (read-only)."""
        self._learning_memory = learning
        self._access_modes["learning_memory"] = AccessMode.READ_ONLY

    def set_reasoning_handler(self, handler: Callable) -> None:
        """
        Set the reasoning model handler (Kimi 2.5, etc.)

        The handler receives a JSON context dict and returns a string.
        """
        self._reasoning_handler = handler

    def connect_all_from_loop(self, loop) -> None:
        """
        Connect all subsystems from a PerpetualLearningLoop instance.

        One-line connection to everything.
        """
        self.connect_oracle(loop.oracle)
        self.connect_source_index(loop.source_index)
        self.connect_trust_chain(loop.trust_chain)
        self.connect_discovery(loop.discovery)
        self.connect_librarian(loop.librarian)
        self.connect_hallucination_guard(loop.hallucination_guard)

    def connect_unified_memory(
        self,
        memory_mesh=None,
        magma=None,
        episodic=None,
        procedural=None,
        learning=None,
    ) -> None:
        """
        Connect the unified memory system (all at once).

        Args:
            memory_mesh: MemoryMeshIntegration instance
            magma: GraceMagmaSystem instance
            episodic: EpisodicBuffer instance
            procedural: ProceduralRepository instance
            learning: LearningMemoryManager instance
        """
        if memory_mesh:
            self.connect_memory_mesh(memory_mesh)
        if magma:
            self.connect_magma(magma)
        if episodic:
            self.connect_episodic_memory(episodic)
        if procedural:
            self.connect_procedural_memory(procedural)
        if learning:
            self.connect_learning_memory(learning)

    def query_memory(self, query: str, memory_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Query the unified memory system (read-only).

        Searches across all connected memory systems for relevant information.
        Returns structured JSON results.

        Args:
            query: What to search for
            memory_type: Optional filter (episodic, procedural, learning, magma, all)

        Returns:
            Dict with results from each memory system
        """
        results: Dict[str, Any] = {"query": query, "results": {}}

        # Query MAGMA (graph-based memory)
        if self._magma and memory_type in (None, "all", "magma"):
            try:
                magma_query = getattr(self._magma, 'query', None)
                if magma_query and callable(magma_query):
                    magma_results = magma_query(query)
                    results["results"]["magma"] = {
                        "found": bool(magma_results),
                        "data": magma_results if isinstance(magma_results, (list, dict)) else str(magma_results),
                    }
                else:
                    results["results"]["magma"] = {"found": False, "data": None}
            except Exception as e:
                results["results"]["magma"] = {"found": False, "error": str(e)}

        # Query Episodic Memory
        if self._episodic_memory and memory_type in (None, "all", "episodic"):
            try:
                recall = getattr(self._episodic_memory, 'recall', None)
                if recall and callable(recall):
                    episodes = recall(query)
                    results["results"]["episodic"] = {
                        "found": bool(episodes),
                        "count": len(episodes) if isinstance(episodes, list) else 0,
                        "data": episodes if isinstance(episodes, (list, dict)) else str(episodes) if episodes else None,
                    }
                else:
                    results["results"]["episodic"] = {"found": False, "data": None}
            except Exception as e:
                results["results"]["episodic"] = {"found": False, "error": str(e)}

        # Query Procedural Memory
        if self._procedural_memory and memory_type in (None, "all", "procedural"):
            try:
                find = getattr(self._procedural_memory, 'find_procedure', None)
                if find and callable(find):
                    procedures = find(query)
                    results["results"]["procedural"] = {
                        "found": bool(procedures),
                        "data": procedures if isinstance(procedures, (list, dict)) else str(procedures) if procedures else None,
                    }
                else:
                    results["results"]["procedural"] = {"found": False, "data": None}
            except Exception as e:
                results["results"]["procedural"] = {"found": False, "error": str(e)}

        # Query Learning Memory
        if self._learning_memory and memory_type in (None, "all", "learning"):
            try:
                search = getattr(self._learning_memory, 'search_examples', None)
                if search and callable(search):
                    examples = search(query)
                    results["results"]["learning"] = {
                        "found": bool(examples),
                        "count": len(examples) if isinstance(examples, list) else 0,
                        "data": examples if isinstance(examples, (list, dict)) else str(examples) if examples else None,
                    }
                else:
                    results["results"]["learning"] = {"found": False, "data": None}
            except Exception as e:
                results["results"]["learning"] = {"found": False, "error": str(e)}

        # Always query Oracle (if connected)
        if self._oracle and memory_type in (None, "all", "oracle"):
            try:
                oracle_results = self._oracle.search_by_content(query, limit=5)
                results["results"]["oracle"] = {
                    "found": bool(oracle_results),
                    "count": len(oracle_results),
                    "data": [
                        {"content": r.content[:200], "domain": r.domain, "trust": r.trust_score, "score": r.score}
                        for r in oracle_results
                    ],
                }
            except Exception as e:
                results["results"]["oracle"] = {"found": False, "error": str(e)}

        results["systems_queried"] = list(results["results"].keys())
        results["total_systems"] = len(results["systems_queried"])

        return results

    # =========================================================================
    # SYSTEM SNAPSHOT (read-only aggregate)
    # =========================================================================

    def take_snapshot(self) -> SystemSnapshot:
        """
        Take a read-only snapshot of all connected systems.

        This is the JSON context that gets sent to the reasoning model.
        No system is modified by taking a snapshot.
        """
        # Oracle stats
        oracle_domains = []
        oracle_count = 0
        oracle_stats = {}
        if self._oracle:
            oracle_domains = self._oracle.get_all_domains()
            oracle_count = len(self._oracle.records)
            oracle_stats = self._oracle.get_domain_stats()

        # Source code stats
        sc_modules = 0
        sc_functions = 0
        sc_classes = 0
        if self._source_index:
            sc_stats = self._source_index.get_stats()
            sc_modules = sc_stats.get("total_modules", 0)
            sc_functions = sc_stats.get("functions", 0)
            sc_classes = sc_stats.get("classes", 0)

        # Trust temperature
        trust_temp = 0.5
        if self._thermometer:
            trust_temp = self._thermometer.get_current_temperature()

        # Competence
        comp_domains = {}
        if self._competence_tracker:
            for domain, comp in getattr(self._competence_tracker, 'domains', {}).items():
                comp_domains[domain] = comp.accuracy

        # Pillar health
        pillar_health = {}
        if self._pillar_tracker:
            for pillar, kpi in getattr(self._pillar_tracker, 'kpis', {}).items():
                pillar_health[pillar.value if hasattr(pillar, 'value') else str(pillar)] = kpi.success_rate

        # Trust chain
        chain_size = 0
        chain_gens = {}
        if self._trust_chain:
            chain_size = len(self._trust_chain)
            for entry in self._trust_chain.values():
                gen = getattr(entry, 'generation', 0)
                chain_gens[gen] = chain_gens.get(gen, 0) + 1

        # Discovery
        pending_disc = 0
        active_domains = []
        if self._discovery_engine:
            disc_stats = self._discovery_engine.get_stats()
            pending_disc = disc_stats.get("queue_size", 0)
            active_domains = list(getattr(self._discovery_engine, '_domain_activity', {}).keys())

        # Hallucination guard
        verifications = 0
        halluc_rate = 0.0
        if self._hallucination_guard:
            hg_stats = self._hallucination_guard.get_stats()
            verifications = hg_stats.get("total_checks", 0)
            halluc_rate = 1.0 - hg_stats.get("grounding_rate", 1.0)

        # Librarian
        lib_files = 0
        lib_code = 0
        lib_docs = 0
        if self._librarian:
            lib_stats = self._librarian.get_stats()
            lib_files = lib_stats.get("total_files", 0)
            lib_code = lib_stats.get("code_files", 0)
            lib_docs = lib_stats.get("document_files", 0)

        # Unified Memory System
        mesh_connected = self._memory_mesh is not None
        magma_connected = self._magma is not None
        episodic_count = 0
        procedural_count = 0
        learning_ex_count = 0
        learning_pat_count = 0
        mesh_links = 0
        magma_nodes = 0
        magma_relations = 0
        causal_count = 0

        if self._episodic_memory:
            try:
                episodic_count = getattr(self._episodic_memory, 'episode_count', 0)
                if callable(episodic_count):
                    episodic_count = episodic_count()
            except Exception:
                pass

        if self._procedural_memory:
            try:
                procedural_count = getattr(self._procedural_memory, 'procedure_count', 0)
                if callable(procedural_count):
                    procedural_count = procedural_count()
            except Exception:
                pass

        if self._learning_memory:
            try:
                lm_stats = getattr(self._learning_memory, 'get_stats', None)
                if lm_stats and callable(lm_stats):
                    stats = lm_stats()
                    learning_ex_count = stats.get('total_examples', 0)
                    learning_pat_count = stats.get('total_patterns', 0)
            except Exception:
                pass

        if self._magma:
            try:
                magma_stats = getattr(self._magma, 'get_stats', None)
                if magma_stats and callable(magma_stats):
                    ms = magma_stats()
                    magma_nodes = ms.get('total_nodes', 0)
                    magma_relations = ms.get('total_relations', 0)
                    causal_count = ms.get('causal_chains', 0)
            except Exception:
                pass

        return SystemSnapshot(
            oracle_domains=oracle_domains,
            oracle_record_count=oracle_count,
            oracle_domain_stats=oracle_stats,
            source_code_modules=sc_modules,
            source_code_functions=sc_functions,
            source_code_classes=sc_classes,
            trust_temperature=trust_temp,
            competence_domains=comp_domains,
            pillar_health=pillar_health,
            trust_chain_size=chain_size,
            trust_chain_generations=chain_gens,
            pending_discoveries=pending_disc,
            active_learning_domains=active_domains,
            recent_verifications=verifications,
            hallucination_rate=halluc_rate,
            librarian_file_count=lib_files,
            librarian_code_files=lib_code,
            librarian_doc_files=lib_docs,
            memory_mesh_connected=mesh_connected,
            magma_connected=magma_connected,
            episodic_memory_count=episodic_count,
            procedural_memory_count=procedural_count,
            learning_example_count=learning_ex_count,
            learning_pattern_count=learning_pat_count,
            memory_mesh_links=mesh_links,
            magma_nodes=magma_nodes,
            magma_relations=magma_relations,
            causal_chains=causal_count,
        )

    # =========================================================================
    # REASONING TASKS
    # =========================================================================

    def reason(self, request: ReasoningRequest) -> ReasoningResult:
        """
        Execute a deep reasoning task.

        1. Takes a snapshot of all systems (read-only)
        2. Builds JSON context from snapshot + query
        3. Sends to reasoning model (Kimi)
        4. Parses response into structured chain
        5. Returns result in both JSON and NLP format
        """
        snapshot = self.take_snapshot()
        systems_consulted: List[str] = list(self._access_modes.keys())

        # Build reasoning context (JSON)
        context = self._build_reasoning_context(request, snapshot)

        # Get reasoning from handler or heuristic
        if self._reasoning_handler:
            try:
                raw_response = self._reasoning_handler(context)
                reasoning_chain = self._parse_reasoning_response(raw_response)
            except Exception as e:
                logger.warning(f"[DEEP-REASONING] Handler failed: {e}")
                reasoning_chain = self._heuristic_reasoning(request, snapshot)
        else:
            reasoning_chain = self._heuristic_reasoning(request, snapshot)

        # Calculate confidence from chain
        if reasoning_chain:
            confidence = sum(s.confidence for s in reasoning_chain) / len(reasoning_chain)
        else:
            confidence = 0.5

        # Build conclusion
        conclusion = self._build_conclusion(request, reasoning_chain, snapshot)

        # Generate recommendations
        recommendations = self._generate_recommendations(request, snapshot, reasoning_chain)

        # Build dual-format outputs
        json_output = {
            "request_id": request.request_id,
            "task_type": request.task_type.value,
            "conclusion": conclusion,
            "confidence": confidence,
            "evidence_count": sum(len(s.evidence) for s in reasoning_chain),
            "systems_consulted": systems_consulted,
            "reasoning_steps": [
                {
                    "step": s.step_number,
                    "thought": s.thought,
                    "confidence": s.confidence,
                    "sources": s.sources_consulted,
                }
                for s in reasoning_chain
            ],
            "recommendations": recommendations,
            "snapshot": {
                "oracle_records": snapshot.oracle_record_count,
                "oracle_domains": len(snapshot.oracle_domains),
                "trust_temperature": snapshot.trust_temperature,
                "source_code_modules": snapshot.source_code_modules,
            },
        }

        nlp_output = self._format_nlp(conclusion, reasoning_chain, recommendations, snapshot)

        result = ReasoningResult(
            request_id=request.request_id,
            task_type=request.task_type,
            conclusion=conclusion,
            reasoning_chain=reasoning_chain,
            confidence=confidence,
            evidence_count=sum(len(s.evidence) for s in reasoning_chain),
            systems_consulted=systems_consulted,
            recommendations=recommendations,
            json_output=json_output,
            nlp_output=nlp_output,
        )

        self.results.append(result)

        logger.info(
            f"[DEEP-REASONING] {request.task_type.value}: "
            f"{len(reasoning_chain)} steps, "
            f"confidence={confidence:.2f}, "
            f"{len(systems_consulted)} systems consulted"
        )

        return result

    def _build_reasoning_context(
        self, request: ReasoningRequest, snapshot: SystemSnapshot
    ) -> Dict[str, Any]:
        """Build JSON context for the reasoning model."""
        context = {
            "task": request.task_type.value,
            "query": request.query,
            "system_state": {
                "oracle_records": snapshot.oracle_record_count,
                "oracle_domains": snapshot.oracle_domains,
                "domain_stats": snapshot.oracle_domain_stats,
                "source_code": {
                    "modules": snapshot.source_code_modules,
                    "functions": snapshot.source_code_functions,
                    "classes": snapshot.source_code_classes,
                },
                "trust": {
                    "temperature": snapshot.trust_temperature,
                    "chain_size": snapshot.trust_chain_size,
                    "generations": snapshot.trust_chain_generations,
                },
                "competence": snapshot.competence_domains,
                "pillars": snapshot.pillar_health,
                "discovery": {
                    "pending": snapshot.pending_discoveries,
                    "active_domains": snapshot.active_learning_domains,
                },
                "hallucination_rate": snapshot.hallucination_rate,
                "files": {
                    "total": snapshot.librarian_file_count,
                    "code": snapshot.librarian_code_files,
                    "docs": snapshot.librarian_doc_files,
                },
                "unified_memory": {
                    "memory_mesh_connected": snapshot.memory_mesh_connected,
                    "magma_connected": snapshot.magma_connected,
                    "episodic_memories": snapshot.episodic_memory_count,
                    "procedural_memories": snapshot.procedural_memory_count,
                    "learning_examples": snapshot.learning_example_count,
                    "learning_patterns": snapshot.learning_pattern_count,
                    "magma_nodes": snapshot.magma_nodes,
                    "magma_relations": snapshot.magma_relations,
                    "causal_chains": snapshot.causal_chains,
                },
            },
            "user_context": request.context,
        }

        # Add domain-specific context from Oracle
        if self._oracle and request.context.get("domain"):
            domain = request.context["domain"]
            records = self._oracle.search_by_domain(domain, limit=5)
            context["domain_knowledge"] = [
                {"content": r.content[:200], "trust": r.trust_score}
                for r in records
            ]

        return context

    def _heuristic_reasoning(
        self, request: ReasoningRequest, snapshot: SystemSnapshot
    ) -> List[ReasoningStep]:
        """Heuristic reasoning when no external model is available."""
        steps: List[ReasoningStep] = []

        # Step 1: Assess system state including memory
        memory_summary = ""
        if snapshot.memory_mesh_connected or snapshot.magma_connected:
            memory_parts = []
            if snapshot.episodic_memory_count:
                memory_parts.append(f"{snapshot.episodic_memory_count} episodes")
            if snapshot.procedural_memory_count:
                memory_parts.append(f"{snapshot.procedural_memory_count} procedures")
            if snapshot.learning_example_count:
                memory_parts.append(f"{snapshot.learning_example_count} learning examples")
            if snapshot.magma_nodes:
                memory_parts.append(f"{snapshot.magma_nodes} MAGMA nodes")
            if memory_parts:
                memory_summary = f" Memory: {', '.join(memory_parts)}."
            else:
                memory_summary = " Unified memory systems connected."

        steps.append(ReasoningStep(
            step_number=1,
            thought=(
                f"System state: {snapshot.oracle_record_count} records across "
                f"{len(snapshot.oracle_domains)} domains. "
                f"Trust temperature: {snapshot.trust_temperature:.2f}. "
                f"{snapshot.source_code_modules} code modules indexed."
                f"{memory_summary}"
            ),
            evidence=[{"type": "system_snapshot", "records": snapshot.oracle_record_count}],
            confidence=0.9,
            sources_consulted=["oracle", "source_index", "thermometer", "unified_memory"],
        ))

        # Step 2: Address the query
        if request.task_type == ReasoningTaskType.GAP_ANALYSIS:
            steps.append(ReasoningStep(
                step_number=2,
                thought=(
                    f"Analyzing knowledge gaps. Known domains: "
                    f"{', '.join(snapshot.oracle_domains[:5])}. "
                    f"Pending discoveries: {snapshot.pending_discoveries}."
                ),
                evidence=[{"type": "domain_coverage", "domains": snapshot.oracle_domains}],
                confidence=0.7,
                sources_consulted=["oracle", "discovery"],
            ))
        elif request.task_type == ReasoningTaskType.STRATEGIC_PLANNING:
            steps.append(ReasoningStep(
                step_number=2,
                thought=(
                    f"Strategic assessment: "
                    f"strongest domains have most records, "
                    f"trust chain has {snapshot.trust_chain_size} entries. "
                    f"System should focus on deepening high-activity domains."
                ),
                evidence=[{"type": "strategy", "chain_size": snapshot.trust_chain_size}],
                confidence=0.65,
                sources_consulted=["trust_chain", "competence"],
            ))
        else:
            steps.append(ReasoningStep(
                step_number=2,
                thought=f"Analyzing query: {request.query[:200]}",
                evidence=[{"type": "query_analysis"}],
                confidence=0.6,
                sources_consulted=["oracle"],
            ))

        # Step 3: Synthesize
        steps.append(ReasoningStep(
            step_number=3,
            thought="Synthesis: combining evidence from all consulted systems.",
            evidence=[{"type": "synthesis", "systems": len(self._access_modes)}],
            confidence=0.7,
            sources_consulted=list(self._access_modes.keys()),
        ))

        return steps

    def _parse_reasoning_response(self, response: str) -> List[ReasoningStep]:
        """Parse a reasoning model's response into steps."""
        steps: List[ReasoningStep] = []
        lines = response.strip().split("\n")

        step_num = 1
        for line in lines:
            line = line.strip()
            if line and len(line) > 10:
                steps.append(ReasoningStep(
                    step_number=step_num,
                    thought=line,
                    evidence=[{"type": "model_output"}],
                    confidence=0.75,
                    sources_consulted=["reasoning_model"],
                ))
                step_num += 1

        if not steps:
            steps.append(ReasoningStep(
                step_number=1,
                thought=response[:500],
                evidence=[{"type": "model_output"}],
                confidence=0.6,
                sources_consulted=["reasoning_model"],
            ))

        return steps

    def _build_conclusion(
        self, request: ReasoningRequest,
        chain: List[ReasoningStep],
        snapshot: SystemSnapshot,
    ) -> str:
        """Build a conclusion from the reasoning chain."""
        if chain:
            last_thought = chain[-1].thought
            return (
                f"Based on analysis of {len(self._access_modes)} systems "
                f"({snapshot.oracle_record_count} records, "
                f"{len(snapshot.oracle_domains)} domains): {last_thought}"
            )
        return "Insufficient data for conclusive reasoning."

    def _generate_recommendations(
        self, request: ReasoningRequest,
        snapshot: SystemSnapshot,
        chain: List[ReasoningStep],
    ) -> List[str]:
        """Generate actionable recommendations."""
        recs: List[str] = []

        if snapshot.trust_temperature < 0.5:
            recs.append("Trust temperature is low. Increase verification before adding new content.")

        if snapshot.pending_discoveries > 20:
            recs.append(f"{snapshot.pending_discoveries} pending discoveries. Process the backlog.")

        if snapshot.oracle_record_count < 100:
            recs.append("Knowledge base is small. Prioritize ingestion from whitelist.")

        if snapshot.hallucination_rate > 0.2:
            recs.append(f"Hallucination rate is {snapshot.hallucination_rate:.0%}. Increase grounding.")

        if not recs:
            recs.append("System is operating within normal parameters.")

        return recs

    def _format_nlp(
        self, conclusion: str,
        chain: List[ReasoningStep],
        recommendations: List[str],
        snapshot: SystemSnapshot,
    ) -> str:
        """Format reasoning result as NLP for user/LLM consumption."""
        lines = [
            "Deep Reasoning Analysis",
            "=" * 40,
            "",
            f"Conclusion: {conclusion}",
            "",
            "Reasoning Chain:",
        ]
        for step in chain:
            lines.append(f"  {step.step_number}. {step.thought} (confidence: {step.confidence:.0%})")
        lines.append("")
        lines.append("Recommendations:")
        for rec in recommendations:
            lines.append(f"  - {rec}")
        lines.append("")
        lines.append(f"System: {snapshot.oracle_record_count} records, "
                      f"{len(snapshot.oracle_domains)} domains, "
                      f"trust={snapshot.trust_temperature:.2f}")
        return "\n".join(lines)

    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================

    def analyze_gaps(self, domain: Optional[str] = None) -> ReasoningResult:
        """Analyze knowledge gaps in the system."""
        return self.reason(ReasoningRequest(
            request_id=f"reason-{uuid.uuid4().hex[:12]}",
            task_type=ReasoningTaskType.GAP_ANALYSIS,
            query=f"What knowledge gaps exist{f' in {domain}' if domain else ''}?",
            context={"domain": domain} if domain else {},
        ))

    def plan_strategy(self) -> ReasoningResult:
        """Generate strategic learning plan."""
        return self.reason(ReasoningRequest(
            request_id=f"reason-{uuid.uuid4().hex[:12]}",
            task_type=ReasoningTaskType.STRATEGIC_PLANNING,
            query="What should Grace learn next and why?",
        ))

    def verify_claim(self, claim: str) -> ReasoningResult:
        """Deep verification of a claim across all systems."""
        return self.reason(ReasoningRequest(
            request_id=f"reason-{uuid.uuid4().hex[:12]}",
            task_type=ReasoningTaskType.VERIFICATION,
            query=f"Verify this claim across all systems: {claim}",
        ))

    def review_architecture(self) -> ReasoningResult:
        """Review system architecture."""
        return self.reason(ReasoningRequest(
            request_id=f"reason-{uuid.uuid4().hex[:12]}",
            task_type=ReasoningTaskType.ARCHITECTURE_REVIEW,
            query="Review the current system architecture for issues.",
        ))

    def get_connected_systems(self) -> Dict[str, str]:
        """Get list of connected systems with access modes."""
        return {
            name: mode.value for name, mode in self._access_modes.items()
        }

    def get_memory_connections(self) -> Dict[str, bool]:
        """Get which memory systems are connected."""
        return {
            "memory_mesh": self._memory_mesh is not None,
            "magma": self._magma is not None,
            "episodic_memory": self._episodic_memory is not None,
            "procedural_memory": self._procedural_memory is not None,
            "learning_memory": self._learning_memory is not None,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "connected_systems": len(self._access_modes),
            "systems": self.get_connected_systems(),
            "memory_connections": self.get_memory_connections(),
            "total_reasoning_tasks": len(self.results),
            "has_reasoning_handler": self._reasoning_handler is not None,
            "average_confidence": (
                sum(r.confidence for r in self.results) / len(self.results)
                if self.results else 0.0
            ),
        }
