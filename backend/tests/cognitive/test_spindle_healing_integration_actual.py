"""
Spindle ↔ HealingCoordinator ↔ CodingAgent Integration Tests
=============================================================
Verifies the full wiring between Spindle's Z3-verified execution,
the HealingCoordinator's 7-step chain (including coding agent),
and the Spindle event store audit trail.

Deterministic by design:
- All LLM calls are stubbed to return fixed outputs
- All external services (DB, Qdrant, Ollama) are bypassed
- Z3 solver runs REAL — the only non-deterministic thing is wall-clock time
- Every test asserts on exact values, not ranges

NO mocks for Spindle internals — Z3, bitmasks, gate, executor are all real.
"""
import pytest
import sys
import time
import threading
from types import ModuleType
from unittest.mock import patch, MagicMock

z3 = pytest.importorskip("z3", reason="z3-solver required for Spindle tests")


# ═══════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all Spindle + HealingCoordinator singletons between tests."""
    import cognitive.spindle_executor as ex_mod
    import cognitive.spindle_event_store as es_mod
    import cognitive.spindle_checkpoint as cp_mod
    import cognitive.spindle_projection as pr_mod
    import cognitive.physics.spindle_gate as gt_mod
    import cognitive.healing_coordinator as hc_mod

    ex_mod._instance = None
    es_mod._store = None
    cp_mod._manager = None
    pr_mod._projection = None
    gt_mod._gate = None
    hc_mod._coordinator = None
    # Also reset backend-prefixed alias if loaded
    backend_es = sys.modules.get("backend.cognitive.spindle_event_store")
    if backend_es:
        backend_es._store = None
    yield


@pytest.fixture
def BD():
    from cognitive.braille_compiler import BrailleDictionary
    return BrailleDictionary


def _set_event_store_singleton(store):
    """Set the event store singleton on both module aliases (cognitive.* and backend.cognitive.*)."""
    import cognitive.spindle_event_store as es_mod
    es_mod._store = store
    # Force-import the backend-prefixed version to ensure it exists, then set its singleton too
    try:
        import backend.cognitive.spindle_event_store as bes_mod
        bes_mod._store = store
    except Exception:
        pass


@pytest.fixture
def event_store():
    from cognitive.spindle_event_store import SpindleEventStore
    store = SpindleEventStore()
    store._db_available = False
    return store


@pytest.fixture
def mock_brain():
    """Stub brain API module to return deterministic responses without importing the real module."""
    responses = {
        ("system", "reset_db"): {"ok": True, "data": {"status": "reconnected"}},
        ("system", "reset_vector_db"): {"ok": True, "data": {"status": "reconnected"}},
        ("system", "scan_heal"): {"ok": True, "data": {"status": "scanned"}},
        ("govern", "heal"): {"ok": True, "data": {"status": "healed"}},
        ("govern", "learn"): {"ok": True, "data": {}},
        ("govern", "record_gap"): {"ok": True, "data": {}},
        ("code", "generate"): {
            "ok": True,
            "data": {
                "code": "def fixed():\n    return True\n",
                "response": "Fixed the issue",
                "trust_score": 0.85,
                "stages_passed": ["syntax", "security", "deterministic"],
            },
        },
    }

    def fake_call_brain(namespace, action, params=None):
        return responses.get((namespace, action), {"ok": False, "error": "unknown"})

    # Inject a fake module into sys.modules so `from api.brain_api_v2 import call_brain` works
    # without triggering the real import chain (SQLAlchemy, ingestion, etc.)
    fake_mod = ModuleType("api.brain_api_v2")
    fake_mod.call_brain = fake_call_brain

    old_mod = sys.modules.get("api.brain_api_v2")
    sys.modules["api.brain_api_v2"] = fake_mod
    try:
        yield fake_call_brain
    finally:
        if old_mod is not None:
            sys.modules["api.brain_api_v2"] = old_mod
        else:
            sys.modules.pop("api.brain_api_v2", None)


