import logging
import asyncio
import json
import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

# Module-level logger (moved outside Enum class to prevent conflicts)
logger = logging.getLogger(__name__)


class VoteType(str, Enum):
    """Types of votes in parliament."""
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"
    AMEND = "amend"  # Approve with modifications


class DecisionType(str, Enum):
    """Types of decisions requiring parliament."""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    HALLUCINATION_CHECK = "hallucination_check"
    QUALITY_ASSESSMENT = "quality_assessment"
    REASONING_VALIDATION = "reasoning_validation"
    FACT_VERIFICATION = "fact_verification"


class GovernanceLevel(str, Enum):
    """Levels of governance strictness."""
    MINIMAL = "minimal"       # Single model, no quorum
    STANDARD = "standard"     # 2-model quorum
    STRICT = "strict"         # 3-model quorum, higher thresholds
    CRITICAL = "critical"     # Full parliament, unanimous or supermajority


@dataclass
class ModelTrust:
    """Trust profile for a model."""
    model_id: str
    trust_score: float = 0.7  # 0.0 - 1.0
    accuracy_history: List[float] = field(default_factory=list)
    hallucination_count: int = 0
    correct_votes: int = 0
    total_votes: int = 0
    specializations: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def update_trust(self, was_correct: bool, weight: float = 1.0):
        """Update trust score based on correctness."""
        self.total_votes += 1
        if was_correct:
            self.correct_votes += 1
            delta = 0.02 * weight
        else:
            delta = -0.05 * weight  # Penalize errors more heavily

        self.trust_score = max(0.1, min(1.0, self.trust_score + delta))
        self.accuracy_history.append(1.0 if was_correct else 0.0)
        if len(self.accuracy_history) > 100:
            self.accuracy_history = self.accuracy_history[-100:]
        self.last_updated = datetime.utcnow()


@dataclass
class Vote:
    """A vote from a model in parliament."""
    vote_id: str
    model_id: str
    vote_type: VoteType
    content: str  # The model's output
    confidence: float = 0.0
    trust_weight: float = 1.0
    reasoning: str = ""
    amendments: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ParliamentSession:
    """A parliament session for decision-making."""
    session_id: str
    decision_type: DecisionType
    governance_level: GovernanceLevel
    proposal: str  # The input/task
    votes: List[Vote] = field(default_factory=list)
    quorum_required: int = 2
    quorum_met: bool = False
    final_decision: Optional[str] = None
    decision_confidence: float = 0.0
    anti_hallucination_passed: bool = False
    kpis: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "decision_type": self.decision_type.value,
            "governance_level": self.governance_level.value,
            "proposal": self.proposal[:200],
            "votes": [
                {
                    "model_id": v.model_id,
                    "vote_type": v.vote_type.value,
                    "confidence": v.confidence
                }
                for v in self.votes
            ],
            "quorum_required": self.quorum_required,
            "quorum_met": self.quorum_met,
            "final_decision": self.final_decision[:500] if self.final_decision else None,
            "decision_confidence": self.decision_confidence,
            "anti_hallucination_passed": self.anti_hallucination_passed,
            "kpis": self.kpis
        }


@dataclass
class KPIMetrics:
    """Key Performance Indicators for governance."""
    # Quality KPIs
    code_quality_score: float = 0.0
    hallucination_rate: float = 0.0
    consensus_rate: float = 0.0

    # Performance KPIs
    avg_response_time_ms: float = 0.0
    quorum_achievement_rate: float = 0.0

    # Trust KPIs
    avg_model_trust: float = 0.0
    trust_variance: float = 0.0

    # Governance KPIs
    sessions_completed: int = 0
    decisions_approved: int = 0
    decisions_rejected: int = 0
    amendments_applied: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "quality": {
                "code_quality": self.code_quality_score,
                "hallucination_rate": self.hallucination_rate,
                "consensus_rate": self.consensus_rate
            },
            "performance": {
                "avg_response_time_ms": self.avg_response_time_ms,
                "quorum_rate": self.quorum_achievement_rate
            },
            "trust": {
                "avg_trust": self.avg_model_trust,
                "trust_variance": self.trust_variance
            },
            "governance": {
                "sessions": self.sessions_completed,
                "approved": self.decisions_approved,
                "rejected": self.decisions_rejected,
                "amended": self.amendments_applied
            }
        }


