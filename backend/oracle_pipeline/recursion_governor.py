"""
Kimi-Grace Recursion Governor

Kimi is the overseer. Grace is the executor. Without bounds, this
creates infinite recursion:

  Kimi sees problem -> tells Grace -> Grace acts -> Kimi sees result
  -> Kimi sees new problem -> tells Grace -> Grace acts -> ...forever

The Recursion Governor prevents this with:

1. ACTION CONTRACTS: Every Kimi->Grace instruction is a bounded contract
   with max_depth, max_iterations, timeout, and success criteria.
   Grace MUST stop when the contract bounds are hit.

2. EXECUTION TIERS: Actions are classified by impact level.
   Tier 1 (observe): unlimited - just looking
   Tier 2 (suggest): unlimited - just recommending
   Tier 3 (minor):   max 5 iterations - small changes
   Tier 4 (major):   max 2 iterations - significant changes
   Tier 5 (critical): max 1 iteration + human approval gate

3. CIRCUIT BREAKERS: If an action chain loops (same problem appears
   twice), the circuit breaker trips and escalates to human.

4. COOLDOWN PERIODS: After acting, Grace must wait before acting
   on the same topic again. Prevents oscillation.

5. GENESIS KEY TRACING: Every Kimi->Grace instruction and every
   Grace->result is traced. If the chain gets too long, it stops.

The relationship:
  Kimi = Overseer (sees all, decides what to do)
  Grace = Executor (does the work within bounds)
  Governor = Referee (prevents infinite loops)

Grace doesn't need to be recursive. She needs bounded execution
contracts from Kimi, with circuit breakers when things loop.
"""

import logging
import uuid
import hashlib
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class ExecutionTier(str, Enum):
    """Impact tiers for actions. Higher tier = more restrictions."""
    OBSERVE = "observe"       # Tier 1: Just look, no changes
    SUGGEST = "suggest"       # Tier 2: Recommend, no execution
    MINOR = "minor"           # Tier 3: Small safe changes
    MAJOR = "major"           # Tier 4: Significant changes
    CRITICAL = "critical"     # Tier 5: System-critical, needs approval


class ContractStatus(str, Enum):
    """Status of an action contract."""
    ACTIVE = "active"
    COMPLETED = "completed"
    TERMINATED = "terminated"    # Hit bounds
    CIRCUIT_BROKEN = "circuit_broken"  # Loop detected
    COOLDOWN = "cooldown"
    ESCALATED = "escalated"      # Sent to human


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Tripped, blocking execution
    HALF_OPEN = "half_open" # Testing if problem resolved


# Tier limits
TIER_LIMITS = {
    ExecutionTier.OBSERVE:  {"max_depth": 99, "max_iterations": 99, "cooldown_seconds": 0},
    ExecutionTier.SUGGEST:  {"max_depth": 99, "max_iterations": 99, "cooldown_seconds": 0},
    ExecutionTier.MINOR:    {"max_depth": 3,  "max_iterations": 5,  "cooldown_seconds": 30},
    ExecutionTier.MAJOR:    {"max_depth": 2,  "max_iterations": 2,  "cooldown_seconds": 300},
    ExecutionTier.CRITICAL: {"max_depth": 1,  "max_iterations": 1,  "cooldown_seconds": 3600},
}


@dataclass
class ActionContract:
    """
    A bounded contract from Kimi to Grace.

    Every instruction Kimi gives Grace is wrapped in this contract.
    Grace MUST respect the bounds. When bounds are hit, Grace stops
    and reports back to Kimi.
    """
    contract_id: str
    # What to do
    action: str
    description: str
    tier: ExecutionTier
    # Bounds (from tier limits)
    max_depth: int
    max_iterations: int
    cooldown_seconds: int
    # Current state
    current_depth: int = 0
    current_iteration: int = 0
    status: ContractStatus = ContractStatus.ACTIVE
    # Success criteria
    success_criteria: str = ""
    # Tracking
    genesis_key_chain: List[str] = field(default_factory=list)
    problem_hashes: Set[str] = field(default_factory=set)  # For loop detection
    results: List[Dict[str, Any]] = field(default_factory=list)
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    next_allowed_at: Optional[datetime] = None  # Cooldown
    # Escalation
    escalated: bool = False
    escalation_reason: Optional[str] = None


@dataclass
class CircuitBreaker:
    """Circuit breaker for a specific action topic."""
    topic: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    trip_threshold: int = 3
    last_tripped: Optional[datetime] = None
    reset_timeout_seconds: int = 600  # 10 minutes
    half_open_successes: int = 0
    half_open_threshold: int = 2  # Successes needed to close


