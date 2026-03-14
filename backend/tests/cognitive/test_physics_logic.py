"""
Physics Module Logic Tests
===========================
Tests actual Z3 constraint solving, SpindleProof generation, bitmask geometry
verification, spindle gate validation, Z3 sandbox isolation, and Qwen pipeline
code cleanup.

Mocks ALL external dependencies (LLM calls, unified_memory, event stores).
"""
import pytest
import hashlib
import time
from unittest.mock import patch, MagicMock

z3 = pytest.importorskip("z3", reason="z3-solver required for physics tests")


# ── Bitmask Constants (mirror BrailleDictionary) ──────────────

DOMAIN_DATABASE = 1 << 0
DOMAIN_API      = 1 << 1
DOMAIN_MEMORY   = 1 << 2
DOMAIN_NETWORK  = 1 << 3
DOMAIN_SYS_CONF = 1 << 4

INTENT_START  = 1 << 8
INTENT_STOP   = 1 << 9
INTENT_DELETE = 1 << 10
INTENT_QUERY  = 1 << 11
INTENT_GRANT  = 1 << 12
INTENT_REPAIR = 1 << 13

STATE_FAILED    = 1 << 16
STATE_IMMUTABLE = 1 << 17
STATE_ACTIVE    = 1 << 18
STATE_UNKNOWN   = 1 << 19
STATE_STOPPED   = 1 << 20

PRIV_ADMIN  = 1 << 24
PRIV_USER   = 1 << 25
PRIV_SYSTEM = 1 << 26
PRIV_GUEST  = 1 << 27

CTX_MAINTENANCE = 1 << 32
CTX_EMERGENCY   = 1 << 33
CTX_ELEVATED    = 1 << 34
CTX_RATE_LIMITED = 1 << 35


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def geometry():
    from cognitive.physics.bitmask_geometry import HierarchicalZ3Geometry
    return HierarchicalZ3Geometry()


@pytest.fixture
def sandbox():
    from cognitive.physics.z3_sandbox import Z3Sandbox
    return Z3Sandbox()


# ═══════════════════════════════════════════════════════════════
# SpindleProof Tests
# ═══════════════════════════════════════════════════════════════

class TestSpindleProof:

    def test_proof_fields_and_hash(self):
        from cognitive.physics.spindle_proof import SpindleProof
        proof = SpindleProof(
            is_valid=True, result="SAT", reason="ok",
            domain_mask=1, intent_mask=2, state_mask=3, context_mask=4,
        )
        assert proof.is_valid is True
        assert proof.result == "SAT"
        assert len(proof.constraint_hash) == 16
        assert proof.masks == (1, 2, 3, 4)

    def test_proof_hash_deterministic(self):
        from cognitive.physics.spindle_proof import SpindleProof
        ts = 1700000000.0
        p1 = SpindleProof(is_valid=False, result="UNSAT", reason="bad",
                          domain_mask=5, intent_mask=6, state_mask=7,
                          context_mask=8, timestamp=ts)
        p2 = SpindleProof(is_valid=False, result="UNSAT", reason="bad",
                          domain_mask=5, intent_mask=6, state_mask=7,
                          context_mask=8, timestamp=ts)
        assert p1.constraint_hash == p2.constraint_hash

    def test_proof_hash_changes_with_masks(self):
        from cognitive.physics.spindle_proof import SpindleProof
        ts = 1700000000.0
        p1 = SpindleProof(is_valid=True, result="SAT", reason="ok",
                          domain_mask=1, intent_mask=2, state_mask=3,
                          context_mask=4, timestamp=ts)
        p2 = SpindleProof(is_valid=True, result="SAT", reason="ok",
                          domain_mask=99, intent_mask=2, state_mask=3,
                          context_mask=4, timestamp=ts)
        assert p1.constraint_hash != p2.constraint_hash

    def test_proof_to_dict(self):
        from cognitive.physics.spindle_proof import SpindleProof
        proof = SpindleProof(is_valid=True, result="SAT", reason="valid",
                             domain_mask=1, intent_mask=2, state_mask=3,
                             context_mask=4)
        d = proof.to_dict()
        assert d["is_valid"] is True
        assert d["result"] == "SAT"
        assert d["masks"]["domain"] == 1
        assert d["masks"]["intent"] == 2
        assert "constraint_hash" in d
        assert d["violated_rules"] == []

    def test_proof_violated_rules_preserved(self):
        from cognitive.physics.spindle_proof import SpindleProof
        proof = SpindleProof(is_valid=False, result="UNSAT", reason="fail",
                             violated_rules=["S1", "P2"])
        assert proof.violated_rules == ["S1", "P2"]
        assert proof.to_dict()["violated_rules"] == ["S1", "P2"]


