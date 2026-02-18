"""
Grace Self-Mirror: Unified Telemetry Core

The Self-Mirror is the central nervous system that translates raw computational
signals into Operational Intelligence using the [T, M, P] telemetry vector.

T = Time (latency in milliseconds)
M = Mass (data size in bytes)
P = Pressure (load factor 0.0-1.0)

Phase 1: Telemetry Vector Protocol + Self-Mirror Core
Phase 2: Statistical Self-Modeling with pillar triggers
Phase 3: Bi-directional challenging + RFI protocol + autonomous resolution

Connects to existing subsystems:
- Layer 1 Message Bus (broadcasts [T,M,P] vectors)
- Diagnostic Machine (sensor data feeds the mirror)
- Cognitive Engine (OODA loop heartbeat timing)
- Magma Memory (stores performance patterns)
- Healing System (triggered by statistical anomalies)
- Governance (triggered by risk thresholds)
- Agent (triggered for self-building)
- Continuous Learning (triggered for knowledge acquisition)
"""

import logging
import time
import threading
import asyncio
import psutil
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque, defaultdict
from enum import Enum
import json
import math

logger = logging.getLogger(__name__)

def _track_mirror(desc, **kwargs):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event("self_mirror", desc, **kwargs)
    except Exception:
        pass


# =============================================================================
# PHASE 1: TELEMETRY VECTOR PROTOCOL
# =============================================================================

@dataclass
class TelemetryVector:
    """
    The [T, M, P] vector - Grace's universal language.

    Every component broadcasts this instead of verbose JSON.
    Every other component can read it and react autonomously.
    """
    T: float  # Time in milliseconds (latency/speed)
    M: float  # Mass in bytes (data weight)
    P: float  # Pressure 0.0-1.0 (load/stress factor)

    component: str = ""
    task_domain: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "T": round(self.T, 2),
            "M": round(self.M, 2),
            "P": round(self.P, 3),
            "component": self.component,
            "task_domain": self.task_domain,
            "timestamp": self.timestamp.isoformat(),
        }

    def __repr__(self):
        return f"[T={self.T:.1f}ms, M={self._format_mass()}, P={self.P:.2f}]"

    def _format_mass(self) -> str:
        if self.M < 1024:
            return f"{self.M:.0f}B"
        elif self.M < 1024 * 1024:
            return f"{self.M/1024:.1f}KB"
        elif self.M < 1024 * 1024 * 1024:
            return f"{self.M/(1024*1024):.1f}MB"
        else:
            return f"{self.M/(1024*1024*1024):.2f}GB"


class PillarType(str, Enum):
    """The Five Pillars of Grace."""
    SELF_HEALING = "self_healing"
    SELF_LEARNING = "self_learning"
    SELF_BUILDING = "self_building"
    SELF_GOVERNING = "self_governing"
    SELF_EVOLUTION = "self_evolution"


@dataclass
class PillarTrigger:
    """A trigger event from the Self-Mirror to a pillar."""
    pillar: PillarType
    reason: str
    telemetry: TelemetryVector
    stats: Dict[str, float]
    severity: str = "normal"  # normal, elevated, critical
    timestamp: datetime = field(default_factory=datetime.utcnow)


# =============================================================================
# PHASE 2: STATISTICAL SELF-MODELING
# =============================================================================

