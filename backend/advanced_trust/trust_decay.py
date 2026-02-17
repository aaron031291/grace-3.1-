"""
Trust Decay + Auto Re-verification Engine

Data verified 6 months ago should have lower trust than data verified
yesterday. The world changes. Grace should periodically re-verify aging
high-trust knowledge by running it through the verification pipeline again.

The forgetting curve handles memory decay -- but trust decay is different.
A fact can be remembered perfectly but be outdated.
"""

import logging
import math
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class DecayModel(str, Enum):
    """Models for trust decay over time."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    STEP = "step"


class VerificationUrgency(str, Enum):
    """Urgency of re-verification."""
    CRITICAL = "critical"    # Trust below floor, re-verify immediately
    HIGH = "high"            # Trust decayed significantly
    MEDIUM = "medium"        # Trust moderately decayed
    LOW = "low"              # Minor decay, routine re-verification
    NONE = "none"            # No re-verification needed


@dataclass
class TrustRecord:
    """A record of trust for a data item with decay tracking."""
    item_id: str
    domain: Optional[str] = None
    original_trust: float = 0.5
    current_trust: float = 0.5
    verified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_decay_check: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    verification_count: int = 0
    decay_model: DecayModel = DecayModel.EXPONENTIAL
    half_life_days: float = 180.0  # Trust halves every 180 days
    trust_floor: float = 0.1  # Never decay below this
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecayCheckResult:
    """Result of a decay check."""
    item_id: str
    old_trust: float
    new_trust: float
    decay_amount: float
    days_since_verification: float
    urgency: VerificationUrgency
    needs_reverification: bool


@dataclass
class ReverificationTask:
    """A task to re-verify a data item."""
    task_id: str
    item_id: str
    urgency: VerificationUrgency
    current_trust: float
    days_since_verification: float
    domain: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    result_trust: Optional[float] = None
    status: str = "pending"  # pending, in_progress, completed, failed


class TrustDecayEngine:
    """
    Manages time-based trust decay and auto re-verification scheduling.

    Trust decays over time because the world changes. A fact verified
    6 months ago is less trustworthy than one verified yesterday, even
    if it was originally high-trust.

    Decay Models:
    - Exponential: trust = original * e^(-lambda * days)
    - Linear: trust = original - (rate * days)
    - Step: trust drops at specific intervals

    Re-verification is automatically scheduled when trust decays
    below thresholds.
    """

    # Default decay parameters
    DEFAULT_HALF_LIFE = 180  # days
    DEFAULT_TRUST_FLOOR = 0.1
    DEFAULT_REVERIFICATION_THRESHOLD = 0.4

    # Urgency thresholds
    URGENCY_THRESHOLDS = {
        VerificationUrgency.CRITICAL: 0.15,
        VerificationUrgency.HIGH: 0.25,
        VerificationUrgency.MEDIUM: 0.40,
        VerificationUrgency.LOW: 0.60,
    }

    # Domain-specific half-lives (some domains change faster)
    DOMAIN_HALF_LIVES = {
        "technology": 90,      # Tech changes fast
        "programming": 120,
        "security": 60,        # Security changes very fast
        "legal": 90,           # Laws change frequently
        "science": 365,        # Science moves slowly
        "mathematics": 3650,   # Math doesn't change
        "history": 3650,       # History doesn't change
        "general": 180,
    }

    def __init__(
        self,
        default_half_life: float = DEFAULT_HALF_LIFE,
        trust_floor: float = DEFAULT_TRUST_FLOOR,
        reverification_threshold: float = DEFAULT_REVERIFICATION_THRESHOLD,
    ):
        self.default_half_life = default_half_life
        self.trust_floor = trust_floor
        self.reverification_threshold = reverification_threshold
        self.records: Dict[str, TrustRecord] = {}
        self.reverification_queue: List[ReverificationTask] = []
        logger.info("[TRUST-DECAY] Engine initialized")

    def register_item(
        self,
        item_id: str,
        trust_score: float,
        domain: Optional[str] = None,
        decay_model: DecayModel = DecayModel.EXPONENTIAL,
        half_life_days: Optional[float] = None,
        verified_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TrustRecord:
        """
        Register a data item for trust decay tracking.

        Args:
            item_id: Unique identifier
            trust_score: Current trust score
            domain: Knowledge domain (affects half-life)
            decay_model: Model for decay
            half_life_days: Custom half-life (overrides domain default)
            verified_at: When the item was last verified
            metadata: Additional metadata

        Returns:
            TrustRecord
        """
        if half_life_days is None:
            half_life_days = self.DOMAIN_HALF_LIVES.get(
                domain or "general", self.default_half_life
            )

        record = TrustRecord(
            item_id=item_id,
            domain=domain,
            original_trust=trust_score,
            current_trust=trust_score,
            verified_at=verified_at or datetime.now(timezone.utc),
            decay_model=decay_model,
            half_life_days=half_life_days,
            trust_floor=self.trust_floor,
            metadata=metadata or {},
        )

        self.records[item_id] = record
        return record

    def check_decay(self, item_id: str) -> Optional[DecayCheckResult]:
        """
        Check and apply trust decay for an item.

        Args:
            item_id: Item to check

        Returns:
            DecayCheckResult or None if item not found
        """
        if item_id not in self.records:
            return None

        record = self.records[item_id]
        old_trust = record.current_trust
        days_since = (datetime.now(timezone.utc) - record.verified_at).total_seconds() / 86400

        # Apply decay model
        new_trust = self._apply_decay(record, days_since)
        decay_amount = old_trust - new_trust

        record.current_trust = new_trust
        record.last_decay_check = datetime.now(timezone.utc)

        # Determine urgency
        urgency = self._calculate_urgency(new_trust)
        needs_reverification = new_trust < self.reverification_threshold

        result = DecayCheckResult(
            item_id=item_id,
            old_trust=old_trust,
            new_trust=new_trust,
            decay_amount=decay_amount,
            days_since_verification=days_since,
            urgency=urgency,
            needs_reverification=needs_reverification,
        )

        if needs_reverification:
            self._schedule_reverification(record, urgency, days_since)

        return result

    def check_all_decay(self) -> List[DecayCheckResult]:
        """Check decay for all registered items."""
        results = []
        for item_id in list(self.records.keys()):
            result = self.check_decay(item_id)
            if result:
                results.append(result)
        return results

    def record_reverification(
        self, item_id: str, new_trust: float
    ) -> Optional[TrustRecord]:
        """
        Record that an item has been re-verified.

        Args:
            item_id: Item that was re-verified
            new_trust: New trust score after re-verification

        Returns:
            Updated TrustRecord
        """
        if item_id not in self.records:
            return None

        record = self.records[item_id]
        record.original_trust = new_trust
        record.current_trust = new_trust
        record.verified_at = datetime.now(timezone.utc)
        record.verification_count += 1
        record.last_decay_check = datetime.now(timezone.utc)

        # Mark any pending reverification tasks as completed
        for task in self.reverification_queue:
            if task.item_id == item_id and task.status == "pending":
                task.status = "completed"
                task.completed_at = datetime.now(timezone.utc)
                task.result_trust = new_trust

        return record

    def _apply_decay(self, record: TrustRecord, days: float) -> float:
        """Apply the decay model to calculate new trust."""
        if record.decay_model == DecayModel.EXPONENTIAL:
            # Exponential decay: T(t) = T0 * e^(-lambda*t)
            # lambda = ln(2) / half_life
            decay_lambda = math.log(2) / max(record.half_life_days, 1)
            decayed = record.original_trust * math.exp(-decay_lambda * days)
            return max(decayed, record.trust_floor)

        elif record.decay_model == DecayModel.LINEAR:
            # Linear decay: T(t) = T0 - (rate * t)
            rate = record.original_trust / (record.half_life_days * 2)
            decayed = record.original_trust - (rate * days)
            return max(decayed, record.trust_floor)

        elif record.decay_model == DecayModel.STEP:
            # Step decay: drops at specific intervals
            steps = int(days / (record.half_life_days / 4))
            step_size = (record.original_trust - record.trust_floor) / 8
            decayed = record.original_trust - (steps * step_size)
            return max(decayed, record.trust_floor)

        return record.current_trust

    def _calculate_urgency(self, trust: float) -> VerificationUrgency:
        """Calculate re-verification urgency based on current trust."""
        for urgency, threshold in self.URGENCY_THRESHOLDS.items():
            if trust <= threshold:
                return urgency
        return VerificationUrgency.NONE

    def _schedule_reverification(
        self,
        record: TrustRecord,
        urgency: VerificationUrgency,
        days_since: float,
    ) -> ReverificationTask:
        """Schedule a re-verification task."""
        # Check if already scheduled
        for task in self.reverification_queue:
            if task.item_id == record.item_id and task.status == "pending":
                # Update urgency if higher
                urgency_order = list(VerificationUrgency)
                if urgency_order.index(urgency) < urgency_order.index(
                    task.urgency
                ):
                    task.urgency = urgency
                return task

        task = ReverificationTask(
            task_id=f"rv-{uuid.uuid4().hex[:12]}",
            item_id=record.item_id,
            urgency=urgency,
            current_trust=record.current_trust,
            days_since_verification=days_since,
            domain=record.domain,
        )

        self.reverification_queue.append(task)
        logger.info(
            f"[TRUST-DECAY] Scheduled re-verification: {record.item_id} "
            f"(urgency={urgency.value}, trust={record.current_trust:.2f})"
        )
        return task

    def get_reverification_queue(
        self,
        urgency: Optional[VerificationUrgency] = None,
    ) -> List[ReverificationTask]:
        """Get pending re-verification tasks."""
        tasks = [t for t in self.reverification_queue if t.status == "pending"]
        if urgency:
            tasks = [t for t in tasks if t.urgency == urgency]
        # Sort by urgency (critical first)
        urgency_order = list(VerificationUrgency)
        tasks.sort(key=lambda t: urgency_order.index(t.urgency))
        return tasks

    def get_decayed_items(
        self, threshold: Optional[float] = None
    ) -> List[TrustRecord]:
        """Get items with trust below threshold."""
        threshold = threshold or self.reverification_threshold
        return [
            r for r in self.records.values()
            if r.current_trust < threshold
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        if not self.records:
            return {
                "total_items": 0,
                "average_trust": 0.5,
                "decayed_items": 0,
                "pending_reverifications": 0,
            }

        trusts = [r.current_trust for r in self.records.values()]
        pending = sum(
            1 for t in self.reverification_queue if t.status == "pending"
        )
        decayed = sum(
            1 for r in self.records.values()
            if r.current_trust < self.reverification_threshold
        )

        return {
            "total_items": len(self.records),
            "average_trust": sum(trusts) / len(trusts),
            "min_trust": min(trusts),
            "max_trust": max(trusts),
            "decayed_items": decayed,
            "pending_reverifications": pending,
            "completed_reverifications": sum(
                1 for t in self.reverification_queue if t.status == "completed"
            ),
        }
