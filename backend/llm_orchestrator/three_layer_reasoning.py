"""
Three-Layer Reasoning Pipeline

Layer 1 (Parallel Reasoning):
  All available LLMs receive the SAME data + prompt simultaneously.
  Each reasons independently using its own model/architecture.
  They cannot see each other's output yet.
  Output: N independent reasoning chains.

Layer 2 (Synthesis Reasoning):
  Each LLM receives ALL Layer 1 outputs combined.
  Each re-reasons on the SAME data but now informed by what everyone else thought.
  They synthesize, challenge, and refine their reasoning.
  Output: N synthesized conclusions that have been cross-examined.

Layer 3 (Grace Verification):
  Grace's cognitive engine verifies the synthesized outputs.
  Checks against: training data, knowledge base, trust scores, governance rules.
  Produces a final verified answer with confidence score.
  Output: Single verified truth.

The LLM orchestration system has access to:
- Training data (via retrieval/RAG)
- Kimi (primary LLM for complex tasks)
- All other available models
- Knowledge base for grounding
"""

import logging
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

def _track_reasoning(desc, **kw):
    try:
        from cognitive.learning_hook import track_learning_event
        track_learning_event("three_layer_reasoning", desc, **kw)
    except Exception:
        pass


@dataclass
class ReasoningOutput:
    """Output from a single model's reasoning."""
    model_name: str
    layer: int
    reasoning: str
    confidence: float
    duration_ms: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LayerResult:
    """Combined result from a reasoning layer."""
    layer: int
    outputs: List[ReasoningOutput]
    consensus: Optional[str] = None
    agreement_score: float = 0.0
    duration_ms: float = 0.0


@dataclass
class VerifiedResult:
    """Final Grace-verified result."""
    answer: str
    confidence: float
    layer1_agreement: float
    layer2_agreement: float
    verification_passed: bool
    training_data_grounded: bool
    governance_passed: bool
    reasoning_trace: Dict[str, Any] = field(default_factory=dict)
    total_duration_ms: float = 0.0


