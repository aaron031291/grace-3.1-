"""
Clarity Framework - Grace-Aligned Coding Agent Cognitive Framework

A cognitive coding agent that embodies Grace architecture principles:
- Genesis Key tracking for all operations
- Unified Oracle integration for intelligence
- Memory Mesh for learning and feedback loops
- Template-first deterministic code generation
- Multi-layer verification with anti-hallucination
- Trust-scored autonomous execution
- Bidirectional self-healing
- Sub-agent parallel processing

This framework competes with Claude, ChatGPT, and Gemini by using
deterministic templates and Grace's cognitive systems instead of
pure LLM generation.
"""

import logging
import hashlib
import threading
import queue
import time
import ast
import re
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

logger = logging.getLogger(__name__)


# ============================================================================
# GRACE ARCHITECTURE ENUMS
# ============================================================================

class ClarityPhase(str, Enum):
    """Clarity Framework processing phases - aligned with Grace OODA loop."""
    OBSERVE = "observe"         # Gather context, parse intent
    ORIENT = "orient"           # Match templates, consult Oracle
    DECIDE = "decide"           # Select approach, calculate trust
    ACT = "act"                 # Generate code, verify, apply
    LEARN = "learn"             # Update memory mesh, feedback
    COMPLETE = "complete"
    FAILED = "failed"


class CognitiveAgent(str, Enum):
    """Specialized cognitive agents in the framework."""
    OBSERVER = "observer"       # Context analysis, intent extraction
    ORACLE_LIAISON = "oracle"   # Oracle consultation, knowledge retrieval
    SYNTHESIZER = "synthesizer" # Template matching, code generation
    VERIFIER = "verifier"       # Multi-layer verification
    HEALER = "healer"           # Self-healing, error correction
    LEARNER = "learner"         # Memory mesh updates, feedback


class TrustGate(str, Enum):
    """Trust-based action gates."""
    AUTONOMOUS = "autonomous"       # High trust - auto apply
    SUPERVISED = "supervised"       # Medium - sandbox + confirm
    BLOCKED = "blocked"             # Low - do not apply
    ESCALATE = "escalate"           # Template failed - need help


class GenesisKeyType(str, Enum):
    """Genesis key types for Clarity operations."""
    CLARITY_TASK_START = "clarity_task_start"
    CLARITY_INTENT_PARSED = "clarity_intent_parsed"
    CLARITY_ORACLE_CONSULTED = "clarity_oracle_consulted"
    CLARITY_TEMPLATE_MATCHED = "clarity_template_matched"
    CLARITY_CODE_GENERATED = "clarity_code_generated"
    CLARITY_VERIFICATION_COMPLETE = "clarity_verification_complete"
    CLARITY_CODE_APPLIED = "clarity_code_applied"
    CLARITY_HEALING_ATTEMPT = "clarity_healing_attempt"
    CLARITY_LEARNING_STORED = "clarity_learning_stored"
    CLARITY_TASK_COMPLETE = "clarity_task_complete"
    CLARITY_TASK_FAILED = "clarity_task_failed"


# ============================================================================
# DATA MODELS - GRACE ALIGNED
# ============================================================================

