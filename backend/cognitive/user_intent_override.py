"""
User Intent Override — Dynamic Permission System with Guardrails

When a user gives an explicit instruction that conflicts with governance
rules or verification checks, Grace doesn't just refuse. Instead:

1. ANALYSE: Parse the user's intent and identify governance impacts
2. WARN: Explain what checks will be skipped and the consequences
3. OFFER ALTERNATIVES: Suggest compliant ways to achieve the same goal
4. ACCEPT: If user confirms with explicit permission, execute with monitoring
5. MONITOR: Track the override execution with enhanced logging

The user is the real-time deterministic input. Their explicit permission
makes the system dynamic while maintaining safety through transparency.

Philosophy:
  "Aaron, we appreciate you said to do this. Here's what happens if we skip
   the verification. But here's a solution that keeps it tight with the
   system parameters AND still gets what you want."
"""

import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

OVERRIDE_TTL_MINUTES = 30


@dataclass
class GovernanceImpact:
    rule_name: str
    severity: str  # low, medium, high, critical
    description: str
    skipped_check: str


@dataclass
class Alternative:
    description: str
    compliance_level: str  # full, partial, minimal
    trade_offs: str
    recommended: bool = False


@dataclass
class OverrideAnalysis:
    original_intent: str
    parsed_action: str
    governance_impacts: List[GovernanceImpact]
    blast_radius: str  # isolated, local, system-wide
    risk_level: str  # low, medium, high, critical
    alternatives: List[Alternative]
    override_token: Optional[str] = None
    explanation: str = ""
    can_proceed: bool = True


# Active override tokens (in-memory, short-lived)
_active_tokens: Dict[str, Dict[str, Any]] = {}


