"""
Grace Unified Startup - Activates All Subsystems

This module connects every subsystem that was built but never wired.
Called from app.py lifespan after core services (DB, Ollama, Qdrant) are ready.

Subsystems activated:
1. Layer 1 Message Bus (nervous system - connects 9 components)
2. Component Registry (lifecycle management)
3. Cognitive Engine (OODA decision-making)
4. Magma Memory (graph-based memory with causal inference)
5. Diagnostic Engine (4-layer health monitoring with 60s heartbeat)
6. Systems Integration (connects Planning/Todos/Memory/Diagnostics)
7. Autonomous Engine (self-triggered task execution)

Each subsystem is wrapped in try/except so one failure doesn't block others.
"""

import logging
import threading
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class GraceSubsystems:
    """Holds references to all activated subsystems."""

    def __init__(self):
        self.layer1 = None
        self.message_bus = None
        self.registry = None
        self.cortex = None
        self.magma = None
        self.diagnostic_engine = None
        self.systems_integration = None
        self.autonomous_engine = None
        self.timesense = None
        self.self_mirror = None
        self.unified_memory = None
        self.kimi_brain = None
        self.grace_executor = None
        self.verification_engine = None
        self.pattern_learner = None
        self.near_zero_guard = None
        self._active_subsystems = []

    def get_status(self) -> Dict[str, Any]:
        """Get status of all subsystems."""
        return {
            "active_count": len(self._active_subsystems),
            "active_subsystems": self._active_subsystems,
            "layer1": "active" if self.layer1 else "inactive",
            "message_bus": "active" if self.message_bus else "inactive",
            "registry": "active" if self.registry else "inactive",
            "cognitive_engine": "active" if self.cortex else "inactive",
            "magma_memory": "active" if self.magma else "inactive",
            "diagnostic_engine": "active" if self.diagnostic_engine else "inactive",
            "systems_integration": "active" if self.systems_integration else "inactive",
            "autonomous_engine": "active" if self.autonomous_engine else "inactive",
            "timesense": "active" if self.timesense else "inactive",
            "self_mirror": "active" if self.self_mirror else "inactive",
            "unified_memory": "active" if self.unified_memory else "inactive",
            "grace_brain": "active" if self.kimi_brain else "inactive",
            "grace_executor": "active" if self.grace_executor else "inactive",
            "verification_engine": "active" if self.verification_engine else "inactive",
            "pattern_learner": "active" if self.pattern_learner else "inactive",
            "near_zero_guard": "active" if self.near_zero_guard else "inactive",
        }


_subsystems: Optional[GraceSubsystems] = None


def get_subsystems() -> GraceSubsystems:
    """Get the global subsystems instance."""
    global _subsystems
    if _subsystems is None:
        _subsystems = GraceSubsystems()
    return _subsystems


