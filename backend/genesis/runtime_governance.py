import logging
import json
import hashlib
from datetime import datetime, UTC, timedelta
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, field
from models.genesis_key_models import GenesisKey
from genesis.validation_gate import AuthorityScope, DeltaType
class ReviewStatus(str, Enum):
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    logger = logging.getLogger(__name__)
    """Status of Genesis change review."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ReviewType(str, Enum):
    """Type of review required."""
    HUMAN = "human"  # Requires human review
    QUORUM = "quorum"  # Requires quorum approval
    AUTOMATED = "automated"  # Automated review (low risk)
    ROOT = "root"  # Requires root authority


@dataclass
class GenesisChangeProposal:
    """A proposed Genesis change requiring review."""
    proposal_id: str
    genesis_key_id: str
    change_origin: str
    authority_scope: str
    delta_type: str
    proposed_changes: Dict[str, Any]
    requires_review: ReviewType
    risk_level: str  # low, medium, high, critical
    proposer: str
    created_at: str
    deadline: Optional[str] = None
    review_status: ReviewStatus = ReviewStatus.PENDING
    reviewers: List[str] = field(default_factory=list)
    review_comments: List[Dict[str, Any]] = field(default_factory=list)
    signed_by: Optional[str] = None
    signature_hash: Optional[str] = None


@dataclass
class GenesisChangeLog:
    """Log entry for a Genesis change."""
    log_id: str
    timestamp: str
    genesis_key_id: str
    version: int
    change_type: str
    authority_scope: str
    signed_by: str
    signature_hash: str
    git_commit_sha: Optional[str] = None  # Git is just transport
    git_branch: Optional[str] = None
    review_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class GenesisRuntimeGovernance:
    """
    Runtime governance for Genesis evolution.
    
    Ensures Genesis changes are:
    - Runtime-governed (not tied to Git)
    - Logged (complete audit trail)
    - Signed (cryptographic signatures)
    - Reviewed (human or quorum)
    """
    
    def __init__(self, governance_dir: Optional[Path] = None):
        self.governance_dir = governance_dir or Path("backend/data/genesis_governance")
        self.governance_dir.mkdir(parents=True, exist_ok=True)
        
        # Active proposals
        self.proposals: Dict[str, GenesisChangeProposal] = {}
        
        # Change log
        self.change_log: List[GenesisChangeLog] = []
        
        # Load existing state
        self._load_proposals()
        self._load_change_log()
        
        logger.info("[RUNTIME-GOVERNANCE] Initialized Genesis runtime governance")
    
    def _load_proposals(self):
        """Load pending proposals."""
        proposals_file = self.governance_dir / "proposals.json"
        
        if not proposals_file.exists():
            return
        
        try:
            with open(proposals_file, 'r') as f:
                data = json.load(f)
                for prop_data in data.get("proposals", []):
                    proposal = GenesisChangeProposal(**prop_data)
                    if proposal.review_status == ReviewStatus.PENDING:
                        self.proposals[proposal.proposal_id] = proposal
        except Exception as e:
            logger.error(f"[RUNTIME-GOVERNANCE] Failed to load proposals: {e}")
    
    def _save_proposals(self):
        """Save proposals."""
        proposals_file = self.governance_dir / "proposals.json"
        
        data = {
            "proposals": [
                {
                    "proposal_id": p.proposal_id,
                    "genesis_key_id": p.genesis_key_id,
                    "change_origin": p.change_origin,
                    "authority_scope": p.authority_scope,
                    "delta_type": p.delta_type,
                    "proposed_changes": p.proposed_changes,
                    "requires_review": p.requires_review.value,
                    "risk_level": p.risk_level,
                    "proposer": p.proposer,
                    "created_at": p.created_at,
                    "deadline": p.deadline,
                    "review_status": p.review_status.value,
                    "reviewers": p.reviewers,
                    "review_comments": p.review_comments,
                    "signed_by": p.signed_by,
                    "signature_hash": p.signature_hash
                }
                for p in self.proposals.values()
            ]
        }
        
        with open(proposals_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_change_log(self):
        """Load change log."""
        log_file = self.governance_dir / "change_log.json"
        
        if not log_file.exists():
            return
        
        try:
            with open(log_file, 'r') as f:
                data = json.load(f)
                for log_data in data.get("changes", []):
                    log_entry = GenesisChangeLog(**log_data)
                    self.change_log.append(log_entry)
        except Exception as e:
            logger.error(f"[RUNTIME-GOVERNANCE] Failed to load change log: {e}")
    
    def _save_change_log(self):
        """Save change log."""
        log_file = self.governance_dir / "change_log.json"
        
        data = {
            "changes": [
                {
                    "log_id": log.log_id,
                    "timestamp": log.timestamp,
                    "genesis_key_id": log.genesis_key_id,
                    "version": log.version,
                    "change_type": log.change_type,
                    "authority_scope": log.authority_scope,
                    "signed_by": log.signed_by,
                    "signature_hash": log.signature_hash,
                    "git_commit_sha": log.git_commit_sha,
                    "git_branch": log.git_branch,
                    "review_id": log.review_id,
                    "metadata": log.metadata
                }
                for log in self.change_log[-1000:]  # Keep last 1000 entries
            ]
        }
        
        with open(log_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def propose_genesis_change(
        self,
        genesis_key: GenesisKey,
        change_origin: str,
        authority_scope: str,
        delta_type: DeltaType,
        proposed_changes: Dict[str, Any],
        proposer: str,
        git_commit_sha: Optional[str] = None,
        git_branch: Optional[str] = None
    ) -> GenesisChangeProposal:
        """
        Propose a Genesis change requiring review.
        
        This is the entry point for all Genesis mutations.
        Git commits may trigger proposals, but they don't automatically apply.
        """
        proposal_id = f"PROP-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{hashlib.md5(str(genesis_key.key_id).encode()).hexdigest()[:8]}"
        
        # Determine review requirements based on authority and risk
        requires_review = self._determine_review_requirement(authority_scope, delta_type, proposed_changes)
        risk_level = self._assess_risk_level(authority_scope, delta_type, proposed_changes)
        
        # Set deadline based on risk
        deadline = None
        if risk_level == "critical":
            deadline = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        elif risk_level == "high":
            deadline = (datetime.now(UTC) + timedelta(hours=4)).isoformat()
        elif requires_review == ReviewType.HUMAN:
            deadline = (datetime.now(UTC) + timedelta(hours=24)).isoformat()
        
        proposal = GenesisChangeProposal(
            proposal_id=proposal_id,
            genesis_key_id=genesis_key.key_id,
            change_origin=change_origin,
            authority_scope=authority_scope,
            delta_type=delta_type.value,
            proposed_changes=proposed_changes,
            requires_review=requires_review,
            risk_level=risk_level,
            proposer=proposer,
            created_at=datetime.now(UTC).isoformat(),
            deadline=deadline
        )
        
        self.proposals[proposal_id] = proposal
        self._save_proposals()
        
        logger.info(
            f"[RUNTIME-GOVERNANCE] Proposed Genesis change {proposal_id} "
            f"(review: {requires_review.value}, risk: {risk_level})"
        )
        
        return proposal
    
    def _determine_review_requirement(
        self,
        authority_scope: str,
        delta_type: DeltaType,
        proposed_changes: Dict[str, Any]
    ) -> ReviewType:
        """Determine what type of review is required."""
        # ROOT authority always requires ROOT review
        if authority_scope == AuthorityScope.ROOT.value:
            return ReviewType.ROOT
        
        # QUORUM authority requires quorum
        if authority_scope == AuthorityScope.QUORUM.value:
            return ReviewType.QUORUM
        
        # Authority expansion requires human review
        if delta_type == DeltaType.AUTHORITY_EXPANSION:
            return ReviewType.HUMAN
        
        # High-risk changes require human review
        if self._assess_risk_level(authority_scope, delta_type, proposed_changes) in ["high", "critical"]:
            return ReviewType.HUMAN
        
        # Default to automated for low-risk changes
        return ReviewType.AUTOMATED
    
    def _assess_risk_level(
        self,
        authority_scope: str,
        delta_type: DeltaType,
        proposed_changes: Dict[str, Any]
    ) -> str:
        """Assess risk level of proposed change."""
        # ROOT changes are always critical
        if authority_scope == AuthorityScope.ROOT.value:
            return "critical"
        
        # Authority expansion is high risk
        if delta_type == DeltaType.AUTHORITY_EXPANSION:
            return "high"
        
        # Constraint removal is medium-high risk
        if delta_type == DeltaType.CONSTRAINT_REMOVE:
            return "medium"
        
        # Default to low risk
        return "low"
    
    def review_proposal(
        self,
        proposal_id: str,
        reviewer: str,
        approved: bool,
        comment: Optional[str] = None,
        signature: Optional[str] = None
    ) -> GenesisChangeProposal:
        """
        Review a Genesis change proposal.
        
        Returns the updated proposal.
        """
        proposal = self.proposals.get(proposal_id)
        
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        if proposal.review_status != ReviewStatus.PENDING:
            raise ValueError(f"Proposal {proposal_id} already {proposal.review_status.value}")
        
        # Add review comment
        review_comment = {
            "reviewer": reviewer,
            "approved": approved,
            "comment": comment,
            "timestamp": datetime.now(UTC).isoformat(),
            "signature": signature
        }
        
        proposal.review_comments.append(review_comment)
        proposal.reviewers.append(reviewer)
        
        # Check if review requirements are met
        if self._review_requirements_met(proposal):
            proposal.review_status = ReviewStatus.APPROVED if approved else ReviewStatus.REJECTED
            proposal.signed_by = reviewer
            proposal.signature_hash = self._compute_signature_hash(proposal, reviewer)
        
        self._save_proposals()
        
        logger.info(
            f"[RUNTIME-GOVERNANCE] Proposal {proposal_id} reviewed by {reviewer}: "
            f"{'APPROVED' if approved else 'REJECTED'}"
        )
        
        return proposal
    
    def _review_requirements_met(self, proposal: GenesisChangeProposal) -> bool:
        """Check if review requirements are met."""
        if proposal.requires_review == ReviewType.AUTOMATED:
            return len(proposal.reviewers) >= 1
        
        if proposal.requires_review == ReviewType.HUMAN:
            return len(proposal.reviewers) >= 1
        
        if proposal.requires_review == ReviewType.QUORUM:
            return len(proposal.reviewers) >= 3  # Quorum requires 3+ reviewers
        
        if proposal.requires_review == ReviewType.ROOT:
            return any(r == "ROOT" for r in proposal.reviewers)
        
        return False
    
    def _compute_signature_hash(
        self,
        proposal: GenesisChangeProposal,
        signer: str
    ) -> str:
        """Compute signature hash for proposal."""
        data = f"{proposal.proposal_id}:{proposal.genesis_key_id}:{signer}:{datetime.now(UTC).isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def log_genesis_change(
        self,
        genesis_key: GenesisKey,
        change_type: str,
        authority_scope: str,
        signed_by: str,
        git_commit_sha: Optional[str] = None,
        git_branch: Optional[str] = None,
        review_id: Optional[str] = None
    ) -> GenesisChangeLog:
        """
        Log a Genesis change to the audit trail.
        
        This is called AFTER a change is applied (not before).
        Git information is included but is NOT the source of truth.
        """
        log_id = f"LOG-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{hashlib.md5(str(genesis_key.key_id).encode()).hexdigest()[:8]}"
        
        signature_data = f"{genesis_key.key_id}:{genesis_key.genesis_version}:{signed_by}:{datetime.now(UTC).isoformat()}"
        signature_hash = hashlib.sha256(signature_data.encode()).hexdigest()
        
        log_entry = GenesisChangeLog(
            log_id=log_id,
            timestamp=datetime.now(UTC).isoformat(),
            genesis_key_id=genesis_key.key_id,
            version=genesis_key.genesis_version or 0,
            change_type=change_type,
            authority_scope=authority_scope,
            signed_by=signed_by,
            signature_hash=signature_hash,
            git_commit_sha=git_commit_sha,  # Git is just transport
            git_branch=git_branch,
            review_id=review_id,
            metadata={
                "change_origin": genesis_key.change_origin,
                "delta_type": genesis_key.delta_type,
                "propagation_depth": genesis_key.propagation_depth
            }
        )
        
        self.change_log.append(log_entry)
        self._save_change_log()
        
        logger.info(
            f"[RUNTIME-GOVERNANCE] Logged Genesis change {log_id} "
            f"(version {log_entry.version}, signed by {signed_by})"
        )
        
        return log_entry
    
    def get_pending_proposals(self) -> List[GenesisChangeProposal]:
        """Get all pending proposals."""
        return [p for p in self.proposals.values() if p.review_status == ReviewStatus.PENDING]
    
    def get_change_log(self, limit: int = 100) -> List[GenesisChangeLog]:
        """Get recent change log entries."""
        return self.change_log[-limit:]


# Global governance instance
_runtime_governance: Optional[GenesisRuntimeGovernance] = None


def get_runtime_governance() -> GenesisRuntimeGovernance:
    """Get the global runtime governance instance."""
    global _runtime_governance
    if _runtime_governance is None:
        _runtime_governance = GenesisRuntimeGovernance()
    return _runtime_governance
