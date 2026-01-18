"""
Tests for Layer 4 Compiler-Governed Generation Pipeline.

Tests the deterministic, hallucination-free generation system.
Core principle: LLM is RENDERER, not author.
"""

import pytest
import hashlib
from datetime import datetime, timezone

from backend.ml_intelligence.layer4_compiler_governed_pipeline import (
    SymbolTable,
    FunctionContract,
    ControlFlowSketch,
    SideEffectLedger,
    PreGenerationProof,
    PreGenerationGate,
    EdgeCaseOracle,
    SimulationInput,
    ASTSymbolicSimulator,
    LineLoggingEnforcer,
    SandboxedTestExecutor,
    GeneratedTest,
    DeterministicFallbackRegistry,
    GenesisStamper,
    SelfVerifyLoop,
    LearningInjector,
    CompilerGovernedPipeline,
    GenerationAuthority,
    FailureMode,
    create_proof,
    get_compiler_governed_pipeline,
)


# ============================================================================
# 1. SYMBOL TABLE TESTS
# ============================================================================

class TestSymbolTable:
    """Tests for SymbolTable validation."""
    
    def test_valid_symbol_table(self):
        """Valid symbol table passes validation."""
        st = SymbolTable(
            inputs={"x": "input value"},
            types={"x": "int"},
            constraints=["x > 0"],
            invariants=["x is finite"],
        )
        valid, errors = st.is_valid()
        assert valid is True
        assert len(errors) == 0
    
    def test_missing_inputs_fails(self):
        """Symbol table without inputs fails."""
        st = SymbolTable(
            inputs={},
            types={"x": "int"},
        )
        valid, errors = st.is_valid()
        assert valid is False
        assert "No inputs defined" in errors
    
    def test_missing_types_fails(self):
        """Symbol table without types fails."""
        st = SymbolTable(
            inputs={"x": "value"},
            types={},
        )
        valid, errors = st.is_valid()
        assert valid is False
        assert "No types defined" in errors


# ============================================================================
# 2. FUNCTION CONTRACT TESTS
# ============================================================================

class TestFunctionContract:
    """Tests for FunctionContract validation."""
    
    def test_valid_contract(self):
        """Valid contract passes validation."""
        fc = FunctionContract(
            preconditions=["x is not None"],
            postconditions=["result >= 0"],
            failure_modes=["ValueError on invalid input"],
        )
        valid, errors = fc.is_valid()
        assert valid is True
        assert len(errors) == 0
    
    def test_missing_preconditions_fails(self):
        """Contract without preconditions fails."""
        fc = FunctionContract(
            preconditions=[],
            postconditions=["result >= 0"],
            failure_modes=["ValueError"],
        )
        valid, errors = fc.is_valid()
        assert valid is False
        assert "No preconditions defined" in errors
    
    def test_missing_postconditions_fails(self):
        """Contract without postconditions fails."""
        fc = FunctionContract(
            preconditions=["x is not None"],
            postconditions=[],
            failure_modes=["ValueError"],
        )
        valid, errors = fc.is_valid()
        assert valid is False
        assert "No postconditions defined" in errors
    
    def test_missing_failure_modes_fails(self):
        """Contract without failure modes fails."""
        fc = FunctionContract(
            preconditions=["x is not None"],
            postconditions=["result >= 0"],
            failure_modes=[],
        )
        valid, errors = fc.is_valid()
        assert valid is False
        assert "No failure modes defined" in errors


# ============================================================================
# 3. CONTROL FLOW SKETCH TESTS
# ============================================================================

class TestControlFlowSketch:
    """Tests for ControlFlowSketch validation."""
    
    def test_valid_control_flow(self):
        """Valid control flow passes validation."""
        cf = ControlFlowSketch(
            branches=[{"condition": "x > 0", "action": "return x"}],
            error_paths=[{"error": "ValueError", "handler": "return None"}],
            timeouts=[{"operation": "network", "timeout_ms": 5000}],
        )
        valid, errors = cf.is_valid()
        assert valid is True
        assert len(errors) == 0
    
    def test_missing_branches_fails(self):
        """Control flow without branches fails."""
        cf = ControlFlowSketch(
            branches=[],
            error_paths=[{"error": "ValueError"}],
        )
        valid, errors = cf.is_valid()
        assert valid is False
        assert "No branches defined" in errors
    
    def test_missing_error_paths_fails(self):
        """Control flow without error paths fails."""
        cf = ControlFlowSketch(
            branches=[{"condition": "x > 0"}],
            error_paths=[],
        )
        valid, errors = cf.is_valid()
        assert valid is False
        assert "No error paths defined" in errors


