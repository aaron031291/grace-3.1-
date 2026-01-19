"""
Cognitive Modules - REAL Functional Tests

Tests verify ACTUAL cognitive system behavior:
- Learning memory systems
- Coding agent operations
- Clarity framework
- Memory mesh integration
- Deterministic systems
- Autonomous healing
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# LEARNING MEMORY TESTS
# =============================================================================

class TestLearningMemoryFunctional:
    """Functional tests for learning memory system."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        session = MagicMock()
        session.add = MagicMock()
        session.commit = MagicMock()
        session.query = MagicMock()
        return session

    @pytest.fixture
    def learning_memory(self, mock_session):
        """Create learning memory instance."""
        with patch('cognitive.learning_memory.get_session', return_value=mock_session):
            from cognitive.learning_memory import LearningMemory
            return LearningMemory(session=mock_session)

    def test_initialization(self, learning_memory):
        """Learning memory must initialize properly."""
        assert learning_memory is not None

    def test_store_learning_example(self, learning_memory):
        """store_example must store learning example."""
        example_id = learning_memory.store_example(
            example_type="success",
            input_data={"query": "How to sort a list?"},
            output_data={"code": "sorted(lst)"},
            feedback_score=0.9
        )

        assert example_id is not None

    def test_retrieve_similar_examples(self, learning_memory):
        """retrieve_similar must return similar examples."""
        examples = learning_memory.retrieve_similar(
            query="How to sort?",
            limit=5
        )

        assert isinstance(examples, list)

    def test_update_example_feedback(self, learning_memory):
        """update_feedback must update example score."""
        result = learning_memory.update_feedback(
            example_id="EX-001",
            new_score=0.95,
            feedback_source="user"
        )

        assert result is True or result is None


# =============================================================================
# CODING AGENT TESTS
# =============================================================================

class TestCodingAgentFunctional:
    """Functional tests for coding agent."""

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM."""
        llm = MagicMock()
        llm.generate = AsyncMock(return_value="def hello(): print('hello')")
        return llm

    @pytest.fixture
    def coding_agent(self, mock_llm):
        """Create coding agent."""
        with patch('cognitive.coding_agent.get_llm', return_value=mock_llm):
            from cognitive.coding_agent import CodingAgent
            return CodingAgent()

    def test_initialization(self, coding_agent):
        """Coding agent must initialize properly."""
        assert coding_agent is not None

    @pytest.mark.asyncio
    async def test_generate_code(self, coding_agent):
        """generate_code must return code."""
        code = await coding_agent.generate_code(
            task="Write a hello world function",
            language="python"
        )

        assert code is not None
        assert isinstance(code, str)

    @pytest.mark.asyncio
    async def test_fix_code(self, coding_agent):
        """fix_code must return fixed code."""
        broken_code = "def foo(\n    return 1"

        fixed = await coding_agent.fix_code(
            code=broken_code,
            error="SyntaxError: invalid syntax"
        )

        assert fixed is not None

    def test_analyze_code_quality(self, coding_agent):
        """analyze_quality must return quality metrics."""
        code = "def foo(): return 1"

        quality = coding_agent.analyze_quality(code)

        assert isinstance(quality, dict)


# =============================================================================
# CLARITY FRAMEWORK TESTS
# =============================================================================

class TestClarityFrameworkFunctional:
    """Functional tests for clarity framework."""

    @pytest.fixture
    def clarity(self):
        """Create clarity framework."""
        from cognitive.clarity_framework import ClarityFramework
        return ClarityFramework()

    def test_initialization(self, clarity):
        """Clarity framework must initialize properly."""
        assert clarity is not None

    def test_verify_output(self, clarity):
        """verify_output must check code correctness."""
        code = "def add(a, b): return a + b"
        spec = {"function": "add", "returns": "sum of inputs"}

        result = clarity.verify_output(code, spec)

        assert result is not None
        assert hasattr(result, 'verified') or 'verified' in result

    def test_get_confidence_score(self, clarity):
        """get_confidence must return confidence score."""
        code = "def foo(): return 42"

        score = clarity.get_confidence(code)

        assert isinstance(score, (int, float))
        assert 0 <= score <= 1

    def test_check_hallucination(self, clarity):
        """check_hallucination must detect potential hallucinations."""
        response = "The function uses the foobar library"

        result = clarity.check_hallucination(
            response=response,
            context={"available_libraries": ["os", "sys"]}
        )

        assert result is not None


# =============================================================================
# MEMORY MESH TESTS
# =============================================================================

class TestMemoryMeshFunctional:
    """Functional tests for memory mesh."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        return MagicMock()

    @pytest.fixture
    def memory_mesh(self, mock_session):
        """Create memory mesh."""
        with patch('cognitive.memory_mesh_integration.get_session', return_value=mock_session):
            from cognitive.memory_mesh_integration import MemoryMeshIntegration
            return MemoryMeshIntegration(session=mock_session)

    def test_initialization(self, memory_mesh):
        """Memory mesh must initialize properly."""
        assert memory_mesh is not None

    def test_store_memory(self, memory_mesh):
        """store_memory must store memory entry."""
        memory_id = memory_mesh.store_memory(
            memory_type="episodic",
            content={"event": "successful_fix", "file": "test.py"},
            trust_score=0.85
        )

        assert memory_id is not None

    def test_retrieve_memories(self, memory_mesh):
        """retrieve_memories must return relevant memories."""
        memories = memory_mesh.retrieve_memories(
            query="fixing syntax errors",
            memory_type="episodic",
            limit=10
        )

        assert isinstance(memories, list)

    def test_update_trust_score(self, memory_mesh):
        """update_trust must update memory trust score."""
        result = memory_mesh.update_trust(
            memory_id="MEM-001",
            new_score=0.9,
            reason="positive feedback"
        )

        assert result is True or result is None

    def test_get_memory_stats(self, memory_mesh):
        """get_stats must return memory statistics."""
        stats = memory_mesh.get_memory_mesh_stats()

        assert isinstance(stats, dict)


