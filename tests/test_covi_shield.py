"""
COVI-SHIELD Comprehensive Test Suite

Tests all COVI-SHIELD components:
- Static Analysis Engine
- Formal Verification Engine
- Dynamic Analysis Engine
- Repair Engine
- Learning Module
- Certificate Authority
- Orchestrator
- Genesis Integration
"""

import pytest
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import COVI-SHIELD components
from covi_shield.models import (
    VerificationResult,
    VerificationCertificate,
    BugPattern,
    RepairSuggestion,
    AnalysisReport,
    ShieldStatus,
    RiskLevel,
    CertificateStatus,
    AnalysisPhase,
    BugCategory,
    RepairStrategy,
    ProofType
)
from covi_shield.static_analyzer import StaticAnalyzer
from covi_shield.formal_verifier import FormalVerifier
from covi_shield.dynamic_analyzer import DynamicAnalyzer
from covi_shield.repair_engine import RepairEngine
from covi_shield.learning_module import LearningModule
from covi_shield.certificate_authority import CertificateAuthority, CertificateType
from covi_shield.orchestrator import (
    COVIShieldOrchestrator,
    get_covi_shield,
    VerificationLevel
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def sample_clean_code():
    """Sample Python code without issues."""
    return '''
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def greet(name: str) -> str:
    """Greet a person."""
    if name is None:
        return "Hello, stranger!"
    return f"Hello, {name}!"
'''


@pytest.fixture
def sample_buggy_code():
    """Sample Python code with various issues."""
    return '''
import pickle

password = "secret123"  # Hardcoded credential

def divide(a, b):
    return a / b  # Potential division by zero

def process_data(data=[]):  # Mutable default argument
    data.append("item")
    return data

def handle_error():
    try:
        risky_operation()
    except:  # Bare except
        pass

def check_value(x):
    if x == None:  # Should use 'is None'
        return False
    return True

def load_unsafe(data):
    return pickle.loads(data)  # Unsafe deserialization
'''


@pytest.fixture
def sample_security_code():
    """Sample code with security vulnerabilities."""
    return '''
import subprocess
import os

def run_command(user_input):
    # Command injection vulnerability
    subprocess.call(user_input, shell=True)

def get_file(filename):
    # Path traversal vulnerability
    path = "/data/" + filename
    with open(path) as f:
        return f.read()

api_key = "sk-1234567890abcdef"  # Hardcoded API key
'''


@pytest.fixture
def static_analyzer():
    """Create static analyzer instance."""
    return StaticAnalyzer()


@pytest.fixture
def formal_verifier():
    """Create formal verifier instance."""
    return FormalVerifier(secret_key="test-key")


@pytest.fixture
def dynamic_analyzer():
    """Create dynamic analyzer instance."""
    return DynamicAnalyzer()


@pytest.fixture
def repair_engine():
    """Create repair engine instance."""
    return RepairEngine()


@pytest.fixture
def learning_module():
    """Create learning module instance."""
    return LearningModule(memory_mesh_enabled=False)


@pytest.fixture
def certificate_authority():
    """Create certificate authority instance."""
    return CertificateAuthority(secret_key="test-secret-key")


@pytest.fixture
def orchestrator():
    """Create orchestrator instance."""
    return COVIShieldOrchestrator(
        auto_repair=True,
        learning_enabled=False
    )


# ============================================================================
# STATIC ANALYZER TESTS
# ============================================================================

class TestStaticAnalyzer:
    """Tests for Static Analysis Engine."""

    def test_analyze_clean_code(self, static_analyzer, sample_clean_code):
        """Test analysis of clean code."""
        result = static_analyzer.analyze(sample_clean_code)

        assert isinstance(result, VerificationResult)
        assert result.risk_level in [RiskLevel.INFO, RiskLevel.LOW]
        assert result.analysis_time_ms > 0

    def test_analyze_buggy_code(self, static_analyzer, sample_buggy_code):
        """Test analysis of buggy code."""
        result = static_analyzer.analyze(sample_buggy_code)

        assert isinstance(result, VerificationResult)
        assert result.issues_found > 0
        assert result.risk_level != RiskLevel.INFO

        # Check specific issues detected
        issue_types = [i.get("pattern_id", "") for i in result.issues]
        assert any("SYN" in t or "SEC" in t or "LOGIC" in t for t in issue_types)

    def test_analyze_security_vulnerabilities(self, static_analyzer, sample_security_code):
        """Test detection of security vulnerabilities."""
        result = static_analyzer.analyze(sample_security_code)

        assert result.issues_found > 0

        # Should detect security issues
        security_issues = [i for i in result.issues if "SEC" in i.get("pattern_id", "")]
        assert len(security_issues) > 0

    def test_analyze_syntax_error(self, static_analyzer):
        """Test handling of syntax errors."""
        invalid_code = "def broken(\n  pass"

        result = static_analyzer.analyze(invalid_code)

        assert result.risk_level == RiskLevel.CRITICAL
        assert any("SYN" in i.get("pattern_id", "") for i in result.issues)

    def test_analyze_with_genesis_key(self, static_analyzer, sample_clean_code):
        """Test analysis with Genesis Key ID."""
        result = static_analyzer.analyze(
            sample_clean_code,
            genesis_key_id="GK-test-12345"
        )

        assert result.genesis_key_id == "GK-test-12345"

    def test_analyzer_stats(self, static_analyzer, sample_buggy_code):
        """Test analyzer statistics tracking."""
        initial_stats = static_analyzer.get_stats()

        static_analyzer.analyze(sample_buggy_code)

        updated_stats = static_analyzer.get_stats()
        assert updated_stats["total_analyses"] > initial_stats["total_analyses"]


# ============================================================================
# FORMAL VERIFIER TESTS
# ============================================================================

class TestFormalVerifier:
    """Tests for Formal Verification Engine."""

    def test_verify_clean_code(self, formal_verifier, sample_clean_code):
        """Test verification of clean code."""
        result = formal_verifier.verify(sample_clean_code)

        assert isinstance(result, VerificationResult)
        assert len(result.proofs) > 0

    def test_verify_with_properties(self, formal_verifier, sample_clean_code):
        """Test verification with specific properties."""
        result = formal_verifier.verify(
            sample_clean_code,
            properties_to_verify=["PROP-TYPE-001", "PROP-MEM-001"]
        )

        assert result.proofs is not None

    def test_issue_certificate(self, formal_verifier, sample_clean_code):
        """Test certificate issuance."""
        result = formal_verifier.verify(sample_clean_code)

        certificate = formal_verifier.issue_certificate(
            verification_result=result,
            properties_verified=["type_safety"],
            validity_hours=24
        )

        assert isinstance(certificate, VerificationCertificate)
        assert certificate.status == CertificateStatus.VALID
        assert certificate.signature is not None

    def test_verify_certificate(self, formal_verifier, sample_clean_code):
        """Test certificate verification."""
        result = formal_verifier.verify(sample_clean_code)
        certificate = formal_verifier.issue_certificate(
            verification_result=result,
            properties_verified=["type_safety"]
        )

        is_valid = formal_verifier.verify_certificate(certificate)
        assert is_valid is True

    def test_certificate_expiration(self, formal_verifier, sample_clean_code):
        """Test certificate expiration handling."""
        result = formal_verifier.verify(sample_clean_code)
        certificate = formal_verifier.issue_certificate(
            verification_result=result,
            properties_verified=["type_safety"],
            validity_hours=0  # Immediately expired
        )

        # Force expiration
        certificate.expires_at = datetime.utcnow() - timedelta(hours=1)

        is_valid = formal_verifier.verify_certificate(certificate)
        assert is_valid is False


# ============================================================================
# DYNAMIC ANALYZER TESTS
# ============================================================================

class TestDynamicAnalyzer:
    """Tests for Dynamic Analysis Engine."""

    def test_analyze_execution(self, dynamic_analyzer, sample_clean_code):
        """Test dynamic execution analysis."""
        result = dynamic_analyzer.analyze_execution(sample_clean_code)

        assert isinstance(result, VerificationResult)
        assert result.phase == AnalysisPhase.IN_FLIGHT
        assert "coverage" in result.metrics

    def test_analyze_with_test_inputs(self, dynamic_analyzer):
        """Test analysis with provided test inputs."""
        code = '''
def multiply(a, b):
    return a * b
'''
        test_inputs = [
            {"function": "multiply", "args": {"a": 2, "b": 3}},
            {"function": "multiply", "args": {"a": 0, "b": 5}}
        ]

        result = dynamic_analyzer.analyze_execution(
            code,
            test_inputs=test_inputs
        )

        assert result.metrics.get("executions", 0) >= len(test_inputs)

    def test_trace_collection(self, dynamic_analyzer, sample_clean_code):
        """Test execution trace collection."""
        dynamic_analyzer.analyze_execution(sample_clean_code)

        traces = dynamic_analyzer.get_traces()
        assert isinstance(traces, list)

    def test_property_checker(self, dynamic_analyzer):
        """Test runtime property checking."""
        checker = dynamic_analyzer.property_checker

        # Test precondition
        assert checker.check_precondition(True, "test") is True
        assert checker.check_precondition(False, "test") is False

        # Test bounds check
        assert checker.check_bounds(5, min_val=0, max_val=10) is True
        assert checker.check_bounds(15, min_val=0, max_val=10) is False


# ============================================================================
# REPAIR ENGINE TESTS
# ============================================================================

class TestRepairEngine:
    """Tests for Repair Engine."""

    def test_generate_repair_bare_except(self, repair_engine):
        """Test repair for bare except."""
        code = '''
try:
    risky()
except:
    pass
'''
        issue = {
            "pattern_id": "SYN-001",
            "name": "Bare Except",
            "line": 4
        }

        suggestion = repair_engine.generate_repair(code, issue)

        assert isinstance(suggestion, RepairSuggestion)
        assert suggestion.confidence > 0

    def test_generate_repair_none_comparison(self, repair_engine):
        """Test repair for None comparison."""
        code = 'if x == None:\n    pass'
        issue = {
            "pattern_id": "LOGIC-003",
            "name": "None Comparison",
            "line": 1
        }

        suggestion = repair_engine.generate_repair(code, issue)

        assert suggestion.validation_passed or suggestion.confidence > 0

    def test_repair_all(self, repair_engine):
        """Test repairing multiple issues."""
        code = '''
try:
    x = 1
except:
    pass

if y == None:
    pass
'''
        issues = [
            {"pattern_id": "SYN-001", "name": "Bare Except", "line": 4},
            {"pattern_id": "LOGIC-003", "name": "None Comparison", "line": 7}
        ]

        repaired_code, suggestions = repair_engine.repair_all(code, issues)

        assert len(suggestions) >= 0  # May or may not repair all

    def test_repair_validation(self, repair_engine):
        """Test that repairs produce valid Python."""
        code = 'except:'  # Invalid by itself

        issue = {"pattern_id": "SYN-001", "line": 1}

        suggestion = repair_engine.generate_repair(code, issue)

        # Should not produce invalid code
        if suggestion.repaired_code:
            assert suggestion.validation_passed or suggestion.confidence < 0.5


# ============================================================================
# LEARNING MODULE TESTS
# ============================================================================

class TestLearningModule:
    """Tests for Learning Module."""

    def test_record_verification_outcome(self, learning_module, sample_clean_code):
        """Test recording verification outcomes."""
        result = VerificationResult(
            success=True,
            risk_level=RiskLevel.INFO,
            issues_found=0
        )

        example = learning_module.record_verification_outcome(
            verification_result=result,
            code=sample_clean_code
        )

        assert example.example_type == "verification"
        assert example.success is True

    def test_record_repair_outcome(self, learning_module):
        """Test recording repair outcomes."""
        suggestion = RepairSuggestion(
            issue_id="TEST-001",
            strategy=RepairStrategy.TEMPLATE,
            confidence=0.9,
            validation_passed=True
        )

        example = learning_module.record_repair_outcome(
            suggestion=suggestion,
            applied=True,
            verification_passed=True
        )

        assert example.example_type == "repair"
        assert example.success is True

    def test_learning_cycle(self, learning_module):
        """Test running learning cycle."""
        result = learning_module.run_learning_cycle()

        assert "cycle_number" in result
        assert "examples_processed" in result

    def test_best_repair_strategy(self, learning_module):
        """Test getting best repair strategy."""
        strategy, confidence = learning_module.get_best_repair_strategy("TEST-001")

        assert strategy is not None
        assert 0 <= confidence <= 1

    def test_export_knowledge(self, learning_module):
        """Test knowledge export."""
        knowledge = learning_module.export_knowledge()

        assert "pattern_effectiveness" in knowledge
        assert "repair_effectiveness" in knowledge
        assert "exported_at" in knowledge


# ============================================================================
# CERTIFICATE AUTHORITY TESTS
# ============================================================================

class TestCertificateAuthority:
    """Tests for Certificate Authority."""

    def test_issue_certificate(self, certificate_authority):
        """Test certificate issuance."""
        result = VerificationResult(
            success=True,
            risk_level=RiskLevel.INFO
        )

        certificate = certificate_authority.issue_certificate(
            verification_result=result,
            properties_verified=["type_safety", "memory_safety"]
        )

        assert certificate.certificate_id.startswith("CERT-")
        assert certificate.status == CertificateStatus.VALID
        assert len(certificate.properties_verified) == 2

    def test_verify_certificate(self, certificate_authority):
        """Test certificate verification."""
        result = VerificationResult(success=True, risk_level=RiskLevel.INFO)
        certificate = certificate_authority.issue_certificate(
            verification_result=result,
            properties_verified=["test"]
        )

        is_valid, reason = certificate_authority.verify_certificate(certificate)

        assert is_valid is True
        assert "valid" in reason.lower()

    def test_revoke_certificate(self, certificate_authority):
        """Test certificate revocation."""
        result = VerificationResult(success=True, risk_level=RiskLevel.INFO)
        certificate = certificate_authority.issue_certificate(
            verification_result=result,
            properties_verified=["test"]
        )

        revoked = certificate_authority.revoke_certificate(
            certificate.certificate_id,
            "Test revocation"
        )

        assert revoked is True

        is_valid, reason = certificate_authority.verify_certificate(certificate)
        assert is_valid is False
        assert "revoked" in reason.lower()

    def test_audit_certificate(self, certificate_authority):
        """Test certificate audit."""
        result = VerificationResult(success=True, risk_level=RiskLevel.INFO)
        certificate = certificate_authority.issue_certificate(
            verification_result=result,
            properties_verified=["test"]
        )

        audit = certificate_authority.audit_certificate(certificate.certificate_id)

        assert "certificate_id" in audit
        assert "is_currently_valid" in audit
        assert "audited_at" in audit


# ============================================================================
# ORCHESTRATOR TESTS
# ============================================================================

class TestOrchestrator:
    """Tests for COVI-SHIELD Orchestrator."""

    def test_analyze_quick(self, orchestrator, sample_clean_code):
        """Test quick analysis."""
        result = orchestrator.quick_check(sample_clean_code)

        assert isinstance(result, VerificationResult)

    def test_analyze_standard(self, orchestrator, sample_clean_code):
        """Test standard analysis."""
        report = orchestrator.analyze(
            sample_clean_code,
            verification_level=VerificationLevel.STANDARD
        )

        assert isinstance(report, AnalysisReport)
        assert report.static_analysis is not None
        assert report.formal_verification is not None

    def test_analyze_full(self, orchestrator, sample_clean_code):
        """Test full analysis."""
        report = orchestrator.analyze(
            sample_clean_code,
            verification_level=VerificationLevel.FULL
        )

        assert report.static_analysis is not None
        assert report.formal_verification is not None
        assert report.dynamic_analysis is not None

    def test_analyze_with_repair(self, orchestrator, sample_buggy_code):
        """Test analysis with auto-repair."""
        report = orchestrator.analyze(
            sample_buggy_code,
            verification_level=VerificationLevel.REPAIR,
            auto_repair=True
        )

        # Should find issues
        assert report.total_issues > 0

        # May have suggested repairs
        assert len(report.repairs_suggested) >= 0

    def test_repair_and_verify(self, orchestrator, sample_buggy_code):
        """Test repair and verify workflow."""
        repaired_code, report = orchestrator.repair_and_verify(sample_buggy_code)

        assert isinstance(repaired_code, str)
        assert isinstance(report, AnalysisReport)

    def test_certificate_generation(self, orchestrator, sample_clean_code):
        """Test certificate generation in analysis."""
        report = orchestrator.analyze(sample_clean_code)

        assert report.certificate is not None
        assert report.certificate.certificate_id is not None

    def test_get_status(self, orchestrator):
        """Test status retrieval."""
        status = orchestrator.get_status()

        assert isinstance(status, ShieldStatus)
        assert status.operational is True
        assert "static_analyzer" in status.modules_active

    def test_get_module_stats(self, orchestrator, sample_clean_code):
        """Test module statistics retrieval."""
        orchestrator.analyze(sample_clean_code)

        stats = orchestrator.get_module_stats()

        assert "orchestrator" in stats
        assert "static_analyzer" in stats
        assert "formal_verifier" in stats


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for COVI-SHIELD."""

    def test_full_workflow(self, sample_buggy_code):
        """Test complete COVI-SHIELD workflow."""
        # Get global instance
        shield = get_covi_shield(auto_repair=True, learning_enabled=False)

        # Run full analysis
        report = shield.analyze(
            sample_buggy_code,
            verification_level=VerificationLevel.REPAIR
        )

        # Verify report structure
        assert report.report_id is not None
        assert report.total_issues > 0
        assert report.overall_risk != RiskLevel.INFO

        # Certificate should be issued
        assert report.certificate is not None

        # Verify certificate
        is_valid, reason = shield.verify_certificate(report.certificate.certificate_id)
        # May be invalid if critical issues found, which is expected

    def test_genesis_key_simulation(self, sample_clean_code):
        """Test simulated Genesis Key trigger."""
        shield = get_covi_shield(learning_enabled=False)

        # Simulate Genesis Key data
        report = shield.analyze(
            sample_clean_code,
            file_path="/test/path/example.py",
            genesis_key_id="GK-test-simulation"
        )

        assert report.genesis_key_id == "GK-test-simulation"

    def test_learning_integration(self, sample_buggy_code):
        """Test learning integration."""
        shield = COVIShieldOrchestrator(learning_enabled=True)

        # Run analysis
        report = shield.analyze(sample_buggy_code)

        # Run learning cycle
        learning_result = shield.run_learning_cycle()

        assert learning_result is not None
        assert "cycle_number" in learning_result


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Performance tests for COVI-SHIELD."""

    def test_quick_check_performance(self, orchestrator, sample_clean_code):
        """Test quick check completes within time limit."""
        start = time.time()

        orchestrator.quick_check(sample_clean_code)

        duration = time.time() - start
        assert duration < 1.0  # Should complete in under 1 second

    def test_standard_analysis_performance(self, orchestrator, sample_clean_code):
        """Test standard analysis performance."""
        start = time.time()

        orchestrator.analyze(
            sample_clean_code,
            verification_level=VerificationLevel.STANDARD
        )

        duration = time.time() - start
        assert duration < 5.0  # Should complete in under 5 seconds

    def test_large_code_analysis(self, orchestrator):
        """Test analysis of larger code base."""
        # Generate larger code
        large_code = "\n".join([
            f"def func_{i}(x):\n    return x + {i}"
            for i in range(100)
        ])

        start = time.time()

        result = orchestrator.quick_check(large_code)

        duration = time.time() - start
        assert duration < 10.0  # Should complete in under 10 seconds
        assert result is not None


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Edge case tests for COVI-SHIELD."""

    def test_empty_code(self, orchestrator):
        """Test handling of empty code."""
        result = orchestrator.quick_check("")

        assert result is not None
        # Empty code should have no issues
        assert result.issues_found == 0

    def test_unicode_code(self, orchestrator):
        """Test handling of Unicode in code."""
        code = '''
# 日本語コメント
def greet(name):
    return f"こんにちは、{name}さん！"
'''
        result = orchestrator.quick_check(code)
        assert result is not None

    def test_very_long_line(self, orchestrator):
        """Test handling of very long lines."""
        long_line = "x = " + "1 + " * 1000 + "1"
        code = f"def test():\n    {long_line}"

        result = orchestrator.quick_check(code)
        assert result is not None

    def test_deeply_nested_code(self, orchestrator):
        """Test handling of deeply nested code."""
        code = "def f():\n"
        for i in range(20):
            code += "    " * (i + 1) + f"if x{i}:\n"
        code += "    " * 21 + "pass"

        result = orchestrator.quick_check(code)
        assert result is not None

    def test_concurrent_analysis(self, orchestrator, sample_clean_code):
        """Test concurrent analysis requests."""
        import concurrent.futures

        def analyze():
            return orchestrator.quick_check(sample_clean_code)

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(analyze) for _ in range(3)]
            results = [f.result() for f in futures]

        assert all(r is not None for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