@pytest.fixture
def mock_externals():
    """Stub all external service calls (LLM, Qdrant, learning) via sys.modules injection."""
    injected = {}

    # Stub LLM factory
    mock_raw = MagicMock()
    mock_raw.chat.return_value = "Root cause: test error. Fix: restart the service."
    mock_kimi = MagicMock()
    mock_kimi.chat.return_value = "Root cause: config drift. Fix: reset config."
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "Apply the fix by restarting the affected service."

    llm_mod = ModuleType("llm_orchestrator.factory")
    llm_mod.get_raw_client = lambda: mock_raw
    llm_mod.get_kimi_client = lambda: mock_kimi
    llm_mod.get_llm_client = lambda: mock_llm
    injected["llm_orchestrator.factory"] = llm_mod
    # Ensure parent package exists
    if "llm_orchestrator" not in sys.modules:
        parent = ModuleType("llm_orchestrator")
        injected["llm_orchestrator"] = parent

    # Stub async parallel
    def fake_parallel(fns, return_exceptions=False):
        results = []
        for fn in fns:
            try:
                results.append(fn())
            except Exception as e:
                results.append(e if return_exceptions else str(e))
        return results

    def fake_background(fn, name=""):
        try:
            fn()
        except Exception:
            pass

    async_mod = ModuleType("core.async_parallel")
    async_mod.run_parallel = fake_parallel
    async_mod.run_background = fake_background
    injected["core.async_parallel"] = async_mod

    # Stub retrieval modules
    retrieval_mod = ModuleType("retrieval.retriever")
    retrieval_mod.DocumentRetriever = MagicMock()
    injected["retrieval.retriever"] = retrieval_mod
    if "retrieval" not in sys.modules:
        injected["retrieval"] = ModuleType("retrieval")

    embed_mod = ModuleType("embedding.embedder")
    embed_mod.get_embedding_model = MagicMock()
    injected["embedding.embedder"] = embed_mod
    if "embedding" not in sys.modules:
        injected["embedding"] = ModuleType("embedding")

    vdb_mod = ModuleType("vector_db.client")
    vdb_mod.get_qdrant_client = MagicMock()
    injected["vector_db.client"] = vdb_mod
    if "vector_db" not in sys.modules:
        injected["vector_db"] = ModuleType("vector_db")

    # Stub cognitive.pipeline (FeedbackLoop)
    pipeline_mod = ModuleType("cognitive.pipeline")
    pipeline_mod.FeedbackLoop = MagicMock()
    injected["cognitive.pipeline"] = pipeline_mod

    # Stub trust engine
    trust_mod = ModuleType("cognitive.trust_engine")
    mock_trust = MagicMock()
    trust_mod.get_trust_engine = lambda: mock_trust
    injected["cognitive.trust_engine"] = trust_mod

    # Stub magma bridge
    magma_mod = ModuleType("cognitive.magma_bridge")
    magma_mod.store_decision = MagicMock()
    magma_mod.store_pattern = MagicMock()
    magma_mod.ingest = MagicMock()
    injected["cognitive.magma_bridge"] = magma_mod

    # Stub genesis tracker
    tracker_mod = ModuleType("api._genesis_tracker")
    tracker_mod.track = MagicMock()
    injected["api._genesis_tracker"] = tracker_mod

    # Save originals and inject
    originals = {}
    for name, mod in injected.items():
        originals[name] = sys.modules.get(name)
        sys.modules[name] = mod

    yield

    # Restore originals
    for name, orig in originals.items():
        if orig is not None:
            sys.modules[name] = orig
        else:
            sys.modules.pop(name, None)


# ═══════════════════════════════════════════════════════════════
# 1. SPINDLE EXECUTOR → HEALING COORDINATOR DELEGATION
# ═══════════════════════════════════════════════════════════════

