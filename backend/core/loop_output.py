"""
Grace Loop Output - Standardized Loop Output Format

Addresses Clarity Class 3 (Loop Identity Ambiguity):
- Standard output format for all cognitive loops
- Reasoning chain tracking
- Metadata for audit and learning

All cognitive loops should return GraceLoopOutput.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List


class LoopType(Enum):
    """Types of cognitive loops in Grace."""
    OODA = "ooda"                    # Observe-Orient-Decide-Act
    REFLECTION = "reflection"        # Self-reflection loop
    LEARNING = "learning"            # Learning integration
    PLANNING = "planning"            # Task planning
    EXECUTION = "execution"          # Action execution
    GOVERNANCE = "governance"        # Governance evaluation
    MEMORY = "memory"                # Memory retrieval/storage
    REASONING = "reasoning"          # General reasoning


class LoopStatus(Enum):
    """Status of a loop execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    TIMEOUT = "timeout"


@dataclass
class ReasoningStep:
    """A single step in a reasoning chain."""
    step_id: str = field(default_factory=lambda: f"step-{uuid.uuid4().hex[:8]}")
    step_number: int = 0
    description: str = ""
    input_context: Dict[str, Any] = field(default_factory=dict)
    output: str = ""
    confidence: float = 0.5
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "description": self.description,
            "input_context": self.input_context,
            "output": self.output,
            "confidence": self.confidence,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class LoopMetadata:
    """Metadata for loop execution."""
    # Execution context
    triggered_by: str = "system"  # What triggered this loop
    parent_loop_id: Optional[str] = None  # If nested

    # Governance
    governance_decision_id: Optional[str] = None
    governance_approved: bool = True
    autonomy_tier: str = "tier_0_supervised"

    # Learning
    learnable: bool = True
    patterns_extracted: int = 0

    # Resources
    tokens_used: int = 0
    memory_queries: int = 0
    external_calls: int = 0

    # Tags for filtering
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "triggered_by": self.triggered_by,
            "parent_loop_id": self.parent_loop_id,
            "governance_decision_id": self.governance_decision_id,
            "governance_approved": self.governance_approved,
            "autonomy_tier": self.autonomy_tier,
            "learnable": self.learnable,
            "patterns_extracted": self.patterns_extracted,
            "tokens_used": self.tokens_used,
            "memory_queries": self.memory_queries,
            "external_calls": self.external_calls,
            "tags": self.tags,
        }