@dataclass
class ClarityIntent:
    """
    Parsed intent from user request.
    
    Structured extraction - LLM only produces this, never code.
    Connected to Genesis Key for tracking.
    """
    intent_id: str
    task_type: str
    language: str
    framework: Optional[str]
    target_symbols: List[str]
    desired_behavior: str
    constraints: Dict[str, Any]
    confidence: float = 0.0
    llm_used: bool = False
    genesis_key_id: Optional[str] = None
    oracle_insights: List[Dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class OracleConsultation:
    """Result of consulting the Unified Oracle Hub."""
    consultation_id: str
    query: str
    insights: List[Dict[str, Any]]
    relevant_templates: List[str]
    relevant_patterns: List[str]
    code_examples: List[str]
    confidence: float
    sources: List[str]
    genesis_key_id: Optional[str] = None


@dataclass
class TemplateMatch:
    """A matched template with parameters."""
    template_id: str
    template_name: str
    match_score: float
    required_params: List[str]
    filled_params: Dict[str, Any]
    category: str
    historical_success_rate: float = 0.0
    oracle_boosted: bool = False


@dataclass
class SynthesisResult:
    """Result of code synthesis."""
    synthesis_id: str
    template_id: Optional[str]
    code: str
    transform_type: str  # "template", "oracle_guided", "llm_fallback"
    confidence: float
    provenance: Dict[str, Any]
    genesis_key_id: Optional[str] = None


@dataclass
class VerificationReport:
    """Multi-layer verification results with anti-hallucination."""
    verification_id: str
    syntax_valid: bool = False
    ast_parseable: bool = False
    imports_resolve: bool = False
    type_check_passed: Optional[bool] = None
    lint_passed: Optional[bool] = None
    tests_passed: Optional[bool] = None
    grounding_verified: bool = False
    security_safe: bool = True
    anti_hallucination_passed: bool = True
    
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    verification_time_ms: float = 0.0
    genesis_key_id: Optional[str] = None
    
    @property
    def passed(self) -> bool:
        """Overall pass - all critical checks must pass."""
        return (
            self.syntax_valid and 
            self.ast_parseable and 
            self.security_safe and
            self.anti_hallucination_passed and
            len([e for e in self.errors if e.get("severity") == "critical"]) == 0
        )


@dataclass
class TrustDecision:
    """Trust-based autonomy decision with full factors."""
    trust_score: float
    confidence_interval: Tuple[float, float]
    uncertainty: float
    gate: TrustGate
    factors: Dict[str, float]
    reasoning: str
    genesis_key_id: Optional[str] = None


@dataclass
class ClarityState:
    """
    Complete state for a Clarity task.
    
    Tracks everything from intent to completion with Genesis keys.
    """
    task_id: str
    phase: ClarityPhase
    parent_genesis_key: Optional[str] = None
    
    # Phase outputs
    intent: Optional[ClarityIntent] = None
    oracle_consultation: Optional[OracleConsultation] = None
    template_matches: List[TemplateMatch] = field(default_factory=list)
    selected_template: Optional[TemplateMatch] = None
    synthesis: Optional[SynthesisResult] = None
    verification: Optional[VerificationReport] = None
    trust_decision: Optional[TrustDecision] = None
    
    # Healing state
    healing_attempts: int = 0
    max_healing_attempts: int = 3
    healing_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metrics
    llm_escalations: int = 0
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    genesis_keys: List[str] = field(default_factory=list)
    
    # Timing
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    phase_times: Dict[str, float] = field(default_factory=dict)


@dataclass
class ClarityKPIs:
    """KPI tracking for the Clarity Framework."""
    total_tasks: int = 0
    template_solved: int = 0
    oracle_assisted: int = 0
    llm_fallback: int = 0
    verification_passes: int = 0
    verification_failures: int = 0
    self_healing_success: int = 0
    self_healing_failure: int = 0
    autonomous_applied: int = 0
    supervised_applied: int = 0
    blocked: int = 0
    
    avg_trust_score: float = 0.0
    avg_verification_time_ms: float = 0.0
    avg_healing_cycles: float = 0.0
    template_hit_rate: float = 0.0
    oracle_contribution_rate: float = 0.0
    
    # Per-template tracking
    template_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Genesis key tracking
    total_genesis_keys: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        total = max(self.total_tasks, 1)
        return {
            "total_tasks": self.total_tasks,
            "template_solved": self.template_solved,
            "template_coverage_pct": self.template_solved / total * 100,
            "oracle_assisted": self.oracle_assisted,
            "oracle_contribution_rate": self.oracle_assisted / total * 100,
            "llm_fallback": self.llm_fallback,
            "llm_independence_rate": (total - self.llm_fallback) / total * 100,
            "verification_pass_rate": (
                self.verification_passes / 
                max(self.verification_passes + self.verification_failures, 1) * 100
            ),
            "self_healing_success_rate": (
                self.self_healing_success / 
                max(self.self_healing_success + self.self_healing_failure, 1) * 100
            ),
            "autonomy_distribution": {
                "autonomous": self.autonomous_applied,
                "supervised": self.supervised_applied,
                "blocked": self.blocked
            },
            "avg_trust_score": self.avg_trust_score,
            "avg_verification_time_ms": self.avg_verification_time_ms,
            "template_hit_rate": self.template_hit_rate,
            "total_genesis_keys": self.total_genesis_keys
        }


# ============================================================================
# TEMPLATE COMPILER - GRACE ENHANCED
# ============================================================================

class ClarityTemplateCompiler:
    """
    Grace-aligned template compiler with Oracle integration.
    
    Deterministic code synthesis using templates, patterns from
    Oracle, and learned templates from Memory Mesh.
    """
    
    def __init__(self, knowledge_base_path: Optional[Path] = None):
        self.knowledge_base_path = knowledge_base_path or Path("knowledge_base")
        self.templates: Dict[str, Dict[str, Any]] = {}
        self.template_stats: Dict[str, Dict[str, int]] = {}
        self.oracle_patterns: Dict[str, Dict[str, Any]] = {}
        
        self._load_templates()
        self._load_learned_templates()
        self._load_oracle_patterns()
    
    def _load_templates(self):
        """Load comprehensive built-in templates."""
        self.templates = {
            # ================== LIST OPERATIONS ==================
            "list_filter": {
                "name": "List Filter",
                "category": "list_operations",
                "pattern_keywords": ["filter", "select", "where", "matching", "satisfying", "elements that"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    return [x for x in {iterable} if {condition}]""",
                "params": ["function_name", "params", "iterable", "condition"],
                "success_rate": 0.95
            },
            "list_map": {
                "name": "List Map/Transform",
                "category": "list_operations",
                "pattern_keywords": ["transform", "convert", "map", "apply", "each", "modify"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    return [{transform} for x in {iterable}]""",
                "params": ["function_name", "params", "iterable", "transform"],
                "success_rate": 0.94
            },
            "list_reduce": {
                "name": "List Reduce/Aggregate",
                "category": "list_operations", 
                "pattern_keywords": ["sum", "product", "aggregate", "reduce", "accumulate", "total", "combine"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    result = {initial}
    for x in {iterable}:
        result = {operation}
    return result""",
                "params": ["function_name", "params", "iterable", "initial", "operation"],
                "success_rate": 0.92
            },
            "list_find": {
                "name": "Find Element",
                "category": "list_operations",
                "pattern_keywords": ["find", "search", "locate", "first", "index", "position"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    for i, x in enumerate({iterable}):
        if {condition}:
            return {return_value}
    return {default}""",
                "params": ["function_name", "params", "iterable", "condition", "return_value", "default"],
                "success_rate": 0.91
            },
            "list_sort": {
                "name": "Sort List",
                "category": "list_operations",
                "pattern_keywords": ["sort", "order", "arrange", "ascending", "descending", "rank"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    return sorted({iterable}, key={key_func}, reverse={reverse})""",
                "params": ["function_name", "params", "iterable", "key_func", "reverse"],
                "success_rate": 0.96
            },
            "list_group": {
                "name": "Group By",
                "category": "list_operations",
                "pattern_keywords": ["group", "partition", "cluster", "categorize", "bucket", "segment"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    groups = {{}}
    for x in {iterable}:
        key = {key_expr}
        if key not in groups:
            groups[key] = []
        groups[key].append(x)
    return groups""",
                "params": ["function_name", "params", "iterable", "key_expr"],
                "success_rate": 0.90
            },
            "list_unique": {
                "name": "Remove Duplicates",
                "category": "list_operations",
                "pattern_keywords": ["unique", "distinct", "duplicates", "deduplicate", "remove duplicate"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    seen = set()
    result = []
    for x in {iterable}:
        if x not in seen:
            seen.add(x)
            result.append(x)
    return result""",
                "params": ["function_name", "params", "iterable"],
                "success_rate": 0.95
            },
            "list_flatten": {
                "name": "Flatten Nested List",
                "category": "list_operations",
                "pattern_keywords": ["flatten", "nested", "unnest", "concatenate lists"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    result = []
    for sublist in {iterable}:
        if isinstance(sublist, list):
            result.extend(sublist)
        else:
            result.append(sublist)
    return result""",
                "params": ["function_name", "params", "iterable"],
                "success_rate": 0.93
            },
            "list_max_min": {
                "name": "Find Max/Min Element",
                "category": "list_operations",
                "pattern_keywords": ["maximum", "minimum", "max", "min", "largest", "smallest", "biggest"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    if not {iterable}:
        return None
    return {operation}({iterable}, key={key_func})""",
                "params": ["function_name", "params", "iterable", "operation", "key_func"],
                "success_rate": 0.96
            },
            
            # ================== STRING OPERATIONS ==================
            "string_split_join": {
                "name": "String Split/Join",
                "category": "string_operations",
                "pattern_keywords": ["split", "join", "separator", "delimiter", "combine", "tokenize"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    parts = {input_str}.split({delimiter})
    return {join_delimiter}.join({transform})""",
                "params": ["function_name", "params", "input_str", "delimiter", "join_delimiter", "transform"],
                "success_rate": 0.93
            },
            "string_extract": {
                "name": "String Extract/Pattern",
                "category": "string_operations",
                "pattern_keywords": ["extract", "pattern", "regex", "match", "find", "parse"],
                "languages": ["python"],
                "template": """import re

def {function_name}({params}):
    match = re.search(r'{pattern}', {input_str})
    if match:
        return {return_expr}
    return {default}""",
                "params": ["function_name", "params", "pattern", "input_str", "return_expr", "default"],
                "success_rate": 0.88
            },
            "string_replace": {
                "name": "String Replace",
                "category": "string_operations",
                "pattern_keywords": ["replace", "substitute", "swap", "change", "modify string"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    return {input_str}.replace({old}, {new})""",
                "params": ["function_name", "params", "input_str", "old", "new"],
                "success_rate": 0.97
            },
            "string_reverse": {
                "name": "Reverse String",
                "category": "string_operations",
                "pattern_keywords": ["reverse", "backwards", "flip string", "mirror"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    return {input_str}[::-1]""",
                "params": ["function_name", "params", "input_str"],
                "success_rate": 0.99
            },
            "string_palindrome": {
                "name": "Palindrome Check",
                "category": "string_operations",
                "pattern_keywords": ["palindrome", "same backwards", "symmetric string"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    s = {input_str}.lower().replace(' ', '')
    return s == s[::-1]""",
                "params": ["function_name", "params", "input_str"],
                "success_rate": 0.97
            },
            "string_count": {
                "name": "Count Substring/Char",
                "category": "string_operations",
                "pattern_keywords": ["count", "occurrences", "frequency", "how many times"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    return {input_str}.count({substring})""",
                "params": ["function_name", "params", "input_str", "substring"],
                "success_rate": 0.98
            },
            
            # ================== MATH OPERATIONS ==================
            "math_factorial": {
                "name": "Factorial",
                "category": "math_operations",
                "pattern_keywords": ["factorial", "n!", "product of", "multiply 1 to n"],
                "languages": ["python"],
                "template": """def {function_name}(n):
    if n <= 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result""",
                "params": ["function_name"],
                "success_rate": 0.98
            },
            "math_fibonacci": {
                "name": "Fibonacci",
                "category": "math_operations",
                "pattern_keywords": ["fibonacci", "fib", "sequence", "previous two", "fib sequence"],
                "languages": ["python"],
                "template": """def {function_name}(n):
    if n <= 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b""",
                "params": ["function_name"],
                "success_rate": 0.97
            },
            "math_prime_check": {
                "name": "Prime Check",
                "category": "math_operations",
                "pattern_keywords": ["prime", "is prime", "check prime", "divisible", "prime number"],
                "languages": ["python"],
                "template": """def {function_name}(n):
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for i in range(3, int(n**0.5) + 1, 2):
        if n % i == 0:
            return False
    return True""",
                "params": ["function_name"],
                "success_rate": 0.96
            },
            "math_gcd": {
                "name": "GCD",
                "category": "math_operations",
                "pattern_keywords": ["gcd", "greatest common divisor", "hcf", "euclidean", "common factor"],
                "languages": ["python"],
                "template": """def {function_name}(a, b):
    while b:
        a, b = b, a % b
    return a""",
                "params": ["function_name"],
                "success_rate": 0.99
            },
            "math_lcm": {
                "name": "LCM",
                "category": "math_operations",
                "pattern_keywords": ["lcm", "least common multiple", "smallest multiple", "common multiple"],
                "languages": ["python"],
                "template": """def {function_name}(a, b):
    def gcd(x, y):
        while y:
            x, y = y, x % y
        return x
    return abs(a * b) // gcd(a, b)""",
                "params": ["function_name"],
                "success_rate": 0.98
            },
            "math_power": {
                "name": "Power/Exponent",
                "category": "math_operations",
                "pattern_keywords": ["power", "exponent", "raise to", "squared", "cubed", "to the power"],
                "languages": ["python"],
                "template": """def {function_name}(base, exp):
    return base ** exp""",
                "params": ["function_name"],
                "success_rate": 0.99
            },
            "math_sum_digits": {
                "name": "Sum of Digits",
                "category": "math_operations",
                "pattern_keywords": ["sum digits", "digit sum", "add digits", "sum of digits"],
                "languages": ["python"],
                "template": """def {function_name}(n):
    return sum(int(d) for d in str(abs(n)))""",
                "params": ["function_name"],
                "success_rate": 0.97
            },
            
            # ================== ALGORITHMS ==================
            "binary_search": {
                "name": "Binary Search",
                "category": "algorithms",
                "pattern_keywords": ["binary search", "search sorted", "find in sorted", "log n search", "bisect"],
                "languages": ["python"],
                "template": """def {function_name}(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1""",
                "params": ["function_name"],
                "success_rate": 0.97
            },
            "merge_sort": {
                "name": "Merge Sort",
                "category": "algorithms",
                "pattern_keywords": ["merge sort", "divide conquer sort", "stable sort", "nlogn sort"],
                "languages": ["python"],
                "template": """def {function_name}(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = {function_name}(arr[:mid])
    right = {function_name}(arr[mid:])
    return _merge(left, right)

def _merge(left, right):
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1
    result.extend(left[i:])
    result.extend(right[j:])
    return result""",
                "params": ["function_name"],
                "success_rate": 0.94
            },
            "quick_sort": {
                "name": "Quick Sort",
                "category": "algorithms",
                "pattern_keywords": ["quick sort", "partition sort", "pivot sort", "quicksort"],
                "languages": ["python"],
                "template": """def {function_name}(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return {function_name}(left) + middle + {function_name}(right)""",
                "params": ["function_name"],
                "success_rate": 0.95
            },
            "bubble_sort": {
                "name": "Bubble Sort",
                "category": "algorithms",
                "pattern_keywords": ["bubble sort", "simple sort", "swap sort", "bubblesort"],
                "languages": ["python"],
                "template": """def {function_name}(arr):
    arr = arr.copy()
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr""",
                "params": ["function_name"],
                "success_rate": 0.97
            },
            
            # ================== DATA STRUCTURES ==================
            "dict_merge": {
                "name": "Dictionary Merge",
                "category": "data_structures",
                "pattern_keywords": ["merge", "combine", "dict", "dictionary", "join dicts", "merge dictionaries"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    result = {{}}
    for d in {dicts}:
        result.update(d)
    return result""",
                "params": ["function_name", "params", "dicts"],
                "success_rate": 0.95
            },
            "dict_invert": {
                "name": "Dictionary Invert",
                "category": "data_structures",
                "pattern_keywords": ["invert", "reverse", "swap keys values", "flip", "invert dictionary"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    return {{v: k for k, v in {dict_var}.items()}}""",
                "params": ["function_name", "params", "dict_var"],
                "success_rate": 0.93
            },
            "dict_filter": {
                "name": "Filter Dictionary",
                "category": "data_structures",
                "pattern_keywords": ["filter dict", "select keys", "filter dictionary", "dict where"],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    return {{k: v for k, v in {dict_var}.items() if {condition}}}""",
                "params": ["function_name", "params", "dict_var", "condition"],
                "success_rate": 0.94
            },
            
            # ================== VALIDATION ==================
            "validate_email": {
                "name": "Email Validation",
                "category": "validation",
                "pattern_keywords": ["email", "validate email", "check email", "valid email", "email format"],
                "languages": ["python"],
                "template": """import re

def {function_name}(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{{2,}}$'
    return bool(re.match(pattern, email))""",
                "params": ["function_name"],
                "success_rate": 0.94
            },
            "validate_phone": {
                "name": "Phone Validation",
                "category": "validation",
                "pattern_keywords": ["phone", "validate phone", "phone number", "telephone", "phone format"],
                "languages": ["python"],
                "template": """import re

def {function_name}(phone):
    pattern = r'^\\+?1?[-.]?\\(?\\d{{3}}\\)?[-.]?\\d{{3}}[-.]?\\d{{4}}$'
    return bool(re.match(pattern, phone))""",
                "params": ["function_name"],
                "success_rate": 0.91
            },
            
            # ================== GENERIC ==================
            "simple_function": {
                "name": "Simple Function",
                "category": "generic",
                "pattern_keywords": [],
                "languages": ["python"],
                "template": """def {function_name}({params}):
    {body}
    return {return_value}""",
                "params": ["function_name", "params", "body", "return_value"],
                "success_rate": 0.70
            }
        }
        
        # Initialize stats
        for tid in self.templates:
            self.template_stats[tid] = {"uses": 0, "successes": 0, "failures": 0}
    
    def _load_learned_templates(self):
        """Load templates learned from knowledge base."""
        try:
            learned_path = self.knowledge_base_path / "learned_templates.json"
            if learned_path.exists():
                with open(learned_path, 'r') as f:
                    learned = json.load(f)
                    for tid, template in learned.items():
                        if tid not in self.templates:
                            self.templates[tid] = template
                            self.template_stats[tid] = {"uses": 0, "successes": 0, "failures": 0}
                logger.info(f"[CLARITY-TEMPLATES] Loaded {len(learned)} learned templates")
        except Exception as e:
            logger.debug(f"[CLARITY-TEMPLATES] No learned templates: {e}")
    
    def _load_oracle_patterns(self):
        """Load patterns from Oracle exports."""
        try:
            oracle_path = self.knowledge_base_path / "oracle" / "patterns.json"
            if oracle_path.exists():
                with open(oracle_path, 'r') as f:
                    self.oracle_patterns = json.load(f)
                logger.info(f"[CLARITY-TEMPLATES] Loaded {len(self.oracle_patterns)} Oracle patterns")
        except Exception as e:
            logger.debug(f"[CLARITY-TEMPLATES] No Oracle patterns: {e}")
    
    def match_templates(
        self,
        intent: ClarityIntent,
        oracle_boost: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[TemplateMatch]:
        """Match templates to intent with Oracle pattern boost."""
        matches = []
        description_lower = intent.desired_behavior.lower()
        
        for tid, template in self.templates.items():
            # Check language
            if intent.language.lower() not in [l.lower() for l in template.get("languages", ["python"])]:
                continue
            
            # Calculate keyword match score
            keywords = template.get("pattern_keywords", [])
            if not keywords:
                continue
            
            keyword_matches = sum(1 for kw in keywords if kw.lower() in description_lower)
            keyword_score = keyword_matches / len(keywords) if keywords else 0
            
            # Category boost
            category_boost = 0.1 if template.get("category", "") in description_lower else 0
            
            # Oracle pattern boost
            oracle_match_boost = 0.0
            if oracle_boost and tid in oracle_boost:
                oracle_match_boost = 0.15
            
            # Historical success rate
            stats = self.template_stats.get(tid, {})
            total = stats.get("uses", 0)
            historical_rate = stats.get("successes", 0) / total if total > 0 else template.get("success_rate", 0.5)
            
            # Combined score
            match_score = (
                keyword_score * 0.5 +
                historical_rate * 0.25 +
                category_boost * 0.1 +
                oracle_match_boost
            )
            
            if match_score > 0.1:
                matches.append(TemplateMatch(
                    template_id=tid,
                    template_name=template.get("name", tid),
                    match_score=match_score,
                    required_params=template.get("params", []),
                    filled_params={},
                    category=template.get("category", "generic"),
                    historical_success_rate=historical_rate,
                    oracle_boosted=oracle_match_boost > 0
                ))
        
        matches.sort(key=lambda m: m.match_score, reverse=True)
        return matches[:limit]
    
    def synthesize(
        self,
        match: TemplateMatch,
        params: Dict[str, Any]
    ) -> Optional[str]:
        """Synthesize code using template."""
        template = self.templates.get(match.template_id)
        if not template:
            return None
        
        try:
            code = template.get("template", "").format(**params)
            return code
        except KeyError as e:
            logger.warning(f"[CLARITY-TEMPLATES] Missing param {e}")
            return None
        except Exception as e:
            logger.error(f"[CLARITY-TEMPLATES] Synthesis error: {e}")
            return None
    
    def record_outcome(self, template_id: str, success: bool):
        """Record template outcome."""
        if template_id in self.template_stats:
            self.template_stats[template_id]["uses"] += 1
            if success:
                self.template_stats[template_id]["successes"] += 1
            else:
                self.template_stats[template_id]["failures"] += 1


# ============================================================================
# VERIFICATION GATE - ANTI-HALLUCINATION
# ============================================================================

class ClarityVerificationGate:
    """
    Multi-layer verification with anti-hallucination.
    
    Integrates with Grace's hallucination guard for LLM outputs.
    """
    
    def __init__(self):
        self.verification_history: List[Dict[str, Any]] = []
        self.hallucination_guard = None
        
        # Try to load hallucination guard (graceful failure)
        try:
            from llm_orchestrator.hallucination_guard import get_hallucination_guard
            self.hallucination_guard = get_hallucination_guard()
        except (ImportError, NameError, Exception) as e:
            logger.debug(f"[CLARITY-VERIFY] Hallucination guard not available: {e}")
    
    def verify(
        self,
        code: str,
        language: str = "python",
        test_cases: Optional[List[str]] = None,
        is_llm_generated: bool = False
    ) -> VerificationReport:
        """Run multi-layer verification."""
        start_time = time.time()
        report = VerificationReport(verification_id=str(uuid.uuid4())[:12])
        
        # Layer 1: Syntax
        report.syntax_valid = self._check_syntax(code, language)
        if not report.syntax_valid:
            report.errors.append({"layer": "syntax", "severity": "critical", "message": "Invalid syntax"})
        
        # Layer 2: AST
        if language == "python" and report.syntax_valid:
            report.ast_parseable = self._check_ast(code)
            if not report.ast_parseable:
                report.errors.append({"layer": "ast", "severity": "critical", "message": "AST parse failed"})
        else:
            report.ast_parseable = report.syntax_valid
        
        # Layer 3: Imports
        if report.ast_parseable:
            report.imports_resolve = self._check_imports(code, language)
        
        # Layer 4: Security
        report.security_safe = self._check_security(code)
        if not report.security_safe:
            report.errors.append({"layer": "security", "severity": "critical", "message": "Security issue"})
        
        # Layer 5: Tests
        if test_cases and report.syntax_valid:
            report.tests_passed = self._run_tests(code, test_cases)
            if not report.tests_passed:
                report.errors.append({"layer": "tests", "severity": "high", "message": "Tests failed"})
        
        # Layer 6: Anti-hallucination (for LLM outputs)
        if is_llm_generated and self.hallucination_guard:
            report.anti_hallucination_passed = self._check_hallucination(code)
        
        report.verification_time_ms = (time.time() - start_time) * 1000
        
        self.verification_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "passed": report.passed,
            "is_llm": is_llm_generated
        })
        
        return report
    
    def _check_syntax(self, code: str, language: str) -> bool:
        if language == "python":
            try:
                compile(code, "<string>", "exec")
                return True
            except SyntaxError:
                return False
        return True
    
    def _check_ast(self, code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except:
            return False
    
    def _check_imports(self, code: str, language: str) -> bool:
        if language != "python":
            return True
        try:
            tree = ast.parse(code)
            stdlib = {'re', 'os', 'sys', 'json', 'math', 'datetime', 'collections', 
                     'itertools', 'functools', 'typing', 'pathlib', 'time', 'random', 
                     'hashlib', 'copy', 'string', 'operator'}
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    pass  # Allow all imports for now
            return True
        except:
            return False
    
    def _check_security(self, code: str) -> bool:
        dangerous = [r'eval\s*\(', r'exec\s*\(', r'__import__\s*\(', 
                    r'subprocess\.call.*shell\s*=\s*True', r'os\.system\s*\(']
        for pattern in dangerous:
            if re.search(pattern, code):
                return False
        return True
    
    def _run_tests(self, code: str, test_cases: List[str]) -> bool:
        try:
            namespace = {}
            exec(code, namespace)
            for test in test_cases:
                try:
                    result = eval(test, namespace)
                    if result is False:
                        return False
                except (AssertionError, Exception):
                    return False
            return True
        except:
            return False
    
    def _check_hallucination(self, code: str) -> bool:
        """Check for hallucination indicators."""
        # Simple checks - the full guard handles more
        hallucination_indicators = [
            r'TODO:?\s*implement',
            r'pass\s*#\s*placeholder',
            r'\.\.\.\s*#\s*implement',
            r'raise\s+NotImplementedError',
        ]
        for pattern in hallucination_indicators:
            if re.search(pattern, code, re.IGNORECASE):
                return False
        return True


# ============================================================================
# TRUST MANAGER - GRACE ALIGNED
# ============================================================================

class ClarityTrustManager:
    """
    Trust-based autonomy with Grace's enhanced trust scorer.
    """
    
    def __init__(self):
        self.auto_threshold = 0.85
        self.supervised_threshold = 0.60
        
        # Try to load Grace trust scorer
        try:
            from cognitive.enhanced_trust_scorer import get_adaptive_trust_scorer
            self.trust_scorer = get_adaptive_trust_scorer()
        except ImportError:
            self.trust_scorer = None
    
    def calculate_trust(
        self,
        template_match: Optional[TemplateMatch],
        verification: VerificationReport,
        oracle_contributed: bool = False,
        healing_attempts: int = 0
    ) -> TrustDecision:
        """Calculate trust and determine gate."""
        factors = {}
        
        # Factor 1: Template reliability (25%)
        if template_match:
            factors["template_reliability"] = template_match.historical_success_rate
        else:
            factors["template_reliability"] = 0.5
        
        # Factor 2: Match confidence (15%)
        factors["match_confidence"] = template_match.match_score if template_match else 0.3
        
        # Factor 3: Verification strength (35%)
        v_score = 0.0
        if verification.syntax_valid:
            v_score += 0.25
        if verification.ast_parseable:
            v_score += 0.25
        if verification.security_safe:
            v_score += 0.2
        if verification.anti_hallucination_passed:
            v_score += 0.1
        if verification.tests_passed:
            v_score += 0.2
        elif verification.tests_passed is None:
            v_score += 0.1
        factors["verification_strength"] = v_score
        
        # Factor 4: Oracle contribution (10%)
        factors["oracle_contribution"] = 0.1 if oracle_contributed else 0.0
        
        # Factor 5: Healing penalty (15%)
        factors["healing_factor"] = max(0, 1.0 - (healing_attempts * 0.2))
        
        # Weighted calculation
        trust_score = (
            factors["template_reliability"] * 0.25 +
            factors["match_confidence"] * 0.15 +
            factors["verification_strength"] * 0.35 +
            factors["oracle_contribution"] * 0.10 +
            factors["healing_factor"] * 0.15
        )
        
        # Confidence interval
        uncertainty = 0.1 + (0.1 if verification.tests_passed is None else 0)
        confidence_interval = (
            max(0, trust_score - uncertainty),
            min(1, trust_score + uncertainty)
        )
        
        # Determine gate
        if trust_score >= self.auto_threshold:
            gate = TrustGate.AUTONOMOUS
            reasoning = "High trust - autonomous execution"
        elif trust_score >= self.supervised_threshold:
            gate = TrustGate.SUPERVISED
            reasoning = "Medium trust - supervised execution"
        else:
            gate = TrustGate.BLOCKED
            reasoning = "Low trust - blocked"
        
        return TrustDecision(
            trust_score=trust_score,
            confidence_interval=confidence_interval,
            uncertainty=uncertainty,
            gate=gate,
            factors=factors,
            reasoning=reasoning
        )


# ============================================================================
# GENESIS KEY INTEGRATION
# ============================================================================

class ClarityGenesisTracker:
    """
    Genesis Key integration for Clarity Framework.
    
    Tracks all operations with immutable Genesis Keys.
    """
    
    def __init__(self, session=None):
        self.session = session
        self.genesis_service = None
        self._load_genesis_service()
    
    def _load_genesis_service(self):
        try:
            from genesis.genesis_key_service import get_genesis_service
            self.genesis_service = get_genesis_service()
        except ImportError:
            logger.debug("[CLARITY-GENESIS] Genesis service not available")
    
    def create_key(
        self,
        key_type: str,
        description: str,
        context: Dict[str, Any],
        parent_key: Optional[str] = None
    ) -> Optional[str]:
        """Create a Genesis Key for tracking."""
        if not self.genesis_service:
            return None
        
        try:
            from models.genesis_key_models import GenesisKeyType as GKT
            
            # Map to actual GenesisKeyType (using existing types)
            type_map = {
                "clarity_task_start": GKT.CODING_AGENT_ACTION,
                "clarity_code_generated": GKT.AI_CODE_GENERATION,
                "clarity_verification_complete": GKT.SYSTEM_EVENT,
                "clarity_code_applied": GKT.FIX,
                "clarity_healing_attempt": GKT.FIX,
                "clarity_learning_stored": GKT.DATABASE_CHANGE,
                "clarity_task_complete": GKT.SYSTEM_EVENT,
                "clarity_task_failed": GKT.ERROR,
            }
            
            gk_type = type_map.get(key_type, GKT.CODING_AGENT_ACTION)
            
            key = self.genesis_service.create_key(
                key_type=gk_type,
                what_description=description,
                who_actor="ClarityFramework",
                where_location="cognitive/clarity_framework",
                why_reason=f"Clarity {key_type}",
                how_method="clarity_framework",
                context_data=context,
                parent_key_id=parent_key,
                session=self.session
            )
            
            return key.key_id
        except Exception as e:
            logger.warning(f"[CLARITY-GENESIS] Key creation failed: {e}")
            return None


# ============================================================================
# ORACLE LIAISON
# ============================================================================

class ClarityOracleLiaison:
    """
    Interface to Unified Oracle Hub.
    
    Consults Oracle for patterns, insights, and knowledge.
    """
    
    def __init__(self, session=None, knowledge_base_path: Optional[Path] = None):
        self.session = session
        self.knowledge_base_path = knowledge_base_path or Path("knowledge_base")
        self.oracle_hub = None
        self._load_oracle()
    
    def _load_oracle(self):
        try:
            from oracle_intelligence.unified_oracle_hub import get_oracle_hub
            self.oracle_hub = get_oracle_hub()
        except ImportError:
            logger.debug("[CLARITY-ORACLE] Oracle Hub not available")
    
    def consult(
        self,
        query: str,
        intent: ClarityIntent
    ) -> OracleConsultation:
        """Consult Oracle for relevant knowledge."""
        consultation_id = str(uuid.uuid4())[:12]
        
        insights = []
        relevant_templates = []
        code_examples = []
        sources = []
        confidence = 0.5
        
        if self.oracle_hub:
            try:
                # Query Oracle for patterns
                result = self.oracle_hub.query_patterns(
                    query=query,
                    context={
                        "task_type": intent.task_type,
                        "language": intent.language
                    }
                )
                
                if result:
                    insights = result.get("insights", [])
                    relevant_templates = result.get("templates", [])
                    code_examples = result.get("code_examples", [])
                    sources = result.get("sources", [])
                    confidence = result.get("confidence", 0.7)
            except Exception as e:
                logger.debug(f"[CLARITY-ORACLE] Consultation error: {e}")
        
        # Also check local pattern cache
        pattern_path = self.knowledge_base_path / "oracle" / "patterns.json"
        if pattern_path.exists():
            try:
                with open(pattern_path, 'r') as f:
                    patterns = json.load(f)
                    for pid, pattern in patterns.items():
                        if any(kw in query.lower() for kw in pattern.get("keywords", [])):
                            relevant_templates.append(pid)
                            if pattern.get("code"):
                                code_examples.append(pattern.get("code"))
            except:
                pass
        
        return OracleConsultation(
            consultation_id=consultation_id,
            query=query,
            insights=insights,
            relevant_templates=list(set(relevant_templates)),
            relevant_patterns=[],
            code_examples=code_examples[:3],
            confidence=confidence,
            sources=sources
        )


# ============================================================================
# MEMORY MESH LEARNER
# ============================================================================

class ClarityMemoryLearner:
    """
    Memory Mesh integration for learning.
    
    Updates learning memory with outcomes for continuous improvement.
    Supports both database-backed and file-based memory.
    """
    
    def __init__(self, session=None, knowledge_base_path: Optional[Path] = None):
        self.session = session
        self.knowledge_base_path = knowledge_base_path or Path("knowledge_base")
        self.memory_mesh = None
        self.memory_mesh_learner = None
        self.learning_memory_manager = None
        self.file_based_memory: List[Dict[str, Any]] = []
        
        # Ensure memory directories exist
        self.clarity_memory_path = self.knowledge_base_path / "clarity_memory"
        self.clarity_memory_path.mkdir(parents=True, exist_ok=True)
        
        self._load_memory_systems()
    
    def _load_memory_systems(self):
        """Load all available memory systems."""
        # Try full Memory Mesh Integration
        try:
            from cognitive.memory_mesh_integration import get_memory_mesh_integration
            if self.session:
                self.memory_mesh = get_memory_mesh_integration(
                    session=self.session,
                    knowledge_base_path=self.knowledge_base_path
                )
                logger.info("[CLARITY-MEMORY] Memory Mesh Integration connected")
        except (ImportError, RuntimeError, Exception) as e:
            logger.debug(f"[CLARITY-MEMORY] Memory Mesh Integration not available: {e}")
        
        # Try Memory Mesh Learner (for gap analysis)
        try:
            from cognitive.memory_mesh_learner import MemoryMeshLearner
            if self.session:
                self.memory_mesh_learner = MemoryMeshLearner(session=self.session)
                logger.info("[CLARITY-MEMORY] Memory Mesh Learner connected")
        except (ImportError, RuntimeError, Exception) as e:
            logger.debug(f"[CLARITY-MEMORY] Memory Mesh Learner not available: {e}")
        
        # Try Learning Memory Manager
        try:
            from cognitive.learning_memory import LearningMemoryManager
            if self.session:
                self.learning_memory_manager = LearningMemoryManager(
                    session=self.session,
                    knowledge_base_path=self.knowledge_base_path
                )
                logger.info("[CLARITY-MEMORY] Learning Memory Manager connected")
        except (ImportError, RuntimeError, Exception) as e:
            logger.debug(f"[CLARITY-MEMORY] Learning Memory Manager not available: {e}")
        
        # Load file-based memory as fallback
        self._load_file_memory()
    
    def _load_file_memory(self):
        """Load file-based memory for when database is unavailable."""
        try:
            memory_file = self.clarity_memory_path / "learning_history.json"
            if memory_file.exists():
                with open(memory_file, 'r') as f:
                    self.file_based_memory = json.load(f)
                logger.info(f"[CLARITY-MEMORY] Loaded {len(self.file_based_memory)} file-based memories")
        except Exception as e:
            logger.debug(f"[CLARITY-MEMORY] File memory load failed: {e}")
    
    def _save_file_memory(self):
        """Save file-based memory."""
        try:
            memory_file = self.clarity_memory_path / "learning_history.json"
            with open(memory_file, 'w') as f:
                json.dump(self.file_based_memory[-1000:], f, indent=2, default=str)
        except Exception as e:
            logger.debug(f"[CLARITY-MEMORY] File memory save failed: {e}")
    
    @property
    def is_connected(self) -> bool:
        """Check if any memory system is connected."""
        return (
            self.memory_mesh is not None or
            self.learning_memory_manager is not None or
            len(self.file_based_memory) >= 0  # File-based always available
        )
    
    def learn_from_outcome(
        self,
        state: ClarityState,
        success: bool
    ) -> Optional[str]:
        """Store learning from task outcome."""
        learning_id = None
        
        # Build learning data
        context = {
            "task_type": state.intent.task_type if state.intent else "unknown",
            "language": state.intent.language if state.intent else "python",
            "description": state.intent.desired_behavior[:200] if state.intent else "",
            "template_used": state.selected_template.template_id if state.selected_template else None,
            "template_name": state.selected_template.template_name if state.selected_template else None,
            "oracle_consulted": state.oracle_consultation is not None,
            "match_score": state.selected_template.match_score if state.selected_template else 0
        }
        
        action = {
            "phase": state.phase.value,
            "template_match_score": state.selected_template.match_score if state.selected_template else 0,
            "healing_attempts": state.healing_attempts,
            "llm_escalations": state.llm_escalations,
            "llm_used": state.intent.llm_used if state.intent else False
        }
        
        outcome = {
            "success": success,
            "trust_score": state.trust_decision.trust_score if state.trust_decision else 0,
            "trust_gate": state.trust_decision.gate.value if state.trust_decision else None,
            "verification_passed": state.verification.passed if state.verification else False,
            "syntax_valid": state.verification.syntax_valid if state.verification else False,
            "tests_passed": state.verification.tests_passed if state.verification else None
        }
        
        # Try database-backed memory first
        if self.memory_mesh:
            try:
                learning_id = self.memory_mesh.ingest_learning_experience(
                    experience_type="clarity_coding_task",
                    context=context,
                    action_taken=action,
                    outcome=outcome,
                    source="clarity_framework",
                    genesis_key_id=state.parent_genesis_key
                )
                logger.debug(f"[CLARITY-MEMORY] Stored in Memory Mesh: {learning_id}")
            except Exception as e:
                logger.warning(f"[CLARITY-MEMORY] Memory Mesh storage failed: {e}")
        
        # Also try Learning Memory Manager
        if self.learning_memory_manager and not learning_id:
            try:
                learning_data = {
                    'context': context,
                    'expected': {"success": True},
                    'actual': outcome
                }
                example = self.learning_memory_manager.ingest_learning_data(
                    learning_type="clarity_task",
                    learning_data=learning_data,
                    source="clarity_framework",
                    genesis_key_id=state.parent_genesis_key
                )
                learning_id = str(example.id) if example else None
                logger.debug(f"[CLARITY-MEMORY] Stored in Learning Memory: {learning_id}")
            except Exception as e:
                logger.warning(f"[CLARITY-MEMORY] Learning Memory storage failed: {e}")
        
        # Always store in file-based memory as backup
        file_entry = {
            "id": learning_id or str(uuid.uuid4())[:12],
            "timestamp": datetime.utcnow().isoformat(),
            "task_id": state.task_id,
            "context": context,
            "action": action,
            "outcome": outcome,
            "success": success,
            "genesis_key": state.parent_genesis_key
        }
        self.file_based_memory.append(file_entry)
        self._save_file_memory()
        
        if not learning_id:
            learning_id = file_entry["id"]
        
        return learning_id
    
    def get_similar_experiences(
        self,
        description: str,
        template_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar past experiences for learning.
        
        Used to improve template matching and synthesis.
        """
        similar = []
        
        # Search file-based memory
        for entry in reversed(self.file_based_memory):
            if not entry.get("outcome", {}).get("success"):
                continue
            
            context = entry.get("context", {})
            
            # Match by template
            if template_id and context.get("template_used") == template_id:
                similar.append(entry)
                if len(similar) >= limit:
                    break
                continue
            
            # Simple keyword matching
            past_desc = context.get("description", "").lower()
            if any(word in past_desc for word in description.lower().split()[:5]):
                similar.append(entry)
                if len(similar) >= limit:
                    break
        
        return similar
    
    def get_template_success_history(
        self,
        template_id: str
    ) -> Dict[str, Any]:
        """Get success history for a specific template."""
        successes = 0
        failures = 0
        avg_trust = 0.0
        
        for entry in self.file_based_memory:
            if entry.get("context", {}).get("template_used") == template_id:
                if entry.get("success"):
                    successes += 1
                    avg_trust += entry.get("outcome", {}).get("trust_score", 0)
                else:
                    failures += 1
        
        total = successes + failures
        return {
            "template_id": template_id,
            "total_uses": total,
            "successes": successes,
            "failures": failures,
            "success_rate": successes / total if total > 0 else 0,
            "avg_trust_score": avg_trust / successes if successes > 0 else 0
        }
    
    def identify_knowledge_gaps(self) -> List[Dict[str, Any]]:
        """
        Identify knowledge gaps from memory.
        
        Returns templates/patterns that have low success rates.
        """
        gaps = []
        
        # Try database-backed learner first
        if self.memory_mesh_learner:
            try:
                gaps = self.memory_mesh_learner.identify_knowledge_gaps()
                if gaps:
                    return gaps
            except Exception as e:
                logger.debug(f"[CLARITY-MEMORY] Gap analysis from DB failed: {e}")
        
        # Fall back to file-based analysis
        template_stats: Dict[str, Dict[str, int]] = {}
        
        for entry in self.file_based_memory:
            template = entry.get("context", {}).get("template_used")
            if not template:
                continue
            
            if template not in template_stats:
                template_stats[template] = {"success": 0, "failure": 0}
            
            if entry.get("success"):
                template_stats[template]["success"] += 1
            else:
                template_stats[template]["failure"] += 1
        
        for template, stats in template_stats.items():
            total = stats["success"] + stats["failure"]
            if total >= 3:  # Minimum attempts
                success_rate = stats["success"] / total
                if success_rate < 0.7:  # Below threshold
                    gaps.append({
                        "template_id": template,
                        "success_rate": success_rate,
                        "total_attempts": total,
                        "recommendation": "improve_template",
                        "reason": f"Template '{template}' has {success_rate:.0%} success rate"
                    })
        
        gaps.sort(key=lambda x: x["success_rate"])
        return gaps
    
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get overall learning statistics."""
        total = len(self.file_based_memory)
        successes = sum(1 for e in self.file_based_memory if e.get("success"))
        template_used = sum(1 for e in self.file_based_memory 
                          if e.get("context", {}).get("template_used") and 
                          not e.get("action", {}).get("llm_used"))
        
        return {
            "total_learnings": total,
            "successful_tasks": successes,
            "success_rate": successes / total if total > 0 else 0,
            "template_only_tasks": template_used,
            "llm_independence_rate": template_used / total if total > 0 else 0,
            "memory_systems": {
                "memory_mesh": self.memory_mesh is not None,
                "memory_mesh_learner": self.memory_mesh_learner is not None,
                "learning_memory_manager": self.learning_memory_manager is not None,
                "file_based_entries": len(self.file_based_memory)
            },
            "knowledge_gaps": len(self.identify_knowledge_gaps())
        }
    
    def feedback_update(
        self,
        learning_id: str,
        was_correct: bool
    ):
        """
        Update memory based on feedback.
        
        Called when we learn if a past decision was correct.
        """
        # Update file-based memory
        for entry in self.file_based_memory:
            if entry.get("id") == learning_id:
                entry["feedback"] = {
                    "was_correct": was_correct,
                    "feedback_time": datetime.utcnow().isoformat()
                }
                break
        
        self._save_file_memory()
        
        # Update database if available
        if self.memory_mesh:
            try:
                self.memory_mesh.feedback_loop_update(
                    learning_example_id=learning_id,
                    actual_outcome={"was_correct": was_correct},
                    success=was_correct
                )
            except Exception as e:
                logger.debug(f"[CLARITY-MEMORY] Feedback update failed: {e}")


# ============================================================================
# MAIN CLARITY FRAMEWORK
# ============================================================================

class ClarityFramework:
    """
    Clarity Framework - Grace-Aligned Coding Agent Cognitive Framework.
    
    A cognitive coding agent that competes with LLMs by using:
    - Deterministic template-first code generation
    - Unified Oracle intelligence integration
    - Memory Mesh learning and feedback loops
    - Genesis Key tracking for all operations
    - Multi-layer verification with anti-hallucination
    - Trust-scored autonomous execution
    - Bidirectional self-healing
    """
    
    def __init__(
        self,
        session=None,
        knowledge_base_path: Optional[Path] = None,
        enable_llm_fallback: bool = True,
        max_parallel_agents: int = 4
    ):
        self.session = session
        self.knowledge_base_path = knowledge_base_path or Path("knowledge_base")
        self.enable_llm_fallback = enable_llm_fallback
        self.max_parallel_agents = max_parallel_agents
        
        # Initialize Grace-aligned components
        self.template_compiler = ClarityTemplateCompiler(self.knowledge_base_path)
        self.verification_gate = ClarityVerificationGate()
        self.trust_manager = ClarityTrustManager()
        self.genesis_tracker = ClarityGenesisTracker(session)
        self.oracle_liaison = ClarityOracleLiaison(session, self.knowledge_base_path)
        self.memory_learner = ClarityMemoryLearner(session, self.knowledge_base_path)
        
        # LLM orchestrator (fallback only)
        self.llm_orchestrator = None
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=max_parallel_agents)
        
        # KPI tracking
        self.kpi = ClarityKPIs()
        
        logger.info(
            f"[CLARITY] Framework initialized with {len(self.template_compiler.templates)} templates, "
            f"Genesis tracking={'enabled' if self.genesis_tracker.genesis_service else 'disabled'}, "
            f"Oracle={'connected' if self.oracle_liaison.oracle_hub else 'local'}"
        )
    
    def solve(
        self,
        description: str,
        language: str = "python",
        test_cases: Optional[List[str]] = None,
        function_name: Optional[str] = None,
        timeout_seconds: float = 30.0
    ) -> Dict[str, Any]:
        """
        Solve a coding task using Grace-aligned cognitive framework.
        
        Phases (OODA Loop):
        1. OBSERVE: Parse intent, extract requirements
        2. ORIENT: Consult Oracle, match templates
        3. DECIDE: Select approach, calculate trust
        4. ACT: Generate code, verify, apply
        5. LEARN: Update memory mesh
        """
        start_time = time.time()
        task_id = str(uuid.uuid4())[:12]
        
        # Initialize state
        state = ClarityState(task_id=task_id, phase=ClarityPhase.OBSERVE)
        
        # Create parent Genesis Key
        parent_key = self.genesis_tracker.create_key(
            key_type="clarity_task_start",
            description=f"Clarity task: {description[:50]}...",
            context={"task_id": task_id, "language": language}
        )
        state.parent_genesis_key = parent_key
        if parent_key:
            state.genesis_keys.append(parent_key)
            self.kpi.total_genesis_keys += 1
        
        try:
            # ==================== OBSERVE ====================
            phase_start = time.time()
            state = self._observe(state, description, language, test_cases, function_name)
            state.phase_times["observe"] = time.time() - phase_start
            
            # ==================== ORIENT ====================
            state.phase = ClarityPhase.ORIENT
            phase_start = time.time()
            state = self._orient(state)
            state.phase_times["orient"] = time.time() - phase_start
            
            # ==================== DECIDE ====================
            state.phase = ClarityPhase.DECIDE
            phase_start = time.time()
            state = self._decide(state)
            state.phase_times["decide"] = time.time() - phase_start
            
            # ==================== ACT ====================
            state.phase = ClarityPhase.ACT
            phase_start = time.time()
            state = self._act(state, test_cases)
            state.phase_times["act"] = time.time() - phase_start
            
            # Self-healing loop
            while state.verification and not state.verification.passed:
                if state.healing_attempts >= state.max_healing_attempts:
                    break
                state = self._heal(state, test_cases)
            
            # ==================== LEARN ====================
            state.phase = ClarityPhase.LEARN
            phase_start = time.time()
            success = state.verification and state.verification.passed
            self._learn(state, success)
            state.phase_times["learn"] = time.time() - phase_start
            
            # Finalize
            if success:
                state.phase = ClarityPhase.COMPLETE
                self._update_kpi(state, True)
                
                # Create completion Genesis Key
                self.genesis_tracker.create_key(
                    key_type="clarity_task_complete",
                    description=f"Task completed successfully",
                    context={"trust_score": state.trust_decision.trust_score if state.trust_decision else 0},
                    parent_key=parent_key
                )
            else:
                state.phase = ClarityPhase.FAILED
                self._update_kpi(state, False)
                
                self.genesis_tracker.create_key(
                    key_type="clarity_task_failed",
                    description=f"Task failed",
                    context={"errors": state.errors[:3]},
                    parent_key=parent_key
                )
            
            state.completed_at = datetime.utcnow()
            state.metrics["total_time_ms"] = (time.time() - start_time) * 1000
            
            return self._build_result(state)
            
        except Exception as e:
            logger.error(f"[CLARITY] Error: {e}\n{traceback.format_exc()}")
            state.phase = ClarityPhase.FAILED
            state.errors.append(str(e))
            self._update_kpi(state, False)
            return self._build_result(state)
    
    def _observe(
        self,
        state: ClarityState,
        description: str,
        language: str,
        test_cases: Optional[List[str]],
        function_name: Optional[str]
    ) -> ClarityState:
        """OBSERVE phase: Parse intent from user request."""
        # Extract function name from test cases if not provided
        if not function_name and test_cases:
            for test in test_cases:
                match = re.search(r'(\w+)\s*\(', str(test))
                if match:
                    function_name = match.group(1)
                    break
        
        state.intent = ClarityIntent(
            intent_id=str(uuid.uuid4())[:12],
            task_type="code_generation",
            language=language,
            framework=None,
            target_symbols=[function_name] if function_name else [],
            desired_behavior=description,
            constraints={
                "test_cases": test_cases or [],
                "function_name": function_name
            },
            confidence=1.0,
            llm_used=False,
            genesis_key_id=state.parent_genesis_key
        )
        
        return state
    
    def _orient(self, state: ClarityState) -> ClarityState:
        """ORIENT phase: Consult Oracle, match templates."""
        if not state.intent:
            return state
        
        # Consult Oracle
        consultation = self.oracle_liaison.consult(
            query=state.intent.desired_behavior,
            intent=state.intent
        )
        state.oracle_consultation = consultation
        
        if consultation.genesis_key_id:
            state.genesis_keys.append(consultation.genesis_key_id)
        
        # Match templates with Oracle boost
        oracle_boost = consultation.relevant_templates if consultation else None
        state.template_matches = self.template_compiler.match_templates(
            state.intent,
            oracle_boost=oracle_boost
        )
        
        return state
    
    def _decide(self, state: ClarityState) -> ClarityState:
        """DECIDE phase: Select approach."""
        if state.template_matches:
            state.selected_template = state.template_matches[0]
        return state
    
    def _act(self, state: ClarityState, test_cases: Optional[List[str]]) -> ClarityState:
        """ACT phase: Generate and verify code."""
        if not state.intent:
            return state
        
        # Try template synthesis
        if state.selected_template:
            # Build params
            params = {
                "function_name": state.intent.target_symbols[0] if state.intent.target_symbols else "solve",
                "params": state.intent.constraints.get("params", "x"),
            }
            
            # Category-specific params
            category = state.selected_template.category
            if category == "list_operations":
                params.update({"iterable": "x", "condition": "True", "transform": "x"})
            
            code = self.template_compiler.synthesize(state.selected_template, params)
            
            if code:
                state.synthesis = SynthesisResult(
                    synthesis_id=str(uuid.uuid4())[:12],
                    template_id=state.selected_template.template_id,
                    code=code,
                    transform_type="template",
                    confidence=state.selected_template.match_score,
                    provenance={"template_name": state.selected_template.template_name}
                )
        
        # LLM fallback if needed
        if not state.synthesis and self.enable_llm_fallback:
            state = self._llm_fallback(state, test_cases)
        
        # Verify
        if state.synthesis:
            is_llm = state.synthesis.transform_type == "llm_fallback"
            state.verification = self.verification_gate.verify(
                code=state.synthesis.code,
                language=state.intent.language,
                test_cases=test_cases,
                is_llm_generated=is_llm
            )
            
            # Calculate trust
            state.trust_decision = self.trust_manager.calculate_trust(
                template_match=state.selected_template,
                verification=state.verification,
                oracle_contributed=state.oracle_consultation is not None,
                healing_attempts=state.healing_attempts
            )
        
        return state
    
    def _heal(self, state: ClarityState, test_cases: Optional[List[str]]) -> ClarityState:
        """Self-healing attempt."""
        state.healing_attempts += 1
        state.healing_history.append({
            "attempt": state.healing_attempts,
            "timestamp": datetime.utcnow().isoformat(),
            "errors": state.verification.errors if state.verification else []
        })
        
        # Create healing Genesis Key
        self.genesis_tracker.create_key(
            key_type="clarity_healing_attempt",
            description=f"Healing attempt {state.healing_attempts}",
            context={"errors": state.errors[:3]},
            parent_key=state.parent_genesis_key
        )
        
        # Try next template
        if state.template_matches and len(state.template_matches) > 1:
            current_idx = 0
            for i, m in enumerate(state.template_matches):
                if state.selected_template and m.template_id == state.selected_template.template_id:
                    current_idx = i
                    break
            
            if current_idx + 1 < len(state.template_matches):
                state.selected_template = state.template_matches[current_idx + 1]
                return self._act(state, test_cases)
        
        # LLM escalation if all templates failed
        if self.enable_llm_fallback and state.llm_escalations < 1:
            return self._llm_fallback(state, test_cases)
        
        return state
    
    def _llm_fallback(self, state: ClarityState, test_cases: Optional[List[str]]) -> ClarityState:
        """LLM fallback when templates fail."""
        state.llm_escalations += 1
        self.kpi.llm_fallback += 1
        
        try:
            if not self.llm_orchestrator:
                from llm_orchestrator.llm_orchestrator import LLMOrchestrator
                from database.session import get_session
                session = self.session or next(get_session())
                self.llm_orchestrator = LLMOrchestrator(
                    session=session,
                    knowledge_base_path=str(self.knowledge_base_path)
                )
            
            if hasattr(self.llm_orchestrator, 'grace_aligned_llm'):
                function_name = state.intent.target_symbols[0] if state.intent and state.intent.target_symbols else "solve"
                description = state.intent.desired_behavior if state.intent else ""
                
                prompt = f"""Generate a Python function that: {description}

Function name: {function_name}
"""
                if test_cases:
                    prompt += "\nTest cases:\n" + "\n".join(test_cases[:3])
                prompt += "\n\nGenerate ONLY Python code. No explanation."
                
                response = self.llm_orchestrator.grace_aligned_llm.generate(
                    prompt=prompt,
                    context={"task_type": "code_generation"},
                    max_tokens=1024,
                    temperature=0.2
                )
                
                if response.get("success") and response.get("content"):
                    code = response.get("content", "").strip()
                    # Clean markdown
                    if code.startswith("```"):
                        code = re.sub(r'^```\w*\n?', '', code)
                        code = re.sub(r'\n?```$', '', code)
                    
                    state.synthesis = SynthesisResult(
                        synthesis_id=str(uuid.uuid4())[:12],
                        template_id=None,
                        code=code.strip(),
                        transform_type="llm_fallback",
                        confidence=0.6,
                        provenance={"source": "llm_fallback"}
                    )
                    
                    if state.intent:
                        state.intent.llm_used = True
                    
                    # Verify with anti-hallucination
                    state.verification = self.verification_gate.verify(
                        code=code,
                        language=state.intent.language if state.intent else "python",
                        test_cases=test_cases,
                        is_llm_generated=True
                    )
                    
                    state.trust_decision = self.trust_manager.calculate_trust(
                        template_match=None,
                        verification=state.verification,
                        oracle_contributed=False,
                        healing_attempts=state.healing_attempts
                    )
        
        except Exception as e:
            logger.error(f"[CLARITY] LLM fallback error: {e}")
            state.errors.append(f"LLM fallback failed: {e}")
        
        return state
    
    def _learn(self, state: ClarityState, success: bool):
        """LEARN phase: Update memory mesh."""
        # Record template outcome
        if state.selected_template:
            self.template_compiler.record_outcome(state.selected_template.template_id, success)
        
        # Store in memory mesh
        learning_id = self.memory_learner.learn_from_outcome(state, success)
        
        if learning_id:
            self.genesis_tracker.create_key(
                key_type="clarity_learning_stored",
                description=f"Learning stored: {'success' if success else 'failure'}",
                context={"learning_id": learning_id},
                parent_key=state.parent_genesis_key
            )
    
    def _update_kpi(self, state: ClarityState, success: bool):
        """Update KPI metrics."""
        self.kpi.total_tasks += 1
        
        if success:
            if state.intent and not state.intent.llm_used:
                self.kpi.template_solved += 1
            if state.oracle_consultation:
                self.kpi.oracle_assisted += 1
            self.kpi.verification_passes += 1
            
            if state.trust_decision:
                if state.trust_decision.gate == TrustGate.AUTONOMOUS:
                    self.kpi.autonomous_applied += 1
                elif state.trust_decision.gate == TrustGate.SUPERVISED:
                    self.kpi.supervised_applied += 1
                
                # Update average trust score
                n = self.kpi.total_tasks
                self.kpi.avg_trust_score = (
                    (self.kpi.avg_trust_score * (n - 1) + state.trust_decision.trust_score) / n
                )
            
            if state.healing_attempts > 0:
                self.kpi.self_healing_success += 1
        else:
            self.kpi.verification_failures += 1
            self.kpi.blocked += 1
            if state.healing_attempts > 0:
                self.kpi.self_healing_failure += 1
        
        # Update verification time
        if state.verification:
            n = self.kpi.total_tasks
            self.kpi.avg_verification_time_ms = (
                (self.kpi.avg_verification_time_ms * (n - 1) + state.verification.verification_time_ms) / n
            )
    
    def _build_result(self, state: ClarityState) -> Dict[str, Any]:
        """Build result dictionary."""
        return {
            "success": state.phase == ClarityPhase.COMPLETE,
            "task_id": state.task_id,
            "code": state.synthesis.code if state.synthesis else None,
            "llm_used": state.intent.llm_used if state.intent else False,
            "template_used": state.selected_template.template_name if state.selected_template else None,
            "oracle_consulted": state.oracle_consultation is not None,
            "trust_score": state.trust_decision.trust_score if state.trust_decision else 0.0,
            "trust_gate": state.trust_decision.gate.value if state.trust_decision else None,
            "verification": {
                "passed": state.verification.passed if state.verification else False,
                "syntax_valid": state.verification.syntax_valid if state.verification else False,
                "tests_passed": state.verification.tests_passed if state.verification else None,
                "anti_hallucination": state.verification.anti_hallucination_passed if state.verification else True,
                "errors": state.verification.errors if state.verification else []
            } if state.verification else None,
            "healing_attempts": state.healing_attempts,
            "llm_escalations": state.llm_escalations,
            "genesis_keys": state.genesis_keys,
            "phase_times": state.phase_times,
            "errors": state.errors,
            "phase": state.phase.value
        }
    
    def get_kpi_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive KPI dashboard."""
        # Get memory learning stats
        memory_stats = self.memory_learner.get_learning_stats()
        knowledge_gaps = self.memory_learner.identify_knowledge_gaps()
        
        return {
            "summary": self.kpi.to_dict(),
            "template_coverage": {
                "total_templates": len(self.template_compiler.templates),
                "stats": self.template_compiler.template_stats
            },
            "grace_integration": {
                "genesis_tracking": self.genesis_tracker.genesis_service is not None,
                "oracle_connected": self.oracle_liaison.oracle_hub is not None,
                "memory_mesh_active": self.memory_learner.is_connected,
                "trust_scorer": self.trust_manager.trust_scorer is not None
            },
            "memory_mesh": {
                "connected": self.memory_learner.is_connected,
                "systems": memory_stats.get("memory_systems", {}),
                "total_learnings": memory_stats.get("total_learnings", 0),
                "success_rate": memory_stats.get("success_rate", 0),
                "knowledge_gaps_found": len(knowledge_gaps)
            },
            "knowledge_gaps": knowledge_gaps[:5],  # Top 5 gaps
            "competing_metrics": {
                "llm_independence_rate": (
                    (self.kpi.total_tasks - self.kpi.llm_fallback) / 
                    max(self.kpi.total_tasks, 1) * 100
                ),
                "autonomous_rate": (
                    self.kpi.autonomous_applied / max(self.kpi.total_tasks, 1) * 100
                ),
                "template_hit_rate": self.kpi.template_hit_rate * 100,
                "historical_success_rate": memory_stats.get("success_rate", 0) * 100
            }
        }
    
    def batch_solve(
        self,
        tasks: List[Dict[str, Any]],
        parallel: bool = True
    ) -> List[Dict[str, Any]]:
        """Solve multiple tasks."""
        results = []
        
        if parallel:
            futures = []
            for task in tasks:
                future = self.executor.submit(
                    self.solve,
                    description=task.get("description", ""),
                    language=task.get("language", "python"),
                    test_cases=task.get("test_cases"),
                    function_name=task.get("function_name")
                )
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append({"success": False, "error": str(e)})
        else:
            for task in tasks:
                result = self.solve(
                    description=task.get("description", ""),
                    language=task.get("language", "python"),
                    test_cases=task.get("test_cases"),
                    function_name=task.get("function_name")
                )
                results.append(result)
        
        return results


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

_clarity_framework: Optional[ClarityFramework] = None


def get_clarity_framework(
    session=None,
    knowledge_base_path: Optional[Path] = None,
    enable_llm_fallback: bool = True
) -> ClarityFramework:
    """Get or create the global Clarity Framework instance."""
    global _clarity_framework
    if _clarity_framework is None:
        _clarity_framework = ClarityFramework(
            session=session,
            knowledge_base_path=knowledge_base_path,
            enable_llm_fallback=enable_llm_fallback
        )
    return _clarity_framework


# Alias for backwards compatibility
CodingAgentCognitiveFramework = ClarityFramework
get_coding_agent_cognitive_framework = get_clarity_framework