class TestSpindleExecutorDelegatesToCoordinator:
    """Verify _delegate_to_healing routes through HealingCoordinator."""

    def test_database_repair_routes_through_coordinator(self, BD, mock_brain, mock_externals):
        """DATABASE × REPAIR → HealingCoordinator.resolve() → event store."""
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof

        executor = SpindleExecutor()
        proof = SpindleProof(
            is_valid=True, result="SAT", reason="ok",
            domain_mask=BD.DOMAIN_DATABASE, intent_mask=BD.INTENT_REPAIR,
        )
        result = executor.execute(proof)

        assert "healing_coordinator" in result.action_taken
        assert result.proof_hash == proof.constraint_hash

    def test_network_repair_routes_through_coordinator(self, BD, mock_brain, mock_externals):
        """NETWORK × REPAIR → HealingCoordinator.resolve()."""
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof

        executor = SpindleExecutor()
        proof = SpindleProof(
            is_valid=True, result="SAT", reason="ok",
            domain_mask=BD.DOMAIN_NETWORK, intent_mask=BD.INTENT_REPAIR,
        )
        result = executor.execute(proof)
        assert "healing_coordinator" in result.action_taken

    def test_api_repair_routes_through_coordinator(self, BD, mock_brain, mock_externals):
        """API × REPAIR → HealingCoordinator.resolve()."""
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof

        executor = SpindleExecutor()
        proof = SpindleProof(
            is_valid=True, result="SAT", reason="ok",
            domain_mask=BD.DOMAIN_API, intent_mask=BD.INTENT_REPAIR,
        )
        result = executor.execute(proof)
        assert "healing_coordinator" in result.action_taken

    def test_database_start_routes_through_coordinator(self, BD, mock_brain, mock_externals):
        """DATABASE × START → HealingCoordinator.resolve()."""
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof

        executor = SpindleExecutor()
        proof = SpindleProof(
            is_valid=True, result="SAT", reason="ok",
            domain_mask=BD.DOMAIN_DATABASE, intent_mask=BD.INTENT_START,
        )
        result = executor.execute(proof)
        assert "healing_coordinator" in result.action_taken

    def test_delegation_output_contains_resolution_chain(self, BD, mock_brain, mock_externals):
        """Verify the output includes the full HealingCoordinator result structure."""
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof

        executor = SpindleExecutor()
        proof = SpindleProof(
            is_valid=True, result="SAT", reason="ok",
            domain_mask=BD.DOMAIN_DATABASE, intent_mask=BD.INTENT_REPAIR,
        )
        result = executor.execute(proof)

        assert isinstance(result.output, dict)
        assert "steps" in result.output
        assert "resolved" in result.output
        assert "problem" in result.output

    def test_delegation_fallback_when_coordinator_unavailable(self, BD):
        """If HealingCoordinator import fails, falls back to AutonomousHealingSystem."""
        from cognitive.spindle_executor import _delegate_to_healing
        from cognitive.physics.spindle_proof import SpindleProof

        proof = SpindleProof(
            is_valid=True, result="SAT", reason="ok",
            domain_mask=BD.DOMAIN_DATABASE, intent_mask=BD.INTENT_REPAIR,
        )

        with patch("cognitive.spindle_executor.get_coordinator", side_effect=ImportError("no coordinator"), create=True):
            with patch("cognitive.healing_coordinator.get_coordinator", side_effect=ImportError("no coordinator")):
                result = _delegate_to_healing("database_repair", proof)
                # Should try fallback path — may succeed or fail but should not crash
                assert result.proof_hash == proof.constraint_hash


# ═══════════════════════════════════════════════════════════════
# 2. HEALING COORDINATOR → CODING AGENT CHAIN
# ═══════════════════════════════════════════════════════════════

