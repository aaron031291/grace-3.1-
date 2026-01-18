"""
Layer 4 API: Recursive Pattern Learning & Cross-Domain Intelligence

Provides REST endpoints for Layer 4 neuro-symbolic intelligence:
- Run recursive learning cycles
- Query cross-domain patterns
- Get transfer insights
- Export to Layer 3 governance
"""

import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime

from database import get_session
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/layer4", tags=["Layer 4 - Neuro-Symbolic Intelligence"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class RunCycleRequest(BaseModel):
    """Request to run a recursive learning cycle."""
    domain: str = Field(..., description="Pattern domain (code, healing, error, template, etc.)")
    data: List[Dict[str, Any]] = Field(..., description="Data to learn from")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    max_iterations: int = Field(3, ge=1, le=10, description="Maximum recursive depth")


class QueryPatternsRequest(BaseModel):
    """Request to query patterns."""
    query: str = Field(..., description="Query text")
    domain: Optional[str] = Field(None, description="Filter by domain")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")


class PatternResponse(BaseModel):
    """Pattern response model."""
    pattern_id: str
    source_domain: str
    applicable_domains: List[str]
    confidence: float
    trust_score: float
    abstraction_level: int
    support_count: int
    transfer_count: int
    abstract_form: Dict[str, Any]


class CycleResponse(BaseModel):
    """Recursive learning cycle response."""
    cycle_id: str
    cycle_number: int
    patterns_discovered: int
    patterns_abstracted: int
    patterns_validated: int
    patterns_transferred: int
    domains_touched: List[str]
    improvement_score: float
    duration_ms: float


class StatusResponse(BaseModel):
    """Layer 4 status response."""
    layer: int
    name: str
    total_patterns: int
    total_cycles: int
    domains_active: List[str]
    neuro_symbolic_connected: bool
    governance_connected: bool
    learning_memory_connected: bool


# ============================================================================
# LAYER 4 INSTANCE
# ============================================================================

_layer4_instance = None


def get_layer4(session: Session = Depends(get_session)):
    """Get or create Layer 4 instance."""
    global _layer4_instance
    
    if _layer4_instance is None:
        try:
            from ml_intelligence.layer4_recursive_pattern_learner import (
                get_layer4_recursive_learner,
                PatternDomain,
            )
            
            # Try to connect dependencies
            neuro_symbolic = None
            rule_generator = None
            rule_storage = None
            governance = None
            learning_memory = None
            
            # Neuro-symbolic reasoner
            try:
                from ml_intelligence.neuro_symbolic_reasoner import get_neuro_symbolic_reasoner
                from retrieval.retriever import DocumentRetriever
                retriever = DocumentRetriever(session=session)
                neuro_symbolic = get_neuro_symbolic_reasoner(retriever=retriever)
                logger.info("[LAYER4-API] Connected neuro-symbolic reasoner")
            except Exception as e:
                logger.warning(f"[LAYER4-API] Neuro-symbolic not available: {e}")
            
            # Rule generator
            try:
                from ml_intelligence.neural_to_symbolic_rule_generator import (
                    get_neural_to_symbolic_generator
                )
                rule_generator = get_neural_to_symbolic_generator()
                logger.info("[LAYER4-API] Connected rule generator")
            except Exception as e:
                logger.warning(f"[LAYER4-API] Rule generator not available: {e}")
            
            # Learning memory
            try:
                from cognitive.learning_memory import get_learning_memory
                learning_memory = get_learning_memory(session)
                logger.info("[LAYER4-API] Connected learning memory")
            except Exception as e:
                logger.warning(f"[LAYER4-API] Learning memory not available: {e}")
            
            # Rule storage
            try:
                if learning_memory:
                    from ml_intelligence.rule_storage import get_rule_storage
                    rule_storage = get_rule_storage(learning_memory)
                    logger.info("[LAYER4-API] Connected rule storage")
            except Exception as e:
                logger.warning(f"[LAYER4-API] Rule storage not available: {e}")
            
            # Governance (Layer 3)
            try:
                from governance.quorum_governance import get_quorum_governance
                governance = get_quorum_governance(session)
                logger.info("[LAYER4-API] Connected Layer 3 governance")
            except Exception as e:
                logger.warning(f"[LAYER4-API] Governance not available: {e}")
            
            _layer4_instance = get_layer4_recursive_learner(
                neuro_symbolic_reasoner=neuro_symbolic,
                rule_generator=rule_generator,
                rule_storage=rule_storage,
                governance_engine=governance,
                learning_memory=learning_memory,
            )
            
            logger.info("[LAYER4-API] Layer 4 initialized")
            
        except Exception as e:
            logger.error(f"[LAYER4-API] Failed to initialize Layer 4: {e}")
            raise HTTPException(status_code=500, detail=f"Layer 4 initialization failed: {e}")
    
    return _layer4_instance


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/status", response_model=StatusResponse)
async def get_status(layer4=Depends(get_layer4)):
    """Get Layer 4 status and connected systems."""
    try:
        status = layer4.get_status()
        return StatusResponse(**status)
    except Exception as e:
        logger.error(f"[LAYER4-API] Status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cycle/run", response_model=CycleResponse)