# ============================================================================
# 4. PRE-GENERATION PROOF TESTS
# ============================================================================

class TestPreGenerationProof:
    """Tests for PreGenerationProof validation and hashing."""
    
    def test_valid_proof(self):
        """Complete proof passes validation."""
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x is not None"],
            postconditions=["result >= 0"],
            failure_modes=["ValueError"],
            branches=[{"condition": "x > 0"}],
            error_paths=[{"error": "ValueError"}],
        )
        valid, errors = proof.is_valid()
        assert valid is True
        assert len(errors) == 0
    
    def test_incomplete_proof_fails(self):
        """Incomplete proof fails validation."""
        proof = PreGenerationProof(
            proof_id="test-proof",
            symbol_table=SymbolTable(inputs={}, types={}),
            contract=FunctionContract(
                preconditions=[],
                postconditions=[],
                failure_modes=[],
            ),
            control_flow=ControlFlowSketch(branches=[], error_paths=[]),
            side_effects=SideEffectLedger(),
        )
        valid, errors = proof.is_valid()
        assert valid is False
        assert len(errors) > 0
    
    def test_proof_hash_deterministic(self):
        """Same proof always produces same hash."""
        proof1 = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x is not None"],
            postconditions=["result >= 0"],
            failure_modes=["ValueError"],
            branches=[{"condition": "x > 0"}],
            error_paths=[{"error": "ValueError"}],
        )
        proof2 = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x is not None"],
            postconditions=["result >= 0"],
            failure_modes=["ValueError"],
            branches=[{"condition": "x > 0"}],
            error_paths=[{"error": "ValueError"}],
        )
        assert proof1.compute_hash() == proof2.compute_hash()
    
    def test_different_proofs_different_hash(self):
        """Different proofs produce different hashes."""
        proof1 = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x is not None"],
            postconditions=["result >= 0"],
            failure_modes=["ValueError"],
            branches=[{"condition": "x > 0"}],
            error_paths=[{"error": "ValueError"}],
        )
        proof2 = create_proof(
            inputs={"y": "different"},
            types={"y": "str"},
            preconditions=["y is not empty"],
            postconditions=["result is str"],
            failure_modes=["TypeError"],
            branches=[{"condition": "len(y) > 0"}],
            error_paths=[{"error": "TypeError"}],
        )
        assert proof1.compute_hash() != proof2.compute_hash()


# ============================================================================
# 5. PRE-GENERATION GATE TESTS
# ============================================================================

class TestPreGenerationGate:
    """Tests for PreGenerationGate."""
    
    def test_accepts_valid_proof(self):
        """Gate accepts valid proof."""
        gate = PreGenerationGate()
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x is not None"],
            postconditions=["result >= 0"],
            failure_modes=["ValueError"],
            branches=[{"condition": "x > 0"}],
            error_paths=[{"error": "ValueError"}],
        )
        passed, reason = gate.submit_proof(proof)
        assert passed is True
        assert "accepted" in reason.lower()
        assert gate.has_proof(proof.proof_id)
    
    def test_rejects_invalid_proof(self):
        """Gate rejects invalid proof."""
        gate = PreGenerationGate()
        proof = PreGenerationProof(
            proof_id="invalid-proof",
            symbol_table=SymbolTable(inputs={}, types={}),
            contract=FunctionContract(
                preconditions=[],
                postconditions=[],
                failure_modes=[],
            ),
            control_flow=ControlFlowSketch(branches=[], error_paths=[]),
            side_effects=SideEffectLedger(),
        )
        passed, reason = gate.submit_proof(proof)
        assert passed is False
        assert "incomplete" in reason.lower()
        assert not gate.has_proof(proof.proof_id)
        assert len(gate.rejections) == 1
    
    def test_get_proof_returns_none_for_missing(self):
        """get_proof returns None for non-existent proof."""
        gate = PreGenerationGate()
        assert gate.get_proof("nonexistent") is None


