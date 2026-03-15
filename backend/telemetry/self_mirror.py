"""
telemetry/self_mirror.py
───────────────────────────────────────────────────────────────────────
Self-Mirroring Telemetry Feedback Loop  (Phase 3.4)

System 3 Integration: Grace observes herself and feeds metrics
back into governance decisions.

Collects:
  - CPU / memory / disk usage (psutil)
  - API latency from telemetry baselines
  - Drift alerts from TelemetryService
  - Governance metrics (trust scores, KPI pass rates)
  - Healing metrics (success rate, MTTR)
  - Sandbox repair stats
  - Spindle deterministic path ratio

Feeds back into:
  - Trust Engine (component trust adjustments)
  - HealingCoordinator (proactive healing triggers)
  - Event bus (dashboard + alerting)

Runs as a background thread, publishing a mirror snapshot every 60s.
"""

import logging
import psutil
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MIRROR_INTERVAL_S = 60  # snapshot every 60 seconds
SAMPLE_WINDOW = 60      # keep last 60 samples for trend analysis


@dataclass
class MirrorSnapshot:
    """A single point-in-time mirror of Grace's state."""
    timestamp: str = ""
    # System resources
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_rss_mb: float = 0.0
    disk_percent: float = 0.0
    # API latency (from telemetry baselines)
    avg_api_latency_ms: float = 0.0
    p95_api_latency_ms: float = 0.0
    # Drift alerts
    active_drift_alerts: int = 0
    # Governance
    system_trust_score: float = 0.0
    low_trust_components: List[str] = field(default_factory=list)
    # Healing
    healing_success_rate: float = 0.0
    healing_total: int = 0
    # Sandbox
    sandbox_pass_rate: float = 0.0
    sandbox_total: int = 0
    # Spindle
    deterministic_path_count: int = 0
    llm_bypass_ratio: float = 0.0
    # Trend indicators
    cpu_trend: str = "stable"      # rising / stable / falling
    memory_trend: str = "stable"
    latency_trend: str = "stable"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "resources": {
                "cpu_percent": self.cpu_percent,
                "memory_percent": self.memory_percent,
                "memory_rss_mb": round(self.memory_rss_mb, 1),
                "disk_percent": self.disk_percent,
            },
            "latency": {
                "avg_ms": round(self.avg_api_latency_ms, 1),
                "p95_ms": round(self.p95_api_latency_ms, 1),
            },
            "drift_alerts": self.active_drift_alerts,
            "governance": {
                "system_trust": round(self.system_trust_score, 2),
                "low_trust_components": self.low_trust_components,
            },
            "healing": {
                "success_rate": round(self.healing_success_rate, 3),
                "total": self.healing_total,
            },
            "sandbox": {
                "pass_rate": round(self.sandbox_pass_rate, 3),
                "total": self.sandbox_total,
            },
            "spindle": {
                "deterministic_paths": self.deterministic_path_count,
                "llm_bypass_ratio": round(self.llm_bypass_ratio, 4),
            },
            "trends": {
                "cpu": self.cpu_trend,
                "memory": self.memory_trend,
                "latency": self.latency_trend,
            },
        }


