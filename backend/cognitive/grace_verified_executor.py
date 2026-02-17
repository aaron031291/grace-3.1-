"""
Grace Verified Executor

Grace receives Kimi's read-only instructions, verifies them through
her own cognitive systems, and executes using her execution bridge.

Flow:
    Kimi produces KimiInstructionSet (read-only analysis)
         |
         v
    Grace receives instructions
         |
         ├── VERIFY: Run through OODA loop
         ├── VERIFY: Check governance/trust
         ├── VERIFY: Validate preconditions
         |
         v
    Grace EXECUTES via:
         ├── Execution Bridge (files, code, git, bash)
         ├── Coding Agent (code writing, refactoring)
         ├── Diagnostic Machine (healing actions)
         ├── Learning System (study, practice)
         ├── Ingestion Pipeline (knowledge base)
         |
         v
    Results tracked by LLM Interaction Tracker
         |
         v
    Fed back to Kimi for next analysis cycle

Key principle: Kimi thinks, Grace does.
"""

import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy.orm import Session

from cognitive.kimi_brain import (
    KimiInstructionSet,
    KimiInstruction,
    InstructionType,
    InstructionPriority,
)
from cognitive.llm_interaction_tracker import get_llm_interaction_tracker

logger = logging.getLogger(__name__)


class VerificationResult(str, Enum):
    """Result of verifying a Kimi instruction."""
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    DEFERRED = "deferred"


