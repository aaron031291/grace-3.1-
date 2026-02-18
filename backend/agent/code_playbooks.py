"""
Code Agent Playbooks — Successful Configuration Tracking

The coding agent tracks every task it executes and stores successful
configurations as playbooks. When a similar task comes in, it consults
its playbook library first.

Playbooks capture:
- Task type (write/fix/refactor/test/debug)
- File patterns affected
- Strategy used (steps taken)
- Tests that passed
- Trust score earned
- Duration and efficiency

The code agent also monitors its own systems:
- Tracks its own pass/fail rate
- Creates playbooks from every success
- Records failures with root cause
- Self-analyzes performance trends
- Asks Kimi when stuck
- Consults healing system when degraded
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Text, DateTime, JSON, Boolean
from sqlalchemy.orm import Session

from database.base import BaseModel

logger = logging.getLogger(__name__)


class CodePlaybook(BaseModel):
    """
    A proven coding strategy stored in the database.

    Created from every successful code agent operation.
    Consulted before attempting new tasks of the same type.
    """
    __tablename__ = "code_playbooks"

    name = Column(String(200), nullable=False, index=True)
    task_type = Column(String(100), nullable=False, index=True)
    file_pattern = Column(String(200), nullable=True, index=True)
    language = Column(String(50), nullable=True)

    success_count = Column(Integer, default=1)
    failure_count = Column(Integer, default=0)
    trust_score = Column(Float, default=0.7)

    strategy = Column(JSON, nullable=False)
    steps = Column(JSON, nullable=True)
    tools_used = Column(JSON, nullable=True)
    tests_run = Column(JSON, nullable=True)

    avg_duration_ms = Column(Float, default=0.0)
    avg_lines_changed = Column(Float, default=0.0)
    avg_test_pass_rate = Column(Float, default=0.0)

    genesis_key_id = Column(String(100), nullable=True)
    last_used = Column(DateTime, nullable=True)
    last_success = Column(DateTime, nullable=True)

    is_active = Column(Boolean, default=True)
    playbook_metadata = Column(JSON, nullable=True)


class CodePlaybookManager:
    """
    Manages code playbooks for the coding agent.

    The coding agent calls this to:
    - Store successful task configurations
    - Look up strategies for similar tasks
    - Track its own performance over time
    - Self-monitor and self-improve
    """

    def __init__(self, session: Session):
        self.session = session

    def create_from_success(
        self,
        task_type: str,
        file_pattern: str = None,
        language: str = None,
        strategy: Dict[str, Any] = None,
        steps: List[str] = None,
        tools_used: List[str] = None,
        tests_run: Dict[str, Any] = None,
        duration_ms: float = 0.0,
        lines_changed: int = 0,
        test_pass_rate: float = 1.0,
        genesis_key_id: str = None,
    ) -> CodePlaybook:
        """Create or update a playbook from a successful code operation."""
        name = f"code_{task_type}_{file_pattern or 'general'}_{language or 'any'}"

        existing = self.session.query(CodePlaybook).filter(
            CodePlaybook.task_type == task_type,
            CodePlaybook.file_pattern == file_pattern,
            CodePlaybook.language == language,
        ).first()

        if existing:
            existing.success_count += 1
            existing.trust_score = min(0.99, existing.trust_score + 0.02)
            existing.last_used = datetime.now()
            existing.last_success = datetime.now()
            # Running averages
            n = existing.success_count
            existing.avg_duration_ms = ((existing.avg_duration_ms * (n-1)) + duration_ms) / n
            existing.avg_lines_changed = ((existing.avg_lines_changed * (n-1)) + lines_changed) / n
            existing.avg_test_pass_rate = ((existing.avg_test_pass_rate * (n-1)) + test_pass_rate) / n
            if strategy:
                existing.strategy = strategy
            if steps:
                existing.steps = steps
            self.session.commit()
            logger.info(f"[CODE-PLAYBOOK] Updated '{name}' (successes: {existing.success_count})")
            return existing

        playbook = CodePlaybook(
            name=name,
            task_type=task_type,
            file_pattern=file_pattern,
            language=language,
            strategy=strategy or {},
            steps=steps or [],
            tools_used=tools_used or [],
            tests_run=tests_run or {},
            avg_duration_ms=duration_ms,
            avg_lines_changed=float(lines_changed),
            avg_test_pass_rate=test_pass_rate,
            genesis_key_id=genesis_key_id,
            last_used=datetime.now(),
            last_success=datetime.now(),
            trust_score=0.7,
        )
        self.session.add(playbook)
        self.session.commit()
        logger.info(f"[CODE-PLAYBOOK] Created '{name}'")
        return playbook

    def record_failure(
        self,
        task_type: str,
        file_pattern: str = None,
        language: str = None,
        error: str = None,
    ):
        """Record a failure for a task type."""
        existing = self.session.query(CodePlaybook).filter(
            CodePlaybook.task_type == task_type,
            CodePlaybook.file_pattern == file_pattern,
            CodePlaybook.language == language,
        ).first()

        if existing:
            existing.failure_count += 1
            existing.trust_score = max(0.1, existing.trust_score - 0.05)
            existing.last_used = datetime.now()
            if existing.failure_count > existing.success_count * 3:
                existing.is_active = False
                logger.warning(f"[CODE-PLAYBOOK] Deactivated '{existing.name}' (too many failures)")
            self.session.commit()

    def find_playbook(
        self,
        task_type: str,
        file_pattern: str = None,
        language: str = None,
    ) -> Optional[CodePlaybook]:
        """Find the best playbook for a task."""
        query = self.session.query(CodePlaybook).filter(
            CodePlaybook.task_type == task_type,
            CodePlaybook.is_active == True,
        )
        if file_pattern:
            query = query.filter(
                (CodePlaybook.file_pattern == file_pattern) |
                (CodePlaybook.file_pattern == None)
            )
        if language:
            query = query.filter(
                (CodePlaybook.language == language) |
                (CodePlaybook.language == None)
            )
        return query.order_by(CodePlaybook.trust_score.desc()).first()

    def get_agent_performance(self) -> Dict[str, Any]:
        """Get the code agent's overall performance from its playbooks."""
        total = self.session.query(CodePlaybook).count()
        active = self.session.query(CodePlaybook).filter(CodePlaybook.is_active == True).count()

        if total == 0:
            return {"total_playbooks": 0, "pass_rate": 0, "avg_trust": 0}

        from sqlalchemy import func
        total_success = self.session.query(func.sum(CodePlaybook.success_count)).scalar() or 0
        total_failure = self.session.query(func.sum(CodePlaybook.failure_count)).scalar() or 0
        avg_trust = self.session.query(func.avg(CodePlaybook.trust_score)).filter(
            CodePlaybook.is_active == True
        ).scalar() or 0.5
        avg_test_rate = self.session.query(func.avg(CodePlaybook.avg_test_pass_rate)).filter(
            CodePlaybook.is_active == True
        ).scalar() or 0.0

        total_ops = total_success + total_failure
        pass_rate = total_success / max(total_ops, 1)

        return {
            "total_playbooks": total,
            "active_playbooks": active,
            "total_successes": int(total_success),
            "total_failures": int(total_failure),
            "pass_rate": round(pass_rate, 3),
            "avg_trust": round(float(avg_trust), 3),
            "avg_test_pass_rate": round(float(avg_test_rate), 3),
        }

    def list_playbooks(self, active_only: bool = True, limit: int = 50) -> List[Dict[str, Any]]:
        """List code playbooks."""
        query = self.session.query(CodePlaybook)
        if active_only:
            query = query.filter(CodePlaybook.is_active == True)

        playbooks = query.order_by(CodePlaybook.trust_score.desc()).limit(limit).all()
        return [
            {
                "name": p.name,
                "task_type": p.task_type,
                "file_pattern": p.file_pattern,
                "language": p.language,
                "trust_score": p.trust_score,
                "success_count": p.success_count,
                "failure_count": p.failure_count,
                "avg_duration_ms": p.avg_duration_ms,
                "avg_test_pass_rate": p.avg_test_pass_rate,
                "is_active": p.is_active,
            }
            for p in playbooks
        ]