class ParliamentGovernance:
    """
    Multi-model parliament for code quality governance.

    Uses democratic voting among LLMs to:
    1. Ensure consensus on code quality
    2. Detect and prevent hallucinations
    3. Track trust scores for each model
    4. Maintain KPIs for quality governance
    """

    def __init__(
        self,
        multi_llm_client=None,
        session=None,
        genesis_service=None
    ):
        self.multi_llm_client = multi_llm_client
        self.session = session
        self._genesis_service = genesis_service

        # Parliament members (models)
        self.members = {
            "deepseek-coder:33b-instruct": ModelTrust(
                model_id="deepseek-coder:33b-instruct",
                trust_score=0.85,
                specializations=["code_generation", "code_review"]
            ),
            "qwen2.5-coder:32b-instruct": ModelTrust(
                model_id="qwen2.5-coder:32b-instruct",
                trust_score=0.82,
                specializations=["code_generation", "reasoning"]
            ),
            "deepseek-r1:70b": ModelTrust(
                model_id="deepseek-r1:70b",
                trust_score=0.88,
                specializations=["reasoning", "fact_verification"]
            ),
            "deepseek-coder:6.7b-instruct": ModelTrust(
                model_id="deepseek-coder:6.7b-instruct",
                trust_score=0.75,
                specializations=["code_review", "quality_assessment"]
            ),
            "mistral:7b": ModelTrust(
                model_id="mistral:7b",
                trust_score=0.70,
                specializations=["general", "fast_review"]
            )
        }

        # Governance configuration
        self.governance_config = {
            GovernanceLevel.MINIMAL: {
                "quorum": 1,
                "approval_threshold": 0.5,
                "models_to_consult": 1
            },
            GovernanceLevel.STANDARD: {
                "quorum": 2,
                "approval_threshold": 0.6,
                "models_to_consult": 2
            },
            GovernanceLevel.STRICT: {
                "quorum": 3,
                "approval_threshold": 0.7,
                "models_to_consult": 3
            },
            GovernanceLevel.CRITICAL: {
                "quorum": 4,
                "approval_threshold": 0.85,
                "models_to_consult": 5
            }
        }

        # Anti-hallucination thresholds
        self.anti_hallucination = {
            "min_consensus": 0.6,  # 60% agreement required
            "max_contradiction_score": 0.3,
            "require_evidence": True,
            "fact_check_threshold": 0.7
        }

        # Session history
        self._sessions: Dict[str, ParliamentSession] = {}

        # KPIs
        self.kpis = KPIMetrics()

        logger.info("[PARLIAMENT] Governance system initialized with %d members", len(self.members))

    async def convene(
        self,
        proposal: str,
        decision_type: DecisionType,
        governance_level: GovernanceLevel = GovernanceLevel.STANDARD,
        context: Optional[str] = None
    ) -> ParliamentSession:
        """
        Convene parliament to make a decision.

        Args:
            proposal: The input/task to decide on
            decision_type: Type of decision
            governance_level: How strict the governance should be
            context: Additional context

        Returns:
            ParliamentSession with votes and decision
        """
        start_time = datetime.now()

        session = ParliamentSession(
            session_id=f"PARL-{uuid.uuid4().hex[:12]}",
            decision_type=decision_type,
            governance_level=governance_level,
            proposal=proposal,
            quorum_required=self.governance_config[governance_level]["quorum"]
        )

        self._sessions[session.session_id] = session

        try:
            # Select members for this session
            members = self._select_members(decision_type, governance_level)

            # Collect votes from each member
            votes = await self._collect_votes(members, proposal, decision_type, context)
            session.votes = votes

            # Check quorum
            session.quorum_met = len(votes) >= session.quorum_required

            if session.quorum_met:
                # Perform anti-hallucination check
                session.anti_hallucination_passed = await self._anti_hallucination_check(votes)

                # Tally votes and make decision
                session.final_decision, session.decision_confidence = self._tally_votes(
                    votes, governance_level
                )

                # Calculate KPIs for this session
                session.kpis = self._calculate_session_kpis(session, votes)

                # Update model trust based on consensus
                self._update_model_trust(votes, session.final_decision)

            session.completed_at = datetime.now()

            # Update global KPIs
            self._update_kpis(session, (datetime.now() - start_time).total_seconds() * 1000)

            logger.info(
                f"[PARLIAMENT] Session {session.session_id}: "
                f"quorum={'MET' if session.quorum_met else 'NOT MET'}, "
                f"hallucination_check={'PASSED' if session.anti_hallucination_passed else 'FAILED'}, "
                f"confidence={session.decision_confidence:.2f}"
            )

        except Exception as e:
            logger.error(f"[PARLIAMENT] Session failed: {e}")
            session.kpis["error"] = str(e)

        return session

    def _select_members(
        self,
        decision_type: DecisionType,
        governance_level: GovernanceLevel
    ) -> List[ModelTrust]:
        """Select parliament members for the decision."""
        config = self.governance_config[governance_level]
        num_to_select = config["models_to_consult"]

        # Score models based on specialization and trust
        scored_members = []
        for model_id, trust in self.members.items():
            score = trust.trust_score

            # Boost for specialization
            if decision_type.value in trust.specializations:
                score += 0.15

            scored_members.append((trust, score))

        # Sort by score and select top N
        scored_members.sort(key=lambda x: x[1], reverse=True)
        return [m[0] for m in scored_members[:num_to_select]]

    async def _collect_votes(
        self,
        members: List[ModelTrust],
        proposal: str,
        decision_type: DecisionType,
        context: Optional[str]
    ) -> List[Vote]:
        """Collect votes from all parliament members."""
        votes = []

        if not self.multi_llm_client:
            # Simulate votes for testing
            for member in members:
                vote = Vote(
                    vote_id=f"VOTE-{uuid.uuid4().hex[:8]}",
                    model_id=member.model_id,
                    vote_type=VoteType.APPROVE,
                    content=f"Simulated response for: {proposal[:100]}",
                    confidence=0.7,
                    trust_weight=member.trust_score
                )
                votes.append(vote)
            return votes

        # Collect votes in parallel
        async def get_vote(member: ModelTrust) -> Vote:
            prompt = self._build_voting_prompt(proposal, decision_type, context)

            try:
                response = await self.multi_llm_client.generate(
                    prompt=prompt,
                    model=member.model_id,
                    temperature=0.3,
                    max_tokens=2000
                )

                content = response.get("response", "")
                vote_type, confidence, reasoning = self._parse_vote(content)

                return Vote(
                    vote_id=f"VOTE-{uuid.uuid4().hex[:8]}",
                    model_id=member.model_id,
                    vote_type=vote_type,
                    content=content,
                    confidence=confidence,
                    trust_weight=member.trust_score,
                    reasoning=reasoning
                )

            except Exception as e:
                logger.warning(f"[PARLIAMENT] Vote collection failed for {member.model_id}: {e}")
                return Vote(
                    vote_id=f"VOTE-{uuid.uuid4().hex[:8]}",
                    model_id=member.model_id,
                    vote_type=VoteType.ABSTAIN,
                    content=f"Error: {e}",
                    confidence=0.0,
                    trust_weight=member.trust_score
                )

        tasks = [get_vote(member) for member in members]
        votes = await asyncio.gather(*tasks)

        return list(votes)

    def _build_voting_prompt(
        self,
        proposal: str,
        decision_type: DecisionType,
        context: Optional[str]
    ) -> str:
        """Build voting prompt for parliament members."""
        type_prompts = {
            DecisionType.CODE_GENERATION: """Evaluate this code generation proposal.
Assess for: correctness, completeness, quality, best practices.
Vote APPROVE if high quality, REJECT if issues found, AMEND if minor fixes needed.""",

            DecisionType.CODE_REVIEW: """Review this code thoroughly.
Check for: bugs, security issues, performance, maintainability.
Vote APPROVE if acceptable, REJECT if significant issues, AMEND with specific fixes.""",

            DecisionType.HALLUCINATION_CHECK: """Verify this content for accuracy.
Check if claims are factual and code is valid.
Vote APPROVE if verified, REJECT if hallucination detected, provide evidence.""",

            DecisionType.QUALITY_ASSESSMENT: """Assess the quality of this output.
Evaluate: code quality, documentation, structure, best practices.
Vote APPROVE if meets standards, REJECT if below threshold.""",

            DecisionType.REASONING_VALIDATION: """Validate this reasoning chain.
Check if logic is sound and conclusions follow from premises.
Vote APPROVE if valid, REJECT if logical errors found.""",

            DecisionType.FACT_VERIFICATION: """Verify these facts and claims.
Cross-check against known information.
Vote APPROVE if accurate, REJECT if inaccurate, cite evidence."""
        }

        return f"""{type_prompts.get(decision_type, type_prompts[DecisionType.CODE_REVIEW])}

PROPOSAL:
{proposal}

{f"CONTEXT:{chr(10)}{context}" if context else ""}

Provide your vote in this format:
VOTE: [APPROVE/REJECT/AMEND/ABSTAIN]
CONFIDENCE: [0.0-1.0]
REASONING: [Your analysis]
{f"AMENDMENTS: [Suggested changes]" if decision_type == DecisionType.CODE_REVIEW else ""}
"""

    def _parse_vote(self, response: str) -> Tuple[VoteType, float, str]:
        """Parse vote from model response."""
        # Default values
        vote_type = VoteType.ABSTAIN
        confidence = 0.5
        reasoning = ""

        # Parse vote type
        vote_match = re.search(r'VOTE:\s*(APPROVE|REJECT|AMEND|ABSTAIN)', response, re.IGNORECASE)
        if vote_match:
            vote_str = vote_match.group(1).upper()
            vote_type = VoteType(vote_str.lower())

        # Parse confidence
        conf_match = re.search(r'CONFIDENCE:\s*(\d+\.?\d*)', response)
        if conf_match:
            confidence = min(1.0, max(0.0, float(conf_match.group(1))))

        # Parse reasoning
        reason_match = re.search(r'REASONING:\s*(.+?)(?=AMENDMENTS:|$)', response, re.DOTALL)
        if reason_match:
            reasoning = reason_match.group(1).strip()

        return vote_type, confidence, reasoning

    async def _anti_hallucination_check(self, votes: List[Vote]) -> bool:
        """Perform anti-hallucination check on votes."""
        if not votes:
            return False

        # Check consensus on key claims
        approve_votes = [v for v in votes if v.vote_type == VoteType.APPROVE]
        reject_votes = [v for v in votes if v.vote_type == VoteType.REJECT]

        # If too many rejections, likely hallucination
        if len(reject_votes) > len(votes) * (1 - self.anti_hallucination["min_consensus"]):
            logger.warning("[PARLIAMENT] Anti-hallucination: Too many rejections")
            return False

        # Check for contradictions in reasoning
        contradiction_score = self._calculate_contradiction_score(votes)
        if contradiction_score > self.anti_hallucination["max_contradiction_score"]:
            logger.warning(f"[PARLIAMENT] Anti-hallucination: High contradiction score ({contradiction_score:.2f})")
            return False

        # Check confidence levels (with division by zero protection)
        if not votes:
            logger.warning("[PARLIAMENT] Anti-hallucination: No votes provided")
            return False
        
        avg_confidence = sum(v.confidence for v in votes) / len(votes)
        if avg_confidence < self.anti_hallucination["fact_check_threshold"]:
            logger.warning(f"[PARLIAMENT] Anti-hallucination: Low average confidence ({avg_confidence:.2f})")
            return False

        return True

    def _calculate_contradiction_score(self, votes: List[Vote]) -> float:
        """Calculate how contradictory the votes are."""
        if len(votes) < 2:
            return 0.0

        # Count vote type distribution
        vote_types = [v.vote_type for v in votes]
        approve = vote_types.count(VoteType.APPROVE)
        reject = vote_types.count(VoteType.REJECT)

        # If split between approve and reject, high contradiction
        if approve > 0 and reject > 0:
            minority = min(approve, reject)
            return minority / len(votes)

        return 0.0

    def _tally_votes(
        self,
        votes: List[Vote],
        governance_level: GovernanceLevel
    ) -> Tuple[Optional[str], float]:
        """Tally votes and determine final decision."""
        if not votes:
            return None, 0.0

        config = self.governance_config[governance_level]
        threshold = config["approval_threshold"]

        # Calculate weighted votes
        weighted_approve = 0.0
        weighted_reject = 0.0
        total_weight = 0.0

        best_content = None
        best_confidence = 0.0

        for vote in votes:
            weight = vote.trust_weight * vote.confidence

            if vote.vote_type == VoteType.APPROVE:
                weighted_approve += weight
                if vote.confidence > best_confidence:
                    best_confidence = vote.confidence
                    best_content = vote.content
            elif vote.vote_type == VoteType.REJECT:
                weighted_reject += weight
            elif vote.vote_type == VoteType.AMEND:
                weighted_approve += weight * 0.7  # Partial approval
                if vote.amendments:
                    best_content = vote.amendments

            total_weight += weight

        if total_weight == 0:
            return None, 0.0

        approval_ratio = weighted_approve / total_weight

        if approval_ratio >= threshold:
            self.kpis.decisions_approved += 1
            return best_content, approval_ratio
        else:
            self.kpis.decisions_rejected += 1
            return None, approval_ratio

    def _update_model_trust(self, votes: List[Vote], final_decision: Optional[str]):
        """Update trust scores based on vote alignment with final decision."""
        decision_approved = final_decision is not None

        for vote in votes:
            if vote.model_id in self.members:
                # Check if vote aligned with final decision
                aligned = (
                    (decision_approved and vote.vote_type in [VoteType.APPROVE, VoteType.AMEND]) or
                    (not decision_approved and vote.vote_type == VoteType.REJECT)
                )

                self.members[vote.model_id].update_trust(aligned, vote.confidence)

    def _calculate_session_kpis(
        self,
        session: ParliamentSession,
        votes: List[Vote]
    ) -> Dict[str, float]:
        """Calculate KPIs for a session."""
        kpis = {}

        # Consensus rate
        if votes:
            vote_types = [v.vote_type for v in votes]
            majority_type = max(set(vote_types), key=vote_types.count)
            kpis["consensus_rate"] = vote_types.count(majority_type) / len(votes)

        # Average confidence
        kpis["avg_confidence"] = sum(v.confidence for v in votes) / len(votes) if votes else 0.0

        # Trust-weighted score
        kpis["trust_weighted_score"] = (
            sum(v.trust_weight * v.confidence for v in votes) /
            sum(v.trust_weight for v in votes)
        ) if votes else 0.0

        # Participation rate
        kpis["participation_rate"] = len(votes) / session.quorum_required if session.quorum_required else 0.0

        return kpis

    def _update_kpis(self, session: ParliamentSession, response_time_ms: float):
        """Update global KPIs."""
        self.kpis.sessions_completed += 1

        # Update response time average
        n = self.kpis.sessions_completed
        self.kpis.avg_response_time_ms = (
            (self.kpis.avg_response_time_ms * (n - 1) + response_time_ms) / n
        )

        # Update quorum achievement rate
        if session.quorum_met:
            self.kpis.quorum_achievement_rate = (
                (self.kpis.quorum_achievement_rate * (n - 1) + 1.0) / n
            )
        else:
            self.kpis.quorum_achievement_rate = (
                (self.kpis.quorum_achievement_rate * (n - 1)) / n
            )

        # Update consensus rate
        if "consensus_rate" in session.kpis:
            self.kpis.consensus_rate = (
                (self.kpis.consensus_rate * (n - 1) + session.kpis["consensus_rate"]) / n
            )

        # Update hallucination rate
        if not session.anti_hallucination_passed:
            self.kpis.hallucination_rate = (
                (self.kpis.hallucination_rate * (n - 1) + 1.0) / n
            )
        else:
            self.kpis.hallucination_rate = (
                (self.kpis.hallucination_rate * (n - 1)) / n
            )

        # Update trust metrics
        trust_scores = [m.trust_score for m in self.members.values()]
        self.kpis.avg_model_trust = sum(trust_scores) / len(trust_scores)
        mean = self.kpis.avg_model_trust
        self.kpis.trust_variance = sum((t - mean) ** 2 for t in trust_scores) / len(trust_scores)

    async def code_quality_parliament(
        self,
        code: str,
        task: str,
        language: str = "python"
    ) -> ParliamentSession:
        """
        Convene parliament specifically for code quality assessment.
        """
        proposal = f"""
LANGUAGE: {language}
TASK: {task}

CODE:
```{language}
{code}
```

Assess this code for:
1. Correctness - Does it implement the task correctly?
2. Quality - Is it well-written, readable, maintainable?
3. Best Practices - Does it follow {language} conventions?
4. Security - Any security issues?
5. Performance - Any performance concerns?
"""

        session = await self.convene(
            proposal=proposal,
            decision_type=DecisionType.QUALITY_ASSESSMENT,
            governance_level=GovernanceLevel.STANDARD
        )

        # Extract quality score from session
        if session.kpis.get("trust_weighted_score"):
            self.kpis.code_quality_score = (
                (self.kpis.code_quality_score * (self.kpis.sessions_completed - 1) +
                 session.kpis["trust_weighted_score"]) / self.kpis.sessions_completed
            )

        return session

    async def anti_hallucination_review(
        self,
        content: str,
        claims: Optional[List[str]] = None
    ) -> ParliamentSession:
        """
        Convene parliament for anti-hallucination review.
        """
        claims_text = ""
        if claims:
            claims_text = "\n\nSPECIFIC CLAIMS TO VERIFY:\n" + "\n".join(f"- {c}" for c in claims)

        proposal = f"""
CONTENT TO VERIFY:
{content}
{claims_text}

Verify this content for:
1. Factual accuracy - Are claims true?
2. Code correctness - Is code valid?
3. Logical consistency - Does it make sense?
4. Source verification - Can claims be verified?
"""

        return await self.convene(
            proposal=proposal,
            decision_type=DecisionType.HALLUCINATION_CHECK,
            governance_level=GovernanceLevel.STRICT  # Higher bar for hallucination
        )

    def get_kpis(self) -> Dict[str, Any]:
        """Get current KPIs."""
        return self.kpis.to_dict()

    def get_trust_report(self) -> Dict[str, Any]:
        """Get trust scores for all models."""
        return {
            model_id: {
                "trust_score": trust.trust_score,
                "accuracy_rate": sum(trust.accuracy_history) / len(trust.accuracy_history) if trust.accuracy_history else 0.0,
                "total_votes": trust.total_votes,
                "correct_votes": trust.correct_votes,
                "hallucination_count": trust.hallucination_count,
                "specializations": trust.specializations
            }
            for model_id, trust in self.members.items()
        }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a parliament session."""
        if session_id in self._sessions:
            return self._sessions[session_id].to_dict()
        return None

    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent parliament sessions."""
        sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.created_at,
            reverse=True
        )
        return [s.to_dict() for s in sessions[:limit]]

    def get_governance_summary(self) -> Dict[str, Any]:
        """Get summary of governance status."""
        return {
            "total_members": len(self.members),
            "active_members": sum(1 for m in self.members.values() if m.trust_score > 0.5),
            "kpis": self.kpis.to_dict(),
            "trust_report": self.get_trust_report(),
            "recent_sessions": len(self._sessions),
            "anti_hallucination_config": self.anti_hallucination,
            "governance_levels": {
                level.value: config for level, config in self.governance_config.items()
            }
        }