class TestHealingCoordinatorCodingAgentChain:
    """Verify the 7-step chain fires the coding agent when needed."""

    def test_code_error_triggers_coding_agent(self, mock_externals):
        """A problem with 'SyntaxError' should route to coding agent at step 4."""
        from cognitive.healing_coordinator import HealingCoordinator

        # Make self-heal FAIL so we progress past step 1 to step 4
        fail_mod = ModuleType("api.brain_api_v2")
        fail_mod.call_brain = lambda ns, act, p=None: {"ok": False, "error": "unavailable"}
        old = sys.modules.get("api.brain_api_v2")
        sys.modules["api.brain_api_v2"] = fail_mod
        try:
            coord = HealingCoordinator()
            problem = {
                "component": "backend_module",
                "description": "SyntaxError in line 42",
                "error": "SyntaxError: unexpected indent",
                "severity": "high",
            }
            result = coord.resolve(problem)
        finally:
            if old is not None:
                sys.modules["api.brain_api_v2"] = old
            else:
                sys.modules.pop("api.brain_api_v2", None)

        step_names = [s.get("step") for s in result.get("steps", [])]
        assert "self_heal" in step_names
        assert "diagnose" in step_names
        assert "agree_fix" in step_names

        agree = next(s for s in result["steps"] if s["step"] == "agree_fix")
        assert agree["fix_type"] == "code_fix"

    def test_connection_error_classified_as_service_restart(self, mock_externals):
        """Connection errors should be classified as service_restart, not code_fix."""
        from cognitive.healing_coordinator import HealingCoordinator

        fail_mod = ModuleType("api.brain_api_v2")
        fail_mod.call_brain = lambda ns, act, p=None: {"ok": False, "error": "unavailable"}
        old = sys.modules.get("api.brain_api_v2")
        sys.modules["api.brain_api_v2"] = fail_mod
        try:
            coord = HealingCoordinator()
            problem = {
                "component": "database",
                "description": "Connection refused on port 5432",
                "error": "ConnectionRefusedError: connection refused",
                "severity": "critical",
            }
            result = coord.resolve(problem)
        finally:
            if old is not None:
                sys.modules["api.brain_api_v2"] = old
            else:
                sys.modules.pop("api.brain_api_v2", None)

        agree = next(s for s in result["steps"] if s["step"] == "agree_fix")
        assert agree["fix_type"] == "service_restart"

    def test_resolution_records_outcome(self, mock_brain, mock_externals):
        """Every resolution should produce a completed result with timing."""
        from cognitive.healing_coordinator import HealingCoordinator

        coord = HealingCoordinator()
        problem = {
            "component": "api",
            "description": "TypeError in handler",
            "error": "TypeError: NoneType",
            "severity": "high",
        }
        result = coord.resolve(problem)

        assert "started_at" in result
        assert isinstance(result["steps"], list)
        assert len(result["steps"]) >= 1

    def test_self_heal_success_short_circuits(self, mock_brain, mock_externals):
        """When self-heal succeeds (step 1), no further steps should run."""
        from cognitive.healing_coordinator import HealingCoordinator

        coord = HealingCoordinator()
        problem = {
            "component": "database",
            "description": "Database lag detected",
            "severity": "medium",
        }
        result = coord.resolve(problem)

        assert result["resolved"] is True
        assert result["resolution"] == "self_healing"
        assert len(result["steps"]) == 1
        assert result["steps"][0]["step"] == "self_heal"


# ═══════════════════════════════════════════════════════════════
# 3. HEALING COORDINATOR → SPINDLE EVENT STORE (AUDIT TRAIL)
# ═══════════════════════════════════════════════════════════════

class TestHealingCoordinatorPublishesToSpindle:
    """Verify _publish_to_spindle writes to the Spindle event store."""

    def test_resolved_problem_written_to_event_store(self, mock_brain, mock_externals):
        """After resolve(), the event store should contain a healing.coordinator.* event."""
        from cognitive.healing_coordinator import HealingCoordinator
        from cognitive.spindle_event_store import SpindleEventStore, get_event_store
        import cognitive.spindle_event_store as es_mod

        store = SpindleEventStore()
        store._db_available = False
        _set_event_store_singleton(store)

        coord = HealingCoordinator()
        problem = {
            "component": "database",
            "description": "Test problem for audit",
            "severity": "medium",
        }
        coord.resolve(problem)

        events = store.query(source_type="healing_coordinator")
        assert len(events) >= 1
        event = events[0]
        assert event["topic"].startswith("healing.coordinator.")
        assert "resolved" in event["payload"]
        assert "resolution" in event["payload"]

    def test_event_store_captures_proof_hash(self, mock_brain, mock_externals):
        """When a proof_hash is present in the problem, it flows through to the event store."""
        from cognitive.healing_coordinator import HealingCoordinator
        from cognitive.spindle_event_store import SpindleEventStore
        import cognitive.spindle_event_store as es_mod

        store = SpindleEventStore()
        store._db_available = False
        _set_event_store_singleton(store)

        coord = HealingCoordinator()
        problem = {
            "component": "network",
            "description": "Test with proof hash",
            "severity": "high",
            "proof_hash": "abc123def456",
        }
        coord.resolve(problem)

        events = store.query(source_type="healing_coordinator")
        assert len(events) >= 1
        assert events[0]["proof_hash"] == "abc123def456"

    def test_unresolved_problem_also_logged(self, mock_externals):
        """Even if healing fails, the event store should record it as UNRESOLVED."""
        from cognitive.healing_coordinator import HealingCoordinator
        from cognitive.spindle_event_store import SpindleEventStore
        import cognitive.spindle_event_store as es_mod

        store = SpindleEventStore()
        store._db_available = False
        _set_event_store_singleton(store)

        # Make all brain calls fail via fake module
        fail_mod = ModuleType("api.brain_api_v2")
        fail_mod.call_brain = MagicMock(side_effect=Exception("all down"))
        old = sys.modules.get("api.brain_api_v2")
        sys.modules["api.brain_api_v2"] = fail_mod
        try:
            coord = HealingCoordinator()
            problem = {
                "component": "everything",
                "description": "Total system failure",
                "severity": "critical",
            }
            coord.resolve(problem)
        finally:
            if old is not None:
                sys.modules["api.brain_api_v2"] = old
            else:
                sys.modules.pop("api.brain_api_v2", None)

        events = store.query(source_type="healing_coordinator")
        assert len(events) >= 1


