#!/usr/bin/env python3
"""
Forensic Deep Dive — Self-Healing System Consensus Analysis

Runs through Kimi and Opus to determine:
1. What subsystems need to be integrated into the self-healing module
2. What APIs need to be connected
3. What capabilities beyond the current 12 are needed
4. How to make the system truly self-healing, self-learning, self-building
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")


FORENSIC_PROMPT = """
You are conducting a forensic deep dive on Grace's self-healing system architecture.

Grace is an autonomous AI assistant with a comprehensive backend. The self-healing system currently has 12 capabilities:
1. database_reconnect
2. qdrant_reconnect  
3. llm_fallback (Ollama → Kimi)
4. memory_pressure (GC, cache clear)
5. connection_pool_reset
6. config_reload
7. embedding_model_reload
8. log_rotation
9. stub_detection
10. import_validation
11. kimi_diagnosis (AI-powered root cause analysis)
12. trend_prediction (memory/error trend forecasting)

Here is the COMPLETE inventory of Grace's subsystems that exist but are NOT yet integrated into the self-healing module:

=== COGNITIVE SUBSYSTEMS ===
- immune_system.py — GraceImmuneSystem: adaptive scan loop, anomaly detection (8 types), vaccination, healing playbook, rollback. Connected to TimeSense, OODA, Mirror, Trust, Kimi. Has API: /immune/scan, /immune/status, /immune/playbook
- deep_test_engine.py — Logic tests, integration tests, stress tests. Has start_stress_test(), stop_stress_test(). Failed tests trigger autonomous healing. API: /test/stress/start, /test/stress/stop
- ooda.py — OODALoop: observe/orient/decide/act cycle for system decisions
- mirror_self_modeling.py — MirrorSelfModelingSystem: behavioral pattern analysis, self-awareness score, improvement suggestions
- trust_engine.py — TrustEngine: trust scores for components, progressive autonomy
- time_sense.py — TimeSense: temporal awareness, adaptive timing for healing windows
- circuit_breaker.py — Circuit breaker with 41 named loops, depth limiting, loop detection
- consensus_engine.py — Multi-model roundtable (Opus + Kimi + Qwen + Reasoning)
- pipeline.py — Core cognitive pipeline
- sandbox_engine.py — Sandbox experimentation engine
- autonomous_sandbox_lab.py — AutonomousSandboxLab for safe testing
- autonomous_healing_loop.py — Autonomous healing loop
- autonomous_diagnostics.py — Autonomous startup diagnostics
- loop_orchestrator.py — Loop orchestration
- intelligence_layer.py — Intelligence layer
- hunter_assimilator.py — Hunter assimilator pattern
- reporting_engine.py — Report generation
- central_orchestrator.py — Central orchestration
- architecture_compass.py — Architecture guidance
- active_learning_system.py — Active learning
- idle_learner.py — Learning during idle time
- proactive_learner.py — Proactive learning
- system_registry.py — System component registry

=== DIAGNOSTIC MACHINE (4-layer) ===
- sensors.py — SensorLayer: system metrics, GraceMirrorData
- interpreters.py — InterpreterLayer: pattern analysis
- judgement.py — JudgementLayer: ForensicFinding, root cause
- action_router.py — ActionRouter: routes to OODA, Mirror, Sandbox, healing
- trend_analysis.py — TimeSeriesStore, TrendAnalyzer
- cognitive_integration.py — Learning memory, forensic insights storage
- notifications.py — Webhook, Slack, Email notification channels
- realtime.py — WebSocket live streaming to UI

=== GENESIS SYSTEM ===
- healing_system.py — Genesis Key-based code scanning and auto-repair
- autonomous_engine.py — AutonomousEngine: scheduled health checks, sandbox-first
- autonomous_triggers.py — Trigger pipeline on Genesis Key creation
- file_watcher.py — File system monitoring via watchdog

=== GRACE OS ===
- trust_scorekeeper.py — Trust score management
- message_bus.py — Internal message bus
- session_manager.py — Session management