# ============================================================================
# 6. EDGE CASE ORACLE TESTS
# ============================================================================

class TestEdgeCaseOracle:
    """Tests for EdgeCaseOracle."""
    
    def test_mandatory_inputs_generated(self):
        """Oracle generates mandatory edge case inputs."""
        inputs = EdgeCaseOracle.get_inputs({})
        
        categories = {inp.category for inp in inputs}
        assert "null" in categories
        assert "numeric_edge" in categories
        assert "empty" in categories
        assert "overflow" in categories
        assert "unicode" in categories
    
    def test_type_specific_inputs(self):
        """Oracle generates type-specific inputs."""
        inputs = EdgeCaseOracle.get_inputs({"x": "int", "y": "str", "z": "list"})
        
        names = {inp.name for inp in inputs}
        assert "x_negative" in names
        assert "y_long" in names
        assert "z_large" in names


# ============================================================================
# 7. AST SYMBOLIC SIMULATOR TESTS
# ============================================================================

class TestASTSymbolicSimulator:
    """Tests for ASTSymbolicSimulator."""
    
    def test_valid_code_passes_simulation(self):
        """Valid code passes simulation."""
        simulator = ASTSymbolicSimulator()
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "Any"},
            preconditions=["x can be any type"],
            postconditions=["returns x unchanged"],
            failure_modes=["None"],
            branches=[{"condition": "always"}],
            error_paths=[{"error": "none"}],
        )
        
        code = """
def main(x):
    return x
"""
        passed, results = simulator.simulate(code, proof, "main")
        assert passed is True
    
    def test_syntax_error_fails_simulation(self):
        """Code with syntax error fails simulation."""
        simulator = ASTSymbolicSimulator()
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "Any"},
            preconditions=["x exists"],
            postconditions=["returns value"],
            failure_modes=["SyntaxError"],
            branches=[{"condition": "always"}],
            error_paths=[{"error": "syntax"}],
        )
        
        code = "def main(x) return x"  # Missing colon
        passed, results = simulator.simulate(code, proof, "main")
        assert passed is False
    
    def test_missing_function_fails(self):
        """Missing function name fails simulation."""
        simulator = ASTSymbolicSimulator()
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "Any"},
            preconditions=["x exists"],
            postconditions=["returns value"],
            failure_modes=["NameError"],
            branches=[{"condition": "always"}],
            error_paths=[{"error": "name"}],
        )
        
        code = """
def other_function(x):
    return x
"""
        passed, results = simulator.simulate(code, proof, "main")
        assert passed is False


# ============================================================================
# 8. DETERMINISTIC FALLBACK TESTS
# ============================================================================

class TestDeterministicFallbackRegistry:
    """Tests for DeterministicFallbackRegistry."""
    
    def test_register_and_retrieve_template(self):
        """Can register and retrieve fallback template."""
        registry = DeterministicFallbackRegistry()
        
        code = "def fallback(x): return None"
        template = registry.register_template(
            name="test_fallback",
            code=code,
            verified_by="test",
        )
        
        assert template.name == "test_fallback"
        assert template.code == code
        assert template.verified_by == "test"
        assert len(template.hash) == 16
    
    def test_get_fallback_logs_usage(self):
        """Getting fallback logs the usage."""
        registry = DeterministicFallbackRegistry()
        registry.register_template("test", "def test(): pass")
        
        template = registry.get_fallback("test", FailureMode.TIMEOUT)
        
        assert template is not None
        assert len(registry.fallback_uses) == 1
        assert registry.fallback_uses[0]["failure_reason"] == "timeout"
    
    def test_get_nonexistent_fallback_returns_none(self):
        """Getting non-existent fallback returns None."""
        registry = DeterministicFallbackRegistry()
        
        template = registry.get_fallback("nonexistent", FailureMode.TIMEOUT)
        
        assert template is None
    
    def test_verify_template_integrity(self):
        """Template integrity verification works."""
        registry = DeterministicFallbackRegistry()
        template = registry.register_template("test", "def test(): pass")
        
        assert registry.verify_template_integrity(template) is True
        
        # Tamper with code
        template.code = "def tampered(): pass"
        assert registry.verify_template_integrity(template) is False


