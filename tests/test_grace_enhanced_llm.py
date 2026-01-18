"""
Tests for Grace-Enhanced LLM System

Tests:
1. Basic code generation
2. Genesis Key tracking
3. Memory Mesh context enhancement
4. Trust scoring
5. Anti-hallucination
6. Fine-tuning log collection
7. Multiple problem types
"""

import pytest
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestGraceEnhancedLLM:
    """Tests for GraceEnhancedLLM class."""
    
    @pytest.fixture
    def llm(self):
        """Create a Grace-Enhanced LLM instance."""
        from backend.llm_orchestrator.grace_enhanced_llm import GraceEnhancedLLM
        
        with tempfile.TemporaryDirectory() as tmpdir:
            llm = GraceEnhancedLLM(
                session=None,
                model_name="deepseek-coder-v2:16b",
                enable_genesis=False,  # Disable for testing without DB
                enable_memory=False,
                enable_anti_hallucination=False,
                enable_finetuning_log=True,
                finetuning_log_path=tmpdir
            )
            yield llm
    
    @pytest.fixture
    def llm_with_mock_ollama(self):
        """Create LLM with mocked Ollama."""
        from backend.llm_orchestrator.grace_enhanced_llm import GraceEnhancedLLM
        
        with tempfile.TemporaryDirectory() as tmpdir:
            llm = GraceEnhancedLLM(
                session=None,
                model_name="test-model",
                enable_genesis=False,
                enable_memory=False,
                enable_anti_hallucination=False,
                enable_finetuning_log=True,
                finetuning_log_path=tmpdir
            )
            yield llm
    
    def test_init(self, llm):
        """Test LLM initialization."""
        assert llm is not None
        assert llm.model_name == "deepseek-coder-v2:16b"
        assert llm.stats["total_generations"] == 0
    
    def test_grace_system_prompt_exists(self, llm):
        """Test that Grace system prompt is defined."""
        assert llm.GRACE_SYSTEM_PROMPT is not None
        assert "OODA" in llm.GRACE_SYSTEM_PROMPT
        assert "Deterministic" in llm.GRACE_SYSTEM_PROMPT
        assert "Trust" in llm.GRACE_SYSTEM_PROMPT
    
    def test_enhance_context(self, llm):
        """Test context enhancement."""
        prompt = "Write a function to find the maximum element in a list"
        
        enhanced = llm.enhance_context(prompt, task_type="code_generation")
        
        assert enhanced.original_prompt == prompt
        assert enhanced.system_prompt == llm.GRACE_SYSTEM_PROMPT
        assert "Complete and executable" in enhanced.trust_context
    
    def test_enhanced_prompt_structure(self, llm):
        """Test that enhanced prompt has correct structure."""
        prompt = "Write a factorial function"
        
        enhanced = llm.enhance_context(prompt, task_type="code_generation")
        full_prompt = enhanced.full_enhanced_prompt
        
        assert llm.GRACE_SYSTEM_PROMPT in full_prompt
        assert prompt in full_prompt
        assert "Task:" in full_prompt
    
    def test_extract_code_from_markdown(self, llm):
        """Test code extraction from markdown blocks."""
        text = '''Here is the code:
```python
def add(a, b):
    return a + b
```
'''
        code = llm._extract_code(text)
        
        assert "def add(a, b):" in code
        assert "return a + b" in code
    
    def test_extract_code_direct_function(self, llm):
        """Test code extraction when function is direct."""
        text = '''def multiply(x, y):
    return x * y
'''
        code = llm._extract_code(text)
        
        assert "def multiply(x, y):" in code
        assert "return x * y" in code
    
    def test_calculate_trust_score_valid_code(self, llm):
        """Test trust score for valid code."""
        code = '''def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
'''
        score = llm._calculate_trust_score("factorial", code, "code_generation")
        
        assert score >= 0.7  # Valid code should have high trust
    
    def test_calculate_trust_score_empty(self, llm):
        """Test trust score for empty output."""
        score = llm._calculate_trust_score("test", "", "code_generation")
        
        assert score == 0.0
    
    def test_calculate_trust_score_placeholder(self, llm):
        """Test trust score for code with placeholder."""
        code = '''def incomplete():
    # TODO: implement this
    pass
'''
        score = llm._calculate_trust_score("test", code, "code_generation")
        
        # Placeholder code should have lower trust than complete code (0.9+)
        # but still passes syntax check, so gets ~0.8
        assert score <= 0.8  # Placeholder code should have lower trust
    
    def test_stats_tracking(self, llm):
        """Test statistics tracking."""
        initial_stats = llm.get_stats()
        
        assert "total_generations" in initial_stats
        assert "successful_generations" in initial_stats
        assert "avg_trust_score" in initial_stats
        assert "success_rate" in initial_stats
        assert initial_stats["total_generations"] == 0
    
    def test_context_sources_extraction(self, llm):
        """Test extraction of context sources."""
        from backend.llm_orchestrator.grace_enhanced_llm import EnhancedContext
        
        enhanced = EnhancedContext(
            original_prompt="test",
            system_prompt="system",
            memory_context="memory",
            episodic_context="",
            procedural_hints="hints",
            trust_context=""
        )
        
        sources = llm._get_context_sources(enhanced)
        
        assert "grace_system_prompt" in sources
        assert "memory_mesh" in sources
        assert "procedural_patterns" in sources


