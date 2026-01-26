"""
Genesis Key Service - Comprehensive tracking and version control system.

Automatically tracks every input, change, and action with full metadata
for what, where, when, why, who, and how.
"""
import uuid
import json
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from sqlalchemy.orm import Session

from models.genesis_key_models import (
    GenesisKey, FixSuggestion, GenesisKeyArchive, UserProfile,
    GenesisKeyType, GenesisKeyStatus, FixSuggestionStatus
)
from database.session import get_session
from version_control.git_service import GitService
from genesis.kb_integration import get_kb_integration
import os

logger = logging.getLogger(__name__)


class GenesisKeyService:
    """
    Service for creating and managing Genesis Keys.

    Provides automatic tracking of all operations with comprehensive metadata.
    """

    def __init__(self, session: Optional[Session] = None, repo_path: Optional[str] = None):
        self.session = session
        self.repo_path = repo_path or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        try:
            self.git_service = GitService(self.repo_path)
        except Exception as e:
            self.git_service = None
            logger.warning(f"Git service not available for Genesis Key tracking: {e}")

    def generate_user_id(self, identifier: Optional[str] = None) -> str:
        """
        Generate a Genesis user ID.

        Args:
            identifier: Optional identifier (email, username, etc.)

        Returns:
            Unique user ID
        """
        if identifier:
            # Generate deterministic ID from identifier
            hash_obj = hashlib.sha256(identifier.encode())
            return f"GU-{hash_obj.hexdigest()[:16]}"
        else:
            # Generate random ID
            return f"GU-{uuid.uuid4().hex[:16]}"

    def get_or_create_user(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        email: Optional[str] = None,
        session: Optional[Session] = None
    ) -> UserProfile:
        """Get or create a user profile."""
        sess = session or self.session or next(get_session())
        close_session = session is None and self.session is None

        try:
            # Generate user_id if not provided
            if not user_id:
                user_id = self.generate_user_id(email or username)

            # Check if user exists
            user = sess.query(UserProfile).filter(UserProfile.user_id == user_id).first()

            if not user:
                user = UserProfile(
                    user_id=user_id,
                    username=username,
                    email=email
                )
                sess.add(user)
                sess.commit()
                logger.info(f"Created new user profile: {user_id}")

            return user
        finally:
            if close_session:
                sess.close()

    def create_key(
        self,
        key_type: GenesisKeyType,
        what_description: str,
        who_actor: str,
        where_location: Optional[str] = None,
        why_reason: Optional[str] = None,
        how_method: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        function_name: Optional[str] = None,
        code_before: Optional[str] = None,
        code_after: Optional[str] = None,
        is_error: bool = False,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        error_traceback: Optional[str] = None,
        input_data: Optional[Dict] = None,
        output_data: Optional[Dict] = None,
        context_data: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        parent_key_id: Optional[str] = None,
        session: Optional[Session] = None
    ) -> GenesisKey:
        """
        Create a new Genesis Key with comprehensive tracking.

        Args:
            key_type: Type of Genesis Key
            what_description: What happened
            who_actor: Who performed the action
            where_location: Where it happened
            why_reason: Why it happened
            how_method: How it was done
            user_id: User ID (Genesis-generated)
            session_id: Session ID for tracking
            file_path: File path for code changes
            line_number: Line number
            function_name: Function name
            code_before: Code before change
            code_after: Code after change
            is_error: Whether this is an error
            error_type: Type of error
            error_message: Error message
            error_traceback: Error traceback
            input_data: Input data
            output_data: Output data
            context_data: Additional context
            tags: Searchable tags
            parent_key_id: Parent key for chaining
            session: Database session

        Returns:
            Created Genesis Key
        """
        sess = session or self.session or next(get_session())
        close_session = session is None and self.session is None

        try:
            # Generate key ID
            key_id = f"GK-{uuid.uuid4().hex}"

            # Get current commit info if available
            commit_sha = None
            branch_name = None
            if self.git_service:
                try:
                    commits = self.git_service.get_commits(limit=1)
                    if commits:
                        commit_sha = commits[0].get('sha')
                except Exception:
                    pass

            # Generate human-readable metadata
            metadata_human = self._generate_human_metadata(
                key_type=key_type,
                what=what_description,
                where=where_location or file_path,
                when=datetime.utcnow(),
                why=why_reason,
                who=who_actor,
                how=how_method
            )

            # Generate AI-readable metadata
            metadata_ai = {
                "key_type": key_type.value,
                "timestamp": datetime.utcnow().isoformat(),
                "commit_sha": commit_sha,
                "has_code_change": bool(code_before or code_after),
                "is_error": is_error,
                "input_hash": self._hash_data(input_data) if input_data else None,
                "output_hash": self._hash_data(output_data) if output_data else None,
                "tags": tags or []
            }

            # Create Genesis Key
            key = GenesisKey(
                key_id=key_id,
                parent_key_id=parent_key_id,
                key_type=key_type,
                status=GenesisKeyStatus.ERROR if is_error else GenesisKeyStatus.ACTIVE,
                user_id=user_id,
                session_id=session_id,
                what_description=what_description,
                where_location=where_location,
                when_timestamp=datetime.utcnow(),
                why_reason=why_reason,
                who_actor=who_actor,
                how_method=how_method,
                file_path=file_path,
                line_number=line_number,
                function_name=function_name,
                code_before=code_before,
                code_after=code_after,
                is_error=is_error,
                error_type=error_type,
                error_message=error_message,
                error_traceback=error_traceback,
                commit_sha=commit_sha,
                branch_name=branch_name,
                metadata_human=metadata_human,
                metadata_ai=metadata_ai,
                input_data=input_data,
                output_data=output_data,
                context_data=context_data,
                tags=tags
            )

            sess.add(key)
            
            # Only commit if we created our own session
            # If a session was passed in, let the caller handle commits
            if close_session:
                sess.commit()

            # Update user statistics if user_id provided
            if user_id:
                self._update_user_stats(user_id, key_type, is_error, sess)

            # Auto-populate to knowledge base
            try:
                kb_integration = get_kb_integration()
                kb_integration.save_genesis_key(key)
            except Exception as kb_error:
                logger.warning(f"Failed to save Genesis Key to KB: {kb_error}")

            # CRITICAL: Feed into Memory Mesh for learning
            try:
                from cognitive.memory_mesh_integration import MemoryMeshIntegration
                from pathlib import Path

                kb_path = Path(self.repo_path) / "backend" / "knowledge_base"
                memory_mesh = MemoryMeshIntegration(session=sess, knowledge_base_path=kb_path)

                # Ingest Genesis Key as learning experience
                memory_mesh.ingest_learning_experience(
                    experience_type=key_type.value,
                    context={
                        "what": what_description,
                        "where": where_location or file_path,
                        "why": why_reason,
                        "how": how_method
                    },
                    action_taken=input_data or {},
                    outcome=output_data or {},
                    source="genesis_key",
                    user_id=user_id,
                    genesis_key_id=key_id
                )
                logger.info(f"✅ Genesis Key fed into Memory Mesh: {key_id}")
            except Exception as mesh_error:
                logger.warning(f"Failed to feed Genesis Key to Memory Mesh: {mesh_error}")

            # CRITICAL: Trigger autonomous pipeline for every Genesis Key
            try:
                from genesis.autonomous_triggers import get_genesis_trigger_pipeline
                trigger_pipeline = get_genesis_trigger_pipeline(session=sess)
                trigger_result = trigger_pipeline.on_genesis_key_created(key)
                if trigger_result.get("triggered"):
                    logger.info(f"✅ Triggered {len(trigger_result['actions_triggered'])} autonomous action(s) from Genesis Key: {key_id}")
            except Exception as trigger_error:
                logger.warning(f"Failed to trigger autonomous pipeline: {trigger_error}")

            logger.info(f"Created Genesis Key: {key_id} - {what_description}")
            return key

        except Exception as e:
            logger.error(f"Failed to create Genesis Key: {e}")
            if close_session:
                sess.rollback()
            raise
        finally:
            if close_session:
                sess.close()

    @contextmanager
    def track_operation(
        self,
        key_type: GenesisKeyType,
        operation_name: str,
        who_actor: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        why_reason: Optional[str] = None,
        context_data: Optional[Dict] = None,
        session: Optional[Session] = None
    ):
        """
        Context manager for tracking operations with Genesis Keys.

        Usage:
            with genesis.track_operation(
                GenesisKeyType.USER_INPUT,
                "file_upload",
                "user@example.com"
            ) as key:
                # Perform operation
                result = upload_file()
        """
        start_time = datetime.utcnow()
        key = None

        try:
            # Create initial key
            key = self.create_key(
                key_type=key_type,
                what_description=f"Started: {operation_name}",
                who_actor=who_actor,
                why_reason=why_reason,
                how_method="Automatic tracking",
                user_id=user_id,
                session_id=session_id,
                context_data=context_data or {},
                session=session
            )

            yield key

            # Update on success
            sess = session or self.session or next(get_session())
            key.what_description = f"Completed: {operation_name}"
            key.status = GenesisKeyStatus.ACTIVE
            duration = (datetime.utcnow() - start_time).total_seconds()
            key.output_data = {"duration_seconds": duration, "status": "success"}
            sess.commit()

        except Exception as e:
            # Update on error
            if key:
                sess = session or self.session or next(get_session())
                key.what_description = f"Failed: {operation_name}"
                key.status = GenesisKeyStatus.ERROR
                key.is_error = True
                key.error_type = type(e).__name__
                key.error_message = str(e)
                duration = (datetime.utcnow() - start_time).total_seconds()
                key.output_data = {"duration_seconds": duration, "status": "failed"}
                sess.commit()
            raise

    def create_fix_suggestion(
        self,
        genesis_key_id: str,
        suggestion_type: str,
        title: str,
        description: str,
        severity: str,
        fix_code: Optional[str] = None,
        fix_diff: Optional[str] = None,
        confidence: Optional[float] = None,
        metadata: Optional[Dict] = None,
        session: Optional[Session] = None
    ) -> FixSuggestion:
        """Create a fix suggestion for an error."""
        sess = session or self.session or next(get_session())
        close_session = session is None and self.session is None

        try:
            suggestion = FixSuggestion(
                suggestion_id=f"FS-{uuid.uuid4().hex[:16]}",
                genesis_key_id=genesis_key_id,
                suggestion_type=suggestion_type,
                title=title,
                description=description,
                severity=severity,
                fix_code=fix_code,
                fix_diff=fix_diff,
                confidence=confidence,
                metadata=metadata
            )

            sess.add(suggestion)

            # Update genesis key
            key = sess.query(GenesisKey).filter(GenesisKey.key_id == genesis_key_id).first()
            if key:
                key.has_fix_suggestion = True

            sess.commit()

            logger.info(f"Created fix suggestion: {suggestion.suggestion_id} for key {genesis_key_id}")
            return suggestion

        finally:
            if close_session:
                sess.close()

    def apply_fix(
        self,
        suggestion_id: str,
        applied_by: str,
        session: Optional[Session] = None
    ) -> GenesisKey:
        """Apply a fix suggestion and create a new Genesis Key for the fix."""
        sess = session or self.session or next(get_session())
        close_session = session is None and self.session is None

        try:
            # Get suggestion
            suggestion = sess.query(FixSuggestion).filter(
                FixSuggestion.suggestion_id == suggestion_id
            ).first()

            if not suggestion:
                raise ValueError(f"Fix suggestion not found: {suggestion_id}")

            # Get original key
            original_key = sess.query(GenesisKey).filter(
                GenesisKey.key_id == suggestion.genesis_key_id
            ).first()

            # Create fix key
            fix_key = self.create_key(
                key_type=GenesisKeyType.FIX,
                what_description=f"Applied fix: {suggestion.title}",
                who_actor=applied_by,
                why_reason=f"Fix for error: {original_key.error_message if original_key else 'Unknown'}",
                how_method="One-click fix suggestion",
                file_path=original_key.file_path if original_key else None,
                line_number=original_key.line_number if original_key else None,
                code_before=original_key.code_after if original_key else None,
                code_after=suggestion.fix_code,
                parent_key_id=original_key.key_id if original_key else None,
                session=sess
            )

            # Update suggestion
            suggestion.status = FixSuggestionStatus.APPLIED
            suggestion.applied_at = datetime.utcnow()
            suggestion.applied_by = applied_by
            suggestion.result_key_id = fix_key.key_id

            # Update original key
            if original_key:
                original_key.fix_applied = True
                original_key.fix_key_id = fix_key.key_id
                original_key.status = GenesisKeyStatus.FIXED

            sess.commit()

            logger.info(f"Applied fix: {suggestion_id}, created key: {fix_key.key_id}")
            return fix_key

        finally:
            if close_session:
                sess.close()

    def _generate_human_metadata(
        self,
        key_type: GenesisKeyType,
        what: str,
        where: Optional[str],
        when: datetime,
        why: Optional[str],
        who: str,
        how: Optional[str]
    ) -> str:
        """Generate human-readable metadata summary."""
        parts = [
            f"WHAT: {what}",
            f"WHO: {who}",
            f"WHEN: {when.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        ]

        if where:
            parts.append(f"WHERE: {where}")
        if why:
            parts.append(f"WHY: {why}")
        if how:
            parts.append(f"HOW: {how}")

        parts.append(f"TYPE: {key_type.value}")

        return "\n".join(parts)

    def _hash_data(self, data: Any) -> str:
        """Generate hash of data for comparison."""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def _update_user_stats(
        self,
        user_id: str,
        key_type: GenesisKeyType,
        is_error: bool,
        session: Session
    ):
        """Update user statistics."""
        try:
            user = session.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            if user:
                user.total_actions += 1
                user.last_seen = datetime.utcnow()

                if key_type == GenesisKeyType.CODE_CHANGE:
                    user.total_changes += 1
                if is_error:
                    user.total_errors += 1
                if key_type == GenesisKeyType.FIX:
                    user.total_fixes += 1

                # session.commit()  # Removed to prevent nested commit
        except Exception as e:
            logger.warning(f"Failed to update user stats: {e}")

    def get_keys_for_archival(
        self,
        before_date: datetime,
        session: Optional[Session] = None
    ) -> List[GenesisKey]:
        """Get keys ready for archival (older than specified date)."""
        sess = session or self.session or next(get_session())
        close_session = session is None and self.session is None

        try:
            keys = sess.query(GenesisKey).filter(
                GenesisKey.when_timestamp < before_date,
                GenesisKey.status != GenesisKeyStatus.ARCHIVED
            ).all()
            return keys
        finally:
            if close_session:
                sess.close()

    def rollback_to_key(
        self,
        key_id: str,
        rolled_back_by: str,
        session: Optional[Session] = None
    ) -> GenesisKey:
        """Rollback to a specific Genesis Key state."""
        sess = session or self.session or next(get_session())
        close_session = session is None and self.session is None

        try:
            # Get the key to rollback to
            target_key = sess.query(GenesisKey).filter(GenesisKey.key_id == key_id).first()

            if not target_key:
                raise ValueError(f"Genesis Key not found: {key_id}")

            # Create rollback key
            rollback_key = self.create_key(
                key_type=GenesisKeyType.ROLLBACK,
                what_description=f"Rolled back to: {target_key.what_description}",
                who_actor=rolled_back_by,
                why_reason=f"Rollback to state at {target_key.when_timestamp}",
                how_method="Version control rollback",
                file_path=target_key.file_path,
                code_after=target_key.code_before,  # Restore previous code
                parent_key_id=target_key.key_id,
                context_data={"rollback_to_key": key_id},
                session=sess
            )

            # Mark target key as rolled back
            target_key.status = GenesisKeyStatus.ROLLED_BACK

            # If we have git service and commit SHA, revert
            if self.git_service and target_key.commit_sha:
                try:
                    self.git_service.revert_to_commit(target_key.commit_sha)
                    logger.info(f"Reverted Git to commit: {target_key.commit_sha}")
                except Exception as e:
                    logger.warning(f"Git revert failed: {e}")

            sess.commit()

            logger.info(f"Rolled back to key: {key_id}")
            return rollback_key

        finally:
            if close_session:
                sess.close()


# Global Genesis Key service instance
_genesis_service: Optional[GenesisKeyService] = None


def get_genesis_service(session: Optional[Session] = None) -> GenesisKeyService:
    """Get or create the global Genesis Key service instance."""
    global _genesis_service
    if _genesis_service is None or session is not None:
        _genesis_service = GenesisKeyService(session=session)
    return _genesis_service