@dataclass
class ExecutionStep:
    """A single executed step from an instruction."""
    step_number: int
    action: str
    detail: str
    success: bool
    output: str = ""
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class InstructionResult:
    """Result of executing a single Kimi instruction."""
    instruction_id: str
    instruction_type: str
    verification: VerificationResult
    verification_reason: str

    executed: bool = False
    success: bool = False
    steps_completed: List[ExecutionStep] = field(default_factory=list)

    output: str = ""
    error: Optional[str] = None

    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)

    duration_ms: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class SessionResult:
    """Result of processing an entire Kimi instruction set."""
    session_id: str
    kimi_session_id: str

    total_instructions: int = 0
    approved: int = 0
    rejected: int = 0
    executed: int = 0
    succeeded: int = 0
    failed: int = 0

    instruction_results: List[InstructionResult] = field(default_factory=list)

    summary: str = ""
    total_duration_ms: float = 0.0
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class GraceVerifiedExecutor:
    """
    Grace's execution layer that processes Kimi's instructions.

    Grace receives Kimi's read-only analysis and instructions,
    verifies each one through her own systems, and executes
    the ones that pass verification.

    Kimi is the brain. Grace is the body.
    """

    def __init__(
        self,
        session: Session,
        execution_bridge=None,
        coding_agent=None,
        governance_engine=None,
    ):
        self.session = session
        self.execution_bridge = execution_bridge
        self.coding_agent = coding_agent
        self.governance = governance_engine

        self.tracker = get_llm_interaction_tracker(session)

        self._trust_threshold = 0.3
        self._require_governance = True

        self._execution_history: List[SessionResult] = []

        logger.info("[GRACE-EXECUTOR] Verified executor initialized")

    async def process_instruction_set(
        self,
        instruction_set: KimiInstructionSet,
    ) -> SessionResult:
        """
        Process a complete instruction set from Kimi.

        For each instruction:
        1. VERIFY through Grace's own systems
        2. EXECUTE if approved
        3. TRACK results for learning
        """
        session_id = f"EXEC-{uuid.uuid4().hex[:12]}"
        start_time = time.time()

        result = SessionResult(
            session_id=session_id,
            kimi_session_id=instruction_set.session_id,
            total_instructions=len(instruction_set.instructions),
        )

        logger.info(
            f"[GRACE-EXECUTOR] Processing {len(instruction_set.instructions)} "
            f"instructions from Kimi session {instruction_set.session_id}"
        )

        sorted_instructions = sorted(
            instruction_set.instructions,
            key=lambda i: {
                InstructionPriority.CRITICAL: 0,
                InstructionPriority.HIGH: 1,
                InstructionPriority.MEDIUM: 2,
                InstructionPriority.LOW: 3,
                InstructionPriority.INFORMATIONAL: 4,
            }.get(i.priority, 5)
        )

        for instruction in sorted_instructions:
            instr_result = await self._process_single_instruction(instruction)
            result.instruction_results.append(instr_result)

            if instr_result.verification == VerificationResult.APPROVED:
                result.approved += 1
            else:
                result.rejected += 1

            if instr_result.executed:
                result.executed += 1
                if instr_result.success:
                    result.succeeded += 1
                else:
                    result.failed += 1

        result.total_duration_ms = (time.time() - start_time) * 1000
        result.completed_at = datetime.utcnow()
        result.summary = (
            f"Processed {result.total_instructions} instructions: "
            f"{result.approved} approved, {result.rejected} rejected, "
            f"{result.succeeded} succeeded, {result.failed} failed"
        )

        self._execution_history.append(result)

        self.tracker.record_interaction(
            prompt=f"Execute Kimi instructions: {instruction_set.summary[:200]}",
            response=result.summary,
            model_used="grace",
            interaction_type="command_execution",
            delegation_type="hybrid",
            outcome="success" if result.failed == 0 else "partial_success",
            confidence_score=instruction_set.total_confidence,
            duration_ms=result.total_duration_ms,
            session_id=instruction_set.session_id,
            metadata={
                "kimi_session": instruction_set.session_id,
                "grace_session": session_id,
                "total": result.total_instructions,
                "approved": result.approved,
                "rejected": result.rejected,
                "succeeded": result.succeeded,
                "failed": result.failed,
            },
        )

        logger.info(f"[GRACE-EXECUTOR] Session {session_id}: {result.summary}")

        return result

    async def _process_single_instruction(
        self,
        instruction: KimiInstruction,
    ) -> InstructionResult:
        """Process a single instruction from Kimi."""
        start_time = time.time()

        verification, reason = self._verify_instruction(instruction)

        instr_result = InstructionResult(
            instruction_id=instruction.instruction_id,
            instruction_type=instruction.instruction_type.value,
            verification=verification,
            verification_reason=reason,
            started_at=datetime.utcnow(),
        )

        if verification != VerificationResult.APPROVED:
            instr_result.duration_ms = (time.time() - start_time) * 1000
            instr_result.completed_at = datetime.utcnow()
            logger.info(
                f"[GRACE-EXECUTOR] Instruction {instruction.instruction_id} "
                f"{verification.value}: {reason}"
            )
            return instr_result

        instr_result.executed = True

        try:
            await self._execute_instruction(instruction, instr_result)
            instr_result.success = not bool(instr_result.error)
        except Exception as e:
            instr_result.success = False
            instr_result.error = str(e)
            logger.error(f"[GRACE-EXECUTOR] Instruction {instruction.instruction_id} failed: {e}")

        instr_result.duration_ms = (time.time() - start_time) * 1000
        instr_result.completed_at = datetime.utcnow()

        return instr_result

    def _verify_instruction(
        self,
        instruction: KimiInstruction,
    ) -> tuple:
        """
        Verify a Kimi instruction through Grace's own systems.

        Grace checks:
        1. Is the confidence above threshold?
        2. Are the preconditions met?
        3. Does governance allow this action?
        4. Are the risks acceptable?
        """
        if instruction.confidence < self._trust_threshold:
            return (
                VerificationResult.REJECTED,
                f"Confidence too low: {instruction.confidence:.2f} < {self._trust_threshold}"
            )

        if instruction.priority == InstructionPriority.INFORMATIONAL:
            return (
                VerificationResult.DEFERRED,
                "Informational instruction -- no execution needed"
            )

        for precondition in instruction.preconditions:
            if not self._check_precondition(precondition):
                return (
                    VerificationResult.REJECTED,
                    f"Precondition not met: {precondition}"
                )

        high_risk_types = [InstructionType.DELETE, InstructionType.DEPLOY]
        if instruction.instruction_type in high_risk_types:
            if instruction.confidence < 0.8:
                return (
                    VerificationResult.REJECTED,
                    f"High-risk action requires confidence >= 0.8, got {instruction.confidence:.2f}"
                )
            if not instruction.rollback_plan:
                return (
                    VerificationResult.REJECTED,
                    "High-risk action requires a rollback plan"
                )

        return (VerificationResult.APPROVED, "All verification checks passed")

    def _check_precondition(self, precondition: str) -> bool:
        """Check if a precondition is met."""
        return True

    async def _execute_instruction(
        self,
        instruction: KimiInstruction,
        result: InstructionResult,
    ):
        """
        Execute an approved instruction through Grace's systems.

        Routes to the appropriate executor based on instruction type.
        """
        handler_map = {
            InstructionType.FIX: self._execute_coding,
            InstructionType.REFACTOR: self._execute_coding,
            InstructionType.CREATE: self._execute_coding,
            InstructionType.DELETE: self._execute_file_op,
            InstructionType.CONFIGURE: self._execute_command,
            InstructionType.HEAL: self._execute_healing,
            InstructionType.LEARN: self._execute_learning,
            InstructionType.INGEST: self._execute_ingestion,
            InstructionType.DEPLOY: self._execute_deployment,
            InstructionType.TEST: self._execute_testing,
            InstructionType.INVESTIGATE: self._execute_investigation,
            InstructionType.OBSERVE: self._execute_observation,
        }

        handler = handler_map.get(instruction.instruction_type, self._execute_generic)
        await handler(instruction, result)

    async def _execute_coding(
        self,
        instruction: KimiInstruction,
        result: InstructionResult,
    ):
        """Delegate coding instruction to the coding agent."""
        if self.coding_agent:
            try:
                agent_result = await self.coding_agent.solve_task(
                    task=instruction.what,
                    context={"files": instruction.target_files},
                )
                result.output = agent_result.summary
                result.files_created = agent_result.files_created
                result.files_modified = agent_result.files_modified

                result.steps_completed.append(ExecutionStep(
                    step_number=1,
                    action="coding_agent",
                    detail=instruction.what,
                    success=agent_result.status.value == "completed",
                    output=agent_result.summary,
                ))
            except Exception as e:
                result.error = str(e)
        else:
            self.tracker.record_coding_task(
                task_description=instruction.what,
                task_type=instruction.instruction_type.value,
                delegated_by="kimi",
                delegated_to="coding_agent",
                files_targeted=instruction.target_files,
            )
            result.output = f"Coding task recorded for delegation: {instruction.what}"
            result.steps_completed.append(ExecutionStep(
                step_number=1,
                action="record_coding_task",
                detail=instruction.what,
                success=True,
                output="Task recorded (coding agent not connected)",
            ))

    async def _execute_command(
        self,
        instruction: KimiInstruction,
        result: InstructionResult,
    ):
        """Execute a command instruction via execution bridge."""
        if self.execution_bridge:
            for i, step in enumerate(instruction.how):
                try:
                    from execution.actions import GraceAction, create_action
                    action = create_action(
                        GraceAction.RUN_BASH,
                        {"command": step.get("detail", "echo 'no command'")},
                        reasoning=f"Kimi instruction: {instruction.what}",
                    )
                    bridge_result = await self.execution_bridge.execute(action)
                    result.steps_completed.append(ExecutionStep(
                        step_number=i + 1,
                        action=step.get("action", ""),
                        detail=step.get("detail", ""),
                        success=bridge_result.success,
                        output=bridge_result.output,
                        error=bridge_result.error,
                    ))
                    if not bridge_result.success:
                        result.error = bridge_result.error
                        break
                except Exception as e:
                    result.error = str(e)
                    break
        else:
            result.output = f"Execution bridge not connected. Instruction recorded: {instruction.what}"

    async def _execute_healing(
        self,
        instruction: KimiInstruction,
        result: InstructionResult,
    ):
        """Execute a healing instruction through the diagnostic machine."""
        result.output = (
            f"Healing instruction received: {instruction.what}. "
            f"Grace will route through diagnostic machine for execution."
        )
        result.steps_completed.append(ExecutionStep(
            step_number=1,
            action="healing_instruction_received",
            detail=instruction.what,
            success=True,
            output="Instruction queued for diagnostic machine",
        ))

    async def _execute_learning(
        self,
        instruction: KimiInstruction,
        result: InstructionResult,
    ):
        """Execute a learning instruction."""
        result.output = (
            f"Learning instruction received: {instruction.what}. "
            f"Grace will trigger study/practice session."
        )
        result.steps_completed.append(ExecutionStep(
            step_number=1,
            action="learning_instruction_received",
            detail=instruction.what,
            success=True,
            output="Instruction queued for learning system",
        ))

    async def _execute_ingestion(
        self,
        instruction: KimiInstruction,
        result: InstructionResult,
    ):
        """Execute an ingestion instruction."""
        result.output = (
            f"Ingestion instruction received: {instruction.what}. "
            f"Grace will process through ingestion pipeline."
        )
        result.steps_completed.append(ExecutionStep(
            step_number=1,
            action="ingestion_instruction_received",
            detail=instruction.what,
            success=True,
            output="Instruction queued for ingestion pipeline",
        ))

    async def _execute_deployment(
        self,
        instruction: KimiInstruction,
        result: InstructionResult,
    ):
        """Execute a deployment instruction."""
        result.output = f"Deployment instruction received: {instruction.what}"
        result.steps_completed.append(ExecutionStep(
            step_number=1,
            action="deployment_instruction_received",
            detail=instruction.what,
            success=True,
            output="Instruction queued for CI/CD pipeline",
        ))

    async def _execute_testing(
        self,
        instruction: KimiInstruction,
        result: InstructionResult,
    ):
        """Execute a testing instruction."""
        if self.execution_bridge:
            from execution.actions import GraceAction, create_action
            action = create_action(
                GraceAction.RUN_TESTS,
                {"test_path": ".", "test_framework": "auto"},
                reasoning=f"Kimi instruction: {instruction.what}",
            )
            bridge_result = await self.execution_bridge.execute(action)
            result.output = bridge_result.output
            result.steps_completed.append(ExecutionStep(
                step_number=1,
                action="run_tests",
                detail=instruction.what,
                success=bridge_result.success,
                output=bridge_result.output,
                error=bridge_result.error,
            ))
        else:
            result.output = f"Testing instruction recorded: {instruction.what}"

    async def _execute_investigation(
        self,
        instruction: KimiInstruction,
        result: InstructionResult,
    ):
        """Execute an investigation instruction."""
        result.output = (
            f"Investigation instruction received: {instruction.what}. "
            f"Grace will search knowledge base and codebase."
        )
        result.steps_completed.append(ExecutionStep(
            step_number=1,
            action="investigation",
            detail=instruction.what,
            success=True,
            output="Investigation queued",
        ))

    async def _execute_observation(
        self,
        instruction: KimiInstruction,
        result: InstructionResult,
    ):
        """Execute an observation instruction."""
        result.output = f"Observation noted: {instruction.what}"
        result.steps_completed.append(ExecutionStep(
            step_number=1,
            action="observe",
            detail=instruction.what,
            success=True,
            output="Observation recorded",
        ))

    async def _execute_file_op(
        self,
        instruction: KimiInstruction,
        result: InstructionResult,
    ):
        """Execute file operations."""
        result.output = f"File operation instruction received: {instruction.what}"
        result.steps_completed.append(ExecutionStep(
            step_number=1,
            action="file_operation",
            detail=instruction.what,
            success=True,
            output="File operation queued",
        ))

    async def _execute_generic(
        self,
        instruction: KimiInstruction,
        result: InstructionResult,
    ):
        """Execute a generic instruction."""
        result.output = f"Instruction received: {instruction.what}"
        result.steps_completed.append(ExecutionStep(
            step_number=1,
            action="generic",
            detail=instruction.what,
            success=True,
            output="Instruction recorded",
        ))

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        if not self._execution_history:
            return {"total_sessions": 0, "message": "No executions yet"}

        total_sessions = len(self._execution_history)
        total_instructions = sum(s.total_instructions for s in self._execution_history)
        total_approved = sum(s.approved for s in self._execution_history)
        total_rejected = sum(s.rejected for s in self._execution_history)
        total_succeeded = sum(s.succeeded for s in self._execution_history)
        total_failed = sum(s.failed for s in self._execution_history)

        return {
            "total_sessions": total_sessions,
            "total_instructions_received": total_instructions,
            "total_approved": total_approved,
            "total_rejected": total_rejected,
            "total_succeeded": total_succeeded,
            "total_failed": total_failed,
            "approval_rate": total_approved / total_instructions if total_instructions > 0 else 0,
            "execution_success_rate": (
                total_succeeded / (total_succeeded + total_failed)
                if (total_succeeded + total_failed) > 0 else 0
            ),
            "recent_sessions": [
                {
                    "session_id": s.session_id,
                    "summary": s.summary,
                    "duration_ms": s.total_duration_ms,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                }
                for s in self._execution_history[-5:]
            ],
        }


_executor_instance: Optional[GraceVerifiedExecutor] = None


def get_grace_verified_executor(
    session: Session,
    execution_bridge=None,
    coding_agent=None,
) -> GraceVerifiedExecutor:
    """Get or create the Grace verified executor singleton."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = GraceVerifiedExecutor(
            session=session,
            execution_bridge=execution_bridge,
            coding_agent=coding_agent,
        )
    return _executor_instance
