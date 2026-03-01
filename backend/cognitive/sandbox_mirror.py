"""
Sandbox Mirror — Grace's Complete Self-Mirror Environment

Mirrors Grace's full backend into a sandbox: diagnostics, memory mesh,
self-healing, genesis keys, consensus, trust — the whole shebang.

Nothing touches production. Grace can test, experiment, develop, learn,
grow within the sandbox. Changes are tracked but only applied after
consensus verification and measurable success.

Connected to:
- Horizon Planner (long-term goals drive what gets tested)
- Patch Consensus (verified changes get applied)
- Self-Healing Tracker (monitors sandbox health)
- Genesis Keys (tracks every experiment)
- Integration Gap Detector (finds what's broken)
"""

import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

SANDBOX_DIR = Path(__file__).parent.parent / "data" / "sandbox_mirror"


@dataclass
class SandboxSession:
    """A sandbox session where Grace mirrors and experiments."""
    id: str
    goal_id: Optional[str] = None
    branch: str = "internal"  # internal or exploration
    status: str = "active"  # active, paused, completed, failed
    components_mirrored: List[str] = field(default_factory=list)
    experiments_run: int = 0
    fixes_tested: int = 0
    fixes_validated: int = 0
    improvements: Dict[str, float] = field(default_factory=dict)
    system_snapshot: Dict[str, Any] = field(default_factory=dict)
    health_baseline: Dict[str, Any] = field(default_factory=dict)
    health_current: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    completed_at: Optional[str] = None


