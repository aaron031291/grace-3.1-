"""
Replay service for Grace's self-modeling mechanism.

Enables replaying failed or anomalous operations with the same inputs
to debug issues and compare results.
"""
import json
import hashlib
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from sqlalchemy.orm import Session

from models.telemetry_models import (
    OperationLog, OperationReplay, OperationStatus
)
from database.session import get_session

logger = logging.getLogger(__name__)


class ReplayService:
    """
    Service for replaying operations with stored inputs.

    This enables debugging of failures and performance regressions
    by rerunning the exact same operation.
    """

    def __init__(self, session: Optional[Session] = None):
        self.session = session

    def replay_operation(
        self,
        original_run_id: str,
        operation_func: Callable,
        reason: Optional[str] = None
    ) -> OperationReplay:
        """
        Replay an operation using its stored inputs.

        Args:
            original_run_id: Run ID of the operation to replay
            operation_func: Function to execute for replay
            reason: Why we're replaying (e.g., "debug_failure", "verify_fix")

        Returns:
            OperationReplay object with comparison results
        """
        session = self.session or next(get_session())
        close_session = self.session is None

        try:
            # Get original operation
            original_op = session.query(OperationLog).filter(
                OperationLog.run_id == original_run_id
            ).first()

            if not original_op:
                raise ValueError(f"Operation {original_run_id} not found")

            # Get stored inputs from metadata
            if not original_op.metadata or 'inputs' not in original_op.metadata:
                raise ValueError(
                    f"Operation {original_run_id} does not have stored inputs. "
                    "Cannot replay."
                )

            inputs = original_op.metadata['inputs']

            logger.info(
                f"Replaying operation: {original_op.operation_name} "
                f"(original run: {original_run_id})"
            )

            # Execute replay
            from telemetry.telemetry_service import get_telemetry_service
            telemetry = get_telemetry_service(session)

            with telemetry.track_operation(
                operation_type=original_op.operation_type,
                operation_name=f"replay_{original_op.operation_name}",
                parent_run_id=original_run_id,
                input_data=inputs,
                metadata={"replay": True, "reason": reason}
            ) as replay_run_id:
                # Call the operation function with stored inputs
                replay_result = operation_func(**inputs)

            # Get replay operation
            replay_op = session.query(OperationLog).filter(
                OperationLog.run_id == replay_run_id
            ).first()

            # Compare results
            outputs_match = self._compare_outputs(
                original_op.metadata.get('outputs'),
                replay_result
            )

            # Compute output hash
            replay_output_hash = None
            if replay_result is not None:
                output_str = json.dumps(replay_result, sort_keys=True, default=str)
                replay_output_hash = hashlib.sha256(output_str.encode()).hexdigest()

            # Create replay record
            replay_record = OperationReplay(
                original_run_id=original_run_id,
                replay_run_id=replay_run_id,
                replay_reason=reason or "manual_replay",
                original_duration_ms=original_op.duration_ms,
                replay_duration_ms=replay_op.duration_ms if replay_op else None,
                original_status=original_op.status.value,
                replay_status=replay_op.status.value if replay_op else "unknown",
                original_output_hash=original_op.metadata.get('output_hash'),
                replay_output_hash=replay_output_hash,
                outputs_match=outputs_match,
                differences=self._compute_differences(original_op, replay_op, replay_result),
                insights=self._generate_insights(original_op, replay_op)
            )

            session.add(replay_record)
            session.commit()

            logger.info(
                f"Replay complete. Status: {replay_record.replay_status}, "
                f"Outputs match: {outputs_match}"
            )

            return replay_record

        except Exception as e:
            logger.error(f"Replay failed: {e}")
            raise
        finally:
            if close_session:
                session.close()

    def get_replayable_failures(
        self,
        limit: int = 20,
        operation_type: Optional[str] = None
    ) -> list[OperationLog]:
        """
        Get recent failed operations that can be replayed.

        Args:
            limit: Maximum number of failures to return
            operation_type: Filter by operation type

        Returns:
            List of failed operations with stored inputs
        """
        session = self.session or next(get_session())
        close_session = self.session is None

        try:
            query = session.query(OperationLog).filter(
                OperationLog.status == OperationStatus.FAILED,
                OperationLog.metadata.isnot(None)
            )

            if operation_type:
                query = query.filter(OperationLog.operation_type == operation_type)

            failures = query.order_by(
                OperationLog.created_at.desc()
            ).limit(limit).all()

            # Filter to only those with inputs stored
            replayable = [
                f for f in failures
                if f.metadata and 'inputs' in f.metadata
            ]

            return replayable

        finally:
            if close_session:
                session.close()

    def _compare_outputs(self, original_output: Any, replay_output: Any) -> bool:
        """Compare original and replay outputs for equality."""
        try:
            original_str = json.dumps(original_output, sort_keys=True, default=str)
            replay_str = json.dumps(replay_output, sort_keys=True, default=str)
            return original_str == replay_str
        except:
            return False

    def _compute_differences(
        self,
        original_op: OperationLog,
        replay_op: Optional[OperationLog],
        replay_result: Any
    ) -> Dict[str, Any]:
        """Compute differences between original and replay."""
        differences = {}

        if replay_op:
            # Duration difference
            if original_op.duration_ms and replay_op.duration_ms:
                duration_diff_percent = (
                    (replay_op.duration_ms - original_op.duration_ms) /
                    original_op.duration_ms * 100
                )
                differences['duration_diff_percent'] = duration_diff_percent

            # Status change
            if original_op.status != replay_op.status:
                differences['status_changed'] = {
                    'original': original_op.status.value,
                    'replay': replay_op.status.value
                }

            # Resource usage changes
            if original_op.cpu_percent and replay_op.cpu_percent:
                differences['cpu_diff_percent'] = (
                    replay_op.cpu_percent - original_op.cpu_percent
                )

            if original_op.memory_mb and replay_op.memory_mb:
                differences['memory_diff_mb'] = (
                    replay_op.memory_mb - original_op.memory_mb
                )

        return differences

    def _generate_insights(
        self,
        original_op: OperationLog,
        replay_op: Optional[OperationLog]
    ) -> str:
        """Generate human-readable insights from replay comparison."""
        insights = []

        if not replay_op:
            return "Replay operation not found in database."

        # Status comparison
        if original_op.status == OperationStatus.FAILED:
            if replay_op.status == OperationStatus.COMPLETED:
                insights.append(
                    "✓ Issue appears to be resolved - replay succeeded where original failed."
                )
            else:
                insights.append(
                    "✗ Issue persists - replay also failed with same error pattern."
                )

        # Performance comparison
        if original_op.duration_ms and replay_op.duration_ms:
            diff_percent = (
                (replay_op.duration_ms - original_op.duration_ms) /
                original_op.duration_ms * 100
            )
            if abs(diff_percent) > 20:
                if diff_percent > 0:
                    insights.append(
                        f"⚠ Replay was {diff_percent:.1f}% slower - possible performance regression."
                    )
                else:
                    insights.append(
                        f"✓ Replay was {abs(diff_percent):.1f}% faster - performance improved."
                    )

        # Error pattern analysis
        if original_op.error_message and replay_op.error_message:
            if original_op.error_message == replay_op.error_message:
                insights.append(
                    "⚠ Identical error message - root cause likely unchanged."
                )
            else:
                insights.append(
                    "⚡ Different error message - error behavior has changed."
                )

        return "\n".join(insights) if insights else "No significant differences detected."


def get_replay_service(session: Optional[Session] = None) -> ReplayService:
    """Get replay service instance."""
    return ReplayService(session=session)