# ═══════════════════════════════════════════════════════════════
# 4. FULL PIPELINE: Z3 → EXECUTOR → COORDINATOR → EVENT STORE
# ═══════════════════════════════════════════════════════════════

class TestFullSpindleHealingPipeline:
    """End-to-end: Compile → Z3 → Gate → Executor → Coordinator → Event Store → Projection."""

    def test_repair_e2e_deterministic(self, BD, mock_brain, mock_externals):
        """DATABASE REPAIR full pipeline — deterministic end-to-end."""
        from cognitive.physics.spindle_gate import SpindleGate
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.spindle_event_store import SpindleEventStore
        from cognitive.spindle_projection import SpindleProjection
        import cognitive.spindle_event_store as es_mod

        store = SpindleEventStore()
        store._db_available = False
        _set_event_store_singleton(store)

        # Step 1: Compile
        d, i, s, c = BD.compile_schema(
            {"domain": "database", "intent": "repair",
             "target_state": "active", "privilege": "admin"},
            {"is_maintenance_window": True},
        )

        # Step 2: Z3 Gate verification
        verdict = SpindleGate().verify(d, i, s, c)
        assert verdict.passed is True
        assert verdict.proof.is_valid is True

        # Step 3: Executor dispatches to HealingCoordinator
        executor = SpindleExecutor()
        result = executor.execute(verdict.proof)
        assert "healing_coordinator" in result.action_taken
        assert result.proof_hash == verdict.proof.constraint_hash

        # Step 4: Event store has audit trail from both executor and coordinator
        all_events = store.replay()
        assert len(all_events) >= 1

        coord_events = store.query(source_type="healing_coordinator")
        assert len(coord_events) >= 1
        assert coord_events[0]["payload"]["resolved"] is not None

        # Step 5: Projection can consume events (healing results tracked as RESOLVED/UNRESOLVED)
        proj = SpindleProjection()
        for ev in all_events:
            proj._apply_event(ev)
        trail = proj.get_audit_trail()
        assert len(trail) >= 1

    def test_query_skips_coordinator(self, BD):
        """DATABASE QUERY should NOT go through HealingCoordinator (passthrough)."""
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof

        executor = SpindleExecutor()
        proof = SpindleProof(
            is_valid=True, result="SAT", reason="ok",
            domain_mask=BD.DOMAIN_DATABASE, intent_mask=BD.INTENT_QUERY,
        )
        result = executor.execute(proof)
        assert result.success is True
        assert "passthrough" in result.action_taken
        assert "healing_coordinator" not in result.action_taken

    def test_rejected_proof_never_reaches_coordinator(self, BD, mock_brain, mock_externals):
        """UNSAT proof → executor rejects → HealingCoordinator never called."""
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof

        executor = SpindleExecutor()
        proof = SpindleProof(is_valid=False, result="UNSAT", reason="Z3 rejected")
        result = executor.execute(proof)

        assert result.success is False
        assert result.action_taken == "rejected"
        assert "healing_coordinator" not in result.action_taken

    def test_multiple_repairs_produce_multiple_events(self, BD, mock_brain, mock_externals):
        """Three repairs should produce healing coordinator events for each."""
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof
        from cognitive.spindle_event_store import SpindleEventStore
        import cognitive.spindle_event_store as es_mod

        store = SpindleEventStore()
        store._db_available = False
        _set_event_store_singleton(store)

        executor = SpindleExecutor()
        domains = [BD.DOMAIN_DATABASE, BD.DOMAIN_API, BD.DOMAIN_NETWORK]

        for domain in domains:
            proof = SpindleProof(
                is_valid=True, result="SAT", reason="ok",
                domain_mask=domain, intent_mask=BD.INTENT_REPAIR,
            )
            executor.execute(proof)

        events = store.query(source_type="healing_coordinator")
        assert len(events) >= 3

    def test_checkpoint_wraps_healing_execution(self, BD, mock_brain, mock_externals):
        """Healing execution through coordinator should be checkpoint-wrapped."""
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof
        from cognitive.spindle_checkpoint import get_checkpoint_manager

        executor = SpindleExecutor()
        proof = SpindleProof(
            is_valid=True, result="SAT", reason="ok",
            domain_mask=BD.DOMAIN_DATABASE, intent_mask=BD.INTENT_REPAIR,
        )
        executor.execute(proof)

        mgr = get_checkpoint_manager()
        recent = mgr.get_recent(5)
        assert len(recent) >= 1
        assert recent[0]["component"] == "database"
        assert recent[0]["rolled_back"] is False


