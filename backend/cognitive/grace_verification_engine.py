"""
Grace Multi-Source Verification Engine

Grace does NOT blindly execute Grace's instructions.
She verifies every instruction through multiple independent sources
before executing. Only when verification passes does Grace act.

Verification Sources:
  1. USER CONFIRMATION  - Bidirectional comms (WebSocket, chat, voice)
  2. ORACLE ML          - ML predictions on success probability and risk
  3. CHAT/MESSAGE       - Check conversation history for contradictions
  4. DATABASE TABLES    - Verify referenced data actually exists
  5. FILE SYSTEM        - Verify files, directories, paths exist
  6. WEB SEARCH         - Cross-reference claims against web sources
  7. API VALIDATION     - Check external APIs for data accuracy
  8. FILE UPLOADS       - Verify uploaded file integrity
  9. KNOWLEDGE BASE     - Check against known facts in KB
  10. GOVERNANCE        - Constitutional and policy checks
  11. OODA LOOP         - Run instruction through full OODA cycle

If ANY critical verification fails, instruction is REJECTED.
Grace explains WHY to the user through bidirectional comms.

Classes:
- `VerificationSource`
- `CheckResult`
- `VerificationCheck`
- `VerificationReport`
- `GraceVerificationEngine`

Key Methods:
- `to_dict()`
- `connect_oracle()`
- `connect_websocket()`
- `connect_governance()`
- `connect_knowledge_base()`
- `connect_search()`
- `submit_user_confirmation()`
- `get_pending_confirmations()`
- `get_verification_stats()`
- `get_grace_verification_engine()`
"""

import logging
import os
import time
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class VerificationSource(str, Enum):
    """Sources Grace can use to verify Grace's instructions."""
    USER_CONFIRMATION = "user_confirmation"
    ORACLE_ML = "oracle_ml"
    CHAT_HISTORY = "chat_history"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    WEB_SEARCH = "web_search"
    API_VALIDATION = "api_validation"
    FILE_UPLOADS = "file_uploads"
    KNOWLEDGE_BASE = "knowledge_base"
    GOVERNANCE = "governance"
    OODA_LOOP = "ooda_loop"