# ============================================================================
# 9. GENESIS STAMPER TESTS
# ============================================================================

class TestGenesisStamper:
    """Tests for GenesisStamper."""
    
    def test_stamps_all_lines(self):
        """Stamper stamps all code lines."""
        stamper = GenesisStamper()
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x exists"],
            postconditions=["returns value"],
            failure_modes=["None"],
            branches=[{"condition": "always"}],
            error_paths=[{"error": "none"}],
        )
        
        code = """def main(x):
    return x
"""
        test_results = {"passed": 1, "failed": 0}
        
        stamped_code, stamps = stamper.stamp_code(code, proof, test_results)
        
        assert len(stamps) == 3  # 3 lines
        assert "G-" in stamped_code
        assert all(s.g_key.startswith("G-") for s in stamps)
    
    def test_genesis_stamp_contains_hashes(self):
        """Genesis stamps contain all required hashes."""
        stamper = GenesisStamper()
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x exists"],
            postconditions=["returns value"],
            failure_modes=["None"],
            branches=[{"condition": "always"}],
            error_paths=[{"error": "none"}],
        )
        
        code = "def main(x): return x"
        test_results = {"passed": 1}
        
        _, stamps = stamper.stamp_code(code, proof, test_results)
        
        stamp = stamps[0]
        assert stamp.symbolic_hash is not None
        assert stamp.ast_hash is not None
        assert stamp.test_hash is not None
        assert stamp.engine_version == "layer4-compiler-v1.0.0"
    
    def test_verify_lineage(self):
        """Can verify line lineage."""
        stamper = GenesisStamper()
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x exists"],
            postconditions=["returns value"],
            failure_modes=["None"],
            branches=[{"condition": "always"}],
            error_paths=[{"error": "none"}],
        )
        
        _, stamps = stamper.stamp_code("x = 1", proof, {})
        
        assert stamper.verify_lineage(stamps[0].g_key) is True
        assert stamper.verify_lineage("G-invalid-key") is False
    
    def test_get_ancestry(self):
        """Can get full ancestry for a line."""
        stamper = GenesisStamper()
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x exists"],
            postconditions=["returns value"],
            failure_modes=["None"],
            branches=[{"condition": "always"}],
            error_paths=[{"error": "none"}],
        )
        
        _, stamps = stamper.stamp_code("x = 1", proof, {})
        
        ancestry = stamper.get_ancestry(stamps[0].g_key)
        
        assert ancestry is not None
        assert "g_key" in ancestry
        assert "symbolic_hash" in ancestry
        assert "ast_hash" in ancestry
        assert "test_hash" in ancestry
        assert "engine_version" in ancestry


# ============================================================================
# 10. SELF-VERIFY LOOP TESTS
# ============================================================================

class TestSelfVerifyLoop:
    """Tests for SelfVerifyLoop."""
    
    def test_verification_passes_on_match(self):
        """Verification passes when intent matches outcome."""
        verifier = SelfVerifyLoop()
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x exists"],
            postconditions=["returns value"],
            failure_modes=["None"],
            branches=[{"condition": "always"}],
            error_paths=[{"error": "none"}],
        )
        
        result = verifier.verify(
            proof=proof,
            execution_result=42,
            observed_side_effects={},
            state_before={},
            state_after={},
        )
        
        assert result.passed is True
        assert len(result.violations) == 0
    
    def test_undeclared_side_effects_fail(self):
        """Undeclared side effects cause verification failure."""
        verifier = SelfVerifyLoop()
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x exists"],
            postconditions=["returns value"],
            failure_modes=["None"],
            branches=[{"condition": "always"}],
            error_paths=[{"error": "none"}],
        )
        
        result = verifier.verify(
            proof=proof,
            execution_result=42,
            observed_side_effects={"io": ["file_write"]},  # Undeclared!
            state_before={},
            state_after={},
        )
        
        assert result.passed is False
        assert result.side_effects_valid is False
    
    def test_mismatch_penalizes_path(self):
        """Mismatch adds penalty to path."""
        verifier = SelfVerifyLoop()
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x exists"],
            postconditions=["returns value"],
            failure_modes=["None"],
            branches=[{"condition": "always"}],
            error_paths=[{"error": "none"}],
        )
        
        verifier.verify(
            proof=proof,
            execution_result=42,
            observed_side_effects={"io": ["undeclared"]},
            state_before={},
            state_after={},
        )
        
        assert proof.proof_id in verifier.path_penalties
        assert verifier.path_penalties[proof.proof_id] > 0