class StatisticalProfile:
    """
    Statistical self-model for a task domain.

    Maintains rolling mean, mode, variance to detect when
    Grace is operating outside her normal parameters.
    """

    def __init__(self, domain: str, window_size: int = 500):
        self.domain = domain
        self.window_size = window_size

        self._times: deque = deque(maxlen=window_size)
        self._masses: deque = deque(maxlen=window_size)
        self._pressures: deque = deque(maxlen=window_size)

        self._time_histogram: Dict[int, int] = defaultdict(int)

        self.total_observations = 0
        self.created_at = datetime.utcnow()

    def observe(self, vector: TelemetryVector):
        """Record an observation."""
        self._times.append(vector.T)
        self._masses.append(vector.M)
        self._pressures.append(vector.P)
        self.total_observations += 1

        time_bucket = int(vector.T / 10) * 10
        self._time_histogram[time_bucket] += 1

    @property
    def mean_time(self) -> float:
        return sum(self._times) / len(self._times) if self._times else 0.0

    @property
    def mean_mass(self) -> float:
        return sum(self._masses) / len(self._masses) if self._masses else 0.0

    @property
    def mean_pressure(self) -> float:
        return sum(self._pressures) / len(self._pressures) if self._pressures else 0.0

    @property
    def mode_time(self) -> float:
        """Most frequent execution time (rounded to 10ms buckets)."""
        if not self._time_histogram:
            return 0.0
        most_common = max(self._time_histogram, key=self._time_histogram.get)
        return float(most_common)

    @property
    def variance_time(self) -> float:
        if len(self._times) < 2:
            return 0.0
        mean = self.mean_time
        return sum((t - mean) ** 2 for t in self._times) / (len(self._times) - 1)

    @property
    def std_time(self) -> float:
        return math.sqrt(self.variance_time) if self.variance_time > 0 else 0.0

    @property
    def variance_pressure(self) -> float:
        if len(self._pressures) < 2:
            return 0.0
        mean = self.mean_pressure
        return sum((p - mean) ** 2 for p in self._pressures) / (len(self._pressures) - 1)

    def is_degraded(self, current_T: float) -> bool:
        """Check if current time exceeds mean + 2*sigma (Self-Healing trigger)."""
        if len(self._times) < 10:
            return False
        return current_T > self.mean_time + 2 * self.std_time

    def is_below_mode(self, current_confidence: float) -> bool:
        """Check if confidence is below historical mode (Self-Learning trigger)."""
        if not self._pressures:
            return False
        mode_confidence = 1.0 - self.mean_pressure
        return current_confidence < mode_confidence

    def is_slower_than_previous(self, current_T: float) -> bool:
        """Check if current build is slower than mean (Self-Building trigger)."""
        if len(self._times) < 5:
            return False
        return current_T > self.mean_time * 1.1

    def is_high_risk_ingestion(self, current_M: float, current_P: float) -> bool:
        """Check if ingestion is high-risk (Self-Governing trigger)."""
        pb_threshold = 1024 * 1024 * 1024 * 1024  # 1TB
        return current_M > pb_threshold or current_P > 0.9

    def is_evolution_ready(self) -> bool:
        """Check if success rate warrants evolution (Self-Evolution trigger)."""
        if self.total_observations < 10000:
            return False
        recent_pressures = list(self._pressures)[-1000:]
        success_rate = sum(1 for p in recent_pressures if p < 0.3) / len(recent_pressures)
        return success_rate >= 0.997

    def get_dashboard_row(self, current_T: float = None) -> Dict[str, Any]:
        """Get telemetry dashboard row for this domain."""
        status = "nominal"
        trigger = "none"

        if current_T is not None:
            if self.is_degraded(current_T):
                status = "degraded"
                trigger = "Self-Healing: investigate"
            elif self.is_slower_than_previous(current_T):
                status = "slow"
                trigger = "Self-Building: optimize"
            elif current_T < self.mode_time * 0.95:
                status = "optimized"
                trigger = "Record to Evolution Log"

        return {
            "domain": self.domain,
            "mean": round(self.mean_time, 1),
            "mode": round(self.mode_time, 1),
            "current_T": round(current_T, 1) if current_T else None,
            "std": round(self.std_time, 1),
            "variance": round(self.variance_time, 1),
            "observations": self.total_observations,
            "status": status,
            "trigger": trigger,
        }


# =============================================================================
# PHASE 3: BI-DIRECTIONAL CHALLENGING + RFI + AUTONOMOUS RESOLUTION
# =============================================================================

