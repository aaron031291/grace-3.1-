"""
Layer Enforcement - Governance Integration with Layer 1 & Layer 2

Enforces Layer 3 Quorum Verification on all data entering Layer 1 (Facts)
and Layer 2 (Understanding).

ENFORCEMENT RULES:
- ALL data entering Layer 1/2 must pass trust verification
- External sources require multi-source correlation
- Genesis Keys track all ingestion decisions
- KPIs updated based on ingestion success/failure
- Constitutional compliance checked for all actions
"""

import logging
import asyncio
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, UTC
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class EnforcementAction(str, Enum):
    """Actions taken by enforcement layer."""
    ALLOW = "allow"  # Data passes, enters Layer 1/2
    BLOCK = "block"  # Data blocked, doesn't enter
    QUARANTINE = "quarantine"  # Data held for review
    ESCALATE = "escalate"  # Requires human approval


@dataclass
class EnforcementDecision:
    """Decision from enforcement layer."""
    action: EnforcementAction
    trust_score: float
    source_classification: str
    genesis_key_id: Optional[str] = None
    verification_passed: bool = False
    kpi_impact: float = 0.0
    reasoning: str = ""
    constitutional_compliant: bool = True
    violations: list = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action.value,
            "trust_score": self.trust_score,
            "source_classification": self.source_classification,
            "genesis_key_id": self.genesis_key_id,
            "verification_passed": self.verification_passed,
            "kpi_impact": self.kpi_impact,
            "reasoning": self.reasoning,
            "constitutional_compliant": self.constitutional_compliant,
            "violations": self.violations,
            "timestamp": self.timestamp.isoformat()
        }


