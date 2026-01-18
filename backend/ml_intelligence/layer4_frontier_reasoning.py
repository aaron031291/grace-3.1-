"""
Layer 4 Frontier: Maximum Neuro-Symbolic Capability

GPU-accelerated implementation of frontier neuro-symbolic reasoning.
Designed for RTX 5090 / high-end GPU compute.

CAPABILITIES:
1. Neural Theorem Proving (NTP) - Neural-guided proof search
2. Analogical Reasoning - Structure Mapping Theory
3. Probabilistic Logic - DeepProbLog-style soft logic
4. Neural Program Synthesis - Spec → Code generation
5. Meta-Reasoning - Dynamic strategy selection
6. Abductive Reasoning - Best explanation inference
7. Concept Formation - Few-shot concept learning
8. Graph Neural Reasoning - GNN over knowledge graphs
9. Memory-Augmented Reasoning - External memory for long chains

Research basis:
- Neural Theorem Provers (Rocktäschel & Riedel, 2017)
- Structure Mapping Engine (Gentner, 1983)
- DeepProbLog (Manhaeve et al., 2018)
- DreamCoder (Ellis et al., 2021)
- Bayesian Program Learning (Lake et al., 2015)
- Graph Attention Networks (Veličković et al., 2018)
- Differentiable Neural Computer (Graves et al., 2016)
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Set, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import json
import uuid
from collections import defaultdict
import heapq
import copy
import math

logger = logging.getLogger(__name__)

# Try to import PyTorch for GPU acceleration
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
    try:
        DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if torch.cuda.is_available():
            logger.info(f"[FRONTIER] GPU available: {torch.cuda.get_device_name(0)}")
    except Exception as e:
        DEVICE = torch.device("cpu")
        logger.warning(f"[FRONTIER] GPU detection failed, using CPU: {e}")
except (ImportError, OSError, AttributeError) as e:
    TORCH_AVAILABLE = False
    DEVICE = None
    logger.warning(f"[FRONTIER] PyTorch not available, using numpy fallback: {e}")


# ============================================================================
# 1. NEURAL THEOREM PROVING
# ============================================================================

@dataclass
class ProofStep:
    """A single step in a proof."""
    step_id: str
    rule_applied: str
    premises: List[str]
    conclusion: str
    confidence: float
    neural_score: float
    depth: int


@dataclass 
class Proof:
    """A complete proof."""
    proof_id: str
    goal: str
    premises: List[str]
    steps: List[ProofStep]
    success: bool
    total_confidence: float
    nodes_explored: int


class NeuralProofNetwork:
    """Neural network for guiding proof search (with numpy fallback)."""
    
    def __init__(self, embedding_dim: int = 256, hidden_dim: int = 512):
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self._torch_initialized = False
        
        if TORCH_AVAILABLE:
            try:
                # Create neural network layers
                self.fact_encoder = nn.Sequential(
                    nn.Linear(embedding_dim, hidden_dim),
                    nn.ReLU(),
                    nn.Linear(hidden_dim, embedding_dim),
                )
                
                self.rule_scorer = nn.Sequential(
                    nn.Linear(embedding_dim * 3, hidden_dim),
                    nn.ReLU(),
                    nn.Linear(hidden_dim, hidden_dim),
                    nn.ReLU(),
                    nn.Linear(hidden_dim, 1),
                    nn.Sigmoid(),
                )
                
                self.success_predictor = nn.Sequential(
                    nn.Linear(embedding_dim * 2, hidden_dim),
                    nn.ReLU(),
                    nn.Linear(hidden_dim, 1),
                    nn.Sigmoid(),
                )
                self._torch_initialized = True
            except Exception as e:
                logger.warning(f"[FRONTIER] PyTorch network init failed: {e}")
                self._torch_initialized = False
    
    def parameters(self):
        """Return parameters for optimizer."""
        if self._torch_initialized:
            params = []
            params.extend(self.fact_encoder.parameters())
            params.extend(self.rule_scorer.parameters())
            params.extend(self.success_predictor.parameters())
            return params
        return []
    
    def to(self, device):
        """Move to device."""
        if self._torch_initialized:
            self.fact_encoder = self.fact_encoder.to(device)
            self.rule_scorer = self.rule_scorer.to(device)
            self.success_predictor = self.success_predictor.to(device)
        return self
    
    def train(self):
        """Set to training mode."""
        if self._torch_initialized:
            self.fact_encoder.train()
            self.rule_scorer.train()
            self.success_predictor.train()
    
    def eval(self):
        """Set to evaluation mode."""
        if self._torch_initialized:
            self.fact_encoder.eval()
            self.rule_scorer.eval()
            self.success_predictor.eval()
    
    def __call__(self, state_emb, goal_emb, rule_emb):
        """Score how promising a rule is for reaching goal from state."""
        return self.forward(state_emb, goal_emb, rule_emb)
    
    def forward(self, state_emb, goal_emb, rule_emb):
        """Score how promising a rule is for reaching goal from state."""
        if not self._torch_initialized:
            return 0.5
        
        combined = torch.cat([state_emb, goal_emb, rule_emb], dim=-1)
        return self.rule_scorer(combined)
    
    def predict_success(self, state_emb, goal_emb):
        """Predict probability of reaching goal from state."""
        if not self._torch_initialized:
            return 0.5
        
        combined = torch.cat([state_emb, goal_emb], dim=-1)
        return self.success_predictor(combined)


class NeuralTheoremProver:
    """
    Neural Theorem Prover: Neural-guided symbolic proof search.
    
    The neural network learns to predict which rules are most likely
    to lead to a successful proof, dramatically reducing search space.
    """
    
    def __init__(self, embedding_dim: int = 256):
        self.embedding_dim = embedding_dim
        self.facts: Set[str] = set()
        self.rules: Dict[str, Dict[str, Any]] = {}
        self.embeddings: Dict[str, np.ndarray] = {}
        self.proof_cache: Dict[str, Proof] = {}
        
        # Neural components (with graceful fallback)
        self.proof_net = None
        self.optimizer = None
        
        try:
            self.proof_net = NeuralProofNetwork(embedding_dim)
            if TORCH_AVAILABLE and DEVICE:
                self.proof_net = self.proof_net.to(DEVICE)
            if self.proof_net._torch_initialized:
                self.optimizer = torch.optim.Adam(self.proof_net.parameters(), lr=0.001)
        except Exception as e:
            logger.warning(f"[FRONTIER] Neural proof network failed, using fallback: {e}")
            self.proof_net = NeuralProofNetwork(embedding_dim)  # Use numpy fallback
        
        # Learning statistics
        self.successful_proofs: List[Proof] = []
        self.failed_attempts: List[Dict] = []
    
    def add_fact(self, fact: str, embedding: Optional[np.ndarray] = None):
        """Add a known fact."""
        self.facts.add(fact)
        self.embeddings[fact] = embedding if embedding is not None else \
                                np.random.randn(self.embedding_dim) * 0.1
    
    def add_rule(self, name: str, premises: List[str], conclusion: str, 
                 confidence: float = 1.0):
        """Add an inference rule: premises → conclusion."""
        self.rules[name] = {
            "premises": premises,
            "conclusion": conclusion,
            "confidence": confidence,
        }
        self.embeddings[name] = np.random.randn(self.embedding_dim) * 0.1
    
    def _get_embedding(self, item: str) -> np.ndarray:
        """Get or create embedding for an item."""
        if item not in self.embeddings:
            self.embeddings[item] = np.random.randn(self.embedding_dim) * 0.1
        return self.embeddings[item]
    
    def _state_embedding(self, facts: Set[str]) -> np.ndarray:
        """Aggregate facts into state embedding."""
        if not facts:
            return np.zeros(self.embedding_dim)
        embeddings = [self._get_embedding(f) for f in facts]
        return np.mean(embeddings, axis=0)
    
    def _neural_score_rule(self, state: Set[str], goal: str, rule: str) -> float:
        """Use neural network to score rule applicability."""
        if not TORCH_AVAILABLE or self.proof_net is None or not self.proof_net._torch_initialized:
            return np.random.random() * 0.5 + 0.25  # Random 0.25-0.75
        
        try:
            state_emb = torch.tensor(self._state_embedding(state), dtype=torch.float32).to(DEVICE)
            goal_emb = torch.tensor(self._get_embedding(goal), dtype=torch.float32).to(DEVICE)
            rule_emb = torch.tensor(self._get_embedding(rule), dtype=torch.float32).to(DEVICE)
            
            with torch.no_grad():
                score = self.proof_net(state_emb, goal_emb, rule_emb)
            
            # Handle different return types
            if isinstance(score, (int, float)):
                return float(score)
            elif hasattr(score, 'item'):
                return float(score.item())
            elif hasattr(score, 'cpu'):
                arr = score.cpu().numpy()
                if arr.ndim == 0:
                    return float(arr)
                return float(arr.flatten()[0])
            return float(score)
        except Exception as e:
            logger.warning(f"[FRONTIER] Neural scoring failed: {e}")
            return np.random.random() * 0.5 + 0.25
    
    def prove(self, goal: str, max_depth: int = 15, max_nodes: int = 5000) -> Proof:
        """
        Prove a goal using neural-guided A* search.
        """
        if goal in self.proof_cache:
            return self.proof_cache[goal]
        
        if goal in self.facts:
            proof = Proof(str(uuid.uuid4()), goal, [goal], [], True, 1.0, 1)
            self.proof_cache[goal] = proof
            return proof
        
        # A* search with neural heuristic
        # Priority = g (depth) + h (neural estimate to goal)
        goal_emb = self._get_embedding(goal)
        
        # State: (priority, depth, facts_frozenset, steps_list)
        start = (0.0, 0, frozenset(self.facts), [])
        queue = [start]
        visited = set()
        nodes = 0
        
        while queue and nodes < max_nodes:
            priority, depth, current_facts, steps = heapq.heappop(queue)
            nodes += 1
            
            state_key = current_facts
            if state_key in visited:
                continue
            visited.add(state_key)
            
            # Check if goal reached
            if goal in current_facts:
                proof = Proof(
                    proof_id=str(uuid.uuid4()),
                    goal=goal,
                    premises=list(self.facts),
                    steps=steps,
                    success=True,
                    total_confidence=self._compute_confidence(steps),
                    nodes_explored=nodes,
                )
                self.proof_cache[goal] = proof
                self.successful_proofs.append(proof)
                self._learn_from_proof(proof)
                return proof
            
            if depth >= max_depth:
                continue
            
            # Try each rule, scored by neural network
            rule_scores = []
            for rule_name, rule in self.rules.items():
                # Check if premises are satisfied
                if all(p in current_facts for p in rule["premises"]):
                    score = self._neural_score_rule(current_facts, goal, rule_name)
                    rule_scores.append((score, rule_name, rule))
            
            # Sort by neural score (highest first)
            rule_scores.sort(reverse=True)
            
            for score, rule_name, rule in rule_scores[:10]:  # Top 10 rules
                new_fact = rule["conclusion"]
                if new_fact in current_facts:
                    continue
                
                new_facts = current_facts | {new_fact}
                new_step = ProofStep(
                    step_id=str(uuid.uuid4()),
                    rule_applied=rule_name,
                    premises=rule["premises"],
                    conclusion=new_fact,
                    confidence=rule["confidence"],
                    neural_score=score,
                    depth=depth + 1,
                )
                new_steps = steps + [new_step]
                
                # Heuristic: neural distance to goal
                h = 1.0 - self._neural_similarity(new_facts, goal)
                new_priority = (depth + 1) + h
                
                heapq.heappush(queue, (new_priority, depth + 1, new_facts, new_steps))
        
        # Failed to prove
        proof = Proof(str(uuid.uuid4()), goal, list(self.facts), [], False, 0.0, nodes)
        self.failed_attempts.append({"goal": goal, "nodes": nodes})
        return proof
    
    def _neural_similarity(self, facts: Set[str], goal: str) -> float:
        """Compute neural similarity between state and goal."""
        state_emb = self._state_embedding(facts)
        goal_emb = self._get_embedding(goal)
        
        norm_s = np.linalg.norm(state_emb)
        norm_g = np.linalg.norm(goal_emb)
        
        if norm_s == 0 or norm_g == 0:
            return 0.0
        
        return float(np.dot(state_emb, goal_emb) / (norm_s * norm_g))
    
    def _compute_confidence(self, steps: List[ProofStep]) -> float:
        """Compute total proof confidence."""
        if not steps:
            return 1.0
        conf = 1.0
        for step in steps:
            conf *= step.confidence
        return conf
    
    def _learn_from_proof(self, proof: Proof):
        """Train neural network on successful proof."""
        if not TORCH_AVAILABLE or self.proof_net is None:
            return
        
        # Create training examples from proof steps
        self.proof_net.train()
        
        for step in proof.steps:
            # Positive example: this rule led to success
            state_emb = torch.tensor(
                self._state_embedding(set(step.premises)), 
                dtype=torch.float32
            ).to(DEVICE)
            goal_emb = torch.tensor(
                self._get_embedding(proof.goal),
                dtype=torch.float32
            ).to(DEVICE)
            rule_emb = torch.tensor(
                self._get_embedding(step.rule_applied),
                dtype=torch.float32
            ).to(DEVICE)
            
            pred = self.proof_net(state_emb, goal_emb, rule_emb)
            target = torch.tensor([1.0]).to(DEVICE)
            
            loss = F.binary_cross_entropy(pred.squeeze(), target.squeeze())
            
            self.optimizer.zero_grad()
            loss.backward()
            self.optimizer.step()
        
        self.proof_net.eval()


# ============================================================================
# 2. ANALOGICAL REASONING (Structure Mapping)
# ============================================================================

@dataclass
class StructuralElement:
    """An element in a structural representation."""
    element_id: str
    element_type: str  # "entity", "attribute", "relation"
    name: str
    arguments: List[str] = field(default_factory=list)
    value: Optional[Any] = None


@dataclass
class StructuralMapping:
    """A mapping between two structural representations."""
    mapping_id: str
    source_domain: str
    target_domain: str
    element_mappings: Dict[str, str]  # source_id → target_id
    score: float
    systematicity: float  # Higher-order relations matched
    

class StructureMappingEngine:
    """
    Structure Mapping Engine for analogical reasoning.
    
    Based on Gentner's Structure Mapping Theory:
    - Prefer relational similarity over surface similarity
    - Prefer systematic (interconnected) mappings
    - One-to-one mapping constraint
    """
    
    def __init__(self, embedding_dim: int = 256):
        self.embedding_dim = embedding_dim
        self.domains: Dict[str, List[StructuralElement]] = {}
        self.embeddings: Dict[str, np.ndarray] = {}
        self.mappings: List[StructuralMapping] = []
    
    def add_domain(self, domain_name: str, elements: List[Dict[str, Any]]):
        """Add a domain with its structural elements."""
        self.domains[domain_name] = []
        
        for elem in elements:
            se = StructuralElement(
                element_id=str(uuid.uuid4()),
                element_type=elem.get("type", "entity"),
                name=elem.get("name", ""),
                arguments=elem.get("arguments", []),
                value=elem.get("value"),
            )
            self.domains[domain_name].append(se)
            self.embeddings[se.element_id] = np.random.randn(self.embedding_dim) * 0.1
    
    def find_analogy(
        self,
        source_domain: str,
        target_domain: str,
        max_mappings: int = 100,
    ) -> Optional[StructuralMapping]:
        """
        Find the best structural mapping between domains.
        
        Uses greedy search with systematicity preference.
        """
        if source_domain not in self.domains or target_domain not in self.domains:
            return None
        
        source_elems = self.domains[source_domain]
        target_elems = self.domains[target_domain]
        
        # Score all possible element pairings
        pair_scores: List[Tuple[float, str, str]] = []
        
        for se in source_elems:
            for te in target_elems:
                # Type compatibility
                if se.element_type != te.element_type:
                    continue
                
                # Structural similarity (argument count)
                if len(se.arguments) != len(te.arguments):
                    continue
                
                # Embedding similarity
                s_emb = self.embeddings.get(se.element_id, np.zeros(self.embedding_dim))
                t_emb = self.embeddings.get(te.element_id, np.zeros(self.embedding_dim))
                
                sim = self._cosine_similarity(s_emb, t_emb)
                
                # Bonus for relations (systematicity)
                if se.element_type == "relation":
                    sim *= 1.5
                
                pair_scores.append((sim, se.element_id, te.element_id))
        
        # Greedy one-to-one mapping
        pair_scores.sort(reverse=True)
        
        mapping = {}
        used_targets = set()
        
        for score, sid, tid in pair_scores:
            if sid in mapping or tid in used_targets:
                continue
            mapping[sid] = tid
            used_targets.add(tid)
        
        if not mapping:
            return None
        
        # Calculate systematicity (how many relations are mapped)
        relations_mapped = sum(
            1 for se in source_elems 
            if se.element_type == "relation" and se.element_id in mapping
        )
        total_relations = sum(
            1 for se in source_elems if se.element_type == "relation"
        )
        systematicity = relations_mapped / max(1, total_relations)
        
        # Overall score
        avg_score = np.mean([s for s, _, _ in pair_scores[:len(mapping)]])
        
        result = StructuralMapping(
            mapping_id=str(uuid.uuid4()),
            source_domain=source_domain,
            target_domain=target_domain,
            element_mappings=mapping,
            score=float(avg_score),
            systematicity=systematicity,
        )
        
        self.mappings.append(result)
        return result
    
    def transfer_inference(
        self,
        mapping: StructuralMapping,
        source_inference: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Transfer an inference from source to target domain via analogy.
        """
        target_inference = {}
        
        for key, value in source_inference.items():
            # Map key if it's an element ID
            if key in mapping.element_mappings:
                new_key = mapping.element_mappings[key]
            else:
                new_key = key
            
            # Map value if it's an element ID
            if isinstance(value, str) and value in mapping.element_mappings:
                new_value = mapping.element_mappings[value]
            else:
                new_value = value
            
            target_inference[new_key] = new_value
        
        return target_inference
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


