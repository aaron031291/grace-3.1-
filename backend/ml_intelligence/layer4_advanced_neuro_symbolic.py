"""
Layer 4 Advanced: Pushing Neuro-Symbolic to the Frontier

This extends Layer 4 with cutting-edge capabilities:

1. COMPOSITIONAL GENERALIZATION
   - Combine patterns to create new ones
   - Pattern algebra: union, intersection, composition
   - Emergent patterns from combinations

2. SELF-MODIFYING RULES
   - Rules that rewrite themselves based on performance
   - Automatic rule refinement
   - Rule mutation and selection

3. DIFFERENTIABLE LOGIC
   - Gradient-based rule learning
   - Soft logic with continuous truth values
   - End-to-end trainable symbolic reasoning

4. COUNTERFACTUAL REASONING
   - "What if" pattern exploration
   - Causal inference from patterns
   - Intervention simulation

5. TEMPORAL PATTERN EVOLUTION
   - Patterns that evolve over time
   - Pattern lifecycle tracking
   - Decay and reinforcement dynamics

Research basis:
- Logic Tensor Networks (LTN)
- Neural Theorem Provers (NTP)
- Differentiable Inductive Logic Programming (∂ILP)
- Scallop: Neurosymbolic Programming
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging
import json
import uuid
from pathlib import Path
from collections import defaultdict
import copy

logger = logging.getLogger(__name__)


# ============================================================================
# COMPOSITIONAL GENERALIZATION
# ============================================================================

class PatternOperator(str, Enum):
    """Operators for pattern composition."""
    UNION = "union"           # A ∪ B: patterns that match A OR B
    INTERSECTION = "intersection"  # A ∩ B: patterns that match A AND B
    COMPOSITION = "composition"    # A ∘ B: apply A then B
    NEGATION = "negation"     # ¬A: patterns that don't match A
    SEQUENCE = "sequence"     # A → B: A followed by B
    PARALLEL = "parallel"     # A ‖ B: A and B together
    CONDITIONAL = "conditional"    # A ? B : C: if A then B else C


@dataclass
class CompositePattern:
    """
    A pattern created by combining other patterns.
    
    This enables compositional generalization:
    - Simple patterns combine to form complex ones
    - Complex patterns can be decomposed
    - Novel patterns emerge from combinations
    """
    composite_id: str
    operator: PatternOperator
    operands: List[str]  # Pattern IDs
    result_pattern: Dict[str, Any]  # Computed composite
    confidence: float  # Confidence in composition
    creation_count: int = 0  # Times this composition was used
    success_count: int = 0   # Times it led to good outcomes
    
    def success_rate(self) -> float:
        if self.creation_count == 0:
            return 0.5
        return self.success_count / self.creation_count


class CompositionEngine:
    """
    Engine for compositional generalization.
    
    Combines patterns using algebraic operators to create
    new, more powerful patterns.
    """
    
    def __init__(self, pattern_store: Dict[str, Dict[str, Any]] = None):
        self.pattern_store = pattern_store or {}
        self.composites: Dict[str, CompositePattern] = {}
        self.composition_history: List[Dict[str, Any]] = []
        
    def compose(
        self,
        operator: PatternOperator,
        pattern_ids: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[CompositePattern]:
        """
        Compose patterns using an operator.
        
        Args:
            operator: How to combine patterns
            pattern_ids: Patterns to combine
            context: Additional context
            
        Returns:
            CompositePattern or None if composition fails
        """
        # Get patterns
        patterns = []
        for pid in pattern_ids:
            if pid in self.pattern_store:
                patterns.append(self.pattern_store[pid])
            else:
                logger.warning(f"Pattern {pid} not found for composition")
                return None
        
        if len(patterns) < 2 and operator not in [PatternOperator.NEGATION]:
            return None
        
        # Apply operator
        result = self._apply_operator(operator, patterns)
        
        if result is None:
            return None
        
        # Create composite
        composite = CompositePattern(
            composite_id=str(uuid.uuid4()),
            operator=operator,
            operands=pattern_ids,
            result_pattern=result,
            confidence=self._calculate_composite_confidence(patterns, operator),
        )
        
        self.composites[composite.composite_id] = composite
        self.composition_history.append({
            "composite_id": composite.composite_id,
            "operator": operator.value,
            "operands": pattern_ids,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        logger.info(f"[COMPOSITION] Created {operator.value} composite from {len(patterns)} patterns")
        
        return composite
    
    def _apply_operator(
        self,
        operator: PatternOperator,
        patterns: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Apply compositional operator to patterns."""
        
        if operator == PatternOperator.UNION:
            # Union: combine all keywords, roles, constraints (OR)
            return {
                "structure": {"type": "union", "components": len(patterns)},
                "keywords": list(set(
                    kw for p in patterns 
                    for kw in p.get("keywords", [])
                )),
                "roles": list(set(
                    r for p in patterns 
                    for r in p.get("roles", [])
                )),
                "constraints": [
                    {"type": "any_of", "options": [
                        p.get("constraints", []) for p in patterns
                    ]}
                ],
                "_operator": "union",
            }
        
        elif operator == PatternOperator.INTERSECTION:
            # Intersection: only common elements (AND)
            if len(patterns) < 2:
                return None
            
            # Find common keywords
            keyword_sets = [set(p.get("keywords", [])) for p in patterns]
            common_keywords = keyword_sets[0]
            for ks in keyword_sets[1:]:
                common_keywords = common_keywords.intersection(ks)
            
            # Find common roles
            role_sets = [set(p.get("roles", [])) for p in patterns]
            common_roles = role_sets[0]
            for rs in role_sets[1:]:
                common_roles = common_roles.intersection(rs)
            
            return {
                "structure": {"type": "intersection", "components": len(patterns)},
                "keywords": list(common_keywords),
                "roles": list(common_roles),
                "constraints": [
                    {"type": "all_of", "requirements": [
                        p.get("constraints", []) for p in patterns
                    ]}
                ],
                "_operator": "intersection",
            }
        
        elif operator == PatternOperator.COMPOSITION:
            # Composition: apply first then second (pipeline)
            return {
                "structure": {"type": "pipeline", "stages": len(patterns)},
                "keywords": [p.get("keywords", []) for p in patterns],
                "roles": ["input", "intermediate", "output"],
                "transformations": [
                    {"stage": i, "pattern": p.get("abstract_form", p)}
                    for i, p in enumerate(patterns)
                ],
                "constraints": [
                    {"type": "sequence", "order": "strict"}
                ],
                "_operator": "composition",
            }
        
        elif operator == PatternOperator.NEGATION:
            # Negation: opposite of pattern
            if not patterns:
                return None
            p = patterns[0]
            return {
                "structure": {"type": "negation"},
                "keywords": p.get("keywords", []),
                "roles": p.get("roles", []),
                "constraints": [
                    {"type": "not", "excluded": p.get("constraints", [])}
                ],
                "_operator": "negation",
                "_negates": p.get("pattern_id", "unknown"),
            }
        
        elif operator == PatternOperator.SEQUENCE:
            # Sequence: temporal ordering
            return {
                "structure": {"type": "sequence", "length": len(patterns)},
                "keywords": [p.get("keywords", []) for p in patterns],
                "roles": ["predecessor", "successor"],
                "constraints": [
                    {"type": "temporal_order", "sequence": [
                        p.get("pattern_id", f"step_{i}") 
                        for i, p in enumerate(patterns)
                    ]}
                ],
                "_operator": "sequence",
            }
        
        elif operator == PatternOperator.PARALLEL:
            # Parallel: concurrent execution
            return {
                "structure": {"type": "parallel", "branches": len(patterns)},
                "keywords": list(set(
                    kw for p in patterns 
                    for kw in p.get("keywords", [])
                )),
                "roles": ["parallel_branch"],
                "constraints": [
                    {"type": "concurrent", "branches": len(patterns)}
                ],
                "_operator": "parallel",
            }
        
        elif operator == PatternOperator.CONDITIONAL:
            # Conditional: if-then-else (needs 3 patterns)
            if len(patterns) < 3:
                return None
            return {
                "structure": {"type": "conditional"},
                "condition": patterns[0],
                "then_branch": patterns[1],
                "else_branch": patterns[2],
                "roles": ["condition", "consequent", "alternative"],
                "constraints": [
                    {"type": "branching", "exclusive": True}
                ],
                "_operator": "conditional",
            }
        
        return None
    
    def _calculate_composite_confidence(
        self,
        patterns: List[Dict[str, Any]],
        operator: PatternOperator,
    ) -> float:
        """Calculate confidence for composite pattern."""
        if not patterns:
            return 0.0
        
        # Get individual confidences
        confidences = [
            p.get("confidence", 0.5) or p.get("trust_score", 0.5)
            for p in patterns
        ]
        
        # Operator-specific confidence calculation
        if operator == PatternOperator.UNION:
            # Union: max confidence (most permissive)
            return max(confidences)
        
        elif operator == PatternOperator.INTERSECTION:
            # Intersection: min confidence (most restrictive)
            return min(confidences)
        
        elif operator == PatternOperator.COMPOSITION:
            # Composition: product (all must work)
            result = 1.0
            for c in confidences:
                result *= c
            return result
        
        elif operator == PatternOperator.NEGATION:
            # Negation: same confidence
            return confidences[0] if confidences else 0.5
        
        else:
            # Default: average
            return np.mean(confidences)
    
    def decompose(
        self,
        composite_id: str,
    ) -> List[Dict[str, Any]]:
        """Decompose a composite pattern back to its components."""
        if composite_id not in self.composites:
            return []
        
        composite = self.composites[composite_id]
        return [
            self.pattern_store.get(pid, {"pattern_id": pid})
            for pid in composite.operands
        ]


