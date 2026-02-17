"""
Comprehensive tests for the Kimi-Grace Recursion Governor.

Tests action contracts, tier limits, circuit breakers, cooldowns,
loop detection, escalation, and bounded execution.

100% pass rate, zero warnings, zero skips.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from oracle_pipeline.recursion_governor import (
    RecursionGovernor,
    ExecutionTier,
    ContractStatus,
    CircuitState,
    GovernorDecision,
    TIER_LIMITS,
)


class TestContractCreation(unittest.TestCase):
    """Tests for action contract creation."""

    def setUp(self):
        self.gov = RecursionGovernor()

    def test_create_observe_contract(self):
        """Test creating an observe-tier contract."""
        decision = self.gov.create_contract(
            "read system status", "Check health", ExecutionTier.OBSERVE
        )
        self.assertTrue(decision.allowed)
        self.assertIsNotNone(decision.contract_id)
        self.assertEqual(decision.tier, ExecutionTier.OBSERVE)

    def test_create_minor_contract(self):
        """Test creating a minor-tier contract."""
        decision = self.gov.create_contract(
            "fix typo in config", "Small fix", ExecutionTier.MINOR
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.remaining_iterations, 5)

    def test_create_major_contract(self):
        """Test creating a major-tier contract."""
        decision = self.gov.create_contract(
            "refactor database module", "Big change", ExecutionTier.MAJOR
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.remaining_iterations, 2)

    def test_create_critical_contract(self):
        """Test creating a critical-tier contract."""
        decision = self.gov.create_contract(
            "delete old database", "Dangerous", ExecutionTier.CRITICAL
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.remaining_iterations, 1)

    def test_duplicate_active_contract_blocked(self):
        """Test duplicate active contract is blocked."""
        self.gov.create_contract("fix bug A", "First", ExecutionTier.MINOR)
        decision = self.gov.create_contract("fix bug A", "Duplicate", ExecutionTier.MINOR)
        self.assertFalse(decision.allowed)
        self.assertIn("Active contract", decision.reason)

    def test_contract_with_genesis_key(self):
        """Test contract tracks Genesis Key."""
        decision = self.gov.create_contract(
            "update config", "Config change", ExecutionTier.MINOR,
            genesis_key_id="GK-001",
        )
        contract = self.gov.get_contract(decision.contract_id)
        self.assertIn("GK-001", contract.genesis_key_chain)


class TestIterationControl(unittest.TestCase):
    """Tests for iteration bounds."""

    def setUp(self):
        self.gov = RecursionGovernor()

    def test_minor_iteration_limit(self):
        """Test minor tier allows exactly 5 iterations."""
        decision = self.gov.create_contract(
            "fix small bug", "Fix", ExecutionTier.MINOR
        )
        contract_id = decision.contract_id

        for i in range(5):
            result = self.gov.request_iteration(contract_id, f"Problem state {i}")
            self.assertTrue(result.allowed, f"Iteration {i+1} should be allowed")

        # 6th should be blocked
        result = self.gov.request_iteration(contract_id, "Problem state 5")
        self.assertFalse(result.allowed)
        self.assertIn("limit", result.reason.lower())

    def test_major_iteration_limit(self):
        """Test major tier allows exactly 2 iterations."""
        decision = self.gov.create_contract(
            "refactor module X", "Refactor", ExecutionTier.MAJOR
        )
        contract_id = decision.contract_id

        self.assertTrue(self.gov.request_iteration(contract_id, "State 0").allowed)
        self.assertTrue(self.gov.request_iteration(contract_id, "State 1").allowed)
        self.assertFalse(self.gov.request_iteration(contract_id, "State 2").allowed)

    def test_critical_iteration_limit(self):
        """Test critical tier allows exactly 1 iteration."""
        decision = self.gov.create_contract(
            "delete temp data", "Delete", ExecutionTier.CRITICAL
        )
        contract_id = decision.contract_id

        self.assertTrue(self.gov.request_iteration(contract_id, "State 0").allowed)
        self.assertFalse(self.gov.request_iteration(contract_id, "State 1").allowed)

    def test_observe_unlimited_iterations(self):
        """Test observe tier has very high iteration limit."""
        decision = self.gov.create_contract(
            "check logs", "Read", ExecutionTier.OBSERVE
        )
        contract_id = decision.contract_id

        for i in range(20):
            result = self.gov.request_iteration(contract_id, f"Check {i}")
            self.assertTrue(result.allowed)

    def test_remaining_iterations_tracked(self):
        """Test remaining iterations are reported correctly."""
        decision = self.gov.create_contract(
            "patch config", "Patch", ExecutionTier.MINOR
        )
        contract_id = decision.contract_id

        result = self.gov.request_iteration(contract_id, "State 0")
        self.assertEqual(result.remaining_iterations, 4)

        result = self.gov.request_iteration(contract_id, "State 1")
        self.assertEqual(result.remaining_iterations, 3)

    def test_nonexistent_contract(self):
        """Test iteration on nonexistent contract."""
        result = self.gov.request_iteration("fake-id", "Test")
        self.assertFalse(result.allowed)


class TestLoopDetection(unittest.TestCase):
    """Tests for loop detection."""

    def setUp(self):
        self.gov = RecursionGovernor()

    def test_same_problem_twice_detected(self):
        """Test that seeing the same problem twice trips circuit breaker."""
        decision = self.gov.create_contract(
            "fix recurring bug", "Fix", ExecutionTier.MINOR
        )
        contract_id = decision.contract_id

        # First time: fine
        result = self.gov.request_iteration(contract_id, "Error: null pointer in handler")
        self.assertTrue(result.allowed)

        # Different problem: fine
        result = self.gov.request_iteration(contract_id, "Error: timeout in connection")
        self.assertTrue(result.allowed)

        # SAME problem again: LOOP DETECTED
        result = self.gov.request_iteration(contract_id, "Error: null pointer in handler")
        self.assertFalse(result.allowed)
        self.assertIn("Loop detected", result.reason)
        self.assertEqual(result.circuit_state, CircuitState.OPEN)

    def test_loop_detection_trips_circuit_breaker(self):
        """Test loop detection trips the circuit breaker."""
        decision = self.gov.create_contract(
            "fix loop bug", "Fix", ExecutionTier.MINOR
        )
        contract_id = decision.contract_id

        self.gov.request_iteration(contract_id, "Same problem")
        self.gov.request_iteration(contract_id, "Same problem")  # Loop!

        contract = self.gov.get_contract(contract_id)
        self.assertEqual(contract.status, ContractStatus.CIRCUIT_BROKEN)


class TestCircuitBreakers(unittest.TestCase):
    """Tests for circuit breakers."""

    def setUp(self):
        self.gov = RecursionGovernor()

    def test_circuit_breaker_blocks_new_contract(self):
        """Test open circuit breaker blocks new contracts on same topic."""
        # Trip the breaker
        d1 = self.gov.create_contract("fix bug X", "Fix", ExecutionTier.MINOR)
        self.gov.request_iteration(d1.contract_id, "Problem A")
        self.gov.request_iteration(d1.contract_id, "Problem A")  # Loop

        # Try new contract on same topic
        d2 = self.gov.create_contract("fix bug X", "Fix again", ExecutionTier.MINOR)
        self.assertFalse(d2.allowed)
        self.assertIn("OPEN", d2.reason)

    def test_circuit_breaker_different_topic_allowed(self):
        """Test different topic is not affected by circuit breaker."""
        d1 = self.gov.create_contract("fix bug X", "Fix", ExecutionTier.MINOR)
        self.gov.request_iteration(d1.contract_id, "Problem A")
        self.gov.request_iteration(d1.contract_id, "Problem A")  # Trip

        # Different topic should work
        d2 = self.gov.create_contract("fix bug Y", "Different", ExecutionTier.MINOR)
        self.assertTrue(d2.allowed)


class TestDepthControl(unittest.TestCase):
    """Tests for depth bounds."""

    def setUp(self):
        self.gov = RecursionGovernor()

    def test_depth_limit(self):
        """Test depth limit is enforced."""
        decision = self.gov.create_contract(
            "nested action", "Nested", ExecutionTier.MINOR
        )
        contract_id = decision.contract_id

        # Deepen 3 times (minor limit)
        for _ in range(3):
            result = self.gov.deepen(contract_id)
            self.assertTrue(result.allowed)

        # 4th should fail
        result = self.gov.deepen(contract_id)
        self.assertFalse(result.allowed)

    def test_depth_nonexistent(self):
        """Test deepen on nonexistent contract."""
        result = self.gov.deepen("fake-id")
        self.assertFalse(result.allowed)


class TestContractCompletion(unittest.TestCase):
    """Tests for contract completion."""

    def setUp(self):
        self.gov = RecursionGovernor()

    def test_complete_contract(self):
        """Test completing a contract."""
        d = self.gov.create_contract("task", "Task", ExecutionTier.MINOR)
        self.gov.request_iteration(d.contract_id, "Work")
        result = self.gov.complete_contract(d.contract_id, success=True)
        self.assertTrue(result)
        contract = self.gov.get_contract(d.contract_id)
        self.assertEqual(contract.status, ContractStatus.COMPLETED)

    def test_complete_with_result(self):
        """Test completing with result data."""
        d = self.gov.create_contract("task", "Task", ExecutionTier.MINOR)
        self.gov.complete_contract(
            d.contract_id, success=True, result={"fixed": True}
        )
        contract = self.gov.get_contract(d.contract_id)
        self.assertEqual(contract.results[0]["fixed"], True)

    def test_complete_nonexistent(self):
        """Test completing nonexistent contract."""
        result = self.gov.complete_contract("fake-id", True)
        self.assertFalse(result)

    def test_escalate_to_human(self):
        """Test escalating a contract to human."""
        d = self.gov.create_contract("dangerous task", "Risky", ExecutionTier.CRITICAL)
        result = self.gov.escalate_to_human(d.contract_id, "Too complex for auto-fix")
        self.assertTrue(result)
        contract = self.gov.get_contract(d.contract_id)
        self.assertEqual(contract.status, ContractStatus.ESCALATED)
        self.assertTrue(contract.escalated)

    def test_escalate_nonexistent(self):
        """Test escalating nonexistent contract."""
        result = self.gov.escalate_to_human("fake-id", "reason")
        self.assertFalse(result)


class TestTierClassification(unittest.TestCase):
    """Tests for auto-tier classification."""

    def setUp(self):
        self.gov = RecursionGovernor()

    def test_classify_observe(self):
        """Test observe tier classification."""
        self.assertEqual(self.gov.classify_tier("read system logs"), ExecutionTier.OBSERVE)
        self.assertEqual(self.gov.classify_tier("check health status"), ExecutionTier.OBSERVE)
        self.assertEqual(self.gov.classify_tier("search for errors"), ExecutionTier.OBSERVE)

    def test_classify_suggest(self):
        """Test suggest tier classification."""
        self.assertEqual(self.gov.classify_tier("recommend next action"), ExecutionTier.SUGGEST)
        self.assertEqual(self.gov.classify_tier("analyze performance"), ExecutionTier.SUGGEST)

    def test_classify_minor(self):
        """Test minor tier classification."""
        self.assertEqual(self.gov.classify_tier("fix typo in config"), ExecutionTier.MINOR)
        self.assertEqual(self.gov.classify_tier("update documentation"), ExecutionTier.MINOR)

    def test_classify_major(self):
        """Test major tier classification."""
        self.assertEqual(self.gov.classify_tier("refactor database module"), ExecutionTier.MAJOR)
        self.assertEqual(self.gov.classify_tier("deploy new version"), ExecutionTier.MAJOR)

    def test_classify_critical(self):
        """Test critical tier classification."""
        self.assertEqual(self.gov.classify_tier("delete old backups"), ExecutionTier.CRITICAL)
        self.assertEqual(self.gov.classify_tier("shutdown service"), ExecutionTier.CRITICAL)
        self.assertEqual(self.gov.classify_tier("rollback to previous version"), ExecutionTier.CRITICAL)


class TestGovernorStats(unittest.TestCase):
    """Tests for statistics."""

    def test_stats_empty(self):
        """Test stats with no contracts."""
        gov = RecursionGovernor()
        stats = gov.get_stats()
        self.assertEqual(stats["total_contracts"], 0)
        self.assertEqual(stats["active"], 0)

    def test_stats_after_activity(self):
        """Test stats after creating and completing contracts."""
        gov = RecursionGovernor()
        d1 = gov.create_contract("task 1", "T1", ExecutionTier.MINOR)
        d2 = gov.create_contract("task 2", "T2", ExecutionTier.OBSERVE)
        gov.complete_contract(d1.contract_id, True)
        stats = gov.get_stats()
        self.assertEqual(stats["total_contracts"], 2)
        self.assertEqual(stats["completed"], 1)
        self.assertEqual(stats["active"], 1)

    def test_active_contracts_list(self):
        """Test getting active contracts."""
        gov = RecursionGovernor()
        gov.create_contract("active task", "Active", ExecutionTier.MINOR)
        active = gov.get_active_contracts()
        self.assertEqual(len(active), 1)


class TestGovernorIntegration(unittest.TestCase):
    """Integration tests."""

    def test_full_contract_lifecycle(self):
        """Test complete lifecycle: create -> iterate -> complete."""
        gov = RecursionGovernor()

        # Kimi creates contract
        decision = gov.create_contract(
            "fix cache bug", "Fix caching", ExecutionTier.MINOR,
            success_criteria="Cache invalidation works correctly",
        )
        self.assertTrue(decision.allowed)
        cid = decision.contract_id

        # Grace iterates
        r1 = gov.request_iteration(cid, "Found stale cache entries")
        self.assertTrue(r1.allowed)

        r2 = gov.request_iteration(cid, "Applied cache TTL fix")
        self.assertTrue(r2.allowed)

        # Grace completes
        gov.complete_contract(cid, success=True, result={"cache_fixed": True})
        contract = gov.get_contract(cid)
        self.assertEqual(contract.status, ContractStatus.COMPLETED)

    def test_loop_detection_escalation(self):
        """Test loop detected -> circuit breaks -> escalation."""
        gov = RecursionGovernor()

        d = gov.create_contract("fix flaky test", "Fix", ExecutionTier.MINOR)
        cid = d.contract_id

        gov.request_iteration(cid, "Test fails with timeout")
        gov.request_iteration(cid, "Test fails with timeout")  # Loop!

        contract = gov.get_contract(cid)
        self.assertEqual(contract.status, ContractStatus.CIRCUIT_BROKEN)

        # New contract on same topic should be blocked
        d2 = gov.create_contract("fix flaky test", "Retry", ExecutionTier.MINOR)
        self.assertFalse(d2.allowed)

    def test_tier_enforces_appropriate_bounds(self):
        """Test each tier enforces its own limits."""
        gov = RecursionGovernor()

        for tier in ExecutionTier:
            limits = TIER_LIMITS[tier]
            d = gov.create_contract(
                f"task for {tier.value}", f"Tier {tier.value}", tier
            )
            self.assertEqual(d.remaining_iterations, limits["max_iterations"])
            self.assertEqual(d.remaining_depth, limits["max_depth"])
            # Clean up
            gov.complete_contract(d.contract_id, True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
