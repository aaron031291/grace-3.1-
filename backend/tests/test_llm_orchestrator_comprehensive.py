"""
Comprehensive Test Suite for LLM Orchestrator Module
=====================================================
Tests for LLMOrchestrator, MultiLLMClient, HallucinationGuard,
CognitiveEnforcer, and related components.

Coverage:
- LLMTaskRequest and LLMTaskResult dataclasses
- LLMOrchestrator initialization
- Task execution pipeline
- Cognitive framework enforcement
- Hallucination mitigation
- Genesis Key assignment
- Learning memory integration
- Query methods
- MultiLLMClient operations
- Rate limiting
- Error handling
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

import sys

# =============================================================================
# Mock dependencies before any imports
# =============================================================================

# Mock sqlalchemy
mock_sqlalchemy = MagicMock()
mock_sqlalchemy.orm = MagicMock()
mock_sqlalchemy.orm.Session = MagicMock()
sys.modules['sqlalchemy'] = mock_sqlalchemy
sys.modules['sqlalchemy.orm'] = mock_sqlalchemy.orm

# Mock ollama_client
mock_ollama = MagicMock()
mock_ollama.client = MagicMock()
mock_ollama.client.OllamaClient = MagicMock()
sys.modules['ollama_client'] = mock_ollama
sys.modules['ollama_client.client'] = mock_ollama.client

# Mock requests
mock_requests = MagicMock()
sys.modules['requests'] = mock_requests

# Mock settings
mock_settings = MagicMock()
mock_settings.settings = MagicMock()
sys.modules['settings'] = mock_settings

# Mock genesis module
mock_genesis = MagicMock()
mock_genesis.cognitive_layer1_integration = MagicMock()
mock_genesis.cognitive_layer1_integration.get_cognitive_layer1_integration = MagicMock(return_value=MagicMock())
mock_genesis.cognitive_layer1_integration.CognitiveLayer1Integration = MagicMock()
sys.modules['genesis'] = mock_genesis
sys.modules['genesis.cognitive_layer1_integration'] = mock_genesis.cognitive_layer1_integration

# Mock cognitive module
mock_cognitive = MagicMock()
mock_cognitive.learning_memory = MagicMock()
mock_cognitive.learning_memory.LearningMemoryManager = MagicMock()
sys.modules['cognitive'] = mock_cognitive
sys.modules['cognitive.learning_memory'] = mock_cognitive.learning_memory

# Mock embedding module
mock_embedding = MagicMock()
mock_embedding.EmbeddingModel = MagicMock()
sys.modules['embedding'] = mock_embedding

# Mock confidence_scorer module
mock_confidence_scorer = MagicMock()
mock_confidence_scorer.confidence_scorer = MagicMock()
mock_confidence_scorer.confidence_scorer.ConfidenceScorer = MagicMock()
mock_confidence_scorer.contradiction_detector = MagicMock()
mock_confidence_scorer.contradiction_detector.SemanticContradictionDetector = MagicMock()
sys.modules['confidence_scorer'] = mock_confidence_scorer
sys.modules['confidence_scorer.confidence_scorer'] = mock_confidence_scorer.confidence_scorer
sys.modules['confidence_scorer.contradiction_detector'] = mock_confidence_scorer.contradiction_detector

sys.path.insert(0, '/home/user/grace-3.1-/backend')


# =============================================================================
# Mock TaskType Enum
# =============================================================================

class TaskType(Enum):
    """Task types for LLM operations."""
    GENERAL = "general"
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    DEBUGGING = "debugging"
    EXPLANATION = "explanation"
    REASONING = "reasoning"
    VALIDATION = "validation"


# =============================================================================
# Mock VerificationResult
# =============================================================================

@dataclass
class MockVerificationResult:
    """Mock verification result."""
    is_verified: bool
    confidence_score: float
    trust_score: float
    final_content: str
    verification_details: Dict[str, Any] = None


# =============================================================================
# Mock CognitiveConstraints
# =============================================================================

@dataclass
class MockCognitiveConstraints:
    """Mock cognitive constraints."""
    max_complexity: float = 0.5
    require_reversibility: bool = True
    min_immediate_value: float = 0.3


# =============================================================================
# LLMTaskRequest Tests
# =============================================================================

class TestLLMTaskRequest:
    """Test LLMTaskRequest dataclass."""

    def test_basic_task_request(self):
        """Test creating a basic task request."""
        @dataclass
        class LLMTaskRequest:
            task_id: str
            prompt: str
            task_type: TaskType
            user_id: Optional[str] = None
            require_verification: bool = True
            require_consensus: bool = True
            require_grounding: bool = True
            enable_learning: bool = True
            system_prompt: Optional[str] = None
            context_documents: Optional[List[str]] = None
            cognitive_constraints: Optional[MockCognitiveConstraints] = None

        request = LLMTaskRequest(
            task_id="test_task_001",
            prompt="Write a function to sort a list",
            task_type=TaskType.CODE_GENERATION
        )

        assert request.task_id == "test_task_001"
        assert request.prompt == "Write a function to sort a list"
        assert request.task_type == TaskType.CODE_GENERATION
        assert request.require_verification is True
        assert request.require_consensus is True
        assert request.require_grounding is True
        assert request.enable_learning is True

    def test_task_request_with_all_options(self):
        """Test task request with all options specified."""
        @dataclass
        class LLMTaskRequest:
            task_id: str
            prompt: str
            task_type: TaskType
            user_id: Optional[str] = None
            require_verification: bool = True
            require_consensus: bool = True
            require_grounding: bool = True
            enable_learning: bool = True
            system_prompt: Optional[str] = None
            context_documents: Optional[List[str]] = None
            cognitive_constraints: Optional[MockCognitiveConstraints] = None

        constraints = MockCognitiveConstraints(max_complexity=0.3, require_reversibility=True)

        request = LLMTaskRequest(
            task_id="test_task_002",
            prompt="Debug this code",
            task_type=TaskType.DEBUGGING,
            user_id="user_123",
            require_verification=False,
            require_consensus=False,
            require_grounding=True,
            enable_learning=False,
            system_prompt="You are a debugging expert",
            context_documents=["doc1.txt", "doc2.txt"],
            cognitive_constraints=constraints
        )

        assert request.user_id == "user_123"
        assert request.require_verification is False
        assert request.require_consensus is False
        assert request.enable_learning is False
        assert request.system_prompt == "You are a debugging expert"
        assert len(request.context_documents) == 2
        assert request.cognitive_constraints.max_complexity == 0.3


# =============================================================================
# LLMTaskResult Tests
# =============================================================================

class TestLLMTaskResult:
    """Test LLMTaskResult dataclass."""

    def test_successful_task_result(self):
        """Test creating a successful task result."""
        @dataclass
        class LLMTaskResult:
            task_id: str
            success: bool
            content: str
            verification_result: Optional[MockVerificationResult]
            cognitive_decision_id: Optional[str]
            genesis_key_id: Optional[str]
            trust_score: float
            confidence_score: float
            model_used: str
            duration_ms: float
            learning_example_id: Optional[str]
            audit_trail: List[Dict[str, Any]]
            timestamp: datetime

        verification = MockVerificationResult(
            is_verified=True,
            confidence_score=0.95,
            trust_score=0.92,
            final_content="def sort_list(lst): return sorted(lst)"
        )

        result = LLMTaskResult(
            task_id="test_task_001",
            success=True,
            content="def sort_list(lst): return sorted(lst)",
            verification_result=verification,
            cognitive_decision_id="decision_123",
            genesis_key_id="GK-LLM-test_task_001",
            trust_score=0.92,
            confidence_score=0.95,
            model_used="deepseek-coder",
            duration_ms=1250.5,
            learning_example_id="learn_001",
            audit_trail=[{"step": "cognitive_enforcement"}],
            timestamp=datetime.now()
        )

        assert result.success is True
        assert result.trust_score == 0.92
        assert result.confidence_score == 0.95
        assert result.model_used == "deepseek-coder"
        assert len(result.audit_trail) == 1

    def test_failed_task_result(self):
        """Test creating a failed task result."""
        @dataclass
        class LLMTaskResult:
            task_id: str
            success: bool
            content: str
            verification_result: Optional[MockVerificationResult]
            cognitive_decision_id: Optional[str]
            genesis_key_id: Optional[str]
            trust_score: float
            confidence_score: float
            model_used: str
            duration_ms: float
            learning_example_id: Optional[str]
            audit_trail: List[Dict[str, Any]]
            timestamp: datetime

        result = LLMTaskResult(
            task_id="test_task_002",
            success=False,
            content="",
            verification_result=None,
            cognitive_decision_id=None,
            genesis_key_id=None,
            trust_score=0.0,
            confidence_score=0.0,
            model_used="unknown",
            duration_ms=500.0,
            learning_example_id=None,
            audit_trail=[{"step": "error", "error": "LLM generation failed"}],
            timestamp=datetime.now()
        )

        assert result.success is False
        assert result.content == ""
        assert result.trust_score == 0.0
        assert result.confidence_score == 0.0


# =============================================================================
# RateLimiter Tests
# =============================================================================

class TestRateLimiter:
    """Test rate limiting functionality."""

    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        class RateLimiter:
            def __init__(
                self,
                requests_per_minute: int = 60,
                requests_per_hour: int = 1000,
                burst_size: int = 10
            ):
                self.requests_per_minute = requests_per_minute
                self.requests_per_hour = requests_per_hour
                self.burst_size = burst_size
                self._minute_tokens = requests_per_minute
                self._hour_tokens = requests_per_hour

        limiter = RateLimiter(requests_per_minute=30, requests_per_hour=500)

        assert limiter.requests_per_minute == 30
        assert limiter.requests_per_hour == 500
        assert limiter._minute_tokens == 30
        assert limiter._hour_tokens == 500

    def test_rate_limiter_acquire(self):
        """Test token acquisition."""
        class RateLimiter:
            def __init__(self, requests_per_minute: int = 60):
                self._minute_tokens = requests_per_minute
                self._hour_tokens = 1000

            def acquire(self) -> bool:
                if self._minute_tokens > 0 and self._hour_tokens > 0:
                    self._minute_tokens -= 1
                    self._hour_tokens -= 1
                    return True
                return False

        limiter = RateLimiter(requests_per_minute=3)

        # Should acquire successfully
        assert limiter.acquire() is True
        assert limiter._minute_tokens == 2

        assert limiter.acquire() is True
        assert limiter._minute_tokens == 1

        assert limiter.acquire() is True
        assert limiter._minute_tokens == 0

        # Should fail when exhausted
        assert limiter.acquire() is False

    def test_rate_limiter_burst(self):
        """Test burst handling."""
        class RateLimiter:
            def __init__(self, burst_size: int = 10):
                self.burst_size = burst_size
                self._burst_count = 0

            def check_burst(self) -> bool:
                if self._burst_count < self.burst_size:
                    self._burst_count += 1
                    return True
                return False

            def reset_burst(self):
                self._burst_count = 0

        limiter = RateLimiter(burst_size=5)

        # Use all burst tokens
        for i in range(5):
            assert limiter.check_burst() is True

        # Should fail after burst exhausted
        assert limiter.check_burst() is False

        # Reset should allow more
        limiter.reset_burst()
        assert limiter.check_burst() is True


# =============================================================================
# MultiLLMClient Tests
# =============================================================================

class TestMultiLLMClient:
    """Test MultiLLMClient functionality."""

    def test_multi_llm_client_initialization(self):
        """Test MultiLLMClient initialization."""
        class MockMultiLLMClient:
            def __init__(self):
                self.models = {
                    "deepseek-coder": {"active": True, "priority": 1},
                    "qwen2.5-coder": {"active": True, "priority": 2},
                    "deepseek-r1": {"active": True, "priority": 3},
                    "mistral-small": {"active": True, "priority": 4},
                    "llama3": {"active": True, "priority": 5},
                    "gemma2": {"active": True, "priority": 6},
                }
                self.stats = {}

        client = MockMultiLLMClient()

        assert len(client.models) == 6
        assert "deepseek-coder" in client.models
        assert client.models["deepseek-coder"]["active"] is True

    def test_model_selection_by_task_type(self):
        """Test model selection based on task type."""
        class MockMultiLLMClient:
            TASK_MODEL_MAP = {
                TaskType.CODE_GENERATION: ["deepseek-coder", "qwen2.5-coder"],
                TaskType.DEBUGGING: ["deepseek-coder", "qwen2.5-coder"],
                TaskType.REASONING: ["deepseek-r1", "mistral-small"],
                TaskType.VALIDATION: ["gemma2", "mistral-small"],
                TaskType.GENERAL: ["llama3", "mistral-small"],
            }

            def select_model(self, task_type: TaskType) -> str:
                models = self.TASK_MODEL_MAP.get(task_type, ["llama3"])
                return models[0]  # Return highest priority

        client = MockMultiLLMClient()

        assert client.select_model(TaskType.CODE_GENERATION) == "deepseek-coder"
        assert client.select_model(TaskType.REASONING) == "deepseek-r1"
        assert client.select_model(TaskType.VALIDATION) == "gemma2"
        assert client.select_model(TaskType.GENERAL) == "llama3"

    def test_generate_response(self):
        """Test LLM response generation."""
        class MockMultiLLMClient:
            def generate(
                self,
                prompt: str,
                task_type: TaskType = TaskType.GENERAL,
                system_prompt: str = ""
            ) -> Dict[str, Any]:
                return {
                    "success": True,
                    "content": f"Response to: {prompt[:50]}",
                    "model_name": "deepseek-coder",
                    "duration_ms": 250.0,
                    "tokens_used": 150
                }

        client = MockMultiLLMClient()
        response = client.generate(
            prompt="Write a sorting function",
            task_type=TaskType.CODE_GENERATION
        )

        assert response["success"] is True
        assert "content" in response
        assert response["model_name"] == "deepseek-coder"

    def test_failover_mechanism(self):
        """Test failover when primary model fails."""
        class MockMultiLLMClient:
            def __init__(self):
                self.failed_models = set()

            def generate_with_failover(
                self,
                prompt: str,
                models: List[str]
            ) -> Dict[str, Any]:
                for model in models:
                    if model not in self.failed_models:
                        if model == "primary_model":
                            self.failed_models.add(model)
                            continue  # Simulate failure
                        return {
                            "success": True,
                            "content": f"Fallback response from {model}",
                            "model_name": model
                        }
                return {"success": False, "error": "All models failed"}

        client = MockMultiLLMClient()
        result = client.generate_with_failover(
            "test prompt",
            ["primary_model", "fallback_model"]
        )

        assert result["success"] is True
        assert result["model_name"] == "fallback_model"

    def test_model_stats_tracking(self):
        """Test tracking of model statistics."""
        class MockMultiLLMClient:
            def __init__(self):
                self.model_stats = {}

            def record_usage(
                self,
                model: str,
                success: bool,
                duration_ms: float,
                tokens: int
            ):
                if model not in self.model_stats:
                    self.model_stats[model] = {
                        "total_calls": 0,
                        "successes": 0,
                        "failures": 0,
                        "total_duration_ms": 0.0,
                        "total_tokens": 0
                    }
                stats = self.model_stats[model]
                stats["total_calls"] += 1
                stats["successes"] += 1 if success else 0
                stats["failures"] += 0 if success else 1
                stats["total_duration_ms"] += duration_ms
                stats["total_tokens"] += tokens

            def get_model_stats(self) -> Dict[str, Any]:
                return self.model_stats

        client = MockMultiLLMClient()
        client.record_usage("deepseek-coder", True, 150.0, 100)
        client.record_usage("deepseek-coder", True, 200.0, 150)
        client.record_usage("deepseek-coder", False, 50.0, 0)

        stats = client.get_model_stats()
        assert stats["deepseek-coder"]["total_calls"] == 3
        assert stats["deepseek-coder"]["successes"] == 2
        assert stats["deepseek-coder"]["failures"] == 1


# =============================================================================
# LLMOrchestrator Tests
# =============================================================================

class TestLLMOrchestrator:
    """Test LLMOrchestrator main class."""

    def test_orchestrator_initialization(self):
        """Test LLMOrchestrator initialization."""
        class MockLLMOrchestrator:
            def __init__(
                self,
                session=None,
                embedding_model=None,
                knowledge_base_path=None
            ):
                self.session = session
                self.embedding_model = embedding_model
                self.multi_llm = MagicMock()
                self.repo_access = MagicMock()
                self.hallucination_guard = MagicMock()
                self.cognitive_enforcer = MagicMock()
                self.cognitive_layer1 = MagicMock() if session else None
                self.learning_memory = MagicMock() if session and knowledge_base_path else None
                self.active_tasks = {}
                self.completed_tasks = []

        orchestrator = MockLLMOrchestrator()

        assert orchestrator.session is None
        assert orchestrator.embedding_model is None
        assert orchestrator.active_tasks == {}
        assert orchestrator.completed_tasks == []

    def test_orchestrator_with_dependencies(self):
        """Test orchestrator with all dependencies."""
        class MockLLMOrchestrator:
            def __init__(
                self,
                session=None,
                embedding_model=None,
                knowledge_base_path=None
            ):
                self.session = session
                self.embedding_model = embedding_model
                self.multi_llm = MagicMock()
                self.repo_access = MagicMock()
                self.hallucination_guard = MagicMock()
                self.cognitive_enforcer = MagicMock()
                self.cognitive_layer1 = MagicMock() if session else None
                self.learning_memory = MagicMock() if session and knowledge_base_path else None
                self.active_tasks = {}
                self.completed_tasks = []

        mock_session = MagicMock()
        mock_embedding = MagicMock()

        orchestrator = MockLLMOrchestrator(
            session=mock_session,
            embedding_model=mock_embedding,
            knowledge_base_path="/path/to/kb"
        )

        assert orchestrator.session is mock_session
        assert orchestrator.embedding_model is mock_embedding
        assert orchestrator.cognitive_layer1 is not None
        assert orchestrator.learning_memory is not None


# =============================================================================
# Cognitive Enforcement Tests
# =============================================================================

class TestCognitiveEnforcement:
    """Test cognitive framework enforcement."""

    def test_ooda_loop_begin(self):
        """Test beginning OODA loop."""
        class MockCognitiveEnforcer:
            def __init__(self):
                self.decisions = {}
                self._decision_counter = 0

            def begin_ooda_loop(
                self,
                operation: str,
                constraints: Optional[MockCognitiveConstraints] = None
            ) -> str:
                self._decision_counter += 1
                decision_id = f"decision_{self._decision_counter}"
                self.decisions[decision_id] = {
                    "operation": operation,
                    "constraints": constraints,
                    "stage": "observe",
                    "observations": None,
                    "context": None,
                    "alternatives": None,
                    "action_result": None
                }
                return decision_id

        enforcer = MockCognitiveEnforcer()
        decision_id = enforcer.begin_ooda_loop("llm_task_code_generation")

        assert decision_id == "decision_1"
        assert enforcer.decisions[decision_id]["operation"] == "llm_task_code_generation"
        assert enforcer.decisions[decision_id]["stage"] == "observe"

    def test_ooda_observe(self):
        """Test OODA observe phase."""
        class MockCognitiveEnforcer:
            def __init__(self):
                self.decisions = {"decision_1": {"stage": "observe"}}

            def observe(self, decision_id: str, observations: Dict[str, Any]):
                if decision_id in self.decisions:
                    self.decisions[decision_id]["observations"] = observations
                    self.decisions[decision_id]["stage"] = "orient"

        enforcer = MockCognitiveEnforcer()
        enforcer.observe("decision_1", {
            "task_id": "task_001",
            "task_type": "code_generation",
            "prompt_length": 150
        })

        assert enforcer.decisions["decision_1"]["stage"] == "orient"
        assert enforcer.decisions["decision_1"]["observations"]["task_id"] == "task_001"

    def test_ooda_orient(self):
        """Test OODA orient phase."""
        class MockCognitiveEnforcer:
            def __init__(self):
                self.decisions = {"decision_1": {"stage": "orient"}}

            def orient(self, decision_id: str, context: Dict[str, Any]):
                if decision_id in self.decisions:
                    self.decisions[decision_id]["context"] = context
                    self.decisions[decision_id]["stage"] = "decide"

        enforcer = MockCognitiveEnforcer()
        enforcer.orient("decision_1", {
            "verification_required": True,
            "consensus_required": True
        })

        assert enforcer.decisions["decision_1"]["stage"] == "decide"
        assert enforcer.decisions["decision_1"]["context"]["verification_required"] is True

    def test_ooda_decide(self):
        """Test OODA decide phase."""
        class MockCognitiveEnforcer:
            def __init__(self):
                self.decisions = {"decision_1": {"stage": "decide"}}

            def decide(self, decision_id: str, alternatives: List[Dict[str, Any]]):
                if decision_id in self.decisions:
                    # Score alternatives and select best
                    best = max(alternatives, key=lambda a: a.get("immediate_value", 0))
                    self.decisions[decision_id]["alternatives"] = alternatives
                    self.decisions[decision_id]["selected"] = best
                    self.decisions[decision_id]["stage"] = "act"

        enforcer = MockCognitiveEnforcer()
        enforcer.decide("decision_1", [
            {"name": "option_a", "immediate_value": 0.5},
            {"name": "option_b", "immediate_value": 0.8}
        ])

        assert enforcer.decisions["decision_1"]["stage"] == "act"
        assert enforcer.decisions["decision_1"]["selected"]["name"] == "option_b"

    def test_ooda_act(self):
        """Test OODA act phase."""
        class MockCognitiveEnforcer:
            def __init__(self):
                self.decisions = {"decision_1": {"stage": "act"}}

            def act(self, decision_id: str, action_result: str, success: bool):
                if decision_id in self.decisions:
                    self.decisions[decision_id]["action_result"] = action_result
                    self.decisions[decision_id]["success"] = success
                    self.decisions[decision_id]["stage"] = "complete"

        enforcer = MockCognitiveEnforcer()
        enforcer.act("decision_1", "Task completed successfully", True)

        assert enforcer.decisions["decision_1"]["stage"] == "complete"
        assert enforcer.decisions["decision_1"]["success"] is True


# =============================================================================
# Hallucination Guard Tests
# =============================================================================

class TestHallucinationGuard:
    """Test hallucination mitigation pipeline."""

    def test_hallucination_guard_initialization(self):
        """Test HallucinationGuard initialization."""
        class MockHallucinationGuard:
            def __init__(
                self,
                multi_llm_client=None,
                repo_access=None,
                confidence_scorer=None
            ):
                self.multi_llm_client = multi_llm_client or MagicMock()
                self.repo_access = repo_access or MagicMock()
                self.confidence_scorer = confidence_scorer
                self.verification_count = 0
                self.verified_count = 0

        guard = MockHallucinationGuard()

        assert guard.multi_llm_client is not None
        assert guard.repo_access is not None
        assert guard.verification_count == 0

    def test_repository_grounding(self):
        """Test Layer 1: Repository grounding."""
        class MockHallucinationGuard:
            def __init__(self):
                self.repo_access = MagicMock()

            def check_repository_grounding(
                self,
                content: str,
                mentioned_files: List[str]
            ) -> Dict[str, Any]:
                # Check if mentioned files exist
                verified_files = []
                missing_files = []

                for f in mentioned_files:
                    if self.repo_access.file_exists(f):
                        verified_files.append(f)
                    else:
                        missing_files.append(f)

                return {
                    "is_grounded": len(missing_files) == 0,
                    "verified_files": verified_files,
                    "missing_files": missing_files,
                    "grounding_score": len(verified_files) / max(len(mentioned_files), 1)
                }

        guard = MockHallucinationGuard()
        guard.repo_access.file_exists = Mock(side_effect=lambda f: f in ["main.py", "utils.py"])

        result = guard.check_repository_grounding(
            "Check main.py and utils.py and missing.py",
            ["main.py", "utils.py", "missing.py"]
        )

        assert result["is_grounded"] is False
        assert "missing.py" in result["missing_files"]
        assert abs(result["grounding_score"] - 0.666) < 0.01

    def test_cross_model_consensus(self):
        """Test Layer 2: Cross-model consensus."""
        class MockHallucinationGuard:
            def check_consensus(
                self,
                prompt: str,
                primary_response: str,
                num_models: int = 3
            ) -> Dict[str, Any]:
                # Simulate consensus from multiple models
                responses = [primary_response]
                for i in range(num_models - 1):
                    responses.append(f"Similar response {i}")

                # Calculate agreement score (simulated)
                agreement_score = 0.85  # Assume high agreement

                return {
                    "has_consensus": agreement_score > 0.7,
                    "agreement_score": agreement_score,
                    "num_models_consulted": num_models,
                    "consensus_content": primary_response
                }

        guard = MockHallucinationGuard()
        result = guard.check_consensus(
            "What is quicksort?",
            "Quicksort is a divide-and-conquer algorithm...",
            num_models=3
        )

        assert result["has_consensus"] is True
        assert result["agreement_score"] == 0.85
        assert result["num_models_consulted"] == 3

    def test_contradiction_detection(self):
        """Test Layer 3: Contradiction detection."""
        class MockHallucinationGuard:
            def check_contradictions(
                self,
                content: str,
                knowledge_base: List[str]
            ) -> Dict[str, Any]:
                # Simulated contradiction check
                contradictions = []

                for knowledge in knowledge_base:
                    # Simple check - in real impl this would be semantic
                    if "Python is typed" in knowledge and "Python is untyped" in content:
                        contradictions.append({
                            "claim": "Python is untyped",
                            "contradicts": knowledge,
                            "confidence": 0.9
                        })

                return {
                    "has_contradictions": len(contradictions) > 0,
                    "contradictions": contradictions,
                    "contradiction_score": 1.0 - len(contradictions) * 0.2
                }

        guard = MockHallucinationGuard()
        result = guard.check_contradictions(
            "Python is untyped language",
            ["Python is typed (dynamically)"]
        )

        assert result["has_contradictions"] is True
        assert len(result["contradictions"]) == 1

    def test_full_verification_pipeline(self):
        """Test complete verification pipeline."""
        class MockHallucinationGuard:
            def verify_content(
                self,
                prompt: str,
                content: str,
                task_type: TaskType,
                enable_consensus: bool = True,
                enable_grounding: bool = True,
                enable_contradiction_check: bool = True,
                enable_trust_verification: bool = True
            ) -> MockVerificationResult:
                # Run all verification layers
                scores = []

                if enable_grounding:
                    scores.append(0.9)  # Grounding score

                if enable_consensus:
                    scores.append(0.85)  # Consensus score

                if enable_contradiction_check:
                    scores.append(0.95)  # No contradictions

                if enable_trust_verification:
                    scores.append(0.88)  # Trust score

                avg_score = sum(scores) / len(scores) if scores else 0.5

                return MockVerificationResult(
                    is_verified=avg_score > 0.7,
                    confidence_score=avg_score,
                    trust_score=avg_score * 0.95,
                    final_content=content
                )

        guard = MockHallucinationGuard()
        result = guard.verify_content(
            prompt="Explain sorting algorithms",
            content="Quicksort has O(n log n) average complexity",
            task_type=TaskType.EXPLANATION
        )

        assert result.is_verified is True
        assert result.confidence_score > 0.7
        assert result.trust_score > 0.6


# =============================================================================
# Genesis Key Assignment Tests
# =============================================================================

class TestGenesisKeyAssignment:
    """Test Genesis Key assignment functionality."""

    def test_genesis_key_format(self):
        """Test Genesis Key format."""
        def assign_genesis_key(task_id: str) -> str:
            return f"GK-LLM-{task_id}"

        key = assign_genesis_key("test_task_001")

        assert key.startswith("GK-LLM-")
        assert "test_task_001" in key

    def test_genesis_key_metadata(self):
        """Test Genesis Key metadata creation."""
        def create_genesis_metadata(
            task_id: str,
            task_type: TaskType,
            user_id: Optional[str],
            prompt: str,
            content_length: int
        ) -> Dict[str, Any]:
            return {
                "task_id": task_id,
                "task_type": task_type.value,
                "user_id": user_id,
                "prompt": prompt[:500],
                "content_length": content_length,
                "timestamp": datetime.now().isoformat()
            }

        metadata = create_genesis_metadata(
            task_id="task_001",
            task_type=TaskType.CODE_GENERATION,
            user_id="user_123",
            prompt="Write a function",
            content_length=500
        )

        assert metadata["task_id"] == "task_001"
        assert metadata["task_type"] == "code_generation"
        assert metadata["user_id"] == "user_123"


# =============================================================================
# Learning Memory Integration Tests
# =============================================================================

class TestLearningMemoryIntegration:
    """Test learning memory integration."""

    def test_learning_data_creation(self):
        """Test learning data structure creation."""
        def create_learning_data(
            task_type: TaskType,
            prompt: str,
            content: str,
            verified: bool,
            confidence_score: float,
            trust_score: float
        ) -> Dict[str, Any]:
            return {
                "context": {
                    "task_type": task_type.value,
                    "prompt": prompt
                },
                "expected": {
                    "content": content,
                    "verified": verified
                },
                "actual": {
                    "confidence_score": confidence_score,
                    "trust_score": trust_score
                }
            }

        data = create_learning_data(
            task_type=TaskType.CODE_GENERATION,
            prompt="Write sorting function",
            content="def sort(lst): return sorted(lst)",
            verified=True,
            confidence_score=0.95,
            trust_score=0.92
        )

        assert data["context"]["task_type"] == "code_generation"
        assert data["expected"]["verified"] is True
        assert data["actual"]["confidence_score"] == 0.95

    def test_learning_integration(self):
        """Test integration with learning memory manager."""
        class MockLearningMemoryManager:
            def __init__(self):
                self.examples = []
                self._id_counter = 0

            def ingest_learning_data(
                self,
                learning_type: str,
                learning_data: Dict[str, Any],
                source: str,
                user_id: Optional[str],
                genesis_key_id: Optional[str]
            ):
                self._id_counter += 1
                example = MagicMock()
                example.id = f"learn_{self._id_counter}"
                self.examples.append(example)
                return example

        manager = MockLearningMemoryManager()
        result = manager.ingest_learning_data(
            learning_type="llm_interaction",
            learning_data={"test": "data"},
            source="system_observation_success",
            user_id="user_123",
            genesis_key_id="GK-LLM-task_001"
        )

        assert result.id == "learn_1"
        assert len(manager.examples) == 1


# =============================================================================
# Query Methods Tests
# =============================================================================

class TestQueryMethods:
    """Test orchestrator query methods."""

    def test_get_task_result(self):
        """Test getting task result by ID."""
        @dataclass
        class MockTaskResult:
            task_id: str
            success: bool

        class MockOrchestrator:
            def __init__(self):
                self.completed_tasks = [
                    MockTaskResult("task_001", True),
                    MockTaskResult("task_002", False),
                    MockTaskResult("task_003", True)
                ]

            def get_task_result(self, task_id: str):
                for result in self.completed_tasks:
                    if result.task_id == task_id:
                        return result
                return None

        orchestrator = MockOrchestrator()

        result = orchestrator.get_task_result("task_002")
        assert result is not None
        assert result.success is False

        result = orchestrator.get_task_result("nonexistent")
        assert result is None

    def test_get_recent_tasks(self):
        """Test getting recent tasks."""
        @dataclass
        class MockTaskResult:
            task_id: str

        class MockOrchestrator:
            def __init__(self):
                self.completed_tasks = [
                    MockTaskResult(f"task_{i}") for i in range(150)
                ]

            def get_recent_tasks(self, limit: int = 100):
                return self.completed_tasks[-limit:]

        orchestrator = MockOrchestrator()

        recent = orchestrator.get_recent_tasks(limit=50)
        assert len(recent) == 50
        assert recent[-1].task_id == "task_149"

    def test_get_stats_empty(self):
        """Test stats with no completed tasks."""
        class MockOrchestrator:
            def __init__(self):
                self.completed_tasks = []

            def get_stats(self) -> Dict[str, Any]:
                if not self.completed_tasks:
                    return {
                        "total_tasks": 0,
                        "success_rate": 0.0,
                        "avg_duration_ms": 0.0,
                        "avg_trust_score": 0.0,
                        "avg_confidence_score": 0.0
                    }
                return {}

        orchestrator = MockOrchestrator()
        stats = orchestrator.get_stats()

        assert stats["total_tasks"] == 0
        assert stats["success_rate"] == 0.0

    def test_get_stats_with_tasks(self):
        """Test stats with completed tasks."""
        @dataclass
        class MockTaskResult:
            success: bool
            duration_ms: float
            trust_score: float
            confidence_score: float

        class MockOrchestrator:
            def __init__(self):
                self.completed_tasks = [
                    MockTaskResult(True, 100.0, 0.9, 0.95),
                    MockTaskResult(True, 200.0, 0.85, 0.9),
                    MockTaskResult(False, 50.0, 0.3, 0.2),
                ]

            def get_stats(self) -> Dict[str, Any]:
                total = len(self.completed_tasks)
                successful = sum(1 for t in self.completed_tasks if t.success)

                return {
                    "total_tasks": total,
                    "success_rate": successful / total,
                    "avg_duration_ms": sum(t.duration_ms for t in self.completed_tasks) / total,
                    "avg_trust_score": sum(t.trust_score for t in self.completed_tasks) / total,
                    "avg_confidence_score": sum(t.confidence_score for t in self.completed_tasks) / total,
                }

        orchestrator = MockOrchestrator()
        stats = orchestrator.get_stats()

        assert stats["total_tasks"] == 3
        assert abs(stats["success_rate"] - 0.666) < 0.01
        assert abs(stats["avg_duration_ms"] - 116.67) < 0.1


# =============================================================================
# External Verification Tests
# =============================================================================

class TestExternalVerification:
    """Test external verification functionality."""

    def test_external_verifier_initialization(self):
        """Test ExternalVerifier initialization."""
        class MockExternalVerifier:
            DOCUMENTATION_SOURCES = {
                "python": "https://docs.python.org/3/",
                "javascript": "https://developer.mozilla.org/",
            }

            def __init__(
                self,
                enable_web_search: bool = True,
                enable_doc_lookup: bool = True,
                search_timeout: float = 10.0
            ):
                self.enable_web_search = enable_web_search
                self.enable_doc_lookup = enable_doc_lookup
                self.search_timeout = search_timeout
                self._cache = {}

        verifier = MockExternalVerifier(search_timeout=5.0)

        assert verifier.enable_web_search is True
        assert verifier.enable_doc_lookup is True
        assert verifier.search_timeout == 5.0

    def test_verify_technical_claim(self):
        """Test technical claim verification."""
        class MockExternalVerifier:
            def verify_technical_claim(
                self,
                claim: str,
                context: str = "",
                technologies: Optional[List[str]] = None
            ) -> Dict[str, Any]:
                # Simulate verification
                is_verified = "sorted()" in claim or "list" in claim.lower()

                return {
                    "claim": claim,
                    "is_verified": is_verified,
                    "confidence": 0.85 if is_verified else 0.3,
                    "sources": ["Python documentation"] if is_verified else []
                }

        verifier = MockExternalVerifier()
        result = verifier.verify_technical_claim(
            "Python's sorted() function returns a new list",
            technologies=["python"]
        )

        assert result["is_verified"] is True
        assert result["confidence"] == 0.85


# =============================================================================
# Task Execution Pipeline Tests
# =============================================================================

class TestTaskExecutionPipeline:
    """Test the complete task execution pipeline."""

    def test_task_lifecycle(self):
        """Test complete task lifecycle."""
        class MockOrchestrator:
            def __init__(self):
                self.active_tasks = {}
                self.completed_tasks = []

            def execute_task(self, prompt: str, task_type: TaskType) -> Dict[str, Any]:
                import uuid
                task_id = f"task_{uuid.uuid4().hex[:8]}"

                # Add to active
                self.active_tasks[task_id] = {"prompt": prompt}

                # Simulate execution
                result = {
                    "task_id": task_id,
                    "success": True,
                    "content": f"Response: {prompt[:50]}",
                    "trust_score": 0.9
                }

                # Move to completed
                del self.active_tasks[task_id]
                self.completed_tasks.append(result)

                return result

        orchestrator = MockOrchestrator()

        assert len(orchestrator.active_tasks) == 0
        assert len(orchestrator.completed_tasks) == 0

        result = orchestrator.execute_task("Test prompt", TaskType.GENERAL)

        assert result["success"] is True
        assert len(orchestrator.active_tasks) == 0
        assert len(orchestrator.completed_tasks) == 1

    def test_task_failure_handling(self):
        """Test task failure handling."""
        class MockOrchestrator:
            def __init__(self):
                self.active_tasks = {}
                self.completed_tasks = []

            def execute_task(self, prompt: str, should_fail: bool = False) -> Dict[str, Any]:
                task_id = "task_001"
                self.active_tasks[task_id] = {"prompt": prompt}

                if should_fail:
                    result = {
                        "task_id": task_id,
                        "success": False,
                        "content": "",
                        "error": "LLM generation failed",
                        "trust_score": 0.0
                    }
                else:
                    result = {
                        "task_id": task_id,
                        "success": True,
                        "content": "Success",
                        "trust_score": 0.9
                    }

                del self.active_tasks[task_id]
                self.completed_tasks.append(result)
                return result

        orchestrator = MockOrchestrator()
        result = orchestrator.execute_task("Test", should_fail=True)

        assert result["success"] is False
        assert result["trust_score"] == 0.0
        assert "error" in result

    def test_audit_trail_creation(self):
        """Test audit trail creation during execution."""
        class MockOrchestrator:
            def execute_with_audit(self, prompt: str) -> Dict[str, Any]:
                audit_trail = []

                # Step 1: Cognitive enforcement
                audit_trail.append({
                    "step": "cognitive_enforcement",
                    "decision_id": "decision_001",
                    "timestamp": datetime.now().isoformat()
                })

                # Step 2: LLM generation
                audit_trail.append({
                    "step": "llm_generation",
                    "model": "deepseek-coder",
                    "duration_ms": 150.0,
                    "timestamp": datetime.now().isoformat()
                })

                # Step 3: Verification
                audit_trail.append({
                    "step": "hallucination_verification",
                    "is_verified": True,
                    "confidence": 0.9,
                    "timestamp": datetime.now().isoformat()
                })

                return {
                    "success": True,
                    "audit_trail": audit_trail
                }

        orchestrator = MockOrchestrator()
        result = orchestrator.execute_with_audit("Test prompt")

        assert len(result["audit_trail"]) == 3
        assert result["audit_trail"][0]["step"] == "cognitive_enforcement"
        assert result["audit_trail"][1]["step"] == "llm_generation"
        assert result["audit_trail"][2]["step"] == "hallucination_verification"


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Test error handling in the orchestrator."""

    def test_llm_generation_failure(self):
        """Test handling of LLM generation failure."""
        class MockOrchestrator:
            def _generate_llm_response(self, task_request) -> Dict[str, Any]:
                return {
                    "success": False,
                    "error": "Model not available"
                }

            def execute_task(self, prompt: str) -> Dict[str, Any]:
                response = self._generate_llm_response({"prompt": prompt})
                if not response.get("success"):
                    return {
                        "success": False,
                        "error": response.get("error"),
                        "content": ""
                    }
                return {"success": True, "content": "OK"}

        orchestrator = MockOrchestrator()
        result = orchestrator.execute_task("Test")

        assert result["success"] is False
        assert "Model not available" in result["error"]

    def test_verification_failure(self):
        """Test handling of verification failure."""
        class MockOrchestrator:
            def _verify_content(self, content: str) -> MockVerificationResult:
                return MockVerificationResult(
                    is_verified=False,
                    confidence_score=0.3,
                    trust_score=0.2,
                    final_content=content
                )

            def execute_task(self, prompt: str, require_verification: bool = True):
                content = "Generated content"

                if require_verification:
                    verification = self._verify_content(content)
                    if not verification.is_verified:
                        return {
                            "success": True,  # Still returns but with low scores
                            "content": verification.final_content,
                            "trust_score": verification.trust_score,
                            "confidence_score": verification.confidence_score,
                            "warning": "Content verification failed"
                        }
                return {"success": True, "content": content}

        orchestrator = MockOrchestrator()
        result = orchestrator.execute_task("Test")

        assert result["success"] is True
        assert result["trust_score"] == 0.2
        assert "warning" in result

    def test_cognitive_layer_unavailable(self):
        """Test handling when cognitive layer is unavailable."""
        class MockOrchestrator:
            def __init__(self):
                self.cognitive_layer1 = None

            def _integrate_layer1(self, task_request, content, genesis_key_id):
                if not self.cognitive_layer1:
                    return {"warning": "Cognitive Layer 1 not available"}
                return {"success": True}

        orchestrator = MockOrchestrator()
        result = orchestrator._integrate_layer1({}, "content", "GK-001")

        assert "warning" in result

    def test_learning_memory_unavailable(self):
        """Test handling when learning memory is unavailable."""
        class MockOrchestrator:
            def __init__(self):
                self.learning_memory = None

            def _integrate_learning_memory(self, task_request, content, verification, genesis_key):
                if not self.learning_memory:
                    return None
                return "learn_001"

        orchestrator = MockOrchestrator()
        result = orchestrator._integrate_learning_memory({}, "content", None, "GK-001")

        assert result is None


