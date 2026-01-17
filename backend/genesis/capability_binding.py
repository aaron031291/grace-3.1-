import logging
from typing import Dict, Any, List, Optional, Set, Callable, Tuple
from datetime import datetime, UTC
from enum import Enum
from dataclasses import dataclass, field
from models.genesis_key_models import GenesisKey
class GenesisCapability(str, Enum):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Genesis capabilities that pipelines can bind to."""
    # Execution capabilities
    EXECUTE_EXTERNAL = "EXECUTE_EXTERNAL"
    EXECUTE_INTERNAL = "EXECUTE_INTERNAL"
    EXECUTE_AUTONOMOUS = "EXECUTE_AUTONOMOUS"
    
    # File operations
    FILE_READ = "FILE_READ"
    FILE_WRITE = "FILE_WRITE"
    FILE_DELETE = "FILE_DELETE"
    
    # Network operations
    NETWORK_OUTBOUND = "NETWORK_OUTBOUND"
    NETWORK_INBOUND = "NETWORK_INBOUND"
    
    # Database operations
    DATABASE_READ = "DATABASE_READ"
    DATABASE_WRITE = "DATABASE_WRITE"
    
    # System operations
    SYSTEM_CONFIG = "SYSTEM_CONFIG"
    SYSTEM_DEPLOY = "SYSTEM_DEPLOY"
    
    # Autonomous operations
    AUTONOMOUS_LEARN = "AUTONOMOUS_LEARN"
    AUTONOMOUS_MODIFY = "AUTONOMOUS_MODIFY"
    AUTONOMOUS_TRIGGER = "AUTONOMOUS_TRIGGER"


class GenesisConstraint(str, Enum):
    """Genesis constraints that pipelines must respect."""
    SANDBOX_ENFORCED = "SANDBOX_ENFORCED"
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL_REQUIRED"
    QUORUM_REQUIRED = "QUORUM_REQUIRED"
    AUDIT_REQUIRED = "AUDIT_REQUIRED"
    ROLLBACK_ENABLED = "ROLLBACK_ENABLED"
    EXTERNAL_EXECUTION = "EXTERNAL_EXECUTION"


@dataclass
class CapabilityRequirement:
    """A capability requirement for a pipeline."""
    capability: GenesisCapability
    required: bool = True
    trust_score_min: Optional[float] = None  # Minimum trust score required
    constraint_tags: List[GenesisConstraint] = field(default_factory=list)


@dataclass
class PipelineCapabilityBinding:
    """Binding between a pipeline and Genesis capabilities."""
    pipeline_id: str
    pipeline_name: str
    required_capabilities: List[CapabilityRequirement]
    last_verified_at: Optional[datetime] = None
    last_verified_version: Optional[int] = None
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    
    def check_eligibility(self, genesis_key: GenesisKey) -> Tuple[bool, List[str]]:
        """
        Check if pipeline is eligible to run based on Genesis capabilities.
        
        Returns:
            Tuple of (is_eligible, list_of_errors)
        """
        errors = []
        
        # Check required capabilities
        granted_capabilities = set(genesis_key.granted_capabilities or [])
        required_capabilities = set(genesis_key.required_capabilities or [])
        
        for req in self.required_capabilities:
            capability_str = req.capability.value
            
            # Check if capability is granted
            if capability_str not in granted_capabilities:
                if req.required:
                    errors.append(f"Required capability {capability_str} not granted")
                else:
                    logger.warning(f"[CAPABILITY] Optional capability {capability_str} not granted")
            
            # Check trust score requirement
            if req.trust_score_min is not None:
                if genesis_key.trust_score is None or genesis_key.trust_score < req.trust_score_min:
                    errors.append(
                        f"Capability {capability_str} requires trust_score >= {req.trust_score_min}, "
                        f"but current is {genesis_key.trust_score}"
                    )
            
            # Check constraint tags
            constraint_tags = set(genesis_key.constraint_tags or [])
            for constraint in req.constraint_tags:
                if constraint.value not in constraint_tags:
                    errors.append(f"Required constraint {constraint.value} not present")
        
        # Check forbidden action classes
        forbidden_actions = set(genesis_key.forbidden_action_classes or [])
        # Pipeline actions should not be in forbidden list
        # This would need pipeline-specific action class mapping
        
        is_eligible = len(errors) == 0
        
        if not is_eligible:
            logger.warning(
                f"[CAPABILITY] Pipeline {self.pipeline_id} not eligible: {errors}"
            )
        
        return is_eligible, errors


class GenesisCapabilityRegistry:
    """
    Registry for pipeline capability bindings.
    
    Tracks which pipelines require which capabilities and
    re-evaluates eligibility when Genesis changes.
    """
    
    def __init__(self):
        self.bindings: Dict[str, PipelineCapabilityBinding] = {}
        self.genesis_version_callbacks: List[Callable] = []
    
    def register_pipeline(
        self,
        pipeline_id: str,
        pipeline_name: str,
        required_capabilities: List[CapabilityRequirement]
    ) -> PipelineCapabilityBinding:
        """Register a pipeline with its capability requirements."""
        binding = PipelineCapabilityBinding(
            pipeline_id=pipeline_id,
            pipeline_name=pipeline_name,
            required_capabilities=required_capabilities
        )
        
        self.bindings[pipeline_id] = binding
        
        logger.info(
            f"[CAPABILITY] Registered pipeline {pipeline_id} with {len(required_capabilities)} capability requirements"
        )
        
        return binding
    
    def check_pipeline_eligibility(
        self,
        pipeline_id: str,
        genesis_key: GenesisKey
    ) -> Tuple[bool, List[str]]:
        """
        Check if a pipeline is eligible to run.
        
        Returns:
            Tuple of (is_eligible, list_of_errors)
        """
        binding = self.bindings.get(pipeline_id)
        
        if not binding:
            logger.warning(f"[CAPABILITY] Pipeline {pipeline_id} not registered")
            return False, [f"Pipeline {pipeline_id} not registered with capability system"]
        
        is_eligible, errors = binding.check_eligibility(genesis_key)
        
        # Update binding status
        binding.is_valid = is_eligible
        binding.validation_errors = errors
        binding.last_verified_at = datetime.now(UTC)
        binding.last_verified_version = genesis_key.genesis_version
        
        return is_eligible, errors
    
    def on_genesis_update(self, genesis_key: GenesisKey):
        """
        Called when Genesis is updated.
        
        Re-evaluates all pipeline bindings and notifies pipelines
        that need to rebind.
        """
        logger.info(
            f"[CAPABILITY] Genesis updated to version {genesis_key.genesis_version}, "
            f"re-evaluating {len(self.bindings)} pipeline bindings"
        )
        
        rebind_required = []
        
        for pipeline_id, binding in self.bindings.items():
            was_valid = binding.is_valid
            is_eligible, errors = binding.check_eligibility(genesis_key)
            
            # If status changed, pipeline needs to rebind
            if was_valid != is_eligible:
                rebind_required.append({
                    "pipeline_id": pipeline_id,
                    "was_valid": was_valid,
                    "is_valid": is_eligible,
                    "errors": errors
                })
                
                logger.warning(
                    f"[CAPABILITY] Pipeline {pipeline_id} eligibility changed: "
                    f"{was_valid} -> {is_eligible}"
                )
        
        # Notify callbacks
        for callback in self.genesis_version_callbacks:
            try:
                callback(genesis_key, rebind_required)
            except Exception as e:
                logger.error(f"[CAPABILITY] Callback error: {e}")
        
        return rebind_required
    
    def register_genesis_update_callback(self, callback: Callable):
        """Register a callback to be called when Genesis updates."""
        self.genesis_version_callbacks.append(callback)
        logger.info(f"[CAPABILITY] Registered Genesis update callback: {callback.__name__}")


# Global capability registry
_capability_registry: Optional[GenesisCapabilityRegistry] = None


def get_capability_registry() -> GenesisCapabilityRegistry:
    """Get the global capability registry."""
    global _capability_registry
    if _capability_registry is None:
        _capability_registry = GenesisCapabilityRegistry()
    return _capability_registry


def register_pipeline_capabilities(
    pipeline_id: str,
    pipeline_name: str,
    required_capabilities: List[CapabilityRequirement]
) -> PipelineCapabilityBinding:
    """Register a pipeline with capability requirements."""
    registry = get_capability_registry()
    return registry.register_pipeline(pipeline_id, pipeline_name, required_capabilities)


def check_pipeline_eligibility(
    pipeline_id: str,
    genesis_key: GenesisKey
) -> Tuple[bool, List[str]]:
    """Check if a pipeline is eligible to run."""
    registry = get_capability_registry()
    return registry.check_pipeline_eligibility(pipeline_id, genesis_key)