class SelfMirror:
    """
    Self-mirroring telemetry loop.

    Periodically captures Grace's vital signs and feeds anomalies
    back into the governance / healing systems.
    """

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._process = psutil.Process()
        # Trend tracking
        self._cpu_samples: deque = deque(maxlen=SAMPLE_WINDOW)
        self._memory_samples: deque = deque(maxlen=SAMPLE_WINDOW)
        self._latency_samples: deque = deque(maxlen=SAMPLE_WINDOW)
        # History
        self._snapshots: List[MirrorSnapshot] = []
        self._max_snapshots = 120  # 2 hours at 60s intervals
        self._snapshot_count = 0
        # Governance feedback thresholds
        self._cpu_alert_threshold = 85.0
        self._memory_alert_threshold = 90.0
        self._latency_alert_threshold_ms = 5000.0

    # ── Start / Stop ──────────────────────────────────────────────────

    def start(self) -> bool:
        if self._running:
            return False
        self._running = True
        self._thread = threading.Thread(
            target=self._mirror_loop,
            daemon=True,
            name="grace-self-mirror",
        )
        self._thread.start()
        logger.info("[SELF-MIRROR] ✅ Self-mirroring telemetry started (every %ds)", MIRROR_INTERVAL_S)
        return True

    def stop(self):
        self._running = False
        logger.info("[SELF-MIRROR] Stopped")

    # ── Main Loop ─────────────────────────────────────────────────────

    def _mirror_loop(self):
        # Wait for core subsystems via Lifecycle Cortex instead of blind sleep
        try:
            from core.lifecycle_cortex import get_lifecycle_cortex
            cortex = get_lifecycle_cortex()
            cortex.wait_ready("central_orchestrator", timeout=30)
        except Exception:
            time.sleep(30)  # fallback if cortex not available
        while self._running:
            try:
                snapshot = self._capture_snapshot()
                self._analyze_and_respond(snapshot)
            except Exception as e:
                logger.error("[SELF-MIRROR] Snapshot error: %s", e)
            time.sleep(MIRROR_INTERVAL_S)

    # ── Capture ───────────────────────────────────────────────────────

    def _capture_snapshot(self) -> MirrorSnapshot:
        snap = MirrorSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # System resources
        try:
            snap.cpu_percent = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            snap.memory_percent = mem.percent
            snap.memory_rss_mb = self._process.memory_info().rss / (1024 * 1024)
            disk = psutil.disk_usage("/")
            snap.disk_percent = disk.percent
        except Exception as e:
            logger.debug("[SELF-MIRROR] Resource collection: %s", e)

        # Track samples for trends
        self._cpu_samples.append(snap.cpu_percent)
        self._memory_samples.append(snap.memory_percent)

        # API latency from telemetry baselines
        try:
            from database.session import get_session
            from models.telemetry_models import PerformanceBaseline
            session = next(get_session())
            try:
                baselines = session.query(PerformanceBaseline).all()
                if baselines:
                    latencies = [b.mean_duration_ms for b in baselines if b.mean_duration_ms]
                    if latencies:
                        snap.avg_api_latency_ms = sum(latencies) / len(latencies)
                    p95s = [b.p95_duration_ms for b in baselines if b.p95_duration_ms]
                    if p95s:
                        snap.p95_api_latency_ms = max(p95s)
            finally:
                session.close()
        except Exception:
            pass

        self._latency_samples.append(snap.avg_api_latency_ms)

        # Drift alerts count
        try:
            from database.session import get_session
            from models.telemetry_models import DriftAlert
            session = next(get_session())
            try:
                snap.active_drift_alerts = session.query(DriftAlert).filter(
                    DriftAlert.acknowledged == False
                ).count()
            finally:
                session.close()
        except Exception:
            pass

        # Governance: trust scores
        try:
            from cognitive.trust_engine import get_trust_engine
            te = get_trust_engine()
            system_trust = te.get_system_trust()
            snap.system_trust_score = system_trust.get("overall_trust", 0)
            for comp_id, comp_data in system_trust.get("components", {}).items():
                trust = comp_data.get("trust", 100)
                if trust < 70:
                    snap.low_trust_components.append(
                        comp_data.get("name", comp_id)
                    )
        except Exception:
            pass

        # Healing stats
        try:
            from ml_intelligence.kpi_tracker import get_kpi_tracker
            tracker = get_kpi_tracker()
            healing_kpis = tracker.get_kpi("healing_coordinator")
            if healing_kpis:
                total = healing_kpis.get("total", 0)
                successes = healing_kpis.get("successes", 0)
                snap.healing_total = int(total)
                snap.healing_success_rate = successes / max(total, 1)
        except Exception:
            pass

        # Sandbox repair stats
        try:
            from cognitive.sandbox_repair_engine import get_sandbox_repair_engine
            stats = get_sandbox_repair_engine().get_stats()
            snap.sandbox_total = stats.get("total_evaluations", 0)
            snap.sandbox_pass_rate = stats.get("pass_rate", 0)
        except Exception:
            pass

        # Spindle / SWE bridge stats
        try:
            from cognitive.swe_spindle_bridge import get_swe_spindle_bridge
            stats = get_swe_spindle_bridge().get_stats()
            snap.deterministic_path_count = stats.get("deterministic_paths", 0)
            snap.llm_bypass_ratio = stats.get("llm_bypass_ratio", 0)
        except Exception:
            pass

        # Compute trends
        snap.cpu_trend = self._compute_trend(self._cpu_samples)
        snap.memory_trend = self._compute_trend(self._memory_samples)
        snap.latency_trend = self._compute_trend(self._latency_samples)

        # Store
        self._snapshots.append(snap)
        if len(self._snapshots) > self._max_snapshots:
            self._snapshots = self._snapshots[-self._max_snapshots:]
        self._snapshot_count += 1

        return snap

    # ── Analyze & Respond ─────────────────────────────────────────────

    def _analyze_and_respond(self, snap: MirrorSnapshot):
        """Analyze snapshot and feed anomalies back to governance/healing."""
        alerts = []

        # CPU sustained high
        if snap.cpu_percent > self._cpu_alert_threshold and snap.cpu_trend == "rising":
            alerts.append({
                "type": "resource",
                "metric": "cpu",
                "value": snap.cpu_percent,
                "threshold": self._cpu_alert_threshold,
                "severity": "high",
            })

        # Memory sustained high
        if snap.memory_percent > self._memory_alert_threshold:
            alerts.append({
                "type": "resource",
                "metric": "memory",
                "value": snap.memory_percent,
                "threshold": self._memory_alert_threshold,
                "severity": "critical" if snap.memory_percent > 95 else "high",
            })

        # Latency spike
        if snap.avg_api_latency_ms > self._latency_alert_threshold_ms:
            alerts.append({
                "type": "latency",
                "metric": "avg_api_latency",
                "value": snap.avg_api_latency_ms,
                "threshold": self._latency_alert_threshold_ms,
                "severity": "high",
            })

        # Low trust components → proactive healing trigger
        if snap.low_trust_components:
            alerts.append({
                "type": "governance",
                "metric": "low_trust",
                "components": snap.low_trust_components,
                "severity": "medium",
            })

        # Publish snapshot to event bus
        try:
            from cognitive.event_bus import publish_async
            publish_async("mirror.snapshot", snap.to_dict(), source="self_mirror")
        except Exception:
            pass

        # Feed alerts to governance
        if alerts:
            self._feed_governance_alerts(alerts, snap)

        # Log periodic summary
        if self._snapshot_count % 10 == 0:
            logger.info(
                "[SELF-MIRROR] #%d: CPU=%.1f%% MEM=%.1f%% LAT=%.0fms TRUST=%.0f DRIFT=%d PATHS=%d",
                self._snapshot_count, snap.cpu_percent, snap.memory_percent,
                snap.avg_api_latency_ms, snap.system_trust_score,
                snap.active_drift_alerts, snap.deterministic_path_count,
            )

    def _feed_governance_alerts(self, alerts: List[Dict], snap: MirrorSnapshot):
        """Route mirror alerts to trust engine and healing system."""
        for alert in alerts:
            # Feed to trust engine as KPI
            try:
                from cognitive.trust_engine import get_trust_engine
                te = get_trust_engine()
                if alert["type"] == "resource":
                    te.record_kpi("system_resources", "degradation")
                elif alert["type"] == "latency":
                    te.record_kpi("api_latency", "degradation")
            except Exception:
                pass

            # Critical alerts trigger proactive healing
            if alert.get("severity") in ("high", "critical"):
                try:
                    from cognitive.event_bus import publish_async
                    publish_async("mirror.alert", {
                        "alert": alert,
                        "snapshot_timestamp": snap.timestamp,
                        "action": "proactive_healing_recommended",
                    }, source="self_mirror")
                except Exception:
                    pass

        # Genesis tracking for alerts
        try:
            from api._genesis_tracker import track
            track(
                key_type="system_event",
                what=f"Self-mirror: {len(alerts)} alert(s) — {[a['type'] for a in alerts]}",
                how="SelfMirror._feed_governance_alerts",
                output_data={"alerts": alerts, "snapshot": snap.to_dict()},
                tags=["mirror", "telemetry", "phase_3.4", "alert"],
            )
        except Exception:
            pass

    # ── Trend Analysis ────────────────────────────────────────────────

    @staticmethod
    def _compute_trend(samples: deque) -> str:
        """Simple linear trend: compare first half avg to second half avg."""
        if len(samples) < 6:
            return "stable"
        mid = len(samples) // 2
        first_half = list(samples)[:mid]
        second_half = list(samples)[mid:]
        avg_first = sum(first_half) / len(first_half) if first_half else 0
        avg_second = sum(second_half) / len(second_half) if second_half else 0
        if avg_first == 0:
            return "stable"
        change = (avg_second - avg_first) / max(avg_first, 0.01)
        if change > 0.10:
            return "rising"
        elif change < -0.10:
            return "falling"
        return "stable"

    # ── Status API ────────────────────────────────────────────────────

    def get_latest(self) -> Optional[Dict[str, Any]]:
        if self._snapshots:
            return self._snapshots[-1].to_dict()
        return None

    def get_history(self, limit: int = 60) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in reversed(self._snapshots[-limit:])]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "snapshot_count": self._snapshot_count,
            "sample_window": SAMPLE_WINDOW,
            "cpu_trend": self._compute_trend(self._cpu_samples),
            "memory_trend": self._compute_trend(self._memory_samples),
            "latency_trend": self._compute_trend(self._latency_samples),
        }


# ── Singleton ─────────────────────────────────────────────────────────
_mirror: Optional[SelfMirror] = None


def get_self_mirror() -> SelfMirror:
    global _mirror
    if _mirror is None:
        _mirror = SelfMirror()
    return _mirror
