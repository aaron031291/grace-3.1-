"""
Genesis Key Service - Comprehensive tracking and version control system.

Genesis keys are deterministic (hash-based) and never model-generated.
Key IDs: GK- from (key_type, what, who, where, why, how, timestamp, input_hash, parent_key_id);
GU- from identifier hash; FS- from genesis_key_id + suggestion content.
"""
import asyncio
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError

from models.genesis_key_models import (
    GenesisKey, FixSuggestion, GenesisKeyArchive, UserProfile,
    GenesisKeyType, GenesisKeyStatus, FixSuggestionStatus
)
from database.session import get_session, get_session_factory
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
        # Always deterministic: hash of identifier or fallback seed (no random, no model)
        seed = (identifier or "").strip() or "anonymous"
        return f"GU-{hashlib.sha256(seed.encode()).hexdigest()[:16]}"

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

            # Eagerly load all needed attributes before potentially closing session
            if close_session:
                sess.flush()
                # Expunge so the object is detached cleanly (not expired)
                from sqlalchemy.orm.session import make_transient
                sess.expunge(user)
                make_transient(user)

            return user
        except Exception as e:
            logger.error(f"Failed to create user profile: {e}")
            if close_session:
                sess.rollback()
            raise
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
        if session is not None:
            sess = session
            close_session = False
        elif self.session is not None:
            sess = self.session
            close_session = False
        else:
            try:
                sess = get_session_factory()()
            except RuntimeError:
                sess = next(get_session())
            close_session = True

        try:
            # Removed aggressive sess.expire_all() as it kills shared session objects.
            # Callers are responsible for their session state.
            
            # Key ID is always deterministic (hash of content). Genesis keys are never model-generated.
            when_ts = datetime.now(timezone.utc).isoformat()
            input_hash = self._hash_data(input_data) if input_data else ""
            payload = f"{key_type.value}|{what_description}|{who_actor}|{where_location or ''}|{why_reason or ''}|{how_method or ''}|{when_ts}|{input_hash}|{parent_key_id or ''}"
            key_id = "GK-" + hashlib.sha256(payload.encode()).hexdigest()[:32]


            # Get current commit info if available
            commit_sha = None
            branch_name = None
            if self.git_service and key_type != GenesisKeyType.API_REQUEST:
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
                when=datetime.now(timezone.utc),
                why=why_reason,
                who=who_actor,
                how=how_method
            )

            # Generate AI-readable metadata
            metadata_ai = {
                "key_type": key_type.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "commit_sha": commit_sha,
                "has_code_change": bool(code_before or code_after),
                "is_error": is_error,
                "input_hash": self._hash_data(input_data) if input_data else None,
                "output_hash": self._hash_data(output_data) if output_data else None,
                "tags": tags or []
            }

            # Create Genesis Key
            def _sqlite_json_safe(val):
                """Ensure value is JSON-serializable for SQLite JSON columns. Recursively replaces
                coroutines and other non-serializable values so insert never fails."""
                if val is None:
                    return None
                if asyncio.iscoroutine(val):
                    return "<coroutine not awaited>"
                if isinstance(val, dict):
                    return {str(k): _sqlite_json_safe(v) for k, v in val.items()}
                if isinstance(val, (list, tuple)):
                    return [_sqlite_json_safe(v) for v in val]
                if isinstance(val, (str, int, float, bool)):
                    return val
                try:
                    json.dumps(val, default=str)
                    return val
                except (TypeError, ValueError):
                    return str(val)

            key = GenesisKey(
                key_id=key_id,
                parent_key_id=parent_key_id,
                key_type=key_type,
                status=GenesisKeyStatus.ERROR if is_error else GenesisKeyStatus.ACTIVE,
                user_id=user_id,
                session_id=session_id,
                what_description=what_description,
                where_location=where_location,
                when_timestamp=datetime.now(timezone.utc),
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
                metadata_ai=_sqlite_json_safe(metadata_ai),
                input_data=_sqlite_json_safe(input_data),
                output_data=_sqlite_json_safe(output_data),
                context_data=_sqlite_json_safe(context_data),
                tags=_sqlite_json_safe(tags),
            )

            # Retry on SQLite "database is locked" / busy with SAVEPOINT isolation
            last_err = None
            for attempt in range(3):
                try:
                    # Use a nested transaction (SAVEPOINT) to isolate deterministic key collisions
                    # from the parent session's transaction state.
                    with sess.begin_nested():
                        # Use merge instead of add for deterministic keys to handle identity map safely
                        key = sess.merge(key)
                        sess.flush()
                    break
                except (IntegrityError, OperationalError, Exception) as e:
                    last_err = e
                    err_str = str(e).lower()
                    
                    # Handle Lock/Busy
                    if "locked" in err_str or "busy" in err_str or "timeout" in err_str:
                        if attempt < 2:
                            import time
                            time.sleep(0.3 * (attempt + 1))
                            # No need to rollback parent session, nested transaction already rolled back
                            continue
                    
                    # Handle Deterministic Key Collision (IntegrityError or Identity map warning)
                    if isinstance(e, IntegrityError) or "identity map already had an identity" in err_str or "unique constraint" in err_str:
                        # Key already exists, re-query to get the persistent instance
                        try:
                            # Re-query in the parent session
                            existing = sess.query(GenesisKey).filter(GenesisKey.key_id == key_id).first()
                            if existing:
                                key = existing
                                break
                        except Exception:
                            pass
                    
                    # If we don't handle it, re-raise
                    if attempt >= 2:
                        raise e
            else:
                if last_err:
                    raise last_err

            # CRITICAL: Extract all key data IMMEDIATELY after flush
            # This prevents DetachedInstanceError if session is rolled back later
            extracted_key_id = key.key_id
            extracted_key_data = {
                "key_id": key.key_id,
                "key_type": key.key_type.value if hasattr(key.key_type, 'value') else str(key.key_type),
                "what_description": key.what_description,
                "who_actor": key.who_actor,
                "where_location": key.where_location,
                "why_reason": key.why_reason,
                "how_method": key.how_method,
                "file_path": key.file_path,
                "user_id": key.user_id,
                "session_id": key.session_id,
                "is_error": key.is_error,
                "code_before": key.code_before,
                "code_after": key.code_after,
                "input_data": key.input_data,
                "output_data": key.output_data,
                "context_data": key.context_data,
                "tags": key.tags,
                "when_timestamp": key.when_timestamp.isoformat() if key.when_timestamp else None
            }
            
            # Only commit if we created our own session
            # If a session was passed in, let the caller handle commits
            if close_session:
                sess.commit()
                # Detach key from session to avoid DetachedInstanceError later
                try:
                    # Access key_id to ensure it's loaded if expired by commit
                    _ = key.key_id
                    sess.expunge(key)
                except Exception:
                    pass

            # Update user statistics if user_id provided (non-fatal)
            if user_id:
                try:
                    self._update_user_stats(user_id, key_type, is_error, sess)
                except Exception as us_err:
                    logger.debug("Genesis user stats update skipped: %s", us_err)

            # Post-creation hooks - use extracted data to prevent DetachedInstanceError
            # These hooks should NEVER cause the main Genesis Key creation to fail
            
            # Hook 1: Auto-populate to knowledge base
            try:
                import threading
                kb_integration = get_kb_integration()
                _kb_data = dict(extracted_key_data)
                def _save_kb():
                    try:
                        kb_integration.save_genesis_key(_kb_data)
                    except Exception:
                        pass
                threading.Thread(target=_save_kb, daemon=True).start()
            except Exception as kb_error:
                logger.warning("Failed to launch KB save thread: %s", kb_error)

            # Hook 2: Feed into Memory Mesh for learning
            # ONLY feed meaningful events — not system noise.
            # Meaningful = code changes, AI responses, errors, learning, user actions
            # Not meaningful = system_event, file_op (file watcher), api_request (every HTTP call)
            LEARNABLE_TYPES = {
                "AI_RESPONSE", "AI_CODE_GENERATION", "CODING_AGENT_ACTION",
                "ERROR", "FIX", "LEARNING_COMPLETE", "GAP_IDENTIFIED",
                "CODE_CHANGE", "USER_INPUT", "USER_UPLOAD",
            }

            key_type_str = extracted_key_data.get("key_type", "")
            should_learn = key_type_str in LEARNABLE_TYPES

            if should_learn:
                try:
                    import threading
                    _mesh_data = dict(extracted_key_data)

                    def _feed_mesh():
                        try:
                            from database.session import session_scope
                            from cognitive.memory_mesh_integration import MemoryMeshIntegration
                            from pathlib import Path

                            kb_path = Path(self.repo_path) / "backend" / "knowledge_base"

                            def _s(val):
                                if val is None: return json.dumps({})
                                if isinstance(val, str): return val
                                try: return json.dumps(val, default=str)
                                except Exception: return json.dumps({"raw": str(val)})

                            with session_scope() as mesh_sess:
                                mesh = MemoryMeshIntegration(session=mesh_sess, knowledge_base_path=kb_path)
                                mesh.ingest_learning_experience(
                                    experience_type=_mesh_data.get("key_type", "system"),
                                    context=_s({
                                        "what": _mesh_data.get("what_description") or "",
                                        "where": _mesh_data.get("where_location") or _mesh_data.get("file_path") or "",
                                        "why": _mesh_data.get("why_reason") or "",
                                        "how": _mesh_data.get("how_method") or "",
                                    }),
                                    action_taken=_s(_mesh_data.get("input_data")),
                                    outcome=_s(_mesh_data.get("output_data")),
                                    source="genesis_key",
                                    user_id=_mesh_data.get("user_id"),
                                    genesis_key_id=_mesh_data.get("key_id"),
                                )
                        except Exception as e:
                            logger.debug(f"Memory mesh feed skipped: {e}")

                    t = threading.Thread(target=_feed_mesh, daemon=True)
                    t.start()
                except Exception:
                    pass

            # Hook 3: Trigger autonomous pipeline (fire-and-forget, never blocks)
            try:
                from genesis.autonomous_triggers import get_genesis_trigger_pipeline
                trigger_pipeline = get_genesis_trigger_pipeline()
                trigger_result = trigger_pipeline.on_genesis_key_created_data(extracted_key_data)
                if trigger_result and trigger_result.get("triggered"):
                    logger.debug(f"Triggered autonomous actions from Genesis Key: {extracted_key_id}")
            except Exception:
                pass

            logger.info(f"Created Genesis Key: {extracted_key_id} - {what_description}")
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
                suggestion_id=f"FS-{hashlib.sha256((genesis_key_id + suggestion_type + (title or '') + (description or '')).encode()).hexdigest()[:16]}",
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
                user.last_seen = datetime.now(timezone.utc)  # Always set a fresh datetime

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


def get_genesis_service(session: Optional[Session] = None) -> GenesisKeyService:
    """Get a Genesis Key service instance."""
    # Never use global singleton for session-dependent services in multi-threaded environments
    return GenesisKeyService(session=session)


# Alias for code that imports get_genesis_key_service (e.g. MAGMA layer_integrations)
get_genesis_key_service = get_genesis_service
