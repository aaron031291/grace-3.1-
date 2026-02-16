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
    # CROSS-WIRE: Connect subsystems to each other
    # =========================================================================
    try:
        # Connect TimeSense to Self-Mirror (timing feeds telemetry)
        if subs.timesense and subs.self_mirror:
            subs.timesense.self_mirror = subs.self_mirror
            print("[STARTUP] [OK] TimeSense -> Self-Mirror connected")

        # Connect Diagnostic Engine to Self-Mirror (scans feed telemetry)
        if subs.diagnostic_engine and subs.self_mirror:
            def on_diagnostic_cycle(cycle):
                """Feed diagnostic cycle timing into Self-Mirror."""
                try:
                    from cognitive.self_mirror import TelemetryVector
                    vector = TelemetryVector(
                        T=cycle.total_duration_ms,
                        M=0.0,
                        P=0.0 if cycle.success else 0.8,
                        component="diagnostic_engine",
                        task_domain="diagnostic_scan",
                    )
                    subs.self_mirror.receive_vector(vector)
                except Exception:
                    pass
            subs.diagnostic_engine._on_cycle_complete.append(on_diagnostic_cycle)
            print("[STARTUP] [OK] Diagnostic Engine -> Self-Mirror connected")

        # Connect Diagnostic Engine to Message Bus
        if subs.diagnostic_engine and subs.message_bus:
            def on_diagnostic_alert(alert_data):
                """Broadcast diagnostic alerts through message bus."""
                try:
                    import asyncio
                    from layer1.message_bus import ComponentType
                    asyncio.ensure_future(subs.message_bus.publish(
                        topic="diagnostic.alert",
                        payload={"alert": str(alert_data)},
                        from_component=ComponentType.COGNITIVE_ENGINE,
                        priority=8,
                    ))
                except Exception:
                    pass
            subs.diagnostic_engine._on_alert.append(on_diagnostic_alert)
            print("[STARTUP] [OK] Diagnostic Engine -> Message Bus connected")

    except Exception as e:
        print(f"[STARTUP] [WARN] Cross-wiring error (non-fatal): {e}")

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