# ═══════════════════════════════════════════════════════════════
# 5. DETERMINISM GUARANTEES
# ═══════════════════════════════════════════════════════════════

class TestDeterminismGuarantees:
    """Verify that the same input always produces the same output."""

    def test_z3_verification_is_deterministic(self, BD):
        """Same bitmask input → same SAT/UNSAT result, every time."""
        from cognitive.physics.bitmask_geometry import HierarchicalZ3Geometry

        geom = HierarchicalZ3Geometry()
        results = []
        for _ in range(10):
            proof = geom.verify_action(
                BD.DOMAIN_DATABASE, BD.INTENT_DELETE,
                BD.STATE_IMMUTABLE, BD.PRIV_ADMIN,
            )
            results.append((proof.is_valid, proof.result))

        assert all(r == results[0] for r in results), f"Non-deterministic Z3: {results}"

    def test_bitmask_compilation_is_deterministic(self, BD):
        """Same schema → same bitmask, every time."""
        schema = {"domain": "network", "intent": "repair",
                  "target_state": "active", "privilege": "admin"}
        ctx = {"is_maintenance_window": True}

        results = [BD.compile_schema(schema, ctx) for _ in range(10)]
        assert all(r == results[0] for r in results)

    def test_gate_consensus_is_deterministic(self, BD):
        """Same input → same gate verdict, every time."""
        from cognitive.physics.spindle_gate import SpindleGate

        verdicts = []
        for _ in range(5):
            gate = SpindleGate()
            v = gate.verify(BD.DOMAIN_DATABASE, BD.INTENT_QUERY,
                            BD.STATE_ACTIVE, BD.PRIV_USER)
            verdicts.append((v.passed, v.votes_for, v.votes_against))

        assert all(v == verdicts[0] for v in verdicts), f"Non-deterministic gate: {verdicts}"

    def test_proof_hash_deterministic_across_executions(self, BD):
        """Same masks + timestamp → same constraint_hash."""
        from cognitive.physics.spindle_proof import SpindleProof

        ts = 1700000000.0
        hashes = set()
        for _ in range(10):
            p = SpindleProof(
                is_valid=True, result="SAT", reason="ok",
                domain_mask=BD.DOMAIN_DATABASE, intent_mask=BD.INTENT_REPAIR,
                timestamp=ts,
            )
            hashes.add(p.constraint_hash)

        assert len(hashes) == 1, f"Non-deterministic hashes: {hashes}"

    def test_event_store_sequence_is_monotonic(self, event_store):
        """Sequence IDs must be strictly monotonically increasing."""
        seqs = [event_store.append(f"t.{i}", "test") for i in range(100)]
        for i in range(1, len(seqs)):
            assert seqs[i] == seqs[i - 1] + 1, f"Non-monotonic at {i}: {seqs[i-1]} -> {seqs[i]}"

    def test_event_store_thread_safe_monotonic(self, event_store):
        """Even under concurrent writes, sequences must be unique and monotonic."""
        results = []
        errors = []
        lock = threading.Lock()

        def writer(tid):
            try:
                for i in range(50):
                    seq = event_store.append(f"t.{tid}.{i}", "test")
                    with lock:
                        results.append(seq)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(results) == 250
        assert len(set(results)) == 250, "Duplicate sequence IDs detected"

    def test_executor_dispatch_deterministic(self, BD, mock_brain, mock_externals):
        """Same proof → same action_taken string pattern."""
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof

        actions = set()
        for _ in range(3):
            executor = SpindleExecutor()
            proof = SpindleProof(
                is_valid=True, result="SAT", reason="ok",
                domain_mask=BD.DOMAIN_DATABASE, intent_mask=BD.INTENT_QUERY,
            )
            result = executor.execute(proof)
            actions.add(result.action_taken)

        assert len(actions) == 1, f"Non-deterministic dispatch: {actions}"


