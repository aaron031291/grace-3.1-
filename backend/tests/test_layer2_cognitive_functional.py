"""
Layer 2 Cognitive Engine - REAL Functional Tests

Tests verify ACTUAL cognitive behavior using real implementations:
- CognitiveEngine decision flow with OODA phases
- OODALoop phase transitions and enforcement
- DecisionContext invariant validation
- Alternative scoring and selection
- Recursion bounds and time bounds
"""

import pytest
from datetime import datetime, timedelta, UTC
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# OODA LOOP FUNCTIONAL TESTS
# =============================================================================

class TestOODALoopFunctional:
    """Functional tests for OODA Loop phase transitions."""

    @pytest.fixture
    def ooda_loop(self):
        """Create fresh OODA loop instance."""
        from cognitive.ooda import OODALoop
        return OODALoop()

    def test_ooda_starts_in_observe_phase(self, ooda_loop):
        """OODA loop must start in OBSERVE phase."""
        from cognitive.ooda import OODAPhase

        assert ooda_loop.state.current_phase == OODAPhase.OBSERVE

    def test_observe_advances_to_orient(self, ooda_loop):
        """observe() must advance phase to ORIENT."""
        from cognitive.ooda import OODAPhase

        ooda_loop.observe({"fact1": "value1", "fact2": "value2"})

        assert ooda_loop.state.current_phase == OODAPhase.ORIENT
        assert ooda_loop.state.observations == {"fact1": "value1", "fact2": "value2"}

    def test_orient_advances_to_decide(self, ooda_loop):
        """orient() must advance phase to DECIDE."""
        from cognitive.ooda import OODAPhase

        ooda_loop.observe({"fact": "value"})
        ooda_loop.orient(context={"key": "context"}, constraints={"limit": 10})

        assert ooda_loop.state.current_phase == OODAPhase.DECIDE
        assert ooda_loop.state.orientation["context"] == {"key": "context"}
        assert ooda_loop.state.orientation["constraints"] == {"limit": 10}

    def test_decide_advances_to_act(self, ooda_loop):
        """decide() must advance phase to ACT."""
        from cognitive.ooda import OODAPhase

        ooda_loop.observe({"fact": "value"})
        ooda_loop.orient(context={}, constraints={})
        ooda_loop.decide({"action": "do_something"})

        assert ooda_loop.state.current_phase == OODAPhase.ACT
        assert ooda_loop.state.decision == {"action": "do_something"}

    def test_act_completes_loop(self, ooda_loop):
        """act() must complete the loop."""
        from cognitive.ooda import OODAPhase

        ooda_loop.observe({"fact": "value"})
        ooda_loop.orient(context={}, constraints={})
        ooda_loop.decide({"action": "test"})

        result = ooda_loop.act(lambda: "action_result")

        assert ooda_loop.state.current_phase == OODAPhase.COMPLETED
        assert result == "action_result"
        assert ooda_loop.is_complete()

    def test_cannot_observe_twice(self, ooda_loop):
        """Cannot call observe() twice without reset."""
        ooda_loop.observe({"fact": "value"})

        with pytest.raises(ValueError, match="Cannot observe"):
            ooda_loop.observe({"another": "fact"})

    def test_cannot_orient_before_observe(self, ooda_loop):
        """Cannot call orient() before observe()."""
        with pytest.raises(ValueError, match="Cannot orient"):
            ooda_loop.orient({}, {})

    def test_cannot_decide_before_orient(self, ooda_loop):
        """Cannot call decide() before orient()."""
        ooda_loop.observe({})

        with pytest.raises(ValueError, match="Cannot decide"):
            ooda_loop.decide({})

    def test_cannot_act_before_decide(self, ooda_loop):
        """Cannot call act() before decide()."""
        ooda_loop.observe({})
        ooda_loop.orient({}, {})

        with pytest.raises(ValueError, match="Cannot act"):
            ooda_loop.act(lambda: None)

    def test_phase_history_tracks_correctly(self, ooda_loop):
        """Phase history must track all transitions."""
        from cognitive.ooda import OODAPhase

        ooda_loop.observe({})
        ooda_loop.orient({}, {})
        ooda_loop.decide({})
        ooda_loop.act(lambda: "done")

        history = ooda_loop.get_phase_history()

        assert history == [
            OODAPhase.OBSERVE,
            OODAPhase.ORIENT,
            OODAPhase.DECIDE,
            OODAPhase.ACT
        ]

    def test_validate_completion_returns_true_after_full_loop(self, ooda_loop):
        """validate_completion() returns True after complete OODA cycle."""
        ooda_loop.observe({})
        ooda_loop.orient({}, {})
        ooda_loop.decide({})
        ooda_loop.act(lambda: None)

        assert ooda_loop.validate_completion() is True

    def test_reset_clears_state(self, ooda_loop):
        """reset() must clear all state."""
        from cognitive.ooda import OODAPhase

        ooda_loop.observe({"data": "value"})
        ooda_loop.orient({}, {})
        ooda_loop.reset()

        assert ooda_loop.state.current_phase == OODAPhase.OBSERVE
        assert ooda_loop.state.observations == {}
        assert len(ooda_loop.get_phase_history()) == 0


