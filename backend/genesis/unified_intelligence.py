"""
Unified Intelligence Table

Single source of truth that aggregates intelligence from ALL subsystems:
- Component registry health
- Healing playbook outcomes
- KPI metrics
- Trust scores
- Learning progress
- Memory mesh state
- Diagnostic signals
- Oracle predictions
- Pipeline statuses

ML/DL algorithms run ON TOP of this table to:
- Predict failures before they happen
- Optimize resource allocation
- Identify improvement opportunities
- Drive autonomous decisions

This is the "brain dashboard" — everything in one place.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import Session

from database.base import BaseModel

logger = logging.getLogger(__name__)


class UnifiedIntelligenceRecord(BaseModel):
    """
    A single intelligence record from any subsystem.

    This table receives data from every part of Grace,
    creating a unified view for ML/DL analysis.
    """
    __tablename__ = "unified_intelligence"

    source_system = Column(String(100), nullable=False, index=True)
    signal_type = Column(String(100), nullable=False, index=True)
    signal_name = Column(String(200), nullable=False)

    value_numeric = Column(Float, nullable=True)
    value_text = Column(Text, nullable=True)
    value_json = Column(JSON, nullable=True)

    trust_score = Column(Float, default=0.5)
    confidence = Column(Float, default=0.5)
    severity = Column(String(20), default="info")

    component_name = Column(String(200), nullable=True)
    genesis_key_id = Column(String(100), nullable=True)

    recorded_at = Column(DateTime, default=datetime.now, index=True)
    expires_at = Column(DateTime, nullable=True)
    is_current = Column(Boolean, default=True)


class UnifiedIntelligenceEngine:
    """
    Aggregates intelligence from all subsystems into one table.

    Collectors:
    - collect_from_registry(): Component health data
    - collect_from_kpis(): KPI metrics
    - collect_from_healing(): Healing outcomes
    - collect_from_memory(): Memory mesh state
    - collect_from_learning(): Learning progress
    - collect_from_diagnostics(): Diagnostic signals

    Analyzers:
    - get_system_snapshot(): Current state of everything
    - get_anomalies(): Things that look wrong
    - get_trends(): Direction things are moving
    - get_predictions(): What might happen next
    """

    def __init__(self, session: Session):
        self.session = session

    def record(
        self,
        source_system: str,
        signal_type: str,
        signal_name: str,
        value_numeric: float = None,
        value_text: str = None,
        value_json: Dict = None,
        trust_score: float = 0.5,
        confidence: float = 0.5,
        severity: str = "info",
        component_name: str = None,
        genesis_key_id: str = None,
        ttl_seconds: int = None,
    ):
        """Record a single intelligence signal with deduplication."""
        # Oracle-level deduplication — prevent spamming same record
        try:
            from cognitive.deduplication_engine import get_dedup_engine
            dedup = get_dedup_engine()
            if dedup.check_oracle_record_duplicate(source_system, signal_name, self.session):
                return  # Skip duplicate
        except Exception:
            pass

        entry = UnifiedIntelligenceRecord(
            source_system=source_system,
            signal_type=signal_type,
            signal_name=signal_name,
            value_numeric=value_numeric,
            value_text=value_text,
            value_json=value_json,
            trust_score=trust_score,
            confidence=confidence,
            severity=severity,
            component_name=component_name,
            genesis_key_id=genesis_key_id,
            expires_at=datetime.now() + timedelta(seconds=ttl_seconds) if ttl_seconds else None,
        )
        self.session.add(entry)
        self.session.commit()

    def collect_from_registry(self):
        """Pull intelligence from component registry."""
        try:
            from genesis.component_registry import ComponentRegistry
            registry = ComponentRegistry(self.session)
            stats = registry.get_stats()
            self.record(
                source_system="component_registry",
                signal_type="health_summary",
                signal_name="registry_stats",
                value_numeric=stats.get("coverage", 0),
                value_json=stats,
                trust_score=0.9,
                confidence=0.95,
                ttl_seconds=300,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] Registry collection failed: {e}")

    def collect_from_kpis(self):
        """Pull intelligence from KPI tracker."""
        try:
            from ml_intelligence.kpi_tracker import KPITracker
            tracker = KPITracker()
            health = tracker.get_system_health()
            self.record(
                source_system="kpi_tracker",
                signal_type="system_health",
                signal_name="kpi_health",
                value_numeric=health.get("overall_health", 0.5),
                value_json=health,
                trust_score=0.85,
                ttl_seconds=300,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] KPI collection failed: {e}")

    def collect_from_healing(self):
        """Pull intelligence from healing system."""
        try:
            from cognitive.healing_playbooks import PlaybookManager
            manager = PlaybookManager(self.session)
            stats = manager.get_stats()
            self.record(
                source_system="healing",
                signal_type="playbook_stats",
                signal_name="healing_stats",
                value_numeric=stats.get("total_playbooks", 0),
                value_json=stats,
                trust_score=0.9,
                ttl_seconds=600,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] Healing collection failed: {e}")

    def collect_from_pipeline(self):
        """Pull intelligence from unified learning pipeline."""
        try:
            from cognitive.unified_learning_pipeline import get_unified_pipeline
            pipeline = get_unified_pipeline()
            status = pipeline.get_status()
            self.record(
                source_system="learning_pipeline",
                signal_type="pipeline_status",
                signal_name="pipeline_stats",
                value_numeric=status["stats"]["total_expansions"],
                value_json=status["stats"],
                trust_score=0.8,
                ttl_seconds=300,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] Pipeline collection failed: {e}")

    # =========================================================================
    # COLLECTORS — One for every subsystem in Grace
    # =========================================================================

    def collect_from_self_agents(self):
        """Pull intelligence from all 6 self-* agent micro-DBs."""
        try:
            from cognitive.self_agent_ecosystem import (
                SelfHealingLog, SelfMirrorLog, SelfModelLog,
                SelfLearnerLog, CodeAgentLog, SelfEvolverLog
            )
            tables = {
                "self_healer": SelfHealingLog,
                "self_mirror": SelfMirrorLog,
                "self_model": SelfModelLog,
                "self_learner": SelfLearnerLog,
                "code_agent": CodeAgentLog,
                "self_evolver": SelfEvolverLog,
            }
            for agent_name, model in tables.items():
                total = self.session.query(model).count()
                passes = self.session.query(model).filter(model.status == "pass").count()
                rate = passes / max(total, 1)
                self.record(
                    source_system=f"self_agent.{agent_name}",
                    signal_type="pass_rate",
                    signal_name=f"{agent_name}_performance",
                    value_numeric=rate,
                    value_json={"total": total, "passes": passes},
                    trust_score=0.85,
                    ttl_seconds=300,
                )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] Self-agent collection failed: {e}")

    def collect_from_memory_mesh(self):
        """Pull intelligence from memory mesh (cache, metrics, snapshots)."""
        try:
            from cognitive.memory_mesh_cache import MemoryMeshCache
            cache = MemoryMeshCache()
            stats = cache.get_stats() if hasattr(cache, 'get_stats') else {}
            self.record(
                source_system="memory_mesh",
                signal_type="cache_stats",
                signal_name="memory_mesh_health",
                value_json=stats,
                trust_score=0.85,
                ttl_seconds=300,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] Memory mesh collection failed: {e}")

    def collect_from_magma(self):
        """Pull intelligence from Magma Memory system."""
        try:
            from cognitive.magma.grace_magma_system import get_grace_magma
            magma = get_grace_magma()
            if magma:
                stats = magma.get_stats() if hasattr(magma, 'get_stats') else {}
                self.record(
                    source_system="magma_memory",
                    signal_type="graph_stats",
                    signal_name="magma_health",
                    value_json=stats,
                    trust_score=0.85,
                    ttl_seconds=300,
                )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] Magma collection failed: {e}")

    def collect_from_episodic_memory(self):
        """Pull intelligence from episodic memory."""
        try:
            from cognitive.episodic_memory import Episode
            total_episodes = self.session.query(Episode).count()
            self.record(
                source_system="episodic_memory",
                signal_type="volume",
                signal_name="total_episodes",
                value_numeric=total_episodes,
                trust_score=0.9,
                ttl_seconds=600,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] Episodic collection failed: {e}")

    def collect_from_learning_memory(self):
        """Pull intelligence from learning memory (examples + patterns)."""
        try:
            from cognitive.learning_memory import LearningExample, LearningPattern
            total_examples = self.session.query(LearningExample).count()
            total_patterns = self.session.query(LearningPattern).count()
            from sqlalchemy import func
            avg_trust = self.session.query(
                func.avg(LearningExample.trust_score)
            ).scalar() or 0.5
            self.record(
                source_system="learning_memory",
                signal_type="volume_and_trust",
                signal_name="learning_stats",
                value_numeric=float(avg_trust),
                value_json={"examples": total_examples, "patterns": total_patterns, "avg_trust": float(avg_trust)},
                trust_score=0.9,
                ttl_seconds=600,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] Learning memory collection failed: {e}")

    def collect_from_genesis_keys(self):
        """Pull intelligence from Genesis Key tracking."""
        try:
            from models.genesis_key_models import GenesisKey
            total_keys = self.session.query(GenesisKey).count()
            cutoff = datetime.now() - timedelta(hours=1)
            recent_keys = self.session.query(GenesisKey).filter(
                GenesisKey.created_at >= cutoff
            ).count()
            self.record(
                source_system="genesis_keys",
                signal_type="tracking_volume",
                signal_name="genesis_key_stats",
                value_numeric=total_keys,
                value_json={"total": total_keys, "last_hour": recent_keys},
                trust_score=0.95,
                ttl_seconds=300,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] Genesis key collection failed: {e}")

    def collect_from_documents(self):
        """Pull intelligence from document/ingestion system."""
        try:
            from models.database_models import Document
            total_docs = self.session.query(Document).count()
            completed = self.session.query(Document).filter(Document.status == "completed").count()
            self.record(
                source_system="ingestion",
                signal_type="document_stats",
                signal_name="ingestion_health",
                value_numeric=completed,
                value_json={"total": total_docs, "completed": completed, "rate": completed / max(total_docs, 1)},
                trust_score=0.9,
                ttl_seconds=600,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] Document collection failed: {e}")

    def collect_from_llm_tracking(self):
        """Pull intelligence from LLM interaction tracking."""
        try:
            from models.llm_tracking_models import LLMInteraction
            total = self.session.query(LLMInteraction).count()
            self.record(
                source_system="llm_tracking",
                signal_type="interaction_volume",
                signal_name="llm_interactions",
                value_numeric=total,
                trust_score=0.85,
                ttl_seconds=600,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] LLM tracking collection failed: {e}")

    def collect_from_handshake(self):
        """Pull intelligence from handshake protocol."""
        try:
            from genesis.handshake_protocol import get_handshake_protocol
            handshake = get_handshake_protocol()
            status = handshake.get_status()
            self.record(
                source_system="handshake_protocol",
                signal_type="liveness",
                signal_name="handshake_stats",
                value_json=status.get("stats", {}),
                trust_score=0.9,
                ttl_seconds=120,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] Handshake collection failed: {e}")

    def collect_from_governance(self):
        """Pull intelligence from governance middleware."""
        try:
            from security.governance_middleware import get_audit_trail_manager
            manager = get_audit_trail_manager()
            summary = manager.get_violation_summary()
            self.record(
                source_system="governance",
                signal_type="audit_trail",
                signal_name="governance_stats",
                value_numeric=summary.get("violation_rate", 0),
                value_json=summary,
                trust_score=0.95,
                severity="warning" if summary.get("violation_rate", 0) > 0.05 else "info",
                ttl_seconds=300,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] Governance collection failed: {e}")

    def collect_from_closed_loop(self):
        """Pull intelligence from self-* closed-loop ecosystem."""
        try:
            from cognitive.self_agent_ecosystem import get_closed_loop
            loop = get_closed_loop()
            if loop:
                status = loop.get_status()
                self.record(
                    source_system="closed_loop",
                    signal_type="ecosystem_status",
                    signal_name="self_agent_ecosystem",
                    value_json=status,
                    trust_score=0.85,
                    ttl_seconds=300,
                )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] Closed-loop collection failed: {e}")

    def collect_from_three_layer_reasoning(self):
        """Pull intelligence from the 3-layer reasoning pipeline."""
        try:
            from llm_orchestrator.three_layer_reasoning import get_three_layer_reasoning
            pipeline = get_three_layer_reasoning()
            models = pipeline.get_available_models()
            self.record(
                source_system="three_layer_reasoning",
                signal_type="capability",
                signal_name="reasoning_models",
                value_numeric=len(models),
                value_json={"models": models[:10]},
                trust_score=0.8,
                ttl_seconds=600,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] 3-layer reasoning collection failed: {e}")

    def collect_from_hia(self):
        """Pull intelligence from HIA (Honesty, Integrity, Accountability) framework."""
        try:
            from security.honesty_integrity_accountability import get_hia_framework
            hia = get_hia_framework()
            scores = hia.get_system_hia_score()
            self.record(
                source_system="hia_framework",
                signal_type="hia_scores",
                signal_name="honesty_integrity_accountability",
                value_numeric=scores.get("overall_hia_score", 0.5),
                value_json=scores,
                trust_score=0.95,
                severity="warning" if scores.get("overall_hia_score", 1) < 0.7 else "info",
                ttl_seconds=300,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] HIA collection failed: {e}")

    def collect_from_timesense_governance(self):
        """Pull intelligence from TimeSense governance SLA monitoring."""
        try:
            from cognitive.timesense_governance import get_timesense_governance
            ts_gov = get_timesense_governance()
            status = ts_gov.get_sla_status()
            self.record(
                source_system="timesense_governance",
                signal_type="sla_status",
                signal_name="timesense_sla_health",
                value_numeric=status["stats"]["total_breaches"],
                value_json=status["stats"],
                trust_score=0.9,
                severity="warning" if status["stats"]["total_breaches"] > 0 else "info",
                ttl_seconds=300,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] TimeSense governance collection failed: {e}")

    def collect_from_training_sources(self):
        """Pull intelligence from the training data source registry."""
        try:
            from cognitive.training_data_sources import get_training_source_registry
            registry = get_training_source_registry()
            stats = registry.get_stats()
            self.record(
                source_system="training_sources",
                signal_type="registry_stats",
                signal_name="training_data_sources",
                value_numeric=stats.get("total_sources", 0),
                value_json=stats,
                trust_score=0.9,
                ttl_seconds=3600,
            )
        except Exception as e:
            logger.debug(f"[UNIFIED-INTEL] Training sources collection failed: {e}")

    def librarian_audit(self):
        """
        Librarian Keeper Function — validates unified intelligence integrity.

        The librarian checks:
        - Are all subsystems reporting?
        - Are there stale records?
        - Is data consistent?
        - Are there gaps in coverage?
        """
        from sqlalchemy import func, distinct

        sources_reporting = self.session.query(
            distinct(UnifiedIntelligenceRecord.source_system)
        ).filter(
            UnifiedIntelligenceRecord.is_current == True,
            UnifiedIntelligenceRecord.recorded_at >= datetime.now() - timedelta(minutes=10)
        ).count()

        expected_sources = 18  # All collectors including HIA + TimeSense governance
        coverage = sources_reporting / max(expected_sources, 1)

        stale = self.session.query(UnifiedIntelligenceRecord).filter(
            UnifiedIntelligenceRecord.is_current == True,
            UnifiedIntelligenceRecord.recorded_at < datetime.now() - timedelta(minutes=15)
        ).count()

        audit_result = {
            "sources_reporting": sources_reporting,
            "expected_sources": expected_sources,
            "coverage": round(coverage, 2),
            "stale_records": stale,
            "status": "healthy" if coverage >= 0.7 else ("degraded" if coverage >= 0.4 else "critical"),
            "audited_at": datetime.now().isoformat(),
        }

        self.record(
            source_system="librarian",
            signal_type="audit",
            signal_name="unified_intelligence_audit",
            value_numeric=coverage,
            value_json=audit_result,
            trust_score=0.95,
            severity="warning" if coverage < 0.7 else "info",
            ttl_seconds=600,
        )

        logger.info(
            f"[UNIFIED-INTEL] Librarian audit: {sources_reporting}/{expected_sources} "
            f"sources ({coverage:.0%}), {stale} stale records"
        )
        return audit_result

    def collect_all(self):
        """Run ALL collectors — every subsystem feeds the unified table."""
        self.collect_from_registry()
        self.collect_from_kpis()
        self.collect_from_healing()
        self.collect_from_pipeline()
        self.collect_from_self_agents()
        self.collect_from_memory_mesh()
        self.collect_from_magma()
        self.collect_from_episodic_memory()
        self.collect_from_learning_memory()
        self.collect_from_genesis_keys()
        self.collect_from_documents()
        self.collect_from_llm_tracking()
        self.collect_from_handshake()
        self.collect_from_governance()
        self.collect_from_closed_loop()
        self.collect_from_three_layer_reasoning()

        self.collect_from_hia()
        self.collect_from_timesense_governance()
        self.collect_from_training_sources()

        # Librarian audit — verifies everything is reporting
        self.librarian_audit()

        logger.info("[UNIFIED-INTEL] Full collection cycle complete (18 sources + librarian audit)")

    def get_system_snapshot(self) -> Dict[str, Any]:
        """Get current snapshot of all intelligence."""
        recent = self.session.query(UnifiedIntelligenceRecord).filter(
            UnifiedIntelligenceRecord.is_current == True
        ).order_by(UnifiedIntelligenceRecord.recorded_at.desc()).limit(100).all()

        snapshot = {}
        for r in recent:
            key = f"{r.source_system}.{r.signal_type}"
            if key not in snapshot:
                snapshot[key] = {
                    "source": r.source_system,
                    "type": r.signal_type,
                    "name": r.signal_name,
                    "value": r.value_numeric,
                    "text": r.value_text,
                    "data": r.value_json,
                    "trust": r.trust_score,
                    "confidence": r.confidence,
                    "severity": r.severity,
                    "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
                }
        return snapshot

    def get_anomalies(self) -> List[Dict[str, Any]]:
        """Find anomalous signals (low trust, high severity)."""
        anomalies = self.session.query(UnifiedIntelligenceRecord).filter(
            UnifiedIntelligenceRecord.is_current == True,
            (UnifiedIntelligenceRecord.severity.in_(["warning", "critical", "error"])) |
            (UnifiedIntelligenceRecord.trust_score < 0.3)
        ).order_by(UnifiedIntelligenceRecord.recorded_at.desc()).limit(50).all()

        return [
            {
                "source": a.source_system,
                "signal": a.signal_name,
                "severity": a.severity,
                "trust": a.trust_score,
                "value": a.value_numeric,
                "recorded_at": a.recorded_at.isoformat() if a.recorded_at else None,
            }
            for a in anomalies
        ]

    def cleanup_expired(self):
        """Remove expired intelligence records."""
        now = datetime.now()
        deleted = self.session.query(UnifiedIntelligenceRecord).filter(
            UnifiedIntelligenceRecord.expires_at != None,
            UnifiedIntelligenceRecord.expires_at < now
        ).delete()
        self.session.commit()
        if deleted:
            logger.info(f"[UNIFIED-INTEL] Cleaned up {deleted} expired records")


class UnifiedIntelligenceDaemon:
    """Background daemon that continuously collects intelligence."""

    def __init__(self, collection_interval: int = 120):
        self.interval = collection_interval
        self.running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self.running:
            return
        self.running = True
        self._thread = threading.Thread(
            target=self._loop, daemon=True, name="unified-intelligence"
        )
        self._thread.start()
        logger.info(f"[UNIFIED-INTEL] Daemon started (interval={self.interval}s)")

    def stop(self):
        self.running = False

    def _loop(self):
        while self.running:
            try:
                from database.session import SessionLocal
                session = SessionLocal()
                if session:
                    try:
                        engine = UnifiedIntelligenceEngine(session)
                        engine.collect_all()
                        engine.cleanup_expired()
                    finally:
                        session.close()
            except Exception as e:
                logger.debug(f"[UNIFIED-INTEL] Collection error: {e}")
            time.sleep(self.interval)


_daemon: Optional[UnifiedIntelligenceDaemon] = None

def get_intelligence_daemon() -> UnifiedIntelligenceDaemon:
    global _daemon
    if _daemon is None:
        _daemon = UnifiedIntelligenceDaemon()
    return _daemon