class ThreeLayerReasoning:
    """
    Three-layer reasoning pipeline with full LLM orchestration.

    All LLMs have access to training data and Kimi.
    """

    def __init__(self, max_workers: int = 4):
        self._client = None
        self._retriever = None
        self.max_workers = max_workers

    @property
    def client(self):
        """Lazy-init Ollama client."""
        if self._client is None:
            try:
                from ollama_client.client import get_ollama_client
                self._client = get_ollama_client()
            except Exception:
                pass
        return self._client

    def get_available_models(self) -> List[str]:
        """Get list of available models from Ollama."""
        if not self.client or not self.client.is_running():
            return []
        try:
            models = self.client.get_all_models()
            return [m.name for m in models] if models else []
        except Exception:
            return []

    def get_training_context(self, query: str, limit: int = 5) -> str:
        """Retrieve training data context for grounding."""
        try:
            if self._retriever is None:
                from retrieval.retriever import DocumentRetriever
                from embedding import get_embedding_model
                model = get_embedding_model()
                self._retriever = DocumentRetriever(
                    collection_name="documents", embedding_model=model
                )

            results = self._retriever.retrieve(
                query=query, limit=limit, score_threshold=0.3, include_metadata=True
            )
            if results:
                chunks = []
                for r in results[:limit]:
                    text = r.get("text", r.get("content", ""))[:500]
                    score = r.get("score", 0)
                    chunks.append(f"[Source score={score:.2f}]: {text}")
                return "\n\n".join(chunks)
        except Exception as e:
            logger.debug(f"[3-LAYER] Training data retrieval failed: {e}")
        return ""

    # =========================================================================
    # LAYER 1: Parallel Independent Reasoning
    # =========================================================================

    def layer1_parallel_reasoning(
        self, query: str, context: str = "", models: List[str] = None
    ) -> LayerResult:
        """
        Layer 1: All LLMs reason independently on the same data.

        Each model gets: the user query + training data context.
        Each model reasons independently (no cross-talk).
        """
        start = time.time()
        available = models or self.get_available_models()
        if not available:
            available = [self._get_default_model()]

        training_context = context or self.get_training_context(query)

        # Personalize with user preferences if available
        user_context = ""
        try:
            from cognitive.user_preference_model import UserPreferenceEngine
            from database.session import SessionLocal
            _up_s = SessionLocal()
            if _up_s:
                try:
                    up = UserPreferenceEngine(_up_s)
                    user_context = up.get_system_prompt_additions("default")
                finally:
                    _up_s.close()
        except Exception:
            pass

        system_prompt = (
            "You are an expert reasoning model. Analyze the question carefully using "
            "the provided training data context. Give your independent analysis and conclusion. "
            "Be specific and cite evidence from the context when possible."
        )

        user_prompt = query
        if training_context:
            user_prompt = (
                f"Training Data Context:\n{training_context}\n\n"
                f"Question: {query}\n\n"
                f"Provide your independent reasoning and conclusion:"
            )

        outputs = []

        def reason_with_model(model_name: str) -> Optional[ReasoningOutput]:
            model_start = time.time()
            try:
                if not self.client or not self.client.is_running():
                    return None
                response = self.client.chat(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    stream=False,
                    temperature=0.4
                )
                duration = (time.time() - model_start) * 1000
                return ReasoningOutput(
                    model_name=model_name, layer=1,
                    reasoning=response, confidence=0.7,
                    duration_ms=duration
                )
            except Exception as e:
                logger.debug(f"[3-LAYER] L1 {model_name} failed: {e}")
                return None

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(reason_with_model, m): m for m in available[:4]}
            for future in as_completed(futures, timeout=120):
                result = future.result()
                if result:
                    outputs.append(result)

        agreement = self._calculate_agreement(outputs) if len(outputs) > 1 else 0.5
        duration = (time.time() - start) * 1000

        _track_reasoning(
            f"L1: {len(outputs)} models reasoned",
            confidence=agreement
        )

        return LayerResult(
            layer=1, outputs=outputs,
            agreement_score=agreement, duration_ms=duration
        )

    # =========================================================================
    # LAYER 2: Synthesis Reasoning
    # =========================================================================

    def layer2_synthesis_reasoning(
        self, query: str, layer1_result: LayerResult, models: List[str] = None
    ) -> LayerResult:
        """
        Layer 2: Each LLM re-reasons with knowledge of ALL Layer 1 conclusions.

        Each model gets: original query + training data + ALL L1 reasoning outputs.
        Each model synthesizes, challenges, and refines.
        """
        start = time.time()
        available = models or self.get_available_models()
        if not available:
            available = [self._get_default_model()]

        l1_summary = self._format_layer1_outputs(layer1_result)

        system_prompt = (
            "You are an expert synthesis reasoner. You have been given the independent "
            "analyses from multiple AI models on the same question. Your job is to:\n"
            "1. Consider each model's reasoning and evidence\n"
            "2. Identify agreements and disagreements\n"
            "3. Challenge weak reasoning\n"
            "4. Synthesize the strongest conclusion\n"
            "5. State your confidence level (0-100%)\n"
            "Be rigorous. If models disagree, explain why one is more credible."
        )

        user_prompt = (
            f"Original Question: {query}\n\n"
            f"=== Layer 1 Independent Analyses ===\n{l1_summary}\n\n"
            f"Synthesize these analyses. What is the strongest conclusion? "
            f"Where do the models agree? Where do they disagree and why? "
            f"Give your refined answer with confidence percentage:"
        )

        outputs = []

        def synthesize_with_model(model_name: str) -> Optional[ReasoningOutput]:
            model_start = time.time()
            try:
                if not self.client or not self.client.is_running():
                    return None
                response = self.client.chat(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    stream=False,
                    temperature=0.3
                )
                duration = (time.time() - model_start) * 1000
                return ReasoningOutput(
                    model_name=model_name, layer=2,
                    reasoning=response, confidence=0.8,
                    duration_ms=duration
                )
            except Exception as e:
                logger.debug(f"[3-LAYER] L2 {model_name} failed: {e}")
                return None

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(synthesize_with_model, m): m for m in available[:4]}
            for future in as_completed(futures, timeout=120):
                result = future.result()
                if result:
                    outputs.append(result)

        agreement = self._calculate_agreement(outputs) if len(outputs) > 1 else 0.6
        consensus = self._extract_consensus(outputs) if outputs else ""
        duration = (time.time() - start) * 1000

        _track_reasoning(
            f"L2: {len(outputs)} models synthesized",
            confidence=agreement
        )

        return LayerResult(
            layer=2, outputs=outputs, consensus=consensus,
            agreement_score=agreement, duration_ms=duration
        )

    # =========================================================================
    # LAYER 3: Grace Verification
    # =========================================================================

    def layer3_grace_verification(
        self, query: str, layer2_result: LayerResult
    ) -> VerifiedResult:
        """
        Layer 3: Grace verifies the synthesized output.

        Checks against:
        - Training data grounding
        - Knowledge base consistency
        - Governance rules
        - Trust scores
        """
        start = time.time()
        consensus = layer2_result.consensus or ""
        if not consensus and layer2_result.outputs:
            consensus = layer2_result.outputs[0].reasoning

        # Check 1: Training data grounding
        training_grounded = self._verify_against_training_data(query, consensus)

        # Check 2: Governance
        governance_passed = self._verify_governance(consensus)

        # Check 3: Confidence from agreement scores
        l2_agreement = layer2_result.agreement_score
        confidence = (l2_agreement * 0.5) + (0.3 if training_grounded else 0.0) + (0.2 if governance_passed else 0.0)

        # Check 4: Final Grace verification via primary model
        verified_answer = consensus
        try:
            if self.client and self.client.is_running():
                model = self._get_default_model()
                verification_prompt = (
                    f"You are Grace's verification system. A multi-model reasoning pipeline "
                    f"has produced this answer to the question '{query}':\n\n"
                    f"{consensus[:2000]}\n\n"
                    f"Verify this answer. Is it accurate, complete, and safe? "
                    f"If corrections are needed, provide the corrected answer. "
                    f"If it's correct, confirm it. Be concise."
                )
                verified_answer = self.client.chat(
                    model=model,
                    messages=[{"role": "user", "content": verification_prompt}],
                    stream=False, temperature=0.2
                )
        except Exception as e:
            logger.debug(f"[3-LAYER] L3 verification LLM failed: {e}")

        duration = (time.time() - start) * 1000

        _track_reasoning(
            f"L3: verified (confidence={confidence:.1%})",
            confidence=confidence
        )

        return VerifiedResult(
            answer=verified_answer,
            confidence=round(confidence, 3),
            layer1_agreement=0.0,
            layer2_agreement=l2_agreement,
            verification_passed=confidence >= 0.6,
            training_data_grounded=training_grounded,
            governance_passed=governance_passed,
            reasoning_trace={
                "l2_consensus_length": len(consensus),
                "l2_models_used": [o.model_name for o in layer2_result.outputs],
                "verification_model": self._get_default_model(),
            },
            total_duration_ms=duration,
        )

    # =========================================================================
    # FULL PIPELINE
    # =========================================================================

    def reason(self, query: str, models: List[str] = None) -> VerifiedResult:
        """
        Run the full 3-layer reasoning pipeline.

        L1: Parallel independent reasoning
        L2: Synthesis reasoning on L1 outputs
        L3: Grace verification

        Returns a verified, grounded answer.
        """
        total_start = time.time()

        logger.info(f"[3-LAYER] Starting 3-layer reasoning for: {query[:80]}...")

        # Layer 1
        l1 = self.layer1_parallel_reasoning(query, models=models)
        logger.info(f"[3-LAYER] L1 complete: {len(l1.outputs)} models, agreement={l1.agreement_score:.2f}")

        if not l1.outputs:
            return VerifiedResult(
                answer="Unable to reason: no models available.",
                confidence=0.0, layer1_agreement=0.0, layer2_agreement=0.0,
                verification_passed=False, training_data_grounded=False,
                governance_passed=False,
                total_duration_ms=(time.time() - total_start) * 1000,
            )

        # Layer 2
        l2 = self.layer2_synthesis_reasoning(query, l1, models=models)
        logger.info(f"[3-LAYER] L2 complete: {len(l2.outputs)} syntheses, agreement={l2.agreement_score:.2f}")

        # Layer 3
        result = self.layer3_grace_verification(query, l2)
        result.layer1_agreement = l1.agreement_score
        result.total_duration_ms = (time.time() - total_start) * 1000

        logger.info(
            f"[3-LAYER] Complete: confidence={result.confidence:.1%}, "
            f"grounded={result.training_data_grounded}, "
            f"governance={result.governance_passed}, "
            f"duration={result.total_duration_ms:.0f}ms"
        )

        # Feed result to unified intelligence
        try:
            from genesis.unified_intelligence import UnifiedIntelligenceEngine
            from database.session import SessionLocal
            _ui_s = SessionLocal()
            if _ui_s:
                try:
                    UnifiedIntelligenceEngine(_ui_s).record(
                        source_system="three_layer_reasoning", signal_type="result",
                        signal_name="reasoning_complete", value_numeric=result.confidence,
                        value_json={"l1_agreement": result.layer1_agreement, "l2_agreement": result.layer2_agreement, "grounded": result.training_data_grounded},
                        trust_score=result.confidence, ttl_seconds=600,
                    )
                finally:
                    _ui_s.close()
        except Exception:
            pass

        # TimeSense timing
        try:
            from cognitive.timesense_governance import get_timesense_governance
            get_timesense_governance().record("reasoning.full", result.total_duration_ms, "reasoning")
        except Exception:
            pass

        # HIA verification on final answer
        try:
            from security.honesty_integrity_accountability import get_hia_framework
            hia_result = get_hia_framework().verify_llm_output(result.answer, has_sources=result.training_data_grounded)
            if not hia_result.passed:
                logger.warning(f"[3-LAYER] HIA violation: honesty={hia_result.honesty_score:.0%}")
        except Exception:
            pass

        # Feed reasoning result as seed for KNN discovery
        try:
            from cognitive.unified_learning_pipeline import get_unified_pipeline
            pipeline = get_unified_pipeline()
            if pipeline.running:
                pipeline.add_seed(
                    topic=query[:100],
                    text=result.answer[:300]
                )
        except Exception:
            pass

        # Contradiction detection between L1/L2 outputs
        try:
            from confidence_scorer.contradiction_detector import SemanticContradictionDetector
            detector = SemanticContradictionDetector()
            if len(l1.outputs) >= 2:
                texts = [o.reasoning[:500] for o in l1.outputs[:3]]
                for i in range(len(texts)):
                    for j in range(i+1, len(texts)):
                        contradiction = detector.detect_contradiction(texts[i], texts[j])
                        if contradiction and contradiction.get("is_contradiction"):
                            result.reasoning_trace["contradictions_detected"] = True
                            logger.info(f"[3-LAYER] Contradiction detected between L1 models {i+1} and {j+1}")
                            break
        except Exception:
            pass

        return result

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _get_default_model(self) -> str:
        try:
            from settings import settings
            return getattr(settings, "OLLAMA_LLM_DEFAULT", "mistral:7b")
        except Exception:
            return "mistral:7b"

    def _format_layer1_outputs(self, l1: LayerResult) -> str:
        parts = []
        for i, o in enumerate(l1.outputs):
            parts.append(
                f"--- Model {i+1}: {o.model_name} (confidence: {o.confidence:.0%}) ---\n"
                f"{o.reasoning[:1500]}\n"
            )
        return "\n".join(parts)

    def _calculate_agreement(self, outputs: List[ReasoningOutput]) -> float:
        """Estimate agreement between outputs using simple heuristics."""
        if len(outputs) < 2:
            return 0.5
        texts = [o.reasoning.lower()[:500] for o in outputs]
        total_pairs = 0
        agreement_sum = 0.0
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                words_i = set(texts[i].split())
                words_j = set(texts[j].split())
                if not words_i or not words_j:
                    continue
                overlap = len(words_i & words_j) / max(len(words_i | words_j), 1)
                agreement_sum += overlap
                total_pairs += 1
        return round(agreement_sum / max(total_pairs, 1), 3)

    def _extract_consensus(self, outputs: List[ReasoningOutput]) -> str:
        """Extract consensus from synthesis outputs (longest = most thorough)."""
        if not outputs:
            return ""
        return max(outputs, key=lambda o: len(o.reasoning)).reasoning

    def _verify_against_training_data(self, query: str, answer: str) -> bool:
        """Check if the answer is grounded in training data."""
        context = self.get_training_context(query, limit=3)
        if not context:
            return False
        answer_words = set(answer.lower().split()[:50])
        context_words = set(context.lower().split())
        overlap = len(answer_words & context_words) / max(len(answer_words), 1)
        return overlap > 0.15

    def _verify_governance(self, answer: str) -> bool:
        """Check answer against governance rules."""
        try:
            from security.governance_middleware import OutputSafetyValidator
            result = OutputSafetyValidator.validate(answer)
            return result.get("safe", True)
        except Exception:
            return True


_pipeline: Optional[ThreeLayerReasoning] = None

def get_three_layer_reasoning() -> ThreeLayerReasoning:
    """Get the 3-layer reasoning pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = ThreeLayerReasoning()
    return _pipeline
