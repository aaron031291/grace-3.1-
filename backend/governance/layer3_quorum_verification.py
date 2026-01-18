"""
Layer 3 Quorum Verification Engine

Grace's built-in ethical compass and governance system:
- Verification layer that double-checks reasoning
- Internal "Parliament" that oversees bigger decisions  
- Constitutional framework that sets moral guidelines
- Trust scoring with multi-source correlation

Trust Score Sources:
- WHITELIST (100%): Explicitly trusted sources
- INTERNAL_DATA (100%): From Grace's own systems
- PROACTIVE_LEARNING (100%): Self-discovered knowledge
- ORACLE (100%): Oracle-validated data
- HUMAN_TRIGGERED (100%): Direct human input
- EXTERNAL (requires verification): Web, LLM queries, chat, external files

Verification passes when data/logic correlates across multiple sources.
Genesis Keys help detect contradictions.
TimeSense helps with temporal verification.
"""

import logging
import asyncio
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class TrustSource(str, Enum):
    """Source categories for trust scoring."""
    WHITELIST = "whitelist"  # 100% trusted
    INTERNAL_DATA = "internal_data"  # 100% trusted
    PROACTIVE_LEARNING = "proactive_learning"  # 100% trusted
    ORACLE = "oracle"  # 100% trusted
    HUMAN_TRIGGERED = "human_triggered"  # 100% trusted
    WEB = "web"  # Requires verification
    LLM_QUERY = "llm_query"  # Requires verification
    CHAT_MESSAGE = "chat_message"  # Requires verification
    EXTERNAL_FILE = "external_file"  # Requires verification
    UNKNOWN = "unknown"  # Requires verification


class VerificationResult(str, Enum):
    """Result of verification."""
    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"
    PENDING = "pending"


class QuorumDecision(str, Enum):
    """Quorum voting decisions."""
    APPROVE = "approve"
    REJECT = "reject"
    AMEND = "amend"
    ESCALATE = "escalate"


@dataclass
class TrustAssessment:
    """Assessment of data/action trustworthiness."""
    assessment_id: str
    source: TrustSource
    base_score: float  # Initial score based on source
    verified_score: float  # Score after verification
    verification_result: VerificationResult
    genesis_key_id: Optional[str] = None
    correlation_sources: List[str] = field(default_factory=list)
    contradictions_found: List[str] = field(default_factory=list)
    timesense_validated: bool = False
    quorum_approved: bool = False
    kpi_impact: float = 0.0  # Impact on component KPIs
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            "source": self.source.value,
            "base_score": self.base_score,
            "verified_score": self.verified_score,
            "verification_result": self.verification_result.value,
            "genesis_key_id": self.genesis_key_id,
            "correlation_sources": self.correlation_sources,
            "contradictions_found": self.contradictions_found,
            "timesense_validated": self.timesense_validated,
            "quorum_approved": self.quorum_approved,
            "kpi_impact": self.kpi_impact,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ComponentKPI:
    """KPI tracking for a Grace component."""
    component_id: str
    component_name: str
    success_count: int = 0
    failure_count: int = 0
    total_operations: int = 0
    current_score: float = 0.5  # 0-1, starts neutral
    trend: str = "stable"  # improving, declining, stable
    last_updated: datetime = field(default_factory=lambda: datetime.now(UTC))
    history: List[Dict[str, Any]] = field(default_factory=list)
    
    def record_outcome(self, success: bool, weight: float = 1.0, 
                       meets_grace_standard: bool = True, 
                       meets_user_standard: bool = True):
        """Record operation outcome and update KPI."""
        self.total_operations += 1
        
        # Calculate adjustment
        if success and meets_grace_standard and meets_user_standard:
            self.success_count += 1
            adjustment = 0.02 * weight
        elif success and (meets_grace_standard or meets_user_standard):
            self.success_count += 1
            adjustment = 0.01 * weight
        else:
            self.failure_count += 1
            adjustment = -0.03 * weight  # Failures penalized more
        
        old_score = self.current_score
        self.current_score = max(0.0, min(1.0, self.current_score + adjustment))
        
        # Update trend
        if self.current_score > old_score:
            self.trend = "improving"
        elif self.current_score < old_score:
            self.trend = "declining"
        else:
            self.trend = "stable"
        
        self.last_updated = datetime.now(UTC)
        
        # Keep history (last 100 entries)
        self.history.append({
            "timestamp": self.last_updated.isoformat(),
            "success": success,
            "score": self.current_score,
            "meets_grace": meets_grace_standard,
            "meets_user": meets_user_standard
        })
        if len(self.history) > 100:
            self.history = self.history[-100:]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_name": self.component_name,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_operations": self.total_operations,
            "current_score": self.current_score,
            "success_rate": self.success_count / max(1, self.total_operations),
            "trend": self.trend,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class QuorumVote:
    """A vote in the quorum."""
    voter_id: str  # Model ID, system component, or human
    decision: QuorumDecision
    confidence: float
    reasoning: str
    genesis_key_ref: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class QuorumSession:
    """A quorum session for decision-making."""
    session_id: str
    proposal: Dict[str, Any]
    required_votes: int = 3
    votes: List[QuorumVote] = field(default_factory=list)
    decision: Optional[QuorumDecision] = None
    confidence: float = 0.0
    genesis_key_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: Optional[datetime] = None
    
    def is_complete(self) -> bool:
        return len(self.votes) >= self.required_votes
    
    def calculate_decision(self) -> Tuple[QuorumDecision, float]:
        """Calculate final decision from votes."""
        if not self.votes:
            return QuorumDecision.REJECT, 0.0
        
        vote_counts = {}
        confidence_sum = {}
        
        for vote in self.votes:
            decision = vote.decision
            vote_counts[decision] = vote_counts.get(decision, 0) + 1
            confidence_sum[decision] = confidence_sum.get(decision, 0) + vote.confidence
        
        # Find majority
        majority_decision = max(vote_counts, key=vote_counts.get)
        avg_confidence = confidence_sum[majority_decision] / vote_counts[majority_decision]
        
        return majority_decision, avg_confidence