# ═══════════════════════════════════════════════════════════════
# HierarchicalZ3Geometry Tests (real Z3 solving)
# ═══════════════════════════════════════════════════════════════

class TestBitmaskGeometry:

    def test_valid_query_on_active_database(self, geometry):
        """QUERY on ACTIVE DATABASE should be SAT (allowed)."""
        proof = geometry.verify_action(DOMAIN_DATABASE, INTENT_QUERY, STATE_ACTIVE, PRIV_USER)
        assert proof.is_valid is True
        assert proof.result == "SAT"

    def test_rule_s1_delete_immutable_blocked(self, geometry):
        """Rule S1: DELETE on IMMUTABLE → UNSAT."""
        proof = geometry.verify_action(DOMAIN_DATABASE, INTENT_DELETE, STATE_IMMUTABLE, PRIV_ADMIN | CTX_ELEVATED)
        assert proof.is_valid is False
        assert proof.result == "UNSAT"

    def test_rule_s2_start_failed_blocked(self, geometry):
        """Rule S2: START on FAILED → UNSAT."""
        proof = geometry.verify_action(DOMAIN_API, INTENT_START, STATE_FAILED, CTX_MAINTENANCE)
        assert proof.is_valid is False
        assert proof.result == "UNSAT"

    def test_rule_s3_stop_stopped_blocked(self, geometry):
        """Rule S3: STOP on already STOPPED → UNSAT."""
        proof = geometry.verify_action(DOMAIN_API, INTENT_STOP, STATE_STOPPED, CTX_MAINTENANCE)
        assert proof.is_valid is False
        assert proof.result == "UNSAT"

    def test_rule_p1_core_infra_needs_maintenance(self, geometry):
        """Rule P1: Mutating NETWORK without MAINTENANCE/EMERGENCY → UNSAT."""
        proof = geometry.verify_action(DOMAIN_NETWORK, INTENT_STOP, STATE_ACTIVE, PRIV_ADMIN)
        assert proof.is_valid is False
        assert proof.result == "UNSAT"

    def test_rule_p1_core_infra_with_maintenance_passes(self, geometry):
        """Rule P1: Mutating NETWORK WITH MAINTENANCE → SAT."""
        proof = geometry.verify_action(DOMAIN_NETWORK, INTENT_STOP, STATE_ACTIVE, CTX_MAINTENANCE)
        assert proof.is_valid is True
        assert proof.result == "SAT"

    def test_rule_p1_core_infra_with_emergency_passes(self, geometry):
        """Rule P1: Mutating SYS_CONF WITH EMERGENCY → SAT."""
        proof = geometry.verify_action(DOMAIN_SYS_CONF, INTENT_REPAIR, STATE_ACTIVE, CTX_EMERGENCY)
        assert proof.is_valid is True
        assert proof.result == "SAT"

    def test_rule_p2_user_db_mutation_needs_elevated(self, geometry):
        """Rule P2: USER mutating DATABASE without ELEVATED → UNSAT."""
        proof = geometry.verify_action(DOMAIN_DATABASE, INTENT_DELETE, STATE_ACTIVE, PRIV_USER)
        assert proof.is_valid is False
        assert proof.result == "UNSAT"

    def test_rule_p2_user_db_with_elevated_passes(self, geometry):
        """Rule P2: USER mutating DATABASE WITH ELEVATED → SAT."""
        proof = geometry.verify_action(DOMAIN_DATABASE, INTENT_START, STATE_ACTIVE,
                                       PRIV_USER | CTX_ELEVATED)
        assert proof.is_valid is True
        assert proof.result == "SAT"

    def test_rule_s4_rate_limited_start_blocked(self, geometry):
        """Rule S4: START when RATE_LIMITED → UNSAT."""
        proof = geometry.verify_action(DOMAIN_MEMORY, INTENT_START, STATE_ACTIVE, CTX_RATE_LIMITED)
        assert proof.is_valid is False
        assert proof.result == "UNSAT"

    def test_rule_p3_cascading_failure_prevention(self, geometry):
        """Rule P3: STOP NETWORK when STATE_FAILED → UNSAT."""
        proof = geometry.verify_action(DOMAIN_NETWORK, INTENT_STOP, STATE_FAILED, CTX_MAINTENANCE)
        assert proof.is_valid is False
        assert proof.result == "UNSAT"

    def test_proof_certificate_has_correct_masks(self, geometry):
        """verify_action returns proof with the exact masks we passed in."""
        d, i, s, c = DOMAIN_API, INTENT_QUERY, STATE_ACTIVE, PRIV_USER
        proof = geometry.verify_action(d, i, s, c)
        assert proof.domain_mask == d
        assert proof.intent_mask == i
        assert proof.state_mask == s
        assert proof.context_mask == c

    def test_solver_isolation_between_calls(self, geometry):
        """Successive calls should not pollute each other (push/pop)."""
        proof1 = geometry.verify_action(DOMAIN_DATABASE, INTENT_DELETE, STATE_IMMUTABLE, PRIV_ADMIN)
        assert proof1.is_valid is False  # UNSAT - delete immutable

        proof2 = geometry.verify_action(DOMAIN_DATABASE, INTENT_QUERY, STATE_ACTIVE, PRIV_USER)
        assert proof2.is_valid is True  # SAT - simple query