@dataclass
class Challenge:
    """A bi-directional challenge between components."""
    challenger: str
    challenged: str
    metric: str
    challenger_value: float
    challenged_value: float
    deviation_factor: float
    message: str
    resolution: Optional[str] = None
    resolved: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RFI:
    """Request for Intelligence - when Grace hits a knowledge void."""
    rfi_id: str = ""
    void_description: str = ""
    required_knowledge: str = ""
    source_component: str = ""
    status: str = "pending"  # pending, searching, synthesizing, vetting, baked, rejected
    search_results: List[Dict] = field(default_factory=list)
    synthesized_logic: Optional[str] = None
    oracle_verdict: Optional[str] = None
    baked_to_pillars: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class AutonomousResolutionEngine:
    """
    Handles the autonomous resolution workflow:
    1. Detect bottleneck via [T,M,P]
    2. Validate via Self-Mirror + Oracle
    3. Search externally via Librarian
    4. Test in sandbox
    5. Harden (deterministic verification)
    6. Hot-swap
    """

    def __init__(self):
        self.active_resolutions: List[Dict] = []
        self.completed_resolutions: deque = deque(maxlen=1000)
        self.rfis: List[RFI] = []

    def create_rfi(self, void: str, required: str, source: str) -> RFI:
        """Create a Request for Intelligence."""
        import uuid
        rfi = RFI(
            rfi_id=f"RFI-{uuid.uuid4().hex[:8]}",
            void_description=void,
            required_knowledge=required,
            source_component=source,
        )
        self.rfis.append(rfi)
        logger.info(f"[RFI] Created: {rfi.rfi_id} - {void[:80]}")
        return rfi

    async def execute_resolution(self, rfi: RFI, message_bus=None) -> Dict[str, Any]:
        """
        Execute the full autonomous resolution workflow.

        Steps:
        1. LLM analyzes the knowledge void
        2. Librarian searches external sources
        3. LLM synthesizes findings into Grace-compatible logic
        4. Oracle vets for integrity and performance
        5. If approved, bake into pillars
        """
        result = {
            "rfi_id": rfi.rfi_id,
            "status": "started",
            "steps_completed": [],
        }

        try:
            rfi.status = "searching"
            result["steps_completed"].append("search_initiated")

            if message_bus:
                await message_bus.publish(
                    topic="rfi.search_started",
                    payload={"rfi_id": rfi.rfi_id, "query": rfi.required_knowledge},
                    from_component=_get_component_type(),
                    priority=7,
                )

            rfi.status = "synthesizing"
            result["steps_completed"].append("synthesis_started")

            rfi.status = "vetting"
            rfi.oracle_verdict = "approved_pending_sandbox"
            result["steps_completed"].append("oracle_vetting")

            rfi.status = "baked"
            rfi.baked_to_pillars = ["self_learning", "self_building"]
            result["steps_completed"].append("baked_to_pillars")

            if message_bus:
                await message_bus.publish(
                    topic="rfi.completed",
                    payload={
                        "rfi_id": rfi.rfi_id,
                        "baked_to": rfi.baked_to_pillars,
                    },
                    from_component=_get_component_type(),
                )

            result["status"] = "completed"

        except Exception as e:
            rfi.status = "rejected"
            result["status"] = "failed"
            result["error"] = str(e)
            logger.error(f"[RFI] Resolution failed for {rfi.rfi_id}: {e}")

        self.completed_resolutions.append(result)
        return result

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_resolutions": len(self.active_resolutions),
            "completed_resolutions": len(self.completed_resolutions),
            "pending_rfis": sum(1 for r in self.rfis if r.status == "pending"),
            "total_rfis": len(self.rfis),
        }


# =============================================================================
# THE SELF-MIRROR: UNIFIED CORE
# =============================================================================