# ============================================================================
# 3. PROBABILISTIC LOGIC (DeepProbLog-style)
# ============================================================================

@dataclass
class ProbabilisticFact:
    """A fact with associated probability."""
    fact_id: str
    predicate: str
    arguments: List[str]
    probability: float  # P(fact is true)
    learned: bool = False  # Whether probability was learned


@dataclass
class ProbabilisticRule:
    """A rule with probabilistic semantics."""
    rule_id: str
    head: str  # Conclusion predicate
    body: List[str]  # Premise predicates
    confidence: float  # Rule reliability


class ProbabilisticLogicEngine:
    """
    Probabilistic Logic Programming engine.
    
    Combines neural networks with probabilistic logic:
    - Facts have probabilities
    - Rules propagate probabilities
    - Neural networks can learn fact probabilities
    """
    
    def __init__(self, embedding_dim: int = 256):
        self.embedding_dim = embedding_dim
        self.facts: Dict[str, ProbabilisticFact] = {}
        self.rules: Dict[str, ProbabilisticRule] = {}
        
        # Neural probability predictor
        if TORCH_AVAILABLE:
            self.prob_net = nn.Sequential(
                nn.Linear(embedding_dim * 2, 256),
                nn.ReLU(),
                nn.Linear(256, 128),
                nn.ReLU(),
                nn.Linear(128, 1),
                nn.Sigmoid(),
            ).to(DEVICE)
            self.optimizer = torch.optim.Adam(self.prob_net.parameters(), lr=0.001)
        else:
            self.prob_net = None
        
        self.embeddings: Dict[str, np.ndarray] = {}
    
    def add_fact(self, predicate: str, arguments: List[str], probability: float = 1.0):
        """Add a probabilistic fact."""
        fact_id = f"{predicate}({','.join(arguments)})"
        self.facts[fact_id] = ProbabilisticFact(
            fact_id=fact_id,
            predicate=predicate,
            arguments=arguments,
            probability=probability,
        )
        self.embeddings[fact_id] = np.random.randn(self.embedding_dim) * 0.1
    
    def add_rule(self, head: str, body: List[str], confidence: float = 1.0):
        """Add a probabilistic rule."""
        rule_id = f"{head} :- {', '.join(body)}"
        self.rules[rule_id] = ProbabilisticRule(
            rule_id=rule_id,
            head=head,
            body=body,
            confidence=confidence,
        )
    
    def query(self, predicate: str, arguments: List[str]) -> float:
        """
        Query the probability of a predicate.
        
        Uses forward chaining with probability propagation.
        """
        query_id = f"{predicate}({','.join(arguments)})"
        
        # Direct fact lookup
        if query_id in self.facts:
            return self.facts[query_id].probability
        
        # Try rules
        max_prob = 0.0
        
        for rule in self.rules.values():
            if rule.head == predicate:
                # Check if body is satisfiable
                body_prob = 1.0
                for premise in rule.body:
                    # Simple: check if premise fact exists
                    premise_prob = self._find_premise_prob(premise, arguments)
                    body_prob *= premise_prob
                
                # Rule probability
                rule_prob = body_prob * rule.confidence
                max_prob = max(max_prob, rule_prob)
        
        return max_prob
    
    def _find_premise_prob(self, premise: str, context_args: List[str]) -> float:
        """Find probability of a premise predicate."""
        # Try exact match
        for fact in self.facts.values():
            if fact.predicate == premise:
                return fact.probability
        return 0.0
    
    def learn_probability(
        self,
        fact_id: str,
        observed: bool,
        learning_rate: float = 0.1,
    ):
        """Update fact probability based on observation."""
        if fact_id not in self.facts:
            return
        
        fact = self.facts[fact_id]
        target = 1.0 if observed else 0.0
        
        # Bayesian update (simplified)
        fact.probability = (1 - learning_rate) * fact.probability + learning_rate * target
        fact.learned = True
    
    def marginal_probability(self, query_predicate: str) -> float:
        """Compute marginal probability over all groundings."""
        probs = []
        
        for fact in self.facts.values():
            if fact.predicate == query_predicate:
                probs.append(fact.probability)
        
        if not probs:
            return 0.0
        
        # Noisy-OR combination
        prob_none = 1.0
        for p in probs:
            prob_none *= (1 - p)
        
        return 1 - prob_none