=== TELEMETRY ===
- telemetry_service.py — Operation logging, performance baselines, drift detection
- replay_service.py — Telemetry replay for debugging
- decorators.py — Telemetry decorators

=== ML INTELLIGENCE ===
- ml_intelligence/ — ML features orchestrator

=== API ENDPOINTS NOT CONNECTED TO SELF-HEALING ===
- /immune/scan, /immune/status, /immune/playbook
- /test/stress/start, /test/stress/stop, /test/stress/status
- /diagnostic/* (full 4-layer diagnostic)
- /monitoring/organs (12 organs of Grace)
- /api/consensus/run (multi-model roundtable)
- /api/system-health/* (system health checks)
- /api/learn-heal/* (learning + healing triggers)
- /api/audit/* (system audit, circuit breaker)
- /api/telemetry/* (operation logs, baselines, drift)

=== CURRENT LIMITATIONS ===
The proactive healing engine runs as a background thread but:
- Does NOT integrate with the immune system's adaptive scan loop
- Does NOT use the diagnostic machine's 4-layer sensor/interpreter/judgement/action pipeline
- Does NOT leverage the OODA loop for decision-making
- Does NOT use Mirror self-modeling for behavioral baselines
- Does NOT connect to the stress test engine for load testing
- Does NOT use TimeSense for optimal healing windows
- Does NOT use the trust engine for progressive autonomy
- Does NOT connect to telemetry for drift detection
- Does NOT use the circuit breaker for loop prevention
- Does NOT trigger the consensus mechanism for complex decisions
- Does NOT feed healing outcomes to the learning memory system
- Does NOT use the notification system (Slack, webhook, email)

QUESTIONS TO ANSWER:

1. What SPECIFIC subsystems from the inventory above need to be directly integrated into the self-healing module? For each one, explain exactly HOW it should connect and what data flows between them.

2. What SPECIFIC API endpoints need to be connected, and what would the integration pattern look like?

3. Beyond the current 12 capabilities, what ADDITIONAL capabilities should the self-healing system have? Be specific — name them, describe what they do, what risk level they carry, and whether they should be autonomous or require approval.

4. What would a truly PROACTIVE (not reactive) self-healing architecture look like? How should the system prevent problems before they happen?

5. How should the immune system, diagnostic machine, OODA loop, mirror self-modeling, stress testing, telemetry, and trust engine work TOGETHER as a unified self-healing organism?

6. What are the critical data flows that need to exist between these systems for real-time healing?

7. What capabilities would make this system truly SELF-BUILDING — able to expand its own healing capabilities over time?

Provide a detailed, actionable architecture with specific integration points, data flows, and implementation priorities.
"""

SYSTEM_PROMPT = (
    "You are a senior systems architect specializing in autonomous self-healing systems. "
    "You are conducting a forensic deep dive on an AI assistant's self-healing architecture. "
    "Be extremely specific and technical. Name exact files, functions, data flows, and integration patterns. "
    "Your output will be used as an engineering specification to build the integration."
)

def run_consensus():
    """Run the forensic analysis through available models."""
    print("=" * 80)
    print("FORENSIC DEEP DIVE — Self-Healing System Consensus Analysis")
    print(f"Started: {datetime.utcnow().isoformat()}")
    print("=" * 80)

    results = {}

    # Try Kimi
    print("\n[1/2] Running analysis through Kimi K2.5...")
    try:
        from llm_orchestrator.factory import get_kimi_client
        client = get_kimi_client()
        if client.is_running():
            response = client.generate(
                prompt=FORENSIC_PROMPT,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.4,
                max_tokens=8192,
            )
            results["kimi"] = response
            print(f"  [OK] Kimi response received ({len(response)} chars)")
        else:
            print("  [SKIP] Kimi not available")
    except Exception as e:
        print(f"  [FAIL] Kimi: {e}")

    # Try Opus
    print("\n[2/2] Running analysis through Opus (Claude)...")
    try:
        from llm_orchestrator.factory import get_opus_client
        client = get_opus_client()
        if client.is_running():
            response = client.generate(
                prompt=FORENSIC_PROMPT,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.4,
                max_tokens=8192,
            )
            results["opus"] = response
            print(f"  [OK] Opus response received ({len(response)} chars)")
        else:
            print("  [SKIP] Opus not available")
    except Exception as e:
        print(f"  [FAIL] Opus: {e}")

    if not results:
        print("\n[WARN] No cloud models available. Generating analysis from codebase knowledge.\n")
        return generate_local_analysis()

    # If we have both, try consensus synthesis
    if len(results) >= 2:
        print("\n[CONSENSUS] Synthesizing Kimi + Opus responses...")
        try:
            from cognitive.consensus_engine import layer2_consensus, ModelResponse
            responses = []
            for model_id, text in results.items():
                responses.append(ModelResponse(
                    model_id=model_id,
                    model_name=f"{model_id.title()} Analysis",
                    response=text,
                    latency_ms=0,
                ))
            consensus_text, agreements, disagreements = layer2_consensus(
                FORENSIC_PROMPT, responses, synthesizer_model="kimi"
            )
            results["consensus"] = consensus_text
            results["agreements"] = agreements
            results["disagreements"] = disagreements
            print(f"  [OK] Consensus formed ({len(agreements)} agreements, {len(disagreements)} disagreements)")
        except Exception as e:
            print(f"  [WARN] Consensus synthesis failed: {e}")

    # Save results
    output_dir = Path(__file__).parent.parent / "data" / "self_healing_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"forensic_analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.utcnow().isoformat(),
            "prompt": FORENSIC_PROMPT[:500] + "...",
            "results": results,
        }, f, indent=2, default=str)

    print(f"\n[SAVED] Full analysis saved to: {output_file}")

    # Print results
    for model_id, text in results.items():
        if model_id in ("agreements", "disagreements"):
            continue
        print(f"\n{'=' * 80}")
        print(f"  {model_id.upper()} ANALYSIS")
        print(f"{'=' * 80}\n")
        print(text if isinstance(text, str) else json.dumps(text, indent=2))

    return results


def generate_local_analysis():
    """Generate the analysis locally from codebase knowledge when no cloud models available."""
    analysis = build_comprehensive_analysis()

    output_dir = Path(__file__).parent.parent / "data" / "self_healing_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"forensic_analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    with open(output_file, "w") as f:
        json.dump({
            "timestamp": datetime.utcnow().isoformat(),
            "source": "codebase_forensic_analysis",
            "results": analysis,
        }, f, indent=2, default=str)

    print(f"[SAVED] Analysis saved to: {output_file}")

    # Print it
    print(json.dumps(analysis, indent=2))
    return analysis


def build_comprehensive_analysis():
    """Build the comprehensive analysis from codebase knowledge."""
    return {
        "subsystem_integrations_required": {
            "priority_1_critical": [
                {
                    "subsystem": "immune_system.py (GraceImmuneSystem)",
                    "integration": "Merge proactive engine's monitoring loop WITH immune system's adaptive scan loop. The immune system already has anomaly detection (8 types), vaccination, healing playbook, and rollback. The proactive engine should DELEGATE health assessment to the immune system rather than duplicating it.",
                    "data_flow": "ProactiveEngine → ImmuneSystem.scan() → AnomalyResult → ProactiveEngine.handle_anomaly()",
                    "api_connection": "/immune/scan, /immune/status, /immune/playbook",
                    "files": ["cognitive/immune_system.py", "api/system_health_api.py"],
                },
                {
                    "subsystem": "diagnostic_machine (4-layer pipeline)",
                    "integration": "Feed diagnostic machine sensor data into proactive engine trend analysis. Use interpreter layer for pattern detection, judgement layer for forensic findings, action router for healing dispatch.",
                    "data_flow": "Sensors → Interpreters → Judgement → ActionRouter → HealingEngine",
                    "api_connection": "/diagnostic/*, /diagnostic/forensics",
                    "files": ["diagnostic_machine/sensors.py", "diagnostic_machine/interpreters.py", "diagnostic_machine/judgement.py", "diagnostic_machine/action_router.py"],
                },
                {
                    "subsystem": "deep_test_engine.py (Stress Testing)",
                    "integration": "Stress test results should feed directly into self-healing. When stress tests fail, the healing system should be notified immediately and attempt remediation. Stress test should also run AFTER healing to verify the fix worked.",
                    "data_flow": "StressTest.fail → ProactiveEngine.handle_issue() → heal → StressTest.verify()",
                    "api_connection": "/test/stress/start, /test/stress/stop, /test/stress/status",
                    "files": ["cognitive/deep_test_engine.py", "api/system_audit_api.py"],
                },
            ],
            "priority_2_important": [
                {
                    "subsystem": "ooda.py (OODALoop)",
                    "integration": "Use OODA for healing decision-making. Observe: collect metrics. Orient: compare against baselines. Decide: select healing action. Act: execute. This replaces the simple if/else logic in handle_issue().",
                    "data_flow": "Metrics → OODA.observe() → orient() → decide() → act() → HealingAction",
                    "files": ["cognitive/ooda.py"],
                },
                {
                    "subsystem": "mirror_self_modeling.py",
                    "integration": "Use mirror's behavioral baselines as the NORMAL against which anomalies are detected. Mirror should observe healing patterns and suggest improvements.",
                    "data_flow": "Mirror.build_self_model() → baseline → ProactiveEngine.compare(current, baseline)",
                    "files": ["cognitive/mirror_self_modeling.py"],
                },
                {
                    "subsystem": "trust_engine.py",
                    "integration": "Use trust scores to gate autonomous healing. High-trust actions execute automatically. Low-trust actions require governance approval. Trust should increase on successful heals, decrease on failures.",
                    "data_flow": "HealingAction → TrustEngine.check_permission() → execute/defer → TrustEngine.record_outcome()",
                    "files": ["cognitive/trust_engine.py"],
                },
                {
                    "subsystem": "time_sense.py (TimeSense)",
                    "integration": "Use temporal awareness to schedule healing at optimal times. Avoid healing during peak usage. Detect time-based patterns (e.g., memory leak every 2 hours).",
                    "data_flow": "TimeSense.best_window() → schedule_healing() | TimeSense.detect_temporal_pattern()",
                    "files": ["cognitive/time_sense.py"],
                },
            ],
            "priority_3_enhancement": [
                {
                    "subsystem": "circuit_breaker.py",
                    "integration": "Wrap healing actions in circuit breakers to prevent healing loops (healing that causes more damage). 41 named loops already exist — add healing-specific ones.",
                    "data_flow": "CircuitBreaker.enter_loop('healing:db_reconnect') → heal → exit_loop()",
                    "files": ["cognitive/circuit_breaker.py"],
                },
                {
                    "subsystem": "consensus_engine.py",
                    "integration": "For CRITICAL healing decisions (state rollback, isolation, emergency shutdown), run through multi-model consensus before executing.",
                    "data_flow": "CriticalAction → consensus.run(models=['kimi','opus']) → approve/deny → execute",
                    "files": ["cognitive/consensus_engine.py"],
                },
                {
                    "subsystem": "telemetry (telemetry_service.py)",
                    "integration": "Log every healing action to telemetry. Use performance baselines for drift detection. Replay telemetry to debug failed healings.",
                    "data_flow": "HealingAction → TelemetryService.log_operation() | TelemetryService.check_drift() → alert",
                    "files": ["telemetry/telemetry_service.py", "telemetry/replay_service.py"],
                },
                {
                    "subsystem": "notifications.py",
                    "integration": "Send notifications on critical healing events via configured channels (Slack, webhook, email).",
                    "data_flow": "CriticalHealing → NotificationManager.notify() → Slack/Email/Webhook",
                    "files": ["diagnostic_machine/notifications.py"],
                },
                {
                    "subsystem": "learning_memory / LearningExample",
                    "integration": "Store every healing outcome as a learning example. Build a healing playbook that improves over time.",
                    "data_flow": "HealingOutcome → LearningExample(topic='healing:action', outcome=success/fail) → DB",
                    "files": ["cognitive/learning_memory.py"],
                },
                {
                    "subsystem": "realtime.py (WebSocket)",
                    "integration": "Broadcast healing events to connected UI clients in real-time.",
                    "data_flow": "HealingEvent → DiagnosticEventEmitter.emit_healing_*() → WebSocket clients",
                    "files": ["diagnostic_machine/realtime.py"],
                },
            ],
        },
        "additional_capabilities_beyond_12": [
            {
                "id": 13,
                "name": "immune_adaptive_scan",
                "description": "Delegate to GraceImmuneSystem for adaptive interval scanning with anomaly type detection (8 types: performance degradation, memory leak, resource exhaustion, cascade failure, pattern drift, security anomaly, service down, code error)",
                "risk": "low",
                "autonomous": True,
            },
            {
                "id": 14,
                "name": "stress_test_verification",
                "description": "Run targeted stress tests after healing to verify the fix holds under load. Failed verification triggers re-healing with escalated strategy.",
                "risk": "medium",
                "autonomous": True,
            },
            {
                "id": 15,
                "name": "forensic_root_cause",
                "description": "Use diagnostic machine's 4-layer pipeline (sensors → interpreters → judgement → action) for deep forensic root cause analysis before healing.",
                "risk": "low",
                "autonomous": True,
            },
            {
                "id": 16,
                "name": "ooda_decision_loop",
                "description": "Route healing decisions through OODA (observe/orient/decide/act) for structured decision-making rather than simple threshold checks.",
                "risk": "low",
                "autonomous": True,
            },
            {
                "id": 17,
                "name": "behavioral_baseline_comparison",
                "description": "Use mirror self-modeling to maintain behavioral baselines and detect anomalies as deviations from normal patterns.",
                "risk": "low",
                "autonomous": True,
            },
            {
                "id": 18,
                "name": "vaccination_proactive_hardening",
                "description": "After healing a recurring issue, apply the immune system's vaccination mechanism to proactively harden against recurrence.",
                "risk": "medium",
                "autonomous": True,
            },
            {
                "id": 19,
                "name": "temporal_pattern_healing",
                "description": "Use TimeSense to detect time-based failure patterns (e.g., memory leak every 2 hours) and schedule preemptive healing.",
                "risk": "low",
                "autonomous": True,
            },
            {
                "id": 20,
                "name": "cascade_failure_prevention",
                "description": "Detect cascade failure patterns where one service failure triggers others. Isolate affected components before cascade propagates.",
                "risk": "high",
                "autonomous": False,
            },
            {
                "id": 21,
                "name": "drift_detection_healing",
                "description": "Use telemetry's drift detection to identify when system behavior drifts from established baselines and trigger corrective healing.",
                "risk": "medium",
                "autonomous": True,
            },
            {
                "id": 22,
                "name": "consensus_critical_decisions",
                "description": "For critical/destructive healing actions (rollback, isolation, shutdown), run through multi-model consensus (Kimi + Opus) before executing.",
                "risk": "low",
                "autonomous": True,
            },
            {
                "id": 23,
                "name": "healing_playbook_learning",
                "description": "Build a structured healing playbook from outcomes. Each healing attempt creates a learning example. Over time, the playbook becomes the primary decision source.",
                "risk": "low",
                "autonomous": True,
            },
            {
                "id": 24,
                "name": "circuit_breaker_loop_prevention",
                "description": "Wrap all healing actions in circuit breakers to prevent healing loops where a fix causes new damage that triggers more healing.",
                "risk": "low",
                "autonomous": True,
            },
            {
                "id": 25,
                "name": "sandbox_safe_testing",
                "description": "Before applying risky healing actions to production, test them in the sandbox first. Only apply if sandbox verification passes.",
                "risk": "low",
                "autonomous": True,
            },
            {
                "id": 26,
                "name": "realtime_ui_broadcast",
                "description": "Broadcast all healing events, predictions, and decisions to the UI via WebSocket for real-time visibility.",
                "risk": "none",
                "autonomous": True,
            },
            {
                "id": 27,
                "name": "notification_escalation",
                "description": "Send Slack/webhook/email notifications for critical healing events. Escalation ladder: log → UI → Slack → email based on severity.",
                "risk": "none",
                "autonomous": True,
            },
            {
                "id": 28,
                "name": "self_capability_expansion",
                "description": "When the system encounters a problem it cannot heal, it creates a capability gap report, uses Kimi to design a healing strategy, tests it in sandbox, and if governance approves, adds it as a new capability.",
                "risk": "high",
                "autonomous": False,
            },
            {
                "id": 29,
                "name": "code_repair_via_coding_agent",
                "description": "For code-level issues (broken imports, syntax errors, stub code), delegate to the unified coding agent for automated repair with genesis key tracking.",
                "risk": "high",
                "autonomous": False,
            },
            {
                "id": 30,
                "name": "autonomous_rollback",
                "description": "Maintain state snapshots before healing. If healing makes things worse (verified by stress test), automatically rollback to pre-healing state.",
                "risk": "medium",
                "autonomous": True,
            },
        ],
        "unified_architecture": {
            "description": "The Immune System should be the ORCHESTRATOR that coordinates all healing. The Proactive Engine provides the real-time monitoring loop. The Diagnostic Machine provides deep analysis. The OODA loop provides decision structure. Mirror provides baselines. Trust gates autonomy. TimeSense schedules windows. Stress tests verify fixes.",
            "data_flow_diagram": [
                "ProactiveEngine (monitoring loop, every 30s)",
                "  → collects metrics (psutil, DB, Qdrant, LLM, error counts)",
                "  → feeds to DiagnosticMachine.sensors",
                "  → DiagnosticMachine.interpreters (pattern analysis)",
                "  → DiagnosticMachine.judgement (forensic findings, root cause)",
                "  → feeds anomalies to ImmuneSystem.scan()",
                "  → ImmuneSystem uses OODA: observe(metrics) → orient(baselines from Mirror) → decide(action) → act(heal)",
                "  → TrustEngine.check_permission(action) → allow/deny/escalate",
                "  → TimeSense.best_window() → schedule or execute now",
                "  → CircuitBreaker.enter_loop('healing:action') → prevent healing loops",
                "  → Execute healing action",
                "  → StressTest.verify(post_healing) → pass/fail",
                "  → If fail: rollback, escalate, try alternative",
                "  → If pass: TrustEngine.record_success(), LearningMemory.store(outcome)",
                "  → ImmuneSystem.vaccinate(pattern) → prevent recurrence",
                "  → TelemetryService.log(healing_operation)",
                "  → NotificationManager.notify(if critical)",
                "  → RealtimeEmitter.broadcast(healing_event) → UI",
                "  → If beyond capability: ConsensusEngine.run(models=['kimi','opus']) → governance approval",
                "  → If capability gap: create gap report → Kimi designs solution → sandbox test → governance approval → add capability",
            ],
        },
        "implementation_priority": [
            "Phase 1 (Immediate): Integrate immune system + diagnostic machine + stress test verification",
            "Phase 2 (Next): Add OODA decision-making + mirror baselines + trust gating + TimeSense scheduling",
            "Phase 3 (Enhancement): Circuit breaker + consensus for critical decisions + telemetry drift detection",
            "Phase 4 (Self-Building): Healing playbook learning + self-capability expansion + autonomous rollback + sandbox safe testing",
            "Phase 5 (Full Autonomy): Real-time UI broadcast + notification escalation + code repair via coding agent",
        ],
    }


if __name__ == "__main__":
    run_consensus()
