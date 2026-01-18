import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
logger = logging.getLogger(__name__)

class Rule:
    """A code transformation rule."""
    id: str
    version: str
    pattern: Dict[str, Any]
    rewrite: Dict[str, Any]
    constraints: Dict[str, Any]
    proof_required: List[str]
    side_effects: List[str]
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        """Create rule from dictionary."""
        return cls(**data)


class RuleDSL:
    """
    Rule DSL parser and rule definitions manager.
    
    Supports defining rules with:
    - AST match patterns
    - Rewrite templates
    - Pre/post constraints
    - Required proofs
    - Expected side effects
    """

    def __init__(self, rules_dir: Optional[Path] = None):
        """Initialize Rule DSL."""
        if rules_dir is None:
            # Default to rules directory in transformation_library
            rules_dir = Path(__file__).parent / "rules"
        self.rules_dir = Path(rules_dir)
        self.rules_dir.mkdir(parents=True, exist_ok=True)
        
        self._rules: Dict[str, Rule] = {}
        self._load_builtin_rules()

    def _load_builtin_rules(self):
        """Load built-in transformation rules."""
        builtin_rules = [
            {
                "id": "bare_except_to_exception",
                "version": "1.0",
                "pattern": {
                    "type": "ast",
                    "match": "ExceptHandler(type=None)",
                    "language": "python"
                },
                "rewrite": {
                    "template": "except Exception as {name}:",
                    "preserve": ["body", "name"]
                },
                "constraints": {
                    "pre": ["no_nested_except"],
                    "post": ["handles_exception_types", "preserves_traceback"]
                },
                "proof_required": ["type_safety", "exception_coverage"],
                "side_effects": ["improves_error_handling", "may_change_exception_caught"],
                "description": "Replace bare except clauses with 'except Exception'"
            },
            {
                "id": "print_to_logging",
                "version": "1.0",
                "pattern": {
                    "type": "ast",
                    "match": "Call(func=Name(id='print'))",
                    "language": "python"
                },
                "rewrite": {
                    "template": "logger.info({args})",
                    "preserve": ["args"]
                },
                "constraints": {
                    "pre": ["not_in_function_definition"],
                    "post": ["logging_import_exists", "logger_defined"]
                },
                "proof_required": ["logging_available"],
                "side_effects": ["adds_logging_dependency"],
                "description": "Replace print statements with logger.info"
            }
        ]
        
        for rule_data in builtin_rules:
            rule = Rule.from_dict(rule_data)
            self._rules[rule.id] = rule

    def define_rule(self, rule: Rule) -> None:
        """Define a new rule."""
        self._rules[rule.id] = rule
        logger.info(f"[RULE-DSL] Defined rule: {rule.id} v{rule.version}")

    def get_rule(self, rule_id: str, version: Optional[str] = None) -> Optional[Rule]:
        """Get a rule by ID and optional version."""
        if rule_id not in self._rules:
            return None
        
        rule = self._rules[rule_id]
        if version and rule.version != version:
            # Could implement version lookup here
            logger.warning(f"[RULE-DSL] Version mismatch for {rule_id}: requested {version}, got {rule.version}")
        
        return rule

    def list_rules(self) -> List[str]:
        """List all available rule IDs."""
        return list(self._rules.keys())

    def load_rule_from_file(self, file_path: Path) -> Rule:
        """Load a rule from a JSON file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        rule = Rule.from_dict(data)
        self.define_rule(rule)
        return rule

    def save_rule_to_file(self, rule: Rule, file_path: Optional[Path] = None) -> Path:
        """Save a rule to a JSON file."""
        if file_path is None:
            file_path = self.rules_dir / f"{rule.id}_v{rule.version}.json"
        
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            json.dump(rule.to_dict(), f, indent=2)
        
        logger.info(f"[RULE-DSL] Saved rule to {file_path}")
        return file_path

    def validate_rule(self, rule: Rule) -> tuple[bool, List[str]]:
        """Validate a rule structure."""
        errors = []
        
        if not rule.id:
            errors.append("Rule ID is required")
        
        if not rule.version:
            errors.append("Rule version is required")
        
        if not rule.pattern or not rule.pattern.get("match"):
            errors.append("Rule pattern.match is required")
        
        if not rule.rewrite or not rule.rewrite.get("template"):
            errors.append("Rule rewrite.template is required")
        
        return len(errors) == 0, errors


# Global Rule DSL instance
_rule_dsl: Optional[RuleDSL] = None


def get_rule_dsl() -> RuleDSL:
    """Get or create global Rule DSL instance."""
    global _rule_dsl
    if _rule_dsl is None:
        _rule_dsl = RuleDSL()
    return _rule_dsl


def load_rule(rule_id: str, version: Optional[str] = None) -> Optional[Rule]:
    """Load a rule by ID."""
    return get_rule_dsl().get_rule(rule_id, version)
