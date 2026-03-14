"""
Spindle Proof Certificate
Structured output from Z3 verification for audit, replay, and dispatch.
"""
import hashlib
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class SpindleProof:
    """Immutable proof certificate from Z3 SMT verification."""
    is_valid: bool
    result: str  # "SAT", "UNSAT", "UNKNOWN"
    reason: str
    domain_mask: int = 0
    intent_mask: int = 0
    state_mask: int = 0
    context_mask: int = 0
    timestamp: float = field(default_factory=time.time)
    constraint_hash: str = ""
    violated_rules: list = field(default_factory=list)

    def __post_init__(self):
        if not self.constraint_hash:
            # Hash of the masks + result for tamper detection
            payload = f"{self.domain_mask}:{self.intent_mask}:{self.state_mask}:{self.context_mask}:{self.result}:{self.timestamp}"
            self.constraint_hash = hashlib.sha256(payload.encode()).hexdigest()[:16]

    @property
    def masks(self) -> tuple:
        return (self.domain_mask, self.intent_mask, self.state_mask, self.context_mask)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "result": self.result,
            "reason": self.reason,
            "masks": {"domain": self.domain_mask, "intent": self.intent_mask, "state": self.state_mask, "context": self.context_mask},
            "timestamp": self.timestamp,
            "constraint_hash": self.constraint_hash,
            "violated_rules": self.violated_rules,
        }