# ============================================================================
# SELF-MODIFYING RULES
# ============================================================================

@dataclass
class SelfModifyingRule:
    """
    A rule that can rewrite itself based on performance.
    
    Key concepts:
    - Rules track their own success/failure
    - Underperforming rules mutate
    - Successful mutations are kept
    - Rules can spawn variants
    """
    rule_id: str
    premise: Dict[str, Any]
    conclusion: Dict[str, Any]
    confidence: float
    generation: int = 0  # How many mutations from original
    parent_id: Optional[str] = None
    
    # Performance tracking
    applications: int = 0
    successes: int = 0
    failures: int = 0
    
    # Mutation parameters
    mutation_rate: float = 0.1
    last_mutation: Optional[datetime] = None
    
    def success_rate(self) -> float:
        if self.applications == 0:
            return 0.5
        return self.successes / self.applications
    
    def should_mutate(self) -> bool:
        """Decide if rule should mutate based on performance."""
        if self.applications < 5:
            return False  # Not enough data
        
        success_rate = self.success_rate()
        
        # Low performers mutate more
        if success_rate < 0.3:
            return True
        
        # Random mutation for exploration
        if np.random.random() < self.mutation_rate:
            return True
        
        return False


class SelfModifyingRuleEngine:
    """
    Engine for self-modifying rules.
    
    Rules evolve over time based on their performance,
    automatically improving or being replaced.
    """
    
    def __init__(self):
        self.rules: Dict[str, SelfModifyingRule] = {}
        self.mutation_history: List[Dict[str, Any]] = []
        self.graveyard: List[str] = []  # Retired rules
        
        # Mutation operators
        self.mutation_operators = [
            self._mutate_threshold,
            self._mutate_add_condition,
            self._mutate_remove_condition,
            self._mutate_generalize,
            self._mutate_specialize,
        ]
    
    def add_rule(self, rule: SelfModifyingRule):
        """Add a rule to the engine."""
        self.rules[rule.rule_id] = rule
    
    def apply_rule(
        self,
        rule_id: str,
        context: Dict[str, Any],
    ) -> Tuple[bool, Any]:
        """
        Apply a rule and track performance.
        
        Returns:
            (success, result)
        """
        if rule_id not in self.rules:
            return False, None
        
        rule = self.rules[rule_id]
        rule.applications += 1
        
        # Check if premise matches
        if not self._premise_matches(rule.premise, context):
            return False, None
        
        # Apply conclusion
        result = self._apply_conclusion(rule.conclusion, context)
        
        return True, result
    
    def record_outcome(
        self,
        rule_id: str,
        success: bool,
    ):
        """Record whether rule application was successful."""
        if rule_id not in self.rules:
            return
        
        rule = self.rules[rule_id]
        if success:
            rule.successes += 1
        else:
            rule.failures += 1
        
        # Check if mutation needed
        if rule.should_mutate():
            self._mutate_rule(rule_id)
    
    def _mutate_rule(self, rule_id: str) -> Optional[str]:
        """
        Mutate a rule to improve it.
        
        Returns:
            New rule ID if mutation created variant
        """
        if rule_id not in self.rules:
            return None
        
        rule = self.rules[rule_id]
        
        # Select mutation operator
        operator = np.random.choice(self.mutation_operators)
        
        # Apply mutation
        mutated = operator(rule)
        
        if mutated is None:
            return None
        
        # Create new rule from mutation
        new_rule = SelfModifyingRule(
            rule_id=str(uuid.uuid4()),
            premise=mutated["premise"],
            conclusion=mutated["conclusion"],
            confidence=rule.confidence * 0.9,  # Slightly lower confidence
            generation=rule.generation + 1,
            parent_id=rule.rule_id,
            mutation_rate=rule.mutation_rate,
        )
        
        self.rules[new_rule.rule_id] = new_rule
        
        self.mutation_history.append({
            "parent_id": rule_id,
            "child_id": new_rule.rule_id,
            "operator": operator.__name__,
            "generation": new_rule.generation,
            "timestamp": datetime.utcnow().isoformat(),
        })
        
        rule.last_mutation = datetime.utcnow()
        
        logger.info(
            f"[SELF-MODIFY] Mutated rule {rule_id[:8]} -> {new_rule.rule_id[:8]} "
            f"(gen {new_rule.generation})"
        )
        
        return new_rule.rule_id
    
    def _premise_matches(
        self,
        premise: Dict[str, Any],
        context: Dict[str, Any],
    ) -> bool:
        """Check if premise matches context (simplified)."""
        for key, value in premise.items():
            if key.startswith("_"):
                continue
            if key not in context:
                return False
            if isinstance(value, dict) and "threshold" in value:
                if context.get(key, 0) < value["threshold"]:
                    return False
            elif context.get(key) != value:
                return False
        return True
    
    def _apply_conclusion(
        self,
        conclusion: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Apply conclusion to context (simplified)."""
        result = context.copy()
        result.update(conclusion)
        return result
    
    # Mutation operators
    
    def _mutate_threshold(self, rule: SelfModifyingRule) -> Optional[Dict]:
        """Mutate threshold values in premise."""
        premise = copy.deepcopy(rule.premise)
        conclusion = copy.deepcopy(rule.conclusion)
        
        # Find threshold values and adjust
        for key, value in premise.items():
            if isinstance(value, dict) and "threshold" in value:
                delta = np.random.normal(0, 0.1)
                value["threshold"] = max(0, min(1, value["threshold"] + delta))
                return {"premise": premise, "conclusion": conclusion}
        
        return None
    
    def _mutate_add_condition(self, rule: SelfModifyingRule) -> Optional[Dict]:
        """Add a new condition to premise."""
        premise = copy.deepcopy(rule.premise)
        conclusion = copy.deepcopy(rule.conclusion)
        
        # Add a random condition
        new_key = f"condition_{len(premise)}"
        premise[new_key] = {"threshold": np.random.random()}
        
        return {"premise": premise, "conclusion": conclusion}
    
    def _mutate_remove_condition(self, rule: SelfModifyingRule) -> Optional[Dict]:
        """Remove a condition from premise."""
        premise = copy.deepcopy(rule.premise)
        conclusion = copy.deepcopy(rule.conclusion)
        
        # Remove a random non-essential condition
        removable = [k for k in premise.keys() if not k.startswith("_")]
        if len(removable) > 1:
            to_remove = np.random.choice(removable)
            del premise[to_remove]
            return {"premise": premise, "conclusion": conclusion}
        
        return None
    
    def _mutate_generalize(self, rule: SelfModifyingRule) -> Optional[Dict]:
        """Generalize rule by loosening constraints."""
        premise = copy.deepcopy(rule.premise)
        conclusion = copy.deepcopy(rule.conclusion)
        
        for key, value in premise.items():
            if isinstance(value, dict) and "threshold" in value:
                value["threshold"] *= 0.8  # Lower threshold = more general
                return {"premise": premise, "conclusion": conclusion}
        
        return None
    
    def _mutate_specialize(self, rule: SelfModifyingRule) -> Optional[Dict]:
        """Specialize rule by tightening constraints."""
        premise = copy.deepcopy(rule.premise)
        conclusion = copy.deepcopy(rule.conclusion)
        
        for key, value in premise.items():
            if isinstance(value, dict) and "threshold" in value:
                value["threshold"] = min(1.0, value["threshold"] * 1.2)  # Higher = more specific
                return {"premise": premise, "conclusion": conclusion}
        
        return None
    
    def prune_underperformers(self, min_success_rate: float = 0.2):
        """Remove rules that consistently fail."""
        to_remove = []
        
        for rule_id, rule in self.rules.items():
            if rule.applications >= 10 and rule.success_rate() < min_success_rate:
                to_remove.append(rule_id)
        
        for rule_id in to_remove:
            del self.rules[rule_id]
            self.graveyard.append(rule_id)
        
        if to_remove:
            logger.info(f"[SELF-MODIFY] Pruned {len(to_remove)} underperforming rules")


# ============================================================================
# DIFFERENTIABLE LOGIC
# ============================================================================

class SoftLogic:
    """
    Soft (fuzzy/differentiable) logic operations.
    
    Instead of hard True/False, uses continuous [0,1] truth values.
    This enables gradient-based learning of logical rules.
    """
    
    @staticmethod
    def AND(a: float, b: float) -> float:
        """Soft AND: product t-norm."""
        return a * b
    
    @staticmethod
    def OR(a: float, b: float) -> float:
        """Soft OR: probabilistic sum."""
        return a + b - a * b
    
    @staticmethod
    def NOT(a: float) -> float:
        """Soft NOT: complement."""
        return 1.0 - a
    
    @staticmethod
    def IMPLIES(a: float, b: float) -> float:
        """Soft implication: Reichenbach."""
        return 1.0 - a + a * b
    
    @staticmethod
    def FORALL(values: List[float]) -> float:
        """Soft universal quantifier: product."""
        result = 1.0
        for v in values:
            result *= v
        return result
    
    @staticmethod
    def EXISTS(values: List[float]) -> float:
        """Soft existential quantifier: max."""
        return max(values) if values else 0.0
    
    @staticmethod
    def similarity(a: np.ndarray, b: np.ndarray) -> float:
        """Soft equality via cosine similarity."""
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))


@dataclass
class DifferentiableRule:
    """
    A rule with learnable parameters.
    
    The rule's behavior can be adjusted via gradient descent.
    """
    rule_id: str
    predicate: str  # Rule name
    
    # Learnable parameters
    weights: np.ndarray  # Connection weights
    bias: float = 0.0
    temperature: float = 1.0  # Softmax temperature
    
    # Metadata
    learning_rate: float = 0.01
    
    def forward(self, inputs: np.ndarray) -> float:
        """Forward pass: compute soft truth value."""
        logit = np.dot(inputs, self.weights) + self.bias
        # Sigmoid activation for [0,1] output
        return float(1.0 / (1.0 + np.exp(-logit / self.temperature)))
    
    def backward(self, inputs: np.ndarray, target: float, prediction: float):
        """Backward pass: update weights via gradient descent."""
        error = target - prediction
        gradient = prediction * (1 - prediction)  # Sigmoid derivative
        
        # Update weights
        self.weights += self.learning_rate * error * gradient * inputs
        self.bias += self.learning_rate * error * gradient


class DifferentiableLogicEngine:
    """
    Engine for differentiable/soft logic reasoning.
    
    Enables:
    - Gradient-based rule learning
    - Soft constraint satisfaction
    - Neural-symbolic integration via continuous relaxation
    """
    
    def __init__(self, embedding_dim: int = 128):
        self.embedding_dim = embedding_dim
        self.rules: Dict[str, DifferentiableRule] = {}
        self.soft_logic = SoftLogic()
        
        # Knowledge base: predicate -> (subject, object) -> truth value
        self.knowledge: Dict[str, Dict[Tuple[str, str], float]] = defaultdict(dict)
    
    def add_rule(
        self,
        predicate: str,
        initial_weights: Optional[np.ndarray] = None,
    ) -> DifferentiableRule:
        """Add a differentiable rule."""
        weights = initial_weights if initial_weights is not None else \
                  np.random.randn(self.embedding_dim) * 0.1
        
        rule = DifferentiableRule(
            rule_id=str(uuid.uuid4()),
            predicate=predicate,
            weights=weights,
        )
        
        self.rules[predicate] = rule
        return rule
    
    def assert_fact(
        self,
        predicate: str,
        subject: str,
        obj: str,
        truth_value: float = 1.0,
    ):
        """Assert a soft fact."""
        self.knowledge[predicate][(subject, obj)] = truth_value
    
    def query(
        self,
        predicate: str,
        subject_embedding: np.ndarray,
        object_embedding: np.ndarray,
    ) -> float:
        """
        Query a predicate with soft truth value.
        
        Combines:
        - Stored knowledge (if available)
        - Rule inference (if rule exists)
        """
        # Combine embeddings
        combined = np.concatenate([
            subject_embedding[:self.embedding_dim//2],
            object_embedding[:self.embedding_dim//2],
        ])
        
        if len(combined) < self.embedding_dim:
            combined = np.pad(combined, (0, self.embedding_dim - len(combined)))
        combined = combined[:self.embedding_dim]
        
        # Apply rule if exists
        if predicate in self.rules:
            rule = self.rules[predicate]
            return rule.forward(combined)
        
        return 0.5  # Unknown
    
    def reason(
        self,
        query_predicate: str,
        subject_embedding: np.ndarray,
        object_embedding: np.ndarray,
        chain_length: int = 2,
    ) -> Tuple[float, List[str]]:
        """
        Perform soft reasoning with rule chaining.
        
        Returns:
            (truth_value, reasoning_chain)
        """
        chain = []
        current_truth = 1.0
        
        # Direct query
        direct = self.query(query_predicate, subject_embedding, object_embedding)
        chain.append(f"{query_predicate}: {direct:.3f}")
        
        # Chain through related rules
        for rule_name, rule in list(self.rules.items())[:chain_length]:
            if rule_name == query_predicate:
                continue
            
            intermediate = rule.forward(
                np.concatenate([
                    subject_embedding[:self.embedding_dim//2],
                    object_embedding[:self.embedding_dim//2],
                ])[:self.embedding_dim]
            )
            
            # Soft implication
            implied = self.soft_logic.IMPLIES(intermediate, direct)
            current_truth = self.soft_logic.AND(current_truth, implied)
            chain.append(f"{rule_name} -> {query_predicate}: {implied:.3f}")
        
        return current_truth, chain
    
    def train_step(
        self,
        examples: List[Tuple[str, np.ndarray, np.ndarray, float]],
    ) -> float:
        """
        Train rules on examples.
        
        Args:
            examples: List of (predicate, subject_emb, object_emb, target_truth)
            
        Returns:
            Average loss
        """
        total_loss = 0.0
        
        for predicate, subj_emb, obj_emb, target in examples:
            if predicate not in self.rules:
                self.add_rule(predicate)
            
            rule = self.rules[predicate]
            
            # Forward
            combined = np.concatenate([
                subj_emb[:self.embedding_dim//2],
                obj_emb[:self.embedding_dim//2],
            ])[:self.embedding_dim]
            
            if len(combined) < self.embedding_dim:
                combined = np.pad(combined, (0, self.embedding_dim - len(combined)))
            
            prediction = rule.forward(combined)
            
            # Loss (binary cross-entropy)
            eps = 1e-7
            loss = -(target * np.log(prediction + eps) + 
                    (1 - target) * np.log(1 - prediction + eps))
            total_loss += loss
            
            # Backward
            rule.backward(combined, target, prediction)
        
        return total_loss / len(examples) if examples else 0.0


# ============================================================================
# COUNTERFACTUAL REASONING
# ============================================================================

@dataclass
class Counterfactual:
    """
    A counterfactual scenario: "What if X were different?"
    """
    counterfactual_id: str
    original_state: Dict[str, Any]
    intervention: Dict[str, Any]  # What we change
    counterfactual_state: Dict[str, Any]  # Resulting state
    outcome_difference: float  # How much outcome changes
    confidence: float
    
    def describe(self) -> str:
        changes = []
        for key, new_val in self.intervention.items():
            old_val = self.original_state.get(key, "?")
            changes.append(f"{key}: {old_val} -> {new_val}")
        return f"If {', '.join(changes)}, then outcome differs by {self.outcome_difference:.2f}"


class CounterfactualReasoner:
    """
    Reasons about counterfactuals: what would happen if things were different?
    
    This enables:
    - Causal understanding
    - Intervention planning
    - Explanation generation
    """
    
    def __init__(self, causal_model: Optional[Dict[str, List[str]]] = None):
        # Causal graph: variable -> list of variables it causes
        self.causal_model = causal_model or {}
        self.counterfactuals: List[Counterfactual] = []
    
    def add_causal_relation(self, cause: str, effect: str):
        """Add a causal relation: cause -> effect."""
        if cause not in self.causal_model:
            self.causal_model[cause] = []
        if effect not in self.causal_model[cause]:
            self.causal_model[cause].append(effect)
    
    def intervene(
        self,
        original_state: Dict[str, Any],
        intervention: Dict[str, Any],
        outcome_fn: Callable[[Dict[str, Any]], float],
    ) -> Counterfactual:
        """
        Perform an intervention and compute counterfactual outcome.
        
        Args:
            original_state: Current state
            intervention: Variables to change
            outcome_fn: Function that computes outcome from state
            
        Returns:
            Counterfactual with results
        """
        # Compute original outcome
        original_outcome = outcome_fn(original_state)
        
        # Apply intervention
        counterfactual_state = original_state.copy()
        counterfactual_state.update(intervention)
        
        # Propagate through causal model
        for var, new_val in intervention.items():
            self._propagate_intervention(var, new_val, counterfactual_state)
        
        # Compute counterfactual outcome
        cf_outcome = outcome_fn(counterfactual_state)
        
        cf = Counterfactual(
            counterfactual_id=str(uuid.uuid4()),
            original_state=original_state,
            intervention=intervention,
            counterfactual_state=counterfactual_state,
            outcome_difference=cf_outcome - original_outcome,
            confidence=self._calculate_confidence(intervention),
        )
        
        self.counterfactuals.append(cf)
        
        return cf
    
    def _propagate_intervention(
        self,
        variable: str,
        new_value: Any,
        state: Dict[str, Any],
    ):
        """Propagate intervention effects through causal model."""
        if variable not in self.causal_model:
            return
        
        for effect in self.causal_model[variable]:
            # Simple linear effect (can be made more sophisticated)
            if effect in state and isinstance(state[effect], (int, float)):
                if isinstance(new_value, (int, float)):
                    original = state.get(variable, 0)
                    delta = new_value - original if isinstance(original, (int, float)) else 0
                    state[effect] = state[effect] + delta * 0.5  # 50% transmission
    
    def _calculate_confidence(self, intervention: Dict[str, Any]) -> float:
        """Calculate confidence in counterfactual based on intervention size."""
        # More interventions = less confident
        n_interventions = len(intervention)
        return 1.0 / (1.0 + 0.2 * n_interventions)
    
    def find_minimal_intervention(
        self,
        original_state: Dict[str, Any],
        target_outcome: float,
        outcome_fn: Callable[[Dict[str, Any]], float],
        candidate_vars: List[str],
        max_attempts: int = 100,
    ) -> Optional[Counterfactual]:
        """
        Find the smallest intervention to achieve target outcome.
        
        This answers: "What's the minimum change needed to get outcome X?"
        """
        best_cf = None
        best_intervention_size = float('inf')
        
        for _ in range(max_attempts):
            # Random intervention subset
            n_vars = np.random.randint(1, len(candidate_vars) + 1)
            vars_to_change = np.random.choice(
                candidate_vars, size=n_vars, replace=False
            )
            
            intervention = {}
            for var in vars_to_change:
                if var in original_state and isinstance(original_state[var], (int, float)):
                    # Random perturbation
                    delta = np.random.normal(0, 0.5)
                    intervention[var] = original_state[var] + delta
            
            if not intervention:
                continue
            
            cf = self.intervene(original_state, intervention, outcome_fn)
            
            # Check if outcome is close to target
            if abs(outcome_fn(cf.counterfactual_state) - target_outcome) < 0.1:
                if len(intervention) < best_intervention_size:
                    best_cf = cf
                    best_intervention_size = len(intervention)
        
        return best_cf


# ============================================================================
# TEMPORAL PATTERN EVOLUTION
# ============================================================================

@dataclass
class TemporalPattern:
    """
    A pattern that evolves over time.
    
    Tracks:
    - Strength over time (reinforcement/decay)
    - Version history
    - Environmental conditions when pattern succeeds/fails
    """
    pattern_id: str
    content: Dict[str, Any]
    
    # Temporal dynamics
    creation_time: datetime
    last_activation: datetime
    activation_count: int = 0
    
    # Strength dynamics
    current_strength: float = 1.0
    peak_strength: float = 1.0
    
    # Decay parameters
    decay_rate: float = 0.01  # Strength decay per day without activation
    reinforcement_rate: float = 0.1  # Strength gain per activation
    
    # Version history
    version: int = 1
    previous_versions: List[Dict[str, Any]] = field(default_factory=list)
    
    def decay(self):
        """Apply time-based decay to pattern strength."""
        days_since_activation = (datetime.utcnow() - self.last_activation).days
        decay = self.decay_rate * days_since_activation
        self.current_strength = max(0.1, self.current_strength - decay)
    
    def reinforce(self):
        """Reinforce pattern on successful activation."""
        self.activation_count += 1
        self.last_activation = datetime.utcnow()
        self.current_strength = min(
            1.0, 
            self.current_strength + self.reinforcement_rate
        )
        self.peak_strength = max(self.peak_strength, self.current_strength)
    
    def evolve(self, new_content: Dict[str, Any]):
        """Evolve pattern to new version."""
        self.previous_versions.append({
            "version": self.version,
            "content": self.content.copy(),
            "strength": self.current_strength,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.content = new_content
        self.version += 1


class TemporalPatternManager:
    """
    Manages patterns with temporal dynamics.
    
    Patterns strengthen with use, decay without use,
    and evolve over time.
    """
    
    def __init__(self):
        self.patterns: Dict[str, TemporalPattern] = {}
        self.activation_history: List[Dict[str, Any]] = []
    
    def add_pattern(
        self,
        content: Dict[str, Any],
        initial_strength: float = 1.0,
    ) -> TemporalPattern:
        """Add a new temporal pattern."""
        now = datetime.utcnow()
        
        pattern = TemporalPattern(
            pattern_id=str(uuid.uuid4()),
            content=content,
            creation_time=now,
            last_activation=now,
            current_strength=initial_strength,
        )
        
        self.patterns[pattern.pattern_id] = pattern
        return pattern
    
    def activate(self, pattern_id: str, success: bool = True):
        """Activate a pattern (use it)."""
        if pattern_id not in self.patterns:
            return
        
        pattern = self.patterns[pattern_id]
        
        if success:
            pattern.reinforce()
        else:
            # Failed activation causes decay
            pattern.current_strength = max(
                0.1,
                pattern.current_strength - 0.05
            )
        
        self.activation_history.append({
            "pattern_id": pattern_id,
            "success": success,
            "strength_after": pattern.current_strength,
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    def decay_all(self):
        """Apply decay to all patterns."""
        for pattern in self.patterns.values():
            pattern.decay()
    
    def get_strongest(self, n: int = 10) -> List[TemporalPattern]:
        """Get the n strongest patterns."""
        sorted_patterns = sorted(
            self.patterns.values(),
            key=lambda p: p.current_strength,
            reverse=True,
        )
        return sorted_patterns[:n]
    
    def prune_weak(self, min_strength: float = 0.2):
        """Remove patterns below minimum strength."""
        to_remove = [
            pid for pid, p in self.patterns.items()
            if p.current_strength < min_strength
        ]
        
        for pid in to_remove:
            del self.patterns[pid]
        
        return len(to_remove)


# ============================================================================
# UNIFIED ADVANCED LAYER 4
# ============================================================================

class Layer4AdvancedNeuroSymbolic:
    """
    Advanced Layer 4 combining all frontier capabilities.
    
    This is the highest level of neuro-symbolic intelligence,
    pushing the boundaries of what's possible.
    """
    
    def __init__(
        self,
        base_layer4=None,  # Layer4RecursivePatternLearner
        embedding_dim: int = 128,
    ):
        self.base = base_layer4
        self.embedding_dim = embedding_dim
        
        # Advanced components
        self.composition_engine = CompositionEngine()
        self.self_modifying_engine = SelfModifyingRuleEngine()
        self.differentiable_logic = DifferentiableLogicEngine(embedding_dim)
        self.counterfactual_reasoner = CounterfactualReasoner()
        self.temporal_manager = TemporalPatternManager()
        
        logger.info("[LAYER4-ADVANCED] Initialized with all frontier capabilities")
    
    def compose_patterns(
        self,
        operator: str,
        pattern_ids: List[str],
    ) -> Optional[CompositePattern]:
        """Compose patterns using algebra."""
        try:
            op = PatternOperator(operator)
        except ValueError:
            logger.warning(f"Unknown operator: {operator}")
            return None
        
        # Get patterns from base layer if available
        if self.base:
            for pid in pattern_ids:
                if pid in self.base.patterns and pid not in self.composition_engine.pattern_store:
                    pattern = self.base.patterns[pid]
                    self.composition_engine.pattern_store[pid] = pattern.abstract_form
        
        return self.composition_engine.compose(op, pattern_ids)
    
    def add_self_modifying_rule(
        self,
        premise: Dict[str, Any],
        conclusion: Dict[str, Any],
        confidence: float = 0.7,
    ) -> SelfModifyingRule:
        """Add a rule that can modify itself."""
        rule = SelfModifyingRule(
            rule_id=str(uuid.uuid4()),
            premise=premise,
            conclusion=conclusion,
            confidence=confidence,
        )
        self.self_modifying_engine.add_rule(rule)
        return rule
    
    def soft_reason(
        self,
        predicate: str,
        subject_embedding: np.ndarray,
        object_embedding: np.ndarray,
    ) -> Tuple[float, List[str]]:
        """Perform soft/differentiable reasoning."""
        return self.differentiable_logic.reason(
            predicate,
            subject_embedding,
            object_embedding,
        )
    
    def what_if(
        self,
        original_state: Dict[str, Any],
        intervention: Dict[str, Any],
        outcome_fn: Callable[[Dict[str, Any]], float],
    ) -> Counterfactual:
        """Counterfactual reasoning: what if we changed X?"""
        return self.counterfactual_reasoner.intervene(
            original_state,
            intervention,
            outcome_fn,
        )
    
    def track_pattern_temporally(
        self,
        content: Dict[str, Any],
    ) -> TemporalPattern:
        """Add a pattern with temporal tracking."""
        return self.temporal_manager.add_pattern(content)
    
    def get_status(self) -> Dict[str, Any]:
        """Get advanced Layer 4 status."""
        return {
            "layer": "4-advanced",
            "name": "Advanced Neuro-Symbolic Intelligence",
            "components": {
                "composition_engine": {
                    "composites": len(self.composition_engine.composites),
                    "patterns_stored": len(self.composition_engine.pattern_store),
                },
                "self_modifying_rules": {
                    "active_rules": len(self.self_modifying_engine.rules),
                    "graveyard": len(self.self_modifying_engine.graveyard),
                    "mutations": len(self.self_modifying_engine.mutation_history),
                },
                "differentiable_logic": {
                    "rules": len(self.differentiable_logic.rules),
                    "knowledge_predicates": len(self.differentiable_logic.knowledge),
                },
                "counterfactual_reasoner": {
                    "causal_relations": sum(
                        len(v) for v in self.counterfactual_reasoner.causal_model.values()
                    ),
                    "counterfactuals_generated": len(
                        self.counterfactual_reasoner.counterfactuals
                    ),
                },
                "temporal_patterns": {
                    "active": len(self.temporal_manager.patterns),
                    "activations": len(self.temporal_manager.activation_history),
                },
            },
            "base_layer4_connected": self.base is not None,
        }


# ============================================================================
# FACTORY
# ============================================================================

def get_advanced_layer4(
    base_layer4=None,
    embedding_dim: int = 128,
) -> Layer4AdvancedNeuroSymbolic:
    """Get advanced Layer 4 instance."""
    return Layer4AdvancedNeuroSymbolic(
        base_layer4=base_layer4,
        embedding_dim=embedding_dim,
    )