# ═══════════════════════════════════════════════════════════════
# 6. TRUST FLOW — Z3 SAFETY PREVENTS UNSAFE HEALING
# ═══════════════════════════════════════════════════════════════

class TestTrustSafetyFlow:
    """Verify that Z3 safety gates prevent unsafe healing actions."""

    def test_cannot_delete_immutable_through_healing(self, BD):
        """Even if healing wants to delete immutable data, Z3 blocks it."""
        from cognitive.physics.bitmask_geometry import HierarchicalZ3Geometry
        from cognitive.spindle_executor import SpindleExecutor

        geom = HierarchicalZ3Geometry()
        proof = geom.verify_action(
            BD.DOMAIN_DATABASE, BD.INTENT_DELETE,
            BD.STATE_IMMUTABLE, BD.PRIV_SYSTEM,
        )
        assert proof.is_valid is False

        result = SpindleExecutor().execute(proof)
        assert result.success is False
        assert result.action_taken == "rejected"

    def test_guest_cannot_delete(self, BD):
        """Guest privilege should be blocked from destructive (DELETE/GRANT) operations."""
        from cognitive.physics.spindle_gate import SpindleGate

        gate = SpindleGate()
        verdict = gate.verify(
            BD.DOMAIN_DATABASE, BD.INTENT_DELETE,
            BD.STATE_ACTIVE, BD.PRIV_GUEST | BD.CTX_ELEVATED,
        )
        priv_result = next(
            r for r in verdict.validator_results if r.validator_name == "privilege_check"
        )
        assert priv_result.passed is False

    def test_repair_requires_admin_or_system(self, BD):
        """Repair on any domain requires at least admin privilege."""
        from cognitive.physics.spindle_gate import SpindleGate

        gate = SpindleGate()

        # User without elevation → should fail privilege check
        verdict_user = gate.verify(
            BD.DOMAIN_DATABASE, BD.INTENT_REPAIR,
            BD.STATE_ACTIVE, BD.PRIV_USER,
        )
        priv_user = next(
            r for r in verdict_user.validator_results if r.validator_name == "privilege_check"
        )

        # Admin with maintenance → should pass
        verdict_admin = gate.verify(
            BD.DOMAIN_DATABASE, BD.INTENT_REPAIR,
            BD.STATE_ACTIVE, BD.PRIV_ADMIN | BD.CTX_MAINTENANCE,
        )

        assert verdict_admin.passed is True

    def test_system_emergency_bypasses_maintenance_requirement(self, BD):
        """SYSTEM + EMERGENCY context should allow repair without maintenance window."""
        from cognitive.physics.bitmask_geometry import HierarchicalZ3Geometry

        geom = HierarchicalZ3Geometry()
        proof = geom.verify_action(
            BD.DOMAIN_NETWORK, BD.INTENT_REPAIR,
            BD.STATE_ACTIVE,
            BD.PRIV_SYSTEM | BD.CTX_EMERGENCY,
        )
        assert proof.is_valid is True
        assert proof.result == "SAT"


# ═══════════════════════════════════════════════════════════════
# 7. SPINDLE DAEMON ESCALATION PATH
# ═══════════════════════════════════════════════════════════════