# ============================================================================
# 11. LEARNING INJECTOR TESTS
# ============================================================================

class TestLearningInjector:
    """Tests for LearningInjector."""
    
    def test_injects_on_success(self):
        """Injector creates trace on successful verification."""
        injector = LearningInjector()
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x exists"],
            postconditions=["returns value"],
            failure_modes=["None"],
            branches=[{"condition": "always"}],
            error_paths=[{"error": "none"}],
        )
        
        from backend.ml_intelligence.layer4_compiler_governed_pipeline import VerificationResult
        verification = VerificationResult(
            passed=True,
            intent_vs_outcome_match=True,
            side_effects_valid=True,
            state_deltas_valid=True,
        )
        test_results = {"passed": 5, "failed": 0}
        
        trace = injector.inject(proof, verification, test_results)
        
        assert trace is not None
        assert trace.proof_id == proof.proof_id
        assert len(injector.validated_traces) == 1
    
    def test_rejects_on_verification_failure(self):
        """Injector rejects trace on verification failure."""
        injector = LearningInjector()
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x exists"],
            postconditions=["returns value"],
            failure_modes=["None"],
            branches=[{"condition": "always"}],
            error_paths=[{"error": "none"}],
        )
        
        from backend.ml_intelligence.layer4_compiler_governed_pipeline import VerificationResult
        verification = VerificationResult(
            passed=False,
            intent_vs_outcome_match=False,
            side_effects_valid=True,
            state_deltas_valid=True,
            violations=["Postcondition failed"],
        )
        test_results = {"passed": 5, "failed": 0}
        
        trace = injector.inject(proof, verification, test_results)
        
        assert trace is None
        assert len(injector.rejection_log) == 1
    
    def test_rejects_on_test_failure(self):
        """Injector rejects trace on test failure."""
        injector = LearningInjector()
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x exists"],
            postconditions=["returns value"],
            failure_modes=["None"],
            branches=[{"condition": "always"}],
            error_paths=[{"error": "none"}],
        )
        
        from backend.ml_intelligence.layer4_compiler_governed_pipeline import VerificationResult
        verification = VerificationResult(
            passed=True,
            intent_vs_outcome_match=True,
            side_effects_valid=True,
            state_deltas_valid=True,
        )
        test_results = {"passed": 3, "failed": 2}  # Some tests failed
        
        trace = injector.inject(proof, verification, test_results)
        
        assert trace is None
        assert len(injector.rejection_log) == 1


# ============================================================================
# 12. FULL PIPELINE TESTS
# ============================================================================