# ═══════════════════════════════════════════════════════════════
# Z3Sandbox Tests (subprocess mocked)
# ═══════════════════════════════════════════════════════════════

class TestZ3Sandbox:

    @patch("cognitive.physics.z3_sandbox.subprocess.run")
    def test_valid_snippet_returns_true(self, mock_run, sandbox):
        mock_run.return_value = MagicMock(returncode=0, stdout="SUCCESS: Rule parses", stderr="")
        ok, msg = sandbox.test_generated_constraint("self.solver.add(True)")
        assert ok is True
        assert "SUCCESS" in msg

    @patch("cognitive.physics.z3_sandbox.subprocess.run")
    def test_invalid_snippet_returns_false(self, mock_run, sandbox):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="SyntaxError: invalid")
        ok, msg = sandbox.test_generated_constraint("this is not python!!")
        assert ok is False
        assert "SyntaxError" in msg

    @patch("cognitive.physics.z3_sandbox.subprocess.run")
    def test_timeout_returns_false(self, mock_run, sandbox):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="python", timeout=5)
        ok, msg = sandbox.test_generated_constraint("while True: pass")
        assert ok is False
        assert "TIMEOUT" in msg

    @patch("cognitive.physics.z3_sandbox.subprocess.run")
    def test_exception_returns_sandbox_error(self, mock_run, sandbox):
        mock_run.side_effect = OSError("No such file")
        ok, msg = sandbox.test_generated_constraint("anything")
        assert ok is False
        assert "SANDBOX_ERROR" in msg

    def test_default_timeout(self, sandbox):
        assert sandbox.exec_timeout == 5.0


# ═══════════════════════════════════════════════════════════════
# QwenZ3Pipeline Tests (LLM calls fully mocked)
# ═══════════════════════════════════════════════════════════════

class TestQwenZ3Pipeline:

    @patch("cognitive.physics.qwen_z3_pipeline.get_llm_orchestrator")
    def test_generate_constraint_success(self, mock_orch):
        result_obj = MagicMock()
        result_obj.success = True
        result_obj.content = 'self.solver.add(Implies(True, True))'
        mock_orch.return_value.execute_task.return_value = result_obj

        from cognitive.physics.qwen_z3_pipeline import QwenZ3Pipeline
        pipe = QwenZ3Pipeline()
        code = pipe.generate_z3_constraint("Users cannot delete databases")
        assert code is not None
        assert "self.solver.add" in code

    @patch("cognitive.physics.qwen_z3_pipeline.get_llm_orchestrator")
    def test_generate_constraint_strips_markdown(self, mock_orch):
        result_obj = MagicMock()
        result_obj.success = True
        result_obj.content = '```python\nself.solver.add(True)\n```'
        mock_orch.return_value.execute_task.return_value = result_obj

        from cognitive.physics.qwen_z3_pipeline import QwenZ3Pipeline
        pipe = QwenZ3Pipeline()
        code = pipe.generate_z3_constraint("some rule")
        assert not code.startswith("```")
        assert not code.endswith("```")
        assert "self.solver.add" in code

    @patch("cognitive.physics.qwen_z3_pipeline.get_llm_orchestrator")
    def test_generate_constraint_failure_returns_none(self, mock_orch):
        result_obj = MagicMock()
        result_obj.success = False
        result_obj.error_message = "model unavailable"
        mock_orch.return_value.execute_task.return_value = result_obj

        from cognitive.physics.qwen_z3_pipeline import QwenZ3Pipeline
        pipe = QwenZ3Pipeline()
        code = pipe.generate_z3_constraint("rule that fails")
        assert code is None

    @patch("cognitive.physics.qwen_z3_pipeline.get_llm_orchestrator")
    def test_generate_constraint_exception_returns_none(self, mock_orch):
        mock_orch.return_value.execute_task.side_effect = RuntimeError("boom")

        from cognitive.physics.qwen_z3_pipeline import QwenZ3Pipeline
        pipe = QwenZ3Pipeline()
        code = pipe.generate_z3_constraint("crashing rule")
        assert code is None


# ═══════════════════════════════════════════════════════════════
# SpindleGate Tests (external validators mocked)
# ═══════════════════════════════════════════════════════════════