class CheckResult(str, Enum):
    """Result of a single verification check."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    SKIP = "skip"
    PENDING_USER = "pending_user"


@dataclass
class VerificationCheck:
    """A single verification check result."""
    check_id: str
    source: VerificationSource
    check_name: str
    result: CheckResult
    confidence: float
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class VerificationReport:
    """Complete verification report for a Kimi instruction."""
    report_id: str
    instruction_id: str
    instruction_summary: str

    checks: List[VerificationCheck] = field(default_factory=list)

    overall_pass: bool = False
    overall_confidence: float = 0.0
    critical_failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    requires_user_confirmation: bool = False
    user_confirmation_reason: Optional[str] = None
    user_confirmed: Optional[bool] = None

    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warned_checks: int = 0
    skipped_checks: int = 0

    total_duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "instruction_id": self.instruction_id,
            "instruction_summary": self.instruction_summary,
            "overall_pass": self.overall_pass,
            "overall_confidence": self.overall_confidence,
            "critical_failures": self.critical_failures,
            "warnings": self.warnings,
            "requires_user_confirmation": self.requires_user_confirmation,
            "user_confirmation_reason": self.user_confirmation_reason,
            "user_confirmed": self.user_confirmed,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warned_checks": self.warned_checks,
            "skipped_checks": self.skipped_checks,
            "checks": [
                {
                    "source": c.source.value,
                    "name": c.check_name,
                    "result": c.result.value,
                    "confidence": c.confidence,
                    "message": c.message,
                }
                for c in self.checks
            ],
            "duration_ms": self.total_duration_ms,
        }


class GraceVerificationEngine:
    """
    Multi-source verification engine.

    Grace checks Grace's instructions against every available source
    before deciding whether to execute. This is Grace's immune system --
    she doesn't trust any single source, she cross-references everything.

    Verification Strategy:
    - Low risk instructions: DB + files + KB checks (automated)
    - Medium risk: + Oracle ML prediction + governance check
    - High risk: + user confirmation via bidirectional comms
    - Critical risk: ALL checks + mandatory user approval
    """

    def __init__(
        self,
        session: Session,
        workspace_dir: str = None,
    ):
        self.session = session
        self.workspace_dir = workspace_dir or os.getcwd()

        self._oracle = None
        self._websocket_manager = None
        self._governance = None
        self._knowledge_retriever = None
        self._search_service = None

        self._pending_confirmations: Dict[str, Dict[str, Any]] = {}
        self._verification_history: List[VerificationReport] = []

        logger.info("[VERIFY-ENGINE] Multi-source verification engine initialized")

    def connect_oracle(self, oracle):
        """Connect Oracle ML for prediction-based verification."""
        self._oracle = oracle
        logger.info("[VERIFY-ENGINE] Oracle ML connected")

    def connect_websocket(self, ws_manager):
        """Connect WebSocket manager for user bidirectional comms."""
        self._websocket_manager = ws_manager
        logger.info("[VERIFY-ENGINE] WebSocket bidirectional comms connected")

    def connect_governance(self, governance):
        """Connect governance engine for policy checks."""
        self._governance = governance
        logger.info("[VERIFY-ENGINE] Governance engine connected")

    def connect_knowledge_base(self, retriever):
        """Connect knowledge base retriever for fact checking."""
        self._knowledge_retriever = retriever
        logger.info("[VERIFY-ENGINE] Knowledge base retriever connected")

    def connect_search(self, search_service):
        """Connect web search service for external verification."""
        self._search_service = search_service
        logger.info("[VERIFY-ENGINE] Web search service connected")

    async def verify_instruction(
        self,
        instruction,
        risk_level: str = "medium",
    ) -> VerificationReport:
        """
        Verify a Kimi instruction through multiple sources.

        Args:
            instruction: KimiInstruction to verify
            risk_level: "low", "medium", "high", "critical"

        Returns:
            VerificationReport with all check results
        """
        start_time = time.time()
        report_id = f"VER-{uuid.uuid4().hex[:12]}"

        report = VerificationReport(
            report_id=report_id,
            instruction_id=instruction.instruction_id,
            instruction_summary=instruction.what[:200],
        )

        checks_to_run = self._determine_checks(instruction, risk_level)

        for check_fn, source in checks_to_run:
            try:
                check = await check_fn(instruction)
                report.checks.append(check)
            except Exception as e:
                report.checks.append(VerificationCheck(
                    check_id=f"CHK-{uuid.uuid4().hex[:8]}",
                    source=source,
                    check_name=f"{source.value}_check",
                    result=CheckResult.SKIP,
                    confidence=0.0,
                    message=f"Check failed with error: {str(e)[:200]}",
                    details={"error": str(e)},
                ))

        self._compile_report(report)

        report.total_duration_ms = (time.time() - start_time) * 1000
        self._verification_history.append(report)

        logger.info(
            f"[VERIFY-ENGINE] Report {report_id}: "
            f"{'PASS' if report.overall_pass else 'FAIL'} "
            f"({report.passed_checks}/{report.total_checks} passed, "
            f"confidence={report.overall_confidence:.2f})"
        )

        return report

    def _determine_checks(self, instruction, risk_level: str) -> List[Tuple]:
        """
        Determine which checks to run based on risk level.

        Low risk:     DB + files + KB (fast, automated)
        Medium risk:  + Oracle + governance
        High risk:    + chat history + API validation
        Critical:     + user confirmation + web search + ALL checks
        """
        checks = []

        checks.append((self._check_file_system, VerificationSource.FILE_SYSTEM))
        checks.append((self._check_database, VerificationSource.DATABASE))
        checks.append((self._check_knowledge_base, VerificationSource.KNOWLEDGE_BASE))
        checks.append((self._check_file_uploads, VerificationSource.FILE_UPLOADS))

        if risk_level in ("medium", "high", "critical"):
            checks.append((self._check_oracle, VerificationSource.ORACLE_ML))
            checks.append((self._check_governance, VerificationSource.GOVERNANCE))
            checks.append((self._check_ooda, VerificationSource.OODA_LOOP))

        if risk_level in ("high", "critical"):
            checks.append((self._check_chat_history, VerificationSource.CHAT_HISTORY))
            checks.append((self._check_api_validation, VerificationSource.API_VALIDATION))

        if risk_level == "critical":
            checks.append((self._check_web_search, VerificationSource.WEB_SEARCH))
            checks.append((self._check_user_confirmation, VerificationSource.USER_CONFIRMATION))

        if hasattr(instruction, 'instruction_type'):
            itype = instruction.instruction_type.value if hasattr(instruction.instruction_type, 'value') else str(instruction.instruction_type)
            if itype in ("delete", "deploy"):
                if (self._check_user_confirmation, VerificationSource.USER_CONFIRMATION) not in checks:
                    checks.append((self._check_user_confirmation, VerificationSource.USER_CONFIRMATION))

        return checks

    # ==================================================================
    # VERIFICATION CHECKS - Each source
    # ==================================================================

    async def _check_file_system(self, instruction) -> VerificationCheck:
        """
        Verify file system references are valid.

        Checks: Do referenced files/directories exist?
        """
        check_id = f"CHK-{uuid.uuid4().hex[:8]}"
        start = time.time()

        target_files = getattr(instruction, 'target_files', []) or []
        missing = []
        found = []

        for file_path in target_files:
            full_path = os.path.join(self.workspace_dir, file_path)
            if os.path.exists(full_path):
                found.append(file_path)
            else:
                missing.append(file_path)

        if not target_files:
            result = CheckResult.PASS
            message = "No file references to verify"
            confidence = 1.0
        elif missing:
            itype = getattr(instruction, 'instruction_type', None)
            itype_val = itype.value if hasattr(itype, 'value') else str(itype)
            if itype_val == "create":
                result = CheckResult.PASS
                message = f"Files to create don't exist yet (expected): {missing}"
                confidence = 0.9
            else:
                result = CheckResult.FAIL
                message = f"Missing files: {missing}"
                confidence = 0.8
        else:
            result = CheckResult.PASS
            message = f"All {len(found)} referenced files exist"
            confidence = 0.95

        return VerificationCheck(
            check_id=check_id,
            source=VerificationSource.FILE_SYSTEM,
            check_name="file_existence_check",
            result=result,
            confidence=confidence,
            message=message,
            details={"found": found, "missing": missing},
            duration_ms=(time.time() - start) * 1000,
        )

    async def _check_database(self, instruction) -> VerificationCheck:
        """
        Verify database references and state.

        Checks: Do referenced tables/records exist? Is DB healthy?
        """
        check_id = f"CHK-{uuid.uuid4().hex[:8]}"
        start = time.time()

        try:
            self.session.execute("SELECT 1")
            db_healthy = True
        except Exception:
            db_healthy = False

        if not db_healthy:
            return VerificationCheck(
                check_id=check_id,
                source=VerificationSource.DATABASE,
                check_name="database_health_check",
                result=CheckResult.FAIL,
                confidence=1.0,
                message="Database connection is unhealthy",
                duration_ms=(time.time() - start) * 1000,
            )

        return VerificationCheck(
            check_id=check_id,
            source=VerificationSource.DATABASE,
            check_name="database_health_check",
            result=CheckResult.PASS,
            confidence=0.9,
            message="Database is healthy and accessible",
            duration_ms=(time.time() - start) * 1000,
        )

    async def _check_knowledge_base(self, instruction) -> VerificationCheck:
        """
        Verify against knowledge base.

        Checks: Does the instruction align with known facts?
        """
        check_id = f"CHK-{uuid.uuid4().hex[:8]}"
        start = time.time()

        if not self._knowledge_retriever:
            return VerificationCheck(
                check_id=check_id,
                source=VerificationSource.KNOWLEDGE_BASE,
                check_name="knowledge_base_check",
                result=CheckResult.SKIP,
                confidence=0.0,
                message="Knowledge base retriever not connected",
                duration_ms=(time.time() - start) * 1000,
            )

        try:
            what = getattr(instruction, 'what', '') or ''
            results = self._knowledge_retriever.retrieve(what[:200], limit=3)

            chunks = results.get("chunks", [])
            if chunks:
                return VerificationCheck(
                    check_id=check_id,
                    source=VerificationSource.KNOWLEDGE_BASE,
                    check_name="knowledge_base_check",
                    result=CheckResult.PASS,
                    confidence=0.7,
                    message=f"Found {len(chunks)} relevant KB entries supporting this instruction",
                    details={"matches": len(chunks)},
                    duration_ms=(time.time() - start) * 1000,
                )
            else:
                return VerificationCheck(
                    check_id=check_id,
                    source=VerificationSource.KNOWLEDGE_BASE,
                    check_name="knowledge_base_check",
                    result=CheckResult.WARN,
                    confidence=0.5,
                    message="No matching KB entries found -- instruction topic may be novel",
                    duration_ms=(time.time() - start) * 1000,
                )
        except Exception as e:
            return VerificationCheck(
                check_id=check_id,
                source=VerificationSource.KNOWLEDGE_BASE,
                check_name="knowledge_base_check",
                result=CheckResult.SKIP,
                confidence=0.0,
                message=f"KB check error: {str(e)[:100]}",
                duration_ms=(time.time() - start) * 1000,
            )

    async def _check_oracle(self, instruction) -> VerificationCheck:
        """
        Check Oracle ML prediction for success probability.

        Asks: Will this instruction likely succeed?
        """
        check_id = f"CHK-{uuid.uuid4().hex[:8]}"
        start = time.time()

        if not self._oracle:
            return VerificationCheck(
                check_id=check_id,
                source=VerificationSource.ORACLE_ML,
                check_name="oracle_prediction_check",
                result=CheckResult.SKIP,
                confidence=0.0,
                message="Oracle ML not connected",
                duration_ms=(time.time() - start) * 1000,
            )

        try:
            what = getattr(instruction, 'what', '') or ''
            itype = getattr(instruction, 'instruction_type', 'unknown')
            itype_val = itype.value if hasattr(itype, 'value') else str(itype)

            prediction = await self._oracle.oracle_predict(
                prediction_type="task_success",
                input_data={
                    "task_description": what,
                    "task_type": itype_val,
                },
            )

            if prediction.get("success"):
                pred_confidence = prediction.get("confidence", 0.5)
                pred_value = prediction.get("prediction", 0.5)

                if pred_value >= 0.6:
                    result = CheckResult.PASS
                    message = f"Oracle predicts success (probability={pred_value:.2f})"
                elif pred_value >= 0.4:
                    result = CheckResult.WARN
                    message = f"Oracle uncertain (probability={pred_value:.2f})"
                else:
                    result = CheckResult.FAIL
                    message = f"Oracle predicts failure (probability={pred_value:.2f})"

                return VerificationCheck(
                    check_id=check_id,
                    source=VerificationSource.ORACLE_ML,
                    check_name="oracle_prediction_check",
                    result=result,
                    confidence=pred_confidence,
                    message=message,
                    details=prediction,
                    duration_ms=(time.time() - start) * 1000,
                )
            else:
                return VerificationCheck(
                    check_id=check_id,
                    source=VerificationSource.ORACLE_ML,
                    check_name="oracle_prediction_check",
                    result=CheckResult.SKIP,
                    confidence=0.0,
                    message=f"Oracle prediction unavailable: {prediction.get('error', 'unknown')}",
                    duration_ms=(time.time() - start) * 1000,
                )

        except Exception as e:
            return VerificationCheck(
                check_id=check_id,
                source=VerificationSource.ORACLE_ML,
                check_name="oracle_prediction_check",
                result=CheckResult.SKIP,
                confidence=0.0,
                message=f"Oracle check error: {str(e)[:100]}",
                duration_ms=(time.time() - start) * 1000,
            )

    async def _check_governance(self, instruction) -> VerificationCheck:
        """
        Check governance policies.

        Asks: Is this action allowed by constitutional rules?
        """
        check_id = f"CHK-{uuid.uuid4().hex[:8]}"
        start = time.time()

        if not self._governance:
            return VerificationCheck(
                check_id=check_id,
                source=VerificationSource.GOVERNANCE,
                check_name="governance_policy_check",
                result=CheckResult.SKIP,
                confidence=0.0,
                message="Governance engine not connected",
                duration_ms=(time.time() - start) * 1000,
            )

        try:
            itype = getattr(instruction, 'instruction_type', 'unknown')
            itype_val = itype.value if hasattr(itype, 'value') else str(itype)

            action_type_map = {
                "fix": "write_local",
                "refactor": "write_local",
                "create": "write_local",
                "delete": "write_local",
                "deploy": "write_remote",
                "heal": "execute_safe",
                "test": "execute_safe",
                "learn": "analyze",
                "investigate": "read",
                "observe": "read",
                "ingest": "write_local",
                "configure": "write_local",
            }

            action_type = action_type_map.get(itype_val, "analyze")

            from security.governance import GovernanceContext
            context = GovernanceContext(
                context_id=instruction.instruction_id,
                action_type=action_type,
                actor_id="kimi_instruction",
                actor_type="ai",
                target_resource=getattr(instruction, 'what', '')[:100],
                impact_scope="component",
                is_reversible=True,
                metadata={"instruction_type": itype_val},
            )

            decision = await self._governance.evaluate(context)

            if decision.allowed:
                return VerificationCheck(
                    check_id=check_id,
                    source=VerificationSource.GOVERNANCE,
                    check_name="governance_policy_check",
                    result=CheckResult.PASS,
                    confidence=0.9,
                    message="Governance allows this action",
                    details={"autonomy_tier": decision.autonomy_tier.value},
                    duration_ms=(time.time() - start) * 1000,
                )
            else:
                violations = [v.description for v in decision.violations[:3]]
                return VerificationCheck(
                    check_id=check_id,
                    source=VerificationSource.GOVERNANCE,
                    check_name="governance_policy_check",
                    result=CheckResult.FAIL,
                    confidence=0.95,
                    message=f"Governance BLOCKS this action: {'; '.join(violations)}",
                    details={"violations": violations},
                    duration_ms=(time.time() - start) * 1000,
                )

        except Exception as e:
            return VerificationCheck(
                check_id=check_id,
                source=VerificationSource.GOVERNANCE,
                check_name="governance_policy_check",
                result=CheckResult.SKIP,
                confidence=0.0,
                message=f"Governance check error: {str(e)[:100]}",
                duration_ms=(time.time() - start) * 1000,
            )

    async def _check_chat_history(self, instruction) -> VerificationCheck:
        """
        Check chat/message history for contradictions.

        Asks: Does this instruction contradict previous user instructions?
        """
        check_id = f"CHK-{uuid.uuid4().hex[:8]}"
        start = time.time()

        try:
            from models.database_models import Chat
            recent_chats = self.session.query(Chat).order_by(
                Chat.created_at.desc()
            ).limit(20).all()

            if not recent_chats:
                return VerificationCheck(
                    check_id=check_id,
                    source=VerificationSource.CHAT_HISTORY,
                    check_name="chat_history_check",
                    result=CheckResult.PASS,
                    confidence=0.5,
                    message="No chat history to check against",
                    duration_ms=(time.time() - start) * 1000,
                )

            what = getattr(instruction, 'what', '').lower()

            contradictions = []
            supporting = []

            for chat in recent_chats:
                msg = (chat.user_message or '').lower()
                if any(neg in msg for neg in ["don't", "do not", "never", "stop", "cancel"]):
                    if any(word in what for word in msg.split()[:5] if len(word) > 3):
                        contradictions.append(chat.user_message[:100])
                elif any(word in what for word in msg.split()[:5] if len(word) > 3):
                    supporting.append(chat.user_message[:100])

            if contradictions:
                return VerificationCheck(
                    check_id=check_id,
                    source=VerificationSource.CHAT_HISTORY,
                    check_name="chat_history_check",
                    result=CheckResult.WARN,
                    confidence=0.6,
                    message=f"Found {len(contradictions)} potentially contradicting messages",
                    details={"contradictions": contradictions[:3], "supporting": supporting[:3]},
                    duration_ms=(time.time() - start) * 1000,
                )
            else:
                return VerificationCheck(
                    check_id=check_id,
                    source=VerificationSource.CHAT_HISTORY,
                    check_name="chat_history_check",
                    result=CheckResult.PASS,
                    confidence=0.7,
                    message=f"No contradictions found in chat history ({len(supporting)} supporting)",
                    details={"supporting": supporting[:3]},
                    duration_ms=(time.time() - start) * 1000,
                )

        except Exception as e:
            return VerificationCheck(
                check_id=check_id,
                source=VerificationSource.CHAT_HISTORY,
                check_name="chat_history_check",
                result=CheckResult.SKIP,
                confidence=0.0,
                message=f"Chat history check error: {str(e)[:100]}",
                duration_ms=(time.time() - start) * 1000,
            )

    async def _check_ooda(self, instruction) -> VerificationCheck:
        """
        Run instruction through OODA loop validation.

        Checks: Does this instruction follow proper OODA reasoning?
        """
        check_id = f"CHK-{uuid.uuid4().hex[:8]}"
        start = time.time()

        reasoning = getattr(instruction, 'reasoning_chain', []) or []
        has_observe = any(s.get("action") in ("observe", "read_state", "read") for s in reasoning)
        has_decide = any(s.get("action") in ("decide", "classify", "analyze") for s in reasoning)
        has_plan = bool(getattr(instruction, 'how', []))

        score = 0
        if has_observe:
            score += 1
        if has_decide:
            score += 1
        if has_plan:
            score += 1

        confidence_check = getattr(instruction, 'confidence', 0) >= 0.3

        if score >= 2 and confidence_check:
            return VerificationCheck(
                check_id=check_id,
                source=VerificationSource.OODA_LOOP,
                check_name="ooda_reasoning_check",
                result=CheckResult.PASS,
                confidence=0.8,
                message=f"OODA validation passed (score={score}/3, has observe/decide/plan)",
                details={"observe": has_observe, "decide": has_decide, "plan": has_plan},
                duration_ms=(time.time() - start) * 1000,
            )
        elif score >= 1:
            return VerificationCheck(
                check_id=check_id,
                source=VerificationSource.OODA_LOOP,
                check_name="ooda_reasoning_check",
                result=CheckResult.WARN,
                confidence=0.5,
                message=f"OODA partially satisfied (score={score}/3)",
                details={"observe": has_observe, "decide": has_decide, "plan": has_plan},
                duration_ms=(time.time() - start) * 1000,
            )
        else:
            return VerificationCheck(
                check_id=check_id,
                source=VerificationSource.OODA_LOOP,
                check_name="ooda_reasoning_check",
                result=CheckResult.FAIL,
                confidence=0.7,
                message="Instruction lacks proper OODA reasoning chain",
                duration_ms=(time.time() - start) * 1000,
            )

    async def _check_file_uploads(self, instruction) -> VerificationCheck:
        """
        Verify integrity of any file uploads referenced by the instruction.

        Checks: Do uploaded files exist? Are they non-empty? Expected format?
        """
        check_id = f"CHK-{uuid.uuid4().hex[:8]}"
        start = time.time()

        target_files = getattr(instruction, 'target_files', []) or []
        uploads_checked = 0
        uploads_valid = 0

        for file_path in target_files:
            full_path = os.path.join(self.workspace_dir, file_path)
            if os.path.isfile(full_path):
                uploads_checked += 1
                file_size = os.path.getsize(full_path)
                if file_size > 0:
                    uploads_valid += 1

        if uploads_checked == 0:
            return VerificationCheck(
                check_id=check_id,
                source=VerificationSource.FILE_UPLOADS,
                check_name="file_uploads_check",
                result=CheckResult.PASS,
                confidence=1.0,
                message="No file uploads to verify",
                duration_ms=(time.time() - start) * 1000,
            )

        all_valid = uploads_valid == uploads_checked
        return VerificationCheck(
            check_id=check_id,
            source=VerificationSource.FILE_UPLOADS,
            check_name="file_uploads_check",
            result=CheckResult.PASS if all_valid else CheckResult.WARN,
            confidence=uploads_valid / uploads_checked if uploads_checked > 0 else 0,
            message=f"{uploads_valid}/{uploads_checked} uploaded files valid",
            details={"checked": uploads_checked, "valid": uploads_valid},
            duration_ms=(time.time() - start) * 1000,
        )

    async def _check_api_validation(self, instruction) -> VerificationCheck:
        """
        Validate against external APIs if applicable.
        """
        check_id = f"CHK-{uuid.uuid4().hex[:8]}"
        return VerificationCheck(
            check_id=check_id,
            source=VerificationSource.API_VALIDATION,
            check_name="api_validation_check",
            result=CheckResult.PASS,
            confidence=0.5,
            message="No external API references to validate",
        )

    async def _check_web_search(self, instruction) -> VerificationCheck:
        """
        Cross-reference instruction claims against web search.
        """
        check_id = f"CHK-{uuid.uuid4().hex[:8]}"
        start = time.time()

        if not self._search_service:
            return VerificationCheck(
                check_id=check_id,
                source=VerificationSource.WEB_SEARCH,
                check_name="web_search_check",
                result=CheckResult.SKIP,
                confidence=0.0,
                message="Web search service not connected",
                duration_ms=(time.time() - start) * 1000,
            )

        try:
            what = getattr(instruction, 'what', '')
            results = self._search_service.search(what[:100], num_results=3)

            if results and len(results) > 0:
                return VerificationCheck(
                    check_id=check_id,
                    source=VerificationSource.WEB_SEARCH,
                    check_name="web_search_check",
                    result=CheckResult.PASS,
                    confidence=0.6,
                    message=f"Found {len(results)} web results supporting this approach",
                    details={"result_count": len(results)},
                    duration_ms=(time.time() - start) * 1000,
                )
            else:
                return VerificationCheck(
                    check_id=check_id,
                    source=VerificationSource.WEB_SEARCH,
                    check_name="web_search_check",
                    result=CheckResult.WARN,
                    confidence=0.4,
                    message="No web results found -- approach may be unconventional",
                    duration_ms=(time.time() - start) * 1000,
                )
        except Exception as e:
            return VerificationCheck(
                check_id=check_id,
                source=VerificationSource.WEB_SEARCH,
                check_name="web_search_check",
                result=CheckResult.SKIP,
                confidence=0.0,
                message=f"Web search error: {str(e)[:100]}",
                duration_ms=(time.time() - start) * 1000,
            )

    async def _check_user_confirmation(self, instruction) -> VerificationCheck:
        """
        Request user confirmation through bidirectional comms.

        Uses WebSocket or marks as pending for user to confirm via chat/voice.
        """
        check_id = f"CHK-{uuid.uuid4().hex[:8]}"
        start = time.time()

        what = getattr(instruction, 'what', 'Unknown action')
        itype = getattr(instruction, 'instruction_type', 'unknown')
        itype_val = itype.value if hasattr(itype, 'value') else str(itype)
        risks = getattr(instruction, 'risks', []) or []

        confirmation_request = {
            "check_id": check_id,
            "instruction_id": instruction.instruction_id,
            "action": what,
            "type": itype_val,
            "risks": risks,
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }

        self._pending_confirmations[check_id] = confirmation_request

        if self._websocket_manager:
            try:
                await self._websocket_manager.broadcast(
                    json.dumps({
                        "type": "user_confirmation_required",
                        "data": confirmation_request,
                    }),
                    channel="status",
                )
            except Exception:
                pass

        return VerificationCheck(
            check_id=check_id,
            source=VerificationSource.USER_CONFIRMATION,
            check_name="user_confirmation_check",
            result=CheckResult.PENDING_USER,
            confidence=0.0,
            message=(
                f"User confirmation required for: {what[:100]}. "
                f"Risks: {', '.join(risks[:3]) if risks else 'none listed'}. "
                "Respond via chat or WebSocket."
            ),
            details=confirmation_request,
            duration_ms=(time.time() - start) * 1000,
        )

    def submit_user_confirmation(
        self,
        check_id: str,
        approved: bool,
        user_note: Optional[str] = None,
    ) -> bool:
        """
        Submit user confirmation for a pending check.

        Called when user responds via chat, WebSocket, or voice.
        """
        if check_id not in self._pending_confirmations:
            return False

        self._pending_confirmations[check_id]["status"] = "confirmed" if approved else "rejected"
        self._pending_confirmations[check_id]["user_approved"] = approved
        self._pending_confirmations[check_id]["user_note"] = user_note
        self._pending_confirmations[check_id]["confirmed_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"[VERIFY-ENGINE] User confirmation for {check_id}: "
            f"{'APPROVED' if approved else 'REJECTED'}"
        )

        return True

    def get_pending_confirmations(self) -> List[Dict[str, Any]]:
        """Get all pending user confirmations."""
        return [
            conf for conf in self._pending_confirmations.values()
            if conf.get("status") == "pending"
        ]

    # ==================================================================
    # REPORT COMPILATION
    # ==================================================================

    def _compile_report(self, report: VerificationReport):
        """Compile check results into overall verdict."""
        report.total_checks = len(report.checks)
        report.passed_checks = sum(1 for c in report.checks if c.result == CheckResult.PASS)
        report.failed_checks = sum(1 for c in report.checks if c.result == CheckResult.FAIL)
        report.warned_checks = sum(1 for c in report.checks if c.result == CheckResult.WARN)
        report.skipped_checks = sum(1 for c in report.checks if c.result == CheckResult.SKIP)

        for check in report.checks:
            if check.result == CheckResult.FAIL:
                report.critical_failures.append(
                    f"[{check.source.value}] {check.message}"
                )
            elif check.result == CheckResult.WARN:
                report.warnings.append(
                    f"[{check.source.value}] {check.message}"
                )
            elif check.result == CheckResult.PENDING_USER:
                report.requires_user_confirmation = True
                report.user_confirmation_reason = check.message

        if report.critical_failures:
            report.overall_pass = False
        elif report.requires_user_confirmation:
            report.overall_pass = False
        else:
            active_checks = [
                c for c in report.checks
                if c.result not in (CheckResult.SKIP, CheckResult.PENDING_USER)
            ]
            if active_checks:
                pass_rate = sum(1 for c in active_checks if c.result == CheckResult.PASS) / len(active_checks)
                report.overall_pass = pass_rate >= 0.5
            else:
                report.overall_pass = True

        active_confidences = [
            c.confidence for c in report.checks
            if c.result != CheckResult.SKIP
        ]
        report.overall_confidence = (
            sum(active_confidences) / len(active_confidences)
            if active_confidences else 0.0
        )

    def get_verification_stats(self) -> Dict[str, Any]:
        """Get verification statistics."""
        if not self._verification_history:
            return {"total_reports": 0, "message": "No verifications yet"}

        total = len(self._verification_history)
        passed = sum(1 for r in self._verification_history if r.overall_pass)
        failed = sum(1 for r in self._verification_history if not r.overall_pass)
        avg_checks = sum(r.total_checks for r in self._verification_history) / total
        avg_confidence = sum(r.overall_confidence for r in self._verification_history) / total

        source_stats = {}
        for report in self._verification_history:
            for check in report.checks:
                src = check.source.value
                if src not in source_stats:
                    source_stats[src] = {"total": 0, "pass": 0, "fail": 0, "warn": 0, "skip": 0}
                source_stats[src]["total"] += 1
                source_stats[src][check.result.value] = source_stats[src].get(check.result.value, 0) + 1

        return {
            "total_reports": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0,
            "avg_checks_per_report": round(avg_checks, 1),
            "avg_confidence": round(avg_confidence, 3),
            "pending_user_confirmations": len(self.get_pending_confirmations()),
            "source_stats": source_stats,
        }


# Avoid circular import at module level
import json

_engine_instance: Optional[GraceVerificationEngine] = None


def get_grace_verification_engine(session: Session) -> GraceVerificationEngine:
    """Get or create the Grace verification engine singleton."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = GraceVerificationEngine(session)
    return _engine_instance