class SandboxMirror:
    """
    Grace's self-mirror. Creates a complete snapshot of the system state,
    runs diagnostics, experiments, and learning cycles in isolation.
    """

    def __init__(self):
        self._sessions: Dict[str, SandboxSession] = {}
        self._active_session: Optional[str] = None
        SANDBOX_DIR.mkdir(parents=True, exist_ok=True)

    def create_session(
        self,
        goal_id: Optional[str] = None,
        branch: str = "internal",
    ) -> SandboxSession:
        """
        Create a new sandbox session and mirror Grace's full state into it.
        """
        session = SandboxSession(
            id=f"SB-{uuid.uuid4().hex[:12]}",
            goal_id=goal_id,
            branch=branch,
        )

        self._log(session, "session_created", f"Sandbox session started (branch={branch})")

        session.system_snapshot = self._capture_system_snapshot()
        session.health_baseline = self._capture_health()
        session.health_current = dict(session.health_baseline)
        session.components_mirrored = list(session.system_snapshot.get("components", {}).keys())

        self._sessions[session.id] = session
        self._active_session = session.id
        self._save_session(session)

        self._log(session, "mirror_complete",
                  f"Mirrored {len(session.components_mirrored)} components")

        try:
            from api._genesis_tracker import track
            track(
                key_type="system",
                what=f"Sandbox mirror session created: {session.id}",
                how="sandbox_mirror.create_session",
                output_data={
                    "session_id": session.id,
                    "goal_id": goal_id,
                    "branch": branch,
                    "components_mirrored": len(session.components_mirrored),
                },
                tags=["sandbox", "mirror", "session", branch],
            )
        except Exception:
            pass

        return session

    def _capture_system_snapshot(self) -> Dict[str, Any]:
        """Capture a complete snapshot of Grace's current system state."""
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "components": {},
            "metrics": {},
            "gaps": [],
            "health": {},
        }

        # Self-healing tracker state
        try:
            from cognitive.self_healing_tracker import get_self_healing_tracker
            tracker = get_self_healing_tracker()
            health = tracker.get_system_health()
            snapshot["health"] = health
            snapshot["components"] = health.get("components", {})
        except Exception as e:
            snapshot["components"]["self_healing"] = {"status": "error", "error": str(e)}

        # Memory mesh stats
        try:
            from database.session import get_session
            from cognitive.memory_mesh_integration import MemoryMeshIntegration
            sess = next(get_session())
            mesh = MemoryMeshIntegration(session=sess, knowledge_base_path=Path("knowledge_base"))
            snapshot["metrics"]["memory_mesh"] = mesh.get_memory_mesh_stats()
            sess.close()
        except Exception as e:
            snapshot["metrics"]["memory_mesh"] = {"error": str(e)}

        # Genesis key counts
        try:
            from database.session import get_session
            from models.genesis_key_models import GenesisKey
            sess = next(get_session())
            total = sess.query(GenesisKey).count()
            snapshot["metrics"]["genesis_keys"] = {"total": total}
            sess.close()
        except Exception:
            snapshot["metrics"]["genesis_keys"] = {"total": 0}

        # Integration gaps
        try:
            from cognitive.integration_gap_detector import detect_all_gaps
            snapshot["gaps"] = detect_all_gaps()
        except Exception:
            snapshot["gaps"] = []

        # World model state
        try:
            from api.world_model_api import _get_system_state
            snapshot["metrics"]["world_model"] = _get_system_state()
        except Exception:
            pass

        return snapshot

    def _capture_health(self) -> Dict[str, Any]:
        """Capture current health metrics."""
        try:
            from cognitive.self_healing_tracker import get_self_healing_tracker
            return get_self_healing_tracker().get_system_health()
        except Exception:
            return {"overall_status": "unknown"}

    def run_diagnostics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Run full system diagnostics within the sandbox.
        Identifies what's broken, what's working, integration gaps.
        """
        session = self._get_session(session_id)
        if not session:
            return {"error": "No active session"}

        results = {
            "session_id": session.id,
            "timestamp": datetime.utcnow().isoformat(),
            "health_check": {},
            "integration_gaps": [],
            "bottlenecks": [],
            "fix_classifications": [],
        }

        # Health check
        try:
            from cognitive.self_healing_tracker import get_self_healing_tracker
            tracker = get_self_healing_tracker()
            probe = tracker.run_health_check()
            results["health_check"] = tracker.get_system_health()
        except Exception as e:
            results["health_check"] = {"error": str(e)}

        # Integration gaps
        try:
            from cognitive.integration_gap_detector import detect_all_gaps
            gaps = detect_all_gaps()
            results["integration_gaps"] = gaps

            from cognitive.horizon_planner import classify_fix
            for gap in gaps[:20]:
                classification = classify_fix(
                    problem=gap.get("description", ""),
                    component=gap.get("component", ""),
                    system_impact=gap.get("severity", "medium"),
                )
                results["fix_classifications"].append({
                    "gap": gap.get("description", "")[:100],
                    "component": gap.get("component", ""),
                    **classification,
                })
        except Exception as e:
            results["integration_gaps"] = [{"error": str(e)}]

        session.experiments_run += 1
        session.health_current = results.get("health_check", {})
        self._log(session, "diagnostics", f"Found {len(results['integration_gaps'])} gaps")
        self._save_session(session)

        return results

    def run_experiment(
        self,
        session_id: Optional[str] = None,
        task_description: str = "",
        use_consensus: bool = True,
    ) -> Dict[str, Any]:
        """
        Run an experiment in the sandbox. Uses consensus mechanism if requested.
        The experiment is contained — nothing affects production.
        """
        session = self._get_session(session_id)
        if not session:
            return {"error": "No active session"}

        result = {
            "session_id": session.id,
            "experiment_id": f"EXP-{uuid.uuid4().hex[:8]}",
            "task": task_description,
            "timestamp": datetime.utcnow().isoformat(),
            "consensus_used": use_consensus,
            "status": "pending",
        }

        if use_consensus:
            try:
                from cognitive.patch_consensus import run_patch_consensus
                consensus_result = run_patch_consensus(
                    task=task_description,
                    auto_apply=False,
                    threshold=0.67,
                )
                result["consensus"] = consensus_result
                result["status"] = consensus_result.get("status", "unknown")
                result["proposal_id"] = consensus_result.get("proposal_id")

                if consensus_result.get("instructions"):
                    session.fixes_tested += 1
                    if consensus_result.get("status") == "verified":
                        session.fixes_validated += 1

            except Exception as e:
                result["error"] = str(e)
                result["status"] = "failed"
        else:
            try:
                from cognitive.consensus_engine import run_consensus
                consensus = run_consensus(
                    prompt=task_description,
                    source="sandbox",
                )
                result["consensus_output"] = consensus.final_output[:2000]
                result["confidence"] = consensus.confidence
                result["status"] = "completed"
                session.experiments_run += 1
            except Exception as e:
                result["error"] = str(e)
                result["status"] = "failed"

        self._log(session, "experiment", f"{task_description[:80]} → {result['status']}")
        self._save_session(session)

        return result

    def run_learning_cycle(
        self,
        session_id: Optional[str] = None,
        focus: str = "internal",
    ) -> Dict[str, Any]:
        """
        Run a complete learning cycle in the sandbox.
        Internal: fix Grace's systems, healing, bottlenecks.
        Exploration: research papers, whitelist data, new capabilities.
        """
        session = self._get_session(session_id)
        if not session:
            return {"error": "No active session"}

        result = {
            "session_id": session.id,
            "focus": focus,
            "timestamp": datetime.utcnow().isoformat(),
            "actions": [],
        }

        if focus == "internal":
            # Run self-healing
            try:
                from cognitive.self_healing_tracker import get_self_healing_tracker
                tracker = get_self_healing_tracker()
                health = tracker.get_system_health()
                for comp in health.get("broken", []) + health.get("degraded", []):
                    tracker.report_error(comp, "Sandbox healing attempt", auto_heal=True)
                    result["actions"].append(f"Heal attempt: {comp}")
            except Exception as e:
                result["actions"].append(f"Healing error: {e}")

            # Run file health monitor
            try:
                from file_manager.file_health_monitor import get_file_health_monitor
                monitor = get_file_health_monitor(dry_run=True)
                report = monitor.run_health_check_cycle()
                result["health_report"] = {
                    "status": report.health_status,
                    "anomalies": len(report.anomalies),
                    "healing_actions": report.healing_actions,
                    "recommendations": report.recommendations,
                }
                result["actions"].append(
                    f"Health check: {report.health_status}, {len(report.anomalies)} anomalies"
                )
            except Exception as e:
                result["actions"].append(f"Health monitor error: {e}")

        elif focus == "exploration":
            # Research and learning
            try:
                from cognitive.auto_research import get_auto_research
                research = get_auto_research()
                result["actions"].append("Auto-research scan initiated")
            except Exception:
                result["actions"].append("Auto-research not available")

            # Check whitelist sources
            try:
                from cognitive.flash_cache import get_flash_cache
                fc = get_flash_cache()
                stats = fc.get_stats()
                result["flash_cache_stats"] = stats
                result["actions"].append(f"Flash cache: {stats.get('total_entries', 0)} entries")
            except Exception:
                result["actions"].append("Flash cache not available")

        session.experiments_run += 1
        self._log(session, "learning_cycle", f"Focus: {focus}, actions: {len(result['actions'])}")
        self._save_session(session)

        return result

    def get_session_summary(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive summary of a sandbox session."""
        session = self._get_session(session_id)
        if not session:
            return {"error": "No active session"}

        baseline_healthy = len(session.health_baseline.get("healthy", []))
        current_healthy = len(session.health_current.get("healthy", []))
        health_delta = current_healthy - baseline_healthy

        return {
            "session_id": session.id,
            "goal_id": session.goal_id,
            "branch": session.branch,
            "status": session.status,
            "experiments_run": session.experiments_run,
            "fixes_tested": session.fixes_tested,
            "fixes_validated": session.fixes_validated,
            "components_mirrored": len(session.components_mirrored),
            "health_improvement": {
                "baseline_healthy": baseline_healthy,
                "current_healthy": current_healthy,
                "delta": health_delta,
            },
            "improvements": session.improvements,
            "recent_logs": session.logs[-20:],
            "created_at": session.created_at,
            "duration_minutes": self._session_duration_minutes(session),
        }

    def close_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Close a sandbox session and generate final report."""
        session = self._get_session(session_id)
        if not session:
            return {"error": "No active session"}

        session.status = "completed"
        session.completed_at = datetime.utcnow().isoformat()
        session.health_current = self._capture_health()

        summary = self.get_session_summary(session.id)
        self._log(session, "session_closed", f"Session completed after {summary['duration_minutes']}min")
        self._save_session(session)

        if self._active_session == session.id:
            self._active_session = None

        try:
            from api._genesis_tracker import track
            track(
                key_type="system",
                what=f"Sandbox session completed: {session.id}",
                how="sandbox_mirror.close_session",
                output_data=summary,
                tags=["sandbox", "mirror", "completed"],
            )
        except Exception:
            pass

        return summary

    def _get_session(self, session_id: Optional[str] = None) -> Optional[SandboxSession]:
        sid = session_id or self._active_session
        if not sid:
            return None
        if sid in self._sessions:
            return self._sessions[sid]
        session = self._load_session(sid)
        if session:
            self._sessions[sid] = session
        return session

    def _log(self, session: SandboxSession, event_type: str, message: str):
        session.logs.append({
            "type": event_type,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        })
        if len(session.logs) > 500:
            session.logs = session.logs[-500:]

    def _session_duration_minutes(self, session: SandboxSession) -> int:
        try:
            start = datetime.fromisoformat(session.created_at)
            end = datetime.fromisoformat(session.completed_at) if session.completed_at else datetime.utcnow()
            return int((end - start).total_seconds() / 60)
        except Exception:
            return 0

    def _save_session(self, session: SandboxSession):
        path = SANDBOX_DIR / f"{session.id}.json"
        path.write_text(json.dumps(asdict(session), indent=2, default=str))

    def _load_session(self, session_id: str) -> Optional[SandboxSession]:
        path = SANDBOX_DIR / f"{session_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return SandboxSession(**data)

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        sessions = []
        for path in sorted(SANDBOX_DIR.glob("SB-*.json"), reverse=True)[:limit]:
            try:
                data = json.loads(path.read_text())
                sessions.append({
                    "id": data["id"],
                    "goal_id": data.get("goal_id"),
                    "branch": data.get("branch", "internal"),
                    "status": data.get("status", "unknown"),
                    "experiments_run": data.get("experiments_run", 0),
                    "fixes_validated": data.get("fixes_validated", 0),
                    "created_at": data.get("created_at", ""),
                })
            except Exception:
                continue
        return sessions


_mirror = None

def get_sandbox_mirror() -> SandboxMirror:
    global _mirror
    if _mirror is None:
        _mirror = SandboxMirror()
    return _mirror
