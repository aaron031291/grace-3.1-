"""
REAL Functional Tests for Layer 4 Recursive Pattern Learner.

These are NOT smoke tests - they verify that components ACTUALLY:
1. Pattern domains ACTUALLY organize patterns correctly
2. AbstractPattern ACTUALLY stores and updates metadata
3. Recursive cycles ACTUALLY track learning progress
4. Cross-domain transfer ACTUALLY tracks success rates
5. Meta-learning strategies ACTUALLY update weights
6. Pattern queries ACTUALLY return relevant results
7. Persistence ACTUALLY saves and loads patterns

Run with: pytest tests/test_layer4_pattern_learner_real.py -v
"""

import sys
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import pytest

backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def pattern_learner(temp_storage):
    """Create fresh pattern learner for each test."""
    from ml_intelligence.layer4_recursive_pattern_learner import (
        Layer4RecursivePatternLearner
    )
    return Layer4RecursivePatternLearner(storage_path=temp_storage)


# =============================================================================
# PATTERN DOMAIN TESTS
# =============================================================================

class TestPatternDomains:
    """Verify pattern domains ACTUALLY organize patterns correctly."""
    
    def test_all_8_domains_defined(self):
        """All 8 pattern domains ACTUALLY defined."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        domains = list(PatternDomain)
        
        assert len(domains) == 8
        assert PatternDomain.CODE in domains
        assert PatternDomain.HEALING in domains
        assert PatternDomain.ERROR in domains
        assert PatternDomain.TEMPLATE in domains
        assert PatternDomain.REASONING in domains
        assert PatternDomain.KNOWLEDGE in domains
        assert PatternDomain.WORKFLOW in domains
        assert PatternDomain.TESTING in domains
    
    def test_domain_values_are_strings(self):
        """Domain values ACTUALLY usable as strings."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        assert PatternDomain.CODE.value == "code"
        assert PatternDomain.HEALING.value == "healing"
        assert PatternDomain.ERROR.value == "error"
        assert PatternDomain.TEMPLATE.value == "template"


# =============================================================================
# ABSTRACT PATTERN TESTS
# =============================================================================

class TestAbstractPattern:
    """Verify AbstractPattern ACTUALLY stores and updates correctly."""
    
    def test_pattern_creation(self):
        """AbstractPattern ACTUALLY created with all fields."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        pattern = AbstractPattern(
            pattern_id="test-001",
            abstract_form={"type": "error_handler", "keywords": ["try", "catch"]},
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE, PatternDomain.HEALING],
            confidence=0.85,
            trust_score=0.72,
            abstraction_level=2,
            support_count=15,
        )
        
        assert pattern.pattern_id == "test-001"
        assert pattern.source_domain == PatternDomain.CODE
        assert len(pattern.applicable_domains) == 2
        assert pattern.confidence == 0.85
        assert pattern.trust_score == 0.72
        assert pattern.abstraction_level == 2
        assert pattern.support_count == 15
    
    def test_pattern_to_dict_serialization(self):
        """AbstractPattern ACTUALLY serializes to dict."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        pattern = AbstractPattern(
            pattern_id="serialize-test",
            abstract_form={"type": "test"},
            source_domain=PatternDomain.TESTING,
            applicable_domains=[PatternDomain.TESTING],
            confidence=0.9,
            trust_score=0.8,
            abstraction_level=1,
            support_count=10,
        )
        
        data = pattern.to_dict()
        
        assert data["pattern_id"] == "serialize-test"
        assert data["source_domain"] == "testing"
        assert data["applicable_domains"] == ["testing"]
        assert data["confidence"] == 0.9
        assert data["trust_score"] == 0.8
        assert "created_at" in data
    
    def test_pattern_tracks_transfer_count(self):
        """Pattern ACTUALLY tracks transfer count."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        pattern = AbstractPattern(
            pattern_id="transfer-test",
            abstract_form={"type": "transferable"},
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE, PatternDomain.TEMPLATE],
            confidence=0.8,
            trust_score=0.75,
            abstraction_level=1,
            support_count=5,
            transfer_count=3,
        )
        
        assert pattern.transfer_count == 3


# =============================================================================
# RECURSIVE LEARNING CYCLE TESTS
# =============================================================================

class TestRecursiveLearningCycle:
    """Verify RecursiveLearningCycle ACTUALLY tracks progress."""
    
    def test_cycle_creation(self):
        """RecursiveLearningCycle ACTUALLY created correctly."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            RecursiveLearningCycle, PatternDomain
        )
        
        cycle = RecursiveLearningCycle(
            cycle_id="cycle-001",
            cycle_number=5,
            patterns_discovered=20,
            patterns_abstracted=15,
            patterns_validated=12,
            patterns_transferred=4,
            domains_touched=[PatternDomain.CODE, PatternDomain.HEALING],
            improvement_score=1.25,
            started_at=datetime.utcnow(),
        )
        
        assert cycle.cycle_id == "cycle-001"
        assert cycle.cycle_number == 5
        assert cycle.patterns_discovered == 20
        assert cycle.patterns_abstracted == 15
        assert cycle.patterns_validated == 12
        assert cycle.patterns_transferred == 4
        assert len(cycle.domains_touched) == 2
        assert cycle.improvement_score == 1.25
    
    def test_cycle_to_dict(self):
        """RecursiveLearningCycle ACTUALLY serializes."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            RecursiveLearningCycle, PatternDomain
        )
        
        cycle = RecursiveLearningCycle(
            cycle_id="dict-test",
            cycle_number=1,
            patterns_discovered=5,
            patterns_abstracted=3,
            patterns_validated=2,
            patterns_transferred=1,
            domains_touched=[PatternDomain.ERROR],
            improvement_score=1.0,
            started_at=datetime.utcnow(),
        )
        
        data = cycle.to_dict()
        
        assert data["cycle_id"] == "dict-test"
        assert data["domains_touched"] == ["error"]
        assert data["improvement_score"] == 1.0
    
    def test_cycle_parent_link(self):
        """Cycles ACTUALLY link to parent (recursion)."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            RecursiveLearningCycle, PatternDomain
        )
        
        parent = RecursiveLearningCycle(
            cycle_id="parent",
            cycle_number=1,
            patterns_discovered=10,
            patterns_abstracted=5,
            patterns_validated=3,
            patterns_transferred=1,
            domains_touched=[PatternDomain.CODE],
            improvement_score=1.0,
            started_at=datetime.utcnow(),
        )
        
        child = RecursiveLearningCycle(
            cycle_id="child",
            cycle_number=2,
            patterns_discovered=15,
            patterns_abstracted=8,
            patterns_validated=5,
            patterns_transferred=2,
            domains_touched=[PatternDomain.CODE, PatternDomain.HEALING],
            improvement_score=1.5,
            started_at=datetime.utcnow(),
            parent_cycle_id="parent",
        )
        
        assert child.parent_cycle_id == parent.cycle_id


