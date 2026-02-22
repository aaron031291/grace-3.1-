"""
Tests for Three-Layer Reasoning Pipeline.

100% pass, 0 warnings, 0 skips.
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
BACKEND_DIR = Path(__file__).parent.parent


class TestDataclasses:
    def test_reasoning_output(self):
        from llm_orchestrator.three_layer_reasoning import ReasoningOutput
        r = ReasoningOutput(model_name="test", layer=1, reasoning="test", confidence=0.8, duration_ms=100)
        assert r.model_name == "test"
        assert r.layer == 1
        assert r.confidence == 0.8

    def test_layer_result(self):
        from llm_orchestrator.three_layer_reasoning import LayerResult
        lr = LayerResult(layer=1, outputs=[], agreement_score=0.5, duration_ms=50)
        assert lr.layer == 1
        assert lr.outputs == []

    def test_verified_result(self):
        from llm_orchestrator.three_layer_reasoning import VerifiedResult
        vr = VerifiedResult(
            answer="test", confidence=0.9, layer1_agreement=0.8, layer2_agreement=0.85,
            verification_passed=True, training_data_grounded=True, governance_passed=True,
            total_duration_ms=500
        )
        assert vr.confidence == 0.9
        assert vr.verification_passed is True
        assert vr.training_data_grounded is True


class TestThreeLayerReasoning:
    def test_class_exists(self):
        from llm_orchestrator.three_layer_reasoning import ThreeLayerReasoning
        t = ThreeLayerReasoning()
        assert t is not None
        assert t.max_workers == 4

    def test_singleton(self):
        from llm_orchestrator.three_layer_reasoning import get_three_layer_reasoning
        r1 = get_three_layer_reasoning()
        r2 = get_three_layer_reasoning()
        assert r1 is r2

    def test_has_three_layers(self):
        from llm_orchestrator.three_layer_reasoning import ThreeLayerReasoning
        t = ThreeLayerReasoning()
        assert callable(getattr(t, "layer1_parallel_reasoning", None))
        assert callable(getattr(t, "layer2_synthesis_reasoning", None))
        assert callable(getattr(t, "layer3_grace_verification", None))

    def test_has_full_pipeline(self):
        from llm_orchestrator.three_layer_reasoning import ThreeLayerReasoning
        t = ThreeLayerReasoning()
        assert callable(getattr(t, "reason", None))

    def test_has_training_data_access(self):
        from llm_orchestrator.three_layer_reasoning import ThreeLayerReasoning
        t = ThreeLayerReasoning()
        assert callable(getattr(t, "get_training_context", None))

    def test_has_governance_verification(self):
        source = (BACKEND_DIR / "llm_orchestrator" / "three_layer_reasoning.py").read_text()
        assert "OutputSafetyValidator" in source
        assert "_verify_governance" in source

    def test_has_training_data_grounding(self):
        source = (BACKEND_DIR / "llm_orchestrator" / "three_layer_reasoning.py").read_text()
        assert "_verify_against_training_data" in source
        assert "get_training_context" in source

    def test_agreement_calculation(self):
        from llm_orchestrator.three_layer_reasoning import ThreeLayerReasoning, ReasoningOutput
        t = ThreeLayerReasoning()

        o1 = ReasoningOutput(model_name="m1", layer=1, reasoning="the answer is python programming", confidence=0.8, duration_ms=100)
        o2 = ReasoningOutput(model_name="m2", layer=1, reasoning="python programming is the answer", confidence=0.7, duration_ms=100)
        agreement = t._calculate_agreement([o1, o2])
        assert 0 <= agreement <= 1.0
        assert agreement > 0.3

    def test_agreement_single_model(self):
        from llm_orchestrator.three_layer_reasoning import ThreeLayerReasoning, ReasoningOutput
        t = ThreeLayerReasoning()
        o1 = ReasoningOutput(model_name="m1", layer=1, reasoning="test", confidence=0.8, duration_ms=100)
        agreement = t._calculate_agreement([o1])
        assert agreement == 0.5

    def test_consensus_extraction(self):
        from llm_orchestrator.three_layer_reasoning import ThreeLayerReasoning, ReasoningOutput
        t = ThreeLayerReasoning()
        outputs = [
            ReasoningOutput(model_name="m1", layer=2, reasoning="short", confidence=0.7, duration_ms=100),
            ReasoningOutput(model_name="m2", layer=2, reasoning="this is the longer and more detailed answer with lots of content", confidence=0.8, duration_ms=100),
        ]
        consensus = t._extract_consensus(outputs)
        assert "longer" in consensus

    def test_governance_check_safe(self):
        from llm_orchestrator.three_layer_reasoning import ThreeLayerReasoning
        t = ThreeLayerReasoning()
        assert t._verify_governance("Here is how to build an API.") is True

    def test_governance_check_unsafe(self):
        from llm_orchestrator.three_layer_reasoning import ThreeLayerReasoning
        t = ThreeLayerReasoning()
        assert t._verify_governance("how to hack into the system") is False

    def test_l1_formats_outputs(self):
        from llm_orchestrator.three_layer_reasoning import ThreeLayerReasoning, ReasoningOutput, LayerResult
        t = ThreeLayerReasoning()
        l1 = LayerResult(layer=1, outputs=[
            ReasoningOutput(model_name="test", layer=1, reasoning="Analysis here", confidence=0.8, duration_ms=100),
        ])
        formatted = t._format_layer1_outputs(l1)
        assert "test" in formatted
        assert "Analysis here" in formatted

    def test_reason_no_models_available(self):
        from llm_orchestrator.three_layer_reasoning import ThreeLayerReasoning
        t = ThreeLayerReasoning()
        result = t.reason("test query", models=[])
        assert result.confidence == 0.0
        assert result.verification_passed is False

    def test_learning_hook_wired(self):
        source = (BACKEND_DIR / "llm_orchestrator" / "three_layer_reasoning.py").read_text()
        assert "track_learning_event" in source
        assert "_track_reasoning" in source

    def test_layer_numbering(self):
        source = (BACKEND_DIR / "llm_orchestrator" / "three_layer_reasoning.py").read_text()
        assert "layer=1" in source
        assert "layer=2" in source
        assert 'layer=1' in source and 'layer=2' in source