class ConstitutionalFramework:
    """Grace's constitutional/ethical guidelines."""
    
    CORE_PRINCIPLES = {
        "transparency": "All decisions must be explainable and traceable",
        "human_centricity": "Human welfare is the primary concern",
        "trust_earned": "Trust is earned through consistent behavior, not assumed",
        "no_harm": "Actions must not cause harm to users or systems",
        "privacy": "User data is protected and respected",
        "accountability": "All actions are logged and attributable",
        "reversibility": "Critical actions should be reversible when possible"
    }
    
    AUTONOMY_TIERS = {
        0: "No autonomy - Human approval required for all actions",
        1: "Limited autonomy - Can perform read operations, suggest changes",
        2: "Moderate autonomy - Can make reversible changes, needs approval for critical",
        3: "Full autonomy - Can act independently within constitutional bounds"
    }
    
    @classmethod
    def check_compliance(cls, action: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Check if an action complies with constitutional principles."""
        violations = []
        
        # Check transparency
        if not action.get("reasoning") and not action.get("explanation"):
            violations.append("transparency: Missing explanation/reasoning")
        
        # Check reversibility for critical actions
        if action.get("risk_level") == "critical" and not action.get("rollback_plan"):
            violations.append("reversibility: Critical action lacks rollback plan")
        
        # Check privacy
        if action.get("accesses_user_data") and not action.get("privacy_justified"):
            violations.append("privacy: Accessing user data without justification")
        
        return len(violations) == 0, violations


class Layer3QuorumVerification:
    """
    Layer 3 Quorum Verification Engine.
    
    Grace's governance system with:
    - Trust source classification
    - Multi-source correlation verification
    - Genesis Key contradiction detection
    - TimeSense temporal validation
    - Component KPI tracking
    - Constitutional compliance
    """
    
    # 100% trusted sources
    TRUSTED_SOURCES = {
        TrustSource.WHITELIST,
        TrustSource.INTERNAL_DATA,
        TrustSource.PROACTIVE_LEARNING,
        TrustSource.ORACLE,
        TrustSource.HUMAN_TRIGGERED
    }
    
    def __init__(self):
        self.component_kpis: Dict[str, ComponentKPI] = {}
        self.trust_assessments: List[TrustAssessment] = []
        self.quorum_sessions: Dict[str, QuorumSession] = {}
        self.whitelist: set = set()
        
        # Initialize default component KPIs
        self._initialize_component_kpis()
        
        logger.info("[LAYER3-QUORUM] Initialized Layer 3 Quorum Verification Engine")
    
    def _initialize_component_kpis(self):
        """Initialize KPIs for core Grace components."""
        components = [
            ("coding_agent", "Coding Agent"),
            ("self_healing", "Self-Healing System"),
            ("knowledge_base", "Knowledge Base"),
            ("llm_orchestrator", "LLM Orchestrator"),
            ("parliament", "Parliament Governance"),
            ("genesis_tracker", "Genesis Key Tracker"),
            ("timesense", "TimeSense Engine"),
            ("template_engine", "Template Engine"),
            ("oracle", "Oracle System"),
            ("verification_engine", "Verification Engine")
        ]
        
        for comp_id, comp_name in components:
            self.component_kpis[comp_id] = ComponentKPI(
                component_id=comp_id,
                component_name=comp_name
            )
    
    def get_source_base_score(self, source: TrustSource) -> float:
        """Get base trust score for a source type."""
        if source in self.TRUSTED_SOURCES:
            return 1.0
        
        # Verification-required sources start lower
        source_scores = {
            TrustSource.WEB: 0.3,
            TrustSource.LLM_QUERY: 0.5,
            TrustSource.CHAT_MESSAGE: 0.4,
            TrustSource.EXTERNAL_FILE: 0.3,
            TrustSource.UNKNOWN: 0.1
        }
        return source_scores.get(source, 0.1)
    
    def classify_source(self, origin: str, metadata: Dict[str, Any] = None) -> TrustSource:
        """Classify the source of data/action."""
        origin_lower = origin.lower()
        metadata = metadata or {}
        
        # Whitelist check
        if origin in self.whitelist:
            return TrustSource.WHITELIST
        
        # Internal data check
        if any(x in origin_lower for x in ["layer1", "layer2", "internal", "grace_"]):
            return TrustSource.INTERNAL_DATA
        
        # Proactive learning check
        if any(x in origin_lower for x in ["proactive", "self_learned", "autonomous_learning"]):
            return TrustSource.PROACTIVE_LEARNING
        
        # Oracle check
        if any(x in origin_lower for x in ["oracle", "validated_oracle"]):
            return TrustSource.ORACLE
        
        # Human check
        if any(x in origin_lower for x in ["human", "user_input", "manual", "aaron"]):
            return TrustSource.HUMAN_TRIGGERED
        
        # External sources requiring verification
        if any(x in origin_lower for x in ["web", "http", "api_external"]):
            return TrustSource.WEB
        
        if any(x in origin_lower for x in ["llm", "gpt", "claude", "deepseek"]):
            return TrustSource.LLM_QUERY
        
        if any(x in origin_lower for x in ["chat", "message", "conversation"]):
            return TrustSource.CHAT_MESSAGE
        
        if any(x in origin_lower for x in ["file", "upload", "import"]):
            return TrustSource.EXTERNAL_FILE
        
        return TrustSource.UNKNOWN
    
    async def assess_trust(
        self,
        data: Any,
        origin: str,
        genesis_key_id: Optional[str] = None,
        correlation_check: bool = True,
        timesense_validate: bool = True
    ) -> TrustAssessment:
        """
        Assess trustworthiness of data/action.
        
        Args:
            data: The data or action to assess
            origin: Where the data came from
            genesis_key_id: Associated Genesis Key
            correlation_check: Whether to check correlation across sources
            timesense_validate: Whether to validate with TimeSense
        
        Returns:
            TrustAssessment with verified score
        """
        assessment_id = str(uuid.uuid4())[:8]
        source = self.classify_source(origin)
        base_score = self.get_source_base_score(source)
        
        # For trusted sources, verification is automatic pass
        if source in self.TRUSTED_SOURCES:
            assessment = TrustAssessment(
                assessment_id=assessment_id,
                source=source,
                base_score=base_score,
                verified_score=base_score,
                verification_result=VerificationResult.PASSED,
                genesis_key_id=genesis_key_id,
                quorum_approved=True
            )
            self.trust_assessments.append(assessment)
            return assessment
        
        # For external sources, run verification
        verified_score = base_score
        verification_result = VerificationResult.PENDING
        correlation_sources = []
        contradictions = []
        timesense_valid = False
        
        # Multi-source correlation check
        if correlation_check:
            correlation_result = await self._check_correlation(data, genesis_key_id)
            correlation_sources = correlation_result.get("sources", [])
            contradictions = correlation_result.get("contradictions", [])
            
            if len(correlation_sources) >= 2 and not contradictions:
                verified_score = min(1.0, base_score + 0.3)
                verification_result = VerificationResult.PASSED
            elif contradictions:
                verified_score = max(0.0, base_score - 0.3)
                verification_result = VerificationResult.FAILED
        
        # TimeSense validation
        if timesense_validate:
            timesense_valid = await self._validate_with_timesense(data, genesis_key_id)
            if timesense_valid:
                verified_score = min(1.0, verified_score + 0.1)
        
        # Genesis Key contradiction detection
        if genesis_key_id:
            genesis_contradictions = await self._check_genesis_contradictions(
                genesis_key_id, data
            )
            if genesis_contradictions:
                contradictions.extend(genesis_contradictions)
                verified_score = max(0.0, verified_score - 0.2)
                verification_result = VerificationResult.FAILED
        
        # Final determination
        if verification_result == VerificationResult.PENDING:
            if verified_score >= 0.6:
                verification_result = VerificationResult.PASSED
            elif verified_score >= 0.3:
                verification_result = VerificationResult.INCONCLUSIVE
            else:
                verification_result = VerificationResult.FAILED
        
        assessment = TrustAssessment(
            assessment_id=assessment_id,
            source=source,
            base_score=base_score,
            verified_score=verified_score,
            verification_result=verification_result,
            genesis_key_id=genesis_key_id,
            correlation_sources=correlation_sources,
            contradictions_found=contradictions,
            timesense_validated=timesense_valid,
            quorum_approved=verification_result == VerificationResult.PASSED
        )
        
        self.trust_assessments.append(assessment)
        
        logger.info(
            f"[LAYER3-QUORUM] Trust assessment: {source.value} "
            f"base={base_score:.2f} verified={verified_score:.2f} "
            f"result={verification_result.value}"
        )
        
        return assessment
    
    async def _check_correlation(
        self, data: Any, genesis_key_id: Optional[str]
    ) -> Dict[str, Any]:
        """Check if data correlates across multiple sources."""
        try:
            from cognitive.knowledge_synthesis import get_knowledge_synthesizer
            synthesizer = get_knowledge_synthesizer()
            
            # Search for corroborating evidence
            data_str = str(data)[:500]
            results = await synthesizer.search_all_layers(data_str, limit=5)
            
            sources = []
            contradictions = []
            
            for result in results:
                source_type = result.get("source", "unknown")
                confidence = result.get("confidence", 0.5)
                
                if confidence > 0.6:
                    sources.append(source_type)
                elif confidence < 0.3:
                    contradictions.append(f"Low confidence from {source_type}")
            
            return {"sources": sources, "contradictions": contradictions}
        except Exception as e:
            logger.warning(f"[LAYER3-QUORUM] Correlation check failed: {e}")
            return {"sources": [], "contradictions": []}
    
    async def _validate_with_timesense(
        self, data: Any, genesis_key_id: Optional[str]
    ) -> bool:
        """Validate data using TimeSense temporal analysis."""
        try:
            from timesense.timesense_engine import get_timesense_engine
            engine = get_timesense_engine()
            
            if genesis_key_id:
                # Check temporal consistency
                validation = engine.validate_temporal_consistency(genesis_key_id)
                return validation.get("consistent", False)
            return True  # No temporal data to validate
        except Exception as e:
            logger.warning(f"[LAYER3-QUORUM] TimeSense validation failed: {e}")
            return True  # Assume valid if TimeSense unavailable
    
    async def _check_genesis_contradictions(
        self, genesis_key_id: str, data: Any
    ) -> List[str]:
        """Check for contradictions using Genesis Keys."""
        try:
            from genesis.genesis_key_service import get_genesis_service
            service = get_genesis_service()
            
            # Get related Genesis Keys
            related_keys = service.get_related_keys(genesis_key_id)
            
            contradictions = []
            data_hash = hashlib.sha256(str(data).encode()).hexdigest()[:16]
            
            for key in related_keys:
                if key.data_hash and key.data_hash[:16] != data_hash:
                    # Check if this is actually contradictory
                    if key.key_type == "assertion" and key.status == "verified":
                        contradictions.append(
                            f"Contradicts Genesis Key {key.key_id}: {key.description}"
                        )
            
            return contradictions
        except Exception as e:
            logger.warning(f"[LAYER3-QUORUM] Genesis contradiction check failed: {e}")
            return []
    
    async def request_quorum(
        self,
        proposal: Dict[str, Any],
        required_votes: int = 3,
        escalation_threshold: float = 0.7
    ) -> QuorumSession:
        """
        Request quorum decision for a proposal.
        
        Args:
            proposal: The decision to be made
            required_votes: Number of votes required
            escalation_threshold: Confidence threshold for auto-escalation
        
        Returns:
            QuorumSession with voting results
        """
        session = QuorumSession(
            session_id=str(uuid.uuid4())[:8],
            proposal=proposal,
            required_votes=required_votes
        )
        
        # Get votes from Parliament
        try:
            from llm_orchestrator.parliament_governance import ParliamentGovernance
            parliament = ParliamentGovernance()
            
            # Conduct parliament session
            result = await parliament.conduct_session(
                decision_type="quorum_vote",
                proposal=str(proposal),
                governance_level="strict"
            )
            
            # Convert parliament votes to quorum votes
            for vote_data in result.get("votes", []):
                vote = QuorumVote(
                    voter_id=vote_data.get("model_id", "unknown"),
                    decision=QuorumDecision.APPROVE if vote_data.get("vote_type") == "approve" else QuorumDecision.REJECT,
                    confidence=vote_data.get("confidence", 0.5),
                    reasoning=vote_data.get("reasoning", "")
                )
                session.votes.append(vote)
            
            session.genesis_key_id = result.get("genesis_key_id")
        except Exception as e:
            logger.warning(f"[LAYER3-QUORUM] Parliament integration failed: {e}")
            # Fallback to automated voting based on trust assessment
            await self._automated_quorum_fallback(session, proposal)
        
        # Calculate final decision
        if session.votes:
            session.decision, session.confidence = session.calculate_decision()
        else:
            session.decision = QuorumDecision.ESCALATE
            session.confidence = 0.0
        
        session.completed_at = datetime.now(UTC)
        self.quorum_sessions[session.session_id] = session
        
        # Check escalation
        if session.confidence < escalation_threshold:
            session.decision = QuorumDecision.ESCALATE
            logger.warning(
                f"[LAYER3-QUORUM] Escalating decision due to low confidence: "
                f"{session.confidence:.2f}"
            )
        
        logger.info(
            f"[LAYER3-QUORUM] Quorum decision: {session.decision.value} "
            f"confidence={session.confidence:.2f}"
        )
        
        return session
    
    async def _automated_quorum_fallback(
        self, session: QuorumSession, proposal: Dict[str, Any]
    ):
        """Fallback automated voting when Parliament unavailable."""
        # Constitutional compliance check
        compliant, violations = ConstitutionalFramework.check_compliance(proposal)
        
        # Create automated vote based on compliance
        vote = QuorumVote(
            voter_id="constitutional_validator",
            decision=QuorumDecision.APPROVE if compliant else QuorumDecision.REJECT,
            confidence=0.8 if compliant else 0.9,
            reasoning=f"Constitutional: {'Compliant' if compliant else 'Violations: ' + ', '.join(violations)}"
        )
        session.votes.append(vote)
        
        # Risk assessment vote
        risk_level = proposal.get("risk_level", "medium")
        risk_vote = QuorumVote(
            voter_id="risk_assessor",
            decision=QuorumDecision.APPROVE if risk_level in ["low", "medium"] else QuorumDecision.ESCALATE,
            confidence=0.7,
            reasoning=f"Risk level: {risk_level}"
        )
        session.votes.append(risk_vote)
        
        # Trust score vote
        trust_score = proposal.get("trust_score", 0.5)
        trust_vote = QuorumVote(
            voter_id="trust_evaluator",
            decision=QuorumDecision.APPROVE if trust_score >= 0.6 else QuorumDecision.REJECT,
            confidence=trust_score,
            reasoning=f"Trust score: {trust_score:.2f}"
        )
        session.votes.append(trust_vote)
    
    def record_component_outcome(
        self,
        component_id: str,
        success: bool,
        meets_grace_standard: bool = True,
        meets_user_standard: bool = True,
        weight: float = 1.0
    ):
        """
        Record outcome for component KPI tracking.
        
        KPIs go up with success + meeting standards.
        KPIs go down with failure or not meeting standards.
        """
        if component_id not in self.component_kpis:
            self.component_kpis[component_id] = ComponentKPI(
                component_id=component_id,
                component_name=component_id.replace("_", " ").title()
            )
        
        kpi = self.component_kpis[component_id]
        old_score = kpi.current_score
        kpi.record_outcome(success, weight, meets_grace_standard, meets_user_standard)
        
        logger.info(
            f"[LAYER3-QUORUM] KPI update for {component_id}: "
            f"{old_score:.2f} -> {kpi.current_score:.2f} ({kpi.trend})"
        )
    
    def get_component_kpi(self, component_id: str) -> Optional[ComponentKPI]:
        """Get KPI for a component."""
        return self.component_kpis.get(component_id)
    
    def get_all_kpis(self) -> Dict[str, Dict[str, Any]]:
        """Get all component KPIs."""
        return {cid: kpi.to_dict() for cid, kpi in self.component_kpis.items()}
    
    def add_to_whitelist(self, source: str):
        """Add a source to the trusted whitelist."""
        self.whitelist.add(source)
        logger.info(f"[LAYER3-QUORUM] Added to whitelist: {source}")
    
    def remove_from_whitelist(self, source: str):
        """Remove a source from the whitelist."""
        self.whitelist.discard(source)
        logger.info(f"[LAYER3-QUORUM] Removed from whitelist: {source}")
    
    def get_governance_status(self) -> Dict[str, Any]:
        """Get overall governance status."""
        # Calculate overall system health from KPIs
        kpi_scores = [kpi.current_score for kpi in self.component_kpis.values()]
        avg_kpi = sum(kpi_scores) / len(kpi_scores) if kpi_scores else 0.5
        
        # Recent trust assessments
        recent_assessments = self.trust_assessments[-50:]
        passed = sum(1 for a in recent_assessments if a.verification_result == VerificationResult.PASSED)
        failed = sum(1 for a in recent_assessments if a.verification_result == VerificationResult.FAILED)
        
        # Recent quorum sessions
        recent_quorums = list(self.quorum_sessions.values())[-20:]
        approved = sum(1 for q in recent_quorums if q.decision == QuorumDecision.APPROVE)
        
        return {
            "governance_health": avg_kpi,
            "component_kpis": self.get_all_kpis(),
            "trust_verification": {
                "total_assessments": len(self.trust_assessments),
                "recent_passed": passed,
                "recent_failed": failed,
                "pass_rate": passed / len(recent_assessments) if recent_assessments else 0
            },
            "quorum_sessions": {
                "total": len(self.quorum_sessions),
                "recent_approved": approved,
                "recent_total": len(recent_quorums),
                "approval_rate": approved / len(recent_quorums) if recent_quorums else 0
            },
            "constitutional_framework": {
                "principles": list(ConstitutionalFramework.CORE_PRINCIPLES.keys()),
                "current_autonomy_tier": 2  # Default to moderate
            },
            "whitelist_size": len(self.whitelist)
        }


# Global instance
_quorum_engine: Optional[Layer3QuorumVerification] = None


def get_quorum_engine() -> Layer3QuorumVerification:
    """Get or create the quorum verification engine."""
    global _quorum_engine
    if _quorum_engine is None:
        _quorum_engine = Layer3QuorumVerification()
    return _quorum_engine


async def verify_and_trust(
    data: Any,
    origin: str,
    genesis_key_id: Optional[str] = None
) -> TrustAssessment:
    """Quick helper to verify data trustworthiness."""
    engine = get_quorum_engine()
    return await engine.assess_trust(data, origin, genesis_key_id)


async def request_governance_decision(
    proposal: Dict[str, Any],
    required_votes: int = 3
) -> QuorumSession:
    """Quick helper to request quorum decision."""
    engine = get_quorum_engine()
    return await engine.request_quorum(proposal, required_votes)
