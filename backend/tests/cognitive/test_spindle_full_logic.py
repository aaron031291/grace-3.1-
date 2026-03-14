"""
Spindle Full Logic Tests
========================
Real Z3 solving, real bitmask compilation, real gate consensus,
real executor dispatch, real event persistence, real checkpoints.

NO mocks for Spindle internals — exercises the actual pipeline.
"""
import pytest
import time
import threading

z3 = pytest.importorskip("z3", reason="z3-solver required for Spindle tests")


# ═══════════════════════════════════════════════════════════════
# FIXTURES
# ═══════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset all Spindle singletons between tests."""
    import cognitive.spindle_executor as ex_mod
    import cognitive.spindle_event_store as es_mod
    import cognitive.spindle_checkpoint as cp_mod
    import cognitive.spindle_projection as pr_mod
    import cognitive.physics.spindle_gate as gt_mod

    ex_mod._instance = None
    es_mod._store = None
    cp_mod._manager = None
    pr_mod._projection = None
    gt_mod._gate = None
    yield


@pytest.fixture
def BD():
    from cognitive.braille_compiler import BrailleDictionary
    return BrailleDictionary


@pytest.fixture
def z3_geometry():
    from cognitive.physics.bitmask_geometry import HierarchicalZ3Geometry
    return HierarchicalZ3Geometry()


@pytest.fixture
def event_store():
    from cognitive.spindle_event_store import SpindleEventStore
    store = SpindleEventStore()
    store._db_available = False
    return store


@pytest.fixture
def checkpoint_mgr():
    from cognitive.spindle_checkpoint import SpindleCheckpointManager
    return SpindleCheckpointManager()


@pytest.fixture
def projection():
    from cognitive.spindle_projection import SpindleProjection
    return SpindleProjection()


# ═══════════════════════════════════════════════════════════════
# 1. SPINDLE PROOF CERTIFICATE
# ═══════════════════════════════════════════════════════════════

class TestSpindleProof:
    def test_creates_hash(self):
        from cognitive.physics.spindle_proof import SpindleProof
        p = SpindleProof(is_valid=True, result="SAT", reason="t", domain_mask=1, intent_mask=256)
        assert len(p.constraint_hash) == 16

    def test_hash_deterministic(self):
        from cognitive.physics.spindle_proof import SpindleProof
        ts = 1234567890.0
        p1 = SpindleProof(is_valid=True, result="SAT", reason="x", domain_mask=1, intent_mask=2, timestamp=ts)
        p2 = SpindleProof(is_valid=True, result="SAT", reason="x", domain_mask=1, intent_mask=2, timestamp=ts)
        assert p1.constraint_hash == p2.constraint_hash

    def test_hash_changes_with_masks(self):
        from cognitive.physics.spindle_proof import SpindleProof
        ts = 1234567890.0
        p1 = SpindleProof(is_valid=True, result="SAT", reason="x", domain_mask=1, intent_mask=2, timestamp=ts)
        p2 = SpindleProof(is_valid=True, result="SAT", reason="x", domain_mask=1, intent_mask=3, timestamp=ts)
        assert p1.constraint_hash != p2.constraint_hash

    def test_masks_property(self):
        from cognitive.physics.spindle_proof import SpindleProof
        p = SpindleProof(is_valid=True, result="SAT", reason="x",
                         domain_mask=1, intent_mask=2, state_mask=3, context_mask=4)
        assert p.masks == (1, 2, 3, 4)

    def test_to_dict(self):
        from cognitive.physics.spindle_proof import SpindleProof
        p = SpindleProof(is_valid=True, result="SAT", reason="test reason")
        d = p.to_dict()
        assert d["is_valid"] is True
        assert d["result"] == "SAT"
        assert "masks" in d
        assert "constraint_hash" in d


# ═══════════════════════════════════════════════════════════════
# 2. Z3 BITMASK GEOMETRY — REAL SMT SOLVING
# ═══════════════════════════════════════════════════════════════

