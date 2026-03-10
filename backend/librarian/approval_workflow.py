"""
ApprovalWorkflow - Permission Management and Approval Queue

Manages tiered permission system for librarian actions:
- Auto-commit: Safe actions (tagging, metadata, indexing)
- Approval required: Sensitive actions (folder creation, deletion, moves)

Provides approval queue for human review of pending actions.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timezone
import logging

from models.librarian_models import LibrarianAction
from models.database_models import Document

logger = logging.getLogger(__name__)


class ApprovalWorkflow:
    """
    Manages approval workflow for librarian actions.

    Permission Tiers:
    - **auto**: Executed immediately (tag assignment, metadata updates, indexing, relationship detection)
    - **approval_required**: Wait for human approval (folder creation, file deletion, cross-category moves)

    Example:
        >>> workflow = ApprovalWorkflow(db_session)
        >>>
        >>> # Create action
        >>> action = workflow.create_action(
        ...     document_id=123,
        ...     action_type="assign_tag",
        ...     action_params={"tag_names": ["ai"]},
        ...     triggered_by="rule",
        ...     reason="Matched PDF Documents rule"
        ... )
        >>>
        >>> # Check permission tier
        >>> if action.permission_tier == "auto":
        ...     # Execute immediately
        ...     pass
        >>> else:
        ...     # Wait for approval
        ...     pass
    """

    # Action types that are auto-approved
    AUTO_APPROVED_ACTIONS = {
        "assign_tag",
        "update_metadata",
        "reindex",
        "detect_relationship",
        "calculate_confidence",
        "extract_content"
    }

    # Action types requiring approval
    APPROVAL_REQUIRED_ACTIONS = {
        "create_folder",
        "delete_file",
        "move_file",
        "rename_file",
        "delete_folder",
        "modify_system_file"
    }

    def __init__(self, db_session: Session):
        """
        Initialize ApprovalWorkflow.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def create_action(
        self,
        document_id: Optional[int],
        action_type: str,
        action_params: Dict[str, Any],
        triggered_by: str = "system",
        reason: Optional[str] = None,
        confidence: float = 1.0
    ) -> LibrarianAction:
        """
        Create a new action for the approval workflow.

        Args:
            document_id: Document ID (None for system-wide actions)
            action_type: Type of action (assign_tag, create_folder, etc.)
            action_params: Parameters for the action
            triggered_by: Who/what triggered it (system, user, rule, ai, grace)
            reason: Human-readable explanation
            confidence: Confidence in the action (0.0-1.0)

        Returns:
            LibrarianAction: Created action

        Example:
            >>> action = workflow.create_action(
            ...     document_id=123,
            ...     action_type="assign_tag",
            ...     action_params={"tag_names": ["research", "ai"]},
            ...     triggered_by="rule",
            ...     reason="Matched AI Research folder pattern",
            ...     confidence=0.95
            ... )
        """
        # Determine permission tier
        permission_tier = self.get_permission_tier(action_type, action_params)

        # Create action
        action = LibrarianAction(
            document_id=document_id,
            action_type=action_type,
            action_params=action_params,
            permission_tier=permission_tier,
            status="pending",
            triggered_by=triggered_by,
            reason=reason,
            confidence=confidence
        )

        self.db.add(action)
        self.db.commit()
        self.db.refresh(action)

        logger.info(f"Created action {action.id}: {action_type} (tier: {permission_tier})")
        return action

    def get_permission_tier(
        self,
        action_type: str,
        action_params: Dict[str, Any]
    ) -> str:
        """
        Determine permission tier for an action.

        Args:
            action_type: Type of action
            action_params: Action parameters

        Returns:
            str: "auto" or "approval_required"

        Example:
            >>> tier = workflow.get_permission_tier("assign_tag", {"tag_names": ["ai"]})
            >>> print(tier)  # "auto"
            >>>
            >>> tier = workflow.get_permission_tier("delete_file", {"file_id": 123})
            >>> print(tier)  # "approval_required"
        """
        # Check if action is explicitly auto-approved
        if action_type in self.AUTO_APPROVED_ACTIONS:
            return "auto"

        # Check if action explicitly requires approval
        if action_type in self.APPROVAL_REQUIRED_ACTIONS:
            return "approval_required"

        # Additional heuristics based on action params
        if action_type == "move_file":
            # Moving within same folder is auto, across folders requires approval
            source_path = action_params.get("source_path", "")
            target_path = action_params.get("target_path", "")

            source_folder = "/".join(source_path.split("/")[:-1])
            target_folder = "/".join(target_path.split("/")[:-1])

            if source_folder == target_folder:
                return "auto"
            else:
                return "approval_required"

        # Default to requiring approval for unknown actions
        logger.warning(f"Unknown action type '{action_type}', defaulting to approval_required")
        return "approval_required"

    def get_pending_actions(
        self,
        document_id: Optional[int] = None,
        permission_tier: Optional[str] = None,
        limit: int = 50
    ) -> List[LibrarianAction]:
        """
        Get pending actions from the approval queue.

        Args:
            document_id: Filter by document ID
            permission_tier: Filter by permission tier
            limit: Maximum number of actions to return

        Returns:
            List[LibrarianAction]: Pending actions

        Example:
            >>> # Get all pending actions requiring approval
            >>> pending = workflow.get_pending_actions(permission_tier="approval_required")
            >>> print(f"{len(pending)} actions awaiting approval")
        """
        query = self.db.query(LibrarianAction).filter(
            LibrarianAction.status == "pending"
        )

        if document_id is not None:
            query = query.filter(LibrarianAction.document_id == document_id)

        if permission_tier:
            query = query.filter(LibrarianAction.permission_tier == permission_tier)

        query = query.order_by(LibrarianAction.created_at.desc()).limit(limit)

        return query.all()

    def approve_action(
        self,
        action_id: int,
        reviewed_by: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Approve a pending action.

        Args:
            action_id: Action ID to approve
            reviewed_by: Who approved it (user ID, username, etc.)
            notes: Optional review notes

        Returns:
            bool: True if approved, False if not found or already processed

        Example:
            >>> success = workflow.approve_action(
            ...     action_id=5,
            ...     reviewed_by="user@example.com",
            ...     notes="Looks good, proceed"
            ... )
        """
        action = self.db.query(LibrarianAction).filter(
            LibrarianAction.id == action_id
        ).first()

        if not action:
            logger.warning(f"Action {action_id} not found")
            return False

        if action.status != "pending":
            logger.warning(f"Action {action_id} is not pending (status: {action.status})")
            return False

        action.status = "approved"
        action.reviewed_by = reviewed_by
        action.reviewed_at = datetime.now(timezone.utc)
        action.review_notes = notes
        action.updated_at = datetime.now(timezone.utc)

        self.db.commit()

        logger.info(f"Action {action_id} approved by {reviewed_by}")
        return True

    def reject_action(
        self,
        action_id: int,
        reviewed_by: str,
        reason: str
    ) -> bool:
        """
        Reject a pending action.

        Args:
            action_id: Action ID to reject
            reviewed_by: Who rejected it
            reason: Reason for rejection

        Returns:
            bool: True if rejected, False if not found or already processed

        Example:
            >>> success = workflow.reject_action(
            ...     action_id=5,
            ...     reviewed_by="user@example.com",
            ...     reason="Incorrect categorization"
            ... )
        """
        action = self.db.query(LibrarianAction).filter(
            LibrarianAction.id == action_id
        ).first()

        if not action:
            logger.warning(f"Action {action_id} not found")
            return False

        if action.status != "pending":
            logger.warning(f"Action {action_id} is not pending (status: {action.status})")
            return False

        action.status = "rejected"
        action.reviewed_by = reviewed_by
        action.reviewed_at = datetime.now(timezone.utc)
        action.review_notes = reason
        action.updated_at = datetime.now(timezone.utc)

        self.db.commit()

        logger.info(f"Action {action_id} rejected by {reviewed_by}: {reason}")
        return True

    def auto_approve_safe_actions(
        self,
        min_confidence: float = 0.8
    ) -> int:
        """
        Automatically approve safe actions with high confidence.

        Args:
            min_confidence: Minimum confidence to auto-approve (default: 0.8)

        Returns:
            int: Number of actions auto-approved

        Example:
            >>> count = workflow.auto_approve_safe_actions(min_confidence=0.9)
            >>> print(f"Auto-approved {count} high-confidence actions")
        """
        # Get pending auto-tier actions with high confidence
        pending_actions = self.db.query(LibrarianAction).filter(
            and_(
                LibrarianAction.status == "pending",
                LibrarianAction.permission_tier == "auto",
                LibrarianAction.confidence >= min_confidence
            )
        ).all()

        approved_count = 0

        for action in pending_actions:
            action.status = "approved"
            action.reviewed_by = "system"
            action.reviewed_at = datetime.now(timezone.utc)
            action.review_notes = f"Auto-approved (confidence: {action.confidence})"
            action.updated_at = datetime.now(timezone.utc)
            approved_count += 1

        if approved_count > 0:
            self.db.commit()
            logger.info(f"Auto-approved {approved_count} actions")

        return approved_count

    def get_action_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about actions in the workflow.

        Returns:
            Dict: Statistics including counts by status, tier, etc.

        Example:
            >>> stats = workflow.get_action_statistics()
            >>> print(f"Pending: {stats['by_status']['pending']}")
            >>> print(f"Auto-tier: {stats['by_tier']['auto']}")
        """
        from sqlalchemy import func

        # Count by status
        by_status = {}
        status_counts = self.db.query(
            LibrarianAction.status,
            func.count(LibrarianAction.id)
        ).group_by(LibrarianAction.status).all()

        for status, count in status_counts:
            by_status[status] = count

        # Count by tier
        by_tier = {}
        tier_counts = self.db.query(
            LibrarianAction.permission_tier,
            func.count(LibrarianAction.id)
        ).group_by(LibrarianAction.permission_tier).all()

        for tier, count in tier_counts:
            by_tier[tier] = count

        # Count by action type
        by_type = {}
        type_counts = self.db.query(
            LibrarianAction.action_type,
            func.count(LibrarianAction.id)
        ).group_by(LibrarianAction.action_type).all()

        for action_type, count in type_counts:
            by_type[action_type] = count

        return {
            "by_status": by_status,
            "by_tier": by_tier,
            "by_type": by_type,
            "total_actions": sum(by_status.values()),
            "pending_approvals": by_status.get("pending", 0)
        }

    def batch_approve(
        self,
        action_ids: List[int],
        reviewed_by: str,
        notes: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Approve multiple actions at once.

        Args:
            action_ids: List of action IDs to approve
            reviewed_by: Who approved them
            notes: Optional notes for all actions

        Returns:
            Dict: {"approved": count, "failed": count}

        Example:
            >>> result = workflow.batch_approve([1, 2, 3, 4], "admin@example.com")
            >>> print(f"Approved {result['approved']}/{len([1,2,3,4])}")
        """
        approved = 0
        failed = 0

        for action_id in action_ids:
            if self.approve_action(action_id, reviewed_by, notes):
                approved += 1
            else:
                failed += 1

        return {"approved": approved, "failed": failed}

    def batch_reject(
        self,
        action_ids: List[int],
        reviewed_by: str,
        reason: str
    ) -> Dict[str, int]:
        """
        Reject multiple actions at once.

        Args:
            action_ids: List of action IDs to reject
            reviewed_by: Who rejected them
            reason: Rejection reason

        Returns:
            Dict: {"rejected": count, "failed": count}
        """
        rejected = 0
        failed = 0

        for action_id in action_ids:
            if self.reject_action(action_id, reviewed_by, reason):
                rejected += 1
            else:
                failed += 1

        return {"rejected": rejected, "failed": failed}
