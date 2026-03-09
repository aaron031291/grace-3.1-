import yaml
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GuardianActionGate:
    """
    Enforces the Grace Guardian ACL for autonomous actions.
    Ensures the consensus engine only executes whitelisted, reversible, or dry-run safe commands.
    """
    def __init__(self):
        self.config_path = Path(__file__).parent / "config" / "auto_defense.yml"
        self.whitelist = self._load_config()

    def _load_config(self) -> list:
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("graduated_whitelist", [])
        except Exception as e:
            logger.error(f"[GUARDIAN] Failed to load auto_defense.yml: {e}")
            return []

    def authorize(self, action_payload: Dict[str, Any], trust_score: float) -> dict:
        """
        Validates an action against the auto_defense.yml whitelist.
        Returns {"authorized": bool, "reason": str}
        """
        action_type = action_payload.get("action_type")
        
        if not action_type:
            return {"authorized": False, "reason": "Action payload missing 'action_type'."}

        # Find matching rules in the whitelist
        matching_rules = [rule for rule in self.whitelist if rule.get("action_type") == action_type]
        
        if not matching_rules:
            return {
                "authorized": False, 
                "reason": f"Action type '{action_type}' is not whitelisted by Guardian. Auto-defense REJECT."
            }
            
        rule = matching_rules[0]
        
        # 1. Check Risk / Trust
        max_risk = rule.get("max_risk_score", 0.0)
        # Assuming trust_score maps inversely to risk (or directly if max_risk is a threshold of allowed risk)
        # Trust score typically 0.0 - 1.0. If trust is lower than the required threshold (1.0 - max_risk), deny.
        min_required_trust = 1.0 - max_risk
        if trust_score < min_required_trust:
            return {
                "authorized": False,
                "reason": f"Trust score {trust_score:.2f} is below Guardian requirement {min_required_trust:.2f} for '{action_type}'."
            }

        # 2. Check Dry-Run flag if required
        require_dry_run = rule.get("require_dry_run", False)
        params = action_payload.get("params", {})
        is_dry_run = str(params.get("dry_run", "false")).lower() == "true"
        
        if require_dry_run and not is_dry_run:
             return {
                "authorized": False,
                "reason": f"Guardian STRICT ENFORCEMENT: '{action_type}' requires 'dry_run: true' parameter. Auto-defense REJECT."
            }

        # Check explain_fix if required
        require_explanation = rule.get("require_explanation", False)
        if require_explanation:
            explain_fix = params.get("explain_fix", "").strip()
            if not explain_fix:
                return {
                    "authorized": False,
                    "reason": f"Guardian STRICT ENFORCEMENT: '{action_type}' requires an 'explain_fix' explanation. Auto-defense REJECT."
                }
            
            # Store explanation in ClarityDecision
            try:
                from core.clarity_framework import ClarityFramework
                cf = ClarityFramework()
                cf.record_decision(
                    what=f"Action '{action_type}' requested",
                    why=explain_fix,
                    who="Consensus Engine / Autonomous Loop",
                    where=action_payload.get("target", "system"),
                    how=str(params),
                    risk_score=1.0 - trust_score
                )
            except Exception as e:
                logger.error(f"[GUARDIAN] Failed to record ClarityDecision: {e}")

        # 3. Specific validations for execute_shell_command
        if action_type == "execute_shell_command":
            allowed_cmd_prefixes = rule.get("allowed_commands", [])
            cmd = params.get("command", "")
            if not any(cmd.startswith(prefix) for prefix in allowed_cmd_prefixes):
                return {
                    "authorized": False,
                    "reason": f"Command '{cmd}' is not in the Guardian shell whitelist. Allowed: {allowed_cmd_prefixes}."
                }

        # 4. Specific validations for restart_service
        if action_type == "restart_service":
            allowed_targets = rule.get("allowed_targets", [])
            target = params.get("target", "")
            if target not in allowed_targets:
                 return {
                    "authorized": False,
                    "reason": f"Restart target '{target}' is not in the Guardian whitelist. Allowed: {allowed_targets}."
                }

        # If it passes all checks
        logger.info(f"[GUARDIAN] Action Gate AUTHORIZED autonomous command: {action_type}")
        return {"authorized": True, "reason": "Guardian whitelist checks passed."}

# Global singleton
_gate = None

def get_action_gate() -> GuardianActionGate:
    global _gate
    if not _gate:
        _gate = GuardianActionGate()
    return _gate