class TestZ3BitmaskGeometry:
    def test_valid_query_on_active_database(self, z3_geometry, BD):
        proof = z3_geometry.verify_action(BD.DOMAIN_DATABASE, BD.INTENT_QUERY,
                                          BD.STATE_ACTIVE, BD.PRIV_USER)
        assert proof.is_valid is True
        assert proof.result == "SAT"

    def test_cannot_delete_immutable(self, z3_geometry, BD):
        proof = z3_geometry.verify_action(BD.DOMAIN_DATABASE, BD.INTENT_DELETE,
                                          BD.STATE_IMMUTABLE, BD.PRIV_ADMIN)
        assert proof.is_valid is False
        assert proof.result == "UNSAT"

    def test_cannot_start_failed(self, z3_geometry, BD):
        proof = z3_geometry.verify_action(BD.DOMAIN_API, BD.INTENT_START,
                                          BD.STATE_FAILED, BD.PRIV_SYSTEM)
        assert proof.is_valid is False

    def test_cannot_stop_stopped(self, z3_geometry, BD):
        proof = z3_geometry.verify_action(BD.DOMAIN_NETWORK, BD.INTENT_STOP,
                                          BD.STATE_STOPPED,
                                          BD.PRIV_ADMIN | BD.CTX_MAINTENANCE)
        assert proof.is_valid is False

    def test_network_mutation_requires_maintenance(self, z3_geometry, BD):
        proof = z3_geometry.verify_action(BD.DOMAIN_NETWORK, BD.INTENT_REPAIR,
                                          BD.STATE_ACTIVE, BD.PRIV_ADMIN)
        assert proof.is_valid is False

    def test_network_mutation_with_maintenance_passes(self, z3_geometry, BD):
        proof = z3_geometry.verify_action(BD.DOMAIN_NETWORK, BD.INTENT_REPAIR,
                                          BD.STATE_ACTIVE,
                                          BD.PRIV_ADMIN | BD.CTX_MAINTENANCE)
        assert proof.is_valid is True

    def test_network_mutation_with_emergency_passes(self, z3_geometry, BD):
        proof = z3_geometry.verify_action(BD.DOMAIN_NETWORK, BD.INTENT_REPAIR,
                                          BD.STATE_ACTIVE,
                                          BD.PRIV_SYSTEM | BD.CTX_EMERGENCY)
        assert proof.is_valid is True

    def test_user_db_mutation_needs_elevation(self, z3_geometry, BD):
        proof = z3_geometry.verify_action(BD.DOMAIN_DATABASE, BD.INTENT_DELETE,
                                          BD.STATE_ACTIVE, BD.PRIV_USER)
        assert proof.is_valid is False

    def test_user_db_mutation_with_elevation_passes(self, z3_geometry, BD):
        proof = z3_geometry.verify_action(BD.DOMAIN_DATABASE, BD.INTENT_DELETE,
                                          BD.STATE_ACTIVE,
                                          BD.PRIV_USER | BD.CTX_ELEVATED)
        assert proof.is_valid is True

    def test_proof_contains_masks(self, z3_geometry, BD):
        d, i, s, c = BD.DOMAIN_DATABASE, BD.INTENT_QUERY, BD.STATE_ACTIVE, BD.PRIV_USER
        proof = z3_geometry.verify_action(d, i, s, c)
        assert proof.domain_mask == d
        assert proof.intent_mask == i
        assert proof.state_mask == s
        assert proof.context_mask == c

    def test_sequential_verifications_independent(self, z3_geometry, BD):
        p1 = z3_geometry.verify_action(BD.DOMAIN_DATABASE, BD.INTENT_QUERY,
                                        BD.STATE_ACTIVE, BD.PRIV_USER)
        p2 = z3_geometry.verify_action(BD.DOMAIN_DATABASE, BD.INTENT_DELETE,
                                        BD.STATE_IMMUTABLE, BD.PRIV_ADMIN)
        p3 = z3_geometry.verify_action(BD.DOMAIN_DATABASE, BD.INTENT_QUERY,
                                        BD.STATE_ACTIVE, BD.PRIV_USER)
        assert p1.is_valid is True
        assert p2.is_valid is False
        assert p3.is_valid is True


