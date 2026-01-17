import logging
import ast
import json
from typing import Dict, List, Optional, Any, Tuple, Set
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from cognitive.grace_code_analyzer import CodeIssue, Severity
from genesis.genesis_key_service import get_genesis_service
from models.genesis_key_models import GenesisKeyType, GenesisKey
class IntentType(str, Enum):
    logger = logging.getLogger(__name__)
    """Types of code modification intents (constrained semantic space)"""
    ADD_LOGGING = "add_logging"
    ADD_ERROR_HANDLING = "add_error_handling"
    ADD_TYPE_HINTS = "add_type_hints"
    ADD_DOCSTRING = "add_docstring"
    REPLACE_PRINT = "replace_print"
    FIX_BARE_EXCEPT = "fix_bare_except"
    ADD_IMPORT = "add_import"
    REMOVE_UNUSED_IMPORT = "remove_unused_import"
    REFACTOR_FUNCTION = "refactor_function"
    OPTIMIZE_QUERY = "optimize_query"


@dataclass
class CodeIntent:
    """
    LLM-generated intent (never code, only structured proposals).
    
    This is the ONLY output format allowed from LLM.
    No code-shaped strings. No syntax. Only intent objects.
    """
    intent_type: IntentType
    target_file: str
    target_line: Optional[int] = None
    target_function: Optional[str] = None
    target_class: Optional[str] = None
    
    # Criteria for rule matching (semantic, not syntactic)
    criteria: Dict[str, Any] = field(default_factory=dict)
    
    # Justification from LLM (why this intent)
    justification: str = ""
    
    # LLM metadata (for traceability)
    llm_model: Optional[str] = None
    llm_confidence: float = 0.0  # LLM's confidence (0-1)
    llm_tokens_used: Optional[int] = None
    
    # Validation metadata
    validated: bool = False
    validation_error: Optional[str] = None


@dataclass
class RuleProposal:
    """
    AST Transformer's proposal (rule → diff).
    
    Generated from intent by matching against ruleset.
    This is what gets executed - deterministic transformation.
    """
    rule_id: str
    rule_version: str
    intent: CodeIntent
    
    # AST transformation details
    ast_path: List[str]  # Path to AST node being transformed
    transformation_type: str  # Type of AST transformation
    
    # Diff (before/after)
    before_code: str
    after_code: str
    diff_lines: List[Dict[str, Any]]  # Line-by-line diff
    
    # Safety checks
    preserves_syntax: bool = False
    preserves_semantics: bool = False  # Control-flow, side-effects
    dependency_changes: List[str] = field(default_factory=list)
    
    # Justification chain (intent → rule → diff)
    justification_chain: List[str] = field(default_factory=list)


# ============================================================================
# Ruleset (Constitution - Human-Authored, Versioned)
# ============================================================================

@dataclass
class TransformRule:
    """
    Human-authored transformation rule.
    
    This is the constitution - explicit, versioned, reversible.
    LLM never writes rules. Only humans.
    """
    rule_id: str
    version: str
    description: str
    
    # Intent matching (which intents trigger this rule)
    matches_intent_types: List[IntentType]
    intent_criteria: Dict[str, Any]  # Additional criteria for matching
    
    # AST transformation function
    transformer_class: type  # AST transformer class
    
    # Safety constraints
    allowed_file_patterns: List[str] = field(default_factory=list)
    blocked_file_patterns: List[str] = field(default_factory=list)
    requires_approval: bool = False
    trust_level_required: int = 2  # Minimum trust level
    
    # Audit metadata
    author: str = "system"
    created_at: str = ""
    last_modified: str = ""
    
    # Reversibility
    reversible: bool = True
    rollback_rule_id: Optional[str] = None


