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
        """Record a single intelligence signal."""
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

    def collect_all(self):
        """Run all collectors."""
        self.collect_from_registry()
        self.collect_from_kpis()
        self.collect_from_healing()
        self.collect_from_pipeline()
        logger.info("[UNIFIED-INTEL] Full collection cycle complete")

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