# ═══════════════════════════════════════════════════════════════
# 3. BRAILLE DICTIONARY — COMPILATION
# ═══════════════════════════════════════════════════════════════

class TestBrailleDictionary:
    def test_compile_valid_schema(self, BD):
        schema = {"domain": "database", "intent": "query",
                  "target_state": "active", "privilege": "user"}
        d, i, s, c = BD.compile_schema(schema, {})
        assert d == BD.DOMAIN_DATABASE
        assert i == BD.INTENT_QUERY
        assert s == BD.STATE_ACTIVE
        assert c & BD.PRIV_USER

    def test_compile_with_context_flags(self, BD):
        schema = {"domain": "network", "intent": "repair",
                  "target_state": "active", "privilege": "admin"}
        ctx = {"is_maintenance_window": True, "is_emergency": False,
               "has_elevation_token": True}
        _, _, _, c = BD.compile_schema(schema, ctx)
        assert c & BD.CTX_MAINTENANCE
        assert c & BD.CTX_ELEVATED
        assert not (c & BD.CTX_EMERGENCY)

    def test_rejects_unknown_domain(self, BD):
        schema = {"domain": "blockchain", "intent": "query",
                  "target_state": "active", "privilege": "user"}
        with pytest.raises(ValueError, match="hallucinated"):
            BD.compile_schema(schema, {})

    def test_rejects_unknown_intent(self, BD):
        schema = {"domain": "database", "intent": "teleport",
                  "target_state": "active", "privilege": "user"}
        with pytest.raises(ValueError, match="hallucinated"):
            BD.compile_schema(schema, {})

    def test_all_domains_compile(self, BD):
        for domain in ["database", "api", "memory", "network", "sys_conf"]:
            schema = {"domain": domain, "intent": "query",
                      "target_state": "active", "privilege": "user"}
            result = BD.compile_schema(schema, {})
            assert len(result) == 4

    def test_all_intents_compile(self, BD):
        for intent in ["start", "stop", "delete", "query", "grant", "repair"]:
            schema = {"domain": "database", "intent": intent,
                      "target_state": "active", "privilege": "admin"}
            result = BD.compile_schema(schema, {})
            assert result[1] > 0

    def test_all_states_compile(self, BD):
        for state in ["failed", "immutable", "active", "unknown", "stopped"]:
            schema = {"domain": "database", "intent": "query",
                      "target_state": state, "privilege": "user"}
            result = BD.compile_schema(schema, {})
            assert result[2] > 0

    def test_all_privileges_compile(self, BD):
        for priv in ["admin", "user", "system", "guest"]:
            schema = {"domain": "database", "intent": "query",
                      "target_state": "active", "privilege": priv}
            result = BD.compile_schema(schema, {})
            assert result[3] > 0


# ═══════════════════════════════════════════════════════════════
# 4. SPINDLE GATE — PARALLEL CONSENSUS
# ═══════════════════════════════════════════════════════════════