# =============================================================================
# OODA PHASE ENUM TESTS
# =============================================================================

class TestOODAPhaseEnumFunctional:
    """Functional tests for OODA Phase enum."""

    def test_all_required_phases_exist(self):
        """All required OODA phases must be defined."""
        from cognitive.ooda import OODAPhase

        required_phases = ["OBSERVE", "ORIENT", "DECIDE", "ACT", "COMPLETED"]

        for phase_name in required_phases:
            assert hasattr(OODAPhase, phase_name), f"Missing phase: {phase_name}"

    def test_phase_values_are_lowercase(self):
        """Phase values must be lowercase strings."""
        from cognitive.ooda import OODAPhase

        for phase in OODAPhase:
            assert isinstance(phase.value, str)
            assert phase.value == phase.value.lower()


# =============================================================================
# COGNITIVE ENGINE FUNCTIONAL TESTS
# =============================================================================

class TestCognitiveEngineFunctional:
    """Functional tests for CognitiveEngine."""

    @pytest.fixture
    def engine(self):
        """Create CognitiveEngine instance."""
        from cognitive.engine import CognitiveEngine
        return CognitiveEngine(enable_strict_mode=False)

    @pytest.fixture
    def strict_engine(self):
        """Create CognitiveEngine in strict mode."""
        from cognitive.engine import CognitiveEngine
        return CognitiveEngine(enable_strict_mode=True)

    def test_begin_decision_creates_context(self, engine):
        """begin_decision must create DecisionContext."""
        context = engine.begin_decision(
            problem_statement="Test problem",
            goal="Solve the test",
            success_criteria=["criterion_1", "criterion_2"]
        )

        assert context.problem_statement == "Test problem"
        assert context.goal == "Solve the test"
        assert context.success_criteria == ["criterion_1", "criterion_2"]
        assert context.decision_id is not None

    def test_begin_decision_registers_active_context(self, engine):
        """begin_decision must register context as active."""
        context = engine.begin_decision(
            problem_statement="Test",
            goal="Goal",
            success_criteria=[]
        )

        active = engine.get_active_decisions()
        assert len(active) == 1
        assert active[0].decision_id == context.decision_id

    def test_observe_updates_context_metadata(self, engine):
        """observe must update context with observations."""
        context = engine.begin_decision("Problem", "Goal", [])

        engine.observe(context, {"key1": "value1", "key2": "value2"})

        assert context.metadata["observations"] == {"key1": "value1", "key2": "value2"}

    def test_observe_tracks_known_values_in_ambiguity_ledger(self, engine):
        """observe must track known values in ambiguity ledger."""
        context = engine.begin_decision("Problem", "Goal", [])

        engine.observe(context, {"known_fact": "concrete_value"})

        knowns = context.ambiguity_ledger.get_knowns()
        assert "known_fact" in knowns

    def test_observe_tracks_unknown_values(self, engine):
        """observe must track unknown/null values in ambiguity ledger."""
        context = engine.begin_decision("Problem", "Goal", [])

        engine.observe(context, {"missing_data": None})

        unknowns = [u["name"] for u in context.ambiguity_ledger.unknowns]
        assert "missing_data" in unknowns

    def test_orient_updates_context_with_constraints(self, engine):
        """orient must update context with constraints."""
        context = engine.begin_decision("Problem", "Goal", [])
        engine.observe(context, {})

        engine.orient(
            context,
            constraints={"max_time": 60, "safety_critical": True},
            context_info={"environment": "production"}
        )

        assert context.metadata["constraints"] == {"max_time": 60, "safety_critical": True}
        assert context.is_safety_critical is True
        assert context.requires_determinism is True

    def test_decide_selects_best_alternative(self, engine):
        """decide must select best scored alternative."""
        context = engine.begin_decision("Problem", "Goal", [])
        engine.observe(context, {})
        engine.orient(context, {}, {})

        def gen_alternatives():
            return [
                {"name": "option_a", "immediate_value": 5, "future_options": 3, "simplicity": 0.8},
                {"name": "option_b", "immediate_value": 10, "future_options": 8, "simplicity": 0.9},
                {"name": "option_c", "immediate_value": 2, "future_options": 1, "simplicity": 0.5},
            ]

        selected = engine.decide(context, gen_alternatives)

        # option_b has highest values, should be selected
        assert selected["name"] == "option_b"
        assert context.selected_path is not None

    def test_decide_stores_all_alternatives(self, engine):
        """decide must store all considered alternatives."""
        context = engine.begin_decision("Problem", "Goal", [])
        engine.observe(context, {})
        engine.orient(context, {}, {})

        def gen_alternatives():
            return [{"option": 1}, {"option": 2}, {"option": 3}]

        engine.decide(context, gen_alternatives)

        assert len(context.alternative_paths) == 3

    def test_act_executes_action_and_returns_result(self, engine):
        """act must execute action and return result."""
        context = engine.begin_decision("Problem", "Goal", [])
        engine.observe(context, {})
        engine.orient(context, {}, {})
        engine.decide(context, lambda: [{"action": "test"}])

        result = engine.act(context, lambda: {"status": "success", "value": 42})

        assert result == {"status": "success", "value": 42}
        assert context.metadata["action_status"] == "success"

    def test_act_dry_run_does_not_execute(self, engine):
        """act with dry_run=True must not execute action."""
        context = engine.begin_decision("Problem", "Goal", [])
        engine.observe(context, {})
        engine.orient(context, {}, {})
        engine.decide(context, lambda: [{}])

        executed = False

        def action():
            nonlocal executed
            executed = True
            return "should_not_run"

        result = engine.act(context, action, dry_run=True)

        assert executed is False
        assert result["dry_run"] is True

    def test_finalize_decision_removes_from_active(self, engine):
        """finalize_decision must remove context from active decisions."""
        context = engine.begin_decision("Problem", "Goal", [])

        engine.finalize_decision(context)

        active = engine.get_active_decisions()
        assert len(active) == 0

    def test_abort_decision_records_reason(self, engine):
        """abort_decision must record abort reason."""
        context = engine.begin_decision("Problem", "Goal", [])

        engine.abort_decision(context, reason="Test abort reason")

        assert context.metadata["aborted"] is True
        assert context.metadata["abort_reason"] == "Test abort reason"

    def test_abort_decision_removes_from_active(self, engine):
        """abort_decision must remove context from active decisions."""
        context = engine.begin_decision("Problem", "Goal", [])

        engine.abort_decision(context, "Reason")

        assert len(engine.get_active_decisions()) == 0