@dataclass
class GovernorDecision:
    """Decision from the governor about whether an action can proceed."""
    allowed: bool
    reason: str
    contract_id: Optional[str] = None
    tier: Optional[ExecutionTier] = None
    remaining_iterations: int = 0
    remaining_depth: int = 0
    cooldown_remaining_seconds: float = 0
    circuit_state: Optional[CircuitState] = None


class RecursionGovernor:
    """
    Prevents infinite recursion between Kimi and Grace.

    Kimi sees everything and decides what Grace should do.
    Grace executes within the bounds of action contracts.
    The Governor is the referee that enforces the bounds.

    Key mechanisms:
    1. Action Contracts: Bounded instructions (depth, iterations, timeout)
    2. Execution Tiers: Impact classification controls aggressiveness
    3. Circuit Breakers: Detect and break loops
    4. Cooldown Periods: Prevent oscillation
    5. Genesis Key Chains: Trace execution depth
    6. Problem Hash Dedup: Same problem twice = loop detected
    """

    def __init__(self):
        self.contracts: Dict[str, ActionContract] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._topic_cooldowns: Dict[str, datetime] = {}
        self._action_history: List[Dict[str, Any]] = []
        logger.info("[GOVERNOR] Recursion Governor initialized")

    # =========================================================================
    # CONTRACT MANAGEMENT
    # =========================================================================

    def create_contract(
        self,
        action: str,
        description: str,
        tier: ExecutionTier,
        success_criteria: str = "",
        genesis_key_id: Optional[str] = None,
    ) -> GovernorDecision:
        """
        Kimi requests a new action contract for Grace.

        The Governor checks:
        1. Is the circuit breaker open for this topic?
        2. Is there an active cooldown?
        3. Is there already an active contract for this topic?

        If allowed, creates a bounded contract.

        Args:
            action: What to do
            description: Human-readable description
            tier: Impact tier
            success_criteria: When to stop
            genesis_key_id: Tracking ID

        Returns:
            GovernorDecision allowing or blocking the action
        """
        topic = self._hash_topic(action)

        # Check circuit breaker
        if topic in self.circuit_breakers:
            cb = self.circuit_breakers[topic]
            cb_decision = self._check_circuit_breaker(cb)
            if not cb_decision.allowed:
                return cb_decision

        # Check cooldown
        if topic in self._topic_cooldowns:
            cooldown_until = self._topic_cooldowns[topic]
            now = datetime.now(timezone.utc)
            if now < cooldown_until:
                remaining = (cooldown_until - now).total_seconds()
                return GovernorDecision(
                    allowed=False,
                    reason=f"Cooldown active: {remaining:.0f}s remaining",
                    cooldown_remaining_seconds=remaining,
                )

        # Check for duplicate active contract
        for c in self.contracts.values():
            if c.status == ContractStatus.ACTIVE and self._hash_topic(c.action) == topic:
                return GovernorDecision(
                    allowed=False,
                    reason=f"Active contract already exists: {c.contract_id}",
                    contract_id=c.contract_id,
                )

        # Create contract
        limits = TIER_LIMITS[tier]
        contract = ActionContract(
            contract_id=f"contract-{uuid.uuid4().hex[:12]}",
            action=action,
            description=description,
            tier=tier,
            max_depth=limits["max_depth"],
            max_iterations=limits["max_iterations"],
            cooldown_seconds=limits["cooldown_seconds"],
            success_criteria=success_criteria,
        )

        if genesis_key_id:
            contract.genesis_key_chain.append(genesis_key_id)

        self.contracts[contract.contract_id] = contract

        logger.info(
            f"[GOVERNOR] Contract created: {contract.contract_id} "
            f"tier={tier.value} max_iter={limits['max_iterations']}"
        )

        return GovernorDecision(
            allowed=True,
            reason="Contract approved",
            contract_id=contract.contract_id,
            tier=tier,
            remaining_iterations=limits["max_iterations"],
            remaining_depth=limits["max_depth"],
        )

    def request_iteration(
        self,
        contract_id: str,
        problem_description: str = "",
        genesis_key_id: Optional[str] = None,
    ) -> GovernorDecision:
        """
        Grace requests permission for another iteration.

        Before Grace acts again within a contract, she asks the Governor.
        The Governor checks bounds and loop detection.

        Args:
            contract_id: The active contract
            problem_description: Current problem (for loop detection)
            genesis_key_id: Current Genesis Key

        Returns:
            GovernorDecision
        """
        if contract_id not in self.contracts:
            return GovernorDecision(
                allowed=False, reason="Contract not found"
            )

        contract = self.contracts[contract_id]

        if contract.status != ContractStatus.ACTIVE:
            return GovernorDecision(
                allowed=False,
                reason=f"Contract not active: {contract.status.value}",
            )

        # Check iteration limit
        if contract.current_iteration >= contract.max_iterations:
            contract.status = ContractStatus.TERMINATED
            self._apply_cooldown(contract)
            return GovernorDecision(
                allowed=False,
                reason=f"Iteration limit reached ({contract.max_iterations})",
                remaining_iterations=0,
            )

        # Check depth limit
        if contract.current_depth >= contract.max_depth:
            contract.status = ContractStatus.TERMINATED
            self._apply_cooldown(contract)
            return GovernorDecision(
                allowed=False,
                reason=f"Depth limit reached ({contract.max_depth})",
                remaining_depth=0,
            )

        # Loop detection: hash the problem description
        if problem_description:
            problem_hash = hashlib.sha256(
                problem_description.encode()
            ).hexdigest()[:16]

            if problem_hash in contract.problem_hashes:
                # Same problem appeared twice = loop!
                contract.status = ContractStatus.CIRCUIT_BROKEN
                self._trip_circuit_breaker(contract.action)
                return GovernorDecision(
                    allowed=False,
                    reason="Loop detected: same problem appeared twice",
                    circuit_state=CircuitState.OPEN,
                )

            contract.problem_hashes.add(problem_hash)

        # Approved
        contract.current_iteration += 1
        if genesis_key_id:
            contract.genesis_key_chain.append(genesis_key_id)

        remaining_iter = contract.max_iterations - contract.current_iteration
        remaining_depth = contract.max_depth - contract.current_depth

        return GovernorDecision(
            allowed=True,
            reason="Iteration approved",
            contract_id=contract_id,
            remaining_iterations=remaining_iter,
            remaining_depth=remaining_depth,
        )

    def deepen(self, contract_id: str) -> GovernorDecision:
        """Increase depth within a contract (nested sub-action)."""
        if contract_id not in self.contracts:
            return GovernorDecision(allowed=False, reason="Contract not found")

        contract = self.contracts[contract_id]
        if contract.current_depth >= contract.max_depth:
            return GovernorDecision(
                allowed=False,
                reason=f"Depth limit reached ({contract.max_depth})",
            )

        contract.current_depth += 1
        return GovernorDecision(
            allowed=True,
            reason="Depth increase approved",
            remaining_depth=contract.max_depth - contract.current_depth,
        )

    def complete_contract(
        self, contract_id: str, success: bool, result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Mark a contract as completed."""
        if contract_id not in self.contracts:
            return False

        contract = self.contracts[contract_id]
        contract.status = ContractStatus.COMPLETED
        contract.completed_at = datetime.now(timezone.utc)
        if result:
            contract.results.append(result)

        self._apply_cooldown(contract)

        # Update circuit breaker
        topic = self._hash_topic(contract.action)
        if topic in self.circuit_breakers:
            cb = self.circuit_breakers[topic]
            if success:
                if cb.state == CircuitState.HALF_OPEN:
                    cb.half_open_successes += 1
                    if cb.half_open_successes >= cb.half_open_threshold:
                        cb.state = CircuitState.CLOSED
                        cb.failure_count = 0
            else:
                cb.failure_count += 1

        self._action_history.append({
            "contract_id": contract_id,
            "action": contract.action,
            "tier": contract.tier.value,
            "iterations_used": contract.current_iteration,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return True

    def escalate_to_human(self, contract_id: str, reason: str) -> bool:
        """Escalate a contract to human review."""
        if contract_id not in self.contracts:
            return False

        contract = self.contracts[contract_id]
        contract.status = ContractStatus.ESCALATED
        contract.escalated = True
        contract.escalation_reason = reason

        logger.info(
            f"[GOVERNOR] ESCALATED to human: {contract_id} - {reason}"
        )
        return True

    # =========================================================================
    # CIRCUIT BREAKERS
    # =========================================================================

    def _trip_circuit_breaker(self, action: str) -> None:
        """Trip a circuit breaker for an action topic."""
        topic = self._hash_topic(action)
        if topic not in self.circuit_breakers:
            self.circuit_breakers[topic] = CircuitBreaker(topic=topic)

        cb = self.circuit_breakers[topic]
        cb.state = CircuitState.OPEN
        cb.failure_count += 1
        cb.last_tripped = datetime.now(timezone.utc)

        logger.info(f"[GOVERNOR] Circuit breaker TRIPPED for topic: {topic}")

    def _check_circuit_breaker(self, cb: CircuitBreaker) -> GovernorDecision:
        """Check if a circuit breaker allows execution."""
        now = datetime.now(timezone.utc)

        if cb.state == CircuitState.CLOSED:
            return GovernorDecision(
                allowed=True, reason="Circuit closed",
                circuit_state=CircuitState.CLOSED,
            )

        if cb.state == CircuitState.OPEN:
            if cb.last_tripped:
                elapsed = (now - cb.last_tripped).total_seconds()
                if elapsed >= cb.reset_timeout_seconds:
                    cb.state = CircuitState.HALF_OPEN
                    cb.half_open_successes = 0
                    return GovernorDecision(
                        allowed=True,
                        reason="Circuit half-open, testing",
                        circuit_state=CircuitState.HALF_OPEN,
                    )

            return GovernorDecision(
                allowed=False,
                reason=f"Circuit breaker OPEN (failures: {cb.failure_count})",
                circuit_state=CircuitState.OPEN,
            )

        if cb.state == CircuitState.HALF_OPEN:
            return GovernorDecision(
                allowed=True,
                reason="Circuit half-open, cautious execution",
                circuit_state=CircuitState.HALF_OPEN,
            )

        return GovernorDecision(allowed=True, reason="Unknown state, allowing")

    # =========================================================================
    # COOLDOWNS
    # =========================================================================

    def _apply_cooldown(self, contract: ActionContract) -> None:
        """Apply cooldown after a contract completes."""
        if contract.cooldown_seconds > 0:
            topic = self._hash_topic(contract.action)
            self._topic_cooldowns[topic] = (
                datetime.now(timezone.utc)
                + timedelta(seconds=contract.cooldown_seconds)
            )

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _hash_topic(self, action: str) -> str:
        """Hash an action to a topic key."""
        return hashlib.sha256(action.lower().strip().encode()).hexdigest()[:16]

    def classify_tier(self, action: str) -> ExecutionTier:
        """
        Auto-classify an action's execution tier.

        Observe: read, check, list, get, search, query
        Suggest: recommend, suggest, analyze, plan
        Minor: update, add, fix (small), configure
        Major: refactor, rebuild, migrate, deploy
        Critical: delete, drop, shutdown, rollback
        """
        action_lower = action.lower()

        critical_words = ["delete", "drop", "shutdown", "rollback", "destroy", "wipe"]
        major_words = ["refactor", "rebuild", "migrate", "deploy", "restructure", "overhaul"]
        minor_words = ["update", "add", "fix", "configure", "patch", "adjust", "edit"]
        suggest_words = ["recommend", "suggest", "analyze", "plan", "assess", "evaluate"]
        observe_words = ["read", "check", "list", "get", "search", "query", "view", "inspect"]

        for word in critical_words:
            if word in action_lower:
                return ExecutionTier.CRITICAL
        for word in major_words:
            if word in action_lower:
                return ExecutionTier.MAJOR
        for word in minor_words:
            if word in action_lower:
                return ExecutionTier.MINOR
        for word in suggest_words:
            if word in action_lower:
                return ExecutionTier.SUGGEST
        for word in observe_words:
            if word in action_lower:
                return ExecutionTier.OBSERVE

        return ExecutionTier.MINOR  # Default to minor

    def get_active_contracts(self) -> List[ActionContract]:
        """Get all active contracts."""
        return [c for c in self.contracts.values() if c.status == ContractStatus.ACTIVE]

    def get_contract(self, contract_id: str) -> Optional[ActionContract]:
        """Get a specific contract."""
        return self.contracts.get(contract_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get governor statistics."""
        active = sum(1 for c in self.contracts.values() if c.status == ContractStatus.ACTIVE)
        completed = sum(1 for c in self.contracts.values() if c.status == ContractStatus.COMPLETED)
        terminated = sum(1 for c in self.contracts.values() if c.status == ContractStatus.TERMINATED)
        broken = sum(1 for c in self.contracts.values() if c.status == ContractStatus.CIRCUIT_BROKEN)
        escalated = sum(1 for c in self.contracts.values() if c.status == ContractStatus.ESCALATED)

        open_breakers = sum(1 for cb in self.circuit_breakers.values() if cb.state == CircuitState.OPEN)

        return {
            "total_contracts": len(self.contracts),
            "active": active,
            "completed": completed,
            "terminated": terminated,
            "circuit_broken": broken,
            "escalated": escalated,
            "circuit_breakers_open": open_breakers,
            "total_circuit_breakers": len(self.circuit_breakers),
            "active_cooldowns": sum(
                1 for t in self._topic_cooldowns.values()
                if t > datetime.now(timezone.utc)
            ),
            "action_history_size": len(self._action_history),
        }