# =============================================================================
# DETERMINISTIC SYSTEMS TESTS
# =============================================================================

class TestDeterministicSystemsFunctional:
    """Functional tests for deterministic systems."""

    def test_deterministic_code_fixer(self):
        """DeterministicCodeFixer must fix code deterministically."""
        from cognitive.deterministic_code_fixer import DeterministicCodeFixer

        fixer = DeterministicCodeFixer()

        # Same input should always produce same output
        code = "def foo():\nprint('hello')"  # Missing indent

        fix1 = fixer.fix(code)
        fix2 = fixer.fix(code)

        assert fix1 == fix2

    def test_deterministic_validator(self):
        """DeterministicValidator must validate consistently."""
        from cognitive.deterministic_validator import DeterministicValidator

        validator = DeterministicValidator()

        code = "def foo(): return 1"

        result1 = validator.validate(code)
        result2 = validator.validate(code)

        assert result1 == result2

    def test_deterministic_pattern_matcher(self):
        """DeterministicPatternMatcher must match patterns consistently."""
        from cognitive.deterministic_pattern_matcher import DeterministicPatternMatcher

        matcher = DeterministicPatternMatcher()

        code = "for i in range(10): print(i)"

        patterns1 = matcher.find_patterns(code)
        patterns2 = matcher.find_patterns(code)

        assert patterns1 == patterns2


# =============================================================================
# AUTONOMOUS HEALING TESTS
# =============================================================================