class TestGraceEnhancedLLMIntegration:
    """Integration tests that require Ollama."""
    
    @pytest.fixture
    def llm_real(self):
        """Create LLM with real Ollama connection."""
        from backend.llm_orchestrator.grace_enhanced_llm import get_grace_enhanced_llm
        return get_grace_enhanced_llm(model_name="deepseek-coder-v2:16b")
    
    @pytest.mark.integration
    def test_generate_code_is_prime(self, llm_real):
        """Test generating is_prime function."""
        code = llm_real.generate_code(
            problem="Write a function to check if a number is prime",
            function_name="is_prime",
            test_cases=["assert is_prime(7) == True", "assert is_prime(4) == False"]
        )
        
        assert code is not None
        assert "def is_prime" in code
        assert "return" in code
    
    @pytest.mark.integration
    def test_generate_code_factorial(self, llm_real):
        """Test generating factorial function."""
        code = llm_real.generate_code(
            problem="Write a function to calculate factorial of n",
            function_name="factorial",
            test_cases=["assert factorial(5) == 120"]
        )
        
        assert code is not None
        assert "def factorial" in code
    
    @pytest.mark.integration
    def test_generate_code_list_sum(self, llm_real):
        """Test generating list sum function."""
        code = llm_real.generate_code(
            problem="Write a function to find the sum of all elements in a list",
            function_name="list_sum",
            test_cases=["assert list_sum([1,2,3]) == 6"]
        )
        
        assert code is not None
        assert "def list_sum" in code
    
    @pytest.mark.integration
    def test_generate_with_tracking(self, llm_real):
        """Test full generation with tracking."""
        result = llm_real.generate(
            prompt="Write a function to reverse a string",
            task_type="code_generation",
            max_tokens=200
        )
        
        assert "content" in result
        assert "trust_score" in result
        assert "generation_time_ms" in result
        assert result["enhanced"] == True
    
    @pytest.mark.integration
    def test_stats_after_generation(self, llm_real):
        """Test stats are updated after generation."""
        initial_count = llm_real.stats["total_generations"]
        
        llm_real.generate_code(
            problem="Write a function to add two numbers",
            function_name="add"
        )
        
        assert llm_real.stats["total_generations"] == initial_count + 1


class TestEnhancedContext:
    """Tests for EnhancedContext dataclass."""
    
    def test_full_enhanced_prompt(self):
        """Test full enhanced prompt building."""
        from backend.llm_orchestrator.grace_enhanced_llm import EnhancedContext
        
        context = EnhancedContext(
            original_prompt="Write hello world",
            system_prompt="You are helpful",
            memory_context="Previous: hello example",
            episodic_context="Past: worked well",
            procedural_hints="Pattern: print statement",
            trust_context="Be accurate"
        )
        
        full = context.full_enhanced_prompt
        
        assert "You are helpful" in full
        assert "Relevant Knowledge:" in full
        assert "Past Experiences:" in full
        assert "Known Patterns:" in full
        assert "Trust Guidelines:" in full
        assert "Write hello world" in full


class TestLLMGenerationRecord:
    """Tests for LLMGenerationRecord dataclass."""
    
    def test_record_creation(self):
        """Test creating a generation record."""
        from backend.llm_orchestrator.grace_enhanced_llm import LLMGenerationRecord
        
        record = LLMGenerationRecord(
            record_id="test123",
            genesis_key_id="genesis123",
            timestamp=datetime.now(),
            prompt="test prompt",
            enhanced_prompt="enhanced test",
            context_sources=["memory"],
            raw_output="raw",
            cleaned_output="clean",
            output_type="code",
            trust_score=0.9,
            hallucination_score=0.1,
            verification_passed=True,
            model_name="test-model",
            temperature=0.1,
            tokens_in=100,
            tokens_out=50,
            generation_time_ms=1000.0
        )
        
        assert record.record_id == "test123"
        assert record.trust_score == 0.9
        assert record.is_good_example == False  # Default
    
    def test_record_good_example(self):
        """Test marking record as good example."""
        from backend.llm_orchestrator.grace_enhanced_llm import LLMGenerationRecord
        
        record = LLMGenerationRecord(
            record_id="good123",
            genesis_key_id="genesis",
            timestamp=datetime.now(),
            prompt="test",
            enhanced_prompt="enhanced",
            context_sources=[],
            raw_output="raw",
            cleaned_output="clean",
            output_type="code",
            trust_score=0.95,
            hallucination_score=0.0,
            verification_passed=True,
            model_name="model",
            temperature=0.1,
            tokens_in=50,
            tokens_out=100,
            generation_time_ms=500.0,
            is_good_example=True
        )
        
        assert record.is_good_example == True


class TestFineTuningLogging:
    """Tests for fine-tuning log functionality."""
    
    def test_finetuning_log_created(self):
        """Test that fine-tuning log is created."""
        from backend.llm_orchestrator.grace_enhanced_llm import GraceEnhancedLLM
        
        with tempfile.TemporaryDirectory() as tmpdir:
            llm = GraceEnhancedLLM(
                session=None,
                model_name="test",
                enable_genesis=False,
                enable_memory=False,
                enable_finetuning_log=True,
                finetuning_log_path=tmpdir
            )
            
            assert llm.finetuning_log_path.exists()
    
    def test_finetuning_log_path(self):
        """Test custom fine-tuning log path."""
        from backend.llm_orchestrator.grace_enhanced_llm import GraceEnhancedLLM
        
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "custom_logs"
            
            llm = GraceEnhancedLLM(
                session=None,
                model_name="test",
                enable_finetuning_log=True,
                finetuning_log_path=str(custom_path)
            )
            
            assert llm.finetuning_log_path == custom_path
            assert custom_path.exists()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x", "--tb=short"])