class TestSpindleGate:
    def test_passes_valid_action(self, BD):
        from cognitive.physics.spindle_gate import SpindleGate
        gate = SpindleGate()
        verdict = gate.verify(BD.DOMAIN_DATABASE, BD.INTENT_QUERY,
                              BD.STATE_ACTIVE, BD.PRIV_USER)
        assert verdict.passed is True
        assert verdict.votes_for >= 2
        assert verdict.proof is not None
        assert verdict.proof.is_valid is True

    def test_rejects_physics_violation(self, BD):
        """Z3 should vote UNSAT even if other validators pass."""
        from cognitive.physics.spindle_gate import SpindleGate
        gate = SpindleGate()
        verdict = gate.verify(BD.DOMAIN_DATABASE, BD.INTENT_DELETE,
                              BD.STATE_IMMUTABLE, BD.PRIV_ADMIN)
        z3r = next(r for r in verdict.validator_results if r.validator_name == "z3_geometry")
        assert z3r.passed is False
        assert verdict.votes_against >= 1

    def test_rejects_guest_delete(self, BD):
        from cognitive.physics.spindle_gate import SpindleGate
        gate = SpindleGate()
        verdict = gate.verify(BD.DOMAIN_DATABASE, BD.INTENT_DELETE,
                              BD.STATE_ACTIVE,
                              BD.PRIV_GUEST | BD.CTX_ELEVATED)
        pr = next(r for r in verdict.validator_results if r.validator_name == "privilege_check")
        assert pr.passed is False

    def test_parallel_execution(self, BD):
        from cognitive.physics.spindle_gate import SpindleGate
        gate = SpindleGate()

        def slow_validator(d, i, s, c, ctx):
            time.sleep(0.3)
            return True, "slow ok", None

        gate.add_validator("slow_1", slow_validator)
        gate.add_validator("slow_2", slow_validator)

        start = time.perf_counter()
        verdict = gate.verify(BD.DOMAIN_DATABASE, BD.INTENT_QUERY,
                              BD.STATE_ACTIVE, BD.PRIV_USER)
        wall = time.perf_counter() - start

        assert wall < 0.55, f"Not parallel: {wall:.2f}s"
        assert verdict.passed is True

    def test_custom_validator_consensus(self, BD):
        from cognitive.physics.spindle_gate import SpindleGate
        gate = SpindleGate()
        gate.add_validator("custom_fail", lambda d, i, s, c, ctx: (False, "nope", None))
        verdict = gate.verify(BD.DOMAIN_DATABASE, BD.INTENT_QUERY,
                              BD.STATE_ACTIVE, BD.PRIV_USER)
        assert verdict.passed is True
        assert verdict.votes_against >= 1

    def test_verdict_has_wall_time(self, BD):
        from cognitive.physics.spindle_gate import SpindleGate
        verdict = SpindleGate().verify(BD.DOMAIN_DATABASE, BD.INTENT_QUERY,
                                       BD.STATE_ACTIVE, BD.PRIV_USER)
        assert verdict.wall_time_ms > 0

    def test_confidence_calculation(self, BD):
        from cognitive.physics.spindle_gate import SpindleGate
        verdict = SpindleGate().verify(BD.DOMAIN_DATABASE, BD.INTENT_QUERY,
                                       BD.STATE_ACTIVE, BD.PRIV_USER)
        assert verdict.confidence == verdict.votes_for / verdict.total_validators


# ═══════════════════════════════════════════════════════════════
# 5. SPINDLE EXECUTOR — DISPATCH TABLE
# ═══════════════════════════════════════════════════════════════