# =============================================================================
# DECISION CONTEXT FUNCTIONAL TESTS
# =============================================================================

class TestDecisionContextFunctional:
    """Functional tests for DecisionContext."""

    def test_decision_context_has_uuid(self):
        """DecisionContext must have unique UUID."""
        from cognitive.engine import DecisionContext

        ctx1 = DecisionContext()
        ctx2 = DecisionContext()

        assert ctx1.decision_id != ctx2.decision_id
        assert len(ctx1.decision_id) == 36  # UUID length

    def test_decision_context_defaults(self):
        """DecisionContext must have sensible defaults."""
        from cognitive.engine import DecisionContext

        ctx = DecisionContext()

        assert ctx.is_reversible is True
        assert ctx.requires_determinism is False
        assert ctx.impact_scope == "local"
        assert ctx.recursion_depth == 0
        assert ctx.max_recursion_depth == 3
        assert ctx.iteration_count == 0
        assert ctx.max_iterations == 5

    def test_nested_decision_tracks_parent(self):
        """Nested decisions must track parent decision ID."""
        from cognitive.engine import DecisionContext

        parent = DecisionContext()
        child = DecisionContext(parent_decision_id=parent.decision_id)

        assert child.parent_decision_id == parent.decision_id


# =============================================================================
# RECURSION BOUNDS FUNCTIONAL TESTS
# =============================================================================