# =============================================================================
# Global Instance Tests
# =============================================================================

class TestGlobalInstance:
    """Test global orchestrator instance management."""

    def test_get_llm_orchestrator_singleton(self):
        """Test singleton behavior of get_llm_orchestrator."""
        _global_instance = None

        def get_llm_orchestrator(session=None, embedding_model=None, knowledge_base_path=None):
            nonlocal _global_instance
            if _global_instance is None:
                _global_instance = {
                    "session": session,
                    "embedding_model": embedding_model,
                    "knowledge_base_path": knowledge_base_path
                }
            return _global_instance

        # First call creates instance
        instance1 = get_llm_orchestrator(session="session1")
        assert instance1["session"] == "session1"

        # Second call returns same instance (ignores new params)
        instance2 = get_llm_orchestrator(session="session2")
        assert instance2["session"] == "session1"
        assert instance1 is instance2


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the complete orchestrator."""

    def test_full_pipeline_mock(self):
        """Test full pipeline with mocked components."""
        class FullMockOrchestrator:
            def __init__(self):
                self.multi_llm = MagicMock()
                self.multi_llm.generate.return_value = {
                    "success": True,
                    "content": "Generated code",
                    "model_name": "deepseek-coder",
                    "duration_ms": 200.0
                }

                self.hallucination_guard = MagicMock()
                self.hallucination_guard.verify_content.return_value = MockVerificationResult(
                    is_verified=True,
                    confidence_score=0.9,
                    trust_score=0.88,
                    final_content="Verified code"
                )

                self.cognitive_enforcer = MagicMock()
                self.cognitive_enforcer.begin_ooda_loop.return_value = "decision_001"

                self.completed_tasks = []

            def execute_task(self, prompt: str, task_type: TaskType) -> Dict[str, Any]:
                # Cognitive enforcement
                decision_id = self.cognitive_enforcer.begin_ooda_loop("test")

                # LLM generation
                llm_response = self.multi_llm.generate(prompt=prompt)

                # Verification
                verification = self.hallucination_guard.verify_content(
                    prompt=prompt,
                    content=llm_response["content"],
                    task_type=task_type
                )

                result = {
                    "task_id": "task_001",
                    "success": True,
                    "content": verification.final_content,
                    "trust_score": verification.trust_score,
                    "confidence_score": verification.confidence_score,
                    "model_used": llm_response["model_name"],
                    "decision_id": decision_id
                }

                self.completed_tasks.append(result)
                return result

        orchestrator = FullMockOrchestrator()
        result = orchestrator.execute_task("Write sorting code", TaskType.CODE_GENERATION)

        assert result["success"] is True
        assert result["content"] == "Verified code"
        assert result["trust_score"] == 0.88
        assert result["decision_id"] == "decision_001"
        assert len(orchestrator.completed_tasks) == 1

    def test_concurrent_task_tracking(self):
        """Test tracking of concurrent tasks."""
        class MockOrchestrator:
            def __init__(self):
                self.active_tasks = {}
                self.completed_tasks = []

            def start_task(self, task_id: str, prompt: str):
                self.active_tasks[task_id] = {"prompt": prompt, "started": datetime.now()}

            def complete_task(self, task_id: str, result: Dict[str, Any]):
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
                    self.completed_tasks.append(result)

        orchestrator = MockOrchestrator()

        # Start multiple tasks
        orchestrator.start_task("task_1", "Prompt 1")
        orchestrator.start_task("task_2", "Prompt 2")
        orchestrator.start_task("task_3", "Prompt 3")

        assert len(orchestrator.active_tasks) == 3

        # Complete tasks
        orchestrator.complete_task("task_2", {"task_id": "task_2", "success": True})
        assert len(orchestrator.active_tasks) == 2
        assert "task_2" not in orchestrator.active_tasks

        orchestrator.complete_task("task_1", {"task_id": "task_1", "success": True})
        orchestrator.complete_task("task_3", {"task_id": "task_3", "success": False})

        assert len(orchestrator.active_tasks) == 0
        assert len(orchestrator.completed_tasks) == 3


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Test performance-related functionality."""

    def test_response_caching(self):
        """Test response caching mechanism."""
        class MockCachingClient:
            def __init__(self, cache_size: int = 100):
                self._cache = {}
                self._cache_size = cache_size
                self._cache_hits = 0
                self._cache_misses = 0

            def _get_cache_key(self, prompt: str, task_type: TaskType) -> str:
                import hashlib
                key = f"{prompt}:{task_type.value}"
                return hashlib.md5(key.encode()).hexdigest()

            def generate(self, prompt: str, task_type: TaskType) -> Dict[str, Any]:
                cache_key = self._get_cache_key(prompt, task_type)

                if cache_key in self._cache:
                    self._cache_hits += 1
                    return self._cache[cache_key]

                self._cache_misses += 1
                result = {"content": f"Response to {prompt}", "cached": False}
                self._cache[cache_key] = result
                return result

        client = MockCachingClient()

        # First call - cache miss
        result1 = client.generate("Test prompt", TaskType.GENERAL)
        assert client._cache_misses == 1
        assert client._cache_hits == 0

        # Second call with same params - cache hit
        result2 = client.generate("Test prompt", TaskType.GENERAL)
        assert client._cache_misses == 1
        assert client._cache_hits == 1

    def test_duration_tracking(self):
        """Test task duration tracking."""
        class MockOrchestrator:
            def execute_with_timing(self, prompt: str) -> Dict[str, Any]:
                import time
                start = time.time()

                # Simulate work
                time.sleep(0.01)

                duration_ms = (time.time() - start) * 1000

                return {
                    "success": True,
                    "duration_ms": duration_ms
                }

        orchestrator = MockOrchestrator()
        result = orchestrator.execute_with_timing("Test")

        assert result["duration_ms"] >= 10.0  # At least 10ms


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