async def run_learning_cycle(
    request: RunCycleRequest,
    layer4=Depends(get_layer4),
):
    """
    Run a recursive learning cycle.
    
    This is the core Layer 4 operation:
    1. Discover patterns in data
    2. Abstract to domain-agnostic form
    3. Validate against knowledge base
    4. Transfer to applicable domains
    5. Export high-trust patterns to Layer 3
    """
    try:
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        # Validate domain
        try:
            domain = PatternDomain(request.domain.lower())
        except ValueError:
            valid_domains = [d.value for d in PatternDomain]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid domain '{request.domain}'. Valid: {valid_domains}"
            )
        
        # Run cycle
        start_time = datetime.utcnow()
        cycle = layer4.run_recursive_cycle(
            domain=domain,
            data=request.data,
            context=request.context,
            max_iterations=request.max_iterations,
        )
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return CycleResponse(
            cycle_id=cycle.cycle_id,
            cycle_number=cycle.cycle_number,
            patterns_discovered=cycle.patterns_discovered,
            patterns_abstracted=cycle.patterns_abstracted,
            patterns_validated=cycle.patterns_validated,
            patterns_transferred=cycle.patterns_transferred,
            domains_touched=[d.value for d in cycle.domains_touched],
            improvement_score=cycle.improvement_score,
            duration_ms=duration_ms,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LAYER4-API] Cycle error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patterns/query")
async def query_patterns(
    request: QueryPatternsRequest,
    layer4=Depends(get_layer4),
):
    """Query patterns by text similarity."""
    try:
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        domain = None
        if request.domain:
            try:
                domain = PatternDomain(request.domain.lower())
            except ValueError:
                pass  # Ignore invalid domain, query all
        
        results = layer4.query_patterns(
            query=request.query,
            domain=domain,
            limit=request.limit,
        )
        
        return {
            "query": request.query,
            "domain": request.domain,
            "results": [
                {
                    "pattern": PatternResponse(
                        pattern_id=p.pattern_id,
                        source_domain=p.source_domain.value,
                        applicable_domains=[d.value for d in p.applicable_domains],
                        confidence=p.confidence,
                        trust_score=p.trust_score,
                        abstraction_level=p.abstraction_level,
                        support_count=p.support_count,
                        transfer_count=p.transfer_count,
                        abstract_form=p.abstract_form,
                    ).dict(),
                    "score": score,
                }
                for p, score in results
            ],
            "count": len(results),
        }
        
    except Exception as e:
        logger.error(f"[LAYER4-API] Query error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patterns/domain/{domain}")
async def get_patterns_for_domain(
    domain: str,
    min_trust: float = Query(0.5, ge=0.0, le=1.0),
    limit: int = Query(50, ge=1, le=200),
    layer4=Depends(get_layer4),
):
    """Get all patterns applicable to a domain."""
    try:
        from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
        
        try:
            domain_enum = PatternDomain(domain.lower())
        except ValueError:
            valid_domains = [d.value for d in PatternDomain]
            raise HTTPException(
                status_code=400,
                detail=f"Invalid domain '{domain}'. Valid: {valid_domains}"
            )
        
        patterns = layer4.get_patterns_for_domain(
            domain=domain_enum,
            min_trust=min_trust,
            limit=limit,
        )
        
        return {
            "domain": domain,
            "min_trust": min_trust,
            "patterns": [
                PatternResponse(
                    pattern_id=p.pattern_id,
                    source_domain=p.source_domain.value,
                    applicable_domains=[d.value for d in p.applicable_domains],
                    confidence=p.confidence,
                    trust_score=p.trust_score,
                    abstraction_level=p.abstraction_level,
                    support_count=p.support_count,
                    transfer_count=p.transfer_count,
                    abstract_form=p.abstract_form,
                ).dict()
                for p in patterns
            ],
            "count": len(patterns),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LAYER4-API] Domain patterns error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/cross-domain")