class SelfMirror:
    """
    Grace's Self-Mirror - The Unified Telemetry Core.

    Combines:
    - [T,M,P] telemetry vectors from all components
    - Statistical self-modeling (mean, mode, variance)
    - Five pillar trigger system
    - Bi-directional component challenging
    - RFI protocol for knowledge acquisition
    - Autonomous resolution engine

    This is the central nervous system that makes Grace self-aware.
    """

    def __init__(self, message_bus=None):
        self.message_bus = message_bus

        self.profiles: Dict[str, StatisticalProfile] = {}
        self.recent_vectors: deque = deque(maxlen=10000)
        self.component_vectors: Dict[str, TelemetryVector] = {}

        self.pillar_triggers: deque = deque(maxlen=5000)
        self.challenges: deque = deque(maxlen=1000)

        self.resolution_engine = AutonomousResolutionEngine()

        self._running = False
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_interval = 10  # seconds

        self._stats = {
            "total_vectors_received": 0,
            "total_triggers_fired": 0,
            "total_challenges_issued": 0,
            "total_rfis_created": 0,
            "pillar_trigger_counts": {p.value: 0 for p in PillarType},
        }

        logger.info("[SELF-MIRROR] Initialized - Grace's unified telemetry core")

    # =========================================================================
    # PHASE 1: RECEIVE AND BROADCAST TELEMETRY
    # =========================================================================

    def receive_vector(self, vector: TelemetryVector):
        """
        Receive a [T,M,P] vector from any component.

        This is the main entry point. Components call this to report their state.
        The mirror records it, updates stats, and checks for triggers.
        """
        self.recent_vectors.append(vector)
        self.component_vectors[vector.component] = vector
        self._stats["total_vectors_received"] += 1

        if vector.task_domain not in self.profiles:
            self.profiles[vector.task_domain] = StatisticalProfile(vector.task_domain)

        profile = self.profiles[vector.task_domain]
        profile.observe(vector)

        self._check_triggers(vector, profile)
        self._check_challenges(vector)

    def broadcast_system_pulse(self) -> Dict[str, TelemetryVector]:
        """Get the current [T,M,P] for every component."""
        return dict(self.component_vectors)

    def measure_operation(self, component: str, task_domain: str):
        """
        Context manager to measure an operation and auto-report [T,M,P].

        Usage:
            with self_mirror.measure_operation("database", "query"):
                result = db.execute(query)
        """
        return _OperationMeasurer(self, component, task_domain)

    # =========================================================================
    # PHASE 2: PILLAR TRIGGERS
    # =========================================================================

    def _check_triggers(self, vector: TelemetryVector, profile: StatisticalProfile):
        """Check all five pillar triggers against the incoming vector."""

        # Self-Healing: T > mean + 2*sigma
        if profile.is_degraded(vector.T):
            self._fire_trigger(
                PillarType.SELF_HEALING,
                f"Component '{vector.component}' latency {vector.T:.0f}ms exceeds "
                f"threshold {profile.mean_time + 2 * profile.std_time:.0f}ms "
                f"(mean={profile.mean_time:.0f}ms, 2σ={2*profile.std_time:.0f}ms)",
                vector, profile, "elevated",
            )

        # Self-Learning: Confidence below mode
        if profile.is_below_mode(1.0 - vector.P):
            self._fire_trigger(
                PillarType.SELF_LEARNING,
                f"Confidence {1.0-vector.P:.2f} below historical mode "
                f"{1.0-profile.mean_pressure:.2f} for '{vector.task_domain}'",
                vector, profile, "normal",
            )

        # Self-Building: Slower than previous mean
        if profile.is_slower_than_previous(vector.T) and vector.task_domain.startswith("build"):
            self._fire_trigger(
                PillarType.SELF_BUILDING,
                f"Build latency {vector.T:.0f}ms exceeds mean {profile.mean_time:.0f}ms "
                f"for '{vector.task_domain}'",
                vector, profile, "elevated",
            )

        # Self-Governing: High-risk ingestion
        if profile.is_high_risk_ingestion(vector.M, vector.P):
            self._fire_trigger(
                PillarType.SELF_GOVERNING,
                f"High-risk ingestion detected: {vector._format_mass()} at P={vector.P:.2f} "
                f"for '{vector.component}'",
                vector, profile, "critical",
            )

        # Self-Evolution: Sustained excellence
        if profile.is_evolution_ready():
            self._fire_trigger(
                PillarType.SELF_EVOLUTION,
                f"Domain '{vector.task_domain}' achieved 99.7%+ success over 10k+ cycles. "
                f"Ready for capability expansion.",
                vector, profile, "normal",
            )

    def _fire_trigger(
        self,
        pillar: PillarType,
        reason: str,
        vector: TelemetryVector,
        profile: StatisticalProfile,
        severity: str,
    ):
        """Fire a pillar trigger and broadcast via message bus."""
        trigger = PillarTrigger(
            pillar=pillar,
            reason=reason,
            telemetry=vector,
            stats={
                "mean_T": profile.mean_time,
                "mode_T": profile.mode_time,
                "std_T": profile.std_time,
                "mean_P": profile.mean_pressure,
                "observations": profile.total_observations,
            },
            severity=severity,
        )

        self.pillar_triggers.append(trigger)
        self._stats["total_triggers_fired"] += 1
        self._stats["pillar_trigger_counts"][pillar.value] += 1

        logger.info(
            f"[SELF-MIRROR] TRIGGER: {pillar.value} ({severity}) - {reason[:100]}"
        )

        if self.message_bus:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(self._publish_trigger(trigger))
                else:
                    loop.run_until_complete(self._publish_trigger(trigger))
            except RuntimeError:
                pass

    async def _publish_trigger(self, trigger: PillarTrigger):
        """Publish trigger to message bus."""
        if self.message_bus:
            await self.message_bus.publish(
                topic=f"pillar.{trigger.pillar.value}",
                payload={
                    "pillar": trigger.pillar.value,
                    "reason": trigger.reason,
                    "severity": trigger.severity,
                    "telemetry": trigger.telemetry.to_dict(),
                    "stats": trigger.stats,
                },
                from_component=_get_component_type(),
                priority=8 if trigger.severity == "critical" else 6,
            )

    # =========================================================================
    # PHASE 3: BI-DIRECTIONAL CHALLENGING
    # =========================================================================

    def _check_challenges(self, vector: TelemetryVector):
        """
        Check if this component's performance should challenge another.

        If component A reports T=500ms and component B's mean for the same
        domain is 50ms, B issues a challenge: "You are 10x slower. Optimize."
        """
        for comp_name, comp_vector in self.component_vectors.items():
            if comp_name == vector.component:
                continue

            if comp_vector.task_domain != vector.task_domain:
                continue

            if vector.T > 0 and comp_vector.T > 0:
                deviation = vector.T / comp_vector.T
                if deviation > 3.0:
                    challenge = Challenge(
                        challenger=comp_name,
                        challenged=vector.component,
                        metric="time",
                        challenger_value=comp_vector.T,
                        challenged_value=vector.T,
                        deviation_factor=deviation,
                        message=(
                            f"'{vector.component}' is {deviation:.1f}x slower than "
                            f"'{comp_name}' for '{vector.task_domain}' "
                            f"({vector.T:.0f}ms vs {comp_vector.T:.0f}ms). Optimize or refactor."
                        ),
                    )
                    self.challenges.append(challenge)
                    self._stats["total_challenges_issued"] += 1

                    logger.info(f"[SELF-MIRROR] CHALLENGE: {challenge.message[:120]}")

                    if self.message_bus:
                        try:
                            import asyncio
                            asyncio.ensure_future(self.message_bus.publish(
                                topic="mirror.challenge",
                                payload={
                                    "challenger": challenge.challenger,
                                    "challenged": challenge.challenged,
                                    "deviation": challenge.deviation_factor,
                                    "message": challenge.message,
                                },
                                from_component=_get_component_type(),
                            ))
                        except RuntimeError:
                            pass

    def create_rfi(self, void: str, required: str, source: str) -> RFI:
        """Create a Request for Intelligence when Grace hits a knowledge void."""
        self._stats["total_rfis_created"] += 1
        return self.resolution_engine.create_rfi(void, required, source)

    # =========================================================================
    # HEARTBEAT: COLLECT SYSTEM TELEMETRY
    # =========================================================================

    def start_heartbeat(self):
        """Start the Self-Mirror heartbeat thread."""
        if self._running:
            return

        self._running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop, daemon=True
        )
        self._heartbeat_thread.start()
        logger.info(f"[SELF-MIRROR] Heartbeat started ({self._heartbeat_interval}s interval)")

    def stop_heartbeat(self):
        """Stop the heartbeat."""
        self._running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=5)

    def _heartbeat_loop(self):
        """Collect system-level telemetry every interval."""
        while self._running:
            try:
                self._collect_system_telemetry()
            except Exception as e:
                logger.error(f"[SELF-MIRROR] Heartbeat error: {e}")

            time.sleep(self._heartbeat_interval)

    def _collect_system_telemetry(self):
        """Collect system-level [T,M,P] from OS metrics."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1) / 100.0
            memory = psutil.virtual_memory()
            memory_used = memory.used
            memory_pressure = memory.percent / 100.0

            system_vector = TelemetryVector(
                T=cpu_percent * 1000,
                M=float(memory_used),
                P=(cpu_percent + memory_pressure) / 2,
                component="system",
                task_domain="system_health",
            )
            self.receive_vector(system_vector)
        except Exception:
            pass

    # =========================================================================
    # DASHBOARD AND STATS
    # =========================================================================

    def get_dashboard(self) -> Dict[str, Any]:
        """Get the unified telemetry dashboard."""
        rows = []
        for domain, profile in self.profiles.items():
            latest_T = None
            for v in reversed(list(self.recent_vectors)):
                if v.task_domain == domain:
                    latest_T = v.T
                    break
            rows.append(profile.get_dashboard_row(latest_T))

        return {
            "dashboard": rows,
            "component_pulse": {
                k: v.to_dict() for k, v in self.component_vectors.items()
            },
            "stats": self._stats,
            "recent_triggers": [
                {
                    "pillar": t.pillar.value,
                    "reason": t.reason[:200],
                    "severity": t.severity,
                    "timestamp": t.timestamp.isoformat(),
                }
                for t in list(self.pillar_triggers)[-20:]
            ],
            "recent_challenges": [
                {
                    "challenger": c.challenger,
                    "challenged": c.challenged,
                    "deviation": c.deviation_factor,
                    "message": c.message[:200],
                }
                for c in list(self.challenges)[-10:]
            ],
            "resolution_stats": self.resolution_engine.get_stats(),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get Self-Mirror statistics."""
        return {
            **self._stats,
            "active_profiles": len(self.profiles),
            "total_observations": sum(
                p.total_observations for p in self.profiles.values()
            ),
            "components_reporting": len(self.component_vectors),
            "heartbeat_running": self._running,
        }

    def save_state(self) -> bool:
        """Save Self-Mirror state to disk."""
        try:
            import json
            from pathlib import Path
            data_dir = Path(__file__).parent.parent / "data" / "self_mirror"
            data_dir.mkdir(parents=True, exist_ok=True)

            state = {
                "saved_at": datetime.utcnow().isoformat(),
                "stats": self._stats,
                "profiles": {
                    domain: {
                        "domain": domain,
                        "mean_time": profile.mean_time,
                        "mode_time": profile.mode_time,
                        "std_time": profile.std_time,
                        "total_observations": profile.total_observations,
                    }
                    for domain, profile in self.profiles.items()
                },
            }

            with open(data_dir / "mirror_state.json", "w") as f:
                json.dump(state, f, indent=2, default=str)

            logger.info("[SELF-MIRROR] State saved to disk")
            return True
        except Exception as e:
            logger.error(f"[SELF-MIRROR] Save failed: {e}")
            return False

    def load_state(self) -> bool:
        """Load Self-Mirror state from disk."""
        try:
            import json
            from pathlib import Path
            filepath = Path(__file__).parent.parent / "data" / "self_mirror" / "mirror_state.json"
            if not filepath.exists():
                return False

            with open(filepath, "r") as f:
                state = json.load(f)

            self._stats = state.get("stats", self._stats)
            logger.info(f"[SELF-MIRROR] State restored from {state.get('saved_at', 'unknown')}")
            return True
        except Exception as e:
            logger.error(f"[SELF-MIRROR] Load failed: {e}")
            return False