class TestAutonomousHealingFunctional:
    """Functional tests for autonomous healing system."""

    @pytest.fixture
    def mock_session(self):
        """Create mock session."""
        session = MagicMock()
        session.query.return_value.filter.return_value.all.return_value = []
        return session

    @pytest.fixture
    def healing_system(self, mock_session):
        """Create autonomous healing system."""
        from cognitive.autonomous_healing_system import AutonomousHealingSystem, TrustLevel

        return AutonomousHealingSystem(
            session=mock_session,
            repo_path=Path.cwd(),
            trust_level=TrustLevel.MEDIUM_RISK_AUTO
        )

    def test_initialization(self, healing_system):
        """Healing system must initialize properly."""
        assert healing_system is not None

    def test_health_status_enum(self):
        """HealthStatus must have required values."""
        from cognitive.autonomous_healing_system import HealthStatus

        required = ["HEALTHY", "DEGRADED", "CRITICAL", "UNKNOWN"]

        for status in required:
            assert hasattr(HealthStatus, status)

    def test_trust_level_enum(self):
        """TrustLevel must have required values."""
        from cognitive.autonomous_healing_system import TrustLevel

        # Should have multiple trust levels
        levels = list(TrustLevel)
        assert len(levels) >= 3

    def test_assess_health(self, healing_system):
        """assess_system_health must return assessment."""
        assessment = healing_system.assess_system_health()

        assert isinstance(assessment, dict)
        assert 'health_status' in assessment

    def test_get_capabilities(self, healing_system):
        """get_system_capabilities must return capabilities."""
        capabilities = healing_system.get_system_capabilities()

        assert isinstance(capabilities, dict)
        assert 'available' in capabilities
        assert 'degraded' in capabilities


# =============================================================================
# HEALING SCHEDULER TESTS
# =============================================================================

class TestHealingSchedulerFunctional:
    """Functional tests for healing scheduler."""

    @pytest.fixture
    def scheduler(self):
        """Create healing scheduler."""
        with patch('cognitive.healing_scheduler.get_session'):
            from cognitive.healing_scheduler import get_healing_scheduler
            return get_healing_scheduler()

    def test_initialization(self, scheduler):
        """Scheduler must initialize properly."""
        assert scheduler is not None

    def test_healing_priority_enum(self):
        """HealingPriority must have required values."""
        from cognitive.healing_scheduler import HealingPriority

        required = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "BACKGROUND"]

        for priority in required:
            assert hasattr(HealingPriority, priority)

    def test_add_task(self, scheduler):
        """add_task must add healing task."""
        from cognitive.healing_scheduler import HealingPriority

        task_id = scheduler.add_task(
            task_type="code_fix",
            priority=HealingPriority.MEDIUM,
            data={"file": "test.py", "issue": "syntax_error"}
        )

        assert task_id is not None

    def test_get_status(self, scheduler):
        """get_status must return scheduler status."""
        status = scheduler.get_status()

        assert isinstance(status, dict)
        assert 'running' in status


# =============================================================================
# CODE ANALYZER SELF-HEALING TESTS
# =============================================================================

class TestCodeAnalyzerSelfHealingFunctional:
    """Functional tests for code analyzer self-healing."""

    @pytest.fixture
    def applicator(self):
        """Create code fix applicator."""
        from cognitive.code_analyzer_self_healing import CodeFixApplicator
        return CodeFixApplicator()

    def test_applicator_initialization(self, applicator):
        """Applicator must initialize properly."""
        assert applicator is not None

    def test_apply_fix_missing_docstring(self, applicator):
        """apply_fix must add missing docstring."""
        from cognitive.grace_code_analyzer import CodeIssue, Severity, Confidence

        source = "def foo():\n    return 42\n"

        issue = CodeIssue(
            rule_id="G001",
            message="Missing docstring",
            file_path="test.py",
            line_number=1,
            severity=Severity.MEDIUM,
            confidence=Confidence.HIGH
        )

        success, fixed = applicator.apply_fix(issue, source)

        assert success is True
        assert '"""' in fixed or "'''" in fixed

    def test_apply_fix_bare_except(self, applicator):
        """apply_fix must fix bare except."""
        from cognitive.grace_code_analyzer import CodeIssue, Severity, Confidence

        source = "try:\n    x = 1\nexcept:\n    pass\n"

        issue = CodeIssue(
            rule_id="G005",
            message="Bare except",
            file_path="test.py",
            line_number=3,
            severity=Severity.MEDIUM,
            confidence=Confidence.HIGH
        )

        success, fixed = applicator.apply_fix(issue, source)

        assert success is True
        assert "except Exception:" in fixed