async def get_cross_domain_insights(layer4=Depends(get_layer4)):
    """Get insights about cross-domain pattern transfer."""
    try:
        insights = layer4.get_cross_domain_insights()
        return insights
    except Exception as e:
        logger.error(f"[LAYER4-API] Insights error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/domains")
async def list_domains():
    """List available pattern domains."""
    from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
    
    return {
        "domains": [
            {
                "name": d.value,
                "description": _get_domain_description(d),
            }
            for d in PatternDomain
        ]
    }


def _get_domain_description(domain) -> str:
    """Get human-readable description for domain."""
    from ml_intelligence.layer4_recursive_pattern_learner import PatternDomain
    
    descriptions = {
        PatternDomain.CODE: "Code patterns (syntax, structure, fixes)",
        PatternDomain.HEALING: "Self-healing patterns (error → fix)",
        PatternDomain.ERROR: "Error patterns (symptoms, causes)",
        PatternDomain.TEMPLATE: "Template patterns (generation, transformation)",
        PatternDomain.REASONING: "Reasoning patterns (logic, inference)",
        PatternDomain.KNOWLEDGE: "Knowledge patterns (facts, relationships)",
        PatternDomain.WORKFLOW: "Workflow patterns (sequences, dependencies)",
        PatternDomain.TESTING: "Testing patterns (assertions, coverage)",
    }
    return descriptions.get(domain, "Unknown domain")