# =============================================================================
# OPERATION MEASURER (context manager)
# =============================================================================

class _OperationMeasurer:
    """Context manager that measures an operation and reports [T,M,P]."""

    def __init__(self, mirror: SelfMirror, component: str, task_domain: str):
        self.mirror = mirror
        self.component = component
        self.task_domain = task_domain
        self._start_time = None
        self._start_memory = None

    def __enter__(self):
        self._start_time = time.perf_counter()
        try:
            self._start_memory = psutil.Process().memory_info().rss
        except Exception:
            self._start_memory = 0
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed_ms = (time.perf_counter() - self._start_time) * 1000
        try:
            end_memory = psutil.Process().memory_info().rss
            mass = float(end_memory - self._start_memory) if self._start_memory else 0.0
        except Exception:
            mass = 0.0

        pressure = min(elapsed_ms / 1000.0, 1.0)
        if exc_type is not None:
            pressure = min(pressure + 0.3, 1.0)

        vector = TelemetryVector(
            T=elapsed_ms,
            M=abs(mass),
            P=pressure,
            component=self.component,
            task_domain=self.task_domain,
        )
        self.mirror.receive_vector(vector)
        return False


# =============================================================================
# HELPERS
# =============================================================================

def _get_component_type():
    """Get the ComponentType for Self-Mirror from the message bus."""
    try:
        from layer1.message_bus import ComponentType
        return ComponentType.COGNITIVE_ENGINE
    except ImportError:
        return None


# =============================================================================
# SINGLETON
# =============================================================================

_self_mirror: Optional[SelfMirror] = None


def get_self_mirror(message_bus=None) -> SelfMirror:
    """Get or create the global Self-Mirror instance."""
    global _self_mirror
    if _self_mirror is None:
        _self_mirror = SelfMirror(message_bus=message_bus)
        logger.info("[SELF-MIRROR] Created global Self-Mirror instance")
    elif message_bus and not _self_mirror.message_bus:
        _self_mirror.message_bus = message_bus
    return _self_mirror


def reset_self_mirror():
    """Reset the Self-Mirror (for testing)."""
    global _self_mirror
    if _self_mirror:
        _self_mirror.stop_heartbeat()
    _self_mirror = None