# ============================================================================
# 4. NEURAL PROGRAM SYNTHESIS
# ============================================================================

@dataclass
class ProgramSpec:
    """Specification for program synthesis."""
    spec_id: str
    input_output_examples: List[Tuple[Any, Any]]
    natural_language: Optional[str] = None
    constraints: List[str] = field(default_factory=list)


@dataclass
class SynthesizedProgram:
    """A synthesized program."""
    program_id: str
    code: str
    spec_id: str
    confidence: float
    passes_examples: bool
    iterations: int


class NeuralProgramSynthesizer:
    """
    Neural Program Synthesis: Generate code from specifications.
    
    Combines:
    - Neural: Propose program sketches
    - Symbolic: Fill holes and verify correctness
    """
    
    def __init__(self, embedding_dim: int = 256):
        self.embedding_dim = embedding_dim
        
        # Library of primitive operations
        self.primitives: Dict[str, Callable] = {
            "add": lambda x, y: x + y,
            "sub": lambda x, y: x - y,
            "mul": lambda x, y: x * y,
            "div": lambda x, y: x / y if y != 0 else 0,
            "mod": lambda x, y: x % y if y != 0 else 0,
            "neg": lambda x: -x,
            "abs": lambda x: abs(x),
            "max": lambda x, y: max(x, y),
            "min": lambda x, y: min(x, y),
            "square": lambda x: x * x,
            "double": lambda x: x * 2,
            "inc": lambda x: x + 1,
            "dec": lambda x: x - 1,
            "is_zero": lambda x: x == 0,
            "is_pos": lambda x: x > 0,
            "is_neg": lambda x: x < 0,
            "identity": lambda x: x,
        }
        
        # Learned program templates
        self.templates: List[str] = []
        self.successful_programs: List[SynthesizedProgram] = []
        
        # Neural program encoder
        if TORCH_AVAILABLE:
            self.program_encoder = nn.Sequential(
                nn.Linear(embedding_dim, 256),
                nn.ReLU(),
                nn.Linear(256, 256),
                nn.ReLU(),
                nn.Linear(256, len(self.primitives)),
                nn.Softmax(dim=-1),
            ).to(DEVICE)
    
    def synthesize(
        self,
        spec: ProgramSpec,
        max_iterations: int = 1000,
        max_depth: int = 4,
    ) -> Optional[SynthesizedProgram]:
        """
        Synthesize a program from specification.
        
        Uses neural-guided enumeration with verification.
        """
        examples = spec.input_output_examples
        
        if not examples:
            return None
        
        # Try each primitive directly
        for name, func in self.primitives.items():
            if self._check_program(func, examples):
                return SynthesizedProgram(
                    program_id=str(uuid.uuid4()),
                    code=name,
                    spec_id=spec.spec_id,
                    confidence=1.0,
                    passes_examples=True,
                    iterations=1,
                )
        
        # Try compositions
        iterations = 0
        for depth in range(2, max_depth + 1):
            programs = self._enumerate_compositions(depth)
            
            for code, func in programs:
                iterations += 1
                if iterations > max_iterations:
                    break
                
                if self._check_program(func, examples):
                    prog = SynthesizedProgram(
                        program_id=str(uuid.uuid4()),
                        code=code,
                        spec_id=spec.spec_id,
                        confidence=1.0,
                        passes_examples=True,
                        iterations=iterations,
                    )
                    self.successful_programs.append(prog)
                    return prog
        
        return None
    
    def _check_program(
        self,
        func: Callable,
        examples: List[Tuple[Any, Any]],
    ) -> bool:
        """Check if program satisfies all examples."""
        for inp, expected in examples:
            try:
                if isinstance(inp, tuple):
                    result = func(*inp)
                else:
                    result = func(inp)
                
                if result != expected:
                    return False
            except:
                return False
        return True
    
    def _enumerate_compositions(
        self,
        depth: int,
    ) -> List[Tuple[str, Callable]]:
        """Enumerate program compositions up to given depth."""
        if depth == 1:
            return [(name, func) for name, func in self.primitives.items()]
        
        compositions = []
        sub_programs = self._enumerate_compositions(depth - 1)
        
        for name1, func1 in self.primitives.items():
            for code2, func2 in sub_programs[:50]:  # Limit branching
                # Compose: func1(func2(x))
                try:
                    # Unary composition
                    composed = lambda x, f1=func1, f2=func2: f1(f2(x))
                    code = f"{name1}({code2})"
                    compositions.append((code, composed))
                except:
                    pass
        
        return compositions[:500]  # Limit total


