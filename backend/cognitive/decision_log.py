"""
Decision Logger for Grace's Cognitive Engine.

Implements Invariant 6: Observability Is Mandatory.
All decisions are logged with full rationale and alternatives.
"""
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from .engine import DecisionContext


class DecisionLogger:
    """
    Logs all decisions with full context and rationale.

    Implements Invariant 6: If behavior cannot be inspected, it is invalid.
    """

    def __init__(self, log_dir: Optional[str] = None):
        """
        Initialize the decision logger.

        Args:
            log_dir: Directory to write decision logs (None = don't write files)
        """
        self.log_dir = Path(log_dir) if log_dir else None
        if self.log_dir:
            self.log_dir.mkdir(parents=True, exist_ok=True)

        self._log_entries: List[Dict[str, Any]] = []

    def log_decision_start(self, context: 'DecisionContext') -> None:
        """
        Log the start of a decision process.

        Args:
            context: Decision context
        """
        entry = {
            'event': 'decision_start',
            'decision_id': context.decision_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'problem_statement': context.problem_statement,
            'goal': context.goal,
            'success_criteria': context.success_criteria,
            'parent_decision_id': context.parent_decision_id,
        }

        self._log_entries.append(entry)
        self._write_log_entry(entry)

    def log_alternatives(
        self,
        decision_id: str,
        alternatives: List[Dict[str, Any]],
        selected: Dict[str, Any]
    ) -> None:
        """
        Log alternative paths considered and which was selected.

        Implements Invariant 12: Forward Simulation tracking.

        Args:
            decision_id: ID of the decision
            alternatives: List of all alternatives considered
            selected: The selected alternative
        """
        entry = {
            'event': 'alternatives_considered',
            'decision_id': decision_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'alternatives_count': len(alternatives),
            'alternatives': alternatives,
            'selected': selected,
        }

        self._log_entries.append(entry)
        self._write_log_entry(entry)

    def log_decision_complete(
        self,
        context: 'DecisionContext',
        result: Any
    ) -> None:
        """
        Log the completion of a decision.

        Args:
            context: Decision context
            result: Result of the action
        """
        entry = {
            'event': 'decision_complete',
            'decision_id': context.decision_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'duration_seconds': (
                datetime.now(timezone.utc) - context.created_at
            ).total_seconds(),
            'result_summary': str(result)[:500],  # Truncate long results
            'ambiguity_state': context.ambiguity_ledger.to_dict(),
            'impact_scope': context.impact_scope,
            'was_reversible': context.is_reversible,
            'complexity_score': context.complexity_score,
            'benefit_score': context.benefit_score,
        }

        self._log_entries.append(entry)
        self._write_log_entry(entry)

    def log_decision_finalized(self, context: 'DecisionContext') -> None:
        """
        Log finalization of a decision.

        Args:
            context: Decision context
        """
        entry = {
            'event': 'decision_finalized',
            'decision_id': context.decision_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }

        self._log_entries.append(entry)
        self._write_log_entry(entry)

    def log_decision_aborted(
        self,
        context: 'DecisionContext',
        reason: str
    ) -> None:
        """
        Log abortion of a decision.

        Args:
            context: Decision context
            reason: Reason for aborting
        """
        entry = {
            'event': 'decision_aborted',
            'decision_id': context.decision_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'reason': reason,
            'ambiguity_state': context.ambiguity_ledger.to_dict(),
        }

        self._log_entries.append(entry)
        self._write_log_entry(entry)

    def log_warning(self, decision_id: str, message: str) -> None:
        """
        Log a warning for a decision.

        Args:
            decision_id: ID of the decision
            message: Warning message
        """
        entry = {
            'event': 'warning',
            'decision_id': decision_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'message': message,
        }

        self._log_entries.append(entry)
        self._write_log_entry(entry)

    def log_invariant_violation(
        self,
        decision_id: str,
        invariant_number: int,
        violation: str
    ) -> None:
        """
        Log an invariant violation.

        Args:
            decision_id: ID of the decision
            invariant_number: Which invariant was violated
            violation: Description of the violation
        """
        entry = {
            'event': 'invariant_violation',
            'decision_id': decision_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'invariant_number': invariant_number,
            'violation': violation,
        }

        self._log_entries.append(entry)
        self._write_log_entry(entry)

    def get_decision_log(self, decision_id: str) -> List[Dict[str, Any]]:
        """
        Get all log entries for a specific decision.

        Args:
            decision_id: ID of the decision

        Returns:
            List of log entries
        """
        return [
            entry for entry in self._log_entries
            if entry.get('decision_id') == decision_id
        ]

    def get_all_logs(self) -> List[Dict[str, Any]]:
        """
        Get all log entries.

        Returns:
            List of all log entries
        """
        return self._log_entries.copy()

    def get_recent_decisions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent decisions with their metadata.

        Args:
            limit: Maximum number of decisions to return

        Returns:
            List of decision dictionaries with status and metadata
        """
        # Get all decision_start events
        decisions = []
        for entry in reversed(self._log_entries):
            if entry.get('event') == 'decision_start':
                decision_id = entry.get('decision_id')
                # Find the status of this decision
                status = 'in_progress'
                for e in self._log_entries:
                    if e.get('decision_id') == decision_id:
                        if e.get('event') == 'decision_complete':
                            status = 'completed'
                        elif e.get('event') == 'decision_aborted':
                            status = 'aborted'
                        elif e.get('event') == 'decision_finalized':
                            status = 'finalized'

                decisions.append({
                    'decision_id': decision_id,
                    'problem_statement': entry.get('problem_statement'),
                    'goal': entry.get('goal'),
                    'success_criteria': entry.get('success_criteria'),
                    'timestamp': entry.get('timestamp'),
                    'status': status
                })

                if len(decisions) >= limit:
                    break

        return decisions

    def get_active_decisions(self) -> List[Dict[str, Any]]:
        """
        Get currently active (non-completed) decisions.

        Returns:
            List of active decision dictionaries
        """
        all_decisions = self.get_recent_decisions(limit=100)
        return [d for d in all_decisions if d.get('status') == 'in_progress']

    def _write_log_entry(self, entry: Dict[str, Any]) -> None:
        """
        Write a log entry to file if log_dir is set.

        Args:
            entry: Log entry to write
        """
        if not self.log_dir:
            return

        # Write to daily log file
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
        log_file = self.log_dir / f"decisions_{date_str}.jsonl"

        with open(log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

        # Also write to decision-specific file
        if 'decision_id' in entry:
            decision_file = self.log_dir / f"{entry['decision_id']}.jsonl"
            with open(decision_file, 'a') as f:
                f.write(json.dumps(entry) + '\n')

    def generate_decision_report(self, decision_id: str) -> str:
        """
        Generate a human-readable report for a decision.

        Args:
            decision_id: ID of the decision

        Returns:
            Formatted report string
        """
        entries = self.get_decision_log(decision_id)

        if not entries:
            return f"No logs found for decision {decision_id}"

        report_lines = [
            f"Decision Report: {decision_id}",
            "=" * 60,
            ""
        ]

        for entry in entries:
            event = entry.get('event', 'unknown')
            timestamp = entry.get('timestamp', 'unknown')

            report_lines.append(f"[{timestamp}] {event.upper()}")

            if event == 'decision_start':
                report_lines.append(f"  Problem: {entry.get('problem_statement')}")
                report_lines.append(f"  Goal: {entry.get('goal')}")
                report_lines.append(f"  Success Criteria: {entry.get('success_criteria')}")

            elif event == 'alternatives_considered':
                report_lines.append(f"  Alternatives: {entry.get('alternatives_count')}")
                report_lines.append(f"  Selected: {entry.get('selected', {}).get('name', 'unknown')}")

            elif event == 'decision_complete':
                report_lines.append(f"  Duration: {entry.get('duration_seconds')}s")
                report_lines.append(f"  Impact: {entry.get('impact_scope')}")
                report_lines.append(f"  Reversible: {entry.get('was_reversible')}")

            elif event == 'warning':
                report_lines.append(f"  [WARN] {entry.get('message')}")

            elif event == 'invariant_violation':
                report_lines.append(
                    f"  [FAIL] Invariant {entry.get('invariant_number')}: "
                    f"{entry.get('violation')}"
                )

            report_lines.append("")

        return "\n".join(report_lines)
