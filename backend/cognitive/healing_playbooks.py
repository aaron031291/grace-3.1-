"""
Healing Playbooks - Reusable Success Configurations

Every time self-healing succeeds, the configuration is stored as a playbook
in the database. When the same anomaly type is detected again, the system
consults existing playbooks before deciding on a healing action.

This creates a growing library of proven healing strategies that:
1. Speed up healing (skip LLM consultation if playbook exists)
2. Increase trust (proven strategies get higher trust)
3. Enable knowledge transfer (playbooks survive restarts)
4. Support auditing (full Genesis Key trail per playbook)
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import Session

from database.base import BaseModel

logger = logging.getLogger(__name__)


class HealingPlaybook(BaseModel):
    """
    A proven healing strategy stored in the database.

    Each playbook represents a successful healing action that can be
    replayed when the same anomaly type is detected.
    """
    __tablename__ = "healing_playbooks"

    name = Column(String(200), nullable=False, index=True)
    anomaly_type = Column(String(100), nullable=False, index=True)
    anomaly_severity = Column(String(50), nullable=False)
    healing_action = Column(String(100), nullable=False)

    success_count = Column(Integer, default=1)
    failure_count = Column(Integer, default=0)
    trust_score = Column(Float, default=0.7)

    configuration = Column(JSON, nullable=False)
    steps = Column(JSON, nullable=True)
    preconditions = Column(JSON, nullable=True)
    postconditions = Column(JSON, nullable=True)

    genesis_key_id = Column(String(100), nullable=True)
    last_used = Column(DateTime, nullable=True)
    last_success = Column(DateTime, nullable=True)

    is_active = Column(Boolean, default=True)
    playbook_metadata = Column(JSON, nullable=True)


class PlaybookManager:
    """
    Manages healing playbooks - stores, retrieves, and updates them.

    Integrates with:
    - AutonomousHealingSystem: Creates playbooks from successful healings
    - Magma Memory: Stores playbooks in persistent memory
    - Genesis Keys: Tracks playbook provenance
    - KPI Tracker: Measures playbook effectiveness
    """

    def __init__(self, session: Session):
        self.session = session

    def create_playbook(
        self,
        anomaly_type: str,
        anomaly_severity: str,
        healing_action: str,
        configuration: Dict[str, Any],
        steps: List[str] = None,
        genesis_key_id: str = None,
    ) -> HealingPlaybook:
        """Create a new playbook from a successful healing."""
        name = f"{anomaly_type}_{healing_action}_{anomaly_severity}"

        existing = self.session.query(HealingPlaybook).filter(
            HealingPlaybook.anomaly_type == anomaly_type,
            HealingPlaybook.healing_action == healing_action,
            HealingPlaybook.anomaly_severity == anomaly_severity,
        ).first()

        if existing:
            existing.success_count += 1
            existing.trust_score = min(0.99, existing.trust_score + 0.02)
            existing.last_used = datetime.now()
            existing.last_success = datetime.now()
            if configuration:
                merged = json.loads(existing.configuration) if isinstance(existing.configuration, str) else (existing.configuration or {})
                merged.update(configuration)
                existing.configuration = merged
            self.session.commit()
            logger.info(f"[PLAYBOOK] Updated existing playbook '{name}' (uses: {existing.success_count})")
            return existing

        playbook = HealingPlaybook(
            name=name,
            anomaly_type=anomaly_type,
            anomaly_severity=anomaly_severity,
            healing_action=healing_action,
            configuration=configuration,
            steps=steps or [],
            genesis_key_id=genesis_key_id,
            last_used=datetime.now(),
            last_success=datetime.now(),
            trust_score=0.75,
        )
        self.session.add(playbook)
        self.session.commit()
        logger.info(f"[PLAYBOOK] Created new playbook '{name}'")
        return playbook

    def record_failure(self, anomaly_type: str, healing_action: str, anomaly_severity: str):
        """Record that a playbook's strategy failed."""
        playbook = self.session.query(HealingPlaybook).filter(
            HealingPlaybook.anomaly_type == anomaly_type,
            HealingPlaybook.healing_action == healing_action,
            HealingPlaybook.anomaly_severity == anomaly_severity,
        ).first()

        if playbook:
            playbook.failure_count += 1
            playbook.trust_score = max(0.1, playbook.trust_score - 0.05)
            playbook.last_used = datetime.now()
            if playbook.failure_count > playbook.success_count * 2:
                playbook.is_active = False
                logger.warning(f"[PLAYBOOK] Deactivated playbook '{playbook.name}' (too many failures)")
            self.session.commit()

    def find_playbook(self, anomaly_type: str, anomaly_severity: str = None) -> Optional[HealingPlaybook]:
        """Find the best playbook for an anomaly type."""
        query = self.session.query(HealingPlaybook).filter(
            HealingPlaybook.anomaly_type == anomaly_type,
            HealingPlaybook.is_active == True,
        )
        if anomaly_severity:
            query = query.filter(HealingPlaybook.anomaly_severity == anomaly_severity)

        return query.order_by(HealingPlaybook.trust_score.desc()).first()

    def list_playbooks(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all playbooks."""
        query = self.session.query(HealingPlaybook)
        if active_only:
            query = query.filter(HealingPlaybook.is_active == True)

        playbooks = query.order_by(HealingPlaybook.trust_score.desc()).all()
        return [
            {
                "id": p.id,
                "name": p.name,
                "anomaly_type": p.anomaly_type,
                "healing_action": p.healing_action,
                "trust_score": p.trust_score,
                "success_count": p.success_count,
                "failure_count": p.failure_count,
                "is_active": p.is_active,
                "last_used": p.last_used.isoformat() if p.last_used else None,
            }
            for p in playbooks
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get playbook statistics."""
        total = self.session.query(HealingPlaybook).count()
        active = self.session.query(HealingPlaybook).filter(HealingPlaybook.is_active == True).count()
        total_uses = sum(
            p.success_count + p.failure_count
            for p in self.session.query(HealingPlaybook).all()
        ) if total > 0 else 0

        return {
            "total_playbooks": total,
            "active_playbooks": active,
            "total_uses": total_uses,
        }