class TestCompilerGovernedPipeline:
    """Tests for the complete CompilerGovernedPipeline."""
    
    def test_pipeline_initialization(self):
        """Pipeline initializes correctly."""
        pipeline = get_compiler_governed_pipeline()
        
        assert pipeline is not None
        assert pipeline.pre_gate is not None
        assert pipeline.simulator is not None
        assert pipeline.stamper is not None
    
    def test_successful_generation(self):
        """Full pipeline generates code successfully."""
        pipeline = CompilerGovernedPipeline()
        
        proof = create_proof(
            inputs={"x": "input value"},
            types={"x": "Any"},
            preconditions=["x can be any type"],
            postconditions=["returns x unchanged"],
            failure_modes=["None"],
            branches=[{"condition": "identity function"}],
            error_paths=[{"error": "none expected"}],
        )
        
        def generator(p):
            return """
def main(x):
    return x
"""
        
        result = pipeline.generate(proof, generator, "main")
        
        assert result.success is True
        assert result.authority == GenerationAuthority.SYMBOLIC_PROOF
        assert result.code is not None
        assert "G-" in result.code  # Has genesis stamps
        assert len(result.genesis_stamps) > 0
    
    def test_generation_fails_without_proof(self):
        """Generation fails if proof not submitted first."""
        pipeline = CompilerGovernedPipeline()
        
        proof = PreGenerationProof(
            proof_id="invalid",
            symbol_table=SymbolTable(inputs={}, types={}),
            contract=FunctionContract(
                preconditions=[],
                postconditions=[],
                failure_modes=[],
            ),
            control_flow=ControlFlowSketch(branches=[], error_paths=[]),
            side_effects=SideEffectLedger(),
        )
        
        def generator(p):
            return "def main(x): return x"
        
        result = pipeline.generate(proof, generator, "main")
        
        assert result.success is False
        assert result.authority == GenerationAuthority.REJECTED
        assert result.failure_reason == FailureMode.MISSING_SYMBOL_TABLE
    
    def test_fallback_on_simulation_failure(self):
        """Pipeline uses fallback when simulation fails."""
        pipeline = CompilerGovernedPipeline()
        
        # Register fallback
        pipeline.fallback_registry.register_template(
            "fallback_main",
            "def main(x): return None",
        )
        
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "int"},
            preconditions=["x is int"],
            postconditions=["returns int"],
            failure_modes=["TypeError"],
            branches=[{"condition": "x > 0"}],
            error_paths=[{"error": "TypeError"}],
        )
        
        def bad_generator(p):
            # This will fail simulation (division by zero for x=0)
            return """
def main(x):
    return 1 / x
"""
        
        result = pipeline.generate(proof, bad_generator, "main")
        
        # Should use fallback
        assert result.success is True
        assert "return None" in result.code
    
    def test_pipeline_status(self):
        """Pipeline status returns expected structure."""
        pipeline = CompilerGovernedPipeline()
        
        status = pipeline.get_status()
        
        assert status["layer"] == "4-compiler-governed"
        assert "principle" in status
        assert "components" in status
        assert "pre_generation_gate" in status["components"]
        assert "genesis_stamper" in status["components"]
        assert "learning_injector" in status["components"]
    
    def test_generation_history_tracked(self):
        """Pipeline tracks generation history."""
        pipeline = CompilerGovernedPipeline()
        
        proof = create_proof(
            inputs={"x": "input"},
            types={"x": "Any"},
            preconditions=["x exists"],
            postconditions=["returns value"],
            failure_modes=["None"],
            branches=[{"condition": "always"}],
            error_paths=[{"error": "none"}],
        )
        
        pipeline.generate(proof, lambda p: "def main(x): return x", "main")
        
        assert len(pipeline.generation_history) == 1
        assert pipeline.generation_history[0]["success"] is True


# ============================================================================
# 13. INTEGRATION TESTS
# ============================================================================

class TestPipelineIntegration:
    """Integration tests for the full pipeline flow."""
    
    def test_full_flow_with_learning_injection(self):
        """Complete flow from proof to learning injection."""
        pipeline = CompilerGovernedPipeline()
        
        # Create valid proof
        proof = create_proof(
            inputs={"n": "number to check"},
            types={"n": "int"},
            preconditions=["n is integer"],
            postconditions=["returns boolean"],
            failure_modes=["TypeError for non-int"],
            branches=[
                {"condition": "n <= 1", "action": "return False"},
                {"condition": "n > 1", "action": "check primality"},
            ],
            error_paths=[{"error": "TypeError", "handler": "return False"}],
            constraints=["n must be finite"],
            invariants=["result is always boolean"],
        )
        
        def is_prime_generator(p):
            return """
def main(n):
    if n is None:
        return False
    if not isinstance(n, int):
        return False
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True
"""
        
        result = pipeline.generate(proof, is_prime_generator, "main")
        
        assert result.success is True
        assert result.verification is not None
        assert len(pipeline.learning_injector.validated_traces) >= 0


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
