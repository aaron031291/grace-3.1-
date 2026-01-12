"""
Grace Feedback Processor

Processes execution results and feeds them to Grace's learning systems.
This is the critical component that enables Grace to learn from doing.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from .actions import ActionRequest, ActionResult, ActionStatus, GraceAction

logger = logging.getLogger(__name__)


@dataclass
class LearningSignal:
    """A signal extracted from execution for learning."""

    signal_type: str  # success, failure, pattern, correction
    action_type: GraceAction
    context: Dict[str, Any]
    outcome: str
    confidence: float
    patterns: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_type": self.signal_type,
            "action_type": self.action_type.value,
            "context": self.context,
            "outcome": self.outcome,
            "confidence": self.confidence,
            "patterns": self.patterns,
            "created_at": self.created_at.isoformat(),
        }


class FeedbackProcessor:
    """
    Processes execution feedback and creates learning signals.

    Responsibilities:
    - Parse execution results
    - Extract learnable patterns
    - Update trust scores
    - Feed signals to memory mesh
    - Track success/failure patterns
    """

    def __init__(
        self,
        learning_memory=None,
        procedural_memory=None,
        trust_scorer=None,
        min_confidence_for_learning: float = 0.3,
    ):
        self.learning_memory = learning_memory
        self.procedural_memory = procedural_memory
        self.trust_scorer = trust_scorer
        self.min_confidence = min_confidence_for_learning

        # Statistics
        self.stats = {
            "total_processed": 0,
            "successes": 0,
            "failures": 0,
            "patterns_extracted": 0,
            "learning_signals_created": 0,
        }

    async def process(
        self,
        action: ActionRequest,
        result: ActionResult,
    ) -> List[LearningSignal]:
        """
        Process an action-result pair and extract learning signals.

        Returns list of learning signals for the memory system.
        """
        self.stats["total_processed"] += 1
        signals = []

        # Skip non-learnable actions
        if not result.learnable:
            return signals

        # Determine signal type based on result
        if result.success:
            self.stats["successes"] += 1
            signals.extend(await self._process_success(action, result))
        else:
            self.stats["failures"] += 1
            signals.extend(await self._process_failure(action, result))

        # Extract patterns regardless of success/failure
        patterns = await self._extract_patterns(action, result)
        if patterns:
            self.stats["patterns_extracted"] += len(patterns)
            signals.append(
                LearningSignal(
                    signal_type="pattern",
                    action_type=action.action_type,
                    context=action.parameters,
                    outcome="patterns_found",
                    confidence=action.confidence,
                    patterns=patterns,
                )
            )

        # Update trust score if scorer available
        if self.trust_scorer and result.trust_delta != 0:
            await self._update_trust(action, result)

        # Store in learning memory if available
        if self.learning_memory and signals:
            await self._store_learning_signals(signals)

        self.stats["learning_signals_created"] += len(signals)
        return signals

    async def _process_success(
        self,
        action: ActionRequest,
        result: ActionResult,
    ) -> List[LearningSignal]:
        """Process a successful action."""
        signals = []

        # Create success signal
        signal = LearningSignal(
            signal_type="success",
            action_type=action.action_type,
            context={
                "parameters": action.parameters,
                "reasoning": action.reasoning,
            },
            outcome=self._summarize_output(result.output),
            confidence=min(action.confidence + 0.1, 1.0),  # Boost confidence on success
        )
        signals.append(signal)

        # Special handling for test successes
        if action.action_type in [GraceAction.RUN_TESTS, GraceAction.RUN_PYTEST]:
            test_signal = await self._process_test_success(action, result)
            if test_signal:
                signals.append(test_signal)

        # Special handling for code execution
        if action.action_type in [GraceAction.RUN_PYTHON, GraceAction.RUN_BASH]:
            code_signal = await self._process_code_success(action, result)
            if code_signal:
                signals.append(code_signal)

        return signals

    async def _process_failure(
        self,
        action: ActionRequest,
        result: ActionResult,
    ) -> List[LearningSignal]:
        """Process a failed action."""
        signals = []

        # Analyze the error
        error_analysis = await self._analyze_error(result.error, result.output)

        signal = LearningSignal(
            signal_type="failure",
            action_type=action.action_type,
            context={
                "parameters": action.parameters,
                "reasoning": action.reasoning,
                "error_type": error_analysis.get("error_type"),
                "error_message": error_analysis.get("message"),
            },
            outcome=f"Failed: {error_analysis.get('summary', result.error)}",
            confidence=max(action.confidence - 0.1, 0.0),  # Lower confidence on failure
            patterns=error_analysis.get("patterns", []),
        )
        signals.append(signal)

        # Special handling for test failures - very valuable for learning
        if action.action_type in [GraceAction.RUN_TESTS, GraceAction.RUN_PYTEST]:
            test_signal = await self._process_test_failure(action, result)
            if test_signal:
                signals.append(test_signal)

        return signals

    async def _process_test_success(
        self,
        action: ActionRequest,
        result: ActionResult,
    ) -> Optional[LearningSignal]:
        """Extract learning from successful tests."""
        data = result.data
        passed = data.get("passed", 0)

        if passed > 0:
            return LearningSignal(
                signal_type="success",
                action_type=action.action_type,
                context={
                    "test_path": data.get("test_path"),
                    "framework": data.get("framework"),
                },
                outcome=f"Tests passed: {passed}",
                confidence=0.8,  # High confidence for passing tests
                patterns=[f"test_pass:{data.get('test_path')}"],
            )
        return None

    async def _process_test_failure(
        self,
        action: ActionRequest,
        result: ActionResult,
    ) -> Optional[LearningSignal]:
        """Extract learning from failed tests."""
        data = result.data
        failed = data.get("failed", 0)
        errors = data.get("errors", 0)

        # Parse test output for specific failures
        failure_patterns = self._parse_test_failures(result.output)

        return LearningSignal(
            signal_type="failure",
            action_type=action.action_type,
            context={
                "test_path": data.get("test_path"),
                "framework": data.get("framework"),
                "failed_count": failed,
                "error_count": errors,
            },
            outcome=f"Tests failed: {failed}, errors: {errors}",
            confidence=0.9,  # High confidence - we know this failed
            patterns=failure_patterns,
        )

    async def _process_code_success(
        self,
        action: ActionRequest,
        result: ActionResult,
    ) -> Optional[LearningSignal]:
        """Extract patterns from successful code execution."""
        code = action.parameters.get("code", "")

        # Extract useful patterns from the code
        patterns = []

        # Detect common patterns
        if "import " in code:
            patterns.append("uses_imports")
        if "def " in code:
            patterns.append("defines_function")
        if "class " in code:
            patterns.append("defines_class")
        if "try:" in code:
            patterns.append("uses_error_handling")
        if "async " in code:
            patterns.append("uses_async")

        if patterns:
            return LearningSignal(
                signal_type="pattern",
                action_type=action.action_type,
                context={"code_snippet": code[:500]},
                outcome="successful_execution",
                confidence=0.7,
                patterns=patterns,
            )
        return None

    async def _extract_patterns(
        self,
        action: ActionRequest,
        result: ActionResult,
    ) -> List[str]:
        """Extract reusable patterns from action-result pair."""
        patterns = []

        # Action type patterns
        patterns.append(f"action:{action.action_type.value}")

        # Success/failure patterns
        if result.success:
            patterns.append(f"success:{action.action_type.value}")
        else:
            patterns.append(f"failure:{action.action_type.value}")

        # File patterns
        if result.files_created:
            for f in result.files_created:
                ext = f.split('.')[-1] if '.' in f else 'unknown'
                patterns.append(f"created:{ext}")

        if result.files_modified:
            for f in result.files_modified:
                ext = f.split('.')[-1] if '.' in f else 'unknown'
                patterns.append(f"modified:{ext}")

        # Git patterns
        if action.action_type.value.startswith("git_"):
            patterns.append("git_operation")

        return patterns

    async def _analyze_error(
        self,
        error: Optional[str],
        output: str,
    ) -> Dict[str, Any]:
        """Analyze an error to extract useful information."""
        if not error and not output:
            return {"error_type": "unknown", "message": "No error details", "summary": "Unknown error"}

        text = error or output
        analysis = {
            "error_type": "unknown",
            "message": text[:500],
            "summary": text[:100],
            "patterns": [],
        }

        # Common Python errors
        if "SyntaxError" in text:
            analysis["error_type"] = "syntax_error"
            analysis["patterns"].append("python:syntax_error")
        elif "NameError" in text:
            analysis["error_type"] = "name_error"
            analysis["patterns"].append("python:name_error")
        elif "TypeError" in text:
            analysis["error_type"] = "type_error"
            analysis["patterns"].append("python:type_error")
        elif "ImportError" in text or "ModuleNotFoundError" in text:
            analysis["error_type"] = "import_error"
            analysis["patterns"].append("python:import_error")
        elif "FileNotFoundError" in text:
            analysis["error_type"] = "file_not_found"
            analysis["patterns"].append("io:file_not_found")
        elif "PermissionError" in text:
            analysis["error_type"] = "permission_error"
            analysis["patterns"].append("io:permission_error")
        elif "TimeoutError" in text or "timed out" in text.lower():
            analysis["error_type"] = "timeout"
            analysis["patterns"].append("execution:timeout")

        # Git errors
        if "fatal:" in text:
            analysis["error_type"] = "git_error"
            analysis["patterns"].append("git:fatal_error")
        elif "conflict" in text.lower():
            analysis["error_type"] = "git_conflict"
            analysis["patterns"].append("git:conflict")

        # Test errors
        if "FAILED" in text:
            analysis["patterns"].append("test:failed")
        if "AssertionError" in text:
            analysis["error_type"] = "assertion_error"
            analysis["patterns"].append("test:assertion_error")

        return analysis

    def _parse_test_failures(self, output: str) -> List[str]:
        """Parse test output to extract failure patterns."""
        patterns = []

        lines = output.splitlines()
        for line in lines:
            if "FAILED" in line:
                # Extract test name
                if "::" in line:
                    test_name = line.split("::")[1].split()[0] if "::" in line else None
                    if test_name:
                        patterns.append(f"failed_test:{test_name}")
            elif "AssertionError" in line:
                patterns.append("assertion_failure")
            elif "Error" in line and ":" in line:
                error_type = line.split(":")[0].strip().split()[-1]
                patterns.append(f"error:{error_type}")

        return patterns[:10]  # Limit patterns

    def _summarize_output(self, output: str, max_length: int = 200) -> str:
        """Create a brief summary of output."""
        if not output:
            return "No output"

        # Get first few meaningful lines
        lines = [l.strip() for l in output.splitlines() if l.strip()]
        summary = "\n".join(lines[:3])

        if len(summary) > max_length:
            summary = summary[:max_length] + "..."

        return summary

    async def _update_trust(self, action: ActionRequest, result: ActionResult):
        """Update trust score based on result."""
        if not self.trust_scorer:
            return

        try:
            # Trust scorer interface (implement based on your trust_scorer)
            await self.trust_scorer.update(
                context=action.action_type.value,
                delta=result.trust_delta,
                metadata={
                    "action_id": action.action_id,
                    "success": result.success,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to update trust: {e}")

    async def _store_learning_signals(self, signals: List[LearningSignal]):
        """Store learning signals in memory."""
        if not self.learning_memory:
            return

        for signal in signals:
            try:
                # Learning memory interface (implement based on your learning_memory)
                await self.learning_memory.record(
                    experience_type=signal.signal_type,
                    data=signal.to_dict(),
                    confidence=signal.confidence,
                )
            except Exception as e:
                logger.warning(f"Failed to store learning signal: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successes"] / self.stats["total_processed"]
                if self.stats["total_processed"] > 0
                else 0
            ),
        }


# Singleton instance
_processor_instance: Optional[FeedbackProcessor] = None


def get_feedback_processor(
    learning_memory=None,
    procedural_memory=None,
    trust_scorer=None,
) -> FeedbackProcessor:
    """Get or create the feedback processor singleton."""
    global _processor_instance
    if _processor_instance is None:
        _processor_instance = FeedbackProcessor(
            learning_memory=learning_memory,
            procedural_memory=procedural_memory,
            trust_scorer=trust_scorer,
        )
    return _processor_instance
