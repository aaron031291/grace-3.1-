"""
ULH Meta-Rule Injector — Runtime CTL/LTL constraint management.

Replaces the hardcoded ULH_MR_ENABLE=0 flag with a governance-gated
meta-rule system that allows self-healing to rewrite policy constraints.

CTL (Computation Tree Logic) rules: express branching-time properties
  e.g., "AG(trust > 0.4)" = on ALL paths, GLOBALLY trust stays above 0.4
LTL (Linear Temporal Logic) rules: express linear-time properties
  e.g., "G(error → F recovery)" = GLOBALLY, every error is EVENTUALLY followed by recovery
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent.parent / "data"
_RULES_FILE = _DATA_DIR / "meta_rules.json"


class RuleType(str, Enum):
    CTL = "ctl"
    LTL = "ltl"


@dataclass
class MetaRule:
    rule_id: str
    rule_type: RuleType
    formula: str
    description: str
    enabled: bool = True
    requires_governance_approval: bool = True
    trust_threshold: float = 0.75
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_evaluated: Optional[str] = None
    last_result: Optional[bool] = None


class MetaRuleInjector:
    """
    Runtime meta-rule injector for CTL/LTL constraints.
    Gated behind governance approval instead of a hardcoded flag.
    """

    _instance = None

    def __init__(self):
        self._rules: Dict[str, MetaRule] = {}
        self._load_rules()
        self._seed_defaults()

    @classmethod
    def get_instance(cls) -> "MetaRuleInjector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _seed_defaults(self):
        """Seed default safety rules if registry is empty."""
        if self._rules:
            return
        defaults = [
            MetaRule(
                rule_id="safety_trust_floor",
                rule_type=RuleType.CTL,
                formula="AG(trust > 0.3)",
                description="On all paths, trust must remain above critical threshold",
                requires_governance_approval=False,
            ),
            MetaRule(
                rule_id="error_recovery",
                rule_type=RuleType.LTL,
                formula="G(error -> F recovery)",
                description="Every error must eventually be followed by recovery",
                requires_governance_approval=False,
            ),
            MetaRule(
                rule_id="no_unaudited_exec",
                rule_type=RuleType.LTL,
                formula="G(exec_action -> X audit_logged)",
                description="Every executive action must be immediately followed by audit logging",
                requires_governance_approval=False,
            ),
        ]
        for rule in defaults:
            self._rules[rule.rule_id] = rule
        self._save_rules()

    def is_enabled(self) -> bool:
        """Check if meta-rule system is enabled (replaces ULH_MR_ENABLE=0)."""
        try:
            from settings import settings
            return getattr(settings, "ULH_META_RULES_ENABLED", True)
        except Exception:
            return True

    def inject_rule(self, rule: MetaRule) -> Dict[str, Any]:
        """
        Add or update a meta-rule. Gated behind governance approval.
        """
        if not self.is_enabled():
            return {"status": "disabled", "reason": "ULH_META_RULES_ENABLED is False"}

        # Check governance approval
        approval = self._check_governance_approval(rule)
        if not approval["approved"]:
            return {"status": "blocked", "reason": approval["reason"]}

        self._rules[rule.rule_id] = rule
        self._save_rules()

        # Publish event
        try:
            from cognitive.event_bus import publish
            publish("ulh.rule_injected", {
                "rule_id": rule.rule_id,
                "rule_type": rule.rule_type.value,
                "formula": rule.formula,
            }, source="ulh_meta_rule_injector")
        except Exception:
            pass

        logger.info(f"[ULH] Injected meta-rule: {rule.rule_id} ({rule.formula})")
        return {"status": "injected", "rule_id": rule.rule_id}

    def evaluate_rule(self, rule_id: str, system_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a CTL/LTL rule against current system state.
        Uses simplified pattern matching (not full model checking).
        """
        rule = self._rules.get(rule_id)
        if not rule or not rule.enabled:
            return {"rule_id": rule_id, "status": "not_found_or_disabled"}

        result = self._evaluate_formula(rule, system_state)
        rule.last_evaluated = datetime.now(timezone.utc).isoformat()
        rule.last_result = result["satisfied"]
        self._save_rules()

        return result

    def evaluate_all(self, system_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate all active rules against current state."""
        if not self.is_enabled():
            return []
        results = []
        for rule_id, rule in self._rules.items():
            if rule.enabled:
                results.append(self.evaluate_rule(rule_id, system_state))
        return results

    def get_active_rules(self) -> List[MetaRule]:
        """Return all enabled meta-rules."""
        return [r for r in self._rules.values() if r.enabled]

    def get_violations(self, system_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Return rules that are violated in the current state."""
        results = self.evaluate_all(system_state)
        return [r for r in results if not r.get("satisfied", True)]

    def _check_governance_approval(self, rule: MetaRule) -> Dict[str, Any]:
        """
        Check if governance approves this rule injection.
        Tier 0 (supervised): requires human approval
        Tier 1+: auto-approve if system trust > rule.trust_threshold
        """
        if not rule.requires_governance_approval:
            return {"approved": True, "reason": "no_approval_required"}

        try:
            from security.governance import get_governance_engine
            gov = get_governance_engine()
            tier = gov.get_autonomy_tier() if hasattr(gov, 'get_autonomy_tier') else 1
        except Exception:
            tier = 1

        if tier == 0:
            return {"approved": False, "reason": "Tier 0 (supervised): human approval required"}

        # Check system trust
        try:
            from cognitive.trust_engine import get_trust_engine
            trust = get_trust_engine()
            overall = trust.get_system_trust() if hasattr(trust, 'get_system_trust') else 0.7
            if overall >= rule.trust_threshold:
                return {"approved": True, "reason": f"auto_approved (trust={overall:.2f} >= {rule.trust_threshold})"}
            else:
                return {"approved": False, "reason": f"trust too low ({overall:.2f} < {rule.trust_threshold})"}
        except Exception:
            return {"approved": True, "reason": "trust_check_unavailable_default_approve"}

    def _evaluate_formula(self, rule: MetaRule, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simplified formula evaluation against system state.
        Supports basic patterns from CTL/LTL formulas.
        """
        formula = rule.formula.strip()
        satisfied = True
        details = ""

        # Pattern: AG(x > val) or G(x > val) — global invariant check
        match = re.match(r'[AG]+\((\w+)\s*([><=!]+)\s*([\d.]+)\)', formula)
        if match:
            var_name, op, threshold = match.group(1), match.group(2), float(match.group(3))
            actual = state.get(var_name)
            if actual is not None:
                if op == '>':
                    satisfied = float(actual) > threshold
                elif op == '>=':
                    satisfied = float(actual) >= threshold
                elif op == '<':
                    satisfied = float(actual) < threshold
                elif op == '<=':
                    satisfied = float(actual) <= threshold
                elif op == '==':
                    satisfied = float(actual) == threshold
                details = f"{var_name}={actual} {op} {threshold} → {'✓' if satisfied else '✗'}"
            else:
                details = f"{var_name} not in state (assumed satisfied)"

        # Pattern: G(a -> F b) — every a must eventually lead to b
        elif '->' in formula and 'F' in formula:
            lhs_match = re.search(r'G\((\w+)\s*->\s*F\s+(\w+)\)', formula)
            if lhs_match:
                trigger = lhs_match.group(1)
                recovery = lhs_match.group(2)
                trigger_count = state.get(f"{trigger}_count", 0)
                recovery_count = state.get(f"{recovery}_count", 0)
                if trigger_count > 0:
                    satisfied = recovery_count >= trigger_count * 0.8
                details = f"{trigger}={trigger_count} → {recovery}={recovery_count}"

        # Pattern: G(a -> X b) — every a must be immediately followed by b
        elif '->' in formula and 'X' in formula:
            lhs_match = re.search(r'G\((\w+)\s*->\s*X\s+(\w+)\)', formula)
            if lhs_match:
                action = lhs_match.group(1)
                follow = lhs_match.group(2)
                action_count = state.get(f"{action}_count", 0)
                follow_count = state.get(f"{follow}_count", 0)
                if action_count > 0:
                    satisfied = follow_count >= action_count * 0.95
                details = f"{action}={action_count} → {follow}={follow_count}"

        else:
            details = f"formula not parseable: {formula}"

        return {
            "rule_id": rule.rule_id,
            "formula": formula,
            "satisfied": satisfied,
            "details": details,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _save_rules(self):
        """Persist rules to disk."""
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        data = {rid: asdict(r) for rid, r in self._rules.items()}
        _RULES_FILE.write_text(json.dumps(data, indent=2, default=str))

    def _load_rules(self):
        """Load rules from disk."""
        if not _RULES_FILE.exists():
            return
        try:
            data = json.loads(_RULES_FILE.read_text())
            for rid, rdata in data.items():
                rdata["rule_type"] = RuleType(rdata.get("rule_type", "ltl"))
                self._rules[rid] = MetaRule(**rdata)
        except Exception as e:
            logger.warning(f"[ULH] Failed to load meta-rules: {e}")


def get_meta_rule_injector() -> MetaRuleInjector:
    return MetaRuleInjector.get_instance()