class TestSpindleGate:

    def _make_gate(self, validators):
        """Build a SpindleGate with ONLY the given validators (no defaults)."""
        from cognitive.physics.spindle_gate import SpindleGate
        gate = SpindleGate.__new__(SpindleGate)
        gate.quorum_ratio = 0.5
        gate.timeout = 2.0
        from concurrent.futures import ThreadPoolExecutor
        gate._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="test-gate")
        gate._validators = validators
        return gate

    @patch("cognitive.physics.spindle_gate.SpindleGate._run_validator")
    def test_gate_verdict_fields(self, _mock):
        from cognitive.physics.spindle_gate import GateVerdict
        v = GateVerdict(passed=True, quorum_met=True, votes_for=3,
                        votes_against=1, total_validators=4, wall_time_ms=12.5)
        assert v.confidence == 0.75
        assert v.passed is True

    def test_gate_verdict_confidence_zero_validators(self):
        from cognitive.physics.spindle_gate import GateVerdict
        v = GateVerdict(passed=False, quorum_met=False, votes_for=0,
                        votes_against=0, total_validators=0)
        assert v.confidence == 0.0

    @patch("cognitive.physics.spindle_gate.get_unified_memory", create=True)
    def test_gate_all_pass_quorum_met(self, mock_mem):
        mock_mem.side_effect = Exception("not available")
        validators = [
            ("v1", lambda d, i, s, c, ctx: (True, "ok", None)),
            ("v2", lambda d, i, s, c, ctx: (True, "ok", None)),
            ("v3", lambda d, i, s, c, ctx: (True, "ok", None)),
        ]
        gate = self._make_gate(validators)
        with patch("cognitive.physics.spindle_gate.get_unified_memory", side_effect=Exception):
            verdict = gate.verify(DOMAIN_API, INTENT_QUERY, STATE_ACTIVE, PRIV_USER)
        assert verdict.passed is True
        assert verdict.votes_for == 3

    @patch("cognitive.physics.spindle_gate.get_unified_memory", create=True)
    def test_gate_all_fail_quorum_not_met(self, mock_mem):
        mock_mem.side_effect = Exception("not available")
        validators = [
            ("v1", lambda d, i, s, c, ctx: (False, "no", None)),
            ("v2", lambda d, i, s, c, ctx: (False, "no", None)),
        ]
        gate = self._make_gate(validators)
        with patch("cognitive.physics.spindle_gate.get_unified_memory", side_effect=Exception):
            verdict = gate.verify(0, 0, 0, 0)
        assert verdict.passed is False
        assert verdict.votes_against == 2

    def test_validate_privilege_guest_delete_blocked(self):
        from cognitive.physics.spindle_gate import SpindleGate
        gate = SpindleGate.__new__(SpindleGate)
        passed, reason, _ = gate._validate_privilege(
            DOMAIN_DATABASE, INTENT_DELETE, STATE_ACTIVE, PRIV_GUEST, {}
        )
        assert passed is False
        assert "Guest" in reason

    def test_validate_privilege_admin_delete_allowed(self):
        from cognitive.physics.spindle_gate import SpindleGate
        gate = SpindleGate.__new__(SpindleGate)
        passed, reason, _ = gate._validate_privilege(
            DOMAIN_DATABASE, INTENT_DELETE, STATE_ACTIVE, PRIV_ADMIN, {}
        )
        assert passed is True

    def test_validate_privilege_guest_query_allowed(self):
        from cognitive.physics.spindle_gate import SpindleGate
        gate = SpindleGate.__new__(SpindleGate)
        passed, reason, _ = gate._validate_privilege(
            DOMAIN_DATABASE, INTENT_QUERY, STATE_ACTIVE, PRIV_GUEST, {}
        )
        assert passed is True

    def test_validator_result_dataclass(self):
        from cognitive.physics.spindle_gate import ValidatorResult
        vr = ValidatorResult(validator_name="test", passed=True,
                             reason="ok", duration_ms=1.5)
        assert vr.validator_name == "test"
        assert vr.passed is True
        assert vr.duration_ms == 1.5

    def test_add_validator(self):
        from cognitive.physics.spindle_gate import SpindleGate
        gate = self._make_gate([])
        gate.add_validator("custom", lambda d, i, s, c, ctx: (True, "ok", None))
        assert len(gate._validators) == 1
        assert gate._validators[0][0] == "custom"

    def test_run_validator_catches_crash(self):
        from cognitive.physics.spindle_gate import SpindleGate
        def crashing(d, i, s, c, ctx):
            raise ValueError("boom")
        vr, extra = SpindleGate._run_validator("crash_test", crashing, 0, 0, 0, 0, {})
        assert vr.passed is False
        assert "Crashed" in vr.reason
        assert extra is None
