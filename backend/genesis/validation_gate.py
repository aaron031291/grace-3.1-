import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, UTC
from enum import Enum
from models.genesis_key_models import GenesisKey, GenesisKeyType

# Module-level logger
logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Raised when Genesis key validation fails."""
    pass


class AuthorityScope(str, Enum):
    """Authority scopes for Genesis mutations."""
    ROOT = "ROOT"  # Root authority - highest level
    QUORUM = "QUORUM"  # Requires quorum approval
    USER = "USER"  # User-initiated change
    SYSTEM = "SYSTEM"  # System-initiated change
    AUTONOMOUS = "AUTONOMOUS"  # Autonomous agent change
    SANDBOX = "SANDBOX"  # Sandbox/test environment


class DeltaType(str, Enum):
    """Types of Genesis state changes."""
    AUTHORITY_EXPANSION = "AUTHORITY_EXPANSION"
    AUTHORITY_RESTRICTION = "AUTHORITY_RESTRICTION"
    CONSTRAINT_ADD = "CONSTRAINT_ADD"
    CONSTRAINT_REMOVE = "CONSTRAINT_REMOVE"
    CAPABILITY_GRANT = "CAPABILITY_GRANT"
    CAPABILITY_REVOKE = "CAPABILITY_REVOKE"
    VALUE_UPDATE = "VALUE_UPDATE"
    STRUCTURE_CHANGE = "STRUCTURE_CHANGE"


class GenesisValidationGate:
    """
    Hard stop validation gate for Genesis keys.
    
    Every Genesis mutation must pass ALL validation checks:
    1. Schema validation
    2. Intent verification
    3. Authority validation
    4. Invariant preservation
    5. Propagation rule validation
    """
    
    def __init__(self):
        self.invariants: List[callable] = []
        self._register_default_invariants()
    
    def _register_default_invariants(self):
        """Register default system invariants."""
        # Invariant: ROOT authority cannot be granted by non-ROOT
        self.invariants.append(self._check_root_authority_invariant)
        
        # Invariant: Propagation depth must be non-negative
        self.invariants.append(self._check_propagation_depth_invariant)
        
        # Invariant: Forbidden actions cannot be in allowed list
        self.invariants.append(self._check_action_class_conflict_invariant)
    
    def validate_genesis_key(
        self,
        key: GenesisKey,
        is_mutation: bool = False,
        previous_version: Optional[GenesisKey] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate a Genesis key before persistence.
        
        Args:
            key: Genesis key to validate
            is_mutation: Whether this is a mutation (change to existing key)
            previous_version: Previous version if this is a mutation
            
        Returns:
            Tuple of (is_valid, list_of_errors)
            
        Raises:
            ValidationError: If validation fails (hard stop)
        """
        errors = []
        
        # 1. Schema Validation
        schema_errors = self._validate_schema(key)
        errors.extend(schema_errors)
        
        # 2. Intent Verification (REQUIRED for mutations)
        if is_mutation:
            intent_errors = self._validate_intent(key, previous_version)
            errors.extend(intent_errors)
        
        # 3. Authority Validation
        authority_errors = self._validate_authority(key)
        errors.extend(authority_errors)
        
        # 4. Invariant Preservation
        invariant_errors = self._validate_invariants(key, previous_version)
        errors.extend(invariant_errors)
        
        # 5. Propagation Rule Validation
        propagation_errors = self._validate_propagation_rules(key)
        errors.extend(propagation_errors)
        
        # Hard stop: If any errors, reject
        if errors:
            error_msg = f"Genesis validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(f"[VALIDATION-GATE] {error_msg}")
            raise ValidationError(error_msg)
        
        logger.info(f"[VALIDATION-GATE] Genesis key {key.key_id} passed all validation checks")
        return True, []
    
    def _validate_schema(self, key: GenesisKey) -> List[str]:
        """Validate basic schema requirements."""
        errors = []
        
        # Required fields
        if not key.key_id:
            errors.append("key_id is required")
        if not key.what_description:
            errors.append("what_description is required")
        if not key.who_actor:
            errors.append("who_actor is required")
        if not key.when_timestamp:
            errors.append("when_timestamp is required")
        
        # Intent verification fields (REQUIRED for mutations)
        # Note: For new keys, these may be optional, but mutations MUST have them
        if key.change_origin is None:
            logger.warning(f"[VALIDATION-GATE] change_origin missing for key {key.key_id}")
        
        return errors
    
    def _validate_intent(
        self,
        key: GenesisKey,
        previous_version: Optional[GenesisKey]
    ) -> List[str]:
        """
        Validate intent - WHY this change exists.
        
        Required fields:
        - change_origin: Why this change exists
        - authority_scope: What authority allowed it
        - allowed_action_classes: Which actions are allowed
        - forbidden_action_classes: Which actions are forbidden
        - propagation_depth: How deep can this propagate
        """
        errors = []
        
        # For mutations, intent verification is MANDATORY
        if not key.change_origin:
            errors.append("change_origin is REQUIRED for Genesis mutations (why this change exists)")
        
        if not key.authority_scope:
            errors.append("authority_scope is REQUIRED for Genesis mutations (what authority allowed it)")
        
        if key.allowed_action_classes is None:
            errors.append("allowed_action_classes is REQUIRED for Genesis mutations (which actions are allowed)")
        
        if key.forbidden_action_classes is None:
            # Empty list is acceptable, but None is not
            key.forbidden_action_classes = []
        
        if key.propagation_depth is None:
            errors.append("propagation_depth is REQUIRED for Genesis mutations (how deep can this propagate)")
        
        # Validate change_origin makes sense
        if key.change_origin:
            valid_origins = ["user", "system", "autonomous", "sandbox", "governance", "pipeline", "external"]
            if key.change_origin.lower() not in valid_origins:
                errors.append(f"change_origin '{key.change_origin}' is not a valid origin (must be one of: {valid_origins})")
        
        # Validate authority_scope
        if key.authority_scope:
            try:
                AuthorityScope(key.authority_scope)
            except ValueError:
                errors.append(f"authority_scope '{key.authority_scope}' is not valid (must be one of: {[e.value for e in AuthorityScope]})")
        
        # Validate action classes are lists
        if key.allowed_action_classes is not None and not isinstance(key.allowed_action_classes, list):
            errors.append("allowed_action_classes must be a list")
        
        if key.forbidden_action_classes is not None and not isinstance(key.forbidden_action_classes, list):
            errors.append("forbidden_action_classes must be a list")
        
        # Validate no overlap between allowed and forbidden
        if key.allowed_action_classes and key.forbidden_action_classes:
            overlap = set(key.allowed_action_classes) & set(key.forbidden_action_classes)
            if overlap:
                errors.append(f"Action classes cannot be both allowed and forbidden: {overlap}")
        
        return errors
    
    def _validate_authority(self, key: GenesisKey) -> List[str]:
        """Validate authority scope and permissions."""
        errors = []
        
        if not key.authority_scope:
            return errors  # Already caught in intent validation
        
        # ROOT authority can only be granted by ROOT
        if key.authority_scope == AuthorityScope.ROOT.value:
            # Check if this is attempting to grant ROOT authority
            if key.granted_capabilities:
                # This would need to check previous version or context
                # For now, log a warning
                logger.warning(f"[VALIDATION-GATE] ROOT authority scope detected for key {key.key_id}")
        
        # AUTONOMOUS changes require higher trust scores
        if key.authority_scope == AuthorityScope.AUTONOMOUS.value:
            if key.trust_score is None or key.trust_score < 0.75:
                errors.append("AUTONOMOUS authority requires trust_score >= 0.75")
        
        return errors
    
    def _validate_invariants(
        self,
        key: GenesisKey,
        previous_version: Optional[GenesisKey]
    ) -> List[str]:
        """Validate that system invariants are preserved."""
        errors = []
        
        for invariant_check in self.invariants:
            try:
                invariant_errors = invariant_check(key, previous_version)
                errors.extend(invariant_errors)
            except Exception as e:
                logger.error(f"[VALIDATION-GATE] Invariant check failed: {e}")
                errors.append(f"Invariant check error: {str(e)}")
        
        return errors
    
    def _validate_propagation_rules(self, key: GenesisKey) -> List[str]:
        """Validate propagation depth and rules."""
        errors = []
        
        if key.propagation_depth is None:
            return errors  # Already caught in intent validation
        
        # Propagation depth must be non-negative
        if key.propagation_depth < 0:
            errors.append("propagation_depth must be >= 0")
        
        # High propagation depth requires higher authority
        if key.propagation_depth > 3:
            if key.authority_scope not in [AuthorityScope.ROOT.value, AuthorityScope.QUORUM.value]:
                errors.append(f"propagation_depth > 3 requires ROOT or QUORUM authority (current: {key.authority_scope})")
        
        return errors
    
    # ============================================================
    # Invariant Checkers
    # ============================================================
    
    def _check_root_authority_invariant(
        self,
        key: GenesisKey,
        previous_version: Optional[GenesisKey]
    ) -> List[str]:
        """Invariant: ROOT authority cannot be granted by non-ROOT."""
        errors = []
        
        if key.authority_scope == AuthorityScope.ROOT.value:
            # If granting ROOT capabilities, must be from ROOT
            if key.granted_capabilities and "ROOT" in str(key.granted_capabilities):
                if previous_version and previous_version.authority_scope != AuthorityScope.ROOT.value:
                    errors.append("ROOT authority can only be granted by ROOT authority")
        
        return errors
    
    def _check_propagation_depth_invariant(
        self,
        key: GenesisKey,
        previous_version: Optional[GenesisKey]
    ) -> List[str]:
        """Invariant: Propagation depth must be non-negative."""
        errors = []
        
        if key.propagation_depth is not None and key.propagation_depth < 0:
            errors.append("propagation_depth must be non-negative")
        
        return errors
    
    def _check_action_class_conflict_invariant(
        self,
        key: GenesisKey,
        previous_version: Optional[GenesisKey]
    ) -> List[str]:
        """Invariant: Forbidden actions cannot be in allowed list."""
        errors = []
        
        if key.allowed_action_classes and key.forbidden_action_classes:
            overlap = set(key.allowed_action_classes) & set(key.forbidden_action_classes)
            if overlap:
                errors.append(f"Action classes cannot be both allowed and forbidden: {overlap}")
        
        return errors
    
    def register_invariant(self, invariant_check: callable):
        """Register a custom invariant checker."""
        self.invariants.append(invariant_check)
        logger.info(f"[VALIDATION-GATE] Registered custom invariant: {invariant_check.__name__}")


# Global validation gate instance
_validation_gate: Optional[GenesisValidationGate] = None


def get_validation_gate() -> GenesisValidationGate:
    """Get the global validation gate instance."""
    global _validation_gate
    if _validation_gate is None:
        _validation_gate = GenesisValidationGate()
    return _validation_gate


def validate_genesis_key(
    key: GenesisKey,
    is_mutation: bool = False,
    previous_version: Optional[GenesisKey] = None
) -> bool:
    """
    Validate a Genesis key (convenience function).
    
    Raises ValidationError if validation fails.
    """
    gate = get_validation_gate()
    is_valid, errors = gate.validate_genesis_key(key, is_mutation, previous_version)
    return is_valid