@router.get("/cycles/history")
async def get_cycle_history(
    limit: int = Query(20, ge=1, le=100),
    layer4=Depends(get_layer4),
):
    """Get history of recursive learning cycles."""
    try:
        cycles = layer4.cycles[-limit:] if layer4.cycles else []
        
        return {
            "total_cycles": len(layer4.cycles),
            "current_cycle_number": layer4.current_cycle_number,
            "recent_cycles": [c.to_dict() for c in reversed(cycles)],
        }
        
    except Exception as e:
        logger.error(f"[LAYER4-API] History error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADVANCED LAYER 4 ENDPOINTS
# ============================================================================

_advanced_layer4_instance = None


def get_advanced_layer4(layer4=Depends(get_layer4)):
    """Get or create advanced Layer 4 instance."""
    global _advanced_layer4_instance
    
    if _advanced_layer4_instance is None:
        try:
            from ml_intelligence.layer4_advanced_neuro_symbolic import (
                get_advanced_layer4 as create_advanced,
            )
            _advanced_layer4_instance = create_advanced(base_layer4=layer4)
            logger.info("[LAYER4-API] Advanced Layer 4 initialized")
        except Exception as e:
            logger.error(f"[LAYER4-API] Advanced Layer 4 init failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return _advanced_layer4_instance


@router.get("/advanced/status")
async def get_advanced_status(advanced=Depends(get_advanced_layer4)):
    """Get advanced Layer 4 status with all frontier capabilities."""
    try:
        return advanced.get_status()
    except Exception as e:
        logger.error(f"[LAYER4-API] Advanced status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ComposeRequest(BaseModel):
    """Request to compose patterns."""
    operator: str = Field(..., description="union, intersection, composition, negation, sequence, parallel, conditional")
    pattern_ids: List[str] = Field(..., description="Pattern IDs to compose")


@router.post("/advanced/compose")
async def compose_patterns(
    request: ComposeRequest,
    advanced=Depends(get_advanced_layer4),
):
    """
    Compose patterns using algebraic operators.
    
    Operators:
    - union: A OR B
    - intersection: A AND B
    - composition: A then B (pipeline)
    - negation: NOT A
    - sequence: A followed by B
    - parallel: A and B together
    - conditional: if A then B else C
    """
    try:
        composite = advanced.compose_patterns(
            operator=request.operator,
            pattern_ids=request.pattern_ids,
        )
        
        if composite is None:
            raise HTTPException(
                status_code=400,
                detail="Composition failed - check operator and pattern IDs"
            )
        
        return {
            "composite_id": composite.composite_id,
            "operator": composite.operator.value,
            "operands": composite.operands,
            "result_pattern": composite.result_pattern,
            "confidence": composite.confidence,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LAYER4-API] Compose error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SelfModifyingRuleRequest(BaseModel):
    """Request to add a self-modifying rule."""
    premise: Dict[str, Any] = Field(..., description="Rule conditions (IF)")
    conclusion: Dict[str, Any] = Field(..., description="Rule outcome (THEN)")
    confidence: float = Field(0.7, ge=0.0, le=1.0)


@router.post("/advanced/rules/self-modifying")
async def add_self_modifying_rule(
    request: SelfModifyingRuleRequest,
    advanced=Depends(get_advanced_layer4),
):
    """
    Add a self-modifying rule that evolves based on performance.
    
    Rules automatically:
    - Track success/failure
    - Mutate when underperforming
    - Spawn improved variants
    """
    try:
        rule = advanced.add_self_modifying_rule(
            premise=request.premise,
            conclusion=request.conclusion,
            confidence=request.confidence,
        )
        
        return {
            "rule_id": rule.rule_id,
            "premise": rule.premise,
            "conclusion": rule.conclusion,
            "confidence": rule.confidence,
            "generation": rule.generation,
            "mutation_rate": rule.mutation_rate,
        }
        
    except Exception as e:
        logger.error(f"[LAYER4-API] Self-modifying rule error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SoftReasonRequest(BaseModel):
    """Request for soft/differentiable reasoning."""
    predicate: str = Field(..., description="Predicate to query")
    subject_embedding: List[float] = Field(..., description="Subject embedding vector")
    object_embedding: List[float] = Field(..., description="Object embedding vector")


@router.post("/advanced/reason/soft")
async def soft_reason(
    request: SoftReasonRequest,
    advanced=Depends(get_advanced_layer4),
):
    """
    Perform soft/differentiable reasoning.
    
    Uses continuous [0,1] truth values instead of hard True/False.
    Enables gradient-based learning of logical rules.
    """
    try:
        import numpy as np
        
        subject_emb = np.array(request.subject_embedding)
        object_emb = np.array(request.object_embedding)
        
        truth_value, chain = advanced.soft_reason(
            predicate=request.predicate,
            subject_embedding=subject_emb,
            object_embedding=object_emb,
        )
        
        return {
            "predicate": request.predicate,
            "truth_value": truth_value,
            "reasoning_chain": chain,
        }
        
    except Exception as e:
        logger.error(f"[LAYER4-API] Soft reason error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CounterfactualRequest(BaseModel):
    """Request for counterfactual reasoning."""
    original_state: Dict[str, Any] = Field(..., description="Current state")
    intervention: Dict[str, Any] = Field(..., description="What to change")


@router.post("/advanced/counterfactual")
async def counterfactual_reason(
    request: CounterfactualRequest,
    advanced=Depends(get_advanced_layer4),
):
    """
    Counterfactual reasoning: What if we changed X?
    
    Simulates interventions and computes hypothetical outcomes.
    """
    try:
        # Simple outcome function: sum of numeric values
        def outcome_fn(state: Dict[str, Any]) -> float:
            total = 0.0
            for v in state.values():
                if isinstance(v, (int, float)):
                    total += v
            return total
        
        cf = advanced.what_if(
            original_state=request.original_state,
            intervention=request.intervention,
            outcome_fn=outcome_fn,
        )
        
        return {
            "counterfactual_id": cf.counterfactual_id,
            "original_state": cf.original_state,
            "intervention": cf.intervention,
            "counterfactual_state": cf.counterfactual_state,
            "outcome_difference": cf.outcome_difference,
            "confidence": cf.confidence,
            "description": cf.describe(),
        }
        
    except Exception as e:
        logger.error(f"[LAYER4-API] Counterfactual error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TemporalPatternRequest(BaseModel):
    """Request to add temporal pattern."""
    content: Dict[str, Any] = Field(..., description="Pattern content")
    initial_strength: float = Field(1.0, ge=0.0, le=1.0)


@router.post("/advanced/patterns/temporal")
async def add_temporal_pattern(
    request: TemporalPatternRequest,
    advanced=Depends(get_advanced_layer4),
):
    """
    Add a pattern with temporal dynamics.
    
    Patterns:
    - Strengthen with use
    - Decay without use
    - Evolve over time
    """
    try:
        pattern = advanced.track_pattern_temporally(request.content)
        
        return {
            "pattern_id": pattern.pattern_id,
            "content": pattern.content,
            "current_strength": pattern.current_strength,
            "version": pattern.version,
            "decay_rate": pattern.decay_rate,
            "reinforcement_rate": pattern.reinforcement_rate,
        }
        
    except Exception as e:
        logger.error(f"[LAYER4-API] Temporal pattern error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/advanced/patterns/temporal/strongest")
async def get_strongest_patterns(
    n: int = Query(10, ge=1, le=50),
    advanced=Depends(get_advanced_layer4),
):
    """Get the N strongest temporal patterns."""
    try:
        patterns = advanced.temporal_manager.get_strongest(n)
        
        return {
            "count": len(patterns),
            "patterns": [
                {
                    "pattern_id": p.pattern_id,
                    "current_strength": p.current_strength,
                    "peak_strength": p.peak_strength,
                    "activation_count": p.activation_count,
                    "version": p.version,
                    "content": p.content,
                }
                for p in patterns
            ],
        }
        
    except Exception as e:
        logger.error(f"[LAYER4-API] Strongest patterns error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FRONTIER LAYER 4 ENDPOINTS (Maximum Capability)
# ============================================================================

_frontier_layer4_instance = None


def get_frontier_layer4():
    """Get or create frontier Layer 4 instance."""
    global _frontier_layer4_instance
    
    if _frontier_layer4_instance is None:
        try:
            from ml_intelligence.layer4_frontier_reasoning import get_frontier_layer4 as create_frontier
            _frontier_layer4_instance = create_frontier(embedding_dim=256)
            logger.info("[LAYER4-API] Frontier Layer 4 initialized with GPU support")
        except Exception as e:
            logger.error(f"[LAYER4-API] Frontier init failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return _frontier_layer4_instance


@router.get("/frontier/status")
async def get_frontier_status(frontier=Depends(get_frontier_layer4)):
    """Get frontier Layer 4 status with all GPU-accelerated capabilities."""
    try:
        return frontier.get_status()
    except Exception as e:
        logger.error(f"[LAYER4-API] Frontier status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ProveRequest(BaseModel):
    """Request to prove a goal."""
    goal: str = Field(..., description="Goal to prove")
    facts: List[str] = Field(default=[], description="Initial facts")
    rules: List[Dict[str, Any]] = Field(default=[], description="Inference rules")
    max_depth: int = Field(15, ge=1, le=50)
    max_nodes: int = Field(5000, ge=100, le=50000)


@router.post("/frontier/prove")
async def neural_prove(
    request: ProveRequest,
    frontier=Depends(get_frontier_layer4),
):
    """
    Neural Theorem Proving: Prove a goal using neural-guided search.
    
    GPU-accelerated proof search that learns from successful proofs.
    """
    try:
        # Add facts and rules
        for fact in request.facts:
            frontier.theorem_prover.add_fact(fact)
        
        for rule in request.rules:
            frontier.theorem_prover.add_rule(
                name=rule.get("name", str(uuid.uuid4())[:8]),
                premises=rule.get("premises", []),
                conclusion=rule.get("conclusion", ""),
                confidence=rule.get("confidence", 1.0),
            )
        
        # Prove
        proof = frontier.prove(
            request.goal,
            max_depth=request.max_depth,
            max_nodes=request.max_nodes,
        )
        
        return {
            "proof_id": proof.proof_id,
            "goal": proof.goal,
            "success": proof.success,
            "confidence": proof.total_confidence,
            "nodes_explored": proof.nodes_explored,
            "steps": [
                {
                    "rule": s.rule_applied,
                    "premises": s.premises,
                    "conclusion": s.conclusion,
                    "neural_score": s.neural_score,
                }
                for s in proof.steps
            ],
        }
        
    except Exception as e:
        logger.error(f"[LAYER4-API] Prove error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AnalogyRequest(BaseModel):
    """Request to find analogy between domains."""
    source_domain: str
    source_elements: List[Dict[str, Any]]
    target_domain: str
    target_elements: List[Dict[str, Any]]


@router.post("/frontier/analogy")
async def find_analogy(
    request: AnalogyRequest,
    frontier=Depends(get_frontier_layer4),
):
    """
    Structure Mapping: Find structural analogy between domains.
    
    Based on Gentner's Structure Mapping Theory.
    """
    try:
        # Add domains
        frontier.structure_mapper.add_domain(request.source_domain, request.source_elements)
        frontier.structure_mapper.add_domain(request.target_domain, request.target_elements)
        
        # Find mapping
        mapping = frontier.find_analogy(request.source_domain, request.target_domain)
        
        if mapping is None:
            return {"success": False, "message": "No analogy found"}
        
        return {
            "success": True,
            "mapping_id": mapping.mapping_id,
            "score": mapping.score,
            "systematicity": mapping.systematicity,
            "element_mappings": mapping.element_mappings,
        }
        
    except Exception as e:
        logger.error(f"[LAYER4-API] Analogy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SynthesizeRequest(BaseModel):
    """Request to synthesize a program."""
    examples: List[List[Any]] = Field(..., description="List of [input, output] pairs")
    max_iterations: int = Field(1000, ge=10, le=10000)
    max_depth: int = Field(4, ge=1, le=8)


@router.post("/frontier/synthesize")
async def synthesize_program(
    request: SynthesizeRequest,
    frontier=Depends(get_frontier_layer4),
):
    """
    Neural Program Synthesis: Generate code from input-output examples.
    """
    try:
        examples = [(ex[0], ex[1]) for ex in request.examples]
        
        program = frontier.synthesize_program(
            examples,
            max_iterations=request.max_iterations,
            max_depth=request.max_depth,
        )
        
        if program is None:
            return {"success": False, "message": "No program found"}
        
        return {
            "success": True,
            "program_id": program.program_id,
            "code": program.code,
            "confidence": program.confidence,
            "iterations": program.iterations,
        }
        
    except Exception as e:
        logger.error(f"[LAYER4-API] Synthesize error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ExplainRequest(BaseModel):
    """Request to explain observations."""
    observations: List[Dict[str, Any]]
    patterns: List[Dict[str, Any]] = Field(default=[], description="Explanation patterns")


@router.post("/frontier/explain")
async def abductive_explain(
    request: ExplainRequest,
    frontier=Depends(get_frontier_layer4),
):
    """
    Abductive Reasoning: Find the best explanation for observations.
    """
    try:
        # Add patterns
        for pattern in request.patterns:
            frontier.abductive.add_explanation_pattern(
                condition=pattern.get("condition", {}),
                explains=pattern.get("explains", {}),
                probability=pattern.get("probability", 0.5),
            )
        
        # Get explanation
        hypothesis = frontier.explain(request.observations)
        
        if hypothesis is None:
            return {"success": False, "message": "No explanation found"}
        
        return {
            "success": True,
            "hypothesis_id": hypothesis.hypothesis_id,
            "content": hypothesis.content,
            "explains": hypothesis.explains,
            "probability": hypothesis.probability,
            "simplicity": hypothesis.simplicity,
            "coherence": hypothesis.coherence,
        }
        
    except Exception as e:
        logger.error(f"[LAYER4-API] Explain error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ConceptRequest(BaseModel):
    """Request to learn or classify concepts."""
    action: str = Field(..., description="learn or classify")
    concept_name: Optional[str] = None
    embeddings: List[List[float]]


@router.post("/frontier/concept")
async def concept_learning(
    request: ConceptRequest,
    frontier=Depends(get_frontier_layer4),
):
    """
    Concept Formation: Few-shot concept learning and classification.
    """
    try:
        import numpy as np
        
        embeddings = [np.array(e) for e in request.embeddings]
        
        if request.action == "learn":
            if not request.concept_name:
                raise HTTPException(status_code=400, detail="concept_name required for learning")
            
            frontier.learn_concept(request.concept_name, embeddings)
            
            return {
                "success": True,
                "action": "learn",
                "concept": request.concept_name,
                "examples_added": len(embeddings),
            }
        
        elif request.action == "classify":
            results = []
            for emb in embeddings:
                classifications = frontier.classify_concept(emb)
                results.append(classifications)
            
            return {
                "success": True,
                "action": "classify",
                "results": results,
            }
        
        else:
            raise HTTPException(status_code=400, detail="action must be 'learn' or 'classify'")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[LAYER4-API] Concept error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class GraphQueryRequest(BaseModel):
    """Request for graph neural reasoning."""
    nodes: List[Dict[str, Any]] = Field(default=[], description="Nodes to add")
    edges: List[Dict[str, str]] = Field(default=[], description="Edges: source, target, type")
    query_source: str
    query_target: str


@router.post("/frontier/graph-reason")
async def graph_neural_reason(
    request: GraphQueryRequest,
    frontier=Depends(get_frontier_layer4),
):
    """
    Graph Neural Reasoning: Query relations via GNN message passing.
    """
    try:
        # Add nodes
        for node in request.nodes:
            frontier.graph_reasoner.add_node(node.get("id", str(uuid.uuid4())))
        
        # Add edges
        for edge in request.edges:
            frontier.graph_reasoner.add_edge(
                edge["source"],
                edge["target"],
                edge.get("type", "related"),
            )
        
        # Query
        probability = frontier.graph_query(request.query_source, request.query_target)
        
        return {
            "source": request.query_source,
            "target": request.query_target,
            "relation_probability": probability,
            "graph_stats": {
                "nodes": len(frontier.graph_reasoner.node_embeddings),
                "edge_types": len(frontier.graph_reasoner.edge_types),
            },
        }
        
    except Exception as e:
        logger.error(f"[LAYER4-API] Graph reason error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/frontier/meta-stats")
async def get_meta_reasoning_stats(frontier=Depends(get_frontier_layer4)):
    """Get meta-reasoning statistics."""
    try:
        return frontier.meta_reasoner.get_statistics()
    except Exception as e:
        logger.error(f"[LAYER4-API] Meta stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# INTEGRATION HUB ENDPOINTS (Layer 4 ↔ Layer 3/2/1)
# ============================================================================

_integration_hub = None


def get_integration_hub(session: Session = Depends(get_session)):
    """Get Layer 4 integration hub."""
    global _integration_hub
    
    if _integration_hub is None:
        try:
            from genesis.layer4_integration import get_layer4_integration
            _integration_hub = get_layer4_integration(session)
            logger.info("[LAYER4-API] Integration hub initialized")
        except Exception as e:
            logger.error(f"[LAYER4-API] Integration hub failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return _integration_hub


@router.get("/integration/status")
async def get_integration_status(hub=Depends(get_integration_hub)):
    """Get Layer 4 integration status with all connected layers."""
    try:
        return hub.get_status()
    except Exception as e:
        logger.error(f"[LAYER4-API] Integration status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class HealingEventRequest(BaseModel):
    """Healing event for Layer 4 learning."""
    error_type: str
    error_content: str
    fix_applied: str
    success: bool


@router.post("/integration/healing-event")
async def receive_healing_event(
    request: HealingEventRequest,
    hub=Depends(get_integration_hub),
):
    """
    Receive a healing event and learn from it.
    
    This wires self-healing → Layer 4 pattern learning.
    """
    try:
        result = hub.receive_healing_event(
            error_type=request.error_type,
            error_content=request.error_content,
            fix_applied=request.fix_applied,
            success=request.success,
        )
        return result
    except Exception as e:
        logger.error(f"[LAYER4-API] Healing event error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CodeAnalysisRequest(BaseModel):
    """Code analysis for Layer 4 pattern extraction."""
    file_path: str
    analysis_data: Dict[str, Any]


@router.post("/integration/code-analysis")
async def receive_code_analysis(
    request: CodeAnalysisRequest,
    hub=Depends(get_integration_hub),
):
    """
    Receive code analysis and extract patterns.
    
    This wires code analyzer → Layer 4 pattern learning.
    """
    try:
        result = hub.receive_code_analysis(
            file_path=request.file_path,
            analysis_data=request.analysis_data,
        )
        return result
    except Exception as e:
        logger.error(f"[LAYER4-API] Code analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class LearningCycleRequest(BaseModel):
    """Full learning cycle request."""
    domain: str
    data: List[Dict[str, Any]]


@router.post("/integration/learning-cycle")
async def run_integrated_learning_cycle(
    request: LearningCycleRequest,
    hub=Depends(get_integration_hub),
):
    """
    Run a full learning cycle with propagation to Layer 3/2/1.
    
    This is the main entry point for Layer 4 learning that
    automatically exports results to lower layers.
    """
    try:
        result = hub.run_learning_cycle(
            domain=request.domain,
            data=request.data,
        )
        return result
    except Exception as e:
        logger.error(f"[LAYER4-API] Learning cycle error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/integration/sync")
async def sync_pending_exports(hub=Depends(get_integration_hub)):
    """Sync any pending exports to lower layers."""
    try:
        return hub.sync_pending_exports()
    except Exception as e:
        logger.error(f"[LAYER4-API] Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