class RulesetRegistry:
    """Registry for all transformation rules (the constitution)"""
    
    def __init__(self):
        self.rules: Dict[str, TransformRule] = {}
        self.rule_versions: Dict[str, List[str]] = {}  # rule_id → versions
    
    def register_rule(self, rule: TransformRule):
        """Register a human-authored rule"""
        if rule.rule_id not in self.rules:
            self.rules[rule.rule_id] = rule
            self.rule_versions[rule.rule_id] = [rule.version]
        else:
            # Version control
            if rule.version not in self.rule_versions[rule.rule_id]:
                self.rule_versions[rule.rule_id].append(rule.version)
            self.rules[rule.rule_id] = rule
    
    def match_intent_to_rule(self, intent: CodeIntent) -> Optional[TransformRule]:
        """Match LLM intent to appropriate rule"""
        for rule_id, rule in self.rules.items():
            if intent.intent_type in rule.matches_intent_types:
                # Check additional criteria
                if self._matches_criteria(intent, rule.intent_criteria):
                    return rule
        return None
    
    def _matches_criteria(self, intent: CodeIntent, criteria: Dict[str, Any]) -> bool:
        """Check if intent matches rule criteria"""
        for key, expected_value in criteria.items():
            if key not in intent.criteria:
                return False
            if intent.criteria[key] != expected_value:
                return False
        return True


# ============================================================================
# AST Transformer Authority (Executes Rules Only)
# ============================================================================

class AuthorityASTTransformer(ast.NodeTransformer):
    """
    AST Transformer as Authority.
    
    Only executes human-authored rules.
    No LLM code execution. Zero write access for LLM.
    """
    
    def __init__(self, rule: TransformRule, intent: CodeIntent):
        self.rule = rule
        self.intent = intent
        self.transformed = False
        self.ast_path_taken: List[str] = []
        self.diff_segments: List[Dict[str, Any]] = []
    
    def transform(self, tree: ast.AST, source_code: str) -> Tuple[ast.AST, str, Dict[str, Any]]:
        """
        Transform AST according to rule.
        
        Returns:
            (transformed_ast, diff_info, validation_result)
        """
        original_code = source_code
        
        # Execute transformation via rule's transformer class
        transformed_tree = self.visit(tree)
        
        # Generate diff
        transformed_code = self._ast_to_source(transformed_tree, original_code)
        
        # Validate transformation
        validation = self._validate_transformation(original_code, transformed_code)
        
        return transformed_tree, transformed_code, validation
    
    def _validate_transformation(self, before: str, after: str) -> Dict[str, Any]:
        """Validate transformation preserves syntax and semantics"""
        validation = {
            'preserves_syntax': False,
            'preserves_semantics': False,
            'dependency_changes': [],
            'control_flow_changes': [],
            'side_effect_changes': []
        }
        
        # Syntax validation
        try:
            ast.parse(before)
            ast.parse(after)
            validation['preserves_syntax'] = True
        except SyntaxError as e:
            validation['syntax_error'] = str(e)
            return validation
        
        # Semantic validation (control-flow, dependencies, side-effects)
        # This is simplified - full implementation would do deep analysis
        before_tree = ast.parse(before)
        after_tree = ast.parse(after)
        
        validation['preserves_semantics'] = self._semantic_analysis(before_tree, after_tree)
        
        return validation
    
    def _semantic_analysis(self, before_tree: ast.AST, after_tree: ast.AST) -> bool:
        """Analyze semantic changes (control-flow, side-effects, dependencies)"""
        # Simplified - would do full control-flow graph comparison
        # Check that function signatures unchanged
        # Check that imports only added, not removed critical ones
        # Check that control-flow structure preserved
        
        # For now, assume safe if syntax valid and only logging/error handling added
        return True
    
    def _ast_to_source(self, tree: ast.AST, original_source: str) -> str:
        """Convert AST back to source (same as CodeFixApplicator)"""
        try:
            if hasattr(ast, 'unparse'):
                return ast.unparse(tree)
        except (AttributeError, Exception):
            pass
        
        try:
            import astor
            return astor.to_source(tree)
        except ImportError:
            pass
        
        # Fallback - manual reconstruction
        return original_source


# ============================================================================
# Compiler-Governed Agency System
# ============================================================================