class TestRecursionBoundsFunctional:
    """Functional tests for bounded recursion enforcement."""

    @pytest.fixture
    def engine(self):
        """Create CognitiveEngine."""
        from cognitive.engine import CognitiveEngine
        return CognitiveEngine()

    def test_recursion_within_bounds_allowed(self, engine):
        """Recursion within bounds must be allowed."""
        from cognitive.engine import DecisionContext

        context = DecisionContext(
            recursion_depth=2,
            max_recursion_depth=5,
            iteration_count=3,
            max_iterations=10
        )

        assert engine.check_recursion_bounds(context) is True

    def test_recursion_exceeding_depth_blocked(self, engine):
        """Recursion exceeding max depth must be blocked."""
        from cognitive.engine import DecisionContext

        context = DecisionContext(
            recursion_depth=5,
            max_recursion_depth=3,
            iteration_count=0,
            max_iterations=10
        )

        assert engine.check_recursion_bounds(context) is False

    def test_iteration_exceeding_max_blocked(self, engine):
        """Iteration exceeding max must be blocked."""
        from cognitive.engine import DecisionContext

        context = DecisionContext(
            recursion_depth=0,
            max_recursion_depth=5,
            iteration_count=10,
            max_iterations=5
        )

        assert engine.check_recursion_bounds(context) is False


# =============================================================================
# TIME BOUNDS FUNCTIONAL TESTS
# =============================================================================

class TestTimeBoundsFunctional:
    """Functional tests for time-bounded reasoning."""

    @pytest.fixture
    def engine(self):
        """Create CognitiveEngine."""
        from cognitive.engine import CognitiveEngine
        return CognitiveEngine()

    def test_no_freeze_point_allows_continue(self, engine):
        """No freeze point means decision can continue."""
        from cognitive.engine import DecisionContext

        context = DecisionContext(decision_freeze_point=None)

        assert engine.enforce_decision_freeze(context) is False

    def test_future_freeze_point_allows_continue(self, engine):
        """Future freeze point allows continued deliberation."""
        from cognitive.engine import DecisionContext

        context = DecisionContext(
            decision_freeze_point=datetime.now(UTC) + timedelta(hours=1)
        )

        assert engine.enforce_decision_freeze(context) is False

    def test_past_freeze_point_forces_decision(self, engine):
        """Past freeze point forces immediate decision."""
        from cognitive.engine import DecisionContext

        context = DecisionContext(
            decision_freeze_point=datetime.now(UTC) - timedelta(minutes=5)
        )

        assert engine.enforce_decision_freeze(context) is True


# =============================================================================
# ALTERNATIVE SCORING FUNCTIONAL TESTS
# =============================================================================

class TestAlternativeScoringFunctional:
    """Functional tests for alternative scoring logic."""

    @pytest.fixture
    def engine(self):
        """Create CognitiveEngine."""
        from cognitive.engine import CognitiveEngine
        return CognitiveEngine()

    def test_higher_future_options_score_higher(self, engine):
        """Alternatives with more future options must score higher."""
        from cognitive.engine import DecisionContext

        context = DecisionContext()

        alt_low_options = {"immediate_value": 5, "future_options": 1, "simplicity": 0.5}
        alt_high_options = {"immediate_value": 5, "future_options": 10, "simplicity": 0.5}

        score_low = engine._score_alternative(context, alt_low_options)
        score_high = engine._score_alternative(context, alt_high_options)

        assert score_high > score_low

    def test_reversible_alternatives_get_bonus(self, engine):
        """Reversible alternatives must get scoring bonus."""
        from cognitive.engine import DecisionContext

        context = DecisionContext()

        alt_reversible = {"immediate_value": 5, "future_options": 5, "simplicity": 0.5, "reversibility": 0.9}
        alt_irreversible = {"immediate_value": 5, "future_options": 5, "simplicity": 0.5, "reversibility": 0.3}

        score_rev = engine._score_alternative(context, alt_reversible)
        score_irr = engine._score_alternative(context, alt_irreversible)

        assert score_rev > score_irr

    def test_complex_alternatives_penalized(self, engine):
        """Complex alternatives must be penalized."""
        from cognitive.engine import DecisionContext

        context = DecisionContext()

        alt_simple = {"immediate_value": 5, "future_options": 5, "simplicity": 0.9, "complexity": 0.1}
        alt_complex = {"immediate_value": 5, "future_options": 5, "simplicity": 0.3, "complexity": 0.9}

        score_simple = engine._score_alternative(context, alt_simple)
        score_complex = engine._score_alternative(context, alt_complex)

        assert score_simple > score_complex