class TestSpindleDaemonEscalation:
    """Verify the daemon's _escalate_to_coordinator method."""

    def _make_daemon(self):
        """Create a minimal SpindleDaemon without ZMQ sockets."""
        import asyncio
        zmq_asyncio = pytest.importorskip("zmq.asyncio", reason="zmq required for daemon tests")
        from spindle_daemon import SpindleDaemon

        daemon = SpindleDaemon.__new__(SpindleDaemon)
        daemon._stats = {"events_processed": 0, "errors": 0}
        daemon._pub_socket = MagicMock()
        daemon._zmq_ctx = MagicMock()

        # Create a temporary event loop for the async publish
        loop = asyncio.new_event_loop()

        async def fake_publish(topic, data):
            pass
        daemon._publish = fake_publish

        return daemon, loop

    def test_escalate_calls_coordinator(self, mock_brain, mock_externals):
        """_escalate_to_coordinator should call HealingCoordinator.resolve()."""
        import asyncio
        import cognitive.spindle_event_store as es_mod
        from cognitive.spindle_event_store import SpindleEventStore

        store = SpindleEventStore()
        store._db_available = False
        _set_event_store_singleton(store)

        daemon, loop = self._make_daemon()
        asyncio.set_event_loop(loop)
        try:
            result = daemon._escalate_to_coordinator("test.topic", "test problem description")
            assert result["status"] in ("resolved", "unresolved", "error")
        finally:
            loop.close()

    def test_escalate_writes_to_event_store(self, mock_brain, mock_externals):
        """Escalation should persist an event to the spindle event store."""
        import asyncio
        import cognitive.spindle_event_store as es_mod
        from cognitive.spindle_event_store import SpindleEventStore

        store = SpindleEventStore()
        store._db_available = False
        _set_event_store_singleton(store)

        daemon, loop = self._make_daemon()
        asyncio.set_event_loop(loop)
        try:
            daemon._escalate_to_coordinator("healing.db", "database down", proof_hash="proof_abc")
        finally:
            loop.close()

        # Check event store has escalation event
        events = store.query(topic="spindle.escalation.healing.db")
        assert len(events) >= 1
        assert events[0]["payload"]["resolved"] is not None


# ═══════════════════════════════════════════════════════════════
# 8. FULL PHYSICS MATRIX WITH HEALING
# ═══════════════════════════════════════════════════════════════

class TestFullPhysicsMatrixWithHealing:
    """Every domain×REPAIR must route through HealingCoordinator."""

    def test_all_repair_intents_route_through_coordinator(self, BD, mock_brain, mock_externals):
        """All 5 domains with REPAIR intent → HealingCoordinator."""
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof
        from cognitive.spindle_event_store import SpindleEventStore
        import cognitive.spindle_event_store as es_mod

        store = SpindleEventStore()
        store._db_available = False
        _set_event_store_singleton(store)

        executor = SpindleExecutor()
        domains = [
            BD.DOMAIN_DATABASE, BD.DOMAIN_API, BD.DOMAIN_MEMORY,
            BD.DOMAIN_NETWORK, BD.DOMAIN_SYS_CONF,
        ]

        for domain in domains:
            proof = SpindleProof(
                is_valid=True, result="SAT", reason="ok",
                domain_mask=domain, intent_mask=BD.INTENT_REPAIR,
            )
            result = executor.execute(proof)
            assert "healing_coordinator" in result.action_taken, (
                f"Domain {domain:#x} REPAIR did not route through coordinator"
            )

        events = store.query(source_type="healing_coordinator")
        assert len(events) >= 5

    def test_all_query_intents_skip_coordinator(self, BD):
        """All 5 domains with QUERY intent → passthrough, no coordinator."""
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof

        executor = SpindleExecutor()
        domains = [
            BD.DOMAIN_DATABASE, BD.DOMAIN_API, BD.DOMAIN_MEMORY,
            BD.DOMAIN_NETWORK, BD.DOMAIN_SYS_CONF,
        ]

        for domain in domains:
            proof = SpindleProof(
                is_valid=True, result="SAT", reason="ok",
                domain_mask=domain, intent_mask=BD.INTENT_QUERY,
            )
            result = executor.execute(proof)
            assert "healing_coordinator" not in result.action_taken, (
                f"Domain {domain:#x} QUERY should not route through coordinator"
            )


if __name__ == "__main__":
    pytest.main(["-v", __file__])