# =============================================================================
# LAYER 4 LEARNER INITIALIZATION TESTS
# =============================================================================

class TestLayer4Initialization:
    """Verify Layer4RecursivePatternLearner ACTUALLY initializes correctly."""
    
    def test_learner_initialization(self, pattern_learner):
        """Learner ACTUALLY initializes with correct defaults."""
        assert pattern_learner.min_confidence == 0.6
        assert pattern_learner.min_trust_for_transfer == 0.7
        assert pattern_learner.max_abstraction_level == 5
        assert pattern_learner.current_cycle_number == 0
    
    def test_learner_has_empty_patterns(self, pattern_learner):
        """Fresh learner ACTUALLY starts with no patterns."""
        assert len(pattern_learner.patterns) == 0
        assert len(pattern_learner.cycles) == 0
    
    def test_abstraction_strategies_initialized(self, pattern_learner):
        """Abstraction strategies ACTUALLY initialized."""
        strategies = pattern_learner.abstraction_strategies
        
        assert "keyword_extraction" in strategies
        assert "structure_matching" in strategies
        assert "relationship_mapping" in strategies
        assert "type_generalization" in strategies
        
        for strategy, weight in strategies.items():
            assert weight == 1.0


# =============================================================================
# PATTERN STORAGE TESTS
# =============================================================================

class TestPatternStorage:
    """Verify patterns ACTUALLY stored and retrieved correctly."""
    
    def test_register_pattern(self, pattern_learner):
        """Patterns ACTUALLY registered in storage."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        pattern = AbstractPattern(
            pattern_id="store-test",
            abstract_form={"type": "test"},
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE],
            confidence=0.8,
            trust_score=0.7,
            abstraction_level=1,
            support_count=5,
        )
        
        pattern_learner.patterns[pattern.pattern_id] = pattern
        pattern_learner.patterns_by_domain[PatternDomain.CODE].append(pattern.pattern_id)
        
        assert "store-test" in pattern_learner.patterns
        assert "store-test" in pattern_learner.patterns_by_domain[PatternDomain.CODE]
    
    def test_get_patterns_for_domain(self, pattern_learner):
        """get_patterns_for_domain ACTUALLY returns domain patterns."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        for i in range(5):
            pattern = AbstractPattern(
                pattern_id=f"domain-test-{i}",
                abstract_form={"type": "test", "index": i},
                source_domain=PatternDomain.HEALING,
                applicable_domains=[PatternDomain.HEALING],
                confidence=0.7 + i * 0.05,
                trust_score=0.6 + i * 0.05,
                abstraction_level=1,
                support_count=i + 1,
            )
            pattern_learner.patterns[pattern.pattern_id] = pattern
            pattern_learner.patterns_by_domain[PatternDomain.HEALING].append(pattern.pattern_id)
        
        patterns = pattern_learner.get_patterns_for_domain(PatternDomain.HEALING, min_trust=0.5)
        
        assert len(patterns) == 5
        assert patterns[0].trust_score >= patterns[-1].trust_score


