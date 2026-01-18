import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from cognitive.transformation_library.rule_dsl import Rule, load_rule
from cognitive.transformation_library.ast_matcher import ASTMatcher
from cognitive.transformation_library.rewrite_engine import RewriteEngine
from cognitive.transformation_library.constraint_validator import ConstraintValidator
from cognitive.transformation_library.proof_system import ProofSystem
from cognitive.transformation_library.outcome_ledger import OutcomeLedger
logger = logging.getLogger(__name__)

class TransformationExecutor:
    """
    Main orchestrator for code transformations.
    
    Coordinates:
    - AST pattern matching
    - Code rewriting
    - Constraint validation
    - Proof verification
    - Outcome logging
    """

    def __init__(
        self,
        session,
        magma_memory=None,
        outcome_ledger: Optional[OutcomeLedger] = None
    ):
        """
        Initialize Transformation Executor.
        
        Args:
            session: Database session
            magma_memory: Magma memory system (optional)
            outcome_ledger: Outcome ledger (optional, created if not provided)
        """
        self.session = session
        self.magma_memory = magma_memory
        
        # Components
        self.ast_matcher = ASTMatcher()
        self.rewrite_engine = RewriteEngine()
        self.constraint_validator = ConstraintValidator()
        self.proof_system = ProofSystem()
        
        # Outcome ledger
        if outcome_ledger is None:
            self.outcome_ledger = OutcomeLedger(session, magma_memory)
        else:
            self.outcome_ledger = outcome_ledger

    def execute_transform(
        self,
        code: str,
        rule: Rule,
        file_path: Optional[str] = None,
        user_id: Optional[str] = None,
        genesis_key_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a transformation using a rule.
        
        Args:
            code: Source code to transform
            rule: Transformation rule
            file_path: Optional file path for context
            user_id: Optional user ID
            genesis_key_id: Optional Genesis Key ID for tracking
        
        Returns:
            Transformation result with transformed code and metadata
        """
        start_time = datetime.utcnow()
        
        logger.info(f"[TRANSFORM-EXECUTOR] Executing rule: {rule.id} v{rule.version}")
        
        # 1. Match AST patterns
        matches = self.ast_matcher.match_pattern(
            code=code,
            pattern=rule.pattern,
            language=rule.pattern.get("language", "python")
        )
        
        if not matches:
            logger.info(f"[TRANSFORM-EXECUTOR] No matches found for rule {rule.id}")
            return {
                "success": False,
                "error": "no_matches",
                "rule_id": rule.id,
                "rule_version": rule.version,
                "transformed_code": code,
                "matches_found": 0
            }
        
        logger.info(f"[TRANSFORM-EXECUTOR] Found {len(matches)} matches")
        
        # 2. Validate preconditions
        pre_constraints = rule.constraints.get("pre", [])
        if pre_constraints:
            is_valid, errors = self.constraint_validator.validate_preconditions(
                code=code,
                constraints=pre_constraints,
                matches=matches
            )
            
            if not is_valid:
                logger.warning(f"[TRANSFORM-EXECUTOR] Preconditions failed: {errors}")
                return {
                    "success": False,
                    "error": "preconditions_failed",
                    "errors": errors,
                    "rule_id": rule.id,
                    "rule_version": rule.version,
                    "transformed_code": code,
                    "matches_found": len(matches)
                }
        
        # 3. Apply rewrite
        transformed_code = self.rewrite_engine.apply_rewrite(
            code=code,
            matches=matches,
            rewrite=rule.rewrite,
            preserve=rule.rewrite.get("preserve", [])
        )
        
        # 4. Validate postconditions
        post_constraints = rule.constraints.get("post", [])
        if post_constraints:
            is_valid, errors = self.constraint_validator.validate_postconditions(
                before_code=code,
                after_code=transformed_code,
                constraints=post_constraints,
                matches=matches
            )
            
            if not is_valid:
                logger.warning(f"[TRANSFORM-EXECUTOR] Postconditions failed: {errors}")
                # Continue anyway, but log the failure
        
        # 5. Generate and verify proofs
        proof_results = {}
        if rule.proof_required:
            proof_results = self.proof_system.generate_proofs(
                before_code=code,
                after_code=transformed_code,
                required_proofs=rule.proof_required,
                rule=rule,
                matches=matches
            )
            
            all_verified, failed_proofs = self.proof_system.verify_proofs(
                proof_results=proof_results,
                required_proofs=rule.proof_required
            )
            
            if not all_verified:
                logger.warning(f"[TRANSFORM-EXECUTOR] Some proofs failed: {failed_proofs}")
                # Continue anyway, but log the failure
        
        # 6. Compute AST pattern signature
        ast_pattern_signature = self.ast_matcher.compute_pattern_signature(matches)
        
        # 7. Generate diff summary
        diff_summary = self.rewrite_engine.generate_diff_summary(code, transformed_code)
        
        # 8. Log outcome to ledger
        outcome = self.outcome_ledger.log_transformation(
            rule_id=rule.id,
            rule_version=rule.version,
            ast_pattern_signature=ast_pattern_signature,
            before_code=code,
            after_code=transformed_code,
            diff_summary=diff_summary,
            proof_results=proof_results,
            rollback_status="available",
            file_path=file_path,
            user_id=user_id,
            genesis_key_id=genesis_key_id
        )
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        logger.info(
            f"[TRANSFORM-EXECUTOR] Transform complete: {rule.id} "
            f"({len(matches)} matches, {execution_time:.3f}s)"
        )
        
        return {
            "success": True,
            "rule_id": rule.id,
            "rule_version": rule.version,
            "transformed_code": transformed_code,
            "matches_found": len(matches),
            "proof_results": proof_results,
            "diff_summary": diff_summary,
            "outcome_id": outcome.get("id") if outcome else None,
            "execution_time": execution_time,
            "ast_pattern_signature": ast_pattern_signature
        }