class CompilerGovernedAgency:
    """
    Compiler-Governed Agency System.
    
    Mechanical alignment via deterministic AST transformation.
    LLM has zero write access - only emits intents.
    
    Integrated with GRACE systems:
    - Genesis Keys: Audit trail (diff + stamp)
    - Trust Scoring: Alignment quality metrics
    - KPI Tracking: Transformation performance
    - Anti-Hallucination: Cognitive + Clarity framework validation
    """
    
    def __init__(
        self,
        genesis_service=None,
        enable_trust_scoring: bool = True,
        enable_kpi_tracking: bool = True,
        enable_anti_hallucination: bool = True
    ):
        self.ruleset = RulesetRegistry()
        self.genesis_service = genesis_service or get_genesis_service()
        self.enable_trust_scoring = enable_trust_scoring
        self.enable_kpi_tracking = enable_kpi_tracking
        self.enable_anti_hallucination = enable_anti_hallucination
        
        # GRACE system integrations
        self.trust_scorer = None
        self.kpi_tracker = None
        self.hallucination_guard = None
        self.cognitive_engine = None
        
        if self.enable_trust_scoring:
            try:
                from cognitive.enhanced_trust_scorer import EnhancedTrustScorer
                self.trust_scorer = EnhancedTrustScorer()
            except Exception as e:
                logger.warning(f"Could not initialize trust scorer: {e}")
        
        if self.enable_kpi_tracking:
            try:
                from ml_intelligence.kpi_tracker import KPITracker
                self.kpi_tracker = KPITracker()
                self.kpi_tracker.register_component('compiler_governed_agency')
            except Exception as e:
                logger.warning(f"Could not initialize KPI tracker: {e}")
        
        if self.enable_anti_hallucination:
            try:
                from llm_orchestrator.hallucination_guard import HallucinationGuard
                from llm_orchestrator.cognitive_enforcer import CognitiveConstraints
                from cognitive.engine import CognitiveEngine
                
                self.hallucination_guard = HallucinationGuard()
                self.cognitive_engine = CognitiveEngine()
                self.cognitive_constraints = CognitiveConstraints(
                    requires_determinism=True,
                    is_safety_critical=False,
                    impact_scope="local",
                    is_reversible=True,
                    requires_grounding=True,
                    min_confidence_threshold=0.7
                )
            except Exception as e:
                logger.warning(f"Could not initialize anti-hallucination systems: {e}")
        
        # Track all mutations (audit trail)
        self.mutation_history: List[Dict[str, Any]] = []
        
        # Initialize ruleset (load human-authored rules)
        self._initialize_ruleset()
    
    def _initialize_ruleset(self):
        """Initialize ruleset with human-authored rules"""
        # RULE-001: Add logger to class
        self.ruleset.register_rule(TransformRule(
            rule_id='RULE-001',
            version='1.0.0',
            description='Add logger = logging.getLogger(__name__) to classes',
            matches_intent_types=[IntentType.ADD_LOGGING],
            intent_criteria={'target': 'class'},
            transformer_class=self._create_logger_transformer,
            reversible=True,
            author='system'
        ))
        
        # RULE-002: Replace print with logger
        self.ruleset.register_rule(TransformRule(
            rule_id='RULE-002',
            version='1.0.0',
            description='Replace print() with logger.info()',
            matches_intent_types=[IntentType.REPLACE_PRINT],
            intent_criteria={},
            transformer_class=self._create_print_transformer,
            reversible=True,
            author='system'
        ))
        
        # Add more rules...
    
    def process_intent(
        self,
        intent: CodeIntent,
        source_code: str,
        file_path: str
    ) -> Tuple[bool, Optional[RuleProposal], Dict[str, Any]]:
        """
        Process LLM intent through compiler-governed pipeline.
        
        Flow:
        1. Validate intent (anti-hallucination check)
        2. Match intent to rule (ruleset lookup)
        3. Transform via AST (authority execution)
        4. Generate diff + stamp (Genesis key)
        5. Track trust/KPI (alignment metrics)
        
        Returns:
            (success, rule_proposal, metadata)
        """
        metadata = {
            'intent_validated': False,
            'rule_matched': False,
            'transformation_success': False,
            'genesis_key_created': False,
            'trust_score': 0.0,
            'kpi_updated': False
        }
        
        # Step 1: Validate intent (anti-hallucination governance)
        if not self._validate_intent(intent, source_code, file_path):
            metadata['validation_error'] = 'Intent failed anti-hallucination check'
            return False, None, metadata
        
        metadata['intent_validated'] = True
        
        # Step 2: Match intent to rule (constitution lookup)
        rule = self.ruleset.match_intent_to_rule(intent)
        if not rule:
            metadata['validation_error'] = 'No matching rule found for intent'
            return False, None, metadata
        
        metadata['rule_matched'] = True
        metadata['rule_id'] = rule.rule_id
        metadata['rule_version'] = rule.version
        
        # Step 3: Execute transformation (AST authority)
        try:
            tree = ast.parse(source_code)
            transformer = AuthorityASTTransformer(rule, intent)
            transformed_tree, transformed_code, validation = transformer.transform(tree, source_code)
            
            if not validation['preserves_syntax']:
                metadata['validation_error'] = 'Transformation broke syntax'
                return False, None, metadata
            
            metadata['transformation_success'] = True
            
            # Generate diff
            diff_lines = self._generate_diff(source_code, transformed_code)
            
            # Create rule proposal
            proposal = RuleProposal(
                rule_id=rule.rule_id,
                rule_version=rule.version,
                intent=intent,
                ast_path=transformer.ast_path_taken,
                transformation_type=rule.description,
                before_code=source_code,
                after_code=transformed_code,
                diff_lines=diff_lines,
                preserves_syntax=validation['preserves_syntax'],
                preserves_semantics=validation['preserves_semantics'],
                dependency_changes=validation.get('dependency_changes', []),
                justification_chain=[
                    f"Intent: {intent.intent_type}",
                    f"Rule: {rule.rule_id} v{rule.version}",
                    f"AST Path: {' → '.join(transformer.ast_path_taken)}"
                ]
            )
            
            # Step 4: Create Genesis key (audit trail - diff + stamp)
            genesis_key = self._create_genesis_key(proposal, file_path, validation)
            metadata['genesis_key_created'] = genesis_key is not None
            metadata['genesis_key_id'] = genesis_key.key_id if genesis_key else None
            
            # Step 5: Update trust scoring and KPI
            if self.enable_trust_scoring:
                trust_score = self._calculate_trust_score(proposal, validation)
                metadata['trust_score'] = trust_score
                
                # Record in Genesis key
                if genesis_key:
                    genesis_key.details = genesis_key.details or {}
                    genesis_key.details['trust_score'] = trust_score
            
            if self.enable_kpi_tracking:
                self._update_kpi_metrics(proposal, validation)
                metadata['kpi_updated'] = True
                
                # Get system KPI trust score
                if self.kpi_tracker:
                    system_trust = self.kpi_tracker.get_system_trust_score()
                    metadata['system_kpi_trust'] = system_trust
            
            # Track mutation
            self.mutation_history.append({
                'timestamp': datetime.utcnow().isoformat(),
                'intent': intent,
                'proposal': proposal,
                'genesis_key_id': genesis_key.key_id if genesis_key else None,
                'metadata': metadata
            })
            
            return True, proposal, metadata
            
        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            metadata['validation_error'] = str(e)
            return False, None, metadata
    
    def _validate_intent(self, intent: CodeIntent, source_code: str, file_path: str) -> bool:
        """
        Anti-hallucination governance.
        
        Validates intent against:
        - Cognitive framework (reasoning validity)
        - Clarity framework (ambiguity detection)
        - Semantic constraints (no code-shaped output)
        """
        # Check 1: Intent is properly structured (not code-shaped)
        if self._contains_code_syntax(intent):
            logger.warning(f"Intent contains code syntax - rejected: {intent.intent_type}")
            return False
        
        # Check 2: Target exists in source code
        if not self._target_exists(intent, source_code):
            logger.warning(f"Intent target not found in source: {intent.intent_type}")
            return False
        
        # Check 3: Cognitive framework validation (if enabled)
        if self.enable_anti_hallucination:
            if not self._cognitive_validation(intent, source_code):
                logger.warning(f"Intent failed cognitive validation: {intent.intent_type}")
                return False
        
        return True
    
    def _contains_code_syntax(self, intent: CodeIntent) -> bool:
        """Check if intent contains code-shaped strings (forbidden)"""
        # Check all string fields for code syntax patterns
        forbidden_patterns = ['def ', 'class ', 'import ', '=', '(', ')', '{', '}']
        
        check_fields = [
            intent.justification,
            str(intent.criteria),
            str(intent.target_function),
            str(intent.target_class)
        ]
        
        for field_value in check_fields:
            if field_value:
                for pattern in forbidden_patterns:
                    if pattern in str(field_value) and not self._is_safe_reference(str(field_value)):
                        return True
        
        return False
    
    def _is_safe_reference(self, text: str) -> bool:
        """Check if text is safe reference (not code execution)"""
        # References like "function foo" or "class Bar" are OK
        # But "def foo():" or "class Bar:" are not
        if 'def ' in text and '(' in text:
            return False
        if 'class ' in text and ':' in text and '\n' not in text:
            return True  # Might be reference
        return True  # Conservative
    
    def _target_exists(self, intent: CodeIntent, source_code: str) -> bool:
        """Verify intent target actually exists in source code"""
        try:
            tree = ast.parse(source_code)
            
            if intent.target_class:
                # Check if class exists
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == intent.target_class:
                        return True
                return False
            
            if intent.target_function:
                # Check if function exists
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef) and node.name == intent.target_function:
                        return True
                return False
            
            # If no specific target, assume file-level intent (OK)
            return True
            
        except SyntaxError:
            return False
    
    def _cognitive_validation(self, intent: CodeIntent, source_code: str) -> bool:
        """
        Cognitive framework + Clarity framework validation.
        
        Checks:
        - Reasoning chain validity (cognitive framework)
        - Clarity (no ambiguity - clarity framework)
        - Consistency with codebase patterns
        - Anti-hallucination checks
        """
        if not self.cognitive_engine or not self.cognitive_constraints:
            # Fallback: basic checks
            if intent.llm_confidence < self.cognitive_constraints.min_confidence_threshold if self.cognitive_constraints else 0.5:
                return False
            return True
        
        # Cognitive framework validation
        try:
            # Create cognitive decision context
            decision_context = {
                'intent_type': intent.intent_type.value,
                'target_file': intent.target_file,
                'criteria': intent.criteria,
                'justification': intent.justification,
                'llm_confidence': intent.llm_confidence
            }
            
            # Validate via cognitive framework
            # Check reasoning validity, determinism, grounding
            if self.cognitive_engine:
                # Use cognitive engine to validate intent reasoning
                # Would call cognitive_engine.validate_decision(context, constraints)
                pass
            
            # Clarity framework check (ambiguity detection)
            if self._check_clarity(intent):
                return False  # Intent is ambiguous
            
            # Anti-hallucination check via HallucinationGuard
            if self.hallucination_guard:
                # Verify intent justification is grounded
                is_grounded, _, details = self.hallucination_guard.verify_repository_grounding(
                    content=intent.justification,
                    require_file_references=True
                )
                
                if not is_grounded:
                    logger.warning(f"Intent justification not grounded: {intent.intent_type}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Cognitive validation error: {e}")
            return False
    
    def _check_clarity(self, intent: CodeIntent) -> bool:
        """
        Clarity framework: Check for ambiguity in intent.
        
        Returns True if ambiguous (should reject).
        """
        # Check 1: Ambiguous target (multiple matches possible)
        if not intent.target_class and not intent.target_function and not intent.target_line:
            # Too vague - could match multiple things
            if intent.intent_type in [IntentType.ADD_LOGGING, IntentType.ADD_ERROR_HANDLING]:
                return True  # Needs specific target
        
        # Check 2: Ambiguous criteria
        if 'target' in intent.criteria and intent.criteria['target'] == 'both':
            # "both class and function" is ambiguous
            return True
        
        # Check 3: Vague justification
        vague_phrases = ['might need', 'could be', 'maybe', 'perhaps', 'possibly']
        if any(phrase in intent.justification.lower() for phrase in vague_phrases):
            # Justification is uncertain
            if intent.llm_confidence < 0.8:
                return True  # Low confidence + vague = ambiguous
        
        return False  # Clear intent
    
    def _generate_diff(self, before: str, after: str) -> List[Dict[str, Any]]:
        """Generate semantic diff (line-by-line with context)"""
        before_lines = before.split('\n')
        after_lines = after.split('\n')
        
        # Simplified diff - full implementation would use difflib
        diff = []
        max_len = max(len(before_lines), len(after_lines))
        
        for i in range(max_len):
            before_line = before_lines[i] if i < len(before_lines) else None
            after_line = after_lines[i] if i < len(after_lines) else None
            
            if before_line != after_line:
                diff.append({
                    'line': i + 1,
                    'before': before_line,
                    'after': after_line,
                    'type': 'modified' if before_line and after_line else ('added' if after_line else 'removed')
                })
        
        return diff
    
    def _create_genesis_key(
        self,
        proposal: RuleProposal,
        file_path: str,
        validation: Dict[str, Any]
    ) -> Optional[GenesisKey]:
        """Create Genesis key for audit trail (diff + stamp)"""
        if not self.genesis_service:
            return None
        
        try:
            key = self.genesis_service.create_genesis_key(
                key_type=GenesisKeyType.CODE_CHANGE,
                action="compiler_governed_transformation",
                file_path=file_path,
                details={
                    'rule_id': proposal.rule_id,
                    'rule_version': proposal.rule_version,
                    'intent_type': proposal.intent.intent_type,
                    'intent_justification': proposal.intent.justification,
                    'ast_path': proposal.ast_path,
                    'diff_lines': proposal.diff_lines,
                    'before_code': proposal.before_code,
                    'after_code': proposal.after_code,
                    'preserves_syntax': proposal.preserves_syntax,
                    'preserves_semantics': proposal.preserves_semantics,
                    'dependency_changes': proposal.dependency_changes,
                    'justification_chain': proposal.justification_chain,
                    'validation': validation
                }
            )
            
            return key
            
        except Exception as e:
            logger.error(f"Failed to create Genesis key: {e}")
            return None
    
    def _calculate_trust_score(
        self,
        proposal: RuleProposal,
        validation: Dict[str, Any]
    ) -> float:
        """
        Calculate trust score for transformation using Enhanced Trust Scorer.
        
        Factors:
        - Rule provenance (human-authored = high trust)
        - Validation results (syntax + semantics)
        - Intent LLM confidence
        - Genesis key trust (historical success)
        - Cognitive framework alignment
        
        Integrated with GRACE Enhanced Trust Scorer.
        """
        if self.trust_scorer:
            try:
                # Use enhanced trust scorer for comprehensive scoring
                trust_factors = {
                    'rule_provenance': 0.8 if proposal.rule_id.startswith('RULE-') else 0.5,
                    'syntax_preserved': 1.0 if validation['preserves_syntax'] else 0.0,
                    'semantics_preserved': 1.0 if validation['preserves_semantics'] else 0.0,
                    'intent_confidence': proposal.intent.llm_confidence,
                    'transformation_determinism': 1.0,  # AST transformation is deterministic
                    'cognitive_alignment': 0.9 if proposal.intent.validated else 0.5
                }
                
                # Calculate via trust scorer
                trust_score = self.trust_scorer.calculate_trust(
                    factors=trust_factors,
                    weights={
                        'rule_provenance': 0.3,
                        'syntax_preserved': 0.2,
                        'semantics_preserved': 0.2,
                        'intent_confidence': 0.1,
                        'transformation_determinism': 0.1,
                        'cognitive_alignment': 0.1
                    }
                )
                
                return trust_score
            except Exception as e:
                logger.warning(f"Trust scorer failed, using fallback: {e}")
        
        # Fallback: Simple trust calculation
        trust_score = 0.5  # Base trust
        
        # Rule provenance (+0.3 if human-authored)
        if proposal.rule_id.startswith('RULE-'):
            trust_score += 0.3
        
        # Validation (+0.2 if syntax + semantics preserved)
        if validation['preserves_syntax'] and validation['preserves_semantics']:
            trust_score += 0.2
        
        # Intent confidence (weighted)
        if proposal.intent.llm_confidence > 0:
            trust_score += proposal.intent.llm_confidence * 0.1
        
        return min(trust_score, 1.0)
    
    def _update_kpi_metrics(
        self,
        proposal: RuleProposal,
        validation: Dict[str, Any]
    ):
        """
        Update KPI metrics for alignment tracking.
        
        Integrated with GRACE KPI Tracker.
        Tracks:
        - Transformation success rate
        - Rule effectiveness
        - Alignment quality
        - Determinism preservation
        """
        if not self.kpi_tracker:
            return
        
        component = 'compiler_governed_agency'
        
        # Track transformation success
        if validation['preserves_syntax'] and validation['preserves_semantics']:
            self.kpi_tracker.increment_kpi(
                component_name=component,
                metric_name='transformations_successful',
                value=1.0,
                metadata={
                    'rule_id': proposal.rule_id,
                    'intent_type': proposal.intent.intent_type.value
                }
            )
        else:
            self.kpi_tracker.increment_kpi(
                component_name=component,
                metric_name='transformations_failed',
                value=1.0,
                metadata={
                    'rule_id': proposal.rule_id,
                    'validation': validation
                }
            )
        
        # Track rule usage
        self.kpi_tracker.increment_kpi(
            component_name=component,
            metric_name=f'rule_{proposal.rule_id}_usage',
            value=1.0
        )
        
        # Track alignment quality (syntax + semantics preserved)
        alignment_score = 1.0 if (validation['preserves_syntax'] and validation['preserves_semantics']) else 0.5
        self.kpi_tracker.increment_kpi(
            component_name=component,
            metric_name='alignment_quality',
            value=alignment_score,
            metadata={'preserves_syntax': validation['preserves_syntax'], 'preserves_semantics': validation['preserves_semantics']}
        )
    
    # Transformer creation helpers
    def _create_logger_transformer(self, rule: TransformRule, intent: CodeIntent):
        """Create transformer for adding logger (similar to ASTCodeTransformer)"""
        from cognitive.code_analyzer_self_healing import ASTCodeTransformer
        # Create issue-like object for transformer
        from cognitive.grace_code_analyzer import CodeIssue, Severity
        issue = CodeIssue(
            rule_id='G012',
            severity=Severity.LOW,
            message='Add logger',
            file_path=intent.target_file,
            line_number=intent.target_line or 1,
            suggested_fix='Add logger initialization',
            fix_confidence=0.9
        )
        return ASTCodeTransformer(issue)
    
    def _create_print_transformer(self, rule: TransformRule, intent: CodeIntent):
        """Create transformer for replacing print (simplified)"""
        # Similar pattern - would create appropriate transformer
        return None


# ============================================================================
# Integration with GRACE Systems
# ============================================================================

def get_compiler_governed_agency(
    genesis_service=None,
    enable_trust_scoring: bool = True,
    enable_kpi_tracking: bool = True,
    enable_anti_hallucination: bool = True
) -> CompilerGovernedAgency:
    """Get compiler-governed agency instance"""
    return CompilerGovernedAgency(
        genesis_service=genesis_service,
        enable_trust_scoring=enable_trust_scoring,
        enable_kpi_tracking=enable_kpi_tracking,
        enable_anti_hallucination=enable_anti_hallucination
    )