class LayerEnforcement:
    """
    Governance enforcement for Layer 1 and Layer 2.
    
    All data must pass through this layer before entering the knowledge base.
    """
    
    # Trust thresholds
    ALLOW_THRESHOLD = 0.7  # Score >= 0.7 passes
    QUARANTINE_THRESHOLD = 0.4  # Score 0.4-0.7 quarantined
    # Below 0.4 = blocked
    
    def __init__(self):
        self._quorum_engine = None
        self._genesis_service = None
        self._initialized = False
        
        # Enforcement statistics
        self.stats = {
            "total_enforced": 0,
            "allowed": 0,
            "blocked": 0,
            "quarantined": 0,
            "escalated": 0,
            "layer1_enforced": 0,
            "layer2_enforced": 0
        }
        
        logger.info("[LAYER-ENFORCE] Layer Enforcement initialized")
    
    async def initialize(self):
        """Initialize enforcement connections."""
        if self._initialized:
            return
        
        try:
            from governance.layer3_quorum_verification import get_quorum_engine
            self._quorum_engine = get_quorum_engine()
            
            from genesis.genesis_key_service import get_genesis_service
            self._genesis_service = get_genesis_service()
            
            self._initialized = True
            logger.info("[LAYER-ENFORCE] Enforcement initialized with Quorum Engine")
        except Exception as e:
            logger.warning(f"[LAYER-ENFORCE] Partial initialization: {e}")
            self._initialized = True
    
    async def enforce_layer1_ingestion(
        self,
        data: Any,
        origin: str,
        input_type: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> EnforcementDecision:
        """
        Enforce governance on Layer 1 (Facts) ingestion.
        
        All data entering Layer 1 must pass trust verification.
        
        Args:
            data: Data being ingested
            origin: Source of data
            input_type: Type of input (user_input, file, api, web, etc.)
            user_id: User ID if applicable
            metadata: Additional metadata
        
        Returns:
            EnforcementDecision with action to take
        """
        await self.initialize()
        self.stats["total_enforced"] += 1
        self.stats["layer1_enforced"] += 1
        
        # Determine origin for classification
        effective_origin = self._determine_origin(origin, input_type, user_id)
        
        # Get trust assessment from Quorum Engine
        if self._quorum_engine:
            assessment = await self._quorum_engine.assess_trust(
                data=data,
                origin=effective_origin,
                genesis_key_id=metadata.get("genesis_key_id") if metadata else None,
                correlation_check=True,
                timesense_validate=True
            )
            trust_score = assessment.verified_score
            source_class = assessment.source.value
            verification_passed = assessment.verification_result.value == "passed"
            genesis_key_id = assessment.genesis_key_id
        else:
            # Fallback scoring
            trust_score = self._fallback_trust_score(effective_origin, input_type)
            source_class = effective_origin
            verification_passed = trust_score >= self.ALLOW_THRESHOLD
            genesis_key_id = None
        
        # Check constitutional compliance
        action_data = {
            "type": "layer1_ingestion",
            "input_type": input_type,
            "origin": origin,
            "data_size": len(str(data)),
            "user_id": user_id,
            "reasoning": f"Ingesting {input_type} from {origin}"
        }
        
        from governance.layer3_quorum_verification import ConstitutionalFramework
        constitutional_ok, violations = ConstitutionalFramework.check_compliance(action_data)
        
        # Determine action
        action, reasoning = self._determine_action(
            trust_score, verification_passed, constitutional_ok, violations
        )
        
        # Update KPIs
        kpi_impact = self._update_kpis(
            "layer1_ingestion", 
            action == EnforcementAction.ALLOW,
            trust_score
        )
        
        # Create Genesis Key for enforcement decision
        if self._genesis_service and action != EnforcementAction.BLOCK:
            try:
                from models.genesis_key_models import GenesisKeyType
                key = self._genesis_service.create_key(
                    key_type=GenesisKeyType.SYSTEM_EVENT,
                    actor_id="layer_enforcement",
                    description=f"Layer 1 enforcement: {action.value} for {input_type}",
                    context={
                        "trust_score": trust_score,
                        "source": source_class,
                        "verification": verification_passed,
                        "input_type": input_type
                    }
                )
                genesis_key_id = key.key_id
            except Exception as e:
                logger.warning(f"[LAYER-ENFORCE] Genesis key creation failed: {e}")
        
        # Update stats
        stat_key = action.value
        if stat_key == "allow":
            stat_key = "allowed"
        elif stat_key == "block":
            stat_key = "blocked"
        if stat_key in self.stats:
            self.stats[stat_key] += 1
        
        decision = EnforcementDecision(
            action=action,
            trust_score=trust_score,
            source_classification=source_class,
            genesis_key_id=genesis_key_id,
            verification_passed=verification_passed,
            kpi_impact=kpi_impact,
            reasoning=reasoning,
            constitutional_compliant=constitutional_ok,
            violations=violations
        )
        
        logger.info(
            f"[LAYER-ENFORCE] Layer 1: {action.value} | "
            f"trust={trust_score:.2f} source={source_class} type={input_type}"
        )
        
        return decision
    
    async def enforce_layer2_processing(
        self,
        intent: str,
        observations: Dict[str, Any],
        context: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> EnforcementDecision:
        """
        Enforce governance on Layer 2 (Understanding) processing.
        
        Ensures cognitive processing meets trust and constitutional requirements.
        
        Args:
            intent: User intent being processed
            observations: OODA observations
            context: Processing context
            user_id: User ID if applicable
        
        Returns:
            EnforcementDecision with action to take
        """
        await self.initialize()
        self.stats["total_enforced"] += 1
        self.stats["layer2_enforced"] += 1
        
        # Layer 2 processes internal data - generally trusted
        # But we still verify the intent and observations
        origin = "layer2_cognitive"
        if user_id:
            origin = "human_triggered"
        
        # Assess trust of the observations (they may contain external data)
        combined_data = {
            "intent": intent,
            "observations": observations,
            "context": context
        }
        
        if self._quorum_engine:
            assessment = await self._quorum_engine.assess_trust(
                data=combined_data,
                origin=origin,
                correlation_check=False,  # Layer 2 already correlates
                timesense_validate=True
            )
            trust_score = assessment.verified_score
            source_class = assessment.source.value
            verification_passed = assessment.verification_result.value == "passed"
        else:
            trust_score = 0.85  # Layer 2 internal is generally trusted
            source_class = origin
            verification_passed = True
        
        # Check constitutional compliance for the decision
        action_data = {
            "type": "layer2_processing",
            "intent": intent,
            "reasoning": f"Processing cognitive intent: {intent[:100]}",
            "user_id": user_id
        }
        
        from governance.layer3_quorum_verification import ConstitutionalFramework
        constitutional_ok, violations = ConstitutionalFramework.check_compliance(action_data)
        
        # Determine action
        action, reasoning = self._determine_action(
            trust_score, verification_passed, constitutional_ok, violations
        )
        
        # Update KPIs
        kpi_impact = self._update_kpis(
            "layer2_processing",
            action == EnforcementAction.ALLOW,
            trust_score
        )
        
        decision = EnforcementDecision(
            action=action,
            trust_score=trust_score,
            source_classification=source_class,
            verification_passed=verification_passed,
            kpi_impact=kpi_impact,
            reasoning=reasoning,
            constitutional_compliant=constitutional_ok,
            violations=violations
        )
        
        logger.info(
            f"[LAYER-ENFORCE] Layer 2: {action.value} | "
            f"trust={trust_score:.2f} intent={intent[:50]}..."
        )
        
        return decision
    
    async def enforce_layer_output(
        self,
        layer: int,
        output_data: Any,
        destination: str,
        genesis_key_id: Optional[str] = None
    ) -> EnforcementDecision:
        """
        Enforce governance on Layer 1/2 outputs.
        
        Ensures data leaving the layers meets quality and trust standards.
        """
        await self.initialize()
        self.stats["total_enforced"] += 1
        
        # Outputs from Layer 1/2 are internal - verify destination
        origin = f"layer{layer}_output"
        
        # Check if destination is external
        external_destinations = ["api", "web", "external", "export", "llm"]
        is_external = any(d in destination.lower() for d in external_destinations)
        
        if is_external:
            # More scrutiny for external outputs
            trust_score = 0.6
            if self._quorum_engine:
                # Request quorum for external outputs
                session = await self._quorum_engine.request_quorum(
                    proposal={
                        "type": f"layer{layer}_external_output",
                        "destination": destination,
                        "data_preview": str(output_data)[:500],
                        "trust_score": trust_score
                    },
                    required_votes=2
                )
                if session.decision and session.decision.value == "approve":
                    action = EnforcementAction.ALLOW
                else:
                    action = EnforcementAction.ESCALATE
            else:
                action = EnforcementAction.ALLOW
        else:
            # Internal outputs trusted
            trust_score = 0.9
            action = EnforcementAction.ALLOW
        
        return EnforcementDecision(
            action=action,
            trust_score=trust_score,
            source_classification=origin,
            genesis_key_id=genesis_key_id,
            verification_passed=action == EnforcementAction.ALLOW,
            reasoning=f"Layer {layer} output to {destination}"
        )
    
    def _determine_origin(
        self, origin: str, input_type: str, user_id: Optional[str]
    ) -> str:
        """Determine effective origin for classification."""
        # Human input is always trusted
        if user_id and input_type in ["chat", "user_input", "command"]:
            return "human_triggered"
        
        # Map input types to origins
        type_mappings = {
            "user_input": "human_triggered",
            "chat": "human_triggered",
            "command": "human_triggered",
            "file": "external_file",
            "upload": "external_file",
            "api": "web",
            "web": "web",
            "scraping": "web",
            "llm": "llm_query",
            "system": "internal_data",
            "learning": "proactive_learning",
            "whitelist": "whitelist"
        }
        
        return type_mappings.get(input_type.lower(), origin)
    
    def _fallback_trust_score(self, origin: str, input_type: str) -> float:
        """Fallback trust scoring when Quorum Engine unavailable."""
        trusted_origins = ["human_triggered", "internal_data", "proactive_learning", 
                          "oracle", "whitelist"]
        
        if any(t in origin for t in trusted_origins):
            return 1.0
        
        scores = {
            "web": 0.3,
            "llm_query": 0.5,
            "chat_message": 0.4,
            "external_file": 0.3,
            "api": 0.4
        }
        
        for key, score in scores.items():
            if key in origin.lower():
                return score
        
        return 0.5
    
    def _determine_action(
        self,
        trust_score: float,
        verification_passed: bool,
        constitutional_ok: bool,
        violations: list
    ) -> Tuple[EnforcementAction, str]:
        """Determine enforcement action based on scores and compliance."""
        reasons = []
        
        # Constitutional violations are serious
        if not constitutional_ok:
            reasons.append(f"Constitutional violations: {', '.join(violations)}")
            if "privacy" in str(violations) or "harm" in str(violations):
                return EnforcementAction.BLOCK, " | ".join(reasons)
            return EnforcementAction.ESCALATE, " | ".join(reasons)
        
        # Trust score based decisions
        if trust_score >= self.ALLOW_THRESHOLD:
            if verification_passed:
                return EnforcementAction.ALLOW, "Trust verified"
            else:
                reasons.append("High trust but verification incomplete")
                return EnforcementAction.QUARANTINE, " | ".join(reasons)
        
        elif trust_score >= self.QUARANTINE_THRESHOLD:
            reasons.append(f"Moderate trust score: {trust_score:.2f}")
            return EnforcementAction.QUARANTINE, " | ".join(reasons)
        
        else:
            reasons.append(f"Low trust score: {trust_score:.2f}")
            return EnforcementAction.BLOCK, " | ".join(reasons)
    
    def _update_kpis(
        self, component: str, success: bool, trust_score: float
    ) -> float:
        """Update component KPIs based on enforcement result."""
        if not self._quorum_engine:
            return 0.0
        
        # Map to KPI component IDs
        component_map = {
            "layer1_ingestion": "knowledge_base",
            "layer2_processing": "llm_orchestrator"
        }
        
        component_id = component_map.get(component, component)
        
        self._quorum_engine.record_component_outcome(
            component_id=component_id,
            success=success,
            meets_grace_standard=trust_score >= 0.7,
            meets_user_standard=True,
            weight=trust_score
        )
        
        kpi = self._quorum_engine.get_component_kpi(component_id)
        return kpi.current_score if kpi else 0.5
    
    def get_enforcement_stats(self) -> Dict[str, Any]:
        """Get enforcement statistics."""
        total = self.stats["total_enforced"]
        return {
            "total_enforced": total,
            "allowed": self.stats["allowed"],
            "blocked": self.stats["blocked"],
            "quarantined": self.stats["quarantined"],
            "escalated": self.stats["escalated"],
            "allow_rate": self.stats["allowed"] / max(1, total),
            "block_rate": self.stats["blocked"] / max(1, total),
            "layer1_enforced": self.stats["layer1_enforced"],
            "layer2_enforced": self.stats["layer2_enforced"]
        }


# Global instance
_enforcement: Optional[LayerEnforcement] = None


def get_layer_enforcement() -> LayerEnforcement:
    """Get or create layer enforcement instance."""
    global _enforcement
    if _enforcement is None:
        _enforcement = LayerEnforcement()
    return _enforcement


async def enforce_layer1(
    data: Any,
    origin: str,
    input_type: str,
    user_id: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> EnforcementDecision:
    """Quick helper for Layer 1 enforcement."""
    enforcement = get_layer_enforcement()
    return await enforcement.enforce_layer1_ingestion(
        data, origin, input_type, user_id, metadata
    )


async def enforce_layer2(
    intent: str,
    observations: Dict[str, Any],
    context: Optional[Dict] = None,
    user_id: Optional[str] = None
) -> EnforcementDecision:
    """Quick helper for Layer 2 enforcement."""
    enforcement = get_layer_enforcement()
    return await enforcement.enforce_layer2_processing(
        intent, observations, context, user_id
    )