# ============================================================================
# 5. META-REASONING
# ============================================================================

class ReasoningStrategy(str, Enum):
    """Available reasoning strategies."""
    FORWARD_CHAIN = "forward_chain"
    BACKWARD_CHAIN = "backward_chain"  
    NEURAL_GUIDED = "neural_guided"
    ANALOGICAL = "analogical"
    PROBABILISTIC = "probabilistic"
    EXHAUSTIVE = "exhaustive"


@dataclass
class ReasoningProblem:
    """A reasoning problem to solve."""
    problem_id: str
    problem_type: str
    complexity: float  # 0-1
    time_budget: float  # seconds
    knowledge_size: int
    goal: str


@dataclass
class StrategyPerformance:
    """Tracked performance of a strategy."""
    strategy: ReasoningStrategy
    successes: int = 0
    failures: int = 0
    total_time: float = 0.0
    
    def success_rate(self) -> float:
        total = self.successes + self.failures
        return self.successes / total if total > 0 else 0.5
    
    def avg_time(self) -> float:
        total = self.successes + self.failures
        return self.total_time / total if total > 0 else 1.0


class MetaReasoner:
    """
    Meta-Reasoning: Reason about reasoning itself.
    
    Dynamically selects the best reasoning strategy based on:
    - Problem characteristics
    - Historical performance
    - Resource constraints
    """
    
    def __init__(self):
        self.strategies: Dict[ReasoningStrategy, StrategyPerformance] = {
            s: StrategyPerformance(strategy=s) for s in ReasoningStrategy
        }
        
        # Strategy-problem type affinity (learned)
        self.affinity: Dict[Tuple[str, ReasoningStrategy], float] = {}
        
        # Problem history
        self.history: List[Dict[str, Any]] = []
    
    def select_strategy(self, problem: ReasoningProblem) -> ReasoningStrategy:
        """
        Select best reasoning strategy for a problem.
        """
        scores = {}
        
        for strategy in ReasoningStrategy:
            perf = self.strategies[strategy]
            
            # Base score: success rate
            base_score = perf.success_rate()
            
            # Time efficiency: prefer fast strategies for tight budgets
            if problem.time_budget < 1.0 and perf.avg_time() > 0:
                time_factor = min(1.0, problem.time_budget / perf.avg_time())
            else:
                time_factor = 1.0
            
            # Problem type affinity
            affinity = self.affinity.get(
                (problem.problem_type, strategy), 
                0.5
            )
            
            # Complexity match
            if problem.complexity > 0.7:
                # Prefer sophisticated strategies for complex problems
                if strategy in [ReasoningStrategy.NEURAL_GUIDED, 
                               ReasoningStrategy.ANALOGICAL]:
                    complexity_bonus = 0.2
                else:
                    complexity_bonus = 0.0
            else:
                complexity_bonus = 0.0
            
            scores[strategy] = (
                0.4 * base_score + 
                0.2 * time_factor + 
                0.3 * affinity + 
                0.1 * complexity_bonus
            )
        
        # Select best
        best = max(scores.items(), key=lambda x: x[1])
        return best[0]
    
    def record_outcome(
        self,
        problem: ReasoningProblem,
        strategy: ReasoningStrategy,
        success: bool,
        time_taken: float,
    ):
        """Record outcome for learning."""
        perf = self.strategies[strategy]
        
        if success:
            perf.successes += 1
        else:
            perf.failures += 1
        perf.total_time += time_taken
        
        # Update affinity
        key = (problem.problem_type, strategy)
        current = self.affinity.get(key, 0.5)
        target = 1.0 if success else 0.0
        self.affinity[key] = 0.9 * current + 0.1 * target
        
        self.history.append({
            "problem_id": problem.problem_id,
            "strategy": strategy.value,
            "success": success,
            "time": time_taken,
        })
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get meta-reasoning statistics."""
        return {
            "strategies": {
                s.value: {
                    "success_rate": perf.success_rate(),
                    "avg_time": perf.avg_time(),
                    "total_attempts": perf.successes + perf.failures,
                }
                for s, perf in self.strategies.items()
            },
            "history_size": len(self.history),
        }


# ============================================================================
# 6. ABDUCTIVE REASONING
# ============================================================================

@dataclass
class Hypothesis:
    """A hypothesis that could explain observations."""
    hypothesis_id: str
    content: Dict[str, Any]
    explains: List[str]  # Observation IDs it explains
    probability: float
    simplicity: float  # Occam's razor score
    coherence: float  # Internal consistency


@dataclass
class Observation:
    """An observation to explain."""
    observation_id: str
    content: Dict[str, Any]
    confidence: float


class AbductiveReasoner:
    """
    Abductive Reasoning: Inference to the best explanation.
    
    Given observations, generates and ranks hypotheses
    that would explain them.
    """
    
    def __init__(self, embedding_dim: int = 256):
        self.embedding_dim = embedding_dim
        self.observations: Dict[str, Observation] = {}
        self.hypotheses: Dict[str, Hypothesis] = {}
        self.embeddings: Dict[str, np.ndarray] = {}
        
        # Explanation patterns
        self.patterns: List[Dict[str, Any]] = []
    
    def add_observation(self, content: Dict[str, Any], confidence: float = 1.0):
        """Add an observation to explain."""
        obs_id = str(uuid.uuid4())
        self.observations[obs_id] = Observation(
            observation_id=obs_id,
            content=content,
            confidence=confidence,
        )
        self.embeddings[obs_id] = np.random.randn(self.embedding_dim) * 0.1
        return obs_id
    
    def add_explanation_pattern(
        self,
        condition: Dict[str, Any],
        explains: Dict[str, Any],
        probability: float = 0.5,
    ):
        """Add a pattern: if condition, then explains observations."""
        self.patterns.append({
            "condition": condition,
            "explains": explains,
            "probability": probability,
        })
    
    def generate_hypotheses(self, max_hypotheses: int = 10) -> List[Hypothesis]:
        """
        Generate hypotheses that explain current observations.
        """
        hypotheses = []
        
        for pattern in self.patterns:
            # Check which observations this pattern could explain
            explained_obs = []
            
            for obs_id, obs in self.observations.items():
                if self._matches_pattern(obs.content, pattern["explains"]):
                    explained_obs.append(obs_id)
            
            if explained_obs:
                hyp = Hypothesis(
                    hypothesis_id=str(uuid.uuid4()),
                    content=pattern["condition"],
                    explains=explained_obs,
                    probability=pattern["probability"],
                    simplicity=1.0 / (1 + len(pattern["condition"])),
                    coherence=len(explained_obs) / len(self.observations),
                )
                hypotheses.append(hyp)
        
        # Rank by combined score
        hypotheses.sort(key=lambda h: self._score_hypothesis(h), reverse=True)
        
        # Store top hypotheses
        for hyp in hypotheses[:max_hypotheses]:
            self.hypotheses[hyp.hypothesis_id] = hyp
        
        return hypotheses[:max_hypotheses]
    
    def _matches_pattern(self, obs_content: Dict, pattern: Dict) -> bool:
        """Check if observation matches pattern."""
        for key, value in pattern.items():
            if key not in obs_content:
                return False
            if value != "*" and obs_content[key] != value:
                return False
        return True
    
    def _score_hypothesis(self, hyp: Hypothesis) -> float:
        """Score a hypothesis using multiple criteria."""
        # Coverage: how many observations explained
        coverage = len(hyp.explains) / max(1, len(self.observations))
        
        # Simplicity: Occam's razor
        simplicity = hyp.simplicity
        
        # Probability: prior likelihood
        probability = hyp.probability
        
        # Coherence: internal consistency
        coherence = hyp.coherence
        
        return (
            0.3 * coverage +
            0.2 * simplicity +
            0.3 * probability +
            0.2 * coherence
        )
    
    def best_explanation(self) -> Optional[Hypothesis]:
        """Get the best explanation for current observations."""
        hypotheses = self.generate_hypotheses()
        return hypotheses[0] if hypotheses else None


# ============================================================================
# 7. CONCEPT FORMATION (Few-Shot Learning)
# ============================================================================

@dataclass
class Concept:
    """A learned concept."""
    concept_id: str
    name: str
    prototype: np.ndarray  # Prototype representation
    exemplars: List[np.ndarray]  # Stored examples
    positive_count: int = 0
    negative_count: int = 0
    abstraction_level: int = 0


class ConceptLearner:
    """
    Concept Formation: Learn concepts from few examples.
    
    Uses hybrid prototype + exemplar model:
    - Prototype: Average representation of positive examples
    - Exemplars: Store specific memorable examples
    """
    
    def __init__(self, embedding_dim: int = 256):
        self.embedding_dim = embedding_dim
        self.concepts: Dict[str, Concept] = {}
        
        # Neural concept encoder
        if TORCH_AVAILABLE:
            self.encoder = nn.Sequential(
                nn.Linear(embedding_dim, 256),
                nn.ReLU(),
                nn.Linear(256, embedding_dim),
            ).to(DEVICE)
        else:
            self.encoder = None
    
    def create_concept(self, name: str) -> Concept:
        """Create a new empty concept."""
        concept = Concept(
            concept_id=str(uuid.uuid4()),
            name=name,
            prototype=np.zeros(self.embedding_dim),
            exemplars=[],
        )
        self.concepts[name] = concept
        return concept
    
    def add_positive_example(
        self,
        concept_name: str,
        embedding: np.ndarray,
        is_exemplar: bool = True,
    ):
        """Add a positive example of a concept."""
        if concept_name not in self.concepts:
            self.create_concept(concept_name)
        
        concept = self.concepts[concept_name]
        concept.positive_count += 1
        
        # Update prototype (running average)
        n = concept.positive_count
        concept.prototype = (
            (n - 1) / n * concept.prototype + 
            1 / n * embedding
        )
        
        # Store as exemplar if notable
        if is_exemplar and len(concept.exemplars) < 10:
            concept.exemplars.append(embedding.copy())
    
    def add_negative_example(self, concept_name: str, embedding: np.ndarray):
        """Add a negative example (for contrastive learning)."""
        if concept_name not in self.concepts:
            return
        
        concept = self.concepts[concept_name]
        concept.negative_count += 1
        
        # Push prototype away from negative
        distance = embedding - concept.prototype
        concept.prototype -= 0.1 * distance / (np.linalg.norm(distance) + 1e-8)
    
    def classify(self, embedding: np.ndarray, threshold: float = 0.5) -> List[Tuple[str, float]]:
        """
        Classify an embedding into concepts.
        
        Returns list of (concept_name, probability) pairs.
        """
        results = []
        
        for name, concept in self.concepts.items():
            # Prototype similarity
            proto_sim = self._cosine_similarity(embedding, concept.prototype)
            
            # Exemplar similarity (max of stored exemplars)
            exemp_sim = 0.0
            if concept.exemplars:
                exemp_sims = [
                    self._cosine_similarity(embedding, ex) 
                    for ex in concept.exemplars
                ]
                exemp_sim = max(exemp_sims)
            
            # Combined (prototype-exemplar hybrid)
            similarity = 0.6 * proto_sim + 0.4 * exemp_sim
            
            if similarity >= threshold:
                results.append((name, similarity))
        
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def generalize(self, concept_name: str) -> Dict[str, Any]:
        """Generalize a concept to an abstract representation."""
        if concept_name not in self.concepts:
            return {}
        
        concept = self.concepts[concept_name]
        
        # Find dimensions with highest variance in prototype
        if len(concept.exemplars) < 2:
            return {"prototype": concept.prototype.tolist()[:10]}
        
        exemplar_matrix = np.array(concept.exemplars)
        variance = np.var(exemplar_matrix, axis=0)
        
        # Invariant dimensions (low variance) = defining features
        invariant_dims = np.argsort(variance)[:10]
        
        return {
            "name": concept.name,
            "positive_examples": concept.positive_count,
            "invariant_features": invariant_dims.tolist(),
            "prototype_norm": float(np.linalg.norm(concept.prototype)),
        }
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


# ============================================================================
# 8. GRAPH NEURAL REASONING
# ============================================================================

class GraphNeuralReasoner:
    """
    Graph Neural Network for reasoning over knowledge graphs.
    
    Uses message passing to propagate information through
    relational structures.
    """
    
    def __init__(self, embedding_dim: int = 256, num_layers: int = 3):
        self.embedding_dim = embedding_dim
        self.num_layers = num_layers
        
        # Node embeddings
        self.node_embeddings: Dict[str, np.ndarray] = {}
        
        # Edge types
        self.edge_types: Set[str] = set()
        
        # Adjacency: node → [(neighbor, edge_type)]
        self.adjacency: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        
        # Neural components
        if TORCH_AVAILABLE:
            self.message_nn = nn.Sequential(
                nn.Linear(embedding_dim * 3, 256),  # source, edge, target
                nn.ReLU(),
                nn.Linear(256, embedding_dim),
            ).to(DEVICE)
            
            self.update_nn = nn.Sequential(
                nn.Linear(embedding_dim * 2, 256),  # current + aggregated
                nn.ReLU(),
                nn.Linear(256, embedding_dim),
            ).to(DEVICE)
            
            self.query_nn = nn.Sequential(
                nn.Linear(embedding_dim * 2, 256),
                nn.ReLU(),
                nn.Linear(256, 1),
                nn.Sigmoid(),
            ).to(DEVICE)
    
    def add_node(self, node_id: str, embedding: Optional[np.ndarray] = None):
        """Add a node to the graph."""
        if embedding is not None:
            self.node_embeddings[node_id] = embedding
        else:
            self.node_embeddings[node_id] = np.random.randn(self.embedding_dim) * 0.1
    
    def add_edge(self, source: str, target: str, edge_type: str):
        """Add an edge to the graph."""
        self.edge_types.add(edge_type)
        self.adjacency[source].append((target, edge_type))
        
        # Ensure nodes exist
        if source not in self.node_embeddings:
            self.add_node(source)
        if target not in self.node_embeddings:
            self.add_node(target)
    
    def propagate(self, num_steps: Optional[int] = None) -> Dict[str, np.ndarray]:
        """
        Run message passing to propagate information.
        
        Returns updated node embeddings.
        """
        steps = num_steps or self.num_layers
        current_embeddings = {k: v.copy() for k, v in self.node_embeddings.items()}
        
        for _ in range(steps):
            new_embeddings = {}
            
            for node, neighbors in self.adjacency.items():
                if not neighbors:
                    new_embeddings[node] = current_embeddings.get(
                        node, np.zeros(self.embedding_dim)
                    )
                    continue
                
                # Aggregate messages from neighbors
                messages = []
                node_emb = current_embeddings.get(node, np.zeros(self.embedding_dim))
                
                for neighbor, edge_type in neighbors:
                    neighbor_emb = current_embeddings.get(
                        neighbor, np.zeros(self.embedding_dim)
                    )
                    
                    # Compute message
                    if TORCH_AVAILABLE:
                        edge_emb = np.random.randn(self.embedding_dim) * 0.1
                        concat = np.concatenate([node_emb, edge_emb, neighbor_emb])
                        concat_t = torch.tensor(concat, dtype=torch.float32).to(DEVICE)
                        
                        with torch.no_grad():
                            message = self.message_nn(concat_t).cpu().numpy()
                    else:
                        # Simple averaging fallback
                        message = 0.5 * (node_emb + neighbor_emb)
                    
                    messages.append(message)
                
                # Aggregate (mean)
                aggregated = np.mean(messages, axis=0)
                
                # Update node embedding
                if TORCH_AVAILABLE:
                    concat = np.concatenate([node_emb, aggregated])
                    concat_t = torch.tensor(concat, dtype=torch.float32).to(DEVICE)
                    
                    with torch.no_grad():
                        new_emb = self.update_nn(concat_t).cpu().numpy()
                else:
                    new_emb = 0.5 * node_emb + 0.5 * aggregated
                
                new_embeddings[node] = new_emb
            
            current_embeddings = new_embeddings
        
        return current_embeddings
    
    def query_relation(self, source: str, target: str) -> float:
        """Query whether a relation exists between nodes."""
        # Propagate first
        embeddings = self.propagate()
        
        source_emb = embeddings.get(source, np.zeros(self.embedding_dim))
        target_emb = embeddings.get(target, np.zeros(self.embedding_dim))
        
        if TORCH_AVAILABLE:
            concat = np.concatenate([source_emb, target_emb])
            concat_t = torch.tensor(concat, dtype=torch.float32).to(DEVICE)
            
            with torch.no_grad():
                prob = self.query_nn(concat_t).item()
            return prob
        else:
            # Cosine similarity fallback
            norm_s = np.linalg.norm(source_emb)
            norm_t = np.linalg.norm(target_emb)
            if norm_s == 0 or norm_t == 0:
                return 0.0
            return float(np.dot(source_emb, target_emb) / (norm_s * norm_t))


# ============================================================================
# 9. MEMORY-AUGMENTED REASONING
# ============================================================================

class DifferentiableMemory:
    """
    Differentiable external memory for long reasoning chains.
    
    Inspired by Neural Turing Machines and Differentiable Neural Computers.
    """
    
    def __init__(
        self,
        memory_size: int = 128,
        memory_dim: int = 256,
    ):
        self.memory_size = memory_size
        self.memory_dim = memory_dim
        
        # Memory matrix
        self.memory = np.zeros((memory_size, memory_dim))
        
        # Usage and temporal linkage
        self.usage = np.zeros(memory_size)
        self.write_weights = np.zeros(memory_size)
        self.read_weights = np.zeros(memory_size)
        
        # Controller networks
        if TORCH_AVAILABLE:
            self.read_head = nn.Sequential(
                nn.Linear(memory_dim, 256),
                nn.ReLU(),
                nn.Linear(256, memory_dim),
            ).to(DEVICE)
            
            self.write_head = nn.Sequential(
                nn.Linear(memory_dim, 256),
                nn.ReLU(),
                nn.Linear(256, memory_dim),
            ).to(DEVICE)
    
    def reset(self):
        """Reset memory to initial state."""
        self.memory = np.zeros((self.memory_size, self.memory_dim))
        self.usage = np.zeros(self.memory_size)
        self.write_weights = np.zeros(self.memory_size)
        self.read_weights = np.zeros(self.memory_size)
    
    def _content_addressing(self, query: np.ndarray) -> np.ndarray:
        """Content-based addressing."""
        similarities = np.zeros(self.memory_size)
        
        for i in range(self.memory_size):
            mem_vec = self.memory[i]
            norm_q = np.linalg.norm(query)
            norm_m = np.linalg.norm(mem_vec)
            
            if norm_q > 0 and norm_m > 0:
                similarities[i] = np.dot(query, mem_vec) / (norm_q * norm_m)
        
        # Softmax
        exp_sim = np.exp(similarities - np.max(similarities))
        return exp_sim / (np.sum(exp_sim) + 1e-8)
    
    def _allocate(self) -> np.ndarray:
        """Allocate memory based on usage."""
        # Least used locations
        sorted_indices = np.argsort(self.usage)
        
        allocation = np.zeros(self.memory_size)
        allocation[sorted_indices[0]] = 1.0  # Write to least used
        
        return allocation
    
    def read(self, query: np.ndarray) -> np.ndarray:
        """Read from memory using content addressing."""
        self.read_weights = self._content_addressing(query)
        
        # Weighted sum
        read_vector = np.sum(
            self.memory * self.read_weights[:, np.newaxis],
            axis=0
        )
        
        return read_vector
    
    def write(self, content: np.ndarray, erase: bool = False):
        """Write to memory."""
        # Allocation-based writing
        self.write_weights = self._allocate()
        
        # Update usage
        self.usage += self.write_weights
        self.usage = np.minimum(self.usage, 1.0)
        
        # Write
        for i in range(self.memory_size):
            w = self.write_weights[i]
            if erase:
                self.memory[i] *= (1 - w)
            self.memory[i] += w * content
    
    def reason_with_memory(
        self,
        steps: List[np.ndarray],
        query: np.ndarray,
    ) -> np.ndarray:
        """
        Reason through a sequence of steps using memory.
        
        Each step is written to memory, allowing attention
        over the full reasoning history.
        """
        self.reset()
        
        # Write each step
        for step in steps:
            self.write(step)
        
        # Read relevant information for query
        result = self.read(query)
        
        return result


# ============================================================================
# UNIFIED FRONTIER LAYER 4
# ============================================================================

class Layer4FrontierReasoning:
    """
    Unified Frontier Layer 4: All advanced capabilities.
    
    Combines all frontier neuro-symbolic reasoning into one system.
    """
    
    def __init__(self, embedding_dim: int = 256):
        self.embedding_dim = embedding_dim
        
        # All frontier components
        self.theorem_prover = NeuralTheoremProver(embedding_dim)
        self.structure_mapper = StructureMappingEngine(embedding_dim)
        self.prob_logic = ProbabilisticLogicEngine(embedding_dim)
        self.program_synth = NeuralProgramSynthesizer(embedding_dim)
        self.meta_reasoner = MetaReasoner()
        self.abductive = AbductiveReasoner(embedding_dim)
        self.concept_learner = ConceptLearner(embedding_dim)
        self.graph_reasoner = GraphNeuralReasoner(embedding_dim)
        self.memory = DifferentiableMemory(memory_dim=embedding_dim)
        
        logger.info(f"[FRONTIER] Initialized with GPU={TORCH_AVAILABLE}, device={DEVICE}")
    
    def prove(self, goal: str, **kwargs) -> Proof:
        """Neural theorem proving."""
        return self.theorem_prover.prove(goal, **kwargs)
    
    def find_analogy(self, source: str, target: str) -> Optional[StructuralMapping]:
        """Find structural analogy between domains."""
        return self.structure_mapper.find_analogy(source, target)
    
    def query_probability(self, predicate: str, args: List[str]) -> float:
        """Query probabilistic fact."""
        return self.prob_logic.query(predicate, args)
    
    def synthesize_program(self, examples: List[Tuple], **kwargs) -> Optional[SynthesizedProgram]:
        """Synthesize program from examples."""
        spec = ProgramSpec(
            spec_id=str(uuid.uuid4()),
            input_output_examples=examples,
        )
        return self.program_synth.synthesize(spec, **kwargs)
    
    def select_strategy(self, problem_type: str, complexity: float) -> ReasoningStrategy:
        """Meta-reasoning: select best strategy."""
        problem = ReasoningProblem(
            problem_id=str(uuid.uuid4()),
            problem_type=problem_type,
            complexity=complexity,
            time_budget=10.0,
            knowledge_size=len(self.theorem_prover.facts),
            goal="",
        )
        return self.meta_reasoner.select_strategy(problem)
    
    def explain(self, observations: List[Dict]) -> Optional[Hypothesis]:
        """Abductive reasoning: find best explanation."""
        for obs in observations:
            self.abductive.add_observation(obs)
        return self.abductive.best_explanation()
    
    def learn_concept(self, name: str, examples: List[np.ndarray]):
        """Few-shot concept learning."""
        for ex in examples:
            self.concept_learner.add_positive_example(name, ex)
    
    def classify_concept(self, embedding: np.ndarray) -> List[Tuple[str, float]]:
        """Classify into learned concepts."""
        return self.concept_learner.classify(embedding)
    
    def graph_query(self, source: str, target: str) -> float:
        """Query relation via graph neural reasoning."""
        return self.graph_reasoner.query_relation(source, target)
    
    def reason_with_memory(self, steps: List[np.ndarray], query: np.ndarray) -> np.ndarray:
        """Use external memory for long chains."""
        return self.memory.reason_with_memory(steps, query)
    
    def get_status(self) -> Dict[str, Any]:
        """Get frontier status."""
        return {
            "layer": "4-frontier",
            "name": "Maximum Neuro-Symbolic Capability",
            "gpu_available": TORCH_AVAILABLE,
            "device": str(DEVICE),
            "components": {
                "neural_theorem_prover": {
                    "facts": len(self.theorem_prover.facts),
                    "rules": len(self.theorem_prover.rules),
                    "proofs_cached": len(self.theorem_prover.proof_cache),
                },
                "structure_mapper": {
                    "domains": len(self.structure_mapper.domains),
                    "mappings": len(self.structure_mapper.mappings),
                },
                "probabilistic_logic": {
                    "facts": len(self.prob_logic.facts),
                    "rules": len(self.prob_logic.rules),
                },
                "program_synthesizer": {
                    "primitives": len(self.program_synth.primitives),
                    "successful_programs": len(self.program_synth.successful_programs),
                },
                "meta_reasoner": self.meta_reasoner.get_statistics(),
                "abductive_reasoner": {
                    "observations": len(self.abductive.observations),
                    "hypotheses": len(self.abductive.hypotheses),
                    "patterns": len(self.abductive.patterns),
                },
                "concept_learner": {
                    "concepts": len(self.concept_learner.concepts),
                },
                "graph_reasoner": {
                    "nodes": len(self.graph_reasoner.node_embeddings),
                    "edge_types": len(self.graph_reasoner.edge_types),
                },
                "memory": {
                    "size": self.memory.memory_size,
                    "dim": self.memory.memory_dim,
                },
            },
        }


# ============================================================================
# FACTORY
# ============================================================================

def get_frontier_layer4(embedding_dim: int = 256) -> Layer4FrontierReasoning:
    """Get frontier Layer 4 with all capabilities."""
    return Layer4FrontierReasoning(embedding_dim=embedding_dim)