class TestSpindleExecutor:
    def test_rejects_invalid_proof(self):
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof
        executor = SpindleExecutor()
        proof = SpindleProof(is_valid=False, result="UNSAT", reason="bad")
        result = executor.execute(proof)
        assert result.success is False
        assert result.action_taken == "rejected"

    def test_dispatches_database_query(self, BD):
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof
        executor = SpindleExecutor()
        proof = SpindleProof(is_valid=True, result="SAT", reason="ok",
                             domain_mask=BD.DOMAIN_DATABASE, intent_mask=BD.INTENT_QUERY)
        result = executor.execute(proof)
        assert result.success is True
        assert "passthrough" in result.action_taken
        assert result.proof_hash == proof.constraint_hash

    def test_checkpoint_on_mutation(self, BD):
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof
        from cognitive.spindle_checkpoint import get_checkpoint_manager
        executor = SpindleExecutor()
        proof = SpindleProof(is_valid=True, result="SAT", reason="ok",
                             domain_mask=BD.DOMAIN_MEMORY, intent_mask=BD.INTENT_REPAIR)
        executor.execute(proof)
        mgr = get_checkpoint_manager()
        recent = mgr.get_recent(1)
        assert len(recent) >= 1
        assert recent[0]["component"] == "memory"

    def test_no_checkpoint_on_query(self, BD):
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof
        from cognitive.spindle_checkpoint import get_checkpoint_manager
        executor = SpindleExecutor()
        proof = SpindleProof(is_valid=True, result="SAT", reason="ok",
                             domain_mask=BD.DOMAIN_DATABASE, intent_mask=BD.INTENT_QUERY)
        executor.execute(proof)
        mgr = get_checkpoint_manager()
        assert len(mgr.get_recent()) == 0

    def test_no_handler_returns_error(self):
        from cognitive.spindle_executor import SpindleExecutor, ProcedureRegistry
        from cognitive.physics.spindle_proof import SpindleProof
        executor = SpindleExecutor()
        executor.registry = ProcedureRegistry()
        proof = SpindleProof(is_valid=True, result="SAT", reason="ok",
                             domain_mask=0xFF, intent_mask=0xFF)
        result = executor.execute(proof)
        assert result.success is False
        assert "no_handler" in result.action_taken

    def test_custom_handler(self, BD):
        from cognitive.spindle_executor import SpindleExecutor, ExecutionResult
        from cognitive.physics.spindle_proof import SpindleProof
        executor = SpindleExecutor()
        called = []

        def custom(proof):
            called.append(True)
            return ExecutionResult(success=True, action_taken="custom", proof_hash=proof.constraint_hash)

        executor.register(BD.DOMAIN_DATABASE, BD.INTENT_QUERY, custom)
        proof = SpindleProof(is_valid=True, result="SAT", reason="ok",
                             domain_mask=BD.DOMAIN_DATABASE, intent_mask=BD.INTENT_QUERY)
        result = executor.execute(proof)
        assert result.action_taken == "custom"
        assert len(called) == 1

    def test_duration_tracked(self, BD):
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof
        executor = SpindleExecutor()
        proof = SpindleProof(is_valid=True, result="SAT", reason="ok",
                             domain_mask=BD.DOMAIN_DATABASE, intent_mask=BD.INTENT_QUERY)
        result = executor.execute(proof)
        assert result.duration_ms >= 0

    def test_stats_tracking(self, BD):
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof
        executor = SpindleExecutor()
        proof = SpindleProof(is_valid=True, result="SAT", reason="ok",
                             domain_mask=BD.DOMAIN_DATABASE, intent_mask=BD.INTENT_QUERY)
        executor.execute(proof)
        executor.execute(proof)
        stats = executor.stats
        assert stats["total_executions"] == 2
        assert stats["successful"] == 2

    def test_submit_background(self, BD):
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof
        executor = SpindleExecutor()
        proof = SpindleProof(is_valid=True, result="SAT", reason="ok",
                             domain_mask=BD.DOMAIN_DATABASE, intent_mask=BD.INTENT_QUERY)
        task_id = executor.submit(proof)
        assert task_id.startswith("EXEC-")
        # Poll for completion (up to 10s — thread pool startup can be slow)
        result = None
        for _ in range(100):
            result = executor.get_result(task_id)
            if result is not None:
                break
            time.sleep(0.1)
        assert result is not None, f"Background task {task_id} did not complete in 10s"
        assert result.success is True

    def test_all_30_handlers_registered(self, BD):
        from cognitive.spindle_executor import SpindleExecutor
        executor = SpindleExecutor()
        keys = executor.registry.all_keys()
        assert len(keys) == 30  # 5 domains × 6 intents


# ═══════════════════════════════════════════════════════════════
# 6. EVENT STORE — APPEND-ONLY LOG
# ═══════════════════════════════════════════════════════════════