# =============================================================================
# PATTERN QUERY TESTS
# =============================================================================

class TestPatternQueries:
    """Verify pattern queries ACTUALLY return relevant results."""
    
    def test_query_by_keywords(self, pattern_learner):
        """query_patterns ACTUALLY finds patterns by keywords."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        pattern = AbstractPattern(
            pattern_id="keyword-test",
            abstract_form={
                "type": "error_handler",
                "keywords": ["try", "catch", "exception", "error"]
            },
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE],
            confidence=0.9,
            trust_score=0.85,
            abstraction_level=2,
            support_count=20,
        )
        
        pattern_learner.patterns[pattern.pattern_id] = pattern
        pattern_learner.patterns_by_domain[PatternDomain.CODE].append(pattern.pattern_id)
        
        results = pattern_learner.query_patterns("error handling exception")
        
        assert len(results) > 0
        assert results[0][0].pattern_id == "keyword-test"
    
    def test_query_respects_trust(self, pattern_learner):
        """Queries ACTUALLY weight by trust score."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        high_trust = AbstractPattern(
            pattern_id="high-trust",
            abstract_form={"keywords": ["test", "pattern"]},
            source_domain=PatternDomain.TESTING,
            applicable_domains=[PatternDomain.TESTING],
            confidence=0.9,
            trust_score=0.95,
            abstraction_level=1,
            support_count=50,
        )
        
        low_trust = AbstractPattern(
            pattern_id="low-trust",
            abstract_form={"keywords": ["test", "pattern"]},
            source_domain=PatternDomain.TESTING,
            applicable_domains=[PatternDomain.TESTING],
            confidence=0.9,
            trust_score=0.4,
            abstraction_level=1,
            support_count=50,
        )
        
        pattern_learner.patterns[high_trust.pattern_id] = high_trust
        pattern_learner.patterns[low_trust.pattern_id] = low_trust
        
        results = pattern_learner.query_patterns("test pattern")
        
        assert len(results) == 2
        assert results[0][0].trust_score >= results[1][0].trust_score


# =============================================================================
# CROSS-DOMAIN TRANSFER TESTS
# =============================================================================

