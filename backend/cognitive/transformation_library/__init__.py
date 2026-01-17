"""
Transformation Library - AST-based Code Transformation System

A deterministic, proof-gated code transformation system with:
- Rule DSL for defining AST match patterns and rewrite templates
- Outcome Ledger (magma-backed) for immutable logging
- Pattern Miner for discovering new rules from successful transforms

Beyond LMs: Focus on deterministic transforms, proof gating, and 
outcome-based learning rather than bigger context windows.
"""

from cognitive.transformation_library.rule_dsl import RuleDSL, load_rule, Rule
from cognitive.transformation_library.ast_matcher import ASTMatcher
from cognitive.transformation_library.rewrite_engine import RewriteEngine
from cognitive.transformation_library.constraint_validator import ConstraintValidator
from cognitive.transformation_library.proof_system import ProofSystem
from cognitive.transformation_library.transformation_executor import TransformationExecutor
from cognitive.transformation_library.outcome_ledger import OutcomeLedger, TransformationOutcome
from cognitive.transformation_library.pattern_miner import TransformationPatternMiner

__all__ = [
    "RuleDSL",
    "load_rule",
    "Rule",
    "ASTMatcher",
    "RewriteEngine",
    "ConstraintValidator",
    "ProofSystem",
    "TransformationExecutor",
    "OutcomeLedger",
    "TransformationOutcome",
    "TransformationPatternMiner",
]