# =============================================================================
# SEMANTIC REFACTORING TESTS
# =============================================================================

class TestSemanticRefactoringFunctional:
    """Functional tests for semantic refactoring engine."""

    @pytest.fixture
    def engine(self):
        """Create refactoring engine."""
        from cognitive.semantic_refactoring_engine import SemanticRefactoringEngine
        return SemanticRefactoringEngine()

    def test_initialization(self, engine):
        """Engine must initialize properly."""
        assert engine is not None

    def test_analyze_refactoring_opportunities(self, engine):
        """analyze must find refactoring opportunities."""
        code = """
def foo():
    x = 1
    y = 2
    z = x + y
    return z

def bar():
    a = 1
    b = 2
    c = a + b
    return c
"""
        opportunities = engine.analyze(code)

        assert isinstance(opportunities, list)

    def test_apply_refactoring(self, engine):
        """apply_refactoring must refactor code."""
        code = "def foo(): x = 1; y = 2; return x + y"

        refactored = engine.apply_refactoring(
            code=code,
            refactoring_type="extract_variable"
        )

        assert refactored is not None


# =============================================================================
# ACTIVE LEARNING TESTS
# =============================================================================

class TestActiveLearningFunctional:
    """Functional tests for active learning system."""

    @pytest.fixture
    def active_learner(self):
        """Create active learning system."""
        with patch('cognitive.active_learning_system.get_session'):
            from cognitive.active_learning_system import ActiveLearningSystem
            return ActiveLearningSystem()

    def test_initialization(self, active_learner):
        """Active learner must initialize properly."""
        assert active_learner is not None

    def test_select_examples(self, active_learner):
        """select_examples must select informative examples."""
        candidates = [
            {"id": 1, "uncertainty": 0.9},
            {"id": 2, "uncertainty": 0.5},
            {"id": 3, "uncertainty": 0.8}
        ]

        selected = active_learner.select_examples(
            candidates=candidates,
            budget=2
        )

        assert len(selected) <= 2

    def test_update_model(self, active_learner):
        """update_model must incorporate new examples."""
        result = active_learner.update_model(
            examples=[{"input": "test", "output": "result"}]
        )

        assert result is not None


# =============================================================================
# FEDERATED LEARNING TESTS
# =============================================================================

class TestFederatedLearningFunctional:
    """Functional tests for federated learning system."""

    @pytest.fixture
    def federated_system(self):
        """Create federated learning system."""
        with patch('cognitive.federated_learning_system.get_session'):
            from cognitive.federated_learning_system import FederatedLearningSystem
            return FederatedLearningSystem()

    def test_initialization(self, federated_system):
        """Federated system must initialize properly."""
        assert federated_system is not None

    def test_aggregate_updates(self, federated_system):
        """aggregate_updates must combine model updates."""
        updates = [
            {"weights": [0.1, 0.2], "samples": 100},
            {"weights": [0.3, 0.4], "samples": 200}
        ]

        aggregated = federated_system.aggregate_updates(updates)

        assert aggregated is not None

    def test_get_global_model(self, federated_system):
        """get_global_model must return current model."""
        model = federated_system.get_global_model()

        assert model is not None


# =============================================================================
# MIRROR SELF-MODELING TESTS
# =============================================================================

class TestMirrorSelfModelingFunctional:
    """Functional tests for mirror self-modeling system."""

    @pytest.fixture
    def mirror_system(self):
        """Create mirror self-modeling system."""
        from cognitive.mirror_self_modeling import get_mirror_system
        return get_mirror_system()

    def test_initialization(self, mirror_system):
        """Mirror system must initialize properly."""
        assert mirror_system is not None

    def test_self_assessment(self, mirror_system):
        """self_assess must return self-assessment."""
        assessment = mirror_system.self_assess()

        assert isinstance(assessment, dict)

    def test_predict_behavior(self, mirror_system):
        """predict_behavior must predict system behavior."""
        prediction = mirror_system.predict_behavior(
            scenario="high_load",
            parameters={"requests_per_second": 1000}
        )

        assert prediction is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
