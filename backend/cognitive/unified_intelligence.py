"""
Unified Intelligence Query Handler

ONE entry point that chains ALL of Grace's intelligence systems
in order. Each layer tries to answer. First layer with sufficient
confidence wins. This is what makes Grace a unified intelligence
instead of a collection of separate systems.

THE CHAIN (in order of speed and determinism):

  Layer 1: COMPILED FACTS      (sub-ms, 100% deterministic)
           SQL lookup of subject/predicate/object triples

  Layer 2: COMPILED PROCEDURES  (sub-ms, 100% deterministic)
           SQL lookup of step-by-step procedures

  Layer 3: COMPILED RULES       (sub-ms, 100% deterministic)
           SQL match of if/then/else decision rules

  Layer 4: DISTILLED KNOWLEDGE  (sub-ms, 100% deterministic)
           Hash lookup of previously answered questions

  Layer 5: MEMORY MESH          (1-5ms, deterministic)
           Episodic + procedural memory recall

  Layer 6: LIBRARY CONNECTORS   (50-200ms, 100% factual)
           Wikidata, ConceptNet, Wolfram - external deterministic knowledge

  Layer 7: RAG + NEURO-SYMBOLIC (10-100ms, high confidence)
           Vector search + trust-aware retrieval + reranker + symbolic rules

  Layer 8: ORACLE ML            (5-50ms, prediction)
           Neural trust scorer + bandit + meta-learner for interpolation

  Layer 9: KIMI (LLM)           (100-2000ms, generative)
           Fallback for composition, novel reasoning, code generation
           Results stored for future deterministic serving

Every query goes through this chain. Every answer is tracked.
Every LLM response is distilled for next time. The chain gets
faster over time as more answers move from Layer 9 to Layers 1-4.
"""