class TestSpindleEventStore:
    def test_append_returns_sequence(self, event_store):
        assert event_store.append("t1", "system", {"k": "v"}) == 1
        assert event_store.append("t2", "healing") == 2

    def test_monotonic_sequence(self, event_store):
        seqs = [event_store.append(f"t.{i}", "system") for i in range(10)]
        assert seqs == list(range(1, 11))

    def test_query_by_topic(self, event_store):
        event_store.append("spindle.exec", "healing", {"a": 1})
        event_store.append("spindle.cp", "system", {"b": 2})
        event_store.append("spindle.exec", "healing", {"c": 3})
        assert len(event_store.query(topic="spindle.exec")) == 2

    def test_query_by_source_type(self, event_store):
        event_store.append("t1", "healing")
        event_store.append("t2", "system")
        event_store.append("t3", "healing")
        assert len(event_store.query(source_type="healing")) == 2

    def test_replay_from_sequence(self, event_store):
        for i in range(5):
            event_store.append(f"t.{i}", "system")
        assert len(event_store.replay(after_sequence=3)) == 2

    def test_replay_from_zero(self, event_store):
        for i in range(3):
            event_store.append(f"t.{i}", "system")
        assert len(event_store.replay(after_sequence=0)) == 3

    def test_append_async_returns_seq(self, event_store):
        seq = event_store.append_async("async.test", "system", {"async": True})
        assert seq > 0

    def test_proof_hash_stored(self, event_store):
        event_store.append("t", "healing", proof_hash="abc123", result="EXECUTED")
        results = event_store.query(source_type="healing")
        assert results[0]["proof_hash"] == "abc123"

    def test_thread_safety(self, event_store):
        errors = []

        def writer(tid):
            try:
                for i in range(50):
                    event_store.append(f"thread.{tid}.{i}", "system")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        assert event_store.get_sequence() == 250


# ═══════════════════════════════════════════════════════════════
# 7. CHECKPOINT — SNAPSHOT & ROLLBACK
# ═══════════════════════════════════════════════════════════════