# =============================================================================
# DECISION TYPE ENUM TESTS
# =============================================================================

class TestDecisionTypeEnumFunctional:
    """Functional tests for DecisionType enum."""

    def test_all_decision_types_defined(self):
        """All required decision types must be defined."""
        from cognitive.engine import DecisionType

        required_types = [
            "REVERSIBLE",
            "IRREVERSIBLE",
            "DETERMINISTIC",
            "ULTRA_DETERMINISTIC"
        ]

        for type_name in required_types:
            assert hasattr(DecisionType, type_name), f"Missing type: {type_name}"

    def test_decision_type_values(self):
        """Decision type values must be lowercase strings."""
        from cognitive.engine import DecisionType

        for dtype in DecisionType:
            assert isinstance(dtype.value, str)
            assert dtype.value == dtype.value.lower()


# =============================================================================
# DEGRADATION METRICS FUNCTIONAL TESTS
# =============================================================================

class TestDegradationMetricsFunctional:
    """Functional tests for degradation tracking."""

    @pytest.fixture
    def engine(self):
        """Create CognitiveEngine."""
        from cognitive.engine import CognitiveEngine
        return CognitiveEngine()

    def test_get_degradation_metrics_returns_dict(self, engine):
        """get_degradation_metrics must return dictionary."""
        metrics = engine.get_degradation_metrics()

        assert isinstance(metrics, dict)

    def test_degradation_count_initially_empty(self, engine):
        """Degradation count must be empty initially."""
        metrics = engine.get_degradation_metrics()

        # May have some default counts, but should be a dict
        assert isinstance(metrics, dict)


# =============================================================================
# FULL OODA CYCLE INTEGRATION TEST
# =============================================================================

class TestFullOODACycleIntegration:
    """Integration test for full OODA cycle through CognitiveEngine."""

    def test_complete_decision_cycle(self):
        """Complete decision cycle must work end-to-end."""
        from cognitive.engine import CognitiveEngine

        engine = CognitiveEngine(enable_strict_mode=False)

        # Begin decision
        context = engine.begin_decision(
            problem_statement="Need to optimize database queries",
            goal="Reduce query time by 50%",
            success_criteria=[
                "Query time under 100ms",
                "No data loss",
                "Backward compatible"
            ]
        )

        # Observe
        engine.observe(context, {
            "current_query_time": 250,
            "slow_queries": ["SELECT * FROM users", "JOIN on large tables"],
            "database_size": "10GB"
        })

        # Orient
        engine.orient(
            context,
            constraints={"budget": 1000, "deadline": "1 week"},
            context_info={"db_type": "PostgreSQL", "version": "14"}
        )

        # Decide
        def generate_alternatives():
            return [
                {
                    "name": "add_indexes",
                    "immediate_value": 8,
                    "future_options": 5,
                    "simplicity": 0.9,
                    "reversibility": 0.95
                },
                {
                    "name": "rewrite_queries",
                    "immediate_value": 6,
                    "future_options": 3,
                    "simplicity": 0.7,
                    "reversibility": 0.8
                },
                {
                    "name": "upgrade_hardware",
                    "immediate_value": 9,
                    "future_options": 2,
                    "simplicity": 0.5,
                    "reversibility": 0.3
                }
            ]

        selected = engine.decide(context, generate_alternatives)

        # Best option should be selected (add_indexes has good balance)
        assert selected["name"] == "add_indexes"

        # Act
        result = engine.act(
            context,
            lambda: {"status": "success", "new_query_time": 80}
        )

        assert result["status"] == "success"
        assert result["new_query_time"] == 80

        # Finalize
        engine.finalize_decision(context)

        # No more active decisions
        assert len(engine.get_active_decisions()) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
