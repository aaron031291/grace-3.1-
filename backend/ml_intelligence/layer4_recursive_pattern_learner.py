"""
Layer 4: Recursive Pattern Learner with Cross-Domain Intelligence

This is the neuro-symbolic intelligence layer that sits above Layer 3 governance.
It implements:
1. Recursive Self-Optimizing Learning Engine (RSOLE)
2. Cross-Domain Pattern Transfer
3. Meta-Recursive Evolution Framework
4. Downward flow to Layer 3 governance

The key insight from neuro-symbolic AI research:
- Neural networks find fuzzy patterns (similarity, clusters)
- Symbolic systems provide precise rules (logic, constraints)
- The magic happens when they inform each other RECURSIVELY

Architecture:
    Layer 4 (This) ──▶ Recursive Pattern Learning
         │              Cross-Domain Transfer
         │              Meta-Learning Evolution
         ▼
    Layer 3 ──────▶ Governance (Validated patterns become trusted)
         │          KPI Tracking (Domain performance)
         ▼
    Layer 1/2 ────▶ Facts & Understanding (Consume trusted patterns)
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import json
import uuid
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN DEFINITIONS
# ============================================================================

class PatternDomain(str, Enum):
    """Domains where patterns can be learned and transferred."""
    CODE = "code"                    # Code patterns (syntax, structure, fixes)
    HEALING = "healing"              # Self-healing patterns (error → fix)
    ERROR = "error"                  # Error patterns (symptoms, causes)
    TEMPLATE = "template"            # Template patterns (generation, transformation)
    REASONING = "reasoning"          # Reasoning patterns (logic, inference)
    KNOWLEDGE = "knowledge"          # Knowledge patterns (facts, relationships)
    WORKFLOW = "workflow"            # Workflow patterns (sequences, dependencies)
    TESTING = "testing"              # Testing patterns (assertions, coverage)


@dataclass
class AbstractPattern:
    """
    Domain-agnostic abstract pattern.
    
    This is the key to cross-domain transfer: patterns are abstracted
    to a common representation that can be applied across domains.
    """
    pattern_id: str
    abstract_form: Dict[str, Any]      # Domain-agnostic representation
    source_domain: PatternDomain       # Where pattern was discovered
    applicable_domains: List[PatternDomain]  # Where pattern can apply
    confidence: float                   # Pattern confidence (0-1)
    trust_score: float                  # Validated trust (0-1)
    abstraction_level: int              # 0=concrete, higher=more abstract
    support_count: int                  # Number of supporting examples
    transfer_count: int = 0             # Times successfully transferred
    validation_count: int = 0           # Times validated
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "abstract_form": self.abstract_form,
            "source_domain": self.source_domain.value,
            "applicable_domains": [d.value for d in self.applicable_domains],
            "confidence": self.confidence,
            "trust_score": self.trust_score,
            "abstraction_level": self.abstraction_level,
            "support_count": self.support_count,
            "transfer_count": self.transfer_count,
            "validation_count": self.validation_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class RecursiveLearningCycle:
    """
    Tracks one cycle of recursive learning.
    
    The RSOLE (Recursive Self-Optimizing Learning Engine) operates in cycles:
    1. Observe patterns in data
    2. Abstract to domain-agnostic form
    3. Test against knowledge base
    4. Refine rules based on feedback
    5. Store validated patterns
    6. Use patterns to find more patterns (RECURSIVE)
    """
    cycle_id: str
    cycle_number: int
    patterns_discovered: int
    patterns_abstracted: int
    patterns_validated: int
    patterns_transferred: int
    domains_touched: List[PatternDomain]
    improvement_score: float            # How much better than previous cycle
    started_at: datetime
    completed_at: datetime = None
    parent_cycle_id: Optional[str] = None  # Link to previous cycle (recursive)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "cycle_number": self.cycle_number,
            "patterns_discovered": self.patterns_discovered,
            "patterns_abstracted": self.patterns_abstracted,
            "patterns_validated": self.patterns_validated,
            "patterns_transferred": self.patterns_transferred,
            "domains_touched": [d.value for d in self.domains_touched],
            "improvement_score": self.improvement_score,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "parent_cycle_id": self.parent_cycle_id,
        }


# ============================================================================
# LAYER 4: RECURSIVE PATTERN LEARNER
# ============================================================================

class Layer4RecursivePatternLearner:
    """
    Layer 4: Recursive Pattern Learner with Cross-Domain Intelligence
    
    This is the highest intelligence layer in Grace's cognitive architecture.
    It learns patterns recursively and transfers them across domains.
    
    Key capabilities:
    1. RECURSIVE LEARNING: Patterns help find more patterns
    2. CROSS-DOMAIN TRANSFER: Patterns from one domain apply to others
    3. META-EVOLUTION: Learning rules themselves evolve
    4. GOVERNANCE EXPORT: Validated patterns flow to Layer 3
    """
    
    def __init__(
        self,
        neuro_symbolic_reasoner=None,
        rule_generator=None,
        rule_storage=None,
        governance_engine=None,
        learning_memory=None,
        min_confidence: float = 0.6,
        min_trust_for_transfer: float = 0.7,
        max_abstraction_level: int = 5,
        storage_path: Optional[Path] = None,
    ):
        """
        Initialize Layer 4 Recursive Pattern Learner.
        
        Args:
            neuro_symbolic_reasoner: NeuroSymbolicReasoner for neural+symbolic search
            rule_generator: NeuralToSymbolicRuleGenerator for pattern→rule
            rule_storage: RuleStorage for persisting rules
            governance_engine: Layer 3 governance for validation
            learning_memory: LearningMemoryManager for knowledge base
            min_confidence: Minimum confidence to keep pattern
            min_trust_for_transfer: Minimum trust for cross-domain transfer
            max_abstraction_level: Maximum abstraction depth
            storage_path: Path for pattern persistence
        """
        self.neuro_symbolic = neuro_symbolic_reasoner
        self.rule_generator = rule_generator
        self.rule_storage = rule_storage
        self.governance = governance_engine
        self.learning_memory = learning_memory
        
        self.min_confidence = min_confidence
        self.min_trust_for_transfer = min_trust_for_transfer
        self.max_abstraction_level = max_abstraction_level
        
        # Pattern storage
        self.patterns: Dict[str, AbstractPattern] = {}
        self.patterns_by_domain: Dict[PatternDomain, List[str]] = defaultdict(list)
        
        # Cycle tracking
        self.cycles: List[RecursiveLearningCycle] = []
        self.current_cycle_number = 0
        
        # Cross-domain transfer graph
        # Tracks which domains successfully transfer to which
        self.transfer_success: Dict[Tuple[PatternDomain, PatternDomain], float] = {}
        
        # Meta-learning: what abstraction strategies work
        self.abstraction_strategies: Dict[str, float] = {
            "keyword_extraction": 1.0,
            "structure_matching": 1.0,
            "relationship_mapping": 1.0,
            "type_generalization": 1.0,
        }
        
        # Persistence
        self.storage_path = storage_path or Path("backend/data/layer4_patterns")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing patterns
        self._load_patterns()
        
        logger.info(f"[LAYER4] Initialized with {len(self.patterns)} existing patterns")
    
    # ========================================================================
    # CORE RECURSIVE LEARNING
    # ========================================================================
    
    def run_recursive_cycle(
        self,
        domain: PatternDomain,
        data: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        max_iterations: int = 3,
    ) -> RecursiveLearningCycle:
        """
        Run a recursive learning cycle.
        
        This is the heart of RSOLE:
        1. Discover patterns in data
        2. Abstract to transferable form
        3. Validate against knowledge base
        4. Transfer to applicable domains
        5. Use new patterns to discover more (recursive)
        
        Args:
            domain: Primary domain for learning
            data: Raw data to learn from
            context: Additional context
            max_iterations: Maximum recursive depth
            
        Returns:
            RecursiveLearningCycle with results
        """
        self.current_cycle_number += 1
        cycle_id = str(uuid.uuid4())
        
        cycle = RecursiveLearningCycle(
            cycle_id=cycle_id,
            cycle_number=self.current_cycle_number,
            patterns_discovered=0,
            patterns_abstracted=0,
            patterns_validated=0,
            patterns_transferred=0,
            domains_touched=[domain],
            improvement_score=0.0,
            started_at=datetime.utcnow(),
            parent_cycle_id=self.cycles[-1].cycle_id if self.cycles else None,
        )
        
        try:
            # ========== STEP 1: Discover Patterns ==========
            raw_patterns = self._discover_patterns(domain, data, context)
            cycle.patterns_discovered = len(raw_patterns)
            logger.info(f"[LAYER4] Cycle {cycle.cycle_number}: Discovered {len(raw_patterns)} patterns")
            
            # ========== STEP 2: Abstract Patterns ==========
            abstract_patterns = self._abstract_patterns(raw_patterns, domain)
            cycle.patterns_abstracted = len(abstract_patterns)
            logger.info(f"[LAYER4] Cycle {cycle.cycle_number}: Abstracted {len(abstract_patterns)} patterns")
            
            # ========== STEP 3: Validate Against KB ==========
            validated_patterns = self._validate_patterns(abstract_patterns)
            cycle.patterns_validated = len(validated_patterns)
            logger.info(f"[LAYER4] Cycle {cycle.cycle_number}: Validated {len(validated_patterns)} patterns")
            
            # ========== STEP 4: Cross-Domain Transfer ==========
            transferred_count = self._transfer_patterns(validated_patterns)
            cycle.patterns_transferred = transferred_count
            logger.info(f"[LAYER4] Cycle {cycle.cycle_number}: Transferred {transferred_count} patterns")
            
            # ========== STEP 5: Export to Layer 3 Governance ==========
            self._export_to_governance(validated_patterns)
            
            # ========== STEP 6: Store Patterns ==========
            for pattern in validated_patterns:
                self._store_pattern(pattern)
            
            # ========== STEP 7: RECURSIVE - Use patterns to find more ==========
            if max_iterations > 1 and validated_patterns:
                # Use newly discovered patterns as seeds for next iteration
                enhanced_data = self._enhance_data_with_patterns(data, validated_patterns)
                
                if len(enhanced_data) > len(data):
                    # Recursively learn with enhanced data
                    sub_cycle = self.run_recursive_cycle(
                        domain=domain,
                        data=enhanced_data,
                        context=context,
                        max_iterations=max_iterations - 1,
                    )
                    
                    # Aggregate results
                    cycle.patterns_discovered += sub_cycle.patterns_discovered
                    cycle.patterns_validated += sub_cycle.patterns_validated
                    cycle.patterns_transferred += sub_cycle.patterns_transferred
                    cycle.domains_touched.extend(
                        d for d in sub_cycle.domains_touched 
                        if d not in cycle.domains_touched
                    )
            
            # Calculate improvement score
            cycle.improvement_score = self._calculate_improvement(cycle)
            
        except Exception as e:
            logger.error(f"[LAYER4] Cycle {cycle.cycle_number} failed: {e}", exc_info=True)
        
        cycle.completed_at = datetime.utcnow()
        self.cycles.append(cycle)
        
        # Persist state
        self._save_patterns()
        
        return cycle
    
    def _discover_patterns(
        self,
        domain: PatternDomain,
        data: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Discover patterns in data using neuro-symbolic reasoning.
        
        Uses both:
        - Neural: Embedding similarity, clustering
        - Symbolic: Rule matching, constraint checking
        """
        patterns = []
        
        # Extract texts from data
        texts = []
        for item in data:
            text = item.get("text", "") or item.get("content", "") or str(item)
            if text:
                texts.append(text)
        
        if not texts:
            return patterns
        
        # Use rule generator to detect neural patterns
        if self.rule_generator:
            try:
                neural_patterns = self.rule_generator.detect_patterns(
                    texts=texts,
                    num_clusters=min(10, len(texts) // 2 + 1),
                    instruction=f"Find patterns related to {domain.value}",
                )
                
                for np_pattern in neural_patterns:
                    patterns.append({
                        "type": "neural_cluster",
                        "pattern_id": np_pattern.pattern_id,
                        "members": np_pattern.members,
                        "confidence": np_pattern.confidence,
                        "features": np_pattern.features,
                        "support_count": np_pattern.support_count,
                    })
            except Exception as e:
                logger.warning(f"[LAYER4] Neural pattern detection failed: {e}")
        
        # Use neuro-symbolic reasoner for cross-referenced patterns
        if self.neuro_symbolic:
            try:
                # Query for patterns using neuro-symbolic fusion
                for text in texts[:20]:  # Limit to avoid overload
                    result = self.neuro_symbolic.reason(
                        query=f"Find patterns in: {text[:200]}",
                        context={"domain": domain.value},
                        limit=5,
                    )
                    
                    if result.fused_results:
                        patterns.append({
                            "type": "neuro_symbolic",
                            "query": text[:100],
                            "fused_results": result.fused_results[:3],
                            "neural_confidence": result.neural_confidence,
                            "symbolic_confidence": result.symbolic_confidence,
                            "fusion_confidence": result.fusion_confidence,
                        })
            except Exception as e:
                logger.warning(f"[LAYER4] Neuro-symbolic reasoning failed: {e}")
        
        # Look for existing patterns in this domain that match
        domain_patterns = self.patterns_by_domain.get(domain, [])
        for pattern_id in domain_patterns[:10]:  # Limit
            existing = self.patterns.get(pattern_id)
            if existing and existing.trust_score >= self.min_confidence:
                # Check if existing pattern matches new data
                match_score = self._pattern_match_score(existing, texts)
                if match_score > 0.5:
                    patterns.append({
                        "type": "existing_match",
                        "pattern_id": existing.pattern_id,
                        "match_score": match_score,
                        "trust_score": existing.trust_score,
                        "abstract_form": existing.abstract_form,
                    })
        
        return patterns
    
    def _abstract_patterns(
        self,
        raw_patterns: List[Dict[str, Any]],
        domain: PatternDomain,
    ) -> List[AbstractPattern]:
        """
        Abstract raw patterns to domain-agnostic form.
        
        This is crucial for cross-domain transfer:
        - Remove domain-specific details
        - Keep structural/logical essence
        - Create transferable representation
        """
        abstract_patterns = []
        
        for raw in raw_patterns:
            try:
                abstract_form = self._create_abstract_form(raw, domain)
                
                if not abstract_form:
                    continue
                
                # Determine applicable domains
                applicable = self._determine_applicable_domains(abstract_form, domain)
                
                # Calculate abstraction level
                level = self._calculate_abstraction_level(abstract_form)
                
                pattern = AbstractPattern(
                    pattern_id=str(uuid.uuid4()),
                    abstract_form=abstract_form,
                    source_domain=domain,
                    applicable_domains=applicable,
                    confidence=raw.get("confidence", 0.5) or raw.get("fusion_confidence", 0.5),
                    trust_score=raw.get("trust_score", 0.5),
                    abstraction_level=level,
                    support_count=raw.get("support_count", 1),
                )
                
                # Skip low confidence patterns
                if pattern.confidence >= self.min_confidence:
                    abstract_patterns.append(pattern)
                    
            except Exception as e:
                logger.warning(f"[LAYER4] Failed to abstract pattern: {e}")
        
        return abstract_patterns
    
    def _create_abstract_form(
        self,
        raw: Dict[str, Any],
        domain: PatternDomain,
    ) -> Dict[str, Any]:
        """
        Create domain-agnostic abstract form from raw pattern.
        
        The abstract form captures:
        - Structure (how things relate)
        - Roles (what things do, not what they are)
        - Constraints (what must hold)
        - Transformations (how things change)
        """
        abstract = {
            "structure": {},
            "roles": [],
            "constraints": [],
            "transformations": [],
            "keywords": [],
            "relationships": [],
        }
        
        pattern_type = raw.get("type", "unknown")
        
        if pattern_type == "neural_cluster":
            # Abstract from neural cluster
            members = raw.get("members", [])
            features = raw.get("features", {})
            
            # Extract keywords (domain-agnostic)
            abstract["keywords"] = features.get("common_keywords", [])[:5]
            
            # Structure: clustering pattern
            abstract["structure"] = {
                "type": "cluster",
                "size": len(members),
                "cohesion": raw.get("confidence", 0.5),
            }
            
            # Roles: member and center
            abstract["roles"] = ["member", "cluster_center"]
            
            # Constraint: members are similar
            abstract["constraints"].append({
                "type": "similarity",
                "threshold": 0.5,
            })
            
        elif pattern_type == "neuro_symbolic":
            # Abstract from neuro-symbolic fusion
            fused = raw.get("fused_results", [])
            
            if fused:
                # Extract common structure from fused results
                sources = set()
                for r in fused:
                    sources.add(r.get("source", "unknown"))
                
                abstract["structure"] = {
                    "type": "fusion",
                    "sources": list(sources),
                    "neural_weight": raw.get("neural_confidence", 0.5),
                    "symbolic_weight": raw.get("symbolic_confidence", 0.5),
                }
                
                # Roles: neural contributor, symbolic validator
                abstract["roles"] = ["neural_contributor", "symbolic_validator", "fused_result"]
                
                # Constraint: must pass both neural and symbolic
                abstract["constraints"].append({
                    "type": "dual_validation",
                    "min_fusion_confidence": 0.5,
                })
                
        elif pattern_type == "existing_match":
            # Use existing abstract form
            abstract = raw.get("abstract_form", abstract)
            
            # Add relationship to original
            abstract["relationships"].append({
                "type": "derived_from",
                "source_id": raw.get("pattern_id"),
            })
        
        # Add domain-specific to domain-agnostic mappings
        abstract["_original_domain"] = domain.value
        abstract["_abstraction_strategy"] = self._select_abstraction_strategy(domain)
        
        return abstract
    
    def _select_abstraction_strategy(self, domain: PatternDomain) -> str:
        """Select best abstraction strategy based on meta-learning."""
        # Weight by historical success
        strategies = list(self.abstraction_strategies.items())
        weights = [s[1] for s in strategies]
        total = sum(weights)
        
        if total == 0:
            return strategies[0][0]
        
        # Weighted random selection
        r = np.random.random() * total
        cumulative = 0
        for strategy, weight in strategies:
            cumulative += weight
            if r <= cumulative:
                return strategy
        
        return strategies[0][0]
    
    def _determine_applicable_domains(
        self,
        abstract_form: Dict[str, Any],
        source_domain: PatternDomain,
    ) -> List[PatternDomain]:
        """
        Determine which domains an abstract pattern can apply to.
        
        Uses:
        - Transfer success history
        - Structural similarity
        - Role compatibility
        """
        applicable = [source_domain]  # Always applicable to source
        
        structure_type = abstract_form.get("structure", {}).get("type", "")
        roles = abstract_form.get("roles", [])
        
        # Check each domain for compatibility
        for domain in PatternDomain:
            if domain == source_domain:
                continue
            
            # Check transfer history
            transfer_key = (source_domain, domain)
            historical_success = self.transfer_success.get(transfer_key, 0.5)
            
            # Check structural compatibility
            structural_compat = self._check_structural_compatibility(
                structure_type, roles, domain
            )
            
            # Combined score
            transfer_score = 0.6 * historical_success + 0.4 * structural_compat
            
            if transfer_score >= 0.5:
                applicable.append(domain)
        
        return applicable
    
    def _check_structural_compatibility(
        self,
        structure_type: str,
        roles: List[str],
        target_domain: PatternDomain,
    ) -> float:
        """Check if structure/roles are compatible with target domain."""
        # Domain-agnostic structural compatibility rules
        compatibility_matrix = {
            # structure_type -> compatible domains
            "cluster": [PatternDomain.CODE, PatternDomain.ERROR, PatternDomain.TEMPLATE],
            "fusion": [PatternDomain.REASONING, PatternDomain.KNOWLEDGE],
            "sequence": [PatternDomain.WORKFLOW, PatternDomain.HEALING],
            "transformation": [PatternDomain.TEMPLATE, PatternDomain.CODE],
            "conditional": [PatternDomain.HEALING, PatternDomain.TESTING],
        }
        
        compatible_domains = compatibility_matrix.get(structure_type, list(PatternDomain))
        
        if target_domain in compatible_domains:
            return 0.8
        
        # Partial compatibility based on roles
        role_compatibility = {
            "member": 0.3,
            "cluster_center": 0.2,
            "neural_contributor": 0.4,
            "symbolic_validator": 0.5,
            "fused_result": 0.4,
        }
        
        score = 0.3  # Base compatibility
        for role in roles:
            score += role_compatibility.get(role, 0.1)
        
        return min(1.0, score)
    
    def _calculate_abstraction_level(self, abstract_form: Dict[str, Any]) -> int:
        """
        Calculate abstraction level (0=concrete, higher=more abstract).
        
        Based on:
        - How many domain-specific details remain
        - Depth of generalization
        - Transferability
        """
        level = 0
        
        # More keywords = more concrete
        keywords = abstract_form.get("keywords", [])
        if len(keywords) < 3:
            level += 1
        
        # More constraints = more abstract (captures essence)
        constraints = abstract_form.get("constraints", [])
        level += len(constraints)
        
        # Relationships to other patterns = higher abstraction
        relationships = abstract_form.get("relationships", [])
        level += len(relationships)
        
        # Fusion structure = higher abstraction
        structure_type = abstract_form.get("structure", {}).get("type", "")
        if structure_type == "fusion":
            level += 1
        
        return min(level, self.max_abstraction_level)
    
    def _validate_patterns(
        self,
        patterns: List[AbstractPattern],
    ) -> List[AbstractPattern]:
        """
        Validate patterns against knowledge base and governance.
        
        A pattern is valid if:
        1. It doesn't contradict existing knowledge
        2. It passes governance checks (if available)
        3. It has sufficient support
        """
        validated = []
        
        for pattern in patterns:
            is_valid = True
            
            # Check for contradictions
            if self.learning_memory:
                try:
                    contradiction = self._check_contradictions(pattern)
                    if contradiction:
                        logger.debug(f"[LAYER4] Pattern {pattern.pattern_id[:8]} contradicts KB")
                        is_valid = False
                except Exception as e:
                    logger.warning(f"[LAYER4] Contradiction check failed: {e}")
            
            # Check governance (if available)
            if is_valid and self.governance:
                try:
                    gov_result = self._check_governance(pattern)
                    if not gov_result.get("approved", True):
                        logger.debug(f"[LAYER4] Pattern {pattern.pattern_id[:8]} rejected by governance")
                        is_valid = False
                    else:
                        # Update trust score from governance
                        pattern.trust_score = gov_result.get("trust_score", pattern.trust_score)
                except Exception as e:
                    logger.warning(f"[LAYER4] Governance check failed: {e}")
            
            # Check support count
            if is_valid and pattern.support_count < 2:
                logger.debug(f"[LAYER4] Pattern {pattern.pattern_id[:8]} has insufficient support")
                is_valid = False
            
            if is_valid:
                pattern.validation_count += 1
                validated.append(pattern)
        
        return validated
    
    def _check_contradictions(self, pattern: AbstractPattern) -> bool:
        """Check if pattern contradicts existing knowledge."""
        # Look for existing patterns with conflicting constraints
        for existing_id in self.patterns_by_domain.get(pattern.source_domain, []):
            existing = self.patterns.get(existing_id)
            if not existing:
                continue
            
            # Check for conflicting constraints
            existing_constraints = existing.abstract_form.get("constraints", [])
            pattern_constraints = pattern.abstract_form.get("constraints", [])
            
            for ec in existing_constraints:
                for pc in pattern_constraints:
                    if self._constraints_conflict(ec, pc):
                        return True
        
        return False
    
    def _constraints_conflict(
        self,
        constraint1: Dict[str, Any],
        constraint2: Dict[str, Any],
    ) -> bool:
        """Check if two constraints conflict."""
        # Same type, different values = potential conflict
        if constraint1.get("type") == constraint2.get("type"):
            # Numeric thresholds: check if ranges overlap
            if "threshold" in constraint1 and "threshold" in constraint2:
                t1 = constraint1["threshold"]
                t2 = constraint2["threshold"]
                # Significant difference = conflict
                if abs(t1 - t2) > 0.3:
                    return True
        
        return False
    
    def _check_governance(self, pattern: AbstractPattern) -> Dict[str, Any]:
        """Check pattern against Layer 3 governance."""
        # Default approval if no governance
        if not self.governance:
            return {"approved": True, "trust_score": pattern.trust_score}
        
        try:
            # Use governance trust assessment
            if hasattr(self.governance, 'assess_trust'):
                assessment = self.governance.assess_trust(
                    data=pattern.to_dict(),
                    origin="layer4_pattern",
                )
                return {
                    "approved": assessment.get("trust_score", 0.5) >= 0.4,
                    "trust_score": assessment.get("trust_score", 0.5),
                }
        except Exception as e:
            logger.warning(f"[LAYER4] Governance assessment failed: {e}")
        
        return {"approved": True, "trust_score": pattern.trust_score}
    
    # ========================================================================
    # CROSS-DOMAIN TRANSFER
    # ========================================================================
    
    def _transfer_patterns(
        self,
        patterns: List[AbstractPattern],
    ) -> int:
        """
        Transfer patterns to applicable domains.
        
        High-trust patterns can be applied to other domains.
        This is the core of cross-domain intelligence.
        """
        transferred_count = 0
        
        for pattern in patterns:
            if pattern.trust_score < self.min_trust_for_transfer:
                continue
            
            for target_domain in pattern.applicable_domains:
                if target_domain == pattern.source_domain:
                    continue  # Skip source domain
                
                # Create domain-specific instance
                success = self._transfer_to_domain(pattern, target_domain)
                
                if success:
                    transferred_count += 1
                    pattern.transfer_count += 1
                    
                    # Update transfer success history
                    key = (pattern.source_domain, target_domain)
                    current = self.transfer_success.get(key, 0.5)
                    self.transfer_success[key] = current * 0.9 + 0.1  # Increase
                    
                    logger.debug(
                        f"[LAYER4] Transferred pattern {pattern.pattern_id[:8]} "
                        f"from {pattern.source_domain.value} to {target_domain.value}"
                    )
        
        return transferred_count
    
    def _transfer_to_domain(
        self,
        pattern: AbstractPattern,
        target_domain: PatternDomain,
    ) -> bool:
        """Transfer a pattern to a specific domain."""
        try:
            # Create domain-specific version
            domain_pattern = AbstractPattern(
                pattern_id=str(uuid.uuid4()),
                abstract_form=self._adapt_to_domain(pattern.abstract_form, target_domain),
                source_domain=pattern.source_domain,  # Keep original source
                applicable_domains=[target_domain],
                confidence=pattern.confidence * 0.9,  # Slight reduction for transfer
                trust_score=pattern.trust_score * 0.85,  # Trust reduces on transfer
                abstraction_level=pattern.abstraction_level,
                support_count=pattern.support_count,
                transfer_count=0,
                validation_count=0,
            )
            
            # Add relationship to original
            domain_pattern.abstract_form["relationships"].append({
                "type": "transferred_from",
                "source_id": pattern.pattern_id,
                "source_domain": pattern.source_domain.value,
            })
            
            # Store the transferred pattern
            self._store_pattern(domain_pattern)
            
            return True
            
        except Exception as e:
            logger.warning(f"[LAYER4] Transfer to {target_domain.value} failed: {e}")
            return False
    
    def _adapt_to_domain(
        self,
        abstract_form: Dict[str, Any],
        target_domain: PatternDomain,
    ) -> Dict[str, Any]:
        """Adapt abstract form to target domain."""
        adapted = abstract_form.copy()
        
        # Add domain-specific hints
        adapted["_target_domain"] = target_domain.value
        
        # Adjust roles for domain
        domain_role_mappings = {
            PatternDomain.CODE: {
                "member": "code_element",
                "cluster_center": "pattern_exemplar",
            },
            PatternDomain.HEALING: {
                "member": "symptom",
                "cluster_center": "fix_template",
            },
            PatternDomain.ERROR: {
                "member": "error_instance",
                "cluster_center": "error_category",
            },
            PatternDomain.TEMPLATE: {
                "member": "template_variant",
                "cluster_center": "base_template",
            },
        }
        
        mappings = domain_role_mappings.get(target_domain, {})
        adapted_roles = []
        for role in adapted.get("roles", []):
            adapted_roles.append(mappings.get(role, role))
        adapted["roles"] = adapted_roles
        
        return adapted
    
    # ========================================================================
    # GOVERNANCE EXPORT (Layer 4 → Layer 3)
    # ========================================================================
    
    def _export_to_governance(self, patterns: List[AbstractPattern]):
        """
        Export validated patterns to Layer 3 governance.
        
        High-trust patterns become part of the trusted knowledge base.
        This is the downward flow from Layer 4 to Layer 3.
        """
        if not self.governance:
            return
        
        for pattern in patterns:
            if pattern.trust_score < 0.7:
                continue  # Only export high-trust patterns
            
            try:
                # Convert to governance-compatible format
                gov_data = {
                    "type": "layer4_pattern",
                    "pattern_id": pattern.pattern_id,
                    "source_domain": pattern.source_domain.value,
                    "trust_score": pattern.trust_score,
                    "confidence": pattern.confidence,
                    "abstraction_level": pattern.abstraction_level,
                    "support_count": pattern.support_count,
                    "validation_count": pattern.validation_count,
                    "transfer_count": pattern.transfer_count,
                    "abstract_form": pattern.abstract_form,
                }
                
                # Add to governance whitelist if very high trust
                if pattern.trust_score >= 0.9 and hasattr(self.governance, 'add_to_whitelist'):
                    self.governance.add_to_whitelist(
                        source=f"layer4_pattern_{pattern.pattern_id[:8]}",
                        data=gov_data,
                    )
                    logger.info(
                        f"[LAYER4] Exported pattern {pattern.pattern_id[:8]} "
                        f"to governance whitelist (trust={pattern.trust_score:.2f})"
                    )
                
                # Record KPI for the domain
                if hasattr(self.governance, 'record_component_outcome'):
                    self.governance.record_component_outcome(
                        component_id=f"layer4_{pattern.source_domain.value}",
                        success=True,
                        meets_grace_standard=pattern.trust_score >= 0.7,
                        meets_user_standard=pattern.confidence >= 0.6,
                        weight=1.0,
                    )
                    
            except Exception as e:
                logger.warning(f"[LAYER4] Governance export failed: {e}")
    
    # ========================================================================
    # PATTERN STORAGE & RETRIEVAL
    # ========================================================================
    
    def _store_pattern(self, pattern: AbstractPattern):
        """Store a pattern in memory and by domain."""
        self.patterns[pattern.pattern_id] = pattern
        
        # Index by source domain
        if pattern.pattern_id not in self.patterns_by_domain[pattern.source_domain]:
            self.patterns_by_domain[pattern.source_domain].append(pattern.pattern_id)
        
        # Index by applicable domains
        for domain in pattern.applicable_domains:
            if pattern.pattern_id not in self.patterns_by_domain[domain]:
                self.patterns_by_domain[domain].append(pattern.pattern_id)
        
        # Also store as symbolic rule if rule_storage available
        if self.rule_storage:
            try:
                from ml_intelligence.neural_to_symbolic_rule_generator import SymbolicRule
                
                rule = SymbolicRule(
                    rule_id=pattern.pattern_id,
                    premise=pattern.abstract_form.get("constraints", [{}])[0] if pattern.abstract_form.get("constraints") else {},
                    conclusion={"pattern_id": pattern.pattern_id, "domain": pattern.source_domain.value},
                    trust_score=pattern.trust_score,
                    confidence=pattern.confidence,
                    source="layer4_recursive",
                    source_pattern_id=pattern.pattern_id,
                    support_count=pattern.support_count,
                    validation_count=pattern.validation_count,
                )
                
                self.rule_storage.store_rule(rule, pattern_type="layer4_pattern")
                
            except Exception as e:
                logger.warning(f"[LAYER4] Rule storage failed: {e}")
    
    def _pattern_match_score(
        self,
        pattern: AbstractPattern,
        texts: List[str],
    ) -> float:
        """Calculate how well a pattern matches new texts."""
        if not texts:
            return 0.0
        
        keywords = pattern.abstract_form.get("keywords", [])
        if not keywords:
            return 0.3  # Default partial match
        
        # Check keyword overlap
        all_text = " ".join(texts).lower()
        matches = sum(1 for kw in keywords if kw.lower() in all_text)
        
        return min(1.0, matches / len(keywords)) if keywords else 0.3
    
    def _enhance_data_with_patterns(
        self,
        data: List[Dict[str, Any]],
        patterns: List[AbstractPattern],
    ) -> List[Dict[str, Any]]:
        """
        Use patterns to enhance/augment data for next recursive iteration.
        
        This is the RECURSIVE part: patterns help find more patterns.
        """
        enhanced = list(data)  # Start with original
        
        for pattern in patterns:
            # Generate synthetic examples from pattern
            synthetic = self._generate_from_pattern(pattern)
            if synthetic:
                enhanced.extend(synthetic)
        
        return enhanced
    
    def _generate_from_pattern(
        self,
        pattern: AbstractPattern,
    ) -> List[Dict[str, Any]]:
        """Generate synthetic examples from a pattern."""
        synthetic = []
        
        # Use keywords to generate variations
        keywords = pattern.abstract_form.get("keywords", [])
        structure = pattern.abstract_form.get("structure", {})
        
        if keywords:
            # Simple: create text from keywords
            text = " ".join(keywords)
            synthetic.append({
                "text": text,
                "source": "pattern_synthetic",
                "pattern_id": pattern.pattern_id,
            })
        
        if structure.get("type") == "cluster":
            # Generate cluster-like examples
            synthetic.append({
                "text": f"Example from {pattern.source_domain.value} cluster",
                "source": "pattern_synthetic",
                "pattern_id": pattern.pattern_id,
            })
        
        return synthetic
    
    def _calculate_improvement(self, cycle: RecursiveLearningCycle) -> float:
        """Calculate improvement score for a cycle."""
        if not self.cycles:
            return 1.0  # First cycle: baseline
        
        prev_cycle = self.cycles[-1]
        
        # Compare key metrics
        discovery_improvement = (
            cycle.patterns_discovered / max(1, prev_cycle.patterns_discovered)
        )
        validation_improvement = (
            cycle.patterns_validated / max(1, prev_cycle.patterns_validated)
        )
        transfer_improvement = (
            cycle.patterns_transferred / max(1, prev_cycle.patterns_transferred)
        )
        
        # Weighted average
        improvement = (
            0.3 * discovery_improvement +
            0.4 * validation_improvement +
            0.3 * transfer_improvement
        )
        
        return improvement
    
    # ========================================================================
    # PERSISTENCE
    # ========================================================================
    
    def _save_patterns(self):
        """Save patterns to disk."""
        try:
            patterns_file = self.storage_path / "patterns.json"
            
            data = {
                "patterns": {
                    pid: p.to_dict() for pid, p in self.patterns.items()
                },
                "patterns_by_domain": {
                    d.value: pids for d, pids in self.patterns_by_domain.items()
                },
                "transfer_success": {
                    f"{k[0].value}->{k[1].value}": v 
                    for k, v in self.transfer_success.items()
                },
                "abstraction_strategies": self.abstraction_strategies,
                "current_cycle_number": self.current_cycle_number,
                "cycles": [c.to_dict() for c in self.cycles[-100:]],  # Last 100
            }
            
            with open(patterns_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"[LAYER4] Failed to save patterns: {e}")
    
    def _load_patterns(self):
        """Load patterns from disk."""
        try:
            patterns_file = self.storage_path / "patterns.json"
            
            if not patterns_file.exists():
                return
            
            with open(patterns_file, 'r') as f:
                data = json.load(f)
            
            # Restore patterns
            for pid, pdata in data.get("patterns", {}).items():
                try:
                    pattern = AbstractPattern(
                        pattern_id=pdata["pattern_id"],
                        abstract_form=pdata["abstract_form"],
                        source_domain=PatternDomain(pdata["source_domain"]),
                        applicable_domains=[
                            PatternDomain(d) for d in pdata["applicable_domains"]
                        ],
                        confidence=pdata["confidence"],
                        trust_score=pdata["trust_score"],
                        abstraction_level=pdata["abstraction_level"],
                        support_count=pdata["support_count"],
                        transfer_count=pdata.get("transfer_count", 0),
                        validation_count=pdata.get("validation_count", 0),
                        created_at=datetime.fromisoformat(pdata["created_at"]),
                        updated_at=datetime.fromisoformat(pdata["updated_at"]),
                    )
                    self.patterns[pid] = pattern
                except Exception as e:
                    logger.warning(f"[LAYER4] Failed to load pattern {pid}: {e}")
            
            # Restore domain index
            for domain_str, pids in data.get("patterns_by_domain", {}).items():
                try:
                    domain = PatternDomain(domain_str)
                    self.patterns_by_domain[domain] = pids
                except ValueError:
                    pass
            
            # Restore transfer success
            for key_str, value in data.get("transfer_success", {}).items():
                try:
                    parts = key_str.split("->")
                    if len(parts) == 2:
                        key = (PatternDomain(parts[0]), PatternDomain(parts[1]))
                        self.transfer_success[key] = value
                except ValueError:
                    pass
            
            # Restore strategies
            self.abstraction_strategies.update(data.get("abstraction_strategies", {}))
            
            # Restore cycle number
            self.current_cycle_number = data.get("current_cycle_number", 0)
            
            logger.info(f"[LAYER4] Loaded {len(self.patterns)} patterns")
            
        except Exception as e:
            logger.error(f"[LAYER4] Failed to load patterns: {e}")
    
    # ========================================================================
    # PUBLIC API
    # ========================================================================
    
    def get_patterns_for_domain(
        self,
        domain: PatternDomain,
        min_trust: float = 0.5,
        limit: int = 50,
    ) -> List[AbstractPattern]:
        """Get patterns applicable to a domain."""
        pattern_ids = self.patterns_by_domain.get(domain, [])
        
        patterns = []
        for pid in pattern_ids:
            pattern = self.patterns.get(pid)
            if pattern and pattern.trust_score >= min_trust:
                patterns.append(pattern)
        
        # Sort by trust score
        patterns.sort(key=lambda p: p.trust_score, reverse=True)
        
        return patterns[:limit]
    
    def query_patterns(
        self,
        query: str,
        domain: Optional[PatternDomain] = None,
        limit: int = 10,
    ) -> List[Tuple[AbstractPattern, float]]:
        """
        Query patterns by text similarity.
        
        Uses neuro-symbolic reasoning if available.
        """
        results = []
        
        # Get candidate patterns
        if domain:
            candidates = self.get_patterns_for_domain(domain, min_trust=0.3, limit=100)
        else:
            candidates = list(self.patterns.values())
        
        # Score each pattern
        query_lower = query.lower()
        for pattern in candidates:
            score = 0.0
            
            # Keyword matching
            keywords = pattern.abstract_form.get("keywords", [])
            for kw in keywords:
                if kw.lower() in query_lower:
                    score += 0.2
            
            # Trust score contribution
            score += pattern.trust_score * 0.3
            
            # Confidence contribution
            score += pattern.confidence * 0.2
            
            if score > 0:
                results.append((pattern, min(1.0, score)))
        
        # Sort by score
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:limit]
    
    def get_cross_domain_insights(self) -> Dict[str, Any]:
        """Get insights about cross-domain pattern transfer."""
        return {
            "total_patterns": len(self.patterns),
            "patterns_by_domain": {
                d.value: len(pids) for d, pids in self.patterns_by_domain.items()
            },
            "transfer_success_rates": {
                f"{k[0].value}->{k[1].value}": v 
                for k, v in sorted(
                    self.transfer_success.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:20]
            },
            "abstraction_strategies": self.abstraction_strategies,
            "total_cycles": len(self.cycles),
            "current_cycle": self.current_cycle_number,
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get Layer 4 status."""
        return {
            "layer": 4,
            "name": "Recursive Pattern Learner",
            "total_patterns": len(self.patterns),
            "total_cycles": len(self.cycles),
            "domains_active": [d.value for d in self.patterns_by_domain.keys()],
            "neuro_symbolic_connected": self.neuro_symbolic is not None,
            "governance_connected": self.governance is not None,
            "learning_memory_connected": self.learning_memory is not None,
            "min_confidence": self.min_confidence,
            "min_trust_for_transfer": self.min_trust_for_transfer,
        }


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def get_layer4_recursive_learner(
    neuro_symbolic_reasoner=None,
    rule_generator=None,
    rule_storage=None,
    governance_engine=None,
    learning_memory=None,
) -> Layer4RecursivePatternLearner:
    """
    Get Layer 4 Recursive Pattern Learner instance.
    
    Args:
        neuro_symbolic_reasoner: NeuroSymbolicReasoner (optional)
        rule_generator: NeuralToSymbolicRuleGenerator (optional)
        rule_storage: RuleStorage (optional)
        governance_engine: Layer 3 governance (optional)
        learning_memory: LearningMemoryManager (optional)
        
    Returns:
        Layer4RecursivePatternLearner instance
    """
    return Layer4RecursivePatternLearner(
        neuro_symbolic_reasoner=neuro_symbolic_reasoner,
        rule_generator=rule_generator,
        rule_storage=rule_storage,
        governance_engine=governance_engine,
        learning_memory=learning_memory,
    )