@dataclass
class GraceLoopOutput:
    """
    Standardized output from any Grace cognitive loop.

    Provides:
    - Unique loop identification
    - Reasoning chain with steps
    - Results with confidence
    - Full metadata for audit
    - Learning integration hooks

    Usage:
        output = GraceLoopOutput(
            loop_type=LoopType.OODA,
            input_context={"query": "What is the status?"},
        )

        output.add_reasoning_step(
            description="Observing current state",
            output="System is healthy",
            confidence=0.9,
        )

        output.complete(
            result={"status": "healthy"},
            confidence=0.85,
            summary="Determined system is healthy",
        )
    """

    # Identity
    loop_id: str = field(default_factory=lambda: f"loop-{uuid.uuid4().hex[:12]}")
    reasoning_chain_id: str = field(default_factory=lambda: f"chain-{uuid.uuid4().hex[:8]}")
    loop_type: LoopType = LoopType.REASONING

    # Input
    input_context: Dict[str, Any] = field(default_factory=dict)

    # Status
    status: LoopStatus = LoopStatus.PENDING

    # Reasoning chain
    reasoning_steps: List[ReasoningStep] = field(default_factory=list)

    # Results
    result: Dict[str, Any] = field(default_factory=dict)
    result_summary: str = ""
    confidence: float = 0.0

    # Errors
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: float = 0.0

    # Metadata
    metadata: LoopMetadata = field(default_factory=LoopMetadata)

    # =========================================================================
    # REASONING CHAIN
    # =========================================================================

    def add_reasoning_step(
        self,
        description: str,
        output: str = "",
        confidence: float = 0.5,
        input_context: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0.0,
        **metadata
    ) -> ReasoningStep:
        """Add a reasoning step to the chain."""
        step = ReasoningStep(
            step_number=len(self.reasoning_steps) + 1,
            description=description,
            input_context=input_context or {},
            output=output,
            confidence=confidence,
            duration_ms=duration_ms,
            metadata=metadata,
        )
        self.reasoning_steps.append(step)
        return step

    def get_reasoning_trace(self) -> str:
        """Get human-readable reasoning trace."""
        lines = [f"Loop {self.loop_id} ({self.loop_type.value}):"]

        for step in self.reasoning_steps:
            lines.append(
                f"  {step.step_number}. {step.description} "
                f"[confidence={step.confidence:.2f}]"
            )
            if step.output:
                lines.append(f"     → {step.output[:100]}...")

        return "\n".join(lines)

    # =========================================================================
    # LIFECYCLE
    # =========================================================================

    def start(self):
        """Mark loop as started."""
        self.status = LoopStatus.RUNNING
        self.started_at = datetime.utcnow()

    def complete(
        self,
        result: Dict[str, Any],
        confidence: float = 0.5,
        summary: str = "",
    ):
        """Mark loop as completed with result."""
        self.status = LoopStatus.COMPLETED
        self.result = result
        self.confidence = confidence
        self.result_summary = summary
        self.completed_at = datetime.utcnow()
        self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000

    def fail(self, error: str, details: Optional[Dict[str, Any]] = None):
        """Mark loop as failed."""
        self.status = LoopStatus.FAILED
        self.error = error
        self.error_details = details
        self.completed_at = datetime.utcnow()
        self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000

    def interrupt(self, reason: str):
        """Mark loop as interrupted."""
        self.status = LoopStatus.INTERRUPTED
        self.error = f"Interrupted: {reason}"
        self.completed_at = datetime.utcnow()
        self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def success(self) -> bool:
        """Whether loop completed successfully."""
        return self.status == LoopStatus.COMPLETED

    @property
    def failed(self) -> bool:
        """Whether loop failed."""
        return self.status in [LoopStatus.FAILED, LoopStatus.TIMEOUT]

    @property
    def step_count(self) -> int:
        """Number of reasoning steps."""
        return len(self.reasoning_steps)

    @property
    def average_step_confidence(self) -> float:
        """Average confidence across reasoning steps."""
        if not self.reasoning_steps:
            return 0.0
        return sum(s.confidence for s in self.reasoning_steps) / len(self.reasoning_steps)

    # =========================================================================
    # SERIALIZATION
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage/transmission."""
        return {
            "loop_id": self.loop_id,
            "reasoning_chain_id": self.reasoning_chain_id,
            "loop_type": self.loop_type.value,
            "input_context": self.input_context,
            "status": self.status.value,
            "reasoning_steps": [s.to_dict() for s in self.reasoning_steps],
            "result": self.result,
            "result_summary": self.result_summary,
            "confidence": self.confidence,
            "error": self.error,
            "error_details": self.error_details,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GraceLoopOutput':
        """Create from dictionary."""
        output = cls(
            loop_id=data.get("loop_id", f"loop-{uuid.uuid4().hex[:12]}"),
            reasoning_chain_id=data.get("reasoning_chain_id", f"chain-{uuid.uuid4().hex[:8]}"),
            loop_type=LoopType(data.get("loop_type", "reasoning")),
            input_context=data.get("input_context", {}),
            status=LoopStatus(data.get("status", "pending")),
            result=data.get("result", {}),
            result_summary=data.get("result_summary", ""),
            confidence=data.get("confidence", 0.0),
            error=data.get("error"),
            error_details=data.get("error_details"),
            duration_ms=data.get("duration_ms", 0.0),
        )

        # Parse timestamps
        if data.get("started_at"):
            output.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            output.completed_at = datetime.fromisoformat(data["completed_at"])

        # Parse reasoning steps
        for step_data in data.get("reasoning_steps", []):
            output.reasoning_steps.append(ReasoningStep(
                step_id=step_data.get("step_id", f"step-{uuid.uuid4().hex[:8]}"),
                step_number=step_data.get("step_number", 0),
                description=step_data.get("description", ""),
                input_context=step_data.get("input_context", {}),
                output=step_data.get("output", ""),
                confidence=step_data.get("confidence", 0.5),
                duration_ms=step_data.get("duration_ms", 0.0),
                metadata=step_data.get("metadata", {}),
            ))

        # Parse metadata
        if data.get("metadata"):
            meta = data["metadata"]
            output.metadata = LoopMetadata(
                triggered_by=meta.get("triggered_by", "system"),
                parent_loop_id=meta.get("parent_loop_id"),
                governance_decision_id=meta.get("governance_decision_id"),
                governance_approved=meta.get("governance_approved", True),
                autonomy_tier=meta.get("autonomy_tier", "tier_0_supervised"),
                learnable=meta.get("learnable", True),
                patterns_extracted=meta.get("patterns_extracted", 0),
                tokens_used=meta.get("tokens_used", 0),
                memory_queries=meta.get("memory_queries", 0),
                external_calls=meta.get("external_calls", 0),
                tags=meta.get("tags", []),
            )

        return output

    def __repr__(self) -> str:
        return (
            f"<GraceLoopOutput({self.loop_type.value}, "
            f"status={self.status.value}, "
            f"steps={self.step_count}, "
            f"confidence={self.confidence:.2f})>"
        )