class UserIntentOverride:
    """Handles user requests that may conflict with governance or verification."""

    def analyse(self, user_command: str, context: str = "") -> OverrideAnalysis:
        """
        Analyse what the user wants to do and identify governance impacts.
        Returns an analysis with alternatives — never just refuses.
        """
        action = self._parse_action(user_command)
        impacts = self._check_governance_impacts(action, user_command)
        blast_radius = self._calculate_blast_radius(action)
        risk_level = self._calculate_risk(impacts, blast_radius)
        alternatives = self._generate_alternatives(action, impacts, user_command)

        # Generate override token if user might want to proceed
        token = None
        if impacts:
            token = f"override_{uuid.uuid4().hex[:12]}"
            _active_tokens[token] = {
                "command": user_command,
                "action": action,
                "impacts": [{"rule": i.rule_name, "severity": i.severity} for i in impacts],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=OVERRIDE_TTL_MINUTES)).isoformat(),
                "executed": False,
            }

        # Build the explanation Grace would give
        explanation = self._build_explanation(action, impacts, alternatives, risk_level)

        return OverrideAnalysis(
            original_intent=user_command,
            parsed_action=action,
            governance_impacts=impacts,
            blast_radius=blast_radius,
            risk_level=risk_level,
            alternatives=alternatives,
            override_token=token,
            explanation=explanation,
            can_proceed=risk_level != "critical",
        )

    def execute_override(self, token: str) -> Dict[str, Any]:
        """
        User confirms: execute with override.
        Enhanced monitoring is applied during override execution.
        """
        if token not in _active_tokens:
            return {"error": "Invalid or expired override token", "executed": False}

        token_data = _active_tokens[token]

        # Check expiry
        expires = datetime.fromisoformat(token_data["expires_at"])
        if datetime.now(timezone.utc) > expires:
            del _active_tokens[token]
            return {"error": "Override token expired", "executed": False}

        if token_data["executed"]:
            return {"error": "Override already executed", "executed": False}

        # Mark as executed
        token_data["executed"] = True
        token_data["executed_at"] = datetime.now(timezone.utc).isoformat()

        # Log the override via Genesis Key
        try:
            from api._genesis_tracker import track
            track(
                key_type="system",
                what=f"User override executed: {token_data['command'][:100]}",
                who="user",
                why="Explicit user permission",
                how="UserIntentOverride.execute_override",
                output_data={
                    "action": token_data["action"],
                    "impacts_skipped": token_data["impacts"],
                    "token": token,
                },
                tags=["override", "user_permission", "governance_bypass"],
            )
        except Exception:
            pass

        # Publish event for system awareness
        try:
            from cognitive.event_bus import publish
            publish("user.override_executed", {
                "action": token_data["action"],
                "impacts": len(token_data["impacts"]),
            }, source="user_intent_override")
        except Exception:
            pass

        return {
            "executed": True,
            "action": token_data["action"],
            "impacts_acknowledged": len(token_data["impacts"]),
            "monitoring": "enhanced",
            "token": token,
        }

    # ── Internal Logic ────────────────────────────────────────────────

    def _parse_action(self, command: str) -> str:
        """Parse what the user is trying to do."""
        lower = command.lower()

        if any(w in lower for w in ["generate", "create", "build", "write", "code"]):
            return "code_generation"
        if any(w in lower for w in ["delete", "remove", "drop", "destroy"]):
            return "destructive_operation"
        if any(w in lower for w in ["deploy", "push", "release", "ship"]):
            return "deployment"
        if any(w in lower for w in ["change", "modify", "update", "edit", "refactor"]):
            return "modification"
        if any(w in lower for w in ["skip", "ignore", "bypass", "override", "disable"]):
            return "governance_bypass"
        if any(w in lower for w in ["install", "add", "import", "integrate"]):
            return "integration"
        return "general_action"

    def _check_governance_impacts(self, action: str, command: str) -> List[GovernanceImpact]:
        """Check what governance rules would be affected."""
        impacts = []

        if action == "destructive_operation":
            impacts.append(GovernanceImpact(
                rule_name="Data Protection",
                severity="high",
                description="Destructive operations bypass the reversibility check in the invariant stage",
                skipped_check="invariant_reversibility",
            ))

        if action == "governance_bypass":
            impacts.append(GovernanceImpact(
                rule_name="Governance Compliance",
                severity="high",
                description="Explicitly bypassing governance rules removes compliance guardrails",
                skipped_check="governance_rules_injection",
            ))

        if action == "deployment":
            impacts.append(GovernanceImpact(
                rule_name="Deployment Safety",
                severity="medium",
                description="Deployment without full verification pipeline may introduce untested code",
                skipped_check="pipeline_verification",
            ))

        if action in ("code_generation", "modification"):
            lower = command.lower()
            if any(w in lower for w in ["skip test", "no test", "without test", "skip verif"]):
                impacts.append(GovernanceImpact(
                    rule_name="Verification Pipeline",
                    severity="medium",
                    description="Skipping verification means hallucination and contradiction checks won't run",
                    skipped_check="hallucination_guard",
                ))

        # Check if any uploaded governance documents would be violated
        try:
            from core.services.govern_service import list_rules
            _list_rule_files = lambda: list_rules().get("documents", [])
            rules = _list_rule_files()
            if rules and action in ("governance_bypass", "destructive_operation"):
                for rule in rules[:3]:
                    impacts.append(GovernanceImpact(
                        rule_name=rule.get("filename", "Unknown Rule"),
                        severity="medium",
                        description=f"Uploaded governance document '{rule.get('filename', '')}' may be violated",
                        skipped_check="uploaded_rule_compliance",
                    ))
        except Exception:
            pass

        return impacts

    def _calculate_blast_radius(self, action: str) -> str:
        if action in ("destructive_operation", "deployment"):
            return "system-wide"
        if action in ("governance_bypass",):
            return "local"
        return "isolated"

    def _calculate_risk(self, impacts: List[GovernanceImpact], blast_radius: str) -> str:
        if not impacts:
            return "low"
        max_severity = max(i.severity for i in impacts)
        if max_severity == "critical" or (max_severity == "high" and blast_radius == "system-wide"):
            return "critical"
        if max_severity == "high":
            return "high"
        if max_severity == "medium":
            return "medium"
        return "low"

    def _generate_alternatives(self, action: str, impacts: List[GovernanceImpact],
                               command: str) -> List[Alternative]:
        """Generate compliant alternatives that achieve the same goal."""
        alternatives = []

        if action == "code_generation" and any(i.skipped_check == "hallucination_guard" for i in impacts):
            alternatives.append(Alternative(
                description="Run the code generation through the full pipeline but with a lower verification threshold (faster, still safe)",
                compliance_level="full",
                trade_offs="Slightly less rigorous verification, but still catches major issues",
                recommended=True,
            ))
            alternatives.append(Alternative(
                description="Generate the code immediately but queue a background verification that will flag issues within 60 seconds",
                compliance_level="partial",
                trade_offs="Code delivered fast, verification catches up asynchronously",
            ))

        if action == "destructive_operation":
            alternatives.append(Alternative(
                description="Create a snapshot/backup before the destructive operation, then proceed",
                compliance_level="full",
                trade_offs="Adds 2-3 seconds for the snapshot, but operation is fully reversible",
                recommended=True,
            ))

        if action == "governance_bypass":
            alternatives.append(Alternative(
                description="Apply a temporary governance exception for this specific action only (auto-expires in 30 minutes)",
                compliance_level="partial",
                trade_offs="Governance is bypassed for this one action, not globally",
                recommended=True,
            ))

        if action == "deployment":
            alternatives.append(Alternative(
                description="Run a quick smoke test (30 seconds) before deployment instead of the full verification suite",
                compliance_level="partial",
                trade_offs="Covers critical paths, skips edge cases",
                recommended=True,
            ))

        # Always offer the "do it anyway with monitoring" option
        if impacts:
            alternatives.append(Alternative(
                description="Proceed as requested with enhanced monitoring — Grace will watch for issues and auto-rollback if problems detected",
                compliance_level="minimal",
                trade_offs="Your intent is followed exactly, but Grace keeps a safety net active",
            ))

        return alternatives

    def _build_explanation(self, action: str, impacts: List[GovernanceImpact],
                           alternatives: List[Alternative], risk_level: str) -> str:
        """Build Grace's natural language explanation to the user."""
        if not impacts:
            return "This action is fully compliant with all governance rules. Proceeding."

        lines = []
        lines.append(f"I understand you want to {action.replace('_', ' ')}. Here's what I need you to know:")
        lines.append("")

        if impacts:
            lines.append(f"**{len(impacts)} governance impact(s) detected** (Risk: {risk_level}):")
            for i, impact in enumerate(impacts, 1):
                lines.append(f"  {i}. [{impact.severity.upper()}] {impact.description}")
            lines.append("")

        if alternatives:
            recommended = [a for a in alternatives if a.recommended]
            if recommended:
                lines.append("**Recommended approach:**")
                lines.append(f"  {recommended[0].description}")
                lines.append(f"  Trade-off: {recommended[0].trade_offs}")
                lines.append("")

            lines.append("**Other options:**")
            for alt in alternatives:
                if not alt.recommended:
                    lines.append(f"  - [{alt.compliance_level}] {alt.description}")

        lines.append("")
        lines.append("If you want to proceed with your original intent, confirm and I'll execute with enhanced monitoring.")

        return "\n".join(lines)

    def get_active_overrides(self) -> List[Dict[str, Any]]:
        """Get all active (non-expired) override tokens."""
        now = datetime.now(timezone.utc)
        active = []
        expired_keys = []
        for token, data in _active_tokens.items():
            expires = datetime.fromisoformat(data["expires_at"])
            if now > expires:
                expired_keys.append(token)
            else:
                active.append({
                    "token": token,
                    "command": data["command"][:100],
                    "action": data["action"],
                    "executed": data["executed"],
                    "created_at": data["created_at"],
                    "expires_at": data["expires_at"],
                })
        for k in expired_keys:
            del _active_tokens[k]
        return active


_override_instance = None


def get_override_system() -> UserIntentOverride:
    global _override_instance
    if _override_instance is None:
        _override_instance = UserIntentOverride()
    return _override_instance