class TestSpindleCheckpoint:
    def test_successful_checkpoint(self, checkpoint_mgr):
        with checkpoint_mgr.checkpoint("database", "proof123") as cp:
            cp.state_snapshot["test"] = "data"
        recent = checkpoint_mgr.get_recent(1)
        assert recent[0]["rolled_back"] is False
        assert recent[0]["component"] == "database"

    def test_rollback_on_exception(self, checkpoint_mgr):
        with pytest.raises(RuntimeError):
            with checkpoint_mgr.checkpoint("network", "proof456"):
                raise RuntimeError("boom")
        assert checkpoint_mgr.get_recent(1)[0]["rolled_back"] is True

    def test_custom_rollback_handler(self, checkpoint_mgr):
        calls = []
        checkpoint_mgr.register_rollback("db", lambda cp: calls.append(cp.component))
        with pytest.raises(ValueError):
            with checkpoint_mgr.checkpoint("db", "p"):
                raise ValueError("fail")
        assert calls == ["db"]

    def test_file_backup_restore(self, checkpoint_mgr, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("original", encoding="utf-8")
        with pytest.raises(RuntimeError):
            with checkpoint_mgr.checkpoint("db") as cp:
                cp.file_backups[str(f)] = "original"
                f.write_text("modified", encoding="utf-8")
                raise RuntimeError("fail")
        assert f.read_text(encoding="utf-8") == "original"

    def test_stats_tracking(self, checkpoint_mgr):
        with checkpoint_mgr.checkpoint("a"):
            pass
        with pytest.raises(RuntimeError):
            with checkpoint_mgr.checkpoint("b"):
                raise RuntimeError("fail")
        assert checkpoint_mgr.stats["created"] == 2
        assert checkpoint_mgr.stats["committed"] == 1
        assert checkpoint_mgr.stats["rolled_back"] == 1


# ═══════════════════════════════════════════════════════════════
# 8. CQRS PROJECTION
# ═══════════════════════════════════════════════════════════════

class TestSpindleProjection:
    def test_apply_executed(self, projection):
        projection._apply_event({
            "topic": "spindle.exec", "payload": {"component": "database", "action_taken": "repair"},
            "result": "EXECUTED", "proof_hash": "abc", "timestamp": time.time(), "sequence_id": 1,
        })
        s = projection.get_component_status("database")
        assert s["total_executions"] == 1
        assert s["success_rate"] == 1.0

    def test_apply_failed(self, projection):
        projection._apply_event({
            "topic": "spindle.exec", "payload": {"component": "net"},
            "result": "FAILED", "timestamp": time.time(), "sequence_id": 1,
        })
        assert projection.get_component_status("net")["success_rate"] == 0.0

    def test_verification_stats(self, projection):
        for r in ["SAT", "SAT", "UNSAT", "EXECUTED"]:
            projection._apply_event({"topic": "t", "payload": {},
                                     "result": r, "timestamp": time.time(), "sequence_id": 0})
        stats = projection.get_verification_stats()
        assert stats["SAT"] == 2
        assert stats["UNSAT"] == 1
        assert stats["total"] == 4
        assert stats["sat_ratio"] == 0.5

    def test_audit_trail(self, projection):
        for i in range(5):
            projection._apply_event({
                "topic": f"t.{i}", "payload": {"action": f"a{i}", "component": "db"},
                "result": "EXECUTED", "timestamp": time.time(), "sequence_id": i + 1,
            })
        trail = projection.get_audit_trail(limit=3)
        assert len(trail) == 3
        assert trail[0]["topic"] == "t.4"

    def test_filter_by_component(self, projection):
        projection._apply_event({"topic": "t1", "payload": {"component": "db"},
                                 "result": "EXECUTED", "timestamp": time.time(), "sequence_id": 1})
        projection._apply_event({"topic": "t2", "payload": {"component": "net"},
                                 "result": "EXECUTED", "timestamp": time.time(), "sequence_id": 2})
        assert len(projection.get_audit_trail(component="db")) == 1

    def test_dashboard(self, projection):
        d = projection.get_dashboard()
        for key in ("components", "verification_stats", "recent_audit", "last_sequence"):
            assert key in d

    def test_rollback_tracking(self, projection):
        projection._apply_event({
            "topic": "spindle.cp", "payload": {"component": "database"},
            "result": "ROLLED_BACK", "timestamp": time.time(), "sequence_id": 1,
        })
        assert projection.get_component_status("database")["rollbacks"] == 1


# ═══════════════════════════════════════════════════════════════
# 9. FULL PIPELINE — END-TO-END
# ═══════════════════════════════════════════════════════════════

class TestFullPipeline:
    def test_valid_action_e2e(self, BD):
        """Compile → Gate → Execute → Store → Project."""
        from cognitive.physics.spindle_gate import SpindleGate
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.spindle_event_store import SpindleEventStore
        from cognitive.spindle_projection import SpindleProjection

        d, i, s, c = BD.compile_schema(
            {"domain": "database", "intent": "query",
             "target_state": "active", "privilege": "user"}, {})

        verdict = SpindleGate().verify(d, i, s, c)
        assert verdict.passed is True

        result = SpindleExecutor().execute(verdict.proof)
        assert result.success is True

        store = SpindleEventStore()
        store._db_available = False
        store.append("spindle.exec", "test",
                     {"action": result.action_taken, "success": result.success},
                     proof_hash=verdict.proof.constraint_hash, result="EXECUTED")

        proj = SpindleProjection()
        for ev in store.replay():
            proj._apply_event(ev)
        assert proj.get_verification_stats()["EXECUTED"] == 1

    def test_rejected_action_e2e(self, BD):
        """DELETE IMMUTABLE → Z3 rejects → proof is invalid → executor refuses."""
        from cognitive.physics.bitmask_geometry import HierarchicalZ3Geometry
        from cognitive.spindle_executor import SpindleExecutor

        d, i, s, c = BD.compile_schema(
            {"domain": "database", "intent": "delete",
             "target_state": "immutable", "privilege": "admin"}, {})

        geom = HierarchicalZ3Geometry()
        proof = geom.verify_action(d, i, s, c)
        assert proof.is_valid is False
        assert proof.result == "UNSAT"

        result = SpindleExecutor().execute(proof)
        assert result.success is False
        assert result.action_taken == "rejected"

    def test_checkpoint_in_pipeline(self, BD):
        from cognitive.spindle_executor import SpindleExecutor
        from cognitive.physics.spindle_proof import SpindleProof
        from cognitive.spindle_checkpoint import get_checkpoint_manager

        executor = SpindleExecutor()
        proof = SpindleProof(is_valid=True, result="SAT", reason="ok",
                             domain_mask=BD.DOMAIN_MEMORY, intent_mask=BD.INTENT_REPAIR)
        executor.execute(proof)
        assert any(cp["component"] == "memory" for cp in get_checkpoint_manager().get_recent())

    def test_concurrent_pipelines(self, BD):
        """Multiple pipelines run sequentially then verify executor handles them all.
        Note: Z3 solver is not thread-safe (known upstream issue), so verification
        must be serialized. Execution dispatch IS parallelizable."""
        from cognitive.physics.bitmask_geometry import HierarchicalZ3Geometry
        from cognitive.spindle_executor import SpindleExecutor

        executor = SpindleExecutor()
        geom = HierarchicalZ3Geometry()

        # Verify all three sequentially (Z3 limitation)
        proofs = []
        for domain in [BD.DOMAIN_DATABASE, BD.DOMAIN_API, BD.DOMAIN_MEMORY]:
            proof = geom.verify_action(domain, BD.INTENT_QUERY, BD.STATE_ACTIVE, BD.PRIV_USER)
            assert proof.is_valid
            proofs.append(proof)

        # Execute all three in parallel
        results = []
        errors = []

        def execute_proof(p):
            try:
                results.append(executor.execute(p))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=execute_proof, args=(p,)) for p in proofs]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert not errors
        assert len(results) == 3
        assert all(r.success for r in results)

    def test_event_store_feeds_projection(self, BD):
        """Events written to store should be replayable into projection."""
        from cognitive.spindle_event_store import SpindleEventStore
        from cognitive.spindle_projection import SpindleProjection

        store = SpindleEventStore()
        store._db_available = False

        store.append("spindle.exec", "healing", {"component": "db"}, result="EXECUTED")
        store.append("spindle.exec", "healing", {"component": "db"}, result="FAILED")
        store.append("spindle.exec", "healing", {"component": "net"}, result="EXECUTED")

        proj = SpindleProjection()
        for ev in store.replay():
            proj._apply_event(ev)

        assert proj.get_component_status("db")["total_executions"] == 2
        assert proj.get_component_status("db")["success_rate"] == 0.5
        assert proj.get_component_status("net")["success_rate"] == 1.0

    def test_full_physics_matrix(self, BD):
        """Test every domain×intent against Z3 for consistency."""
        from cognitive.physics.bitmask_geometry import HierarchicalZ3Geometry
        geom = HierarchicalZ3Geometry()

        domains = [BD.DOMAIN_DATABASE, BD.DOMAIN_API, BD.DOMAIN_MEMORY,
                    BD.DOMAIN_NETWORK, BD.DOMAIN_SYS_CONF]
        intents = [BD.INTENT_START, BD.INTENT_STOP, BD.INTENT_DELETE,
                    BD.INTENT_QUERY, BD.INTENT_GRANT, BD.INTENT_REPAIR]

        for d in domains:
            for i in intents:
                proof = geom.verify_action(d, i, BD.STATE_ACTIVE,
                                            BD.PRIV_ADMIN | BD.CTX_MAINTENANCE | BD.CTX_ELEVATED)
                assert proof.result in ("SAT", "UNSAT", "UNKNOWN")
                assert proof.constraint_hash
                assert proof.domain_mask == d
                assert proof.intent_mask == i


if __name__ == "__main__":
    pytest.main(["-v", __file__])