import logging
import time
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class IntelligenceResult:
    """Result from the unified intelligence chain."""
    answered: bool
    response: str
    layer_used: str
    layer_number: int
    confidence: float
    source: str
    deterministic: bool
    duration_ms: float
    facts_used: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class UnifiedIntelligence:
    """
    One handler. All intelligence systems. Chained in order.

    Usage:
        ui = UnifiedIntelligence(session)
        result = ui.query("What port does Qdrant use?")

        if result.answered:
            print(f"Answer: {result.response}")
            print(f"From: Layer {result.layer_number} ({result.layer_used})")
            print(f"Confidence: {result.confidence}")
            print(f"Deterministic: {result.deterministic}")
    """

    CONFIDENCE_THRESHOLD = 0.6

    def __init__(self, session: Session):
        self.session = session
        self._query_count = 0
        self._layer_hits = {}

    def query(
        self,
        question: str,
        domain: Optional[str] = None,
        min_confidence: float = 0.6,
        max_layer: int = 9,
        skip_layers: Optional[List[int]] = None,
    ) -> IntelligenceResult:
        """
        Query the unified intelligence chain.

        Tries each layer in order. First layer with confidence
        above threshold returns the answer.

        Args:
            question: The question to answer
            domain: Optional domain hint
            min_confidence: Minimum confidence to accept
            max_layer: Highest layer to try (1-9)
            skip_layers: Layers to skip
        """
        start = time.time()
        self._query_count += 1
        skip = set(skip_layers or [])

        layers = [
            (1, "compiled_facts", self._layer1_compiled_facts),
            (2, "compiled_procedures", self._layer2_compiled_procedures),
            (3, "compiled_rules", self._layer3_compiled_rules),
            (4, "distilled_knowledge", self._layer4_distilled_knowledge),
            (5, "memory_mesh", self._layer5_memory_mesh),
            (6, "library_connectors", self._layer6_library_connectors),
            (7, "rag_neuro_symbolic", self._layer7_rag),
            (8, "oracle_ml", self._layer8_oracle),
            (9, "kimi_llm", self._layer9_kimi),
        ]

        for layer_num, layer_name, layer_fn in layers:
            if layer_num > max_layer:
                break
            if layer_num in skip:
                continue

            try:
                result = layer_fn(question, domain, min_confidence)
                if result and result.answered and result.confidence >= min_confidence:
                    result.duration_ms = (time.time() - start) * 1000

                    try:
                        from cognitive.timesense import get_timesense
                        get_timesense().record_operation(f"ui.query.{layer_name}", result.duration_ms, "unified_intelligence")
                    except Exception:
                        pass
                    self._layer_hits[layer_name] = self._layer_hits.get(layer_name, 0) + 1

                    # Track the hit
                    try:
                        from cognitive.learning_hook import track_learning_event
                        track_learning_event(
                            "unified_intelligence",
                            f"Layer {layer_num} ({layer_name}) answered with confidence {result.confidence:.2f}",
                            data={
                                "layer": layer_num,
                                "layer_name": layer_name,
                                "confidence": result.confidence,
                                "deterministic": result.deterministic,
                                "duration_ms": result.duration_ms,
                            },
                        )
                    except Exception:
                        pass

                    return result

            except Exception as e:
                logger.debug(f"[UI] Layer {layer_num} ({layer_name}) error: {e}")
                continue

        # No layer could answer
        duration = (time.time() - start) * 1000
        return IntelligenceResult(
            answered=False,
            response="",
            layer_used="none",
            layer_number=0,
            confidence=0.0,
            source="no_answer",
            deterministic=False,
            duration_ms=duration,
        )

    # ==================================================================
    # LAYER 1: COMPILED FACTS (sub-ms, 100% deterministic)
    # ==================================================================

    def _layer1_compiled_facts(
        self, question: str, domain: Optional[str], min_conf: float
    ) -> Optional[IntelligenceResult]:
        """Direct SQL lookup of compiled facts."""
        try:
            from cognitive.knowledge_compiler import get_knowledge_compiler
            compiler = get_knowledge_compiler(self.session)

            # Extract likely subject from question
            words = [w for w in question.split() if len(w) > 3 and w[0].isupper()]
            if not words:
                words = [w for w in question.split() if len(w) > 4][:3]

            for word in words[:3]:
                facts = compiler.query_facts(subject=word, min_confidence=min_conf, limit=5)
                if facts:
                    response_parts = [f"{f['subject']} {f['predicate']} {f['object']}" for f in facts[:5]]
                    return IntelligenceResult(
                        answered=True,
                        response=". ".join(response_parts),
                        layer_used="compiled_facts",
                        layer_number=1,
                        confidence=max(f["confidence"] for f in facts),
                        source="compiled_knowledge_store",
                        deterministic=True,
                        duration_ms=0,
                        facts_used=facts,
                    )
        except Exception as e:
            logger.debug(f"[UI-L1] {e}")
        return None

    # ==================================================================
    # LAYER 2: COMPILED PROCEDURES (sub-ms, 100% deterministic)
    # ==================================================================

    def _layer2_compiled_procedures(
        self, question: str, domain: Optional[str], min_conf: float
    ) -> Optional[IntelligenceResult]:
        """SQL lookup of step-by-step procedures."""
        try:
            from cognitive.knowledge_compiler import get_knowledge_compiler
            compiler = get_knowledge_compiler(self.session)

            procedures = compiler.query_procedures(goal=question, domain=domain, limit=3)
            if procedures:
                best = procedures[0]
                steps = best.get("steps", [])
                step_text = "\n".join(
                    f"Step {s.get('step', i+1)}: {s.get('action', s.get('detail', ''))}"
                    for i, s in enumerate(steps)
                )
                return IntelligenceResult(
                    answered=True,
                    response=f"{best['goal']}\n\n{step_text}",
                    layer_used="compiled_procedures",
                    layer_number=2,
                    confidence=best.get("confidence", 0.5),
                    source="compiled_knowledge_store",
                    deterministic=True,
                    duration_ms=0,
                    facts_used=procedures,
                )
        except Exception as e:
            logger.debug(f"[UI-L2] {e}")
        return None

    # ==================================================================
    # LAYER 3: COMPILED RULES (sub-ms, 100% deterministic)
    # ==================================================================

    def _layer3_compiled_rules(
        self, question: str, domain: Optional[str], min_conf: float
    ) -> Optional[IntelligenceResult]:
        """SQL match of decision rules."""
        try:
            from cognitive.knowledge_compiler import get_knowledge_compiler
            compiler = get_knowledge_compiler(self.session)

            rules = compiler.query_rules(domain=domain, context=question, limit=3)
            if rules:
                best = rules[0]
                response = f"{best['action']}"
                if best.get("explanation"):
                    response += f"\n\nReason: {best['explanation']}"
                if best.get("alternative"):
                    response += f"\nAlternative: {best['alternative']}"

                return IntelligenceResult(
                    answered=True,
                    response=response,
                    layer_used="compiled_rules",
                    layer_number=3,
                    confidence=best.get("confidence", 0.5),
                    source="compiled_knowledge_store",
                    deterministic=True,
                    duration_ms=0,
                    facts_used=rules,
                )
        except Exception as e:
            logger.debug(f"[UI-L3] {e}")
        return None

    # ==================================================================
    # LAYER 4: DISTILLED KNOWLEDGE (sub-ms, deterministic)
    # ==================================================================

    def _layer4_distilled_knowledge(
        self, question: str, domain: Optional[str], min_conf: float
    ) -> Optional[IntelligenceResult]:
        """Hash lookup of previously answered questions."""
        try:
            from cognitive.knowledge_compiler import get_llm_knowledge_miner
            miner = get_llm_knowledge_miner(self.session)

            # Exact match
            result = miner.lookup(question, min_confidence=min_conf)
            if result:
                return IntelligenceResult(
                    answered=True,
                    response=result["response"],
                    layer_used="distilled_knowledge",
                    layer_number=4,
                    confidence=result["confidence"],
                    source=f"distilled:{result.get('model_used', 'stored')}",
                    deterministic=True,
                    duration_ms=0,
                    metadata={"verified": result.get("verified", False)},
                )

            # Fuzzy match
            fuzzy = miner.fuzzy_lookup(question, min_confidence=min_conf, limit=3)
            if fuzzy:
                best = fuzzy[0]
                return IntelligenceResult(
                    answered=True,
                    response=best["response"],
                    layer_used="distilled_knowledge_fuzzy",
                    layer_number=4,
                    confidence=best["confidence"] * 0.9,  # Slightly lower for fuzzy
                    source="distilled:fuzzy_match",
                    deterministic=True,
                    duration_ms=0,
                    metadata={"fuzzy": True},
                )
        except Exception as e:
            logger.debug(f"[UI-L4] {e}")
        return None

    # ==================================================================
    # LAYER 5: MEMORY MESH (1-5ms, deterministic)
    # ==================================================================

    def _layer5_memory_mesh(
        self, question: str, domain: Optional[str], min_conf: float
    ) -> Optional[IntelligenceResult]:
        """Episodic + procedural memory recall."""
        try:
            from cognitive.procedural_memory import ProceduralRepository
            proc_repo = ProceduralRepository(self.session)

            procedures = proc_repo.find_procedures(question, limit=3)
            if procedures:
                best = procedures[0]
                steps = best.get("steps", [])
                if isinstance(steps, str):
                    import json
                    steps = json.loads(steps)

                return IntelligenceResult(
                    answered=True,
                    response=f"Procedure: {best.get('name', '')}\n{best.get('goal', '')}",
                    layer_used="memory_mesh_procedural",
                    layer_number=5,
                    confidence=best.get("trust_score", 0.5),
                    source="memory_mesh",
                    deterministic=True,
                    duration_ms=0,
                )
        except Exception as e:
            logger.debug(f"[UI-L5] {e}")

        try:
            from cognitive.episodic_memory import EpisodicBuffer
            buffer = EpisodicBuffer(self.session)
            episodes = buffer.recall_similar(question, limit=3)
            if episodes:
                best = episodes[0]
                return IntelligenceResult(
                    answered=True,
                    response=f"From experience: {best.get('problem', '')}\nOutcome: {best.get('outcome', '')}",
                    layer_used="memory_mesh_episodic",
                    layer_number=5,
                    confidence=best.get("trust_score", 0.5),
                    source="memory_mesh",
                    deterministic=True,
                    duration_ms=0,
                )
        except Exception as e:
            logger.debug(f"[UI-L5-episodic] {e}")

        return None

    # ==================================================================
    # LAYER 6: LIBRARY CONNECTORS (50-200ms, 100% factual)
    # ==================================================================

    def _layer6_library_connectors(
        self, question: str, domain: Optional[str], min_conf: float
    ) -> Optional[IntelligenceResult]:
        """Query Wikidata and ConceptNet for external knowledge."""
        try:
            from cognitive.library_connectors import get_library_connectors
            lib = get_library_connectors()

            # Extract key terms
            terms = [w for w in question.split() if len(w) > 3 and w[0].isupper()]
            if not terms:
                terms = [w for w in question.split() if len(w) > 4][:2]

            for term in terms[:2]:
                # Try ConceptNet first (common sense, fast)
                cn_facts = lib.query_conceptnet(term, limit=5)
                if cn_facts:
                    response_parts = []
                    for f in cn_facts[:5]:
                        surface = f.get("surface_text", "")
                        if surface:
                            response_parts.append(surface)
                        else:
                            response_parts.append(f"{f['subject']} {f['predicate']} {f['object']}")

                    # Also compile into store for next time
                    try:
                        lib.mine_and_compile(term, session=self.session, sources=["conceptnet"])
                    except Exception:
                        pass

                    return IntelligenceResult(
                        answered=True,
                        response=". ".join(response_parts),
                        layer_used="library_conceptnet",
                        layer_number=6,
                        confidence=0.85,
                        source="conceptnet",
                        deterministic=True,
                        duration_ms=0,
                        facts_used=cn_facts,
                    )

                # Try Wikidata
                wd_facts = lib.query_wikidata(term, limit=5)
                if wd_facts:
                    response_parts = [f"{f['subject']} {f['predicate']}: {f['object']}" for f in wd_facts[:5]]

                    try:
                        lib.mine_and_compile(term, session=self.session, sources=["wikidata"])
                    except Exception:
                        pass

                    return IntelligenceResult(
                        answered=True,
                        response=". ".join(response_parts),
                        layer_used="library_wikidata",
                        layer_number=6,
                        confidence=0.9,
                        source="wikidata",
                        deterministic=True,
                        duration_ms=0,
                        facts_used=wd_facts,
                    )
        except Exception as e:
            logger.debug(f"[UI-L6] {e}")
        return None

    # ==================================================================
    # LAYER 7: RAG + NEURO-SYMBOLIC (10-100ms)
    # ==================================================================

    def _layer7_rag(
        self, question: str, domain: Optional[str], min_conf: float
    ) -> Optional[IntelligenceResult]:
        """Vector search + trust-aware retrieval."""
        try:
            from retrieval.retriever import DocumentRetriever
            from embedding import get_embedding_model

            model = get_embedding_model()
            retriever = DocumentRetriever(embedding_model=model)

            chunks = retriever.retrieve(question, limit=5, score_threshold=0.5)
            if chunks:
                context = retriever.build_context(chunks, include_sources=True)
                avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks)

                return IntelligenceResult(
                    answered=True,
                    response=context,
                    layer_used="rag_retrieval",
                    layer_number=7,
                    confidence=min(0.85, avg_score),
                    source="rag_vector_search",
                    deterministic=True,
                    duration_ms=0,
                    metadata={"chunks": len(chunks), "avg_score": avg_score},
                )
        except Exception as e:
            logger.debug(f"[UI-L7] {e}")
        return None

    # ==================================================================
    # LAYER 8: ORACLE ML (5-50ms, prediction)
    # ==================================================================

    def _layer8_oracle(
        self, question: str, domain: Optional[str], min_conf: float
    ) -> Optional[IntelligenceResult]:
        """Oracle ML prediction for interpolation."""
        # Oracle handles structured prediction, not open Q&A
        # Skip for general questions, useful for system predictions
        return None

    # ==================================================================
    # LAYER 9: KIMI / LLM FALLBACK (100-2000ms, generative)
    # ==================================================================

    def _layer9_kimi(
        self, question: str, domain: Optional[str], min_conf: float
    ) -> Optional[IntelligenceResult]:
        """
        Cloud LLM fallback. Uses Kimi Cloud for high-quality answers.
        Response stored in distilled knowledge for future deterministic serving.
        """
        try:
            from cognitive.kimi_teacher import get_kimi_teacher
            teacher = get_kimi_teacher(self.session)
            result = teacher.ask(question, topic=domain or "general", max_tokens=500)

            if result.get("success") and result.get("answer"):
                return IntelligenceResult(
                    answered=True,
                    response=result["answer"],
                    layer_used="kimi_cloud",
                    layer_number=9,
                    confidence=0.8,
                    source=f"kimi_cloud:{result.get('model', 'moonshot')}",
                    deterministic=False,
                    duration_ms=0,
                    metadata={"tokens": result.get("tokens", 0), "compiled": result.get("compiled", {})},
                )
        except Exception:
            pass
        return None

    # ==================================================================
    # STATS
    # ==================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get unified intelligence statistics."""
        total_hits = sum(self._layer_hits.values())
        return {
            "total_queries": self._query_count,
            "total_hits": total_hits,
            "hit_rate": total_hits / self._query_count if self._query_count > 0 else 0,
            "layer_hits": dict(self._layer_hits),
            "layer_hit_rates": {
                k: v / self._query_count if self._query_count > 0 else 0
                for k, v in self._layer_hits.items()
            },
        }


_ui_instance: Optional[UnifiedIntelligence] = None


def get_unified_intelligence(session: Session) -> UnifiedIntelligence:
    """Get or create the unified intelligence singleton."""
    global _ui_instance
    if _ui_instance is None:
        _ui_instance = UnifiedIntelligence(session)
    return _ui_instance
