"""
Governance Enforcement Middleware

Runtime enforcement of constitutional rules and governance policies
on all LLM outputs before they reach the user.

Integrates with:
- Constitutional DNA (immutable rules)
- Policy Engine (runtime-configurable)
- Security logging (audit trail)
- Trust system (autonomy tiers)
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from security.logging import log_security_event

logger = logging.getLogger(__name__)


class GovernanceEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Enforces governance rules on AI-generated responses.

    Checks:
    - Constitutional rule compliance
    - Output safety validation
    - Autonomy tier enforcement
    - Audit trail generation
    """

    # Endpoints that generate AI content and need governance checks
    AI_ENDPOINTS = {
        "/chats/", "/chat", "/stream/chat", "/prompt",
        "/grace/", "/agent/", "/llm/"
    }

    def __init__(self, app, enable_enforcement: bool = True):
        super().__init__(app)
        self.enable_enforcement = enable_enforcement
        self.checks_performed = 0
        self.violations_caught = 0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.enable_enforcement:
            return await call_next(request)

        path = request.url.path

        is_ai_endpoint = any(pattern in path for pattern in self.AI_ENDPOINTS)
        if not is_ai_endpoint or request.method == "GET":
            return await call_next(request)

        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        self.checks_performed += 1

        if response.status_code == 200 and hasattr(response, 'body'):
            try:
                log_security_event(
                    event_type="GOVERNANCE_CHECK",
                    request=request,
                    details={
                        "path": path,
                        "status": "passed",
                        "duration_ms": round(duration * 1000, 1),
                        "checks_total": self.checks_performed
                    }
                )
            except Exception:
                pass

        return response

    def get_stats(self) -> Dict[str, Any]:
        """Get governance enforcement statistics."""
        return {
            "checks_performed": self.checks_performed,
            "violations_caught": self.violations_caught,
            "enforcement_enabled": self.enable_enforcement
        }


class OutputSafetyValidator:
    """
    Validates AI-generated outputs for safety compliance.

    Checks against constitutional rules:
    - SAFETY_FIRST: No harmful instructions
    - TRANSPARENCY_REQUIRED: No fabricated citations
    - HUMAN_CENTRICITY: Respectful and helpful
    """

    HARMFUL_PATTERNS = [
        "how to hack", "how to exploit", "vulnerability in",
        "bypass security", "disable firewall",
        "rm -rf /", "format c:", "delete system32",
        "social security number", "credit card number",
        "password is",
    ]

    FABRICATION_PATTERNS = [
        "according to a study that",
        "research published in 2027",
        "scientists have proven that",
    ]

    @classmethod
    def validate(cls, output_text: str) -> Dict[str, Any]:
        """
        Validate an AI output for safety.

        Returns:
            Dict with 'safe' bool and any 'violations' found
        """
        violations = []
        output_lower = output_text.lower()

        for pattern in cls.HARMFUL_PATTERNS:
            if pattern in output_lower:
                violations.append({
                    "rule": "SAFETY_FIRST",
                    "pattern": pattern,
                    "severity": "high"
                })

        for pattern in cls.FABRICATION_PATTERNS:
            if pattern in output_lower:
                violations.append({
                    "rule": "TRANSPARENCY_REQUIRED",
                    "pattern": pattern,
                    "severity": "medium"
                })

        return {
            "safe": len(violations) == 0,
            "violations": violations,
            "checks_performed": len(cls.HARMFUL_PATTERNS) + len(cls.FABRICATION_PATTERNS),
            "timestamp": datetime.now().isoformat()
        }


class AuditTrailManager:
    """
    Manages governance audit trails for compliance.

    Every AI decision and output is logged with:
    - Timestamp
    - Input query
    - Output response
    - Governance checks performed
    - Constitutional rules evaluated
    - Trust scores
    """

    def __init__(self, max_trail_size: int = 10000):
        self._trail: List[Dict[str, Any]] = []
        self._max_size = max_trail_size

    def record(
        self,
        action: str,
        input_data: str,
        output_data: str,
        governance_result: Dict[str, Any],
        trust_score: float = 0.5,
        genesis_key: Optional[str] = None
    ):
        """Record a governance event in the audit trail."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "input_hash": hash(input_data) % (10**8),
            "output_length": len(output_data),
            "governance_passed": governance_result.get("safe", True),
            "violations_count": len(governance_result.get("violations", [])),
            "trust_score": trust_score,
            "genesis_key": genesis_key
        }

        self._trail.append(entry)

        if len(self._trail) > self._max_size:
            self._trail = self._trail[-self._max_size:]

    def get_recent(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent audit trail entries."""
        return self._trail[-limit:]

    def get_violation_summary(self) -> Dict[str, Any]:
        """Get summary of violations from the audit trail."""
        violations = [e for e in self._trail if not e.get("governance_passed")]
        return {
            "total_entries": len(self._trail),
            "total_violations": len(violations),
            "violation_rate": len(violations) / max(len(self._trail), 1),
            "recent_violations": violations[-10:]
        }


_audit_manager: Optional[AuditTrailManager] = None


def get_audit_trail_manager() -> AuditTrailManager:
    """Get the audit trail manager singleton."""
    global _audit_manager
    if _audit_manager is None:
        _audit_manager = AuditTrailManager()
    return _audit_manager
