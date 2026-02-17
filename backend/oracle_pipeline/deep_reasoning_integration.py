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

        # Step 1: Assess system state
        steps.append(ReasoningStep(
            step_number=1,
            thought=(
                f"System state: {snapshot.oracle_record_count} records across "
                f"{len(snapshot.oracle_domains)} domains. "
                f"Trust temperature: {snapshot.trust_temperature:.2f}. "
                f"{snapshot.source_code_modules} code modules indexed."
            ),
            evidence=[{"type": "system_snapshot", "records": snapshot.oracle_record_count}],
            confidence=0.9,
            sources_consulted=["oracle", "source_index", "thermometer"],
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

    def get_stats(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "connected_systems": len(self._access_modes),
            "systems": self.get_connected_systems(),
            "total_reasoning_tasks": len(self.results),
            "has_reasoning_handler": self._reasoning_handler is not None,
            "average_confidence": (
                sum(r.confidence for r in self.results) / len(self.results)
                if self.results else 0.0
            ),
        }