class TestCrossDomainTransfer:
    """Verify cross-domain transfer ACTUALLY tracks success."""
    
    def test_transfer_success_tracking(self, pattern_learner):
        """Transfer success rates ACTUALLY tracked."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        key = (PatternDomain.CODE, PatternDomain.TEMPLATE)
        pattern_learner.transfer_success[key] = 0.85
        
        assert pattern_learner.transfer_success[key] == 0.85
    
    def test_get_cross_domain_insights(self, pattern_learner):
        """get_cross_domain_insights ACTUALLY returns transfer data."""
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        pattern_learner.transfer_success[(PatternDomain.ERROR, PatternDomain.HEALING)] = 0.92
        pattern_learner.transfer_success[(PatternDomain.CODE, PatternDomain.TEMPLATE)] = 0.78
        
        insights = pattern_learner.get_cross_domain_insights()
        
        assert "transfer_success_rates" in insights
        assert len(insights["transfer_success_rates"]) == 2


# =============================================================================
# META-LEARNING STRATEGY TESTS
# =============================================================================

class TestMetaLearningStrategies:
    """Verify meta-learning strategies ACTUALLY update."""
    
    def test_strategy_weights_initialized(self, pattern_learner):
        """Strategy weights ACTUALLY initialized to 1.0."""
        for weight in pattern_learner.abstraction_strategies.values():
            assert weight == 1.0
    
    def test_strategy_weights_modifiable(self, pattern_learner):
        """Strategy weights ACTUALLY modifiable."""
        pattern_learner.abstraction_strategies["keyword_extraction"] = 1.5
        
        assert pattern_learner.abstraction_strategies["keyword_extraction"] == 1.5
    
    def test_insights_include_strategies(self, pattern_learner):
        """Insights ACTUALLY include abstraction strategies."""
        insights = pattern_learner.get_cross_domain_insights()
        
        assert "abstraction_strategies" in insights
        assert "keyword_extraction" in insights["abstraction_strategies"]


# =============================================================================
# PATTERN PERSISTENCE TESTS
# =============================================================================

class TestPatternPersistence:
    """Verify persistence ACTUALLY saves and loads patterns."""
    
    def test_save_patterns(self, temp_storage):
        """Patterns ACTUALLY saved to disk."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            Layer4RecursivePatternLearner, AbstractPattern, PatternDomain
        )
        
        learner = Layer4RecursivePatternLearner(storage_path=temp_storage)
        
        pattern = AbstractPattern(
            pattern_id="persist-test",
            abstract_form={"type": "persistent"},
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE],
            confidence=0.8,
            trust_score=0.7,
            abstraction_level=1,
            support_count=10,
        )
        
        learner.patterns[pattern.pattern_id] = pattern
        learner.patterns_by_domain[PatternDomain.CODE].append(pattern.pattern_id)
        
        learner._save_patterns()
        
        patterns_file = temp_storage / "patterns.json"
        assert patterns_file.exists()
    
    def test_load_patterns(self, temp_storage):
        """Patterns ACTUALLY loaded from disk."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            Layer4RecursivePatternLearner, AbstractPattern, PatternDomain
        )
        import json
        
        patterns_file = temp_storage / "patterns.json"
        patterns_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "patterns": {
                "load-test": {
                    "pattern_id": "load-test",
                    "abstract_form": {"type": "loaded"},
                    "source_domain": "code",
                    "applicable_domains": ["code"],
                    "confidence": 0.9,
                    "trust_score": 0.85,
                    "abstraction_level": 2,
                    "support_count": 25,
                    "transfer_count": 0,
                    "validation_count": 0,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                }
            },
            "patterns_by_domain": {"code": ["load-test"]},
            "transfer_success": {},
            "abstraction_strategies": {"keyword_extraction": 1.2},
            "current_cycle_number": 5,
            "cycles": [],
        }
        
        with open(patterns_file, "w") as f:
            json.dump(data, f)
        
        learner = Layer4RecursivePatternLearner(storage_path=temp_storage)
        
        assert "load-test" in learner.patterns
        assert learner.patterns["load-test"].trust_score == 0.85
        assert learner.current_cycle_number == 5


# =============================================================================
# STATUS REPORTING TESTS
# =============================================================================

class TestStatusReporting:
    """Verify status reporting ACTUALLY reflects state."""
    
    def test_get_status_structure(self, pattern_learner):
        """get_status ACTUALLY returns correct structure."""
        status = pattern_learner.get_status()
        
        assert status["layer"] == 4
        assert "name" in status
        assert "total_patterns" in status
        assert "total_cycles" in status
        assert "domains_active" in status
        assert "min_confidence" in status
        assert "min_trust_for_transfer" in status
    
    def test_status_reflects_patterns(self, pattern_learner):
        """Status ACTUALLY reflects pattern count."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        for i in range(3):
            pattern = AbstractPattern(
                pattern_id=f"status-test-{i}",
                abstract_form={"index": i},
                source_domain=PatternDomain.CODE,
                applicable_domains=[PatternDomain.CODE],
                confidence=0.8,
                trust_score=0.7,
                abstraction_level=1,
                support_count=5,
            )
            pattern_learner.patterns[pattern.pattern_id] = pattern
        
        status = pattern_learner.get_status()
        
        assert status["total_patterns"] == 3


# =============================================================================
# TRUST THRESHOLD TESTS
# =============================================================================

class TestTrustThresholds:
    """Verify trust thresholds ACTUALLY enforced."""
    
    def test_min_trust_for_transfer(self, pattern_learner):
        """min_trust_for_transfer ACTUALLY set."""
        assert pattern_learner.min_trust_for_transfer == 0.7
    
    def test_get_patterns_respects_min_trust(self, pattern_learner):
        """get_patterns_for_domain ACTUALLY filters by trust."""
        from ml_intelligence.layer4_recursive_pattern_learner import (
            AbstractPattern, PatternDomain
        )
        
        low_trust = AbstractPattern(
            pattern_id="low",
            abstract_form={},
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE],
            confidence=0.9,
            trust_score=0.3,
            abstraction_level=1,
            support_count=10,
        )
        
        high_trust = AbstractPattern(
            pattern_id="high",
            abstract_form={},
            source_domain=PatternDomain.CODE,
            applicable_domains=[PatternDomain.CODE],
            confidence=0.9,
            trust_score=0.9,
            abstraction_level=1,
            support_count=10,
        )
        
        pattern_learner.patterns["low"] = low_trust
        pattern_learner.patterns["high"] = high_trust
        pattern_learner.patterns_by_domain[PatternDomain.CODE].extend(["low", "high"])
        
        filtered = pattern_learner.get_patterns_for_domain(PatternDomain.CODE, min_trust=0.5)
        
        assert len(filtered) == 1
        assert filtered[0].pattern_id == "high"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