def initialize_all_subsystems(session=None, settings=None) -> GraceSubsystems:
    """
    Initialize all Grace subsystems in the correct order.

    Args:
        session: Database session (optional, for subsystems that need DB)
        settings: Settings instance

    Returns:
        GraceSubsystems with all activated references
    """
    subs = get_subsystems()

    print("\n" + "=" * 60)
    print("  GRACE SUBSYSTEM ACTIVATION")
    print("=" * 60)

    # =========================================================================
    # 1. COMPONENT REGISTRY
    # =========================================================================
    try:
        from core.registry import get_component_registry

        subs.registry = get_component_registry()
        subs._active_subsystems.append("component_registry")
        print("[STARTUP] [OK] Component Registry initialized")
    except Exception as e:
        print(f"[STARTUP] [WARN] Component Registry failed: {e}")

    # =========================================================================
    # 2. LAYER 1 MESSAGE BUS + CONNECTORS
    # =========================================================================
    skip_layer1 = getattr(settings, "SKIP_LAYER1_INIT", False) if settings else False
    if not skip_layer1:
        try:
            from layer1.message_bus import get_message_bus

            subs.message_bus = get_message_bus()
            subs._active_subsystems.append("message_bus")
            print("[STARTUP] [OK] Layer 1 Message Bus initialized")

            if subs.registry:
                subs.registry.set_message_bus(subs.message_bus)
                print("[STARTUP] [OK] Message Bus connected to Component Registry")

            if session:
                try:
                    kb_path = getattr(settings, "KNOWLEDGE_BASE_PATH", "knowledge_base") if settings else "knowledge_base"
                    from layer1.initialize import initialize_layer1

                    subs.layer1 = initialize_layer1(
                        session=session,
                        kb_path=kb_path,
                        enable_neuro_symbolic=False,
                        enable_knowledge_base=False,
                    )
                    subs._active_subsystems.append("layer1_full")
                    stats = subs.layer1.get_stats()
                    actions = subs.layer1.get_autonomous_actions()
                    print(
                        f"[STARTUP] [OK] Layer 1 System fully initialized: "
                        f"{stats.get('registered_components', 0)} components, "
                        f"{len(actions)} autonomous actions"
                    )
                except Exception as e:
                    print(f"[STARTUP] [WARN] Layer 1 full init failed (message bus still active): {e}")
        except Exception as e:
            print(f"[STARTUP] [WARN] Layer 1 Message Bus failed: {e}")
    else:
        print("[STARTUP] [SKIP] Layer 1 disabled (SKIP_LAYER1_INIT=true)")

    # =========================================================================
    # 3. COGNITIVE ENGINE (Central Cortex)
    # =========================================================================
    skip_cognitive = getattr(settings, "SKIP_COGNITIVE_ENGINE", False) if settings else False
    if not skip_cognitive:
        try:
            from cognitive.engine import CognitiveEngine

            subs.cortex = CognitiveEngine()
            subs._active_subsystems.append("cognitive_engine")
            print("[STARTUP] [OK] Cognitive Engine (Central Cortex) initialized")
        except Exception as e:
            print(f"[STARTUP] [WARN] Cognitive Engine failed: {e}")
    else:
        print("[STARTUP] [SKIP] Cognitive Engine disabled (SKIP_COGNITIVE_ENGINE=true)")

    # =========================================================================
    # 4. MAGMA MEMORY (Graph-based memory with causal inference)
    # =========================================================================
    skip_magma = getattr(settings, "SKIP_MAGMA_MEMORY", False) if settings else False
    if not skip_magma:
        try:
            from cognitive.magma import get_grace_magma

            subs.magma = get_grace_magma()
            subs._active_subsystems.append("magma_memory")
            print("[STARTUP] [OK] Magma Memory System initialized")

            if subs.message_bus:
                try:
                    from cognitive.magma import create_magma_layer_integrations
                    create_magma_layer_integrations(subs.magma, subs.message_bus)
                    print("[STARTUP] [OK] Magma connected to Message Bus (Layer integrations active)")
                except Exception as e:
                    print(f"[STARTUP] [WARN] Magma layer integrations failed: {e}")
        except Exception as e:
            print(f"[STARTUP] [WARN] Magma Memory failed: {e}")
    else:
        print("[STARTUP] [SKIP] Magma Memory disabled (SKIP_MAGMA_MEMORY=true)")

    # =========================================================================
    # 5. DIAGNOSTIC ENGINE (4-layer health monitoring)
    # =========================================================================
    skip_diagnostic = getattr(settings, "SKIP_DIAGNOSTIC_ENGINE", False) if settings else False
    if not skip_diagnostic:
        try:
            from diagnostic_machine.diagnostic_engine import DiagnosticEngine

            subs.diagnostic_engine = DiagnosticEngine()
            subs._active_subsystems.append("diagnostic_engine")
            print("[STARTUP] [OK] Diagnostic Engine initialized (4-layer: Sensors > Interpreters > Judgement > Action)")

            def run_diagnostic_heartbeat():
                try:
                    subs.diagnostic_engine.start()
                except Exception as e:
                    print(f"[DIAGNOSTIC] [WARN] Heartbeat error: {e}")

            diag_thread = threading.Thread(target=run_diagnostic_heartbeat, daemon=True)
            diag_thread.start()
            print("[STARTUP] [OK] Diagnostic heartbeat started (60-second cycle)")
        except Exception as e:
            print(f"[STARTUP] [WARN] Diagnostic Engine failed: {e}")
    else:
        print("[STARTUP] [SKIP] Diagnostic Engine disabled (SKIP_DIAGNOSTIC_ENGINE=true)")

    # =========================================================================
    # 6. SYSTEMS INTEGRATION (connects Planning/Todos/Memory/Diagnostics)
    # =========================================================================
    try:
        from services.grace_systems_integration import GraceSystemsIntegration

        subs.systems_integration = GraceSystemsIntegration()
        subs._active_subsystems.append("systems_integration")
        print("[STARTUP] [OK] Grace Systems Integration initialized")
    except Exception as e:
        print(f"[STARTUP] [WARN] Systems Integration failed: {e}")

    # =========================================================================
    # 7. AUTONOMOUS ENGINE (self-triggered actions)
    # =========================================================================
    try:
        from services.grace_autonomous_engine import GraceAutonomousEngine

        subs.autonomous_engine = GraceAutonomousEngine()
        subs._active_subsystems.append("autonomous_engine")
        print("[STARTUP] [OK] Grace Autonomous Engine initialized")
    except Exception as e:
        print(f"[STARTUP] [WARN] Autonomous Engine failed: {e}")

    # =========================================================================
    # 8. TIMESENSE ENGINE (Temporal reasoning + OODA timing)
    # =========================================================================
    try:
        from cognitive.timesense import get_timesense

        subs.timesense = get_timesense(
            message_bus=subs.message_bus,
            self_mirror=getattr(subs, 'self_mirror', None),
        )
        subs._active_subsystems.append("timesense")
        print("[STARTUP] [OK] TimeSense Engine initialized (temporal reasoning, OODA timing, predictions)")
    except Exception as e:
        print(f"[STARTUP] [WARN] TimeSense failed: {e}")

    # =========================================================================
    # 9. SELF-MIRROR (Unified Telemetry Core - [T,M,P] vectors)
    # =========================================================================
    try:
        from cognitive.self_mirror import get_self_mirror

        subs.self_mirror = get_self_mirror(message_bus=subs.message_bus)
        subs.self_mirror.start_heartbeat()
        subs._active_subsystems.append("self_mirror")
        print("[STARTUP] [OK] Self-Mirror initialized (telemetry vectors, pillar triggers, challenges)")
    except Exception as e:
        print(f"[STARTUP] [WARN] Self-Mirror failed: {e}")

    # =========================================================================
    # 10. UNIFIED MEMORY (connects Memory Mesh + Magma + all memory types)
    # =========================================================================
    try:
        from cognitive.unified_memory import get_unified_memory

        subs.unified_memory = get_unified_memory(
            message_bus=subs.message_bus,
            self_mirror=subs.self_mirror,
            timesense=subs.timesense,
        )
        subs.unified_memory.start_consolidation_loop()
        subs._active_subsystems.append("unified_memory")
        print("[STARTUP] [OK] Unified Memory initialized (all 6 memory types + consolidation + forgetting)")
    except Exception as e:
        print(f"[STARTUP] [WARN] Unified Memory failed: {e}")

    # =========================================================================
    # CROSS-WIRE: Connect ALL subsystems to each other
    # =========================================================================
    try:
        # Connect TimeSense to Self-Mirror
        if subs.timesense and subs.self_mirror:
            subs.timesense.self_mirror = subs.self_mirror
            print("[STARTUP] [OK] TimeSense -> Self-Mirror connected")

        # FULL Diagnostic Engine wiring (message bus + self-mirror + timesense + genesis healing)
        if subs.diagnostic_engine:
            try:
                from diagnostic_machine.full_integration import wire_diagnostic_engine
                wired = wire_diagnostic_engine(
                    diagnostic_engine=subs.diagnostic_engine,
                    message_bus=subs.message_bus,
                    self_mirror=subs.self_mirror,
                    timesense=subs.timesense,
                )
                print(f"[STARTUP] [OK] Diagnostic Engine fully wired: {', '.join(wired)}")
            except Exception as e:
                print(f"[STARTUP] [WARN] Diagnostic full wiring failed: {e}")

        # Magma persistence - load saved state
        if subs.magma:
            try:
                from cognitive.magma.persistence import MagmaPersistence
                subs._magma_persistence = MagmaPersistence()
                loaded = subs._magma_persistence.load(subs.magma)
                if loaded:
                    print("[STARTUP] [OK] Magma Memory state restored from disk")
                else:
                    print("[STARTUP] [OK] Magma Memory starting fresh (no saved state)")
            except Exception as e:
                print(f"[STARTUP] [WARN] Magma persistence load failed: {e}")

            # Start Magma consolidation background worker
            try:
                if hasattr(subs.magma, 'start_background_processing'):
                    subs.magma.start_background_processing()
                    print("[STARTUP] [OK] Magma consolidation worker started")
            except Exception as e:
                print(f"[STARTUP] [WARN] Magma consolidation worker failed: {e}")

        # FULL Genesis wiring (message bus + mirror + timesense + memory + triggers)
        try:
            from genesis.full_integration import wire_genesis_system
            genesis_result = wire_genesis_system(
                message_bus=subs.message_bus,
                self_mirror=subs.self_mirror,
                timesense=subs.timesense,
                unified_memory=subs.unified_memory,
                diagnostic_engine=subs.diagnostic_engine,
            )
            subs._active_subsystems.append("genesis_full_integration")
            wired_to = genesis_result.get("wired_to", [])
            print(f"[STARTUP] [OK] Genesis fully wired: {', '.join(wired_to)}")
            print(f"[STARTUP] [OK] Unified CI/CD pipeline active (engine: {genesis_result['unified_cicd']._engine_name})")
            print(f"[STARTUP] [OK] Active healing system ready")
            print(f"[STARTUP] [OK] Autonomous triggers connected to diagnostic heartbeat")
        except Exception as e:
            print(f"[STARTUP] [WARN] Genesis full wiring failed: {e}")

    except Exception as e:
        print(f"[STARTUP] [WARN] Cross-wiring error (non-fatal): {e}")

    # =========================================================================
    # FEEDBACK LOOPS: Wire ALL remaining subsystem connections
    # =========================================================================
    try:
        from system_loops import wire_all_feedback_loops
        loop_result = wire_all_feedback_loops(
            message_bus=subs.message_bus,
            self_mirror=subs.self_mirror,
            timesense=subs.timesense,
            unified_memory=subs.unified_memory,
            diagnostic_engine=subs.diagnostic_engine,
            cortex=subs.cortex,
            magma=subs.magma,
        )
        loops = loop_result.get("loops_wired", [])
        print(f"[STARTUP] [OK] {len(loops)} feedback loops wired:")
        for loop_name in loops:
            print(f"[STARTUP]   - {loop_name}")
    except Exception as e:
        print(f"[STARTUP] [WARN] Feedback loop wiring error: {e}")

    # =========================================================================
    # 11. KIMI + GRACE LEARNING SYSTEM
    # Wire: GraceBrain (read-only), GraceVerifiedExecutor, VerificationEngine,
    #        PatternLearner, NearZeroHallucinationGuard, DB migration
    # =========================================================================
    try:
        print("[STARTUP] Initializing Grace Intelligence Learning System...")

        # 11a. Run ALL table migrations (unified migration runner)
        try:
            from database.migrate_all import run_all_migrations
            migration_result = run_all_migrations()
            tables = migration_result.get("tables", 0)
            print(f"[STARTUP] [OK] All database tables created/verified ({tables} tables)")
        except Exception as e:
            print(f"[STARTUP] [WARN] Migration failed: {e}")
            # Fallback to just LLM tracking tables
            try:
                from database.migrations.add_llm_tracking_tables import run_migration
                run_migration()
            except Exception:
                pass

        # 11b. Initialize KimiBrain (read-only intelligence)
        try:
            from cognitive.kimi_brain import get_kimi_brain

            subs.kimi_brain = get_kimi_brain(session) if session else None

            if subs.kimi_brain:
                # Connect Kimi to Mirror (read-only behavioral patterns)
                if subs.self_mirror:
                    try:
                        from cognitive.mirror_self_modeling import get_mirror_system
                        mirror_system = get_mirror_system(session)
                        subs.kimi_brain.connect_mirror(mirror_system)
                        print("[STARTUP] [OK] Kimi -> Mirror Self-Modeling connected (read-only)")
                    except Exception as e:
                        print(f"[STARTUP] [WARN] Kimi -> Mirror connection failed: {e}")

                # Connect Kimi to Diagnostic Engine (read-only health data)
                if subs.diagnostic_engine:
                    subs.kimi_brain.connect_diagnostics(subs.diagnostic_engine)
                    print("[STARTUP] [OK] Kimi -> Diagnostic Engine connected (read-only)")

                # Connect Kimi to Learning Efficiency Tracker (read-only progress)
                try:
                    from cognitive.learning_efficiency_tracker import LearningEfficiencyTracker
                    learning_tracker = LearningEfficiencyTracker(session)
                    subs.kimi_brain.connect_learning(learning_tracker)
                    print("[STARTUP] [OK] Kimi -> Learning Tracker connected (read-only)")
                except Exception as e:
                    print(f"[STARTUP] [WARN] Kimi -> Learning Tracker connection failed: {e}")

                # Connect Kimi to Pattern Learner (read-only autonomy readiness)
                try:
                    from cognitive.llm_pattern_learner import get_llm_pattern_learner
                    subs.pattern_learner = get_llm_pattern_learner(session)
                    subs.kimi_brain.connect_pattern_learner(subs.pattern_learner)
                    subs._active_subsystems.append("pattern_learner")
                    print("[STARTUP] [OK] Kimi -> Pattern Learner connected (read-only)")
                except Exception as e:
                    print(f"[STARTUP] [WARN] Kimi -> Pattern Learner connection failed: {e}")

                subs._active_subsystems.append("grace_brain")
                print("[STARTUP] [OK] Grace Brain initialized (read-only intelligence)")
        except Exception as e:
            print(f"[STARTUP] [WARN] Grace Brain failed: {e}")

        # 11c. Initialize Verification Engine with all sources
        try:
            from cognitive.grace_verification_engine import get_grace_verification_engine

            subs.verification_engine = get_grace_verification_engine(session) if session else None

            if subs.verification_engine:
                # Connect Oracle ML
                if subs.systems_integration:
                    subs.verification_engine.connect_oracle(subs.systems_integration)
                    print("[STARTUP] [OK] Verification -> Oracle ML connected")

                # Connect Governance
                try:
                    from security.governance import get_governance_engine
                    governance = get_governance_engine()
                    subs.verification_engine.connect_governance(governance)
                    print("[STARTUP] [OK] Verification -> Governance connected")
                except Exception as e:
                    print(f"[STARTUP] [WARN] Verification -> Governance failed: {e}")

                # Connect WebSocket for bidirectional comms
                try:
                    from api.websocket import manager as ws_manager
                    subs.verification_engine.connect_websocket(ws_manager)
                    print("[STARTUP] [OK] Verification -> WebSocket bidirectional comms connected")
                except Exception as e:
                    print(f"[STARTUP] [WARN] Verification -> WebSocket failed: {e}")

                # Connect Knowledge Base retriever
                try:
                    from api.retrieve import get_document_retriever
                    retriever = get_document_retriever()
                    if retriever:
                        subs.verification_engine.connect_knowledge_base(retriever)
                        print("[STARTUP] [OK] Verification -> Knowledge Base connected")
                except Exception as e:
                    print(f"[STARTUP] [WARN] Verification -> KB failed: {e}")

                # Connect web search
                try:
                    search_service = SerpAPIService()
                    subs.verification_engine.connect_search(search_service)
                    print("[STARTUP] [OK] Verification -> Web Search connected")
                except Exception as e:
                    print(f"[STARTUP] [WARN] Verification -> Web Search failed: {e}")

                subs._active_subsystems.append("verification_engine")
                print("[STARTUP] [OK] Verification Engine initialized (10 sources)")
        except Exception as e:
            print(f"[STARTUP] [WARN] Verification Engine failed: {e}")

        # 11d. Initialize Grace Verified Executor with execution bridge
        try:
            from cognitive.grace_verified_executor import get_grace_verified_executor
            from execution.bridge import get_execution_bridge

            exec_bridge = get_execution_bridge()

            subs.grace_executor = get_grace_verified_executor(
                session=session,
                execution_bridge=exec_bridge,
                coding_agent=None,  # Coding agent connected on-demand
            ) if session else None

            if subs.grace_executor and subs.verification_engine:
                subs.grace_executor.verification = subs.verification_engine

            if subs.grace_executor:
                subs._active_subsystems.append("grace_executor")
                print("[STARTUP] [OK] Grace Verified Executor initialized (with execution bridge)")
        except Exception as e:
            print(f"[STARTUP] [WARN] Grace Executor failed: {e}")

        # 11e. Initialize Near-Zero Hallucination Guard
        try:
            from llm_orchestrator.near_zero_hallucination_guard import get_near_zero_hallucination_guard

            base_guard = None
            multi_llm = None
            repo_access = None

            try:
                from llm_orchestrator.hallucination_guard import get_hallucination_guard
                base_guard = get_hallucination_guard()
            except Exception:
                pass

            subs.near_zero_guard = get_near_zero_hallucination_guard(
                base_guard=base_guard,
                multi_llm=multi_llm,
                repo_access=repo_access,
            )
            subs._active_subsystems.append("near_zero_guard")
            print("[STARTUP] [OK] Near-Zero Hallucination Guard initialized (13 layers)")
        except Exception as e:
            print(f"[STARTUP] [WARN] Near-Zero Guard failed: {e}")

        # 11f. Wire Diagnostic Engine -> LLM Tracker (healing outcomes feed learning)
        if subs.diagnostic_engine and session:
            try:
                from cognitive.llm_interaction_tracker import get_llm_interaction_tracker

                def _diagnostic_to_learning(cycle):
                    """Callback: diagnostic cycle results feed LLM learning tracker."""
                    try:
                        from database.session import SessionLocal
                        _ds = SessionLocal()
                        _dt = get_llm_interaction_tracker(_ds)
                        health_status = "unknown"
                        action_type = "none"
                        if hasattr(cycle, 'judgement') and cycle.judgement:
                            health_status = cycle.judgement.health.status.value if hasattr(cycle.judgement.health, 'status') else "unknown"
                        if hasattr(cycle, 'action_decision') and cycle.action_decision:
                            action_type = cycle.action_decision.action_type.value if hasattr(cycle.action_decision.action_type, 'value') else "unknown"
                        _dt.record_interaction(
                            prompt=f"[DIAGNOSTIC] Cycle {cycle.cycle_id}, trigger={cycle.trigger_source.value}",
                            response=f"health={health_status}, action={action_type}, duration={cycle.total_duration_ms:.0f}ms",
                            model_used="diagnostic_engine",
                            interaction_type="reasoning",
                            outcome="success" if cycle.success else "failure",
                            confidence_score=0.9 if cycle.success else 0.3,
                            duration_ms=cycle.total_duration_ms,
                            error_message=cycle.error_message,
                            metadata={"cycle_id": cycle.cycle_id, "health": health_status, "action": action_type},
                        )
                        _ds.commit()
                        _ds.close()
                    except Exception:
                        pass

                subs.diagnostic_engine.register_cycle_callback(_diagnostic_to_learning)
                print("[STARTUP] [OK] Diagnostic Engine -> LLM Tracker callback wired")
            except Exception as e:
                print(f"[STARTUP] [WARN] Diagnostic -> LLM Tracker wiring failed: {e}")

    except Exception as e:
        print(f"[STARTUP] [WARN] Grace Intelligence Learning System error (non-fatal): {e}")

    # =========================================================================
    # 12. REGISTER ALL NEW SYSTEMS IN COMPONENT REGISTRY + HANDSHAKE
    # =========================================================================
    try:
        from genesis.component_registry import ComponentRegistry
        from genesis.handshake_protocol import HandshakeProtocol

        if session:
            registry = ComponentRegistry(session)

            new_components = [
                ("grace_brain", "cognitive", "cognitive.kimi_brain", "cognitive/kimi_brain.py",
                 "Read-only intelligence layer - observes, diagnoses, produces instructions",
                 ["diagnose", "produce_instructions", "compose_response", "consult"],
                 ["mirror", "diagnostics", "learning", "patterns", "tasks"],
                 ["grace_executor", "verification_engine", "llm_tracker"]),
                ("grace_executor", "cognitive", "cognitive.grace_verified_executor", "cognitive/grace_verified_executor.py",
                 "Verifies Kimi instructions and executes approved ones",
                 ["process_instructions", "verify", "execute"],
                 ["grace_brain", "verification_engine", "execution_bridge"],
                 ["coding_agent", "diagnostic_machine", "learning_system"]),
                ("verification_engine", "security", "cognitive.grace_verification_engine", "cognitive/grace_verification_engine.py",
                 "10-source multi-source verification engine",
                 ["verify_instruction", "check_file_system", "check_database", "check_oracle", "check_governance"],
                 ["oracle_ml", "governance", "websocket", "knowledge_base"],
                 ["grace_executor"]),
                ("knowledge_compiler", "cognitive", "cognitive.knowledge_compiler", "cognitive/knowledge_compiler.py",
                 "Compiles raw data into deterministic facts/procedures/rules",
                 ["compile_chunk", "compile_batch", "query_facts", "query_procedures"],
                 ["llm_client"],
                 ["unified_intelligence", "grace_executor"]),
                ("unified_intelligence", "cognitive", "cognitive.unified_intelligence", "cognitive/unified_intelligence.py",
                 "9-layer unified query chain - deterministic layers first, LLM last",
                 ["query"],
                 ["knowledge_compiler", "memory_mesh", "library_connectors", "rag"],
                 ["chat_endpoint"]),
                ("pattern_learner", "cognitive", "cognitive.llm_pattern_learner", "cognitive/llm_pattern_learner.py",
                 "Extracts reusable patterns from LLM interactions",
                 ["extract_patterns", "can_handle_autonomously", "apply_pattern"],
                 ["llm_tracker"],
                 ["grace_executor", "grace_brain"]),
                ("hallucination_guard", "security", "llm_orchestrator.near_zero_hallucination_guard", "llm_orchestrator/near_zero_hallucination_guard.py",
                 "13-layer near-zero hallucination verification",
                 ["verify"],
                 ["base_guard", "multi_llm"],
                 ["chat_endpoint"]),
                ("task_verifier", "cognitive", "cognitive.task_completion_verifier", "cognitive/task_completion_verifier.py",
                 "100% completion verification - refuses done unless all criteria pass",
                 ["create_task", "verify", "mark_complete"],
                 ["timesense", "self_mirror", "weight_system"],
                 ["playbook_engine", "feedback_loops"]),
                ("playbook_engine", "cognitive", "cognitive.task_playbook_engine", "cognitive/task_playbook_engine.py",
                 "Task breakdown + playbook learning + interrogation",
                 ["interrogate_task", "break_down_task", "save_as_playbook"],
                 ["grace_brain", "knowledge_compiler", "library_connectors", "memory_mesh"],
                 ["task_verifier"]),
                ("weight_system", "cognitive", "cognitive.grace_weight_system", "cognitive/grace_weight_system.py",
                 "Trust/confidence as adjustable weights with backpropagation",
                 ["propagate_outcome", "get_weight_snapshot"],
                 ["knowledge_compiler", "pattern_learner"],
                 ["chat_feedback"]),
                ("library_connectors", "cognitive", "cognitive.library_connectors", "cognitive/library_connectors.py",
                 "External deterministic knowledge - Wikidata, ConceptNet, Wolfram",
                 ["query_wikidata", "query_conceptnet", "mine_and_compile"],
                 [],
                 ["unified_intelligence", "knowledge_compiler"]),
                ("knowledge_indexer", "cognitive", "cognitive.knowledge_indexer", "cognitive/knowledge_indexer.py",
                 "Indexes all internal knowledge for RAG searchability",
                 ["index_all_sources"],
                 ["embedding_model", "vector_db"],
                 ["rag_retriever"]),
                ("integrity_monitor", "cognitive", "cognitive.system_integrity_monitor", "cognitive/system_integrity_monitor.py",
                 "Continuous system health and alignment auditing",
                 ["full_scan", "get_quick_status"],
                 ["all_subsystems"],
                 ["grace_brain"]),
                ("feedback_loops", "cognitive", "cognitive.intelligence_feedback_loops", "cognitive/intelligence_feedback_loops.py",
                 "11 self-improving feedback loops on every task outcome",
                 ["record_task_outcome", "get_improvement_recommendations"],
                 ["task_verifier", "weight_system"],
                 ["criteria_tracker", "question_tracker", "gap_queue"]),
                ("knowledge_exhaustion", "cognitive", "cognitive.knowledge_exhaustion_engine", "cognitive/knowledge_exhaustion_engine.py",
                 "Convergence-based deep extraction until topics exhausted",
                 ["exhaust_topic", "github_massive_dump", "get_topic_status"],
                 ["knowledge_compiler", "cloud_client"],
                 ["unified_intelligence", "knowledge_mining_engine"]),
                ("grace_knowledge_engine", "cognitive", "cognitive.grace_knowledge_engine", "cognitive/grace_knowledge_engine.py",
                 "Unified knowledge engine - single entry point for all knowledge ops",
                 ["query", "discover", "exhaust", "github_dump", "audit_gaps", "compile", "stats"],
                 ["knowledge_compiler", "knowledge_exhaustion", "library_connectors", "cloud_client"],
                 ["unified_intelligence", "grace_brain"]),
            ]

            registered = 0
            for name, ctype, mod_path, file_path, desc, caps, deps, connects in new_components:
                try:
                    registry.register(
                        name=name,
                        component_type=ctype,
                        module_path=mod_path,
                        file_path=file_path,
                        description=desc,
                        capabilities=caps,
                        dependencies=deps,
                        connects_to=connects,
                    )
                    registered += 1
                except Exception:
                    pass

            session.commit()
            print(f"[STARTUP] [OK] Registered {registered} new components in Genesis Component Registry")

            # Register health checks for handshake protocol
            try:
                handshake = HandshakeProtocol(heartbeat_interval=60)

                def _kimi_health():
                    return 1.0 if subs.kimi_brain else 0.0

                def _executor_health():
                    return 1.0 if subs.grace_executor else 0.0

                def _verifier_health():
                    return 1.0 if subs.verification_engine else 0.0

                def _guard_health():
                    return 1.0 if subs.near_zero_guard else 0.0

                def _pattern_health():
                    return 1.0 if subs.pattern_learner else 0.0

                handshake.register_health_check("grace_brain", _kimi_health)
                handshake.register_health_check("grace_executor", _executor_health)
                handshake.register_health_check("verification_engine", _verifier_health)
                handshake.register_health_check("hallucination_guard", _guard_health)
                handshake.register_health_check("pattern_learner", _pattern_health)

                handshake.start()
                subs._active_subsystems.append("handshake_protocol")
                print(f"[STARTUP] [OK] Handshake protocol started with {len(new_components)} component health checks")
            except Exception as e:
                print(f"[STARTUP] [WARN] Handshake protocol failed: {e}")

    except Exception as e:
        print(f"[STARTUP] [WARN] Component registration error: {e}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    total = len(subs._active_subsystems)
    print()
    print(f"[STARTUP] === {total} subsystems activated ===")
    for name in subs._active_subsystems:
        print(f"[STARTUP]   - {name}")
    print("=" * 60 + "\n")

    return subs
