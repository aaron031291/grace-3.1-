import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from sqlalchemy.orm import Session
from transformation_library import get_transformation_library, TransformationLibrary, TransformRule, TransformOutcome, ProofStatus
logger = logging.getLogger(__name__)

class LLMTransformIntegration:
    """
    Integration between LLMs and Transformation Library.
    
    Enables LLMs to:
    1. Use deterministic transforms instead of free-form generation
    2. Apply proof-gated transformations
    3. Learn from outcomes
    4. Use domain-specific rewrite knowledge
    """
    
    def __init__(
        self,
        session: Session,
        knowledge_base_path: Path,
        transform_library: Optional[TransformationLibrary] = None
    ):
        """Initialize LLM-Transform integration."""
        self.session = session
        self.kb_path = knowledge_base_path
        self.transform_library = transform_library or get_transformation_library(
            session, knowledge_base_path
        )
        
        logger.info("[LLM-TRANSFORM] Initialized LLM-Transform integration")
    
    # ==================== DETERMINISTIC CODE GENERATION ====================
    
    def generate_with_transforms(
        self,
        code_intent: str,
        available_rules: Optional[List[TransformRule]] = None,
        use_proofs: bool = True
    ) -> Tuple[str, List[TransformOutcome]]:
        """
        Generate code using deterministic transforms instead of free-form LLM generation.
        
        Process:
        1. Match intent to transform rules
        2. Apply deterministic transforms
        3. Verify with proofs
        4. Return transformed code
        
        This is MORE deterministic than LLM generation.
        """
        # Get available rules
        rules = available_rules or list(self.transform_library.rules.values())
        
        # Match intent to rules
        matched_rules = self._match_intent_to_rules(code_intent, rules)
        
        if not matched_rules:
            logger.warning(f"[LLM-TRANSFORM] No rules matched intent: {code_intent}")
            return "", []
        
        # Apply transforms in sequence
        transformed_code = ""
        outcomes = []
        
        for rule in matched_rules:
            try:
                # Apply transform
                code_after, outcome = self.transform_library.apply_transform(
                    code=transformed_code or code_intent,
                    rule=rule,
                    verify_proofs=use_proofs
                )
                
                transformed_code = code_after
                outcomes.append(outcome)
                
                # If proofs failed, stop
                if use_proofs and not all(
                    p == ProofStatus.PASSED or p == ProofStatus.SKIPPED
                    for p in outcome.proof_results.values()
                ):
                    logger.warning(f"[LLM-TRANSFORM] Proofs failed for rule {rule.rule_name}, stopping")
                    break
                    
            except Exception as e:
                logger.error(f"[LLM-TRANSFORM] Transform error: {e}")
                continue
        
        logger.info(
            f"[LLM-TRANSFORM] Applied {len(outcomes)} transforms, "
            f"proofs passed: {sum(1 for o in outcomes if all(p == ProofStatus.PASSED for p in o.proof_results.values()))}/{len(outcomes)}"
        )
        
        return transformed_code, outcomes
    
    def _match_intent_to_rules(
        self,
        intent: str,
        rules: List[TransformRule]
    ) -> List[TransformRule]:
        """Match code intent to available rules."""
        intent_lower = intent.lower()
        
        matched = []
        
        for rule in rules:
            # Simple keyword matching (can be enhanced with semantic search)
            if any(keyword in intent_lower for keyword in rule.description.lower().split()):
                matched.append(rule)
            elif any(keyword in intent_lower for keyword in rule.rule_name.lower().split("_")):
                matched.append(rule)
        
        # Sort by trust score (highest first)
        matched.sort(key=lambda r: r.trust_score, reverse=True)
        
        return matched[:5]  # Top 5 matches
    
    # ==================== PROOF-GATED TRANSFORMS ====================
    
    def apply_proof_gated_transform(
        self,
        code: str,
        rule: TransformRule,
        require_all_proofs: bool = True
    ) -> Tuple[bool, Optional[str], TransformOutcome]:
        """
        Apply transform only if proofs pass (proof-gated).
        
        Returns:
            (success, transformed_code, outcome)
        """
        # Apply transform
        transformed_code, outcome = self.transform_library.apply_transform(
            code=code,
            rule=rule,
            verify_proofs=True
        )
        
        # Check proofs
        if require_all_proofs:
            all_passed = all(
                p == ProofStatus.PASSED or p == ProofStatus.SKIPPED
                for p in outcome.proof_results.values()
            )
        else:
            # At least one proof passed
            all_passed = any(
                p == ProofStatus.PASSED
                for p in outcome.proof_results.values()
            )
        
        if not all_passed:
            logger.warning(
                f"[LLM-TRANSFORM] Proofs failed for rule {rule.rule_name}: "
                f"{[name for name, status in outcome.proof_results.items() if status != ProofStatus.PASSED]}"
            )
            return False, None, outcome
        
        return True, transformed_code, outcome
    
    # ==================== OUTCOME-BASED LEARNING ====================
    
    def learn_from_outcomes(
        self,
        outcomes: List[TransformOutcome],
        update_rules: bool = True
    ):
        """
        Learn from transform outcomes to improve rules.
        
        Updates:
        - Rule trust scores based on outcomes
        - Rule usage statistics
        - Proposes new rules from patterns
        """
        for outcome in outcomes:
            if outcome.rule_id in self.transform_library.rules:
                rule = self.transform_library.rules[outcome.rule_id]
                
                # Update statistics
                rule.usage_count += 1
                
                # Check if proofs passed
                proofs_passed = all(
                    p == ProofStatus.PASSED or p == ProofStatus.SKIPPED
                    for p in outcome.proof_results.values()
                )
                
                if proofs_passed:
                    rule.success_count += 1
                
                # Update trust score
                rule.trust_score = rule.success_count / rule.usage_count if rule.usage_count > 0 else 0.5
        
        # Mine patterns for new rules
        if update_rules:
            mined_patterns = self.transform_library.mine_patterns()
            
            for pattern in mined_patterns:
                if pattern.proposed_rule and pattern.confidence >= 0.8:
                    # Add proposed rule to library
                    self.transform_library.rules[pattern.proposed_rule.rule_id] = pattern.proposed_rule
                    logger.info(
                        f"[LLM-TRANSFORM] Added mined rule: {pattern.proposed_rule.rule_name} "
                        f"(confidence: {pattern.confidence:.2f})"
                    )
    
    # ==================== DOMAIN-SPECIFIC KNOWLEDGE ====================
    
    def get_domain_rules(
        self,
        domain: str  # "python", "javascript", "code_quality", etc.
    ) -> List[TransformRule]:
        """Get domain-specific transform rules."""
        domain_lower = domain.lower()
        
        domain_rules = []
        
        for rule in self.transform_library.rules.values():
            # Match domain in rule description or name
            if domain_lower in rule.description.lower() or domain_lower in rule.rule_name.lower():
                domain_rules.append(rule)
        
        # Sort by trust score
        domain_rules.sort(key=lambda r: r.trust_score, reverse=True)
        
        return domain_rules
    
    # ==================== LLM ENHANCEMENT ====================
    
    def enhance_llm_generation(
        self,
        llm_output: str,
        use_transforms: bool = True,
        proof_gate: bool = True
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Enhance LLM-generated code with deterministic transforms.
        
        Process:
        1. Take LLM output
        2. Apply relevant transforms
        3. Proof-gate if enabled
        4. Return improved code
        
        This makes LLM output MORE deterministic and reliable.
        """
        metadata = {
            "transforms_applied": 0,
            "proofs_passed": 0,
            "rules_used": []
        }
        
        if not use_transforms:
            return llm_output, metadata
        
        # Get all rules
        rules = list(self.transform_library.rules.values())
        
        # Match to rules
        matched_rules = self._match_intent_to_rules(llm_output, rules)
        
        if not matched_rules:
            return llm_output, metadata
        
        # Apply transforms
        transformed_code = llm_output
        
        for rule in matched_rules[:3]:  # Top 3 rules
            try:
                success, code_after, outcome = self.apply_proof_gated_transform(
                    code=transformed_code,
                    rule=rule,
                    require_all_proofs=proof_gate
                )
                
                if success:
                    transformed_code = code_after
                    metadata["transforms_applied"] += 1
                    metadata["proofs_passed"] += len(
                        [p for p in outcome.proof_results.values() if p == ProofStatus.PASSED]
                    )
                    metadata["rules_used"].append(rule.rule_name)
                    
            except Exception as e:
                logger.warning(f"[LLM-TRANSFORM] Transform application error: {e}")
                continue
        
        logger.info(
            f"[LLM-TRANSFORM] Enhanced LLM output: "
            f"{metadata['transforms_applied']} transforms, "
            f"{metadata['proofs_passed']} proofs passed"
        )
        
        return transformed_code, metadata


def get_llm_transform_integration(
    session: Session,
    knowledge_base_path: Path
) -> LLMTransformIntegration:
    """Factory function to get LLM-Transform integration."""
    return LLMTransformIntegration(session, knowledge_base_path)
